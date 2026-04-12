"""
Neo4j Database Client
Handles all graph database operations for brands, products, and generations.
"""
from neo4j import GraphDatabase
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid

from app.config import get_settings


class Neo4jClient:
    """Client for Neo4j Aura database operations"""
    
    def __init__(self):
        self._driver = None
        self._connection_attempted = False
    
    @property
    def driver(self):
        """Lazy initialization of Neo4j driver"""
        if self._driver is None and not self._connection_attempted:
            self._connection_attempted = True
            settings = get_settings()
            if settings.neo4j_uri and settings.neo4j_password:
                try:
                    self._driver = GraphDatabase.driver(
                        settings.neo4j_uri,
                        auth=(settings.neo4j_user, settings.neo4j_password)
                    )
                except Exception as e:
                    print(f"Failed to create Neo4j driver: {e}")
                    self._driver = None
        return self._driver
    
    def _ensure_connected(self):
        """Raise an error if not connected to database"""
        if self.driver is None:
            raise ConnectionError("Not connected to Neo4j database. Check your NEO4J_URI and NEO4J_PASSWORD in .env")
    
    def close(self):
        """Close the database connection"""
        if self._driver:
            self._driver.close()
            self._driver = None
            self._connection_attempted = False
    
    def verify_connection(self) -> bool:
        """Verify connection to Neo4j is working"""
        try:
            if not self.driver:
                return False
            with self.driver.session() as session:
                session.run("RETURN 1")
            return True
        except Exception as e:
            print(f"Neo4j connection error: {e}")
            return False
    
    def execute_query(self, query: str, parameters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Execute a Cypher query and return results as list of dicts.
        
        Args:
            query: Cypher query string
            parameters: Optional parameters dict
            
        Returns:
            List of record dicts
        """
        self._ensure_connected()
        parameters = parameters or {}
        
        with self.driver.session() as session:
            result = session.run(query, parameters)
            return [dict(record) for record in result]
    
    # === Brand Operations ===
    
    def create_brand(self, data: Dict[str, Any]) -> str:
        """
        Create a new brand node with related nodes.
        
        Args:
            data: Brand data including name, website, tagline, logo, colors
            
        Returns:
            brand_id: The unique ID of the created brand
        """
        self._ensure_connected()
        brand_id = str(uuid.uuid4())[:8]
        
        query = """
        CREATE (b:Brand {
            id: $brand_id,
            name: $name,
            website: $website,
            tagline: $tagline,
            industry: $industry,
            created_at: datetime()
        })
        
        WITH b
        
        // Create logo node if provided
        FOREACH (logo IN CASE WHEN $logo_url IS NOT NULL THEN [1] ELSE [] END |
            CREATE (l:Logo {
                url: $logo_url,
                quality_score: $logo_quality_score,
                source: $logo_source
            })
            CREATE (b)-[:HAS_LOGO]->(l)
        )
        
        RETURN b.id as brand_id
        """
        
        with self.driver.session() as session:
            result = session.run(query, {
                "brand_id": brand_id,
                "name": data.get("company_name", "Unknown"),
                "website": data.get("website", ""),
                "tagline": data.get("tagline"),
                "industry": data.get("industry"),
                "logo_url": data.get("logo", {}).get("url") if data.get("logo") else None,
                "logo_quality_score": data.get("logo", {}).get("quality_score") if data.get("logo") else None,
                "logo_source": "scraped"
            })
            record = result.single()
            brand_id = record["brand_id"]
        
        # Add colors as separate nodes
        if data.get("colors"):
            self.add_colors_to_brand(brand_id, data["colors"])
        
        return brand_id
    
    def get_brand(self, brand_id: str) -> Optional[Dict[str, Any]]:
        """Get brand by ID"""
        self._ensure_connected()
        query = """
        MATCH (b:Brand {id: $brand_id})
        OPTIONAL MATCH (b)-[:HAS_LOGO]->(l:Logo)
        RETURN b {
            .*,
            logo_url: l.url,
            logo_quality_score: l.quality_score,
            logo_source: l.source
        } as brand
        """
        
        with self.driver.session() as session:
            result = session.run(query, {"brand_id": brand_id})
            record = result.single()
            return dict(record["brand"]) if record else None
    
    def get_brand_context(self, brand_id: str) -> Optional[Dict[str, Any]]:
        """
        Get full brand context including logo, colors, and products.
        Used for content generation prompts.
        """
        self._ensure_connected()
        query = """
        MATCH (b:Brand {id: $brand_id})
        OPTIONAL MATCH (b)-[:HAS_LOGO]->(l:Logo)
        WITH b, l
        OPTIONAL MATCH (b)-[:USES_COLOR]->(c:Color)
        WITH b, l, collect(DISTINCT {hex: c.hex, name: c.name}) as colors
        OPTIONAL MATCH (b)-[:SELLS]->(p:Product)
        WITH b, l, colors, collect(DISTINCT {
            name: p.name, 
            price: p.price, 
            category: p.category, 
            description: p.description
        }) as products
        
        RETURN {
            id: b.id,
            name: b.name,
            website: b.website,
            tagline: b.tagline,
            industry: b.industry,
            logo: CASE WHEN l IS NOT NULL THEN {url: l.url, quality_score: l.quality_score, source: l.source} ELSE null END,
            colors: colors,
            products: products
        } as context
        """
        
        with self.driver.session() as session:
            result = session.run(query, {"brand_id": brand_id})
            record = result.single()
            return dict(record["context"]) if record else None
    
    def update_brand_logo(self, brand_id: str, logo_url: str, source: str = "uploaded"):
        """Update or create logo for a brand"""
        self._ensure_connected()
        query = """
        MATCH (b:Brand {id: $brand_id})
        
        // Delete existing logo
        OPTIONAL MATCH (b)-[r:HAS_LOGO]->(old:Logo)
        DELETE r, old
        
        // Create new logo
        CREATE (l:Logo {
            url: $logo_url,
            source: $source,
            updated_at: datetime()
        })
        CREATE (b)-[:HAS_LOGO]->(l)
        
        RETURN l
        """
        
        with self.driver.session() as session:
            session.run(query, {
                "brand_id": brand_id,
                "logo_url": logo_url,
                "source": source
            })
    
    # === Color Operations ===
    
    def add_colors_to_brand(self, brand_id: str, colors: List[Dict[str, str]]):
        """Add color nodes to a brand"""
        self._ensure_connected()
        query = """
        MATCH (b:Brand {id: $brand_id})
        
        UNWIND $colors as color_data
        
        MERGE (c:Color {hex: color_data.hex})
        ON CREATE SET c.name = color_data.name
        
        MERGE (b)-[:USES_COLOR]->(c)
        """
        
        with self.driver.session() as session:
            session.run(query, {
                "brand_id": brand_id,
                "colors": colors
            })
    
    def get_brand_colors(self, brand_id: str) -> List[Dict[str, str]]:
        """Get all colors for a brand"""
        self._ensure_connected()
        query = """
        MATCH (b:Brand {id: $brand_id})-[:USES_COLOR]->(c:Color)
        RETURN c.hex as hex, c.name as name
        """
        
        with self.driver.session() as session:
            result = session.run(query, {"brand_id": brand_id})
            return [dict(record) for record in result]
    
    # === Product Operations ===
    
    def add_products_to_brand(self, brand_id: str, products: List[Dict[str, Any]]):
        """Add product nodes to a brand"""
        self._ensure_connected()
        query = """
        MATCH (b:Brand {id: $brand_id})
        
        UNWIND $products as product_data
        
        CREATE (p:Product {
            id: randomUUID(),
            name: product_data.name,
            price: product_data.price,
            price_range: product_data.price_range,
            category: product_data.category,
            description: product_data.description,
            created_at: datetime()
        })
        
        CREATE (b)-[:SELLS]->(p)
        """
        
        with self.driver.session() as session:
            session.run(query, {
                "brand_id": brand_id,
                "products": products
            })
    
    def get_brand_products(self, brand_id: str) -> List[Dict[str, Any]]:
        """Get all products for a brand"""
        self._ensure_connected()
        query = """
        MATCH (b:Brand {id: $brand_id})-[:SELLS]->(p:Product)
        RETURN p {.*}
        ORDER BY p.name
        """
        
        with self.driver.session() as session:
            result = session.run(query, {"brand_id": brand_id})
            return [dict(record["p"]) for record in result]
    
    def get_products_by_ids(self, product_ids: List[str]) -> List[Dict[str, Any]]:
        """Get products by their IDs"""
        self._ensure_connected()
        query = """
        MATCH (p:Product)
        WHERE p.id IN $product_ids
        RETURN p {.*}
        """
        
        with self.driver.session() as session:
            result = session.run(query, {"product_ids": product_ids})
            return [dict(record["p"]) for record in result]
    
    # === Generation Operations ===
    
    def save_generation(
        self,
        brand_id: str,
        prompt: str,
        image_url: Optional[str] = None,
        headline: Optional[str] = None,
        body_copy: Optional[str] = None,
        brand_score: float = 0.0
    ) -> str:
        """Save a content generation to the graph"""
        self._ensure_connected()
        generation_id = str(uuid.uuid4())[:8]
        
        query = """
        MATCH (b:Brand {id: $brand_id})
        
        CREATE (g:Generation {
            id: $generation_id,
            prompt: $prompt,
            image_url: $image_url,
            headline: $headline,
            body_copy: $body_copy,
            brand_score: $brand_score,
            created_at: datetime()
        })
        
        CREATE (b)-[:GENERATED]->(g)
        
        RETURN g.id as generation_id
        """
        
        with self.driver.session() as session:
            result = session.run(query, {
                "brand_id": brand_id,
                "generation_id": generation_id,
                "prompt": prompt,
                "image_url": image_url,
                "headline": headline,
                "body_copy": body_copy,
                "brand_score": brand_score
            })
            record = result.single()
            return record["generation_id"]
    
    def get_brand_generations(self, brand_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get generation history for a brand"""
        self._ensure_connected()
        query = """
        MATCH (b:Brand {id: $brand_id})-[:GENERATED]->(g:Generation)
        RETURN g {.*, brand_id: $brand_id}
        ORDER BY g.created_at DESC
        LIMIT $limit
        """
        
        with self.driver.session() as session:
            result = session.run(query, {"brand_id": brand_id, "limit": limit})
            generations = []
            for record in result:
                gen = dict(record["g"])
                # Convert Neo4j DateTime to ISO string
                if "created_at" in gen and hasattr(gen["created_at"], "isoformat"):
                    gen["created_at"] = gen["created_at"].isoformat()
                elif "created_at" in gen:
                    gen["created_at"] = str(gen["created_at"])
                generations.append(gen)
            return generations
    
    # === Feedback Operations ===
    
    def save_feedback(
        self,
        generation_id: str,
        rating: str,
        comment: Optional[str] = None
    ) -> str:
        """Save feedback for a generation"""
        self._ensure_connected()
        feedback_id = str(uuid.uuid4())[:8]
        
        query = """
        MATCH (g:Generation {id: $generation_id})
        
        CREATE (f:Feedback {
            id: $feedback_id,
            rating: $rating,
            comment: $comment,
            created_at: datetime()
        })
        
        CREATE (g)-[:RECEIVED_FEEDBACK]->(f)
        
        RETURN f.id as feedback_id
        """
        
        with self.driver.session() as session:
            result = session.run(query, {
                "generation_id": generation_id,
                "feedback_id": feedback_id,
                "rating": rating,
                "comment": comment
            })
            record = result.single()
            if not record:
                raise Exception(f"Generation {generation_id} not found")
            return record["feedback_id"]
    
    def get_feedback_stats(self, brand_id: str) -> Dict[str, Any]:
        """Get feedback statistics for a brand"""
        self._ensure_connected()
        query = """
        MATCH (b:Brand {id: $brand_id})-[:GENERATED]->(g:Generation)-[:RECEIVED_FEEDBACK]->(f:Feedback)
        RETURN 
            count(f) as total_feedback,
            sum(CASE WHEN f.rating = 'positive' THEN 1 ELSE 0 END) as positive_count,
            sum(CASE WHEN f.rating = 'negative' THEN 1 ELSE 0 END) as negative_count
        """
        
        with self.driver.session() as session:
            result = session.run(query, {"brand_id": brand_id})
            record = result.single()
            
            total = record["total_feedback"] or 0
            positive = record["positive_count"] or 0
            negative = record["negative_count"] or 0
            
            satisfaction_rate = (positive / total) if total > 0 else 0.0
            
            return {
                "total_feedback": total,
                "positive_count": positive,
                "negative_count": negative,
                "satisfaction_rate": round(satisfaction_rate, 2)
            }
    
    def get_brand_feedback(self, brand_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get all feedback for a brand's generations"""
        self._ensure_connected()
        query = """
        MATCH (b:Brand {id: $brand_id})-[:GENERATED]->(g:Generation)-[:RECEIVED_FEEDBACK]->(f:Feedback)
        RETURN f {.*, generation_id: g.id, prompt: g.prompt}
        ORDER BY f.created_at DESC
        LIMIT $limit
        """
        
        with self.driver.session() as session:
            result = session.run(query, {"brand_id": brand_id, "limit": limit})
            return [dict(record["f"]) for record in result]
    
    # === Schema Setup ===
    
    def setup_schema(self):
        """Create constraints and indexes for optimal performance"""
        self._ensure_connected()
        constraints = [
            "CREATE CONSTRAINT brand_id IF NOT EXISTS FOR (b:Brand) REQUIRE b.id IS UNIQUE",
            "CREATE CONSTRAINT color_hex IF NOT EXISTS FOR (c:Color) REQUIRE c.hex IS UNIQUE",
            "CREATE INDEX brand_website IF NOT EXISTS FOR (b:Brand) ON (b.website)",
            "CREATE INDEX brand_name IF NOT EXISTS FOR (b:Brand) ON (b.name)",
        ]
        
        with self.driver.session() as session:
            for constraint in constraints:
                try:
                    session.run(constraint)
                except Exception as e:
                    print(f"Schema setup note: {e}")


# Singleton instance
neo4j_client = Neo4jClient()


def get_neo4j_client() -> Neo4jClient:
    """Get the singleton Neo4j client instance"""
    return neo4j_client

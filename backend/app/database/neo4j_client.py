"""
Neo4j Database Client
Handles all graph database operations for brands, products, and generations.
"""
from neo4j import GraphDatabase
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid
import json
import hashlib

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
                    connection_uri = settings.neo4j_uri
                    if settings.neo4j_trust_all_certificates:
                        connection_uri = connection_uri.replace("neo4j+s://", "neo4j+ssc://")
                        connection_uri = connection_uri.replace("bolt+s://", "bolt+ssc://")

                    self._driver = GraphDatabase.driver(
                        connection_uri,
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

    # === Research Manifest Helpers ===

    def _normalize_manifest_data(self, manifest_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize manifest payload for stable hashing and parity checks."""
        seeds = sorted([int(s) for s in manifest_data.get("seeds", [])])
        locked_config_input = manifest_data.get("locked_config") or {}
        locked_config = {str(k): locked_config_input[k] for k in sorted(locked_config_input.keys())}

        return {
            "brand_id": manifest_data.get("brand_id"),
            "prompt": manifest_data.get("prompt", ""),
            "seeds": seeds,
            "locked_config": locked_config,
        }

    def _manifest_parity_hash(self, manifest: Dict[str, Any]) -> str:
        """Calculate deterministic parity hash from normalized manifest payload."""
        normalized = json.dumps(manifest, sort_keys=True)
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def _manifest_differences(self, stored_manifest: Dict[str, Any], requested_manifest: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate field-level differences between stored and requested manifest payloads."""
        differences: List[Dict[str, Any]] = []

        for field in ["brand_id", "prompt", "seeds"]:
            stored_value = stored_manifest.get(field)
            requested_value = requested_manifest.get(field)
            if stored_value != requested_value:
                differences.append({
                    "field": field,
                    "stored": stored_value,
                    "requested": requested_value,
                })

        stored_config = stored_manifest.get("locked_config") or {}
        requested_config = requested_manifest.get("locked_config") or {}
        config_keys = sorted(set(stored_config.keys()).union(set(requested_config.keys())))
        for key in config_keys:
            stored_value = stored_config.get(key)
            requested_value = requested_config.get(key)
            if stored_value != requested_value:
                differences.append({
                    "field": f"locked_config.{key}",
                    "stored": stored_value,
                    "requested": requested_value,
                })

        return differences
    
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

    # === Research Experiment Operations ===

    def setup_research_schema(self):
        """Create constraints and indexes for research experiment tracking."""
        self._ensure_connected()
        constraints = [
            "CREATE CONSTRAINT experiment_manifest_experiment_id IF NOT EXISTS FOR (m:ExperimentManifest) REQUIRE m.experiment_id IS UNIQUE",
            "CREATE CONSTRAINT experiment_run_id IF NOT EXISTS FOR (r:ExperimentRun) REQUIRE r.id IS UNIQUE",
            "CREATE CONSTRAINT experiment_candidate_id IF NOT EXISTS FOR (c:ExperimentCandidate) REQUIRE c.id IS UNIQUE",
            "CREATE CONSTRAINT metric_snapshot_id IF NOT EXISTS FOR (m:MetricSnapshot) REQUIRE m.id IS UNIQUE",
            "CREATE INDEX experiment_manifest_brand_id IF NOT EXISTS FOR (m:ExperimentManifest) ON (m.brand_id)",
            "CREATE INDEX experiment_run_experiment_id IF NOT EXISTS FOR (r:ExperimentRun) ON (r.experiment_id)",
            "CREATE INDEX experiment_run_brand_id IF NOT EXISTS FOR (r:ExperimentRun) ON (r.brand_id)",
        ]

        with self.driver.session() as session:
            for constraint in constraints:
                try:
                    session.run(constraint)
                except Exception as e:
                    print(f"Research schema setup note: {e}")

    def create_experiment_run(self, run_data: Dict[str, Any]) -> Dict[str, str]:
        """Create a research experiment run node and optional relation to Brand."""
        self._ensure_connected()
        run_id = run_data.get("run_id") or f"run_{uuid.uuid4().hex[:12]}"
        experiment_id = run_data.get("experiment_id") or f"exp_{datetime.utcnow().strftime('%Y%m%d')}_{uuid.uuid4().hex[:6]}"

        query = """
        CREATE (r:ExperimentRun {
            id: $run_id,
            experiment_id: $experiment_id,
            brand_id: $brand_id,
            method_name: $method_name,
            prompt: $prompt,
            status: $status,
            seeds_json: $seeds_json,
            config_json: $config_json,
            notes: $notes,
            started_at: datetime($started_at),
            created_at: datetime()
        })
        WITH r
        OPTIONAL MATCH (b:Brand {id: $brand_id})
        FOREACH (_ IN CASE WHEN b IS NOT NULL THEN [1] ELSE [] END |
            CREATE (b)-[:HAS_EXPERIMENT_RUN]->(r)
        )
        WITH r
        OPTIONAL MATCH (m:ExperimentManifest {experiment_id: $experiment_id})
        FOREACH (_ IN CASE WHEN m IS NOT NULL THEN [1] ELSE [] END |
            CREATE (m)-[:HAS_RUN]->(r)
        )
        RETURN r.id as run_id, r.experiment_id as experiment_id
        """

        with self.driver.session() as session:
            result = session.run(query, {
                "run_id": run_id,
                "experiment_id": experiment_id,
                "brand_id": run_data.get("brand_id"),
                "method_name": run_data.get("method_name", "graph_guided"),
                "prompt": run_data.get("prompt", ""),
                "status": run_data.get("status", "running"),
                "seeds_json": json.dumps(run_data.get("seeds", [])),
                "config_json": json.dumps(run_data.get("config", {})),
                "notes": run_data.get("notes"),
                "started_at": run_data.get("started_at", datetime.utcnow().isoformat()),
            })
            record = result.single()
            return {
                "run_id": record["run_id"],
                "experiment_id": record["experiment_id"],
            }

    def lock_experiment_manifest(self, manifest_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create or validate a locked manifest for experiment parity.

        Returns payload with:
        - matches: bool
        - experiment_id: str
        - parity_hash: str
        - manifest: dict
        """
        self._ensure_connected()

        experiment_id = manifest_data["experiment_id"]
        normalized_manifest = self._normalize_manifest_data(manifest_data)
        brand_id = normalized_manifest.get("brand_id")
        prompt = normalized_manifest.get("prompt", "")
        seeds = normalized_manifest.get("seeds", [])
        locked_config = normalized_manifest.get("locked_config", {})
        parity_hash = self._manifest_parity_hash(normalized_manifest)
        manifest_id = manifest_data.get("manifest_id") or f"manifest_{uuid.uuid4().hex[:10]}"

        query = """
        MERGE (m:ExperimentManifest {experiment_id: $experiment_id})
        ON CREATE SET
            m.id = $manifest_id,
            m.brand_id = $brand_id,
            m.prompt = $prompt,
            m.seeds_json = $seeds_json,
            m.locked_config_json = $locked_config_json,
            m.parity_hash = $parity_hash,
            m.status = 'locked',
            m.created_at = datetime(),
            m.updated_at = datetime()
        ON MATCH SET
            m.updated_at = datetime()
        RETURN m
        """

        with self.driver.session() as session:
            result = session.run(query, {
                "experiment_id": experiment_id,
                "manifest_id": manifest_id,
                "brand_id": brand_id,
                "prompt": prompt,
                "seeds_json": json.dumps(seeds),
                "locked_config_json": json.dumps(locked_config),
                "parity_hash": parity_hash,
            })
            record = result.single()
            manifest_node = dict(record["m"]) if record else {}

        existing_hash = manifest_node.get("parity_hash")

        manifest = {
            "id": manifest_node.get("id"),
            "experiment_id": manifest_node.get("experiment_id"),
            "brand_id": manifest_node.get("brand_id"),
            "prompt": manifest_node.get("prompt"),
            "seeds": json.loads(manifest_node.get("seeds_json") or "[]"),
            "locked_config": json.loads(manifest_node.get("locked_config_json") or "{}"),
            "parity_hash": existing_hash,
            "status": manifest_node.get("status", "locked"),
            "created_at": str(manifest_node.get("created_at")) if manifest_node.get("created_at") is not None else None,
            "updated_at": str(manifest_node.get("updated_at")) if manifest_node.get("updated_at") is not None else None,
        }

        differences = self._manifest_differences(manifest, normalized_manifest)
        matches = existing_hash == parity_hash and len(differences) == 0

        return {
            "matches": matches,
            "experiment_id": experiment_id,
            "requested_parity_hash": parity_hash,
            "stored_parity_hash": existing_hash,
            "manifest": manifest,
            "requested_manifest": normalized_manifest,
            "differences": differences,
        }

    def validate_experiment_manifest(self, manifest_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate requested manifest against stored lock for diagnostics."""
        experiment_id = manifest_data["experiment_id"]
        requested_manifest = self._normalize_manifest_data(manifest_data)
        requested_hash = self._manifest_parity_hash(requested_manifest)

        stored_manifest = self.get_experiment_manifest(experiment_id)
        if not stored_manifest:
            return {
                "exists": False,
                "matches": None,
                "experiment_id": experiment_id,
                "requested_manifest": requested_manifest,
                "requested_parity_hash": requested_hash,
                "stored_parity_hash": None,
                "differences": [],
            }

        stored_hash = stored_manifest.get("parity_hash")
        differences = self._manifest_differences(stored_manifest, requested_manifest)
        matches = stored_hash == requested_hash and len(differences) == 0

        return {
            "exists": True,
            "matches": matches,
            "experiment_id": experiment_id,
            "stored_manifest": stored_manifest,
            "requested_manifest": requested_manifest,
            "requested_parity_hash": requested_hash,
            "stored_parity_hash": stored_hash,
            "differences": differences,
        }

    def get_experiment_manifest(self, experiment_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve manifest for an experiment."""
        self._ensure_connected()
        query = """
        MATCH (m:ExperimentManifest {experiment_id: $experiment_id})
        RETURN m
        """

        with self.driver.session() as session:
            result = session.run(query, {"experiment_id": experiment_id})
            record = result.single()
            if not record:
                return None

            node = dict(record["m"])
            return {
                "id": node.get("id"),
                "experiment_id": node.get("experiment_id"),
                "brand_id": node.get("brand_id"),
                "prompt": node.get("prompt"),
                "seeds": json.loads(node.get("seeds_json") or "[]"),
                "locked_config": json.loads(node.get("locked_config_json") or "{}"),
                "parity_hash": node.get("parity_hash"),
                "status": node.get("status", "locked"),
                "created_at": str(node.get("created_at")) if node.get("created_at") is not None else None,
                "updated_at": str(node.get("updated_at")) if node.get("updated_at") is not None else None,
            }

    def update_experiment_run(self, run_id: str, updates: Dict[str, Any]) -> bool:
        """Update status and metadata for an experiment run."""
        self._ensure_connected()
        query = """
        MATCH (r:ExperimentRun {id: $run_id})
        SET r.status = COALESCE($status, r.status),
            r.error_message = COALESCE($error_message, r.error_message),
            r.duration_ms = COALESCE($duration_ms, r.duration_ms),
            r.result_summary_json = COALESCE($result_summary_json, r.result_summary_json),
            r.completed_at = CASE
                WHEN $completed_at IS NULL THEN r.completed_at
                ELSE datetime($completed_at)
            END,
            r.updated_at = datetime()
        RETURN count(r) as updated_count
        """

        with self.driver.session() as session:
            result = session.run(query, {
                "run_id": run_id,
                "status": updates.get("status"),
                "error_message": updates.get("error_message"),
                "duration_ms": updates.get("duration_ms"),
                "result_summary_json": json.dumps(updates.get("result_summary")) if updates.get("result_summary") is not None else None,
                "completed_at": updates.get("completed_at"),
            })
            record = result.single()
            return bool(record and record["updated_count"] > 0)

    def save_experiment_candidate(self, run_id: str, candidate_data: Dict[str, Any]) -> str:
        """Save a candidate generation produced during an experiment run."""
        self._ensure_connected()
        candidate_id = candidate_data.get("candidate_id") or f"cand_{uuid.uuid4().hex[:10]}"

        query = """
        MATCH (r:ExperimentRun {id: $run_id})
        CREATE (c:ExperimentCandidate {
            id: $candidate_id,
            run_id: $run_id,
            seed: $seed,
            status: $status,
            image_url: $image_url,
            model_used: $model_used,
            provider: $provider,
            prompt_used: $prompt_used,
            latency_ms: $latency_ms,
            error_message: $error_message,
            colors_json: $colors_json,
            metadata_json: $metadata_json,
            created_at: datetime()
        })
        CREATE (r)-[:HAS_CANDIDATE]->(c)
        RETURN c.id as candidate_id
        """

        with self.driver.session() as session:
            result = session.run(query, {
                "run_id": run_id,
                "candidate_id": candidate_id,
                "seed": candidate_data.get("seed"),
                "status": candidate_data.get("status", "completed"),
                "image_url": candidate_data.get("image_url"),
                "model_used": candidate_data.get("model_used"),
                "provider": candidate_data.get("provider"),
                "prompt_used": candidate_data.get("prompt_used"),
                "latency_ms": candidate_data.get("latency_ms"),
                "error_message": candidate_data.get("error_message"),
                "colors_json": json.dumps(candidate_data.get("colors", [])),
                "metadata_json": json.dumps(candidate_data.get("metadata", {})),
            })
            record = result.single()
            return record["candidate_id"]

    def save_metric_snapshot(
        self,
        run_id: str,
        metrics: Dict[str, Any],
        level: str = "run",
        candidate_id: Optional[str] = None,
    ) -> str:
        """Store metric snapshots at run or candidate level."""
        self._ensure_connected()
        snapshot_id = f"metric_{uuid.uuid4().hex[:12]}"

        query = """
        MATCH (r:ExperimentRun {id: $run_id})
        OPTIONAL MATCH (c:ExperimentCandidate {id: $candidate_id})
        CREATE (m:MetricSnapshot {
            id: $snapshot_id,
            run_id: $run_id,
            candidate_id: $candidate_id,
            level: $level,
            metrics_json: $metrics_json,
            created_at: datetime()
        })
        CREATE (r)-[:HAS_METRIC]->(m)
        FOREACH (_ IN CASE WHEN c IS NOT NULL THEN [1] ELSE [] END |
            CREATE (c)-[:HAS_METRIC]->(m)
        )
        RETURN m.id as snapshot_id
        """

        with self.driver.session() as session:
            result = session.run(query, {
                "run_id": run_id,
                "candidate_id": candidate_id,
                "snapshot_id": snapshot_id,
                "level": level,
                "metrics_json": json.dumps(metrics),
            })
            record = result.single()
            return record["snapshot_id"]

    def get_experiment_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Get experiment run with candidates and run-level metrics."""
        self._ensure_connected()
        query = """
        MATCH (r:ExperimentRun {id: $run_id})
        OPTIONAL MATCH (r)-[:HAS_CANDIDATE]->(c:ExperimentCandidate)
        OPTIONAL MATCH (r)-[:HAS_METRIC]->(m:MetricSnapshot {level: 'run'})
        RETURN r, collect(DISTINCT c) as candidates, collect(DISTINCT m) as run_metrics
        """

        with self.driver.session() as session:
            result = session.run(query, {"run_id": run_id})
            record = result.single()
            if not record:
                return None

            run_data = dict(record["r"])
            run_data["seeds"] = json.loads(run_data.get("seeds_json") or "[]")
            run_data["config"] = json.loads(run_data.get("config_json") or "{}")
            run_data["result_summary"] = json.loads(run_data.get("result_summary_json") or "{}") if run_data.get("result_summary_json") else None

            candidates = []
            for candidate in record["candidates"]:
                if candidate is None:
                    continue
                candidate_dict = dict(candidate)
                candidate_dict["colors"] = json.loads(candidate_dict.get("colors_json") or "[]")
                candidate_dict["metadata"] = json.loads(candidate_dict.get("metadata_json") or "{}")
                candidates.append(candidate_dict)

            run_metrics = []
            for metric in record["run_metrics"]:
                if metric is None:
                    continue
                metric_dict = dict(metric)
                metric_dict["metrics"] = json.loads(metric_dict.get("metrics_json") or "{}")
                run_metrics.append(metric_dict)

            run_data["candidates"] = candidates
            run_data["run_metrics"] = run_metrics
            return run_data

    def get_metrics_for_run(self, run_id: str) -> List[Dict[str, Any]]:
        """Get all metric snapshots for a run."""
        self._ensure_connected()
        query = """
        MATCH (r:ExperimentRun {id: $run_id})-[:HAS_METRIC]->(m:MetricSnapshot)
        RETURN m
        ORDER BY m.created_at ASC
        """

        with self.driver.session() as session:
            result = session.run(query, {"run_id": run_id})
            snapshots = []
            for record in result:
                metric_dict = dict(record["m"])
                metric_dict["metrics"] = json.loads(metric_dict.get("metrics_json") or "{}")
                snapshots.append(metric_dict)
            return snapshots

    def compare_experiment_runs(self, experiment_id: str) -> List[Dict[str, Any]]:
        """Get run-level comparison payload for all runs in an experiment."""
        self._ensure_connected()
        query = """
        MATCH (r:ExperimentRun {experiment_id: $experiment_id})
        OPTIONAL MATCH (r)-[:HAS_METRIC]->(m:MetricSnapshot {level: 'run'})
        RETURN r, collect(m) as metrics
        ORDER BY r.created_at ASC
        """

        with self.driver.session() as session:
            result = session.run(query, {"experiment_id": experiment_id})
            runs = []
            for record in result:
                run_dict = dict(record["r"])
                run_dict["seeds"] = json.loads(run_dict.get("seeds_json") or "[]")
                run_dict["config"] = json.loads(run_dict.get("config_json") or "{}")
                run_dict["result_summary"] = json.loads(run_dict.get("result_summary_json") or "{}") if run_dict.get("result_summary_json") else None

                parsed_metrics = []
                for metric in record["metrics"]:
                    if metric is None:
                        continue
                    metric_dict = dict(metric)
                    metric_dict["metrics"] = json.loads(metric_dict.get("metrics_json") or "{}")
                    parsed_metrics.append(metric_dict)
                run_dict["metrics"] = parsed_metrics
                runs.append(run_dict)
            return runs

    def get_candidate_metrics_for_experiment(self, experiment_id: str) -> List[Dict[str, Any]]:
        """Get candidate-level metric snapshots across all runs for one experiment."""
        self._ensure_connected()
        query = """
        MATCH (r:ExperimentRun {experiment_id: $experiment_id})-[:HAS_METRIC]->(m:MetricSnapshot {level: 'candidate'})
        RETURN r.id as run_id, r.method_name as method_name, m.metrics_json as metrics_json
        ORDER BY r.created_at ASC, m.created_at ASC
        """

        with self.driver.session() as session:
            result = session.run(query, {"experiment_id": experiment_id})
            rows = []
            for record in result:
                rows.append({
                    "run_id": record["run_id"],
                    "method_name": record["method_name"],
                    "metrics": json.loads(record["metrics_json"] or "{}"),
                })
            return rows

    def list_research_runs(self, brand_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """List recent research runs for a brand."""
        self._ensure_connected()
        query = """
        MATCH (r:ExperimentRun {brand_id: $brand_id})
        RETURN r
        ORDER BY r.created_at DESC
        LIMIT $limit
        """

        with self.driver.session() as session:
            result = session.run(query, {"brand_id": brand_id, "limit": limit})
            runs = []
            for record in result:
                run_dict = dict(record["r"])
                run_dict["seeds"] = json.loads(run_dict.get("seeds_json") or "[]")
                run_dict["config"] = json.loads(run_dict.get("config_json") or "{}")
                run_dict["result_summary"] = json.loads(run_dict.get("result_summary_json") or "{}") if run_dict.get("result_summary_json") else None
                runs.append(run_dict)
            return runs
    
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

"""
Brand DNA Service Layer
========================
This service orchestrates the full GraphRAG pipeline:
1. Retrieves Brand DNA from Neo4j
2. Uses LLM to plan generation
3. Conditions the diffusion model
4. Stores generation and feedback relationships

This is the "brain" that connects everything.
"""

import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, asdict

from app.database.neo4j_client import get_neo4j_client
from app.generation.llm_reasoner import LLMReasoner, GenerationPlan, FeedbackAnalysis, get_reasoner
from app.generation.image_generators import (
    ImageGenerator, 
    GenerationRequest, 
    GenerationResult,
    BrandCondition,
    get_generator
)
from app.generation.text_overlay import composite_text_on_image, add_logo_to_image
import base64
import httpx


@dataclass
class BrandDNA:
    """Complete Brand DNA from Neo4j"""
    brand_id: str
    brand_name: str
    tagline: Optional[str] = None
    industry: Optional[str] = None
    logo_url: Optional[str] = None
    
    colors: List[Dict[str, Any]] = None
    styles: List[Dict[str, Any]] = None
    composition: Optional[Dict[str, Any]] = None
    products: List[Dict[str, Any]] = None
    characters: List[Dict[str, Any]] = None
    learned_preferences: List[Dict[str, Any]] = None
    
    def __post_init__(self):
        self.colors = self.colors or []
        self.styles = self.styles or []
        self.products = self.products or []
        self.characters = self.characters or []
        self.learned_preferences = self.learned_preferences or []
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "brand_id": self.brand_id,
            "brand_name": self.brand_name,
            "tagline": self.tagline,
            "industry": self.industry,
            "logo_url": self.logo_url,
            "colors": self.colors,
            "styles": self.styles,
            "composition": self.composition,
            "products": self.products,
            "characters": self.characters,
            "learned_preferences": self.learned_preferences
        }
    
    def to_brand_condition(self) -> BrandCondition:
        """Convert to BrandCondition for image generator"""
        return BrandCondition(
            primary_colors=[c["hex"] for c in self.colors if c.get("hex")],
            color_weights={c["hex"]: c.get("usage_weight", 0.5) for c in self.colors if c.get("hex")},
            style_keywords=[kw for s in self.styles for kw in (s.get("keywords") or [])],
            negative_keywords=[kw for s in self.styles for kw in (s.get("negative_keywords") or [])],
            layout=self.composition.get("layout", "centered") if self.composition else "centered",
            text_density=self.composition.get("text_density", "moderate") if self.composition else "moderate",
            text_position=self.composition.get("text_position", "bottom") if self.composition else "bottom",
            overlay_opacity=self.composition.get("overlay_opacity", 0.0) if self.composition else 0.0,
            aspect_ratio=self.composition.get("aspect_ratio_preference", "1:1") if self.composition else "1:1",
        )


class BrandDNAService:
    """Service for managing Brand DNA and generation pipeline"""
    
    def __init__(
        self,
        neo4j_client = None,
        llm_reasoner: LLMReasoner = None,
        image_generator: ImageGenerator = None
    ):
        self.neo4j = neo4j_client or get_neo4j_client()
        self.reasoner = llm_reasoner or get_reasoner()
        self.generator = image_generator or get_generator()
    
    # ===================
    # BRAND DNA RETRIEVAL
    # ===================
    
    async def get_brand_dna(self, brand_id: str) -> Optional[BrandDNA]:
        """
        Retrieve complete Brand DNA from Neo4j.
        This is the main query that powers generation.
        """
        query = """
        MATCH (b:Brand {id: $brand_id})
        
        OPTIONAL MATCH (b)-[:HAS_LOGO]->(logo:Logo)
        OPTIONAL MATCH (b)-[cr:HAS_COLOR]->(c:ColorNode)
        OPTIONAL MATCH (b)-[sr:HAS_STYLE]->(s:StyleNode)
        OPTIONAL MATCH (b)-[:HAS_COMPOSITION]->(comp:CompositionNode)
        OPTIONAL MATCH (b)-[:SELLS]->(p:ProductNode)
        OPTIONAL MATCH (b)-[:HAS_CHARACTER]->(ch:CharacterNode)
        OPTIONAL MATCH (b)-[:LEARNED]->(lp:LearnedPreference)
        
        RETURN b,
               logo.url as logo_url,
               collect(DISTINCT {
                   hex: c.hex, 
                   name: c.name, 
                   role: cr.role, 
                   weight: COALESCE(cr.weight, c.usage_weight, 0.5),
                   contexts: c.contexts
               }) as colors,
               collect(DISTINCT {
                   id: s.id,
                   type: s.type, 
                   keywords: s.keywords, 
                   weight: COALESCE(sr.weight, s.weight, 0.5),
                   negative_keywords: s.negative_keywords
               }) as styles,
               comp as composition,
               collect(DISTINCT {
                   id: p.id,
                   name: p.name,
                   category: p.category,
                   image_url: p.image_url,
                   description: p.description
               }) as products,
               collect(DISTINCT {
                   id: ch.id,
                   name: ch.name,
                   reference_image_url: ch.reference_image_url,
                   body_type: ch.body_type
               }) as characters,
               collect(DISTINCT {
                   id: lp.id,
                   trigger: lp.trigger,
                   applies: lp.applies,
                   aspect: lp.aspect,
                   confidence: lp.confidence
               }) as learned_preferences
        """
        
        result = self.neo4j.execute_query(query, {"brand_id": brand_id})
        
        if not result:
            return None
        
        record = result[0]
        brand_node = record["b"]
        logo_url = record.get("logo_url")
        
        # Filter out empty entries
        colors = [c for c in record["colors"] if c.get("hex")]
        styles = [s for s in record["styles"] if s.get("type") or s.get("keywords")]
        products = [p for p in record["products"] if p.get("name")]
        characters = [ch for ch in record["characters"] if ch.get("name")]
        learned_prefs = [lp for lp in record["learned_preferences"] if lp.get("trigger")]
        
        composition = None
        if record["composition"]:
            comp_node = record["composition"]
            composition = {
                "layout": comp_node.get("layout", "centered"),
                "text_density": comp_node.get("text_density", "moderate"),
                "text_position": comp_node.get("text_position", "bottom"),
                "overlay_opacity": comp_node.get("overlay_opacity", 0.0),
                "padding_preference": comp_node.get("padding_preference", "comfortable"),
                "aspect_ratio_preference": comp_node.get("aspect_ratio_preference", "1:1")
            }
        
        return BrandDNA(
            brand_id=brand_id,
            brand_name=brand_node.get("name", "Unknown Brand"),
            tagline=brand_node.get("tagline"),
            industry=brand_node.get("industry"),
            logo_url=logo_url,
            colors=colors,
            styles=styles,
            composition=composition,
            products=products,
            characters=characters,
            learned_preferences=learned_prefs
        )
    
    async def get_applicable_preferences(
        self, 
        brand_id: str, 
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Get learned preferences that apply to current generation context"""
        query = """
        MATCH (b:Brand {id: $brand_id})-[:LEARNED]->(lp:LearnedPreference)
        WHERE lp.confidence > 0.5
        RETURN lp
        ORDER BY lp.confidence DESC
        """
        
        results = self.neo4j.execute_query(query, {"brand_id": brand_id})
        
        applicable = []
        for record in results:
            pref = dict(record["lp"])
            trigger = pref.get("trigger", "")
            
            # Check if trigger matches context
            # Simple matching: "text_position = centered" matches if context has text_position=centered
            for key, value in context.items():
                if f"{key} = {value}".lower() in trigger.lower():
                    applicable.append(pref)
                    break
        
        return applicable
    
    # ===================
    # GENERATION PIPELINE
    # ===================
    
    async def generate_content(
        self,
        brand_id: str,
        user_prompt: str,
        headline: Optional[str] = None,
        body_copy: Optional[str] = None,
        product_id: Optional[str] = None,
        character_id: Optional[str] = None,
        aspect_ratio: str = "1:1",
        text_layout: str = "bottom_centered",
        include_logo: bool = False,
        use_reasoning: bool = True
    ) -> Dict[str, Any]:
        """
        Full GraphRAG generation pipeline:
        1. Retrieve Brand DNA
        2. LLM plans generation
        3. Apply learned preferences
        4. Generate image with conditioning
        5. Store generation in graph
        """
        
        generation_id = str(uuid.uuid4())
        pipeline_steps = []
        
        # Step 1: Retrieve Brand DNA
        pipeline_steps.append({
            "step": "retrieve_brand_dna",
            "status": "started",
            "timestamp": datetime.utcnow().isoformat()
        })
        
        brand_dna = await self.get_brand_dna(brand_id)
        if not brand_dna:
            return {
                "success": False,
                "error": "Brand not found",
                "generation_id": generation_id
            }
        
        pipeline_steps[-1]["status"] = "completed"
        pipeline_steps[-1]["nodes_retrieved"] = {
            "colors": len(brand_dna.colors),
            "styles": len(brand_dna.styles),
            "products": len(brand_dna.products),
            "characters": len(brand_dna.characters),
            "learned_preferences": len(brand_dna.learned_preferences)
        }
        
        # Step 2: LLM Planning (if enabled)
        plan = None
        if use_reasoning:
            pipeline_steps.append({
                "step": "llm_planning",
                "status": "started",
                "timestamp": datetime.utcnow().isoformat()
            })
            
            try:
                plan = await self.reasoner.plan_generation(
                    user_prompt=user_prompt,
                    brand_context=brand_dna.to_dict(),
                    learned_preferences=brand_dna.learned_preferences
                )
                pipeline_steps[-1]["status"] = "completed"
                pipeline_steps[-1]["plan"] = plan.to_dict()
            except Exception as e:
                pipeline_steps[-1]["status"] = "failed"
                pipeline_steps[-1]["error"] = str(e)
        
        # Step 3: Build conditioning
        pipeline_steps.append({
            "step": "build_conditioning",
            "status": "started",
            "timestamp": datetime.utcnow().isoformat()
        })
        
        brand_condition = brand_dna.to_brand_condition()
        brand_condition.aspect_ratio = aspect_ratio
        
        # Apply plan adjustments
        if plan:
            brand_condition.overlay_opacity = plan.suggested_overlay
            brand_condition.layout = plan.suggested_layout
            brand_condition.text_position = plan.suggested_text_position
            brand_condition.style_strength = plan.style_strength
        
        # Apply learned preferences
        context = {
            "text_position": brand_condition.text_position,
            "layout": brand_condition.layout
        }
        applicable_prefs = await self.get_applicable_preferences(brand_id, context)
        
        for pref in applicable_prefs:
            applies = pref.get("applies", "")
            # Parse "property = value" format
            if "=" in applies:
                prop, value = applies.split("=", 1)
                prop = prop.strip()
                value = value.strip()
                
                if hasattr(brand_condition, prop):
                    try:
                        # Try to convert to appropriate type
                        current = getattr(brand_condition, prop)
                        if isinstance(current, float):
                            setattr(brand_condition, prop, float(value))
                        elif isinstance(current, int):
                            setattr(brand_condition, prop, int(value))
                        else:
                            setattr(brand_condition, prop, value)
                        
                        brand_condition.learned_modifiers[prop] = value
                    except:
                        pass
        
        # Get product reference if specified
        product_image_url = None
        if product_id:
            product = next((p for p in brand_dna.products if p.get("id") == product_id), None)
            if product:
                product_image_url = product.get("image_url")
                brand_condition.product_image_url = product_image_url
        
        # Get character reference if specified
        character_image_url = None
        if character_id:
            character = next((c for c in brand_dna.characters if c.get("id") == character_id), None)
            if character:
                character_image_url = character.get("reference_image_url")
                brand_condition.face_image_url = character_image_url
        
        pipeline_steps[-1]["status"] = "completed"
        pipeline_steps[-1]["applied_preferences"] = len(applicable_prefs)
        
        # Step 4: Compile final prompt
        pipeline_steps.append({
            "step": "compile_prompt",
            "status": "started",
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Get product context if product is selected
        product_context = ""
        selected_product = None
        if product_id:
            selected_product = next((p for p in brand_dna.products if p.get("id") == product_id), None)
            if selected_product:
                product_context = f"featuring {selected_product.get('name', 'product')}"
                if selected_product.get('description'):
                    product_context += f" ({selected_product['description'][:100]})"
        
        # Get character context if character is selected
        character_context = ""
        selected_character = None
        if character_id:
            selected_character = next((c for c in brand_dna.characters if c.get("id") == character_id), None)
            if selected_character:
                character_context = f"with {selected_character.get('name', 'person')}"
        
        if plan:
            positive_prompt, negative_prompt = await self.reasoner.compile_final_prompt(
                plan, brand_dna.to_dict()
            )
            # Add product/character context to the compiled prompt
            if product_context:
                positive_prompt = f"{positive_prompt}, {product_context}"
            if character_context:
                positive_prompt = f"{positive_prompt}, {character_context}"
        else:
            # Basic compilation without LLM - include brand name and context
            base_prompt = f"For brand {brand_dna.brand_name}: {user_prompt}"
            if product_context:
                base_prompt = f"{base_prompt}, {product_context}"
            if character_context:
                base_prompt = f"{base_prompt}, {character_context}"
            
            style_terms = ', '.join(brand_condition.style_keywords[:5]) if brand_condition.style_keywords else ""
            positive_prompt = f"{base_prompt}. {style_terms}. professional quality, 8k, detailed, photorealistic"
            
            # Negative prompt - avoid trigger words that cause content policy issues
            # Text will be added via PIL compositing, so always suppress text in image generation
            negative_prompt = "blurry, low quality, distorted, text, words, letters, writing, caption, gibberish text, random letters, ugly, deformed"
        
        pipeline_steps[-1]["status"] = "completed"
        pipeline_steps[-1]["prompt_length"] = len(positive_prompt)
        pipeline_steps[-1]["product_context"] = product_context
        pipeline_steps[-1]["character_context"] = character_context
        
        # Step 5: Generate image
        pipeline_steps.append({
            "step": "image_generation",
            "status": "started",
            "timestamp": datetime.utcnow().isoformat()
        })
        
        request = GenerationRequest(
            prompt=positive_prompt,
            brand_id=brand_id,
            brand_condition=brand_condition,
            headline=headline,
            body_copy=body_copy,
            request_id=generation_id
        )
        
        # Choose generation method based on inputs
        if character_image_url and product_image_url:
            # Use combined method when both are provided
            if hasattr(self.generator, 'generate_with_product_and_character'):
                result = await self.generator.generate_with_product_and_character(
                    request, 
                    product_image_url, 
                    character_image_url,
                    brand_condition.product_strength,
                    brand_condition.face_strength
                )
            else:
                # Fallback: prioritize character for face consistency
                result = await self.generator.generate_with_character(
                    request, character_image_url, brand_condition.face_strength
                )
        elif character_image_url:
            result = await self.generator.generate_with_character(
                request, character_image_url, brand_condition.face_strength
            )
        elif product_image_url:
            result = await self.generator.generate_with_product(
                request, product_image_url, brand_condition.product_strength
            )
        else:
            result = await self.generator.generate(request)
        
        result.generation_id = generation_id
        result.headline = headline
        result.body_copy = body_copy
        
        pipeline_steps[-1]["status"] = "completed" if result.success else "failed"
        pipeline_steps[-1]["model_used"] = result.model_used
        pipeline_steps[-1]["generation_time_ms"] = result.generation_time_ms
        pipeline_steps[-1]["cost_usd"] = result.cost_usd
        
        if not result.success:
            pipeline_steps[-1]["error"] = result.error_message
        
        # Step 5.5: Apply text overlay using PIL (if headline or body_copy requested)
        current_image_bytes = None
        print(f"[DEBUG] Post-processing check: headline={headline}, body_copy={body_copy}, include_logo={include_logo}")
        print(f"[DEBUG] Brand DNA logo_url: {brand_dna.logo_url}")
        
        if result.success and (headline or body_copy or include_logo):
            # Download the generated image first (or decode if base64)
            pipeline_steps.append({
                "step": "post_processing",
                "status": "started",
                "timestamp": datetime.utcnow().isoformat()
            })
            
            try:
                print(f"[DEBUG] Image URL starts with: {result.image_url[:50]}...")
                # Check if image is already base64 data URL
                if result.image_url.startswith("data:image"):
                    # Extract base64 data from data URL
                    # Format: data:image/png;base64,<base64data>
                    parts = result.image_url.split(",", 1)
                    if len(parts) == 2:
                        current_image_bytes = base64.b64decode(parts[1])
                        print(f"[DEBUG] Decoded base64 image, size: {len(current_image_bytes)} bytes")
                    else:
                        raise ValueError("Invalid base64 data URL format")
                else:
                    # Fetch from URL
                    print(f"[DEBUG] Fetching image from URL: {result.image_url}")
                    async with httpx.AsyncClient(timeout=30.0) as client:
                        img_response = await client.get(result.image_url)
                        img_response.raise_for_status()
                        current_image_bytes = img_response.content
                        print(f"[DEBUG] Fetched image, size: {len(current_image_bytes)} bytes")
                
                # Apply text overlay if headline or body_copy
                if headline or body_copy:
                    print(f"[DEBUG] Applying text overlay: headline='{headline}', body_copy='{body_copy}'")
                    # Build brand context for text styling
                    brand_context = {
                        "font_id": brand_condition.font_id if hasattr(brand_condition, 'font_id') else "montserrat",
                        "colors": brand_dna.colors
                    }
                    
                    # Composite text onto image using PIL
                    current_image_bytes = composite_text_on_image(
                        image_bytes=current_image_bytes,
                        headline=headline,
                        body_copy=body_copy,
                        brand_context=brand_context,
                        layout=text_layout
                    )
                    pipeline_steps[-1]["text_added"] = True
                
                # Apply logo if requested and logo exists
                print(f"[DEBUG] Logo check: include_logo={include_logo}, logo_url={brand_dna.logo_url}")
                if include_logo and brand_dna.logo_url:
                    try:
                        print(f"[DEBUG] Fetching logo from: {brand_dna.logo_url}")
                        async with httpx.AsyncClient(timeout=15.0) as client:
                            logo_response = await client.get(brand_dna.logo_url)
                            logo_response.raise_for_status()
                            logo_bytes = logo_response.content
                        
                        print(f"[DEBUG] Logo fetched, size: {len(logo_bytes)} bytes")
                        current_image_bytes = add_logo_to_image(
                            image_bytes=current_image_bytes,
                            logo_bytes=logo_bytes,
                            position="bottom_right",
                            scale=0.12,
                            opacity=0.85
                        )
                        print(f"[DEBUG] Logo added successfully")
                        pipeline_steps[-1]["logo_added"] = True
                    except Exception as e:
                        print(f"[DEBUG] Logo error: {str(e)}")
                        pipeline_steps[-1]["logo_error"] = str(e)
                        # Continue without logo
                
                # Convert to base64 data URL
                composited_b64 = base64.b64encode(current_image_bytes).decode('utf-8')
                result.image_url = f"data:image/png;base64,{composited_b64}"
                if result.image_urls:
                    result.image_urls[0] = result.image_url
                
                pipeline_steps[-1]["status"] = "completed"
            except Exception as e:
                pipeline_steps[-1]["status"] = "failed"
                pipeline_steps[-1]["error"] = str(e)
                # Keep original image if post-processing fails
        
        # Step 6: Store in graph
        if result.success:
            pipeline_steps.append({
                "step": "store_generation",
                "status": "started",
                "timestamp": datetime.utcnow().isoformat()
            })
            
            try:
                await self._store_generation(
                    brand_id=brand_id,
                    generation_id=generation_id,
                    result=result,
                    plan=plan,
                    brand_dna=brand_dna
                )
                pipeline_steps[-1]["status"] = "completed"
            except Exception as e:
                pipeline_steps[-1]["status"] = "failed"
                pipeline_steps[-1]["error"] = str(e)
        
        return {
            "success": result.success,
            "generation_id": generation_id,
            "image_url": result.image_url,
            "image_urls": result.image_urls,
            "headline": result.headline,
            "body_copy": result.body_copy,
            "compiled_prompt": result.compiled_prompt or positive_prompt,
            "model_used": result.model_used,
            "provider": result.provider,
            "cost_usd": result.cost_usd,
            "generation_time_ms": result.generation_time_ms,
            "conditioners_used": result.conditioners_used,
            "pipeline_steps": pipeline_steps,
            "plan": plan.to_dict() if plan else None,
            "brand_name": brand_dna.brand_name,
            "error_message": result.error_message
        }
    
    async def _store_generation(
        self,
        brand_id: str,
        generation_id: str,
        result: GenerationResult,
        plan: Optional[GenerationPlan],
        brand_dna: BrandDNA
    ):
        """Store generation node and relationships in Neo4j"""
        
        query = """
        MATCH (b:Brand {id: $brand_id})
        
        CREATE (g:Generation {
            id: $generation_id,
            prompt: $prompt,
            compiled_prompt: $compiled_prompt,
            image_url: $image_url,
            model_used: $model_used,
            provider: $provider,
            cost_usd: $cost_usd,
            generation_time_ms: $generation_time_ms,
            conditioners_used: $conditioners_used,
            created_at: datetime()
        })
        
        CREATE (b)-[:GENERATED]->(g)
        
        RETURN g
        """
        
        self.neo4j.execute_query(query, {
            "brand_id": brand_id,
            "generation_id": generation_id,
            "prompt": plan.scene_description if plan else result.compiled_prompt,
            "compiled_prompt": result.compiled_prompt,
            "image_url": result.image_url,
            "model_used": result.model_used,
            "provider": result.provider,
            "cost_usd": result.cost_usd,
            "generation_time_ms": result.generation_time_ms,
            "conditioners_used": result.conditioners_used
        })
        
        # Link to used colors
        if brand_dna.colors:
            for color in brand_dna.colors:
                if color.get("hex"):
                    color_query = """
                    MATCH (g:Generation {id: $generation_id})
                    MATCH (c:ColorNode {hex: $hex})
                    MERGE (g)-[:USED_COLOR {weight: $weight}]->(c)
                    """
                    self.neo4j.execute_query(color_query, {
                        "generation_id": generation_id,
                        "hex": color["hex"],
                        "weight": color.get("weight", 0.5)
                    })
    
    # ===================
    # FEEDBACK PROCESSING
    # ===================
    
    async def process_feedback(
        self,
        generation_id: str,
        rating: str,  # positive, negative, neutral
        selected_aspects: List[str],  # color, style, composition, product, character
        feedback_text: str
    ) -> Dict[str, Any]:
        """
        Process user feedback:
        1. Retrieve generation context
        2. LLM analyzes feedback
        3. Update graph nodes
        4. Create learned preferences
        """
        
        # Get generation and brand context
        query = """
        MATCH (b:Brand)-[:GENERATED]->(g:Generation {id: $generation_id})
        RETURN b, g
        """
        result = self.neo4j.execute_query(query, {"generation_id": generation_id})
        
        if not result:
            return {"success": False, "error": "Generation not found"}
        
        brand_node = result[0]["b"]
        generation_node = result[0]["g"]
        brand_id = brand_node["id"]
        
        # Get full brand DNA
        brand_dna = await self.get_brand_dna(brand_id)
        
        generation_context = {
            "prompt": generation_node.get("prompt"),
            "compiled_prompt": generation_node.get("compiled_prompt"),
            "model_used": generation_node.get("model_used"),
            "conditioners_used": generation_node.get("conditioners_used", [])
        }
        
        user_feedback = {
            "rating": rating,
            "selected_aspects": selected_aspects,
            "feedback_text": feedback_text
        }
        
        # LLM analysis
        analysis = await self.reasoner.analyze_feedback(
            generation_context=generation_context,
            user_feedback=user_feedback,
            brand_dna=brand_dna.to_dict()
        )
        
        # Apply node updates
        updates_applied = []
        for update in analysis.node_updates:
            try:
                await self._apply_node_update(brand_id, update)
                updates_applied.append(update)
            except Exception as e:
                print(f"Failed to apply update {update}: {e}")
        
        # Create learned preferences
        preferences_created = []
        for pref in analysis.new_preferences:
            try:
                pref_id = await self._create_learned_preference(brand_id, generation_id, pref)
                pref["id"] = pref_id
                preferences_created.append(pref)
            except Exception as e:
                print(f"Failed to create preference {pref}: {e}")
        
        # Store feedback on generation
        feedback_query = """
        MATCH (g:Generation {id: $generation_id})
        SET g.user_rating = $rating,
            g.feedback_text = $feedback_text,
            g.feedback_aspects = $aspects,
            g.feedback_at = datetime()
        """
        self.neo4j.execute_query(feedback_query, {
            "generation_id": generation_id,
            "rating": rating,
            "feedback_text": feedback_text,
            "aspects": selected_aspects
        })
        
        return {
            "success": True,
            "analysis": analysis.to_dict(),
            "updates_applied": updates_applied,
            "preferences_created": preferences_created,
            "affected_aspects": analysis.affected_aspects
        }
    
    async def _apply_node_update(self, brand_id: str, update: Dict[str, Any]):
        """Apply a single node update from feedback analysis"""
        node_type = update.get("node_type")
        prop = update.get("property")
        new_value = update.get("new_value")
        
        if node_type == "CompositionNode":
            query = """
            MATCH (b:Brand {id: $brand_id})-[:HAS_COMPOSITION]->(comp:CompositionNode)
            SET comp[$property] = $value, comp.updated_at = datetime()
            """
            self.neo4j.execute_query(query, {
                "brand_id": brand_id,
                "property": prop,
                "value": new_value
            })
        
        elif node_type == "StyleNode":
            query = """
            MATCH (b:Brand {id: $brand_id})-[:HAS_STYLE]->(s:StyleNode)
            SET s[$property] = $value
            """
            self.neo4j.execute_query(query, {
                "brand_id": brand_id,
                "property": prop,
                "value": new_value
            })
    
    async def _create_learned_preference(
        self, 
        brand_id: str, 
        generation_id: str,
        pref: Dict[str, Any]
    ) -> str:
        """Create a new LearnedPreference node"""
        pref_id = str(uuid.uuid4())
        
        query = """
        MATCH (b:Brand {id: $brand_id})
        MATCH (g:Generation {id: $generation_id})
        
        CREATE (lp:LearnedPreference {
            id: $pref_id,
            trigger: $trigger,
            applies: $applies,
            aspect: $aspect,
            confidence: $confidence,
            feedback_count: 1,
            positive_count: 1,
            source_generations: [$generation_id],
            created_at: datetime()
        })
        
        CREATE (b)-[:LEARNED {confidence: $confidence}]->(lp)
        CREATE (lp)-[:DERIVED_FROM]->(g)
        
        RETURN lp
        """
        
        self.neo4j.execute_query(query, {
            "brand_id": brand_id,
            "generation_id": generation_id,
            "pref_id": pref_id,
            "trigger": pref.get("trigger", ""),
            "applies": pref.get("applies", ""),
            "aspect": pref.get("aspect", "unknown"),
            "confidence": pref.get("confidence", 1.0)
        })
        
        return pref_id
    
    # ===================
    # BRAND DNA UPDATES
    # ===================
    
    async def add_color(
        self,
        brand_id: str,
        hex_code: str,
        name: str,
        role: str = "accent"
    ) -> Dict[str, Any]:
        """Add a color to brand DNA"""
        query = """
        MATCH (b:Brand {id: $brand_id})
        MERGE (c:ColorNode {hex: $hex})
        ON CREATE SET c.name = $name, c.created_at = datetime()
        MERGE (b)-[r:HAS_COLOR]->(c)
        SET r.role = $role
        RETURN c
        """
        result = self.neo4j.execute_query(query, {
            "brand_id": brand_id,
            "hex": hex_code.upper(),
            "name": name,
            "role": role
        })
        
        return {"success": True, "color": dict(result[0]["c"]) if result else None}
    
    async def add_product(
        self,
        brand_id: str,
        name: str,
        category: str,
        image_url: str,
        description: str = ""
    ) -> Dict[str, Any]:
        """Add a product to brand DNA"""
        product_id = str(uuid.uuid4())
        
        query = """
        MATCH (b:Brand {id: $brand_id})
        CREATE (p:ProductNode {
            id: $product_id,
            name: $name,
            category: $category,
            image_url: $image_url,
            description: $description,
            created_at: datetime()
        })
        CREATE (b)-[:SELLS]->(p)
        RETURN p
        """
        result = self.neo4j.execute_query(query, {
            "brand_id": brand_id,
            "product_id": product_id,
            "name": name,
            "category": category,
            "image_url": image_url,
            "description": description
        })
        
        return {"success": True, "product": dict(result[0]["p"]) if result else None}
    
    async def add_character(
        self,
        brand_id: str,
        name: str,
        reference_image_url: str,
        body_type: str = "average"
    ) -> Dict[str, Any]:
        """Add a character reference for consistency"""
        character_id = str(uuid.uuid4())
        
        query = """
        MATCH (b:Brand {id: $brand_id})
        CREATE (ch:CharacterNode {
            id: $character_id,
            name: $name,
            reference_image_url: $reference_image_url,
            body_type: $body_type,
            usage_count: 0,
            created_at: datetime()
        })
        CREATE (b)-[:HAS_CHARACTER]->(ch)
        RETURN ch
        """
        result = self.neo4j.execute_query(query, {
            "brand_id": brand_id,
            "character_id": character_id,
            "name": name,
            "reference_image_url": reference_image_url,
            "body_type": body_type
        })
        
        return {"success": True, "character": dict(result[0]["ch"]) if result else None}
    
    async def update_composition(
        self,
        brand_id: str,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update composition preferences"""
        # Build dynamic SET clause
        set_parts = []
        params = {"brand_id": brand_id}
        
        allowed_props = ["layout", "text_density", "text_position", 
                        "overlay_opacity", "padding_preference", "aspect_ratio_preference"]
        
        for prop, value in updates.items():
            if prop in allowed_props:
                set_parts.append(f"comp.{prop} = ${prop}")
                params[prop] = value
        
        if not set_parts:
            return {"success": False, "error": "No valid properties to update"}
        
        query = f"""
        MATCH (b:Brand {{id: $brand_id}})
        MERGE (comp:CompositionNode {{id: $brand_id + '_default_comp'}})
        ON CREATE SET comp.created_at = datetime()
        MERGE (b)-[:HAS_COMPOSITION]->(comp)
        SET {', '.join(set_parts)}, comp.updated_at = datetime()
        RETURN comp
        """
        
        result = self.neo4j.execute_query(query, params)
        
        return {"success": True, "composition": dict(result[0]["comp"]) if result else None}


# Factory
_service_instance: Optional[BrandDNAService] = None

def get_brand_dna_service() -> BrandDNAService:
    """Get or create BrandDNAService instance"""
    global _service_instance
    if _service_instance is None:
        _service_instance = BrandDNAService()
    return _service_instance

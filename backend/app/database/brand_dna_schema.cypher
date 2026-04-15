# =============================================================================
# BRAND DNA KNOWLEDGE GRAPH SCHEMA
# GraphRAG-Guided Brand Content Generation System
# =============================================================================
# This schema represents the "Brand DNA" - a living knowledge graph that:
# 1. Stores brand identity (colors, style, products, characters)
# 2. Learns from user feedback (LearnedPreference nodes)
# 3. Conditions the diffusion model via graph embeddings
# =============================================================================

# ========================
# CORE CONSTRAINTS
# ========================

# Brand uniqueness
CREATE CONSTRAINT brand_id IF NOT EXISTS 
FOR (b:Brand) REQUIRE b.id IS UNIQUE;

# Color uniqueness (avoid duplicates)
CREATE CONSTRAINT color_hex IF NOT EXISTS 
FOR (c:ColorNode) REQUIRE c.hex IS UNIQUE;

# Product uniqueness per brand
CREATE CONSTRAINT product_id IF NOT EXISTS 
FOR (p:ProductNode) REQUIRE p.id IS UNIQUE;

# Character uniqueness
CREATE CONSTRAINT character_id IF NOT EXISTS 
FOR (ch:CharacterNode) REQUIRE ch.id IS UNIQUE;

# Style uniqueness
CREATE CONSTRAINT style_id IF NOT EXISTS 
FOR (s:StyleNode) REQUIRE s.id IS UNIQUE;

# Composition rule uniqueness
CREATE CONSTRAINT composition_id IF NOT EXISTS 
FOR (c:CompositionNode) REQUIRE c.id IS UNIQUE;

# Learned preference uniqueness
CREATE CONSTRAINT learned_pref_id IF NOT EXISTS 
FOR (lp:LearnedPreference) REQUIRE lp.id IS UNIQUE;

# Generation uniqueness
CREATE CONSTRAINT generation_id IF NOT EXISTS 
FOR (g:Generation) REQUIRE g.id IS UNIQUE;

# ========================
# PERFORMANCE INDEXES
# ========================

CREATE INDEX brand_name IF NOT EXISTS FOR (b:Brand) ON (b.name);
CREATE INDEX brand_website IF NOT EXISTS FOR (b:Brand) ON (b.website);
CREATE INDEX product_name IF NOT EXISTS FOR (p:ProductNode) ON (p.name);
CREATE INDEX product_category IF NOT EXISTS FOR (p:ProductNode) ON (p.category);
CREATE INDEX style_type IF NOT EXISTS FOR (s:StyleNode) ON (s.type);
CREATE INDEX character_name IF NOT EXISTS FOR (ch:CharacterNode) ON (ch.name);
CREATE INDEX learned_trigger IF NOT EXISTS FOR (lp:LearnedPreference) ON (lp.trigger);
CREATE INDEX generation_created IF NOT EXISTS FOR (g:Generation) ON (g.created_at);

# ========================
# NODE SCHEMAS (with example properties)
# ========================

# --- BRAND NODE ---
# The root of the Brand DNA graph
# (:Brand {
#   id: "brand_uuid",
#   name: "Nike",
#   website: "https://nike.com",
#   tagline: "Just Do It",
#   industry: "sportswear",
#   logo_url: "https://...",
#   logo_embedding: [0.1, 0.2, ...],  # CLIP embedding of logo
#   created_at: datetime(),
#   updated_at: datetime()
# })

# --- COLOR NODE ---
# Brand color palette with learned weights
# (:ColorNode {
#   id: "color_uuid",
#   hex: "#FF5733",
#   name: "Nike Orange",
#   rgb: [255, 87, 51],
#   role: "primary",  # primary | secondary | accent | background
#   usage_weight: 0.85,  # Learned from feedback (0-1)
#   contexts: ["hero", "cta", "background"],  # Where this color works best
#   created_at: datetime()
# })

# --- STYLE NODE ---
# Brand aesthetic/mood characteristics
# (:StyleNode {
#   id: "style_uuid",
#   type: "bold",  # bold | minimalist | playful | luxury | professional | etc
#   keywords: ["dynamic", "athletic", "powerful"],
#   weight: 0.9,  # Learned importance
#   negative_keywords: ["soft", "gentle"],  # What to avoid
#   created_at: datetime()
# })

# --- COMPOSITION NODE ---
# Layout and visual structure preferences (heavily learned from feedback)
# (:CompositionNode {
#   id: "comp_uuid",
#   layout: "centered",  # centered | left-aligned | split | grid | asymmetric
#   text_density: "minimal",  # minimal | moderate | dense
#   text_position: "bottom",  # top | center | bottom | overlay
#   overlay_opacity: 0.3,  # 0-1, learned from feedback
#   padding_preference: "comfortable",  # tight | comfortable | spacious
#   aspect_ratio_preference: "1:1",  # 1:1 | 16:9 | 9:16 | 4:3
#   created_at: datetime(),
#   updated_at: datetime()
# })

# --- PRODUCT NODE ---
# Product references with image embeddings for IP-Adapter
# (:ProductNode {
#   id: "prod_uuid",
#   name: "Air Max 90",
#   category: "footwear",
#   description: "Classic running shoe",
#   image_url: "https://...",
#   clip_embedding: [0.1, 0.2, ...],  # For semantic search
#   ip_adapter_embedding: [...],  # For diffusion conditioning
#   usage_count: 15,  # How often used in generations
#   avg_rating: 0.85,  # Average feedback score
#   created_at: datetime()
# })

# --- CHARACTER NODE ---
# Brand faces/models for consistency (PuLID embeddings)
# (:CharacterNode {
#   id: "char_uuid",
#   name: "Brand Ambassador 1",
#   reference_image_url: "https://...",
#   face_embedding: [...],  # PuLID/InstantID face embedding
#   body_type: "athletic",
#   age_range: "25-35",
#   gender: "female",
#   usage_count: 10,
#   created_at: datetime()
# })

# --- LEARNED PREFERENCE NODE ---
# The key to GraphRAG learning - stores conditional rules from feedback
# (:LearnedPreference {
#   id: "pref_uuid",
#   trigger: "text_position = centered",  # When this condition...
#   applies: "overlay_opacity = 0.3",  # ...apply these settings
#   aspect: "composition",  # color | style | composition | product | character
#   confidence: 0.85,  # Based on feedback count and consistency
#   feedback_count: 5,  # How many times this was reinforced
#   positive_count: 4,
#   negative_count: 1,
#   source_generations: ["gen_id1", "gen_id2"],  # Which generations led to this
#   created_at: datetime(),
#   updated_at: datetime()
# })

# --- GENERATION NODE ---
# Record of each generation with full context
# (:Generation {
#   id: "gen_uuid",
#   prompt: "Athletic woman running in city",
#   compiled_prompt: "Full prompt sent to model...",
#   image_url: "https://...",
#   model_used: "flux-kontext",
#   conditioners_used: ["ip_adapter", "pulid"],
#   brand_score: 0.85,
#   user_rating: "positive",
#   feedback_text: "Great colors but too much text",
#   feedback_aspects: ["text_density"],
#   conditioning_weights: {color: 0.8, style: 0.9},
#   created_at: datetime()
# })

# ========================
# RELATIONSHIP TYPES
# ========================

# Brand Identity Relationships
# (Brand)-[:HAS_COLOR {role: "primary", weight: 0.9}]->(ColorNode)
# (Brand)-[:HAS_STYLE {weight: 0.85}]->(StyleNode)
# (Brand)-[:HAS_COMPOSITION]->(CompositionNode)
# (Brand)-[:SELLS {featured: true}]->(ProductNode)
# (Brand)-[:HAS_CHARACTER {role: "primary"}]->(CharacterNode)

# Learning Relationships
# (Brand)-[:LEARNED {confidence: 0.85}]->(LearnedPreference)
# (LearnedPreference)-[:AFFECTS]->(CompositionNode|StyleNode|ColorNode)
# (LearnedPreference)-[:DERIVED_FROM]->(Generation)

# Generation Relationships
# (Brand)-[:GENERATED]->(Generation)
# (Generation)-[:USED_COLOR {weight: 0.8}]->(ColorNode)
# (Generation)-[:USED_STYLE {weight: 0.9}]->(StyleNode)
# (Generation)-[:USED_PRODUCT]->(ProductNode)
# (Generation)-[:USED_CHARACTER]->(CharacterNode)
# (Generation)-[:APPLIED_COMPOSITION]->(CompositionNode)

# Feedback Relationships
# (Generation)-[:RECEIVED_FEEDBACK {rating: "positive", aspect: "colors"}]->(LearnedPreference)

# ========================
# USEFUL QUERIES
# ========================

# Get full Brand DNA for generation
# MATCH (b:Brand {id: $brandId})
# OPTIONAL MATCH (b)-[cr:HAS_COLOR]->(c:ColorNode)
# OPTIONAL MATCH (b)-[sr:HAS_STYLE]->(s:StyleNode)
# OPTIONAL MATCH (b)-[:HAS_COMPOSITION]->(comp:CompositionNode)
# OPTIONAL MATCH (b)-[:SELLS]->(p:ProductNode)
# OPTIONAL MATCH (b)-[:HAS_CHARACTER]->(ch:CharacterNode)
# OPTIONAL MATCH (b)-[:LEARNED]->(lp:LearnedPreference)
# RETURN b, 
#        collect(DISTINCT {color: c, role: cr.role, weight: cr.weight}) as colors,
#        collect(DISTINCT {style: s, weight: sr.weight}) as styles,
#        comp as composition,
#        collect(DISTINCT p) as products,
#        collect(DISTINCT ch) as characters,
#        collect(DISTINCT lp) as learned_preferences

# Get applicable learned preferences for a context
# MATCH (b:Brand {id: $brandId})-[:LEARNED]->(lp:LearnedPreference)
# WHERE lp.trigger CONTAINS $context  // e.g., "text_position = centered"
# AND lp.confidence > 0.5
# RETURN lp ORDER BY lp.confidence DESC

# Track generation lineage
# MATCH (b:Brand {id: $brandId})-[:GENERATED]->(g:Generation)
# OPTIONAL MATCH (g)-[:USED_COLOR]->(c:ColorNode)
# OPTIONAL MATCH (g)-[:USED_PRODUCT]->(p:ProductNode)
# RETURN g, collect(c) as colors_used, collect(p) as products_used
# ORDER BY g.created_at DESC LIMIT 10

# Get learning evolution over time
# MATCH (b:Brand {id: $brandId})-[:LEARNED]->(lp:LearnedPreference)
# RETURN lp.aspect, count(*) as preference_count, avg(lp.confidence) as avg_confidence
# ORDER BY preference_count DESC

# Find similar generations (for learning)
# MATCH (g1:Generation {id: $genId})-[:USED_STYLE]->(s:StyleNode)<-[:USED_STYLE]-(g2:Generation)
# WHERE g1 <> g2 AND g2.user_rating = 'positive'
# RETURN g2 LIMIT 5

# ========================
# INITIALIZATION QUERIES
# ========================

# Create default composition node for new brand
# MERGE (comp:CompositionNode {id: $brandId + '_default_comp'})
# SET comp.layout = 'centered',
#     comp.text_density = 'moderate',
#     comp.text_position = 'bottom',
#     comp.overlay_opacity = 0.0,
#     comp.padding_preference = 'comfortable',
#     comp.created_at = datetime()
# WITH comp
# MATCH (b:Brand {id: $brandId})
# MERGE (b)-[:HAS_COMPOSITION]->(comp)

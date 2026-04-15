# ============================================================================
# ENHANCED GRAPHRAG SCHEMA FOR BRAND-ALIGNED CONTENT GENERATION
# Version: 2.0 - Capstone Research Implementation
# ============================================================================
# This schema supports:
# - Compositional scene graph generation
# - Element-level constraint management
# - Continuous preference learning from feedback
# - Character consistency preservation
# - Multi-hop reasoning queries
# ============================================================================

# ============================================================================
# CONSTRAINTS (Uniqueness & Existence)
# ============================================================================

# Core entity constraints
CREATE CONSTRAINT brand_id IF NOT EXISTS FOR (b:Brand) REQUIRE b.id IS UNIQUE;
CREATE CONSTRAINT color_hex IF NOT EXISTS FOR (c:Color) REQUIRE c.hex IS UNIQUE;
CREATE CONSTRAINT product_id IF NOT EXISTS FOR (p:Product) REQUIRE p.id IS UNIQUE;
CREATE CONSTRAINT logo_id IF NOT EXISTS FOR (l:Logo) REQUIRE l.id IS UNIQUE;

# Scene and composition constraints
CREATE CONSTRAINT scene_graph_id IF NOT EXISTS FOR (sg:SceneGraph) REQUIRE sg.id IS UNIQUE;
CREATE CONSTRAINT scene_element_id IF NOT EXISTS FOR (se:SceneElement) REQUIRE se.id IS UNIQUE;
CREATE CONSTRAINT composition_id IF NOT EXISTS FOR (comp:Composition) REQUIRE comp.id IS UNIQUE;

# Constraint system
CREATE CONSTRAINT constraint_id IF NOT EXISTS FOR (c:Constraint) REQUIRE c.id IS UNIQUE;
CREATE CONSTRAINT negative_pattern_id IF NOT EXISTS FOR (np:NegativePattern) REQUIRE np.id IS UNIQUE;

# Learning system
CREATE CONSTRAINT learned_pref_id IF NOT EXISTS FOR (lp:LearnedPreference) REQUIRE lp.id IS UNIQUE;
CREATE CONSTRAINT feedback_id IF NOT EXISTS FOR (f:Feedback) REQUIRE f.id IS UNIQUE;

# Generation tracking
CREATE CONSTRAINT generation_id IF NOT EXISTS FOR (g:Generation) REQUIRE g.id IS UNIQUE;
CREATE CONSTRAINT gen_element_id IF NOT EXISTS FOR (ge:GeneratedElement) REQUIRE ge.id IS UNIQUE;

# Character consistency
CREATE CONSTRAINT character_id IF NOT EXISTS FOR (char:Character) REQUIRE char.id IS UNIQUE;
CREATE CONSTRAINT face_embedding_id IF NOT EXISTS FOR (fe:FaceEmbedding) REQUIRE fe.id IS UNIQUE;

# ============================================================================
# INDEXES (Performance Optimization)
# ============================================================================

CREATE INDEX brand_website IF NOT EXISTS FOR (b:Brand) ON (b.website);
CREATE INDEX brand_name IF NOT EXISTS FOR (b:Brand) ON (b.name);
CREATE INDEX product_name IF NOT EXISTS FOR (p:Product) ON (p.name);
CREATE INDEX constraint_type IF NOT EXISTS FOR (c:Constraint) ON (c.type);
CREATE INDEX constraint_strength IF NOT EXISTS FOR (c:Constraint) ON (c.strength);
CREATE INDEX learned_pref_confidence IF NOT EXISTS FOR (lp:LearnedPreference) ON (lp.confidence);
CREATE INDEX feedback_type IF NOT EXISTS FOR (f:Feedback) ON (f.type);
CREATE INDEX generation_timestamp IF NOT EXISTS FOR (g:Generation) ON (g.created_at);
CREATE INDEX scene_element_type IF NOT EXISTS FOR (se:SceneElement) ON (se.type);

# ============================================================================
# NODE TYPE DEFINITIONS (Reference Documentation)
# ============================================================================

# --- ORGANIZATIONAL HIERARCHY ---
# (:Brand {
#     id: String (UUID),
#     name: String,
#     website: String,
#     tagline: String,
#     industry: String,
#     font_id: String,
#     text_layout: String,
#     created_at: DateTime,
#     updated_at: DateTime
# })

# --- VISUAL IDENTITY ---
# (:Logo {
#     id: String (UUID),
#     url: String,
#     quality_score: Float,
#     source: String,  // 'scraped', 'uploaded', 'generated'
#     updated_at: DateTime
# })

# (:Color {
#     hex: String,  // Primary key, e.g., '#FF5733'
#     name: String,  // 'Sunset Orange'
#     rgb: [Integer, Integer, Integer],
#     hsl: [Float, Float, Float],
#     role: String  // 'primary', 'secondary', 'accent', 'background'
# })

# --- PRODUCTS ---
# (:Product {
#     id: String (UUID),
#     name: String,
#     price: String,
#     category: String,
#     description: String,
#     image_url: String,
#     created_at: DateTime
# })

# --- SCENE COMPOSITION (NEW) ---
# (:SceneGraph {
#     id: String (UUID),
#     prompt: String,  // Original user prompt
#     layout_type: String,  // 'centered', 'rule_of_thirds', 'asymmetric', 'grid'
#     aspect_ratio: String,  // '1:1', '16:9', '4:3', etc.
#     mood: String,  // 'energetic', 'calm', 'professional', etc.
#     created_at: DateTime
# })

# (:SceneElement {
#     id: String (UUID),
#     type: String,  // 'BACKGROUND', 'SUBJECT', 'SECONDARY', 'TEXT_AREA', 'ACCENT', 'CHARACTER'
#     semantic_label: String,  // 'coffee_cup', 'outdoor_cafe', 'sale_text'
#     spatial_position: String,  // 'center', 'top-left', 'bottom-right', 'rule-of-thirds-left'
#     z_index: Integer,  // Layering order
#     bounding_box: String,  // JSON: {x, y, width, height} as percentages
#     style_attributes: String,  // JSON: {lighting, material, texture, etc.}
#     importance: Float  // 0.0 to 1.0, for constraint priority
# })

# (:Composition {
#     id: String (UUID),
#     name: String,  // 'product_hero', 'lifestyle_scene', 'promotional_banner'
#     focal_point: String,  // JSON: {x, y} as percentages
#     visual_flow: String,  // 'left-to-right', 'center-out', 'z-pattern'
#     balance_type: String  // 'symmetric', 'asymmetric', 'radial'
# })

# --- CONSTRAINT SYSTEM (NEW) ---
# (:Constraint {
#     id: String (UUID),
#     type: String,  // 'MUST_INCLUDE', 'MUST_AVOID', 'PREFER', 'DISCOURAGE'
#     strength: Float,  // 0.0 to 1.0 (soft to hard)
#     scope: String,  // 'global', 'element_type', 'specific_element'
#     target_type: String,  // 'color', 'style', 'composition', 'content', 'text'
#     target_value: String,  // The specific thing to include/avoid
#     description: String,  // Human-readable explanation
#     reason: String,  // 'brand_guideline', 'legal', 'user_feedback', 'learned'
#     applies_to: String,  // Element type or 'all'
#     created_at: DateTime,
#     expires_at: DateTime  // Optional expiration
# })

# (:NegativePattern {
#     id: String (UUID),
#     element_type: String,
#     pattern_description: String,
#     example_url: String,  // URL to example of what NOT to do
#     severity: String,  // 'minor', 'major', 'critical'
#     occurrence_count: Integer,  // How many times this mistake was made
#     created_at: DateTime
# })

# --- LEARNING SYSTEM (NEW) ---
# (:LearnedPreference {
#     id: String (UUID),
#     attribute: String,  // 'SUBJECT_lighting', 'TEXT_AREA_position', 'color_saturation'
#     preferred_value: String,  // The learned preference value
#     anti_preferred_value: String,  // What to avoid
#     confidence: Float,  // 0.0 to 1.0, based on feedback consistency
#     sample_count: Integer,  // Number of feedback samples
#     positive_count: Integer,
#     negative_count: Integer,
#     last_updated: DateTime
# })

# (:Feedback {
#     id: String (UUID),
#     type: String,  // 'like', 'dislike', 'edit', 'regenerate', 'accept'
#     level: String,  // 'whole', 'element', 'attribute'
#     comment: String,  // Optional user explanation
#     element_type: String,  // If element-level
#     attribute: String,  // If attribute-level
#     old_value: String,  // For edit feedback
#     new_value: String,  // For edit feedback
#     created_at: DateTime
# })

# --- GENERATION TRACKING (ENHANCED) ---
# (:Generation {
#     id: String (UUID),
#     brand_id: String,
#     prompt: String,
#     compiled_prompt: String,  // After constraint injection
#     negative_prompt: String,
#     image_url: String,
#     image_without_text_url: String,
#     headline: String,
#     body_copy: String,
#     brand_score: Float,
#     constraint_satisfaction_score: Float,
#     generation_time_ms: Integer,
#     model_used: String,
#     created_at: DateTime
# })

# (:GeneratedElement {
#     id: String (UUID),
#     type: String,  // Same as SceneElement types
#     content: String,  // Description or actual content
#     bounding_box: String,  // JSON: {x, y, width, height}
#     extracted_colors: String,  // JSON array of hex codes
#     style_analysis: String,  // JSON of detected style attributes
#     satisfaction_score: Float  // Per-element constraint satisfaction
# })

# --- CHARACTER CONSISTENCY (NEW) ---
# (:Character {
#     id: String (UUID),
#     name: String,  // 'brand_mascot', 'spokesperson', 'model_1'
#     description: String,
#     reference_images: String,  // JSON array of image URLs
#     created_at: DateTime
# })

# (:FaceEmbedding {
#     id: String (UUID),
#     embedding_vector: String,  // JSON array of floats (512-dim typically)
#     source_image_url: String,
#     face_landmarks: String,  // JSON of detected landmarks
#     face_attributes: String,  // JSON: {age_range, gender_presentation, etc.}
#     quality_score: Float,
#     created_at: DateTime
# })

# ============================================================================
# RELATIONSHIP DEFINITIONS
# ============================================================================

# --- Brand Relationships ---
# (Brand)-[:HAS_LOGO]->(Logo)
# (Brand)-[:USES_COLOR {role: 'primary'|'secondary'|'accent'}]->(Color)
# (Brand)-[:SELLS]->(Product)
# (Brand)-[:HAS_CHARACTER]->(Character)
# (Brand)-[:HAS_CONSTRAINT]->(Constraint)
# (Brand)-[:HAS_LEARNED_PREFERENCE]->(LearnedPreference)
# (Brand)-[:AVOID_PATTERN]->(NegativePattern)
# (Brand)-[:GENERATED]->(Generation)
# (Brand)-[:PREFERS_COMPOSITION]->(Composition)

# --- Color Relationships ---
# (Color)-[:HARMONIZES_WITH {harmony_type: 'complementary'|'analogous'|'triadic'}]->(Color)
# (Color)-[:CONTRASTS_WITH]->(Color)

# --- Scene Graph Relationships ---
# (Generation)-[:BASED_ON]->(SceneGraph)
# (SceneGraph)-[:CONTAINS]->(SceneElement)
# (SceneGraph)-[:USES_COMPOSITION]->(Composition)
# (SceneElement)-[:POSITIONED_RELATIVE_TO {relation: 'above'|'below'|'left'|'right'|'overlaps'}]->(SceneElement)
# (SceneElement)-[:APPLIES_COLOR {role: 'fill'|'stroke'|'gradient'}]->(Color)
# (SceneElement)-[:REPRESENTS]->(Product)
# (SceneElement)-[:DEPICTS]->(Character)

# --- Constraint Relationships ---
# (Constraint)-[:APPLIES_TO_ELEMENT_TYPE {element_type: String}]->(Brand)
# (Constraint)-[:DERIVED_FROM]->(Feedback)
# (Constraint)-[:CONFLICTS_WITH]->(Constraint)

# --- Learning Relationships ---
# (Feedback)-[:ABOUT_GENERATION]->(Generation)
# (Feedback)-[:ABOUT_ELEMENT]->(GeneratedElement)
# (Feedback)-[:REGARDING_ATTRIBUTE {attribute: String}]->(GeneratedElement)
# (LearnedPreference)-[:DERIVED_FROM_FEEDBACK]->(Feedback)
# (LearnedPreference)-[:OVERRIDES]->(Constraint)  // When learned preference contradicts old constraint

# --- Generation Relationships ---
# (Generation)-[:CONTAINS_ELEMENT]->(GeneratedElement)
# (Generation)-[:RECEIVED_FEEDBACK]->(Feedback)
# (Generation)-[:SATISFIED]->(Constraint)
# (Generation)-[:VIOLATED]->(Constraint)
# (GeneratedElement)-[:MATCHES_SCENE_ELEMENT]->(SceneElement)

# --- Character Consistency Relationships ---
# (Character)-[:HAS_EMBEDDING]->(FaceEmbedding)
# (Generation)-[:FEATURES]->(Character)
# (GeneratedElement)-[:DEPICTS_CHARACTER]->(Character)
# (FaceEmbedding)-[:DERIVED_FROM]->(Generation)

# ============================================================================
# SAMPLE DATA FOR TESTING
# ============================================================================

# Create sample brand with enhanced schema
CREATE (b:Brand {
    id: 'brand_001',
    name: 'Sunrise Coffee',
    website: 'https://sunrisecoffee.com',
    tagline: 'Start your day with sunshine in a cup',
    industry: 'Food & Beverage',
    font_id: 'montserrat',
    text_layout: 'bottom_centered',
    created_at: datetime(),
    updated_at: datetime()
});

# Add colors with harmony relationships
CREATE (c1:Color {hex: '#8B4513', name: 'Coffee Brown', rgb: [139, 69, 19], role: 'primary'});
CREATE (c2:Color {hex: '#FFD700', name: 'Sunrise Gold', rgb: [255, 215, 0], role: 'secondary'});
CREATE (c3:Color {hex: '#F5F5DC', name: 'Cream', rgb: [245, 245, 220], role: 'accent'});
CREATE (c4:Color {hex: '#2F4F4F', name: 'Dark Slate', rgb: [47, 79, 79], role: 'text'});

# Color harmonies
MATCH (c1:Color {hex: '#8B4513'}), (c2:Color {hex: '#FFD700'})
CREATE (c1)-[:HARMONIZES_WITH {harmony_type: 'complementary'}]->(c2);

MATCH (c2:Color {hex: '#FFD700'}), (c3:Color {hex: '#F5F5DC'})
CREATE (c2)-[:HARMONIZES_WITH {harmony_type: 'analogous'}]->(c3);

# Link colors to brand
MATCH (b:Brand {id: 'brand_001'}), (c:Color)
WHERE c.hex IN ['#8B4513', '#FFD700', '#F5F5DC', '#2F4F4F']
CREATE (b)-[:USES_COLOR {role: c.role}]->(c);

# Add sample constraints
CREATE (con1:Constraint {
    id: 'con_001',
    type: 'MUST_AVOID',
    strength: 1.0,
    scope: 'global',
    target_type: 'color',
    target_value: '#FF0000',
    description: 'Never use pure red - competitor brand color',
    reason: 'brand_guideline',
    applies_to: 'all',
    created_at: datetime()
});

CREATE (con2:Constraint {
    id: 'con_002',
    type: 'PREFER',
    strength: 0.8,
    scope: 'element_type',
    target_type: 'lighting',
    target_value: 'warm_natural',
    description: 'Prefer warm natural lighting for product shots',
    reason: 'brand_guideline',
    applies_to: 'SUBJECT',
    created_at: datetime()
});

CREATE (con3:Constraint {
    id: 'con_003',
    type: 'MUST_INCLUDE',
    strength: 0.9,
    scope: 'global',
    target_type: 'style',
    target_value: 'inviting_atmosphere',
    description: 'Always convey warmth and invitation',
    reason: 'brand_guideline',
    applies_to: 'all',
    created_at: datetime()
});

# Link constraints to brand
MATCH (b:Brand {id: 'brand_001'}), (c:Constraint)
WHERE c.id IN ['con_001', 'con_002', 'con_003']
CREATE (b)-[:HAS_CONSTRAINT]->(c);

# Add sample composition templates
CREATE (comp1:Composition {
    id: 'comp_001',
    name: 'product_hero',
    focal_point: '{"x": 0.5, "y": 0.4}',
    visual_flow: 'center-out',
    balance_type: 'symmetric'
});

CREATE (comp2:Composition {
    id: 'comp_002',
    name: 'lifestyle_scene',
    focal_point: '{"x": 0.33, "y": 0.5}',
    visual_flow: 'left-to-right',
    balance_type: 'asymmetric'
});

MATCH (b:Brand {id: 'brand_001'}), (comp:Composition)
WHERE comp.id IN ['comp_001', 'comp_002']
CREATE (b)-[:PREFERS_COMPOSITION]->(comp);

# ============================================================================
# USEFUL QUERIES
# ============================================================================

# --- Get full brand context with constraints ---
# MATCH (b:Brand {id: $brand_id})
# OPTIONAL MATCH (b)-[:HAS_LOGO]->(logo)
# OPTIONAL MATCH (b)-[cr:USES_COLOR]->(color)
# OPTIONAL MATCH (b)-[:SELLS]->(product)
# OPTIONAL MATCH (b)-[:HAS_CONSTRAINT]->(constraint)
# OPTIONAL MATCH (b)-[:HAS_LEARNED_PREFERENCE]->(pref) WHERE pref.confidence > 0.7
# OPTIONAL MATCH (b)-[:AVOID_PATTERN]->(neg)
# OPTIONAL MATCH (b)-[:PREFERS_COMPOSITION]->(comp)
# RETURN b, logo, collect(DISTINCT {color: color, role: cr.role}),
#        collect(DISTINCT product), collect(DISTINCT constraint),
#        collect(DISTINCT pref), collect(DISTINCT neg), collect(DISTINCT comp)

# --- Get constraints for specific element type ---
# MATCH (b:Brand {id: $brand_id})-[:HAS_CONSTRAINT]->(c:Constraint)
# WHERE c.applies_to = $element_type OR c.applies_to = 'all'
# RETURN c ORDER BY c.strength DESC

# --- Aggregate feedback to update preferences ---
# MATCH (b:Brand {id: $brand_id})-[:GENERATED]->(g:Generation)
# MATCH (g)-[:CONTAINS_ELEMENT]->(ge:GeneratedElement)
# MATCH (ge)<-[:ABOUT_ELEMENT]-(f:Feedback)
# WITH ge.type as element_type, f.type as feedback_type, count(*) as count
# RETURN element_type, feedback_type, count
# ORDER BY element_type, count DESC

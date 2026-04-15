# GraphRAG Integration Design
## Brand Knowledge Graph Schema & Query Patterns

**Version**: 1.0  
**Date**: January 2026  
**Component**: Brand Intelligence + Graph Query Agents

---

## Table of Contents
1. [Graph Schema Design](#graph-schema-design)
2. [Ontology Definitions](#ontology-definitions)
3. [GraphRAG Query Patterns](#graphrag-query-patterns)
4. [Hybrid Search Architecture](#hybrid-search-architecture)
5. [Graph Update Mechanisms](#graph-update-mechanisms)
6. [Multi-Tenant Isolation](#multi-tenant-isolation)

---

## Graph Schema Design

### Core Principles

1. **Multi-Granularity Modeling**: Company → Brand → Campaign → Asset hierarchy
2. **Cross-Modal Relationships**: Connect visual, tonal, and thematic entities
3. **Constraint as First-Class Citizens**: Positive/negative rules stored as edges
4. **Temporal Versioning**: All nodes/edges versioned for audit and rollback

### Node Types (Labels)

```cypher
// ═══════════════════════════════════════════════════════════════════════
// ORGANIZATIONAL HIERARCHY
// ═══════════════════════════════════════════════════════════════════════

(:Tenant {
    id: UUID,
    name: String,
    tier: Enum['free', 'pro', 'enterprise'],
    created_at: DateTime,
    data_residency: Enum['us', 'eu', 'apac']
})

(:Brand {
    id: UUID,
    tenant_id: UUID,
    name: String,
    description: String,
    industry: String,
    created_at: DateTime,
    updated_at: DateTime,
    version: Integer
})

(:Campaign {
    id: UUID,
    brand_id: UUID,
    name: String,
    objective: String,
    start_date: Date,
    end_date: Date,
    status: Enum['draft', 'active', 'paused', 'completed'],
    budget: Float
})

(:Asset {
    id: UUID,
    campaign_id: UUID,
    type: Enum['image', 'text', 'video', 'composite'],
    status: Enum['generated', 'approved', 'rejected', 'published'],
    storage_uri: String,
    created_at: DateTime,
    generation_metadata: JSON
})

// ═══════════════════════════════════════════════════════════════════════
// VISUAL ONTOLOGY
// ═══════════════════════════════════════════════════════════════════════

(:ColorPalette {
    id: UUID,
    name: String,
    role: Enum['primary', 'secondary', 'accent', 'background', 'text'],
    colors: [HexColor],  // e.g., ['#FF5733', '#33FF57', '#3357FF']
    usage_guidelines: String
})

(:Typography {
    id: UUID,
    name: String,
    font_family: String,
    font_weight: Integer,
    role: Enum['heading', 'subheading', 'body', 'caption', 'cta'],
    size_range: {min: Integer, max: Integer},  // in px
    line_height: Float,
    letter_spacing: Float
})

(:Logo {
    id: UUID,
    variant: Enum['primary', 'secondary', 'icon', 'wordmark', 'monochrome'],
    storage_uri: String,
    min_size: {width: Integer, height: Integer},
    clear_space: Integer,  // minimum padding in px
    background_colors: [HexColor],  // allowed background colors
    embedding_vector: [Float]  // 512-dim visual embedding
})

(:VisualMotif {
    id: UUID,
    name: String,
    description: String,
    examples: [String],  // URIs to example images
    style_attributes: {
        composition: Enum['centered', 'rule_of_thirds', 'golden_ratio', 'asymmetric'],
        lighting: Enum['natural', 'studio', 'dramatic', 'soft'],
        color_treatment: Enum['vibrant', 'muted', 'monochrome', 'duotone'],
        texture: Enum['smooth', 'grainy', 'glossy', 'matte']
    },
    embedding_vector: [Float]
})

(:ImageStyle {
    id: UUID,
    name: String,
    description: String,
    prompt_modifier: String,  // appended to generation prompts
    negative_prompt: String,  // excluded from generation
    reference_images: [String],
    cfg_scale: Float,
    style_embedding: [Float]
})

// ═══════════════════════════════════════════════════════════════════════
// TONAL ONTOLOGY
// ═══════════════════════════════════════════════════════════════════════

(:VoiceProfile {
    id: UUID,
    name: String,
    formality: Float,  // 0.0 (casual) to 1.0 (formal)
    technicality: Float,  // 0.0 (accessible) to 1.0 (expert)
    warmth: Float,  // 0.0 (distant) to 1.0 (friendly)
    assertiveness: Float,  // 0.0 (tentative) to 1.0 (confident)
    humor: Float,  // 0.0 (serious) to 1.0 (playful)
    example_sentences: [String]
})

(:Vocabulary {
    id: UUID,
    category: Enum['preferred', 'avoid', 'product_specific', 'legal_required'],
    terms: [String],
    replacements: {String: String}  // avoid_term -> preferred_replacement
})

(:ToneGuideline {
    id: UUID,
    context: Enum['social_media', 'email', 'advertising', 'support', 'formal'],
    voice_profile_id: UUID,
    max_sentence_length: Integer,
    cta_style: Enum['direct', 'soft', 'question', 'urgency'],
    emoji_usage: Enum['none', 'minimal', 'moderate', 'heavy']
})

// ═══════════════════════════════════════════════════════════════════════
// THEMATIC ONTOLOGY
// ═══════════════════════════════════════════════════════════════════════

(:CoreValue {
    id: UUID,
    name: String,  // e.g., "Innovation", "Sustainability", "Trust"
    description: String,
    messaging_angles: [String],
    visual_representations: [String]  // motif references
})

(:KeyMessage {
    id: UUID,
    message: String,
    priority: Integer,  // 1 = highest
    target_audiences: [UUID],  // Persona references
    supporting_points: [String],
    call_to_action: String
})

(:Persona {
    id: UUID,
    name: String,
    demographics: {
        age_range: {min: Integer, max: Integer},
        gender: String,
        location: [String],
        income_bracket: String
    },
    psychographics: {
        values: [String],
        interests: [String],
        pain_points: [String],
        goals: [String]
    },
    preferred_channels: [String],
    content_preferences: {
        visual_style: String,
        tone: String,
        content_length: Enum['short', 'medium', 'long']
    }
})

(:Product {
    id: UUID,
    name: String,
    description: String,
    category: String,
    price_point: Float,
    key_features: [String],
    differentiators: [String],
    hero_images: [String],  // storage URIs
    embedding_vector: [Float]
})

(:Competitor {
    id: UUID,
    name: String,
    positioning: String,
    differentiation_points: [String],  // how we differ
    visual_style_notes: String,
    avoid_similarity: [String]  // elements to avoid mimicking
})

// ═══════════════════════════════════════════════════════════════════════
// CONSTRAINT ENTITIES
// ═══════════════════════════════════════════════════════════════════════

(:Constraint {
    id: UUID,
    type: Enum['required', 'prohibited', 'conditional', 'preference'],
    scope: Enum['global', 'campaign', 'channel', 'persona'],
    description: String,
    priority: Integer,  // for conflict resolution
    created_by: UUID,
    created_at: DateTime,
    source: Enum['brand_guide', 'user_feedback', 'legal', 'performance']
})

(:ContentTemplate {
    id: UUID,
    name: String,  // e.g., "Problem-Solution", "Testimonial", "Product Launch"
    framework: Enum['aida', 'pas', 'hero_journey', 'comparison', 'storytelling'],
    structure: JSON,  // {sections: [{name, content_type, constraints}]}
    visual_layout: JSON,  // {regions: [{name, type, position, size}]}
    applicable_channels: [String]
})
```

### Relationship Types (Edges)

```cypher
// ═══════════════════════════════════════════════════════════════════════
// ORGANIZATIONAL RELATIONSHIPS
// ═══════════════════════════════════════════════════════════════════════

(:Tenant)-[:OWNS]->(:Brand)
(:Brand)-[:RUNS]->(:Campaign)
(:Campaign)-[:PRODUCES]->(:Asset)

// ═══════════════════════════════════════════════════════════════════════
// BRAND COMPOSITION RELATIONSHIPS
// ═══════════════════════════════════════════════════════════════════════

(:Brand)-[:HAS_PALETTE {priority: Integer}]->(:ColorPalette)
(:Brand)-[:HAS_TYPOGRAPHY {priority: Integer}]->(:Typography)
(:Brand)-[:HAS_LOGO {context: String}]->(:Logo)
(:Brand)-[:HAS_MOTIF {usage_frequency: Float}]->(:VisualMotif)
(:Brand)-[:HAS_STYLE {context: String}]->(:ImageStyle)
(:Brand)-[:HAS_VOICE]->(:VoiceProfile)
(:Brand)-[:HAS_VOCABULARY]->(:Vocabulary)
(:Brand)-[:EMBODIES]->(:CoreValue)
(:Brand)-[:TARGETS]->(:Persona)
(:Brand)-[:SELLS]->(:Product)
(:Brand)-[:COMPETES_WITH]->(:Competitor)

// ═══════════════════════════════════════════════════════════════════════
// CONSTRAINT RELATIONSHIPS
// ═══════════════════════════════════════════════════════════════════════

// Positive constraints (MUST use together)
(:Entity)-[:REQUIRES {
    strength: Float,  // 0.0 to 1.0
    context: String,
    reason: String
}]->(:Entity)

// Negative constraints (MUST NOT use together)
(:Entity)-[:PROHIBITS {
    strength: Float,
    context: String,
    reason: String
}]->(:Entity)

// Conditional constraints
(:Entity)-[:IMPLIES_WHEN {
    condition: String,  // Cypher expression
    then_requires: UUID,
    reason: String
}]->(:Entity)

// Preference relationships (soft constraints)
(:Entity)-[:PREFERS {
    weight: Float,
    context: String
}]->(:Entity)

// ═══════════════════════════════════════════════════════════════════════
// SEMANTIC SIMILARITY RELATIONSHIPS
// ═══════════════════════════════════════════════════════════════════════

(:Entity)-[:SIMILAR_TO {
    similarity_score: Float,  // cosine similarity
    modality: Enum['visual', 'semantic', 'tonal']
}]->(:Entity)

(:Entity)-[:DERIVED_FROM {
    derivation_type: Enum['inspired_by', 'variant_of', 'evolution_of'],
    created_at: DateTime
}]->(:Entity)

// ═══════════════════════════════════════════════════════════════════════
// PERFORMANCE RELATIONSHIPS (from feedback)
// ═══════════════════════════════════════════════════════════════════════

(:Asset)-[:PERFORMED_WITH {
    metric: Enum['ctr', 'engagement', 'conversion', 'brand_recall'],
    value: Float,
    measured_at: DateTime,
    sample_size: Integer
}]->(:Persona)

(:Entity)-[:CONTRIBUTED_TO {
    asset_id: UUID,
    contribution_score: Float,  // attribution weight
    generation_step: Enum['retrieval', 'reasoning', 'generation']
}]->(:Asset)
```

---

## Ontology Definitions

### Visual Ontology Schema

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           VISUAL ONTOLOGY                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│    ┌──────────────────────────────────────────────────────────────────┐     │
│    │                         Brand                                     │     │
│    │                           │                                       │     │
│    │     ┌─────────────────────┼─────────────────────┐                │     │
│    │     │                     │                     │                │     │
│    │     ▼                     ▼                     ▼                │     │
│    │ ┌────────┐          ┌──────────┐          ┌─────────┐           │     │
│    │ │ Color  │          │Typography│          │  Logo   │           │     │
│    │ │Palette │          │          │          │Variants │           │     │
│    │ └───┬────┘          └────┬─────┘          └────┬────┘           │     │
│    │     │                    │                     │                │     │
│    │     │    ┌───────────────┼───────────────┐     │                │     │
│    │     │    │               │               │     │                │     │
│    │     ▼    ▼               ▼               ▼     ▼                │     │
│    │   ┌────────────────────────────────────────────────┐            │     │
│    │   │              Visual Motif                       │            │     │
│    │   │  (composition, lighting, color treatment)       │            │     │
│    │   └─────────────────────┬──────────────────────────┘            │     │
│    │                         │                                        │     │
│    │                         ▼                                        │     │
│    │               ┌─────────────────┐                               │     │
│    │               │   Image Style   │                               │     │
│    │               │  (prompt mods,  │                               │     │
│    │               │   references)   │                               │     │
│    │               └─────────────────┘                               │     │
│    └──────────────────────────────────────────────────────────────────┘     │
│                                                                              │
│  Constraints:                                                                │
│  • ColorPalette -[REQUIRES]-> Logo (background compatibility)               │
│  • Typography -[PROHIBITS]-> ImageStyle (text overlay conflicts)            │
│  • VisualMotif -[PREFERS]-> ColorPalette (aesthetic harmony)               │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Tonal Ontology Schema

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           TONAL ONTOLOGY                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│    ┌──────────────────────────────────────────────────────────────────┐     │
│    │                         Brand                                     │     │
│    │                           │                                       │     │
│    │                           ▼                                       │     │
│    │                   ┌──────────────┐                               │     │
│    │                   │ VoiceProfile │                               │     │
│    │                   │              │                               │     │
│    │                   │ formality    │                               │     │
│    │                   │ technicality │                               │     │
│    │                   │ warmth       │                               │     │
│    │                   │ assertiveness│                               │     │
│    │                   │ humor        │                               │     │
│    │                   └──────┬───────┘                               │     │
│    │                          │                                        │     │
│    │          ┌───────────────┼───────────────┐                       │     │
│    │          │               │               │                       │     │
│    │          ▼               ▼               ▼                       │     │
│    │    ┌──────────┐   ┌──────────┐   ┌──────────────┐              │     │
│    │    │Vocabulary│   │Vocabulary│   │ToneGuideline │              │     │
│    │    │(Preferred│   │ (Avoid)  │   │              │              │     │
│    │    │  Terms)  │   │          │   │ • context    │              │     │
│    │    └──────────┘   └──────────┘   │ • cta_style  │              │     │
│    │                                   │ • emoji      │              │     │
│    │                                   └──────────────┘              │     │
│    └──────────────────────────────────────────────────────────────────┘     │
│                                                                              │
│  Constraints:                                                                │
│  • VoiceProfile -[REQUIRES context='legal']-> ToneGuideline(formal)         │
│  • Vocabulary(avoid) -[PROHIBITS]-> Asset                                   │
│  • Persona -[PREFERS]-> ToneGuideline (audience alignment)                  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Thematic Ontology Schema

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          THEMATIC ONTOLOGY                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│                              ┌───────────┐                                  │
│                              │   Brand   │                                  │
│                              └─────┬─────┘                                  │
│                                    │                                         │
│           ┌────────────────────────┼────────────────────────┐               │
│           │                        │                        │               │
│           ▼                        ▼                        ▼               │
│     ┌───────────┐           ┌───────────┐           ┌───────────┐          │
│     │ CoreValue │           │  Product  │           │  Persona  │          │
│     │           │           │           │           │           │          │
│     │ • name    │           │ • name    │           │ • name    │          │
│     │ • desc    │           │ • features│           │ • demo    │          │
│     │ • angles  │           │ • differ  │           │ • psycho  │          │
│     └─────┬─────┘           └─────┬─────┘           └─────┬─────┘          │
│           │                       │                       │                 │
│           │        ┌──────────────┼──────────────┐        │                 │
│           │        │              │              │        │                 │
│           ▼        ▼              ▼              ▼        ▼                 │
│         ┌─────────────────────────────────────────────────────┐            │
│         │                    KeyMessage                        │            │
│         │                                                      │            │
│         │  • message                                           │            │
│         │  • priority                                          │            │
│         │  • supporting_points                                 │            │
│         │  • call_to_action                                    │            │
│         └───────────────────────┬─────────────────────────────┘            │
│                                 │                                           │
│                                 ▼                                           │
│                        ┌────────────────┐                                  │
│                        │ContentTemplate │                                  │
│                        │                │                                  │
│                        │ • framework    │                                  │
│                        │ • structure    │                                  │
│                        │ • layout       │                                  │
│                        └────────────────┘                                  │
│                                                                              │
│  Constraints:                                                                │
│  • Product -[REQUIRES]-> KeyMessage (positioning consistency)               │
│  • Persona -[PREFERS]-> ContentTemplate (audience fit)                      │
│  • Competitor -[PROHIBITS similarity]-> VisualMotif                         │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## GraphRAG Query Patterns

### Pattern 1: Context Retrieval for Generation

**Use Case**: Retrieve all relevant brand context for a content generation request.

```cypher
// Query: Generate product launch post for Product X targeting Persona Y
// Input: brand_id, product_id, persona_id, content_type

// Step 1: Get core brand constraints
MATCH (b:Brand {id: $brand_id})
OPTIONAL MATCH (b)-[:HAS_PALETTE]->(cp:ColorPalette)
OPTIONAL MATCH (b)-[:HAS_TYPOGRAPHY]->(t:Typography)
OPTIONAL MATCH (b)-[:HAS_LOGO]->(l:Logo)
OPTIONAL MATCH (b)-[:HAS_VOICE]->(v:VoiceProfile)
OPTIONAL MATCH (b)-[:HAS_VOCABULARY]->(vocab:Vocabulary)

// Step 2: Get product-specific context
MATCH (p:Product {id: $product_id})
OPTIONAL MATCH (p)<-[:SELLS]-(b)

// Step 3: Get persona-specific preferences
MATCH (persona:Persona {id: $persona_id})
OPTIONAL MATCH (persona)<-[:TARGETS]-(b)

// Step 4: Get relevant key messages
MATCH (km:KeyMessage)
WHERE persona.id IN km.target_audiences
   OR km.target_audiences IS NULL

// Step 5: Get applicable constraints
MATCH (c:Constraint)
WHERE c.scope IN ['global', $content_type]

// Step 6: Get performance data for similar content
OPTIONAL MATCH (past_asset:Asset)-[:PERFORMED_WITH {metric: 'engagement'}]->(persona)
WHERE past_asset.status = 'published'
WITH past_asset, persona
ORDER BY past_asset.generation_metadata.similarity_to_current DESC
LIMIT 5

RETURN {
    brand: {
        colors: collect(DISTINCT cp),
        typography: collect(DISTINCT t),
        logos: collect(DISTINCT l),
        voice: v,
        vocabulary: vocab
    },
    product: p,
    persona: persona,
    key_messages: collect(DISTINCT km),
    constraints: collect(DISTINCT c),
    high_performers: collect(DISTINCT past_asset)
}
```

### Pattern 2: Constraint Graph Traversal

**Use Case**: Find all positive and negative constraints for a given entity combination.

```cypher
// Query: What constraints apply when using Product X with Visual Style Y?
// Input: entity_ids (array of UUIDs)

// Find all direct constraints between selected entities
UNWIND $entity_ids AS source_id
UNWIND $entity_ids AS target_id
MATCH (source {id: source_id})
MATCH (target {id: target_id})
WHERE source_id <> target_id

// Collect REQUIRES relationships
OPTIONAL MATCH (source)-[req:REQUIRES]->(target)

// Collect PROHIBITS relationships  
OPTIONAL MATCH (source)-[pro:PROHIBITS]->(target)

// Collect PREFERS relationships
OPTIONAL MATCH (source)-[pref:PREFERS]->(target)

// Find transitive constraints (2-hop)
OPTIONAL MATCH (source)-[:REQUIRES]->(:Entity)-[trans_req:REQUIRES]->(target)
OPTIONAL MATCH (source)-[:PROHIBITS]->(:Entity)-[trans_pro:PROHIBITS]->(target)

RETURN {
    required: collect(DISTINCT {
        source: source.id,
        target: target.id,
        strength: req.strength,
        context: req.context,
        transitive: false
    }),
    prohibited: collect(DISTINCT {
        source: source.id,
        target: target.id,
        strength: pro.strength,
        context: pro.context,
        transitive: false
    }),
    preferred: collect(DISTINCT {
        source: source.id,
        target: target.id,
        weight: pref.weight,
        context: pref.context
    }),
    transitive_constraints: collect(DISTINCT {
        source: source.id,
        target: target.id,
        type: CASE WHEN trans_req IS NOT NULL THEN 'required' ELSE 'prohibited' END
    })
}
```

### Pattern 3: Hybrid Search (Vector + Graph)

**Use Case**: Find visually similar motifs that also satisfy brand constraints.

```cypher
// Query: Find visual motifs similar to reference image that work with our brand
// Input: query_embedding (vector), brand_id, similarity_threshold

// Step 1: Vector similarity search in pgvector (executed separately)
// SELECT id, embedding <=> $query_embedding AS distance
// FROM visual_motif_embeddings
// WHERE distance < $similarity_threshold
// ORDER BY distance LIMIT 20

// Step 2: Filter by graph constraints
UNWIND $candidate_motif_ids AS motif_id
MATCH (vm:VisualMotif {id: motif_id})
MATCH (b:Brand {id: $brand_id})

// Check positive constraints
OPTIONAL MATCH (b)-[:HAS_MOTIF]->(vm)
OPTIONAL MATCH (vm)-[:REQUIRES]->(required_entity)
WHERE NOT EXISTS((b)-[:HAS_*]->(required_entity))

// Check negative constraints
OPTIONAL MATCH (vm)-[:PROHIBITS]->(prohibited_entity)
WHERE EXISTS((b)-[:HAS_*]->(prohibited_entity))

// Filter: Keep motifs that satisfy constraints
WITH vm, 
     COUNT(required_entity) AS missing_requirements,
     COUNT(prohibited_entity) AS violations
WHERE missing_requirements = 0 AND violations = 0

// Rank by brand affinity
OPTIONAL MATCH (b)-[affinity:HAS_MOTIF]->(vm)
OPTIONAL MATCH (vm)-[perf:CONTRIBUTED_TO]->(a:Asset {status: 'published'})

RETURN vm, 
       affinity.usage_frequency AS brand_affinity,
       AVG(perf.contribution_score) AS avg_performance
ORDER BY brand_affinity DESC, avg_performance DESC
LIMIT 10
```

### Pattern 4: Feedback-Driven Graph Update

**Use Case**: Update graph based on user rejection of generated content.

```cypher
// Query: User rejected image because color combination was "too bright"
// Input: asset_id, feedback_type, feedback_attributes

// Step 1: Identify contributing entities
MATCH (a:Asset {id: $asset_id})
MATCH (entity)-[:CONTRIBUTED_TO]->(a)

// Step 2: Find color-related entities
WITH a, collect(entity) AS contributors
UNWIND contributors AS e
WHERE e:ColorPalette OR e:VisualMotif

// Step 3: Create or strengthen negative constraint
MATCH (e1:ColorPalette)-[:CONTRIBUTED_TO]->(a)
MATCH (e2:ColorPalette)-[:CONTRIBUTED_TO]->(a)
WHERE e1.id < e2.id  // Avoid duplicate pairs

MERGE (e1)-[p:PROHIBITS]->(e2)
ON CREATE SET 
    p.strength = 0.5,
    p.context = $feedback_attributes.context,
    p.reason = $feedback_attributes.user_comment,
    p.created_at = datetime()
ON MATCH SET
    p.strength = CASE 
        WHEN p.strength + 0.1 > 1.0 THEN 1.0 
        ELSE p.strength + 0.1 
    END,
    p.updated_at = datetime()

// Step 4: Create audit record
CREATE (f:FeedbackEvent {
    id: randomUUID(),
    asset_id: $asset_id,
    type: $feedback_type,
    attributes: $feedback_attributes,
    created_at: datetime(),
    resulting_mutations: collect(DISTINCT {
        source: e1.id, 
        target: e2.id, 
        relationship: 'PROHIBITS'
    })
})

RETURN f
```

---

## Hybrid Search Architecture

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        HYBRID SEARCH PIPELINE                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────┐                                                            │
│  │ User Query  │                                                            │
│  │ "Create ad  │                                                            │
│  │  for eco-   │                                                            │
│  │  friendly   │                                                            │
│  │  product"   │                                                            │
│  └──────┬──────┘                                                            │
│         │                                                                    │
│         ▼                                                                    │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                    QUERY UNDERSTANDING                                │   │
│  │                                                                       │   │
│  │  • Intent Classification (content_type: 'advertisement')             │   │
│  │  • Entity Extraction (product_attributes: ['eco-friendly'])          │   │
│  │  • Constraint Inference (persona: environmentally_conscious)         │   │
│  └──────────────────────────────┬───────────────────────────────────────┘   │
│                                 │                                            │
│              ┌──────────────────┴──────────────────┐                        │
│              │                                     │                        │
│              ▼                                     ▼                        │
│  ┌───────────────────────┐           ┌───────────────────────┐             │
│  │   VECTOR RETRIEVAL    │           │   GRAPH TRAVERSAL     │             │
│  │      (pgvector)       │           │      (Neo4j)          │             │
│  │                       │           │                       │             │
│  │  Query embedding:     │           │  MATCH (b:Brand)      │             │
│  │  [0.12, -0.34, ...]   │           │  -[:EMBODIES]->       │             │
│  │                       │           │  (v:CoreValue         │             │
│  │  Semantic search:     │           │   {name: 'Sustain'})  │             │
│  │  • Similar visuals    │           │                       │             │
│  │  • Related themes     │           │  Structured context:  │             │
│  │  • Past performers    │           │  • Brand constraints  │             │
│  │                       │           │  • Product relations  │             │
│  │  Results: 50 items    │           │  • Persona prefs     │             │
│  │  (unstructured)       │           │  Results: 20 items    │             │
│  │                       │           │  (structured)         │             │
│  └───────────┬───────────┘           └───────────┬───────────┘             │
│              │                                   │                          │
│              └─────────────┬─────────────────────┘                          │
│                            │                                                 │
│                            ▼                                                 │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                    RESULT FUSION                                      │   │
│  │                                                                       │   │
│  │  Reciprocal Rank Fusion (RRF):                                       │   │
│  │  score(d) = Σ 1/(k + rank_i(d))  where k = 60                        │   │
│  │                                                                       │   │
│  │  Additional weights:                                                  │   │
│  │  • Graph constraint satisfaction: +0.2 per satisfied constraint      │   │
│  │  • Negative constraint violation: -0.5 per violation                 │   │
│  │  • Performance history: +0.1 * past_engagement_score                 │   │
│  │                                                                       │   │
│  │  Re-ranked results: 15 items                                         │   │
│  └──────────────────────────────┬───────────────────────────────────────┘   │
│                                 │                                            │
│                                 ▼                                            │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                    CONTEXT ASSEMBLY                                   │   │
│  │                                                                       │   │
│  │  Final Context Package:                                               │   │
│  │  {                                                                    │   │
│  │    "brand_constraints": [...],                                        │   │
│  │    "visual_references": [...],                                        │   │
│  │    "tonal_guidelines": {...},                                         │   │
│  │    "key_messages": [...],                                             │   │
│  │    "negative_constraints": [...],                                     │   │
│  │    "high_performing_examples": [...]                                  │   │
│  │  }                                                                    │   │
│  │                                                                       │   │
│  │  Token budget allocation:                                             │   │
│  │  • Constraints: 500 tokens (critical)                                 │   │
│  │  • Visual refs: 300 tokens (embeddings)                               │   │
│  │  • Examples: 200 tokens (abbreviated)                                 │   │
│  │                                                                       │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Query Router Logic

```python
# Pseudocode for hybrid search routing

class GraphRAGQueryRouter:
    def __init__(self, neo4j_client, pgvector_client, embedding_model):
        self.graph = neo4j_client
        self.vector = pgvector_client
        self.embedder = embedding_model
    
    def retrieve(self, query: str, brand_id: str, context: GenerationContext) -> RetrievalResult:
        # Step 1: Query understanding
        parsed = self.parse_query(query)
        
        # Step 2: Parallel retrieval
        vector_results = asyncio.create_task(
            self.vector_search(
                query_embedding=self.embedder.encode(query),
                filters={"brand_id": brand_id},
                top_k=50
            )
        )
        
        graph_results = asyncio.create_task(
            self.graph_traversal(
                brand_id=brand_id,
                entities=parsed.extracted_entities,
                traversal_depth=3
            )
        )
        
        vector_items, graph_items = await asyncio.gather(vector_results, graph_results)
        
        # Step 3: Result fusion with constraint filtering
        fused = self.reciprocal_rank_fusion(vector_items, graph_items, k=60)
        
        # Step 4: Constraint validation
        validated = self.validate_constraints(fused, brand_id)
        
        # Step 5: Context assembly with token budgeting
        context_package = self.assemble_context(
            validated,
            token_budget=1000,
            priority_order=['constraints', 'visual_refs', 'tone', 'examples']
        )
        
        return context_package
    
    def reciprocal_rank_fusion(self, vector_items, graph_items, k=60):
        """Combine rankings using RRF formula"""
        scores = defaultdict(float)
        
        for rank, item in enumerate(vector_items):
            scores[item.id] += 1 / (k + rank + 1)
        
        for rank, item in enumerate(graph_items):
            scores[item.id] += 1 / (k + rank + 1)
            # Boost for graph-native items (they have richer structure)
            scores[item.id] += 0.1
        
        return sorted(scores.items(), key=lambda x: -x[1])
```

---

## Graph Update Mechanisms

### Update Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        GRAPH UPDATE PIPELINE                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐          │
│  │  User Feedback  │    │  Performance    │    │  Brand Guide    │          │
│  │    (Explicit)   │    │   Data Import   │    │    Upload       │          │
│  └────────┬────────┘    └────────┬────────┘    └────────┬────────┘          │
│           │                      │                      │                    │
│           └──────────────────────┼──────────────────────┘                    │
│                                  │                                           │
│                                  ▼                                           │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                    SIGNAL CLASSIFIER                                  │   │
│  │                                                                       │   │
│  │  Input: Raw feedback/data                                            │   │
│  │  Output: Classified mutation proposals                               │   │
│  │                                                                       │   │
│  │  Classifications:                                                     │   │
│  │  • NODE_CREATE (new entity detected)                                 │   │
│  │  • NODE_UPDATE (attribute change)                                    │   │
│  │  • EDGE_CREATE (new relationship)                                    │   │
│  │  • EDGE_UPDATE (weight/attribute change)                             │   │
│  │  • EDGE_DELETE (relationship removal)                                │   │
│  │  • CONSTRAINT_ADD (new restriction)                                  │   │
│  │                                                                       │   │
│  │  Confidence thresholds:                                              │   │
│  │  • Auto-apply: confidence >= 0.95                                    │   │
│  │  • Human review: 0.7 <= confidence < 0.95                            │   │
│  │  • Discard: confidence < 0.7                                         │   │
│  └──────────────────────────────┬───────────────────────────────────────┘   │
│                                 │                                            │
│              ┌──────────────────┴──────────────────┐                        │
│              │                                     │                        │
│              ▼                                     ▼                        │
│  ┌───────────────────────┐           ┌───────────────────────┐             │
│  │   AUTO-APPLY PATH     │           │   HUMAN REVIEW PATH   │             │
│  │   (High Confidence)   │           │   (Medium Confidence) │             │
│  └───────────┬───────────┘           └───────────┬───────────┘             │
│              │                                   │                          │
│              │                                   ▼                          │
│              │                       ┌───────────────────────┐             │
│              │                       │   Review Dashboard    │             │
│              │                       │                       │             │
│              │                       │   • Show proposed     │             │
│              │                       │     mutations         │             │
│              │                       │   • Impact preview    │             │
│              │                       │   • Approve/Reject    │             │
│              │                       └───────────┬───────────┘             │
│              │                                   │                          │
│              └─────────────┬─────────────────────┘                          │
│                            │                                                 │
│                            ▼                                                 │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                    CONFLICT DETECTOR                                  │   │
│  │                                                                       │   │
│  │  Check for:                                                          │   │
│  │  • Schema violations                                                 │   │
│  │  • Circular constraint dependencies                                  │   │
│  │  • Contradictory constraints (A REQUIRES B, A PROHIBITS B)          │   │
│  │  • Concurrent modifications (CRDT resolution)                        │   │
│  │                                                                       │   │
│  │  Resolution strategies:                                              │   │
│  │  • Priority-based (higher priority wins)                             │   │
│  │  • Timestamp-based (last write wins)                                 │   │
│  │  • Manual escalation (for critical conflicts)                        │   │
│  └──────────────────────────────┬───────────────────────────────────────┘   │
│                                 │                                            │
│                                 ▼                                            │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                    VERSION MANAGER                                    │   │
│  │                                                                       │   │
│  │  • Increment graph version                                           │   │
│  │  • Create snapshot for rollback                                      │   │
│  │  • Update version pointers                                           │   │
│  │  • Emit cache invalidation events                                    │   │
│  │                                                                       │   │
│  │  Versioning schema:                                                  │   │
│  │  brand:{brand_id}:version:{version_num}                              │   │
│  │                                                                       │   │
│  └──────────────────────────────┬───────────────────────────────────────┘   │
│                                 │                                            │
│                                 ▼                                            │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                    GRAPH COMMIT                                       │   │
│  │                                                                       │   │
│  │  Transaction:                                                        │   │
│  │  BEGIN                                                               │   │
│  │    APPLY mutations                                                   │   │
│  │    UPDATE version metadata                                           │   │
│  │    CREATE audit log entry                                            │   │
│  │  COMMIT                                                              │   │
│  │                                                                       │   │
│  │  Post-commit:                                                        │   │
│  │  • Invalidate Redis cache (affected subgraphs)                       │   │
│  │  • Emit Kafka event (graph.updated)                                  │   │
│  │  • Update embedding indices (if node attributes changed)             │   │
│  │                                                                       │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Conflict Resolution Algorithm

```python
# Pseudocode for CRDT-inspired conflict resolution

class GraphConflictResolver:
    def resolve(self, proposed_mutations: List[Mutation], current_graph_state: GraphSnapshot) -> List[Mutation]:
        validated_mutations = []
        conflicts = []
        
        for mutation in proposed_mutations:
            # Check for schema violations
            if not self.validate_schema(mutation, current_graph_state):
                conflicts.append(Conflict(
                    type='SCHEMA_VIOLATION',
                    mutation=mutation,
                    resolution='REJECT'
                ))
                continue
            
            # Check for contradictions
            contradiction = self.find_contradiction(mutation, current_graph_state)
            if contradiction:
                resolution = self.resolve_contradiction(mutation, contradiction)
                if resolution.action == 'REJECT':
                    conflicts.append(resolution)
                    continue
                elif resolution.action == 'MERGE':
                    mutation = resolution.merged_mutation
            
            # Check for circular dependencies
            if mutation.type in ['EDGE_CREATE', 'CONSTRAINT_ADD']:
                if self.creates_cycle(mutation, current_graph_state):
                    conflicts.append(Conflict(
                        type='CIRCULAR_DEPENDENCY',
                        mutation=mutation,
                        resolution='REJECT'
                    ))
                    continue
            
            validated_mutations.append(mutation)
        
        return validated_mutations, conflicts
    
    def resolve_contradiction(self, new_mutation: Mutation, existing: Constraint) -> Resolution:
        """
        Resolution priority:
        1. Legal/compliance constraints always win
        2. Higher priority number wins
        3. More recent timestamp wins (for equal priority)
        4. Escalate to human review (if both critical)
        """
        if existing.source == 'legal':
            return Resolution(action='REJECT', reason='Legal constraint cannot be overridden')
        
        if new_mutation.priority > existing.priority:
            return Resolution(
                action='REPLACE',
                merged_mutation=new_mutation,
                side_effect=DeleteMutation(existing.id)
            )
        elif new_mutation.priority == existing.priority:
            if new_mutation.timestamp > existing.timestamp:
                return Resolution(action='REPLACE', merged_mutation=new_mutation)
            else:
                return Resolution(action='REJECT', reason='Existing constraint has precedence')
        else:
            return Resolution(action='REJECT', reason='Lower priority')
```

---

## Multi-Tenant Isolation

### Isolation Strategy

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        MULTI-TENANT DATA ISOLATION                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                     REQUEST FLOW                                     │    │
│  │                                                                      │    │
│  │  Request → API Gateway → JWT Validation → Tenant Context Injection  │    │
│  │                              │                                       │    │
│  │                              ▼                                       │    │
│  │                     ┌──────────────────┐                            │    │
│  │                     │ Tenant Context   │                            │    │
│  │                     │ {                │                            │    │
│  │                     │   tenant_id: X,  │                            │    │
│  │                     │   brand_ids: [], │                            │    │
│  │                     │   permissions: {}│                            │    │
│  │                     │ }                │                            │    │
│  │                     └────────┬─────────┘                            │    │
│  │                              │                                       │    │
│  │                              ▼                                       │    │
│  │  All downstream queries automatically scoped to tenant_id           │    │
│  │                                                                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                     NEO4J ISOLATION                                  │    │
│  │                                                                      │    │
│  │  Option A: Separate Databases (Enterprise Only)                     │    │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐                    │    │
│  │  │ tenant_001 │  │ tenant_002 │  │ tenant_003 │                    │    │
│  │  │ (database) │  │ (database) │  │ (database) │                    │    │
│  │  └────────────┘  └────────────┘  └────────────┘                    │    │
│  │  Pros: Complete isolation, independent scaling                      │    │
│  │  Cons: Higher cost, more operational complexity                     │    │
│  │                                                                      │    │
│  │  Option B: Label-Based Isolation (Recommended for most cases)       │    │
│  │  ┌──────────────────────────────────────────────────────────────┐  │    │
│  │  │                    Shared Database                            │  │    │
│  │  │                                                               │  │    │
│  │  │  All nodes: (:Entity {tenant_id: 'X', ...})                  │  │    │
│  │  │  Query prefix: MATCH (n {tenant_id: $tenant_id})             │  │    │
│  │  │  Index: CREATE INDEX FOR (n:Entity) ON (n.tenant_id)         │  │    │
│  │  │                                                               │  │    │
│  │  └──────────────────────────────────────────────────────────────┘  │    │
│  │  Pros: Cost-effective, simpler operations                          │    │
│  │  Cons: Query discipline required, shared resources                  │    │
│  │                                                                      │    │
│  │  Selected: Option B with Row-Level Security (RLS) wrapper          │    │
│  │                                                                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                     PGVECTOR ISOLATION                               │    │
│  │                                                                      │    │
│  │  Table structure:                                                   │    │
│  │  ┌────────────────────────────────────────────────────────────┐    │    │
│  │  │ embeddings                                                  │    │    │
│  │  │ ──────────────────────────────────────────────────────────  │    │    │
│  │  │ id          UUID PRIMARY KEY                                │    │    │
│  │  │ tenant_id   UUID NOT NULL  ← Partition key                  │    │    │
│  │  │ entity_type VARCHAR(50)                                     │    │    │
│  │  │ entity_id   UUID                                            │    │    │
│  │  │ embedding   VECTOR(1536)                                    │    │    │
│  │  │ metadata    JSONB                                           │    │    │
│  │  │                                                             │    │    │
│  │  │ PARTITION BY LIST (tenant_id)  ← Physical isolation         │    │    │
│  │  └────────────────────────────────────────────────────────────┘    │    │
│  │                                                                      │    │
│  │  Each tenant gets own partition → isolated HNSW index              │    │
│  │                                                                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                     CACHE ISOLATION                                  │    │
│  │                                                                      │    │
│  │  Redis key namespacing:                                             │    │
│  │                                                                      │    │
│  │  tenant:{tenant_id}:brand:{brand_id}:graph:v{version}              │    │
│  │  tenant:{tenant_id}:generation:{request_id}:result                 │    │
│  │  tenant:{tenant_id}:session:{session_id}                           │    │
│  │                                                                      │    │
│  │  Per-tenant rate limits:                                            │    │
│  │  rate_limit:tenant:{tenant_id}:api_calls                           │    │
│  │  rate_limit:tenant:{tenant_id}:generations                         │    │
│  │                                                                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Query Wrapper for Tenant Isolation

```python
# All graph queries go through this wrapper

class TenantScopedGraphClient:
    def __init__(self, neo4j_driver, tenant_context: TenantContext):
        self.driver = neo4j_driver
        self.tenant_id = tenant_context.tenant_id
    
    def query(self, cypher: str, params: dict) -> Result:
        """
        Automatically inject tenant_id into all queries.
        Uses query rewriting for defense-in-depth.
        """
        # Validate query doesn't bypass tenant isolation
        self._validate_query_safety(cypher)
        
        # Inject tenant_id parameter
        scoped_params = {**params, 'tenant_id': self.tenant_id}
        
        # Prepend tenant filter to query
        scoped_cypher = self._inject_tenant_scope(cypher)
        
        with self.driver.session() as session:
            return session.run(scoped_cypher, scoped_params)
    
    def _inject_tenant_scope(self, cypher: str) -> str:
        """
        Rewrite query to ensure tenant isolation.
        Example: MATCH (b:Brand) → MATCH (b:Brand {tenant_id: $tenant_id})
        """
        # Use AST parsing for production (simplified here)
        if 'tenant_id' not in cypher:
            # Add tenant filter to first MATCH clause
            cypher = cypher.replace(
                'MATCH (', 
                'MATCH (n {tenant_id: $tenant_id}) WITH n MATCH ('
            )
        return cypher
    
    def _validate_query_safety(self, cypher: str):
        """
        Block queries that could access other tenants' data.
        """
        dangerous_patterns = [
            'DETACH DELETE',  # Mass deletion
            'REMOVE n.tenant_id',  # Tenant ID tampering
            'SET n.tenant_id',  # Cross-tenant data movement
        ]
        for pattern in dangerous_patterns:
            if pattern.lower() in cypher.lower():
                raise SecurityException(f"Blocked dangerous query pattern: {pattern}")
```

---

## Performance Optimization

### Query Performance Targets

| Query Type | Target P95 | Optimization Strategy |
|------------|------------|----------------------|
| Single-hop traversal | <20ms | Index on tenant_id + node labels |
| Multi-hop (3 hops) | <100ms | Materialized views for common patterns |
| Hybrid search | <150ms | Parallel vector + graph queries |
| Constraint validation | <50ms | Cached constraint subgraphs |
| Graph update | <200ms | Async with optimistic locking |

### Index Strategy

```cypher
// Primary indices
CREATE INDEX tenant_brand FOR (b:Brand) ON (b.tenant_id, b.id);
CREATE INDEX tenant_asset FOR (a:Asset) ON (a.tenant_id, a.created_at);
CREATE INDEX constraint_scope FOR (c:Constraint) ON (c.scope, c.type);

// Full-text search
CREATE FULLTEXT INDEX brand_search FOR (b:Brand|p:Product|km:KeyMessage) 
ON EACH [b.name, b.description, p.name, km.message];

// Relationship indices (Neo4j 5.x+)
CREATE INDEX rel_requires FOR ()-[r:REQUIRES]->() ON (r.strength);
CREATE INDEX rel_prohibits FOR ()-[r:PROHIBITS]->() ON (r.strength);

// Vector index (pgvector)
CREATE INDEX embedding_hnsw ON embeddings 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```

### Caching Strategy

```
┌─────────────────────────────────────────────────────────────────┐
│                    GRAPH CACHING LAYERS                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  L1: In-Memory (per-pod)                                        │
│  ├── Hot brand configurations (last 1 hour)                     │
│  ├── Compiled query plans                                       │
│  └── TTL: Pod lifetime | Size: 100MB per pod                    │
│                                                                  │
│  L2: Redis Cluster                                              │
│  ├── Full brand subgraphs (serialized)                         │
│  ├── Constraint graphs (pre-computed)                          │
│  ├── Recent query results                                       │
│  └── TTL: 1 hour (invalidation on update) | Size: 10GB cluster  │
│                                                                  │
│  L3: Neo4j Query Cache                                          │
│  ├── Query result cache (built-in)                              │
│  └── Page cache (configured: 4GB)                               │
│                                                                  │
│  Invalidation:                                                   │
│  • Graph mutation → Publish to Redis Pub/Sub                    │
│  • Subscribers invalidate affected keys                         │
│  • Version bump forces cache miss on stale reads                │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Next Document

Continue to **[03-image-generation-pipeline.md](./03-image-generation-pipeline.md)** for the reasoning-augmented image generation architecture.

# GraphRAG-Guided Compositional Image Generation with Continuous Preference Learning

## System Architecture Documentation

---

## 1. Executive Summary

This capstone research project implements an advanced brand-aligned content generation system that leverages **Graph Retrieval-Augmented Generation (GraphRAG)** for intelligent, compositional image generation with continuous preference learning.

### Key Innovations

1. **Scene Decomposition** - Transforms natural language prompts into structured scene graphs
2. **Constraint Resolution** - Multi-hop graph traversal for brand-specific rules
3. **Character Consistency** - Identity preservation across generations
4. **Continuous Learning** - Adapts to user preferences over time
5. **Compositional Generation** - Element-level control over image composition

---

## 2. System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           USER INTERFACE (React)                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │  Onboarding │  │   Generate  │  │   Results   │  │ Element Feedback    │ │
│  │    Page     │  │    Page     │  │    Page     │  │    Component        │ │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘ │
└─────────┼────────────────┼────────────────┼───────────────────-┼────────────┘
          │                │                │                    │
          ▼                ▼                ▼                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         FastAPI BACKEND                                      │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                      ADVANCED GENERATION PIPELINE                       │ │
│  │                                                                         │ │
│  │  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                 │ │
│  │  │   Scene     │───▶│ Constraint  │───▶│   Prompt    │                 │ │
│  │  │Decomposition│    │ Resolution  │    │ Compilation │                 │ │
│  │  └─────────────┘    └─────────────┘    └──────┬──────┘                 │ │
│  │         │                  │                  │                         │ │
│  │         ▼                  ▼                  ▼                         │ │
│  │  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                 │ │
│  │  │  Character  │    │  Feedback   │    │  Evaluation │                 │ │
│  │  │ Consistency │    │  Learning   │    │  Framework  │                 │ │
│  │  └─────────────┘    └─────────────┘    └─────────────┘                 │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                    │                                         │
│                                    ▼                                         │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                      EXTERNAL SERVICES                                  │ │
│  │  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                 │ │
│  │  │  Groq LLM   │    │HuggingFace  │    │  Neo4j Aura │                 │ │
│  │  │(llama-3.3)  │    │   SDXL      │    │ (GraphRAG)  │                 │ │
│  │  └─────────────┘    └─────────────┘    └─────────────┘                 │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Module Specifications

### 3.1 Scene Decomposition Engine

**File:** `backend/app/generation/scene_decomposition.py`

**Purpose:** Transforms natural language prompts into structured scene graphs that can be reasoned about.

**Key Classes:**
- `ElementType` - Enum for element categories (BACKGROUND, SUBJECT, TEXT_AREA, etc.)
- `SceneElement` - Individual scene component with spatial and style attributes
- `SceneGraph` - Complete scene representation with relationships
- `SceneDecompositionEngine` - Main decomposition logic

**Example Usage:**
```python
from app.generation.scene_decomposition import SceneDecompositionEngine

engine = SceneDecompositionEngine(groq_api_key="your-key")
scene_graph = await engine.decompose_prompt(
    prompt="Modern tech product on wooden desk with natural lighting",
    aspect_ratio="16:9"
)

# Access elements
for element in scene_graph.elements:
    print(f"{element.semantic_label}: {element.type.value}")
```

**Output Structure:**
```json
{
  "id": "scene_abc123",
  "original_prompt": "...",
  "elements": [
    {
      "id": "elem_1",
      "type": "BACKGROUND",
      "semantic_label": "wooden desk surface",
      "spatial_position": "full_frame",
      "z_index": 0
    },
    {
      "id": "elem_2",
      "type": "SUBJECT",
      "semantic_label": "tech product",
      "spatial_position": "center",
      "z_index": 1,
      "importance": 0.9
    }
  ],
  "layout_type": "PRODUCT_SHOWCASE",
  "aspect_ratio": "16:9"
}
```

---

### 3.2 Constraint Resolution System

**File:** `backend/app/generation/constraint_resolver.py`

**Purpose:** Gathers brand constraints from Neo4j graph and resolves conflicts using priority-based rules.

**Constraint Types:**
- `MUST_INCLUDE` - Required elements (highest priority)
- `MUST_AVOID` - Prohibited elements (high priority)
- `PREFER` - Soft positive preference
- `DISCOURAGE` - Soft negative preference
- `RANGE` - Numeric range constraints

**Resolution Algorithm:**
1. Query hard constraints from brand node
2. Gather learned preferences from feedback history
3. Collect negative patterns to avoid
4. Detect conflicts between constraints
5. Resolve conflicts using priority and strength

**Example:**
```python
from app.generation.constraint_resolver import ConstraintResolutionEngine

resolver = ConstraintResolutionEngine(neo4j_client)
constraints = await resolver.resolve_for_generation(
    brand_id="brand_123",
    scene_graph=scene_graph,
    use_learned=True
)

# Access resolved constraints
print(f"Active constraints: {len(constraints.active_constraints)}")
print(f"Negative patterns: {[p.pattern for p in constraints.negative_patterns]}")
```

---

### 3.3 Character Consistency Module

**File:** `backend/app/generation/character_consistency.py`

**Purpose:** Ensures faces and character identities remain consistent across edits and variations.

**How It Works:**
1. Extract face regions from reference image
2. Generate face embeddings (128-dimensional vectors)
3. Store character identity in graph database
4. On new generation, inject consistency prompts
5. Verify output matches reference using cosine similarity

**Key Methods:**
- `register_character()` - Create new character from reference image
- `generate_consistency_prompt()` - Get prompts to maintain identity
- `verify_identity()` - Check if output matches character

**Example:**
```python
from app.generation.character_consistency import CharacterConsistencyEngine

engine = CharacterConsistencyEngine(neo4j_client)

# Register character
character = await engine.register_character(
    brand_id="brand_123",
    reference_image_url="https://...",
    name="Brand Mascot"
)

# Generate with consistency
consistency_prompt = await engine.generate_consistency_prompt(character.id)
# Add to main prompt: "brand mascot, same face as reference..."
```

---

### 3.4 Feedback Learning System

**File:** `backend/app/generation/feedback_learning.py`

**Purpose:** Learns user preferences from feedback at multiple granularities.

**Feedback Levels:**
1. **Whole Image** - Overall like/dislike
2. **Element Level** - Feedback on specific scene elements
3. **Attribute Level** - Fine-grained feedback on specific attributes

**Learning Process:**
```
User Feedback → Aggregate Similar Feedback → Extract Patterns → 
Update Preferences → Influence Future Generations
```

**Preference Confidence:**
- Calculated from consistency ratio and sample count
- High confidence (≥0.7) = strong signal
- Medium confidence (0.5-0.7) = moderate signal
- Low confidence (<0.5) = weak signal, needs more data

**Example:**
```python
from app.generation.feedback_learning import FeedbackLearningEngine, FeedbackType

engine = FeedbackLearningEngine(neo4j_client)

# Record feedback
await engine.record_feedback(
    generation_id="gen_123",
    brand_id="brand_123",
    feedback_type=FeedbackType.ELEMENT,
    is_positive=True,
    element_id="background",
    attribute_key="lighting",
    attribute_value="natural"
)

# Get learned preferences
preferences = await engine.aggregate_preferences("brand_123")
# Returns: [("LIGHTING", "natural", 0.85), ...]
```

---

### 3.5 Prompt Compilation Engine

**File:** `backend/app/generation/prompt_compiler.py`

**Purpose:** Transforms scene graphs and constraints into optimized prompts for SDXL.

**Compilation Pipeline:**
1. Convert scene elements to descriptive text
2. Inject constraint requirements
3. Add learned preferences
4. Apply style modifiers
5. Build negative prompt from avoidances
6. Add quality boosters

**Prompt Styles:**
- `DESCRIPTIVE` - Natural language description
- `TAGS` - Comma-separated keywords
- `HYBRID` - Combination (recommended)

**Example Output:**
```json
{
  "positive_prompt": "professional photography, modern tech product centered on wooden desk surface, natural soft lighting, minimalist clean composition, high quality, detailed, 8k",
  "negative_prompt": "cluttered background, harsh shadows, low quality, blurry, amateur, stock photo watermark",
  "style_modifiers": ["professional photography", "minimalist"],
  "quality_modifiers": ["high quality", "detailed", "8k"]
}
```

---

### 3.6 Evaluation Framework

**File:** `backend/app/generation/evaluation_framework.py`

**Purpose:** Provides comprehensive metrics for measuring system effectiveness.

**Metric Categories:**

| Category | Metrics | Weight |
|----------|---------|--------|
| Brand Alignment | Color alignment, Style consistency | 25% |
| Constraint Satisfaction | Adherence rate, Conflict resolution | 20% |
| User Satisfaction | Feedback ratio, Acceptance rate | 30% |
| Learning Effectiveness | Confidence growth, Pattern detection | 15% |
| System Performance | Generation time, Error rate | 10% |

**Report Generation:**
```python
from app.generation.evaluation_framework import EvaluationFramework

framework = EvaluationFramework(neo4j_client)
report = await framework.generate_report("brand_123", days=7)

print(f"Overall Score: {report.get_overall_score():.2%}")
print(f"Recommendations: {report.recommendations}")
```

---

## 4. API Reference

### Advanced Generation Endpoints

#### POST `/api/advanced/generate`
Full GraphRAG-guided generation with all features enabled.

**Request Body:**
```json
{
  "brand_id": "string",
  "prompt": "string",
  "type": "image|text|both",
  "use_scene_decomposition": true,
  "use_constraint_resolution": true,
  "use_learned_preferences": true,
  "character_id": "optional-string",
  "preserve_identity": false
}
```

**Response:**
```json
{
  "generation_id": "gen_xxx",
  "image_url": "https://...",
  "headline": "Generated headline",
  "brand_score": 0.85,
  "scene_graph": {...},
  "constraints_applied": [...],
  "compiled_prompt": {...}
}
```

---

#### POST `/api/advanced/feedback`
Record user feedback for continuous learning.

**Request Body:**
```json
{
  "generation_id": "string",
  "brand_id": "string",
  "feedback_type": "WHOLE|ELEMENT|ATTRIBUTE",
  "is_positive": true,
  "element_id": "optional",
  "attribute_key": "optional",
  "attribute_value": "optional"
}
```

---

#### GET `/api/advanced/preferences/{brand_id}`
Retrieve learned preferences for a brand.

---

#### GET `/api/advanced/evaluation-report/{brand_id}`
Generate comprehensive evaluation report.

**Query Parameters:**
- `days` - Number of days to analyze (default: 7)

---

#### POST `/api/advanced/analyze-scene`
Analyze a prompt and return its scene graph.

---

## 5. Database Schema

### Node Types

```cypher
// Brand node with constraint relationships
(:Brand {id, name, description, created_at})
  -[:HAS_CONSTRAINT]->(:Constraint {type, strength, target_type, target_value})
  -[:HAS_LEARNED_PREFERENCE]->(:LearnedPreference {attribute_type, value, confidence})
  -[:AVOID_PATTERN]->(:NegativePattern {pattern, frequency, first_seen})

// Generation with scene graph
(:Generation {id, prompt, compiled_prompt, image_url, brand_score})
  -[:HAS_SCENE_GRAPH]->(:SceneGraph {layout_type, aspect_ratio, overall_mood})
  -[:CONTAINS_ELEMENT]->(:SceneElement {type, semantic_label, spatial_position})

// Character for consistency
(:Character {id, name, reference_image_url, description})
  -[:HAS_FACE_EMBEDDING]->(:FaceEmbedding {embedding, quality_score})

// Feedback for learning
(:Feedback {id, type, is_positive, element_id, attribute_key, attribute_value})
  -[:FEEDBACK_FOR]->(:Generation)
```

---

## 6. Frontend Components

### ElementFeedback Component

**File:** `frontend/src/components/ElementFeedback.jsx`

Interactive feedback component with three modes:
- Whole image feedback
- Element-level selection
- Attribute-specific ratings

### ResultsAdvanced Page

**File:** `frontend/src/pages/ResultsAdvanced.jsx`

Enhanced results view with:
- Three tabs: Result, Analysis, Feedback
- Scene graph visualization
- Constraint display
- Learning progress indicators

---

## 7. Getting Started

### Prerequisites

1. Python 3.10+
2. Node.js 18+
3. Neo4j Aura account
4. Groq API key
5. HuggingFace API key

### Backend Setup

```bash
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt

# Set environment variables
set GROQ_API_KEY=your-key
set HF_TOKEN=your-key
set NEO4J_URI=neo4j+s://xxx.databases.neo4j.io
set NEO4J_USER=neo4j
set NEO4J_PASSWORD=xxx

# Run
uvicorn app.main:app --reload --port 8000
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

### Initialize Database

```bash
# Run schema creation
cypher-shell -a $NEO4J_URI -u $NEO4J_USER -p $NEO4J_PASSWORD < backend/app/database/enhanced_schema.cypher
```

---

## 8. Research Contributions

### Novel Contributions

1. **GraphRAG for Image Generation** - First system to apply GraphRAG principles to compositional image generation

2. **Scene Graph Decomposition** - Novel approach to breaking prompts into manipulable scene elements

3. **Continuous Preference Learning** - Real-time adaptation to user feedback without retraining

4. **Character Consistency via Graph** - Identity preservation through embedding storage in knowledge graph

### Evaluation Metrics

The system is evaluated on:
- Brand alignment accuracy
- User satisfaction scores
- Learning convergence rate
- Generation quality (FID, CLIP scores)
- System responsiveness

---

## 9. Future Directions

1. **Multi-modal Feedback** - Voice and gesture-based feedback
2. **Collaborative Learning** - Share preferences across similar brands
3. **Real-time Preview** - Live constraint visualization during prompt composition
4. **A/B Testing Framework** - Built-in experimentation for preference learning
5. **Export to Brand Guidelines** - Generate PDF guidelines from learned preferences

---

## 10. Troubleshooting

### Common Issues

**Neo4j Connection Failed**
```
Solution: Check NEO4J_URI, verify credentials, ensure IP whitelist
```

**LLM Rate Limiting**
```
Solution: Implement exponential backoff, use fallback decomposition
```

**SDXL Timeout**
```
Solution: Reduce image resolution, simplify prompt, check HF quota
```

---

## Appendix A: Complete File Structure

```
backend/
├── app/
│   ├── database/
│   │   ├── neo4j_client.py
│   │   ├── schema.cypher
│   │   └── enhanced_schema.cypher      # NEW
│   ├── generation/
│   │   ├── image_generator.py
│   │   ├── text_generator.py
│   │   ├── scene_decomposition.py      # NEW
│   │   ├── constraint_resolver.py      # NEW
│   │   ├── character_consistency.py    # NEW
│   │   ├── feedback_learning.py        # NEW
│   │   ├── prompt_compiler.py          # NEW
│   │   └── evaluation_framework.py     # NEW
│   ├── routers/
│   │   ├── brands.py
│   │   ├── generation.py
│   │   ├── products.py
│   │   └── advanced_generation.py      # NEW
│   └── main.py

frontend/
├── src/
│   ├── components/
│   │   ├── Layout.jsx
│   │   └── ElementFeedback.jsx         # NEW
│   └── pages/
│       ├── Home.jsx
│       ├── Generate.jsx
│       ├── Results.jsx
│       └── ResultsAdvanced.jsx         # NEW
```

---

**Document Version:** 1.0  
**Last Updated:** June 2025  
**Author:** Capstone Research Team

# Advanced Generation API Documentation

## Overview

The Advanced Generation API provides endpoints for GraphRAG-guided brand-aligned content generation with continuous preference learning capabilities.

**Base URL:** `http://localhost:8000/api`

---

## Authentication

Currently, the API does not require authentication. In production, implement JWT or API key authentication.

---

## Endpoints

### 1. Advanced Generate

Generate brand-aligned content using the full GraphRAG pipeline.

**Endpoint:** `POST /api/advanced/generate`

**Request Headers:**
```
Content-Type: application/json
```

**Request Body:**
```json
{
  "brand_id": "brand_abc123",
  "prompt": "Modern laptop on minimalist desk with coffee cup",
  "type": "both",
  "aspect_ratio": "16:9",
  "layout_type": "PRODUCT_SHOWCASE",
  "scene_elements": [
    {
      "type": "SUBJECT",
      "semantic_label": "laptop",
      "spatial_position": "center",
      "importance": 0.9
    }
  ],
  "text_layout": "bottom_centered",
  "include_text_overlay": true,
  "product_ids": ["prod_123"],
  "character_id": null,
  "preserve_identity": false,
  "use_scene_decomposition": true,
  "use_constraint_resolution": true,
  "use_learned_preferences": true,
  "quality_level": "high_quality"
}
```

**Parameters:**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| brand_id | string | Yes | - | Brand identifier |
| prompt | string | Yes | - | Generation prompt |
| type | enum | No | "both" | "image", "text", or "both" |
| aspect_ratio | string | No | "1:1" | Image aspect ratio |
| layout_type | string | No | auto | Layout type |
| scene_elements | array | No | null | Pre-defined elements |
| text_layout | string | No | "bottom_centered" | Text overlay position |
| include_text_overlay | boolean | No | true | Include text |
| product_ids | array | No | null | Product references |
| character_id | string | No | null | Character for consistency |
| preserve_identity | boolean | No | false | Enable face preservation |
| use_scene_decomposition | boolean | No | true | Use scene decomp |
| use_constraint_resolution | boolean | No | true | Apply constraints |
| use_learned_preferences | boolean | No | true | Use learned prefs |
| quality_level | string | No | "high_quality" | Quality setting |

**Response:**
```json
{
  "generation_id": "gen_xyz789",
  "image_url": "https://cdn.example.com/generated/xyz789.png",
  "image_without_text_url": "https://cdn.example.com/generated/xyz789_notext.png",
  "headline": "Experience Innovation",
  "body_copy": "The perfect blend of design and technology.",
  "brand_score": 0.87,
  "constraint_satisfaction_score": 0.92,
  "colors_used": ["#1a1a2e", "#16213e", "#0f3460"],
  "scene_graph": {
    "id": "scene_abc",
    "elements": [
      {
        "id": "elem_1",
        "type": "BACKGROUND",
        "semantic_label": "minimalist desk surface",
        "spatial_position": "full_frame",
        "z_index": 0,
        "bounding_box": {"x": 0, "y": 0, "width": 1, "height": 1},
        "importance": 0.3
      }
    ],
    "layout_type": "PRODUCT_SHOWCASE",
    "aspect_ratio": "16:9",
    "overall_mood": "professional",
    "focal_point": {"x": 0.5, "y": 0.5}
  },
  "constraints_applied": [
    {
      "id": "const_1",
      "type": "MUST_INCLUDE",
      "strength": 1.0,
      "target_type": "COLOR",
      "target_value": "#1a1a2e",
      "description": "Brand primary color"
    }
  ],
  "compiled_prompt": {
    "positive_prompt": "professional photography, modern laptop centered on minimalist desk...",
    "negative_prompt": "cluttered, low quality, blurry...",
    "style_modifiers": ["professional photography"],
    "quality_modifiers": ["high quality", "detailed"]
  },
  "character_consistency_applied": false,
  "generation_time_ms": 15230,
  "model_used": "stabilityai/stable-diffusion-xl-base-1.0"
}
```

**Status Codes:**
- `200` - Success
- `400` - Invalid request
- `404` - Brand not found
- `500` - Generation failed

---

### 2. Record Feedback

Submit feedback for continuous learning.

**Endpoint:** `POST /api/advanced/feedback`

**Request Body:**
```json
{
  "generation_id": "gen_xyz789",
  "brand_id": "brand_abc123",
  "feedback_type": "ELEMENT",
  "is_positive": true,
  "element_id": "background",
  "attribute_key": "lighting",
  "attribute_value": "natural soft"
}
```

**Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| generation_id | string | Yes | Generation to provide feedback on |
| brand_id | string | Yes | Brand identifier |
| feedback_type | enum | Yes | "WHOLE", "ELEMENT", or "ATTRIBUTE" |
| is_positive | boolean | Yes | True for positive feedback |
| element_id | string | No | Element ID (for ELEMENT/ATTRIBUTE) |
| attribute_key | string | No | Attribute name (for ATTRIBUTE) |
| attribute_value | string | No | Attribute value (for ATTRIBUTE) |

**Response:**
```json
{
  "message": "Feedback recorded successfully",
  "feedback_id": "fb_123456",
  "learning_updated": true,
  "new_preference": {
    "attribute_type": "LIGHTING",
    "value": "natural soft",
    "confidence": 0.65,
    "sample_count": 4
  }
}
```

---

### 3. Get Learned Preferences

Retrieve all learned preferences for a brand.

**Endpoint:** `GET /api/advanced/preferences/{brand_id}`

**Response:**
```json
{
  "brand_id": "brand_abc123",
  "preferences": [
    {
      "id": "pref_1",
      "attribute_type": "LIGHTING",
      "value": "natural soft",
      "confidence": 0.85,
      "sample_count": 12,
      "last_updated": "2025-01-15T10:30:00Z"
    },
    {
      "id": "pref_2",
      "attribute_type": "COLOR_MOOD",
      "value": "warm",
      "confidence": 0.72,
      "sample_count": 8,
      "last_updated": "2025-01-14T15:45:00Z"
    }
  ],
  "negative_patterns": [
    {
      "pattern": "harsh shadows",
      "frequency": 5,
      "first_seen": "2025-01-10T08:00:00Z"
    }
  ],
  "total_preferences": 2,
  "total_negative_patterns": 1
}
```

---

### 4. Get Learning Summary

Get summary of learning progress for a brand.

**Endpoint:** `GET /api/advanced/learning-summary/{brand_id}`

**Response:**
```json
{
  "brand_id": "brand_abc123",
  "learning_status": "active",
  "total_feedback_received": 45,
  "positive_feedback_count": 38,
  "negative_feedback_count": 7,
  "preferences_learned": 5,
  "high_confidence_preferences": 3,
  "negative_patterns_detected": 2,
  "learning_rate": 0.12,
  "last_feedback_at": "2025-01-15T10:30:00Z",
  "recommendation": "System is learning well. Continue providing feedback for better accuracy."
}
```

---

### 5. Register Character

Register a character for identity consistency.

**Endpoint:** `POST /api/advanced/characters`

**Request Body:**
```json
{
  "brand_id": "brand_abc123",
  "reference_image_url": "https://example.com/mascot.jpg",
  "name": "Brand Mascot",
  "description": "Friendly cartoon character with blue hat"
}
```

**Response:**
```json
{
  "character_id": "char_456",
  "brand_id": "brand_abc123",
  "name": "Brand Mascot",
  "face_embedding_stored": true,
  "faces_detected": 1,
  "ready_for_consistency": true
}
```

---

### 6. Get Characters

List all characters for a brand.

**Endpoint:** `GET /api/advanced/characters/{brand_id}`

**Response:**
```json
{
  "brand_id": "brand_abc123",
  "characters": [
    {
      "id": "char_456",
      "name": "Brand Mascot",
      "reference_image_url": "https://...",
      "description": "Friendly cartoon character",
      "created_at": "2025-01-10T09:00:00Z",
      "usage_count": 15
    }
  ],
  "total_characters": 1
}
```

---

### 7. Analyze Scene

Analyze a prompt without generating.

**Endpoint:** `POST /api/advanced/analyze-scene`

**Request Body:**
```json
{
  "prompt": "Cozy coffee shop with warm lighting and wooden furniture",
  "aspect_ratio": "4:3"
}
```

**Response:**
```json
{
  "scene_graph": {
    "id": "scene_temp",
    "original_prompt": "Cozy coffee shop...",
    "elements": [
      {
        "id": "elem_1",
        "type": "BACKGROUND",
        "semantic_label": "coffee shop interior",
        "importance": 0.8
      },
      {
        "id": "elem_2",
        "type": "LIGHTING",
        "semantic_label": "warm lighting",
        "importance": 0.6
      },
      {
        "id": "elem_3",
        "type": "OBJECT",
        "semantic_label": "wooden furniture",
        "importance": 0.5
      }
    ],
    "layout_type": "LIFESTYLE_SCENE",
    "overall_mood": "cozy warm",
    "focal_point": {"x": 0.5, "y": 0.5}
  },
  "suggested_constraints": [
    "warm color temperature",
    "soft diffused lighting",
    "rustic textures"
  ]
}
```

---

### 8. Evaluate Generation

Evaluate a generation against brand guidelines.

**Endpoint:** `POST /api/advanced/evaluate`

**Request Body:**
```json
{
  "generation_id": "gen_xyz789",
  "brand_id": "brand_abc123",
  "generation_result": {
    "colors_used": ["#1a1a2e", "#16213e"],
    "compiled_prompt": {
      "positive_prompt": "...",
      "negative_prompt": "..."
    },
    "generation_time_ms": 15230
  },
  "brand_context": {
    "colors": [
      {"hex": "#1a1a2e", "name": "Primary"},
      {"hex": "#e94560", "name": "Accent"}
    ]
  },
  "constraints_applied": [
    {
      "type": "MUST_INCLUDE",
      "target_value": "#1a1a2e",
      "strength": 1.0
    }
  ]
}
```

**Response:**
```json
{
  "generation_id": "gen_xyz789",
  "evaluation": {
    "scores": {
      "color_alignment": 0.85,
      "constraint_adherence": 0.92,
      "generation_time": 1.0
    },
    "overall": 0.89,
    "grade": "B",
    "metrics_count": 3
  },
  "timestamp": "2025-01-15T11:00:00Z"
}
```

---

### 9. Get Evaluation Report

Generate comprehensive evaluation report.

**Endpoint:** `GET /api/advanced/evaluation-report/{brand_id}?days=7`

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| days | integer | 7 | Days to analyze |

**Response:**
```json
{
  "report_id": "eval_abc123",
  "brand_id": "brand_abc123",
  "period_start": "2025-01-08T00:00:00Z",
  "period_end": "2025-01-15T00:00:00Z",
  "metrics": [
    {
      "metric_type": "user_satisfaction",
      "metric_name": "feedback_ratio",
      "value": 0.84,
      "raw_value": {"positive": 38, "negative": 7, "total": 45}
    },
    {
      "metric_type": "learning_effectiveness",
      "metric_name": "confidence_growth",
      "value": 0.72,
      "raw_value": {"high_confidence": 3, "total_preferences": 5}
    }
  ],
  "summary": {
    "user_satisfaction": 0.82,
    "learning_effectiveness": 0.70,
    "overall": 0.76
  },
  "recommendations": [
    "System is performing well! Continue collecting feedback to maintain quality.",
    "Consider adding more brand constraints to improve alignment."
  ]
}
```

---

### 10. Get Metrics Summary

Quick metrics summary for dashboard.

**Endpoint:** `GET /api/advanced/metrics-summary/{brand_id}`

**Response:**
```json
{
  "brand_id": "brand_abc123",
  "summary": {
    "user_satisfaction": 0.82,
    "learning_effectiveness": 0.70,
    "brand_alignment": 0.88,
    "overall": 0.80
  },
  "overall_score": 0.80,
  "recommendations_count": 2,
  "period_days": 30
}
```

---

## Error Responses

All endpoints return errors in the following format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

**Common Error Codes:**

| Code | Description |
|------|-------------|
| 400 | Bad Request - Invalid parameters |
| 404 | Not Found - Resource doesn't exist |
| 422 | Validation Error - Request body invalid |
| 500 | Internal Server Error - Server-side failure |
| 503 | Service Unavailable - External service down |

---

## Rate Limits

| Endpoint | Limit |
|----------|-------|
| /generate | 10 requests/minute |
| /feedback | 100 requests/minute |
| Other endpoints | 60 requests/minute |

---

## Webhooks (Future)

Planned webhook events:
- `generation.completed`
- `preference.learned`
- `character.registered`
- `report.generated`

---

## SDK Examples

### Python
```python
import requests

BASE_URL = "http://localhost:8000/api"

# Generate content
response = requests.post(f"{BASE_URL}/advanced/generate", json={
    "brand_id": "brand_123",
    "prompt": "Modern product photography",
    "type": "both"
})
result = response.json()
print(f"Generated: {result['image_url']}")

# Submit feedback
requests.post(f"{BASE_URL}/advanced/feedback", json={
    "generation_id": result["generation_id"],
    "brand_id": "brand_123",
    "feedback_type": "WHOLE",
    "is_positive": True
})
```

### JavaScript
```javascript
const BASE_URL = "http://localhost:8000/api";

// Generate content
const result = await fetch(`${BASE_URL}/advanced/generate`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    brand_id: "brand_123",
    prompt: "Modern product photography",
    type: "both"
  })
}).then(r => r.json());

console.log("Generated:", result.image_url);

// Submit feedback
await fetch(`${BASE_URL}/advanced/feedback`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    generation_id: result.generation_id,
    brand_id: "brand_123",
    feedback_type: "WHOLE",
    is_positive: true
  })
});
```

---

## Changelog

### v1.0.0 (January 2025)
- Initial release with full GraphRAG pipeline
- Scene decomposition
- Constraint resolution
- Character consistency
- Feedback learning
- Evaluation framework

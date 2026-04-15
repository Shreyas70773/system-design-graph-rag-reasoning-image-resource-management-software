# Testing Documentation

## Brand-Aligned Content Generation System
### Test Plan and Results

---

## 1. Unit Testing

### 1.1 Scraping Module Tests

| Test ID | Test Case | Input | Expected Output | Status |
|---------|-----------|-------|-----------------|--------|
| SC-01 | Valid URL extraction | https://example.com | Brand name, logo URL extracted | ✓ Pass |
| SC-02 | Invalid URL handling | "not-a-url" | ValidationError raised | ✓ Pass |
| SC-03 | Color extraction from CSS | CSS with hex colors | List of Color objects | ✓ Pass |
| SC-04 | Logo detection | Page with img tags | Logo URL or None | ✓ Pass |
| SC-05 | Robots.txt compliance | URL with robots.txt | Respects disallow rules | ✓ Pass |

### 1.2 GraphRAG Module Tests

| Test ID | Test Case | Input | Expected Output | Status |
|---------|-----------|-------|-----------------|--------|
| GR-01 | Brand context retrieval | Valid brand_id | BrandDNA with colors, styles | ✓ Pass |
| GR-02 | Non-existent brand | Invalid brand_id | Empty result / 404 | ✓ Pass |
| GR-03 | Preference application | Brand with preferences | Context includes preferences | ✓ Pass |
| GR-04 | Cypher query building | Prompt + brand_id | Valid Cypher string | ✓ Pass |
| GR-05 | Multi-hop traversal | Complex brand graph | All related nodes retrieved | ✓ Pass |

### 1.3 Generation Module Tests

| Test ID | Test Case | Input | Expected Output | Status |
|---------|-----------|-------|-----------------|--------|
| GN-01 | Prompt compilation | Prompt + brand context | Compiled prompt string | ✓ Pass |
| GN-02 | Provider selection | Generation request | Selected provider | ✓ Pass |
| GN-03 | Fallback on rate limit | 429 from primary | Success from secondary | ✓ Pass |
| GN-04 | All providers fail | All return errors | Graceful error message | ✓ Pass |
| GN-05 | Result validation | Generated image | Valid URL, metadata | ✓ Pass |

### 1.4 Feedback Module Tests

| Test ID | Test Case | Input | Expected Output | Status |
|---------|-----------|-------|-----------------|--------|
| FB-01 | Rating processing | Rating 1-5 | Stored in database | ✓ Pass |
| FB-02 | Aspect extraction | Selected aspects | Structured aspect data | ✓ Pass |
| FB-03 | Preference creation | Analyzed feedback | LearnedPreference node | ✓ Pass |
| FB-04 | Graph relationship | Feedback + generation | RECEIVED relationship | ✓ Pass |
| FB-05 | Invalid rating | Rating > 5 | ValidationError | ✓ Pass |

### 1.5 LinkedIn Module Tests

| Test ID | Test Case | Input | Expected Output | Status |
|---------|-----------|-------|-----------------|--------|
| LI-01 | News retrieval | Industry string | List of NewsItem | ✓ Pass |
| LI-02 | Post generation | BrandVoice + topic | LinkedInPost object | ✓ Pass |
| LI-03 | Character limit | Long content | Post under 3000 chars | ✓ Pass |
| LI-04 | Hashtag extraction | Generated post | 3-5 hashtags | ✓ Pass |
| LI-05 | Batch generation | Multiple news items | Multiple posts | ✓ Pass |

---

## 2. Integration Testing

### 2.1 End-to-End Generation Flow

```
Test: Complete generation pipeline
Steps:
1. Create brand via onboarding
2. Submit generation request
3. Verify graph traversal
4. Confirm image returned
5. Check generation stored in history

Result: ✓ Pass
Notes: Average latency 45s (within 60s target)
```

### 2.2 Feedback Loop Integration

```
Test: Feedback affects subsequent generation
Steps:
1. Generate initial image
2. Submit feedback (rating: 2, aspect: "colors too dark")
3. Verify preference node created
4. Generate new image
5. Confirm preference applied to prompt

Result: ✓ Pass
Notes: Preference detected in compiled prompt
```

### 2.3 Provider Failover

```
Test: Graceful degradation across providers
Steps:
1. Configure primary provider with exhausted quota
2. Submit generation request
3. Verify fallback triggered
4. Confirm successful generation

Result: ✓ Pass
Notes: Automatic failover in <2s
```

### 2.4 LinkedIn + News Integration

```
Test: News-to-post pipeline
Steps:
1. Request industry news (Technology)
2. Verify Perplexity API response
3. Generate post from news item
4. Validate post structure
5. Check brand voice consistency

Result: ✓ Pass
Notes: Posts average 1,450 characters (optimal range)
```

---

## 3. API Testing

### 3.1 Endpoint Tests

| Endpoint | Method | Test | Expected | Status |
|----------|--------|------|----------|--------|
| /health | GET | Server running | 200 + status | ✓ |
| /api/brands | GET | List brands | Array of brands | ✓ |
| /api/brands | POST | Create brand | Brand object | ✓ |
| /api/brands/{id} | GET | Get single | Brand or 404 | ✓ |
| /api/brands/{id}/brand-dna | GET | Get DNA | BrandDNA object | ✓ |
| /api/generate | POST | Generate image | GenerationResult | ✓ |
| /api/feedback | POST | Submit feedback | Success | ✓ |
| /api/linkedin/news | POST | Get news | NewsItem array | ✓ |
| /api/linkedin/generate | POST | Generate post | LinkedInPost | ✓ |

### 3.2 Error Handling Tests

| Scenario | Expected Response | Status |
|----------|-------------------|--------|
| Invalid JSON body | 422 Unprocessable Entity | ✓ |
| Missing required field | 422 with field details | ✓ |
| Non-existent brand | 404 Not Found | ✓ |
| API key not configured | 503 Service Unavailable | ✓ |
| External API timeout | 500 with timeout message | ✓ |

---

## 4. Performance Testing

### 4.1 Response Time Metrics

| Operation | Target | Measured | Status |
|-----------|--------|----------|--------|
| Health check | <100ms | 45ms | ✓ |
| List brands | <500ms | 210ms | ✓ |
| Get brand DNA | <500ms | 380ms | ✓ |
| Graph query | <500ms | 290ms | ✓ |
| Image generation | <60s | 35-55s | ✓ |
| News retrieval | <10s | 4-8s | ✓ |
| Post generation | <15s | 6-12s | ✓ |

### 4.2 Load Testing

```
Tool: Locust
Configuration: 10 concurrent users, 5 minute duration

Results:
- Requests/sec: 12.4
- Median response: 450ms
- 95th percentile: 2.1s
- Error rate: 0.2%

Conclusion: System handles expected load within targets
```

---

## 5. User Acceptance Testing

### 5.1 Brand Consistency Evaluation

```
Method: 5 evaluators rate generated content
Scale: 1-5 (1=Poor match, 5=Excellent match)

Criteria:
- Color usage matches brand palette
- Style consistent with brand identity
- Overall brand alignment

Results:
- Average score: 3.8/5
- Standard deviation: 0.6
- Evaluator agreement: 78%
```

### 5.2 LinkedIn Post Quality

```
Method: 3 marketing professionals evaluate posts
Criteria:
- Professional tone
- Industry relevance
- Engagement potential
- Brand voice consistency

Results:
- Professional tone: 4.2/5
- Industry relevance: 4.0/5
- Engagement potential: 3.6/5
- Brand voice: 3.9/5
```

### 5.3 System Usability Scale (SUS)

```
Participants: 8 users
Average SUS Score: 72.5
Interpretation: Good usability (above average)

Notable feedback:
+ "Onboarding process is intuitive"
+ "Graph visualization helps understand brand DNA"
- "Could use more guidance on prompt writing"
- "Would like to see generation progress"
```

---

## 6. Test Environment

### 6.1 Configuration

```
Backend:
- Python 3.10.12
- FastAPI 0.100.0
- Neo4j Aura (Free tier)

Frontend:
- Node.js 18.17.0
- React 18.2.0
- Vite 5.0.0

APIs:
- OpenAI GPT-4o-mini
- Google Gemini
- Perplexity (llama-3.1-sonar-small-128k-online)
```

### 6.2 Test Data

```
Test Brands: 5 synthetic brands
- TechNova (Technology)
- GreenLeaf (Sustainability)
- FinanceFirst (Finance)
- HealthPlus (Healthcare)
- RetailHub (Retail)

Each brand includes:
- 4-6 colors
- 2-3 styles
- 3-5 products
- 1-2 characters (mascots)
```

---

## 7. Known Issues and Limitations

| Issue | Severity | Mitigation |
|-------|----------|------------|
| Rate limits on free API tiers | Medium | Multi-provider fallback |
| Graph query performance degrades with large graphs | Low | Index optimization |
| News retrieval sometimes returns older items | Low | Date filtering |
| Image text legibility varies | Medium | Style conditioning |

---

## 8. Test Coverage Summary

| Module | Line Coverage | Branch Coverage |
|--------|---------------|-----------------|
| Scraping | 82% | 75% |
| GraphRAG | 88% | 80% |
| Generation | 85% | 78% |
| Feedback | 90% | 85% |
| LinkedIn | 80% | 72% |
| **Overall** | **85%** | **78%** |

---

## Appendix: Sample Test Code

### Unit Test Example (pytest)

```python
# tests/test_feedback.py
import pytest
from app.feedback.processor import FeedbackProcessor

class TestFeedbackProcessor:
    
    def test_rating_validation(self):
        """Ratings must be 1-5"""
        processor = FeedbackProcessor()
        
        with pytest.raises(ValueError):
            processor.process(rating=6, aspects=[])
        
        with pytest.raises(ValueError):
            processor.process(rating=0, aspects=[])
    
    def test_preference_extraction(self):
        """Feedback creates appropriate preferences"""
        processor = FeedbackProcessor()
        feedback = {
            "rating": 2,
            "aspects": ["colors"],
            "comment": "The colors were too dark for our brand"
        }
        
        result = processor.analyze(feedback)
        
        assert result.trigger == "colors"
        assert "dark" in result.action.lower() or "bright" in result.action.lower()
```

### Integration Test Example

```python
# tests/test_integration.py
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_generation_pipeline():
    """Full generation flow integration test"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Create brand
        brand_response = await client.post("/api/brands", json={
            "name": "TestBrand",
            "website": "https://example.com"
        })
        assert brand_response.status_code == 200
        brand_id = brand_response.json()["id"]
        
        # Generate content
        gen_response = await client.post("/api/generate", json={
            "brand_id": brand_id,
            "prompt": "Modern office workspace"
        })
        assert gen_response.status_code == 200
        assert "image_url" in gen_response.json()
```

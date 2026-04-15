# Implementation Checklist & Technical Guide
## Phase-by-Phase Project Execution (No Docker Required)

---

## 🚫 Docker NOT Required

**Good news**: This capstone project does **NOT require Docker**. Everything runs on:
- **Local development**: Python + Node.js on your machine
- **Cloud services**: All FREE tier (Neo4j Aura, Railway, Vercel, etc.)

Docker would only be needed for production deployment, which is overkill for a capstone demo.

---

## 📋 Master Implementation Checklist

### Phase 0: Setup (Day 1-2)
```
□ Install Python 3.11+
□ Install Node.js 18+
□ Install VS Code with extensions:
  □ Python
  □ Pylance
  □ ES7+ React/Redux/React-Native snippets
  □ Tailwind CSS IntelliSense
□ Create project folder structure
□ Initialize git repository
□ Create GitHub repository
```

### Phase 1: Create Free Accounts (Day 2-3)
```
□ Neo4j Aura (aura.neo4j.io)
  □ Create FREE instance
  □ Save connection URI, username, password
  □ Test connection in Neo4j Browser
  
□ Hugging Face (huggingface.co)
  □ Create account
  □ Generate API token (Settings → Access Tokens)
  □ Save token securely
  
□ Groq (console.groq.com)
  □ Create account
  □ Generate API key
  □ Save key securely
  
□ Cloudflare (cloudflare.com) - Optional for now
  □ Create account
  □ Set up R2 storage bucket
  
□ Vercel (vercel.com) - For deployment later
□ Railway (railway.app) - For deployment later
```

### Phase 2: Backend Foundation (Week 1)
```
□ Create backend folder structure:
  backend/
  ├── app/
  │   ├── __init__.py
  │   ├── main.py
  │   ├── config.py
  │   └── ...
  ├── requirements.txt
  └── .env

□ Set up virtual environment:
  □ python -m venv venv
  □ Activate: venv\Scripts\activate (Windows)
  □ pip install fastapi uvicorn python-dotenv

□ Create basic FastAPI app (main.py)
  □ Health check endpoint: GET /health
  □ Test with: uvicorn app.main:app --reload
  □ Verify at: http://localhost:8000/docs

□ Create .env file with:
  □ NEO4J_URI=neo4j+s://xxxxx.databases.neo4j.io
  □ NEO4J_USER=neo4j
  □ NEO4J_PASSWORD=your-password
  □ HUGGINGFACE_TOKEN=hf_xxxxx
  □ GROQ_API_KEY=gsk_xxxxx

□ Install Neo4j driver:
  □ pip install neo4j
  □ Create neo4j_client.py
  □ Test connection to Aura
```

### Phase 3: Web Scraping Module (Week 1-2)
```
□ Install scraping libraries:
  □ pip install requests beautifulsoup4 pillow colorthief

□ Create scraping/website_scraper.py:
  □ Function: fetch_webpage(url) → HTML
  □ Function: extract_company_info(html) → dict
  □ Function: extract_meta_tags(html) → dict
  □ Handle errors (timeout, invalid URL, blocked)

□ Create scraping/logo_extractor.py:
  □ Function: find_logo_url(html, base_url) → string
  □ Function: download_image(url) → bytes
  □ Look for: <img> with "logo" in class/id/alt
  □ Look for: <link rel="icon">
  □ Handle SVG, PNG, JPG formats

□ Create scraping/color_extractor.py:
  □ Function: extract_colors_from_image(image) → list
  □ Use colorthief library
  □ Return top 5 colors as hex codes

□ Create API endpoint:
  □ POST /api/brands/scrape
  □ Input: { "website_url": "https://..." }
  □ Output: { company_name, tagline, logo_url, colors }

□ Test with real websites:
  □ Simple site (local business)
  □ Complex site (major brand)
  □ Site that blocks scraping (handle gracefully)
```

### Phase 4: Image Quality Module (Week 2)
```
□ Install image processing:
  □ pip install pillow numpy

□ Create quality/image_quality.py:
  □ Function: check_resolution(image) → bool
    - Minimum 200x200 pixels
  □ Function: check_blur(image) → float
    - Laplacian variance method
  □ Function: check_format(image) → string
    - PNG/JPG/SVG detection
  □ Function: calculate_quality_score(image) → float (0-1)

□ Create quality/enhancement.py:
  □ Function: generate_logo_prompt(company_info) → string
  □ Function: generate_ai_logo(prompt) → image
    - Use Hugging Face SDXL API

□ Create API endpoints:
  □ POST /api/brands/{id}/logo/check-quality
  □ POST /api/brands/{id}/logo/generate-ai
  □ POST /api/brands/{id}/logo/upload

□ Test quality checker:
  □ High quality image → score > 0.7
  □ Blurry image → score < 0.4
  □ Small image → score < 0.5
```

### Phase 5: Neo4j Graph Schema (Week 2-3)
```
□ Design graph schema:
  □ Node: Brand (name, website, tagline, industry)
  □ Node: Logo (url, quality_score, source)
  □ Node: Color (hex, name)
  □ Node: Product (name, price_range, description)
  □ Node: Generation (prompt, image_url, text, timestamp)
  
  □ Relationship: (Brand)-[:HAS_LOGO]->(Logo)
  □ Relationship: (Brand)-[:USES_COLOR]->(Color)
  □ Relationship: (Brand)-[:SELLS]->(Product)
  □ Relationship: (Brand)-[:GENERATED]->(Generation)

□ Create database/schema.cypher:
  □ Constraint: Brand.name unique
  □ Index: Brand.website

□ Create neo4j queries:
  □ create_brand(data) → brand_id
  □ get_brand(id) → brand_data
  □ add_logo_to_brand(brand_id, logo_data)
  □ add_products_to_brand(brand_id, products)
  □ get_brand_context(brand_id) → full context

□ Test in Neo4j Browser:
  □ Create sample brand
  □ Visualize relationships
  □ Query brand context
```

### Phase 6: Product Input Module (Week 3)
```
□ Create products/text_parser.py:
  □ Function: parse_products_with_llm(text) → list
  □ Use Groq API (Llama 3 70B)
  □ Extract: name, price, category, description

□ Create products/url_scraper.py:
  □ Function: scrape_product_page(url) → list
  □ Extract product cards/items
  □ Handle pagination if needed

□ Create API endpoints:
  □ POST /api/brands/{id}/products/parse-text
    - Input: { "text": "We sell coffee ($15)..." }
    - Output: [{ name, price, category }, ...]
  □ POST /api/brands/{id}/products/scrape-url
    - Input: { "url": "https://..." }
    - Output: [{ name, price, image_url }, ...]
  □ POST /api/brands/{id}/products
    - Save products to Neo4j

□ Test product parsing:
  □ "We sell shoes ($50), shirts ($30)"
  □ → [{ name: "shoes", price: "$50" }, ...]
```

### Phase 7: Content Generation Module (Week 3-4)
```
□ Install HTTP client:
  □ pip install httpx

□ Create generation/image_generator.py:
  □ Function: build_image_prompt(brand_context, request)
  □ Function: generate_image(prompt) → image_url
  □ Use Hugging Face Inference API
  □ Include brand colors in prompt

□ Create generation/text_generator.py:
  □ Function: build_text_prompt(brand_context, request)
  □ Function: generate_headline(prompt) → string
  □ Function: generate_body_copy(prompt) → string
  □ Use Groq API (Llama 3 70B)

□ Create generation/validator.py:
  □ Function: extract_colors_from_generated(image)
  □ Function: compare_colors(generated, brand)
  □ Function: calculate_brand_score(image, brand)

□ Create API endpoints:
  □ POST /api/generate
    - Input: { brand_id, prompt, type: "image|text|both" }
    - Output: { image_url, headline, body, brand_score }

□ Test generation:
  □ Generate image for coffee shop
  □ Verify colors match brand
  □ Generate marketing copy
```

### Phase 8: Frontend Development (Week 4-5)
```
□ Create React app:
  □ npm create vite@latest frontend -- --template react
  □ cd frontend && npm install
  □ npm install axios react-router-dom
  □ npm install -D tailwindcss postcss autoprefixer
  □ npx tailwindcss init -p

□ Create pages:
  □ Home.jsx - Welcome + "Add Your Brand" button
  □ Onboarding.jsx - Multi-step brand setup
  □ Generate.jsx - Content generation form
  □ Results.jsx - Display generated content
  □ History.jsx - Past generations

□ Create components:
  □ WebsiteInput.jsx - URL input with validation
  □ BrandReview.jsx - Show scraped data
  □ LogoQuality.jsx - Quality score + enhancement options
  □ ProductInput.jsx - Text area or URL input
  □ GenerationForm.jsx - Prompt + options
  □ ResultDisplay.jsx - Image + text + score

□ Connect to backend:
  □ Create api.js service
  □ Handle loading states
  □ Handle errors gracefully
  □ Show progress indicators

□ Style with Tailwind:
  □ Responsive design
  □ Clean, modern look
  □ Brand color previews
```

### Phase 9: Integration Testing (Week 5-6)
```x`
□ Test complete flow:
  □ Enter website URL
  □ Review scraped data
  □ Check/fix logo quality
  □ Add products
  □ Generate content
  □ Give feedback

□ Test edge cases:
  □ Invalid URL
  □ Website blocks scraping
  □ Very slow API response
  □ Poor quality logo
  □ Empty products

□ Fix bugs found
□ Improve error messages
□ Add loading states where missing
```

### Phase 10: Deployment (Week 6-7)
```
□ Deploy Backend to Railway:
  □ Create Procfile: web: uvicorn app.main:app --host 0.0.0.0 --port $PORT
  □ Push to GitHub
  □ Connect Railway to GitHub
  □ Set environment variables
  □ Deploy and test

□ Deploy Frontend to Vercel:
  □ Update API URL to Railway URL
  □ Connect Vercel to GitHub
  □ Set environment variables
  □ Deploy and test

□ Test deployed application:
  □ Full flow works
  □ No CORS issues
  □ Acceptable performance
```

### Phase 11: Demo Preparation (Week 7-8)
```
□ Create demo brands:
  □ Local coffee shop
  □ Fitness gym
  □ Restaurant
  □ Tech startup

□ Prepare demo script:
  □ 5-7 minute walkthrough
  □ Show data intake flow
  □ Show graph in Neo4j Browser
  □ Generate sample content

□ Practice demo:
  □ Time yourself
  □ Prepare for common questions
  □ Have backup plan if something fails

□ Record backup video:
  □ Screen recording of full demo
  □ In case live demo fails
```

---

## 🧠 Technical Knowledge Checklist

### What You MUST Know to Explain the Project

#### 1. Data Flow (Be able to draw this)
```
USER ENTERS URL
      │
      ▼
┌─────────────────┐
│  WEB SCRAPER    │ ← BeautifulSoup parses HTML
│  - Company name │    Finds <title>, <meta>, <img>
│  - Logo URL     │    Downloads logo image
│  - Colors       │    ColorThief extracts palette
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ QUALITY CHECKER │ ← Pillow processes image
│  - Resolution   │    Checks pixels (min 200x200)
│  - Blur score   │    Laplacian variance algorithm
│  - Format       │    PNG/JPG/SVG detection
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
 GOOD       BAD
    │         │
    │    ┌────┴────┐
    │    │ OPTIONS │
    │    │ A) AI   │ ← Hugging Face SDXL
    │    │ B) Upload│
    │    │ C) Keep │
    │    └────┬────┘
    │         │
    └────┬────┘
         │
         ▼
┌─────────────────┐
│ PRODUCT INPUT   │ ← User choice:
│  - Text parsing │    Groq Llama 3 extracts entities
│  - URL scraping │    BeautifulSoup parses product page
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│    NEO4J        │ ← Graph database stores:
│  Brand → Logo   │    Nodes + Relationships
│  Brand → Colors │    Cypher queries retrieve context
│  Brand → Products│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   GENERATION    │ ← User requests content
│  Image: HF SDXL │    Prompt includes brand colors
│  Text: Groq LLM │    Returns image + copy
└─────────────────┘
```

#### 2. Core Technologies (Know what each does)

| Technology | What It Does | Why We Use It |
|------------|--------------|---------------|
| **FastAPI** | Python web framework | Auto-generates API docs, async support, type hints |
| **Neo4j** | Graph database | Perfect for relationships (brand→products), Cypher queries |
| **React** | Frontend framework | Component-based UI, easy state management |
| **BeautifulSoup** | HTML parser | Extracts data from web pages |
| **Pillow** | Image processing | Checks resolution, blur, format |
| **ColorThief** | Color extraction | Gets dominant colors from images |
| **Hugging Face** | AI model hosting | Free SDXL image generation API |
| **Groq** | LLM API provider | Free Llama 3 70B, very fast inference |

#### 3. Key Algorithms (Be able to explain)

**Blur Detection (Laplacian Variance)**
```python
# Simple explanation:
# 1. Convert image to grayscale
# 2. Apply Laplacian filter (detects edges)
# 3. Calculate variance of result
# 4. Low variance = blurry (no sharp edges)

import cv2
import numpy as np

def detect_blur(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    variance = laplacian.var()
    return variance  # < 100 = blurry, > 500 = sharp
```

**Color Extraction (K-Means Clustering)**
```python
# ColorThief uses this internally:
# 1. Sample pixels from image
# 2. Cluster similar colors (K-means)
# 3. Return cluster centers as dominant colors

from colorthief import ColorThief

def get_colors(image_path):
    ct = ColorThief(image_path)
    palette = ct.get_palette(color_count=5)
    return [f"#{r:02x}{g:02x}{b:02x}" for r, g, b in palette]
```

**Graph Query (Cypher)**
```cypher
// Get full brand context for generation
MATCH (b:Brand {id: $brand_id})
OPTIONAL MATCH (b)-[:HAS_LOGO]->(l:Logo)
OPTIONAL MATCH (b)-[:USES_COLOR]->(c:Color)
OPTIONAL MATCH (b)-[:SELLS]->(p:Product)
RETURN b, l, collect(DISTINCT c) as colors, collect(DISTINCT p) as products
```

#### 4. API Design (Know your endpoints)

```
POST /api/brands/scrape
  Input:  { "website_url": "https://example.com" }
  Output: { "company_name": "...", "logo_url": "...", "colors": [...] }

POST /api/brands/{id}/logo/check-quality
  Output: { "quality_score": 0.72, "issues": ["slightly_blurry"] }

POST /api/brands/{id}/logo/generate-ai
  Input:  { "description": "modern tech company logo" }
  Output: { "generated_logo_url": "..." }

POST /api/brands/{id}/products/parse-text
  Input:  { "text": "We sell coffee ($15), tea ($10)" }
  Output: [{ "name": "coffee", "price": "$15" }, ...]

POST /api/generate
  Input:  { "brand_id": "123", "prompt": "summer promotion", "type": "both" }
  Output: { "image_url": "...", "headline": "...", "body": "...", "brand_score": 0.89 }
```

#### 5. Why Graph Database? (Common question)

**Traditional SQL approach:**
```sql
-- Need 4 tables + complex JOINs
SELECT b.*, l.*, c.*, p.*
FROM brands b
LEFT JOIN logos l ON b.id = l.brand_id
LEFT JOIN brand_colors bc ON b.id = bc.brand_id
LEFT JOIN colors c ON bc.color_id = c.id
LEFT JOIN products p ON b.id = p.brand_id
WHERE b.id = 123;
-- Gets messy with more relationships!
```

**Graph approach:**
```cypher
-- One intuitive query
MATCH (b:Brand {id: 123})-[r]->(related)
RETURN b, r, related
-- Naturally follows relationships!
```

**Benefits:**
- Relationships are first-class citizens
- Easy to add new relationship types
- Visual representation in Neo4j Browser
- Natural fit for "brand context" retrieval

---

## ❓ Potential Teacher Questions & Answers

### Architecture Questions

**Q: Why not use a relational database?**
> A: Brand data is highly connected - a brand has logos, colors, products, and generated content all related. Graph databases like Neo4j are optimized for traversing these relationships. In SQL, this would require multiple JOINs. In Neo4j, it's a single traversal query. Also, we can easily add new relationship types without schema migrations.

**Q: Why use separate services for image and text generation?**
> A: Specialization. Hugging Face hosts fine-tuned image models (SDXL) optimized for visuals. Groq provides extremely fast LLM inference for text. Using the best tool for each job gives better results than a single general-purpose model.

**Q: How do you handle if the website blocks scraping?**
> A: We implement graceful degradation:
> 1. First, we set proper User-Agent headers to look like a browser
> 2. If blocked (403/429), we catch the error and prompt the user to manually enter company info
> 3. We also respect robots.txt where applicable
> The user can always manually upload a logo and enter details.

**Q: What happens if an API is down?**
> A: We have error handling at each step:
> - API timeout: Retry up to 3 times with exponential backoff
> - API error: Show user-friendly message, log error for debugging
> - Complete failure: Allow user to skip step or try later
> Critical: We never leave the user stuck without feedback.

### Code-Level Questions

**Q: Show me how you check image quality.**
```python
from PIL import Image
import numpy as np

def calculate_quality_score(image_path):
    img = Image.open(image_path)
    
    # Resolution check (0-0.4 points)
    width, height = img.size
    resolution_score = min(1.0, (width * height) / (500 * 500)) * 0.4
    
    # Blur check using Laplacian variance (0-0.4 points)
    gray = img.convert('L')
    laplacian = np.array(gray.filter(ImageFilter.FIND_EDGES))
    blur_variance = laplacian.var()
    blur_score = min(1.0, blur_variance / 500) * 0.4
    
    # Format check (0-0.2 points)
    format_score = 0.2 if img.format in ['PNG', 'SVG'] else 0.1
    
    return resolution_score + blur_score + format_score
```

**Q: How does the LLM parse product text?**
```python
import os
from groq import Groq

def parse_products(text):
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    
    prompt = f"""Extract products from this text. Return JSON array.
    
Text: {text}

Return format: [{{"name": "...", "price": "...", "category": "..."}}]
Only return the JSON, no explanation."""

    response = client.chat.completions.create(
        model="llama3-70b-8192",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1  # Low temp for consistent extraction
    )
    
    return json.loads(response.choices[0].message.content)
```

**Q: How do you build the image generation prompt?**
```python
def build_image_prompt(brand_context, user_request):
    colors = ", ".join(brand_context["colors"])
    
    prompt = f"""
    Create a marketing image for {brand_context["name"]}.
    Brand colors: {colors}
    Industry: {brand_context["industry"]}
    Style: professional, modern, clean
    
    Request: {user_request}
    
    Important: Use the brand colors prominently.
    """
    
    return prompt
```

**Q: Show me a Cypher query for getting brand context.**
```cypher
// Get everything about a brand for generation
MATCH (b:Brand {id: $brand_id})
OPTIONAL MATCH (b)-[:HAS_LOGO]->(logo:Logo)
OPTIONAL MATCH (b)-[:USES_COLOR]->(color:Color)
OPTIONAL MATCH (b)-[:SELLS]->(product:Product)
OPTIONAL MATCH (b)-[:GENERATED]->(gen:Generation)
RETURN {
  brand: b,
  logo: logo,
  colors: collect(DISTINCT color.hex),
  products: collect(DISTINCT {name: product.name, price: product.price}),
  recent_generations: collect(DISTINCT gen)[0..5]
} as context
```

### Conceptual Questions

**Q: What is GraphRAG?**
> A: GraphRAG combines graph databases with Retrieval-Augmented Generation. Instead of just searching text, we traverse a knowledge graph to find relevant context. For our project:
> 1. User requests content for a brand
> 2. We query Neo4j to get the brand's logo, colors, products, past generations
> 3. This context is added to the LLM prompt
> 4. The LLM generates content that's aware of the brand's identity
> 
> This is better than traditional RAG because relationships (brand→product→category) provide richer context than keyword matching.

**Q: Why free tiers? Would this scale?**
> A: For a capstone demo with 5-10 users, free tiers are sufficient:
> - Neo4j Aura FREE: 50K nodes (we use ~1000)
> - Groq: 6000 requests/day (we need ~100)
> - Hugging Face: ~1000 inference calls/day
> 
> For production, we'd upgrade to paid tiers and add:
> - Rate limiting
> - Caching (Redis)
> - Queue system (for image generation)
> - Multiple Neo4j replicas
> 
> The architecture is designed to scale; we're just using free tiers for cost.

**Q: How do you ensure brand consistency in generated images?**
> A: Multiple approaches:
> 1. **Prompt Engineering**: Include brand colors, style, industry in the prompt
> 2. **Negative Prompts**: Specify what NOT to include
> 3. **Validation**: After generation, extract colors from the image and compare to brand palette
> 4. **Scoring**: Calculate a "brand consistency score" based on color match
> 5. **Feedback Loop**: User feedback (👍👎) trains the system on preferences

---

## 📚 Learning Resources

### Must-Learn Before Starting

| Topic | Resource | Time |
|-------|----------|------|
| **Python Basics** | [Python Tutorial](https://docs.python.org/3/tutorial/) | 4-6 hours |
| **FastAPI** | [FastAPI Tutorial](https://fastapi.tiangolo.com/tutorial/) | 3-4 hours |
| **React Basics** | [React Quick Start](https://react.dev/learn) | 4-5 hours |
| **Neo4j & Cypher** | [Neo4j GraphAcademy](https://graphacademy.neo4j.com/) | 4-6 hours |

### Deep Dive Topics

| Topic | Resource | When to Learn |
|-------|----------|---------------|
| **Web Scraping** | [BeautifulSoup Docs](https://www.crummy.com/software/BeautifulSoup/bs4/doc/) | Week 1 |
| **Image Processing** | [Pillow Tutorial](https://pillow.readthedocs.io/en/stable/handbook/tutorial.html) | Week 2 |
| **REST API Design** | [REST API Tutorial](https://restfulapi.net/) | Week 1 |
| **Prompt Engineering** | [OpenAI Cookbook](https://cookbook.openai.com/) | Week 3 |
| **Tailwind CSS** | [Tailwind Docs](https://tailwindcss.com/docs) | Week 4 |

### Video Tutorials (Recommended)

| Topic | Channel/Course | Link |
|-------|----------------|------|
| FastAPI Crash Course | Traversy Media | YouTube |
| React in 1 Hour | Web Dev Simplified | YouTube |
| Neo4j for Beginners | Neo4j Official | GraphAcademy |
| Python Web Scraping | Corey Schafer | YouTube |

### Documentation to Bookmark

- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [React Docs](https://react.dev/)
- [Neo4j Cypher Manual](https://neo4j.com/docs/cypher-manual/current/)
- [Hugging Face Inference API](https://huggingface.co/docs/api-inference/)
- [Groq API Docs](https://console.groq.com/docs)
- [Tailwind CSS](https://tailwindcss.com/docs)

---

## 🎯 Quick Reference Card (Print This!)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    QUICK REFERENCE CARD                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  DATA FLOW:                                                              │
│  URL → Scrape → Quality Check → Products → Neo4j → Generate             │
│                                                                          │
│  TECH STACK:                                                             │
│  Backend:  Python + FastAPI                                              │
│  Frontend: React + Vite + Tailwind                                       │
│  Database: Neo4j Aura (Graph)                                            │
│  Image AI: Hugging Face (SDXL)                                           │
│  Text AI:  Groq (Llama 3 70B)                                            │
│                                                                          │
│  KEY LIBRARIES:                                                          │
│  • beautifulsoup4 - HTML parsing                                         │
│  • pillow - Image processing                                             │
│  • colorthief - Color extraction                                         │
│  • neo4j - Graph database driver                                         │
│  • httpx - Async HTTP client                                             │
│                                                                          │
│  COMMANDS:                                                               │
│  Backend:  uvicorn app.main:app --reload                                 │
│  Frontend: npm run dev                                                   │
│  Neo4j:    Open browser at your Aura instance                            │
│                                                                          │
│  FREE TIER LIMITS:                                                       │
│  Neo4j Aura:    50,000 nodes                                             │
│  Groq:          6,000 requests/day                                       │
│  Hugging Face:  ~1,000 inferences/day                                    │
│  Railway:       500 hours/month                                          │
│  Vercel:        Unlimited (hobby)                                        │
│                                                                          │
│  WHY GRAPH DB?                                                           │
│  → Relationships are first-class (Brand→Products)                        │
│  → Easy context retrieval for AI                                         │
│  → Visual debugging in Neo4j Browser                                     │
│                                                                          │
│  QUALITY SCORE FORMULA:                                                  │
│  score = resolution(0.4) + blur(0.4) + format(0.2)                       │
│  > 0.7 = Good | 0.4-0.7 = OK | < 0.4 = Bad                               │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## ✅ Pre-Demo Checklist

```
□ All services running (backend, frontend)
□ Neo4j Aura connected and has data
□ Demo brands created and tested
□ Backup demo video recorded
□ Presentation slides ready
□ Quick reference card printed
□ Practiced Q&A responses
□ Tested on presentation laptop
□ Backup laptop/hotspot ready
```

---

**Remember**: The goal is to demonstrate understanding of:
1. **Data pipelines** (scraping → processing → storage)
2. **Graph databases** (relationships, Cypher queries)
3. **AI integration** (prompt engineering, API calls)
4. **Full-stack development** (React + FastAPI)

You don't need to memorize everything—understand the WHY behind each decision!

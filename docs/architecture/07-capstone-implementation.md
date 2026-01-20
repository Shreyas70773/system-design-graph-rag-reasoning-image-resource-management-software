# Capstone Implementation Plan
## 8-Week Development Timeline (Near-Zero Cost)

**Target**: Functional prototype for academic demonstration  
**Team**: 2-3 students  
**Scope**: Simplified architecture (5-10 users)  
**Budget**: < $15/month (using free tiers)

---

## Timeline Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    8-WEEK IMPLEMENTATION TIMELINE                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Week 1-2       Week 3-4       Week 5-6       Week 7-8                      │
│    │              │              │              │                            │
│    ▼              ▼              ▼              ▼                            │
│  ████████      ████████      ████████      ████████                         │
│  FOUNDATION    DATA INTAKE   GENERATION    POLISH                           │
│                                                                              │
│  • Setup       • Scraping     • AI APIs     • Testing                       │
│  • Database    • Logo check   • Frontend    • Demo prep                     │
│  • Backend     • Product add  • Feedback    • Docs                          │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Week 1-2: Foundation

### Goals
- Development environment ready
- Database operational
- Basic API framework
- Free tier accounts created

### Tasks

#### Week 1: Setup & Infrastructure

```yaml
Day 1-2: Environment Setup
  □ Install Python 3.11 (with virtual environment)
  □ Install Node.js 18+
  □ Create GitHub repository
  □ Set up project structure
  □ Create free accounts:
    - Neo4j Aura (aura.neo4j.io) - FREE tier
    - Hugging Face (huggingface.co) - FREE tier
    - Groq (groq.com) - FREE tier
    - Vercel (vercel.com) - FREE tier
    - Railway (railway.app) - FREE tier
    - Cloudflare R2 (cloudflare.com) - FREE tier
  
Day 3-4: Database Setup
  □ Create Neo4j Aura FREE instance (50K nodes)
  □ Get connection credentials
  □ Test connection from Python (neo4j driver)
  □ Learn basic Cypher queries
  
Day 5-7: Backend Foundation
  □ Initialize FastAPI project
  □ Create Neo4j connection module
  □ Build health check endpoint
  □ Set up environment variables (.env)
  □ Create basic error handling
```

#### Week 2: Core Backend + Web Scraping Module

```yaml
Day 1-3: Web Scraping Implementation
  □ Install scraping libraries:
    - pip install requests beautifulsoup4 pillow colorthief
  □ Create scraper module:
    - scrape_website(url) → company info
    - extract_logo(url) → logo image
    - extract_colors(image) → color palette
  □ Handle edge cases:
    - Website blocks scraping
    - Logo not found
    - Invalid URL
  
Day 4-5: Image Quality Checker
  □ Create quality assessment module:
    - check_resolution(image) → bool (min 200x200)
    - check_blur(image) → float (Laplacian variance)
    - check_format(image) → string (PNG/JPG/SVG)
    - calculate_quality_score(image) → 0.0-1.0
  □ Define quality thresholds:
    - > 0.7: Good quality ✓
    - 0.4 - 0.7: Acceptable ⚠️
    - < 0.4: Poor quality ❌
  
Day 6-7: API Endpoints (Data Intake)
  □ POST /api/brands/scrape
    - Input: { "website_url": "https://example.com" }
    - Output: { "company_name", "logo_url", "colors", "quality_score" }
  □ POST /api/brands/upload-logo
    - Input: FormData with image file
    - Output: { "logo_url", "quality_score" }
  □ POST /api/brands/generate-logo
    - Input: { "company_description": "..." }
    - Output: { "generated_logo_url" }
```

### Deliverables
✓ Working FastAPI backend  
✓ Neo4j Aura FREE connected  
✓ Web scraping module working
✓ Image quality checker working
✓ All free tier accounts ready

---

## Week 3-4: Data Intake Pipeline

### Goals
- Complete brand onboarding flow
- Product/service input working
- Graph data storage operational

### Tasks

#### Week 3: Brand Onboarding Flow

```yaml
Day 1-2: Graph Schema Implementation
  □ Define Cypher schema in Neo4j Aura:
    CREATE (b:Brand {
      name: "Example",
      website: "https://example.com",
      tagline: "...",
      industry: "..."
    })
    CREATE (l:Logo {
      url: "...",
      quality_score: 0.85,
      source: "scraped|uploaded|ai_generated"
    })
    CREATE (c:Color {hex: "#FF5733", name: "Brand Orange"})
    CREATE (p:Product {name: "...", price_range: "..."})
    
    CREATE (b)-[:HAS_LOGO]->(l)
    CREATE (b)-[:USES_COLOR]->(c)
    CREATE (b)-[:SELLS]->(p)
  □ Test queries in Neo4j Browser
  
Day 3-4: Logo Enhancement Flow
  □ Implement decision logic:
    quality < 0.4 → Prompt for upgrade
    quality 0.4-0.7 → Suggest upgrade
    quality > 0.7 → Accept as-is
  □ Create Hugging Face SDXL integration:
    - Generate logo from description
    - Use brand colors as input
  □ Build logo selection UI endpoint:
    POST /api/brands/{id}/logo/enhance
    
Day 5-7: Product/Service Input
  □ Create text parsing endpoint:
    POST /api/brands/{id}/products/parse-text
    - Input: { "text": "We sell shoes ($50), shirts ($30)" }
    - Output: [{ name: "shoes", price: "$50" }, ...]
  □ Use Groq (Llama 3 70B) for parsing:
    - Extract product names
    - Extract price ranges
    - Categorize products
  □ Create product URL scraper:
    POST /api/brands/{id}/products/scrape-url
    - Scrape product page for items
```

#### Week 4: Graph Queries & AI Integration

```yaml
Day 1-2: Cypher Query Development
  □ Brand context query (all related data)
  □ Product retrieval query
  □ Color palette query
  □ Full brand profile query
  
Day 3-4: AI API Integration
  □ Hugging Face Inference API setup:
    - SDXL for image generation (FREE tier)
    - Test with brand prompts
  □ Groq API setup:
    - Llama 3 70B for text generation (FREE tier)
    - Test prompt formatting
    
Day 5-7: Generation Endpoints
  □ POST /api/generate/image
    - Input: { brand_id, prompt, style }
    - Output: { image_url, generation_id }
  □ POST /api/generate/text
    - Input: { brand_id, prompt, type: "headline|body" }
    - Output: { text, generation_id }
```

### Deliverables
✓ Complete brand onboarding flow
✓ Product parsing working (text + URL)
✓ Logo quality check with enhancement option
✓ Graph storing all brand data

---

## Week 5-6: Frontend & Generation

### Goals
- Web application working
- End-to-end generation flow
- User feedback collection

### Tasks

#### Week 5: Frontend Development

```yaml
Day 1-2: React Setup
  □ Create React app with Vite:
    npm create vite@latest frontend -- --template react
  □ Set up React Router
  □ Install Tailwind CSS (free, easy styling)
  □ Configure API client (Axios or fetch)
  □ Create component structure
  
Day 3-4: Brand Onboarding Pages
  □ Step 1: Website URL Input
    - URL input field
    - "Analyze Website" button
    - Loading states
  □ Step 2: Review Scraped Data
    - Show extracted: name, tagline, colors
    - Show logo with quality score
    - Enhancement options if poor quality
  □ Step 3: Product Input
    - Text area for manual input
    - URL input for product pages
    - Parsed products display
    
Day 5-7: Generation & Results Pages
  □ Generation Request Form:
    - Brand selector (dropdown)
    - Prompt input (textarea)
    - Content type (image/text/both)
  □ Results Display:
    - Generated image
    - Generated text
    - Brand consistency score
    - Feedback buttons (👍 👎)
```

#### Week 6: Integration & Feedback

```yaml
Day 1-2: End-to-End Flow
  □ Connect frontend to all API endpoints
  □ Test complete user journey:
    1. Enter website URL
    2. Review extracted data
    3. Fix logo quality
    4. Add products
    5. Generate content
    6. Give feedback
  □ Handle loading states and errors
  
Day 3-4: Feedback System
  □ POST /api/feedback endpoint
  □ Store feedback in Neo4j:
    (Generation)-[:RECEIVED_FEEDBACK]->(Feedback)
  □ Update brand preferences based on feedback
  □ Display feedback history
  
Day 5-7: UI Polish
  □ Responsive design (works on mobile)
  □ Better error messages
  □ Loading animations
  □ Success/failure notifications
```

### Deliverables
✓ Complete web application
✓ Full brand onboarding flow
✓ Generation and feedback working
✓ Clean, usable UI

---

## Week 7-8: Polish & Demo Prep

### Goals
- Bug fixes and optimization
- Deployment to free hosting
- Demo preparation

### Tasks

#### Week 7: Testing & Deployment

```yaml
Day 1-2: Testing
  □ Manual end-to-end testing
  □ Test edge cases:
    - Invalid URLs
    - Websites that block scraping
    - Very slow image generation
  □ Fix bugs found
  
Day 3-4: Deploy Backend to Railway FREE
  □ Create Railway account (if not done)
  □ Connect GitHub repository
  □ Set environment variables:
    - NEO4J_URI
    - NEO4J_USER
    - NEO4J_PASSWORD
    - HUGGINGFACE_TOKEN
    - GROQ_API_KEY
  □ Deploy FastAPI backend
  □ Test Railway URL works
  
Day 5-7: Deploy Frontend to Vercel FREE
  □ Create Vercel account (if not done)
  □ Connect GitHub repository
  □ Set environment variable:
    - VITE_API_URL (Railway backend URL)
  □ Deploy React frontend
  □ Test full application on Vercel URL
```

#### Week 8: Demo Preparation

```yaml
Day 1-2: Demo Content
  □ Create 3-5 demo brands by scraping real websites:
    - Local coffee shop
    - Gym/fitness
    - Restaurant
    - Clothing store
    - Tech startup
  □ Prepare demo scenarios:
    - "Create a summer promotion"
    - "Generate a social media post"
    - "Design a sale announcement"
  □ Test demo flow multiple times
  
Day 3-4: Documentation
  □ Update README.md with final instructions
  □ Create DEMO.md walkthrough
  □ Screenshot key screens
  □ Document known limitations
  
Day 5-7: Presentation
  □ Create PowerPoint/Google Slides:
    - Problem statement
    - Data intake flow (scraping → quality check → products)
    - System architecture
    - GraphRAG explanation
    - Live demo
    - Results and learnings
  □ Practice demo (dry run)
  □ Prepare Q&A answers
  □ Record backup demo video (in case live demo fails)
```

### Deliverables
✓ Deployed on Railway + Vercel (FREE)
✓ Complete documentation
✓ Demo presentation
✓ Backup demo video

---

## Project Structure

```
system-design-capstone/
├── backend/
│   ├── app/
│   │   ├── scraping/
│   │   │   ├── website_scraper.py    # Scrape company info
│   │   │   ├── logo_extractor.py     # Extract logo from page
│   │   │   ├── color_extractor.py    # Extract brand colors
│   │   │   └── product_scraper.py    # Scrape product pages
│   │   ├── quality/
│   │   │   ├── image_quality.py      # Check image quality
│   │   │   └── enhancement.py        # AI logo generation
│   │   ├── generation/
│   │   │   ├── image_generator.py    # Hugging Face SDXL
│   │   │   └── text_generator.py     # Groq Llama 3
│   │   ├── api/
│   │   │   ├── brands.py             # Brand CRUD + scraping
│   │   │   ├── products.py           # Product input
│   │   │   ├── generation.py         # Content generation
│   │   │   └── feedback.py           # User feedback
│   │   ├── core/
│   │   │   ├── config.py             # Environment config
│   │   │   └── neo4j_client.py       # Database connection
│   │   └── main.py                   # FastAPI app
│   ├── requirements.txt
│   └── Procfile                      # For Railway deployment
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── WebsiteInput.jsx      # Step 1: URL input
│   │   │   ├── BrandReview.jsx       # Step 2: Review data
│   │   │   ├── LogoQuality.jsx       # Logo quality check
│   │   │   ├── ProductInput.jsx      # Step 3: Add products
│   │   │   ├── GenerationForm.jsx    # Request generation
│   │   │   └── ResultDisplay.jsx     # Show results
│   │   ├── pages/
│   │   │   ├── Home.jsx
│   │   │   ├── Onboarding.jsx        # Brand onboarding flow
│   │   │   ├── Generate.jsx
│   │   │   └── History.jsx
│   │   ├── services/
│   │   │   └── api.js                # API client
│   │   └── App.jsx
│   ├── package.json
│   └── vercel.json                   # For Vercel deployment
├── database/
│   ├── schema/
│   │   └── init.cypher               # Neo4j schema
│   └── queries/
│       └── brand_queries.cypher      # Common queries
├── .env.example
├── README.md
└── docs/
    └── architecture/
        ├── 00-capstone-scope.md
        └── 07-capstone-implementation.md (this file)
```

---

## Technology Stack (FREE Tier Focus)

```yaml
Backend:
  - Python 3.11
  - FastAPI (web framework)
  - neo4j (Python driver)
  - requests + beautifulsoup4 (web scraping)
  - pillow (image processing)
  - colorthief (color extraction)
  - httpx (async HTTP client for APIs)

Frontend:
  - React 18
  - Vite (build tool)
  - React Router
  - Tailwind CSS (styling)
  - Axios (API client)

Database:
  - Neo4j Aura FREE (cloud graph database)

AI APIs (ALL FREE TIER):
  - Hugging Face Inference API (SDXL image generation)
  - Groq (Llama 3 70B for text)

Hosting (ALL FREE):
  - Railway FREE (backend - 500 hours/month)
  - Vercel FREE (frontend - unlimited)
  - Cloudflare R2 FREE (image storage - 10GB)
```

---

## Cost Estimate

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    MONTHLY COST BREAKDOWN                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Service              Plan          Cost      Notes                         │
│  ───────────────────────────────────────────────────────────────────────   │
│  Neo4j Aura           FREE          $0        50K nodes (plenty!)           │
│  Railway              FREE          $0        500 hours/month               │
│  Vercel               Hobby         $0        Unlimited for hobby           │
│  Cloudflare R2        FREE          $0        10GB storage                  │
│  Hugging Face         FREE          $0        Rate limited but enough       │
│  Groq                 FREE          $0        6000 req/day (plenty!)        │
│  ───────────────────────────────────────────────────────────────────────   │
│  TOTAL                              $0        For development/demo          │
│                                                                              │
│  Optional upgrades if needed:                                                │
│  • Railway Pro: $5/month (more hours)                                       │
│  • Replicate: Pay-per-use ($0.0055/image) - backup for Hugging Face        │
│                                                                              │
│  WORST CASE:                        $5-15/month                             │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Minimal Viable Demo

For the capstone presentation, demonstrate this user flow:

```
1. Professor opens web app (Vercel URL)
   ↓
2. Enters a local business website:
   "https://www.localcoffeeshop.com"
   ↓
3. System shows real-time scraping:
   [✓] Fetching webpage...
   [✓] Extracting company info...
   [→] Finding logo...
   [ ] Analyzing colors...
   ↓
4. Review extracted data:
   - Company: "Local Coffee Co."
   - Tagline: "Freshly roasted daily"
   - Logo: [IMAGE] ⚠️ Quality: 0.48
   - Colors: #4A2C2A, #F5E6D3
   ↓
5. System prompts about logo quality:
   "Your logo appears slightly blurry. Would you like to:
    [A] Generate AI version
    [B] Upload better image  
    [C] Keep as is"
   ↓
6. User adds products:
   "We sell specialty coffee ($15-25),
    cold brew ($5), and merchandise"
   → System parses: Coffee Beans, Cold Brew, Merchandise
   ↓
7. User requests content:
   "Create a summer promotion for iced drinks"
   ↓
8. System generates (30-60 seconds):
   [✓] Loading brand context from graph...
   [✓] Building generation prompt...
   [→] Generating image (Hugging Face SDXL)...
   [ ] Writing marketing copy (Groq Llama 3)...
   ↓
9. Results displayed:
   - Generated image (iced coffee, brand colors)
   - Headline: "Cool Down This Summer"
   - Body copy: "Beat the heat with our..."
   - Brand consistency: ✓
   ↓
10. Professor gives feedback (👍)
    → Show Neo4j Browser with updated graph

**Total demo time: 5-7 minutes**
```

---

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Website blocks scraping | MEDIUM | Have manual input fallback, use headers |
| Hugging Face rate limited | LOW | Groq as backup, cache results |
| Groq API slow | LOW | Use Hugging Face text models as backup |
| Neo4j Aura cold start | LOW | Keep warm with periodic pings |
| Railway sleeps after inactivity | MEDIUM | Wake up before demo, use cron ping |
| Time overrun | HIGH | Cut scope: focus on scraping demo only |
| Free tier limits exceeded | LOW | Monitor usage, use backup services |

---

## Success Criteria

### Technical
- [ ] System generates image + text in < 60 seconds
- [ ] Brand consistency score > 0.80 average
- [ ] Handle 5 concurrent users without crashing
- [ ] No critical bugs during demo

### Academic
- [ ] Clear architecture documentation
- [ ] Code is well-commented
- [ ] GraphRAG approach explained clearly
- [ ] Demo runs smoothly

### Presentation
- [ ] Professors understand the system
- [ ] Live demo succeeds
- [ ] Q&A handled confidently
- [ ] Backup demo video ready

---

## Post-Capstone Opportunities

If you want to extend this project:

1. **Add more brands** - Expand to 20-50 brands
2. **Fine-tune models** - Train custom LoRA adapters
3. **Multi-modal feedback** - Voice/video input
4. **A/B testing** - Compare generation strategies
5. **Mobile app** - React Native version
6. **Analytics dashboard** - Track usage patterns
7. **Open source** - Share on GitHub for community

---

## Resources

### Free Services to Sign Up
| Service | URL | What You Get |
|---------|-----|--------------|
| Neo4j Aura | aura.neo4j.io | Free graph database |
| Hugging Face | huggingface.co | Free AI image generation |
| Groq | groq.com | Free Llama 3 70B access |
| Vercel | vercel.com | Free frontend hosting |
| Railway | railway.app | Free backend hosting |
| Cloudflare R2 | cloudflare.com | Free image storage |

### Learning Materials
- Neo4j GraphAcademy: https://graphacademy.neo4j.com/
- FastAPI Tutorial: https://fastapi.tiangolo.com/tutorial/
- React Docs: https://react.dev/
- Web Scraping with BeautifulSoup: https://realpython.com/beautiful-soup-web-scraper-python/
- Hugging Face Inference API: https://huggingface.co/docs/api-inference/
- Groq Documentation: https://console.groq.com/docs

---

## Timeline Checkpoints

| Week | Checkpoint | Demo-able? |
|------|-----------|------------|
| 2 | Backend + Scraping working | ⚠️ API only (Postman demo) |
| 4 | Full data intake pipeline | ⚠️ Can show graph in Neo4j Browser |
| 6 | Web app functional | ✅ Yes! Core demo ready |
| 8 | Polished + deployed | ✅ Yes! Full presentation ready |

---

**Remember**: The goal is to demonstrate understanding of:
- **Web scraping** (data extraction)
- **Image processing** (quality assessment)
- **GraphRAG** (knowledge graph + AI)
- **Full-stack development** (React + FastAPI + Neo4j)

Focus on making the data intake pipeline clear and the core generation working. You don't need production-grade infrastructure—this is a learning project!

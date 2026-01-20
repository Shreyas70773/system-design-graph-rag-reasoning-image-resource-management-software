# Capstone Project Scope
## Near-Zero Cost Architecture for Academic Demonstration

**Target**: College Capstone Project  
**Scale**: 5-10 users  
**Budget**: < $15/month (mostly free tier)  
**Timeline**: 8-10 weeks

---

## Table of Contents
1. [Cost Strategy](#cost-strategy)
2. [Data Intake Pipeline](#data-intake-pipeline)
3. [System Architecture](#system-architecture)
4. [Technology Choices](#technology-choices)
5. [Learning Objectives](#learning-objectives)

---

## Cost Strategy

### Philosophy: Use Free Tiers + Local Development

The key to keeping costs under $15/month is:
1. **Local development** - Run everything on your laptop during development
2. **Free tier APIs** - Use free quotas from OpenAI, Hugging Face, etc.
3. **Free hosting** - Deploy on free platforms (Railway, Render, Vercel)
4. **Open source models** - Use free local models where possible

### Cost Breakdown: < $15/month

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    NEAR-ZERO COST ARCHITECTURE                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  COMPONENT              SERVICE                    COST                     │
│  ─────────────────────────────────────────────────────────────────────────  │
│                                                                              │
│  Database               Neo4j Aura FREE           $0/month                  │
│                         (50K nodes, 175K rels)    ✓ Enough for capstone     │
│                                                                              │
│  Backend Hosting        Railway FREE              $0/month                  │
│                         (500 hours/month)         ✓ Or Render free tier     │
│                                                                              │
│  Frontend Hosting       Vercel FREE               $0/month                  │
│                         (Unlimited for hobby)     ✓ Perfect for React       │
│                                                                              │
│  Image Storage          Cloudflare R2 FREE        $0/month                  │
│                         (10GB storage, 10M req)   ✓ More than enough        │
│                                                                              │
│  Image Generation       Hugging Face FREE         $0/month                  │
│                         (Inference API quota)     ✓ SDXL available          │
│                         OR Replicate ($0.0055/img)                          │
│                                                                              │
│  Text Generation        OpenAI GPT-4o-mini        ~$0.50/month              │
│                         (Free $5 credit for new)  ✓ Very cheap              │
│                         OR Groq FREE tier         $0/month                  │
│                                                                              │
│  Web Scraping           BeautifulSoup + Requests  $0 (Python libraries)    │
│                                                                              │
│  Logo Extraction        Local Python (Pillow)     $0 (runs on your machine)│
│                                                                              │
│  Domain (Optional)      Freenom / .tk domain      $0                       │
│                         OR use Railway subdomain                            │
│                                                                              │
│  ─────────────────────────────────────────────────────────────────────────  │
│                                                                              │
│  ESTIMATED TOTAL:       $0 - $5/month (development)                        │
│                         $5 - $15/month (if using paid APIs for demo)       │
│                                                                              │
│  WORST CASE:            500 generations × $0.02 = $10/month                │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Free Tier Limits (What You Get)

| Service | Free Tier | Enough For Capstone? |
|---------|-----------|---------------------|
| **Neo4j Aura** | 50K nodes, 175K relationships | ✅ Yes (we need ~1000) |
| **Railway** | 500 hours/month, 512MB RAM | ✅ Yes for demo |
| **Render** | 750 hours/month | ✅ Alternative option |
| **Vercel** | Unlimited static hosting | ✅ Yes for React app |
| **Cloudflare R2** | 10GB storage | ✅ Yes (images ~1MB each) |
| **Hugging Face** | ~1000 inference calls/day | ✅ Yes for development |
| **Groq** | 30 requests/min, 6000/day | ✅ Yes (Llama 3 70B!) |
| **OpenAI** | $5 free credit (new accounts) | ✅ Yes for demos |

---

## Data Intake Pipeline

### The Complete Flow (How Data Enters the System)

This is the most important part to understand. Here's exactly what happens when a client adds their brand:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    DATA INTAKE PIPELINE                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  STEP 1: CLIENT ENTERS WEBSITE URL                                          │
│  ═══════════════════════════════════════════════════════════════════════   │
│                                                                              │
│     Client Input: "https://www.nike.com"                                    │
│                         │                                                    │
│                         ▼                                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                  WEB SCRAPER MODULE                                  │   │
│  │                                                                       │   │
│  │  What it does:                                                        │   │
│  │  1. Fetches the HTML of the homepage                                 │   │
│  │  2. Extracts text content (company description, taglines)            │   │
│  │  3. Finds the logo (looks for <img> tags with "logo" in class/id)   │   │
│  │  4. Extracts brand colors (from CSS, common elements)                │   │
│  │  5. Gets meta description and title                                   │   │
│  │                                                                       │   │
│  │  Libraries used:                                                      │   │
│  │  • requests - fetch webpage                                          │   │
│  │  • BeautifulSoup - parse HTML                                        │   │
│  │  • Pillow - process images                                           │   │
│  │  • colorthief - extract colors from logo                             │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                         │                                                    │
│                         ▼                                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                  EXTRACTED DATA                                      │   │
│  │                                                                       │   │
│  │  {                                                                    │   │
│  │    "company_name": "Nike",                                           │   │
│  │    "tagline": "Just Do It",                                          │   │
│  │    "description": "Athletic footwear and apparel...",                │   │
│  │    "logo_url": "https://nike.com/logo.png",                          │   │
│  │    "primary_colors": ["#000000", "#FFFFFF", "#F26522"],              │   │
│  │    "industry_guess": "Sports & Athletics"                            │   │
│  │  }                                                                    │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                         │                                                    │
│                         ▼                                                    │
│                                                                              │
│  STEP 2: LOGO QUALITY CHECK                                                 │
│  ═══════════════════════════════════════════════════════════════════════   │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                  IMAGE QUALITY ANALYZER                              │   │
│  │                                                                       │   │
│  │  Checks:                                                              │   │
│  │  • Resolution: Is it at least 200x200 pixels?                        │   │
│  │  • Format: Is it PNG/SVG (transparent background)?                   │   │
│  │  • Clarity: Is it blurry? (Laplacian variance check)                │   │
│  │  • File size: Is it reasonable (not a placeholder)?                  │   │
│  │                                                                       │   │
│  │  Quality Score: 0.0 - 1.0                                            │   │
│  │  • > 0.7: Good quality ✓                                             │   │
│  │  • 0.4 - 0.7: Acceptable ⚠️                                          │   │
│  │  • < 0.4: Poor quality ❌                                            │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                         │                                                    │
│              ┌──────────┴──────────┐                                        │
│              │                     │                                        │
│              ▼                     ▼                                        │
│         GOOD QUALITY          POOR QUALITY                                  │
│              │                     │                                        │
│              │                     ▼                                        │
│              │         ┌─────────────────────────────────────┐             │
│              │         │  PROMPT USER                         │             │
│              │         │                                      │             │
│              │         │  "Your logo appears to be low        │             │
│              │         │   quality. Would you like us to:     │             │
│              │         │                                      │             │
│              │         │   A) Generate an AI version          │             │
│              │         │   B) Upload a better image           │             │
│              │         │   C) Keep as is"                     │             │
│              │         └─────────────────────────────────────┘             │
│              │                     │                                        │
│              │         ┌───────────┼───────────┐                           │
│              │         │           │           │                           │
│              │         ▼           ▼           ▼                           │
│              │     OPTION A    OPTION B    OPTION C                        │
│              │         │           │           │                           │
│              │         ▼           │           │                           │
│              │  ┌──────────────┐   │           │                           │
│              │  │ AI LOGO GEN  │   │           │                           │
│              │  │              │   │           │                           │
│              │  │ Uses SDXL or │   │           │                           │
│              │  │ DALL-E to    │   │           │                           │
│              │  │ create a     │   │           │                           │
│              │  │ clean logo   │   │           │                           │
│              │  │ based on     │   │           │
│              │  │ description  │   │           │                           │
│              │  └──────────────┘   │           │                           │
│              │         │           │           │                           │
│              └─────────┴───────────┴───────────┘                           │
│                         │                                                    │
│                         ▼                                                    │
│                                                                              │
│  STEP 3: CLIENT ADDS PRODUCTS/SERVICES                                      │
│  ═══════════════════════════════════════════════════════════════════════   │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                  PRODUCT INPUT OPTIONS                               │   │
│  │                                                                       │   │
│  │  Client can choose:                                                   │   │
│  │                                                                       │   │
│  │  ┌───────────────────────────────────────────────────────────────┐   │   │
│  │  │  OPTION A: TEXT INPUT                                         │   │   │
│  │  │                                                                │   │   │
│  │  │  "We sell:                                                    │   │   │
│  │  │   - Running shoes ($80-$200)                                  │   │   │
│  │  │   - Athletic apparel ($30-$100)                               │   │   │
│  │  │   - Sports accessories"                                       │   │   │
│  │  │                                                                │   │   │
│  │  │  → Parsed with NLP (GPT) to extract:                          │   │   │
│  │  │    • Product names                                            │   │   │
│  │  │    • Categories                                               │   │   │
│  │  │    • Price ranges                                             │   │   │
│  │  └───────────────────────────────────────────────────────────────┘   │   │
│  │                                                                       │   │
│  │  ┌───────────────────────────────────────────────────────────────┐   │   │
│  │  │  OPTION B: PRODUCT PAGE URL                                   │   │   │
│  │  │                                                                │   │   │
│  │  │  "https://nike.com/running-shoes"                             │   │   │
│  │  │                                                                │   │   │
│  │  │  → Scraper extracts:                                          │   │   │
│  │  │    • Product images                                           │   │   │
│  │  │    • Product names                                            │   │   │
│  │  │    • Prices                                                   │   │   │
│  │  │    • Descriptions                                             │   │   │
│  │  └───────────────────────────────────────────────────────────────┘   │   │
│  │                                                                       │   │
│  │  For each product image:                                             │   │
│  │  → Same quality check as logo                                        │   │
│  │  → Offer AI enhancement if poor quality                              │   │
│  │                                                                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                         │                                                    │
│                         ▼                                                    │
│                                                                              │
│  STEP 4: STORE IN KNOWLEDGE GRAPH                                           │
│  ═══════════════════════════════════════════════════════════════════════   │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                  NEO4J GRAPH DATABASE                                │   │
│  │                                                                       │   │
│  │         ┌─────────────┐                                              │   │
│  │         │   BRAND     │                                              │   │
│  │         │   "Nike"    │                                              │   │
│  │         └──────┬──────┘                                              │   │
│  │                │                                                      │   │
│  │    ┌───────────┼───────────┬───────────┐                             │   │
│  │    │           │           │           │                             │   │
│  │    ▼           ▼           ▼           ▼                             │   │
│  │ ┌──────┐  ┌──────────┐ ┌────────┐ ┌──────────┐                      │   │
│  │ │ LOGO │  │ COLORS   │ │PRODUCTS│ │ CONTENT  │                      │   │
│  │ │      │  │          │ │        │ │          │                      │   │
│  │ │url:..│  │#000000   │ │Shoes   │ │tagline:  │                      │   │
│  │ │qual:.│  │#FFFFFF   │ │Apparel │ │"Just Do  │                      │   │
│  │ └──────┘  └──────────┘ │Access. │ │ It"      │                      │   │
│  │                        └────────┘ └──────────┘                      │   │
│  │                                                                       │   │
│  │  Relationships:                                                       │   │
│  │  (Brand)-[:HAS_LOGO]->(Logo)                                         │   │
│  │  (Brand)-[:USES_COLOR]->(Color)                                      │   │
│  │  (Brand)-[:SELLS]->(Product)                                         │   │
│  │  (Brand)-[:HAS_TAGLINE]->(Content)                                   │   │
│  │                                                                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## System Architecture

### Simplified Architecture (Runs Locally + Free Cloud)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    CAPSTONE ARCHITECTURE (< $15/month)                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  USER'S BROWSER                                                              │
│       │                                                                      │
│       ▼                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  FRONTEND (React) - Hosted on Vercel FREE                           │   │
│  │                                                                       │   │
│  │  Pages:                                                               │   │
│  │  • Home - Enter your website URL                                     │   │
│  │  • Brand Setup - Review extracted data, add products                 │   │
│  │  • Generate - Create marketing content                               │   │
│  │  • History - View past generations                                   │   │
│  └────────────────────────────┬────────────────────────────────────────┘   │
│                               │ API calls                                   │
│                               ▼                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  BACKEND (FastAPI) - Hosted on Railway FREE                          │   │
│  │                                                                       │   │
│  │  ┌───────────────────────────────────────────────────────────────┐   │   │
│  │  │  SCRAPING MODULE                                              │   │   │
│  │  │  • scrape_website(url) → company info                         │   │   │
│  │  │  • extract_logo(url) → logo image                             │   │   │
│  │  │  • extract_colors(image) → color palette                      │   │   │
│  │  │  • scrape_products(url) → product list                        │   │   │
│  │  └───────────────────────────────────────────────────────────────┘   │   │
│  │                                                                       │   │
│  │  ┌───────────────────────────────────────────────────────────────┐   │   │
│  │  │  QUALITY MODULE                                               │   │   │
│  │  │  • check_image_quality(image) → score                         │   │   │
│  │  │  • enhance_image(image) → better image (if needed)            │   │   │
│  │  │  • generate_logo(description) → AI logo                       │   │   │
│  │  └───────────────────────────────────────────────────────────────┘   │   │
│  │                                                                       │   │
│  │  ┌───────────────────────────────────────────────────────────────┐   │   │
│  │  │  GENERATION MODULE                                            │   │   │
│  │  │  • generate_image(prompt, brand_context) → image              │   │   │
│  │  │  • generate_text(prompt, brand_voice) → copy                  │   │   │
│  │  │  • validate_brand_consistency(output, brand) → score          │   │   │
│  │  └───────────────────────────────────────────────────────────────┘   │   │
│  │                                                                       │   │
│  └────────────────────────────┬────────────────────────────────────────┘   │
│                               │                                             │
│          ┌────────────────────┼────────────────────┐                       │
│          │                    │                    │                       │
│          ▼                    ▼                    ▼                       │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                 │
│  │   Neo4j      │    │  Hugging Face│    │    Groq      │                 │
│  │   Aura FREE  │    │   FREE tier  │    │   FREE tier  │                 │
│  │              │    │              │    │              │                 │
│  │  Brand data  │    │  SDXL image  │    │  Llama 3 70B │                 │
│  │  Products    │    │  generation  │    │  text gen    │                 │
│  │  Preferences │    │              │    │              │                 │
│  └──────────────┘    └──────────────┘    └──────────────┘                 │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  IMAGE STORAGE - Cloudflare R2 FREE                                  │   │
│  │  • Stores generated images                                           │   │
│  │  • Stores uploaded logos                                             │   │
│  │  • CDN for fast delivery                                             │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Technology Choices (With Learning Explanations)

### Why Each Technology?

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    TECHNOLOGY DECISIONS EXPLAINED                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  PYTHON + FASTAPI (Backend)                                                 │
│  ═════════════════════════════════════════════════════════════════════════  │
│                                                                              │
│  Why Python?                                                                 │
│  • Most popular for AI/ML projects                                          │
│  • Excellent libraries for web scraping (BeautifulSoup, Scrapy)            │
│  • Great image processing libraries (Pillow, OpenCV)                        │
│  • Easy to learn and debug                                                  │
│                                                                              │
│  Why FastAPI?                                                                │
│  • Modern, fast Python web framework                                        │
│  • Automatic API documentation (Swagger UI)                                 │
│  • Built-in async support (important for API calls)                        │
│  • Type hints make code more readable                                       │
│                                                                              │
│  What you'll learn:                                                          │
│  ✓ Building REST APIs                                                       │
│  ✓ Async programming in Python                                              │
│  ✓ API design patterns                                                      │
│  ✓ Error handling and validation                                            │
│                                                                              │
│  ─────────────────────────────────────────────────────────────────────────  │
│                                                                              │
│  NEO4J (Graph Database)                                                     │
│  ═════════════════════════════════════════════════════════════════════════  │
│                                                                              │
│  Why a Graph Database?                                                       │
│  • Perfect for storing relationships (brand → products → colors)           │
│  • Easy to query connected data                                             │
│  • Visual tool (Neo4j Browser) for understanding data                       │
│  • Free tier is generous enough for learning                                │
│                                                                              │
│  Why Neo4j specifically?                                                     │
│  • Industry leader with great documentation                                 │
│  • Free cloud tier (Aura)                                                   │
│  • Cypher query language is intuitive                                       │
│  • Built-in vector search (for semantic similarity)                        │
│                                                                              │
│  What you'll learn:                                                          │
│  ✓ Graph data modeling                                                      │
│  ✓ Cypher query language                                                    │
│  ✓ Relationship-based data retrieval                                        │
│  ✓ Why graphs beat tables for connected data                               │
│                                                                              │
│  ─────────────────────────────────────────────────────────────────────────  │
│                                                                              │
│  REACT (Frontend)                                                           │
│  ═════════════════════════════════════════════════════════════════════════  │
│                                                                              │
│  Why React?                                                                  │
│  • Most popular frontend framework                                          │
│  • Component-based (reusable pieces)                                        │
│  • Great ecosystem (libraries for everything)                               │
│  • In-demand job skill                                                      │
│                                                                              │
│  Why Vite (build tool)?                                                     │
│  • Much faster than Create React App                                        │
│  • Simple configuration                                                     │
│  • Hot reload (see changes instantly)                                       │
│                                                                              │
│  What you'll learn:                                                          │
│  ✓ Component-based UI development                                           │
│  ✓ State management (useState, useEffect)                                  │
│  ✓ API integration (fetch/axios)                                            │
│  ✓ Modern JavaScript/TypeScript                                             │
│                                                                              │
│  ─────────────────────────────────────────────────────────────────────────  │
│                                                                              │
│  HUGGING FACE + GROQ (AI APIs)                                              │
│  ═════════════════════════════════════════════════════════════════════════  │
│                                                                              │
│  Why Hugging Face?                                                          │
│  • FREE inference API for image generation                                  │
│  • Access to SDXL and other models                                          │
│  • No GPU needed on your machine                                            │
│  • Industry standard for ML models                                          │
│                                                                              │
│  Why Groq?                                                                   │
│  • FREE tier with generous limits                                           │
│  • Access to Llama 3 70B (very powerful)                                   │
│  • Extremely fast inference                                                 │
│  • No credit card required                                                  │
│                                                                              │
│  What you'll learn:                                                          │
│  ✓ Working with AI APIs                                                     │
│  ✓ Prompt engineering                                                       │
│  ✓ Handling async API calls                                                 │
│  ✓ Error handling for external services                                    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Learning Objectives

### What You'll Actually Learn Building This

```
WEEK 1-2: Foundation
────────────────────
□ Setting up a Python project with virtual environments
□ Understanding FastAPI routing and endpoints
□ Connecting to Neo4j from Python
□ Basic Cypher queries (CREATE, MATCH, RETURN)
□ Environment variables and configuration

WEEK 3-4: Web Scraping & Data Pipeline
──────────────────────────────────────
□ HTTP requests and responses
□ HTML parsing with BeautifulSoup
□ Image processing with Pillow
□ Color extraction algorithms
□ Handling edge cases (websites that block scraping)
□ Data validation and cleaning

WEEK 5-6: AI Integration
────────────────────────
□ Working with REST APIs (Hugging Face, Groq)
□ Prompt engineering for good outputs
□ Async/await in Python
□ Rate limiting and retry logic
□ Image quality assessment

WEEK 7-8: Frontend & Deployment
───────────────────────────────
□ React components and hooks
□ Form handling and validation
□ API integration from frontend
□ Docker basics
□ Deploying to free cloud services
□ Environment management (dev vs prod)
```

---

## Demo Scenario

### What Happens When a Client Uses the System

```
DEMO SCRIPT (5 minutes)
═══════════════════════

1. CLIENT ENTERS WEBSITE (30 seconds)
   ────────────────────────────────
   Input: "https://www.localcoffee.com"
   
   System shows: "Analyzing your website..."
   
   Loading states:
   [✓] Fetching webpage
   [✓] Extracting company info
   [✓] Finding logo
   [→] Analyzing colors
   [ ] Checking image quality

2. REVIEW EXTRACTED DATA (60 seconds)
   ──────────────────────────────────
   System displays:
   ┌────────────────────────────────────────┐
   │ Company: Local Coffee Co.              │
   │ Tagline: "Freshly roasted, locally..." │
   │ Industry: Food & Beverage              │
   │                                        │
   │ Logo: [IMAGE]                          │
   │ Quality: ⚠️ Medium (0.52)              │
   │                                        │
   │ "Your logo appears slightly blurry.   │
   │  Would you like to:"                   │
   │  [Generate AI Version]                 │
   │  [Upload Better Image]                 │
   │  [Keep As Is]                          │
   │                                        │
   │ Colors Detected:                       │
   │ ■ #4A2C2A (Brown)                      │
   │ ■ #F5E6D3 (Cream)                      │
   │ ■ #2D5016 (Green)                      │
   └────────────────────────────────────────┘

3. ADD PRODUCTS (60 seconds)
   ─────────────────────────
   Client clicks "Add Products"
   
   Options shown:
   • Enter text description
   • Provide product page URL
   
   Client types:
   "We sell specialty coffee beans ($15-25),
    cold brew ($5), and coffee merchandise 
    like mugs and t-shirts ($10-30)"
   
   System parses and shows:
   ┌────────────────────────────────────────┐
   │ Products Detected:                     │
   │ ✓ Coffee Beans - $15-25               │
   │ ✓ Cold Brew - $5                       │
   │ ✓ Mugs - $10-30                        │
   │ ✓ T-Shirts - $10-30                    │
   │                                        │
   │ [Confirm] [Edit]                       │
   └────────────────────────────────────────┘

4. GENERATE CONTENT (90 seconds)
   ─────────────────────────────
   Client enters: "Create a summer promotion 
   for our iced coffee drinks"
   
   System shows real-time progress:
   [✓] Loading brand context from graph
   [✓] Building generation prompt
   [→] Generating image...
   [ ] Writing marketing copy
   [ ] Checking brand consistency
   
   Result displayed:
   ┌────────────────────────────────────────┐
   │ [GENERATED IMAGE]                      │
   │ Iced coffee with summer vibes          │
   │ Uses brand colors (brown, cream)       │
   │                                        │
   │ Headline: "Cool Down This Summer"      │
   │ Body: "Beat the heat with our..."     │
   │                                        │
   │ Brand Consistency: 0.89 ✓              │
   │                                        │
   │ [👍 Like] [👎 Dislike] [Regenerate]   │
   └────────────────────────────────────────┘

5. SHOW KNOWLEDGE GRAPH (60 seconds)
   ──────────────────────────────────
   Open Neo4j Browser
   
   Run query: 
   MATCH (b:Brand {name: "Local Coffee Co."})-[r]->(n)
   RETURN b, r, n
   
   Shows visual graph:
        [Brand]
        /  |  \
   [Logo] [Colors] [Products]
             |         |
        [#4A2C2A]  [Coffee Beans]
        [#F5E6D3]  [Cold Brew]
        [#2D5016]  [Merchandise]
```

---

## Next Steps

1. **Read [07-capstone-implementation.md](./07-capstone-implementation.md)** for week-by-week tasks
2. **Set up your development environment** (Python, Node.js, Docker)
3. **Create free accounts** on Neo4j Aura, Hugging Face, Groq, Vercel, Railway
4. **Start coding!** Begin with the web scraping module

---

## Quick Reference: Free Services to Sign Up For

| Service | URL | What You Get |
|---------|-----|--------------|
| **Neo4j Aura** | aura.neo4j.io | Free graph database |
| **Hugging Face** | huggingface.co | Free AI inference |
| **Groq** | groq.com | Free Llama 3 access |
| **Vercel** | vercel.com | Free frontend hosting |
| **Railway** | railway.app | Free backend hosting |
| **Cloudflare R2** | cloudflare.com | Free image storage |
| **GitHub** | github.com | Free code hosting |

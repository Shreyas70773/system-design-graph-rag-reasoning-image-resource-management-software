# Brand-Aligned Content Generation Platform
## Graph-Augmented AI Content System (Capstone Project)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Architecture](https://img.shields.io/badge/Architecture-GraphRAG-blue.svg)](docs/architecture/00-capstone-scope.md)
[![Status](https://img.shields.io/badge/Status-In%20Development-green.svg)](docs/architecture/07-capstone-implementation.md)
[![Budget](https://img.shields.io/badge/Budget-<%20$15/month-brightgreen.svg)](docs/architecture/00-capstone-scope.md#cost-strategy)

---

## 🎓 Project Overview

A **college capstone project** demonstrating a graph-augmented content generation system that combines web scraping, AI image generation, and knowledge graph technology to create brand-consistent marketing content.

**Budget**: < $15/month using FREE tier services  
**Scale**: 5-10 users for academic demonstration

### What This System Does

1. **Client enters their website URL** → System scrapes company info and logo
2. **Quality check on logo** → If poor quality, offers AI-generated version
3. **Client adds products/services** → Text description or product page URL
4. **Everything stored in knowledge graph** → Neo4j for relationships
5. **Generate brand-consistent content** → Images and copy that match the brand

### Key Learning Objectives

- 🕷️ **Web Scraping** - Extract brand data from websites (BeautifulSoup)
- 🖼️ **Image Quality Assessment** - Programmatic quality checks (Pillow)
- 🧠 **GraphRAG Knowledge Base** - Neo4j for brand context retrieval
- 🤖 **AI Content Generation** - Images (Hugging Face) + Text (Groq)
- 🌐 **Full-Stack Development** - React frontend + FastAPI backend

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| **[00-capstone-scope.md](docs/architecture/00-capstone-scope.md)** | ⭐ **START HERE** - Cost breakdown, data pipeline, architecture |
| **[07-capstone-implementation.md](docs/architecture/07-capstone-implementation.md)** | 8-week implementation plan with tasks |

### Production Reference (For Learning)

| Document | Description |
|----------|-------------|
| [01-system-overview.md](docs/architecture/01-system-overview.md) | Production architecture patterns |
| [02-graphrag-design.md](docs/architecture/02-graphrag-design.md) | Neo4j schema design |
| [03-image-generation-pipeline.md](docs/architecture/03-image-generation-pipeline.md) | Generation pipeline concepts |
| [04-agent-orchestration.md](docs/architecture/04-agent-orchestration.md) | Multi-agent architecture |
| [05-monitoring-framework.md](docs/architecture/05-monitoring-framework.md) | Observability patterns |
| [06-implementation-roadmap.md](docs/architecture/06-implementation-roadmap.md) | Enterprise rollout strategy |

---

## 🔄 Data Intake Pipeline

This is how brand data enters the system:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    DATA INTAKE PIPELINE                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  STEP 1: WEBSITE URL                                                         │
│  ──────────────────                                                          │
│  Client enters: "https://www.localcoffee.com"                               │
│                                                                              │
│          ┌──────────────────────────────────────────────┐                   │
│          │  WEB SCRAPER                                  │                   │
│          │  • Extracts company name, tagline            │                   │
│          │  • Finds logo image                          │                   │
│          │  • Detects brand colors                      │                   │
│          │  • Gets meta description                     │                   │
│          └───────────────────────┬──────────────────────┘                   │
│                                  │                                          │
│                                  ▼                                          │
│  STEP 2: LOGO QUALITY CHECK                                                 │
│  ─────────────────────────                                                  │
│          ┌──────────────────────────────────────────────┐                   │
│          │  IMAGE QUALITY ANALYZER                       │                   │
│          │  • Check resolution (min 200x200)            │                   │
│          │  • Check blur (Laplacian variance)           │                   │
│          │  • Calculate quality score (0.0 - 1.0)       │                   │
│          └───────────────────────┬──────────────────────┘                   │
│                                  │                                          │
│              ┌───────────────────┴───────────────────┐                      │
│              │                                       │                      │
│         QUALITY > 0.7                          QUALITY < 0.7                │
│         ✅ Accept                              ⚠️ Prompt User               │
│                                                      │                      │
│                                     ┌────────────────┼────────────────┐     │
│                                     │                │                │     │
│                               [Generate AI]    [Upload New]    [Keep As-Is] │
│                                     │                │                │     │
│                                     ▼                │                │     │
│                              ┌────────────┐          │                │     │
│                              │ AI LOGO GEN│          │                │     │
│                              │ (SDXL/HF)  │          │                │     │
│                              └────────────┘          │                │     │
│                                     │                │                │     │
│              ┌──────────────────────┴────────────────┴────────────────┘     │
│              │                                                              │
│              ▼                                                              │
│  STEP 3: ADD PRODUCTS/SERVICES                                              │
│  ───────────────────────────                                                │
│          ┌──────────────────────────────────────────────┐                   │
│          │  Two Input Methods:                          │                   │
│          │                                               │                   │
│          │  A) TEXT INPUT:                              │                   │
│          │     "We sell coffee ($15), cold brew ($5)"   │                   │
│          │     → Parsed with Groq Llama 3               │                   │
│          │                                               │                   │
│          │  B) PRODUCT PAGE URL:                        │                   │
│          │     "https://localcoffee.com/products"       │                   │
│          │     → Scraped for product info               │                   │
│          └───────────────────────┬──────────────────────┘                   │
│                                  │                                          │
│                                  ▼                                          │
│  STEP 4: STORE IN KNOWLEDGE GRAPH                                           │
│  ───────────────────────────────                                            │
│          ┌──────────────────────────────────────────────┐                   │
│          │  NEO4J GRAPH                                  │                   │
│          │                                               │                   │
│          │         ┌────────┐                           │                   │
│          │         │ BRAND  │                           │                   │
│          │         └───┬────┘                           │                   │
│          │     ┌───────┼───────┬───────┐               │                   │
│          │     ▼       ▼       ▼       ▼               │                   │
│          │  [Logo] [Colors] [Products] [Content]       │                   │
│          │                                               │                   │
│          └──────────────────────────────────────────────┘                   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🏗️ System Architecture

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
│  │  • Step 1: Enter website URL                                        │   │
│  │  • Step 2: Review scraped data + fix logo quality                   │   │
│  │  • Step 3: Add products/services                                    │   │
│  │  • Step 4: Generate content                                         │   │
│  └────────────────────────────────┬────────────────────────────────────┘   │
│                                   │ API calls                               │
│                                   ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  BACKEND (FastAPI) - Hosted on Railway FREE                          │   │
│  │                                                                       │   │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐    │   │
│  │  │  Scraping  │  │  Quality   │  │ Generation │  │  Feedback  │    │   │
│  │  │   Module   │  │   Module   │  │   Module   │  │   Module   │    │   │
│  │  └────────────┘  └────────────┘  └────────────┘  └────────────┘    │   │
│  └────────────────────────────────┬────────────────────────────────────┘   │
│                                   │                                         │
│          ┌────────────────────────┼────────────────────┐                   │
│          │                        │                    │                   │
│          ▼                        ▼                    ▼                   │
│  ┌──────────────┐        ┌──────────────┐     ┌──────────────┐            │
│  │ Neo4j Aura   │        │ Hugging Face │     │    Groq      │            │
│  │   FREE       │        │    FREE      │     │    FREE      │            │
│  │ Graph DB     │        │ SDXL Images  │     │ Llama 3 Text │            │
│  └──────────────┘        └──────────────┘     └──────────────┘            │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Cloudflare R2 FREE - Image Storage (10GB)                           │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 💰 Cost Breakdown (FREE Tier Focus)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    MONTHLY COST: $0 - $15                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Service              Tier          Cost      What You Get                  │
│  ───────────────────────────────────────────────────────────────────────   │
│  Neo4j Aura           FREE          $0        50K nodes, 175K relationships │
│  Railway              FREE          $0        500 hours/month backend       │
│  Vercel               Hobby         $0        Unlimited frontend hosting    │
│  Cloudflare R2        FREE          $0        10GB image storage            │
│  Hugging Face         FREE          $0        SDXL image generation         │
│  Groq                 FREE          $0        Llama 3 70B text generation   │
│  ───────────────────────────────────────────────────────────────────────   │
│  TOTAL                              $0        For development & demo!       │
│                                                                              │
│  Optional if you exceed free tiers:                                         │
│  • Railway Pro:       $5/month                                              │
│  • Replicate backup:  ~$5/month (pay per image)                            │
│                                                                              │
│  WORST CASE:                        ~$15/month                              │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites
```bash
# Required software
- Python 3.11+
- Node.js 18+

# Free accounts to create
- Neo4j Aura (aura.neo4j.io)
- Hugging Face (huggingface.co)
- Groq (groq.com)
- Vercel (vercel.com)
- Railway (railway.app)
```

### Local Development Setup

```bash
# 1. Clone repository
git clone https://github.com/Shreyas70773/system-design-graph-rag-reasoning-image-resource-management-software.git
cd system-design-capstone

# 2. Backend setup
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env with your API keys:
# - NEO4J_URI (from Aura dashboard)
# - NEO4J_USER
# - NEO4J_PASSWORD
# - HUGGINGFACE_TOKEN
# - GROQ_API_KEY

# 4. Frontend setup
cd ../frontend
npm install
cd ..

# 5. Run both backend + frontend with one command
npm install
npm run dev
# API docs: http://localhost:8000/docs
# App: http://localhost:5173
```

### Local ComfyUI Mode (No Cloud Image Provider)

- Install ComfyUI Desktop (Windows) and run it at least once.
- Backend auto-detects ComfyUI on http://127.0.0.1:8001 and http://127.0.0.1:8188.
- If ComfyUI is not running, backend can auto-start it when a Comfy run is requested.
- Put at least one checkpoint file in Documents/ComfyUI/models/checkpoints.
- In Research Lab, choose image provider `comfyui` and leave workflow JSON blank to use auto-workflow.

---

## 🎯 Demo Flow (5-7 Minutes)

Perfect for capstone presentation:

1. **Enter Website URL** → "https://www.localcoffeeshop.com"
2. **Review Scraped Data** → Name, tagline, colors extracted
3. **Check Logo Quality** → System detects 0.48 quality score
4. **Offer Enhancement** → "Generate AI version" / "Upload" / "Keep"
5. **Add Products** → "We sell coffee, cold brew, merchandise"
6. **Generate Content** → "Create a summer iced coffee promotion"
7. **View Results** → Image + headline + body copy + brand score
8. **Show Graph** → Open Neo4j Browser to visualize relationships

---

## 📅 8-Week Implementation Timeline

| Week | Focus | Deliverable |
|------|-------|-------------|
| 1-2 | **Foundation** | Backend + Database + Scraping module |
| 3-4 | **Data Intake** | Logo quality + Product parsing + Graph storage |
| 5-6 | **Generation** | AI APIs + Frontend + Feedback |
| 7-8 | **Polish** | Testing + Deployment + Demo prep |

See [07-capstone-implementation.md](docs/architecture/07-capstone-implementation.md) for detailed week-by-week tasks.

---

## 📊 Technology Stack

| Component | Choice | Why |
|-----------|--------|-----|
| **Frontend** | React + Vite + Tailwind | Modern, fast, free hosting on Vercel |
| **Backend** | FastAPI | Python async, auto-docs, free on Railway |
| **Database** | Neo4j Aura FREE | Graph database, 50K nodes free |
| **Image Gen** | Hugging Face (SDXL) | FREE inference API |
| **Text Gen** | Groq (Llama 3 70B) | FREE tier, 6000 req/day |
| **Scraping** | BeautifulSoup + Pillow | Free Python libraries |
| **Storage** | Cloudflare R2 | 10GB free |

---

## 🎓 What This Project Teaches

### Core Skills
✅ **Web Scraping** - HTML parsing, data extraction  
✅ **Image Processing** - Quality assessment, color extraction  
✅ **Graph Databases** - Neo4j, Cypher queries, relationship modeling  
✅ **API Integration** - REST APIs, async calls, error handling  
✅ **Full-Stack Dev** - React frontend, FastAPI backend

---

## 📝 Project Status

- [x] Architecture documentation complete
- [x] Cost analysis and optimization (< $15/month)
- [x] Data intake pipeline design
- [ ] Backend implementation (Weeks 1-2)
- [ ] Web scraping module (Weeks 1-2)
- [ ] Image quality checker (Weeks 3-4)
- [ ] AI API integrations (Weeks 3-4)
- [ ] Frontend development (Weeks 5-6)
- [ ] Deployment to Railway + Vercel (Weeks 7-8)
- [ ] Demo preparation (Week 8)

**Current Phase**: Documentation Complete → Starting Implementation

---

## 🔗 Resources for Learning

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
- [Neo4j GraphAcademy](https://graphacademy.neo4j.com/) - Free courses
- [FastAPI Tutorial](https://fastapi.tiangolo.com/tutorial/) - Python API
- [React Documentation](https://react.dev/) - UI framework
- [Web Scraping with BeautifulSoup](https://realpython.com/beautiful-soup-web-scraper-python/)

---

## 📄 License

MIT License - Feel free to use for your own capstone/learning projects!

---

## 📧 Contact

**Project**: Brand-Aligned Content Generation System  
**Type**: College Capstone Project  
**Year**: 2026  
**Repository**: [GitHub](https://github.com/Shreyas70773/system-design-graph-rag-reasoning-image-resource-management-software)

---

**⭐ This project demonstrates modern system design principles while building something demo-able in 8 weeks with near-zero cost!**

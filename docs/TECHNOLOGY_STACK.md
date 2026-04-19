# Technology Stack - Sequential Overview

This document lists every technology used in the project, in the order it appears in the data flow.

---

## 1. **Frontend Layer** (What Users See)

### 1.1 React
- **What it does**: Builds the interactive web interface
- **Version**: 18.2.0
- **Why**: Standard for building responsive UIs in JavaScript
- **Where**: `frontend/src/pages/` (OnboardingEnhanced.jsx, Generate.jsx, Results.jsx, etc.)

### 1.2 React Router
- **What it does**: Handles page navigation (Home → Onboarding → Generate → Results)
- **Version**: 6.21.1
- **Why**: Makes multi-page apps work smoothly without reloading

### 1.3 Vite
- **What it does**: Bundles and runs the React code
- **Version**: 5.0.10
- **Why**: Fast development server, quick builds

### 1.4 Tailwind CSS
- **What it does**: Styles all the UI elements (buttons, cards, layouts)
- **Version**: 3.4.0
- **Why**: Fast, utility-based styling without writing CSS from scratch

### 1.5 Lucide React
- **What it does**: Provides clean icons (trash, edit, play, etc.)
- **Version**: 0.303.0
- **Why**: Lightweight, consistent icon set

### 1.6 Axios
- **What it does**: Sends requests from frontend to backend
- **Version**: 1.6.5
- **Why**: Makes HTTP calls simple and reliable

---

## 2. **Backend Framework** (What Runs the Server)

### 2.1 FastAPI
- **What it does**: Builds the REST API that handles all business logic
- **Version**: 0.109.0
- **Why**: Fast, modern Python framework with automatic documentation

### 2.2 Uvicorn
- **What it does**: Runs the FastAPI server
- **Version**: 0.27.0
- **Why**: ASGI server that handles async operations

### 2.3 Pydantic
- **What it does**: Validates all data entering and leaving the API
- **Version**: 2.5.3
- **Why**: Ensures data consistency and catches errors early

### 2.4 Python-Dotenv
- **What it does**: Loads secret API keys from a `.env` file
- **Version**: 1.0.0
- **Why**: Keeps sensitive credentials out of source code

---

## 3. **Database Layer** (Where Data Lives)

### 3.1 Neo4j
- **What it does**: Graph database that stores brand relationships
- **Tier**: FREE tier (Aura cloud)
- **Node limit**: 50,000 nodes
- **What it stores**:
  - Brands
  - Products
  - Colors
  - Learned preferences
  - Generation history
- **Why**: Perfect for relationships ("Brand A uses Color B", "Product C belongs to Brand A")

### 3.2 Neo4j Python Driver
- **What it does**: Connects Python code to Neo4j
- **Version**: 5.17.0
- **Why**: Official library for database queries

---

## 4. **Web Scraping** (Getting Brand Data)

### 4.1 BeautifulSoup4
- **What it does**: Parses HTML from websites
- **Version**: 4.12.3
- **Where used**: Extract company name, logo, colors from brand websites
- **Why**: Industry standard for web scraping

### 4.2 LXML
- **What it does**: Fast HTML/XML parsing library
- **Version**: 5.1.0
- **Why**: Speeds up BeautifulSoup's parsing

### 4.3 Requests
- **What it does**: Downloads web pages
- **Version**: 2.31.0
- **Why**: Simple HTTP library

### 4.4 HTTPx
- **What it does**: Async HTTP client (alternative to Requests)
- **Version**: 0.26.0
- **Why**: Handles concurrent requests efficiently

---

## 5. **Image Processing & Quality** (Quality Checks)

### 5.1 Pillow (PIL)
- **What it does**: Opens, analyzes, and manipulates images
- **Version**: 10.2.0
- **Tasks**:
  - Check logo quality (resolution, blur)
  - Extract colors from images
  - Generate quality scores
  - Compose text overlays on images

### 5.2 ColorThief
- **What it does**: Extracts dominant colors from images
- **Version**: 0.2.1
- **Why**: Gets the 5-7 main colors from a logo or webpage

### 5.3 NumPy
- **What it does**: Fast numerical computing
- **Version**: 1.26.3
- **Uses**:
  - Image array operations
  - Color distance calculations
  - Statistical computations

---

## 6. **Image Generation** (Creating Graphics)

### 6.1 ComfyUI (Local)
- **What it does**: Runs SDXL image generation on user's machine
- **Why**: Free tier, no API costs, full control
- **Fallback**: Hugging Face SDXL if ComfyUI unavailable

### 6.2 Hugging Face
- **What it does**: Cloud-based image generation fallback
- **Models used**: Stable Diffusion XL (SDXL)
- **Why**: Reliable backup when local ComfyUI isn't available

### 6.3 Boto3
- **What it does**: Connects to AWS/S3-compatible storage
- **Version**: 1.35.36
- **Why**: Upload/download generated images

---

## 7. **Text Generation** (Writing Copy)

### 7.1 Groq
- **What it does**: Generates marketing text and product descriptions
- **Model**: Llama 3.3-70B
- **API calls**:
  - Parse product text
  - Generate social media posts
  - Write marketing copy
  - Analyze brand tone

### 7.2 OpenAI SDK
- **What it does**: Optional fallback for text generation
- **Version**: 2.31.0
- **Why**: Alternative if Groq is unavailable

---

## 8. **Search & Research** (Finding Industry News)

### 8.1 Perplexity API
- **What it does**: Searches the web for industry news and trends
- **Use case**: LinkedIn post generation (find trending topics)
- **Why**: Real-time search with sources

---

## 9. **Cloud Storage** (Storing Generated Assets)

### 9.1 Cloudflare R2
- **What it does**: Cloud storage for generated images and uploaded logos
- **Tier**: FREE tier (10GB/month)
- **Why**: Cheap, fast CDN, S3-compatible API

### 9.2 Local Fallback Storage
- **What it does**: If R2 unavailable, saves to local disk
- **Why**: Offline-first strategy, no external dependency

---

## 10. **Statistics & Evaluation** (Research Metrics)

### 10.1 SciPy
- **What it does**: Statistical tests
- **Tests available**:
  - Wilcoxon signed-rank test (compare methods)
  - Friedman test (compare across conditions)
  - Sign test (fallback)

### 10.2 Bootstrap Confidence Intervals
- **What it does**: Compute uncertainty bounds without assuming normal distribution
- **Why**: Works with small sample sizes

### 10.3 Holm Correction
- **What it does**: Adjusts p-values for multiple comparisons
- **Why**: Prevents false positives when running many statistical tests

---

## 11. **Development & Deployment**

### 11.1 Python Multipart
- **What it does**: Handles file uploads (logo, images)
- **Version**: 0.0.6
- **Why**: Required by FastAPI for form submissions

### 11.2 PostCSS
- **What it does**: Post-processes CSS
- **Version**: 8.4.32
- **Why**: Autoprefixer adds browser compatibility

### 11.3 Autoprefixer
- **What it does**: Adds vendor prefixes to CSS
- **Version**: 10.4.16
- **Why**: Ensures CSS works in older browsers

---

## 12. **Hosting Platforms** (< $15/month budget)

### 12.1 Frontend Hosting
- **Platform**: Vercel (FREE tier)
- **What it does**: Hosts the React web app
- **URL**: Automatically deployed from GitHub

### 12.2 Backend Hosting
- **Platform**: Railway or similar (FREE tier or $5/month)
- **What it does**: Runs the FastAPI server
- **Benefit**: Auto-deploys on git push

### 12.3 Database Hosting
- **Platform**: Neo4j Aura (FREE tier)
- **Regions**: AWS cloud
- **What it does**: Managed Neo4j database

---

## **Data Flow (How Everything Connects)**

```
User Browser (React + Tailwind + Lucide)
    │
    ├─→ Sends request via Axios
    └─→ Receives JSON response
              │
              ▼
Backend Server (FastAPI + Uvicorn)
    │
    ├─→ Validates data with Pydantic
    │
    ├─→ Web Scraping (BeautifulSoup + LXML + Requests)
    │       │
    │       └─→ Downloads website
    │
    ├─→ Image Quality (Pillow + ColorThief + NumPy)
    │       │
    │       └─→ Analyzes logo
    │
    ├─→ Stores in Database (Neo4j)
    │
    ├─→ Text Generation (Groq Llama 3.3-70B)
    │
    ├─→ Image Generation (ComfyUI → SDXL or Hugging Face)
    │
    ├─→ Search (Perplexity API for news)
    │
    ├─→ Cloud Storage (Cloudflare R2 or local backup)
    │
    └─→ Statistics (SciPy + Bootstrap + Holm)
              │
              └─→ Sent back to user browser
```

---

## **Environment Variables Required**

```
NEO4J_URL=neo4j+s://...
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=...

GROQ_API_KEY=...
PERPLEXITY_API_KEY=...
OPENAI_API_KEY=... (optional)

CLOUDFLARE_ACCOUNT_ID=...
CLOUDFLARE_ACCESS_KEY_ID=...
CLOUDFLARE_SECRET_ACCESS_KEY=...
CLOUDFLARE_R2_BUCKET_NAME=...

COMFY_API_URL=http://127.0.0.1:8188 (local ComfyUI)
```

---

## **Quick Reference: What Each Tech Does**

| Technology | Purpose | Why Used |
|-----------|---------|----------|
| **React** | User interface | Industry standard |
| **Vite** | Build tool | Fast development |
| **Tailwind** | Styling | Quick UI design |
| **FastAPI** | Backend API | Modern, fast Python |
| **Neo4j** | Graph database | Relationships between brand data |
| **BeautifulSoup** | Web scraping | Extract brand info |
| **Pillow** | Image processing | Quality checks, analysis |
| **Groq** | AI text generation | Fast, cheap LLM |
| **SDXL** | Image generation | Free tier available |
| **Cloudflare R2** | Cloud storage | Cheap, fast |
| **SciPy** | Statistics | Research validation |
| **Vercel** | Frontend hosting | Free, easy deploy |
| **Railway/Heroku** | Backend hosting | Free tier, auto-deploy |

---

## **Cost Breakdown (Per Month)**

| Service | Cost |
|---------|------|
| **Vercel** (Frontend) | FREE |
| **Railway** (Backend) | FREE (CPU limits) |
| **Neo4j Aura** (Database) | FREE (50K nodes) |
| **Groq** (Text Gen) | FREE (rate limited) |
| **Hugging Face** (Image Gen) | FREE (limited inference) |
| **Cloudflare R2** (Storage) | FREE (10GB/month) |
| **Perplexity** (Search) | FREE or $20 (optional) |
| **ComfyUI** (Local) | FREE (use user's GPU) |
| **TOTAL** | **< $15/month** |


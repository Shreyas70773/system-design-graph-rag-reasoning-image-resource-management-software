# Brand-Aligned Content Generation Platform - Backend

## Quick Start

### 1. Set up Python environment

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment

```bash
# Copy the example env file
copy .env.example .env   # Windows
cp .env.example .env     # Mac/Linux

# Edit .env with your API keys
```

### 4. Run the development server

```bash
uvicorn app.main:app --reload
```

The API will be available at:
- **API**: http://localhost:8000
- **Docs**: http://localhost:8000/docs
- **Health**: http://localhost:8000/health

## API Endpoints

### Health Check
- `GET /health` - Check service status

### Brands
- `POST /api/brands/scrape` - Scrape website for brand data
- `GET /api/brands/{id}` - Get brand by ID
- `POST /api/brands/{id}/logo/check-quality` - Check logo quality
- `POST /api/brands/{id}/logo/generate-ai` - Generate AI logo

### Products
- `POST /api/brands/{id}/products/parse-text` - Parse products from text
- `POST /api/brands/{id}/products/scrape-url` - Scrape products from URL
- `GET /api/brands/{id}/products` - Get brand products

### Generation
- `POST /api/generate` - Generate marketing content
- `GET /api/generations/{brand_id}` - Get generation history

## Required API Keys

1. **Neo4j Aura** (FREE) - https://aura.neo4j.io
2. **Hugging Face** (FREE) - https://huggingface.co/settings/tokens
3. **Groq** (FREE) - https://console.groq.com/keys

## Project Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI application
│   ├── config.py            # Environment configuration
│   ├── database/
│   │   ├── neo4j_client.py  # Neo4j database operations
│   │   └── schema.cypher    # Graph schema definition
│   ├── routers/
│   │   ├── health.py        # Health check endpoints
│   │   ├── brands.py        # Brand management endpoints
│   │   ├── products.py      # Product management endpoints
│   │   └── generation.py    # Content generation endpoints
│   ├── scraping/
│   │   ├── website_scraper.py  # Main scraping logic
│   │   ├── logo_extractor.py   # Logo finding & download
│   │   └── color_extractor.py  # Color extraction
│   ├── quality/
│   │   ├── image_quality.py    # Quality assessment
│   │   └── enhancement.py      # AI logo generation
│   ├── products/
│   │   ├── text_parser.py      # LLM product parsing
│   │   └── url_scraper.py      # Product page scraping
│   └── generation/
│       ├── image_generator.py  # Marketing image generation
│       ├── text_generator.py   # Marketing copy generation
│       └── validator.py        # Brand consistency validation
├── requirements.txt
├── .env.example
├── .gitignore
├── Procfile               # For Railway deployment
└── README.md
```

## Deployment to Railway

1. Push code to GitHub
2. Create new project on Railway
3. Connect to GitHub repository
4. Set environment variables in Railway dashboard
5. Deploy!

The `Procfile` is already configured for Railway.

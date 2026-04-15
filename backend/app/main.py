"""
Main FastAPI Application
Brand-Aligned Content Generation Platform
"""
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from app.config import get_settings
from app.database.neo4j_client import neo4j_client
from app.routers import brands, products, generation, health, feedback
from app.routers import advanced_generation
from app.routers import brand_dna
from app.routers import linkedin
from app.routers import content_creator
from app.routers import research


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - startup and shutdown events"""
    # Startup
    settings = get_settings()
    print(f"Starting {settings.app_name}...")
    
    # Verify Neo4j connection
    if neo4j_client.verify_connection():
        print("[OK] Neo4j connection verified")
        try:
            neo4j_client.setup_schema()
            neo4j_client.setup_research_schema()
            print("[OK] Core and research schema ready")
        except Exception as schema_error:
            print(f"[WARN] Schema setup warning: {schema_error}")
    else:
        print("[FAIL] Neo4j connection failed - check credentials")
    
    yield
    
    # Shutdown
    print("Shutting down...")
    neo4j_client.close()


# Create FastAPI app
app = FastAPI(
    title="Brand-Aligned Content Generation API",
    description="API for scraping brand data, managing products, and generating brand-consistent marketing content",
    version="1.0.0",
    lifespan=lifespan
)

# Local uploads mount for logo upload fallback storage.
uploads_dir = Path(__file__).resolve().parents[1] / "uploads"
uploads_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")

# CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins during development
    allow_credentials=False,  # Must be False when using wildcard origins
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(brands.router, prefix="/api/brands", tags=["Brands"])
app.include_router(products.router, prefix="/api/brands", tags=["Products"])
app.include_router(generation.router, prefix="/api", tags=["Generation"])
app.include_router(feedback.router, prefix="/api", tags=["Feedback"])
app.include_router(advanced_generation.router, prefix="/api", tags=["Advanced Generation"])
app.include_router(brand_dna.router, tags=["Brand DNA"])
app.include_router(linkedin.router, prefix="/api", tags=["LinkedIn"])
app.include_router(content_creator.router, prefix="/api/content", tags=["AI Content Creator"])
app.include_router(research.router, prefix="/api", tags=["Research"])


# Global exception handler to ensure CORS headers are always sent
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all exception handler that ensures CORS headers are included"""
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "*",
            "Access-Control-Allow-Headers": "*",
        }
    )


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "name": "Brand-Aligned Content Generation API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)

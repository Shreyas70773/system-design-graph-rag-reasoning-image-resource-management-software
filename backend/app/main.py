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
from app.routers import v2_health
from app.routers import v2_assets, v2_scenes, v2_interactions, v2_brands, v2_jobs
from app.routers import v2_layers
from app.routers import v3_capstone
from app.config_v2 import get_v2_settings
from app.workers.worker_main import start_background_workers, stop_background_workers


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - startup and shutdown events"""
    # Startup
    settings = get_settings()
    print(f"Starting {settings.app_name}...")

    # Verify Neo4j connection with a hard 8-second timeout so a slow/unavailable
    # Neo4j instance never blocks uvicorn from accepting requests.
    import concurrent.futures as _cf
    def _neo4j_init():
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
    try:
        with _cf.ThreadPoolExecutor(max_workers=1) as ex:
            fut = ex.submit(_neo4j_init)
            fut.result(timeout=8)
    except _cf.TimeoutError:
        print("[WARN] Neo4j startup timed out after 8 s — continuing without Neo4j")
    except Exception as _e:
        print(f"[WARN] Neo4j startup error: {_e}")
    
    # V2 workers
    v2_settings = get_v2_settings()
    print(f"[V2] mock_mode={v2_settings.mock_mode}, storage={v2_settings.storage_root}")
    start_background_workers()
    print("[V2] Background workers started (Pipeline A + Pipeline B)")

    yield

    # Shutdown
    print("Shutting down...")
    stop_background_workers()
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
(uploads_dir / "v2").mkdir(parents=True, exist_ok=True)
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
app.include_router(v2_health.router, tags=["V2"])
app.include_router(v2_assets.router)
app.include_router(v2_scenes.router)
app.include_router(v2_interactions.router)
app.include_router(v2_brands.router)
app.include_router(v2_jobs.router)
app.include_router(v2_layers.router)
app.include_router(v3_capstone.router)


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

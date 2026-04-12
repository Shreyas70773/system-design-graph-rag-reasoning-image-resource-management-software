"""
Health check endpoints
"""
from fastapi import APIRouter
from app.database.neo4j_client import neo4j_client
from app.config import get_settings

router = APIRouter()


@router.get("/health")
async def health_check():
    """Basic health check endpoint"""
    settings = get_settings()
    
    # Check Neo4j connection
    neo4j_connected = neo4j_client.verify_connection()
    
    # Check if API keys are configured
    has_huggingface = bool(settings.huggingface_token)
    has_groq = bool(settings.groq_api_key)
    
    return {
        "status": "healthy" if neo4j_connected else "degraded",
        "services": {
            "neo4j": "connected" if neo4j_connected else "disconnected",
            "huggingface": "configured" if has_huggingface else "not configured",
            "groq": "configured" if has_groq else "not configured"
        }
    }

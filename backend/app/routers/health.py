"""
Health check endpoints
"""
from fastapi import APIRouter
from app.database.neo4j_client import neo4j_client
from app.config import get_settings
from app.services.comfy_client import ComfyClient

router = APIRouter()


@router.get("/health")
async def health_check():
    """Basic health check endpoint"""
    settings = get_settings()
    comfy_client = ComfyClient(settings.comfyui_url)
    
    # Check Neo4j connection
    neo4j_connected = neo4j_client.verify_connection()
    
    # Check if API keys are configured
    has_huggingface = bool(settings.huggingface_token)
    has_groq = bool(settings.groq_api_key)
    comfy_status = await comfy_client.health()
    comfy_checkpoints = []
    if comfy_status.get("ok"):
        checkpoint_listing = await comfy_client.list_models("checkpoints")
        if checkpoint_listing.get("ok"):
            comfy_checkpoints = checkpoint_listing.get("models", [])
    
    return {
        "status": "healthy" if neo4j_connected else "degraded",
        "services": {
            "neo4j": "connected" if neo4j_connected else "disconnected",
            "huggingface": "configured" if has_huggingface else "not configured",
            "groq": "configured" if has_groq else "not configured",
            "comfyui": "connected" if comfy_status.get("ok") else "disconnected"
        },
        "research": {
            "enabled": settings.research_mode_enabled,
            "comfyui_url": comfy_status.get("base_url") or settings.comfyui_url,
            "comfyui_attempted_urls": comfy_status.get("attempted_urls", []),
            "comfyui_checkpoint_count": len(comfy_checkpoints),
            "comfyui_checkpoints": comfy_checkpoints[:10],
            "default_seeds": settings.research_default_seeds,
        },
    }

"""
Application configuration - loads environment variables
"""
from functools import lru_cache
from pydantic_settings import BaseSettings
from typing import Optional
from dotenv import load_dotenv
import os

# Load .env file early so os.getenv() works everywhere
_env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
load_dotenv(_env_path)


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Application
    app_name: str = "Brand-Aligned Content Generation Platform"
    debug: bool = False
    
    # Neo4j Aura
    neo4j_uri: str = ""
    neo4j_username: str = "neo4j"  # Maps to NEO4J_USERNAME env var
    neo4j_password: str = ""
    neo4j_database: Optional[str] = None
    neo4j_trust_all_certificates: bool = True
    aura_instanceid: Optional[str] = None
    aura_instancename: Optional[str] = None
    
    # Alias for code compatibility
    @property
    def neo4j_user(self) -> str:
        return self.neo4j_username
    
    # Hugging Face
    huggingface_token: str = ""
    
    # Groq
    groq_api_key: str = ""
    
    # OpenAI (for product extraction)
    openai_api_key: str = ""
    
    # Perplexity (for search)
    perplexity_api_key: str = ""

    # ComfyUI
    comfyui_url: str = "http://127.0.0.1:8001"
    comfyui_auto_start: bool = True
    comfyui_auto_start_timeout_seconds: int = 45
    comfyui_desktop_executable: str = ""

    # Research execution controls
    research_default_seeds: str = "11,22,33"
    research_mode_enabled: bool = True

    # Image generation backend policy
    # Default to OpenRouter image models for production generation reliability.
    allow_google_image_models: bool = False
    allow_openrouter_image_models: bool = True
    image_provider_priority: str = "openrouter,replicate,fal.ai"
    
    # Cloudflare R2 (optional)
    cloudflare_account_id: Optional[str] = None
    cloudflare_r2_access_key: Optional[str] = None
    cloudflare_r2_secret_key: Optional[str] = None
    cloudflare_r2_bucket: Optional[str] = None
    cloudflare_r2_public_base_url: Optional[str] = None
    
    class Config:
        env_file = _env_path
        env_file_encoding = "utf-8"
        extra = "ignore"  # Ignore any extra env vars


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance - clears cache on import"""
    return Settings()

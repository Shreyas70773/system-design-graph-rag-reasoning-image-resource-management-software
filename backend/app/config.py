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
    
    # Cloudflare R2 (optional)
    cloudflare_account_id: Optional[str] = None
    cloudflare_r2_access_key: Optional[str] = None
    cloudflare_r2_secret_key: Optional[str] = None
    cloudflare_r2_bucket: Optional[str] = None
    
    class Config:
        env_file = "C:/Users/bukka/system-design-capstone/backend/.env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # Ignore any extra env vars


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance - clears cache on import"""
    return Settings()

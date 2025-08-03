try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings
from typing import Optional
from pydantic import ConfigDict

class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # NPC Configuration
    USE_FALLBACK_NPCS: bool = False
    
    # Database Configuration
    DATABASE_URL: Optional[str] = None
    
    # Media Configuration
    MINIO_ENDPOINT: Optional[str] = None
    MINIO_ACCESS_KEY: Optional[str] = None
    MINIO_SECRET_KEY: Optional[str] = None
    MINIO_BUCKET: Optional[str] = None
    
    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore"  # Allow extra environment variables
    )

# Global settings instance
settings = Settings() 
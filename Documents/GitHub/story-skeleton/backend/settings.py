# backend/settings.py
"""
Pydantic BaseSettings for environment configuration
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Database
    postgres_url: str = Field(
        default="postgresql://postgres:pass@localhost:5432/purposepath",
        env="POSTGRES_URL"
    )
    pgvector_extension: bool = Field(
        default=True,
        env="PGVECTOR_EXTENSION"
    )
    
    # Storage
    s3_endpoint: str = Field(
        default="http://localhost:9000",
        env="S3_ENDPOINT"
    )
    s3_bucket: str = Field(
        default="purposepath-assets",
        env="S3_BUCKET"
    )
    s3_access_key: str = Field(
        default="minioadmin",
        env="S3_ACCESS_KEY"
    )
    s3_secret_key: str = Field(
        default="minioadmin",
        env="S3_SECRET_KEY"
    )
    
    # GPT / Embedding
    openai_api_key: Optional[str] = Field(
        default=None,
        env="OPENAI_API_KEY"
    )
    embed_model: str = Field(
        default="text-embedding-3-small",
        env="EMBED_MODEL"
    )
    
    # Auth
    jwt_secret: str = Field(
        default="changeme",
        env="JWT_SECRET"
    )
    
    # Local flags
    use_cpu_stubs: bool = Field(
        default=True,
        env="USE_CPU_STUBS"
    )
    sync_media_generation: bool = Field(
        default=True,
        env="SYNC_MEDIA_GENERATION"
    )
    
    # Testing
    testing: bool = Field(
        default=False,
        env="TESTING"
    )
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"  # Ignore extra environment variables


# Global settings instance
settings = Settings() 
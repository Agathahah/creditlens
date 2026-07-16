import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
from typing import Optional

class Settings(BaseSettings):
    """System settings for CreditLens, loaded from environment variables or .env."""
    
    # Environment
    ENV: str = Field(default="development", description="Current environment (development, production, test)")
    
    # Databases
    POSTGRES_URL: str = Field(
        default="postgresql://creditlens:devpassword@localhost:5432/creditlens",
        description="SQLAlchemy-compatible PostgreSQL connection URL"
    )
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL"
    )
    
    # APIs & Keys
    FRED_API_KEY: Optional[str] = Field(default=None, description="API Key for Federal Reserve Economic Data (FRED)")
    OPENAI_API_KEY: Optional[str] = Field(default=None, description="API Key for OpenAI (Embeddings)")
    ANTHROPIC_API_KEY: Optional[str] = Field(default=None, description="API Key for Anthropic Claude")
    
    # MLflow
    MLFLOW_URL: str = Field(
        default="http://localhost:5000",
        description="MLflow tracking server URL"
    )
    
    # Grafana
    GRAFANA_PASSWORD: str = Field(default="admin", description="Admin password for Grafana dashboard")

    # Pydantic Configuration
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @field_validator("POSTGRES_URL")
    @classmethod
    def validate_postgres_url(cls, v: str) -> str:
        if not v.startswith("postgresql://") and not v.startswith("postgresql+asyncpg://"):
            raise ValueError("POSTGRES_URL must be a valid PostgreSQL connection string")
        return v

    @field_validator("REDIS_URL")
    @classmethod
    def validate_redis_url(cls, v: str) -> str:
        if not v.startswith("redis://") and not v.startswith("rediss://"):
            raise ValueError("REDIS_URL must be a valid Redis connection string")
        return v

# Singleton Pattern for global configuration access
_settings: Optional[Settings] = None

def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings

import os
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Environment
    ENV: str = "development"
    DEBUG: bool = True
    
    # Supabase
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str  # Added missing field
    SUPABASE_SERVICE_KEY: str
    
    # Azure Document Intelligence
    AZURE_DOC_INTELLIGENCE_ENDPOINT: str
    AZURE_DOC_INTELLIGENCE_KEY: str
    
    # Redis & Celery
    REDIS_URL: str
    REDIS_HOST: Optional[str] = None  # Added optional fields
    REDIS_PORT: Optional[int] = None
    REDIS_PASSWORD: str  # Added missing field
    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str
    
    # Application Settings
    MAX_FILE_SIZE_MB: int = 50
    PROCESSING_TIMEOUT_SECONDS: int = 300
    ALLOWED_FILE_TYPES: str = "pdf"

    # Server Configuration - ADDED FOR PORT MANAGEMENT
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8001
    FRONTEND_PORT: int = 8080

    # CORS Origins - ADDED FOR FRONTEND INTEGRATION
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173,http://localhost:8080,http://localhost:8081,http://localhost:8082"
    
    # AI/LLM Service Configuration
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o-mini"
    AZURE_OPENAI_ENDPOINT: Optional[str] = None
    AZURE_OPENAI_API_KEY: Optional[str] = None
    AZURE_OPENAI_API_VERSION: str = "2024-02-15-preview"
    ANTHROPIC_API_KEY: Optional[str] = None
    AI_SERVICE_PROVIDER: str = "openai"  # openai, azure_openai, anthropic, mock

    # Security Settings (optional)
    SECRET_KEY: Optional[str] = "dev-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    class Config:
        env_file = ".env"
        extra = "ignore"  # This allows extra fields in .env to be ignored

settings = Settings()

# Configuration validation and utility functions
def get_cors_origins_list() -> list:
    """Convert comma-separated CORS origins to list"""
    return [origin.strip() for origin in settings.CORS_ORIGINS.split(',')]

def validate_config():
    """Validate critical configuration settings"""
    errors = []

    # Port validation
    if not (1024 <= settings.BACKEND_PORT <= 65535):
        errors.append(f"Invalid backend port: {settings.BACKEND_PORT}")

    if not (1024 <= settings.FRONTEND_PORT <= 65535):
        errors.append(f"Invalid frontend port: {settings.FRONTEND_PORT}")

    # File size validation
    if settings.MAX_FILE_SIZE_MB <= 0 or settings.MAX_FILE_SIZE_MB > 100:
        errors.append(f"Invalid max file size: {settings.MAX_FILE_SIZE_MB}MB (must be 1-100MB)")

    if errors:
        raise ValueError(f"Configuration validation failed: {'; '.join(errors)}")

# Validate configuration on import
validate_config()
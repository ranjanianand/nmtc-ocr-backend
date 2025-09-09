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
    
    # Security Settings (optional)
    SECRET_KEY: Optional[str] = "dev-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    class Config:
        env_file = ".env"
        extra = "ignore"  # This allows extra fields in .env to be ignored

settings = Settings()
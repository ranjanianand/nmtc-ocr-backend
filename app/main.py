from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import documents  # Import the documents router
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI(
    title="NMTC Document Processing API",
    description="AI-powered NMTC compliance document processing",
    version="1.0.0"
)

# Get port from environment for Railway deployment
port = int(os.getenv("PORT", 8000))

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(documents.router)

@app.get("/")
def root():
    return {
        "message": "NMTC Document Processing API", 
        "status": "running",
        "version": "1.0.0"
    }

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "environment": os.getenv("ENV", "development"),
        "services": {
            "redis": "connected" if os.getenv("REDIS_URL") else "not configured",
            "azure": "configured" if os.getenv("AZURE_DOC_INTELLIGENCE_KEY") else "not configured",
            "supabase": "configured" if os.getenv("SUPABASE_URL") else "not configured"
        }
    }
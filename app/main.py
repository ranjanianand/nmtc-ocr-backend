from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import documents  # MVP-only documents API
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI(
    title="NMTC MVP - Allocation Agreement Processor",
    description="Simple PDF processing for NMTC Allocation Agreements with compliance checking",
    version="1.0.0-mvp"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://localhost:8080", "http://localhost:8081", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include only MVP API router
app.include_router(documents.router)

@app.get("/")
def root():
    return {
        "message": "NMTC MVP - Allocation Agreement Processor",
        "status": "running",
        "version": "1.0.0-mvp",
        "focus": "Allocation Agreement PDFs Only",
        "features": [
            "PDF Upload & Azure OCR",
            "Data Extraction with Confidence Scores",
            "QEI Deadline Tracking",
            "Geographic Compliance Validation",
            "Allocation Amount Monitoring",
            "Manual Override Capability",
            "PDF Compliance Reports"
        ],
        "endpoint": "/api/process-allocation-agreement"
    }

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "environment": os.getenv("ENV", "development"),
        "services": {
            "azure_ocr": "configured" if os.getenv("AZURE_DOC_INTELLIGENCE_KEY") else "not configured",
            "supabase": "configured" if os.getenv("SUPABASE_URL") else "not configured"
        }
    }
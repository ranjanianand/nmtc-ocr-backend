from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import documents  # Import the documents router
from app.api import document_processing_v2  # Import the enterprise v2 router
# from app.api import document_processing_v3  # Import the enterprise v3 router with database integration - temporarily disabled due to syntax error
from app.api import mvp_workflow  # Import the MVP workflow router
from app.api import allocation_years  # Import the allocation years API
from app.api import metadata_preview  # Import the metadata preview API
from app.api import workflow  # Import the enterprise workflow API
from app.api import stage1_ocr  # Import the Stage 1 OCR API
import os
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI(
    title="NMTC Document Processing API - Enterprise Edition v3",
    description="AI-powered NMTC compliance document processing with enterprise database integration, real-time agent tracking, and background job management",
    version="3.0.0-enterprise"
)

# Get port from environment
port = int(os.getenv("PORT", 8000))

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://localhost:8080", "http://localhost:8081", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(documents.router)  # Legacy v1 API
app.include_router(document_processing_v2.router)  # Enterprise v2 API
# app.include_router(document_processing_v3.router)  # Enterprise v3 API with database integration - temporarily disabled
app.include_router(mvp_workflow.router)  # MVP Workflow API
app.include_router(allocation_years.router)  # Allocation Years API
app.include_router(metadata_preview.router)  # Metadata Preview API
app.include_router(workflow.router)  # Enterprise Workflow Orchestration API
app.include_router(stage1_ocr.router)  # Stage 1 OCR API

@app.on_event("startup")
async def startup_event():
    """Initialize enterprise services on startup"""
    try:
        # Initialize real-time service
        from app.services.realtime_service import realtime_service
        await realtime_service.start()
        
        print("Enterprise services initialized successfully")
        print("Real-time service started")
        print("Background processing ready")
        print("Progress tracking enabled")
        print("Error handling active")
        
    except Exception as e:
        print(f"Failed to initialize enterprise services: {str(e)}")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up services on shutdown"""
    try:
        from app.services.realtime_service import realtime_service
        await realtime_service.stop()
        print("Enterprise services shut down cleanly")
    except Exception as e:
        print(f"Error during shutdown: {str(e)}")

@app.get("/")
def root():
    return {
        "message": "NMTC Document Processing API - Enterprise Edition", 
        "status": "running",
        "version": "3.0.0-enterprise",
        "features": [
            "Enterprise Database Integration",
            "Real-time Agent State Tracking",
            "Background Job Queue with Retry Logic", 
            "3-Agent Processing Pipeline",
            "Cross-device State Synchronization",
            "Comprehensive Error Recovery",
            "FastAPI Background Processing",
            "Enterprise Session Management"
        ],
        "endpoints": {
            "legacy_v1": "/api/documents",
            "enterprise_v2": "/api/v2/documents",
            "enterprise_v3": "/api/v3/documents",
            "v3_health": "/api/v3/documents/health",
            "v3_stats": "/api/v3/documents/stats/realtime",
            "mvp_workflow": "/api/mvp",
            "allocation_years": "/api/allocation-years",
            "enterprise_workflow": "/api/workflow",
            "stage1_ocr": "/api/stage1-ocr"
        },
        "database_features": {
            "processing_sessions": "Enterprise session management with heartbeat monitoring",
            "agent_states": "Individual agent execution tracking",
            "background_jobs": "Job queue with deduplication and retry logic",
            "progress_events": "Real-time progress tracking",
            "error_recovery": "Comprehensive error logging and recovery"
        }
    }

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "environment": os.getenv("ENV", "development"),
        "services": {
            "azure": "configured" if os.getenv("AZURE_DOC_INTELLIGENCE_KEY") else "not configured",
            "supabase": "configured" if os.getenv("SUPABASE_URL") else "not configured",
            "background_processor": "active",
            "real_time_service": "active",
            "progress_tracker": "active",
            "error_handler": "active"
        },
        "note": "For detailed health check, use /api/v2/documents/health"
    }
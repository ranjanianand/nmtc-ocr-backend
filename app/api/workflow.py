"""
FastAPI endpoints for enterprise workflow orchestration
Handles job submission, status tracking, and results retrieval
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
import logging
import os
from datetime import datetime

from ..services.workflow_engine import EnterpriseWorkflowEngine
from ..services.supabase_service import SupabaseService
from ..services.database_service import DatabaseService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/workflow", tags=["workflow"])

# Initialize services
workflow_engine = EnterpriseWorkflowEngine()
supabase_service = SupabaseService()
db_service = DatabaseService()

# Pydantic models for request/response
class JobSubmissionRequest(BaseModel):
    org_id: str = Field(..., description="Organization UUID")
    user_id: str = Field(..., description="User UUID")
    allocation_year: int = Field(..., description="Allocation year (e.g., 2024)")
    description: Optional[str] = Field(None, description="Optional job description")

class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    progress_percent: int
    current_step: Optional[str]
    current_step_detail: Optional[str]
    display_name: str
    original_filename: str
    created_at: datetime
    started_at: Optional[datetime]
    estimated_completion: Optional[datetime]
    error_message: Optional[str]
    retry_count: int

class JobStepResponse(BaseModel):
    step_name: str
    step_display_name: str
    status: str
    progress_percent: int
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    duration_seconds: Optional[int]
    error_details: Optional[str]

class JobDetailsResponse(BaseModel):
    job_info: JobStatusResponse
    steps: List[JobStepResponse]
    recent_events: List[Dict[str, Any]]

class OrganizationJobsResponse(BaseModel):
    active_jobs: List[JobStatusResponse]
    total_active: int
    queue_position: Optional[int]

@router.post("/submit-allocation-job", response_model=Dict[str, str])
async def submit_allocation_job(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    org_id: str = Form(...),
    user_id: str = Form(...),
    allocation_year: int = Form(...),
    description: Optional[str] = Form(None)
):
    """
    Submit a new allocation agreement for processing.
    Returns immediately with job_id for tracking.
    """
    try:
        logger.info(f"Submitting allocation job for org {org_id}, user {user_id}")

        # Validate file type
        if not file.filename.lower().endswith(('.pdf', '.docx')):
            raise HTTPException(
                status_code=400,
                detail="Only PDF and DOCX files are supported"
            )

        # Check file size (50MB limit)
        max_size = 50 * 1024 * 1024  # 50MB
        file_content = await file.read()
        if len(file_content) > max_size:
            raise HTTPException(
                status_code=413,
                detail="File size exceeds 50MB limit"
            )

        # Reset file pointer for upload
        await file.seek(0)

        # Upload to Supabase storage
        storage_path = f"allocation-documents/{org_id}/{datetime.now().strftime('%Y/%m')}/{file.filename}"
        file_url = await supabase_service.upload_file(
            bucket="allocation-documents",
            file_path=storage_path,
            file_content=file_content,
            content_type=file.content_type
        )

        # Create document record
        document_data = {
            "org_id": org_id,
            "user_id": user_id,
            "filename": file.filename,
            "file_path": storage_path,
            "file_url": file_url,
            "file_size": len(file_content),
            "content_type": file.content_type,
            "processing_status": "uploaded"
        }

        document = await supabase_service.create_document(document_data)
        document_id = document["id"]

        # Submit to workflow engine
        job_id = await workflow_engine.submit_allocation_job(
            org_id=org_id,
            user_id=user_id,
            document_id=document_id,
            allocation_year=allocation_year,
            description=description or f"Allocation Agreement - {file.filename}"
        )

        # Update document with job_id
        await supabase_service.update_document(
            document_id,
            {
                "job_id": job_id,
                "processing_status": "queued",
                "job_created_at": datetime.utcnow().isoformat()
            }
        )

        logger.info(f"Job {job_id} submitted successfully for document {document_id}")

        return {
            "job_id": job_id,
            "document_id": document_id,
            "message": f"File uploaded successfully. Processing started with Job ID: {job_id}",
            "status": "queued"
        }

    except Exception as e:
        logger.error(f"Error submitting allocation job: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/job/{job_id}/status", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """Get current status of a workflow job"""
    try:
        job_details = await workflow_engine.get_job_status(job_id)

        if not job_details:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

        return JobStatusResponse(**job_details["job_info"])

    except Exception as e:
        logger.error(f"Error getting job status for {job_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/job/{job_id}/details", response_model=JobDetailsResponse)
async def get_job_details(job_id: str):
    """Get detailed status including steps and events"""
    try:
        job_details = await workflow_engine.get_job_status(job_id)

        if not job_details:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

        # Convert steps to Pydantic models
        steps = [JobStepResponse(**step) for step in job_details["steps_info"]]

        return JobDetailsResponse(
            job_info=JobStatusResponse(**job_details["job_info"]),
            steps=steps,
            recent_events=job_details["recent_events"]
        )

    except Exception as e:
        logger.error(f"Error getting job details for {job_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/job/{job_id}/results")
async def get_job_results(job_id: str):
    """Get final results of completed job"""
    try:
        job_status = await workflow_engine.get_job_status(job_id)

        if not job_status:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

        job_info = job_status["job_info"]

        if job_info["status"] != "completed":
            raise HTTPException(
                status_code=400,
                detail=f"Job {job_id} is not completed. Current status: {job_info['status']}"
            )

        # Get final results from workflow_jobs table
        results = await workflow_engine.get_job_results(job_id)

        return {
            "job_id": job_id,
            "status": "completed",
            "results": results,
            "completed_at": job_info["completed_at"]
        }

    except Exception as e:
        logger.error(f"Error getting job results for {job_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/organization/{org_id}/jobs", response_model=OrganizationJobsResponse)
async def get_organization_jobs(org_id: str, status: Optional[str] = None):
    """Get all jobs for an organization with optional status filter"""
    try:
        active_jobs = await workflow_engine.get_active_jobs_for_org(org_id)

        # Filter by status if provided
        if status:
            active_jobs = [job for job in active_jobs if job["status"] == status]

        jobs_response = [JobStatusResponse(**job) for job in active_jobs]

        return OrganizationJobsResponse(
            active_jobs=jobs_response,
            total_active=len(jobs_response),
            queue_position=None  # TODO: Implement queue position logic
        )

    except Exception as e:
        logger.error(f"Error getting organization jobs for {org_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/job/{job_id}/cancel")
async def cancel_job(job_id: str):
    """Cancel a running or queued job"""
    try:
        success = await workflow_engine.cancel_job(job_id)

        if not success:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot cancel job {job_id}. Job may not exist or cannot be cancelled."
            )

        return {
            "job_id": job_id,
            "status": "cancelled",
            "message": f"Job {job_id} has been cancelled successfully"
        }

    except Exception as e:
        logger.error(f"Error cancelling job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/job/{job_id}/retry")
async def retry_job(job_id: str):
    """Retry a failed job"""
    try:
        success = await workflow_engine.retry_job(job_id)

        if not success:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot retry job {job_id}. Job may not exist or cannot be retried."
            )

        return {
            "job_id": job_id,
            "status": "queued",
            "message": f"Job {job_id} has been queued for retry"
        }

    except Exception as e:
        logger.error(f"Error retrying job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/queue/status")
async def get_queue_status():
    """Get current processing queue status"""
    try:
        queue_status = await workflow_engine.get_queue_status()

        return {
            "total_queued": queue_status.get("total_queued", 0),
            "total_running": queue_status.get("total_running", 0),
            "estimated_wait_time_minutes": queue_status.get("estimated_wait_time_minutes", 0),
            "processing_capacity": queue_status.get("processing_capacity", 5)
        }

    except Exception as e:
        logger.error(f"Error getting queue status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def workflow_health_check():
    """Health check for workflow service"""
    try:
        # Check workflow engine
        engine_status = await workflow_engine.health_check()

        # Check Supabase connection
        supabase_status = await supabase_service.health_check()

        return {
            "status": "healthy" if engine_status and supabase_status else "unhealthy",
            "workflow_engine": "online" if engine_status else "offline",
            "supabase": "online" if supabase_status else "offline",
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Workflow health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )

# WebSocket endpoint for real-time job updates (optional)
@router.websocket("/job/{job_id}/live")
async def job_live_updates(websocket, job_id: str):
    """WebSocket endpoint for real-time job status updates"""
    await websocket.accept()

    try:
        # Subscribe to job updates
        await workflow_engine.subscribe_to_job_updates(job_id, websocket)

    except Exception as e:
        logger.error(f"WebSocket error for job {job_id}: {e}")
        await websocket.close(code=1000)
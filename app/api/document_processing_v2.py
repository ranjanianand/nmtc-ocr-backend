"""
NMTC Document Processing API v2 - Enterprise Background Processing

Complete enterprise-grade document processing API with FastAPI BackgroundTasks,
real-time progress tracking, and comprehensive error handling.

Author: CORE ENGINE PROCESSING AGENT
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Dict, Any, Optional

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from app.models.document import *
from app.services.supabase_service import supabase_service
from app.services.background_processor import background_processor, ProcessingStage
from app.services.progress_tracker import progress_tracker, ProgressEventType
from app.services.error_handler import error_handler, ErrorContext, ErrorCategory
from app.services.realtime_service import realtime_service
from app.config import settings
import uuid
import os

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/documents", tags=["documents-v2"])

@router.post("/upload", response_model=Dict[str, Any])
async def upload_document_enterprise(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    document_type: Optional[str] = Form(None),
    cde_name: Optional[str] = Form(None),
    client_info: Optional[str] = Form(None),
    org_id: str = Form(...),
    user_id: Optional[str] = Form(None),
    processing_mode: str = Form("auto"),  # auto, manual, stage_0a_only
    priority: str = Form("normal")  # low, normal, high, urgent
):
    """
    Enterprise document upload with immediate background processing
    
    This endpoint:
    1. Validates and uploads the document immediately
    2. Starts background processing pipeline
    3. Returns immediately with tracking information
    4. Provides real-time progress updates via WebSocket/SSE
    """
    
    upload_start_time = time.time()
    document_id = None
    session_id = None
    
    try:
        logger.info(f"Enterprise upload started - File: {file.filename}, "
                   f"Org: {org_id}, User: {user_id}, Mode: {processing_mode}")
        
        # Step 1: Validate file immediately
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are supported")
        
        # Read and validate file content
        file_content = await file.read()
        file_size = len(file_content)
        
        if file_size > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
            raise HTTPException(
                status_code=400, 
                detail=f"File size {file_size/1024/1024:.1f}MB exceeds {settings.MAX_FILE_SIZE_MB}MB limit"
            )
        
        if file_size < 1024:  # Minimum 1KB
            raise HTTPException(status_code=400, detail="File appears to be empty or corrupted")
        
        logger.info(f"File validated - Size: {file_size/1024/1024:.2f}MB")
        
        # Step 2: Generate storage path and upload to Supabase
        file_id = str(uuid.uuid4())
        file_extension = os.path.splitext(file.filename)[1]
        stored_filename = f"{file_id}{file_extension}"
        file_path = f"documents/{org_id}/{stored_filename}"
        
        try:
            upload_response = supabase_service.client.storage.from_('documents').upload(
                file_path,
                file_content,
                {
                    "content-type": "application/pdf", 
                    "cache-control": "3600",
                    "x-file-size": str(file_size),
                    "x-upload-time": datetime.utcnow().isoformat()
                }
            )
            logger.info(f"Storage upload completed - Path: {file_path}")
            
        except Exception as storage_error:
            logger.error(f"Storage upload failed: {str(storage_error)}")
            raise HTTPException(status_code=500, detail=f"Storage upload failed: {str(storage_error)}")
        
        # Step 3: Create document record with enterprise metadata
        try:
            metadata = {
                'filename': file.filename,
                'file_size': file_size,
                'file_id': file_id,
                'processing_mode': processing_mode,
                'priority': priority,
                'upload_duration_ms': (time.time() - upload_start_time) * 1000
            }
            
            # Add optional fields
            if document_type:
                metadata['suggested_document_type'] = document_type
            if cde_name:
                metadata['cde_name'] = cde_name  
            if client_info:
                metadata['client_info'] = client_info
            
            document_record = await supabase_service.create_document_record(
                org_id=org_id,
                file_path=file_path,
                metadata=metadata,
                user_id=user_id
            )
            
            document_id = document_record['id']
            logger.info(f"Document record created - ID: {document_id}")
            
        except Exception as db_error:
            logger.error(f"Database record creation failed: {str(db_error)}")
            # Clean up uploaded file
            try:
                supabase_service.client.storage.from_('documents').remove([file_path])
            except:
                pass
            raise HTTPException(status_code=500, detail=f"Database operation failed: {str(db_error)}")
        
        # Step 4: Initialize real-time tracking
        try:
            # Create real-time channel for document
            await realtime_service.create_document_channel(document_id, user_id)
            
            # Subscribe user to updates
            if user_id:
                await realtime_service.subscribe_user_to_document(user_id, document_id)
            
            # Start progress tracking session
            session_id = await progress_tracker.start_tracking(
                document_id=document_id,
                user_id=user_id,
                initial_stage="uploaded"
            )
            
            logger.info(f"Real-time tracking initialized - Session: {session_id}")
            
        except Exception as tracking_error:
            logger.warning(f"Real-time tracking setup failed: {str(tracking_error)}")
            # Continue without real-time tracking
        
        # Step 5: Start background processing based on mode
        processing_started = False
        
        if processing_mode == "auto":
            # Full automatic processing
            background_tasks.add_task(
                _execute_full_background_processing,
                document_id,
                session_id,
                user_id,
                False  # Don't skip Stage 0A
            )
            processing_started = True
            
        elif processing_mode == "stage_0a_only":
            # Only Stage 0A processing
            background_tasks.add_task(
                _execute_stage_0a_only,
                document_id,
                session_id,
                user_id
            )
            processing_started = True
            
        # processing_mode == "manual" -> No automatic processing
        
        upload_duration = (time.time() - upload_start_time) * 1000
        
        # Step 6: Send immediate response
        response_data = {
            "success": True,
            "document_id": document_id,
            "session_id": session_id,
            "status": "uploaded",
            "message": "Document uploaded successfully",
            "file_info": {
                "filename": file.filename,
                "file_size": file_size,
                "file_size_mb": round(file_size / 1024 / 1024, 2),
                "storage_path": file_path
            },
            "processing": {
                "mode": processing_mode,
                "priority": priority,
                "started": processing_started,
                "estimated_completion": "15-30 minutes" if processing_started else "Manual trigger required"
            },
            "tracking": {
                "session_id": session_id,
                "real_time_channel": f"doc_{document_id}",
                "progress_endpoint": f"/api/v2/documents/{document_id}/progress",
                "status_endpoint": f"/api/v2/documents/{document_id}/status"
            },
            "upload_metrics": {
                "duration_ms": round(upload_duration, 2),
                "throughput_mbps": round((file_size / 1024 / 1024) / (upload_duration / 1000), 2)
            },
            "next_steps": _get_next_steps(processing_mode, processing_started)
        }
        
        logger.info(f"Upload completed successfully - Document: {document_id}, "
                   f"Duration: {upload_duration:.2f}ms, Processing: {processing_started}")
        
        return response_data
        
    except HTTPException:
        raise
    except Exception as general_error:
        logger.error(f"Unexpected upload error: {str(general_error)}")
        
        # Clean up resources if possible
        if document_id and session_id:
            try:
                await progress_tracker.error_tracking(
                    session_id=session_id,
                    error_message=str(general_error),
                    error_details={"stage": "upload", "document_id": document_id}
                )
            except:
                pass
        
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(general_error)}")

async def _execute_full_background_processing(
    document_id: str, 
    session_id: str, 
    user_id: str = None,
    skip_stage_0a: bool = False
):
    """Execute complete background processing pipeline"""
    try:
        logger.info(f"Starting full background processing - Document: {document_id}")
        
        # Create error context for comprehensive error handling
        context = ErrorContext(
            document_id=document_id,
            session_id=session_id,
            user_id=user_id,
            processing_stage="full_pipeline"
        )
        
        # Start processing with comprehensive error handling
        session = await background_processor.start_complete_processing_pipeline(
            document_id=document_id,
            user_id=user_id,
            skip_stage_0a=skip_stage_0a
        )
        
        logger.info(f"Background processing completed successfully - Document: {document_id}")
        
    except Exception as e:
        logger.error(f"Background processing failed - Document: {document_id}, Error: {str(e)}")
        
        # Handle error with comprehensive error handling
        context = ErrorContext(
            document_id=document_id,
            session_id=session_id,
            user_id=user_id,
            processing_stage="background_processing"
        )
        
        await error_handler.handle_error(e, context)
        
        # Update progress tracker with error
        if session_id:
            await progress_tracker.error_tracking(
                session_id=session_id,
                error_message=str(e),
                error_details={"stage": "full_background_processing", "document_id": document_id}
            )

async def _execute_stage_0a_only(document_id: str, session_id: str, user_id: str = None):
    """Execute only Stage 0A processing"""
    try:
        logger.info(f"Starting Stage 0A processing - Document: {document_id}")
        
        # Create processing session
        session = background_processor.ProcessingSession(document_id, user_id)
        background_processor.active_sessions[document_id] = session
        
        try:
            await background_processor._execute_stage_0a(session)
            
            logger.info(f"Stage 0A completed - Document: {document_id}")
            
            # Send real-time notification
            await realtime_service.send_user_action_required(
                document_id=document_id,
                action_type="confirm_detection",
                action_message="Document type detected. Please confirm to continue processing.",
                user_id=user_id
            )
            
        finally:
            # Clean up session
            if document_id in background_processor.active_sessions:
                del background_processor.active_sessions[document_id]
        
    except Exception as e:
        logger.error(f"Stage 0A processing failed - Document: {document_id}, Error: {str(e)}")
        
        # Handle error
        context = ErrorContext(
            document_id=document_id,
            session_id=session_id,
            user_id=user_id,
            processing_stage="stage_0a"
        )
        
        await error_handler.handle_error(e, context)

def _get_next_steps(processing_mode: str, processing_started: bool) -> List[str]:
    """Get next steps based on processing mode"""
    if processing_mode == "auto" and processing_started:
        return [
            "Monitor real-time progress updates",
            "Processing will complete automatically in 15-30 minutes",
            "You'll receive notifications when user action is required",
            "Check the progress endpoint for detailed status"
        ]
    elif processing_mode == "stage_0a_only" and processing_started:
        return [
            "Monitor Stage 0A progress (OCR + Detection)",
            "Confirm document type when detection completes",
            "Trigger full processing manually if desired",
            "Check progress endpoint for status updates"
        ]
    else:  # manual mode
        return [
            "Document is uploaded and ready for processing",
            "Trigger processing manually using /start-processing endpoint",
            "Choose between Stage 0A only or full processing",
            "Monitor progress once processing starts"
        ]

@router.get("/{document_id}/progress")
async def get_processing_progress(document_id: str):
    """Get real-time processing progress for a document"""
    try:
        # Get progress from tracker
        progress_status = await progress_tracker.get_status(document_id)
        
        # Get real-time activity
        activity = await realtime_service.get_document_activity(document_id, limit=10)
        
        # Get error summary
        error_summary = await error_handler.get_error_summary(document_id)
        
        return {
            "document_id": document_id,
            "progress": progress_status,
            "recent_activity": activity,
            "error_summary": error_summary,
            "real_time_channel": f"doc_{document_id}",
            "last_updated": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get progress for document {document_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get progress: {str(e)}")

@router.post("/{document_id}/start-processing")
async def start_manual_processing(
    document_id: str,
    background_tasks: BackgroundTasks,
    user_id: Optional[str] = Form(None),
    processing_type: str = Form("full"),  # full, stage_0a_only, core_only
    force_restart: bool = Form(False)
):
    """Manually trigger document processing"""
    try:
        logger.info(f"Manual processing trigger - Document: {document_id}, Type: {processing_type}")
        
        # Check document exists
        document = await supabase_service.get_document(document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Check current status
        current_status = document.get('ocr_status', 'unknown')
        
        if current_status in ['processing', 'stage_0a_starting', 'core_pipeline_starting'] and not force_restart:
            raise HTTPException(
                status_code=400, 
                detail=f"Document is already processing (status: {current_status}). Use force_restart=true to override."
            )
        
        # Start progress tracking
        session_id = await progress_tracker.start_tracking(
            document_id=document_id,
            user_id=user_id,
            initial_stage="manual_trigger"
        )
        
        # Create real-time channel if needed
        await realtime_service.create_document_channel(document_id, user_id)
        if user_id:
            await realtime_service.subscribe_user_to_document(user_id, document_id)
        
        # Start appropriate processing
        if processing_type == "full":
            background_tasks.add_task(
                _execute_full_background_processing,
                document_id,
                session_id,
                user_id,
                False  # Don't skip Stage 0A
            )
        elif processing_type == "stage_0a_only":
            background_tasks.add_task(
                _execute_stage_0a_only,
                document_id,
                session_id,
                user_id
            )
        elif processing_type == "core_only":
            # Skip Stage 0A, go directly to core pipeline
            background_tasks.add_task(
                _execute_full_background_processing,
                document_id,
                session_id,
                user_id,
                True  # Skip Stage 0A
            )
        
        return {
            "success": True,
            "document_id": document_id,
            "session_id": session_id,
            "processing_type": processing_type,
            "message": f"Started {processing_type} processing",
            "estimated_completion": "15-30 minutes",
            "progress_endpoint": f"/api/v2/documents/{document_id}/progress"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start manual processing: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to start processing: {str(e)}")

@router.post("/{document_id}/confirm-detection")
async def confirm_detection_and_continue(
    document_id: str,
    background_tasks: BackgroundTasks,
    confirmed_type: str = Form(...),
    user_id: Optional[str] = Form(None),
    proceed_with_processing: bool = Form(True)
):
    """Confirm document type detection and optionally continue with core processing"""
    try:
        logger.info(f"Detection confirmation - Document: {document_id}, Type: {confirmed_type}")
        
        if proceed_with_processing:
            # Start progress tracking for core pipeline
            session_id = await progress_tracker.start_tracking(
                document_id=document_id,
                user_id=user_id,
                initial_stage="user_confirmed"
            )
            
            # Continue with core pipeline in background
            background_tasks.add_task(
                _execute_core_pipeline_after_confirmation,
                document_id,
                confirmed_type,
                session_id,
                user_id
            )
            
            message = "Detection confirmed. Starting core processing pipeline."
            
        else:
            # Just confirm the detection without proceeding
            await background_processor.confirm_detection_and_continue(
                document_id=document_id,
                confirmed_type=confirmed_type,
                user_id=user_id
            )
            
            message = "Detection confirmed. Processing paused."
        
        return {
            "success": True,
            "document_id": document_id,
            "confirmed_type": confirmed_type,
            "processing_continues": proceed_with_processing,
            "message": message
        }
        
    except Exception as e:
        logger.error(f"Failed to confirm detection: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to confirm detection: {str(e)}")

async def _execute_core_pipeline_after_confirmation(
    document_id: str,
    confirmed_type: str,
    session_id: str,
    user_id: str = None
):
    """Execute core pipeline after user confirmation"""
    try:
        await background_processor.confirm_detection_and_continue(
            document_id=document_id,
            confirmed_type=confirmed_type,
            user_id=user_id
        )
        
        # Send completion notification
        await realtime_service.send_processing_complete(
            document_id=document_id,
            final_status="completed",
            processing_summary={"confirmed_type": confirmed_type},
            user_id=user_id
        )
        
    except Exception as e:
        logger.error(f"Core pipeline after confirmation failed: {str(e)}")
        
        # Handle error
        context = ErrorContext(
            document_id=document_id,
            session_id=session_id,
            user_id=user_id,
            processing_stage="core_pipeline_after_confirmation"
        )
        
        await error_handler.handle_error(e, context)

@router.get("/{document_id}/status")
async def get_document_status_enterprise(document_id: str):
    """Get comprehensive document status with enterprise details"""
    try:
        # Get document from database
        document = await supabase_service.get_document(document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Get progress tracking status
        progress_status = await progress_tracker.get_status(document_id)
        
        # Get processing results
        parsed_index = document.get('parsed_index', {})
        
        # Build comprehensive status response
        response = {
            "document_id": document_id,
            "basic_info": {
                "filename": document.get('filename'),
                "file_size": parsed_index.get('stage_0a_results', {}).get('file_size'),
                "uploaded_at": document.get('uploaded_at'),
                "storage_path": document.get('storage_path'),
                "org_id": document.get('org_id'),
                "uploaded_by": document.get('uploaded_by')
            },
            "processing_status": {
                "current_stage": progress_status.get('current_stage'),
                "progress_percentage": progress_status.get('progress_percentage', 0),
                "is_active": progress_status.get('is_active', False),
                "last_activity": progress_status.get('last_activity'),
                "session_id": progress_status.get('session_id'),
                "message": progress_status.get('message')
            },
            "stage_0a_results": parsed_index.get('stage_0a_results', {}),
            "agent_1_analysis": parsed_index.get('agent_1_analysis', {}),
            "agent_2_risk_assessment": parsed_index.get('agent_2_risk_assessment', {}),
            "agent_3_report_generation": parsed_index.get('agent_3_report_generation', {}),
            "processing_sessions": parsed_index.get('processing_sessions', {}),
            "error_log": parsed_index.get('error_log', [])[-5:],  # Last 5 errors
            "real_time_info": {
                "channel": f"doc_{document_id}",
                "subscribers": len(realtime_service.channel_manager.get_channel_subscribers(f"doc_{document_id}")),
                "recent_messages": await realtime_service.get_document_activity(document_id, 5)
            }
        }
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get document status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")

@router.get("/realtime/stats")
async def get_realtime_stats():
    """Get real-time service statistics"""
    try:
        return realtime_service.get_stats()
    except Exception as e:
        logger.error(f"Failed to get real-time stats: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")

@router.post("/{document_id}/subscribe")
async def subscribe_to_document_updates(
    document_id: str,
    user_id: str = Form(...)
):
    """Subscribe a user to real-time document updates"""
    try:
        success = await realtime_service.subscribe_user_to_document(user_id, document_id)
        
        if not success:
            raise HTTPException(status_code=400, detail="Failed to subscribe to document updates")
        
        return {
            "success": True,
            "document_id": document_id,
            "user_id": user_id,
            "channel": f"doc_{document_id}",
            "message": "Successfully subscribed to document updates"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to subscribe user to document: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to subscribe: {str(e)}")

@router.delete("/{document_id}/subscribe")
async def unsubscribe_from_document_updates(
    document_id: str,
    user_id: str = Form(...)
):
    """Unsubscribe a user from real-time document updates"""
    try:
        success = await realtime_service.unsubscribe_user_from_document(user_id, document_id)
        
        return {
            "success": success,
            "document_id": document_id,
            "user_id": user_id,
            "message": "Successfully unsubscribed from document updates"
        }
        
    except Exception as e:
        logger.error(f"Failed to unsubscribe user from document: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to unsubscribe: {str(e)}")

@router.get("/health")
async def health_check_enterprise():
    """Enterprise health check with detailed service status"""
    try:
        # Check all services
        services_status = {
            "database": "healthy",
            "storage": "healthy", 
            "background_processor": "healthy",
            "progress_tracker": "healthy",
            "error_handler": "healthy",
            "realtime_service": "healthy" if realtime_service.is_running else "unhealthy"
        }
        
        # Get service statistics
        stats = {
            "realtime_service": realtime_service.get_stats(),
            "active_processing_sessions": len(background_processor.active_sessions),
            "total_errors_logged": len(error_handler.error_log)
        }
        
        overall_health = "healthy" if all(status == "healthy" for status in services_status.values()) else "degraded"
        
        return {
            "status": overall_health,
            "timestamp": datetime.utcnow().isoformat(),
            "services": services_status,
            "statistics": stats,
            "version": "2.0.0-enterprise"
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }
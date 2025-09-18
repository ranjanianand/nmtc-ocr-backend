"""
NMTC Document Processing API v3 - Enterprise Database Integration

Enhanced enterprise-grade document processing API that integrates with the new
database architecture for processing sessions, agent states, and real-time progress tracking.

Author: Core Engine Processing Agent + FastAPI Backend Agent
"""

import asyncio
import logging
import time
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from app.models.document import *
from app.services.supabase_service import supabase_service
from app.services.realtime_service import realtime_service
from app.config import settings

# Import new enterprise services
from app.services.background_processor_v2 import enterprise_background_processor
from app.services.database_service import database_service
import os

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v3/documents", tags=["documents-v3-enterprise"])

@router.post("/upload", response_model=Dict[str, Any])
async def upload_document_enterprise_v3(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    document_type: Optional[str] = Form(None),
    cde_name: Optional[str] = Form(None),
    client_info: Optional[str] = Form(None),
    org_id: str = Form(...),
    user_id: Optional[str] = Form(None),
    processing_mode: str = Form("auto"),  # auto, manual, stage_0a_only
    priority: str = Form("normal"),  # low, normal, high, urgent
    skip_stage_0a: bool = Form(False)
):
    """
    Enterprise document upload with immediate background processing v3
    
    Features:
    - Enterprise database session management
    - Real-time agent state tracking  
    - Background job queue with retry logic
    - Cross-device synchronization
    - Comprehensive error recovery
    """
    
    upload_start_time = time.time()
    document_id = None
    session_id = None
    
    try:
        logger.info(f"Enterprise v3 upload started - File: {file.filename}, "
                   f"Org: {org_id}, User: {user_id}, Mode: {processing_mode}")
        
        # Step 1: Validate file
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are supported")
        
        file_content = await file.read()
        file_size = len(file_content)
        
        if file_size > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
            raise HTTPException(
                status_code=400, 
                detail=f"File size {file_size/1024/1024:.1f}MB exceeds {settings.MAX_FILE_SIZE_MB}MB limit"
            )
        
        if file_size < 1024:
            raise HTTPException(status_code=400, detail="File appears to be empty or corrupted")
        
        logger.info(f"File validated - Size: {file_size/1024/1024:.2f}MB")
        
        # Step 2: Upload to Supabase Storage
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
                    "x-upload-time": datetime.utcnow().isoformat(),
                    "x-processing-mode": processing_mode
                }
            )
            logger.info(f"Storage upload completed - Path: {file_path}")
            
        except Exception as storage_error:
            logger.error(f"Storage upload failed: {str(storage_error)}")
            raise HTTPException(status_code=500, detail=f"Storage upload failed: {str(storage_error)}")
        
        # Step 3: Create document record
        try:
            # Map priority levels
            priority_map = {
                'low': 200,
                'normal': 100,
                'high': 50,
                'urgent': 10
            }
            numeric_priority = priority_map.get(priority, 100)
            
            metadata = {
                'filename': file.filename,
                'file_size': file_size,
                'file_id': file_id,
                'processing_mode': processing_mode,
                'priority': priority,
                'numeric_priority': numeric_priority,
                'upload_duration_ms': (time.time() - upload_start_time) * 1000,
                'enterprise_features': {
                    'real_time_tracking': True,
                    'agent_state_monitoring': True,
                    'cross_device_sync': True,
                    'error_recovery': True
                }
            }
            
            # Add optional metadata
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
        
        # Step 4: Start Enterprise Processing Pipeline
        try:
            session = await enterprise_background_processor.start_complete_processing_pipeline(
                document_id=document_id,
                user_id=user_id,
                org_id=org_id,
                session_type='full_pipeline' if not skip_stage_0a else 'core_pipeline_only',
                priority=numeric_priority,
                skip_stage_0a=skip_stage_0a
            )
            
            session_id = session.session_id
            
            logger.info(f"Enterprise processing pipeline started - Session: {session_id}")
            
        except Exception as processing_error:
            logger.error(f"Processing pipeline failed to start: {str(processing_error)}")
            
            # Log error to database
            await database_service.log_processing_error(
                session_id=None,
                job_id=None,
                error_type='pipeline_start_failure',
                error_message=str(processing_error),
                context_data={
                    'document_id': document_id,
                    'user_id': user_id,
                    'org_id': org_id,
                    'processing_mode': processing_mode
                }
            )
            
            raise HTTPException(status_code=500, detail=f"Processing failed to start: {str(processing_error)}")
        
        # Step 5: Setup Real-time Tracking
        try:
            # Create real-time channel for document
            await realtime_service.create_document_channel(document_id, user_id)
            
            # Subscribe user to updates if user_id provided
            if user_id:
                await realtime_service.subscribe_user_to_document(user_id, document_id)
                
                # Sync user session for cross-device functionality
                await database_service.sync_user_session(
                    user_id=uuid.UUID(user_id),
                    device_fingerprint=f"upload_{file_id}",
                    session_token=f"session_{session_id}",
                    user_agent="API Upload",
                    ip_address="127.0.0.1"  # Would be actual IP in production
                )
            
        except Exception as realtime_error:
            logger.warning(f"Real-time setup failed (non-critical): {str(realtime_error)}")
            # Don't fail the upload for real-time issues
        
        # Step 6: Return comprehensive response
        upload_duration = (time.time() - upload_start_time) * 1000
        
        response = {
            "success": True,
            "message": "Document uploaded and processing started successfully",
            "document_id": document_id,
            "session_id": session_id,
            "file_info": {
                "filename": file.filename,
                "file_size": file_size,
                "file_size_mb": round(file_size / 1024 / 1024, 2),
                "storage_path": file_path,
                "file_id": file_id
            },
            "processing_info": {
                "mode": processing_mode,
                "priority": priority,
                "numeric_priority": numeric_priority,
                "skip_stage_0a": skip_stage_0a,
                "estimated_duration_minutes": "15-30"
            },
            "tracking": {
                "session_id": session_id,
                "status": "queued",
                "progress_percentage": 5,
                "current_stage": "uploaded",
                "real_time_updates": True,
                "cross_device_sync": bool(user_id)
            },
            "api_info": {
                "upload_duration_ms": round(upload_duration, 2),
                "api_version": "v3-enterprise",
                "response_time": f"< {round(upload_duration/1000, 1)}s",
                "background_processing": True
            },
            "next_steps": [
                "Monitor progress via GET /api/v3/documents/{document_id}/status",
                "Subscribe to real-time updates via WebSocket",
                "Processing will complete automatically in background",
                f"Estimated completion: {datetime.utcnow().strftime('%H:%M')} (15-30 min)"
            ]
        }
        
        logger.info(f"Enterprise upload completed - Document: {document_id}, "
                   f"Session: {session_id}, Duration: {upload_duration:.1f}ms")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in enterprise upload: {str(e)}")
        
        # Log unexpected error
        if document_id:
            await database_service.log_processing_error(
                session_id=uuid.UUID(session_id) if session_id else None,
                job_id=None,
                error_type='unexpected_upload_error',
                error_message=str(e),
                context_data={
                    'document_id': document_id,
                    'filename': file.filename,
                    'processing_mode': processing_mode
                }
            )
        
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

@router.get("/{document_id}/status", response_model=Dict[str, Any])
async def get_document_processing_status_v3(document_id: str):
    """
    Get comprehensive processing status with enterprise database integration
    """
    try:
        logger.info(f"Getting status for document {document_id}")
        
        # Get comprehensive progress summary from database
        status = await enterprise_background_processor.get_processing_status(document_id)
        
        if 'error' in status:
            raise HTTPException(status_code=404, detail=status['error'])
        
        # Add API metadata
        status['api_info'] = {
            'api_version': 'v3-enterprise',
            'response_time': datetime.utcnow().isoformat(),
            'real_time_tracking': True,
            'database_integration': True
        }
        
        return status
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get document status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Status retrieval failed: {str(e)}")

@router.post("/{document_id}/confirm", response_model=Dict[str, Any])
async def confirm_document_type_v3(
    document_id: str,
    confirmed_type: str = Form(...),
    user_id: Optional[str] = Form(None)
):
    """
    Confirm document type and continue processing with enterprise tracking
    """
    try:
        logger.info(f"Confirming document type - Document: {document_id}, Type: {confirmed_type}")
        
        # Continue processing with confirmed type
        await enterprise_background_processor.confirm_detection_and_continue(
            document_id=document_id,
            confirmed_type=confirmed_type,
            user_id=user_id
        )
        
        return {
            "success": True,
            "message": f"Document type confirmed as '{confirmed_type}' and processing continued",
            "document_id": document_id,
            "confirmed_type": confirmed_type,
            "status": "core_pipeline_running",
            "api_version": "v3-enterprise"
        }
        
    except Exception as e:
        logger.error(f"Failed to confirm document type: {str(e)}")
        
        # Log error
        await database_service.log_processing_error(
            session_id=None,
            job_id=None,
            error_type='confirmation_failure',
            error_message=str(e),
            context_data={
                'document_id': document_id,
                'confirmed_type': confirmed_type,
                'user_id': user_id
            }
        )
        
        raise HTTPException(status_code=500, detail=f"Confirmation failed: {str(e)}")

@router.get("/user/{user_id}/active", response_model=List[Dict[str, Any]])
async def get_user_active_sessions_v3(
    user_id: str,
    org_id: Optional[str] = None
):
    """
    Get active processing sessions for a user with enterprise database integration
    """
    try:
        logger.info(f"Getting active sessions for user {user_id}")
        
        sessions = await enterprise_background_processor.get_active_sessions(
            user_id=user_id,
            org_id=org_id
        )
        
        # Add API metadata to each session
        for session in sessions:
            session['api_info'] = {
                'api_version': 'v3-enterprise',
                'cross_device_sync': True,
                'real_time_updates': True
            }
        
        return sessions
        
    except Exception as e:
        logger.error(f"Failed to get active sessions: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get active sessions: {str(e)}")

@router.get("/health", response_model=Dict[str, Any])
async def health_check_v3():
    """
    Enterprise health check with database connectivity validation
    """
    try:
        health_status = {
            "status": "healthy",
            "api_version": "v3-enterprise",
            "timestamp": datetime.utcnow().isoformat(),
            "features": {
                "enterprise_database": True,
                "real_time_tracking": True,
                "agent_state_monitoring": True,
                "background_job_queue": True,
                "cross_device_sync": True,
                "error_recovery": True
            }
        }
        
        # Test database connectivity
        try:
            # Simple database test
            test_session = await database_service.get_processing_session(uuid.uuid4())
            health_status["database_connectivity"] = "healthy"
        except Exception as db_e:
            health_status["database_connectivity"] = f"warning: {str(db_e)}"
        
        # Test background processor
        try:
            active_sessions = len(enterprise_background_processor.active_sessions)
            health_status["background_processor"] = {
                "status": "healthy",
                "active_sessions": active_sessions
            }
        except Exception as bg_e:
            health_status["background_processor"] = {
                "status": f"warning: {str(bg_e)}",
                "active_sessions": 0
            }
        
        # Test Azure service (optional)
        try:
            health_status["azure_service"] = "configured" if settings.AZURE_DOC_INTELLIGENCE_KEY else "not configured"
        except:
            health_status["azure_service"] = "unknown"
        
        return health_status
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "api_version": "v3-enterprise",
            "timestamp": datetime.utcnow().isoformat()
        }

@router.get("/stats/realtime", response_model=Dict[str, Any])
async def get_realtime_stats_v3():
    """
    Get real-time statistics about the enterprise processing system
    """
    try:
        # Get system statistics from database service
        stats = {
            "timestamp": datetime.utcnow().isoformat(),
            "api_version": "v3-enterprise",
            "system_stats": {
                "active_sessions": len(enterprise_background_processor.active_sessions),
                "worker_id": enterprise_background_processor.worker_id
            }
        }
        
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get real-time stats: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Stats retrieval failed: {str(e)}")

# Background task endpoints for debugging and monitoring

@router.get("/debug/sessions", response_model=Dict[str, Any])
async def debug_active_sessions():
    """Debug endpoint to view active processing sessions"""
    try:
        return {
            "active_sessions": list(enterprise_background_processor.active_sessions.keys()),
            "session_count": len(enterprise_background_processor.active_sessions),
            "worker_id": enterprise_background_processor.worker_id,
            "api_version": "v3-enterprise"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/debug/cleanup")
async def debug_cleanup_old_data():
    """Debug endpoint to trigger data cleanup"""
    try:
        await database_service.cleanup_old_data()
        return {
            "success": True,
            "message": "Data cleanup completed",
            "api_version": "v3-enterprise"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
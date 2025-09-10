from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import JSONResponse
from app.models.document import *
from app.services.supabase_service import supabase_service
from app.config import settings
import uuid
import os
import aiofiles
from typing import Optional
from datetime import datetime
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/documents", tags=["documents"])

@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    document_type: Optional[str] = Form(None),
    cde_name: Optional[str] = Form(None),
    client_info: Optional[str] = Form(None),
    org_id: str = Form(...),
    user_id: Optional[str] = Form(None),
):
    """Upload document and start processing pipeline"""
    
    document_id = None
    file_path = None
    
    try:
        logger.info(f"Starting upload for file: {file.filename}")
        
        # Validate file
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are supported")
        
        # Read file content
        file_content = await file.read()
        file_size = len(file_content)
        
        if file_size > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
            raise HTTPException(status_code=400, detail=f"File size exceeds {settings.MAX_FILE_SIZE_MB}MB limit")
        
        logger.info(f"File validated: {file.filename}, size: {file_size} bytes")
        
        # Generate unique filename
        file_id = str(uuid.uuid4())
        file_extension = os.path.splitext(file.filename)[1]
        stored_filename = f"{file_id}{file_extension}"
        file_path = f"documents/{org_id}/{stored_filename}"
        
        logger.info(f"Generated file path: {file_path}")
        
        # Upload to Supabase Storage
        logger.info("Starting Supabase storage upload...")
        
        try:
            upload_response = supabase_service.client.storage.from_('documents').upload(
                file_path,
                file_content,
                {"content-type": "application/pdf", "cache-control": "3600"}
            )
            
            logger.info(f"Upload response received: {type(upload_response)}")
            logger.info(f"Upload response data: {upload_response}")
            
        except Exception as upload_error:
            logger.error(f"Storage upload exception: {upload_error}")
            logger.error(f"Exception type: {type(upload_error)}")
            raise HTTPException(status_code=500, detail=f"Storage upload failed: {str(upload_error)}")
        
        logger.info("Storage upload completed successfully")
        
        # Create document record
        logger.info("Creating database record...")
        
        try:
            # Simple metadata with only essential fields
            metadata = {
                'filename': file.filename,
                'file_size': file_size
            }
            
            # Add optional fields only if provided
            if document_type:
                metadata['document_type'] = document_type
            if cde_name:
                metadata['cde_name'] = cde_name  
            if client_info:
                metadata['client_info'] = client_info
            
            logger.info(f"Creating document record with metadata: {metadata}")
            
            document_record = await supabase_service.create_document_record(
                org_id=org_id,
                file_path=file_path,
                metadata=metadata,
                user_id=user_id
            )
            
            if not document_record:
                raise Exception("Failed to create document record - no data returned")
            
            document_id = document_record['id']
            logger.info(f"Document record created successfully: {document_id}")
            
        except Exception as db_error:
            logger.error(f"Database error: {db_error}")
            logger.error(f"Database error type: {type(db_error)}")
            raise HTTPException(status_code=500, detail=f"Database operation failed: {str(db_error)}")
        
        # Queue for quick document detection (Stage 0A)
        from app.tasks.document_tasks import process_document_quick_detection
        process_document_quick_detection.delay(document_id, user_id)
        
        # Success response
        logger.info(f"Upload completed successfully for document: {document_id}")
        
        return DocumentUploadResponse(
            document_id=document_id,
            status=DocumentStatus.UPLOADED,
            message="Document uploaded successfully. Starting quick analysis...",
            file_path=file_path
        )
        
    except HTTPException as http_error:
        logger.error(f"HTTP exception: {http_error.detail}")
        raise http_error
        
    except Exception as general_error:
        logger.error(f"Unexpected error: {general_error}")
        logger.error(f"Error type: {type(general_error)}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(general_error)}")

@router.get("/{document_id}/status")
async def get_document_status(document_id: str):
    """Get current processing status of document with detection results"""
    try:
        logger.info(f"Getting status for document: {document_id}")
        
        document = await supabase_service.get_document(document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Basic document info
        response = {
            "document_id": document_id,
            "status": document.get('ocr_status'),
            "filename": document.get('filename'),
            "storage_path": document.get('storage_path'),
            "uploaded_at": document.get('uploaded_at'),
            "mime_type": document.get('mime_type'),
            "org_id": document.get('org_id')
        }
        
        # Add detection results if available
        parsed_index = document.get('parsed_index', {})
        if 'detection_results' in parsed_index:
            detection_results = parsed_index['detection_results']
            response['detection'] = {
                "detected_type": detection_results.get('document_type_detected'),
                "confidence": detection_results.get('confidence', 0.0),
                "reasoning": detection_results.get('reasoning', ''),
                "primary_indicators_count": len(detection_results.get('primary_indicators', [])),
                "secondary_indicators_count": len(detection_results.get('secondary_indicators', [])),
                "processed_at": detection_results.get('processed_at'),
                "user_confirmed_type": detection_results.get('user_confirmed_type'),
                "confirmed_at": detection_results.get('confirmed_at')
            }
            
            # Add confidence level and requirements
            confidence = detection_results.get('confidence', 0.0)
            if confidence >= 0.9:
                response['detection']['confidence_level'] = 'high'
                response['detection']['requires_confirmation'] = False
            elif confidence >= 0.7:
                response['detection']['confidence_level'] = 'medium'
                response['detection']['requires_confirmation'] = True
                response['detection']['auto_process_countdown'] = 10
            else:
                response['detection']['confidence_level'] = 'low'
                response['detection']['requires_confirmation'] = True
        
        # Add processing history if available
        if 'processing_history' in parsed_index:
            response['processing_history'] = parsed_index['processing_history']
        
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")

@router.post("/{document_id}/validate", response_model=dict)
async def validate_document(document_id: str, validation: DocumentValidationRequest):
    """User validates/corrects document detection results"""
    try:
        logger.info(f"Validating document: {document_id}")
        
        # Update document with user validation
        updates = {
            'document_type_id': validation.confirmed_type.value,
        }
        
        updated_document = await supabase_service.update_document_status(
            document_id, 
            'validated', 
            updates
        )
        
        if validation.proceed_with_processing:
            # TODO: Queue for full OCR processing (Stage 0B)
            # celery_app.send_task("full_document_processing", args=[document_id])
            logger.info(f"Queuing document {document_id} for full processing")
        
        return {
            "document_id": document_id,
            "ocr_status": "validated",
            "message": "Document validated. Starting full processing..." if validation.proceed_with_processing else "Document validated."
        }
        
    except Exception as e:
        logger.error(f"Error validating document: {e}")
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")

@router.get("/test-table")
async def test_table():
    """Test what columns exist in documents table"""
    try:
        result = supabase_service.client.table('documents').select('*').limit(1).execute()
        
        if result.data:
            columns = list(result.data[0].keys())
            return {
                "status": "success",
                "available_columns": columns,
                "sample_record": result.data[0]
            }
        else:
            return {
                "status": "empty_table",
                "message": "No records found in documents table"
            }
        
    except Exception as e:
        logger.error(f"Table test failed: {e}")
        return {
            "status": "failed",
            "error": str(e)
        }

@router.get("/test-storage")
async def test_storage():
    """Test Supabase storage connection"""
    try:
        buckets = supabase_service.client.storage.list_buckets()
        logger.info(f"Available buckets: {buckets}")
        
        test_content = b"Hello World Test"
        test_path = "test/test-file.txt"
        
        result = supabase_service.client.storage.from_('documents').upload(
            test_path,
            test_content,
            {"content-type": "text/plain"}
        )
        
        return {
            "status": "success",
            "buckets": buckets,
            "test_upload": result
        }
        
    except Exception as e:
        logger.error(f"Storage test failed: {e}")
        return {
            "status": "failed",
            "error": str(e)
        }

@router.post("/{document_id}/start-detection", response_model=DocumentDetectionResponse)
async def start_document_detection(
    document_id: str,
    request: StartDetectionRequest,
    user_id: Optional[str] = None
):
    """Manually trigger document detection for uploaded document"""
    try:
        logger.info(f"Starting detection for document: {document_id}")
        
        # Check if document exists
        document = await supabase_service.get_document(document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Check if document is in correct state
        if document.get('ocr_status') not in ['processing', 'uploaded']:
            raise HTTPException(
                status_code=400, 
                detail=f"Document is in {document.get('ocr_status')} state, cannot start detection"
            )
        
        # Queue the detection task
        from app.tasks.document_tasks import process_document_quick_detection
        task = process_document_quick_detection.delay(document_id, request.user_id or user_id)
        
        # Update status to detecting
        await supabase_service.update_document_status(document_id, 'detecting')
        
        return DocumentDetectionResponse(
            document_id=document_id,
            status=DocumentStatus.DETECTING,
            message="Document detection started successfully",
            processing_time_ms=None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting detection: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start detection: {str(e)}")

@router.get("/{document_id}/detection-status", response_model=DocumentDetectionResponse)
async def get_detection_status(document_id: str):
    """Get current detection status and results"""
    try:
        logger.info(f"Getting detection status for document: {document_id}")
        
        document = await supabase_service.get_document(document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Check if document has detection results
        parsed_index = document.get('parsed_index', {})
        detection_results = parsed_index.get('detection_results', {})
        
        if not detection_results:
            return DocumentDetectionResponse(
                document_id=document_id,
                status=DocumentStatus(document.get('ocr_status', 'uploaded')),
                message="Detection not started or still in progress"
            )
        
        # Parse detection results
        detected_type = detection_results.get('document_type_detected', 'unknown')
        confidence = detection_results.get('confidence', 0.0)
        
        # Determine confidence level and requirements
        confidence_level = ConfidenceLevel.LOW
        requires_confirmation = True
        auto_process_countdown = None
        
        if confidence >= 0.9:
            confidence_level = ConfidenceLevel.HIGH
            requires_confirmation = False
        elif confidence >= 0.7:
            confidence_level = ConfidenceLevel.MEDIUM
            requires_confirmation = True
            auto_process_countdown = 10
        
        # Build pattern indicators
        primary_indicators = [
            PatternIndicator(
                pattern_type=ind.get('pattern_type', ''),
                match_text=ind.get('match_text', ''),
                confidence=ind.get('confidence', 0.0),
                location=ind.get('location', ''),
                context=ind.get('context', '')
            )
            for ind in detection_results.get('primary_indicators', [])
        ]
        
        secondary_indicators = [
            PatternIndicator(
                pattern_type=ind.get('pattern_type', ''),
                match_text=ind.get('match_text', ''),
                confidence=ind.get('confidence', 0.0),
                location=ind.get('location', ''),
                context=ind.get('context', '')
            )
            for ind in detection_results.get('secondary_indicators', [])
        ]
        
        detection_result = DetectionResult(
            document_id=document_id,
            detected_type=DocumentType(detected_type),
            confidence=confidence,
            confidence_level=confidence_level,
            primary_indicators=primary_indicators,
            secondary_indicators=secondary_indicators,
            reasoning=detection_results.get('reasoning', ''),
            requires_confirmation=requires_confirmation,
            auto_process_countdown=auto_process_countdown
        )
        
        return DocumentDetectionResponse(
            document_id=document_id,
            status=DocumentStatus.DETECTION_COMPLETE,
            detection_result=detection_result,
            message="Detection completed successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting detection status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get detection status: {str(e)}")

@router.post("/{document_id}/confirm-detection")
async def confirm_detection_result(
    document_id: str,
    validation: DocumentValidationRequest
):
    """User confirms or corrects document detection result"""
    try:
        logger.info(f"Confirming detection for document: {document_id}")
        
        document = await supabase_service.get_document(document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Update document with user confirmation
        updates = {
            'ocr_status': 'processing' if validation.proceed_with_processing else 'detection_complete'
        }
        
        # Store user validation in parsed_index
        parsed_index = document.get('parsed_index', {})
        if 'detection_results' not in parsed_index:
            parsed_index['detection_results'] = {}
        
        parsed_index['detection_results']['user_confirmed_type'] = validation.confirmed_type.value
        parsed_index['detection_results']['user_corrections'] = validation.user_corrections
        parsed_index['detection_results']['user_notes'] = validation.user_notes
        parsed_index['detection_results']['confirmed_at'] = datetime.utcnow().isoformat()
        
        updates['parsed_index'] = parsed_index
        
        updated_document = await supabase_service.update_document_status(
            document_id, 
            updates['ocr_status'], 
            updates
        )
        
        if validation.proceed_with_processing:
            # TODO: Trigger full document processing (Stage 0B)
            # from app.tasks.document_tasks import process_document_full_analysis
            # process_document_full_analysis.delay(document_id, validation.user_id)
            logger.info(f"Queuing document {document_id} for full processing")
        
        return {
            "document_id": document_id,
            "status": updates['ocr_status'],
            "confirmed_type": validation.confirmed_type.value,
            "message": "Detection result confirmed successfully" + (
                ". Starting full processing..." if validation.proceed_with_processing 
                else ". Ready for manual processing trigger."
            )
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error confirming detection: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to confirm detection: {str(e)}")

@router.post("/{document_id}/manual-detection")
async def manual_detection_trigger(document_id: str):
    """Temporary endpoint to manually trigger detection without Celery"""
    try:
        logger.info(f"Manual detection trigger for document: {document_id}")
        
        # Import the detection task function directly
        from app.tasks.document_tasks import process_document_quick_detection
        from app.services.azure_service import AzureDocumentIntelligenceService
        from app.services.detection_service import DetectionService
        from app.services.supabase_service import SupabaseService
        
        # Get document info
        document = await supabase_service.get_document(document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
            
        logger.info(f"Processing document: {document.get('file_name')} at {document.get('storage_path')}")
        
        # Update status to detecting
        await supabase_service.update_document_status(
            document_id, 
            "detecting",
            {"processing_stage": "detecting"}
        )
        
        # Initialize services
        azure_service = AzureDocumentIntelligenceService()
        nmtc_detector = DetectionService()
        
        # Download PDF from Supabase Storage
        supabase_client = SupabaseService()
        file_url = supabase_client.get_signed_url(document['storage_path'])
        
        # Extract text using Azure Document Intelligence
        logger.info("Starting Azure Document Intelligence extraction...")
        extraction_result = await azure_service.analyze_document_quick(file_url)
        
        if not extraction_result or not extraction_result.get('content'):
            raise Exception("Failed to extract text from document")
            
        # Detect document type using NMTC patterns
        logger.info("Starting NMTC document type detection...")
        detection_result = await nmtc_detector.process_quick_detection(document_id, extraction_result['content'])
        
        # Update document with results
        updates = {
            'ocr_status': 'detection_complete',
            'processing_stage': 'detection_complete',
            'document_type_id': detection_result.get('detected_type'),
            'confidence_score': detection_result.get('confidence', 0.0),
            'parsed_index': {
                'detection_results': {
                    'detected_type': detection_result.get('detected_type'),
                    'confidence': detection_result.get('confidence', 0.0),
                    'confidence_level': detection_result.get('confidence_level', 'low'),
                    'reasoning': detection_result.get('reasoning', ''),
                    'extracted_metadata': detection_result.get('extracted_metadata', {}),
                    'requires_confirmation': detection_result.get('requires_confirmation', True),
                    'detected_at': datetime.utcnow().isoformat()
                },
                'azure_extraction': extraction_result
            }
        }
        
        updated_document = await supabase_service.update_document_status(
            document_id,
            updates['ocr_status'],
            updates
        )
        
        return {
            "document_id": document_id,
            "status": "detection_complete",
            "detection_result": detection_result,
            "extraction_summary": {
                "content_length": len(extraction_result['content']),
                "pages_processed": extraction_result.get('pages', 0)
            },
            "message": "Manual detection completed successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Manual detection error: {e}")
        await supabase_service.update_document_status(
            document_id,
            "error",
            {"error_message": str(e), "processing_stage": "error"}
        )
        raise HTTPException(status_code=500, detail=f"Manual detection failed: {str(e)}")
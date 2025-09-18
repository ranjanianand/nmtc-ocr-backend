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

@router.get("/types")
async def get_document_types():
    """Get available document types from database"""
    try:
        # Get document types from database
        result = supabase_service.client.table('document_types').select('id, key, display_name, status').eq('status', 'active').execute()
        
        if result.data:
            types = [
                {
                    "id": doc_type["id"],
                    "key": doc_type["key"], 
                    "display_name": doc_type["display_name"]
                }
                for doc_type in result.data
            ]
        else:
            # Fallback to hardcoded types if database is empty
            types = [
                {"id": None, "key": "allocation_agreement", "display_name": "Allocation Agreement"},
                {"id": None, "key": "qlici_loan", "display_name": "QLICI Loan Document"},
                {"id": None, "key": "qalicb_certification", "display_name": "QALICB Certification"},
                {"id": None, "key": "cba", "display_name": "Community Benefit Agreement"},
                {"id": None, "key": "annual_compliance_report", "display_name": "Annual Compliance Report"},
                {"id": None, "key": "financial_statement", "display_name": "Financial Statement"},
                {"id": None, "key": "promissory_note", "display_name": "Promissory Note"},
                {"id": None, "key": "insurance", "display_name": "Insurance Document"},
                {"id": None, "key": "other", "display_name": "Other NMTC Document"}
            ]
        
        return {
            "document_types": types,
            "total": len(types)
        }
        
    except Exception as e:
        logger.error(f"Failed to get document types: {str(e)}")
        # Return fallback types on error
        types = [
            {"id": None, "key": "other", "display_name": "Other NMTC Document"}
        ]
        return {
            "document_types": types,
            "total": len(types)
        }

@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    document_type_id: str = Form(...),  # Required document type ID
    description: Optional[str] = Form(None),  # Optional description/notes
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
                'file_size': file_size,
                'document_type_id': document_type_id,
                'user_selected_type': True,  # Mark as user-selected
                'description': description or ''  # Add description field
            }
            
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
        
        # SYNCHRONOUS PROCESSING: Azure OCR + Direct Processing (Stage 0A)
        logger.info("Starting immediate processing: Azure OCR + Core Processing...")
        
        try:
            # Step 1: Azure OCR Processing
            logger.info("Step 1: Azure OCR processing...")
            from app.services.azure_service import azure_service
            
            ocr_result = await azure_service.analyze_document_quick(file_content, document_id)
            extracted_text = ocr_result.get('full_text', '')
            page_count = len(ocr_result.get('pages', []))
            
            logger.info(f"Azure OCR completed: {len(extracted_text)} chars, {page_count} pages")
            
            # Step 2: SKIP NMTC Detection - Use User Selected Type
            logger.info("Step 2: Using user-selected document type (skipping AI detection)...")
            
            # User has already provided document_type_id, so we skip detection entirely
            detected_type = "user_selected"
            confidence = 1.0  # User selection has 100% confidence
            confidence_level = 'high'
            
            logger.info(f"NMTC Detection completed: {detected_type} ({confidence}% confidence, {confidence_level})")
            
            # Step 3: TRIGGER CORE PROCESSING ENGINE
            logger.info("Step 3: Triggering core processing engine...")
            
            # Import the corrected workflow service
            from app.services.corrected_workflow_service import corrected_workflow_service
            
            # Start core processing pipeline
            try:
                logger.info(f"Starting core processing for document {document_id}")
                
                # Create processing session first
                from app.services.database_service import DatabaseService
                db_service = DatabaseService()
                session_id = await db_service.create_processing_session(
                    document_id=document_id,
                    user_id=user_id,
                    org_id=org_id
                )
                
                # Execute complete workflow
                workflow_result = await corrected_workflow_service.execute_complete_workflow(
                    session_id=session_id,
                    document_id=document_id,
                    org_id=org_id
                )
                
                if workflow_result and workflow_result.get('success'):
                    logger.info(f"Core processing completed successfully: {session_id}")
                    core_processing_success = True
                    processing_session_id = session_id
                else:
                    logger.error(f"Core processing failed: {workflow_result}")
                    core_processing_success = False
                    processing_session_id = None
                    
            except Exception as core_error:
                logger.error(f"Core processing engine error: {core_error}")
                core_processing_success = False
                processing_session_id = None
            
            # Step 4: Post-Processing - Allocation Year Detection
            logger.info("Step 4: Running post-processing analysis...")
            
            allocation_analysis = None
            if core_processing_success and processing_session_id:
                try:
                    from app.services.allocation_year_service import allocation_year_service
                    
                    # Prepare processing results for allocation analysis
                    processing_results_for_analysis = {
                        'extracted_text': extracted_text,
                        'parsed_index': {
                            'extracted_text': extracted_text,
                            'page_count': page_count,
                            'character_count': len(extracted_text),
                            'detected_type': detected_type,
                            'confidence': confidence
                        }
                    }
                    
                    # Run allocation year analysis
                    allocation_analysis = await allocation_year_service.analyze_for_allocation_data(
                        document_id=document_id,
                        processing_results=processing_results_for_analysis
                    )
                    
                    if allocation_analysis:
                        logger.info(f"Allocation analysis completed: {allocation_analysis}")
                    else:
                        logger.info("No allocation data detected - document is not allocation-related")
                        
                except Exception as allocation_error:
                    logger.error(f"Allocation analysis error (non-critical): {allocation_error}")
                    # Don't fail the whole workflow if allocation analysis fails
                    allocation_analysis = None
            
            # Step 5: Store processing results
            logger.info("Step 5: Storing processing results...")
            
            processing_results = {
                'ocr_status': 'done',
                'parsed_index': {
                    'extracted_text': extracted_text,
                    'page_count': page_count,
                    'character_count': len(extracted_text),
                    'detected_type': detected_type,
                    'confidence': confidence,
                    'confidence_level': confidence_level,
                    'processing_completed_at': datetime.utcnow().isoformat(),
                    'core_processing': {
                        'success': core_processing_success,
                        'session_id': processing_session_id,
                        'triggered_at': datetime.utcnow().isoformat()
                    },
                    'allocation_analysis': allocation_analysis  # Add allocation analysis results
                }
            }
            
            updated_record = await supabase_service.update_document_status(
                document_id=document_id,
                status='done',
                updates=processing_results
            )
            
            logger.info("Processing completed successfully!")
            
            # Return comprehensive response with results
            success_message = f"Document processed successfully! Detected: {detected_type}. Core processing: {'SUCCESS' if core_processing_success else 'FAILED'}"
            
            if allocation_analysis and allocation_analysis.get('allocation_detected'):
                success_message += f" | Allocation Year: {allocation_analysis.get('allocation_data', {}).get('year', 'Unknown')}"
            
            return {
                "document_id": document_id,
                "status": "completed",
                "message": success_message,
                "file_path": file_path,
                "processing_results": {
                    "detected_type": detected_type,
                    "confidence": confidence,
                    "confidence_level": confidence_level,
                    "page_count": page_count,
                    "character_count": len(extracted_text),
                    "requires_confirmation": confidence < 90,
                    "auto_process_ready": confidence >= 90,
                    "core_processing": {
                        "success": core_processing_success,
                        "session_id": processing_session_id,
                        "workflow_triggered": True
                    },
                    "allocation_analysis": allocation_analysis  # Include allocation analysis results
                }
            }
            
        except Exception as processing_error:
            logger.error(f"Processing error: {processing_error}")
            
            # Update document status to error
            try:
                await supabase_service.update_document_status(
                    document_id=document_id,
                    status='done',
                    updates={'parsed_index': {'error': str(processing_error), 'stage': 'processing'}}
                )
            except:
                pass
            
            # Return error response but document was still uploaded
            return {
                "document_id": document_id,
                "status": "error", 
                "message": f"Upload successful but processing failed: {str(processing_error)}",
                "file_path": file_path,
                "error": str(processing_error)
            }
        
    except HTTPException as http_error:
        logger.error(f"HTTP exception: {http_error.detail}")
        raise http_error
        
    except Exception as general_error:
        logger.error(f"Unexpected error: {general_error}")
        logger.error(f"Error type: {type(general_error)}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(general_error)}")

@router.get("/{document_id}/status")
async def get_document_status(document_id: str):
    """Get current processing status of document with detection results - Updated"""
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
        logger.info(f"DEBUG: parsed_index keys: {list(parsed_index.keys()) if parsed_index else 'None'}")
        
        # Check for detection results in both possible locations
        detection_data = None
        if 'detection_results' in parsed_index:
            logger.info(f"DEBUG: Found detection_results in nested structure")
            detection_data = parsed_index['detection_results']
        elif 'detected_type' in parsed_index and 'confidence' in parsed_index:
            logger.info(f"DEBUG: Found detection data directly in parsed_index")
            # Detection results stored directly in parsed_index
            detection_data = parsed_index
            
        if detection_data:
            response['detection'] = {
                "detected_type": detection_data.get('detected_type') or detection_data.get('document_type_detected'),
                "confidence": detection_data.get('confidence', 0.0),
                "reasoning": detection_data.get('reasoning', ''),
                "primary_indicators_count": len(detection_data.get('primary_indicators', [])),
                "secondary_indicators_count": len(detection_data.get('secondary_indicators', [])),
                "processed_at": detection_data.get('processed_at') or detection_data.get('processing_completed_at'),
                "user_confirmed_type": detection_data.get('user_confirmed_type'),
                "confirmed_at": detection_data.get('confirmed_at'),
                "confidence_level": detection_data.get('confidence_level', 'low')
            }
            
            # Add confidence level and requirements based on confidence score
            confidence = detection_data.get('confidence', 0.0)
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

@router.get("/allocation-years/{org_id}")
async def get_organization_allocation_years(org_id: str):
    """Get all allocation years for an organization"""
    try:
        from app.services.allocation_year_service import allocation_year_service
        
        allocation_years = await allocation_year_service.get_allocation_years_for_org(org_id)
        
        return {
            "org_id": org_id,
            "total_allocation_years": len(allocation_years),
            "allocation_years": allocation_years
        }
        
    except Exception as e:
        logger.error(f"Error fetching allocation years for org {org_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch allocation years: {str(e)}")

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
            "done",
            {"parsed_index": {"error": str(e), "processing_stage": "error"}}
        )
        raise HTTPException(status_code=500, detail=f"Manual detection failed: {str(e)}")


# =====================================================
# NEW WORKFLOW RESULT RETRIEVAL API ENDPOINTS
# =====================================================

@router.get("/{document_id}/workflow-results")
async def get_workflow_results(document_id: str):
    """Get comprehensive workflow results for a document"""
    try:
        from app.services.database_service import database_service
        
        # Get all processing sessions for this document
        sessions = await database_service.get_processing_sessions_by_document(uuid.UUID(document_id))
        
        if not sessions:
            raise HTTPException(status_code=404, detail="No processing sessions found for this document")
        
        # Get the latest session
        latest_session = sessions[0]  # Assuming sessions are ordered by created_at desc
        session_id = latest_session['id']
        
        # Get workflow stage completions
        workflow_progress = await database_service.get_workflow_progress(session_id)
        
        # Get agent workflow results
        workflow_results = await database_service.get_agent_workflow_results(session_id, uuid.UUID(document_id))
        
        # Get extraction results
        extractions = await database_service.get_agent_extraction_results(session_id)
        
        # Get risk assessments
        risk_assessments = await database_service.get_risk_assessment_results(session_id)
        
        # Get generated reports
        reports = await database_service.get_generated_reports(session_id)
        
        return {
            "document_id": document_id,
            "session_id": str(session_id),
            "session_info": latest_session,
            "workflow_progress": workflow_progress,
            "workflow_results": workflow_results[0] if workflow_results else None,
            "extraction_results": {
                "total_extractions": len(extractions),
                "extractions": extractions
            },
            "risk_assessment": {
                "total_risks": len(risk_assessments),
                "risk_assessments": risk_assessments
            },
            "generated_reports": {
                "total_reports": len(reports),
                "reports": reports
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving workflow results: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve workflow results: {str(e)}")

@router.get("/{document_id}/extraction-results")
async def get_extraction_results(document_id: str):
    """Get detailed extraction results for a document"""
    try:
        from app.services.database_service import database_service
        
        # Get latest processing session
        sessions = await database_service.get_processing_sessions_by_document(uuid.UUID(document_id))
        if not sessions:
            raise HTTPException(status_code=404, detail="No processing sessions found")
        
        session_id = sessions[0]['id']
        
        # Get extraction results with section and query details
        extractions = await database_service.get_agent_extraction_results(session_id)
        
        # Get normalization applications
        normalizations = await database_service.get_normalization_applications(session_id)
        
        # Group extractions by section
        extractions_by_section = {}
        for extraction in extractions:
            section_name = extraction.get('section_name', 'Unknown Section')
            if section_name not in extractions_by_section:
                extractions_by_section[section_name] = []
            extractions_by_section[section_name].append(extraction)
        
        return {
            "document_id": document_id,
            "session_id": str(session_id),
            "total_extractions": len(extractions),
            "extractions_by_section": extractions_by_section,
            "normalization_summary": {
                "total_normalizations": len(normalizations),
                "normalizations": normalizations
            },
            "extraction_metrics": {
                "sections_processed": len(extractions_by_section),
                "average_confidence": sum(e.get('confidence_score', 0) for e in extractions) / len(extractions) if extractions else 0,
                "extraction_methods": list(set(e.get('extraction_method', 'unknown') for e in extractions))
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving extraction results: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve extraction results: {str(e)}")

@router.get("/{document_id}/risk-assessment")
async def get_risk_assessment(document_id: str):
    """Get risk assessment results for a document"""
    try:
        from app.services.database_service import database_service
        
        # Get latest processing session
        sessions = await database_service.get_processing_sessions_by_document(uuid.UUID(document_id))
        if not sessions:
            raise HTTPException(status_code=404, detail="No processing sessions found")
        
        session_id = sessions[0]['id']
        
        # Get risk assessments
        risk_assessments = await database_service.get_risk_assessment_results(session_id)
        
        # Get business rule evaluations
        business_rule_results = await database_service.get_business_rule_evaluations(session_id)
        
        # Calculate risk summary
        risk_by_category = {}
        for risk in risk_assessments:
            category = risk.get('risk_category', 'unknown')
            if category not in risk_by_category:
                risk_by_category[category] = []
            risk_by_category[category].append(risk)
        
        # Calculate overall risk metrics
        risk_scores = [r.get('risk_score', 0) for r in risk_assessments]
        overall_risk_score = sum(risk_scores) / len(risk_scores) if risk_scores else 0
        
        risk_levels = [r.get('risk_level', 'low') for r in risk_assessments]
        highest_risk_level = 'low'
        if 'critical' in risk_levels:
            highest_risk_level = 'critical'
        elif 'high' in risk_levels:
            highest_risk_level = 'high'
        elif 'medium' in risk_levels:
            highest_risk_level = 'medium'
        
        return {
            "document_id": document_id,
            "session_id": str(session_id),
            "overall_risk_score": overall_risk_score,
            "highest_risk_level": highest_risk_level,
            "risk_by_category": risk_by_category,
            "business_rule_evaluations": {
                "total_rules_evaluated": len(business_rule_results),
                "rules_passed": len([r for r in business_rule_results if r.get('evaluation_result', False)]),
                "rules_failed": len([r for r in business_rule_results if not r.get('evaluation_result', True)]),
                "evaluations": business_rule_results
            },
            "risk_summary": {
                "total_risks_identified": len(risk_assessments),
                "critical_risks": len([r for r in risk_assessments if r.get('risk_level') == 'critical']),
                "high_risks": len([r for r in risk_assessments if r.get('risk_level') == 'high']),
                "medium_risks": len([r for r in risk_assessments if r.get('risk_level') == 'medium']),
                "low_risks": len([r for r in risk_assessments if r.get('risk_level') == 'low'])
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving risk assessment: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve risk assessment: {str(e)}")

@router.get("/{document_id}/reports")
async def get_generated_reports(document_id: str):
    """Get all generated reports for a document"""
    try:
        from app.services.database_service import database_service
        
        # Get latest processing session
        sessions = await database_service.get_processing_sessions_by_document(uuid.UUID(document_id))
        if not sessions:
            raise HTTPException(status_code=404, detail="No processing sessions found")
        
        session_id = sessions[0]['id']
        
        # Get generated reports
        reports = await database_service.get_generated_reports(session_id)
        
        # Get agent prompt applications (for insights into how reports were generated)
        agent_applications = await database_service.get_agent_prompt_applications(session_id)
        
        return {
            "document_id": document_id,
            "session_id": str(session_id),
            "total_reports": len(reports),
            "reports": reports,
            "agent_applications": {
                "total_applications": len(agent_applications),
                "applications": agent_applications
            },
            "report_summary": {
                "report_formats": list(set(r.get('report_format', 'unknown') for r in reports)),
                "report_types": list(set(r.get('report_type', 'unknown') for r in reports)),
                "total_downloads": sum(r.get('download_count', 0) for r in reports)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving reports: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve reports: {str(e)}")

@router.get("/{document_id}/processing-sessions")
async def get_processing_sessions(document_id: str):
    """Get all processing sessions for a document"""
    try:
        from app.services.database_service import database_service
        
        # Get processing sessions
        sessions = await database_service.get_processing_sessions_by_document(uuid.UUID(document_id))
        
        if not sessions:
            raise HTTPException(status_code=404, detail="No processing sessions found")
        
        # Get agent states for each session
        sessions_with_agents = []
        for session in sessions:
            session_id = session['id']
            
            # Get agent states
            agent_states = await database_service.get_agent_states(session_id)
            
            # Get workflow progress
            workflow_progress = await database_service.get_workflow_progress(session_id)
            
            sessions_with_agents.append({
                **session,
                'agent_states': agent_states,
                'workflow_progress': workflow_progress
            })
        
        return {
            "document_id": document_id,
            "total_sessions": len(sessions),
            "sessions": sessions_with_agents
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving processing sessions: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve processing sessions: {str(e)}")
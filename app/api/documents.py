from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import JSONResponse
from app.models.document import *
from app.services.supabase_service import supabase_service
from app.config import settings
import uuid
import os
import aiofiles
from typing import Optional
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
            metadata = {
                'filename': file.filename,
                'document_type': document_type,
                'cde_name': cde_name,
                'client_info': client_info,
                'file_size': file_size
            }
            
            logger.info(f"Creating document record with metadata: {metadata}")
            
            document_record = await supabase_service.create_document_record(
                org_id=org_id,
                file_path=file_path,
                metadata=metadata
            )
            
            if not document_record:
                raise Exception("Failed to create document record - no data returned")
            
            document_id = document_record['id']
            logger.info(f"Document record created successfully: {document_id}")
            
        except Exception as db_error:
            logger.error(f"Database error: {db_error}")
            logger.error(f"Database error type: {type(db_error)}")
            raise HTTPException(status_code=500, detail=f"Database operation failed: {str(db_error)}")
        
        # TODO: Queue for quick document detection (Stage 0A)
        # celery_app.send_task("quick_document_detection", args=[document_id])
        
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
    """Get current processing status of document"""
    try:
        logger.info(f"Getting status for document: {document_id}")
        
        document = await supabase_service.get_document(document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        return {
            "document_id": document_id,
            "ocr_status": document.get('ocr_status'),
            "filename": document.get('filename'),
            "storage_path": document.get('storage_path'),
            "uploaded_at": document.get('uploaded_at'),
            "mime_type": document.get('mime_type'),
            "org_id": document.get('org_id')
        }
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
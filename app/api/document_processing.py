from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, BackgroundTasks
from app.models.database import *
from app.services.database_service import database_service
from app.tasks.document_tasks import process_document_quick_detection, get_document_processing_status
from app.utils.auth import get_current_user_with_org, UserContext, log_user_action
from app.utils.exceptions import DocumentProcessingError, ValidationError
from app.utils.logging_config import get_structured_logger
from typing import Dict, Any, List
import uuid
from datetime import datetime
import io

router = APIRouter(prefix="/api/v1/documents", tags=["Document Processing"])
structured_logger = get_structured_logger(__name__)


@router.post("/upload", response_model=Dict[str, Any])
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    document_type_id: str = None,
    user: UserContext = Depends(get_current_user_with_org)
):
    """
    Upload a document and start quick detection processing
    
    This endpoint:
    1. Validates the uploaded file
    2. Stores it in Supabase storage
    3. Creates a document record in the database
    4. Queues it for quick detection processing
    """
    try:
        # Require organization context
        org = await user.require_organization_context()
        
        # Validate file
        if not file.filename.endswith('.pdf'):
            raise ValidationError("Only PDF files are supported", "file_type", file.filename)
        
        # Check file size (50MB limit)
        file_content = await file.read()
        if len(file_content) > 50 * 1024 * 1024:
            raise ValidationError(f"File size {len(file_content)} bytes exceeds 50MB limit", "file_size")
        
        structured_logger.info("Processing document upload",
                             filename=file.filename,
                             file_size=len(file_content),
                             org_id=str(org.id),
                             user_id=str(user.user_id))
        
        # Generate storage path
        document_id = uuid.uuid4()
        storage_path = f"organizations/{org.id}/documents/{document_id}_{file.filename}"
        
        try:
            # Upload to Supabase storage
            database_service.upload_file(storage_path, file_content, file.content_type or "application/pdf")
            
            # Create document record
            doc_create = DocumentCreate(
                document_type_id=uuid.UUID(document_type_id) if document_type_id else None,
                filename=file.filename,
                storage_path=storage_path,
                mime_type=file.content_type or "application/pdf"
            )
            
            document = await database_service.create_document(
                org_id=org.id,
                doc_data=doc_create,
                uploaded_by=user.user_id
            )
            
            if not document:
                raise DocumentProcessingError("Failed to create document record")
            
            # Log the action
            await log_user_action(
                user=user,
                action="document_uploaded",
                scope="document",
                record_id=document.id
            )
            
            # Queue for processing
            task = process_document_quick_detection.delay(
                str(document.id),
                str(user.user_id)
            )
            
            structured_logger.info("Document uploaded and queued for processing",
                                 document_id=str(document.id),
                                 task_id=task.id,
                                 filename=file.filename)
            
            return {
                "document_id": str(document.id),
                "filename": file.filename,
                "status": document.ocr_status.value,
                "task_id": task.id,
                "storage_path": storage_path,
                "uploaded_at": document.uploaded_at.isoformat(),
                "message": "Document uploaded successfully and queued for processing"
            }
            
        except Exception as storage_error:
            structured_logger.error("Failed to upload document to storage",
                                  filename=file.filename,
                                  error=str(storage_error))
            raise DocumentProcessingError(f"Storage upload failed: {storage_error}")
            
    except Exception as e:
        structured_logger.error("Document upload failed",
                              filename=file.filename if file else "unknown",
                              error=str(e))
        raise


@router.get("/{document_id}/status", response_model=Dict[str, Any])
async def get_document_status(
    document_id: str,
    user: UserContext = Depends(get_current_user_with_org)
):
    """Get the current processing status of a document"""
    try:
        document_uuid = uuid.UUID(document_id)
        
        # Get document and verify access
        document = await database_service.get_document(document_uuid)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        if not user.can_access_document(document):
            raise HTTPException(status_code=403, detail="Access denied to document")
        
        # Get processing status from task
        status_info = get_document_processing_status.delay(document_id).get(timeout=5)
        
        return status_info
        
    except uuid.UUID as e:
        raise HTTPException(status_code=400, detail="Invalid document ID format")
    except Exception as e:
        structured_logger.error("Failed to get document status",
                              document_id=document_id,
                              error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{document_id}", response_model=Dict[str, Any])
async def get_document_details(
    document_id: str,
    user: UserContext = Depends(get_current_user_with_org)
):
    """Get detailed information about a document including OCR results"""
    try:
        document_uuid = uuid.UUID(document_id)
        
        # Get document and verify access
        document = await database_service.get_document(document_uuid)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        if not user.can_access_document(document):
            raise HTTPException(status_code=403, detail="Access denied to document")
        
        # Build response with OCR results if available
        response = {
            "document_id": str(document.id),
            "filename": document.filename,
            "mime_type": document.mime_type,
            "uploaded_at": document.uploaded_at.isoformat(),
            "uploaded_by": str(document.uploaded_by),
            "ocr_status": document.ocr_status.value,
            "organization_id": str(document.org_id)
        }
        
        # Add OCR results if available
        if document.parsed_index:
            ocr_results = document.parsed_index.get("ocr_results", {})
            if ocr_results:
                response["ocr_results"] = {
                    "page_count": ocr_results.get("page_count", 0),
                    "character_count": len(ocr_results.get("full_text", "")),
                    "overall_confidence": ocr_results.get("overall_confidence"),
                    "processing_duration_ms": ocr_results.get("processing_duration_ms", 0),
                    "processed_at": ocr_results.get("processed_at")
                }
                
                # Include full text if requested (could be large)
                include_text = False  # Could be a query parameter
                if include_text:
                    response["full_text"] = ocr_results.get("full_text", "")
            
            # Add processing history
            processing_history = document.parsed_index.get("processing_history", [])
            if processing_history:
                response["processing_history"] = processing_history
        
        return response
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid document ID format")
    except Exception as e:
        structured_logger.error("Failed to get document details",
                              document_id=document_id,
                              error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=Dict[str, Any])
async def list_documents(
    status: str = None,
    limit: int = 50,
    offset: int = 0,
    user: UserContext = Depends(get_current_user_with_org)
):
    """List documents for the current organization with optional filtering"""
    try:
        org = await user.require_organization_context()
        
        # Filter by status if provided
        status_filter = None
        if status:
            try:
                status_filter = OcrStatus(status)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
        
        if status_filter:
            documents = await database_service.get_documents_by_status(
                org_id=org.id,
                status=status_filter,
                limit=limit
            )
        else:
            documents = await database_service.get_organization_documents(
                org_id=org.id,
                limit=limit,
                offset=offset
            )
        
        # Build response
        document_list = []
        for doc in documents:
            doc_info = {
                "document_id": str(doc.id),
                "filename": doc.filename,
                "uploaded_at": doc.uploaded_at.isoformat(),
                "ocr_status": doc.ocr_status.value,
                "document_type_id": str(doc.document_type_id) if doc.document_type_id else None
            }
            
            # Add processing summary if available
            if doc.parsed_index:
                ocr_results = doc.parsed_index.get("ocr_results", {})
                if ocr_results:
                    doc_info["page_count"] = ocr_results.get("page_count", 0)
                    doc_info["character_count"] = len(ocr_results.get("full_text", ""))
                    doc_info["confidence"] = ocr_results.get("overall_confidence")
            
            document_list.append(doc_info)
        
        # Get processing statistics
        stats = await database_service.get_document_processing_stats(org.id)
        
        return {
            "documents": document_list,
            "total_count": len(documents),
            "processing_stats": stats,
            "filters": {"status": status},
            "pagination": {"limit": limit, "offset": offset}
        }
        
    except Exception as e:
        structured_logger.error("Failed to list documents",
                              org_id=str(org.id) if org else None,
                              error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{document_id}/search", response_model=Dict[str, Any])
async def search_document_content(
    document_id: str,
    query: str,
    user: UserContext = Depends(get_current_user_with_org)
):
    """Search within a specific document's OCR content"""
    try:
        document_uuid = uuid.UUID(document_id)
        org = await user.require_organization_context()
        
        # Verify document access
        document = await database_service.get_document(document_uuid)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        if not user.can_access_document(document):
            raise HTTPException(status_code=403, detail="Access denied to document")
        
        # Search in document content
        if not document.parsed_index or "ocr_results" not in document.parsed_index:
            return {
                "document_id": document_id,
                "query": query,
                "matches": [],
                "message": "Document has not been processed yet"
            }
        
        ocr_results = document.parsed_index["ocr_results"]
        full_text = ocr_results.get("full_text", "").lower()
        query_lower = query.lower()
        
        # Simple search implementation
        matches = []
        if query_lower in full_text:
            # Find all occurrences
            start = 0
            while True:
                pos = full_text.find(query_lower, start)
                if pos == -1:
                    break
                
                # Extract context around match
                context_start = max(0, pos - 100)
                context_end = min(len(full_text), pos + len(query) + 100)
                context = full_text[context_start:context_end]
                
                matches.append({
                    "position": pos,
                    "context": context,
                    "match_text": full_text[pos:pos + len(query)]
                })
                
                start = pos + 1
        
        return {
            "document_id": document_id,
            "query": query,
            "total_matches": len(matches),
            "matches": matches[:10],  # Limit to first 10 matches
            "document_info": {
                "filename": document.filename,
                "page_count": ocr_results.get("page_count", 0),
                "character_count": len(ocr_results.get("full_text", ""))
            }
        }
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid document ID format")
    except Exception as e:
        structured_logger.error("Document search failed",
                              document_id=document_id,
                              query=query,
                              error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{document_id}/reprocess")
async def reprocess_document(
    document_id: str,
    background_tasks: BackgroundTasks,
    user: UserContext = Depends(get_current_user_with_org)
):
    """Reprocess a document (useful for failed or error status documents)"""
    try:
        document_uuid = uuid.UUID(document_id)
        
        # Get document and verify access
        document = await database_service.get_document(document_uuid)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        if not user.can_modify_document(document):
            raise HTTPException(status_code=403, detail="Insufficient permissions to reprocess document")
        
        # Reset status to queued
        await database_service.update_document_ocr_status(document_uuid, OcrStatus.QUEUED)
        
        # Queue for processing
        task = process_document_quick_detection.delay(
            str(document.id),
            str(user.user_id)
        )
        
        # Log the action
        await log_user_action(
            user=user,
            action="document_reprocessed",
            scope="document",
            record_id=document.id
        )
        
        structured_logger.info("Document queued for reprocessing",
                             document_id=document_id,
                             task_id=task.id,
                             user_id=str(user.user_id))
        
        return {
            "document_id": document_id,
            "status": "queued",
            "task_id": task.id,
            "message": "Document queued for reprocessing"
        }
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid document ID format")
    except Exception as e:
        structured_logger.error("Document reprocessing failed",
                              document_id=document_id,
                              error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
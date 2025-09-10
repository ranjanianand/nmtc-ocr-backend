from celery import Celery
from app.config import settings
from app.services.azure_service import azure_service
from app.services.database_service import database_service
from app.services.detection_service import detection_service
from app.models.database import OcrStatus, DocumentUpdate
from app.utils.exceptions import (
    DocumentProcessingError, 
    OCRProcessingError, 
    DatabaseError,
    StorageError
)
import uuid
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import asyncio

logger = logging.getLogger(__name__)
# Removed structured logger to avoid circular import

# Initialize Celery app
celery_app = Celery(
    "nmtc-backend",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

# Configure Celery
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50,
)


def run_async(coro):
    """Helper to run async functions in Celery tasks"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(coro)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=300)
def process_document_quick_detection(self, document_id: str, user_id: str = None):
    """
    Celery task for quick document detection and OCR processing
    
    Args:
        document_id: UUID string of the document to process
        user_id: UUID string of the user who initiated the processing
        
    Returns:
        Dict containing processing results
    """
    document_uuid = uuid.UUID(document_id)
    user_uuid = uuid.UUID(user_id) if user_id else None
    
    logger.info("Starting quick document detection task",
                         document_id=document_id,
                         user_id=user_id,
                         task_id=self.request.id)
    
    try:
        # Step 1: Get document from database
        document = run_async(database_service.get_document(document_uuid))
        if not document:
            error_msg = f"Document {document_id} not found"
            logger.error("Document not found for processing",
                                  document_id=document_id)
            raise DocumentProcessingError(error_msg, document_uuid, "document_lookup")
        
        logger.info("Document retrieved from database",
                             document_id=document_id,
                             filename=document.filename,
                             storage_path=document.storage_path,
                             current_status=document.ocr_status)
        
        # Step 2: Update status to processing
        run_async(database_service.update_document(
            document_uuid,
            DocumentUpdate(ocr_status=OcrStatus.PROCESSING)
        ))
        
        logger.info("Updated document status to processing",
                             document_id=document_id)
        
        # Step 3: Download PDF from Supabase Storage
        try:
            logger.info("Downloading document from storage",
                                 document_id=document_id,
                                 storage_path=document.storage_path)
            
            # Download file content from Supabase storage
            try:
                # Use the storage client to download the file
                result = database_service.client.storage.from_('documents').download(document.storage_path)
                if not result:
                    raise StorageError(f"Failed to download file: {document.storage_path}")
                
                document_content = result
                logger.info("Successfully downloaded document from storage",
                                     document_id=document_id,
                                     file_size=len(document_content))
                
            except Exception as download_error:
                # Fallback: try getting public URL and downloading via HTTP
                logger.warning("Direct download failed, trying public URL method",
                                        document_id=document_id,
                                        error=str(download_error))
                
                file_url = database_service.get_file_url(document.storage_path)
                if not file_url:
                    raise StorageError(f"Could not get URL for file: {document.storage_path}")
                
                import requests
                import asyncio
                
                def download_file():
                    response = requests.get(file_url, timeout=30)
                    response.raise_for_status()
                    return response.content
                
                # Run the synchronous request in a thread
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    document_content = executor.submit(download_file).result()
                
                logger.info("Downloaded document via public URL",
                                     document_id=document_id,
                                     file_size=len(document_content))
            
        except Exception as e:
            error_msg = f"Failed to download document from storage: {str(e)}"
            logger.error("Document download failed",
                                  document_id=document_id,
                                  storage_path=document.storage_path,
                                  error=str(e))
            
            # Update status to error
            run_async(database_service.update_document(
                document_uuid,
                DocumentUpdate(ocr_status=OcrStatus.ERROR)
            ))
            
            raise StorageError(error_msg, document.storage_path)
        
        # Step 4: Send to Azure OCR for quick text extraction
        try:
            analysis_result = run_async(azure_service.analyze_document_quick(
                document_content=document_content,
                document_id=document_uuid,
                content_type=document.mime_type
            ))
            
            logger.info("Azure OCR analysis completed",
                                 document_id=document_id,
                                 pages_processed=analysis_result.get('page_count', 0),
                                 characters_extracted=len(analysis_result.get('full_text', '')),
                                 processing_duration=analysis_result.get('processing_duration_ms', 0))
            
        except Exception as e:
            error_msg = f"Azure OCR processing failed: {str(e)}"
            logger.error("Azure OCR processing failed",
                                  document_id=document_id,
                                  error=str(e))
            
            # Update status to error
            run_async(database_service.update_document(
                document_uuid,
                DocumentUpdate(ocr_status=OcrStatus.ERROR)
            ))
            
            raise OCRProcessingError(error_msg, document_uuid)
        
        # Step 5: Perform NMTC document type detection
        try:
            full_text = analysis_result.get("full_text", "")
            
            logger.info("Starting document type detection",
                                 document_id=document_id,
                                 text_length=len(full_text))
            
            # Detect document type using NMTC patterns
            detection_result = detection_service.detect_document_type(
                text_content=full_text,
                document_id=document_uuid,
                filename=document.filename
            )
            
            logger.info("Document type detection completed",
                                 document_id=document_id,
                                 detected_type=detection_result.document_type.value,
                                 confidence=detection_result.confidence,
                                 primary_indicators=len(detection_result.primary_indicators),
                                 secondary_indicators=len(detection_result.secondary_indicators))
            
        except Exception as e:
            # Don't fail the entire task if detection fails
            logger.warning("Document type detection failed, continuing with OCR results",
                                    document_id=document_id,
                                    error=str(e))
            
            # Create a fallback detection result
            from app.utils.nmtc_patterns import NMTCDocumentType, DocumentTypeResult
            detection_result = DocumentTypeResult(
                document_type=NMTCDocumentType.UNKNOWN,
                confidence=0.0,
                primary_indicators=[],
                secondary_indicators=[],
                metadata={
                    "detection_timestamp": datetime.utcnow().isoformat(),
                    "detection_failed": True,
                    "failure_reason": str(e)
                },
                reasoning=f"Document type detection failed: {str(e)}"
            )
        
        # Step 6: Process and structure results
        try:
            # Extract metadata for database storage
            metadata = azure_service.extract_document_metadata(analysis_result)
            
            # Prepare parsed_index with structured results
            parsed_index = {
                "ocr_results": {
                    "full_text": analysis_result.get("full_text", ""),
                    "page_count": analysis_result.get("page_count", 0),
                    "confidence_scores": analysis_result.get("confidence_scores", []),
                    "overall_confidence": analysis_result.get("overall_confidence"),
                    "processing_metadata": metadata
                },
                "detection_results": {
                    "document_type_detected": detection_result.document_type.value,
                    "confidence": detection_result.confidence,
                    "primary_indicators": [
                        {
                            "pattern_type": indicator.pattern_type,
                            "match_text": indicator.match_text,
                            "confidence": indicator.confidence,
                            "location": indicator.location,
                            "context": indicator.context
                        }
                        for indicator in detection_result.primary_indicators
                    ],
                    "secondary_indicators": [
                        {
                            "pattern_type": indicator.pattern_type,
                            "match_text": indicator.match_text,
                            "confidence": indicator.confidence,
                            "location": indicator.location,
                            "context": indicator.context
                        }
                        for indicator in detection_result.secondary_indicators
                    ],
                    "metadata": detection_result.metadata,
                    "reasoning": detection_result.reasoning,
                    "processed_at": datetime.utcnow().isoformat()
                },
                "processing_history": [
                    {
                        "stage": "quick_detection",
                        "status": "completed",
                        "processed_at": datetime.utcnow().isoformat(),
                        "processing_duration_ms": analysis_result.get("processing_duration_ms", 0),
                        "task_id": self.request.id,
                        "user_id": user_id
                    }
                ]
            }
            
            # Step 7: Update database with results
            run_async(database_service.update_document(
                document_uuid,
                DocumentUpdate(
                    ocr_status=OcrStatus.COMPLETED,
                    parsed_index=parsed_index
                )
            ))
            
            logger.info("Document processing completed successfully",
                                 document_id=document_id,
                                 final_status=OcrStatus.COMPLETED.value,
                                 text_length=len(analysis_result.get("full_text", "")),
                                 ocr_confidence=analysis_result.get("overall_confidence"),
                                 detected_type=detection_result.document_type.value,
                                 detection_confidence=detection_result.confidence)
            
            # Step 8: Create audit log entry
            try:
                run_async(database_service.create_audit_log(
                    scope="document_processing",
                    action="quick_detection_completed",
                    org_id=document.org_id,
                    actor_user_id=user_uuid,
                    record_id=document_uuid,
                    diff={
                        "old_status": "processing",
                        "new_status": "completed",
                        "pages_processed": analysis_result.get("page_count", 0),
                        "characters_extracted": len(analysis_result.get("full_text", "")),
                        "document_type_detected": detection_result.document_type.value,
                        "detection_confidence": detection_result.confidence,
                        "primary_indicators_count": len(detection_result.primary_indicators)
                    }
                ))
            except Exception as audit_error:
                # Don't fail the task if audit logging fails
                logger.warning("Failed to create audit log",
                                        document_id=document_id,
                                        error=str(audit_error))
            
            # Return success result
            return {
                "document_id": document_id,
                "status": "completed",
                "pages_processed": analysis_result.get("page_count", 0),
                "characters_extracted": len(analysis_result.get("full_text", "")),
                "ocr_confidence": analysis_result.get("overall_confidence"),
                "processing_duration_ms": analysis_result.get("processing_duration_ms", 0),
                "document_type_detected": detection_result.document_type.value,
                "detection_confidence": detection_result.confidence,
                "primary_indicators_found": len(detection_result.primary_indicators),
                "secondary_indicators_found": len(detection_result.secondary_indicators),
                "task_id": self.request.id,
                "completed_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            error_msg = f"Failed to update database with results: {str(e)}"
            logger.error("Database update failed",
                                  document_id=document_id,
                                  error=str(e))
            
            # Try to update status to error
            try:
                run_async(database_service.update_document(
                    document_uuid,
                    DocumentUpdate(ocr_status=OcrStatus.ERROR)
                ))
            except Exception as db_error:
                logger.error("Failed to update error status",
                                      document_id=document_id,
                                      error=str(db_error))
            
            raise DatabaseError(error_msg, "update_document_results")
        
    except Exception as exc:
        # Log the error and attempt retry
        logger.error("Document processing task failed",
                              document_id=document_id,
                              task_id=self.request.id,
                              error=str(exc),
                              retries=self.request.retries)
        
        # Retry logic
        if self.request.retries < self.max_retries:
            retry_delay = min(300 * (2 ** self.request.retries), 1800)  # Exponential backoff, max 30 min
            logger.info("Retrying document processing task",
                                 document_id=document_id,
                                 retry_count=self.request.retries + 1,
                                 retry_delay=retry_delay)
            raise self.retry(countdown=retry_delay, exc=exc)
        else:
            # Max retries reached, mark as failed
            try:
                run_async(database_service.update_document(
                    document_uuid,
                    DocumentUpdate(ocr_status=OcrStatus.ERROR)
                ))
                
                # Create audit log for failure
                run_async(database_service.create_audit_log(
                    scope="document_processing",
                    action="quick_detection_failed",
                    org_id=document.org_id if document else None,
                    actor_user_id=user_uuid,
                    record_id=document_uuid,
                    diff={
                        "error": str(exc),
                        "retries": self.request.retries,
                        "task_id": self.request.id
                    }
                ))
            except Exception as cleanup_error:
                logger.error("Failed to clean up after task failure",
                                      document_id=document_id,
                                      error=str(cleanup_error))
            
            # Re-raise the original exception
            raise


@celery_app.task(bind=True, max_retries=2, default_retry_delay=60)
def process_document_type_detection(self, document_id: str, user_id: str = None):
    """
    Celery task for standalone document type detection
    
    Args:
        document_id: UUID string of the document to process
        user_id: UUID string of the user who initiated the processing
        
    Returns:
        Dict containing detection results
    """
    document_uuid = uuid.UUID(document_id)
    user_uuid = uuid.UUID(user_id) if user_id else None
    
    logger.info("Starting standalone document type detection task",
                         document_id=document_id,
                         user_id=user_id,
                         task_id=self.request.id)
    
    try:
        # Get document from database
        document = run_async(database_service.get_document(document_uuid))
        if not document:
            raise DocumentProcessingError(f"Document {document_id} not found", 
                                        document_uuid, "document_lookup")
        
        # Check if document has OCR text available
        if not document.parsed_index or "ocr_results" not in document.parsed_index:
            raise DocumentProcessingError("Document must have OCR results before type detection",
                                        document_uuid, "prerequisite_check")
        
        full_text = document.parsed_index["ocr_results"].get("full_text", "")
        if not full_text or len(full_text.strip()) < 50:
            raise DocumentProcessingError("Document has insufficient OCR text for type detection",
                                        document_uuid, "insufficient_text")
        
        # Perform document type detection
        detection_result = detection_service.detect_document_type(
            text_content=full_text,
            document_id=document_uuid,
            filename=document.filename
        )
        
        # Update the detection results in parsed_index
        current_parsed_index = document.parsed_index.copy()
        current_parsed_index["detection_results"] = {
            "document_type_detected": detection_result.document_type.value,
            "confidence": detection_result.confidence,
            "primary_indicators": [
                {
                    "pattern_type": indicator.pattern_type,
                    "match_text": indicator.match_text,
                    "confidence": indicator.confidence,
                    "location": indicator.location,
                    "context": indicator.context
                }
                for indicator in detection_result.primary_indicators
            ],
            "secondary_indicators": [
                {
                    "pattern_type": indicator.pattern_type,
                    "match_text": indicator.match_text,
                    "confidence": indicator.confidence,
                    "location": indicator.location,
                    "context": indicator.context
                }
                for indicator in detection_result.secondary_indicators
            ],
            "metadata": detection_result.metadata,
            "reasoning": detection_result.reasoning,
            "processed_at": datetime.utcnow().isoformat()
        }
        
        # Update processing history
        if "processing_history" not in current_parsed_index:
            current_parsed_index["processing_history"] = []
        
        current_parsed_index["processing_history"].append({
            "stage": "type_detection",
            "status": "completed",
            "processed_at": datetime.utcnow().isoformat(),
            "task_id": self.request.id,
            "user_id": user_id
        })
        
        # Update database
        run_async(database_service.update_document(
            document_uuid,
            DocumentUpdate(parsed_index=current_parsed_index)
        ))
        
        logger.info("Standalone document type detection completed",
                             document_id=document_id,
                             detected_type=detection_result.document_type.value,
                             confidence=detection_result.confidence,
                             primary_indicators=len(detection_result.primary_indicators),
                             secondary_indicators=len(detection_result.secondary_indicators))
        
        # Create audit log entry
        try:
            run_async(database_service.create_audit_log(
                scope="document_processing",
                action="type_detection_completed",
                org_id=document.org_id,
                actor_user_id=user_uuid,
                record_id=document_uuid,
                diff={
                    "document_type_detected": detection_result.document_type.value,
                    "detection_confidence": detection_result.confidence,
                    "primary_indicators_count": len(detection_result.primary_indicators),
                    "secondary_indicators_count": len(detection_result.secondary_indicators)
                }
            ))
        except Exception as audit_error:
            logger.warning("Failed to create audit log for type detection",
                                    document_id=document_id,
                                    error=str(audit_error))
        
        return {
            "document_id": document_id,
            "status": "completed",
            "document_type_detected": detection_result.document_type.value,
            "detection_confidence": detection_result.confidence,
            "primary_indicators_found": len(detection_result.primary_indicators),
            "secondary_indicators_found": len(detection_result.secondary_indicators),
            "reasoning": detection_result.reasoning,
            "task_id": self.request.id,
            "completed_at": datetime.utcnow().isoformat()
        }
        
    except Exception as exc:
        logger.error("Document type detection task failed",
                              document_id=document_id,
                              task_id=self.request.id,
                              error=str(exc),
                              retries=self.request.retries)
        
        # Retry logic for transient failures
        if self.request.retries < self.max_retries:
            retry_delay = 60 * (self.request.retries + 1)
            logger.info("Retrying document type detection task",
                                 document_id=document_id,
                                 retry_count=self.request.retries + 1,
                                 retry_delay=retry_delay)
            raise self.retry(countdown=retry_delay, exc=exc)
        else:
            # Max retries reached
            logger.error("Document type detection task failed permanently",
                                  document_id=document_id,
                                  task_id=self.request.id,
                                  error=str(exc))
            raise


@celery_app.task(bind=True)
def process_document_layout_analysis(self, document_id: str, user_id: str = None):
    """
    Celery task for detailed document layout analysis
    
    Args:
        document_id: UUID string of the document to process
        user_id: UUID string of the user who initiated the processing
        
    Returns:
        Dict containing layout analysis results
    """
    document_uuid = uuid.UUID(document_id)
    user_uuid = uuid.UUID(user_id) if user_id else None
    
    logger.info("Starting document layout analysis task",
                         document_id=document_id,
                         user_id=user_id,
                         task_id=self.request.id)
    
    try:
        # Get document from database
        document = run_async(database_service.get_document(document_uuid))
        if not document:
            raise DocumentProcessingError(f"Document {document_id} not found", 
                                        document_uuid, "document_lookup")
        
        # Ensure document has been through quick detection first
        if document.ocr_status not in [OcrStatus.COMPLETED, OcrStatus.DONE]:
            raise DocumentProcessingError("Document must complete quick detection first",
                                        document_uuid, "prerequisite_check")
        
        # Download document content (simplified for now)
        file_url = database_service.get_file_url(document.storage_path)
        document_content = b"PDF content placeholder"  # TODO: Actual download
        
        # Perform layout analysis
        analysis_result = run_async(azure_service.analyze_document_layout(
            document_content=document_content,
            document_id=document_uuid,
            content_type=document.mime_type
        ))
        
        # Update parsed_index with layout results
        current_parsed_index = document.parsed_index or {}
        current_parsed_index["layout_analysis"] = {
            "tables": analysis_result.get("tables", []),
            "paragraphs": analysis_result.get("paragraphs", []),
            "key_value_pairs": analysis_result.get("key_value_pairs", []),
            "processed_at": datetime.utcnow().isoformat(),
            "processing_metadata": azure_service.extract_document_metadata(analysis_result)
        }
        
        # Update processing history
        if "processing_history" not in current_parsed_index:
            current_parsed_index["processing_history"] = []
        
        current_parsed_index["processing_history"].append({
            "stage": "layout_analysis",
            "status": "completed",
            "processed_at": datetime.utcnow().isoformat(),
            "processing_duration_ms": analysis_result.get("processing_duration_ms", 0),
            "task_id": self.request.id,
            "user_id": user_id
        })
        
        # Update database
        run_async(database_service.update_document(
            document_uuid,
            DocumentUpdate(parsed_index=current_parsed_index)
        ))
        
        logger.info("Document layout analysis completed",
                             document_id=document_id,
                             tables_found=len(analysis_result.get("tables", [])),
                             paragraphs_found=len(analysis_result.get("paragraphs", [])))
        
        return {
            "document_id": document_id,
            "status": "completed",
            "tables_found": len(analysis_result.get("tables", [])),
            "paragraphs_found": len(analysis_result.get("paragraphs", [])),
            "key_value_pairs_found": len(analysis_result.get("key_value_pairs", [])),
            "task_id": self.request.id,
            "completed_at": datetime.utcnow().isoformat()
        }
        
    except Exception as exc:
        logger.error("Layout analysis task failed",
                              document_id=document_id,
                              error=str(exc))
        raise


@celery_app.task
def cleanup_failed_documents():
    """
    Periodic task to clean up documents that have been stuck in processing state
    """
    logger.info("Starting cleanup of failed documents")
    
    try:
        # This would query for documents stuck in processing state for too long
        # and reset their status or mark them as failed
        
        # TODO: Implement actual cleanup logic
        # Example:
        # - Find documents in "processing" state older than 1 hour
        # - Update their status to "error"
        # - Create audit log entries
        
        logger.info("Completed cleanup of failed documents")
        return {"status": "completed", "documents_cleaned": 0}
        
    except Exception as e:
        logger.error("Failed to clean up documents", error=str(e))
        raise


@celery_app.task
def get_document_processing_status(document_id: str):
    """
    Get the current processing status of a document
    
    Args:
        document_id: UUID string of the document
        
    Returns:
        Dict containing current status information
    """
    try:
        document_uuid = uuid.UUID(document_id)
        document = run_async(database_service.get_document(document_uuid))
        
        if not document:
            return {
                "document_id": document_id,
                "status": "not_found",
                "error": "Document not found"
            }
        
        # Extract processing history if available
        processing_history = []
        if document.parsed_index and "processing_history" in document.parsed_index:
            processing_history = document.parsed_index["processing_history"]
        
        # Extract detection information if available
        detection_info = {}
        if document.parsed_index and "detection_results" in document.parsed_index:
            detection_results = document.parsed_index["detection_results"]
            detection_info = {
                "document_type_detected": detection_results.get("document_type_detected"),
                "detection_confidence": detection_results.get("confidence"),
                "primary_indicators_count": len(detection_results.get("primary_indicators", [])),
                "secondary_indicators_count": len(detection_results.get("secondary_indicators", [])),
                "detection_reasoning": detection_results.get("reasoning"),
                "detection_processed_at": detection_results.get("processed_at")
            }
        
        return {
            "document_id": document_id,
            "status": document.ocr_status.value,
            "filename": document.filename,
            "uploaded_at": document.uploaded_at.isoformat(),
            "processing_history": processing_history,
            "has_ocr_results": bool(document.parsed_index and "ocr_results" in document.parsed_index),
            "has_layout_analysis": bool(document.parsed_index and "layout_analysis" in document.parsed_index),
            "has_type_detection": bool(document.parsed_index and "detection_results" in document.parsed_index),
            "detection_info": detection_info
        }
        
    except Exception as e:
        logger.error("Failed to get document status",
                              document_id=document_id,
                              error=str(e))
        return {
            "document_id": document_id,
            "status": "error",
            "error": str(e)
        }


# Configure periodic tasks
celery_app.conf.beat_schedule = {
    'cleanup-failed-documents': {
        'task': 'app.tasks.document_tasks.cleanup_failed_documents',
        'schedule': 3600.0,  # Every hour
    },
}


if __name__ == "__main__":
    # For testing the tasks locally
    celery_app.start()
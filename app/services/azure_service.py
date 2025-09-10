from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest, ContentFormat
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import AzureError, HttpResponseError
from app.config import settings
from app.utils.exceptions import ExternalServiceError, ConfigurationError
from typing import Dict, Any, List, Optional, Union
import logging
import uuid
from datetime import datetime
import io
import time
import base64

logger = logging.getLogger(__name__)


class AzureDocumentIntelligenceError(ExternalServiceError):
    """Azure Document Intelligence specific error"""
    def __init__(self, detail: str, operation: Optional[str] = None, status_code: int = 502):
        super().__init__("Azure Document Intelligence", detail, status_code)
        if operation:
            self.context["operation"] = operation


class AzureDocumentIntelligenceService:
    """Azure Document Intelligence service for OCR and document analysis"""
    
    def __init__(self):
        """Initialize Azure Document Intelligence client"""
        try:
            # Check for required configuration
            if not hasattr(settings, 'AZURE_DOC_INTELLIGENCE_ENDPOINT'):
                raise ConfigurationError("AZURE_DOC_INTELLIGENCE_ENDPOINT not configured")
            if not hasattr(settings, 'AZURE_DOC_INTELLIGENCE_KEY'):
                raise ConfigurationError("AZURE_DOC_INTELLIGENCE_KEY not configured")
            
            self.endpoint = settings.AZURE_DOC_INTELLIGENCE_ENDPOINT
            self.key = settings.AZURE_DOC_INTELLIGENCE_KEY
            
            # Initialize the client
            self.client = DocumentIntelligenceClient(
                endpoint=self.endpoint,
                credential=AzureKeyCredential(self.key)
            )
            
            logger.info(f"Azure Document Intelligence service initialized at {self.endpoint}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Azure Document Intelligence service: {e}")
            raise ConfigurationError(f"Failed to initialize Azure Document Intelligence: {e}")
    
    def _handle_azure_error(self, error: Exception, operation: str) -> None:
        """Handle Azure-specific errors with proper logging"""
        if isinstance(error, HttpResponseError):
            status_code = error.status_code
            error_msg = f"Azure API error (HTTP {status_code}): {error.message}"
            logger.error(f"Azure Document Intelligence API error - operation: {operation}, status: {status_code}, message: {error.message}")
            raise AzureDocumentIntelligenceError(error_msg, operation, status_code)
        elif isinstance(error, AzureError):
            error_msg = f"Azure service error: {str(error)}"
            logger.error(f"Azure Document Intelligence service error - operation: {operation}, error: {str(error)}")
            raise AzureDocumentIntelligenceError(error_msg, operation)
        else:
            error_msg = f"Unexpected error during {operation}: {str(error)}"
            logger.error(f"Unexpected Azure Document Intelligence error - operation: {operation}, error: {str(error)}")
            raise AzureDocumentIntelligenceError(error_msg, operation)
    
    async def analyze_document_quick(
        self,
        document_content: bytes,
        document_id: uuid.UUID,
        content_type: str = "application/pdf"
    ) -> Dict[str, Any]:
        """
        Perform quick document analysis for text extraction and basic classification
        
        Args:
            document_content: Raw document bytes
            document_id: Document UUID for tracking
            content_type: MIME type of the document
            
        Returns:
            Dictionary containing extracted text and metadata
        """
        start_time = time.time()
        operation = "analyze_document_quick"
        
        try:
            logger.info(f"Starting quick document analysis for document {document_id}, content_type: {content_type}, size: {len(document_content)} bytes")
            
            # Create analyze request with base64 encoded content
            base64_content = base64.b64encode(document_content).decode('utf-8')
            analyze_request = AnalyzeDocumentRequest(base64_source=base64_content)
            
            # Use prebuilt-read model for quick text extraction
            poller = self.client.begin_analyze_document(
                model_id="prebuilt-read",
                analyze_request=analyze_request,
                output_content_format=ContentFormat.TEXT
            )
            
            # Wait for completion
            result = poller.result()
            
            duration_ms = (time.time() - start_time) * 1000
            
            # Extract and structure the results
            analysis_result = self._process_read_result(result, document_id, duration_ms)
            
            logger.info(f"Quick document analysis completed for document {document_id}, duration: {duration_ms}ms, pages: {analysis_result.get('page_count', 0)}, chars: {len(analysis_result.get('full_text', ''))}")
            
            return analysis_result
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(f"Quick document analysis failed for document {document_id}, duration: {duration_ms}ms, error: {str(e)}")
            self._handle_azure_error(e, operation)
    
    async def analyze_document_layout(
        self,
        document_content: bytes,
        document_id: uuid.UUID,
        content_type: str = "application/pdf"
    ) -> Dict[str, Any]:
        """
        Perform detailed document layout analysis
        
        Args:
            document_content: Raw document bytes
            document_id: Document UUID for tracking
            content_type: MIME type of the document
            
        Returns:
            Dictionary containing layout analysis results
        """
        start_time = time.time()
        operation = "analyze_document_layout"
        
        try:
            logger.info("Starting document layout analysis",
                                 document_id=str(document_id),
                                 content_type=content_type)
            
            # Create analyze request
            analyze_request = AnalyzeDocumentRequest(bytes_source=document_content)
            
            # Use prebuilt-layout model for detailed analysis
            poller = self.client.begin_analyze_document(
                model_id="prebuilt-layout",
                analyze_request=analyze_request,
                output_content_format=ContentFormat.TEXT
            )
            
            # Wait for completion
            result = poller.result()
            
            duration_ms = (time.time() - start_time) * 1000
            
            # Process layout results
            analysis_result = self._process_layout_result(result, document_id, duration_ms)
            
            logger.info("Document layout analysis completed",
                                 document_id=str(document_id),
                                 duration_ms=duration_ms,
                                 tables_found=len(analysis_result.get('tables', [])),
                                 paragraphs_found=len(analysis_result.get('paragraphs', [])))
            
            return analysis_result
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error("Document layout analysis failed",
                                  document_id=str(document_id),
                                  duration_ms=duration_ms,
                                  error=str(e))
            self._handle_azure_error(e, operation)
    
    def _process_read_result(self, result, document_id: uuid.UUID, duration_ms: float) -> Dict[str, Any]:
        """Process Azure Document Intelligence read results"""
        try:
            # Extract basic document information
            analysis_result = {
                "document_id": str(document_id),
                "analysis_type": "quick_read",
                "processed_at": datetime.utcnow().isoformat(),
                "processing_duration_ms": duration_ms,
                "api_version": getattr(result, 'api_version', 'unknown'),
                "model_id": getattr(result, 'model_id', 'prebuilt-read'),
                "full_text": "",
                "pages": [],
                "page_count": 0,
                "confidence_scores": []
            }
            
            if hasattr(result, 'content') and result.content:
                analysis_result["full_text"] = result.content
            
            if hasattr(result, 'pages') and result.pages:
                analysis_result["page_count"] = len(result.pages)
                
                for page_idx, page in enumerate(result.pages):
                    page_info = {
                        "page_number": page_idx + 1,
                        "width": getattr(page, 'width', 0),
                        "height": getattr(page, 'height', 0),
                        "unit": getattr(page, 'unit', 'pixel'),
                        "lines_count": len(getattr(page, 'lines', [])),
                        "words_count": len(getattr(page, 'words', []))
                    }
                    
                    # Extract confidence scores if available
                    if hasattr(page, 'words'):
                        confidences = []
                        for word in page.words:
                            if hasattr(word, 'confidence') and word.confidence is not None:
                                confidences.append(word.confidence)
                        
                        if confidences:
                            page_info["average_confidence"] = sum(confidences) / len(confidences)
                            page_info["min_confidence"] = min(confidences)
                            analysis_result["confidence_scores"].extend(confidences)
                    
                    analysis_result["pages"].append(page_info)
            
            # Calculate overall confidence
            if analysis_result["confidence_scores"]:
                analysis_result["overall_confidence"] = sum(analysis_result["confidence_scores"]) / len(analysis_result["confidence_scores"])
                analysis_result["min_confidence"] = min(analysis_result["confidence_scores"])
                analysis_result["max_confidence"] = max(analysis_result["confidence_scores"])
            
            return analysis_result
            
        except Exception as e:
            logger.error("Error processing read results",
                                  document_id=str(document_id),
                                  error=str(e))
            # Return minimal result on processing error
            return {
                "document_id": str(document_id),
                "analysis_type": "quick_read",
                "processed_at": datetime.utcnow().isoformat(),
                "processing_duration_ms": duration_ms,
                "error": f"Result processing failed: {str(e)}",
                "full_text": "",
                "pages": [],
                "page_count": 0
            }
    
    def _process_layout_result(self, result, document_id: uuid.UUID, duration_ms: float) -> Dict[str, Any]:
        """Process Azure Document Intelligence layout results"""
        try:
            analysis_result = {
                "document_id": str(document_id),
                "analysis_type": "layout",
                "processed_at": datetime.utcnow().isoformat(),
                "processing_duration_ms": duration_ms,
                "api_version": getattr(result, 'api_version', 'unknown'),
                "model_id": getattr(result, 'model_id', 'prebuilt-layout'),
                "full_text": "",
                "pages": [],
                "tables": [],
                "paragraphs": [],
                "key_value_pairs": []
            }
            
            # Extract content
            if hasattr(result, 'content'):
                analysis_result["full_text"] = result.content
            
            # Process pages
            if hasattr(result, 'pages') and result.pages:
                for page_idx, page in enumerate(result.pages):
                    page_info = {
                        "page_number": page_idx + 1,
                        "width": getattr(page, 'width', 0),
                        "height": getattr(page, 'height', 0),
                        "unit": getattr(page, 'unit', 'pixel')
                    }
                    analysis_result["pages"].append(page_info)
            
            # Process tables
            if hasattr(result, 'tables') and result.tables:
                for table_idx, table in enumerate(result.tables):
                    table_info = {
                        "table_id": table_idx,
                        "row_count": getattr(table, 'row_count', 0),
                        "column_count": getattr(table, 'column_count', 0),
                        "cells": []
                    }
                    
                    if hasattr(table, 'cells'):
                        for cell in table.cells:
                            cell_info = {
                                "content": getattr(cell, 'content', ''),
                                "row_index": getattr(cell, 'row_index', 0),
                                "column_index": getattr(cell, 'column_index', 0),
                                "kind": getattr(cell, 'kind', 'content')
                            }
                            table_info["cells"].append(cell_info)
                    
                    analysis_result["tables"].append(table_info)
            
            # Process paragraphs
            if hasattr(result, 'paragraphs') and result.paragraphs:
                for para_idx, paragraph in enumerate(result.paragraphs):
                    para_info = {
                        "paragraph_id": para_idx,
                        "content": getattr(paragraph, 'content', ''),
                        "role": getattr(paragraph, 'role', 'paragraph')
                    }
                    analysis_result["paragraphs"].append(para_info)
            
            # Process key-value pairs
            if hasattr(result, 'key_value_pairs') and result.key_value_pairs:
                for kv_idx, kv_pair in enumerate(result.key_value_pairs):
                    kv_info = {
                        "key": getattr(kv_pair.key, 'content', '') if kv_pair.key else '',
                        "value": getattr(kv_pair.value, 'content', '') if kv_pair.value else '',
                        "confidence": getattr(kv_pair, 'confidence', 0.0)
                    }
                    analysis_result["key_value_pairs"].append(kv_info)
            
            return analysis_result
            
        except Exception as e:
            logger.error("Error processing layout results",
                                  document_id=str(document_id),
                                  error=str(e))
            # Return minimal result on processing error
            return {
                "document_id": str(document_id),
                "analysis_type": "layout",
                "processed_at": datetime.utcnow().isoformat(),
                "processing_duration_ms": duration_ms,
                "error": f"Result processing failed: {str(e)}",
                "full_text": "",
                "pages": [],
                "tables": [],
                "paragraphs": []
            }
    
    async def get_operation_status(self, operation_id: str) -> Dict[str, Any]:
        """Get status of a long-running operation"""
        try:
            # This would be used for checking operation status
            # Azure Document Intelligence handles this internally with pollers
            return {
                "operation_id": operation_id,
                "status": "completed",  # Placeholder
                "message": "Operation status check not implemented for current SDK version"
            }
        except Exception as e:
            self._handle_azure_error(e, "get_operation_status")
    
    def validate_document(self, document_content: bytes) -> bool:
        """Validate document before processing"""
        try:
            # Basic validation
            if not document_content:
                return False
            
            # Check file size (Azure has limits)
            max_size = 50 * 1024 * 1024  # 50MB limit
            if len(document_content) > max_size:
                logger.warning(f"Document exceeds size limit - size: {len(document_content)}, max: {max_size}")
                return False
            
            # Additional validation could be added here
            return True
            
        except Exception as e:
            logger.error(f"Document validation failed: {e}")
            return False
    
    def extract_document_metadata(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Extract metadata from analysis results for database storage"""
        try:
            metadata = {
                "analysis_type": result.get("analysis_type", "unknown"),
                "processed_at": result.get("processed_at"),
                "processing_duration_ms": result.get("processing_duration_ms", 0),
                "page_count": result.get("page_count", 0),
                "character_count": len(result.get("full_text", "")),
                "overall_confidence": result.get("overall_confidence"),
                "has_tables": len(result.get("tables", [])) > 0,
                "table_count": len(result.get("tables", [])),
                "paragraph_count": len(result.get("paragraphs", [])),
                "api_version": result.get("api_version"),
                "model_id": result.get("model_id")
            }
            
            # Add error information if present
            if "error" in result:
                metadata["processing_error"] = result["error"]
            
            return metadata
            
        except Exception as e:
            logger.error(f"Error extracting document metadata: {e}")
            return {"error": f"Metadata extraction failed: {str(e)}"}


# Global service instance
azure_service = AzureDocumentIntelligenceService()
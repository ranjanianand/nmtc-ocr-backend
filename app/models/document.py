from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum

class DocumentStatus(str, Enum):
    UPLOADED = "uploaded"
    QUICK_SCAN_COMPLETE = "quick_scan_complete"
    VALIDATED_BY_USER = "validated_by_user"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"

class DocumentType(str, Enum):
    ALLOCATION_AGREEMENT = "allocation_agreement"
    QLICI_LOAN = "qlici_loan"
    CBA = "cba"
    FINANCIAL_STATEMENT = "financial_statement"
    INSURANCE = "insurance"

class DocumentUploadRequest(BaseModel):
    document_type: Optional[DocumentType] = None
    cde_name: Optional[str] = None
    client_info: Optional[str] = None
    analysis_scope: str = "full"
    priority: str = "normal"

class DocumentUploadResponse(BaseModel):
    document_id: str
    status: DocumentStatus
    message: str
    file_path: str

class QuickDetectionResult(BaseModel):
    document_id: str
    detected_type: DocumentType
    confidence: int
    extracted_metadata: Dict[str, Any]
    status: DocumentStatus

class DocumentValidationRequest(BaseModel):
    document_id: str
    confirmed_type: DocumentType
    user_corrections: Optional[Dict[str, Any]] = None
    proceed_with_processing: bool = True
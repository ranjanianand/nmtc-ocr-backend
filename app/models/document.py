from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

class DocumentStatus(str, Enum):
    UPLOADED = "uploaded"
    DETECTING = "detecting"
    DETECTION_COMPLETE = "detection_complete"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"

class DocumentType(str, Enum):
    ALLOCATION_AGREEMENT = "allocation_agreement"
    QLICI_LOAN = "qlici_loan"
    QALICB_CERTIFICATION = "qalicb_certification"
    CBA = "cba"
    ANNUAL_COMPLIANCE_REPORT = "annual_compliance_report"
    FINANCIAL_STATEMENT = "financial_statement"
    PROMISSORY_NOTE = "promissory_note"
    INSURANCE = "insurance"
    UNKNOWN = "unknown"

class ConfidenceLevel(str, Enum):
    HIGH = "high"      # ≥90% - auto-proceed
    MEDIUM = "medium"  # 70-89% - show confirmation
    LOW = "low"        # <70% - manual selection

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

class PatternIndicator(BaseModel):
    pattern_type: str
    match_text: str
    confidence: float
    location: str
    context: str

class DetectionResult(BaseModel):
    document_id: str
    detected_type: DocumentType
    confidence: float
    confidence_level: ConfidenceLevel
    primary_indicators: List[PatternIndicator]
    secondary_indicators: List[PatternIndicator]
    reasoning: str
    requires_confirmation: bool
    auto_process_countdown: Optional[int] = None
    suggested_types: Optional[List[DocumentType]] = None

class DocumentDetectionResponse(BaseModel):
    document_id: str
    status: DocumentStatus
    detection_result: Optional[DetectionResult] = None
    message: str
    processing_time_ms: Optional[int] = None

class DocumentValidationRequest(BaseModel):
    document_id: str
    confirmed_type: DocumentType
    user_corrections: Optional[Dict[str, Any]] = None
    proceed_with_processing: bool = True
    user_notes: Optional[str] = None

class StartDetectionRequest(BaseModel):
    user_id: Optional[str] = None
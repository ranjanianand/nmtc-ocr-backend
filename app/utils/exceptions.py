"""
Custom exception classes for the NMTC platform
"""
from fastapi import HTTPException
from typing import Optional, Dict, Any
import uuid


class BaseNMTCException(HTTPException):
    """Base exception for NMTC platform"""
    
    def __init__(
        self, 
        status_code: int, 
        detail: str,
        error_code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(status_code=status_code, detail=detail)
        self.error_code = error_code or self.__class__.__name__
        self.context = context or {}


# Authentication and Authorization Exceptions
class AuthenticationError(BaseNMTCException):
    """Authentication failed"""
    def __init__(self, detail: str = "Authentication failed"):
        super().__init__(status_code=401, detail=detail, error_code="AUTH_FAILED")


class AuthorizationError(BaseNMTCException):
    """Authorization/permission denied"""
    def __init__(self, detail: str = "Permission denied"):
        super().__init__(status_code=403, detail=detail, error_code="AUTH_DENIED")


class InvalidTokenError(AuthenticationError):
    """Invalid or expired token"""
    def __init__(self, detail: str = "Invalid or expired token"):
        super().__init__(detail=detail)
        self.error_code = "INVALID_TOKEN"


class OrganizationAccessDeniedError(AuthorizationError):
    """User doesn't have access to organization"""
    def __init__(self, org_id: uuid.UUID):
        super().__init__(detail=f"Access denied to organization {org_id}")
        self.error_code = "ORG_ACCESS_DENIED"
        self.context = {"org_id": str(org_id)}


# Resource Not Found Exceptions
class ResourceNotFoundError(BaseNMTCException):
    """Generic resource not found"""
    def __init__(self, resource_type: str, resource_id: uuid.UUID):
        super().__init__(
            status_code=404,
            detail=f"{resource_type} not found",
            error_code="RESOURCE_NOT_FOUND",
            context={"resource_type": resource_type, "resource_id": str(resource_id)}
        )


class OrganizationNotFoundError(ResourceNotFoundError):
    """Organization not found"""
    def __init__(self, org_id: uuid.UUID):
        super().__init__("Organization", org_id)
        self.error_code = "ORG_NOT_FOUND"


class DocumentNotFoundError(ResourceNotFoundError):
    """Document not found"""
    def __init__(self, document_id: uuid.UUID):
        super().__init__("Document", document_id)
        self.error_code = "DOCUMENT_NOT_FOUND"


class ObligationNotFoundError(ResourceNotFoundError):
    """Obligation not found"""
    def __init__(self, obligation_id: uuid.UUID):
        super().__init__("Obligation", obligation_id)
        self.error_code = "OBLIGATION_NOT_FOUND"


# Validation Exceptions
class ValidationError(BaseNMTCException):
    """Data validation failed"""
    def __init__(self, detail: str, field: Optional[str] = None, value: Optional[Any] = None):
        super().__init__(
            status_code=422,
            detail=detail,
            error_code="VALIDATION_ERROR",
            context={"field": field, "value": str(value) if value is not None else None}
        )


class DuplicateResourceError(BaseNMTCException):
    """Resource already exists"""
    def __init__(self, resource_type: str, identifier: str):
        super().__init__(
            status_code=409,
            detail=f"{resource_type} already exists: {identifier}",
            error_code="DUPLICATE_RESOURCE",
            context={"resource_type": resource_type, "identifier": identifier}
        )


class InvalidFileTypeError(ValidationError):
    """Invalid file type uploaded"""
    def __init__(self, file_type: str, allowed_types: list):
        super().__init__(
            detail=f"Invalid file type: {file_type}. Allowed types: {', '.join(allowed_types)}",
            field="file_type", 
            value=file_type
        )
        self.error_code = "INVALID_FILE_TYPE"
        self.context["allowed_types"] = allowed_types


class FileTooLargeError(ValidationError):
    """File size exceeds limits"""
    def __init__(self, file_size: int, max_size: int):
        super().__init__(
            detail=f"File size {file_size} bytes exceeds maximum of {max_size} bytes",
            field="file_size",
            value=file_size
        )
        self.error_code = "FILE_TOO_LARGE"
        self.context["max_size"] = max_size


# Business Logic Exceptions
class BusinessRuleViolationError(BaseNMTCException):
    """Business rule validation failed"""
    def __init__(self, rule_name: str, detail: str):
        super().__init__(
            status_code=422,
            detail=f"Business rule violation ({rule_name}): {detail}",
            error_code="BUSINESS_RULE_VIOLATION",
            context={"rule_name": rule_name}
        )


class OrganizationLimitExceededError(BusinessRuleViolationError):
    """Organization has exceeded usage limits"""
    def __init__(self, limit_type: str, current: int, maximum: int):
        super().__init__(
            rule_name="usage_limits",
            detail=f"{limit_type} limit exceeded: {current}/{maximum}"
        )
        self.error_code = "USAGE_LIMIT_EXCEEDED"
        self.context.update({
            "limit_type": limit_type,
            "current": current,
            "maximum": maximum
        })


# Document Processing Exceptions
class DocumentProcessingError(BaseNMTCException):
    """Document processing failed"""
    def __init__(
        self, 
        detail: str, 
        document_id: Optional[uuid.UUID] = None,
        processing_stage: Optional[str] = None
    ):
        super().__init__(
            status_code=500,
            detail=detail,
            error_code="DOCUMENT_PROCESSING_ERROR",
            context={
                "document_id": str(document_id) if document_id else None,
                "processing_stage": processing_stage
            }
        )


class OCRProcessingError(DocumentProcessingError):
    """OCR processing failed"""
    def __init__(self, detail: str, document_id: uuid.UUID):
        super().__init__(
            detail=f"OCR processing failed: {detail}",
            document_id=document_id,
            processing_stage="ocr"
        )
        self.error_code = "OCR_ERROR"


class ExtractionError(DocumentProcessingError):
    """Data extraction failed"""
    def __init__(self, detail: str, document_id: uuid.UUID, query_id: Optional[uuid.UUID] = None):
        super().__init__(
            detail=f"Data extraction failed: {detail}",
            document_id=document_id,
            processing_stage="extraction"
        )
        self.error_code = "EXTRACTION_ERROR"
        if query_id:
            self.context["query_id"] = str(query_id)


# Database Exceptions
class DatabaseError(BaseNMTCException):
    """Database operation failed"""
    def __init__(
        self, 
        detail: str, 
        operation: Optional[str] = None,
        table: Optional[str] = None
    ):
        super().__init__(
            status_code=500,
            detail=f"Database error: {detail}",
            error_code="DATABASE_ERROR",
            context={"operation": operation, "table": table}
        )


class DatabaseConnectionError(DatabaseError):
    """Database connection failed"""
    def __init__(self, detail: str = "Database connection failed"):
        super().__init__(detail=detail)
        self.error_code = "DATABASE_CONNECTION_ERROR"


class DatabaseTimeoutError(DatabaseError):
    """Database operation timed out"""
    def __init__(self, operation: str, timeout: float):
        super().__init__(
            detail=f"Database operation timed out after {timeout}s",
            operation=operation
        )
        self.error_code = "DATABASE_TIMEOUT"
        self.context["timeout"] = timeout


# External Service Exceptions
class ExternalServiceError(BaseNMTCException):
    """External service integration failed"""
    def __init__(self, service_name: str, detail: str, status_code: int = 502):
        super().__init__(
            status_code=status_code,
            detail=f"{service_name} error: {detail}",
            error_code="EXTERNAL_SERVICE_ERROR",
            context={"service_name": service_name}
        )


class SupabaseError(ExternalServiceError):
    """Supabase service error"""
    def __init__(self, detail: str, operation: Optional[str] = None):
        super().__init__("Supabase", detail)
        self.error_code = "SUPABASE_ERROR"
        if operation:
            self.context["operation"] = operation


class StorageError(ExternalServiceError):
    """File storage error"""
    def __init__(self, detail: str, file_path: Optional[str] = None):
        super().__init__("Storage", detail)
        self.error_code = "STORAGE_ERROR"
        if file_path:
            self.context["file_path"] = file_path


# System Configuration Exceptions
class ConfigurationError(BaseNMTCException):
    """System configuration error"""
    def __init__(self, detail: str, config_key: Optional[str] = None):
        super().__init__(
            status_code=500,
            detail=f"Configuration error: {detail}",
            error_code="CONFIGURATION_ERROR",
            context={"config_key": config_key}
        )


class FeatureNotAvailableError(BaseNMTCException):
    """Feature not available for organization"""
    def __init__(self, feature: str, plan_required: Optional[str] = None):
        detail = f"Feature '{feature}' not available"
        if plan_required:
            detail += f". {plan_required} plan required."
        
        super().__init__(
            status_code=402,  # Payment Required
            detail=detail,
            error_code="FEATURE_NOT_AVAILABLE",
            context={"feature": feature, "plan_required": plan_required}
        )


class MaintenanceModeError(BaseNMTCException):
    """System is in maintenance mode"""
    def __init__(self, detail: str = "System is temporarily unavailable for maintenance"):
        super().__init__(
            status_code=503,
            detail=detail,
            error_code="MAINTENANCE_MODE"
        )


class RateLimitExceededError(BaseNMTCException):
    """Rate limit exceeded"""
    def __init__(self, limit: int, window: str, retry_after: Optional[int] = None):
        super().__init__(
            status_code=429,
            detail=f"Rate limit exceeded: {limit} requests per {window}",
            error_code="RATE_LIMIT_EXCEEDED",
            context={"limit": limit, "window": window, "retry_after": retry_after}
        )


# Exception Helper Functions
def handle_database_exception(e: Exception, operation: str, table: Optional[str] = None) -> BaseNMTCException:
    """Convert database exceptions to appropriate NMTC exceptions"""
    error_msg = str(e).lower()
    
    if "connection" in error_msg or "network" in error_msg:
        return DatabaseConnectionError()
    elif "timeout" in error_msg:
        return DatabaseTimeoutError(operation, 30.0)
    elif "duplicate" in error_msg or "unique" in error_msg:
        return DuplicateResourceError("Record", "unknown")
    else:
        return DatabaseError(str(e), operation, table)


def handle_supabase_exception(e: Exception, operation: Optional[str] = None) -> SupabaseError:
    """Convert Supabase exceptions to NMTC exceptions"""
    return SupabaseError(str(e), operation)


def handle_validation_exception(e: Exception, field: Optional[str] = None) -> ValidationError:
    """Convert validation exceptions to NMTC exceptions"""
    return ValidationError(str(e), field)


def create_error_response(exception: BaseNMTCException) -> Dict[str, Any]:
    """Create standardized error response"""
    response = {
        "error": True,
        "error_code": exception.error_code,
        "message": exception.detail,
        "status_code": exception.status_code,
        "timestamp": datetime.now().isoformat()
    }
    
    if exception.context:
        response["context"] = exception.context
    
    return response


def log_exception(
    logger, 
    exception: BaseNMTCException, 
    user_id: Optional[uuid.UUID] = None,
    org_id: Optional[uuid.UUID] = None, 
    request_id: Optional[str] = None
):
    """Log exception with context"""
    log_data = {
        "error_code": exception.error_code,
        "message": exception.detail,
        "status_code": exception.status_code,
        "context": exception.context
    }
    
    if user_id:
        log_data["user_id"] = str(user_id)
    if org_id:
        log_data["org_id"] = str(org_id)
    if request_id:
        log_data["request_id"] = request_id
    
    if exception.status_code >= 500:
        logger.error(f"Server error: {log_data}")
    elif exception.status_code >= 400:
        logger.warning(f"Client error: {log_data}")
    else:
        logger.info(f"Exception: {log_data}")


# Context manager for error handling
class ErrorHandler:
    """Context manager for consistent error handling"""
    
    def __init__(self, logger, operation: str, user_id: Optional[uuid.UUID] = None, org_id: Optional[uuid.UUID] = None):
        self.logger = logger
        self.operation = operation
        self.user_id = user_id
        self.org_id = org_id
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type and issubclass(exc_type, BaseNMTCException):
            log_exception(self.logger, exc_val, self.user_id, self.org_id)
        elif exc_type:
            # Convert unexpected exceptions to DatabaseError
            db_error = DatabaseError(f"Unexpected error in {self.operation}: {str(exc_val)}")
            log_exception(self.logger, db_error, self.user_id, self.org_id)
        return False  # Don't suppress the exception
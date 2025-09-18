"""
NMTC Enterprise Error Handling and Retry Mechanisms

Comprehensive error handling system for long-running document processing with
intelligent retry strategies, circuit breaker patterns, and recovery mechanisms.

Author: CORE ENGINE PROCESSING AGENT
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Callable, Type
from enum import Enum
from dataclasses import dataclass, field
import traceback

from app.services.supabase_service import supabase_service
from app.services.progress_tracker import progress_tracker, ProgressEventType

logger = logging.getLogger(__name__)

class ErrorSeverity(str, Enum):
    """Error severity levels"""
    LOW = "low"          # Minor issues, auto-recoverable
    MEDIUM = "medium"    # Requires retry, may need intervention
    HIGH = "high"        # Serious issues, likely requires manual intervention
    CRITICAL = "critical" # System-level failures, immediate attention required

class ErrorCategory(str, Enum):
    """Categories of errors for handling strategies"""
    NETWORK = "network"              # Network connectivity issues
    STORAGE = "storage"              # File storage/retrieval issues
    OCR_PROCESSING = "ocr_processing"  # Azure OCR processing errors
    DETECTION = "detection"          # Document type detection errors
    AGENT_PROCESSING = "agent_processing"  # 3-Agent pipeline errors
    DATABASE = "database"            # Database operation errors
    AUTHENTICATION = "authentication"  # Auth/permission errors
    VALIDATION = "validation"        # Data validation errors
    TIMEOUT = "timeout"              # Processing timeout errors
    RESOURCE = "resource"            # Resource exhaustion errors
    UNKNOWN = "unknown"              # Unclassified errors

@dataclass
class ErrorContext:
    """Context information for error handling"""
    document_id: str
    session_id: str = ""
    user_id: str = ""
    processing_stage: str = ""
    attempt_number: int = 1
    max_attempts: int = 3
    error_timestamp: datetime = field(default_factory=datetime.utcnow)
    additional_context: Dict[str, Any] = field(default_factory=dict)

@dataclass
class RetryStrategy:
    """Configuration for retry behavior"""
    max_attempts: int = 3
    base_delay: float = 1.0  # seconds
    max_delay: float = 60.0  # seconds
    exponential_base: float = 2.0
    jitter: bool = True
    retry_on_exceptions: List[Type[Exception]] = field(default_factory=list)
    
class ProcessingError(Exception):
    """Base exception for processing errors"""
    
    def __init__(
        self, 
        message: str, 
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        context: ErrorContext = None,
        original_exception: Exception = None,
        recoverable: bool = True
    ):
        super().__init__(message)
        self.message = message
        self.category = category
        self.severity = severity
        self.context = context
        self.original_exception = original_exception
        self.recoverable = recoverable
        self.timestamp = datetime.utcnow()

class NetworkError(ProcessingError):
    """Network-related errors"""
    def __init__(self, message: str, context: ErrorContext = None, original_exception: Exception = None):
        super().__init__(message, ErrorCategory.NETWORK, ErrorSeverity.MEDIUM, context, original_exception)

class StorageError(ProcessingError):
    """Storage-related errors"""
    def __init__(self, message: str, context: ErrorContext = None, original_exception: Exception = None):
        super().__init__(message, ErrorCategory.STORAGE, ErrorSeverity.MEDIUM, context, original_exception)

class OCRProcessingError(ProcessingError):
    """OCR processing errors"""
    def __init__(self, message: str, context: ErrorContext = None, original_exception: Exception = None):
        super().__init__(message, ErrorCategory.OCR_PROCESSING, ErrorSeverity.MEDIUM, context, original_exception)

class AgentProcessingError(ProcessingError):
    """3-Agent pipeline processing errors"""
    def __init__(self, message: str, context: ErrorContext = None, original_exception: Exception = None):
        super().__init__(message, ErrorCategory.AGENT_PROCESSING, ErrorSeverity.MEDIUM, context, original_exception)

class CircuitBreaker:
    """Circuit breaker pattern for preventing cascade failures"""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open
    
    def can_execute(self) -> bool:
        """Check if execution is allowed"""
        if self.state == "closed":
            return True
        elif self.state == "open":
            if self.last_failure_time and \
               (datetime.utcnow() - self.last_failure_time).seconds >= self.recovery_timeout:
                self.state = "half-open"
                return True
            return False
        elif self.state == "half-open":
            return True
        return False
    
    def record_success(self):
        """Record successful execution"""
        self.failure_count = 0
        self.state = "closed"
    
    def record_failure(self):
        """Record failed execution"""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "open"

class ErrorHandler:
    """Comprehensive error handling service"""
    
    def __init__(self):
        self.error_log: List[Dict[str, Any]] = []
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.retry_strategies: Dict[ErrorCategory, RetryStrategy] = self._setup_retry_strategies()
        self.error_callbacks: Dict[ErrorCategory, List[Callable]] = {}
        
    def _setup_retry_strategies(self) -> Dict[ErrorCategory, RetryStrategy]:
        """Setup retry strategies for different error categories"""
        return {
            ErrorCategory.NETWORK: RetryStrategy(
                max_attempts=5,
                base_delay=2.0,
                max_delay=120.0,
                exponential_base=2.0
            ),
            ErrorCategory.STORAGE: RetryStrategy(
                max_attempts=3,
                base_delay=1.0,
                max_delay=30.0,
                exponential_base=1.5
            ),
            ErrorCategory.OCR_PROCESSING: RetryStrategy(
                max_attempts=3,
                base_delay=5.0,
                max_delay=60.0,
                exponential_base=2.0
            ),
            ErrorCategory.DETECTION: RetryStrategy(
                max_attempts=2,
                base_delay=1.0,
                max_delay=10.0,
                exponential_base=1.5
            ),
            ErrorCategory.AGENT_PROCESSING: RetryStrategy(
                max_attempts=3,
                base_delay=3.0,
                max_delay=90.0,
                exponential_base=2.0
            ),
            ErrorCategory.DATABASE: RetryStrategy(
                max_attempts=5,
                base_delay=1.0,
                max_delay=30.0,
                exponential_base=1.8
            ),
            ErrorCategory.TIMEOUT: RetryStrategy(
                max_attempts=2,
                base_delay=10.0,
                max_delay=60.0,
                exponential_base=1.5
            ),
            ErrorCategory.AUTHENTICATION: RetryStrategy(
                max_attempts=2,
                base_delay=1.0,
                max_delay=5.0,
                exponential_base=1.0
            ),
            ErrorCategory.VALIDATION: RetryStrategy(
                max_attempts=1,  # Usually not retryable
                base_delay=0.0,
                max_delay=0.0
            ),
            ErrorCategory.RESOURCE: RetryStrategy(
                max_attempts=4,
                base_delay=5.0,
                max_delay=180.0,
                exponential_base=2.5
            ),
            ErrorCategory.UNKNOWN: RetryStrategy(
                max_attempts=2,
                base_delay=2.0,
                max_delay=30.0,
                exponential_base=2.0
            )
        }
    
    async def handle_error(
        self, 
        error: Exception, 
        context: ErrorContext,
        recovery_function: Callable = None
    ) -> bool:
        """
        Handle an error with appropriate strategy
        
        Returns:
            bool: True if error was handled/recovered, False if processing should stop
        """
        # Classify the error
        processing_error = self._classify_error(error, context)
        
        # Log the error
        await self._log_error(processing_error, context)
        
        # Update progress tracker
        await self._notify_progress_error(processing_error, context)
        
        # Check circuit breaker
        circuit_breaker_key = f"{context.document_id}_{processing_error.category.value}"
        if circuit_breaker_key not in self.circuit_breakers:
            self.circuit_breakers[circuit_breaker_key] = CircuitBreaker()
        
        circuit_breaker = self.circuit_breakers[circuit_breaker_key]
        
        if not circuit_breaker.can_execute():
            logger.error(f"Circuit breaker OPEN for {circuit_breaker_key} - stopping retries")
            await self._handle_circuit_breaker_open(processing_error, context)
            return False
        
        # Determine if retry is appropriate
        if not self._should_retry(processing_error, context):
            logger.info(f"Error not retryable: {processing_error.message}")
            circuit_breaker.record_failure()
            return False
        
        # Execute retry strategy
        retry_strategy = self.retry_strategies.get(
            processing_error.category, 
            self.retry_strategies[ErrorCategory.UNKNOWN]
        )
        
        if context.attempt_number >= retry_strategy.max_attempts:
            logger.error(f"Max retry attempts reached ({retry_strategy.max_attempts}) for {context.document_id}")
            circuit_breaker.record_failure()
            return False
        
        # Calculate retry delay
        delay = self._calculate_retry_delay(retry_strategy, context.attempt_number)
        
        logger.info(f"Retrying in {delay:.2f}s - Attempt {context.attempt_number}/{retry_strategy.max_attempts}")
        
        # Update progress with retry information
        await progress_tracker.update_progress(
            session_id=context.session_id,
            stage=f"{context.processing_stage}_retry",
            progress_percentage=0,
            message=f"Retrying after error - Attempt {context.attempt_number}/{retry_strategy.max_attempts}",
            details={
                'error_category': processing_error.category.value,
                'retry_delay': delay,
                'error_message': processing_error.message
            },
            event_type=ProgressEventType.STAGE_PROGRESS
        )
        
        # Wait for retry delay
        await asyncio.sleep(delay)
        
        # Execute recovery function if provided
        if recovery_function:
            try:
                await recovery_function()
                circuit_breaker.record_success()
                
                # Update progress with recovery success
                await progress_tracker.update_progress(
                    session_id=context.session_id,
                    stage=context.processing_stage,
                    progress_percentage=0,
                    message="Recovered from error, resuming processing",
                    details={'recovery_successful': True},
                    event_type=ProgressEventType.STAGE_PROGRESS
                )
                
                return True
                
            except Exception as recovery_error:
                logger.error(f"Recovery function failed: {str(recovery_error)}")
                circuit_breaker.record_failure()
                return False
        
        circuit_breaker.record_success()
        return True
    
    def _classify_error(self, error: Exception, context: ErrorContext) -> ProcessingError:
        """Classify an error into appropriate category and severity"""
        if isinstance(error, ProcessingError):
            return error
        
        error_message = str(error)
        error_lower = error_message.lower()
        
        # Network-related errors
        if any(keyword in error_lower for keyword in ['connection', 'timeout', 'network', 'dns']):
            return NetworkError(error_message, context, error)
        
        # Storage-related errors
        if any(keyword in error_lower for keyword in ['storage', 'file not found', 'upload', 'download']):
            return StorageError(error_message, context, error)
        
        # OCR processing errors
        if any(keyword in error_lower for keyword in ['azure', 'ocr', 'document intelligence', 'analysis']):
            return OCRProcessingError(error_message, context, error)
        
        # Database errors
        if any(keyword in error_lower for keyword in ['database', 'sql', 'supabase', 'postgres']):
            return ProcessingError(error_message, ErrorCategory.DATABASE, ErrorSeverity.MEDIUM, context, error)
        
        # Authentication errors
        if any(keyword in error_lower for keyword in ['auth', 'permission', 'unauthorized', 'forbidden']):
            return ProcessingError(error_message, ErrorCategory.AUTHENTICATION, ErrorSeverity.HIGH, context, error, recoverable=False)
        
        # Timeout errors
        if any(keyword in error_lower for keyword in ['timeout', 'timed out']):
            return ProcessingError(error_message, ErrorCategory.TIMEOUT, ErrorSeverity.MEDIUM, context, error)
        
        # Validation errors
        if any(keyword in error_lower for keyword in ['validation', 'invalid', 'malformed']):
            return ProcessingError(error_message, ErrorCategory.VALIDATION, ErrorSeverity.LOW, context, error, recoverable=False)
        
        # Resource errors
        if any(keyword in error_lower for keyword in ['memory', 'disk space', 'quota', 'limit']):
            return ProcessingError(error_message, ErrorCategory.RESOURCE, ErrorSeverity.HIGH, context, error)
        
        # Default to unknown
        return ProcessingError(error_message, ErrorCategory.UNKNOWN, ErrorSeverity.MEDIUM, context, error)
    
    def _should_retry(self, error: ProcessingError, context: ErrorContext) -> bool:
        """Determine if an error should be retried"""
        if not error.recoverable:
            return False
        
        # Don't retry validation errors
        if error.category == ErrorCategory.VALIDATION:
            return False
        
        # Don't retry authentication errors
        if error.category == ErrorCategory.AUTHENTICATION:
            return False
        
        # Don't retry if max attempts reached
        retry_strategy = self.retry_strategies.get(error.category, self.retry_strategies[ErrorCategory.UNKNOWN])
        if context.attempt_number >= retry_strategy.max_attempts:
            return False
        
        return True
    
    def _calculate_retry_delay(self, strategy: RetryStrategy, attempt: int) -> float:
        """Calculate retry delay using exponential backoff with jitter"""
        delay = strategy.base_delay * (strategy.exponential_base ** (attempt - 1))
        delay = min(delay, strategy.max_delay)
        
        if strategy.jitter:
            import random
            # Add ±25% jitter
            jitter_factor = 0.25
            jitter = random.uniform(-jitter_factor, jitter_factor)
            delay = delay * (1 + jitter)
        
        return max(0, delay)
    
    async def _log_error(self, error: ProcessingError, context: ErrorContext):
        """Log error details for monitoring and debugging"""
        error_entry = {
            'timestamp': error.timestamp.isoformat(),
            'document_id': context.document_id,
            'session_id': context.session_id,
            'user_id': context.user_id,
            'processing_stage': context.processing_stage,
            'attempt_number': context.attempt_number,
            'error_category': error.category.value,
            'error_severity': error.severity.value,
            'error_message': error.message,
            'recoverable': error.recoverable,
            'stack_trace': traceback.format_exc() if error.original_exception else None,
            'additional_context': context.additional_context
        }
        
        self.error_log.append(error_entry)
        
        # Keep only last 1000 errors in memory
        if len(self.error_log) > 1000:
            self.error_log = self.error_log[-1000:]
        
        # Store in database for persistence
        try:
            await self._persist_error_log(error_entry)
        except Exception as log_error:
            logger.error(f"Failed to persist error log: {str(log_error)}")
        
        # Log to application logger
        log_level = {
            ErrorSeverity.LOW: logging.INFO,
            ErrorSeverity.MEDIUM: logging.WARNING,
            ErrorSeverity.HIGH: logging.ERROR,
            ErrorSeverity.CRITICAL: logging.CRITICAL
        }.get(error.severity, logging.ERROR)
        
        logger.log(log_level, f"Processing error - Document: {context.document_id}, "
                             f"Stage: {context.processing_stage}, "
                             f"Category: {error.category.value}, "
                             f"Message: {error.message}")
    
    async def _persist_error_log(self, error_entry: Dict[str, Any]):
        """Persist error log to database"""
        try:
            document = await supabase_service.get_document(error_entry['document_id'])
            parsed_index = document.get('parsed_index', {})
            
            if 'error_log' not in parsed_index:
                parsed_index['error_log'] = []
            
            parsed_index['error_log'].append(error_entry)
            
            # Keep only last 50 errors per document
            if len(parsed_index['error_log']) > 50:
                parsed_index['error_log'] = parsed_index['error_log'][-50:]
            
            await supabase_service.update_document_status(
                document_id=error_entry['document_id'],
                status='error_logged',
                updates={'parsed_index': parsed_index}
            )
            
        except Exception as e:
            logger.error(f"Failed to persist error log to database: {str(e)}")
    
    async def _notify_progress_error(self, error: ProcessingError, context: ErrorContext):
        """Notify progress tracker of error"""
        try:
            await progress_tracker.update_progress(
                session_id=context.session_id,
                stage=f"{context.processing_stage}_error",
                progress_percentage=0,
                message=f"Error: {error.message}",
                details={
                    'error_category': error.category.value,
                    'error_severity': error.severity.value,
                    'attempt_number': context.attempt_number,
                    'recoverable': error.recoverable
                },
                event_type=ProgressEventType.ERROR_OCCURRED
            )
        except Exception as e:
            logger.error(f"Failed to notify progress tracker of error: {str(e)}")
    
    async def _handle_circuit_breaker_open(self, error: ProcessingError, context: ErrorContext):
        """Handle circuit breaker open state"""
        await progress_tracker.update_progress(
            session_id=context.session_id,
            stage="circuit_breaker_open",
            progress_percentage=0,
            message="Processing temporarily suspended due to repeated failures",
            details={
                'error_category': error.category.value,
                'circuit_breaker_state': 'open'
            },
            event_type=ProgressEventType.ERROR_OCCURRED
        )
    
    async def get_error_summary(self, document_id: str) -> Dict[str, Any]:
        """Get error summary for a document"""
        document_errors = [error for error in self.error_log if error['document_id'] == document_id]
        
        if not document_errors:
            return {
                'document_id': document_id,
                'total_errors': 0,
                'error_categories': {},
                'recent_errors': []
            }
        
        # Count errors by category
        category_counts = {}
        for error in document_errors:
            category = error['error_category']
            category_counts[category] = category_counts.get(category, 0) + 1
        
        return {
            'document_id': document_id,
            'total_errors': len(document_errors),
            'error_categories': category_counts,
            'recent_errors': document_errors[-5:],  # Last 5 errors
            'first_error': document_errors[0]['timestamp'] if document_errors else None,
            'last_error': document_errors[-1]['timestamp'] if document_errors else None
        }

# Global error handler instance
error_handler = ErrorHandler()

# Decorator for automatic error handling
def with_error_handling(
    category: ErrorCategory = ErrorCategory.UNKNOWN,
    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    recoverable: bool = True
):
    """Decorator for automatic error handling"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            context = None
            
            # Try to extract context from function arguments
            for arg in args:
                if hasattr(arg, 'document_id'):
                    context = ErrorContext(
                        document_id=getattr(arg, 'document_id', ''),
                        session_id=getattr(arg, 'session_id', ''),
                        user_id=getattr(arg, 'user_id', ''),
                        processing_stage=func.__name__
                    )
                    break
            
            if not context:
                context = ErrorContext(
                    document_id=kwargs.get('document_id', ''),
                    session_id=kwargs.get('session_id', ''),
                    user_id=kwargs.get('user_id', ''),
                    processing_stage=func.__name__
                )
            
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                processing_error = ProcessingError(
                    message=str(e),
                    category=category,
                    severity=severity,
                    context=context,
                    original_exception=e,
                    recoverable=recoverable
                )
                
                handled = await error_handler.handle_error(processing_error, context)
                
                if not handled:
                    raise
                
                # If handled successfully, retry the function
                context.attempt_number += 1
                return await func(*args, **kwargs)
        
        return wrapper
    return decorator
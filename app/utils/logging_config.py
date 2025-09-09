"""
Logging configuration for the NMTC platform
"""
import logging
import logging.config
import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path
import os


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields from the record
        extra_fields = {
            key: value for key, value in record.__dict__.items()
            if key not in {
                'name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                'filename', 'module', 'lineno', 'funcName', 'created', 'msecs',
                'relativeCreated', 'thread', 'threadName', 'processName', 'process',
                'message', 'exc_info', 'exc_text', 'stack_info', 'getMessage'
            }
        }
        
        if extra_fields:
            log_entry["extra"] = extra_fields
        
        return json.dumps(log_entry)


class ContextFilter(logging.Filter):
    """Add context information to log records"""
    
    def __init__(self):
        super().__init__()
        self.request_id = None
        self.user_id = None
        self.org_id = None
    
    def filter(self, record: logging.LogRecord) -> bool:
        # Add context information to the record
        if self.request_id:
            record.request_id = self.request_id
        if self.user_id:
            record.user_id = self.user_id
        if self.org_id:
            record.org_id = self.org_id
        
        return True
    
    def set_context(
        self, 
        request_id: Optional[str] = None,
        user_id: Optional[uuid.UUID] = None,
        org_id: Optional[uuid.UUID] = None
    ):
        """Set context for current request"""
        self.request_id = request_id
        self.user_id = str(user_id) if user_id else None
        self.org_id = str(org_id) if org_id else None
    
    def clear_context(self):
        """Clear context"""
        self.request_id = None
        self.user_id = None
        self.org_id = None


# Global context filter instance
context_filter = ContextFilter()


def setup_logging(
    log_level: str = "INFO",
    log_format: str = "standard",
    log_file: Optional[str] = None,
    enable_json: bool = False
) -> None:
    """Setup logging configuration"""
    
    # Create logs directory if needed
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Configure handlers
    handlers = {}
    
    # Console handler
    console_config = {
        'class': 'logging.StreamHandler',
        'stream': 'ext://sys.stdout',
        'level': log_level,
        'filters': ['context']
    }
    
    if enable_json or log_format == "json":
        console_config['formatter'] = 'json'
    else:
        console_config['formatter'] = 'standard'
    
    handlers['console'] = console_config
    
    # File handler
    if log_file:
        file_config = {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': log_file,
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
            'level': log_level,
            'filters': ['context']
        }
        
        if enable_json or log_format == "json":
            file_config['formatter'] = 'json'
        else:
            file_config['formatter'] = 'standard'
        
        handlers['file'] = file_config
    
    # Logging configuration
    config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'standard': {
                'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
            },
            'detailed': {
                'format': '%(asctime)s [%(levelname)s] %(name)s:%(lineno)d %(funcName)s(): %(message)s'
            },
            'json': {
                '()': 'app.utils.logging_config.JSONFormatter'
            }
        },
        'filters': {
            'context': {
                '()': lambda: context_filter
            }
        },
        'handlers': handlers,
        'root': {
            'level': log_level,
            'handlers': list(handlers.keys())
        },
        'loggers': {
            'app': {
                'level': log_level,
                'propagate': True
            },
            'uvicorn': {
                'level': 'INFO',
                'propagate': True
            },
            'uvicorn.access': {
                'level': 'INFO',
                'propagate': True
            },
            'fastapi': {
                'level': 'INFO',
                'propagate': True
            },
            'supabase': {
                'level': 'WARNING',
                'propagate': True
            }
        }
    }
    
    logging.config.dictConfig(config)
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured - Level: {log_level}, Format: {log_format}")


class StructuredLogger:
    """Structured logger with context support"""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
    
    def _log_with_context(self, level: int, message: str, **kwargs):
        """Log message with structured context"""
        extra = {}
        
        # Add any kwargs as extra context
        for key, value in kwargs.items():
            if isinstance(value, (uuid.UUID, datetime)):
                extra[key] = str(value)
            elif value is not None:
                extra[key] = value
        
        # Log with extra context
        self.logger.log(level, message, extra=extra)
    
    def info(self, message: str, **kwargs):
        self._log_with_context(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        self._log_with_context(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs):
        self._log_with_context(logging.ERROR, message, **kwargs)
    
    def debug(self, message: str, **kwargs):
        self._log_with_context(logging.DEBUG, message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        self._log_with_context(logging.CRITICAL, message, **kwargs)


# Utility functions
def get_logger(name: str) -> logging.Logger:
    """Get a standard logger instance"""
    return logging.getLogger(name)


def get_structured_logger(name: str) -> StructuredLogger:
    """Get a structured logger instance"""
    return StructuredLogger(name)


def log_api_request(
    logger: logging.Logger,
    method: str,
    path: str,
    status_code: int,
    duration_ms: Optional[float] = None,
    user_id: Optional[uuid.UUID] = None,
    org_id: Optional[uuid.UUID] = None,
    request_id: Optional[str] = None,
    error: Optional[str] = None
):
    """Log API request with structured data"""
    log_data = {
        "event": "api_request",
        "method": method,
        "path": path,
        "status_code": status_code
    }
    
    if duration_ms is not None:
        log_data["duration_ms"] = duration_ms
    if user_id:
        log_data["user_id"] = str(user_id)
    if org_id:
        log_data["org_id"] = str(org_id)
    if request_id:
        log_data["request_id"] = request_id
    if error:
        log_data["error"] = error
        logger.error("API request failed", extra=log_data)
    else:
        logger.info("API request", extra=log_data)


def log_database_operation(
    logger: logging.Logger,
    operation: str,
    table: str,
    duration_ms: Optional[float] = None,
    record_count: Optional[int] = None,
    error: Optional[str] = None
):
    """Log database operation with performance metrics"""
    log_data = {
        "event": "database_operation",
        "operation": operation,
        "table": table
    }
    
    if duration_ms is not None:
        log_data["duration_ms"] = duration_ms
    if record_count is not None:
        log_data["record_count"] = record_count
    if error:
        log_data["error"] = error
        logger.error("Database operation failed", extra=log_data)
    else:
        logger.info("Database operation", extra=log_data)


def log_business_event(
    logger: logging.Logger,
    event_type: str,
    org_id: uuid.UUID,
    user_id: Optional[uuid.UUID] = None,
    **context
):
    """Log business events for analytics and audit"""
    log_data = {
        "event": "business_event",
        "event_type": event_type,
        "org_id": str(org_id),
        "timestamp": datetime.utcnow().isoformat()
    }
    
    if user_id:
        log_data["user_id"] = str(user_id)
    
    # Add any additional context
    for key, value in context.items():
        if isinstance(value, (uuid.UUID, datetime)):
            log_data[key] = str(value)
        elif value is not None:
            log_data[key] = value
    
    logger.info("Business event", extra=log_data)


def log_security_event(
    logger: logging.Logger,
    event_type: str,
    severity: str = "medium",
    user_id: Optional[uuid.UUID] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    **context
):
    """Log security-related events"""
    log_data = {
        "event": "security_event",
        "event_type": event_type,
        "severity": severity,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    if user_id:
        log_data["user_id"] = str(user_id)
    if ip_address:
        log_data["ip_address"] = ip_address
    if user_agent:
        log_data["user_agent"] = user_agent
    
    # Add additional context
    for key, value in context.items():
        if isinstance(value, (uuid.UUID, datetime)):
            log_data[key] = str(value)
        elif value is not None:
            log_data[key] = value
    
    if severity in ["high", "critical"]:
        logger.error("Security event", extra=log_data)
    else:
        logger.warning("Security event", extra=log_data)


# Context managers
class RequestLoggingContext:
    """Context manager for request-level logging"""
    
    def __init__(
        self,
        request_id: str,
        user_id: Optional[uuid.UUID] = None,
        org_id: Optional[uuid.UUID] = None
    ):
        self.request_id = request_id
        self.user_id = user_id
        self.org_id = org_id
    
    def __enter__(self):
        context_filter.set_context(self.request_id, self.user_id, self.org_id)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        context_filter.clear_context()


class LoggerMixin:
    """Mixin class to add logging capabilities"""
    
    @property
    def logger(self) -> logging.Logger:
        return logging.getLogger(self.__class__.__module__ + "." + self.__class__.__name__)
    
    @property
    def structured_logger(self) -> StructuredLogger:
        return StructuredLogger(self.__class__.__module__ + "." + self.__class__.__name__)


# Environment-specific configurations
def setup_production_logging():
    """Setup logging for production environment"""
    log_level = os.getenv("LOG_LEVEL", "INFO")
    log_file = os.getenv("LOG_FILE", "/var/log/nmtc-backend.log")
    
    setup_logging(
        log_level=log_level,
        log_format="json",
        log_file=log_file,
        enable_json=True
    )
    
    # Reduce noise in production
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def setup_development_logging():
    """Setup logging for development environment"""
    setup_logging(
        log_level="DEBUG",
        log_format="standard",
        log_file=None,
        enable_json=False
    )


def setup_test_logging():
    """Setup logging for test environment"""
    setup_logging(
        log_level="WARNING",
        log_format="standard",
        log_file=None,
        enable_json=False
    )
    
    # Silence most loggers during tests
    logging.getLogger("app").setLevel(logging.ERROR)
    logging.getLogger("uvicorn").setLevel(logging.ERROR)


# Auto-detect environment and configure
def configure_logging():
    """Auto-configure logging based on environment"""
    environment = os.getenv("ENVIRONMENT", "development").lower()
    
    if environment == "production":
        setup_production_logging()
    elif environment == "test":
        setup_test_logging()
    else:
        setup_development_logging()
    
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured for {environment} environment")


# Initialize logging when module is imported
if __name__ != "__main__":
    configure_logging()
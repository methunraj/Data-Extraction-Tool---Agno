"""
Structured logging configuration for IntelliExtract.
"""

import logging
import logging.config
import json
import sys
from datetime import datetime
from typing import Dict, Any, Optional
import traceback
import os
from pathlib import Path

from .config import settings


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured JSON logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON."""
        
        # Base log entry
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add process and thread info
        log_entry.update({
            "process_id": os.getpid(),
            "thread_id": record.thread,
            "thread_name": record.threadName,
        })
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": traceback.format_exception(*record.exc_info)
            }
        
        # Add extra fields from the log record
        extra_fields = {}
        for key, value in record.__dict__.items():
            if key not in {
                'name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                'filename', 'module', 'exc_info', 'exc_text', 'stack_info',
                'lineno', 'funcName', 'created', 'msecs', 'relativeCreated',
                'thread', 'threadName', 'processName', 'process', 'message'
            }:
                extra_fields[key] = value
        
        if extra_fields:
            log_entry["extra"] = extra_fields
        
        # Add application context
        log_entry["application"] = {
            "name": "intelliextract",
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT
        }
        
        return json.dumps(log_entry, default=str, ensure_ascii=False)


class ErrorMonitor:
    """Error monitoring and alerting system."""
    
    def __init__(self):
        self.error_counts = {}
        self.logger = logging.getLogger("error_monitor")
    
    def record_error(self, error: Exception, context: Optional[Dict[str, Any]] = None):
        """Record an error for monitoring."""
        error_type = type(error).__name__
        error_message = str(error)
        
        # Count errors by type
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
        
        # Log structured error
        self.logger.error(
            f"Error occurred: {error_message}",
            extra={
                "error_type": error_type,
                "error_message": error_message,
                "error_count": self.error_counts[error_type],
                "context": context or {},
                "traceback": traceback.format_exc()
            },
            exc_info=True
        )
        
        # Check if we should alert (e.g., too many errors of same type)
        if self.error_counts[error_type] > 10:
            self._send_alert(error_type, self.error_counts[error_type])
    
    def _send_alert(self, error_type: str, count: int):
        """Send alert for high error rates."""
        self.logger.critical(
            f"High error rate detected: {error_type} occurred {count} times",
            extra={
                "alert_type": "high_error_rate",
                "error_type": error_type,
                "error_count": count
            }
        )
    
    def get_error_stats(self) -> Dict[str, int]:
        """Get current error statistics."""
        return self.error_counts.copy()


def setup_logging():
    """Setup structured logging configuration."""
    
    # Create logs directory
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Determine log level
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    
    # Logging configuration
    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "structured": {
                "()": StructuredFormatter,
            },
            "simple": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": log_level,
                "formatter": "structured" if settings.ENVIRONMENT == "production" else "simple",
                "stream": sys.stdout
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": log_level,
                "formatter": "structured",
                "filename": log_dir / "intelliextract.log",
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5,
                "encoding": "utf8"
            },
            "error_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": logging.ERROR,
                "formatter": "structured",
                "filename": log_dir / "errors.log",
                "maxBytes": 10485760,  # 10MB
                "backupCount": 10,
                "encoding": "utf8"
            }
        },
        "loggers": {
            "app": {
                "level": log_level,
                "handlers": ["console", "file", "error_file"],
                "propagate": False
            },
            "error_monitor": {
                "level": logging.ERROR,
                "handlers": ["console", "error_file"],
                "propagate": False
            },
            "uvicorn": {
                "level": logging.INFO,
                "handlers": ["console", "file"],
                "propagate": False
            },
            "fastapi": {
                "level": logging.INFO,
                "handlers": ["console", "file"],
                "propagate": False
            }
        },
        "root": {
            "level": log_level,
            "handlers": ["console", "file"]
        }
    }
    
    # Apply configuration
    logging.config.dictConfig(config)
    
    # Log startup message
    logger = logging.getLogger("app.startup")
    logger.info(
        "Logging system initialized",
        extra={
            "log_level": settings.LOG_LEVEL,
            "environment": settings.ENVIRONMENT,
            "log_directory": str(log_dir.absolute())
        }
    )


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the specified name."""
    return logging.getLogger(f"app.{name}")


def log_api_request(request_id: str, method: str, path: str, **kwargs):
    """Log API request with structured data."""
    logger = get_logger("api")
    logger.info(
        f"{method} {path}",
        extra={
            "request_id": request_id,
            "method": method,
            "path": path,
            **kwargs
        }
    )


def log_api_response(request_id: str, status_code: int, duration_ms: float, **kwargs):
    """Log API response with structured data."""
    logger = get_logger("api")
    logger.info(
        f"Response {status_code}",
        extra={
            "request_id": request_id,
            "status_code": status_code,
            "duration_ms": duration_ms,
            **kwargs
        }
    )


def log_workflow_event(workflow_name: str, event: str, **kwargs):
    """Log workflow events with structured data."""
    logger = get_logger("workflow")
    logger.info(
        f"Workflow {workflow_name}: {event}",
        extra={
            "workflow_name": workflow_name,
            "event": event,
            **kwargs
        }
    )


# Global error monitor instance
error_monitor = ErrorMonitor()


def log_error(error: Exception, context: Optional[Dict[str, Any]] = None):
    """Log an error with monitoring."""
    error_monitor.record_error(error, context)
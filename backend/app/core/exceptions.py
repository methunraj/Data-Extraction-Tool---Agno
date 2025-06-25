# app/core/exceptions.py
from typing import Optional, Dict, Any

class BaseAPIException(Exception):
    """Base exception for all API exceptions."""
    
    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}

class ConfigurationError(BaseAPIException):
    """Raised when there's a configuration issue."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=500, error_code="CONFIGURATION_ERROR", details=details)

class ModelNotFoundError(BaseAPIException):
    """Raised when a requested model is not found."""
    
    def __init__(self, model_id: str, details: Optional[Dict[str, Any]] = None):
        message = f"Model '{model_id}' not found"
        super().__init__(message, status_code=404, error_code="MODEL_NOT_FOUND", details=details)

class InvalidRequestError(BaseAPIException):
    """Raised when the request is invalid."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=400, error_code="INVALID_REQUEST", details=details)

class ExtractionError(BaseAPIException):
    """Raised when data extraction fails."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=500, error_code="EXTRACTION_ERROR", details=details)

class GenerationError(BaseAPIException):
    """Raised when content generation fails."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=500, error_code="GENERATION_ERROR", details=details)

class CacheError(BaseAPIException):
    """Raised when caching operations fail."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=500, error_code="CACHE_ERROR", details=details)

class TokenLimitError(BaseAPIException):
    """Raised when token limits are exceeded."""
    
    def __init__(self, message: str, limit: int, actual: int, details: Optional[Dict[str, Any]] = None):
        if details is None:
            details = {}
        details.update({"limit": limit, "actual": actual})
        super().__init__(message, status_code=400, error_code="TOKEN_LIMIT_EXCEEDED", details=details)

class APIKeyError(BaseAPIException):
    """Raised when API key is missing or invalid."""
    
    def __init__(self, message: str = "API key is missing or invalid", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=401, error_code="API_KEY_ERROR", details=details)

class RateLimitError(BaseAPIException):
    """Raised when rate limits are exceeded."""
    
    def __init__(self, message: str, retry_after: Optional[int] = None, details: Optional[Dict[str, Any]] = None):
        if details is None:
            details = {}
        if retry_after:
            details["retry_after"] = retry_after
        super().__init__(message, status_code=429, error_code="RATE_LIMIT_EXCEEDED", details=details)

class TimeoutError(BaseAPIException):
    """Raised when an operation times out."""
    
    def __init__(self, message: str, timeout_seconds: Optional[int] = None, details: Optional[Dict[str, Any]] = None):
        if details is None:
            details = {}
        if timeout_seconds:
            details["timeout_seconds"] = timeout_seconds
        super().__init__(message, status_code=504, error_code="TIMEOUT_ERROR", details=details)
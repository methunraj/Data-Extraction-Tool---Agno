# app/schemas/common.py
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str = Field(description="Error message")
    error_code: str = Field(description="Error code")
    status_code: int = Field(description="HTTP status code")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")

class SuccessResponse(BaseModel):
    """Standard success response."""
    message: str = Field(description="Success message")
    data: Optional[Dict[str, Any]] = Field(None, description="Additional data")

class HealthCheckResponse(BaseModel):
    """Health check response."""
    status: str = Field(description="Service status")
    version: str = Field(description="API version")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    services: Dict[str, str] = Field(description="Status of dependent services")
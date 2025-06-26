# app/core/dependencies.py
from typing import Annotated
from fastapi import Depends, HTTPException, Header
from .config import settings
from .google_client import GoogleGenAIClient
from ..utils.model_utils import get_model_service
from ..services.model_service import ModelService
import logging

logger = logging.getLogger(__name__)

async def get_api_key(
    x_api_key: Annotated[str | None, Header()] = None
) -> str:
    """
    Get API key from request header or fall back to environment variable.
    
    Args:
        x_api_key: API key from request header
    
    Returns:
        The API key
    
    Raises:
        HTTPException: If no API key is found
    """
    # First check header
    if x_api_key:
        return x_api_key
    
    # Fall back to environment variable
    if settings.GOOGLE_API_KEY:
        return settings.GOOGLE_API_KEY
    
    raise HTTPException(
        status_code=401,
        detail="API key required. Please provide via X-API-Key header or set GOOGLE_API_KEY environment variable."
    )

async def get_google_client() -> GoogleGenAIClient:
    """Get the Google GenAI client instance."""
    if not GoogleGenAIClient.validate_api_key():
        raise HTTPException(
            status_code=500,
            detail="Google API key not configured properly"
        )
    return GoogleGenAIClient.get_client()

async def get_model_service_dep() -> ModelService:
    """Get the model service instance."""
    return get_model_service()

# Dependency annotations for cleaner imports
APIKeyDep = Annotated[str, Depends(get_api_key)]
GoogleClientDep = Annotated[GoogleGenAIClient, Depends(get_google_client)]
ModelServiceDep = Annotated[ModelService, Depends(get_model_service_dep)]
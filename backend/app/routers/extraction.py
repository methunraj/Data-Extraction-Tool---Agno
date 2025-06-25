# app/routers/extraction.py
from fastapi import APIRouter, Depends, HTTPException
from typing import List

from ..core.dependencies import ModelServiceDep, APIKeyDep
from ..core.exceptions import BaseAPIException
from ..schemas.extraction import (
    ExtractDataRequest, ExtractDataResponse,
    EstimateTokensRequest, EstimateTokensResponse
)
from ..services.extraction_service import ExtractionService
from ..services.token_service import TokenService
from ..services.cache_service import get_cache_service

router = APIRouter(prefix="/api", tags=["extraction"])

def get_extraction_service(
    model_service: ModelServiceDep
) -> ExtractionService:
    """Get extraction service instance."""
    token_service = TokenService(model_service)
    cache_service = get_cache_service(model_service)
    return ExtractionService(model_service, token_service, cache_service)

def get_token_service(
    model_service: ModelServiceDep
) -> TokenService:
    """Get token service instance."""
    return TokenService(model_service)

@router.post("/extract-data", response_model=ExtractDataResponse)
async def extract_data(
    request: ExtractDataRequest,
    api_key: APIKeyDep,
    extraction_service: ExtractionService = Depends(get_extraction_service)
) -> ExtractDataResponse:
    """
    Extract structured data from documents using the selected model.
    
    This endpoint replaces the frontend Genkit extract-data-flow functionality.
    It supports:
    - Text and multimodal document input
    - JSON schema-based extraction
    - Few-shot examples
    - Thinking mode (for supported models)
    - Context caching for repeated extractions
    - Automatic retries with exponential backoff
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # Log the request for debugging
    logger.info(f"Extraction request - Model: {request.model_name}, Provider: {request.provider}")
    logger.info(f"Has document_text: {bool(request.document_text)}, Has document_file: {bool(request.document_file)}")
    logger.info(f"Schema length: {len(request.schema_definition)}, System prompt length: {len(request.system_prompt)}")
    
    try:
        return await extraction_service.extract_data(request)
    except BaseAPIException:
        raise
    except Exception as e:
        # Log the actual error with full traceback
        logger.error(f"Extraction failed with error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/estimate-tokens", response_model=EstimateTokensResponse)
async def estimate_tokens(
    request: EstimateTokensRequest,
    api_key: APIKeyDep,
    token_service: TokenService = Depends(get_token_service)
) -> EstimateTokensResponse:
    """
    Estimate token count and cost before extraction.
    
    This helps users understand the cost implications before running extraction.
    Provides breakdown by content type:
    - Document content
    - Schema definition  
    - System prompt
    - User task description
    - Examples
    - Media content (images, PDFs, etc.)
    """
    try:
        extraction_service = ExtractionService(
            model_service=token_service.model_service,
            token_service=token_service
        )
        return await extraction_service.estimate_tokens(request)
    except BaseAPIException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
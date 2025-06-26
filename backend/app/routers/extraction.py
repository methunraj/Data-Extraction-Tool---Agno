# app/routers/extraction.py
import asyncio
import logging
from fastapi import APIRouter, Depends, HTTPException, Request
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
logger = logging.getLogger(__name__)

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
    fastapi_request: Request,
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
    # Log the request for debugging
    logger.info(f"Extraction request - Model: {request.model_name}, Provider: {request.provider}")
    logger.info(f"Has document_text: {bool(request.document_text)}, Has document_file: {bool(request.document_file)}")
    logger.info(f"Schema length: {len(request.schema_definition)}, System prompt length: {len(request.system_prompt)}")
    
    # Add client disconnection checking
    async def check_disconnect():
        while True:
            if await fastapi_request.is_disconnected():
                logger.warning("Client disconnected during extraction, cancelling operation.")
                return True
            await asyncio.sleep(0.1)
    
    disconnect_task = asyncio.create_task(check_disconnect())
    
    try:
        # Run extraction and disconnect check concurrently
        extraction_task = asyncio.create_task(extraction_service.extract_data(request))
        
        done, pending = await asyncio.wait(
            [extraction_task, disconnect_task],
            return_when=asyncio.FIRST_COMPLETED
        )
        
        # Cancel pending tasks
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        # Check if extraction completed or was cancelled
        if extraction_task in done:
            return extraction_task.result()
        else:
            # Client disconnected
            raise HTTPException(status_code=499, detail="Client disconnected")
            
    except BaseAPIException:
        raise
    except Exception as e:
        # Log the actual error with full traceback
        logger.error(f"Extraction failed with error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Ensure disconnect task is cancelled
        if not disconnect_task.done():
            disconnect_task.cancel()
            try:
                await disconnect_task
            except asyncio.CancelledError:
                pass

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
# app/routers/generation.py
import asyncio
import logging
from fastapi import APIRouter, Depends, HTTPException, Request

from ..core.dependencies import ModelServiceDep, APIKeyDep
from ..core.exceptions import BaseAPIException
from ..schemas.generation import (
    GenerateConfigRequest, GenerateConfigResponse,
    GenerateSchemaRequest, GenerateSchemaResponse,
    GeneratePromptRequest, GeneratePromptResponse,
    RefineConfigRequest, RefineConfigResponse
)
from ..services.generation_service import GenerationService

router = APIRouter(prefix="/api", tags=["generation"])
logger = logging.getLogger(__name__)

def get_generation_service(
    model_service: ModelServiceDep
) -> GenerationService:
    """Get generation service instance."""
    return GenerationService(model_service)

@router.post("/generate-unified-config", response_model=GenerateConfigResponse)
async def generate_unified_config(
    request: GenerateConfigRequest,
    fastapi_request: Request,
    api_key: APIKeyDep,
    generation_service: GenerationService = Depends(get_generation_service)
) -> GenerateConfigResponse:
    """
    Generate a complete extraction configuration from user intent.
    
    This endpoint replaces the frontend unified-generation-flow functionality.
    It generates:
    - JSON schema for structured extraction
    - System prompt optimized for the extraction task
    - User prompt template with placeholders
    - Few-shot examples (optional)
    - Reasoning explanation (optional)
    
    The generated configuration can be directly used with the /extract-data endpoint.
    """
    # Add client disconnection checking
    async def check_disconnect():
        while True:
            if await fastapi_request.is_disconnected():
                logger.warning("Client disconnected during generation, cancelling operation.")
                return True
            await asyncio.sleep(0.1)
    
    disconnect_task = asyncio.create_task(check_disconnect())
    
    try:
        # Run generation and disconnect check concurrently
        generation_task = asyncio.create_task(generation_service.generate_unified_config(request))
        
        done, pending = await asyncio.wait(
            [generation_task, disconnect_task],
            return_when=asyncio.FIRST_COMPLETED
        )
        
        # Cancel pending tasks
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        # Check if generation completed or was cancelled
        if generation_task in done:
            return generation_task.result()
        else:
            # Client disconnected
            raise HTTPException(status_code=499, detail="Client disconnected")
            
    except BaseAPIException:
        raise
    except Exception as e:
        logger.error(f"Generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Ensure disconnect task is cancelled
        if not disconnect_task.done():
            disconnect_task.cancel()
            try:
                await disconnect_task
            except asyncio.CancelledError:
                pass

@router.post("/generate-schema", response_model=GenerateSchemaResponse)
async def generate_schema(
    request: GenerateSchemaRequest,
    api_key: APIKeyDep,
    generation_service: GenerationService = Depends(get_generation_service)
) -> GenerateSchemaResponse:
    """
    Generate only a JSON schema from user intent.
    
    Use this when you want to:
    - Create a schema for a specific data structure
    - Define validation rules and constraints
    - Get field-level explanations
    
    The generated schema can be refined with specific field descriptions and constraints.
    """
    try:
        return await generation_service.generate_schema(request)
    except BaseAPIException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/generate-prompts", response_model=GeneratePromptResponse)
async def generate_prompts(
    request: GeneratePromptRequest,
    api_key: APIKeyDep,
    generation_service: GenerationService = Depends(get_generation_service)
) -> GeneratePromptResponse:
    """
    Generate prompts for a given schema and extraction goal.
    
    Use this when you have a schema but need:
    - Optimized system prompt for extraction
    - User prompt template with placeholders
    - Usage tips for best results
    
    This is useful for fine-tuning extraction behavior with existing schemas.
    """
    try:
        return await generation_service.generate_prompts(request)
    except BaseAPIException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/refine-config", response_model=RefineConfigResponse)
async def refine_config(
    request: RefineConfigRequest,
    api_key: APIKeyDep,
    generation_service: GenerationService = Depends(get_generation_service)
) -> RefineConfigResponse:
    """
    Refine an existing extraction configuration based on feedback.
    
    Use this to improve extraction accuracy by providing:
    - Current schema and prompts
    - Specific refinement instructions
    - Examples that failed extraction
    
    The service will analyze issues and generate improved configuration
    while maintaining backward compatibility where possible.
    """
    try:
        return await generation_service.refine_config(request)
    except BaseAPIException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
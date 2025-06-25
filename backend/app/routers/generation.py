# app/routers/generation.py
from fastapi import APIRouter, Depends, HTTPException

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

def get_generation_service(
    model_service: ModelServiceDep
) -> GenerationService:
    """Get generation service instance."""
    return GenerationService(model_service)

@router.post("/generate-unified-config", response_model=GenerateConfigResponse)
async def generate_unified_config(
    request: GenerateConfigRequest,
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
    try:
        return await generation_service.generate_unified_config(request)
    except BaseAPIException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
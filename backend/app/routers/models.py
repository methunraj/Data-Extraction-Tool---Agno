# app/routers/models.py
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional

from ..core.dependencies import ModelServiceDep
from ..schemas.models import (
    ModelInfo, ModelListResponse,
    CostEstimateRequest, CostEstimateResponse
)

router = APIRouter(prefix="/api/models", tags=["models"])

@router.get("", response_model=ModelListResponse)
async def list_models(
    purpose: Optional[str] = Query(None, description="Filter by purpose (extraction, generation, agno)"),
    model_service: ModelServiceDep = ModelServiceDep
) -> ModelListResponse:
    """
    List available AI models with their capabilities and pricing.
    
    Optionally filter by purpose:
    - extraction: Models that support document data extraction
    - generation: Models that support configuration generation
    - agno: Models that support backend Agno processing
    
    Each model includes:
    - Capabilities (vision, audio, thinking mode, etc.)
    - Token limits and context window
    - Pricing information (input/output/cache)
    - Supported features
    """
    try:
        if purpose:
            models = model_service.get_models_for_purpose(purpose)
        else:
            models = model_service.get_all_models()
        
        # Convert to response models
        model_infos = []
        for model in models:
            model_info = ModelInfo(
                id=model["id"],
                displayName=model["displayName"],
                description=model["description"],
                provider=model["provider"],
                supportedIn=model["supportedIn"],
                capabilities=model.get("capabilities", {}),
                limits=model.get("limits", {}),
                pricing=model["pricing"],
                tokenCalculation=model.get("tokenCalculation"),
                status=model.get("status", "stable"),
                knowledgeCutoff=model.get("knowledgeCutoff")
            )
            model_infos.append(model_info)
        
        return ModelListResponse(
            models=model_infos,
            total=len(model_infos)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{model_id}", response_model=ModelInfo)
async def get_model(
    model_id: str,
    model_service: ModelServiceDep = ModelServiceDep
) -> ModelInfo:
    """
    Get detailed information about a specific model.
    
    Returns complete model configuration including:
    - All capabilities and features
    - Detailed pricing breakdown
    - Token calculation rules
    - Limits and constraints
    """
    try:
        model = model_service.get_model(model_id)
        if not model:
            raise HTTPException(status_code=404, detail=f"Model {model_id} not found")
        
        return ModelInfo(
            id=model["id"],
            displayName=model["displayName"],
            description=model["description"],
            provider=model["provider"],
            supportedIn=model["supportedIn"],
            capabilities=model.get("capabilities", {}),
            limits=model.get("limits", {}),
            pricing=model["pricing"],
            tokenCalculation=model.get("tokenCalculation"),
            status=model.get("status", "stable"),
            knowledgeCutoff=model.get("knowledgeCutoff")
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/estimate-cost", response_model=CostEstimateResponse)
async def estimate_cost(
    request: CostEstimateRequest,
    model_service: ModelServiceDep = ModelServiceDep
) -> CostEstimateResponse:
    """
    Estimate cost for specific token usage.
    
    Provide token counts to get:
    - Total estimated cost
    - Breakdown by type (input, output, cache)
    - Currency information
    
    Supports:
    - Regular input/output tokens
    - Cached tokens (reduced pricing)
    - Thinking tokens (for models with thinking mode)
    - Cache storage costs
    """
    try:
        # Validate model exists
        model = model_service.get_model(request.model_id)
        if not model:
            raise HTTPException(status_code=404, detail=f"Model {request.model_id} not found")
        
        # Calculate costs
        usage = {
            "input_tokens": request.input_tokens,
            "output_tokens": request.output_tokens,
            "cached_tokens": request.cached_tokens,
            "thinking_tokens": request.thinking_tokens,
            "cache_storage_hours": request.cache_hours,
            "cached_content_size": request.cached_tokens  # Assume size equals tokens
        }
        
        total_cost = model_service.calculate_cost(request.model_id, usage)
        
        # Get detailed breakdown
        breakdown = {}
        pricing = model["pricing"]
        
        # Input cost
        uncached_input = max(0, request.input_tokens - request.cached_tokens)
        if isinstance(pricing["input"], dict):
            breakdown["input"] = (uncached_input / 1_000_000) * pricing["input"]["default"]
            if request.cached_tokens > 0 and "cached" in pricing["input"]:
                breakdown["cached_input"] = (request.cached_tokens / 1_000_000) * pricing["input"]["cached"]
        else:
            breakdown["input"] = (request.input_tokens / 1_000_000) * pricing["input"]
        
        # Output cost (including thinking if applicable)
        total_output = request.output_tokens
        if not pricing.get("output", {}).get("includesThinking", False):
            total_output += request.thinking_tokens
        
        if isinstance(pricing["output"], dict):
            breakdown["output"] = (total_output / 1_000_000) * pricing["output"]["default"]
        else:
            breakdown["output"] = (total_output / 1_000_000) * pricing["output"]
        
        # Cache storage cost
        if request.cache_hours > 0 and "cacheStorage" in pricing:
            breakdown["cache_storage"] = (request.cached_tokens / 1_000_000) * request.cache_hours * pricing["cacheStorage"]
        
        return CostEstimateResponse(
            model_id=request.model_id,
            estimated_cost=total_cost,
            breakdown=breakdown,
            currency=pricing.get("currency", "USD")
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{model_id}/validate-limits")
async def validate_limits(
    model_id: str,
    input_tokens: int = Query(..., ge=0, description="Number of input tokens"),
    output_tokens: Optional[int] = Query(None, ge=0, description="Expected output tokens"),
    model_service: ModelServiceDep = ModelServiceDep
):
    """
    Validate if token counts are within model limits.
    
    Check if your request will fit within:
    - Maximum input tokens
    - Maximum output tokens
    - Total context window
    
    Returns validation results with any warnings or errors.
    """
    try:
        # Get token service
        from ..services.token_service import TokenService
        token_service = TokenService(model_service)
        
        result = token_service.validate_token_limits(
            model_id=model_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens
        )
        
        if not result["valid"]:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Token limits exceeded",
                    "errors": result["errors"],
                    "limits": result["limits"]
                }
            )
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
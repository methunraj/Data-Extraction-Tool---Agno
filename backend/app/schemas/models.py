# app/schemas/models.py
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Union
from enum import Enum

class ModelCapabilities(BaseModel):
    """Model capabilities information."""
    thinking: Optional[Dict[str, Any]] = Field(None, description="Thinking mode configuration")
    vision: bool = Field(False, description="Supports image input")
    audio: bool = Field(False, description="Supports audio input")
    video: bool = Field(False, description="Supports video input")
    pdf: bool = Field(False, description="Supports PDF input")
    contextCaching: bool = Field(False, description="Supports context caching")
    functionCalling: bool = Field(False, description="Supports function calling")
    structuredOutputs: bool = Field(False, description="Supports structured outputs")
    liveAPI: bool = Field(False, description="Supports live API")

class ModelLimits(BaseModel):
    """Model token and context limits."""
    maxInputTokens: int = Field(description="Maximum input tokens")
    maxOutputTokens: int = Field(description="Maximum output tokens")
    contextWindow: int = Field(description="Total context window size")

class ModelPricing(BaseModel):
    """Model pricing information."""
    input: Union[float, Dict[str, float]] = Field(description="Input pricing")
    output: Union[float, Dict[str, float]] = Field(description="Output pricing")
    cacheStorage: Optional[float] = Field(None, description="Cache storage cost per million tokens per hour")
    currency: str = Field(default="USD", description="Currency code")
    unit: str = Field(default="perMillionTokens", description="Pricing unit")

class ModelTokenCalculation(BaseModel):
    """Token calculation rules for different media types."""
    image: Optional[Dict[str, Any]] = None
    document: Optional[Dict[str, Any]] = None
    video: Optional[Dict[str, Any]] = None
    audio: Optional[Dict[str, Any]] = None

class ModelInfo(BaseModel):
    """Complete model information."""
    id: str = Field(description="Model ID")
    displayName: str = Field(description="Display name")
    description: str = Field(description="Model description")
    provider: str = Field(description="Provider ID")
    supportedIn: List[str] = Field(description="Supported purposes")
    capabilities: ModelCapabilities = Field(description="Model capabilities")
    limits: ModelLimits = Field(description="Token and context limits")
    pricing: ModelPricing = Field(description="Pricing information")
    tokenCalculation: Optional[ModelTokenCalculation] = Field(None, description="Token calculation rules")
    status: str = Field(description="Model status (stable, preview, experimental)")
    knowledgeCutoff: Optional[str] = Field(None, description="Knowledge cutoff date")

class ModelListResponse(BaseModel):
    """Response for listing models."""
    models: List[ModelInfo] = Field(description="List of available models")
    total: int = Field(description="Total number of models")

class CostEstimateRequest(BaseModel):
    """Request for cost estimation."""
    model_id: str = Field(description="Model ID")
    input_tokens: int = Field(ge=0, description="Number of input tokens")
    output_tokens: int = Field(ge=0, description="Number of output tokens")
    cached_tokens: int = Field(default=0, ge=0, description="Number of cached tokens")
    thinking_tokens: int = Field(default=0, ge=0, description="Number of thinking tokens")
    cache_hours: float = Field(default=0, ge=0, description="Hours of cache storage")

class CostEstimateResponse(BaseModel):
    """Response for cost estimation."""
    model_id: str = Field(description="Model ID")
    estimated_cost: float = Field(description="Total estimated cost in USD")
    breakdown: Dict[str, float] = Field(description="Cost breakdown by type")
    currency: str = Field(default="USD", description="Currency code")
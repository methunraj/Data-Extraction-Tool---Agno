# app/schemas/extraction.py
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any, Union
from enum import Enum

class ExtractionProvider(str, Enum):
    """Supported AI providers for extraction."""
    GOOGLE_AI = "googleAI"

class MediaContent(BaseModel):
    """Media content for multimodal extraction."""
    mime_type: str = Field(description="MIME type of the media")
    data: str = Field(description="Base64 encoded data or URI")
    
class Example(BaseModel):
    """Few-shot example for extraction."""
    input: str = Field(description="Example input")
    output: Union[str, Dict[str, Any]] = Field(description="Example output")

class ExtractDataRequest(BaseModel):
    """Request model for data extraction."""
    # Document input (text or file)
    document_text: Optional[str] = Field(None, description="Raw text content to extract from")
    document_file: Optional[MediaContent] = Field(None, description="Document file (PDF, image, etc)")
    
    # Schema and prompts
    schema_definition: str = Field(description="JSON schema for extraction")
    system_prompt: str = Field(description="System prompt for the AI model")
    user_prompt_template: Optional[str] = Field(None, description="User prompt template with placeholders")
    user_task_description: Optional[str] = Field(None, description="Additional user instructions")
    
    # Model configuration
    provider: ExtractionProvider = Field(default=ExtractionProvider.GOOGLE_AI, description="AI provider")
    model_name: str = Field(description="Model ID to use for extraction")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Temperature for generation")
    
    # Advanced options
    examples: Optional[List[Example]] = Field(default=[], description="Few-shot examples")
    thinking_budget: Optional[int] = Field(None, ge=-1, le=32768, description="Thinking token budget (-1 for auto)")
    use_cache: bool = Field(default=False, description="Whether to use caching")
    cache_id: Optional[str] = Field(None, description="Cache ID for reuse")
    max_retries: int = Field(default=1, ge=0, le=3, description="Maximum retry attempts")
    
    @validator('document_file')
    def validate_document_input(cls, v, values):
        """Ensure at least one document input is provided."""
        document_text = values.get('document_text')
        document_file = v
        
        if not document_text and not document_file:
            raise ValueError("Either document_text or document_file must be provided")
        return v
    
    # Removed JSON validation - let the LLM handle schema format flexibility

class TokenUsage(BaseModel):
    """Token usage information."""
    prompt_tokens: int = Field(description="Number of prompt tokens")
    completion_tokens: int = Field(description="Number of completion tokens")
    total_tokens: int = Field(description="Total tokens used")
    cached_tokens: Optional[int] = Field(0, description="Number of cached tokens")
    thinking_tokens: Optional[int] = Field(0, description="Number of thinking tokens")

class ExtractDataResponse(BaseModel):
    """Response model for data extraction."""
    extracted_json: str = Field(description="Extracted data as JSON string")
    token_usage: TokenUsage = Field(description="Token usage details")
    cost: float = Field(description="Estimated cost in USD")
    model_used: str = Field(description="Model ID that was used")
    cache_hit: bool = Field(default=False, description="Whether cache was hit")
    retry_count: int = Field(default=0, description="Number of retries performed")
    thinking_text: Optional[str] = Field(None, description="Thinking process text if available")

class EstimateTokensRequest(BaseModel):
    """Request model for token estimation."""
    document_text: Optional[str] = None
    document_file: Optional[MediaContent] = None
    schema_definition: str
    system_prompt: str
    user_task_description: Optional[str] = None
    examples: Optional[List[Example]] = []
    model_name: str

class EstimateTokensResponse(BaseModel):
    """Response model for token estimation."""
    estimated_tokens: Dict[str, int] = Field(description="Token breakdown by content type")
    total_tokens: int = Field(description="Total estimated tokens")
    estimated_cost: float = Field(description="Estimated cost in USD")
    warnings: List[str] = Field(default=[], description="Any warnings about the estimation")
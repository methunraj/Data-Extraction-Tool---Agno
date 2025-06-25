# app/services/extraction_service.py
import json
import base64
import logging
from typing import Dict, Any, Optional, List, Tuple
from google import genai
from google.genai import types
import asyncio

from ..core.google_client import GoogleGenAIClient
from ..core.exceptions import (
    ExtractionError, ModelNotFoundError, TokenLimitError,
    InvalidRequestError, APIKeyError
)
from ..schemas.extraction import (
    ExtractDataRequest, ExtractDataResponse, TokenUsage,
    EstimateTokensRequest, EstimateTokensResponse, MediaContent
)
from .model_service import ModelService
from .token_service import TokenService
from .cache_service import CacheService

logger = logging.getLogger(__name__)

class ExtractionService:
    """Service for extracting structured data from documents using AI models."""
    
    def __init__(self, model_service: ModelService, token_service: TokenService = None, cache_service: CacheService = None):
        self.model_service = model_service
        self.token_service = token_service or TokenService(model_service)
        self.cache_service = cache_service
        self.client = GoogleGenAIClient.get_client()
    
    async def extract_data(self, request: ExtractDataRequest) -> ExtractDataResponse:
        """
        Extract structured data from documents using the specified model.
        
        Args:
            request: Extraction request with document, schema, and configuration
            
        Returns:
            ExtractDataResponse with extracted data and metadata
            
        Raises:
            ModelNotFoundError: If the specified model is not found
            ExtractionError: If extraction fails
            TokenLimitError: If token limits are exceeded
        """
        # Validate model exists and supports extraction
        model_config = self.model_service.get_model(request.model_name)
        if not model_config:
            raise ModelNotFoundError(request.model_name)
        
        if not self.model_service.validate_model_for_purpose(request.model_name, "extraction"):
            raise InvalidRequestError(
                f"Model {request.model_name} does not support extraction",
                details={"supported_purposes": model_config.get("supportedIn", [])}
            )
        
        # Prepare content for generation
        contents = await self._prepare_contents(request)
        
        # Handle caching if requested
        cache_entry = None
        cached_content = None
        if request.use_cache and self.cache_service:
            # Try to use existing cache or create new one
            if request.cache_id:
                cache_entry = await self.cache_service.get_cache(request.cache_id)
            
            if not cache_entry:
                # Create cache for system prompt and schema
                cache_contents = [
                    {"role": "system", "content": request.system_prompt},
                    {"role": "user", "content": f"Schema: {request.schema_definition}"}
                ]
                
                try:
                    cache_id, cache_entry = await self.cache_service.create_cache(
                        content=cache_contents,
                        model_id=request.model_name,
                        ttl_hours=1.0,
                        cache_id=request.cache_id
                    )
                    logger.info(f"Created cache with ID: {cache_id}")
                except Exception as e:
                    logger.warning(f"Failed to create cache: {e}")
            
            # If we have a cache entry, prepare cached content
            if cache_entry and cache_entry.google_cache_name:
                cached_content = types.CachedContent(name=cache_entry.google_cache_name)
        
        # Create generation configuration
        config = self._create_generation_config(request, model_config)
        
        # Perform extraction with retries
        retry_count = 0
        last_error = None
        
        while retry_count <= request.max_retries:
            try:
                # Generate content
                if cached_content:
                    # Use cached content
                    response = await asyncio.to_thread(
                        self.client.models.generate_content,
                        model=request.model_name,
                        contents=contents,
                        config=config,
                        cached_content=cached_content
                    )
                else:
                    response = await asyncio.to_thread(
                        self.client.models.generate_content,
                        model=request.model_name,
                        contents=contents,
                        config=config
                    )
                
                # Process response
                return await self._process_response(response, request, retry_count)
                
            except Exception as e:
                import traceback
                logger.warning(f"Extraction attempt {retry_count + 1} failed: {e}")
                logger.debug(f"Full traceback: {traceback.format_exc()}")
                last_error = e
                retry_count += 1
                
                if retry_count <= request.max_retries:
                    await asyncio.sleep(2 ** retry_count)  # Exponential backoff
        
        # All retries failed
        raise ExtractionError(
            f"Extraction failed after {retry_count} attempts",
            details={"last_error": str(last_error)}
        )
    
    async def estimate_tokens(self, request: EstimateTokensRequest) -> EstimateTokensResponse:
        """Estimate token count and cost for an extraction request."""
        estimates = {}
        warnings = []
        
        # Estimate document tokens
        if request.document_text:
            estimates["document"] = self.token_service.estimate_text_tokens(request.document_text)
        elif request.document_file:
            media_estimate = await self._estimate_media_tokens(request.document_file, request.model_name)
            estimates["media"] = media_estimate["tokens"]
            if media_estimate.get("warning"):
                warnings.append(media_estimate["warning"])
        
        # Estimate schema tokens
        estimates["schema"] = self.token_service.estimate_text_tokens(request.schema_definition)
        
        # Estimate prompt tokens
        estimates["system_prompt"] = self.token_service.estimate_text_tokens(request.system_prompt)
        if request.user_task_description:
            estimates["user_task"] = self.token_service.estimate_text_tokens(request.user_task_description)
        
        # Estimate examples tokens
        if request.examples:
            examples_text = "\n".join([
                f"Input: {ex.input}\nOutput: {json.dumps(ex.output) if isinstance(ex.output, dict) else ex.output}"
                for ex in request.examples
            ])
            estimates["examples"] = self.token_service.estimate_text_tokens(examples_text)
        
        # Calculate totals
        total_tokens = sum(estimates.values())
        
        # Estimate output tokens (rough estimate based on schema complexity)
        try:
            schema_obj = json.loads(request.schema_definition)
            estimated_output = self._estimate_output_tokens(schema_obj)
        except json.JSONDecodeError:
            # If schema is not valid JSON, estimate based on length
            estimated_output = min(len(request.schema_definition) // 4, 1000)  # Rough token estimate
        estimates["estimated_output"] = estimated_output
        
        # Calculate cost
        usage = {
            "input_tokens": total_tokens,
            "output_tokens": estimated_output
        }
        estimated_cost = self.model_service.calculate_cost(request.model_name, usage)
        
        return EstimateTokensResponse(
            estimated_tokens=estimates,
            total_tokens=total_tokens + estimated_output,
            estimated_cost=estimated_cost,
            warnings=warnings
        )
    
    async def _prepare_contents(self, request: ExtractDataRequest) -> List[Dict[str, Any]]:
        """Prepare content list for generation."""
        contents = []
        
        # Add user content with document
        user_parts = []
        
        # Add document content
        if request.document_text:
            user_parts.append({"text": f"Document to extract from:\n{request.document_text}"})
        elif request.document_file:
            # Handle file upload for multimodal input
            file_data = await self._prepare_file_content(request.document_file)
            user_parts.append(file_data)
        
        # Add user task description if provided
        if request.user_task_description:
            user_parts.append({"text": f"\nTask: {request.user_task_description}"})
        
        # Add examples if provided
        if request.examples:
            examples_text = "\n\nExamples:\n"
            for i, example in enumerate(request.examples, 1):
                output_str = json.dumps(example.output) if isinstance(example.output, dict) else example.output
                examples_text += f"\nExample {i}:\nInput: {example.input}\nOutput: {output_str}\n"
            user_parts.append({"text": examples_text})
        
        contents.append({
            "role": "user",
            "parts": user_parts
        })
        
        return contents
    
    def _create_generation_config(
        self, 
        request: ExtractDataRequest, 
        model_config: Dict[str, Any]
    ) -> types.GenerateContentConfig:
        """Create generation configuration for extraction."""
        # Always use basic JSON mode and include schema in system instruction
        # This approach is more flexible and handles both JSON schemas and text descriptions
        config_dict = {
            "system_instruction": f"{request.system_prompt}\n\nPlease format your response as valid JSON according to this schema:\n{request.schema_definition}",
            "temperature": request.temperature,
            "response_mime_type": "application/json"
        }
        
        config = types.GenerateContentConfig(**config_dict)
        
        # Add thinking configuration if supported and requested
        capabilities = model_config.get("capabilities", {})
        thinking_config = capabilities.get("thinking", {})
        
        if thinking_config.get("supported") and request.thinking_budget is not None:
            config.thinking_config = types.ThinkingConfig(
                thinking_budget=request.thinking_budget
            )
        
        return config
    
    async def _process_response(
        self, 
        response: Any, 
        request: ExtractDataRequest,
        retry_count: int
    ) -> ExtractDataResponse:
        """Process the generation response."""
        # Extract text from response
        if hasattr(response, "text"):
            extracted_text = response.text
        elif hasattr(response, "candidates") and response.candidates:
            extracted_text = response.candidates[0].content.parts[0].text
        else:
            raise ExtractionError("No text content in response")
        
        # Clean up common JSON issues
        extracted_json = self._clean_json_output(extracted_text)
        
        # Validate JSON
        try:
            json.loads(extracted_json)
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON in extraction output: {e}")
            # Attempt to fix common issues
            extracted_json = self._fix_json_issues(extracted_json)
        
        # Get usage metadata
        usage = response.usage_metadata
        
        # Calculate cost with null checks
        cached_tokens = getattr(usage, "cached_content_token_count", 0) or 0
        prompt_tokens = getattr(usage, "prompt_token_count", 0) or 0
        candidates_tokens = getattr(usage, "candidates_token_count", 0) or 0
        thinking_tokens = getattr(usage, "thoughts_token_count", 0) or 0
        
        cost = self.model_service.calculate_cost(request.model_name, {
            "input_tokens": prompt_tokens,
            "output_tokens": candidates_tokens,
            "cached_tokens": cached_tokens,
            "thinking_tokens": thinking_tokens
        })
        
        # Record cache hit if applicable
        if cached_tokens > 0 and self.cache_service and request.cache_id:
            # Calculate cost savings from cache
            full_input_cost = self.model_service.calculate_cost(request.model_name, {
                "input_tokens": prompt_tokens,
                "output_tokens": 0
            })
            cached_input_cost = self.model_service.calculate_cost(request.model_name, {
                "input_tokens": prompt_tokens - cached_tokens,
                "output_tokens": 0,
                "cached_tokens": cached_tokens
            })
            cost_saved = full_input_cost - cached_input_cost
            
            await self.cache_service.record_cache_hit(
                cache_id=request.cache_id,
                tokens_saved=cached_tokens,
                cost_saved=cost_saved
            )
        
        # Build token usage
        total_tokens = getattr(usage, "total_token_count", 0) or (prompt_tokens + candidates_tokens)
        token_usage = TokenUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=candidates_tokens,
            total_tokens=total_tokens,
            cached_tokens=cached_tokens,
            thinking_tokens=thinking_tokens
        )
        
        # Get thinking text if available
        thinking_text = None
        if hasattr(response, "candidates") and response.candidates:
            candidate = response.candidates[0]
            if hasattr(candidate, "thoughts") and candidate.thoughts:
                thinking_text = "\n".join([
                    getattr(thought, "text", str(thought)) 
                    for thought in candidate.thoughts
                ])
        
        return ExtractDataResponse(
            extracted_json=extracted_json,
            token_usage=token_usage,
            cost=cost,
            model_used=request.model_name,
            cache_hit=bool(getattr(usage, "cached_content_token_count", 0)),
            retry_count=retry_count,
            thinking_text=thinking_text
        )
    
    async def _prepare_file_content(self, file: MediaContent) -> Dict[str, Any]:
        """Prepare file content for multimodal input."""
        if file.data.startswith("data:"):
            # Data URI format
            return {
                "inline_data": {
                    "mime_type": file.mime_type,
                    "data": file.data.split(",", 1)[1]  # Remove data URI prefix
                }
            }
        else:
            # Assume base64 encoded
            return {
                "inline_data": {
                    "mime_type": file.mime_type,
                    "data": file.data
                }
            }
    
    async def _estimate_media_tokens(
        self, 
        file: MediaContent, 
        model_name: str
    ) -> Dict[str, Any]:
        """Estimate tokens for media content."""
        # This is a simplified estimation
        # In production, you'd want to decode and analyze the media
        result = {"tokens": 0, "warning": None}
        
        if file.mime_type.startswith("image/"):
            # Rough estimate for images
            result["tokens"] = 258  # Base tokens for small image
            result["warning"] = "Image token estimation is approximate"
        elif file.mime_type == "application/pdf":
            # Rough estimate for PDFs
            result["tokens"] = 1000  # Assume ~4 pages
            result["warning"] = "PDF token estimation is approximate without page count"
        elif file.mime_type.startswith("video/"):
            # Rough estimate for video
            result["tokens"] = 5000  # Assume short video
            result["warning"] = "Video token estimation is approximate without duration"
        elif file.mime_type.startswith("audio/"):
            # Rough estimate for audio
            result["tokens"] = 1000  # Assume short audio
            result["warning"] = "Audio token estimation is approximate without duration"
        else:
            result["tokens"] = 500
            result["warning"] = f"Unknown media type {file.mime_type}, using default estimate"
        
        return result
    
    def _estimate_output_tokens(self, schema: Dict[str, Any]) -> int:
        """Estimate output tokens based on schema complexity."""
        # Count fields in schema
        field_count = self._count_schema_fields(schema)
        
        # Rough estimate: 50 tokens per field
        return field_count * 50
    
    def _count_schema_fields(self, schema: Dict[str, Any], max_depth: int = 10) -> int:
        """Recursively count fields in a JSON schema."""
        if max_depth <= 0:
            return 0
        
        count = 0
        
        if schema.get("type") == "object" and "properties" in schema:
            for prop_schema in schema["properties"].values():
                count += 1 + self._count_schema_fields(prop_schema, max_depth - 1)
        elif schema.get("type") == "array" and "items" in schema:
            count += 1 + self._count_schema_fields(schema["items"], max_depth - 1)
        else:
            count = 1
        
        return count
    
    def _clean_json_output(self, text: str) -> str:
        """Clean common issues in JSON output."""
        # Remove any markdown code blocks
        if "```json" in text:
            text = text.replace("```json", "").replace("```", "")
        
        # Remove any leading/trailing whitespace
        text = text.strip()
        
        # Remove any non-JSON prefixes (common with some models)
        if text.startswith("Here") or text.startswith("The"):
            # Find the first { or [
            for i, char in enumerate(text):
                if char in "{[":
                    text = text[i:]
                    break
        
        return text
    
    def _fix_json_issues(self, json_str: str) -> str:
        """Attempt to fix common JSON formatting issues."""
        # Try to fix trailing commas
        import re
        json_str = re.sub(r',\s*}', '}', json_str)
        json_str = re.sub(r',\s*]', ']', json_str)
        
        # Try to fix single quotes (replace with double quotes)
        # This is risky but sometimes necessary
        # json_str = json_str.replace("'", '"')
        
        # Validate again
        try:
            json.loads(json_str)
            return json_str
        except:
            # If still invalid, return original
            return json_str
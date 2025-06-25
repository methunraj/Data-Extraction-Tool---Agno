# app/services/generation_service.py
import json
import logging
from typing import Dict, Any, List, Optional
from google import genai
from google.genai import types

from ..core.google_client import GoogleGenAIClient
from ..core.exceptions import GenerationError, ModelNotFoundError, InvalidRequestError
from ..schemas.generation import (
    GenerateConfigRequest, GenerateConfigResponse, GeneratedExample,
    GenerateSchemaRequest, GenerateSchemaResponse,
    GeneratePromptRequest, GeneratePromptResponse,
    RefineConfigRequest, RefineConfigResponse
)
from .model_service import ModelService

logger = logging.getLogger(__name__)

class GenerationService:
    """Service for generating extraction configurations using AI models."""
    
    def __init__(self, model_service: ModelService):
        self.model_service = model_service
        self.client = GoogleGenAIClient.get_client()
    
    async def generate_unified_config(
        self, 
        request: GenerateConfigRequest
    ) -> GenerateConfigResponse:
        """
        Generate a complete extraction configuration from user intent.
        
        Args:
            request: Generation request with user intent and options
            
        Returns:
            GenerateConfigResponse with schema, prompts, and examples
        """
        # Validate model
        model_config = self._validate_model(request.model_name, "generation")
        
        # Build generation prompt
        prompt = self._build_unified_generation_prompt(request)
        
        # Create response schema
        response_schema = self._create_unified_response_schema(request)
        
        # Generate configuration
        config = types.GenerateContentConfig(
            temperature=request.temperature,
            response_mime_type="application/json",
            response_schema=response_schema
        )
        
        try:
            response = self.client.models.generate_content(
                model=request.model_name,
                contents=prompt,
                config=config
            )
            
            # Parse response
            result = json.loads(response.text)
            
            # Calculate cost
            usage = response.usage_metadata
            cost = self.model_service.calculate_cost(request.model_name, {
                "input_tokens": usage.prompt_token_count,
                "output_tokens": usage.candidates_token_count
            })
            
            # Convert examples
            examples = []
            for ex in result.get("examples", []):
                try:
                    output_json = json.loads(ex["output"])
                except json.JSONDecodeError:
                    # Handle cases where the output is not a valid JSON string
                    output_json = {"error": "Invalid JSON format", "raw": ex["output"]}
                
                examples.append(GeneratedExample(
                    input=ex["input"],
                    output=output_json
                ))
            
            return GenerateConfigResponse(
                schema=result["schema"],
                system_prompt=result["systemPrompt"],
                user_prompt_template=result["userPromptTemplate"],
                examples=examples,
                reasoning=result.get("reasoning"),
                cost=cost,
                tokens_used=usage.total_token_count
            )
            
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            raise GenerationError(f"Failed to generate configuration: {str(e)}")
    
    async def generate_schema(
        self, 
        request: GenerateSchemaRequest
    ) -> GenerateSchemaResponse:
        """Generate only a JSON schema from user intent."""
        # Validate model
        model_config = self._validate_model(request.model_name, "generation")
        
        # Build schema generation prompt
        prompt = self._build_schema_generation_prompt(request)
        
        # Create response schema
        response_schema = {
            "type": "object",
            "properties": {
                "schema": {
                    "type": "string",
                    "description": "Generated JSON schema as string"
                },
                "fieldExplanations": {
                    "type": "object",
                    "description": "Explanations for each field",
                    "additionalProperties": {"type": "string"}
                }
            },
            "required": ["schema"]
        }
        
        # Generate schema
        config = types.GenerateContentConfig(
            temperature=request.temperature,
            response_mime_type="application/json",
            response_schema=response_schema
        )
        
        try:
            response = self.client.models.generate_content(
                model=request.model_name,
                contents=prompt,
                config=config
            )
            
            result = json.loads(response.text)
            
            # Validate the generated schema
            try:
                json.loads(result["schema"])
            except json.JSONDecodeError:
                raise GenerationError("Generated schema is not valid JSON")
            
            # Calculate cost
            usage = response.usage_metadata
            cost = self.model_service.calculate_cost(request.model_name, {
                "input_tokens": usage.prompt_token_count,
                "output_tokens": usage.candidates_token_count
            })
            
            return GenerateSchemaResponse(
                schema=result["schema"],
                field_explanations=result.get("fieldExplanations"),
                cost=cost,
                tokens_used=usage.total_token_count
            )
            
        except GenerationError:
            raise
        except Exception as e:
            logger.error(f"Schema generation failed: {e}")
            raise GenerationError(f"Failed to generate schema: {str(e)}")
    
    async def generate_prompts(
        self, 
        request: GeneratePromptRequest
    ) -> GeneratePromptResponse:
        """Generate prompts for a given schema and extraction goal."""
        # Validate model
        model_config = self._validate_model(request.model_name, "generation")
        
        # Build prompt generation prompt
        prompt = self._build_prompt_generation_prompt(request)
        
        # Create response schema
        properties = {}
        required = []
        
        if request.generate_system_prompt:
            properties["systemPrompt"] = {
                "type": "string",
                "description": "Generated system prompt"
            }
            required.append("systemPrompt")
        
        if request.generate_user_template:
            properties["userPromptTemplate"] = {
                "type": "string",
                "description": "Generated user prompt template"
            }
            required.append("userPromptTemplate")
        
        properties["usageTips"] = {
            "type": "array",
            "items": {"type": "string"},
            "description": "Tips for using the prompts"
        }
        
        response_schema = {
            "type": "object",
            "properties": properties,
            "required": required
        }
        
        # Generate prompts
        config = types.GenerateContentConfig(
            temperature=request.temperature,
            response_mime_type="application/json",
            response_schema=response_schema
        )
        
        try:
            response = self.client.models.generate_content(
                model=request.model_name,
                contents=prompt,
                config=config
            )
            
            result = json.loads(response.text)
            
            # Calculate cost
            usage = response.usage_metadata
            cost = self.model_service.calculate_cost(request.model_name, {
                "input_tokens": usage.prompt_token_count,
                "output_tokens": usage.candidates_token_count
            })
            
            return GeneratePromptResponse(
                system_prompt=result.get("systemPrompt"),
                user_prompt_template=result.get("userPromptTemplate"),
                usage_tips=result.get("usageTips", []),
                cost=cost,
                tokens_used=usage.total_token_count
            )
            
        except Exception as e:
            logger.error(f"Prompt generation failed: {e}")
            raise GenerationError(f"Failed to generate prompts: {str(e)}")
    
    async def refine_config(
        self, 
        request: RefineConfigRequest
    ) -> RefineConfigResponse:
        """Refine an existing extraction configuration."""
        # Validate model
        model_config = self._validate_model(request.model_name, "generation")
        
        # Build refinement prompt
        prompt = self._build_refinement_prompt(request)
        
        # Create response schema
        response_schema = {
            "type": "object",
            "properties": {
                "refinedSchema": {
                    "type": "string",
                    "description": "Refined JSON schema"
                },
                "refinedSystemPrompt": {
                    "type": "string",
                    "description": "Refined system prompt"
                },
                "changesMade": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of changes made"
                },
                "reasoning": {
                    "type": "string",
                    "description": "Explanation of refinements"
                }
            },
            "required": ["refinedSchema", "refinedSystemPrompt", "changesMade", "reasoning"]
        }
        
        # Generate refinements
        config = types.GenerateContentConfig(
            temperature=request.temperature,
            response_mime_type="application/json",
            response_schema=response_schema
        )
        
        try:
            response = self.client.models.generate_content(
                model=request.model_name,
                contents=prompt,
                config=config
            )
            
            result = json.loads(response.text)
            
            # Validate refined schema
            try:
                json.loads(result["refinedSchema"])
            except json.JSONDecodeError:
                raise GenerationError("Refined schema is not valid JSON")
            
            # Calculate cost
            usage = response.usage_metadata
            cost = self.model_service.calculate_cost(request.model_name, {
                "input_tokens": usage.prompt_token_count,
                "output_tokens": usage.candidates_token_count
            })
            
            return RefineConfigResponse(
                refined_schema=result["refinedSchema"],
                refined_system_prompt=result["refinedSystemPrompt"],
                changes_made=result["changesMade"],
                reasoning=result["reasoning"],
                cost=cost,
                tokens_used=usage.total_token_count
            )
            
        except GenerationError:
            raise
        except Exception as e:
            logger.error(f"Configuration refinement failed: {e}")
            raise GenerationError(f"Failed to refine configuration: {str(e)}")
    
    def _validate_model(self, model_id: str, purpose: str) -> Dict[str, Any]:
        """Validate model exists and supports the purpose."""
        model_config = self.model_service.get_model(model_id)
        if not model_config:
            raise ModelNotFoundError(model_id)
        
        if not self.model_service.validate_model_for_purpose(model_id, purpose):
            raise InvalidRequestError(
                f"Model {model_id} does not support {purpose}",
                details={"supported_purposes": model_config.get("supportedIn", [])}
            )
        
        return model_config
    
    def _build_unified_generation_prompt(self, request: GenerateConfigRequest) -> str:
        """Build prompt for unified configuration generation."""
        prompt_parts = [
            "You are an expert at creating extraction configurations for structured data extraction from documents.",
            f"\nUser Intent: {request.user_intent}"
        ]
        
        if request.document_type:
            prompt_parts.append(f"\nDocument Type: {request.document_type}")
        
        if request.sample_data:
            prompt_parts.append(f"\nSample Document Content:\n{request.sample_data}")
        
        prompt_parts.append("""\nGenerate a complete extraction configuration including:
1. A JSON schema that defines the structure of data to extract
2. A system prompt that instructs the AI how to perform the extraction
3. A user prompt template with placeholders for dynamic content
4. For the 'output' field in 'examples', ensure it is a JSON object represented as a string.""")
        
        if request.include_examples:
            prompt_parts.append(f"4. {request.example_count} realistic examples showing input documents and expected output")
        
        if request.include_reasoning:
            prompt_parts.append("5. Clear reasoning explaining your design choices")
        
        prompt_parts.append("\nEnsure the schema is practical, the prompts are clear, and examples are realistic.")
        
        return "\n".join(prompt_parts)
    
    def _build_schema_generation_prompt(self, request: GenerateSchemaRequest) -> str:
        """Build prompt for schema-only generation."""
        prompt_parts = [
            "You are an expert at creating JSON schemas for data extraction.",
            f"\nCreate a JSON schema for: {request.user_intent}"
        ]
        
        if request.field_descriptions:
            prompt_parts.append("\nSpecific field requirements:")
            for field, desc in request.field_descriptions.items():
                prompt_parts.append(f"- {field}: {desc}")
        
        if request.constraints:
            prompt_parts.append("\nAdditional constraints:")
            for constraint in request.constraints:
                prompt_parts.append(f"- {constraint}")
        
        prompt_parts.append("\nGenerate a well-structured JSON schema with appropriate types, formats, and validation rules.")
        prompt_parts.append("Also provide brief explanations for each field to help users understand the schema.")
        
        return "\n".join(prompt_parts)
    
    def _build_prompt_generation_prompt(self, request: GeneratePromptRequest) -> str:
        """Build prompt for prompt generation."""
        prompt_parts = [
            "You are an expert at creating AI prompts for structured data extraction.",
            f"\nExtraction Goal: {request.extraction_goal}",
            f"\nTarget Schema:\n{request.schema}"
        ]
        
        if request.document_context:
            prompt_parts.append(f"\nDocument Context: {request.document_context}")
        
        prompt_parts.append("\nGenerate:")
        
        if request.generate_system_prompt:
            prompt_parts.append("1. A system prompt that instructs the AI how to extract data according to the schema")
        
        if request.generate_user_template:
            prompt_parts.append("2. A user prompt template with placeholders like {{document}} for dynamic content")
        
        prompt_parts.append("3. Usage tips to help users get the best results")
        
        return "\n".join(prompt_parts)
    
    def _build_refinement_prompt(self, request: RefineConfigRequest) -> str:
        """Build prompt for configuration refinement."""
        prompt_parts = [
            "You are an expert at refining extraction configurations.",
            f"\nCurrent Schema:\n{request.current_schema}",
            f"\nCurrent System Prompt:\n{request.current_system_prompt}",
            f"\nRefinement Instructions: {request.refinement_instructions}"
        ]
        
        if request.failed_examples:
            prompt_parts.append("\nExamples that failed:")
            for i, example in enumerate(request.failed_examples, 1):
                prompt_parts.append(f"\nExample {i}:")
                prompt_parts.append(json.dumps(example, indent=2))
        
        prompt_parts.append("\nRefine the configuration to address the issues while maintaining backward compatibility where possible.")
        prompt_parts.append("Clearly list all changes made and explain your reasoning.")
        
        return "\n".join(prompt_parts)
    
    def _create_unified_response_schema(self, request: GenerateConfigRequest) -> Dict[str, Any]:
        """Create response schema for unified generation."""
        properties = {
            "schema": {
                "type": "string",
                "description": "JSON schema as string"
            },
            "systemPrompt": {
                "type": "string",
                "description": "System prompt for extraction"
            },
            "userPromptTemplate": {
                "type": "string",
                "description": "User prompt template with placeholders"
            }
        }
        
        required = ["schema", "systemPrompt", "userPromptTemplate"]
        
        if request.include_examples:
            properties["examples"] = {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "input": {"type": "string"},
                        "output": {
                            "type": "string",
                            "description": "JSON object represented as a string"
                        }
                    },
                    "required": ["input", "output"]
                },
                "minItems": request.example_count,
                "maxItems": request.example_count
            }
            required.append("examples")
        
        if request.include_reasoning:
            properties["reasoning"] = {
                "type": "string",
                "description": "Explanation of design choices"
            }
            required.append("reasoning")
        
        return {
            "type": "object",
            "properties": properties,
            "required": required
        }
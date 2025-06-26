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

# app/services/generation_service.py
import json
import logging
from typing import Dict, Any

from ..core.exceptions import GenerationError
from ..schemas.generation import (
    GenerateConfigRequest, GenerateConfigResponse,
    GenerateSchemaRequest, GenerateSchemaResponse,
    GeneratePromptRequest, GeneratePromptResponse,
    RefineConfigRequest, RefineConfigResponse,
    GeneratedExample
)
from .model_service import ModelService
from ..agents.prompt_engineer.prompt_engineer import PromptEngineerAgent
from ..agents.factory import create_agent

logger = logging.getLogger(__name__)

class GenerationService:
    def __init__(self, model_service: ModelService):
        self.model_service = model_service
        # No longer need direct Google client
        
    async def generate_unified_config(self, request: GenerateConfigRequest) -> GenerateConfigResponse:
        """Generate complete extraction configuration using Prompt Engineer Agent."""
        
        logger.info(f"Generation request received with model_name: {request.model_name}")
        agent: PromptEngineerAgent = create_agent("prompt_engineer", model_id=request.model_name)
        
        generation_prompt = f"""
        Create a complete extraction configuration for the following request:
        
        User Intent: {request.user_intent}
        Document Type: {request.document_type or "general"}
        Sample Data: {request.sample_data or "not provided"}
        
        Generate:
        1. A JSON schema that captures the required data structure.
        2. A system prompt for the extraction model that is comprehensive and instructs the AI to extract data thoroughly.
        3. A user prompt template with placeholders: {{{{document_text}}}} for document content and {{{{schema}}}} for the schema.
        4. {request.example_count} realistic examples if requested.
        5. A brief reasoning for your design choices.
        
        Requirements for the system prompt:
        - Must be detailed and comprehensive
        - Should instruct the AI to analyze EVERY page and section
        - Should handle multiple languages
        - Should be specific about output format requirements
        - Should include instructions for handling missing data
        - Should specify to include page numbers and locations where data was found
        
        Requirements for user prompt template:
        - Must include {{{{document_text}}}} placeholder where the actual document will be inserted
        - Must include {{{{schema}}}} placeholder where the JSON schema will be inserted
        - Should be clear and concise
        - Should specify the exact output format expected
        
        Return ONLY a single JSON object with keys: "schema", "system_prompt", "user_prompt_template", "examples", "reasoning".
        The 'schema' value should be a JSON string.
        The 'examples' value should be an array of objects, each with "input" and "output" keys. The "output" should be a JSON string.
        
        IMPORTANT: Return ONLY the JSON object without any markdown formatting, code blocks, or additional text.
        """
        
        response = await agent.arun(generation_prompt)
        result = self._parse_agent_response(response.content)
        cost = self._calculate_agent_cost(request.model_name, response)
        
        # Process examples to handle JSON string outputs
        processed_examples = []
        for ex in result.get("examples", []):
            try:
                # If output is a JSON string, parse it to a dict
                if isinstance(ex.get("output"), str):
                    ex["output"] = json.loads(ex["output"])
                processed_examples.append(GeneratedExample(**ex))
            except (json.JSONDecodeError, TypeError) as e:
                logger.warning(f"Failed to parse example output as JSON: {e}")
                # Keep as string if parsing fails
                processed_examples.append(GeneratedExample(**ex))
        
        return GenerateConfigResponse(
            schema=result.get("schema", "{}"),
            system_prompt=result.get("system_prompt", ""),
            user_prompt_template=result.get("user_prompt_template", ""),
            examples=processed_examples,
            reasoning=result.get("reasoning"),
            cost=cost,
            tokens_used=0  # Agno agents don't provide token usage
        )

    async def generate_schema(self, request: GenerateSchemaRequest) -> GenerateSchemaResponse:
        """Generate a JSON schema using the Prompt Engineer Agent."""
        agent: PromptEngineerAgent = create_agent("prompt_engineer", model_id=request.model_name)

        prompt = f"""
        Generate a JSON schema based on the following user intent:
        User Intent: {request.user_intent}
        
        Include field explanations.
        Return a single JSON object with keys: "schema", "field_explanations".
        The 'schema' value should be a JSON string.
        """
        
        response = await agent.arun(prompt)
        result = self._parse_agent_response(response.content)
        cost = self._calculate_agent_cost(request.model_name, response)

        return GenerateSchemaResponse(
            schema=result.get("schema", "{}"),
            field_explanations=result.get("field_explanations", {}),
            cost=cost,
            tokens_used=0  # Agno agents don't provide token usage,
        )

    async def generate_prompts(self, request: GeneratePromptRequest) -> GeneratePromptResponse:
        """Generate prompts using the Prompt Engineer Agent."""
        agent: PromptEngineerAgent = create_agent("prompt_engineer", model_id=request.model_name)

        prompt = f"""
        Generate prompts for the following extraction goal and schema:
        Extraction Goal: {request.extraction_goal}
        Schema: {request.schema}

        Generate a system prompt and a user prompt template.
        Return a single JSON object with keys: "system_prompt", "user_prompt_template".
        """

        response = await agent.arun(prompt)
        result = self._parse_agent_response(response.content)
        cost = self._calculate_agent_cost(request.model_name, response)

        return GeneratePromptResponse(
            system_prompt=result.get("system_prompt", ""),
            user_prompt_template=result.get("user_prompt_template", ""),
            usage_tips=[], # This can be added to the agent's capabilities later
            cost=cost,
            tokens_used=0  # Agno agents don't provide token usage,
        )
        
    def _parse_agent_response(self, content: str) -> Dict[str, Any]:
        """Safely parse the JSON response from the agent with robust error handling."""
        # Try multiple parsing strategies
        for attempt in range(3):
            try:
                # Log the raw content for debugging
                if attempt == 0:
                    logger.debug(f"Raw agent response content: {content[:500]}...")
                
                # Clean up the content
                cleaned_content = content.strip()
                
                # Handle markdown code blocks
                if cleaned_content.startswith("```json"):
                    cleaned_content = cleaned_content[7:]
                    if cleaned_content.endswith("```"):
                        cleaned_content = cleaned_content[:-3]
                elif cleaned_content.startswith("```"):
                    # Handle generic code blocks
                    first_newline = cleaned_content.find('\n')
                    if first_newline != -1:
                        cleaned_content = cleaned_content[first_newline + 1:]
                    if cleaned_content.endswith("```"):
                        cleaned_content = cleaned_content[:-3]
                
                cleaned_content = cleaned_content.strip()
                
                # If content is empty after cleaning, log error
                if not cleaned_content:
                    logger.error("Content is empty after markdown cleanup")
                    raise GenerationError("Agent returned empty content after parsing")
                
                # Handle case where agent returns partial JSON (starting with a field)
                if not cleaned_content.startswith('{'):
                    logger.warning(f"Content doesn't start with '{{', attempting to extract JSON object")
                    # Look for the first '{' and last '}' to extract the JSON object
                    start_idx = cleaned_content.find('{')
                    end_idx = cleaned_content.rfind('}')
                    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                        cleaned_content = cleaned_content[start_idx:end_idx+1]
                        logger.info(f"Extracted JSON from position {start_idx} to {end_idx}")
                    else:
                        logger.error("Could not find valid JSON object boundaries")
                        raise GenerationError(f"Agent response doesn't contain valid JSON: {cleaned_content[:200]}...")
                
                # Apply escape sequence fixes based on attempt
                if attempt == 1:
                    # Fix common escape sequence issues
                    logger.info("Attempt 2: Fixing escape sequences")
                    cleaned_content = self._fix_escape_sequences(cleaned_content)
                elif attempt == 2:
                    # More aggressive JSON repair
                    logger.info("Attempt 3: Aggressive JSON repair")
                    cleaned_content = self._repair_json_aggressively(cleaned_content)
                
                # Try to parse JSON
                return json.loads(cleaned_content)
                
            except json.JSONDecodeError as e:
                logger.warning(f"JSON parsing attempt {attempt + 1} failed: {e}")
                if attempt == 2:  # Last attempt
                    logger.error(f"All JSON parsing attempts failed")
                    logger.error(f"Final cleaned content: {cleaned_content[:1000]}...")
                    # Try to extract and return partial JSON as fallback
                    fallback_result = self._extract_partial_json(cleaned_content)
                    if fallback_result:
                        logger.warning("Using fallback partial JSON extraction")
                        return fallback_result
                    raise GenerationError(f"Agent returned invalid JSON after all repair attempts: {str(e)}")
                continue
            except Exception as e:
                logger.error(f"An unexpected error occurred while parsing agent response: {e}")
                raise GenerationError(f"Could not process agent response: {str(e)}")
    
    def _fix_escape_sequences(self, content: str) -> str:
        """Fix common escape sequence issues in JSON strings."""
        import re
        
        # Fix invalid escape sequences like \w, \s, \d, etc.
        # These are common in regex patterns that appear in JSON
        invalid_escapes = [
            (r'\\w', r'\\\\w'),  # \w -> \\w
            (r'\\s', r'\\\\s'),  # \s -> \\s
            (r'\\d', r'\\\\d'),  # \d -> \\d
            (r'\\W', r'\\\\W'),  # \W -> \\W
            (r'\\S', r'\\\\S'),  # \S -> \\S
            (r'\\D', r'\\\\D'),  # \D -> \\D
            (r'\\A', r'\\\\A'),  # \A -> \\A
            (r'\\Z', r'\\\\Z'),  # \Z -> \\Z
            (r'\\b', r'\\\\b'),  # \b -> \\b (word boundary in regex)
            (r'\\B', r'\\\\B'),  # \B -> \\B
        ]
        
        fixed_content = content
        for invalid, valid in invalid_escapes:
            # Only fix if it's not already properly escaped
            fixed_content = re.sub(invalid, valid, fixed_content)
        
        # Fix standalone backslashes that aren't valid JSON escapes
        # This is more complex and should be done carefully
        fixed_content = re.sub(r'\\(?!["\\/bfnrt]|u[0-9a-fA-F]{4})', r'\\\\', fixed_content)
        
        return fixed_content
    
    def _repair_json_aggressively(self, content: str) -> str:
        """More aggressive JSON repair for severely malformed JSON."""
        import re
        
        # Remove any non-printable characters
        content = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', content)
        
        # Fix unescaped quotes in strings (very basic approach)
        # This is risky and might break valid JSON, so only used as last resort
        content = re.sub(r'(?<!\\)"(?![,\]\}:])', r'\\"', content)
        
        # Remove any trailing commas
        content = re.sub(r',(\s*[}\]])', r'\1', content)
        
        # Try to balance braces and brackets
        open_braces = content.count('{')
        close_braces = content.count('}')
        if open_braces > close_braces:
            content += '}' * (open_braces - close_braces)
        
        return content
    
    def _extract_partial_json(self, content: str) -> Optional[Dict[str, Any]]:
        """Extract valid JSON from partial or malformed content as fallback."""
        try:
            # Try to extract key-value pairs manually
            import re
            
            # Find potential JSON fields
            fields = {}
            
            # Extract schema field
            schema_match = re.search(r'"schema"\s*:\s*"([^"]+)"', content)
            if schema_match:
                fields["schema"] = schema_match.group(1)
            
            # Extract system_prompt field
            system_prompt_match = re.search(r'"system_prompt"\s*:\s*"([^"]+)"', content)
            if system_prompt_match:
                fields["system_prompt"] = system_prompt_match.group(1)
            
            # Extract user_prompt_template field
            user_prompt_match = re.search(r'"user_prompt_template"\s*:\s*"([^"]+)"', content)
            if user_prompt_match:
                fields["user_prompt_template"] = user_prompt_match.group(1)
            
            # If we extracted some fields, return them
            if fields:
                logger.info(f"Extracted {len(fields)} fields from malformed JSON")
                return fields
                
        except Exception as e:
            logger.warning(f"Partial JSON extraction failed: {e}")
        
        return None

    def _calculate_agent_cost(self, model_id: str, agent_response: Any) -> float:
        """Calculate the cost of an agent run."""
        # Agno agent responses don't have usage metadata like Google API responses
        # For now, return 0 cost since we can't track tokens from Agno agents
        # TODO: Implement token tracking for Agno agents if needed
        return 0.0

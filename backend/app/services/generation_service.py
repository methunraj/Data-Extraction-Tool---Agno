# app/services/generation_service.py
import json
import logging
from typing import Dict, Any, List, Optional
from google import genai
from google.genai import types

from ..core.google_client import GoogleGenAIClient
from ..core.exceptions import GenerationError, ModelNotFoundError, InvalidRequestError
# Removed problematic JSON corrector agent
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
        
    async def generate_unified_config(self, request: GenerateConfigRequest) -> GenerateConfigResponse:
        """Generate complete extraction configuration using Prompt Engineer Agent."""
        
        logger.info(f"Generation request received with model_name: {request.model_name}")
        agent: PromptEngineerAgent = create_agent("prompt_engineer", model_id=request.model_name)
        
        generation_prompt = f"""🎯 TASK: Create a professional data extraction configuration for high-precision document analysis.

📝 REQUEST DETAILS:
User Intent: {request.user_intent}
Document Type: {request.document_type or "general"}
Sample Data: {request.sample_data or "not provided"}
Examples Required: {max(2, request.example_count)}

🔧 GENERATE THESE COMPONENTS:

1️⃣ **JSON SCHEMA**: Design a comprehensive, nested schema that:
   - Captures ALL relevant data fields from the user intent
   - Uses proper JSON Schema validation (types, formats, patterns)
   - Includes detailed field descriptions
   - Handles optional vs required fields intelligently
   - Supports arrays for repeating data
   - Includes metadata fields (page_number, confidence, location)

2️⃣ **SYSTEM PROMPT**: Create an expert-level system prompt that:
   - Establishes AI as a forensic-level data extraction specialist
   - Mandates analysis of EVERY page, section, table, chart, and appendix
   - Handles multilingual documents with translation requirements
   - Specifies exact JSON output format adherence
   - Includes advanced error handling for missing/corrupted data
   - Demands source attribution (page numbers, locations, context)
   - Emphasizes accuracy over speed
   - Includes validation requirements before output

3️⃣ **USER PROMPT TEMPLATE**: Design a precise template that:
   - Uses {{{{document_text}}}} and {{{{schema}}}} placeholders correctly
   - Provides clear instructions for JSON-only output
   - Includes validation reminders
   - Specifies handling of edge cases

4️⃣ **REALISTIC EXAMPLES**: Generate {max(2, request.example_count)} complete examples with:
   - Realistic input text samples relevant to the user intent
   - Complete JSON outputs that follow the schema exactly
   - Diverse scenarios (complete data, partial data, edge cases)
   - Professional, business-realistic content

5️⃣ **DESIGN REASONING**: Explain schema design choices, prompt strategies, and extraction approach.

🚨 CRITICAL REQUIREMENTS:
- Output MUST be valid JSON starting with {{ and ending with }}
- ABSOLUTELY NO markdown blocks, code fences, or formatting
- NO explanations, descriptions, or additional text outside JSON  
- Escape all quotes and special characters properly
- Ensure examples array is never empty
- All JSON strings must be properly escaped
- Schema must be a valid JSON string (not object)
- Return ONLY the JSON object - nothing before or after
- DO NOT wrap in ```json``` or any code blocks

🏗️ EXACT OUTPUT STRUCTURE:
{{
    "schema": "ESCAPED_JSON_SCHEMA_STRING",
    "system_prompt": "COMPREHENSIVE_SYSTEM_PROMPT_TEXT",
    "user_prompt_template": "PRECISE_USER_TEMPLATE_TEXT",
    "examples": [
        {{
            "input": "Realistic document text sample...",
            "output": "Valid JSON matching schema"
        }},
        {{
            "input": "Another realistic example...",
            "output": "Another valid JSON output"
        }}
    ],
    "reasoning": "Detailed explanation of design choices"
}}

✅ VALIDATION CHECKLIST:
- Valid JSON syntax with balanced braces
- Schema as escaped JSON string
- Examples array populated with realistic data
- All quotes properly escaped
- No trailing commas"""
        
        response = await agent.arun(generation_prompt)
        
        # Check if response.content is a structured Pydantic model instance
        from pydantic import BaseModel
        if isinstance(response.content, BaseModel):
            # Handle structured output from Pydantic model
            structured_data = response.content
            # Convert Pydantic model to dict for processing
            result = structured_data.model_dump()
            
            # Convert examples from Pydantic objects to dicts if needed
            if "examples" in result and result["examples"]:
                processed_examples = []
                for ex in result["examples"]:
                    if isinstance(ex, BaseModel):
                        processed_examples.append(ex.model_dump())
                    else:
                        processed_examples.append(ex)
                result["examples"] = processed_examples
            
            logger.info(f"Successfully received structured output from agent: {type(structured_data).__name__}")
        else:
            # Fallback to parsing content as string (old behavior)
            logger.info("Received string response, parsing as JSON")
            result = await self._parse_agent_response(str(response.content))
        
        cost = self._calculate_agent_cost(request.model_name, response)
        
        # Fix schema field if it's returned as dict instead of string
        if isinstance(result.get("schema"), dict):
            result["schema"] = json.dumps(result["schema"])
        
        # Process examples to handle JSON string outputs
        processed_examples = []
        examples_data = result.get("examples", [])
        
        # Get schema first before processing examples
        schema = result.get("schema", "{}")
        if not schema or schema == "{}":
            # Provide a basic schema as fallback
            schema = '{"type": "object", "properties": {}, "required": []}'
        
        if not examples_data:
            # Generate fallback examples based on user intent
            logger.info("No examples in result, generating fallback examples")
            examples_data = self._generate_fallback_examples(request.user_intent, schema)
        
        for i, ex in enumerate(examples_data):
            try:
                # Ensure we have the right structure
                example_input = ex.get("input", "")
                example_output = ex.get("output", {})
                
                # If output is a JSON string, try to parse it to a dict
                if isinstance(example_output, str):
                    # Try to clean up common JSON issues first
                    cleaned_output = example_output.strip()
                    
                    # Try parsing the JSON
                    try:
                        parsed_output = json.loads(cleaned_output)
                        example_output = parsed_output
                    except json.JSONDecodeError as json_error:
                        logger.warning(f"Failed to parse example {i+1} output as JSON: {json_error}")
                        logger.debug(f"Problematic JSON string (first 500 chars): {cleaned_output[:500]}...")
                        
                        # Try to fix common JSON issues and retry
                        try:
                            # Remove trailing commas
                            fixed_json = self._fix_common_json_issues(cleaned_output)
                            parsed_output = json.loads(fixed_json)
                            example_output = parsed_output
                            logger.info(f"Successfully parsed example {i+1} output after JSON cleanup")
                        except json.JSONDecodeError:
                            # Create a fallback simple output structure
                            example_output = {
                                "company_name": "Example Corporation",
                                "extracted_data": "Fallback example - original JSON was malformed",
                                "note": "This is a simplified example due to JSON parsing issues"
                            }
                
                # Ensure output is a dictionary
                if not isinstance(example_output, dict):
                    example_output = {"data": str(example_output)}
                
                processed_examples.append(GeneratedExample(
                    input=example_input,
                    output=example_output
                ))
                
            except Exception as e:
                logger.error(f"Failed to process example {i+1}: {e}")
                # Create a basic fallback example
                processed_examples.append(GeneratedExample(
                    input=ex.get("input", "Sample input text"),
                    output={"error": f"Failed to process example: {str(e)}"}
                ))
        
        # Schema was already processed above
            
        system_prompt = result.get("system_prompt", "")
        if not system_prompt:
            system_prompt = "🔬 You are a forensic-level data extraction specialist with expertise in document analysis. Your mission: Extract ALL requested information with surgical precision.\n\n📋 CORE DIRECTIVES:\n• Analyze EVERY page, section, table, chart, footnote, and appendix\n• Extract data in ANY language, translating key terms to English\n• Maintain 100% accuracy - verify all data points\n• Include source attribution: page numbers, locations, context\n• Handle missing data by using null values\n• Output ONLY valid JSON conforming to the provided schema\n\n⚡ QUALITY STANDARDS:\n• Cross-reference data across multiple sources within the document\n• Validate numerical values and formats\n• Preserve original terminology in quotes when relevant\n• Flag any inconsistencies or anomalies found\n\n🎯 OUTPUT REQUIREMENTS:\n• Single valid JSON object only\n• No explanations or additional text\n• Proper escaping of all special characters\n• Include metadata: page_number, location, confidence_level"
            
        user_prompt_template = result.get("user_prompt_template", "")
        if not user_prompt_template:
            user_prompt_template = "📄 DOCUMENT ANALYSIS TASK\n\n🎯 Extract data according to this JSON schema:\n{{schema}}\n\n📝 Document content:\n{{document_text}}\n\n🚨 REQUIREMENTS:\n- Return ONLY valid JSON matching the schema\n- Include page numbers and locations where data was found\n- Use null for missing data\n- Ensure proper JSON formatting"

        return GenerateConfigResponse(
            schema=schema,
            system_prompt=system_prompt,
            user_prompt_template=user_prompt_template,
            examples=processed_examples,
            reasoning=result.get("reasoning", "AI generation completed with basic configuration."),
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
        result = await self._parse_agent_response(response.content)
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
        
        CRITICAL OUTPUT REQUIREMENTS:
        1. Return ONLY a single valid JSON object
        2. No markdown code blocks, no explanations, no additional text
        3. Start with {{ and end with }}
        4. Use proper JSON syntax with double quotes
        5. Escape quotes inside strings with backslashes
        6. No trailing commas
        
        Required JSON structure:
        {{
            "system_prompt": "DETAILED_SYSTEM_PROMPT_HERE",
            "user_prompt_template": "USER_TEMPLATE_WITH_PLACEHOLDERS_HERE"
        }}
        """

        response = await agent.arun(prompt)
        result = await self._parse_agent_response(response.content)
        cost = self._calculate_agent_cost(request.model_name, response)

        return GeneratePromptResponse(
            system_prompt=result.get("system_prompt", ""),
            user_prompt_template=result.get("user_prompt_template", ""),
            usage_tips=[], # This can be added to the agent's capabilities later
            cost=cost,
            tokens_used=0  # Agno agents don't provide token usage,
        )
        
    async def _parse_agent_response(self, content: str) -> Dict[str, Any]:
        """Safely parse the JSON response from the agent with robust error handling."""
        # Try multiple parsing strategies
        for attempt in range(3):
            try:
                # Log the raw content for debugging
                if attempt == 0:
                    logger.debug(f"Raw agent response content: {content[:500]}...")
                    logger.debug(f"Full raw content length: {len(content)}")
                
                # Clean up the content
                cleaned_content = content.strip()
                logger.debug(f"Content after initial strip: '{cleaned_content[:200]}...' (length: {len(cleaned_content)})")
                
                # Handle markdown code blocks more robustly - fix the order
                if cleaned_content.startswith("```json"):
                    logger.debug("Removing ```json markdown")
                    cleaned_content = cleaned_content[7:].strip()
                    if cleaned_content.endswith("```"):
                        cleaned_content = cleaned_content[:-3].strip()
                elif cleaned_content.startswith("```"):
                    logger.debug("Removing generic ``` markdown")
                    # Handle generic code blocks
                    first_newline = cleaned_content.find('\n')
                    if first_newline != -1:
                        cleaned_content = cleaned_content[first_newline + 1:].strip()
                    if cleaned_content.endswith("```"):
                        cleaned_content = cleaned_content[:-3].strip()
                
                # Also handle cases where there might be extra text before/after JSON
                # Look for JSON object boundaries if no markdown was found
                if not cleaned_content.startswith('{') and '{' in cleaned_content:
                    logger.debug("Looking for JSON boundaries in content")
                    start_idx = cleaned_content.find('{')
                    end_idx = cleaned_content.rfind('}')
                    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                        extracted = cleaned_content[start_idx:end_idx+1]
                        logger.debug(f"Extracted JSON from position {start_idx} to {end_idx}")
                        cleaned_content = extracted
                
                cleaned_content = cleaned_content.strip()
                logger.debug(f"Content after markdown cleanup: '{cleaned_content[:200]}...' (length: {len(cleaned_content)})")
                
                # If content is empty after cleaning, return basic fallback
                if not cleaned_content:
                    logger.error("Content is empty after markdown cleanup")
                    logger.error(f"Original content was: '{content}'")
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
                
                # Clean up malformed JSON structure - fix spacing and formatting issues
                cleaned_content = self._clean_malformed_json(cleaned_content)
                
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
                    
                    # Try to extract and return partial JSON as final fallback
                    fallback_result = self._extract_partial_json(cleaned_content)
                    if fallback_result:
                        logger.warning("Using fallback partial JSON extraction")
                        return fallback_result
                    
                    # Final fallback: return empty structure for the service to handle
                    logger.error("All parsing attempts failed, returning empty structure")
                    return {
                        "schema": '{"type": "object", "properties": {}, "required": []}',
                        "system_prompt": "",
                        "user_prompt_template": "",
                        "examples": [
                            {
                                "input": "Sample document text to extract data from...",
                                "output": {"extracted_data": "Sample output"}
                            }
                        ],
                        "reasoning": "Agent response parsing failed. Using fallback configuration with basic examples."
                    }
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
    
    def _clean_malformed_json(self, content: str) -> str:
        """Clean up malformed JSON structure with spacing and formatting issues."""
        import re
        
        # Fix the specific issue where there are extra spaces before quotes
        # Pattern: {      "key": -> {"key":
        content = re.sub(r'{\s+\"', r'{"', content)
        
        # Fix spaces before colons and commas
        content = re.sub(r'\s+\":', r'":', content)
        content = re.sub(r'\s+,', r',', content)
        
        # Fix multiple spaces between elements
        content = re.sub(r'\s{2,}', r' ', content)
        
        # Ensure proper spacing after colons and commas
        content = re.sub(r':\s*(["\{\[])', r': \1', content)
        content = re.sub(r',\s*(["\{\[])', r', \1', content)
        
        return content.strip()
    
    def _repair_json_aggressively(self, content: str) -> str:
        """More aggressive JSON repair for severely malformed JSON."""
        import re
        
        # Remove any non-printable characters
        content = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', content)
        
        # Remove any remaining markdown artifacts
        content = re.sub(r'```json\s*', '', content)
        content = re.sub(r'```\s*$', '', content)
        content = re.sub(r'^```[a-zA-Z]*\s*', '', content)
        
        # Apply the malformed JSON cleaning first
        content = self._clean_malformed_json(content)
        
        # Remove any trailing commas before closing braces/brackets
        content = re.sub(r',(\s*[}\]])', r'\1', content)
        
        # Fix common escape sequence issues more aggressively
        # Fix invalid escape sequences in JSON strings
        content = re.sub(r'\\([^"\\\/bfnrt])', r'\\\\\\1', content)
        
        # Try to balance braces and brackets
        open_braces = content.count('{')
        close_braces = content.count('}')
        if open_braces > close_braces:
            content += '}' * (open_braces - close_braces)
        elif close_braces > open_braces:
            # Remove extra closing braces from the end
            extra_braces = close_braces - open_braces
            for _ in range(extra_braces):
                content = content.rstrip('}').rstrip()
        
        # Handle the specific case where we have nested JSON strings
        # Look for patterns like "output": "{ ... }" and try to parse the inner JSON
        output_match = re.search(r'"output":\s*"(\{.*\})"', content, re.DOTALL)
        if output_match:
            inner_json = output_match.group(1)
            # Unescape the inner JSON
            inner_json = inner_json.replace('\\"', '"').replace('\\n', '\n').replace('\\t', '\t')
            # Replace the escaped JSON with the unescaped version
            content = content.replace(output_match.group(0), f'"output": {inner_json}')
        
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

    def _fix_common_json_issues(self, json_string: str) -> str:
        """Fix common JSON syntax issues."""
        import re
        
        # Remove trailing commas before closing braces/brackets
        fixed = re.sub(r',(\s*[}\]])', r'\1', json_string)
        
        # Fix unescaped quotes in string values (basic attempt)
        # This is a simple fix - more complex cases may still fail
        fixed = re.sub(r'(?<!\\)"(?=(?:[^"\\]|\\.)+")', '\\"', fixed)
        
        # Remove any extra commas at the end
        fixed = re.sub(r',\s*$', '', fixed.strip())
        
        # Ensure the JSON is properly closed
        open_braces = fixed.count('{')
        close_braces = fixed.count('}')
        if open_braces > close_braces:
            fixed += '}' * (open_braces - close_braces)
        
        return fixed

    def _generate_fallback_examples(self, user_intent: str, schema: str) -> List[Dict[str, Any]]:
        """Generate fallback examples when AI fails to provide them."""
        try:
            # Parse the schema to understand the structure
            if isinstance(schema, str):
                schema_obj = json.loads(schema)
            else:
                schema_obj = schema
            
            examples = []
            
            # Generate basic examples based on common patterns
            if "company" in user_intent.lower() or "business" in user_intent.lower():
                examples.extend([
                    {
                        "input": "ACME Corporation is a leading technology company founded in 1995. Our headquarters are located at 123 Tech Street, San Francisco, CA 94105. For inquiries, contact us at info@acme.com or call (555) 123-4567. Visit our website at www.acme.com.",
                        "output": {"company_name": "ACME Corporation", "headquarters": "123 Tech Street, San Francisco, CA 94105", "email": "info@acme.com", "phone": "(555) 123-4567", "website": "www.acme.com"}
                    },
                    {
                        "input": "Global Industries Ltd. Annual Report 2023. Revenue: $2.5 billion. Net Income: $180 million. Employees: 12,000 worldwide.",
                        "output": {"company_name": "Global Industries Ltd.", "revenue": "$2.5 billion", "net_income": "$180 million", "employees": 12000}
                    }
                ])
            elif "financial" in user_intent.lower() or "revenue" in user_intent.lower():
                examples.extend([
                    {
                        "input": "Q4 2023 Financial Results: Total Revenue $1.2B (up 15% YoY), Gross Profit $480M, Operating Income $156M, Net Income $98M. EPS: $2.45.",
                        "output": {"revenue": 1200000000, "gross_profit": 480000000, "operating_income": 156000000, "net_income": 98000000, "eps": 2.45}
                    },
                    {
                        "input": "Balance Sheet Summary: Total Assets $5.8B, Total Liabilities $2.1B, Shareholders' Equity $3.7B. Cash and Equivalents $890M.",
                        "output": {"total_assets": 5800000000, "total_liabilities": 2100000000, "shareholders_equity": 3700000000, "cash": 890000000}
                    }
                ])
            else:
                # Generic examples
                examples.extend([
                    {
                        "input": "Sample document text containing the information you're looking for...",
                        "output": {"extracted_data": "Sample extracted information", "confidence": 0.85}
                    },
                    {
                        "input": "Another example document with different data points...", 
                        "output": {"extracted_data": "Different extracted information", "confidence": 0.92}
                    }
                ])
            
            return examples[:2]  # Return max 2 examples
            
        except Exception as e:
            logger.warning(f"Failed to generate fallback examples: {e}")
            return [
                {
                    "input": "Example document text...",
                    "output": {"data": "extracted information"}
                }
            ]

    def _calculate_agent_cost(self, model_id: str, agent_response: Any) -> float:
        """Calculate the cost of an agent run."""
        # Agno agent responses don't have usage metadata like Google API responses
        # For now, return 0 cost since we can't track tokens from Agno agents
        # TODO: Implement token tracking for Agno agents if needed
        return 0.0

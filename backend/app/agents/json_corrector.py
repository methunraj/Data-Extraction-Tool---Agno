# backend/app/agents/json_corrector.py
import json
import re
from typing import Dict, Any, Optional
from .base import BaseAgent
from agno.tools import tool
import logging

logger = logging.getLogger(__name__)

class JSONCorrectorAgent(BaseAgent):
    """Agent specialized in correcting malformed JSON responses."""
    
    def __init__(self, model_id=None):
        super().__init__("json_corrector", model_id=model_id)
        
    def get_instructions(self) -> list:
        return [
            "You are a JSON correction specialist. Your ONLY job is to fix malformed JSON.",
            "You receive malformed JSON text and must return ONLY valid, properly formatted JSON.",
            "CRITICAL RULES:",
            "1. Return ONLY the corrected JSON object - no explanations, no markdown, no code blocks",
            "2. Preserve all original data and structure - only fix formatting issues",
            "3. Fix common issues: missing quotes, extra spaces, unescaped characters, trailing commas",
            "4. Ensure proper JSON syntax: balanced braces, proper string escaping, valid structure",
            "5. If the input contains nested JSON strings, properly unescape them",
            "6. Your response must start with '{' and end with '}' - nothing else",
            "7. Test your output mentally to ensure it's valid JSON before responding"
        ]
    
    def get_tools(self) -> list:
        return [
            validate_json_syntax,
            fix_common_json_errors,
            extract_json_from_text
        ]

    async def correct_malformed_json(self, malformed_json: str) -> str:
        """Correct malformed JSON using the agent."""
        correction_prompt = f"""
Fix this malformed JSON and return ONLY the corrected JSON object:

{malformed_json}

IMPORTANT: 
- Return ONLY valid JSON starting with {{ and ending with }}
- No explanations, no markdown, no code blocks
- Preserve all original data, only fix syntax errors
- Ensure proper escaping of quotes and special characters
"""
        
        try:
            response = await self.agent.arun(correction_prompt)
            corrected_json = response.content.strip()
            
            # Validate the corrected JSON
            try:
                json.loads(corrected_json)
                return corrected_json
            except json.JSONDecodeError:
                logger.error("Agent failed to produce valid JSON")
                # Fallback to manual correction
                return self._manual_json_correction(malformed_json)
                
        except Exception as e:
            logger.error(f"JSON correction agent failed: {e}")
            return self._manual_json_correction(malformed_json)

    def _manual_json_correction(self, malformed_json: str) -> str:
        """Manual JSON correction as fallback."""
        try:
            # Apply basic fixes
            corrected = fix_common_json_errors(malformed_json)
            
            # Try to extract JSON if it's embedded in text
            if not corrected.strip().startswith('{'):
                extracted = extract_json_from_text(corrected)
                if extracted:
                    corrected = extracted
            
            # Validate
            json.loads(corrected)
            return corrected
            
        except Exception as e:
            logger.error(f"Manual JSON correction failed: {e}")
            # Return a minimal valid JSON as last resort
            return '{"error": "Failed to correct malformed JSON", "original": "' + malformed_json.replace('"', '\\"')[:100] + '"}'

# Define tools as module-level functions
@tool
def validate_json_syntax(json_text: str) -> Dict[str, Any]:
    """Validate if a JSON string is syntactically correct."""
    try:
        parsed = json.loads(json_text)
        return {"valid": True, "parsed": parsed}
    except json.JSONDecodeError as e:
        return {
            "valid": False, 
            "error": str(e),
            "line": getattr(e, 'lineno', None),
            "column": getattr(e, 'colno', None)
        }

@tool
def fix_common_json_errors(json_text: str) -> str:
    """Apply common JSON error fixes."""
    # Remove extra spaces around braces and brackets
    json_text = re.sub(r'{\s+', '{', json_text)
    json_text = re.sub(r'\s+}', '}', json_text)
    json_text = re.sub(r'\[\s+', '[', json_text)
    json_text = re.sub(r'\s+\]', ']', json_text)
    
    # Fix spacing around colons and commas
    json_text = re.sub(r'\s*:\s*', ': ', json_text)
    json_text = re.sub(r'\s*,\s*', ', ', json_text)
    
    # Remove trailing commas
    json_text = re.sub(r',(\s*[}\]])', r'\1', json_text)
    
    # Fix unescaped quotes in strings (basic approach)
    json_text = re.sub(r'(?<!\\)"(?![,\]\}:\s])', r'\\"', json_text)
    
    return json_text

@tool
def extract_json_from_text(text: str) -> Optional[str]:
    """Extract JSON object from mixed text content."""
    # Find the first '{' and last '}' to extract JSON
    start = text.find('{')
    end = text.rfind('}')
    
    if start != -1 and end != -1 and end > start:
        return text[start:end+1]
    
    return None
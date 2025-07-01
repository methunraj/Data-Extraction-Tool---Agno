"""
Prompt loader utility for loading prompts from text files.
"""

import os
from pathlib import Path
from typing import Dict, Optional
from functools import lru_cache


class PromptLoader:
    """Singleton class for loading and caching prompts."""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize the prompt loader."""
        self.prompts_dir = Path(__file__).parent
        self._cache: Dict[str, str] = {}
    
    @lru_cache(maxsize=None)
    def load(self, prompt_path: str) -> str:
        """
        Load a prompt from a file path relative to the prompts directory.
        
        Args:
            prompt_path: Path to the prompt file relative to the prompts directory
                        e.g., "agents/data_analyst.txt" or "services/extraction/system.txt"
        
        Returns:
            The content of the prompt file
        
        Raises:
            FileNotFoundError: If the prompt file doesn't exist
        """
        full_path = self.prompts_dir / prompt_path
        
        if not full_path.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
        
        with open(full_path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    
    def load_with_template(self, prompt_path: str, **kwargs) -> str:
        """
        Load a prompt and substitute template variables.
        
        Args:
            prompt_path: Path to the prompt file
            **kwargs: Template variables to substitute
        
        Returns:
            The formatted prompt with substituted variables
        """
        prompt = self.load(prompt_path)
        
        # Replace template variables
        for key, value in kwargs.items():
            placeholder = f"{{{{{key}}}}}"  # e.g., {{key}}
            prompt = prompt.replace(placeholder, str(value))
        
        return prompt
    
    def clear_cache(self):
        """Clear the prompt cache."""
        self.load.cache_clear()


# Global instance
_prompt_loader = PromptLoader()


def load_prompt(prompt_path: str, **kwargs) -> str:
    """
    Load a prompt from a file with optional template substitution.
    
    Args:
        prompt_path: Path to the prompt file relative to the prompts directory
        **kwargs: Optional template variables to substitute
    
    Returns:
        The loaded (and optionally formatted) prompt
    
    Example:
        >>> load_prompt("agents/data_analyst.txt")
        >>> load_prompt("services/extraction/user.txt", document_text="sample text")
    """
    if kwargs:
        return _prompt_loader.load_with_template(prompt_path, **kwargs)
    return _prompt_loader.load(prompt_path)
"""Prompt Manager for loading and caching prompts."""

import os
from typing import Dict


class PromptManager:
    """Manages loading and caching of prompts from files."""

    def __init__(self, prompt_dir: str = "docs/prompts_archive"):
        """Initialize the PromptManager.

        Args:
            prompt_dir: Directory containing prompt files
        """
        self.prompt_dir = prompt_dir
        self.prompt_cache: Dict[str, str] = {}  # Cache for loaded prompts

    def get_prompt(self, prompt_name: str, placeholders: Dict[str, str] = None) -> str:
        """Load a prompt from file with caching and replace placeholders.

        Args:
            prompt_name: Name of the prompt file (without directory or .md extension)
            placeholders: Optional dictionary of placeholders to replace in the prompt
                          Format: {'placeholder_name': 'replacement_value'}

        Returns:
            The prompt text with placeholders replaced
        """
        # Build the full path
        prompt_path = os.path.join(self.prompt_dir, f"{prompt_name}.md")

        # Get the prompt text
        prompt_text = self._load_prompt(prompt_path)

        # Replace placeholders if provided
        if placeholders and prompt_text:
            for placeholder, value in placeholders.items():
                prompt_text = prompt_text.replace(f"{{{{{placeholder}}}}}", value)

        return prompt_text

    def _load_prompt(self, prompt_path: str) -> str:
        """Load prompt from file with caching.

        Args:
            prompt_path: Path to the prompt file

        Returns:
            The prompt text
        """
        # Check if prompt is already in cache
        if prompt_path in self.prompt_cache:
            return self.prompt_cache[prompt_path]

        # Load prompt from file
        try:
            with open(prompt_path, "r") as f:
                prompt_text = f.read()

            # Cache the prompt for future use
            self.prompt_cache[prompt_path] = prompt_text
            return prompt_text
        except Exception as e:
            print(f"Error loading prompt from {prompt_path}: {str(e)}")
            return ""  # Return empty string on error

    def combine_prompts(self, prompt_names: list, separator: str = "\n\n") -> str:
        """Combine multiple prompts into a single prompt.

        Args:
            prompt_names: List of prompt names to combine
            separator: Separator to use between prompts

        Returns:
            Combined prompt text
        """
        prompt_texts = [self.get_prompt(name) for name in prompt_names]
        return separator.join([text for text in prompt_texts if text])

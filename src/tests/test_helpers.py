"""Helper functions for tests."""
import contextlib
from pathlib import Path
from unittest.mock import patch


@contextlib.contextmanager
def use_test_prompts():
    """Context manager to temporarily use test prompts directory."""
    test_prompts_dir = Path(__file__).parent / "test_prompts"

    with patch("src.geminiservice.PROMPTS_DIR", test_prompts_dir):
        yield test_prompts_dir


def get_test_prompt_path(prompt_name: str) -> Path:
    """Get the path to a test prompt file."""
    test_prompts_dir = Path(__file__).parent / "test_prompts"

    # Try .md first, then .txt
    for extension in [".md", ".txt"]:
        prompt_path = test_prompts_dir / f"{prompt_name}{extension}"
        if prompt_path.exists():
            return prompt_path

    raise FileNotFoundError(f"Test prompt not found: {prompt_name}")

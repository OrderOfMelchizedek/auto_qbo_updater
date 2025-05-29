import os
import shutil
import sys
import tempfile
import unittest

# Add src to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from utils.prompt_manager import PromptManager


class TestPromptManager(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for test prompts
        self.temp_dir = tempfile.mkdtemp()

        # Create a test prompt file
        self.test_prompt_content = (
            "This is a test prompt with {{placeholder}} for testing."
        )
        self.test_prompt_path = os.path.join(self.temp_dir, "test_prompt.md")
        with open(self.test_prompt_path, "w") as f:
            f.write(self.test_prompt_content)

        # Initialize the PromptManager with the temp directory
        self.prompt_manager = PromptManager(prompt_dir=self.temp_dir)

    def tearDown(self):
        # Clean up the temporary directory
        shutil.rmtree(self.temp_dir)

    def test_get_prompt(self):
        """Test that get_prompt correctly loads a prompt file."""
        prompt = self.prompt_manager.get_prompt("test_prompt")
        self.assertEqual(prompt, self.test_prompt_content)

    def test_prompt_caching(self):
        """Test that prompts are cached after being loaded."""
        # First call should load the prompt
        self.prompt_manager.get_prompt("test_prompt")

        # Modify the file after caching
        with open(self.test_prompt_path, "w") as f:
            f.write("Modified content")

        # Second call should return the cached content
        prompt = self.prompt_manager.get_prompt("test_prompt")
        self.assertEqual(prompt, self.test_prompt_content)

    def test_placeholder_replacement(self):
        """Test that placeholders are correctly replaced in prompts."""
        prompt = self.prompt_manager.get_prompt("test_prompt", {"placeholder": "value"})
        self.assertEqual(prompt, "This is a test prompt with value for testing.")

    def test_missing_prompt(self):
        """Test handling of missing prompt files."""
        prompt = self.prompt_manager.get_prompt("nonexistent_prompt")
        self.assertEqual(prompt, "")

    def test_combine_prompts(self):
        """Test combining multiple prompts."""
        # Create a second test prompt
        second_prompt_content = "This is a second test prompt."
        with open(os.path.join(self.temp_dir, "second_prompt.md"), "w") as f:
            f.write(second_prompt_content)

        combined_prompt = self.prompt_manager.combine_prompts(
            ["test_prompt", "second_prompt"]
        )
        expected = f"{self.test_prompt_content}\n\n{second_prompt_content}"
        self.assertEqual(combined_prompt, expected)

    def test_combine_prompts_with_missing(self):
        """Test combining prompts when one is missing."""
        combined_prompt = self.prompt_manager.combine_prompts(
            ["test_prompt", "nonexistent_prompt"]
        )
        self.assertEqual(combined_prompt, self.test_prompt_content)


if __name__ == "__main__":
    unittest.main()

import os
import json
import io
import base64
from PIL import Image
import google.generativeai as genai
from typing import Dict, Any, Optional

class GeminiService:
    """Service for interacting with Google's Gemini 2.5 Pro Preview API."""
    
    def __init__(self, api_key: str):
        """Initialize the Gemini service with API key."""
        self.api_key = api_key
        genai.configure(api_key=api_key)
    
    def extract_donation_data(self, image_path: str) -> Optional[Dict[str, Any]]:
        """Extract donation data from an image using Gemini.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Dictionary containing extracted donation data or None if extraction failed
        """
        try:
            # Read the prompt template
            with open('FOM Deposit Assistant Prompt 2025-04-12.md', 'r') as f:
                prompt_template = f.read()
            
            # Load image
            image = Image.open(image_path)
            
            # Convert image to base64 for API
            image_buffer = io.BytesIO()
            image.save(image_buffer, format=image.format or 'JPEG')
            image_bytes = image_buffer.getvalue()
            
            # Create simplified implementation without function calling
            # Create a direct prompt that asks for structured output
            extraction_prompt = f"""
{prompt_template}

Please extract the donation information from the image and return it in JSON format with the following fields:
- customerLookup
- Salutation
- Donor Name 
- Check No.
- Gift Amount
- Check Date
- Gift Date
- Deposit Date
- Deposit Method
- Memo
- First Name
- Last Name
- Full Name
- Organization Name
- Address - Line 1
- City
- State
- ZIP

Format your response as valid JSON only.
"""
            
            # Set up model
            model = genai.GenerativeModel('gemini-2.5-pro-preview-03-25')
            
            # Call Gemini API with image
            response = model.generate_content(
                contents=[extraction_prompt, image],
                generation_config=genai.GenerationConfig(
                    temperature=0.2
                )
            )
            
            # Extract response text
            text_response = response.text
            if text_response and '{' in text_response and '}' in text_response:
                # Try to extract JSON from text
                json_start = text_response.find('{')
                json_end = text_response.rfind('}') + 1
                json_str = text_response[json_start:json_end]
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    print("Error parsing JSON from Gemini response")
            
            print("Failed to extract donation data from Gemini response")
            print(f"Response text: {text_response}")
            return None
        
        except Exception as e:
            print(f"Error calling Gemini API: {str(e)}")
            return None
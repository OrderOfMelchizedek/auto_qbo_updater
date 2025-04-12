import os
import json
import google.generativeai as genai
from typing import Dict, Any, Optional

class GeminiService:
    """Service for interacting with Google's Gemini 2.5 Pro Preview API."""
    
    def __init__(self, api_key: str):
        """Initialize the Gemini service with API key."""
        self.api_key = api_key
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.5-pro-preview')
    
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
            with open(image_path, 'rb') as f:
                image_data = f.read()
            
            # Create structured output schema based on headers
            schema = {
                "type": "object",
                "properties": {
                    "customerLookup": {"type": "string"},
                    "Salutation": {"type": "string"},
                    "Donor Name": {"type": "string"},
                    "Check No.": {"type": "string"},
                    "Gift Amount": {"type": "string"},
                    "Check Date": {"type": "string"},
                    "Gift Date": {"type": "string"},
                    "Deposit Date": {"type": "string"},
                    "Deposit Method": {"type": "string"},
                    "Memo": {"type": "string"},
                    "First Name": {"type": "string"},
                    "Last Name": {"type": "string"},
                    "Full Name": {"type": "string"},
                    "Organization Name": {"type": "string"},
                    "Address - Line 1": {"type": "string"},
                    "City": {"type": "string"},
                    "State": {"type": "string"},
                    "ZIP": {"type": "string"}
                },
                "required": ["customerLookup", "Donor Name", "Gift Amount"]
            }
            
            # Call Gemini API with image
            response = self.model.generate_content(
                [prompt_template, image_data],
                generation_config={"response_mime_type": "application/json"},
                tools=[{"function_declarations": [{"name": "extract_donation", "schema": schema}]}]
            )
            
            if hasattr(response, 'candidates') and len(response.candidates) > 0:
                # Parse JSON response
                if hasattr(response.candidates[0], 'content') and hasattr(response.candidates[0].content, 'parts'):
                    parts = response.candidates[0].content.parts
                    for part in parts:
                        if hasattr(part, 'function_call') and part.function_call.name == 'extract_donation':
                            return json.loads(part.function_call.args)
            
            # Handle non-function-call response format
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
            return None
        
        except Exception as e:
            print(f"Error calling Gemini API: {str(e)}")
            return None
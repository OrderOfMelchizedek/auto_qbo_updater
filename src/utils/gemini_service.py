import os
import json
import io
import base64
from PIL import Image
import google.generativeai as genai
from typing import Dict, Any, Optional, List, Union

class GeminiService:
    """Service for interacting with Google's Gemini 2.5 Pro Preview API."""
    
    def __init__(self, api_key: str):
        """Initialize the Gemini service with API key."""
        self.api_key = api_key
        genai.configure(api_key=api_key)
    
    def extract_text_data(self, prompt_text: str) -> Optional[Union[Dict[str, Any], List[Dict[str, Any]]]]:
        """Extract structured data from text using Gemini.
        
        Args:
            prompt_text: The prompt text to send to Gemini
            
        Returns:
            Dictionary or list of dictionaries containing extracted data or None if extraction failed
        """
        try:
            # Set up model
            model = genai.GenerativeModel('gemini-2.5-pro-preview-03-25')
            
            # Call Gemini API with prompt text
            print(f"Processing text with Gemini")
            response = model.generate_content(
                contents=[prompt_text],
                generation_config=genai.GenerationConfig(
                    temperature=0.2
                )
            )
            
            # Extract response text
            text_response = response.text
            
            # Check for JSON in the response
            if text_response:
                print(f"Response text: {text_response}")
                
                # First try to directly parse the text as JSON
                try:
                    parsed_json = json.loads(text_response)
                    print("Successfully parsed complete JSON response")
                    
                    # Return the full array of data (or single object)
                    if isinstance(parsed_json, list):
                        print(f"Found array of {len(parsed_json)} items, returning all items")
                    return parsed_json
                    
                except json.JSONDecodeError:
                    # If that fails, try to extract JSON from the text
                    try:
                        # Check for array format
                        if '[' in text_response and ']' in text_response:
                            json_start = text_response.find('[')
                            json_end = text_response.rfind(']') + 1
                        # Check for object format
                        elif '{' in text_response and '}' in text_response:
                            json_start = text_response.find('{')
                            json_end = text_response.rfind('}') + 1
                        else:
                            raise ValueError("No JSON markers found in response")
                            
                        json_str = text_response[json_start:json_end]
                        parsed_json = json.loads(json_str)
                        
                        # Return the full array of data (or single object)
                        if isinstance(parsed_json, list):
                            print(f"Found array of {len(parsed_json)} items, returning all items")
                        return parsed_json
                        
                    except (json.JSONDecodeError, ValueError) as e:
                        print(f"Error extracting JSON from response: {str(e)}")
            
            print("Failed to extract data from Gemini response")
            return None
        
        except Exception as e:
            print(f"Error calling Gemini API: {str(e)}")
            return None
    
    def extract_donation_data(self, file_path: str, custom_prompt: str = None) -> Optional[Dict[str, Any]]:
        """Extract donation data from an image or PDF using Gemini.
        
        Args:
            file_path: Path to the image or PDF file
            custom_prompt: Optional custom prompt to use instead of the default
            
        Returns:
            Dictionary containing extracted donation data or None if extraction failed
        """
        try:
            # Determine file type by extension
            file_ext = os.path.splitext(file_path)[1].lower()
            
            # Use custom prompt if provided, otherwise use the default prompt
            if custom_prompt:
                extraction_prompt = custom_prompt
            else:
                # Read the prompt template
                with open('FOM Deposit Assistant Prompt 2025-04-12.md', 'r') as f:
                    prompt_template = f.read()
                
                # Create extraction prompt that asks for structured output
                extraction_prompt = f"""
{prompt_template}

Please extract the donation information from the document and return it in JSON format with the following fields:
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
            
            # Process based on file type
            if file_ext == '.pdf':
                # For PDFs, we'll try two approaches:
                # 1. First, attempt to use the image data directly as a multimodal input
                # 2. If that fails, fall back to extracting text and sending a text-only request
                import PyPDF2
                import fitz  # PyMuPDF
                
                # Try to extract text from PDF as a fallback
                pdf_text = ""
                try:
                    pdf_reader = PyPDF2.PdfReader(file_path)
                    for page in pdf_reader.pages:
                        extracted_text = page.extract_text()
                        if extracted_text:
                            pdf_text += extracted_text + "\n\n"
                except Exception as e:
                    print(f"Error extracting text with PyPDF2: {str(e)}")
                
                # Approach 1: Try to render PDF pages as images
                try:
                    print("Processing PDF visually by converting to images")
                    pdf_doc = fitz.open(file_path)
                    
                    # Enhanced prompt
                    enhanced_extraction_prompt = extraction_prompt
                    
                    # If text was successfully extracted, enhance the prompt with it
                    if pdf_text.strip():
                        print("PDF contains extractable text - adding as context")
                        enhanced_extraction_prompt += f"""
                        
Additional context - extracted text from the PDF:

{pdf_text}

"""
                    else:
                        print("PDF does not contain extractable text")
                    
                    # If it's a multi-page PDF, process the first page only for now
                    # (you can extend this to handle multiple pages if needed)
                    page = pdf_doc[0]
                    pix = page.get_pixmap()
                    img_data = pix.tobytes("png")
                    
                    # Load image data
                    image = Image.open(io.BytesIO(img_data))
                    
                    # Use multimodal processing with the rendered image
                    content_parts = [enhanced_extraction_prompt, image]
                    
                except Exception as e:
                    print(f"Error processing PDF visually: {str(e)}")
                    
                    # Approach 2: Fall back to text-only if we have extracted text
                    if pdf_text.strip():
                        print("Falling back to text-only processing")
                        
                        # Create a prompt with the extracted text
                        text_fallback_prompt = f"""
{extraction_prompt}

Here is the extracted text from the PDF document:

{pdf_text}

Based on this text, please extract the donation information and return it in the requested JSON format.
"""
                        content_parts = [text_fallback_prompt]
                    else:
                        # If we have no text and the visual approach failed, we can't process this PDF
                        raise ValueError("Cannot process this PDF - no extractable text and visual processing failed")
                
            elif file_ext in ['.jpg', '.jpeg', '.png']:
                # For images, use PIL to load the image
                image = Image.open(file_path)
                content_parts = [extraction_prompt, image]
            else:
                raise ValueError(f"Unsupported file type: {file_ext}")
            
            # Call Gemini API with content
            print(f"Processing {file_ext} file with Gemini: {file_path}")
            response = model.generate_content(
                contents=content_parts,
                generation_config=genai.GenerationConfig(
                    temperature=0.2
                )
            )
            
            # Extract response text
            text_response = response.text
            
            # Check for JSON in the response
            # Look for either array '[' or object '{' as valid JSON start characters
            if text_response:
                # For clarity in logs
                print(f"Response text: {text_response}")
                
                # First try to directly parse the text as JSON
                try:
                    parsed_json = json.loads(text_response)
                    print("Successfully parsed complete JSON response")
                    
                    # Return the full array of donations (or single object)
                    if isinstance(parsed_json, list):
                        print(f"Found array of {len(parsed_json)} donations, returning all items")
                    return parsed_json
                    
                except json.JSONDecodeError:
                    # If that fails, try to extract JSON from the text
                    try:
                        # Check for array format
                        if '[' in text_response and ']' in text_response:
                            json_start = text_response.find('[')
                            json_end = text_response.rfind(']') + 1
                        # Check for object format
                        elif '{' in text_response and '}' in text_response:
                            json_start = text_response.find('{')
                            json_end = text_response.rfind('}') + 1
                        else:
                            raise ValueError("No JSON markers found in response")
                            
                        json_str = text_response[json_start:json_end]
                        parsed_json = json.loads(json_str)
                        
                        # Return the full array of donations (or single object)
                        if isinstance(parsed_json, list):
                            print(f"Found array of {len(parsed_json)} donations, returning all items")
                        return parsed_json
                        
                    except (json.JSONDecodeError, ValueError) as e:
                        print(f"Error extracting JSON from response: {str(e)}")
            
            print("Failed to extract donation data from Gemini response")
            return None
        
        except Exception as e:
            print(f"Error calling Gemini API: {str(e)}")
            return None
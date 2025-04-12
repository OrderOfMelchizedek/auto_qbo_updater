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
        
    def _extract_json_from_text(self, text: str) -> Any:
        """Extract JSON from text, handling various response formats.
        
        Args:
            text: Text that may contain JSON
            
        Returns:
            Parsed JSON data (object or array) or None if extraction failed
        """
        # First try to directly parse the text as JSON
        try:
            parsed_json = json.loads(text)
            print("Successfully parsed complete JSON response")
            return parsed_json
        except json.JSONDecodeError:
            # If that fails, try to extract JSON from the text
            try:
                # Check for array format
                if '[' in text and ']' in text:
                    json_start = text.find('[')
                    json_end = text.rfind(']') + 1
                # Check for object format
                elif '{' in text and '}' in text:
                    json_start = text.find('{')
                    json_end = text.rfind('}') + 1
                else:
                    raise ValueError("No JSON markers found in response")
                    
                json_str = text[json_start:json_end]
                parsed_json = json.loads(json_str)
                print(f"Extracted JSON from text (length: {len(json_str)})")
                return parsed_json
                
            except (json.JSONDecodeError, ValueError) as e:
                print(f"Error extracting JSON from text: {str(e)}")
                return None
    
    def extract_text_data(self, prompt_text: str) -> Optional[Union[Dict[str, Any], List[Dict[str, Any]]]]:
        """Extract structured data from text using Gemini with schema.
        
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
            
            if text_response:
                print(f"Response text: {text_response}")
                
                # Use the helper method to extract JSON
                parsed_json = self._extract_json_from_text(text_response)
                if parsed_json:
                    # Return the data (array or single object)
                    if isinstance(parsed_json, list):
                        print(f"Found array of {len(parsed_json)} items, returning all items")
                        return parsed_json
                    else:
                        return [parsed_json]  # Wrap single object in list for consistency
            
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

Please extract the donation information from the document and return it in STRICT JSON format.
VERY IMPORTANT: Your response MUST include ONLY valid JSON with NO additional text.

The JSON must include ALL of these fields, even if the value is null:
{{
  "customerLookup": "string or null",
  "Salutation": "string or null",
  "Donor Name": "string (REQUIRED)",
  "Check No.": "string or null",
  "Gift Amount": "string (REQUIRED)",
  "Check Date": "string or null",
  "Gift Date": "string (REQUIRED)",
  "Deposit Date": "string or null",
  "Deposit Method": "string or null",
  "Memo": "string or null",
  "First Name": "string (REQUIRED)",
  "Last Name": "string (REQUIRED)",
  "Full Name": "string or null",
  "Organization Name": "string or null",
  "Address - Line 1": "string (REQUIRED)",
  "City": "string (REQUIRED)",
  "State": "string (REQUIRED)",
  "ZIP": "string (REQUIRED)"
}}

These fields are REQUIRED and MUST have a value (not null):
- Donor Name
- Gift Amount
- Gift Date
- First Name
- Last Name
- Address - Line 1
- City
- State
- ZIP

Please examine the document thoroughly to find all required information.
IMPORTANT: Return ONLY the JSON object, with no additional text before or after.
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
                    
                    # Process all pages of the PDF
                    print(f"PDF has {len(pdf_doc)} pages - processing all pages")
                    
                    # Store results from all pages
                    all_results = []
                    
                    # Process each page of the PDF
                    for page_num in range(len(pdf_doc)):
                        page = pdf_doc[page_num]
                        print(f"Processing page {page_num + 1} of {len(pdf_doc)}")
                        
                        # Convert page to image
                        pix = page.get_pixmap()
                        img_data = pix.tobytes("png")
                        
                        # Load image data
                        image = Image.open(io.BytesIO(img_data))
                        
                        # Update prompt to specify which page is being processed
                        page_specific_prompt = enhanced_extraction_prompt + f"\n\nThis is page {page_num + 1} of {len(pdf_doc)}."
                        
                        # Use multimodal processing with the rendered image
                        content_parts = [page_specific_prompt, image]
                        
                        # Call Gemini API for this page
                        page_response = model.generate_content(
                            contents=content_parts,
                            generation_config=genai.GenerationConfig(
                                temperature=0.2
                            )
                        )
                        
                        # Extract response for this page
                        if page_response.text:
                            print(f"Extracted data from page {page_num + 1}")
                            try:
                                # Try to parse the JSON response
                                page_json = self._extract_json_from_text(page_response.text)
                                if page_json:
                                    # Add to results (could be a single object or array)
                                    if isinstance(page_json, list):
                                        all_results.extend(page_json)
                                    else:
                                        all_results.append(page_json)
                            except Exception as e:
                                print(f"Error processing data from page {page_num + 1}: {str(e)}")
                    
                    # Return combined results from all pages
                    if all_results:
                        print(f"Successfully extracted data from {len(all_results)} donation records across {len(pdf_doc)} pages")
                        return all_results
                    
                    # If we didn't get any results, try processing the first page again
                    # as a fallback (in case the multi-page approach had issues)
                    if not all_results:
                        print("No results from multi-page processing, falling back to single page")
                        page = pdf_doc[0]
                        pix = page.get_pixmap()
                        img_data = pix.tobytes("png")
                        image = Image.open(io.BytesIO(img_data))
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
            
            # For Gemini API 0.5.4, we need to explicitly request JSON in the prompt
            # Update the prompt to strongly emphasize structured JSON output
            if isinstance(content_parts[0], str):
                content_parts[0] += "\n\nVery important: Your response must be VALID JSON only. No explanation text or Markdown formatting."
                
            response = model.generate_content(
                contents=content_parts,
                generation_config=genai.GenerationConfig(
                    temperature=0.2
                )
            )
            
            # Extract response text
            text_response = response.text
            
            if text_response:
                # For clarity in logs
                print(f"Response text: {text_response}")
                
                # Use the helper method to extract JSON
                parsed_json = self._extract_json_from_text(text_response)
                if parsed_json:
                    # Structure the output consistently - always return a list
                    if isinstance(parsed_json, list):
                        print(f"Found array of {len(parsed_json)} donations, returning all items")
                        return parsed_json
                    else:
                        # Wrap single donation in a list for consistency
                        return [parsed_json]
            
            print("Failed to extract donation data from Gemini response")
            return None
        
        except Exception as e:
            print(f"Error calling Gemini API: {str(e)}")
            return None
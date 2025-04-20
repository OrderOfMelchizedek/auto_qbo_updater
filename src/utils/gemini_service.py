import os
import json
import io
import base64
from PIL import Image
import google.generativeai as genai
from typing import Dict, Any, Optional, List, Union
from .prompt_manager import PromptManager

class GeminiService:
    """Service for interacting with Google's Gemini API."""
    
    def __init__(self, api_key: str, model_name: str = 'gemini-2.5-flash-preview-04-17'):
        """Initialize the Gemini service with API key and model name.
        
        Args:
            api_key: Gemini API key
            model_name: Gemini model name to use ('gemini-2.5-flash-preview-04-17' by default)
        """
        self.api_key = api_key
        self.model_name = model_name
        genai.configure(api_key=api_key)
        self.prompt_manager = PromptManager(prompt_dir='docs/prompts_archive')
        print(f"Initialized Gemini service with model: {self.model_name}")
        
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
            # Set up model using the configured model name
            model = genai.GenerativeModel(self.model_name)
            
            # Call Gemini API with prompt text
            print(f"Processing text with Gemini model: {self.model_name}")
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
    
    def verify_customer_match(self, extracted_donor: Dict[str, Any], qbo_customer: Dict[str, Any]) -> Dict[str, Any]:
        """Verify if the QuickBooks customer is a match for the extracted donor data.
        
        This uses Gemini to intelligently verify the match and enrich the donor data
        with information from QuickBooks, handling discrepancies appropriately.
        
        Args:
            extracted_donor: Dictionary of extracted donor data
            qbo_customer: Dictionary of QuickBooks customer data
            
        Returns:
            Dictionary containing verification results and enhanced data if it's a match
        """
        try:
            # Format the input data as JSON strings for the prompt
            extracted_json = json.dumps(extracted_donor, indent=2)
            qbo_json = json.dumps(qbo_customer, indent=2)
            
            # Get the verification prompt with placeholders replaced
            verification_prompt = self.prompt_manager.get_prompt('customer_verification_prompt', {
                'extracted_data': extracted_json,
                'qbo_data': qbo_json
            })
            
            # Set up the model using the configured model name
            model = genai.GenerativeModel(self.model_name)
            
            # Call Gemini API with verification prompt
            print(f"Verifying customer match with Gemini model: {self.model_name}")
            response = model.generate_content(
                contents=[verification_prompt],
                generation_config=genai.GenerationConfig(
                    temperature=0.1  # Lower temperature for more deterministic response
                )
            )
            
            # Extract response text
            text_response = response.text
            
            if text_response:
                # Use the helper method to extract JSON
                verification_result = self._extract_json_from_text(text_response)
                if verification_result:
                    print(f"Match verification result: valid match = {verification_result.get('validMatch', False)}")
                    if verification_result.get('validMatch') == False:
                        print(f"Mismatch reason: {verification_result.get('mismatchReason', 'No reason provided')}")
                    if verification_result.get('addressMateriallyDifferent'):
                        print("Address is materially different - will need user input")
                    return verification_result
            
            # If verification failed, return a default result indicating no match
            print("Failed to verify customer match with Gemini")
            return {
                "validMatch": False,
                "mismatchReason": "Verification process failed",
                "matchConfidence": "none"
            }
        
        except Exception as e:
            print(f"Error verifying customer match: {str(e)}")
            return {
                "validMatch": False,
                "mismatchReason": f"Error during verification: {str(e)}",
                "matchConfidence": "none"
            }
            
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
                # Use prompt manager to combine main prompt and extraction prompt
                extraction_prompt = self.prompt_manager.combine_prompts(['main_prompt', 'extraction_prompt'])
            
            # Set up model using the configured model name
            model = genai.GenerativeModel(self.model_name)
            
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
                        # Use prompt manager to get PDF text context prompt with placeholder replaced
                        pdf_context = self.prompt_manager.get_prompt('pdf_text_context_prompt', {'pdf_text': pdf_text})
                        enhanced_extraction_prompt += f"\n\n{pdf_context}"
                    else:
                        print("PDF does not contain extractable text")
                    
                    # Process PDF in batches of pages
                    print(f"PDF has {len(pdf_doc)} pages - processing in batches")
                    
                    # Maximum number of pages per batch
                    BATCH_SIZE = 15
                    
                    # Store results from all batches
                    all_results = []
                    
                    # Calculate number of batches
                    num_batches = (len(pdf_doc) + BATCH_SIZE - 1) // BATCH_SIZE
                    
                    # Process each batch
                    for batch_num in range(num_batches):
                        batch_start = batch_num * BATCH_SIZE
                        batch_end = min(batch_start + BATCH_SIZE, len(pdf_doc))
                        
                        print(f"Processing batch {batch_num + 1} of {num_batches} (pages {batch_start + 1}-{batch_end})")
                        
                        # Use prompt manager to get batch processing prompt with placeholders replaced
                        batch_prompt = self.prompt_manager.get_prompt('batch_processing_prompt', {
                            'start_page': str(batch_start + 1),
                            'end_page': str(batch_end),
                            'total_pages': str(len(pdf_doc))
                        })
                        
                        # Create content parts starting with the prompt
                        content_parts = [
                            enhanced_extraction_prompt + f"\n\n{batch_prompt}"
                        ]
                        
                        # Convert all pages in this batch to images and add to content
                        for page_num in range(batch_start, batch_end):
                            page = pdf_doc[page_num]
                            
                            # Convert page to image with good resolution
                            pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))  # 1.5x zoom for better resolution
                            img_data = pix.tobytes("png")
                            
                            # Load image data
                            image = Image.open(io.BytesIO(img_data))
                            
                            # Add this image to the content parts
                            content_parts.append(image)
                        
                        # Call Gemini API for this batch of pages
                        try:
                            print(f"Sending batch of {len(content_parts) - 1} pages to Gemini")
                            batch_response = model.generate_content(
                                contents=content_parts,
                                generation_config=genai.GenerationConfig(
                                    temperature=0.2
                                )
                            )
                            
                            # Extract response for this batch
                            if batch_response.text:
                                print(f"Received response for batch {batch_num + 1}")
                                try:
                                    # Try to parse the JSON response
                                    batch_json = self._extract_json_from_text(batch_response.text)
                                    
                                    if batch_json:
                                        # Add to results (could be a single object or array)
                                        if isinstance(batch_json, list):
                                            all_results.extend(batch_json)
                                            print(f"Added {len(batch_json)} donations from batch {batch_num + 1}")
                                        else:
                                            all_results.append(batch_json)
                                            print(f"Added 1 donation from batch {batch_num + 1}")
                                except Exception as e:
                                    print(f"Error processing data from batch {batch_num + 1}: {str(e)}")
                        except Exception as e:
                            print(f"Error processing batch {batch_num + 1}: {str(e)}")
                    
                    # Return combined results from all batches
                    if all_results:
                        print(f"Successfully extracted data from {len(all_results)} donation records across {len(pdf_doc)} pages")
                        return all_results
                    
                    # If we didn't get any results, try processing the first page as a fallback
                    if not all_results:
                        print("No results from batch processing, falling back to single page")
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
                        
                        # Use prompt manager to get PDF text fallback prompt with placeholder replaced
                        fallback_content = self.prompt_manager.get_prompt('pdf_text_fallback_prompt', {'pdf_text': pdf_text})
                        text_fallback_prompt = f"{extraction_prompt}\n\n{fallback_content}"
                        content_parts = [text_fallback_prompt]
                    else:
                        # If we have no text and the visual approach failed, we can't process this PDF
                        raise ValueError("Cannot process this PDF - no extractable text and visual processing failed")
                
            elif file_ext in ['.jpg', '.jpeg', '.png']:
                try:
                    # For images, use PIL to load the image
                    image = Image.open(file_path)
                    print(f"Successfully opened image file: {file_path}")
                    content_parts = [extraction_prompt, image]
                except Exception as e:
                    print(f"Error loading image with PIL: {str(e)}")
                    # Try an alternative approach - read raw bytes
                    with open(file_path, 'rb') as img_file:
                        img_bytes = img_file.read()
                    print(f"Read {len(img_bytes)} bytes from image file")
                    # Handle image as raw data
                    # Use prompt manager to get image extraction prompt
                    image_prompt = self.prompt_manager.get_prompt('image_extraction_prompt')
                    content_parts = [
                        extraction_prompt + f"\n\n{image_prompt}"
                    ]
            else:
                raise ValueError(f"Unsupported file type: {file_ext}")
            
            # Call Gemini API with content
            print(f"Processing {file_ext} file with Gemini: {file_path}")
            
            # For Gemini API 0.5.4, we need to explicitly request JSON in the prompt
            # Update the prompt to strongly emphasize structured JSON output
            if isinstance(content_parts[0], str):
                # Use prompt manager to get JSON format reminder
                json_reminder = self.prompt_manager.get_prompt('json_format_reminder')
                content_parts[0] += f"\n\n{json_reminder}"
                
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
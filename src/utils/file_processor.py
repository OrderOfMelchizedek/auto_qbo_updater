import os
from typing import Dict, Any, Optional, List, Union
import PyPDF2
from PIL import Image
import io

from utils.gemini_service import GeminiService

class FileProcessor:
    """Service for processing different file types (images, PDFs) for donation extraction."""
    
    def __init__(self, gemini_service: GeminiService):
        """Initialize the file processor with a Gemini service."""
        self.gemini_service = gemini_service
    
    def process(self, file_path: str, file_ext: str) -> Any:
        """Process a file to extract donation information.
        
        Args:
            file_path: Path to the file
            file_ext: File extension (.jpg, .png, .pdf, .csv, etc.)
            
        Returns:
            Dictionary containing extracted donation data or 
            List of dictionaries (for PDFs/CSVs with multiple donations) or None if extraction failed
        """
        if file_ext in ['.jpg', '.jpeg', '.png']:
            return self._process_image(file_path)
        elif file_ext == '.pdf':
            return self._process_pdf(file_path)
        elif file_ext == '.csv':
            return self._process_csv(file_path)
        else:
            print(f"Unsupported file type: {file_ext}")
            return None
    
    def _process_image(self, image_path: str) -> Optional[Dict[str, Any]]:
        """Process an image file.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Dictionary containing extracted donation data or None if extraction failed
        """
        try:
            # Simple validation of image before sending to Gemini
            img = Image.open(image_path)
            img.verify()  # Check if it's a valid image
            
            # Extract donation data using Gemini
            donation_data = self.gemini_service.extract_donation_data(image_path)
            return donation_data
        
        except Exception as e:
            print(f"Error processing image {image_path}: {str(e)}")
            return None
    
    def _process_pdf(self, pdf_path: str) -> Optional[Union[Dict[str, Any], List[Dict[str, Any]]]]:
        """Process a PDF file.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Dictionary containing extracted donation data,
            List of dictionaries (for PDFs with multiple donations),
            or None if extraction failed
        """
        try:
            # Send PDF directly to Gemini for processing
            donation_data = self.gemini_service.extract_donation_data(pdf_path)
            return donation_data
        
        except Exception as e:
            print(f"Error processing PDF {pdf_path}: {str(e)}")
            return None
            
    def _process_csv(self, csv_path: str) -> Optional[Union[Dict[str, Any], List[Dict[str, Any]]]]:
        """Process a CSV file using Gemini.
        
        Args:
            csv_path: Path to the CSV file
            
        Returns:
            Dictionary containing extracted donation data,
            List of dictionaries (for CSVs with multiple donations),
            or None if extraction failed
        """
        try:
            # Read CSV file content
            encodings = ['utf-8-sig', 'utf-8', 'latin-1', 'cp1252']
            csv_content = None
            
            # Try different encodings
            for encoding in encodings:
                try:
                    with open(csv_path, 'r', encoding=encoding) as f:
                        csv_content = f.read()
                    print(f"Successfully read CSV with encoding: {encoding}")
                    break
                except UnicodeDecodeError:
                    continue
            
            if not csv_content:
                raise ValueError(f"Unable to read CSV file with any of these encodings: {encodings}")
                
            print(f"CSV content sample: {csv_content[:500]}")
            
            # Create a special text prompt for CSV processing
            csv_prompt = f"""
You are analyzing a CSV file containing donation information. This CSV data represents online donations.
Here is the raw CSV content:

{csv_content}

Please extract all donation records from this CSV file. Each donation should include the following fields:
- customerLookup (from name or organization)
- Salutation (Mr./Mrs./Ms./Members of/etc. based on context)
- Donor Name (full name of the donor)
- Check No. (always "N/A" for online donations)
- Gift Amount (donation amount)
- Gift Date (date of donation)
- Deposit Date (Today's date)
- Deposit Method (always "Online Donation")
- Memo (additional notes, or "Online Donation" if no other info)
- First Name (first name or names of donor)
- Last Name (last name of donor)
- Full Name (combination of first and last name)
- Organization Name (if donation is from an organization)
- Address - Line 1 (street address)
- City (city name)
- State (state or province)
- ZIP (ZIP or postal code)

Return the extracted data in structured JSON format, with each donation as an item in an array.
"""
            
            # Send CSV text to Gemini for processing
            donation_data = self.gemini_service.extract_text_data(csv_prompt)
            return donation_data
            
        except Exception as e:
            print(f"Error processing CSV {csv_path}: {str(e)}")
            return None
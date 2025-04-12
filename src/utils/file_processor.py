import os
import json
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
            return self._process_with_validation(self._process_image, file_path, file_ext)
        elif file_ext == '.pdf':
            return self._process_with_validation(self._process_pdf, file_path, file_ext)
        elif file_ext == '.csv':
            return self._process_csv(file_path)
        else:
            print(f"Unsupported file type: {file_ext}")
            return None
            
    def _process_with_validation(self, processing_func, file_path, file_ext):
        """Process a file with validation and retry for missing fields.
        
        Args:
            processing_func: Function to call for initial processing
            file_path: Path to the file
            file_ext: File extension
            
        Returns:
            Validated donation data or None if processing failed
        """
        # Initial processing
        donation_data = processing_func(file_path)
        
        if donation_data is None:
            return None
            
        # Convert to list if it's a single donation
        donations_list = donation_data if isinstance(donation_data, list) else [donation_data]
        
        # Check if any donations need reprocessing for missing fields
        complete_donations = []
        donations_to_reprocess = []
        
        # Required fields (Memo is optional)
        required_fields = [
            'Donor Name', 'Gift Amount', 'Gift Date', 'Address - Line 1', 
            'City', 'State', 'ZIP', 'Last Name'
        ]
        
        for donation in donations_list:
            # Check for missing fields (except Memo which is optional)
            missing_fields = [field for field in required_fields if not donation.get(field)]
            
            # Gift Amount and Check No (for non-online) are strictly required
            # and will be checked later in the JavaScript validation
            
            if missing_fields:
                # Non-essential fields are missing - queue for reprocessing
                print(f"Donation has missing fields: {', '.join(missing_fields)}. Queuing for reprocessing.")
                donations_to_reprocess.append({
                    'donation': donation,
                    'missing_fields': missing_fields
                })
            else:
                # All required fields are present
                complete_donations.append(donation)
                
        # If we have donations needing reprocessing, send them back to Gemini
        if donations_to_reprocess:
            for item in donations_to_reprocess:
                donation = item['donation']
                missing_fields = item['missing_fields']
                
                # Create a detailed prompt specifying exactly what's missing
                reprocess_prompt = f"""
I need to extract complete donation information from this document.

I previously extracted this partial information:
{json.dumps(donation, indent=2)}

However, the following fields are missing or incomplete:
{', '.join(missing_fields)}

Please carefully examine the document again and provide the COMPLETE donation information with special attention to the missing fields.
Return ONLY a complete JSON object with ALL fields including:
- Donor Name
- Gift Amount
- Gift Date
- Address - Line 1
- City
- State
- ZIP
- Last Name
- Check No. (if this is a check payment)
"""
                
                print(f"Reprocessing donation to find missing fields: {missing_fields}")
                
                # Reprocess the document with focused prompt
                if file_ext in ['.jpg', '.jpeg', '.png']: 
                    reprocessed = self.gemini_service.extract_donation_data(file_path, custom_prompt=reprocess_prompt)
                elif file_ext == '.pdf':
                    reprocessed = self.gemini_service.extract_donation_data(file_path, custom_prompt=reprocess_prompt)
                    
                if reprocessed:
                    # If reprocessing returned a list, take the first item
                    if isinstance(reprocessed, list) and len(reprocessed) > 0:
                        reprocessed = reprocessed[0]
                        
                    # Only use the reprocessed data if it found the missing fields
                    still_missing = [field for field in missing_fields if not reprocessed.get(field)]
                    
                    if len(still_missing) < len(missing_fields):
                        print(f"Reprocessing improved the data - found {len(missing_fields) - len(still_missing)} of {len(missing_fields)} missing fields")
                        
                        # Merge the original and reprocessed data, preferring reprocessed for previously missing fields
                        for field in missing_fields:
                            if reprocessed.get(field):
                                donation[field] = reprocessed[field]
                                
                    else:
                        print(f"Reprocessing did not find any of the missing fields")
                        
                # Add the donation to complete list (even if some fields still missing)
                complete_donations.append(donation)
                        
        # Return in the same format as the original data
        if isinstance(donation_data, list):
            return complete_donations
        elif complete_donations:
            return complete_donations[0]
        else:
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

Please extract all donation records from this CSV file. 
VERY IMPORTANT: Return ONLY a valid JSON array containing objects with these fields, with NO additional text before or after:

[
  {{
    "customerLookup": "string or null",
    "Salutation": "string or null",
    "Donor Name": "string (REQUIRED)",
    "Check No.": "N/A",
    "Gift Amount": "string (REQUIRED)",
    "Check Date": "string or null",
    "Gift Date": "string (REQUIRED)",
    "Deposit Date": "today's date",
    "Deposit Method": "Online Donation", 
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
]

For Online Donations:
- Check No. should always be "N/A"
- Deposit Method should always be "Online Donation"
- Deposit Date should be today's date

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

Return ONLY the JSON array with no additional text. Ensure it is valid JSON that can be parsed directly.
"""
            
            # Send CSV text to Gemini for processing
            donation_data = self.gemini_service.extract_text_data(csv_prompt)
            return donation_data
            
        except Exception as e:
            print(f"Error processing CSV {csv_path}: {str(e)}")
            return None
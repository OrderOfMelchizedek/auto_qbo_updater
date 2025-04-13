import os
import json
from typing import Dict, Any, Optional, List, Union
import PyPDF2
from PIL import Image
import io

from utils.gemini_service import GeminiService
from utils.prompt_manager import PromptManager

class FileProcessor:
    """Service for processing different file types (images, PDFs) for donation extraction."""
    
    def __init__(self, gemini_service: GeminiService, qbo_service=None):
        """Initialize the file processor with Gemini and QBO services.
        
        Args:
            gemini_service: Service for AI-based extraction
            qbo_service: Optional QuickBooks Online service for customer lookups
        """
        self.gemini_service = gemini_service
        self.qbo_service = qbo_service
        self.prompt_manager = PromptManager(prompt_dir='prompts')
    
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
                
                # Use prompt manager to get reprocessing prompt with placeholders replaced
                reprocess_prompt = self.prompt_manager.get_prompt('reprocess_prompt', {
                    'partial_data': json.dumps(donation, indent=2),
                    'missing_fields': ', '.join(missing_fields)
                })
                
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
        
        # Match donations with QuickBooks customers if QBO service is available
        if self.qbo_service:
            print("Performing QBO customer matching for all donations...")
            complete_donations = self.match_donations_with_qbo_customers(complete_donations)
                        
        # Return in the same format as the original data
        if isinstance(donation_data, list):
            return complete_donations
        elif complete_donations:
            return complete_donations[0] if isinstance(complete_donations, list) else complete_donations
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
            # Basic file existence check
            if not os.path.exists(image_path):
                print(f"Image file doesn't exist: {image_path}")
                return None
                
            print(f"Processing image file: {image_path}")
            
            # Validate file size
            file_size = os.path.getsize(image_path)
            print(f"Image file size: {file_size} bytes")
            if file_size == 0:
                print(f"Image file is empty: {image_path}")
                return None
                
            # Extract donation data using Gemini directly
            # Skip PIL validation which might fail
            print(f"Sending image to Gemini service for processing")
            donation_data = self.gemini_service.extract_donation_data(image_path)
            
            print(f"Received response from Gemini service: {donation_data is not None}")
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
            
            # Use prompt manager to get CSV extraction prompt with placeholder replaced
            csv_prompt = self.prompt_manager.get_prompt('csv_extraction_prompt', {
                'csv_content': csv_content
            })
            
            # Send CSV text to Gemini for processing
            donation_data = self.gemini_service.extract_text_data(csv_prompt)
            
            # Match each donation with QuickBooks customers
            if donation_data and self.qbo_service:
                donation_data = self.match_donations_with_qbo_customers(donation_data)
                
            return donation_data
            
        except Exception as e:
            print(f"Error processing CSV {csv_path}: {str(e)}")
            return None
            
    # We no longer need to get all customers, as we're using direct QBO API lookups
        
    def match_donations_with_qbo_customers(self, donations):
        """Match extracted donations with QuickBooks customers using direct QBO API.
        
        Args:
            donations: List of donation dictionaries or single donation dictionary
            
        Returns:
            Enhanced donations with customer matching information
        """
        if not self.qbo_service:
            print("QBO service not available - customer matching skipped")
            return donations
        
        print(f"Matching {len(donations) if isinstance(donations, list) else 1} donation(s) with QBO API")
        
        # Handle both single donation and list of donations
        is_single = not isinstance(donations, list)
        donations_list = [donations] if is_single else donations
        matched_donations = []
        
        for donation in donations_list:
            # Skip if the donation doesn't have the minimum required fields for matching
            if not donation.get('Donor Name'):
                print("Donation missing donor name - skipping customer matching")
                matched_donations.append(donation)
                continue
            
            try:
                # Use the customerLookup field or Donor Name for matching
                customer_lookup = donation.get('customerLookup', donation.get('Donor Name', ''))
                
                if customer_lookup:
                    print(f"Looking up customer: {customer_lookup}")
                    # Use QBO service's find_customer method for direct API matching
                    customer = self.qbo_service.find_customer(customer_lookup)
                    
                    if customer:
                        print(f"Customer found: {customer.get('DisplayName')}")
                        # Compare addresses to detect changes
                        address_match = True
                        if (donation.get('Address - Line 1') and 
                            donation.get('Address - Line 1') != customer.get('BillAddr', {}).get('Line1', '')):
                            address_match = False
                            print("Address mismatch detected")
                        
                        # Update donation with customer information
                        donation['customerLookup'] = customer.get('DisplayName', '')
                        donation['qboCustomerId'] = customer.get('Id')
                        donation['qbCustomerStatus'] = 'Matched' if address_match else 'Matched-AddressMismatch'
                    else:
                        print(f"No customer found for: {customer_lookup}")
                        donation['qbCustomerStatus'] = 'New'
                else:
                    print("No customer lookup information available")
                    donation['qbCustomerStatus'] = 'New'
                
                # Add the matched donation to the result list
                matched_donations.append(donation)
                
            except Exception as e:
                print(f"Error matching donation: {str(e)}")
                # If matching fails, keep the original donation
                matched_donations.append(donation)
        
        # Return in the same format as input
        return matched_donations[0] if is_single else matched_donations
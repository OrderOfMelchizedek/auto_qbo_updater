import os
import json
from typing import Dict, Any, Optional, List, Union
import PyPDF2
from PIL import Image
import io

# Try importing from the src package first
try:
    from src.utils.gemini_service import GeminiService
    from src.utils.prompt_manager import PromptManager
except ModuleNotFoundError:
    # Fall back to relative imports if running directly
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
        self.prompt_manager = PromptManager(prompt_dir='docs/prompts_archive')

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
            missing_fields = [field for field in required_fields if not donation.get(field) or str(donation.get(field, '')).strip().lower() in ['unknown', 'n/a', '']]

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
                reprocessed_list = None
                if file_ext in ['.jpg', '.jpeg', '.png']:
                    reprocessed_list = self.gemini_service.extract_donation_data(file_path, custom_prompt=reprocess_prompt)
                elif file_ext == '.pdf':
                    reprocessed_list = self.gemini_service.extract_donation_data(file_path, custom_prompt=reprocess_prompt)

                if reprocessed_list:
                    # If reprocessing returned a list, take the first item that seems most relevant or complete
                    # This assumes reprocessing focuses on the specific donation needing help
                    reprocessed = reprocessed_list[0] if isinstance(reprocessed_list, list) and len(reprocessed_list) > 0 else None

                    if reprocessed:
                        # Only use the reprocessed data if it found the missing fields
                        still_missing_after_reprocessing = [field for field in missing_fields if not reprocessed.get(field)]

                        if len(still_missing_after_reprocessing) < len(missing_fields):
                            print(f"Reprocessing improved the data - found {len(missing_fields) - len(still_missing_after_reprocessing)} of {len(missing_fields)} missing fields")

                            # Merge the original and reprocessed data, preferring reprocessed for previously missing fields
                            for field in missing_fields:
                                if reprocessed.get(field):
                                    donation[field] = reprocessed[field]
                        else:
                            print(f"Reprocessing did not find any of the missing fields for this donation.")

                # Add the donation to complete list (even if some fields still missing)
                complete_donations.append(donation)

        # Match donations with QuickBooks customers if QBO service is available
        if self.qbo_service:
            print("Performing QBO customer matching for all donations...")
            complete_donations = self.match_donations_with_qbo_customers(complete_donations)

        # Return in the same format as the original data
        if isinstance(donation_data, list):
            return complete_donations
        elif complete_donations: # Check if complete_donations is not empty
            return complete_donations[0] if len(complete_donations) == 1 and not isinstance(donation_data, list) else complete_donations
        else:
            return None # Or original donation_data if no reprocessing was needed and it was singular


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
            donation_data_list = self.gemini_service.extract_text_data(csv_prompt)

            # Match each donation with QuickBooks customers
            if donation_data_list and self.qbo_service:
                donation_data_list = self.match_donations_with_qbo_customers(donation_data_list)

            return donation_data_list

        except Exception as e:
            print(f"Error processing CSV {csv_path}: {str(e)}")
            return None

    def match_donations_with_qbo_customers(self, donations_input: Union[Dict[str, Any], List[Dict[str, Any]]]) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """Match extracted donations with QuickBooks customers using direct QBO API.

        Args:
            donations_input: List of donation dictionaries or single donation dictionary

        Returns:
            Enhanced donations with customer matching information
        """
        if not self.qbo_service:
            print("QBO service not available - customer matching skipped")
            return donations_input

        is_single_input = not isinstance(donations_input, list)
        donations_list = [donations_input] if is_single_input else donations_input
        
        if not donations_list: # Handle empty list case
            return [] if not is_single_input else None

        print(f"Matching {len(donations_list)} donation(s) with QBO API")
        matched_donations_output = []

        for donation in donations_list:
            # Skip if the donation doesn't have the minimum required fields for matching
            if not donation or not donation.get('Donor Name'): # Added check for empty donation
                print("Donation missing or missing donor name - skipping customer matching")
                matched_donations_output.append(donation)
                continue

            try:
                customer = None
                match_method = None
                # Use explicit customerLookup first if available and sensible
                customer_lookup_explicit = donation.get('customerLookup')
                if customer_lookup_explicit and str(customer_lookup_explicit).strip() and str(customer_lookup_explicit).lower() not in ['unknown', 'n/a']:
                    print(f"Trying lookup with explicit customerLookup field: {customer_lookup_explicit}")
                    customer = self.qbo_service.find_customer(str(customer_lookup_explicit))
                    if customer:
                        match_method = 'explicit customerLookup field'
                        print(f"Customer found using {match_method}: {customer.get('DisplayName')}")

                # Fallback strategies if explicit lookup fails or isn't present
                if not customer:
                    lookup_strategies = [
                        {'field': 'Donor Name', 'description': 'donor name'},
                        {'field': 'Email', 'description': 'email address'},
                        {'field': 'Phone', 'description': 'phone number'}
                    ]
                    for strategy in lookup_strategies:
                        field_value = donation.get(strategy['field'])
                        if field_value and str(field_value).strip() and str(field_value).lower() not in ['unknown', 'n/a']:
                            print(f"Trying lookup with {strategy['description']}: {field_value}")
                            potential_customer = self.qbo_service.find_customer(str(field_value))
                            if potential_customer:
                                customer = potential_customer
                                match_method = strategy['description']
                                print(f"Customer found using {match_method}: {customer.get('DisplayName')}")
                                break
                
                if customer:
                    print(f"Verifying match between extracted '{donation.get('Donor Name')}' and QBO '{customer.get('DisplayName')}'")
                    verification_result = self.gemini_service.verify_customer_match(donation, customer)

                    if verification_result and verification_result.get('validMatch', False):
                        print(f"Valid match confirmed for {donation.get('Donor Name')} with {verification_result.get('matchConfidence', 'unknown')} confidence")
                        
                        donation['customerLookup'] = customer.get('DisplayName', '') 
                        donation['qboCustomerId'] = customer.get('Id')
                        donation['matchMethod'] = match_method
                        donation['matchConfidence'] = verification_result.get('matchConfidence')

                        address_populated_from_qbo_or_enhanced = False
                        # Prioritize enhancedData from LLM for address, as it should be the reconciled version
                        if 'enhancedData' in verification_result and verification_result['enhancedData']:
                            enhanced_data = verification_result['enhancedData']
                            print(f"Attempting to use enhancedData for address: {enhanced_data}")
                            if enhanced_data.get('Address - Line 1') and str(enhanced_data.get('Address - Line 1','')).strip().lower() not in ['unknown address', 'address not provided', '']:
                                donation['Address - Line 1'] = enhanced_data.get('Address - Line 1')
                                donation['City'] = enhanced_data.get('City')
                                donation['State'] = enhanced_data.get('State')
                                donation['ZIP'] = enhanced_data.get('ZIP')
                                address_populated_from_qbo_or_enhanced = True
                                print(f"Address for {donation.get('Donor Name')} populated from LLM's enhancedData.")
                        
                        # If enhancedData didn't set a valid address, use QBO BillAddr directly
                        if not address_populated_from_qbo_or_enhanced and 'BillAddr' in customer:
                            bill_addr = customer.get('BillAddr', {})
                            if bill_addr.get('Line1') and str(bill_addr.get('Line1','')).strip().lower() not in ['unknown address', 'address not provided', '']:
                                donation['Address - Line 1'] = bill_addr.get('Line1')
                                donation['City'] = bill_addr.get('City')
                                donation['State'] = bill_addr.get('CountrySubDivisionCode')
                                donation['ZIP'] = bill_addr.get('PostalCode')
                                address_populated_from_qbo_or_enhanced = True
                                print(f"Address for {donation.get('Donor Name')} populated directly from QBO BillAddr.")
                        
                        if not address_populated_from_qbo_or_enhanced:
                            print(f"Address for {donation.get('Donor Name')} remains as originally extracted (or unknown).")

                        # Set UI status based on LLM's material difference assessment
                        if verification_result.get('addressMateriallyDifferent', False):
                            donation['qbCustomerStatus'] = 'Matched-AddressNeedsReview'
                            donation['addressMateriallyDifferent'] = True
                            print(f"Address for {donation.get('Donor Name')} flagged as 'materially different' by LLM, requires review.")
                            if 'BillAddr' in customer: # Store QBO address for UI comparison if needed
                                bill_addr_raw = customer.get('BillAddr', {})
                                donation['qboAddress'] = {
                                    'Line1': bill_addr_raw.get('Line1', ''), 'City': bill_addr_raw.get('City', ''),
                                    'State': bill_addr_raw.get('CountrySubDivisionCode', ''), 'ZIP': bill_addr_raw.get('PostalCode', '')
                                }
                        else:
                            donation['qbCustomerStatus'] = 'Matched'
                            print(f"Address for {donation.get('Donor Name')} considered not materially different by LLM.")

                        # Merge other fields from enhancedData if present, carefully
                        if 'enhancedData' in verification_result and verification_result['enhancedData']:
                            enhanced_data = verification_result['enhancedData']
                            # Fields that should primarily come from the original donation or QBO direct mapping
                            protected_fields = [
                                'Gift Amount', 'Gift Date', 'Check No.', 'Memo', 'dataSource', 'internalId', 
                                'qbSyncStatus', 'qboSalesReceiptId', 'qbCustomerStatus', 'addressMateriallyDifferent', 'qboAddress',
                                'customerLookup', 'qboCustomerId', 'matchMethod', 'matchConfidence',
                                'Address - Line 1', 'City', 'State', 'ZIP' # these are now handled above
                            ]
                            for key, value in enhanced_data.items():
                                if key not in protected_fields:
                                    donation[key] = value
                            # Ensure critical QBO mapping fields are not overwritten if they were in enhancedData
                            donation['customerLookup'] = customer.get('DisplayName', donation.get('customerLookup'))
                            donation['qboCustomerId'] = customer.get('Id', donation.get('qboCustomerId'))


                    elif verification_result: # Valid match is False or verification_result is incomplete
                        mismatch_reason = verification_result.get('mismatchReason', 'LLM verification failed or did not confirm match.')
                        print(f"LLM did not confirm match for {donation.get('Donor Name')} (QBO: {customer.get('DisplayName')}): {mismatch_reason}")
                        donation['qbCustomerStatus'] = 'New' # Treat as new if LLM rejects or fails
                        donation['matchRejectionReason'] = mismatch_reason
                    else: # verification_result itself is None (Gemini call failed)
                         print(f"LLM verification call failed for {donation.get('Donor Name')}. Treating as New.")
                         donation['qbCustomerStatus'] = 'New'
                         donation['matchRejectionReason'] = "LLM verification process failed."

                else: # No customer found by QBO API lookup
                    print(f"No QBO customer found for donation from: {donation.get('Donor Name')}")
                    donation['qbCustomerStatus'] = 'New'
                
                matched_donations_output.append(donation)

            except Exception as e:
                print(f"Error matching donation for '{donation.get('Donor Name', 'Unknown Donor')}': {str(e)}")
                import traceback
                traceback.print_exc()
                # If matching fails, keep the original donation but flag it
                donation['qbCustomerStatus'] = 'ErrorInMatching'
                donation['matchError'] = str(e)
                matched_donations_output.append(donation)
        
        return matched_donations_output[0] if is_single_input and matched_donations_output else matched_donations_output
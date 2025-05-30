import gc
import io
import json
import os
from typing import Any, Dict, List, Optional, Tuple, Union

import PyPDF2
from PIL import Image

from .batch_processor import BatchProcessor
from .gemini_adapter import GeminiAdapter
from .gemini_service import GeminiService
from .memory_monitor import memory_monitor
from .progress_logger import ProgressLogger
from .prompt_manager import PromptManager


class FileProcessor:
    """Service for processing different file types (images, PDFs) for donation extraction."""

    def __init__(self, gemini_service: GeminiService, qbo_service=None, progress_logger=None):
        """Initialize the file processor with Gemini and QBO services.

        Args:
            gemini_service: Service for AI-based extraction
            qbo_service: Optional QuickBooks Online service for customer lookups
            progress_logger: Optional progress logger for tracking batch processing
        """
        self.gemini_service = gemini_service
        self.qbo_service = qbo_service
        self.progress_logger = progress_logger
        self.prompt_manager = PromptManager(prompt_dir="docs/prompts_archive")
        self.batch_processor = BatchProcessor(gemini_service, progress_logger)

    def process(self, file_path: str, file_ext: str) -> Any:
        """Process a file to extract donation information.

        Args:
            file_path: Path to the file
            file_ext: File extension (.jpg, .png, .pdf, .csv, etc.)

        Returns:
            Dictionary containing extracted donation data or
            List of dictionaries (for PDFs/CSVs with multiple donations) or None if extraction failed
        """
        if file_ext in [".jpg", ".jpeg", ".png"]:
            return self._process_with_validation(self._process_image, file_path, file_ext)
        elif file_ext == ".pdf":
            return self._process_with_validation(self._process_pdf, file_path, file_ext)
        elif file_ext == ".csv":
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

        # Critical fields that must be present
        critical_fields = ["Donor Name", "Gift Amount", "Check No."]

        # Nice-to-have fields (we'll try to get these but won't reprocess just for them)
        optional_fields = [
            "Check Date",
            "Address - Line 1",
            "City",
            "State",
            "ZIP",
            "First Name",
            "Last Name",
        ]

        for donation in donations_list:
            # Warn if Check Date equals Deposit Date (likely extraction error)
            if donation.get("Check Date") and donation.get("Deposit Date"):
                if donation["Check Date"] == donation["Deposit Date"]:
                    print(
                        f"WARNING: Check Date equals Deposit Date ({donation['Check Date']}) for {donation.get('Donor Name', 'Unknown')} - this may be incorrect!"
                    )

            # Check for missing critical fields
            missing_critical = [field for field in critical_fields if not donation.get(field)]

            if missing_critical:
                # Critical fields are missing - must reprocess
                print(f"Donation has missing CRITICAL fields: {', '.join(missing_critical)}. Queuing for reprocessing.")
                donations_to_reprocess.append({"donation": donation, "missing_fields": missing_critical})
            else:
                # Check optional fields just for logging
                missing_optional = [field for field in optional_fields if not donation.get(field)]
                if missing_optional:
                    print(f"Donation missing optional fields: {', '.join(missing_optional)}. Skipping reprocessing.")

                # All critical fields are present - add to complete list
                complete_donations.append(donation)

        # If we have donations needing reprocessing, send them back to Gemini
        if donations_to_reprocess:
            for item in donations_to_reprocess:
                donation = item["donation"]
                missing_fields = item["missing_fields"]

                # Use prompt manager to get reprocessing prompt with placeholders replaced
                reprocess_prompt = self.prompt_manager.get_prompt(
                    "simplified_reprocess",
                    {
                        "partial_data": json.dumps(donation, indent=2),
                        "missing_fields": ", ".join(missing_fields),
                    },
                )

                print(f"Reprocessing donation to find missing fields: {missing_fields}")

                # Reprocess the document with focused prompt
                if file_ext in [".jpg", ".jpeg", ".png"]:
                    reprocessed = self.gemini_service.extract_donation_data(file_path, custom_prompt=reprocess_prompt)
                elif file_ext == ".pdf":
                    reprocessed = self.gemini_service.extract_donation_data(file_path, custom_prompt=reprocess_prompt)

                if reprocessed:
                    # If reprocessing returned a list, we need to find the matching donation
                    if isinstance(reprocessed, list) and len(reprocessed) > 0:
                        # Try to match the reprocessed donation with the original
                        matched_reprocessed = None
                        donor_name = donation.get("Donor Name", "").lower()
                        check_no = str(donation.get("Check No.", "")).strip()

                        for r in reprocessed:
                            r_donor = r.get("Donor Name", "").lower()
                            r_check = str(r.get("Check No.", "")).strip()

                            # Match by donor name and/or check number
                            if (donor_name and donor_name in r_donor or r_donor in donor_name) or (
                                check_no and check_no == r_check
                            ):
                                matched_reprocessed = r
                                break

                        # If we found a match, use it. Otherwise, skip reprocessing for this donation
                        if matched_reprocessed:
                            reprocessed = matched_reprocessed
                        else:
                            print(f"Could not match reprocessed donation to original for {donation.get('Donor Name')}")
                            reprocessed = None

                    # Only use the reprocessed data if it found the missing fields
                    still_missing = [field for field in missing_fields if not reprocessed.get(field)]

                    if len(still_missing) < len(missing_fields):
                        print(
                            f"Reprocessing improved the data - found {len(missing_fields) - len(still_missing)} of {len(missing_fields)} missing fields"
                        )

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
            complete_donations = self.match_donations_with_qbo_customers_batch(complete_donations)

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

    @memory_monitor.monitor_function
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

            # Force garbage collection after PDF processing
            gc.collect()

            return donation_data

        except Exception as e:
            print(f"Error processing PDF {pdf_path}: {str(e)}")
            return None
        finally:
            # Ensure cleanup happens even on error
            gc.collect()

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
            encodings = ["utf-8-sig", "utf-8", "latin-1", "cp1252"]
            csv_content = None

            # Try different encodings
            for encoding in encodings:
                try:
                    with open(csv_path, "r", encoding=encoding) as f:
                        csv_content = f.read()
                    print(f"Successfully read CSV with encoding: {encoding}")
                    break
                except UnicodeDecodeError:
                    continue

            if not csv_content:
                raise ValueError(f"Unable to read CSV file with any of these encodings: {encodings}")

            print(f"CSV content sample: {csv_content[:500]}")

            # Use prompt manager to get CSV extraction prompt with placeholder replaced
            csv_prompt = self.prompt_manager.get_prompt("simplified_csv_prompt", {"csv_content": csv_content})

            # Send CSV text to Gemini for processing
            donation_data = self.gemini_service.extract_text_data(csv_prompt)

            # Match each donation with QuickBooks customers
            if donation_data and self.qbo_service:
                donation_data = self.match_donations_with_qbo_customers_batch(donation_data)

            return donation_data

        except Exception as e:
            print(f"Error processing CSV {csv_path}: {str(e)}")
            return None

    # We no longer need to get all customers, as we're using direct QBO API lookups

    def match_donations_with_qbo_customers_batch(self, donations):
        """Match donations with existing QBO customers using batch processing for performance.

        Args:
            donations: List of donation dictionaries or single donation dictionary

        Returns:
            Enhanced donations with customer matching information
        """
        if not self.qbo_service:
            print("QBO service not available - customer matching skipped")
            return donations

        # Handle both single donation and list of donations
        is_single = not isinstance(donations, list)
        donations_list = [donations] if is_single else donations

        print(f"Batch matching {len(donations_list)} donation(s) with QBO API")

        # Step 1: Pre-load QBO customer cache for better performance
        try:
            self.qbo_service.get_all_customers(use_cache=True)
            print("Customer cache preloaded successfully")
        except Exception as e:
            print(f"Warning: Could not preload customer cache: {e}")

        # Step 2: Collect all unique lookup values
        all_lookups = set()
        donation_to_lookups = {}

        for i, donation in enumerate(donations_list):
            if not donation.get("Donor Name"):
                donation_to_lookups[i] = []
                continue

            # Skip if already matched
            if donation.get("qbCustomerStatus") in ["Matched", "Matched-AddressMismatch", "Matched-AddressNeedsReview"]:
                donation_to_lookups[i] = []
                continue

            # Collect lookup strategies for this donation
            lookups = []
            lookup_strategies = ["customerLookup", "Donor Name", "Email", "Phone"]

            for field in lookup_strategies:
                value = donation.get(field)
                if value and str(value).strip():
                    clean_value = str(value).strip()
                    lookups.append(clean_value)
                    all_lookups.add(clean_value)

            donation_to_lookups[i] = lookups

        # Step 3: Batch lookup all unique customer names
        print(f"Looking up {len(all_lookups)} unique customer values")
        customer_results = self.qbo_service.find_customers_batch(list(all_lookups))

        # Step 4: Process each donation with pre-fetched results
        matched_donations = []

        for i, donation in enumerate(donations_list):
            if not donation.get("Donor Name"):
                print("Donation missing donor name - skipping customer matching")
                matched_donations.append(donation)
                continue

            # Skip if already matched
            if donation.get("qbCustomerStatus") in ["Matched", "Matched-AddressMismatch", "Matched-AddressNeedsReview"]:
                print(f"Donation already matched to customer ID {donation.get('qboCustomerId')} - skipping")
                matched_donations.append(donation)
                continue

            try:
                # Find the first successful match from the batch results
                customer = None
                match_method = None

                for lookup_value in donation_to_lookups[i]:
                    potential_customer = customer_results.get(lookup_value)
                    if potential_customer:
                        customer = potential_customer
                        # Determine match method
                        if lookup_value == donation.get("customerLookup"):
                            match_method = "explicit customerLookup field"
                        elif lookup_value == donation.get("Donor Name"):
                            match_method = "donor name"
                        elif lookup_value == donation.get("Email"):
                            match_method = "email address"
                        elif lookup_value == donation.get("Phone"):
                            match_method = "phone number"
                        else:
                            match_method = "unknown field"

                        print(f"Customer found using {match_method}: {customer.get('DisplayName')}")
                        break

                if customer:
                    print(f"Verifying match between {donation.get('Donor Name')} and {customer.get('DisplayName')}")

                    try:
                        # Use Gemini to verify the match and enhance the data
                        verification_result = self.gemini_service.verify_customer_match(donation, customer)
                    except Exception as verify_error:
                        print(f"Error during verification: {str(verify_error)}")
                        # If verification fails, still mark as matched but needs review
                        donation["customerLookup"] = customer.get("DisplayName", "")
                        donation["qboCustomerId"] = customer.get("Id")
                        donation["matchMethod"] = match_method
                        donation["qbCustomerStatus"] = "Matched-AddressNeedsReview"
                        donation["matchRejectionReason"] = f"Error during verification: {str(verify_error)}"

                        # Include QBO address if available
                        if "BillAddr" in customer:
                            bill_addr = customer.get("BillAddr", {})
                            donation["qboAddress"] = {
                                "Line1": bill_addr.get("Line1", ""),
                                "City": bill_addr.get("City", ""),
                                "State": bill_addr.get("CountrySubDivisionCode", ""),
                                "ZIP": bill_addr.get("PostalCode", ""),
                            }

                        matched_donations.append(donation)
                        continue

                    # Process verification result (same logic as before)
                    if verification_result.get("validMatch", False):
                        print(
                            f"Valid match confirmed with {verification_result.get('matchConfidence', 'unknown')} confidence"
                        )

                        donation["customerLookup"] = customer.get("DisplayName", "")
                        donation["qboCustomerId"] = customer.get("Id")
                        donation["matchMethod"] = match_method
                        donation["matchConfidence"] = verification_result.get("matchConfidence")

                        # Clear any previous rejection reason since this is a valid match
                        if "matchRejectionReason" in donation:
                            del donation["matchRejectionReason"]

                        if verification_result.get("addressMateriallyDifferent", False):
                            print("Address is materially different - will need user confirmation")
                            donation["qbCustomerStatus"] = "Matched-AddressNeedsReview"
                            donation["addressMateriallyDifferent"] = True

                            if "BillAddr" in customer:
                                bill_addr = customer.get("BillAddr", {})
                                donation["qboAddress"] = {
                                    "Line1": bill_addr.get("Line1", ""),
                                    "City": bill_addr.get("City", ""),
                                    "State": bill_addr.get("CountrySubDivisionCode", ""),
                                    "ZIP": bill_addr.get("PostalCode", ""),
                                }
                        else:
                            donation["qbCustomerStatus"] = "Matched"

                            if "enhancedData" in verification_result:
                                preserved_fields = ["Gift Amount", "Gift Date", "Check No", "Memo"]
                                preserved_values = {
                                    field: donation.get(field) for field in preserved_fields if field in donation
                                }

                                enhanced_data = verification_result["enhancedData"]
                                for key, value in enhanced_data.items():
                                    donation[key] = value

                                for field, value in preserved_values.items():
                                    donation[field] = value

                                donation["customerLookup"] = customer.get("DisplayName", "")
                    else:
                        mismatch_reason = verification_result.get("mismatchReason", "No specific reason provided")
                        print(f"Not a valid match: {mismatch_reason}")
                        donation["qbCustomerStatus"] = "New"
                        donation["matchRejectionReason"] = mismatch_reason
                else:
                    print(f"No customer found for donation from: {donation.get('Donor Name')}")
                    donation["qbCustomerStatus"] = "New"

                matched_donations.append(donation)

            except Exception as e:
                print(f"Error matching donation: {str(e)}")
                # Ensure status is set even on error
                if "qbCustomerStatus" not in donation:
                    donation["qbCustomerStatus"] = "New"
                matched_donations.append(donation)

        return matched_donations[0] if is_single else matched_donations

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
            if not donation.get("Donor Name"):
                print("Donation missing donor name - skipping customer matching")
                matched_donations.append(donation)
                continue

            # Skip if already matched
            if donation.get("qbCustomerStatus") in ["Matched", "Matched-AddressMismatch", "Matched-AddressNeedsReview"]:
                print(f"Donation already matched to customer ID {donation.get('qboCustomerId')} - skipping")
                matched_donations.append(donation)
                continue

            try:
                # Try multiple lookup strategies for better matching
                customer = None
                match_method = None
                lookup_strategies = [
                    # Strategy 1: Use explicit customerLookup field if available
                    {"field": "customerLookup", "description": "explicit customerLookup field"},
                    # Strategy 2: Use donor name
                    {"field": "Donor Name", "description": "donor name"},
                    # Strategy 3: Use email if available
                    {"field": "Email", "description": "email address"},
                    # Strategy 4: Use phone if available
                    {"field": "Phone", "description": "phone number"},
                ]

                for strategy in lookup_strategies:
                    field = strategy["field"]
                    lookup_value = donation.get(field)

                    if lookup_value and str(lookup_value).strip():
                        print(f"Trying lookup with {strategy['description']}: {lookup_value}")
                        potential_customer = self.qbo_service.find_customer(str(lookup_value))

                        if potential_customer:
                            customer = potential_customer
                            match_method = strategy["description"]
                            print(f"Customer found using {match_method}: {customer.get('DisplayName')}")
                            break

                if customer:
                    print(f"Verifying match between {donation.get('Donor Name')} and {customer.get('DisplayName')}")

                    try:
                        # Use Gemini to verify the match and enhance the data
                        verification_result = self.gemini_service.verify_customer_match(donation, customer)
                    except Exception as verify_error:
                        print(f"Error during verification: {str(verify_error)}")
                        # If verification fails, still mark as matched but needs review
                        donation["customerLookup"] = customer.get("DisplayName", "")
                        donation["qboCustomerId"] = customer.get("Id")
                        donation["matchMethod"] = match_method
                        donation["qbCustomerStatus"] = "Matched-AddressNeedsReview"
                        donation["matchRejectionReason"] = f"Error during verification: {str(verify_error)}"

                        # Include QBO address if available
                        if "BillAddr" in customer:
                            bill_addr = customer.get("BillAddr", {})
                            donation["qboAddress"] = {
                                "Line1": bill_addr.get("Line1", ""),
                                "City": bill_addr.get("City", ""),
                                "State": bill_addr.get("CountrySubDivisionCode", ""),
                                "ZIP": bill_addr.get("PostalCode", ""),
                            }

                        matched_donations.append(donation)
                        continue

                    # First, check if this is a valid match according to Gemini
                    if verification_result.get("validMatch", False):
                        print(
                            f"Valid match confirmed with {verification_result.get('matchConfidence', 'unknown')} confidence"
                        )

                        # Update donation with customer information
                        donation["customerLookup"] = customer.get("DisplayName", "")
                        donation["qboCustomerId"] = customer.get("Id")
                        donation["matchMethod"] = match_method
                        donation["matchConfidence"] = verification_result.get("matchConfidence")

                        # Clear any previous rejection reason since this is a valid match
                        if "matchRejectionReason" in donation:
                            del donation["matchRejectionReason"]

                        # Check if address is materially different (requiring user attention)
                        if verification_result.get("addressMateriallyDifferent", False):
                            print("Address is materially different - will need user confirmation")
                            donation["qbCustomerStatus"] = "Matched-AddressNeedsReview"
                            donation["addressMateriallyDifferent"] = True

                            # Preserve both address versions for user to choose
                            if "BillAddr" in customer:
                                bill_addr = customer.get("BillAddr", {})
                                donation["qboAddress"] = {
                                    "Line1": bill_addr.get("Line1", ""),
                                    "City": bill_addr.get("City", ""),
                                    "State": bill_addr.get("CountrySubDivisionCode", ""),
                                    "ZIP": bill_addr.get("PostalCode", ""),
                                }
                        else:
                            # Address is not materially different, use the enhanced data
                            donation["qbCustomerStatus"] = "Matched"

                            # Update the donation with the enhanced data from verification
                            if "enhancedData" in verification_result:
                                # Replace the donation with the enhanced data, but preserve
                                # any fields that should always come from the extracted data
                                preserved_fields = ["Gift Amount", "Gift Date", "Check No", "Memo"]
                                preserved_values = {
                                    field: donation.get(field) for field in preserved_fields if field in donation
                                }

                                # Update with enhanced data
                                enhanced_data = verification_result["enhancedData"]
                                for key, value in enhanced_data.items():
                                    donation[key] = value

                                # Restore preserved fields
                                for field, value in preserved_values.items():
                                    donation[field] = value

                                # Ensure customerLookup is always set to QBO DisplayName
                                # (in case it was overwritten by enhancedData)
                                donation["customerLookup"] = customer.get("DisplayName", "")
                    else:
                        # This is not a valid match despite the fuzzy matching
                        mismatch_reason = verification_result.get("mismatchReason", "No specific reason provided")
                        print(f"Not a valid match: {mismatch_reason}")
                        donation["qbCustomerStatus"] = "New"
                        donation["matchRejectionReason"] = mismatch_reason
                else:
                    print(f"No customer found for donation from: {donation.get('Donor Name')}")
                    donation["qbCustomerStatus"] = "New"

                # Add the matched donation to the result list
                matched_donations.append(donation)

            except Exception as e:
                print(f"Error matching donation: {str(e)}")
                # If matching fails, ensure status is set and keep the original donation
                if "qbCustomerStatus" not in donation:
                    donation["qbCustomerStatus"] = "New"
                matched_donations.append(donation)

        # Return in the same format as input
        return matched_donations[0] if is_single else matched_donations

    @memory_monitor.monitor_function
    def process_files_concurrently(
        self, files: List[Tuple[str, str]], task_id: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], List[str]]:
        """Process multiple files concurrently using batch processing.

        Args:
            files: List of tuples (file_path, file_type)
            task_id: Optional task ID for progress tracking

        Returns:
            Tuple of (all_donations, all_errors)
        """
        try:
            # Log initial memory state
            memory_monitor.log_memory_usage("Start of concurrent processing")

            # Prepare batches from all files
            print(f"Preparing batches for {len(files)} files")
            batches = self.batch_processor.prepare_batches(files)
            print(f"Created {len(batches)} batches for concurrent processing")

            # Process all batches concurrently
            all_donations, all_errors = self.batch_processor.process_batches_concurrently(batches, task_id)

            # Force cleanup after batch processing
            gc.collect()
            memory_monitor.log_memory_usage("After batch processing")

            # Perform validation and reprocessing on all donations
            if all_donations:
                print(f"Validating and enhancing {len(all_donations)} donations")
                validated_donations = []

                # Critical fields that must be present
                critical_fields = ["Donor Name", "Gift Amount", "Check No."]

                for donation in all_donations:
                    # Check for missing critical fields
                    missing_critical = [field for field in critical_fields if not donation.get(field)]

                    if missing_critical:
                        # Critical fields are missing - reject this donation
                        error_msg = f"Donation rejected - missing critical fields: {', '.join(missing_critical)}. Donor: {donation.get('Donor Name', 'Unknown')}"
                        print(error_msg)
                        all_errors.append(error_msg)
                    else:
                        # All critical fields present - add to validated list
                        validated_donations.append(donation)

                # Deduplicate all donations after batch processing
                print(f"Deduplicating {len(validated_donations)} donations")
                deduplicated = self._deduplicate_donations(validated_donations)

                # Match with QBO customers - but only for donations that haven't been matched yet
                if self.qbo_service and deduplicated:
                    # Count how many are already matched
                    already_matched = sum(
                        1
                        for d in deduplicated
                        if d.get("qbCustomerStatus")
                        in ["Matched", "Matched-AddressMismatch", "Matched-AddressNeedsReview"]
                    )
                    unmatched_count = len(deduplicated) - already_matched

                    if unmatched_count > 0:
                        print(
                            f"Matching {unmatched_count} unmatched donations with QBO customers ({already_matched} already matched)"
                        )
                        deduplicated = self.match_donations_with_qbo_customers_batch(deduplicated)

                return deduplicated, all_errors

            return [], all_errors

        except Exception as e:
            error_msg = f"Error in concurrent file processing: {str(e)}"
            print(error_msg)
            return [], [error_msg]
        finally:
            # Always cleanup after processing
            gc.collect()
            memory_monitor.log_memory_usage("End of concurrent processing")

    def _deduplicate_donations(self, donations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Deduplicate donations based on key fields.

        Args:
            donations: List of donation dictionaries

        Returns:
            List of unique donations
        """
        seen = {}
        unique_donations = []

        # Critical fields that must be present (safety check)
        critical_fields = ["Donor Name", "Gift Amount", "Check No."]

        for donation in donations:
            # Final safety check - skip donations missing critical fields
            missing_critical = [field for field in critical_fields if not donation.get(field)]
            if missing_critical:
                print(
                    f"WARNING: Skipping invalid donation during deduplication - missing: {', '.join(missing_critical)}"
                )
                continue

            # Create a key based on donor name, amount, check date, and check number
            key = (
                donation.get("Donor Name", "").lower().strip(),
                donation.get("Gift Amount", ""),
                donation.get("Check Date", ""),  # Use Check Date instead of Gift Date
                donation.get("Check No.", ""),
            )

            if key not in seen:
                seen[key] = donation
                unique_donations.append(donation)
            else:
                # Merge duplicate donations, keeping the most complete data
                existing = seen[key]
                for field, value in donation.items():
                    if value and not existing.get(field):
                        existing[field] = value

        return unique_donations

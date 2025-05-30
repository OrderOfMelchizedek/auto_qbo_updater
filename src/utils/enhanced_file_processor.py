"""
Enhanced file processor that integrates QBO data enrichment and payment combining.
This module extends the existing FileProcessor with new capabilities.
"""

import logging
import os
from typing import Any, Dict, List, Optional, Tuple

from .file_processor import FileProcessor
from .payment_combiner import PaymentCombiner
from .qbo_data_enrichment import QBODataEnrichment

logger = logging.getLogger(__name__)


class EnhancedFileProcessor(FileProcessor):
    """Enhanced file processor with QBO data enrichment capabilities."""

    def __init__(self, gemini_service, qbo_service=None, progress_logger=None):
        """Initialize enhanced file processor.

        Args:
            gemini_service: Service for AI-based extraction
            qbo_service: Optional QuickBooks Online service
            progress_logger: Optional progress logger
        """
        super().__init__(gemini_service, qbo_service, progress_logger)
        self.qbo_enrichment = QBODataEnrichment()
        self.payment_combiner = PaymentCombiner(self.qbo_enrichment)

    def match_donations_with_qbo_customers_batch_enhanced(self, donations):
        """Enhanced version that pulls all QBO fields and enriches data.

        Args:
            donations: List of donation dictionaries or single donation

        Returns:
            Enhanced donations with full QBO data and comparison results
        """
        if not self.qbo_service:
            logger.warning("QBO service not available - customer matching skipped")
            return donations

        # Handle both single donation and list of donations
        is_single = not isinstance(donations, list)
        donations_list = [donations] if is_single else donations

        logger.info(f"Enhanced batch matching {len(donations_list)} donation(s) with QBO API")

        # Use parent class method to do the matching
        matched_donations = super().match_donations_with_qbo_customers_batch(donations)

        # Ensure we have a list
        matched_list = [matched_donations] if is_single else matched_donations

        # Now enhance each matched donation with full QBO data
        enhanced_donations = []

        for donation in matched_list:
            if donation.get("qboCustomerId"):
                # Fetch full customer data from QBO
                try:
                    customer = self.qbo_service.get_customer_by_id(donation["qboCustomerId"])
                    if customer:
                        # Extract all QBO fields
                        qbo_data = self.qbo_enrichment.extract_qbo_customer_data(customer)

                        # Add all QBO fields to donation
                        donation.update(
                            {
                                "qbo_first_name": qbo_data["first_name"],
                                "qbo_last_name": qbo_data["last_name"],
                                "qbo_full_name": qbo_data["full_name"],
                                "qbo_organization_name": qbo_data["qb_organization_name"],
                                "qbo_address_line_1": qbo_data["qb_address_line_1"],
                                "qbo_city": qbo_data["qb_city"],
                                "qbo_state": qbo_data["qb_state"],
                                "qbo_zip": qbo_data["qb_zip"],
                                "qbo_email": qbo_data["qb_email"],
                                "qbo_phone": qbo_data["qb_phone"],
                                "qbo_sync_token": qbo_data["qbo_sync_token"],
                            }
                        )

                        # Compare addresses
                        extracted_addr = {
                            "address_line_1": donation.get("Address - Line 1", ""),
                            "city": donation.get("City", ""),
                            "state": donation.get("State", ""),
                            "zip": donation.get("ZIP", ""),
                        }

                        address_comparison = self.qbo_enrichment.compare_addresses(extracted_addr, qbo_data)

                        donation["address_needs_update"] = address_comparison["address_needs_update"]
                        if address_comparison["address_needs_update"]:
                            donation["address_differences"] = address_comparison["differences"]
                            donation["address_similarity"] = address_comparison["similarity_score"]

                        # Handle email/phone updates
                        email_phone_result = self.qbo_enrichment.merge_email_phone_lists(
                            donation.get("Email"), donation.get("Phone"), qbo_data["qb_email"], qbo_data["qb_phone"]
                        )

                        donation["merged_emails"] = email_phone_result["emails"]
                        donation["merged_phones"] = email_phone_result["phones"]
                        donation["email_updated"] = email_phone_result["email_added"]
                        donation["phone_updated"] = email_phone_result["phone_added"]

                except Exception as e:
                    logger.error(f"Error fetching full customer data: {e}")
                    # Keep the basic match data even if full fetch fails

            enhanced_donations.append(donation)

        return enhanced_donations[0] if is_single else enhanced_donations

    def process_files_concurrently_with_enrichment(
        self, files: List[Tuple[str, str]], task_id: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], List[str]]:
        """Process files with full QBO enrichment and final JSON formatting.

        Args:
            files: List of tuples (file_path, file_type)
            task_id: Optional task ID for progress tracking

        Returns:
            Tuple of (combined_payment_data, errors)
        """
        # Use parent class to process files
        deduplicated, errors = super().process_files_concurrently(files, task_id)

        if not deduplicated:
            return [], errors

        # Replace the basic matching with enhanced matching
        if self.qbo_service:
            logger.info(f"Performing enhanced customer matching for {len(deduplicated)} payments...")

            # Remove the basic matching that was already done
            # We'll redo it with enhanced version
            for donation in deduplicated:
                # Clear any existing match data
                match_fields = [
                    "customerLookup",
                    "qboCustomerId",
                    "matchMethod",
                    "qbCustomerStatus",
                    "matchConfidence",
                    "qboAddress",
                ]
                for field in match_fields:
                    donation.pop(field, None)

            # Perform enhanced matching
            enriched = self.match_donations_with_qbo_customers_batch_enhanced(deduplicated)

            # Convert to final combined format
            logger.info("Converting to final payment format...")
            combined_payments = self.payment_combiner.process_batch(enriched)

            # Log summary
            matched_count = sum(1 for p in combined_payments if p["match_status"] != "New")
            update_count = sum(1 for p in combined_payments if p["payer_info"].get("address_needs_update"))

            logger.info(
                f"Processing complete: {len(combined_payments)} payments, "
                f"{matched_count} matched, {update_count} need address updates"
            )

            return combined_payments, errors
        else:
            # No QBO service - convert to final format without enrichment
            logger.info("Converting to final format without QBO enrichment...")
            combined_payments = self.payment_combiner.process_batch(deduplicated)
            return combined_payments, errors

    def process_files_concurrently(
        self, files: List[Tuple[str, str]], task_id: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], List[str]]:
        """Override parent method to use enrichment by default.

        This ensures all file processing uses the enhanced flow with QBO enrichment.

        Args:
            files: List of tuples (file_path, file_type)
            task_id: Optional task ID for progress tracking

        Returns:
            Tuple of (combined_payment_data, errors)
        """
        # Check if we should return legacy format (for backward compatibility)
        use_legacy_format = os.environ.get("USE_LEGACY_FORMAT", "true").lower() == "true"

        if use_legacy_format:
            # Process with enrichment but convert back to legacy format
            combined_payments, errors = self.process_files_concurrently_with_enrichment(files, task_id)

            # Convert to legacy format
            if combined_payments:
                legacy_payments = []
                for payment in combined_payments:
                    legacy = self.payment_combiner.convert_to_legacy_format(payment)
                    legacy_payments.append(legacy)
                return legacy_payments, errors
            return combined_payments, errors
        else:
            # Return new enriched format
            return self.process_files_concurrently_with_enrichment(files, task_id)

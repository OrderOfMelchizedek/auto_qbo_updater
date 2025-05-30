"""
Enhanced file processor V3 that uses unified batching for all files.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from ..models.payment import PaymentRecord
from .alias_matcher import AliasMatcher
from .gemini_adapter_v3 import GeminiAdapterV3
from .payment_combiner_v2 import PaymentCombinerV2
from .qbo_data_enrichment import QBODataEnrichment

logger = logging.getLogger(__name__)


class EnhancedFileProcessorV3:
    """File processor that uses unified batching for better accuracy."""

    def __init__(self, gemini_service: GeminiAdapterV3, qbo_service=None):
        """Initialize the enhanced file processor.

        Args:
            gemini_service: GeminiAdapterV3 instance for extraction
            qbo_service: Optional QBO service for customer matching
        """
        self.gemini_service = gemini_service
        self.qbo_service = qbo_service
        self.alias_matcher = AliasMatcher(qbo_service) if qbo_service else None
        self.qbo_enrichment = QBODataEnrichment()
        self.payment_combiner = PaymentCombinerV2(self.qbo_enrichment)

    def process_files(self, files: List[Tuple[str, str]]) -> Tuple[List[Dict[str, Any]], List[str]]:
        """Process multiple files and return enriched payment data.

        Args:
            files: List of tuples (file_path, file_type)

        Returns:
            Tuple of (enriched_payments, errors)
        """
        errors = []

        # Step 1: Extract payments from all files together in unified batches
        logger.info(f"Extracting payments from {len(files)} files using unified batching...")

        # Collect all file paths
        file_paths = [file_path for file_path, _ in files]

        try:
            # Extract all payments in one call with unified batching
            all_payments = self.gemini_service.extract_payments_batch(file_paths)
            logger.info(f"Extracted {len(all_payments)} total payments")
        except Exception as e:
            error_msg = f"Error in batch extraction: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)
            return [], errors

        if not all_payments:
            logger.warning("No payments extracted from any files")
            return [], errors

        # Step 2: Deduplicate payments
        logger.info(f"Deduplicating {len(all_payments)} payments...")
        deduplicated = self._deduplicate_payments(all_payments)
        logger.info(f"After deduplication: {len(deduplicated)} unique payments")

        # Step 3: Match with QBO customers using aliases
        if self.alias_matcher:
            logger.info("Matching payments with QBO customers using aliases...")
            matched_payments = self.alias_matcher.match_payment_batch(deduplicated)
        else:
            logger.warning("No QBO service available - skipping customer matching")
            matched_payments = [(payment, None) for payment in deduplicated]

        # Step 4: Enrich and combine data
        logger.info("Enriching payment data...")
        enriched_payments = []

        for payment_record, qbo_customer in matched_payments:
            if qbo_customer:
                # Fetch full customer data if needed
                customer_id = qbo_customer.get("Id")
                if customer_id and self.qbo_service:
                    try:
                        # Get latest customer data
                        full_customer = self.qbo_service.get_customer_by_id(customer_id)
                        if full_customer:
                            qbo_customer = full_customer
                    except Exception as e:
                        logger.warning(f"Could not fetch full customer data: {e}")

                # Create enriched payment with QBO data
                enriched = self.payment_combiner.combine_payment_data(
                    payment_record, qbo_customer, match_status="Matched"
                )
            else:
                # No match - create new customer entry
                enriched = self.payment_combiner.combine_payment_data(payment_record, None, match_status="New")

            enriched_payments.append(enriched)

        # Log summary
        matched_count = sum(1 for p in enriched_payments if p["match_status"] == "Matched")
        needs_update = sum(1 for p in enriched_payments if p["payer_info"].get("address_needs_update"))

        logger.info(f"Processing complete: {len(enriched_payments)} payments")
        logger.info(f"  - Matched: {matched_count}")
        logger.info(f"  - New: {len(enriched_payments) - matched_count}")
        logger.info(f"  - Address updates needed: {needs_update}")

        return enriched_payments, errors

    def _deduplicate_payments(self, payments: List[PaymentRecord]) -> List[PaymentRecord]:
        """Deduplicate payment records, merging when necessary.

        Args:
            payments: List of PaymentRecord objects

        Returns:
            Deduplicated list of PaymentRecord objects
        """
        # Group payments by their unique key
        payment_groups = {}
        unkeyed_payments = []

        for payment in payments:
            # Create unique key
            if payment.payment_info.check_no:
                key = f"CHECK_{payment.payment_info.check_no}_{payment.payment_info.amount}"
            elif payment.payment_info.payment_ref:
                key = f"REF_{payment.payment_info.payment_ref}_{payment.payment_info.amount}"
            else:
                # No unique identifier - needs special handling
                # For now, add to unkeyed list
                unkeyed_payments.append(payment)
                continue

            if key not in payment_groups:
                payment_groups[key] = []
            payment_groups[key].append(payment)

        # Process each group
        deduplicated = []

        for key, group in payment_groups.items():
            if len(group) == 1:
                # No duplicates
                deduplicated.append(group[0])
            else:
                # Multiple payments with same key - merge them
                logger.info(f"Merging {len(group)} payments with key: {key}")
                merged = self._merge_payment_records(group)
                deduplicated.append(merged)

        # Add unkeyed payments (can't deduplicate without identifiers)
        if unkeyed_payments:
            logger.warning(f"Found {len(unkeyed_payments)} payments without check/ref numbers")
            deduplicated.extend(unkeyed_payments)

        return deduplicated

    def _merge_payment_records(self, payments: List[PaymentRecord]) -> PaymentRecord:
        """Merge multiple payment records into one, keeping the most complete data.

        Args:
            payments: List of PaymentRecord objects to merge

        Returns:
            Merged PaymentRecord
        """
        # Start with the first payment as base
        merged = payments[0]

        # Merge data from other payments
        for payment in payments[1:]:
            # Merge payment info (prefer non-null values)
            if payment.payment_info.check_date and not merged.payment_info.check_date:
                merged.payment_info.check_date = payment.payment_info.check_date
            if payment.payment_info.deposit_date and not merged.payment_info.deposit_date:
                merged.payment_info.deposit_date = payment.payment_info.deposit_date
            if payment.payment_info.postmark_date and not merged.payment_info.postmark_date:
                merged.payment_info.postmark_date = payment.payment_info.postmark_date
            if payment.payment_info.memo and not merged.payment_info.memo:
                merged.payment_info.memo = payment.payment_info.memo

            # Merge payer info (prefer the one with more data)
            if payment.payer_info.organization_name and not merged.payer_info.organization_name:
                merged.payer_info.organization_name = payment.payer_info.organization_name
            if payment.payer_info.aliases and not merged.payer_info.aliases:
                merged.payer_info.aliases = payment.payer_info.aliases
            elif payment.payer_info.aliases and merged.payer_info.aliases:
                # Merge alias lists
                all_aliases = set(merged.payer_info.aliases + payment.payer_info.aliases)
                merged.payer_info.aliases = sorted(list(all_aliases))

            # Merge contact info (prefer non-null values)
            if payment.contact_info.address_line_1 and not merged.contact_info.address_line_1:
                merged.contact_info.address_line_1 = payment.contact_info.address_line_1
            if payment.contact_info.city and not merged.contact_info.city:
                merged.contact_info.city = payment.contact_info.city
            if payment.contact_info.state and not merged.contact_info.state:
                merged.contact_info.state = payment.contact_info.state
            if payment.contact_info.zip and not merged.contact_info.zip:
                merged.contact_info.zip = payment.contact_info.zip
            if payment.contact_info.email and not merged.contact_info.email:
                merged.contact_info.email = payment.contact_info.email
            if payment.contact_info.phone and not merged.contact_info.phone:
                merged.contact_info.phone = payment.contact_info.phone

        return merged

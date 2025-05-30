"""
Enhanced file processor V2 that works with PaymentRecord objects throughout.
No legacy format conversions, no Gemini verification calls.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from ..models.payment import PaymentRecord
from ..services.deduplication import DeduplicationService
from .alias_matcher import AliasMatcher
from .gemini_adapter_v2 import GeminiAdapterV2
from .payment_combiner_v2 import PaymentCombinerV2
from .qbo_data_enrichment import QBODataEnrichment

logger = logging.getLogger(__name__)


class EnhancedFileProcessorV2:
    """File processor that maintains PaymentRecord objects throughout the pipeline."""

    def __init__(self, gemini_service: GeminiAdapterV2, qbo_service=None):
        """Initialize the enhanced file processor.

        Args:
            gemini_service: GeminiAdapterV2 instance for extraction
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
        all_payments = []
        errors = []

        # Step 1: Extract payments from all files
        logger.info(f"Extracting payments from {len(files)} files...")
        for file_path, file_type in files:
            try:
                # Extract PaymentRecord objects
                payment_records = self.gemini_service.extract_payments(file_path)
                all_payments.extend(payment_records)
                logger.info(f"Extracted {len(payment_records)} payments from {file_path}")
            except Exception as e:
                error_msg = f"Error extracting from {file_path}: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)

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
        """Deduplicate payment records.

        Args:
            payments: List of PaymentRecord objects

        Returns:
            Deduplicated list of PaymentRecord objects
        """
        # For now, use a simple deduplication based on check number and amount
        # This maintains PaymentRecord objects
        seen = set()
        deduplicated = []

        for payment in payments:
            # Create unique key
            if payment.payment_info.check_no:
                key = f"CHECK_{payment.payment_info.check_no}_{payment.payment_info.amount}"
            elif payment.payment_info.payment_ref:
                key = f"REF_{payment.payment_info.payment_ref}_{payment.payment_info.amount}"
            else:
                # No unique identifier - include it
                deduplicated.append(payment)
                continue

            if key not in seen:
                seen.add(key)
                deduplicated.append(payment)
            else:
                logger.debug(f"Duplicate payment found: {key}")

        return deduplicated

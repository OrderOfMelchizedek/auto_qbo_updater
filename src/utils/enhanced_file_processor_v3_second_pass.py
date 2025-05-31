"""
Enhanced file processor V3 with second-pass extraction for payments without payer info.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from models.payment import ContactInfo, PayerInfo, PaymentInfo, PaymentRecord
from .alias_matcher import AliasMatcher
from .check_normalizer import normalize_check_number
from .gemini_adapter_v3 import GeminiAdapterV3
from .payment_combiner_v2 import PaymentCombinerV2
from .qbo_data_enrichment import QBODataEnrichment

logger = logging.getLogger(__name__)


class EnhancedFileProcessorV3:
    """File processor that uses unified batching with second-pass extraction."""

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

        # Step 2: Normalize check numbers
        logger.info("Normalizing check numbers...")
        for payment in all_payments:
            if payment.payment_info.check_no:
                original = payment.payment_info.check_no
                normalized = normalize_check_number(original)
                if original != normalized:
                    logger.debug(f"Normalized check number: {original} -> {normalized}")
                payment.payment_info.check_no = normalized

        # Step 3: Deduplicate payments
        logger.info(f"Deduplicating {len(all_payments)} payments...")
        deduplicated = self._deduplicate_payments(all_payments)
        logger.info(f"After deduplication: {len(deduplicated)} unique payments")

        # Step 4: Match with QBO customers using aliases
        if self.alias_matcher:
            logger.info("Matching payments with QBO customers using aliases...")
            matched_payments = self.alias_matcher.match_payment_batch(deduplicated)
        else:
            logger.warning("No QBO service available - skipping customer matching")
            matched_payments = [(payment, None) for payment in deduplicated]

        # Step 5: Enrich and combine data
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

        # Step 6: Second-pass extraction for payments without payer info
        payments_needing_second_pass = []
        payments_with_payer = []

        for i, payment in enumerate(enriched_payments):
            payer_info = payment.get("payer_info", {})

            # Check if payment has valid payer information
            has_customer_lookup = bool(payer_info.get("customer_lookup", "").strip())
            has_org_name = bool(payer_info.get("qb_organization_name", "").strip())
            has_full_name = bool(payer_info.get("full_name", "").strip())

            if has_customer_lookup or has_org_name or has_full_name:
                payments_with_payer.append(payment)
            else:
                # Track which payment needs second pass (store original index and payment record)
                payments_needing_second_pass.append((i, matched_payments[i][0]))  # Store PaymentRecord
                payment_info = payment.get("payment_info", {})
                check_ref = payment_info.get("check_no_or_payment_ref", "Unknown")
                amount = payment_info.get("amount", 0)
                logger.info(f"Payment needs second pass: Check/Ref {check_ref}, Amount ${amount}")

        # Perform second-pass extraction if needed
        if payments_needing_second_pass:
            logger.info(
                f"\nPerforming second-pass extraction for {len(payments_needing_second_pass)} payments without payer info..."
            )

            # Extract just the PaymentRecord objects for second pass
            second_pass_payment_records = [pr for _, pr in payments_needing_second_pass]

            try:
                # Re-extract with focused prompt
                second_pass_results = self._second_pass_extraction(second_pass_payment_records, file_paths)

                if second_pass_results:
                    logger.info(f"Second pass extracted {len(second_pass_results)} payments")

                    # Normalize check numbers in second pass results
                    for payment in second_pass_results:
                        if payment.payment_info.check_no:
                            payment.payment_info.check_no = normalize_check_number(payment.payment_info.check_no)

                    # Match second-pass results with original payments
                    updated_count = 0
                    for new_payment in second_pass_results:
                        # Find matching original payment by check/ref and amount
                        for orig_idx, orig_payment in payments_needing_second_pass:
                            if self._payments_match(orig_payment, new_payment):
                                # Check if new extraction has payer info
                                if new_payment.payer_info.aliases or new_payment.payer_info.organization_name:
                                    logger.info(
                                        f"Second pass found payer info for Check/Ref {new_payment.payment_info.check_no or new_payment.payment_info.payment_ref}"
                                    )

                                    # Re-match with QBO
                                    if self.alias_matcher:
                                        match_results = self.alias_matcher.match_payment_batch([new_payment])
                                        new_payment_matched, qbo_customer = match_results[0]
                                    else:
                                        new_payment_matched, qbo_customer = new_payment, None

                                    # Re-enrich with new data
                                    if qbo_customer:
                                        enriched = self.payment_combiner.combine_payment_data(
                                            new_payment_matched, qbo_customer, match_status="Matched"
                                        )
                                    else:
                                        enriched = self.payment_combiner.combine_payment_data(
                                            new_payment_matched, None, match_status="New"
                                        )

                                    # Update the enriched payment
                                    enriched_payments[orig_idx] = enriched
                                    updated_count += 1
                                    break

                    logger.info(f"Second pass updated {updated_count} payments with payer information")
                else:
                    logger.warning("Second pass did not extract any payments")

            except Exception as e:
                logger.error(f"Error in second-pass extraction: {e}")
                errors.append(f"Second-pass extraction error: {str(e)}")

        # Step 7: Final filtering of payments without valid payer info
        initial_count = len(enriched_payments)
        valid_payments = []

        for payment in enriched_payments:
            payer_info = payment.get("payer_info", {})

            # Check if payment has valid payer information
            has_customer_lookup = bool(payer_info.get("customer_lookup", "").strip())
            has_org_name = bool(payer_info.get("qb_organization_name", "").strip())
            has_full_name = bool(payer_info.get("full_name", "").strip())

            if has_customer_lookup or has_org_name or has_full_name:
                valid_payments.append(payment)
            else:
                # Log discarded payment
                payment_info = payment.get("payment_info", {})
                check_ref = payment_info.get("check_no_or_payment_ref", "Unknown")
                amount = payment_info.get("amount", 0)
                logger.warning(
                    f"Discarding payment without payer info after second pass: Check/Ref {check_ref}, Amount ${amount}"
                )

        discarded_count = initial_count - len(valid_payments)
        if discarded_count > 0:
            logger.info(f"Discarded {discarded_count} payments without valid payer information after second pass")

        # Log final summary
        matched_count = sum(1 for p in valid_payments if p["match_status"] == "Matched")
        needs_update = sum(1 for p in valid_payments if p["payer_info"].get("address_needs_update"))

        logger.info(f"\nProcessing complete: {len(valid_payments)} valid payments")
        logger.info(f"  - Matched: {matched_count}")
        logger.info(f"  - New: {len(valid_payments) - matched_count}")
        logger.info(f"  - Address updates needed: {needs_update}")
        logger.info(f"  - Discarded (no payer after 2 passes): {discarded_count}")

        return valid_payments, errors

    def _second_pass_extraction(
        self, payment_records: List[PaymentRecord], file_paths: List[str]
    ) -> List[PaymentRecord]:
        """Perform focused second-pass extraction for payments missing payer info.

        Args:
            payment_records: List of PaymentRecord objects missing payer info
            file_paths: Original file paths to re-process

        Returns:
            List of re-extracted PaymentRecord objects
        """
        # Create a focused prompt for missing payer info
        focused_prompt = """
IMPORTANT: Focus on extracting PAYER INFORMATION that may have been missed.

The following payments were extracted but are missing payer names or organizations.
Please carefully re-examine the documents and extract any payer information such as:
- Names written on checks (look for signatures, printed names, or return addresses)
- Organization names on checks or letterheads
- Any identifying information in memo lines or endorsements

For each payment, you MUST provide either:
- aliases: Array of name variations for individuals
- organization_name: For businesses/organizations

Look especially carefully at:
1. The "Pay to the order of" FROM section (not TO section)
2. Pre-printed names/addresses on checks
3. Signatures that might indicate names
4. Return addresses on envelopes
5. Any letterhead or organization information
"""

        # Include payment details to help identify which payments need payer info
        payment_details = []
        for p in payment_records:
            detail = f"- Check/Ref: {p.payment_info.check_no or p.payment_info.payment_ref}, Amount: ${p.payment_info.amount}"
            if p.payment_info.memo:
                detail += f", Memo: {p.payment_info.memo}"
            payment_details.append(detail)

        focused_prompt += "\n\nPayments needing payer information:\n" + "\n".join(payment_details)

        # Re-process files with focused prompt
        try:
            # Use the same file paths but with focused extraction
            results = self.gemini_service.extract_payments_batch(file_paths)

            # Filter to only payments that match our problematic ones
            matched_results = []
            for result in results:
                for original in payment_records:
                    if self._payments_match(original, result):
                        matched_results.append(result)
                        break

            return matched_results

        except Exception as e:
            logger.error(f"Second-pass extraction failed: {e}")
            return []

    def _payments_match(self, payment1: PaymentRecord, payment2: PaymentRecord) -> bool:
        """Check if two payments are the same based on check/ref and amount.

        Args:
            payment1: First payment
            payment2: Second payment

        Returns:
            True if payments match
        """
        # Compare check numbers (already normalized)
        if payment1.payment_info.check_no and payment2.payment_info.check_no:
            if payment1.payment_info.check_no != payment2.payment_info.check_no:
                return False

        # Compare payment refs
        if payment1.payment_info.payment_ref and payment2.payment_info.payment_ref:
            if payment1.payment_info.payment_ref != payment2.payment_info.payment_ref:
                return False

        # Compare amounts
        if abs(payment1.payment_info.amount - payment2.payment_info.amount) > 0.01:
            return False

        return True

    def _deduplicate_payments(self, payments: List[PaymentRecord]) -> List[PaymentRecord]:
        """Deduplicate payment records, merging when necessary.
        Check numbers are already normalized at this point.

        Args:
            payments: List of PaymentRecord objects

        Returns:
            Deduplicated list of PaymentRecord objects
        """
        # Group payments by their unique key
        payment_groups = {}
        unkeyed_payments = []

        for payment in payments:
            # Create unique key (check numbers are already normalized)
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

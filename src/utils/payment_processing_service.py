"""
Enhanced payment processing service that combines structured extraction with customer matching.
"""

import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.models.payment import PaymentRecord
from src.models.ui_models import BatchProcessingResult, UIPaymentRecord
from utils.customer_matcher import CustomerMatcher
from utils.gemini_adapter_v3 import GeminiAdapterV3
from utils.qbo_service.customers import QBOCustomerService

logger = logging.getLogger(__name__)


class PaymentProcessingService:
    """Service that orchestrates the complete payment processing pipeline."""

    def __init__(self, gemini_api_key: str, qbo_service, model_name: str = None):
        """Initialize the payment processing service.

        Args:
            gemini_api_key: Gemini API key for extraction
            qbo_service: QBO service for customer operations
            model_name: Optional Gemini model name
        """
        self.gemini_adapter = GeminiAdapterV3(gemini_api_key, model_name)

        # Initialize customer service and matcher
        self.qbo_customer_service = QBOCustomerService(
            client_id=qbo_service.client_id,
            client_secret=qbo_service.client_secret,
            redirect_uri=qbo_service.redirect_uri,
            environment=qbo_service.environment,
        )
        # Copy credentials
        self.qbo_customer_service.access_token = qbo_service.access_token
        self.qbo_customer_service.realm_id = qbo_service.realm_id
        self.qbo_customer_service.refresh_token = qbo_service.refresh_token

        self.customer_matcher = CustomerMatcher(self.qbo_customer_service)

        logger.info("Initialized PaymentProcessingService with structured outputs and customer matching")

    def process_files(self, file_paths: List[str], session_id: str = None) -> BatchProcessingResult:
        """Process uploaded files through the complete pipeline.

        Args:
            file_paths: List of file paths to process
            session_id: Optional session ID for tracking

        Returns:
            BatchProcessingResult with processed records and statistics
        """
        start_time = time.time()

        # Initialize result tracking
        result = BatchProcessingResult(
            session_id=session_id or f"session_{int(time.time())}",
            total_processed=len(file_paths),
            successful_extractions=0,
            customer_matches=0,
            new_customers=0,
            address_updates=0,
            contact_updates=0,
            records=[],
            errors=[],
            warnings=[],
        )

        try:
            # Step 1: Extract payment data using structured outputs
            logger.info(f"Starting structured extraction for {len(file_paths)} files")

            payment_records = self.gemini_adapter.extract_payments_batch(file_paths)
            result.successful_extractions = len(payment_records)

            if not payment_records:
                result.warnings.append("No payment records extracted from uploaded files")
                result.processing_time_seconds = time.time() - start_time
                return result

            logger.info(f"Extracted {len(payment_records)} payment records")

            # Step 2: Match customers and merge data
            logger.info("Starting customer matching and data merging")

            for i, payment_record in enumerate(payment_records):
                try:
                    # Match and merge each payment record
                    ui_record = self.customer_matcher.match_and_merge_payment(payment_record)

                    # Update statistics
                    if ui_record.payer_info.is_matched:
                        result.customer_matches += 1
                    if ui_record.payer_info.is_new_customer:
                        result.new_customers += 1
                    if ui_record.payer_info.address_updated:
                        result.address_updates += 1
                    if ui_record.payer_info.contact_updated:
                        result.contact_updates += 1

                    # Add to results
                    result.records.append(ui_record)
                    result.total_amount += ui_record.payment_info.amount

                    # Track payment methods
                    payment_method = getattr(payment_record.payment_info, "payment_method", "unknown")
                    result.payment_methods[payment_method] = result.payment_methods.get(payment_method, 0) + 1

                except Exception as e:
                    error_msg = f"Error processing payment record {i+1}: {str(e)}"
                    logger.error(error_msg)
                    result.errors.append(error_msg)

            # Step 3: Final validation and cleanup
            logger.info(f"Processing complete: {len(result.records)} records processed")

            # Filter out any records with critical errors
            valid_records = []
            for record in result.records:
                if record.processing_status != "error":
                    valid_records.append(record)
                else:
                    result.warnings.append(f"Excluded invalid record: {record.warnings}")

            result.records = valid_records
            result.processing_time_seconds = time.time() - start_time

            # Log final statistics
            logger.info(
                f"Final results: {len(result.records)} valid records, "
                f"{result.customer_matches} matches, {result.new_customers} new customers, "
                f"${result.total_amount:.2f} total amount"
            )

            return result

        except Exception as e:
            error_msg = f"Critical error in payment processing: {str(e)}"
            logger.error(error_msg, exc_info=True)
            result.errors.append(error_msg)
            result.processing_time_seconds = time.time() - start_time
            return result

    def process_single_file(self, file_path: str) -> List[UIPaymentRecord]:
        """Process a single file and return UI records.

        Args:
            file_path: Path to file to process

        Returns:
            List of UIPaymentRecord objects
        """
        result = self.process_files([file_path])
        return result.records

    def reprocess_with_customer_selection(
        self, extracted_record: PaymentRecord, selected_customer_id: str
    ) -> UIPaymentRecord:
        """Reprocess a payment record with a manually selected customer.

        Args:
            extracted_record: Original extracted payment record
            selected_customer_id: QB customer ID selected by user

        Returns:
            UIPaymentRecord with selected customer data
        """
        try:
            # Get the selected customer data from QB
            customer_data = self.qbo_customer_service.get_customer_by_id(selected_customer_id)

            if not customer_data:
                raise ValueError(f"Customer not found: {selected_customer_id}")

            # Create a mock QBCustomer for the merger
            from src.models.qbo_customer import QBCustomer

            qb_customer = QBCustomer(
                customer_lookup=selected_customer_id,
                first_name=customer_data.get("given_name"),
                last_name=customer_data.get("family_name"),
                full_name=customer_data.get("name"),
                qb_organization_name=customer_data.get("company_name"),
                qb_address_line_1=self.customer_matcher._get_qb_address_field(customer_data, "line1"),
                qb_city=self.customer_matcher._get_qb_address_field(customer_data, "city"),
                qb_state=self.customer_matcher._get_qb_address_field(customer_data, "state"),
                qb_zip=self.customer_matcher._get_qb_address_field(customer_data, "postal_code"),
                qb_email=self.customer_matcher._get_qb_email(customer_data),
                qb_phone=self.customer_matcher._get_qb_phone(customer_data),
            )

            # Merge the data
            ui_payer_info = self.customer_matcher._merge_customer_data(
                extracted_record.payer_info, extracted_record.contact_info, customer_data
            )
            ui_payer_info.is_matched = True
            ui_payer_info.match_confidence = 1.0  # Manual selection = 100% confidence
            ui_payer_info.customer_lookup = selected_customer_id

            # Convert payment info
            ui_payment_info = self.customer_matcher._convert_payment_info(extracted_record.payment_info)

            # Create final UI record
            ui_record = UIPaymentRecord(
                payer_info=ui_payer_info,
                payment_info=ui_payment_info,
                processing_status="manually_matched",
                extraction_source=extracted_record.source_document_type or "unknown",
            )

            return ui_record

        except Exception as e:
            logger.error(f"Error reprocessing with selected customer: {e}")
            return self.customer_matcher._create_error_record(
                extracted_record, f"Manual customer selection failed: {str(e)}"
            )

    def get_customer_suggestions(self, payer_info) -> List[Dict[str, Any]]:
        """Get customer suggestions for manual matching.

        Args:
            payer_info: Extracted payer information

        Returns:
            List of customer suggestions with scores
        """
        try:
            match_result = self.customer_matcher._match_customer(payer_info)

            suggestions = []

            # Add best match if available
            if match_result.qb_customer:
                suggestions.append(
                    {
                        "customer_id": match_result.qb_customer.customer_lookup,
                        "name": match_result.qb_customer.full_name,
                        "confidence": match_result.confidence_score,
                        "method": match_result.match_method,
                        "organization": match_result.qb_customer.qb_organization_name,
                    }
                )

            # Add alternatives
            if match_result.alternatives:
                for alt in match_result.alternatives:
                    suggestions.append(
                        {
                            "customer_id": alt.customer_lookup,
                            "name": alt.full_name,
                            "confidence": 0.5,  # Lower confidence for alternatives
                            "method": "alternative_match",
                            "organization": alt.qb_organization_name,
                        }
                    )

            return suggestions

        except Exception as e:
            logger.error(f"Error getting customer suggestions: {e}")
            return []

    def validate_processing_result(self, result: BatchProcessingResult) -> List[str]:
        """Validate processing result and return any issues.

        Args:
            result: Processing result to validate

        Returns:
            List of validation issues
        """
        issues = []

        # Check for basic data completeness
        if not result.records:
            issues.append("No payment records were processed")
            return issues

        # Validate each record
        for i, record in enumerate(result.records):
            record_issues = []

            # Check payment info
            if not record.payment_info.amount or record.payment_info.amount <= 0:
                record_issues.append("Invalid or missing amount")

            if not record.payment_info.check_no_or_payment_ref:
                record_issues.append("Missing check number or payment reference")

            if not record.payment_info.payment_date:
                record_issues.append("Missing payment date")

            # Check payer info
            if not record.payer_info.customer_lookup and not record.payer_info.is_new_customer:
                record_issues.append("No customer match and not marked for new customer creation")

            if record_issues:
                issues.append(f"Record {i+1}: {'; '.join(record_issues)}")

        # Check statistics consistency
        total_records = len(result.records)
        if result.customer_matches + result.new_customers != total_records:
            issues.append("Customer match statistics don't add up to total records")

        return issues

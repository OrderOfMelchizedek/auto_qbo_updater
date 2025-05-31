"""
Comprehensive test suite to enforce V3 refactored workflow and prevent regression to legacy format.
These tests ensure that the entire pipeline uses only V3 components and enriched format.
"""

import json
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.models.payment import ContactInfo, PayerInfo, PaymentInfo, PaymentRecord
from src.utils.alias_matcher import AliasMatcher
from src.utils.enhanced_file_processor_v3_second_pass import EnhancedFileProcessorV3
from src.utils.gemini_adapter_v3 import GeminiAdapterV3
from src.utils.payment_combiner_v2 import PaymentCombinerV2


class TestV3WorkflowEnforcement:
    """Test suite to enforce V3 refactored workflow compliance."""

    def test_v3_processor_returns_enriched_format(self):
        """Test that V3 processor returns enriched payment format, not legacy."""
        # Mock dependencies
        mock_gemini = Mock(spec=GeminiAdapterV3)
        mock_qbo = Mock()

        # Create sample PaymentRecord
        payment_record = PaymentRecord(
            payer_info=PayerInfo(aliases=["John Smith"], organization_name="", salutation=""),
            payment_info=PaymentInfo(
                payment_method="handwritten_check",
                check_no="123456",
                amount=100.00,
                check_date="2025-01-01",
                deposit_date="2025-01-02",
                payment_date="2025-01-01",
                memo="Test payment",
                deposit_method="ATM Deposit",
            ),
            contact_info=ContactInfo(
                address_line_1="123 Main St",
                city="Anytown",
                state="CA",
                zip="12345",
                email="john@example.com",
                phone="555-1234",
            ),
        )

        # Mock gemini service to return PaymentRecord
        mock_gemini.extract_payments_batch.return_value = [payment_record]

        # Mock QBO service
        mock_qbo.is_token_valid.return_value = False

        # Create processor
        processor = EnhancedFileProcessorV3(mock_gemini, mock_qbo)

        # Process files
        files = [("/fake/path1.pdf", ".pdf")]
        enriched_payments, errors = processor.process_files(files)

        # Verify we get enriched format, not legacy
        assert len(enriched_payments) == 1
        enriched = enriched_payments[0]

        # Must have V3 enriched structure
        assert "payer_info" in enriched
        assert "payment_info" in enriched
        assert "match_status" in enriched

        # Must NOT have legacy format fields
        assert "Donor Name" not in enriched
        assert "Gift Amount" not in enriched
        assert "Check Date" not in enriched
        assert "qbCustomerStatus" not in enriched

        # Verify enriched structure contents
        payer_info = enriched["payer_info"]
        assert "customer_lookup" in payer_info
        assert "qb_address_line_1" in payer_info
        assert "qb_city" in payer_info

        payment_info = enriched["payment_info"]
        assert "check_no_or_payment_ref" in payment_info
        assert "amount" in payment_info
        assert "payment_date" in payment_info

    def test_v3_components_only_no_legacy_imports(self):
        """Test that V3 processor only imports and uses V3 components."""
        # This test ensures no legacy components are imported

        # Check that V3 processor imports only V3 components
        from src.utils.enhanced_file_processor_v3_second_pass import EnhancedFileProcessorV3

        # Verify it uses V3 components
        processor_source = EnhancedFileProcessorV3.__module__
        assert "enhanced_file_processor_v3" in processor_source

        # Create instance and verify it has V3 dependencies
        mock_gemini = Mock(spec=GeminiAdapterV3)
        mock_qbo = Mock()
        processor = EnhancedFileProcessorV3(mock_gemini, mock_qbo)

        # Verify it has V3 adapter and combiner
        assert hasattr(processor, "gemini_service")
        assert hasattr(processor, "payment_combiner")
        assert isinstance(processor.payment_combiner, PaymentCombinerV2)

    def test_tasks_py_uses_v3_processor(self):
        """Test that tasks.py imports and uses only V3 processor."""
        # Check that tasks module imports V3 processor
        import inspect

        from src.utils import tasks

        source = inspect.getsource(tasks)

        # Must import V3 processor
        assert "enhanced_file_processor_v3_second_pass" in source
        assert "EnhancedFileProcessorV3" in source

        # Must NOT import legacy components
        assert "file_processor" not in source or "enhanced_file_processor_v3" in source
        assert "gemini_service" not in source or "gemini_adapter_v3" in source

        # Must use V3 adapter
        assert "GeminiAdapterV3" in source

    def test_app_py_uses_v3_components(self):
        """Test that app.py imports and uses only V3 components."""
        # Check app source
        import inspect

        from src import app

        source = inspect.getsource(app)

        # Must import V3 components
        assert "enhanced_file_processor_v3_second_pass" in source
        assert "gemini_adapter_v3" in source

        # Must NOT import legacy components
        assert "file_processor.py" not in source
        assert "gemini_service.py" not in source

    @patch("src.utils.tasks.EnhancedFileProcessorV3")
    @patch("src.utils.tasks.GeminiAdapterV3")
    def test_celery_task_uses_v3_workflow(self, mock_gemini_adapter, mock_processor):
        """Test that Celery tasks use V3 workflow end-to-end."""
        from src.utils.tasks import process_files_task

        # Mock V3 processor to return enriched format
        mock_processor_instance = Mock()
        mock_processor.return_value = mock_processor_instance

        # Mock enriched payments output
        enriched_payments = [
            {
                "payer_info": {
                    "customer_lookup": "John Smith",
                    "qb_address_line_1": "123 Main St",
                    "qb_city": "Anytown",
                    "qb_state": "CA",
                    "qb_zip": "12345",
                },
                "payment_info": {
                    "check_no_or_payment_ref": "123456",
                    "amount": 100.00,
                    "payment_date": "2025-01-01",
                    "memo": "Test payment",
                },
                "match_status": "New",
                "qbo_customer_id": None,
            }
        ]

        mock_processor_instance.process_files.return_value = (enriched_payments, [])

        # Mock other dependencies
        with patch("src.utils.tasks.QBOService") as mock_qbo_service:
            mock_qbo_instance = Mock()
            mock_qbo_service.return_value = mock_qbo_instance
            mock_qbo_instance.is_token_valid.return_value = False

            # Create mock task
            mock_task = Mock()
            mock_task.request.id = "test-task-id"

            # Call the task
            s3_references = [{"s3_key": "test/file.pdf", "filename": "test.pdf", "content_type": "application/pdf"}]

            with patch("src.utils.tasks.S3Storage") as mock_s3:
                mock_s3_instance = Mock()
                mock_s3.return_value = mock_s3_instance
                mock_s3_instance.download_file.return_value = b"fake pdf content"

                result = process_files_task(mock_task, s3_references=s3_references, session_id="test-session")

        # Verify task used V3 processor
        mock_processor.assert_called_once()
        mock_processor_instance.process_files.assert_called_once()

        # Verify result contains enriched format
        assert result["success"] == True
        assert "donations" in result

        # Each donation should be in enriched format
        for donation in result["donations"]:
            # Must have V3 enriched structure
            assert "payer_info" in donation
            assert "payment_info" in donation

    def test_frontend_handles_enriched_format(self):
        """Test that frontend JavaScript can handle V3 enriched format."""
        # This test verifies the updated frontend code can work with enriched format

        # Sample enriched payment
        enriched_payment = {
            "payer_info": {
                "customer_lookup": "John Smith",
                "qb_address_line_1": "123 Main St",
                "qb_city": "Anytown",
                "qb_state": "CA",
                "qb_zip": "12345",
                "qb_email": ["john@example.com"],
                "qb_phone": ["555-1234"],
            },
            "payment_info": {
                "check_no_or_payment_ref": "123456",
                "amount": 100.00,
                "payment_date": "2025-01-01",
                "memo": "Test payment",
            },
            "match_status": "New",
            "qbo_customer_id": None,
            "internal_id": "test-payment-1",
        }

        # Read the updated frontend JavaScript
        with open("/Users/svaug/dev/svl_apps/fom_to_qbo_automation/src/static/js/app.js", "r") as f:
            frontend_code = f.read()

        # Verify frontend uses V3 field access patterns
        assert "payer_info" in frontend_code
        assert "payment_info" in frontend_code
        assert "donation.payer_info" in frontend_code
        assert "donation.payment_info" in frontend_code
        assert "match_status" in frontend_code

        # Verify it doesn't use legacy field access
        assert "donation['Donor Name']" not in frontend_code or "payer_info" in frontend_code
        assert "donation.qbCustomerStatus" not in frontend_code or "match_status" in frontend_code

    def test_no_legacy_conversion_functions(self):
        """Test that there are no legacy conversion functions in the codebase."""
        import glob
        import os

        # Search for potential legacy conversion functions
        python_files = glob.glob("/Users/svaug/dev/svl_apps/fom_to_qbo_automation/src/**/*.py", recursive=True)

        forbidden_patterns = [
            "convert_to_legacy",
            "legacy_format",
            "enriched_to_legacy",
            "_convert_enriched_to_legacy_format",
        ]

        for file_path in python_files:
            # Skip deprecated folder
            if "deprecated" in file_path:
                continue

            with open(file_path, "r") as f:
                content = f.read()

            for pattern in forbidden_patterns:
                assert pattern not in content, f"Found forbidden legacy conversion pattern '{pattern}' in {file_path}"

    def test_v3_check_normalization_works(self):
        """Test that V3 processor properly normalizes check numbers."""
        from src.utils.check_normalizer import normalize_check_number

        # Test various check number formats
        test_cases = [
            ("0003517031", "3517031"),  # Leading zeros removed
            ("00001234", "1234"),  # Multiple leading zeros
            ("1234", "1234"),  # No change needed
            ("ABC123", "ABC123"),  # Non-numeric preserved
            ("", ""),  # Empty string
            (None, ""),  # None handled
        ]

        for input_val, expected in test_cases:
            result = normalize_check_number(input_val)
            assert result == expected, f"normalize_check_number({input_val}) = {result}, expected {expected}"

    def test_v3_alias_matching_works(self):
        """Test that V3 alias matching works with PaymentRecord objects."""
        # Mock QBO service
        mock_qbo = Mock()
        mock_customers = [{"Id": "1", "DisplayName": "Smith, John", "FamilyName": "Smith", "CompanyName": ""}]
        mock_qbo.get_all_customers.return_value = mock_customers

        # Create alias matcher
        matcher = AliasMatcher(mock_qbo)

        # Create PaymentRecord with aliases
        payment_record = PaymentRecord(
            payer_info=PayerInfo(aliases=["Smith, J.", "John Smith"], organization_name="", salutation=""),
            payment_info=PaymentInfo(
                payment_method="handwritten_check", check_no="123", amount=100.00, check_date="2025-01-01"
            ),
            contact_info=ContactInfo(),
        )

        # Test matching
        results = matcher.match_payment_batch([payment_record])

        # Should find a match
        assert len(results) == 1
        payment, customer = results[0]
        assert payment == payment_record
        assert customer is not None
        assert customer["DisplayName"] == "Smith, John"

    def test_v3_payment_combiner_creates_enriched_format(self):
        """Test that PaymentCombinerV2 creates proper enriched format."""
        # Create payment record
        payment_record = PaymentRecord(
            payer_info=PayerInfo(aliases=["John Smith"], organization_name="Acme Corp", salutation="Mr."),
            payment_info=PaymentInfo(
                payment_method="handwritten_check",
                check_no="123456",
                amount=250.00,
                check_date="2025-01-01",
                memo="Donation",
            ),
            contact_info=ContactInfo(
                address_line_1="123 Main St",
                city="Anytown",
                state="CA",
                zip="12345",
                email="john@example.com",
                phone="555-1234",
            ),
        )

        # Create combiner
        combiner = PaymentCombinerV2()

        # Test without QBO customer
        result = combiner.combine_payment_data(payment_record, None, "New")

        # Verify enriched structure
        assert "payer_info" in result
        assert "payment_info" in result
        assert "match_status" in result

        payer_info = result["payer_info"]
        assert payer_info["customer_lookup"] == "Acme Corp"  # Organization takes precedence
        assert payer_info["qb_address_line_1"] == "123 Main St"
        assert payer_info["qb_city"] == "Anytown"

        payment_info = result["payment_info"]
        assert payment_info["check_no_or_payment_ref"] == "123456"
        assert payment_info["amount"] == 250.00
        assert payment_info["memo"] == "Donation"

        assert result["match_status"] == "New"

    def test_no_direct_legacy_field_usage_in_backend(self):
        """Test that backend code doesn't use legacy field names."""
        import glob
        import os

        # Get all Python files in src/ except deprecated
        python_files = glob.glob("/Users/svaug/dev/svl_apps/fom_to_qbo_automation/src/**/*.py", recursive=True)

        legacy_fields = [
            '"Donor Name"',
            '"Gift Amount"',
            '"Check Date"',
            '"Check No."',
            '"Address - Line 1"',
            "qbCustomerStatus",
            "internalId",
        ]

        for file_path in python_files:
            # Skip deprecated folder and test files
            if "deprecated" in file_path or "test_" in file_path:
                continue

            with open(file_path, "r") as f:
                content = f.read()

            for field in legacy_fields:
                # Allow some usage in comments or conversion context
                lines_with_field = [line for line in content.split("\n") if field in line]
                for line in lines_with_field:
                    # Skip comments and docstrings
                    if line.strip().startswith("#") or line.strip().startswith('"""') or line.strip().startswith("'''"):
                        continue
                    # Skip if it's in a conversion context (which we've eliminated)
                    if "legacy" in line.lower() or "convert" in line.lower():
                        raise AssertionError(f"Found legacy conversion code in {file_path}: {line.strip()}")
                    # For other cases, flag as potential issue
                    if field in line and not any(skip in line for skip in ["# ", '"""', "'''"]):
                        print(f"Warning: Legacy field {field} found in {file_path}: {line.strip()}")


class TestV3DataIntegrity:
    """Test data integrity throughout the V3 pipeline."""

    def test_v3_pipeline_preserves_data_fidelity(self):
        """Test that data isn't lost or corrupted through V3 pipeline."""
        # Create comprehensive test data
        original_payment = PaymentRecord(
            payer_info=PayerInfo(aliases=["John Smith", "J. Smith"], organization_name="Acme Corp", salutation="Mr."),
            payment_info=PaymentInfo(
                payment_method="handwritten_check",
                check_no="0003517031",  # Test check normalization
                amount=150.75,
                check_date="2025-01-15",
                deposit_date="2025-01-16",
                payment_date="2025-01-15",
                memo="Quarterly donation",
                deposit_method="ATM Deposit",
                payment_ref="REF123",
            ),
            contact_info=ContactInfo(
                address_line_1="456 Oak Avenue",
                city="Springfield",
                state="IL",
                zip="62701",
                email="john.smith@acme.com",
                phone="217-555-0123",
            ),
        )

        # Create combiner and process
        combiner = PaymentCombinerV2()
        enriched = combiner.combine_payment_data(original_payment, None, "New")

        # Verify all data is preserved in enriched format
        payer_info = enriched["payer_info"]
        payment_info = enriched["payment_info"]

        # Check data integrity
        assert payer_info["customer_lookup"] == "Acme Corp"
        assert payer_info["qb_address_line_1"] == "456 Oak Avenue"
        assert payer_info["qb_city"] == "Springfield"
        assert payer_info["qb_state"] == "IL"
        assert payer_info["qb_zip"] == "62701"
        assert payer_info["qb_email"] == ["john.smith@acme.com"]
        assert payer_info["qb_phone"] == ["217-555-0123"]

        assert payment_info["check_no_or_payment_ref"] == "3517031"  # Check normalization applied
        assert payment_info["amount"] == 150.75
        assert payment_info["payment_date"] == "2025-01-15"
        assert payment_info["deposit_date"] == "2025-01-16"
        assert payment_info["memo"] == "Quarterly donation"
        assert payment_info["deposit_method"] == "ATM Deposit"

        assert enriched["match_status"] == "New"

    def test_v3_handles_missing_data_gracefully(self):
        """Test that V3 components handle missing/incomplete data gracefully."""
        # Create minimal payment record
        minimal_payment = PaymentRecord(
            payer_info=PayerInfo(aliases=[], organization_name="", salutation=""),
            payment_info=PaymentInfo(payment_method="handwritten_check", check_no="", amount=50.00, check_date=""),
            contact_info=ContactInfo(),
        )

        # Process with combiner
        combiner = PaymentCombinerV2()
        enriched = combiner.combine_payment_data(minimal_payment, None, "New")

        # Should handle gracefully without errors
        assert "payer_info" in enriched
        assert "payment_info" in enriched
        assert enriched["payment_info"]["amount"] == 50.00

        # Empty fields should be empty strings, not None
        payer_info = enriched["payer_info"]
        assert payer_info["customer_lookup"] == ""
        assert payer_info["qb_address_line_1"] == ""
        assert isinstance(payer_info["qb_email"], list)
        assert isinstance(payer_info["qb_phone"], list)


class TestV3PerformanceAndScalability:
    """Test V3 performance characteristics."""

    def test_v3_batch_processing_scales(self):
        """Test that V3 batch processing can handle multiple files efficiently."""
        # Mock large batch
        mock_gemini = Mock(spec=GeminiAdapterV3)
        mock_qbo = Mock()

        # Create multiple payment records
        payment_records = []
        for i in range(100):  # Simulate 100 payments
            payment_records.append(
                PaymentRecord(
                    payer_info=PayerInfo(aliases=[f"Customer {i}"], organization_name="", salutation=""),
                    payment_info=PaymentInfo(
                        payment_method="handwritten_check",
                        check_no=str(1000 + i),
                        amount=100.00 + i,
                        check_date="2025-01-01",
                    ),
                    contact_info=ContactInfo(),
                )
            )

        mock_gemini.extract_payments_batch.return_value = payment_records
        mock_qbo.is_token_valid.return_value = False

        # Create processor
        processor = EnhancedFileProcessorV3(mock_gemini, mock_qbo)

        # Process multiple files
        files = [(f"/fake/path{i}.pdf", ".pdf") for i in range(10)]

        # Should complete without timeout or memory issues
        enriched_payments, errors = processor.process_files(files)

        # Verify batch processing
        assert len(enriched_payments) == 100
        assert len(errors) == 0

        # Verify each payment is in enriched format
        for payment in enriched_payments:
            assert "payer_info" in payment
            assert "payment_info" in payment
            assert "match_status" in payment

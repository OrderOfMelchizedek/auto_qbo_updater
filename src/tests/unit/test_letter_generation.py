"""Unit tests for letter generation service."""
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.models.donation import (
    Address,
    ContactInfo,
    DonationEntry,
    PayerInfo,
    PaymentInfo,
)
from src.models.letter import (
    GeneratedLetter,
    LetterBatch,
    LetterGenerationRequest,
    OrganizationInfo,
)
from src.services.letter.letter_generator import LetterGenerator
from src.utils.exceptions import DonationProcessingError


@pytest.fixture
def organization_info():
    """Sample organization info for testing."""
    return OrganizationInfo(
        name="Test Charity",
        address_line1="123 Main St",
        address_line2="Suite 100",
        city="Testville",
        state="TS",
        postal_code="12345",
        phone="555-123-4567",
        email="contact@testcharity.org",
        ein="12-3456789",
        treasurer_name="Jane Doe",
        treasurer_title="Treasurer",
        mission_statement="Making the world a better place",
        logo_url="https://example.com/logo.png",
    )


@pytest.fixture
def sample_donation():
    """Sample donation for testing."""
    return DonationEntry(
        payer_info=PayerInfo(name="John Smith", business_name="Smith Corp"),
        payment_info=PaymentInfo(
            amount=Decimal("250.00"),
            payment_date=date(2024, 1, 15),
            check_number="1234",
        ),
        contact_info=ContactInfo(
            email="john@example.com",
            phone="555-987-6543",
            address=Address(
                street1="456 Oak Ave",
                street2="Apt 2B",
                city="Donorville",
                state="DN",
                postal_code="54321",
            ),
        ),
        notes="Annual contribution",
    )


@pytest.fixture
def mock_s3_service():
    """Mock S3 service."""
    mock = Mock()
    mock.upload_file.return_value = (
        "letters/test_charity/john_smith_20240115_120000.pdf"
    )
    return mock


class TestLetterGenerator:
    """Test cases for LetterGenerator class."""

    def test_init(self, mock_s3_service):
        """Test LetterGenerator initialization."""
        generator = LetterGenerator(s3_service=mock_s3_service)
        assert generator.s3_service == mock_s3_service
        assert generator.env is not None
        assert "currency" in generator.env.filters
        assert "date" in generator.env.filters

    def test_format_currency(self):
        """Test currency formatting."""
        generator = LetterGenerator()
        assert generator._format_currency(Decimal("1234.56")) == "$1,234.56"
        assert generator._format_currency(Decimal("0.00")) == "$0.00"
        assert generator._format_currency(Decimal("1000000.99")) == "$1,000,000.99"

    def test_format_date(self):
        """Test date formatting."""
        generator = LetterGenerator()
        test_date = datetime(2024, 1, 15)
        assert generator._format_date(test_date) == "January 15, 2024"
        assert generator._format_date("2024-01-15") == "2024-01-15"

    def test_prepare_letter_data(self, sample_donation, organization_info):
        """Test letter data preparation."""
        generator = LetterGenerator()
        custom_data = {"custom_message": "Thank you!"}

        data = generator._prepare_letter_data(
            sample_donation, organization_info, custom_data
        )

        assert data["organization"] == organization_info
        assert data["donation"] == sample_donation
        assert data["donor_name"] == "John Smith"
        assert data["amount"] == Decimal("250.00")
        assert data["payment_date"] == date(2024, 1, 15)
        assert data["check_number"] == "1234"
        assert data["has_address"] is True
        assert data["address"] == sample_donation.contact_info.address
        assert data["salutation"] == "Mr./Ms."
        assert data["last_name"] == "Smith"
        assert data["custom_message"] == "Thank you!"

    def test_prepare_letter_data_no_address(self, organization_info):
        """Test letter data preparation without address."""
        donation = DonationEntry(
            payer_info=PayerInfo(name="Anonymous"),
            payment_info=PaymentInfo(
                amount=Decimal("50.00"), payment_date=date.today()
            ),
        )

        generator = LetterGenerator()
        data = generator._prepare_letter_data(donation, organization_info)

        assert data["donor_name"] == "Anonymous"
        assert data["has_address"] is False
        assert data["salutation"] == "Dear"
        assert data["last_name"] == "Anonymous"

    def test_generate_file_name(self, sample_donation, organization_info):
        """Test file name generation."""
        generator = LetterGenerator()
        file_name = generator._generate_file_name(sample_donation, organization_info)

        assert file_name.startswith("letters/test_charity/john_smith_")
        assert file_name.endswith(".pdf")

    @patch("src.services.letter.letter_generator.HTML")
    def test_generate_pdf(self, mock_html_class):
        """Test PDF generation."""
        mock_html = Mock()
        mock_html.write_pdf.return_value = b"PDF content"
        mock_html_class.return_value = mock_html

        generator = LetterGenerator()
        pdf_content = generator._generate_pdf("<html>Test</html>")

        assert pdf_content == b"PDF content"
        mock_html_class.assert_called_once_with(string="<html>Test</html>")
        mock_html.write_pdf.assert_called_once()

    def test_get_available_templates(self):
        """Test getting available templates."""
        with patch("pathlib.Path.glob") as mock_glob:
            mock_template1 = Mock(spec=Path)
            mock_template1.name = "default_letter.html"
            mock_template1.stem = "default_letter"
            mock_read1 = Mock()
            mock_read1.read.return_value = ""
            mock_template1.open.return_value.__enter__.return_value = mock_read1

            mock_template2 = Mock(spec=Path)
            mock_template2.name = "simple_letter.html"
            mock_template2.stem = "simple_letter"
            mock_read2 = Mock()
            mock_read2.read.return_value = ""
            mock_template2.open.return_value.__enter__.return_value = mock_read2

            mock_glob.return_value = [mock_template1, mock_template2]

            generator = LetterGenerator()
            templates = generator.get_available_templates()

            assert len(templates) == 2
            assert templates[0].name == "default_letter.html"
            assert templates[0].display_name == "Default Letter"
            assert templates[1].name == "simple_letter.html"
            assert templates[1].display_name == "Simple Letter"

    @patch("src.services.letter.letter_generator.HTML")
    def test_generate_letter(
        self, mock_html_class, sample_donation, organization_info, mock_s3_service
    ):
        """Test single letter generation."""
        # Setup mocks
        mock_html = Mock()
        mock_html.write_pdf.return_value = b"PDF content"
        mock_html_class.return_value = mock_html

        generator = LetterGenerator(s3_service=mock_s3_service)

        # Mock template
        with patch.object(generator, "_get_template") as mock_get_template:
            mock_template = Mock()
            mock_template.render.return_value = "<html>Rendered letter</html>"
            mock_get_template.return_value = mock_template

            # Generate letter
            letter = generator.generate_letter(
                sample_donation, organization_info, template_name="default_letter.html"
            )

            # Assertions
            assert isinstance(letter, GeneratedLetter)
            assert letter.recipient_name == "John Smith"
            assert letter.recipient_email == "john@example.com"
            assert letter.template_name == "default_letter.html"
            assert letter.pdf_content == b"PDF content"
            assert (
                letter.file_url == "letters/test_charity/john_smith_20240115_120000.pdf"
            )

            # Verify mocks called
            mock_get_template.assert_called_once_with("default_letter.html")
            mock_template.render.assert_called_once()
            mock_s3_service.upload_file.assert_called_once()

    def test_generate_letter_error_handling(self, sample_donation, organization_info):
        """Test error handling in letter generation."""
        generator = LetterGenerator()

        with patch.object(generator, "_get_template") as mock_get_template:
            mock_get_template.side_effect = Exception("Template error")

            with pytest.raises(DonationProcessingError) as exc_info:
                generator.generate_letter(sample_donation, organization_info)

            assert "Letter generation failed" in str(exc_info.value)

    @patch("src.services.letter.letter_generator.HTML")
    def test_generate_batch_letters(
        self, mock_html_class, organization_info, mock_s3_service
    ):
        """Test batch letter generation."""
        # Setup
        mock_html = Mock()
        mock_html.write_pdf.return_value = b"PDF content"
        mock_html_class.return_value = mock_html

        donations = [
            DonationEntry(
                payer_info=PayerInfo(name=f"Donor {i}"),
                payment_info=PaymentInfo(
                    amount=Decimal(f"{i}00.00"), payment_date=date.today()
                ),
            )
            for i in range(1, 4)
        ]

        generator = LetterGenerator(s3_service=mock_s3_service)

        with patch.object(generator, "_get_template") as mock_get_template:
            mock_template = Mock()
            mock_template.render.return_value = "<html>Letter</html>"
            mock_get_template.return_value = mock_template

            # Generate batch
            letters = generator.generate_batch_letters(donations, organization_info)

            # Assertions
            assert len(letters) == 3
            assert all(isinstance(letter, GeneratedLetter) for letter in letters)
            assert letters[0].recipient_name == "Donor 1"
            assert letters[1].recipient_name == "Donor 2"
            assert letters[2].recipient_name == "Donor 3"

    def test_preview_letter(self, sample_donation, organization_info):
        """Test letter preview generation."""
        generator = LetterGenerator()

        with patch.object(generator, "_get_template") as mock_get_template:
            mock_template = Mock()
            mock_template.render.return_value = "<html>Preview content</html>"
            mock_get_template.return_value = mock_template

            preview = generator.preview_letter(
                sample_donation, organization_info, custom_data={"preview": True}
            )

            assert preview == "<html>Preview content</html>"
            mock_template.render.assert_called_once()


class TestLetterEndpoints:
    """Test cases for letter API endpoints."""

    @pytest.mark.asyncio
    async def test_get_templates_endpoint(self):
        """Test GET /api/letters/templates endpoint."""
        from src.api.endpoints.letters import get_templates

        with patch("src.api.endpoints.letters.LetterGenerator") as mock_generator_class:
            mock_generator = Mock()
            mock_templates = [
                Mock(
                    name="test.html",
                    display_name="Test",
                    description="Test template",
                    fields=["field1"],
                )
            ]
            mock_generator.get_available_templates.return_value = mock_templates
            mock_generator_class.return_value = mock_generator

            response = await get_templates(current_user={"sub": "test_user"})

            assert response.success is True
            assert len(response.data) == 1
            assert response.data[0].template_id == "test"
            assert response.data[0].name == "Test"

    @pytest.mark.asyncio
    async def test_generate_letters_endpoint(self, organization_info):
        """Test POST /api/letters/generate endpoint."""
        from src.api.endpoints.letters import generate_letters

        request = LetterGenerationRequest(
            donation_ids=["donation_1", "donation_2"],
            template_name="default_letter.html",
            organization_info=organization_info,
            send_email=False,
        )

        with patch("src.api.endpoints.letters.LetterGenerator") as mock_generator_class:
            mock_generator = Mock()
            mock_letters = [
                GeneratedLetter(
                    donation_id="donation_1",
                    recipient_name="Donor 1",
                    template_name="default_letter.html",
                ),
                GeneratedLetter(
                    donation_id="donation_2",
                    recipient_name="Donor 2",
                    template_name="default_letter.html",
                ),
            ]
            mock_generator.generate_batch_letters.return_value = mock_letters
            mock_generator_class.return_value = mock_generator

            response = await generate_letters(
                request=request, current_user={"sub": "test_user"}
            )

            assert response.success is True
            assert isinstance(response.data, LetterBatch)
            assert response.data.total_count == 2
            assert len(response.data.letters) == 2

    @pytest.mark.asyncio
    async def test_preview_letter_endpoint(self, organization_info):
        """Test POST /api/letters/preview endpoint."""
        from src.api.endpoints.letters import preview_letter

        request = LetterGenerationRequest(
            donation_ids=["donation_1"],
            template_name="default_letter.html",
            organization_info=organization_info,
        )

        with patch("src.api.endpoints.letters.LetterGenerator") as mock_generator_class:
            mock_generator = Mock()
            mock_generator.preview_letter.return_value = "<html>Preview</html>"
            mock_generator_class.return_value = mock_generator

            response = await preview_letter(
                request=request, current_user={"sub": "test_user"}
            )

            assert response.success is True
            assert response.data == "<html>Preview</html>"
            assert "preview generated successfully" in response.message

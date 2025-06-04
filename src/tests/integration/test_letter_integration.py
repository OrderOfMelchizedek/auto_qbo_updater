"""Integration tests for letter generation functionality."""
import os
from datetime import date
from decimal import Decimal

import pytest

from src.models.donation import (
    Address,
    ContactInfo,
    DonationEntry,
    PayerInfo,
    PaymentInfo,
)
from src.models.letter import OrganizationInfo
from src.services.letter.letter_generator import LetterGenerator


@pytest.fixture
def test_organization():
    """Test organization for integration tests."""
    return OrganizationInfo(
        name="Integration Test Charity",
        address_line1="789 Test Blvd",
        city="Test City",
        state="TC",
        postal_code="99999",
        ein="98-7654321",
        treasurer_name="Test Treasurer",
        treasurer_title="Chief Financial Officer",
    )


@pytest.fixture
def test_donations():
    """Test donations for integration tests."""
    return [
        DonationEntry(
            payer_info=PayerInfo(name="Alice Johnson"),
            payment_info=PaymentInfo(
                amount=Decimal("500.00"),
                payment_date=date(2024, 1, 1),
                check_number="5001",
            ),
            contact_info=ContactInfo(
                email="alice@example.com",
                address=Address(
                    street1="100 First St",
                    city="Alicetown",
                    state="AL",
                    postal_code="11111",
                ),
            ),
        ),
        DonationEntry(
            payer_info=PayerInfo(name="Bob Williams"),
            payment_info=PaymentInfo(
                amount=Decimal("1000.00"),
                payment_date=date(2024, 1, 2),
                check_number="5002",
            ),
            contact_info=ContactInfo(email="bob@example.com"),
        ),
    ]


class TestLetterGeneratorIntegration:
    """Integration tests for LetterGenerator."""

    def test_template_loading(self):
        """Test that actual templates can be loaded."""
        generator = LetterGenerator()

        # Test default template exists
        template = generator._get_template("default_letter.html")
        assert template is not None

        # Test simple template exists
        template = generator._get_template("simple_letter.html")
        assert template is not None

        # Test fallback for non-existent template
        template = generator._get_template("non_existent.html")
        assert template is not None  # Should fall back to default

    def test_get_available_templates_real_files(self):
        """Test getting templates from actual file system."""
        generator = LetterGenerator()
        templates = generator.get_available_templates()

        # Should find at least our two templates
        assert len(templates) >= 2
        template_names = [t.name for t in templates]
        assert "default_letter.html" in template_names
        assert "simple_letter.html" in template_names

    def test_render_default_template(self, test_organization, test_donations):
        """Test rendering the default template with real data."""
        generator = LetterGenerator()
        donation = test_donations[0]

        # Prepare data
        letter_data = generator._prepare_letter_data(donation, test_organization)

        # Load and render template
        template = generator._get_template("default_letter.html")
        html_content = template.render(**letter_data)

        # Verify content
        assert "Integration Test Charity" in html_content
        assert "Alice Johnson" in html_content
        assert "$500.00" in html_content
        assert "5001" in html_content
        assert "98-7654321" in html_content
        assert "100 First St" in html_content

    def test_render_simple_template(self, test_organization, test_donations):
        """Test rendering the simple template."""
        generator = LetterGenerator()
        donation = test_donations[1]

        # Prepare data
        letter_data = generator._prepare_letter_data(donation, test_organization)

        # Load and render template
        template = generator._get_template("simple_letter.html")
        html_content = template.render(**letter_data)

        # Verify content
        assert "Integration Test Charity" in html_content
        assert "Bob Williams" in html_content
        assert "$1,000.00" in html_content
        assert "98-7654321" in html_content

    @pytest.mark.skipif(
        os.environ.get("CI") == "true",
        reason="PDF generation requires system dependencies",
    )
    def test_pdf_generation_with_real_template(self, test_organization, test_donations):
        """Test PDF generation with actual templates."""
        generator = LetterGenerator()
        donation = test_donations[0]

        # Generate letter without S3
        letter = generator.generate_letter(
            donation, test_organization, "default_letter.html"
        )

        # Verify PDF was generated
        assert letter.pdf_content is not None
        assert len(letter.pdf_content) > 0
        assert letter.pdf_content.startswith(b"%PDF")  # PDF magic number

    def test_batch_generation(self, test_organization, test_donations):
        """Test batch letter generation."""
        generator = LetterGenerator()

        # Generate batch
        letters = generator.generate_batch_letters(test_donations, test_organization)

        # Verify all letters generated
        assert len(letters) == len(test_donations)
        assert letters[0].recipient_name == "Alice Johnson"
        assert letters[1].recipient_name == "Bob Williams"

    def test_custom_data_merge(self, test_organization, test_donations):
        """Test custom data merging in templates."""
        generator = LetterGenerator()
        donation = test_donations[0]

        custom_data = {
            "custom_data": {
                "custom_message": "Special thanks for your continued support!",
                "campaign_name": "Annual Fund 2024",
            }
        }

        # Preview with custom data
        html_content = generator.preview_letter(
            donation, test_organization, "default_letter.html", custom_data
        )

        # Verify custom message appears
        assert "Special thanks for your continued support!" in html_content

    def test_error_handling_missing_required_fields(self):
        """Test error handling for missing required fields."""
        generator = LetterGenerator()

        # Create donation with minimal data
        donation = DonationEntry()

        # Organization missing required fields
        org = OrganizationInfo(
            name="Test",
            address_line1="123 St",
            city="City",
            state="ST",
            postal_code="12345",
            ein="12-3456789",
            treasurer_name="Test",
        )

        # Should handle gracefully
        letter_data = generator._prepare_letter_data(donation, org)
        assert letter_data["donor_name"] == "Valued Donor"
        assert letter_data["amount"] == Decimal("0")

    def test_template_with_all_features(self, test_organization):
        """Test template with all possible features."""
        generator = LetterGenerator()

        # Create donation with all fields
        donation = DonationEntry(
            payer_info=PayerInfo(
                name="Mr. John Q. Public Jr.", business_name="Public Enterprises LLC"
            ),
            payment_info=PaymentInfo(
                amount=Decimal("12345.67"),
                payment_date=date(2024, 12, 31),
                check_number="9999",
            ),
            contact_info=ContactInfo(
                email="john@public.com",
                phone="555-123-4567",
                address=Address(
                    street1="123 Main Street",
                    street2="Suite 456",
                    city="Metropolis",
                    state="NY",
                    postal_code="10001-1234",
                ),
            ),
            notes="VIP donor - handle with care",
        )

        # Add all organization fields
        org = OrganizationInfo(
            name="Full Feature Charity",
            address_line1="999 Charity Lane",
            address_line2="Executive Floor",
            city="Philanthropy",
            state="PH",
            postal_code="00000",
            phone="1-800-CHARITY",
            email="info@charity.org",
            ein="00-0000000",
            treasurer_name="Treasury McTreasureface",
            treasurer_title="Grand Poobah of Finance",
            mission_statement="to test all the features",
            logo_url="https://example.com/logo.png",
        )

        # Generate preview
        html_content = generator.preview_letter(donation, org)

        # Verify all fields rendered
        assert "Mr. John Q. Public Jr." in html_content
        assert "$12,345.67" in html_content
        assert "December 31, 2024" in html_content
        assert "9999" in html_content
        assert "Suite 456" in html_content
        assert "10001-1234" in html_content
        assert "Executive Floor" in html_content
        assert "1-800-CHARITY" in html_content
        assert "Grand Poobah of Finance" in html_content
        assert "to test all the features" in html_content

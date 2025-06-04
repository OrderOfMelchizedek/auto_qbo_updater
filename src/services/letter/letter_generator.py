"""Service for generating donation thank-you letters."""
import logging
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional

from jinja2 import Environment, FileSystemLoader, Template, select_autoescape
from weasyprint import HTML

from src.models.donation import DonationEntry
from src.models.letter import GeneratedLetter, LetterTemplate, OrganizationInfo
from src.services.storage.s3_service import S3Service
from src.utils.exceptions import DonationProcessingError

logger = logging.getLogger(__name__)


class LetterGenerator:
    """Service for generating donation receipt letters."""

    def __init__(self, s3_service: Optional[S3Service] = None):
        """
        Initialize the letter generator.

        Args:
            s3_service: Optional S3 service for storing generated letters
        """
        self.s3_service = s3_service

        # Set up Jinja2 environment
        template_dir = Path(__file__).parent.parent.parent.parent / "templates"
        self.env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(["html", "xml"]),
        )

        # Add custom filters
        self.env.filters["currency"] = self._format_currency
        self.env.filters["date"] = self._format_date

    def generate_letter(
        self,
        donation: DonationEntry,
        organization: OrganizationInfo,
        template_name: str = "default_letter.html",
        custom_data: Optional[Dict[str, Any]] = None,
    ) -> GeneratedLetter:
        """
        Generate a thank-you letter for a donation.

        Args:
            donation: Donation entry with donor and payment information
            organization: Organization information for the letter
            template_name: Name of the template to use
            custom_data: Additional custom data for the template

        Returns:
            Generated letter with PDF content and metadata
        """
        try:
            # Prepare letter data
            letter_data = self._prepare_letter_data(donation, organization, custom_data)

            # Load template
            template = self._get_template(template_name)

            # Render HTML
            html_content = template.render(**letter_data)

            # Generate PDF
            pdf_content = self._generate_pdf(html_content)

            # Store if S3 service available
            file_url = None
            if self.s3_service:
                file_name = self._generate_file_name(donation, organization)
                file_url = self.s3_service.upload_file(
                    file_object=pdf_content,
                    key=file_name,
                    content_type="application/pdf",
                )

            return GeneratedLetter(
                donation_id=str(id(donation)),  # TODO: Use actual donation ID
                recipient_name=donation.payer_info.name
                if donation.payer_info
                else "Donor",
                recipient_email=(
                    donation.contact_info.email if donation.contact_info else None
                ),
                template_name=template_name,
                pdf_content=pdf_content,
                file_url=file_url,
                generated_at=datetime.now(),
            )

        except Exception as e:
            logger.error(f"Failed to generate letter: {e}")
            raise DonationProcessingError(
                f"Letter generation failed: {str(e)}", details={"error": str(e)}
            )

    def generate_batch_letters(
        self,
        donations: List[DonationEntry],
        organization: OrganizationInfo,
        template_name: str = "default_letter.html",
        custom_data: Optional[Dict[str, Any]] = None,
    ) -> List[GeneratedLetter]:
        """
        Generate letters for multiple donations.

        Args:
            donations: List of donations to generate letters for
            organization: Organization information
            template_name: Template to use
            custom_data: Additional custom data

        Returns:
            List of generated letters
        """
        letters = []
        errors = []

        for donation in donations:
            try:
                letter = self.generate_letter(
                    donation, organization, template_name, custom_data
                )
                letters.append(letter)
            except Exception as e:
                logger.error(f"Failed to generate letter for donation: {e}")
                errors.append({"donation": donation, "error": str(e)})

        if errors:
            logger.warning(f"Failed to generate {len(errors)} letters")

        return letters

    def _prepare_letter_data(
        self,
        donation: DonationEntry,
        organization: OrganizationInfo,
        custom_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Prepare data for letter template."""
        data = {
            "organization": organization,
            "donation": donation,
            "donor_name": donation.payer_info.name
            if donation.payer_info
            else "Valued Donor",
            "amount": donation.payment_info.amount
            if donation.payment_info
            else Decimal("0"),
            "payment_date": (
                donation.payment_info.payment_date
                if donation.payment_info and donation.payment_info.payment_date
                else datetime.now().date()
            ),
            "check_number": (
                donation.payment_info.check_number if donation.payment_info else None
            ),
            "current_date": datetime.now().date(),
            "year": datetime.now().year,
        }

        # Add address information if available
        if donation.contact_info and donation.contact_info.address:
            data["address"] = donation.contact_info.address
            data["has_address"] = True
        else:
            data["has_address"] = False

        # Add salutation
        if donation.payer_info and donation.payer_info.name:
            parts = donation.payer_info.name.split()
            data["salutation"] = "Mr./Ms." if len(parts) > 1 else "Dear"
            data["last_name"] = (
                parts[-1] if len(parts) > 1 else donation.payer_info.name
            )
        else:
            data["salutation"] = "Dear"
            data["last_name"] = "Friend"

        # Merge custom data
        if custom_data:
            data.update(custom_data)

        return data

    def _get_template(self, template_name: str) -> Template:
        """Get a letter template."""
        try:
            return self.env.get_template(template_name)
        except Exception as e:
            logger.error(f"Failed to load template {template_name}: {e}")
            # Fall back to default template
            return self.env.get_template("default_letter.html")

    def _generate_pdf(self, html_content: str) -> bytes:
        """Generate PDF from HTML content."""
        try:
            # Create PDF
            pdf = HTML(string=html_content).write_pdf()
            return pdf
        except Exception as e:
            logger.error(f"Failed to generate PDF: {e}")
            raise

    def _generate_file_name(
        self, donation: DonationEntry, organization: OrganizationInfo
    ) -> str:
        """Generate a file name for the letter."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        donor_name = "unknown"
        if donation.payer_info and donation.payer_info.name:
            # Clean donor name for filename
            donor_name = (
                donation.payer_info.name.lower()
                .replace(" ", "_")
                .replace(".", "")
                .replace(",", "")
            )

        org_name = organization.name.lower().replace(" ", "_")
        return f"letters/{org_name}/{donor_name}_{timestamp}.pdf"

    def _format_currency(self, value: Decimal) -> str:
        """Format currency for display."""
        return f"${value:,.2f}"

    def _format_date(self, value: datetime) -> str:
        """Format date for display."""
        if isinstance(value, str):
            return value
        return value.strftime("%B %d, %Y")

    def get_available_templates(self) -> List[LetterTemplate]:
        """Get list of available letter templates."""
        templates = []
        template_dir = Path(__file__).parent.parent.parent.parent / "templates"

        for template_file in template_dir.glob("*.html"):
            if template_file.name.startswith("_"):
                continue  # Skip partial templates

            try:
                # Read template metadata from comments
                # Simple parsing - in production, use proper metadata
                name = template_file.stem
                description = f"Letter template: {name}"

                templates.append(
                    LetterTemplate(
                        name=template_file.name,
                        display_name=name.replace("_", " ").title(),
                        description=description,
                        fields=["donor_name", "amount", "payment_date"],
                    )
                )
            except Exception as e:
                logger.error(f"Failed to read template {template_file}: {e}")

        return templates

    def preview_letter(
        self,
        donation: DonationEntry,
        organization: OrganizationInfo,
        template_name: str = "default_letter.html",
        custom_data: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Preview a letter in HTML format.

        Args:
            donation: Donation to preview
            organization: Organization info
            template_name: Template to use
            custom_data: Additional data

        Returns:
            HTML content of the letter
        """
        letter_data = self._prepare_letter_data(donation, organization, custom_data)
        template = self._get_template(template_name)
        return template.render(**letter_data)

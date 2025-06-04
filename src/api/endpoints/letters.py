"""Letter generation endpoints."""
import logging
import uuid
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import List

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from src.api.dependencies.auth import CurrentUser
from src.models.api import APIResponse
from src.models.letter import LetterBatch, LetterGenerationRequest, LetterTemplate
from src.services.letter.letter_generator import LetterGenerator
from src.services.storage.s3_service import S3Service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/letters", tags=["letters"])


@router.get("/templates", response_model=APIResponse[List[LetterTemplate]])
async def get_templates(
    current_user: CurrentUser,
) -> APIResponse[List[LetterTemplate]]:
    """Get available letter templates."""
    try:
        letter_generator = LetterGenerator()
        templates = letter_generator.get_available_templates()

        # Convert to API format
        api_templates = []
        for template in templates:
            api_templates.append(
                LetterTemplate(
                    template_id=template.name.replace(".html", ""),
                    name=template.display_name,
                    description=template.description,
                    merge_fields=template.fields or [],
                    is_default=template.name == "default_letter.html",
                    created_by="system",
                )
            )

        return APIResponse(
            success=True,
            data=api_templates,
            message=f"Found {len(api_templates)} templates",
        )
    except Exception as e:
        logger.error(f"Failed to get templates: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve templates",
        )


@router.post("/generate", response_model=APIResponse[LetterBatch])
async def generate_letters(
    request: LetterGenerationRequest,
    current_user: CurrentUser,
) -> APIResponse[LetterBatch]:
    """
    Generate tax receipt letters for donations.

    Creates PDF letters using the specified template.
    """
    try:
        logger.info(f"Generating letters for {len(request.donation_ids)} donations")

        # Initialize services
        letter_generator = LetterGenerator(s3_service=S3Service())

        # TODO: Fetch actual donations from database
        # For now, create mock donations
        from datetime import date
        from decimal import Decimal

        from src.models.donation import (
            ContactInfo,
            DonationEntry,
            PayerInfo,
            PaymentInfo,
        )

        donations = []
        for donation_id in request.donation_ids:
            # This is mock data - replace with actual database fetch
            donation = DonationEntry(
                payer_info=PayerInfo(name=f"Donor {donation_id}"),
                payment_info=PaymentInfo(
                    amount=Decimal("100.00"),
                    payment_date=date.today(),
                    check_number="1234",
                ),
                contact_info=ContactInfo(email="donor@example.com"),
                notes=f"Donation {donation_id}",
            )
            donations.append(donation)

        # Generate letters
        generated_letters = letter_generator.generate_batch_letters(
            donations=donations,
            organization=request.organization_info,
            template_name=request.template_name,
            custom_data=request.custom_data,
        )

        # Create batch response
        batch_id = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        batch = LetterBatch(
            batch_id=batch_id,
            template_id=request.template_name.replace(".html", ""),
            letters=generated_letters,
            total_count=len(generated_letters),
            created_by=current_user.get("sub", "unknown"),
        )

        # TODO: Store batch information in database

        return APIResponse(
            success=True,
            data=batch,
            message=f"Generated {len(generated_letters)} letters successfully",
        )
    except Exception as e:
        logger.error(f"Failed to generate letters: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate letters",
        )


@router.get("/batches/{batch_id}", response_model=APIResponse[LetterBatch])
async def get_letter_batch(
    batch_id: str,
    current_user: CurrentUser,
) -> APIResponse[LetterBatch]:
    """Get letter batch details."""
    try:
        # TODO: Retrieve batch from database
        # For now, return a mock response
        logger.info(f"Retrieving letter batch {batch_id}")

        # This would normally fetch from database
        # For now, return not found
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Letter batch {batch_id} not found",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get letter batch: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve letter batch",
        )


@router.get("/download/{letter_id}")
async def download_letter(
    letter_id: str,
    current_user: CurrentUser,
) -> StreamingResponse:
    """
    Download a generated letter PDF.

    Returns the PDF file as a streaming response.
    """
    try:
        logger.info(f"Downloading letter {letter_id}")

        # TODO: Retrieve letter metadata from database
        # For now, check if we have a file URL

        # Initialize S3 service
        s3_service = S3Service()

        # TODO: Get actual file path from database
        # For demonstration, construct a file path
        file_key = f"letters/{letter_id}.pdf"

        # Try to get file from S3
        try:
            file_content = s3_service.download_file(file_key)

            return StreamingResponse(
                BytesIO(file_content),
                media_type="application/pdf",
                headers={
                    "Content-Disposition": (
                        f"attachment; filename=donation_letter_{letter_id}.pdf"
                    )
                },
            )
        except Exception:
            # File not found in S3
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Letter {letter_id} not found",
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to download letter: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to download letter",
        )


@router.post("/templates", response_model=APIResponse[LetterTemplate])
async def create_template(
    template: LetterTemplate,
    current_user: CurrentUser,
) -> APIResponse[LetterTemplate]:
    """Create a new letter template."""
    try:
        logger.info(f"Creating new template: {template.name}")

        # Generate template ID if not provided
        if not template.template_id:
            template.template_id = f"template_{uuid.uuid4().hex[:8]}"

        template.created_by = current_user.get("sub", "unknown")

        # TODO: Save template to database and file system
        # For now, we would:
        # 1. Save HTML content to templates directory
        # 2. Store metadata in database

        if template.html_template:
            # Would save to file system
            template_path = (
                Path(__file__).parent.parent.parent.parent.parent
                / "templates"
                / f"{template.template_id}.html"
            )
            # template_path.write_text(template.html_template)
            logger.info(f"Would save template to {template_path}")

        return APIResponse(
            success=True,
            data=template,
            message="Template created successfully",
        )
    except Exception as e:
        logger.error(f"Failed to create template: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create template",
        )


@router.post("/preview", response_model=APIResponse[str])
async def preview_letter(
    request: LetterGenerationRequest,
    current_user: CurrentUser,
) -> APIResponse[str]:
    """Preview a letter in HTML format."""
    try:
        logger.info("Previewing letter")

        # Initialize letter generator
        letter_generator = LetterGenerator()

        # Create a sample donation for preview
        from datetime import date
        from decimal import Decimal

        from src.models.donation import (
            Address,
            ContactInfo,
            DonationEntry,
            PayerInfo,
            PaymentInfo,
        )

        # Use first donation ID or create sample
        if request.donation_ids:
            # TODO: Fetch actual donation from database
            donation = DonationEntry(
                payer_info=PayerInfo(name="Sample Donor"),
                payment_info=PaymentInfo(
                    amount=Decimal("100.00"),
                    payment_date=date.today(),
                    check_number="1234",
                ),
                contact_info=ContactInfo(
                    email="donor@example.com",
                    address=Address(
                        street1="123 Main St",
                        city="Anytown",
                        state="CA",
                        postal_code="12345",
                    ),
                ),
                notes="Sample donation for preview",
            )
        else:
            # Create default sample
            donation = DonationEntry(
                payer_info=PayerInfo(name="John Doe"),
                payment_info=PaymentInfo(
                    amount=Decimal("250.00"),
                    payment_date=date.today(),
                    check_number="5678",
                ),
                contact_info=ContactInfo(
                    email="john.doe@example.com",
                    address=Address(
                        street1="456 Oak Ave",
                        city="Springfield",
                        state="IL",
                        postal_code="62701",
                    ),
                ),
                notes="Preview donation",
            )

        # Generate preview
        html_content = letter_generator.preview_letter(
            donation=donation,
            organization=request.organization_info,
            template_name=request.template_name,
            custom_data=request.custom_data,
        )

        return APIResponse(
            success=True,
            data=html_content,
            message="Letter preview generated successfully",
        )
    except Exception as e:
        logger.error(f"Failed to preview letter: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to preview letter",
        )

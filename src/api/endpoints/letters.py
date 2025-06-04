"""Letter generation endpoints."""
import logging
from typing import List

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from src.api.dependencies.auth import CurrentUser
from src.models.api import APIResponse
from src.models.letter import LetterBatch, LetterGenerationRequest, LetterTemplate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/letters", tags=["letters"])


@router.get("/templates", response_model=APIResponse[List[LetterTemplate]])
async def get_templates(
    current_user: CurrentUser,
) -> APIResponse[List[LetterTemplate]]:
    """Get available letter templates."""
    try:
        # TODO: Retrieve templates from storage
        default_template = LetterTemplate(
            template_id="default",
            name="Default Tax Receipt",
            description="Standard IRS-compliant tax receipt letter",
            html_template="""
            <h1>{{ organization_name }}</h1>
            <p>{{ organization_address }}</p>
            <p>Date: {{ letter_date }}</p>

            <p>Dear {{ donor_name }},</p>

            <p>Thank you for your generous donation of
            {{ donation_amount }} on {{ donation_date }}.</p>

            <p>{{ no_goods_services_statement }}</p>

            <p>Please retain this letter for your tax records.</p>

            <p>Sincerely,<br>
            {{ organization_name }}</p>
            """,
            merge_fields=[
                "organization_name",
                "organization_address",
                "donor_name",
                "donation_amount",
                "donation_date",
            ],
            is_default=True,
            created_by="system",
        )

        return APIResponse(
            success=True,
            data=[default_template],
            message="Templates retrieved successfully",
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
        # TODO: Implement letter generation
        logger.info(f"Generating letters for {len(request.donation_ids)} donations")

        batch = LetterBatch(
            batch_id="letter_batch_123",
            template_id=request.template_id,
            letters=[],
            total_count=0,
            created_by=current_user.get("sub", "unknown"),
        )

        return APIResponse(
            success=True,
            data=batch,
            message="Letter generation started",
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
        # TODO: Retrieve batch from storage
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
        # TODO: Get letter from storage and stream
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
        # TODO: Save template to storage
        template.created_by = current_user.get("sub", "unknown")

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

"""QuickBooks integration endpoints."""
import logging
from typing import Annotated, List, Optional

from fastapi import APIRouter, HTTPException, Query, status

from src.api.dependencies.auth import CurrentUser
from src.models.api import APIResponse, QuickBooksSyncRequest
from src.models.quickbooks import (
    CustomerMatch,
    MatchConfidence,
    QBConfig,
    QBCustomer,
    QBSyncResult,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/quickbooks", tags=["quickbooks"])


@router.get("/customers/search", response_model=APIResponse[List[QBCustomer]])
async def search_customers(
    current_user: CurrentUser,
    query: Annotated[str, Query(description="Search query")],
    limit: Annotated[int, Query(ge=1, le=50, description="Number of results")] = 10,
) -> APIResponse[List[QBCustomer]]:
    """
    Search QuickBooks customers.

    Searches by name, email, or phone number.
    """
    try:
        # TODO: Implement QuickBooks customer search
        logger.info(f"Searching QB customers with query: {query}")

        return APIResponse(
            success=True,
            data=[],
            message="No customers found",
        )
    except Exception as e:
        logger.error(f"Failed to search customers: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search QuickBooks customers",
        )


@router.post("/customers/match", response_model=APIResponse[CustomerMatch])
async def match_customer(
    donor_name: str,
    current_user: CurrentUser,
    email: Optional[str] = None,
    phone: Optional[str] = None,
) -> APIResponse[CustomerMatch]:
    """
    Find best matching QuickBooks customer for a donor.

    Uses fuzzy matching to find the most likely customer match.
    """
    try:
        # TODO: Implement customer matching logic
        logger.info(f"Matching customer for donor: {donor_name}")

        match = CustomerMatch(
            qb_customer=None,
            confidence=MatchConfidence.NO_MATCH,
            score=0.0,
            match_reasons=[],
        )

        return APIResponse(
            success=True,
            data=match,
            message="No matching customer found",
        )
    except Exception as e:
        logger.error(f"Failed to match customer: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to match customer",
        )


@router.post("/sync", response_model=APIResponse[List[QBSyncResult]])
async def sync_donations(
    request: QuickBooksSyncRequest,
    current_user: CurrentUser,
) -> APIResponse[List[QBSyncResult]]:
    """
    Sync donations to QuickBooks as sales receipts.

    Creates sales receipts and updates/creates customers as needed.
    """
    try:
        # TODO: Implement QuickBooks sync
        logger.info(f"Syncing {len(request.donation_ids)} donations to QuickBooks")

        results = []
        for donation_id in request.donation_ids:
            # Placeholder result
            result = QBSyncResult(
                donation_id=donation_id,
                success=False,
                error_message="QuickBooks sync not yet implemented",
                action_taken="skipped",
            )
            results.append(result)

        return APIResponse(
            success=True,
            data=results,
            message=f"Processed {len(results)} donations",
        )
    except Exception as e:
        logger.error(f"Failed to sync donations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to sync donations to QuickBooks",
        )


@router.get("/config", response_model=APIResponse[QBConfig])
async def get_quickbooks_config(
    current_user: CurrentUser,
) -> APIResponse[QBConfig]:
    """Get QuickBooks configuration for the current user."""
    try:
        # TODO: Retrieve user's QB configuration
        config = QBConfig(
            company_id="placeholder_company_id",
            payment_method_mappings={
                "check": "Check",
                "cash": "Cash",
                "credit_card": "Credit Card",
            },
        )

        return APIResponse(
            success=True,
            data=config,
            message="Configuration retrieved",
        )
    except Exception as e:
        logger.error(f"Failed to get QB config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve QuickBooks configuration",
        )


@router.put("/config", response_model=APIResponse[QBConfig])
async def update_quickbooks_config(
    config: QBConfig,
    current_user: CurrentUser,
) -> APIResponse[QBConfig]:
    """Update QuickBooks configuration."""
    try:
        # TODO: Save user's QB configuration
        logger.info(f"Updating QB config for user: {current_user}")

        return APIResponse(
            success=True,
            data=config,
            message="Configuration updated successfully",
        )
    except Exception as e:
        logger.error(f"Failed to update QB config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update QuickBooks configuration",
        )

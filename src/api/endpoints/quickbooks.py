"""QuickBooks integration endpoints."""
import json
import logging
from typing import List

from fastapi import APIRouter, HTTPException, status

from src.api.dependencies.auth import CurrentUser
from src.config.settings import settings
from src.models.api import APIResponse
from src.models.donation import DonationEntry
from src.models.quickbooks import (
    CustomerMatch,
    ManualReviewRequest,
    QuickBooksAuthCallback,
    QuickBooksSyncRequest,
    QuickBooksSyncResult,
    SyncStatus,
)
from src.services.auth.quickbooks_oauth import QuickBooksOAuth
from src.services.quickbooks.sync_service import MatchStrategy, QuickBooksSyncService
from src.utils.redis_client import get_redis_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/quickbooks", tags=["quickbooks"])

# Initialize OAuth service
qb_oauth = QuickBooksOAuth(
    client_id=settings.QUICKBOOKS_CLIENT_ID or "",
    client_secret=settings.QUICKBOOKS_CLIENT_SECRET or "",
    redirect_uri=settings.QUICKBOOKS_REDIRECT_URI,
)
redis_client = get_redis_client()


@router.get("/auth/url")
async def get_auth_url(
    current_user: CurrentUser,
) -> APIResponse[dict]:
    """Get QuickBooks OAuth authorization URL."""
    try:
        auth_url = qb_oauth.generate_auth_url()
        return APIResponse(
            success=True,
            data={"auth_url": auth_url},
            message="Authorization URL generated successfully",
        )
    except Exception as e:
        logger.error(f"Failed to generate auth URL: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate authorization URL",
        )


@router.post("/auth/callback")
async def handle_auth_callback(
    callback_data: QuickBooksAuthCallback,
    current_user: CurrentUser,
) -> APIResponse[dict]:
    """Handle QuickBooks OAuth callback."""
    try:
        # Validate state
        # Exchange authorization code for tokens
        token = qb_oauth._exchange_code_for_tokens(callback_data.code)
        # Add realm ID to token data
        token["realm_id"] = callback_data.realmId

        # Store tokens in Redis for the user
        # In production, encrypt tokens before storage
        user_id = current_user.get("email", "unknown")
        token_key = f"qb_token:{user_id}"
        redis_client.setex(
            token_key,
            3600,  # 1 hour expiry
            json.dumps(token),
        )

        return APIResponse(
            success=True,
            data={"company_id": callback_data.realmId},
            message="QuickBooks connected successfully",
        )
    except Exception as e:
        logger.error(f"OAuth callback failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth callback failed: {str(e)}",
        )


@router.get("/auth/status")
async def get_auth_status(
    current_user: CurrentUser,
) -> APIResponse[dict]:
    """Check QuickBooks connection status."""
    try:
        # Check if user has valid token
        user_id = current_user.get("email", "unknown")
        token_key = f"qb_token:{user_id}"
        token_data = redis_client.get(token_key)

        if not token_data:
            return APIResponse(
                success=True,
                data={"connected": False},
                message="QuickBooks not connected",
            )

        # Parse token and validate
        import json

        token = json.loads(token_data)
        sync_service = QuickBooksSyncService(token)

        if sync_service.validate_oauth_token():
            return APIResponse(
                success=True,
                data={
                    "connected": True,
                    "company_id": token.get("realm_id"),
                },
                message="QuickBooks connected",
            )
        else:
            # Token is invalid, remove it
            redis_client.delete(token_key)
            return APIResponse(
                success=True,
                data={"connected": False},
                message="QuickBooks connection expired",
            )
    except Exception as e:
        logger.error(f"Failed to check auth status: {e}")
        return APIResponse(
            success=False,
            data={"connected": False},
            message="Failed to check connection status",
        )


@router.post("/search/customers")
async def search_customers(
    donation: DonationEntry,
    current_user: CurrentUser,
) -> APIResponse[List[CustomerMatch]]:
    """
    Search for potential customer matches for a donation.

    This endpoint helps with manual matching by returning potential
    QuickBooks customers that might match the donor.
    """
    try:
        # Get user's QB token
        user_id = current_user.get("email", "unknown")
        token_key = f"qb_token:{user_id}"
        token_data = redis_client.get(token_key)

        if not token_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="QuickBooks not connected",
            )

        import json

        token = json.loads(token_data)
        sync_service = QuickBooksSyncService(token)

        # Search for matches
        if not donation.payer_info:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Donation must have payer information",
            )
        matches = sync_service.customer_service.search_customers(
            donation.payer_info, donation.contact_info
        )

        return APIResponse(
            success=True,
            data=matches,
            message=f"Found {len(matches)} potential matches",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Customer search failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search customers",
        )


@router.post("/sync/donation")
async def sync_single_donation(
    sync_request: QuickBooksSyncRequest,
    current_user: CurrentUser,
) -> APIResponse[QuickBooksSyncResult]:
    """
    Sync a single donation to QuickBooks.

    Supports automatic matching, manual customer selection, or creating new customers.
    """
    try:
        # Get user's QB token
        user_id = current_user.get("email", "unknown")
        token_key = f"qb_token:{user_id}"
        token_data = redis_client.get(token_key)

        if not token_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="QuickBooks not connected",
            )

        import json

        token = json.loads(token_data)
        sync_service = QuickBooksSyncService(token)

        # Determine strategy
        strategy = MatchStrategy(sync_request.strategy)

        # Sync donation
        result = sync_service.sync_donation(
            sync_request.donation,
            strategy,
            sync_request.customer_id,
        )

        return APIResponse(
            success=True,
            data=result,
            message="Donation sync completed",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Donation sync failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync donation: {str(e)}",
        )


@router.post("/sync/batch")
async def sync_donations_batch(
    donations: List[DonationEntry],
    current_user: CurrentUser,
    strategy: str = "auto_high",
) -> APIResponse[List[QuickBooksSyncResult]]:
    """
    Sync multiple donations to QuickBooks.

    This will attempt to automatically match donors with high confidence,
    and flag others for manual review.
    """
    try:
        # Get user's QB token
        user_id = current_user.get("email", "unknown")
        token_key = f"qb_token:{user_id}"
        token_data = redis_client.get(token_key)

        if not token_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="QuickBooks not connected",
            )

        import json

        token = json.loads(token_data)
        sync_service = QuickBooksSyncService(token)

        # Sync donations
        match_strategy = MatchStrategy(strategy)
        results = sync_service.sync_donations_batch(donations, match_strategy)

        # Calculate summary
        synced = sum(1 for r in results if r.status == SyncStatus.SYNCED)
        pending = sum(1 for r in results if r.status == SyncStatus.PENDING_REVIEW)
        errors = sum(1 for r in results if r.status == SyncStatus.ERROR)

        return APIResponse(
            success=True,
            data=results,
            message=(
                f"Batch sync complete: {synced} synced, "
                f"{pending} pending review, {errors} errors"
            ),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Batch sync failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync donations: {str(e)}",
        )


@router.get("/sync/pending")
async def get_pending_reviews(
    current_user: CurrentUser,
) -> APIResponse[List[dict]]:
    """Get donations pending manual review."""
    try:
        # Get user's QB token
        user_id = current_user.get("email", "unknown")
        token_key = f"qb_token:{user_id}"
        token_data = redis_client.get(token_key)

        if not token_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="QuickBooks not connected",
            )

        import json

        token = json.loads(token_data)
        sync_service = QuickBooksSyncService(token)

        # Get pending reviews
        pending = sync_service.get_pending_reviews()

        return APIResponse(
            success=True,
            data=pending,
            message=f"Found {len(pending)} donations pending review",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get pending reviews: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get pending reviews",
        )


@router.post("/sync/manual-review")
async def complete_manual_review(
    review_request: ManualReviewRequest,
    current_user: CurrentUser,
) -> APIResponse[QuickBooksSyncResult]:
    """Complete manual review for a donation."""
    try:
        # Get user's QB token
        user_id = current_user.get("email", "unknown")
        token_key = f"qb_token:{user_id}"
        token_data = redis_client.get(token_key)

        if not token_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="QuickBooks not connected",
            )

        import json

        token = json.loads(token_data)
        sync_service = QuickBooksSyncService(token)

        # Complete manual review
        result = sync_service.complete_manual_review(
            review_request.donation_id,
            review_request.customer_id,
            review_request.create_new,
        )

        return APIResponse(
            success=True,
            data=result,
            message="Manual review completed",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Manual review failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to complete manual review: {str(e)}",
        )


@router.get("/sync/stats")
async def get_sync_statistics(
    start_date: str,
    end_date: str,
    current_user: CurrentUser,
) -> APIResponse[dict]:
    """
    Get sync statistics for a date range.

    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
    """
    try:
        # Get user's QB token
        user_id = current_user.get("email", "unknown")
        token_key = f"qb_token:{user_id}"
        token_data = redis_client.get(token_key)

        if not token_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="QuickBooks not connected",
            )

        import json

        token = json.loads(token_data)
        sync_service = QuickBooksSyncService(token)

        # Get statistics
        stats = sync_service.get_sync_statistics(start_date, end_date)

        return APIResponse(
            success=True,
            data=stats,
            message="Statistics retrieved successfully",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get statistics",
        )

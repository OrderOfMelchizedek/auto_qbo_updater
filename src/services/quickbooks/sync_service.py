"""Service for syncing donations to QuickBooks."""
import logging
from enum import Enum
from typing import Any, Dict, List, Optional

from src.models.donation import DonationEntry
from src.models.quickbooks import CustomerMatch, QuickBooksSyncResult, SyncStatus
from src.services.quickbooks.customer_service import CustomerService
from src.services.quickbooks.sales_receipt_service import SalesReceiptService

# QuickBooksIntegrationError removed - not used
from src.utils.redis_client import get_redis_client

logger = logging.getLogger(__name__)


class MatchStrategy(str, Enum):
    """Customer matching strategies."""

    AUTO_MATCH_HIGH_CONFIDENCE = "auto_high"
    MANUAL_REVIEW = "manual"
    CREATE_NEW = "create_new"


class QuickBooksSyncService:
    """Service for syncing donations to QuickBooks."""

    def __init__(self, oauth_token: Dict[str, Any]):
        """
        Initialize the sync service.

        Args:
            oauth_token: OAuth token dictionary with access_token and realm_id
        """
        self.customer_service = CustomerService(oauth_token)
        self.receipt_service = SalesReceiptService(oauth_token)
        self.redis_client = get_redis_client()

        # Configuration
        self.auto_match_threshold = 0.85  # 85% confidence for auto-matching
        self.cache_ttl = 3600  # 1 hour cache

    def sync_donation(
        self,
        donation: DonationEntry,
        strategy: MatchStrategy = MatchStrategy.AUTO_MATCH_HIGH_CONFIDENCE,
        customer_id: Optional[str] = None,
    ) -> QuickBooksSyncResult:
        """
        Sync a single donation to QuickBooks.

        Args:
            donation: Donation to sync
            strategy: Matching strategy to use
            customer_id: Optional pre-selected customer ID (for manual matches)

        Returns:
            Sync result with customer and receipt information
        """
        try:
            # Validate donation
            if not donation.payer_info:
                raise ValueError("Donation must have payer information")
            if not donation.payment_info:
                raise ValueError("Donation must have payment information")

            # Handle customer matching based on strategy
            if customer_id:
                # Use provided customer ID
                customer = self.customer_service.get_customer(customer_id)
                match_confidence = 1.0  # Manual match
            elif strategy == MatchStrategy.CREATE_NEW:
                # Create new customer
                customer = self.customer_service.create_customer(
                    donation.payer_info, donation.contact_info
                )
                match_confidence = 1.0
            else:
                # Search for matches
                matches = self._search_customers_with_cache(donation)

                if not matches:
                    # No matches found, create new
                    customer = self.customer_service.create_customer(
                        donation.payer_info, donation.contact_info
                    )
                    match_confidence = 1.0
                elif (
                    strategy == MatchStrategy.AUTO_MATCH_HIGH_CONFIDENCE
                    and matches[0].confidence_score >= self.auto_match_threshold
                ):
                    # Auto-match with high confidence
                    customer = self.customer_service.get_customer(
                        matches[0].customer_id
                    )
                    match_confidence = matches[0].confidence_score
                else:
                    # Requires manual review
                    return QuickBooksSyncResult(
                        donation_id=str(id(donation)),  # TODO: Use actual donation ID
                        status=SyncStatus.PENDING_REVIEW,
                        customer_matches=matches,
                    )

            # Create sales receipt
            receipt = self.receipt_service.create_sales_receipt(donation, customer.id)

            # Update donation with QB info
            if donation.quickbooks_info:
                donation.quickbooks_info.customer_id = customer.id
                donation.quickbooks_info.customer_name = customer.display_name
                donation.quickbooks_info.receipt_id = receipt.id
                donation.quickbooks_info.sync_status = SyncStatus.SYNCED
                donation.quickbooks_info.match_confidence = str(match_confidence)

            return QuickBooksSyncResult(
                donation_id=str(id(donation)),  # TODO: Use actual donation ID
                status=SyncStatus.SYNCED,
                customer_id=customer.id,
                customer_name=customer.display_name,
                receipt_id=receipt.id,
                receipt_number=receipt.doc_number,
                match_confidence=match_confidence,
            )

        except Exception as e:
            logger.error(f"Failed to sync donation: {e}")
            return QuickBooksSyncResult(
                donation_id=str(id(donation)),  # TODO: Use actual donation ID
                status=SyncStatus.ERROR,
                error_message=str(e),
            )

    def sync_donations_batch(
        self,
        donations: List[DonationEntry],
        strategy: MatchStrategy = MatchStrategy.AUTO_MATCH_HIGH_CONFIDENCE,
    ) -> List[QuickBooksSyncResult]:
        """
        Sync multiple donations to QuickBooks.

        Args:
            donations: List of donations to sync
            strategy: Matching strategy to use

        Returns:
            List of sync results
        """
        results = []

        # Group donations by sync approach
        auto_sync = []
        manual_review = []

        for donation in donations:
            if not donation.payer_info or not donation.payment_info:
                results.append(
                    QuickBooksSyncResult(
                        donation_id=str(id(donation)),
                        status=SyncStatus.ERROR,
                        error_message="Missing required payer or payment information",
                    )
                )
                continue

            # Search for customer matches
            matches = self._search_customers_with_cache(donation)

            if (
                matches
                and strategy == MatchStrategy.AUTO_MATCH_HIGH_CONFIDENCE
                and matches[0].confidence_score >= self.auto_match_threshold
            ):
                auto_sync.append((donation, matches[0].customer_id))
            else:
                manual_review.append((donation, matches))

        # Process auto-sync donations
        if auto_sync:
            logger.info(f"Auto-syncing {len(auto_sync)} donations")
            for donation, customer_id in auto_sync:
                result = self.sync_donation(
                    donation, MatchStrategy.AUTO_MATCH_HIGH_CONFIDENCE, customer_id
                )
                results.append(result)

        # Mark manual review donations
        for donation, matches in manual_review:
            results.append(
                QuickBooksSyncResult(
                    donation_id=str(id(donation)),
                    status=SyncStatus.PENDING_REVIEW,
                    customer_matches=matches,
                )
            )

        # Log summary
        synced = sum(1 for r in results if r.status == SyncStatus.SYNCED)
        pending = sum(1 for r in results if r.status == SyncStatus.PENDING_REVIEW)
        errors = sum(1 for r in results if r.status == SyncStatus.ERROR)

        logger.info(
            f"Batch sync complete: {synced} synced, {pending} pending review, "
            f"{errors} errors"
        )

        return results

    def get_pending_reviews(self) -> List[Dict[str, Any]]:
        """
        Get donations pending manual review.

        Returns:
            List of donations with their potential matches
        """
        # TODO: Implement database query to get pending donations
        # For now, return empty list
        return []

    def complete_manual_review(
        self,
        donation_id: str,
        customer_id: Optional[str] = None,
        create_new: bool = False,
    ) -> QuickBooksSyncResult:
        """
        Complete manual review for a donation.

        Args:
            donation_id: ID of the donation pending review
            customer_id: Selected customer ID (if matching existing)
            create_new: Whether to create a new customer

        Returns:
            Sync result
        """
        # TODO: Implement with actual database
        # For now, return error
        return QuickBooksSyncResult(
            donation_id=donation_id,
            status=SyncStatus.ERROR,
            error_message="Manual review completion not yet implemented",
        )

    def _search_customers_with_cache(
        self, donation: DonationEntry
    ) -> List[CustomerMatch]:
        """Search for customers with caching."""
        # Generate cache key based on payer info
        if not donation.payer_info:
            return []
        cache_key = f"qb_customer_search:{donation.payer_info.name}"

        # Check cache
        cached_result = self.redis_client.get(cache_key)
        if cached_result:
            # Parse cached matches
            import json

            cached_data = json.loads(cached_result)
            return [CustomerMatch(**match) for match in cached_data]

        # Search customers
        matches = self.customer_service.search_customers(
            donation.payer_info, donation.contact_info
        )

        # Cache results
        if matches:
            import json

            cache_data = [match.model_dump() for match in matches]
            self.redis_client.setex(cache_key, self.cache_ttl, json.dumps(cache_data))

        return matches

    def validate_oauth_token(self) -> bool:
        """
        Validate that the OAuth token is still valid.

        Returns:
            True if valid, False otherwise
        """
        try:
            # Try a simple query to validate token
            query = "SELECT COUNT(*) FROM Customer WHERE Active = true"
            self.customer_service._execute_query(query)
            return True
        except Exception as e:
            logger.error(f"OAuth token validation failed: {e}")
            return False

    def get_sync_statistics(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """
        Get sync statistics for a date range.

        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            Dictionary with sync statistics
        """
        # TODO: Implement with actual database queries
        return {
            "total_donations": 0,
            "synced": 0,
            "pending_review": 0,
            "errors": 0,
            "auto_matched": 0,
            "manually_matched": 0,
            "new_customers_created": 0,
        }

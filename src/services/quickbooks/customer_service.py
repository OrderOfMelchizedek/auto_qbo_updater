"""Service for QuickBooks customer operations."""
import logging
from typing import Any, Dict, List, Optional, Tuple

import requests
from authlib.integrations.requests_client import OAuth2Session

from src.config.settings import settings
from src.models.donation import ContactInfo, PayerInfo
from src.models.quickbooks import CustomerMatch, QuickBooksCustomer
from src.utils.exceptions import QuickBooksIntegrationError

logger = logging.getLogger(__name__)


class CustomerService:
    """Service for managing QuickBooks customers."""

    def __init__(self, oauth_token: Dict[str, Any]):
        """
        Initialize the customer service.

        Args:
            oauth_token: OAuth token dictionary with access_token and realm_id
        """
        self.oauth_token = oauth_token
        self.realm_id = oauth_token.get("realm_id")
        self.base_url = f"{settings.QUICKBOOKS_BASE_URL}/v3/company/{self.realm_id}"

        # Create OAuth session
        self.session = OAuth2Session(
            client_id=settings.QUICKBOOKS_CLIENT_ID,
            token=oauth_token,
        )

    def search_customers(
        self, payer_info: PayerInfo, contact_info: Optional[ContactInfo] = None
    ) -> List[CustomerMatch]:
        """
        Search for customers in QuickBooks based on donor information.

        Args:
            payer_info: Payer information from donation
            contact_info: Optional contact information for additional matching

        Returns:
            List of potential customer matches with confidence scores
        """
        try:
            matches = []

            # Search by name variations
            if payer_info.name:
                name_matches = self._search_by_name(payer_info.name)
                matches.extend(name_matches)

            # Search by aliases
            for alias in payer_info.aliases:
                alias_matches = self._search_by_name(alias)
                matches.extend(alias_matches)

            # Search by email if available
            if contact_info and contact_info.email:
                email_matches = self._search_by_email(contact_info.email)
                matches.extend(email_matches)

            # Deduplicate and score matches
            unique_matches = self._deduplicate_and_score_matches(
                matches, payer_info, contact_info
            )

            # Sort by confidence score
            unique_matches.sort(key=lambda x: x.confidence_score, reverse=True)

            logger.info(
                f"Found {len(unique_matches)} potential matches for {payer_info.name}"
            )

            return unique_matches[:5]  # Return top 5 matches

        except requests.RequestException as e:
            logger.error(f"Failed to search customers: {e}")
            raise QuickBooksIntegrationError(
                f"Customer search failed: {str(e)}", details={"error": str(e)}
            )

    def _search_by_name(self, name: str) -> List[Dict[str, Any]]:
        """Search customers by name using various strategies."""
        matches = []

        # Clean and prepare name for search
        clean_name = name.strip()

        # Search by full display name
        query = (
            f"SELECT * FROM Customer WHERE Active = true AND "
            f"DisplayName LIKE '%{clean_name}%'"
        )
        matches.extend(self._execute_query(query))

        # Search by company name
        query = (
            f"SELECT * FROM Customer WHERE Active = true AND "
            f"CompanyName LIKE '%{clean_name}%'"
        )
        matches.extend(self._execute_query(query))

        # If name has multiple parts, search by family/given name
        name_parts = clean_name.split()
        if len(name_parts) >= 2:
            # Try last name as family name
            query = (
                f"SELECT * FROM Customer WHERE Active = true AND "
                f"FamilyName LIKE '%{name_parts[-1]}%'"
            )
            matches.extend(self._execute_query(query))

            # Try first name as given name
            query = (
                f"SELECT * FROM Customer WHERE Active = true AND "
                f"GivenName LIKE '%{name_parts[0]}%'"
            )
            matches.extend(self._execute_query(query))

        return matches

    def _search_by_email(self, email: str) -> List[Dict[str, Any]]:
        """Search customers by email address."""
        query = (
            f"SELECT * FROM Customer WHERE Active = true AND "
            f"PrimaryEmailAddr LIKE '%{email}%'"
        )
        return self._execute_query(query)

    def _execute_query(self, query: str) -> List[Dict[str, Any]]:
        """Execute a QuickBooks query."""
        try:
            response = self.session.get(
                f"{self.base_url}/query",
                params={"query": query},
            )
            response.raise_for_status()

            data = response.json()
            return data.get("QueryResponse", {}).get("Customer", [])

        except requests.RequestException as e:
            logger.error(f"Query execution failed: {e}")
            return []

    def _deduplicate_and_score_matches(
        self,
        matches: List[Dict[str, Any]],
        payer_info: PayerInfo,
        contact_info: Optional[ContactInfo],
    ) -> List[CustomerMatch]:
        """Deduplicate matches and calculate confidence scores."""
        seen_ids = set()
        unique_matches = []

        for match in matches:
            customer_id = match.get("Id")
            if customer_id in seen_ids:
                continue
            seen_ids.add(customer_id)

            # Calculate confidence score
            score = self._calculate_match_score(match, payer_info, contact_info)

            # Create CustomerMatch object
            customer_match = CustomerMatch(
                customer_id=customer_id,
                display_name=match.get("DisplayName", ""),
                company_name=match.get("CompanyName"),
                given_name=match.get("GivenName"),
                family_name=match.get("FamilyName"),
                email=match.get("PrimaryEmailAddr", {}).get("Address"),
                phone=match.get("PrimaryPhone", {}).get("FreeFormNumber"),
                confidence_score=score,
                match_reasons=self._get_match_reasons(match, payer_info, contact_info),
            )

            unique_matches.append(customer_match)

        return unique_matches

    def _calculate_match_score(
        self,
        customer: Dict[str, Any],
        payer_info: PayerInfo,
        contact_info: Optional[ContactInfo],
    ) -> float:
        """Calculate confidence score for a customer match."""
        score = 0.0
        max_score = 0.0

        # Name matching (40% weight)
        name_score, name_max = self._score_name_match(customer, payer_info)
        score += name_score * 0.4
        max_score += name_max * 0.4

        # Email matching (30% weight)
        if contact_info and contact_info.email:
            email_score = self._score_email_match(customer, contact_info.email)
            score += email_score * 0.3
            max_score += 0.3

        # Address matching (20% weight)
        if contact_info and contact_info.address:
            addr_score = self._score_address_match(customer, contact_info)
            score += addr_score * 0.2
            max_score += 0.2

        # Phone matching (10% weight)
        if contact_info and contact_info.phone:
            phone_score = self._score_phone_match(customer, contact_info.phone)
            score += phone_score * 0.1
            max_score += 0.1

        # Normalize to 0-1 range
        return score / max_score if max_score > 0 else 0.0

    def _score_name_match(
        self, customer: Dict[str, Any], payer_info: PayerInfo
    ) -> Tuple[float, float]:
        """Score name matching between customer and payer."""
        score = 0.0
        max_score = 1.0

        customer_display = customer.get("DisplayName", "").lower()
        customer_company = customer.get("CompanyName", "").lower()
        customer_given = customer.get("GivenName", "").lower()
        customer_family = customer.get("FamilyName", "").lower()

        payer_name = payer_info.name.lower()

        # Exact match on display name
        if customer_display == payer_name:
            return 1.0, max_score

        # Exact match on company name
        if customer_company and customer_company == payer_name:
            return 1.0, max_score

        # Check aliases
        for alias in payer_info.aliases:
            alias_lower = alias.lower()
            if customer_display == alias_lower or customer_company == alias_lower:
                return 0.9, max_score

        # Partial matches - check display name and company name
        if (
            payer_name in customer_display
            or customer_display in payer_name
            or (
                customer_company
                and (payer_name in customer_company or customer_company in payer_name)
            )
        ):
            score = 0.7

        # Name parts matching
        name_parts = payer_name.split()
        if len(name_parts) >= 2:
            # Check if all name parts are in customer display name
            # (handles "Smith, John" format)
            all_parts_found = all(part in customer_display for part in name_parts)
            if all_parts_found:
                score = max(score, 0.8)

            # Check given/family name fields
            if customer_given and name_parts[0] in customer_given:
                score += 0.3
            if customer_family and name_parts[-1] in customer_family:
                score += 0.3

        return min(score, 1.0), max_score

    def _score_email_match(self, customer: Dict[str, Any], email: str) -> float:
        """Score email matching."""
        customer_email = customer.get("PrimaryEmailAddr", {}).get("Address", "").lower()
        if customer_email == email.lower():
            return 1.0
        return 0.0

    def _score_address_match(
        self, customer: Dict[str, Any], contact_info: ContactInfo
    ) -> float:
        """Score address matching."""
        if not contact_info.address:
            return 0.0

        score = 0.0
        bill_addr = customer.get("BillAddr", {})

        # ZIP code match (highest weight)
        if (
            contact_info.address.postal_code
            and bill_addr.get("PostalCode")
            and contact_info.address.postal_code == bill_addr["PostalCode"]
        ):
            score += 0.5

        # City match
        if (
            contact_info.address.city
            and bill_addr.get("City")
            and contact_info.address.city.lower() == bill_addr["City"].lower()
        ):
            score += 0.3

        # State match
        if (
            contact_info.address.state
            and bill_addr.get("CountrySubDivisionCode")
            and contact_info.address.state.upper()
            == bill_addr["CountrySubDivisionCode"]
        ):
            score += 0.2

        return score

    def _score_phone_match(self, customer: Dict[str, Any], phone: str) -> float:
        """Score phone matching."""
        customer_phone = customer.get("PrimaryPhone", {}).get("FreeFormNumber", "")
        # Remove non-numeric characters for comparison
        clean_phone = "".join(filter(str.isdigit, phone))
        clean_customer_phone = "".join(filter(str.isdigit, customer_phone))

        # Check if last 7 digits match (local number)
        if (
            clean_phone
            and clean_customer_phone
            and clean_phone[-7:] == clean_customer_phone[-7:]
        ):
            return 1.0
        return 0.0

    def _get_match_reasons(
        self,
        customer: Dict[str, Any],
        payer_info: PayerInfo,
        contact_info: Optional[ContactInfo],
    ) -> List[str]:
        """Get reasons why this customer matched."""
        reasons = []

        # Check name matches
        customer_display = customer.get("DisplayName", "").lower()
        customer_company = customer.get("CompanyName", "").lower()
        payer_name = payer_info.name.lower()

        if customer_display == payer_name or customer_company == payer_name:
            reasons.append("Exact name match")
        elif payer_name in customer_display or payer_name in customer_company:
            reasons.append("Partial name match")

        # Check email match
        if contact_info and contact_info.email:
            customer_email = customer.get("PrimaryEmailAddr", {}).get("Address", "")
            if customer_email.lower() == contact_info.email.lower():
                reasons.append("Email match")

        # Check address match
        if contact_info and contact_info.address:
            bill_addr = customer.get("BillAddr", {})
            if (
                contact_info.address.postal_code
                and bill_addr.get("PostalCode") == contact_info.address.postal_code
            ):
                reasons.append("ZIP code match")

        return reasons

    def get_customer(self, customer_id: str) -> QuickBooksCustomer:
        """
        Get a customer by ID.

        Args:
            customer_id: QuickBooks customer ID

        Returns:
            Customer details
        """
        try:
            response = self.session.get(f"{self.base_url}/customer/{customer_id}")
            response.raise_for_status()

            data = response.json()
            customer_data = data.get("Customer", {})

            return self._parse_customer(customer_data)

        except requests.RequestException as e:
            logger.error(f"Failed to get customer {customer_id}: {e}")
            raise QuickBooksIntegrationError(
                f"Failed to get customer: {str(e)}", details={"error": str(e)}
            )

    def create_customer(
        self, payer_info: PayerInfo, contact_info: Optional[ContactInfo] = None
    ) -> QuickBooksCustomer:
        """
        Create a new customer in QuickBooks.

        Args:
            payer_info: Payer information
            contact_info: Optional contact information

        Returns:
            Created customer details
        """
        try:
            # Build customer data
            customer_data = {
                "DisplayName": payer_info.name,
                "Active": True,
            }

            # Add organization name if available
            if payer_info.organization:
                customer_data["CompanyName"] = payer_info.organization

            # Parse name into given/family if possible
            name_parts = payer_info.name.split()
            if len(name_parts) >= 2:
                customer_data["GivenName"] = name_parts[0]
                customer_data["FamilyName"] = " ".join(name_parts[1:])

            # Add contact information
            if contact_info:
                if contact_info.email:
                    customer_data["PrimaryEmailAddr"] = {"Address": contact_info.email}

                if contact_info.phone:
                    customer_data["PrimaryPhone"] = {
                        "FreeFormNumber": contact_info.phone
                    }

                if contact_info.address:
                    bill_addr = {
                        "Line1": contact_info.address.street1,
                        "City": contact_info.address.city,
                        "CountrySubDivisionCode": contact_info.address.state,
                        "PostalCode": contact_info.address.postal_code,
                    }
                    if contact_info.address.street2:
                        bill_addr["Line2"] = contact_info.address.street2
                    customer_data["BillAddr"] = bill_addr

            # Create customer
            response = self.session.post(
                f"{self.base_url}/customer",
                json=customer_data,
            )
            response.raise_for_status()

            data = response.json()
            created_customer = data.get("Customer", {})

            logger.info(f"Created customer: {created_customer.get('Id')}")

            return self._parse_customer(created_customer)

        except requests.RequestException as e:
            logger.error(f"Failed to create customer: {e}")
            raise QuickBooksIntegrationError(
                f"Customer creation failed: {str(e)}", details={"error": str(e)}
            )

    def _parse_customer(self, customer_data: Dict[str, Any]) -> QuickBooksCustomer:
        """Parse QuickBooks customer data into our model."""
        return QuickBooksCustomer(
            id=customer_data.get("Id"),
            sync_token=customer_data.get("SyncToken"),
            display_name=customer_data.get("DisplayName", ""),
            company_name=customer_data.get("CompanyName"),
            given_name=customer_data.get("GivenName"),
            family_name=customer_data.get("FamilyName"),
            email=customer_data.get("PrimaryEmailAddr", {}).get("Address"),
            phone=customer_data.get("PrimaryPhone", {}).get("FreeFormNumber"),
            active=customer_data.get("Active", True),
            balance=customer_data.get("Balance", 0),
        )

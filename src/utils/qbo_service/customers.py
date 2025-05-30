"""
QuickBooks Online Customer Service.

This module handles customer search, creation, update, and caching operations.
"""

import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import requests

from .base import QBOBaseService

logger = logging.getLogger(__name__)


class QBOCustomerService(QBOBaseService):
    """Service for managing QuickBooks Online customers."""

    def __init__(self, auth_service):
        """Initialize customer service with auth service.

        Args:
            auth_service: QBOAuthService instance
        """
        super().__init__(auth_service)

        # Performance optimization: Customer caching
        self._customer_cache: Dict[str, Any] = {}
        self._cache_timestamp: Optional[float] = None
        self._cache_lock = threading.Lock()
        self._cache_ttl = 300  # 5 minutes cache TTL

    def find_customers_batch(self, customer_lookups: List[str]) -> Dict[str, Optional[Dict[str, Any]]]:
        """Find multiple customers in QBO using batch processing for better performance.

        Args:
            customer_lookups: List of customer names or lookup values

        Returns:
            Dictionary mapping lookup values to customer data (or None if not found)
        """
        if not self.auth_service.is_token_valid():
            logger.warning("Not authenticated with QBO")
            return {lookup: None for lookup in customer_lookups}

        # Remove duplicates and empty values
        unique_lookups = list({lookup.strip() for lookup in customer_lookups if lookup and lookup.strip()})

        if not unique_lookups:
            return {lookup: None for lookup in customer_lookups}

        results = {}

        # Check cache first
        uncached_lookups = []
        for lookup in unique_lookups:
            cached_customer = self.get_cached_customer(lookup)
            if cached_customer:
                results[lookup] = cached_customer
            else:
                uncached_lookups.append(lookup)

        logger.info(f"Batch customer lookup: {len(unique_lookups)} total, {len(uncached_lookups)} not in cache")

        # Process uncached lookups with parallel processing
        if uncached_lookups:
            with ThreadPoolExecutor(max_workers=5) as executor:
                future_to_lookup = {executor.submit(self.find_customer, lookup): lookup for lookup in uncached_lookups}

                for future in as_completed(future_to_lookup):
                    lookup = future_to_lookup[future]
                    try:
                        customer = future.result()
                        results[lookup] = customer

                        # Cache the result for future use
                        if customer:
                            with self._cache_lock:
                                self._customer_cache[lookup.lower()] = customer
                    except Exception as e:
                        logger.error(f"Error finding customer '{lookup}': {str(e)}")
                        results[lookup] = None

        # Map original input lookups to results (including duplicates)
        final_results = {}
        for original_lookup in customer_lookups:
            clean_lookup = original_lookup.strip() if original_lookup else ""
            final_results[original_lookup] = results.get(clean_lookup)

        return final_results

    def find_customer(self, customer_lookup: str) -> Optional[Dict[str, Any]]:
        """Find a customer in QBO by name or other lookup value with enhanced fuzzy matching.

        Args:
            customer_lookup: Customer name or other lookup value

        Returns:
            Customer data if found, None otherwise
        """
        if not self.auth_service.is_token_valid():
            logger.warning("Not authenticated with QBO")
            return None

        # Handle empty lookup values
        if not customer_lookup or customer_lookup.strip() == "":
            logger.warning("Empty customer lookup value")
            return None

        # Try cache first for performance
        cached_customer = self.get_cached_customer(customer_lookup)
        if cached_customer:
            logger.info(f"Found customer '{customer_lookup}' in cache: {cached_customer.get('DisplayName')}")
            return cached_customer

        # Properly escape the lookup value
        safe_lookup = self._escape_query_value(customer_lookup)

        try:
            logger.info(f"Finding customer with progressive matching: '{customer_lookup}'")

            # Strategy 1: Exact match on DisplayName (highest confidence)
            query = f"SELECT * FROM Customer WHERE DisplayName = '{safe_lookup}'"  # nosec B608
            encoded_query = quote(query)

            response = self._make_qbo_request("GET", f"query?query={encoded_query}")
            if response.get("QueryResponse", {}).get("Customer"):
                customer = response["QueryResponse"]["Customer"][0]
                return self._cache_and_return_customer(customer, "Strategy 1 - Exact")

            # Strategy 2: Match on partial DisplayName (contains)
            query = f"SELECT * FROM Customer WHERE DisplayName LIKE '%{safe_lookup}%'"  # nosec B608
            encoded_query = quote(query)

            response = self._make_qbo_request("GET", f"query?query={encoded_query}")
            if response.get("QueryResponse", {}).get("Customer"):
                customer = response["QueryResponse"]["Customer"][0]
                return self._cache_and_return_customer(customer, "Strategy 2 - Partial")

            # Strategy 3: Try matching after reversing the name parts
            # This handles cases like "John Smith" vs "Smith, John"
            name_parts = safe_lookup.split()
            if len(name_parts) >= 2:
                # Try last name first pattern
                if "," not in safe_lookup:  # Only if original doesn't have a comma
                    reversed_name = f"{name_parts[-1]}, {' '.join(name_parts[:-1])}"
                    escaped_reversed = self._escape_query_value(reversed_name)
                    query = f"SELECT * FROM Customer WHERE DisplayName LIKE '%{escaped_reversed}%'"  # nosec B608
                    encoded_query = quote(query)

                    response = self._make_qbo_request("GET", f"query?query={encoded_query}")
                    if response.get("QueryResponse", {}).get("Customer"):
                        customer = response["QueryResponse"]["Customer"][0]
                        return self._cache_and_return_customer(customer, "Strategy 3 - Reversed name")

                # Try comma-separated to space-separated conversion
                elif "," in safe_lookup:  # Handle "Smith, John" to "John Smith" format
                    parts = safe_lookup.split(",")
                    if len(parts) == 2:
                        # Take last name from before comma, first name from after comma, and reverse them
                        space_separated = f"{parts[1].strip()} {parts[0].strip()}"
                        escaped_space_separated = self._escape_query_value(space_separated)
                        query = (
                            f"SELECT * FROM Customer WHERE DisplayName LIKE '%{escaped_space_separated}%'"  # nosec B608
                        )
                        encoded_query = quote(query)

                        response = self._make_qbo_request("GET", f"query?query={encoded_query}")
                        if response.get("QueryResponse", {}).get("Customer"):
                            customer = response["QueryResponse"]["Customer"][0]
                            return self._cache_and_return_customer(customer, "Strategy 3b - Comma to space conversion")

            # Strategy 4: Try matching on significant parts
            # Remove common tokens like "and", "&", etc.
            significant_parts = []
            skip_tokens = ["and", "&", "mr", "mrs", "ms", "dr", "the", "of", "for"]

            # Extract significant tokens
            for part in safe_lookup.lower().replace(",", " ").replace(".", " ").split():
                if part not in skip_tokens and len(part) > 1:
                    significant_parts.append(part)

            if significant_parts:
                # Sort tokens by length (longer tokens are likely more specific)
                significant_parts.sort(key=len, reverse=True)

                # Try to match on the most significant tokens
                for significant_part in significant_parts:
                    if len(significant_part) > 3:  # Only use tokens with more than 3 chars
                        escaped_part = self._escape_query_value(significant_part)
                        query = f"SELECT * FROM Customer WHERE DisplayName LIKE '%{escaped_part}%'"  # nosec B608
                        encoded_query = quote(query)

                        response = self._make_qbo_request("GET", f"query?query={encoded_query}")
                        if response.get("QueryResponse", {}).get("Customer"):
                            customer = response["QueryResponse"]["Customer"][0]
                            return self._cache_and_return_customer(
                                customer, f"Strategy 4 - Significant part ('{significant_part}')"
                            )

            # Strategy 5: Try matching on email domain
            # This handles organization names vs email domains (e.g., "XYZ Foundation" vs "xyz.org")
            if "@" in safe_lookup:
                # Extract the domain part of the email
                email_parts = safe_lookup.split("@")
                if len(email_parts) == 2 and "." in email_parts[1]:
                    domain = email_parts[1]
                    # Get the part before the TLD
                    org_name = domain.split(".")[0]
                    if len(org_name) > 3:  # Only use if meaningful
                        escaped_org_name = self._escape_query_value(org_name)
                        query = f"SELECT * FROM Customer WHERE DisplayName LIKE '%{escaped_org_name}%'"  # nosec B608
                        encoded_query = quote(query)

                        response = self._make_qbo_request("GET", f"query?query={encoded_query}")
                        if response.get("QueryResponse", {}).get("Customer"):
                            customer = response["QueryResponse"]["Customer"][0]
                            return self._cache_and_return_customer(
                                customer, f"Strategy 5 - Email domain ('{org_name}')"
                            )

            # Strategy 6: Try searching by Primary Phone for numeric inputs
            # This is useful if the lookup string is a phone number
            if safe_lookup.replace("-", "").replace(" ", "").replace("(", "").replace(")", "").isdigit():
                # Format a cleaned phone number (last 10 digits)
                cleaned_phone = "".join([c for c in safe_lookup if c.isdigit()])[-10:]
                if len(cleaned_phone) >= 7:  # Need at least 7 digits for meaningful phone match
                    escaped_phone = self._escape_query_value(cleaned_phone[-7:])
                    query = f"SELECT * FROM Customer WHERE PrimaryPhone LIKE '%{escaped_phone}%'"  # nosec B608
                    encoded_query = quote(query)

                    response = self._make_qbo_request("GET", f"query?query={encoded_query}")
                    if response.get("QueryResponse", {}).get("Customer"):
                        customer = response["QueryResponse"]["Customer"][0]
                        return self._cache_and_return_customer(
                            customer, f"Strategy 6 - Phone (ending '{cleaned_phone[-7:]}')"
                        )

            # No match found after all strategies
            logger.info(f"No matching customer found for: '{customer_lookup}' after trying all strategies")
            return None

        except Exception as e:
            logger.error(f"Exception in find_customer: {str(e)}")
            return None

    def _cache_and_return_customer(self, customer: Dict[str, Any], strategy: str) -> Dict[str, Any]:
        """Cache a found customer and return it.

        Args:
            customer: Customer data to cache
            strategy: Strategy name for logging

        Returns:
            The customer data
        """
        logger.info(f"{strategy} match found: {customer.get('DisplayName')}")
        self._update_customer_cache([customer])
        return customer

    def get_customer_cache_stats(self) -> Dict[str, Any]:
        """Get statistics about the customer cache.

        Returns:
            Dictionary with cache statistics
        """
        with self._cache_lock:
            cache_size = len([k for k in self._customer_cache.keys() if not k.startswith("id_")])
            cache_age_seconds = 0
            if self._cache_timestamp:
                cache_age_seconds = int(datetime.now().timestamp() - self._cache_timestamp)

            return {
                "cache_size": cache_size,
                "cache_age_seconds": cache_age_seconds,
                "cache_valid": self._is_cache_valid(),
                "cache_ttl": self._cache_ttl,
            }

    def create_customer(self, customer_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new customer in QBO.

        Args:
            customer_data: Customer data dictionary

        Returns:
            Created customer data if successful, None otherwise
        """
        if not self.auth_service.is_token_valid():
            logger.warning("Not authenticated with QBO")
            return None

        try:
            response = self._make_qbo_request("POST", "customer", data=customer_data)
            return response.get("Customer")

        except Exception as e:
            logger.error(f"Exception in create_customer: {str(e)}")
            return None

    def update_customer(self, customer_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update an existing customer in QBO.

        Args:
            customer_data: Customer data dictionary with Id and SyncToken

        Returns:
            Updated customer data if successful, None otherwise
        """
        if not self.auth_service.is_token_valid():
            logger.warning("Not authenticated with QBO")
            return None

        try:
            response = self._make_qbo_request("POST", "customer", data=customer_data)
            return response.get("Customer")

        except Exception as e:
            logger.error(f"Exception in update_customer: {str(e)}")
            return None

    def _is_cache_valid(self) -> bool:
        """Check if the customer cache is still valid.

        Returns:
            True if cache is valid, False otherwise
        """
        if not self._cache_timestamp:
            return False

        cache_age = datetime.now().timestamp() - self._cache_timestamp
        return cache_age < self._cache_ttl

    def _update_customer_cache(self, customers: List[Dict[str, Any]]) -> None:
        """Update the customer cache with a list of customers.

        Args:
            customers: List of customer dictionaries
        """
        with self._cache_lock:
            self._customer_cache.clear()
            for customer in customers:
                # Cache by various lookup keys
                display_name = customer.get("DisplayName", "").lower()
                if display_name:
                    self._customer_cache[display_name] = customer

                # Also cache by ID
                customer_id = customer.get("Id")
                if customer_id:
                    self._customer_cache[f"id_{customer_id}"] = customer

            self._cache_timestamp = datetime.now().timestamp()
            logger.info(f"Updated customer cache with {len(customers)} customers")

    def get_cached_customer(self, lookup_value: str) -> Optional[Dict[str, Any]]:
        """Get a customer from the cache.

        Args:
            lookup_value: Customer name or ID to look up

        Returns:
            Customer data if found in cache, None otherwise
        """
        with self._cache_lock:
            if not self._is_cache_valid():
                return None

            # Try direct lookup
            customer = self._customer_cache.get(lookup_value.lower())
            if customer:
                return customer

            # Try ID lookup
            customer = self._customer_cache.get(f"id_{lookup_value}")
            if customer:
                return customer

            return None

    def clear_customer_cache(self) -> None:
        """Clear the customer cache."""
        with self._cache_lock:
            self._customer_cache.clear()
            self._cache_timestamp = None
            logger.info("Cleared customer cache")

    def get_all_customers(self, use_cache: bool = True) -> List[Dict[str, Any]]:
        """Get all customers from QBO with pagination support.

        Args:
            use_cache: Whether to use cached data if available

        Returns:
            List of all customers
        """
        # Check cache first
        if use_cache and self._is_cache_valid():
            with self._cache_lock:
                # Extract non-ID entries from cache
                customers = [v for k, v in self._customer_cache.items() if not k.startswith("id_")]
                if customers:
                    logger.info(f"Returning {len(customers)} customers from cache")
                    return customers

        if not self.auth_service.is_token_valid():
            logger.warning("Not authenticated with QBO")
            return []

        try:
            all_customers = []
            start_position = 1
            max_results = 1000  # QBO max per request

            while True:
                query = f"SELECT * FROM Customer ORDERBY DisplayName STARTPOSITION {start_position} MAXRESULTS {max_results}"  # nosec B608
                encoded_query = quote(query)

                response = self._make_qbo_request("GET", f"query?query={encoded_query}")

                customers = response.get("QueryResponse", {}).get("Customer", [])
                if not customers:
                    break

                all_customers.extend(customers)
                logger.info(f"Retrieved {len(customers)} customers (total: {len(all_customers)})")

                # Check if there are more results
                if len(customers) < max_results:
                    break

                start_position += max_results

            # Update cache with fresh data
            self._update_customer_cache(all_customers)

            return all_customers

        except Exception as e:
            logger.error(f"Error getting all customers: {str(e)}")
            return []

"""Routes for QuickBooks Online integration and customer management."""

import logging
from datetime import datetime

from flask import Blueprint, current_app, jsonify, request, session

from services.validation import log_audit_event, sanitize_for_logging

logger = logging.getLogger(__name__)

qbo_bp = Blueprint("qbo", __name__, url_prefix="/qbo")


def get_qbo_service():
    """Get QBO service instance from app context."""
    return current_app.qbo_service


@qbo_bp.route("/customer/<donation_id>", methods=["GET"])
def search_qbo_customer(donation_id):
    """Search for a QuickBooks customer based on donation information."""
    try:
        # Get donation from session
        donations = session.get("donations", [])
        donation = next((d for d in donations if d.get("internalId") == donation_id), None)

        if not donation:
            return jsonify({"error": "Donation not found"}), 404

        # Check QBO authentication
        if not session.get("qbo_authenticated"):
            return jsonify({"error": "QuickBooks not authenticated"}), 401

        qbo_service = get_qbo_service()

        # Search for customer
        donor_name = donation.get("Donor Name", "")
        if not donor_name:
            return jsonify({"error": "No donor name available"}), 400

        logger.info(f"Searching QBO for customer: {donor_name}")

        # Use the service's find_customer method which includes fuzzy matching
        customer = qbo_service.find_customer(donor_name)

        if customer:
            # Update donation with customer info
            donation["qboCustomerId"] = customer.get("Id")
            donation["qbCustomerStatus"] = "Found"
            donation["matchMethod"] = "Search"
            donation["matchConfidence"] = "High"

            # Extract customer details
            customer_data = {
                "id": customer.get("Id"),
                "displayName": customer.get("DisplayName"),
                "givenName": customer.get("GivenName"),
                "familyName": customer.get("FamilyName"),
                "companyName": customer.get("CompanyName"),
                "email": customer.get("PrimaryEmailAddr", {}).get("Address"),
                "phone": customer.get("PrimaryPhone", {}).get("FreeFormNumber"),
                "billingAddress": customer.get("BillAddr"),
                "syncToken": customer.get("SyncToken"),
            }

            # Update session
            session["donations"] = donations
            session.modified = True

            return jsonify(
                {
                    "success": True,
                    "found": True,
                    "customer": customer_data,
                    "matchConfidence": "High",
                }
            )
        else:
            # No match found
            donation["qbCustomerStatus"] = "Not Found"
            donation.pop("qboCustomerId", None)

            session["donations"] = donations
            session.modified = True

            return jsonify(
                {
                    "success": True,
                    "found": False,
                    "message": f'No customer found for "{donor_name}"',
                }
            )

    except Exception as e:
        logger.error(f"Error searching QBO customer: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@qbo_bp.route("/customers/all", methods=["GET"])
def get_all_qbo_customers():
    """Get all QuickBooks customers for manual matching."""
    try:
        # Check QBO authentication
        if not session.get("qbo_authenticated"):
            return jsonify({"error": "QuickBooks not authenticated"}), 401

        qbo_service = get_qbo_service()

        # Get all customers (with caching)
        customers = qbo_service.get_all_customers()

        # Transform to simpler format for frontend
        customer_list = []
        for customer in customers:
            customer_list.append(
                {
                    "id": customer.get("Id"),
                    "displayName": customer.get("DisplayName"),
                    "givenName": customer.get("GivenName"),
                    "familyName": customer.get("FamilyName"),
                    "companyName": customer.get("CompanyName"),
                    "email": customer.get("PrimaryEmailAddr", {}).get("Address"),
                    "active": customer.get("Active", True),
                }
            )

        # Sort by display name
        customer_list.sort(key=lambda x: x.get("displayName", "").lower())

        return jsonify({"success": True, "customers": customer_list, "count": len(customer_list)})

    except Exception as e:
        logger.error(f"Error getting QBO customers: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@qbo_bp.route("/customer/manual-match/<donation_id>", methods=["POST"])
def manual_match_customer(donation_id):
    """Manually match a donation to a QuickBooks customer."""
    try:
        # Get request data
        data = request.json
        customer_id = data.get("customerId")

        if not customer_id:
            return jsonify({"error": "Customer ID required"}), 400

        # Get donation from session
        donations = session.get("donations", [])
        donation = next((d for d in donations if d.get("internalId") == donation_id), None)

        if not donation:
            return jsonify({"error": "Donation not found"}), 404

        # Check QBO authentication
        if not session.get("qbo_authenticated"):
            return jsonify({"error": "QuickBooks not authenticated"}), 401

        qbo_service = get_qbo_service()

        # Get customer details from QBO
        customer = qbo_service.get_customer_by_id(customer_id)

        if not customer:
            return jsonify({"error": "Customer not found in QuickBooks"}), 404

        # Update donation with manual match
        donation["qboCustomerId"] = customer.get("Id")
        donation["qbCustomerStatus"] = "Matched"
        donation["matchMethod"] = "Manual"
        donation["matchConfidence"] = "Manual"
        donation["customerLookup"] = {
            "displayName": customer.get("DisplayName"),
            "email": customer.get("PrimaryEmailAddr", {}).get("Address"),
        }

        # Update session
        session["donations"] = donations
        session.modified = True

        # Log the manual match
        log_audit_event(
            "qbo_manual_customer_match",
            user_id=session.get("session_id"),
            details={
                "donation_id": donation_id,
                "customer_id": customer_id,
                "donor_name": donation.get("Donor Name"),
            },
            request_ip=request.remote_addr,
        )

        return jsonify(
            {
                "success": True,
                "message": "Customer matched successfully",
                "customer": {"id": customer.get("Id"), "displayName": customer.get("DisplayName")},
            }
        )

    except Exception as e:
        logger.error(f"Error in manual customer match: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@qbo_bp.route("/customer/create/<donation_id>", methods=["POST"])
def create_qbo_customer(donation_id):
    """Create a new QuickBooks customer from donation data."""
    try:
        # Get donation from session
        donations = session.get("donations", [])
        donation = next((d for d in donations if d.get("internalId") == donation_id), None)

        if not donation:
            return jsonify({"error": "Donation not found"}), 404

        # Check QBO authentication
        if not session.get("qbo_authenticated"):
            return jsonify({"error": "QuickBooks not authenticated"}), 401

        qbo_service = get_qbo_service()

        # Get customer data from request (if provided) or use donation data
        customer_data = request.json if request.json else {}

        # Prepare customer object
        if not customer_data:
            # Use donation data to create customer
            customer_data = {
                "DisplayName": donation.get("Donor Name", ""),
                "GivenName": donation.get("First Name", ""),
                "FamilyName": donation.get("Last Name", ""),
                "CompanyName": donation.get("Organization Name", ""),
            }

            # Add email if available
            if donation.get("Email"):
                customer_data["PrimaryEmailAddr"] = {"Address": donation.get("Email")}

            # Add phone if available
            if donation.get("Phone"):
                customer_data["PrimaryPhone"] = {"FreeFormNumber": donation.get("Phone")}

            # Add address if available
            if donation.get("Address - Line 1"):
                customer_data["BillAddr"] = {
                    "Line1": donation.get("Address - Line 1", ""),
                    "City": donation.get("City", ""),
                    "CountrySubDivisionCode": donation.get("State", ""),
                    "PostalCode": donation.get("ZIP", ""),
                }

        # Create customer in QuickBooks
        new_customer = qbo_service.create_customer(customer_data)

        if new_customer:
            # Update donation with new customer info
            donation["qboCustomerId"] = new_customer.get("Id")
            donation["qbCustomerStatus"] = "Created"
            donation["matchMethod"] = "Created"
            donation["matchConfidence"] = "New"

            # Update session
            session["donations"] = donations
            session.modified = True

            # Log the customer creation
            log_audit_event(
                "qbo_customer_created",
                user_id=session.get("session_id"),
                details={
                    "donation_id": donation_id,
                    "customer_id": new_customer.get("Id"),
                    "customer_name": new_customer.get("DisplayName"),
                },
                request_ip=request.remote_addr,
            )

            return jsonify(
                {
                    "success": True,
                    "message": "Customer created successfully",
                    "customer": {
                        "id": new_customer.get("Id"),
                        "displayName": new_customer.get("DisplayName"),
                        "syncToken": new_customer.get("SyncToken"),
                    },
                }
            )
        else:
            return jsonify({"error": "Failed to create customer"}), 500

    except Exception as e:
        logger.error(f"Error creating QBO customer: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@qbo_bp.route("/customer/update/<donation_id>", methods=["POST"])
def update_qbo_customer(donation_id):
    """Update an existing QuickBooks customer with donation data."""
    try:
        # Get request data
        data = request.json

        # Get donation from session
        donations = session.get("donations", [])
        donation = next((d for d in donations if d.get("internalId") == donation_id), None)

        if not donation:
            return jsonify({"error": "Donation not found"}), 404

        # Check if donation has a matched customer
        customer_id = donation.get("qboCustomerId")
        if not customer_id:
            return jsonify({"error": "No customer matched to this donation"}), 400

        # Check QBO authentication
        if not session.get("qbo_authenticated"):
            return jsonify({"error": "QuickBooks not authenticated"}), 401

        qbo_service = get_qbo_service()

        # Update customer in QuickBooks
        updated_customer = qbo_service.update_customer(customer_id, data)

        if updated_customer:
            # Update donation status
            donation["qbCustomerStatus"] = "Updated"
            donation["lastUpdated"] = datetime.utcnow().isoformat()

            # Update session
            session["donations"] = donations
            session.modified = True

            # Log the update
            log_audit_event(
                "qbo_customer_updated",
                user_id=session.get("session_id"),
                details={
                    "donation_id": donation_id,
                    "customer_id": customer_id,
                    "updated_fields": list(data.keys()),
                },
                request_ip=request.remote_addr,
            )

            return jsonify(
                {
                    "success": True,
                    "message": "Customer updated successfully",
                    "customer": {
                        "id": updated_customer.get("Id"),
                        "displayName": updated_customer.get("DisplayName"),
                        "syncToken": updated_customer.get("SyncToken"),
                    },
                }
            )
        else:
            return jsonify({"error": "Failed to update customer"}), 500

    except Exception as e:
        logger.error(f"Error updating QBO customer: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@qbo_bp.route("/sales-receipt/<donation_id>", methods=["POST"])
def create_sales_receipt(donation_id):
    """Create a sales receipt in QuickBooks for a donation."""
    try:
        # Get donation from session
        donations = session.get("donations", [])
        donation = next((d for d in donations if d.get("internalId") == donation_id), None)

        if not donation:
            return jsonify({"error": "Donation not found"}), 404

        # Check if donation has a matched customer
        if not donation.get("qboCustomerId"):
            return jsonify({"error": "Customer must be matched before creating sales receipt"}), 400

        # Check QBO authentication
        if not session.get("qbo_authenticated"):
            return jsonify({"error": "QuickBooks not authenticated"}), 401

        qbo_service = get_qbo_service()

        # Create sales receipt
        receipt = qbo_service.create_sales_receipt(donation)

        if receipt:
            # Update donation with receipt info
            donation["qboSalesReceiptId"] = receipt.get("Id")
            donation["qboSalesReceiptNumber"] = receipt.get("DocNumber")
            donation["qboSyncStatus"] = "Synced"
            donation["qboSyncDate"] = datetime.utcnow().isoformat()

            # Update session
            session["donations"] = donations
            session.modified = True

            # Log the sales receipt creation
            log_audit_event(
                "qbo_sales_receipt_created",
                user_id=session.get("session_id"),
                details={
                    "donation_id": donation_id,
                    "receipt_id": receipt.get("Id"),
                    "receipt_number": receipt.get("DocNumber"),
                    "amount": donation.get("Gift Amount"),
                },
                request_ip=request.remote_addr,
            )

            return jsonify(
                {
                    "success": True,
                    "message": "Sales receipt created successfully",
                    "receipt": {
                        "id": receipt.get("Id"),
                        "docNumber": receipt.get("DocNumber"),
                        "totalAmount": receipt.get("TotalAmt"),
                    },
                }
            )
        else:
            return jsonify({"error": "Failed to create sales receipt"}), 500

    except Exception as e:
        logger.error(f"Error creating sales receipt: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@qbo_bp.route("/environment", methods=["GET"])
def get_environment():
    """Get the current QBO environment."""
    try:
        qbo_service = current_app.qbo_service
        return jsonify({"environment": qbo_service.environment})
    except Exception as e:
        logger.error(f"Error getting QBO environment: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@qbo_bp.route("/items/all", methods=["GET"])
def get_all_items():
    """Get all items from QuickBooks."""
    try:
        # Check QBO authentication
        if not session.get("qbo_authenticated"):
            return jsonify({"error": "QuickBooks not authenticated"}), 401

        qbo_service = current_app.qbo_service

        items = qbo_service.get_all_items()
        return jsonify(items)

    except Exception as e:
        logger.error(f"Error fetching items: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@qbo_bp.route("/accounts/all", methods=["GET"])
def get_all_accounts():
    """Get all accounts from QuickBooks."""
    try:
        # Check QBO authentication
        if not session.get("qbo_authenticated"):
            return jsonify({"error": "QuickBooks not authenticated"}), 401

        qbo_service = current_app.qbo_service

        accounts = qbo_service.get_all_accounts()

        # Find Undeposited Funds account
        undeposited_funds = None
        for account in accounts:
            if account.get("AccountSubType") == "UndepositedFunds":
                undeposited_funds = {
                    "id": account.get("Id"),
                    "name": account.get("Name"),
                    "type": account.get("AccountType"),
                    "subType": account.get("AccountSubType"),
                }
                break

        return jsonify({"accounts": accounts, "undepositedFunds": undeposited_funds})

    except Exception as e:
        logger.error(f"Error fetching accounts: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@qbo_bp.route("/payment-methods/all", methods=["GET"])
def get_all_payment_methods():
    """Get all payment methods from QuickBooks."""
    try:
        # Check QBO authentication
        if not session.get("qbo_authenticated"):
            return jsonify({"error": "QuickBooks not authenticated"}), 401

        qbo_service = current_app.qbo_service

        payment_methods = qbo_service.get_all_payment_methods()
        return jsonify(payment_methods)

    except Exception as e:
        logger.error(f"Error fetching payment methods: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

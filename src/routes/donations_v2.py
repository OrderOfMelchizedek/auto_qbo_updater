"""Routes for managing donation data in the new enriched format."""

import logging

from flask import Blueprint, jsonify, request, session

logger = logging.getLogger(__name__)

donations_v2_bp = Blueprint("donations_v2", __name__)


@donations_v2_bp.route("/v2/donations", methods=["GET"])
def get_donations_enriched():
    """Get all donations from the current session in enriched format.

    This endpoint returns the new combined format with full QBO data enrichment.
    """
    try:
        donations = session.get("donations", [])
        session_id = session.get("session_id", "No session")

        # Check if we have enriched format data
        enriched_donations = session.get("enriched_donations")

        if enriched_donations:
            # Return enriched format
            total_amount = sum(p.get("payment_info", {}).get("amount", 0) for p in enriched_donations)

            matched_count = sum(1 for p in enriched_donations if p.get("match_status") != "New")

            update_count = sum(
                1 for p in enriched_donations if p.get("payer_info", {}).get("address_needs_update", False)
            )

            return jsonify(
                {
                    "success": True,
                    "format": "enriched",
                    "payments": enriched_donations,
                    "count": len(enriched_donations),
                    "total_amount": f"{total_amount:.2f}",
                    "matched_customers": matched_count,
                    "addresses_need_update": update_count,
                    "session_id": session_id,
                }
            )
        else:
            # Convert legacy format to enriched on the fly
            from src.utils.payment_combiner import PaymentCombiner

            combiner = PaymentCombiner()

            enriched = []
            for donation in donations:
                # Basic conversion - would be better with full QBO data
                payment = {
                    "payer_info": {
                        "customer_lookup": donation.get("Donor Name", ""),
                        "salutation": donation.get("Salutation", ""),
                        "first_name": donation.get("First Name", ""),
                        "last_name": donation.get("Last Name", ""),
                        "full_name": donation.get("Donor Name", ""),
                        "qb_organization_name": donation.get("Organization Name", ""),
                        "qb_address_line_1": donation.get("Address - Line 1", ""),
                        "qb_city": donation.get("City", ""),
                        "qb_state": donation.get("State", ""),
                        "qb_zip": donation.get("ZIP", ""),
                        "qb_email": [donation.get("Email")] if donation.get("Email") else [],
                        "qb_phone": [donation.get("Phone")] if donation.get("Phone") else [],
                        "address_needs_update": donation.get("addressNeedsUpdate", False),
                        "extracted_address": {
                            "line_1": donation.get("Address - Line 1", ""),
                            "city": donation.get("City", ""),
                            "state": donation.get("State", ""),
                            "zip": donation.get("ZIP", ""),
                        },
                    },
                    "payment_info": {
                        "check_no_or_payment_ref": donation.get("Check No.", ""),
                        "amount": float(donation.get("Gift Amount", 0) or 0),
                        "payment_date": donation.get("Check Date", ""),
                        "deposit_date": donation.get("Deposit Date", ""),
                        "deposit_method": donation.get("Deposit Method", ""),
                        "memo": donation.get("Memo", ""),
                    },
                    "match_status": donation.get("qbCustomerStatus", "New"),
                    "qbo_customer_id": donation.get("qboCustomerId"),
                    "match_method": donation.get("matchMethod"),
                    "match_confidence": donation.get("matchConfidence"),
                }
                enriched.append(payment)

            # Calculate stats
            total_amount = sum(p.get("payment_info", {}).get("amount", 0) for p in enriched)

            matched_count = sum(1 for p in enriched if p.get("match_status") != "New")

            return jsonify(
                {
                    "success": True,
                    "format": "converted",
                    "payments": enriched,
                    "count": len(enriched),
                    "total_amount": f"{total_amount:.2f}",
                    "matched_customers": matched_count,
                    "addresses_need_update": 0,  # Not available in legacy
                    "session_id": session_id,
                }
            )

    except Exception as e:
        logger.error(f"Error getting enriched donations: {str(e)}")
        return jsonify({"error": str(e)}), 500


@donations_v2_bp.route("/v2/donations/<payment_id>", methods=["PUT"])
def update_donation_enriched(payment_id):
    """Update a specific payment in enriched format."""
    try:
        enriched_donations = session.get("enriched_donations", [])
        payment_data = request.json

        # Find the payment to update
        payment_index = None
        for i, payment in enumerate(enriched_donations):
            # Check both possible ID fields
            if payment.get("id") == payment_id or payment.get("payment_info", {}).get("id") == payment_id:
                payment_index = i
                break

        if payment_index is None:
            return jsonify({"error": "Payment not found"}), 404

        # Deep update the payment
        if "payer_info" in payment_data:
            enriched_donations[payment_index]["payer_info"].update(payment_data["payer_info"])

        if "payment_info" in payment_data:
            enriched_donations[payment_index]["payment_info"].update(payment_data["payment_info"])

        # Update other top-level fields
        for key in ["match_status", "qbo_customer_id", "match_method", "match_confidence"]:
            if key in payment_data:
                enriched_donations[payment_index][key] = payment_data[key]

        session["enriched_donations"] = enriched_donations
        session.modified = True

        # Also update legacy format for backward compatibility
        donations = session.get("donations", [])
        if payment_index < len(donations):
            # Convert back to legacy
            from src.utils.payment_combiner import PaymentCombiner

            combiner = PaymentCombiner()
            legacy = combiner.convert_to_legacy_format(enriched_donations[payment_index])
            donations[payment_index] = legacy
            session["donations"] = donations

        return jsonify(
            {
                "success": True,
                "message": "Payment updated successfully",
                "payment": enriched_donations[payment_index],
            }
        )

    except Exception as e:
        logger.error(f"Error updating payment: {str(e)}")
        return jsonify({"error": str(e)}), 500


@donations_v2_bp.route("/v2/donations/export", methods=["GET"])
def export_donations_enriched():
    """Export donations in enriched format for processing."""
    try:
        enriched_donations = session.get("enriched_donations", [])

        if not enriched_donations:
            # Try to get from legacy format
            donations = session.get("donations", [])
            if not donations:
                return jsonify({"success": True, "payments": [], "message": "No payments to export"})

            # Convert legacy to enriched for export
            from src.utils.payment_combiner import PaymentCombiner

            combiner = PaymentCombiner()
            enriched_donations = []

            for donation in donations:
                # Create a minimal enriched format
                payment = combiner.combine_payment_data(donation, None, donation.get("qbCustomerStatus", "New"))
                enriched_donations.append(payment)

        # Filter only matched payments if requested
        filter_matched = request.args.get("matched_only", "false").lower() == "true"

        if filter_matched:
            export_payments = [p for p in enriched_donations if p.get("match_status") != "New"]
        else:
            export_payments = enriched_donations

        return jsonify(
            {"success": True, "payments": export_payments, "count": len(export_payments), "format": "enriched"}
        )

    except Exception as e:
        logger.error(f"Error exporting payments: {str(e)}")
        return jsonify({"error": str(e)}), 500

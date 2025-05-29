"""Routes for managing donation data in the session."""

import json
import logging
from datetime import datetime

from flask import Blueprint, Response, current_app, jsonify, request, session

from services.deduplication import DeduplicationService
from services.validation import log_audit_event, sanitize_for_logging

logger = logging.getLogger(__name__)

donations_bp = Blueprint("donations", __name__)


@donations_bp.route("/donations", methods=["GET"])
def get_donations():
    """Get all donations from the current session."""
    try:
        donations = session.get("donations", [])
        session_id = session.get("session_id", "No session")

        # Add statistics
        total_amount = sum(float(d.get("Gift Amount", 0) or 0) for d in donations)

        # Count matched customers
        matched_count = sum(
            1
            for d in donations
            if d.get("qbCustomerStatus")
            in ["Matched", "Matched-AddressMismatch", "Matched-AddressNeedsReview"]
        )

        return jsonify(
            {
                "success": True,
                "donations": donations,
                "count": len(donations),
                "total_amount": f"{total_amount:.2f}",
                "matched_customers": matched_count,
                "session_id": session_id,
            }
        )
    except Exception as e:
        logger.error(f"Error getting donations: {str(e)}")
        return jsonify({"error": str(e)}), 500


@donations_bp.route("/donations/<donation_id>", methods=["PUT"])
def update_donation(donation_id):
    """Update a specific donation."""
    try:
        donations = session.get("donations", [])
        donation_data = request.json

        # Find the donation to update
        donation_index = None
        for i, donation in enumerate(donations):
            if donation.get("internalId") == donation_id:
                donation_index = i
                break

        if donation_index is None:
            return jsonify({"error": "Donation not found"}), 404

        # Update the donation
        donations[donation_index].update(donation_data)
        session["donations"] = donations
        session.modified = True

        # Log the update
        log_audit_event(
            "donation_updated",
            user_id=session.get("session_id"),
            details={"donation_id": donation_id, "updated_fields": list(donation_data.keys())},
            request_ip=request.remote_addr,
        )

        return jsonify(
            {
                "success": True,
                "message": "Donation updated successfully",
                "donation": donations[donation_index],
            }
        )

    except Exception as e:
        logger.error(f"Error updating donation: {str(e)}")
        return jsonify({"error": str(e)}), 500


@donations_bp.route("/donations/remove-invalid", methods=["POST"])
def remove_invalid_donations():
    """Remove donations marked as invalid from the session."""
    try:
        donations = session.get("donations", [])
        initial_count = len(donations)

        # Filter out invalid donations
        valid_donations = [d for d in donations if not d.get("isInvalid", False)]
        removed_count = initial_count - len(valid_donations)

        # Update session
        session["donations"] = valid_donations
        session.modified = True

        # Log the removal
        log_audit_event(
            "invalid_donations_removed",
            user_id=session.get("session_id"),
            details={"removed_count": removed_count, "remaining_count": len(valid_donations)},
            request_ip=request.remote_addr,
        )

        return jsonify(
            {
                "success": True,
                "removed_count": removed_count,
                "remaining_count": len(valid_donations),
            }
        )

    except Exception as e:
        logger.error(f"Error removing invalid donations: {str(e)}")
        return jsonify({"error": str(e)}), 500


@donations_bp.route("/donations/update-session", methods=["POST"])
def update_session_donations():
    """Update all donations in the session."""
    try:
        data = request.json
        new_donations = data.get("donations", [])

        # Validate donation data
        if not isinstance(new_donations, list):
            return jsonify({"error": "Invalid donation data format"}), 400

        # Store in session
        session["donations"] = new_donations
        session.modified = True

        # Log the update
        log_audit_event(
            "session_donations_updated",
            user_id=session.get("session_id"),
            details={"donation_count": len(new_donations), "action": "bulk_update"},
            request_ip=request.remote_addr,
        )

        return jsonify(
            {"success": True, "message": "Session donations updated", "count": len(new_donations)}
        )

    except Exception as e:
        logger.error(f"Error updating session donations: {str(e)}")
        return jsonify({"error": str(e)}), 500


@donations_bp.route("/progress-stream/<session_id>")
def progress_stream(session_id):
    """SSE endpoint for real-time progress updates."""

    def generate():
        import time

        from utils.progress_logger import get_progress_messages

        # Send initial connection message
        yield f"data: {json.dumps({'message': 'Connected to progress stream', 'progress': 0})}\n\n"

        last_index = 0
        complete = False

        while not complete:
            # Get new messages since last index
            messages = get_progress_messages(session_id, last_index)

            for msg in messages:
                yield f"data: {json.dumps(msg)}\n\n"
                if msg.get("complete", False):
                    complete = True
                last_index = msg.get("index", last_index) + 1

            if not complete:
                time.sleep(0.5)  # Poll every 500ms

        # Send final message
        yield f"data: {json.dumps({'message': 'Stream complete', 'progress': 100, 'complete': True})}\n\n"

    return Response(generate(), mimetype="text/event-stream")

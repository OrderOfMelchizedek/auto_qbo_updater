import logging
from datetime import datetime

from flask import Blueprint, current_app, jsonify, redirect, request, session

logger = logging.getLogger(__name__)

auth_bp = Blueprint("auth", __name__, url_prefix="/qbo")


def get_qbo_service():
    """Get QBO service instance from app context."""
    return current_app.qbo_service


@auth_bp.route("/auth-status", methods=["GET"])
def auth_status():
    """Check QBO authentication status."""
    try:
        qbo_service = get_qbo_service()
        is_authenticated = session.get("qbo_authenticated", False)

        # Additional validation - check if we actually have valid tokens
        if is_authenticated and not qbo_service.get_access_token():
            # Session says authenticated but no valid token
            session["qbo_authenticated"] = False
            is_authenticated = False
            logger.warning("Session marked as authenticated but no valid token found")

        status_data = {
            "authenticated": is_authenticated,
            "company_id": session.get("qbo_company_id"),
            "token_expires_at": session.get("qbo_token_expires_at"),
            "environment": qbo_service.environment,
        }

        # Add token validity info if authenticated
        if is_authenticated:
            try:
                token_info = qbo_service.get_token_info()
                status_data.update(
                    {
                        "token_valid": token_info.get("is_valid", False),
                        "token_expires_in": token_info.get("expires_in_seconds", 0),
                    }
                )
            except Exception as e:
                logger.error(f"Error getting token info: {e}")
                status_data["token_error"] = str(e)

        return jsonify(status_data)

    except Exception as e:
        logger.error(f"Error checking auth status: {str(e)}", exc_info=True)
        return jsonify({"error": str(e), "authenticated": False}), 500


@auth_bp.route("/disconnect", methods=["POST"])
def disconnect():
    """Disconnect from QuickBooks (clear local session only)."""
    try:
        # Clear QBO-related session data
        qbo_keys = [
            "qbo_authenticated",
            "qbo_company_id",
            "qbo_access_token",
            "qbo_refresh_token",
            "qbo_token_expires_at",
        ]
        for key in qbo_keys:
            session.pop(key, None)

        # Clear Redis tokens if configured
        qbo_service = get_qbo_service()
        if qbo_service.redis_client:
            try:
                qbo_service.clear_tokens()
                logger.info("Cleared QBO tokens from Redis")
            except Exception as e:
                logger.error(f"Error clearing Redis tokens: {e}")

        logger.info("QBO disconnected successfully")
        return jsonify({"success": True, "message": "Disconnected from QuickBooks"})

    except Exception as e:
        logger.error(f"Error disconnecting from QBO: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@auth_bp.route("/status")
def qbo_status():
    """Get QuickBooks connection status."""
    try:
        qbo_service = get_qbo_service()
        is_authenticated = qbo_service.is_authenticated()

        status = {"authenticated": is_authenticated, "environment": qbo_service.environment}

        if is_authenticated:
            # Get company info if authenticated
            try:
                company_info = qbo_service.get_company_info()
                if company_info:
                    status["company"] = {"name": company_info.get("CompanyName"), "id": company_info.get("Id")}
            except Exception as e:
                logger.error(f"Error fetching company info: {e}")
                status["company_error"] = str(e)

        return jsonify(status)
    except Exception as e:
        logger.error(f"Error getting QBO status: {e}")
        return jsonify({"error": str(e)}), 500


@auth_bp.route("/authorize")
def qbo_authorize():
    """Initiate QuickBooks OAuth flow."""
    auth_url = get_qbo_service().get_auth_url()
    return redirect(auth_url)


@auth_bp.route("/callback")
def qbo_callback():
    """Handle QuickBooks OAuth callback."""
    try:
        code = request.args.get("code")
        state = request.args.get("state")
        realm_id = request.args.get("realmId")  # QuickBooks company ID

        if not code:
            error = request.args.get("error", "Unknown error")
            error_description = request.args.get("error_description", "No description")
            logger.error(f"OAuth error: {error} - {error_description}")
            return redirect("/?qbo_error=" + error)

        # Exchange code for tokens
        qbo_service = get_qbo_service()
        token_response = qbo_service.exchange_code_for_tokens(code)

        if token_response:
            # Store in session
            session["qbo_authenticated"] = True
            session["qbo_company_id"] = realm_id
            session["qbo_access_token"] = token_response.get("access_token")
            session["qbo_refresh_token"] = token_response.get("refresh_token")
            session["qbo_token_expires_at"] = token_response.get("expires_at")

            # Log the authentication event
            from services.validation import log_audit_event

            log_audit_event(
                "qbo_auth_success",
                user_id=session.get("session_id"),
                details={"company_id": realm_id},
                request_ip=request.remote_addr,
            )

            logger.info(f"QBO authentication successful for company {realm_id}")

            # Redirect back to main page with success flag
            return redirect("/?qbo_connected=true")
        else:
            logger.error("Failed to exchange code for tokens")
            return redirect("/?qbo_error=token_exchange_failed")

    except Exception as e:
        logger.error(f"OAuth callback error: {str(e)}", exc_info=True)
        return redirect("/?qbo_error=" + str(e))

"""Routes for health checks and system monitoring."""

import json
import logging
import os
from datetime import datetime

import psutil
from flask import Blueprint, Response, jsonify, session

logger = logging.getLogger(__name__)

health_bp = Blueprint("health", __name__)


@health_bp.route("/health", methods=["GET"])
def health_check():
    """Enhanced health check endpoint with detailed system status.

    Returns:
        dict: System health status including memory usage, dependencies, and runtime info
    """
    try:
        # Get current process info
        process = psutil.Process()
        memory_info = process.memory_info()

        # Calculate memory usage
        memory_mb = memory_info.rss / 1024 / 1024
        memory_limit_mb = int(os.environ.get("MEMORY_LIMIT", "512"))
        memory_percent = (memory_mb / memory_limit_mb * 100) if memory_limit_mb > 0 else 0

        # Check if memory usage is concerning
        memory_status = "healthy"
        if memory_percent > 90:
            memory_status = "critical"
        elif memory_percent > 75:
            memory_status = "warning"

        # Check Redis connection
        redis_status = "unknown"
        redis_details = {}
        try:
            # Try to get Redis client from app context
            from flask import current_app

            redis_client = getattr(current_app, "redis_client", None)
            if redis_client:
                # Test Redis with ping
                redis_client.ping()
                redis_status = "connected"

                # Get Redis info
                info = redis_client.info()
                redis_details = {
                    "version": info.get("redis_version"),
                    "connected_clients": info.get("connected_clients"),
                    "used_memory_mb": round(info.get("used_memory", 0) / 1024 / 1024, 2),
                    "uptime_days": round(info.get("uptime_in_seconds", 0) / 86400, 2),
                }
            else:
                redis_status = "not_configured"
        except Exception as e:
            redis_status = "error"
            redis_details["error"] = str(e)

        # Check Celery status
        celery_status = "unknown"
        celery_details = {}
        try:
            from utils.celery_app import celery_app

            # Inspect active tasks
            inspect = celery_app.control.inspect()
            stats = inspect.stats()
            if stats:
                celery_status = "connected"
                # Count total workers
                celery_details["workers"] = len(stats)
                # Get active tasks count
                active = inspect.active()
                if active:
                    celery_details["active_tasks"] = sum(len(tasks) for tasks in active.values())
            else:
                celery_status = "no_workers"
        except Exception as e:
            celery_status = "error"
            celery_details["error"] = str(e)

        # Build health response
        health_data = {
            "status": "healthy" if memory_status == "healthy" else memory_status,
            "timestamp": datetime.utcnow().isoformat(),
            "version": os.environ.get("APP_VERSION", "unknown"),
            "environment": os.environ.get("FLASK_ENV", "development"),
            "memory": {
                "status": memory_status,
                "used_mb": round(memory_mb, 2),
                "limit_mb": memory_limit_mb,
                "percent": round(memory_percent, 2),
                "available_mb": round(psutil.virtual_memory().available / 1024 / 1024, 2),
            },
            "dependencies": {
                "redis": {"status": redis_status, **redis_details},
                "celery": {"status": celery_status, **celery_details},
            },
            "runtime": {
                "python_version": os.sys.version.split()[0],
                "process_uptime_seconds": int(process.create_time()),
                "cpu_percent": process.cpu_percent(interval=0.1),
            },
        }

        # Log health check if there are issues
        if memory_status != "healthy":
            logger.warning(f"Health check: memory {memory_status} - {memory_percent:.1f}% used")

        # Set appropriate HTTP status
        http_status = 200 if health_data["status"] == "healthy" else 503

        return jsonify(health_data), http_status

    except Exception as e:
        logger.error(f"Health check failed: {str(e)}", exc_info=True)
        return (
            jsonify({"status": "error", "error": str(e), "timestamp": datetime.utcnow().isoformat()}),
            503,
        )


@health_bp.route("/ready", methods=["GET"])
def readiness_check():
    """Kubernetes-style readiness probe.

    Checks if the application is ready to serve traffic.
    Different from health check - this verifies all required services are available.

    Returns:
        dict: Readiness status and component details
    """
    try:
        ready = True
        checks = {}

        # Check 1: Verify upload directory exists and is writable
        upload_check = {"status": "unknown"}
        try:
            upload_dir = os.environ.get("UPLOAD_FOLDER", "uploads")
            if os.path.exists(upload_dir):
                # Test write permissions
                test_file = os.path.join(upload_dir, ".write_test")
                try:
                    with open(test_file, "w") as f:
                        f.write("test")
                    os.remove(test_file)
                    upload_check["status"] = "ready"
                    upload_check["path"] = upload_dir
                except Exception as e:
                    upload_check["status"] = "not_writable"
                    upload_check["error"] = str(e)
                    ready = False
            else:
                upload_check["status"] = "not_found"
                ready = False
        except Exception as e:
            upload_check["status"] = "error"
            upload_check["error"] = str(e)
            ready = False
        checks["upload_directory"] = upload_check

        # Check 2: Verify Gemini API key is configured
        gemini_check = {"status": "unknown"}
        try:
            if os.environ.get("GEMINI_API_KEY"):
                gemini_check["status"] = "configured"
            else:
                gemini_check["status"] = "missing"
                ready = False
        except Exception as e:
            gemini_check["status"] = "error"
            gemini_check["error"] = str(e)
        checks["gemini_api"] = gemini_check

        # Check 3: Verify QBO credentials are configured
        qbo_check = {"status": "unknown"}
        try:
            required_vars = ["QBO_CLIENT_ID", "QBO_CLIENT_SECRET", "QBO_REDIRECT_URI"]
            missing_vars = [var for var in required_vars if not os.environ.get(var)]

            if not missing_vars:
                qbo_check["status"] = "configured"
                qbo_check["environment"] = os.environ.get("QBO_ENVIRONMENT", "sandbox")
            else:
                qbo_check["status"] = "missing_credentials"
                qbo_check["missing"] = missing_vars
                ready = False
        except Exception as e:
            qbo_check["status"] = "error"
            qbo_check["error"] = str(e)
        checks["quickbooks_oauth"] = qbo_check

        # Check 4: Verify session configuration
        session_check = {"status": "unknown"}
        try:
            if "SESSION_TYPE" in os.environ:
                session_check["status"] = "configured"
                session_check["type"] = os.environ.get("SESSION_TYPE")
            else:
                session_check["status"] = "using_default"
                session_check["type"] = "filesystem"
        except Exception as e:
            session_check["status"] = "error"
            session_check["error"] = str(e)
        checks["session"] = session_check

        # Build response
        response = {"ready": ready, "timestamp": datetime.utcnow().isoformat(), "checks": checks}

        # Set appropriate HTTP status
        http_status = 200 if ready else 503

        return jsonify(response), http_status

    except Exception as e:
        logger.error(f"Readiness check failed: {str(e)}", exc_info=True)
        return (
            jsonify({"ready": False, "error": str(e), "timestamp": datetime.utcnow().isoformat()}),
            503,
        )


@health_bp.route("/session-info", methods=["GET"])
def get_session_info():
    """Get current session information for debugging."""
    try:
        session_data = {
            "session_id": session.get("session_id", "No session"),
            "csrf_token": session.get("csrf_token", "No CSRF token"),
            "qbo_authenticated": session.get("qbo_authenticated", False),
            "total_donations": len(session.get("donations", [])),
            "session_keys": list(session.keys()) if session else [],
        }

        return jsonify(session_data)
    except Exception as e:
        logger.error(f"Error getting session info: {str(e)}")
        return jsonify({"error": str(e)}), 500


@health_bp.route("/test-progress", methods=["GET"])
def test_progress():
    """Test endpoint for progress streaming."""

    def generate():
        import time

        for i in range(10):
            time.sleep(1)
            yield f"data: {json.dumps({'progress': (i+1)*10, 'message': f'Test progress {i+1}/10'})}\n\n"
        yield f"data: {json.dumps({'progress': 100, 'message': 'Test complete', 'complete': True})}\n\n"

    return Response(generate(), mimetype="text/event-stream")

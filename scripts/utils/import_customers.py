#!/usr/bin/env python3
"""
Standalone app to import customers from CSV into QuickBooks Online Sandbox.
"""
import csv
import os
import sys
import threading
import time

from dotenv import load_dotenv
from flask import Flask, redirect, render_template_string, request, url_for
from tqdm import tqdm  # For progress bar

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from utils.qbo_service import QBOService

# Load environment variables
load_dotenv()

# Global variables
QBO_ENVIRONMENT = "sandbox"
qbo_service = None
import_status = {
    "total": 0,
    "imported": 0,
    "skipped": 0,
    "errors": 0,
    "logs": [],
    "is_running": False,
    "is_complete": False,
}

# Create Flask app
app = Flask(__name__)
app.secret_key = os.urandom(24)

# HTML template for the import status page
STATUS_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>QBO Customer Import</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
    <meta http-equiv="refresh" content="3" />
    <style>
        .container { max-width: 900px; margin-top: 30px; }
        .log-container { max-height: 400px; overflow-y: auto; margin-top: 20px; }
        .log-entry { font-family: monospace; margin-bottom: 2px; }
        .success { color: green; }
        .warning { color: orange; }
        .error { color: red; }
        .progress { height: 25px; margin-top: 20px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>QuickBooks Customer Import</h1>
        <div class="alert {% if is_authenticated %}alert-info{% else %}alert-warning{% endif %} mb-4">
            <p><strong>Environment:</strong> {{ environment }}</p>
            <p><strong>QuickBooks:</strong>
                {% if is_authenticated %}
                    <span class="badge bg-success">Connected</span>
                {% else %}
                    <span class="badge bg-warning">Not Connected</span>
                {% endif %}
            </p>
            <p><strong>Status:</strong>
                {% if is_complete %}
                    <span class="badge bg-success">Complete</span>
                {% elif is_running %}
                    <span class="badge bg-primary">Running</span>
                {% else %}
                    <span class="badge bg-secondary">Waiting</span>
                {% endif %}
            </p>
        </div>

        {% if total > 0 %}
        <div class="card mb-4">
            <div class="card-header">
                Progress
            </div>
            <div class="card-body">
                <div class="progress">
                    <div class="progress-bar" role="progressbar"
                         style="width: {{ (imported / total) * 100 }}%;"
                         aria-valuenow="{{ imported }}" aria-valuemin="0" aria-valuemax="{{ total }}">
                        {{ imported }} / {{ total }}
                    </div>
                </div>

                <div class="row mt-3">
                    <div class="col-md-4">
                        <div class="card text-white bg-success">
                            <div class="card-body text-center">
                                <h5 class="card-title">Imported</h5>
                                <p class="card-text">{{ imported }}</p>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="card text-white bg-warning">
                            <div class="card-body text-center">
                                <h5 class="card-title">Skipped</h5>
                                <p class="card-text">{{ skipped }}</p>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="card text-white bg-danger">
                            <div class="card-body text-center">
                                <h5 class="card-title">Errors</h5>
                                <p class="card-text">{{ errors }}</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        {% endif %}

        <div class="card">
            <div class="card-header">
                Log Messages
            </div>
            <div class="card-body">
                <div class="log-container">
                    {% for log in logs %}
                        <div class="log-entry {{ log.type }}">{{ log.message }}</div>
                    {% endfor %}
                </div>
            </div>
        </div>

        {% if not is_running and not is_complete %}
        <div class="mt-4">
            {% if is_authenticated %}
                <a href="/start-import" class="btn btn-primary">Start Import Process</a>
            {% else %}
                <a href="/qbo/authorize" class="btn btn-warning">Connect to QBO</a>
                <p class="mt-2 text-muted">You must connect to QuickBooks Online before importing.</p>
            {% endif %}
        </div>
        {% endif %}

        {% if is_complete %}
        <div class="alert alert-success mt-4">
            <p>Import process complete!</p>
            <p>You can now close this browser window and use the main application to test with your imported customers.</p>
        </div>
        {% endif %}
    </div>
</body>
</html>
"""


def add_log(message, log_type="info"):
    """Add a log message to the status"""
    import_status["logs"].append({"message": message, "type": log_type})
    print(message)


def create_customer_from_csv_row(row):
    """Create a QBO customer object from a CSV row."""
    # Extract the necessary fields from the CSV row
    customer_data = {
        "DisplayName": row.get("Customer", ""),
        "FullyQualifiedName": row.get("Customer full name", ""),
        "GivenName": row.get("First name", ""),
        "FamilyName": row.get("Last name", ""),
        "CompanyName": row.get("Company", ""),
        "PrimaryPhone": {"FreeFormNumber": row.get("Phone", "")},
        "PrimaryEmailAddr": {"Address": row.get("Email", "")},
        "BillAddr": {
            "Line1": row.get("Bill street", ""),
            "City": row.get("Bill city", ""),
            "CountrySubDivisionCode": row.get("Bill state", ""),
            "PostalCode": row.get("Bill zip", ""),
        },
        "Notes": row.get("Note", ""),
    }

    # Remove empty fields to avoid QBO validation errors
    if not customer_data["PrimaryPhone"]["FreeFormNumber"]:
        customer_data.pop("PrimaryPhone")

    if not customer_data["PrimaryEmailAddr"]["Address"]:
        customer_data.pop("PrimaryEmailAddr")

    # Check if BillAddr is completely empty
    bill_addr = customer_data["BillAddr"]
    if not any(
        [
            bill_addr["Line1"],
            bill_addr["City"],
            bill_addr["CountrySubDivisionCode"],
            bill_addr["PostalCode"],
        ]
    ):
        customer_data.pop("BillAddr")

    return customer_data


def import_customers_thread():
    """Import customers from CSV in a separate thread"""
    global import_status

    try:
        # Mark as running
        import_status["is_running"] = True

        csv_file = "Friends of Mwangaza_Customer Contact List - All Fields.csv"

        if not os.path.exists(csv_file):
            add_log(f"CSV file not found: {csv_file}", "error")
            import_status["is_running"] = False
            return

        add_log(f"Reading customers from {csv_file}...")

        # Read customers from CSV
        customers = []
        with open(csv_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                customers.append(row)

        add_log(f"Found {len(customers)} customers in CSV file.")

        # Get existing customers to avoid duplicates
        add_log("Fetching existing customers from QBO Sandbox...")
        existing_customers = qbo_service.get_all_customers()
        existing_names = [customer.get("DisplayName", "").lower() for customer in existing_customers]
        add_log(f"Found {len(existing_customers)} existing customers in QBO Sandbox.")

        # Create a list of customers to import (excluding those to skip)
        customers_to_import = []
        for row in customers:
            display_name = row.get("Customer", "")

            # Skip empty names
            if not display_name:
                add_log(f"Skipping: Empty customer name", "warning")
                import_status["skipped"] += 1
                continue

            # Skip if customer already exists (case-insensitive check)
            if display_name.lower() in existing_names:
                add_log(f"Skipping: {display_name} (already exists in QBO)", "warning")
                import_status["skipped"] += 1
                continue

            customers_to_import.append(row)

        import_status["total"] = len(customers_to_import)
        add_log(f"Found {len(customers_to_import)} new customers to import")
        add_log(f"Skipping {import_status['skipped']} customers that already exist")

        # Import customers
        for row in customers_to_import:
            display_name = row.get("Customer", "")

            # Create customer data
            customer_data = create_customer_from_csv_row(row)

            try:
                # Create customer in QBO
                result = qbo_service.create_customer(customer_data)

                if result and "Id" in result:
                    add_log(f"✓ Created: {display_name} (ID: {result['Id']})", "success")
                    import_status["imported"] += 1
                    # Update existing names list to avoid duplicates in the same import
                    existing_names.append(display_name.lower())
                else:
                    add_log(f"✗ Failed: {display_name}", "error")
                    import_status["errors"] += 1

                # Add a small delay to avoid rate limits
                time.sleep(0.5)

            except Exception as e:
                add_log(f"✗ Error: {display_name} - {str(e)}", "error")
                import_status["errors"] += 1
                # Continue with next customer even if one fails

        add_log("\nImport Summary:")
        add_log("=" * 50)
        add_log(f"Total customers in CSV: {len(customers)}")
        add_log(f"Successfully imported: {import_status['imported']}")
        add_log(f"Skipped (already exists): {import_status['skipped']}")
        add_log(f"Errors: {import_status['errors']}")

        # Mark as complete
        import_status["is_complete"] = True
        import_status["is_running"] = False

    except Exception as e:
        add_log(f"Error in import process: {str(e)}", "error")
        import_status["is_running"] = False


@app.route("/")
def index():
    """Render the status page"""
    # Check if we're authenticated with QBO
    is_authenticated = qbo_service.access_token is not None and qbo_service.realm_id is not None

    return render_template_string(
        STATUS_TEMPLATE,
        environment=QBO_ENVIRONMENT,
        total=import_status["total"],
        imported=import_status["imported"],
        skipped=import_status["skipped"],
        errors=import_status["errors"],
        logs=import_status["logs"],
        is_running=import_status["is_running"],
        is_complete=import_status["is_complete"],
        is_authenticated=is_authenticated,
    )


@app.route("/start-import")
def start_import():
    """Start the import process"""
    if not import_status["is_running"] and not import_status["is_complete"]:
        # Start import in a background thread
        thread = threading.Thread(target=import_customers_thread)
        thread.daemon = True
        thread.start()

    return redirect(url_for("index"))


@app.route("/qbo/authorize")
def authorize_qbo():
    """Start QBO OAuth flow."""
    global qbo_service
    authorization_url = qbo_service.get_authorization_url()
    return redirect(authorization_url)


@app.route("/qbo/callback")
def qbo_callback():
    """Handle QBO OAuth callback."""
    global qbo_service
    code = request.args.get("code")
    realmId = request.args.get("realmId")

    if code and realmId:
        success = qbo_service.get_tokens(code, realmId)
        if success:
            add_log(f"Successfully authenticated with QBO {QBO_ENVIRONMENT}!", "success")
        else:
            add_log("Failed to authenticate with QBO", "error")
    else:
        add_log("Missing code or realmId in callback", "error")

    return redirect(url_for("index"))


if __name__ == "__main__":
    # Initialize QBO service
    qbo_service = QBOService(
        client_id=os.getenv("QBO_CLIENT_ID"),
        client_secret=os.getenv("QBO_CLIENT_SECRET"),
        redirect_uri="http://localhost:5000/qbo/callback",  # Must match the app's callback URL
        environment=QBO_ENVIRONMENT,
    )

    add_log(f"Starting QBO Customer Import App (Environment: {QBO_ENVIRONMENT})")
    add_log("Open your browser to http://localhost:5000/ to continue")

    # Check if we're already authenticated
    if qbo_service.access_token and qbo_service.realm_id:
        add_log("Already authenticated with QBO", "success")
    else:
        add_log(
            "Not authenticated with QBO. Please click 'Connect to QBO' in the web interface.",
            "warning",
        )

    # Start the Flask app
    app.run(debug=True, host="0.0.0.0", port=5000)

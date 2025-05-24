import os
import json
import requests
import argparse
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from werkzeug.utils import secure_filename
import pandas as pd
from dotenv import load_dotenv
from urllib.parse import quote

# Try importing from the src package first
try:
    from src.utils.gemini_service import GeminiService
    from src.utils.qbo_service import QBOService
    from src.utils.file_processor import FileProcessor
except ModuleNotFoundError:
    # Fall back to relative imports if running directly from src directory
    from utils.gemini_service import GeminiService
    from utils.qbo_service import QBOService
    from utils.file_processor import FileProcessor

# Load environment variables
load_dotenv()

import re
from datetime import datetime
import dateutil.parser

def normalize_check_number(check_no):
    """Normalize check number for comparison."""
    if not check_no:
        return ''
    # Remove leading zeros and spaces
    normalized = str(check_no).strip().lstrip('0')
    # If all zeros were removed, ensure at least '0' remains
    return normalized if normalized else '0'

def normalize_amount(amount):
    """Normalize amount for comparison."""
    if not amount:
        return ''
    # Remove currency symbols, commas, and spaces
    amount_str = str(amount).replace('$', '').replace(',', '').strip()
    try:
        # Convert to float and format to 2 decimal places
        return f"{float(amount_str):.2f}"
    except:
        return amount_str

def normalize_donor_name(name):
    """Normalize donor name for comparison."""
    if not name:
        return ''
    # Convert to lowercase, remove punctuation, normalize whitespace
    name = re.sub(r'[^\w\s]', '', str(name).lower())
    return ' '.join(name.split())

def normalize_date(date_str):
    """Normalize date string to consistent format."""
    if not date_str:
        return ''
    try:
        # Try to parse various date formats
        parsed_date = dateutil.parser.parse(str(date_str))
        return parsed_date.strftime('%Y-%m-%d')
    except:
        # If parsing fails, return the original string
        return str(date_str).strip()

def deduplicate_and_synthesize_donations(existing_donations, new_donations):
    """
    Strict deduplication using Check No. + Amount as unique key.
    
    This ensures NO duplicates can exist with the same check number and amount.
    All data is merged into the single record for each unique key.
    """
    # Convert existing donations list to a dictionary with unique keys
    unique_donations = {}
    
    # First, add all existing donations to the unique dictionary
    for donation in existing_donations:
        check_no = normalize_check_number(donation.get('Check No.', ''))
        amount = normalize_amount(donation.get('Gift Amount', ''))
        
        # Create unique key
        if check_no and amount:
            # Check donations use check number + amount as key
            unique_key = f"CHECK_{check_no}_{amount}"
        else:
            # Non-check donations use donor name + amount + date as key
            donor_name = normalize_donor_name(donation.get('Donor Name', ''))
            gift_date = normalize_date(donation.get('Gift Date', ''))
            
            if donor_name and amount:
                unique_key = f"OTHER_{donor_name}_{amount}_{gift_date}"
            else:
                # Skip donations without enough identifying information
                print(f"Skipping donation without sufficient identifying info: {donation}")
                continue
        
        # Store in dictionary (will overwrite if duplicate key exists)
        if unique_key in unique_donations:
            print(f"WARNING: Duplicate key found in existing donations: {unique_key}")
        unique_donations[unique_key] = donation
    
    # Now process new donations
    merge_count = 0
    new_count = 0
    
    for new_donation in new_donations:
        check_no = normalize_check_number(new_donation.get('Check No.', ''))
        amount = normalize_amount(new_donation.get('Gift Amount', ''))
        
        # Skip suspicious entries (e.g., check numbers that are too short or don't look valid)
        if check_no and len(check_no) < 3 and check_no.isdigit():
            # Check numbers like "195" are suspicious - real checks are usually 4+ digits
            print(f"WARNING: Suspicious check number '{check_no}' - may be a page number or reference")
            # Still process it but log the warning
        
        # Create unique key
        if check_no and amount:
            # Check donations use check number + amount as key
            unique_key = f"CHECK_{check_no}_{amount}"
        else:
            # Non-check donations use donor name + amount + date as key
            donor_name = normalize_donor_name(new_donation.get('Donor Name', ''))
            gift_date = normalize_date(new_donation.get('Gift Date', ''))
            
            if donor_name and amount:
                unique_key = f"OTHER_{donor_name}_{amount}_{gift_date}"
            else:
                # Skip donations without enough identifying information
                print(f"Skipping new donation without sufficient identifying info: {new_donation}")
                continue
        
        # Check if this key already exists
        if unique_key in unique_donations:
            # Merge with existing donation
            print(f"Merging donation with key: {unique_key}")
            unique_donations[unique_key] = synthesize_donation_data(
                unique_donations[unique_key], new_donation
            )
            merge_count += 1
        else:
            # Add as new donation
            print(f"Adding new donation with key: {unique_key}")
            unique_donations[unique_key] = new_donation
            new_count += 1
    
    # Convert back to list
    result = list(unique_donations.values())
    
    # Ensure internal IDs are unique
    for i, donation in enumerate(result):
        if 'internalId' not in donation or not donation['internalId']:
            donation['internalId'] = f"donation_{i}"
    
    print(f"Deduplication complete: {len(result)} unique donations (merged {merge_count}, added {new_count})")
    
    return result

def synthesize_donation_data(existing, new):
    """
    Intelligently merge two donation records, preserving the most complete information.
    
    Priority rules:
    1. Non-null values override null values
    2. Longer/more complete values override shorter ones
    3. Values from images override values from PDFs (generally more accurate)
    4. Specific fields have custom merge logic
    """
    merged = existing.copy()
    
    # Initialize merge history if not present
    if 'mergeHistory' not in merged:
        merged['mergeHistory'] = []
    
    # Track what fields are being merged
    merged_fields = []
    
    # Fields that should be merged by taking non-null or most complete value
    simple_merge_fields = [
        'Donor Name', 'First Name', 'Last Name', 'Full Name',
        'Address - Line 1', 'City', 'State', 'ZIP',
        'Organization Name', 'Email', 'Phone',
        'Check Date', 'Deposit Date', 'Deposit Method'
    ]
    
    for field in simple_merge_fields:
        existing_val = existing.get(field)
        new_val = new.get(field)
        
        # Take new value if existing is empty/null/N/A
        if (not existing_val or existing_val == 'N/A') and new_val and new_val != 'N/A':
            merged[field] = new_val
            merged_fields.append(field)
        # Take longer/more complete value for text fields
        elif existing_val and new_val and isinstance(existing_val, str) and isinstance(new_val, str):
            # Safely strip whitespace
            existing_stripped = existing_val.strip() if existing_val else ''
            new_stripped = new_val.strip() if new_val else ''
            
            # Also replace N/A with actual values
            if existing_val == 'N/A' and new_val != 'N/A':
                merged[field] = new_val
                merged_fields.append(field)
            elif len(new_stripped) > len(existing_stripped) and new_val != 'N/A':
                merged[field] = new_val
                merged_fields.append(field)
    
    # Special handling for memo - concatenate if different
    existing_memo = existing.get('Memo') or ''
    new_memo = new.get('Memo') or ''
    existing_memo = existing_memo.strip() if existing_memo else ''
    new_memo = new_memo.strip() if new_memo else ''
    
    if new_memo and new_memo not in existing_memo:
        if existing_memo:
            merged['Memo'] = f"{existing_memo}; {new_memo}"
        else:
            merged['Memo'] = new_memo
    
    # Preserve QBO-related fields from existing record
    qbo_fields = ['qboCustomerId', 'qbCustomerStatus', 'qbSyncStatus', 
                  'matchMethod', 'matchConfidence', 'internalId']
    for field in qbo_fields:
        if field in existing:
            merged[field] = existing[field]
    
    # Data source tracking
    if 'dataSource' in existing and 'dataSource' in new:
        if existing['dataSource'] != new['dataSource']:
            merged['dataSource'] = 'Mixed'
    
    # Add merge history entry if fields were merged
    if merged_fields:
        merged['mergeHistory'].append({
            'timestamp': datetime.now().isoformat(),
            'mergedFields': merged_fields,
            'sourceData': {
                'checkNo': new.get('Check No.', ''),
                'amount': new.get('Gift Amount', ''),
                'donor': new.get('Donor Name', '')
            }
        })
        merged['isMerged'] = True
    
    return merged

# Define model aliases
MODEL_MAPPING = {
    'gemini-flash': 'gemini-2.5-flash-preview-04-17',
    'gemini-pro': 'gemini-2.5-pro-preview-03-25',
    # Include the full model names as keys for consistency
    'gemini-2.5-flash-preview-04-17': 'gemini-2.5-flash-preview-04-17',
    'gemini-2.5-pro-preview-03-25': 'gemini-2.5-pro-preview-03-25'
}

# Resolve the environment variable model
gemini_env_model = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash-preview-04-17')
# If the environment variable is an alias, resolve it
resolved_env_model = MODEL_MAPPING.get(gemini_env_model, gemini_env_model)

# Parse command line arguments for QBO environment and Gemini model
parser = argparse.ArgumentParser(description="FOM to QBO Automation App")
parser.add_argument('--env', type=str, choices=['sandbox', 'production'], default=os.getenv('QBO_ENVIRONMENT', 'sandbox'),
                    help='QuickBooks Online environment (sandbox or production)')
parser.add_argument('--model', type=str, default=resolved_env_model,
                    choices=['gemini-flash', 'gemini-pro', 'gemini-2.5-flash-preview-04-17', 'gemini-2.5-pro-preview-03-25'],
                    help='Gemini model to use (flash for faster responses, pro for better quality)')
args, _ = parser.parse_known_args()

# Use the command-line specified environment
qbo_environment = args.env
# Resolve model alias if needed
gemini_model = MODEL_MAPPING.get(args.model, args.model)

print(f"Starting application with QBO environment: {qbo_environment}")
print(f"Using Gemini model: {gemini_model}")

app = Flask(__name__)
app.secret_key = os.urandom(24)  # For session management
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB upload limit

# Create necessary directories
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize services
gemini_service = GeminiService(
    api_key=os.getenv('GEMINI_API_KEY'),
    model_name=gemini_model  # Use the command-line specified model
)
qbo_service = QBOService(
    client_id=os.getenv('QBO_CLIENT_ID'),
    client_secret=os.getenv('QBO_CLIENT_SECRET'),
    redirect_uri=os.getenv('QBO_REDIRECT_URI'),
    environment=qbo_environment  # Use the command-line specified environment
)
# Pass both services to the file processor for integrated customer matching
file_processor = FileProcessor(gemini_service, qbo_service)

# Routes
@app.route('/')
def index():
    """Render the main application page."""
    return render_template('index.html')
    
@app.route('/qbo/auth-status')
def qbo_auth_status():
    """Check QBO authentication status."""
    authenticated = qbo_service.access_token is not None and qbo_service.realm_id is not None
    
    # Check if we just connected to QBO and need to resume file processing
    just_connected = session.pop('qbo_just_connected', False)
    
    return jsonify({
        'authenticated': authenticated,
        'tokenExpiry': qbo_service.token_expires_at if authenticated else None,
        'justConnected': just_connected
    })

@app.route('/upload', methods=['POST'])
def upload_files():
    """Handle file uploads (images, PDFs, CSV)."""
    try:
        # Check if QBO is authenticated for customer matching
        qbo_authenticated = qbo_service.access_token is not None and qbo_service.realm_id is not None
        if not qbo_authenticated:
            print("Warning: QBO is not authenticated - customer matching will be skipped")
            
        # Check if request has the files part
        if 'files' not in request.files:
            print("No files part in the request")
            return jsonify({
                'success': False,
                'message': 'No files were selected'
            }), 400
        
        files = request.files.getlist('files')
        if not files or len(files) == 0 or all(file.filename == '' for file in files):
            print("No files selected")
            return jsonify({
                'success': False,
                'message': 'No files were selected'
            }), 400
            
        # Log the number of files and their sizes
        print(f"Received {len(files)} files:")
        for file in files:
            if file.filename != '':
                file.seek(0, os.SEEK_END)
                file_size = file.tell()
                file.seek(0)  # Reset file pointer
                print(f"- {file.filename}: {file_size / 1024 / 1024:.2f} MB")
        
        # Placeholder for extracted donation data
        donations = []
        errors = []
        warnings = []
        
        # If QBO is not authenticated, add a warning
        if not qbo_authenticated:
            warnings.append("QuickBooks is not connected. Customer matching will be skipped. Please connect to QuickBooks to enable automatic customer matching.")
        
        for file in files:
            if file.filename == '':
                continue
            
            try:
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                
                # Process different file types
                file_ext = os.path.splitext(filename)[1].lower()
                
                if file_ext in ['.jpg', '.jpeg', '.png', '.pdf', '.csv']:
                    # Process all files using Gemini
                    print(f"Processing {file_ext} file: {filename}")
                    
                    extracted_data = file_processor.process(file_path, file_ext)
                    
                    # Set the data source based on file type
                    data_source = 'CSV' if file_ext == '.csv' else 'LLM'
                    source_prefix = 'csv' if file_ext == '.csv' else 'llm'
                    
                    if extracted_data:
                        # Check if we have a list of donations or a single donation
                        if isinstance(extracted_data, list):
                            print(f"Processing multiple donations from {file_ext}: {len(extracted_data)}")
                            for idx, donation in enumerate(extracted_data):
                                donation['dataSource'] = data_source
                                donation['internalId'] = f"{source_prefix}_{len(donations) + idx}"
                                donation['qbSyncStatus'] = 'Pending'
                                # Only initialize as Unknown if no status was set during matching
                                if 'qbCustomerStatus' not in donation:
                                    donation['qbCustomerStatus'] = 'Unknown'
                                donations.append(donation)
                        else:
                            # Single donation (typically from image)
                            extracted_data['dataSource'] = data_source
                            extracted_data['internalId'] = f"{source_prefix}_{len(donations)}"
                            extracted_data['qbSyncStatus'] = 'Pending'
                            # Only initialize as Unknown if no status was set during matching
                            if 'qbCustomerStatus' not in extracted_data:
                                extracted_data['qbCustomerStatus'] = 'Unknown'
                            donations.append(extracted_data)
                    else:
                        print(f"No donation data extracted from {filename}")
                        errors.append(f"No donation data could be extracted from {filename}")
                else:
                    print(f"Unsupported file type: {file_ext}")
                    errors.append(f"Unsupported file type: {file_ext}")
            
            except Exception as e:
                print(f"Error processing {file.filename}: {str(e)}")
                errors.append(f"Error processing {file.filename}: {str(e)}")
        
        # Store donations in session for later use with deduplication
        if 'donations' not in session:
            session['donations'] = []
        
        # Track counts before deduplication
        initial_count = len(session['donations'])
        new_count = len(donations)
        
        # Apply smart deduplication and data synthesis
        session['donations'] = deduplicate_and_synthesize_donations(
            session['donations'], donations
        )
        
        # Calculate merge statistics
        final_count = len(session['donations'])
        merged_count = initial_count + new_count - final_count
        
        # Return appropriate response based on success/errors
        if session['donations']:
            # Return the deduplicated donations from session
            return jsonify({
                'success': True,
                'donations': session['donations'],
                'newCount': new_count,
                'totalCount': final_count,
                'mergedCount': merged_count,
                'warnings': (errors + warnings) if (errors or warnings) else None,
                'qboAuthenticated': qbo_authenticated
            })
        else:
            message = 'No donation data could be extracted. ' + (', '.join(errors) if errors else '')
            if warnings:
                message += ' ' + (', '.join(warnings))
                
            return jsonify({
                'success': False,
                'message': message,
                'qboAuthenticated': qbo_authenticated
            }), 400
    
    except Exception as e:
        import traceback
        print(f"Unexpected error in upload processing: {str(e)}")
        print("Full traceback:")
        traceback.print_exc()
        
        return jsonify({
            'success': False,
            'message': f'An unexpected error occurred: {str(e)}'
        }), 500

@app.route('/donations', methods=['GET'])
def get_donations():
    """Return all donations currently in the session."""
    donations = session.get('donations', [])
    return jsonify(donations)

@app.route('/donations/<donation_id>', methods=['PUT'])
def update_donation(donation_id):
    """Update a donation record."""
    donations = session.get('donations', [])
    donation_data = request.json
    
    for i, donation in enumerate(donations):
        if donation['internalId'] == donation_id:
            donations[i] = donation_data
            session['donations'] = donations
            return jsonify({'success': True})
    
    return jsonify({'success': False, 'message': 'Donation not found'}), 404

@app.route('/donations/remove-invalid', methods=['POST'])
def remove_invalid_donations():
    """Remove invalid donations from the session."""
    donations = session.get('donations', [])
    
    if not request.json or 'invalidIds' not in request.json:
        return jsonify({
            'success': False,
            'message': 'No invalid IDs provided'
        }), 400
    
    invalid_ids = request.json['invalidIds']
    if not invalid_ids or not isinstance(invalid_ids, list):
        return jsonify({
            'success': False,
            'message': 'Invalid IDs must be a non-empty list'
        }), 400
    
    # Count the number of donations before filtering
    initial_count = len(donations)
    
    # Filter out invalid donations
    valid_donations = [d for d in donations if d.get('internalId') not in invalid_ids]
    
    # Count how many were removed
    removed_count = initial_count - len(valid_donations)
    
    # Update the session
    session['donations'] = valid_donations
    
    print(f"Removed {removed_count} invalid donations from session")
    
    return jsonify({
        'success': True,
        'removedCount': removed_count
    })

@app.route('/qbo/status')
def qbo_status():
    """Check if QBO is authenticated."""
    return jsonify({
        'authenticated': qbo_service.access_token is not None and qbo_service.realm_id is not None,
        'realmId': qbo_service.realm_id,
        'tokenExpiry': qbo_service.token_expires_at if hasattr(qbo_service, 'token_expires_at') else None,
        'environment': qbo_service.environment  # Include the environment in the status
    })

@app.route('/qbo/authorize')
def authorize_qbo():
    """Start QBO OAuth flow."""
    authorization_url = qbo_service.get_authorization_url()
    return redirect(authorization_url)

@app.route('/qbo/callback')
def qbo_callback():
    """Handle QBO OAuth callback."""
    code = request.args.get('code')
    realmId = request.args.get('realmId')
    
    if code and realmId:
        qbo_service.get_tokens(code, realmId)
        
        # Pre-fetch customers for future matching to populate cache
        try:
            customers = qbo_service.get_all_customers()
            customer_count = len(customers)
            print(f"Pre-fetched {customer_count} customers for future matching")
            
            # Store success message including customer count
            flash(f'Successfully connected to QuickBooks Online. Retrieved {customer_count} customers.', 'success')
        except Exception as e:
            print(f"Error pre-fetching customers: {str(e)}")
            flash('Connected to QuickBooks Online, but had trouble retrieving customers.', 'warning')
    else:
        flash('Failed to connect to QuickBooks Online. Please try again.', 'error')
    
    # Add a script to update the UI
    session['qbo_connected'] = True
    
    # Return a simple success page that will work with the popup window
    success_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>QuickBooks Connected</title>
        <style>
            body { font-family: Arial, sans-serif; text-align: center; padding-top: 50px; }
            .success { color: #28a745; font-size: 24px; margin-bottom: 20px; }
            .message { margin-bottom: 30px; }
        </style>
    </head>
    <body>
        <div class="success">✓ Successfully Connected to QuickBooks!</div>
        <div class="message">You may close this window and return to the application.</div>
        <script>
            // Close this window after 3 seconds
            setTimeout(function() {
                window.close();
            }, 3000);
        </script>
    </body>
    </html>
    """
    
    return success_html

@app.route('/qbo/customer/<donation_id>', methods=['GET'])
def find_customer(donation_id):
    """Find QBO customer based on donation information."""
    donations = session.get('donations', [])
    
    for donation in donations:
        if donation['internalId'] == donation_id:
            customer_lookup = donation.get('customerLookup', '')
            
            if customer_lookup:
                customer = qbo_service.find_customer(customer_lookup)
                
                if customer:
                    # Compare addresses
                    address_match = True
                    if (donation.get('Address - Line 1') and 
                        donation.get('Address - Line 1') != customer.get('BillAddr', {}).get('Line1', '')):
                        address_match = False
                    
                    donation['qbCustomerStatus'] = 'Matched' if address_match else 'Matched-AddressMismatch'
                    donation['qboCustomerId'] = customer.get('Id')
                    session['donations'] = donations
                    
                    return jsonify({
                        'success': True,
                        'customerFound': True,
                        'addressMatch': address_match,
                        'customer': customer
                    })
                else:
                    donation['qbCustomerStatus'] = 'New'
                    session['donations'] = donations
                    
                    return jsonify({
                        'success': True,
                        'customerFound': False
                    })
    
    return jsonify({'success': False, 'message': 'Donation not found'}), 404

@app.route('/qbo/customers/all', methods=['GET'])
def get_all_customers():
    """Get all QuickBooks customers for manual matching."""
    try:
        # Check if authenticated
        if not qbo_service.access_token or not qbo_service.realm_id:
            return jsonify({
                'success': False,
                'message': 'Not authenticated with QuickBooks Online'
            }), 401
        
        # Get all customers
        all_customers = qbo_service.get_all_customers()
        
        # Prepare simplified customer data for the UI
        customers = []
        for customer in all_customers:
            # Extract address if available
            address = "No address on file"
            if customer.get('BillAddr'):
                bill_addr = customer.get('BillAddr', {})
                addr_parts = []
                if bill_addr.get('Line1'):
                    addr_parts.append(bill_addr.get('Line1'))
                if bill_addr.get('City'):
                    addr_parts.append(bill_addr.get('City'))
                if bill_addr.get('CountrySubDivisionCode'):
                    addr_parts.append(bill_addr.get('CountrySubDivisionCode'))
                if bill_addr.get('PostalCode'):
                    addr_parts.append(bill_addr.get('PostalCode'))
                
                if addr_parts:
                    address = ", ".join(addr_parts)
            
            customers.append({
                'id': customer.get('Id'),
                'name': customer.get('DisplayName', ''),
                'address': address,
                'syncToken': customer.get('SyncToken', '0')
            })
        
        # Sort customers by name for easier browsing
        customers.sort(key=lambda x: x['name'].lower())
        
        return jsonify({
            'success': True,
            'customers': customers
        })
        
    except Exception as e:
        print(f"Error fetching customers: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error fetching customers: {str(e)}'
        }), 500

@app.route('/qbo/customer/manual-match/<donation_id>', methods=['POST'])
def manual_match_customer(donation_id):
    """Manually match a donation to a QBO customer."""
    try:
        # Get donation from session
        donations = session.get('donations', [])
        donation_index = None
        
        for i, donation in enumerate(donations):
            if donation['internalId'] == donation_id:
                donation_index = i
                break
        
        if donation_index is None:
            return jsonify({
                'success': False,
                'message': 'Donation not found'
            }), 404
        
        # Get customer ID from request
        if not request.json or 'customerId' not in request.json:
            return jsonify({
                'success': False,
                'message': 'Customer ID is required'
            }), 400
            
        customer_id = request.json['customerId']
        
        # Get customer details from QBO
        query = f"SELECT * FROM Customer WHERE Id = '{customer_id}'"
        encoded_query = quote(query)
        url = f"{qbo_service.api_base}{qbo_service.realm_id}/query?query={encoded_query}"
        response = requests.get(url, headers=qbo_service._get_auth_headers())
        
        customer = None
        if response.status_code == 200:
            data = response.json()
            if data['QueryResponse'].get('Customer'):
                customer = data['QueryResponse']['Customer'][0]
        
        if not customer:
            return jsonify({
                'success': False,
                'message': 'Customer not found in QBO'
            }), 404
        
        # Update donation with customer info
        donation = donations[donation_index]
        donation['qbCustomerStatus'] = 'Matched'
        donation['qboCustomerId'] = customer.get('Id')
        donation['customerLookup'] = customer.get('DisplayName', '')
        donation['matchMethod'] = 'manual'
        donation['matchConfidence'] = 'high'
        
        # Update session
        session['donations'] = donations
        
        return jsonify({
            'success': True,
            'customer': {
                'id': customer.get('Id'),
                'name': customer.get('DisplayName', ''),
                'syncToken': customer.get('SyncToken', '0')
            }
        })
        
    except Exception as e:
        print(f"Error manually matching customer: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error manually matching customer: {str(e)}'
        }), 500

@app.route('/qbo/customer/create/<donation_id>', methods=['POST'])
def create_customer(donation_id):
    """Create a new QBO customer from donation information."""
    donations = session.get('donations', [])
    
    for i, donation in enumerate(donations):
        if donation['internalId'] == donation_id:
            if donation['dataSource'] == 'CSV':
                return jsonify({'success': False, 'message': 'Cannot create customer from CSV data'}), 400
            
            customer_data = {
                'DisplayName': donation.get('customerLookup', ''),
                'PrimaryEmailAddr': {'Address': ''},
                'BillAddr': {
                    'Line1': donation.get('Address - Line 1', ''),
                    'City': donation.get('City', ''),
                    'CountrySubDivisionCode': donation.get('State', ''),
                    'PostalCode': donation.get('ZIP', '')
                }
            }
            
            result = qbo_service.create_customer(customer_data)
            
            if result and 'Id' in result:
                donation['qbCustomerStatus'] = 'Matched'
                donation['qboCustomerId'] = result['Id']
                donations[i] = donation
                session['donations'] = donations
                
                return jsonify({
                    'success': True,
                    'customer': result
                })
            else:
                return jsonify({
                    'success': False,
                    'message': 'Failed to create customer in QBO'
                }), 500
    
    return jsonify({'success': False, 'message': 'Donation not found'}), 404

@app.route('/qbo/customer/update/<donation_id>', methods=['PUT'])
def update_customer(donation_id):
    """Update a QBO customer with new address information."""
    donations = session.get('donations', [])
    
    for i, donation in enumerate(donations):
        if donation['internalId'] == donation_id:
            if donation['dataSource'] == 'CSV':
                return jsonify({'success': False, 'message': 'Cannot update customer from CSV data'}), 400
            
            if not donation.get('qboCustomerId'):
                return jsonify({'success': False, 'message': 'No QBO customer ID available'}), 400
            
            customer_data = {
                'Id': donation['qboCustomerId'],
                'SyncToken': request.json.get('syncToken', '0'),
                'BillAddr': {
                    'Line1': donation.get('Address - Line 1', ''),
                    'City': donation.get('City', ''),
                    'CountrySubDivisionCode': donation.get('State', ''),
                    'PostalCode': donation.get('ZIP', '')
                }
            }
            
            result = qbo_service.update_customer(customer_data)
            
            if result and 'Id' in result:
                donation['qbCustomerStatus'] = 'Matched'
                donations[i] = donation
                session['donations'] = donations
                
                return jsonify({
                    'success': True,
                    'customer': result
                })
            else:
                return jsonify({
                    'success': False,
                    'message': 'Failed to update customer in QBO'
                }), 500
    
    return jsonify({'success': False, 'message': 'Donation not found'}), 404

@app.route('/qbo/sales-receipt/<donation_id>', methods=['POST'])
def create_sales_receipt(donation_id):
    """Create a QBO sales receipt for a donation."""
    donations = session.get('donations', [])
    
    for i, donation in enumerate(donations):
        if donation['internalId'] == donation_id:
            if donation['dataSource'] == 'CSV':
                return jsonify({'success': False, 'message': 'Cannot create sales receipt from CSV data'}), 400
            
            if not donation.get('qboCustomerId'):
                # Try to find customer first
                customer_lookup = donation.get('customerLookup', '')
                if customer_lookup:
                    customer = qbo_service.find_customer(customer_lookup)
                    if customer:
                        donation['qboCustomerId'] = customer.get('Id')
                    else:
                        return jsonify({
                            'success': False,
                            'message': 'Customer not found in QBO. Please create customer first.'
                        }), 400
                else:
                    return jsonify({
                        'success': False,
                        'message': 'Customer lookup field is empty'
                    }), 400
            
            # Get the item ref from request or use default
            # Ensure we always have a valid itemRef to avoid QBO API errors
            item_ref = request.json.get('itemRef')
            if not item_ref or item_ref.strip() == '':
                item_ref = '1'  # Default fallback
            print(f"Using item_ref: {item_ref} for donation {donation_id}")
            
            # Format dates with validation
            today = pd.Timestamp.now().strftime('%Y-%m-%d')
            
            # Validate Check Date
            check_date = donation.get('Check Date', '')
            try:
                # Check if it's a valid date and format it
                if check_date:
                    pd.to_datetime(check_date)
            except:
                # If invalid date, use today's date
                print(f"Invalid Check Date: {check_date}, using today's date")
                check_date = today
            
            # Get other fields with validation
            check_no = donation.get('Check No.', 'N/A')
            # Validate Gift Amount
            try:
                gift_amount = float(donation.get('Gift Amount', 0))
            except ValueError:
                return jsonify({
                    'success': False,
                    'message': 'Invalid Gift Amount, must be a number'
                }), 400
            
            last_name = donation.get('Last Name', '')
            first_name = donation.get('First Name', '')
            memo = donation.get('Memo', '')
            
            # Format description, limiting to reasonable length
            description = f"{check_no}_{gift_date}_{gift_amount}_{last_name}_{first_name}"
            if memo:
                description += f"_{memo}"
            
            # Truncate if too long - QuickBooks has limits
            if len(description) > 1000:
                description = description[:997] + "..."
            
            # Format receipt number
            doc_number = f"{today}_{check_no}"
            if len(doc_number) > 21:  # QB has a 21 char limit
                doc_number = doc_number[:21]
            
            # Check for custom account ID from setup modal
            deposit_account_id = request.json.get('depositToAccountId', '12000')
            payment_method_id = request.json.get('paymentMethodId', 'CHECK')
            
            # Log custom fields if provided
            if request.json.get('depositToAccountId'):
                print(f"Using custom deposit account ID: {deposit_account_id}")
            if request.json.get('paymentMethodId'):
                print(f"Using custom payment method ID: {payment_method_id}")
                
            # Prepare sales receipt data
            sales_receipt_data = {
                'CustomerRef': {
                    'value': donation['qboCustomerId']
                },
                'PaymentMethodRef': {
                    'value': payment_method_id  # May be custom or default 'CHECK'
                },
                'PaymentRefNum': check_no,
                'TxnDate': check_date,
                'DepositToAccountRef': {
                    'value': deposit_account_id  # May be custom or default '12000'
                },
                'DocNumber': doc_number,
                'Line': [
                    {
                        'DetailType': 'SalesItemLineDetail',
                        'Amount': gift_amount,
                        'SalesItemLineDetail': {
                            'ItemRef': {
                                'value': item_ref
                            },
                            'ServiceDate': check_date
                        },
                        'Description': description
                    }
                ],
                'CustomerMemo': {
                    'value': f"auto import on {today}"
                }
            }
            
            result = qbo_service.create_sales_receipt(sales_receipt_data)
            
            # Check for error returned from enhanced error handling
            if result and result.get('error'):
                error_message = result.get('message', 'Unknown error')
                error_detail = result.get('detail', '')
                
                # Format storage of the error in the donation record
                donation['qbSyncStatus'] = 'Error'
                donation['qbSyncError'] = error_message
                donations[i] = donation
                session['donations'] = donations
                
                # Check for specific types of errors
                if result.get('requiresSetup'):
                    return jsonify({
                        'success': False,
                        'requiresSetup': True,
                        'setupType': result.get('setupType'),
                        'invalidId': result.get('invalidId'),
                        'message': error_message,
                        'detail': error_detail
                    }), 400
                
                # Default error response for other types of errors
                return jsonify({
                    'success': False,
                    'message': error_message,
                    'detail': error_detail
                }), 500
            
            if result and 'Id' in result:
                donation['qbSyncStatus'] = 'Sent'
                donation['qboSalesReceiptId'] = result['Id']
                donations[i] = donation
                session['donations'] = donations
                
                return jsonify({
                    'success': True,
                    'salesReceipt': result
                })
            else:
                donation['qbSyncStatus'] = 'Error'
                donations[i] = donation
                session['donations'] = donations
                
                return jsonify({
                    'success': False,
                    'message': 'Failed to create sales receipt in QBO'
                }), 500
    
    return jsonify({'success': False, 'message': 'Donation not found'}), 404

@app.route('/qbo/sales-receipt/batch', methods=['POST'])
def create_batch_sales_receipts():
    """Create QBO sales receipts for all eligible donations."""
    donations = session.get('donations', [])
    results = []
    
    # Get the default values from request or use defaults
    default_item_ref = request.json.get('defaultItemRef', '1')  # Default fallback
    default_account_id = request.json.get('defaultDepositToAccountId', '12000')  # Default fallback
    default_payment_method_id = request.json.get('defaultPaymentMethodId', 'CHECK')  # Default fallback
    
    # Log what we're sending for debugging
    print(f"Sending batch sales receipts with default itemRef: {default_item_ref}, depositToAccountId: {default_account_id}, paymentMethodId: {default_payment_method_id}")
    
    # Track processing stats
    success_count = 0
    failure_count = 0
    
    for i, donation in enumerate(donations):
        try:
            # Skip CSV donations and already sent donations
            if donation['dataSource'] == 'CSV' or donation['qbSyncStatus'] == 'Sent':
                continue
            
            # Skip donations marked to exclude
            if donation.get('excludeFromBatch'):
                results.append({
                    'internalId': donation['internalId'],
                    'success': False,
                    'message': 'Excluded from batch processing'
                })
                failure_count += 1
                continue
            
            if not donation.get('qboCustomerId'):
                # Try to find customer first
                customer_lookup = donation.get('customerLookup', '')
                if customer_lookup:
                    customer = qbo_service.find_customer(customer_lookup)
                    if customer:
                        donation['qboCustomerId'] = customer.get('Id')
                    else:
                        results.append({
                            'internalId': donation['internalId'],
                            'success': False,
                            'message': 'Customer not found in QBO'
                        })
                        failure_count += 1
                        continue
                else:
                    results.append({
                        'internalId': donation['internalId'],
                        'success': False,
                        'message': 'Customer lookup field is empty'
                    })
                    failure_count += 1
                    continue
            
            # Validate data before sending
            
            # Validate Check Date
            today = pd.Timestamp.now().strftime('%Y-%m-%d')
            check_date = donation.get('Check Date', '')
            try:
                # Check if it's a valid date
                if check_date:
                    pd.to_datetime(check_date)
                else:
                    raise ValueError("Empty check date")
            except:
                # If invalid date, use today's date
                print(f"Invalid Check Date for donation {donation['internalId']}: {check_date}, using today's date")
                check_date = today
            
            # Validate Gift Amount
            try:
                gift_amount = float(donation.get('Gift Amount', 0))
                if gift_amount <= 0:
                    raise ValueError("Gift amount must be greater than zero")
            except ValueError as e:
                # Skip donations with invalid amounts
                error_msg = f"Invalid Gift Amount: {donation.get('Gift Amount')} - {str(e)}"
                results.append({
                    'internalId': donation['internalId'],
                    'success': False,
                    'message': error_msg
                })
                # Mark donation as error
                donation['qbSyncStatus'] = 'Error'
                donation['qbSyncError'] = error_msg
                donations[i] = donation
                failure_count += 1
                continue
            
            # Get other fields with validation
            check_no = donation.get('Check No.', 'N/A')
            last_name = donation.get('Last Name', '')
            first_name = donation.get('First Name', '')
            memo = donation.get('Memo', '')
            
            # Format description
            description = f"{check_no}_{check_date}_{gift_amount}_{last_name}_{first_name}"
            if memo:
                description += f"_{memo}"
            
            # Truncate if too long - QuickBooks has limits
            if len(description) > 1000:
                description = description[:997] + "..."
            
            # Format receipt number
            doc_number = f"{today}_{check_no}"
            if len(doc_number) > 21:  # QB has a 21 char limit
                doc_number = doc_number[:21]
            
            # Use item ref from the donation if specified, otherwise use the default
            # Ensure we always have a valid item reference to avoid QBO API errors
            item_ref = donation.get('itemRef') 
            if not item_ref or (isinstance(item_ref, str) and item_ref.strip() == ''):
                item_ref = default_item_ref
            # If we still don't have a valid item_ref, use '1' as the last resort
            if not item_ref or (isinstance(item_ref, str) and item_ref.strip() == ''):
                item_ref = '1'
            print(f"Using item_ref: {item_ref} for batch donation {donation.get('internalId')}")
            
            # Prepare sales receipt data with all required fields
            sales_receipt_data = {
                'CustomerRef': {
                    'value': donation['qboCustomerId']
                },
                'PaymentMethodRef': {
                    'value': default_payment_method_id  # Use the parameter from request
                },
                'PaymentRefNum': check_no,
                'TxnDate': check_date,
                'DepositToAccountRef': {
                    'value': default_account_id  # Use the parameter from request
                },
                'DocNumber': doc_number,
                'Line': [
                    {
                        'DetailType': 'SalesItemLineDetail',
                        'Amount': gift_amount,
                        'SalesItemLineDetail': {
                            'ItemRef': {
                                'value': item_ref
                            },
                            'ServiceDate': check_date
                        },
                        'Description': description
                    }
                ],
                'CustomerMemo': {
                    'value': f"auto import on {today}"
                }
            }
            
            result = qbo_service.create_sales_receipt(sales_receipt_data)
            
            # Check for error returned from enhanced error handling
            if result and result.get('error'):
                error_msg = result.get('message', 'Unknown error')
                donation['qbSyncStatus'] = 'Error'
                donation['qbSyncError'] = error_msg
                donations[i] = donation
                
                results.append({
                    'internalId': donation['internalId'],
                    'success': False,
                    'message': error_msg
                })
                failure_count += 1
                continue
            
            if result and 'Id' in result:
                donation['qbSyncStatus'] = 'Sent'
                donation['qboSalesReceiptId'] = result['Id']
                donations[i] = donation
                
                results.append({
                    'internalId': donation['internalId'],
                    'success': True,
                    'salesReceiptId': result['Id']
                })
                success_count += 1
            else:
                error_msg = 'Failed to create sales receipt in QBO'
                donation['qbSyncStatus'] = 'Error'
                donation['qbSyncError'] = error_msg
                donations[i] = donation
                
                results.append({
                    'internalId': donation['internalId'],
                    'success': False,
                    'message': error_msg
                })
                failure_count += 1
        
        except Exception as e:
            # Catch any unexpected errors during processing
            error_msg = f"Unexpected error: {str(e)}"
            results.append({
                'internalId': donation.get('internalId', 'unknown'),
                'success': False,
                'message': error_msg
            })
            
            # If we have a valid donation index, update its status
            if i < len(donations):
                donations[i]['qbSyncStatus'] = 'Error'
                donations[i]['qbSyncError'] = error_msg
            
            failure_count += 1
    
    # Save all donation changes to session
    session['donations'] = donations
    
    return jsonify({
        'success': True,
        'summary': {
            'total': len(results),
            'success': success_count,
            'failure': failure_count
        },
        'results': results
    })

@app.route('/report/generate', methods=['GET'])
def generate_report():
    """Generate a donation report."""
    donations = session.get('donations', [])
    
    if not donations:
        return jsonify({'success': False, 'message': 'No donations to report'}), 400
    
    # Format report similar to the provided examples
    report_data = []
    valid_entry_index = 1
    
    # Current date for the report
    current_date = pd.Timestamp.now().strftime('%m/%d/%Y')
    
    for donation in donations:
        # Skip entries with missing or invalid gift amounts
        if 'Gift Amount' not in donation or not donation['Gift Amount']:
            print(f"Skipping donation with missing Gift Amount: {donation.get('Donor Name', 'Unknown')}")
            continue
            
        donor_name = donation.get('Donor Name', 'Unknown Donor')
        address = donation.get('Address - Line 1', '')
        city = donation.get('City', '')
        state = donation.get('State', '')
        zipcode = donation.get('ZIP', '')
        address_line = f"{address}, {city}, {state} {zipcode}" if all([address, city, state, zipcode]) else ''
        
        # Create a multi-line address for text report format
        address_line_1 = address
        address_line_2 = f"{city}, {state} {zipcode}" if all([city, state, zipcode]) else ''
        
        # Safely convert gift amount to float
        try:
            amount_str = donation.get('Gift Amount', '0')
            if isinstance(amount_str, str):
                amount = float(amount_str.replace('$', '').replace(',', ''))
            else:
                amount = float(amount_str) if amount_str is not None else 0.0
        except (ValueError, TypeError):
            print(f"Skipping donation with invalid Gift Amount: {donor_name}")
            continue
        
        gift_date = donation.get('Gift Date', donation.get('Check Date', ''))
        check_no = donation.get('Check No.', '')
        if not check_no and donation.get('dataSource') == 'CSV':
            check_no = 'Online Donation'
        
        memo = donation.get('Memo', '')
        
        # Create full donation record with all fields for CSV export
        report_entry = {
            'index': valid_entry_index,
            'donor_name': donor_name,
            'address_line_1': address_line_1,
            'address_line_2': address_line_2,
            'address': address_line,  # Single line address for display
            'amount': amount,
            'date': gift_date,
            'check_no': check_no,
            'memo': memo,
            # Include all original fields for CSV export
            'first_name': donation.get('First Name', ''),
            'last_name': donation.get('Last Name', ''),
            'full_name': donation.get('Full Name', ''),
            'organization': donation.get('Organization Name', ''),
            'city': city,
            'state': state,
            'zip': zipcode,
            'deposit_date': donation.get('Deposit Date', current_date),
            'deposit_method': donation.get('Deposit Method', 'Check'),
            'customer_lookup': donation.get('customerLookup', '')
        }
        
        report_data.append(report_entry)
        valid_entry_index += 1
    
    # Calculate total (only for valid entries that made it to report_data)
    total = sum(entry['amount'] for entry in report_data)
    
    # Generate text report format (like in FOM deposit reports.md)
    text_report_lines = [
        f"**Deposit Report: {current_date}**",
        f"Below is a list of deposits totaling ${total:.2f}:",
        ""  # Blank line
    ]
    
    for entry in report_data:
        # Format each donation in the text format from the example
        text_report_lines.extend([
            f"{entry['index']}. {entry['donor_name']}",
            f"   {entry['address_line_1']}" if entry['address_line_1'] else "",
            f"   {entry['address_line_2']}" if entry['address_line_2'] else "",
            f"   ${entry['amount']:.2f} on {entry['date']}",
            f"   Check No. {entry['check_no']}",
            f"   Memo: {entry['memo']}" if entry['memo'] else "",
            ""  # Blank line between entries
        ])
    
    # Add total to the text report
    text_report_lines.append(f"Total Deposits: ${total:.2f}")
    
    # Remove any empty lines (like if address_line_1 was empty)
    text_report_lines = [line for line in text_report_lines if line]
    
    # Join the text report lines
    text_report = "\n".join(text_report_lines)
    
    report = {
        'entries': report_data,
        'total': total,
        'text_report': text_report,
        'report_date': current_date
    }
    
    return jsonify({
        'success': True,
        'report': report
    })

@app.route('/save', methods=['POST'])
def save_changes():
    """Save current donation data to local storage."""
    # This is a placeholder for saving to a database in a future implementation
    # Currently, data is just maintained in the session
    donations = session.get('donations', [])
    
    if request.json and 'donations' in request.json:
        session['donations'] = request.json['donations']
        return jsonify({'success': True})
    
    return jsonify({'success': False, 'message': 'No donation data provided'}), 400

@app.route('/test/qbo/customers', methods=['GET'])
def test_qbo_customers():
    """Test route to verify QuickBooks customer retrieval."""
    try:
        print("Starting QBO customer retrieval test...")
        # First check if we're authenticated
        if not qbo_service.access_token or not qbo_service.realm_id:
            print("Not authenticated with QBO")
            return jsonify({
                'success': False,
                'message': 'Not authenticated with QuickBooks. Please connect to QBO first.',
                'authenticated': False
            })
        
        # Try to get a customer count first (lightweight operation)
        query = "SELECT COUNT(*) FROM Customer"
        encoded_query = quote(query)
        url = f"{qbo_service.api_base}{qbo_service.realm_id}/query?query={encoded_query}"
        response = requests.get(url, headers=qbo_service._get_auth_headers())
        
        customer_count = 0
        if response.status_code == 200:
            data = response.json()
            if 'QueryResponse' in data and 'totalCount' in data['QueryResponse']:
                customer_count = data['QueryResponse']['totalCount']
                print(f"Found {customer_count} customers in QuickBooks")
        
        # Try to get at most 10 customers for the test
        customers = []
        query = "SELECT * FROM Customer MAXRESULTS 10"
        encoded_query = quote(query)
        url = f"{qbo_service.api_base}{qbo_service.realm_id}/query?query={encoded_query}"
        response = requests.get(url, headers=qbo_service._get_auth_headers())
        
        if response.status_code == 200:
            data = response.json()
            customers = data['QueryResponse'].get('Customer', [])
            print(f"Retrieved {len(customers)} sample customers")
        
        # Now test the get_all_customers method
        print("Testing get_all_customers method...")
        all_customers = qbo_service.get_all_customers()
        
        return jsonify({
            'success': True,
            'authenticated': True,
            'customerCount': customer_count,
            'sampleCustomersCount': len(customers),
            'sampleCustomers': [c.get('DisplayName') for c in customers[:10]],
            'allCustomersCount': len(all_customers),
            'message': f"Successfully retrieved {len(all_customers)} customers out of {customer_count} total"
        })
        
    except Exception as e:
        print(f"Error in test_qbo_customers: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f"Error testing QBO customers: {str(e)}",
            'error': str(e)
        }), 500

@app.route('/test/match', methods=['POST'])
def test_customer_matching():
    """Test route to check customer matching for a sample donation."""
    try:
        if not request.json:
            return jsonify({'success': False, 'message': 'No donation data provided'}), 400
            
        donation_data = request.json
        customer_lookup = donation_data.get('customerLookup', donation_data.get('Donor Name', ''))
        
        if not customer_lookup:
            return jsonify({
                'success': False,
                'message': 'No customer lookup value provided'
            }), 400
            
        # Perform direct QBO API lookup
        customer = qbo_service.find_customer(customer_lookup)
        
        # Check for address match if customer found
        address_match = True
        if customer and donation_data.get('Address - Line 1') and donation_data.get('Address - Line 1') != customer.get('BillAddr', {}).get('Line1', ''):
            address_match = False
        
        # Return the matching result
        if customer:
            return jsonify({
                'success': True,
                'customerFound': True,
                'addressMatch': address_match,
                'customer': customer,
                'message': 'Customer found in QBO'
            })
        else:
            return jsonify({
                'success': True,
                'customerFound': False,
                'message': 'No matching customer found in QBO'
            })
        
    except Exception as e:
        print(f"Error in test_customer_matching: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f"Error testing customer matching: {str(e)}",
            'error': str(e)
        }), 500

@app.route('/qbo/sales-receipt/preview/<donation_id>', methods=['POST'])
def preview_sales_receipt(donation_id):
    """Preview a QBO sales receipt for a donation without sending it."""
    try:
        donations = session.get('donations', [])
        donation = None
        
        # Find the donation
        for d in donations:
            if d['internalId'] == donation_id:
                donation = d
                break
        
        if not donation:
            return jsonify({'success': False, 'message': 'Donation not found'}), 404
        
        if donation['dataSource'] == 'CSV':
            return jsonify({'success': False, 'message': 'Cannot create sales receipt from CSV data'}), 400
        
        # Get the item ref from request or use default
        item_ref = '1'  # Default fallback
        if request.json and 'itemRef' in request.json:
            item_ref = request.json['itemRef']
        
        # Format dates and construct the sales receipt data
        today = pd.Timestamp.now().strftime('%Y-%m-%d')
        gift_date = donation.get('Gift Date', '')
        check_date = donation.get('Check Date', '')
        check_no = donation.get('Check No.', 'N/A')
        
        # Handle gift amount with proper parsing of currency strings
        gift_amount_str = donation.get('Gift Amount', '0')
        try:
            # If it's already a number, use it directly
            if isinstance(gift_amount_str, (int, float)):
                gift_amount = float(gift_amount_str)
            else:
                # Remove currency symbols, commas, and other formatting
                gift_amount = float(gift_amount_str.replace('$', '').replace(',', '').strip())
        except (ValueError, TypeError) as e:
            print(f"Error parsing gift amount '{gift_amount_str}': {str(e)}")
            gift_amount = 0.0  # Default to zero if parsing fails
        
        last_name = donation.get('Last Name', '')
        first_name = donation.get('First Name', '')
        memo = donation.get('Memo', '')
        
        # Format description
        description = f"{check_no}_{gift_date}_{gift_amount_str}_{last_name}_{first_name}"
        if memo:
            description += f"_{memo}"
        
        # Format receipt number
        doc_number = f"{today}_{check_no}"
        if len(doc_number) > 21:  # QB has a 21 char limit
            doc_number = doc_number[:21]
        
        # Get deposit account info from request
        deposit_account_id = request.json.get('depositToAccountId', '12000')
        
        # Construct the preview data
        preview_data = {
            'success': True,
            'salesReceiptPreview': {
                'customerName': donation.get('customerLookup', ''),
                'paymentMethod': 'Check',
                'referenceNo': check_no,
                'date': gift_date,
                'depositTo': f"{deposit_account_id} Undeposited Funds",
                'depositToAccountId': deposit_account_id,
                'serviceDate': check_date,
                'itemRef': item_ref,
                'description': description,
                'amount': gift_amount,  # Now properly parsed as float
                'message': f"auto import on {today}",
                'docNumber': doc_number
            }
        }
        
        return jsonify(preview_data)
        
    except Exception as e:
        print(f"Error previewing sales receipt: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error previewing sales receipt: {str(e)}'
        }), 500

@app.route('/qbo/environment')
def qbo_environment_info():
    """Show current QBO environment information."""
    return jsonify({
        'environment': qbo_service.environment,
        'apiBaseUrl': qbo_service.api_base,
        'authenticated': qbo_service.access_token is not None and qbo_service.realm_id is not None,
        'realmId': qbo_service.realm_id if qbo_service.realm_id else None
    })

@app.route('/qbo/items/all', methods=['GET'])
def get_all_items():
    """Get all QuickBooks items/products/services."""
    try:
        # Check if authenticated
        if not qbo_service.access_token or not qbo_service.realm_id:
            return jsonify({
                'success': False,
                'message': 'Not authenticated with QuickBooks Online'
            }), 401
        
        # Get all items
        all_items = qbo_service.get_all_items()
        
        # Prepare simplified item data for the UI
        items = []
        for item in all_items:
            # Skip inactive items
            if not item.get('Active', True):
                continue
                
            items.append({
                'id': item.get('Id'),
                'name': item.get('Name', ''),
                'description': item.get('Description', ''),
                'type': item.get('Type', ''),
                'unitPrice': item.get('UnitPrice', 0)
            })
        
        # Sort items by name for easier selection in the UI
        items.sort(key=lambda x: x['name'].lower())
        
        return jsonify({
            'success': True,
            'items': items
        })
        
    except Exception as e:
        print(f"Error fetching items: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error fetching items: {str(e)}'
        }), 500

@app.route('/qbo/item/create', methods=['POST'])
def create_item():
    """Create a new QBO product/service item."""
    try:
        # Check if authenticated
        if not qbo_service.access_token or not qbo_service.realm_id:
            return jsonify({
                'success': False,
                'message': 'Not authenticated with QuickBooks Online'
            }), 401
        
        # Get item data from request
        if not request.json:
            return jsonify({
                'success': False,
                'message': 'No item data provided'
            }), 400
        
        # Validate required fields
        item_data = request.json
        if 'name' not in item_data or not item_data['name']:
            return jsonify({
                'success': False,
                'message': 'Item name is required'
            }), 400
        
        if 'incomeAccountId' not in item_data or not item_data['incomeAccountId']:
            return jsonify({
                'success': False,
                'message': 'Income account is required'
            }), 400
        
        # Build QBO-formatted item data
        qbo_item_data = {
            'Name': item_data['name'],
            'Type': item_data.get('type', 'Service'),
            'IncomeAccountRef': {
                'value': item_data['incomeAccountId']
            },
            'Active': True
        }
        
        # Add optional fields if present
        if 'description' in item_data and item_data['description']:
            qbo_item_data['Description'] = item_data['description']
            
        if 'price' in item_data and item_data['price']:
            try:
                price = float(item_data['price'])
                qbo_item_data['UnitPrice'] = price
            except (ValueError, TypeError):
                pass  # Skip invalid price values
        
        # Create the item
        created_item = qbo_service.create_item(qbo_item_data)
        
        if created_item:
            return jsonify({
                'success': True,
                'item': {
                    'id': created_item.get('Id'),
                    'name': created_item.get('Name'),
                    'description': created_item.get('Description', ''),
                    'type': created_item.get('Type', 'Other'),
                    'price': created_item.get('UnitPrice', 0)
                }
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to create item in QBO'
            }), 500
            
    except Exception as e:
        print(f"Error creating item: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error creating item: {str(e)}'
        }), 500

@app.route('/qbo/accounts/all', methods=['GET'])
def get_all_accounts():
    """Get all QuickBooks accounts."""
    try:
        # Check if authenticated
        if not qbo_service.access_token or not qbo_service.realm_id:
            return jsonify({
                'success': False,
                'message': 'Not authenticated with QuickBooks Online'
            }), 401
        
        # Get all accounts
        all_accounts = qbo_service.get_all_accounts()
        
        # Look for Undeposited Funds account
        undeposited_funds = None
        for account in all_accounts:
            # Check if this is an Undeposited Funds account by name or account type
            if (account.get('Name', '').lower() == 'undeposited funds' or
                account.get('AccountSubType', '').lower() == 'undepositedFunds'.lower()):
                undeposited_funds = {
                    'id': account.get('Id'),
                    'name': account.get('Name', ''),
                    'type': account.get('AccountType', ''),
                    'subType': account.get('AccountSubType', '')
                }
                print(f"Found Undeposited Funds account: {undeposited_funds}")
                break
        
        # Prepare simplified account data for the UI
        accounts = []
        for account in all_accounts:
            accounts.append({
                'id': account.get('Id'),
                'name': account.get('Name', ''),
                'type': account.get('AccountType', ''),
                'subType': account.get('AccountSubType', ''),
                'number': account.get('AcctNum', ''),
                'active': account.get('Active', True)
            })
        
        return jsonify({
            'success': True,
            'accounts': accounts,
            'undepositedFunds': undeposited_funds
        })
        
    except Exception as e:
        print(f"Error fetching accounts: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error fetching accounts: {str(e)}'
        }), 500

@app.route('/qbo/account/create', methods=['POST'])
def create_account():
    """Create a new QBO account."""
    try:
        # Check if authenticated
        if not qbo_service.access_token or not qbo_service.realm_id:
            return jsonify({
                'success': False,
                'message': 'Not authenticated with QuickBooks Online'
            }), 401
        
        # Get account data from request
        if not request.json:
            return jsonify({
                'success': False,
                'message': 'No account data provided'
            }), 400
        
        # Validate required fields
        account_data = request.json
        if 'name' not in account_data or not account_data['name']:
            return jsonify({
                'success': False,
                'message': 'Account name is required'
            }), 400
        
        if 'accountType' not in account_data or not account_data['accountType']:
            return jsonify({
                'success': False,
                'message': 'Account type is required'
            }), 400
        
        # Build QBO-formatted account data
        qbo_account_data = {
            'Name': account_data['name'],
            'AccountType': account_data['accountType'],
            'Active': True
        }
        
        # Add optional fields if present
        if 'accountSubType' in account_data and account_data['accountSubType']:
            qbo_account_data['AccountSubType'] = account_data['accountSubType']
            
        if 'description' in account_data and account_data['description']:
            qbo_account_data['Description'] = account_data['description']
            
        if 'accountNumber' in account_data and account_data['accountNumber']:
            qbo_account_data['AcctNum'] = account_data['accountNumber']
        
        # Create the account
        created_account = qbo_service.create_account(qbo_account_data)
        
        if created_account:
            return jsonify({
                'success': True,
                'account': {
                    'id': created_account.get('Id'),
                    'name': created_account.get('Name'),
                    'type': created_account.get('AccountType')
                }
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to create account in QBO'
            }), 500
            
    except Exception as e:
        print(f"Error creating account: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error creating account: {str(e)}'
        }), 500

@app.route('/qbo/payment-methods/all', methods=['GET'])
def get_all_payment_methods():
    """Get all QuickBooks payment methods."""
    try:
        # Check if authenticated
        if not qbo_service.access_token or not qbo_service.realm_id:
            return jsonify({
                'success': False,
                'message': 'Not authenticated with QuickBooks Online'
            }), 401
        
        # Get all payment methods
        all_payment_methods = qbo_service.get_all_payment_methods()
        
        # Prepare simplified payment method data for the UI
        payment_methods = []
        for method in all_payment_methods:
            payment_methods.append({
                'id': method.get('Id'),
                'name': method.get('Name', ''),
                'active': method.get('Active', True)
            })
        
        return jsonify({
            'success': True,
            'paymentMethods': payment_methods
        })
        
    except Exception as e:
        print(f"Error fetching payment methods: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error fetching payment methods: {str(e)}'
        }), 500

@app.route('/qbo/payment-method/create', methods=['POST'])
def create_payment_method():
    """Create a new QBO payment method."""
    try:
        # Check if authenticated
        if not qbo_service.access_token or not qbo_service.realm_id:
            return jsonify({
                'success': False,
                'message': 'Not authenticated with QuickBooks Online'
            }), 401
        
        # Get payment method data from request
        if not request.json:
            return jsonify({
                'success': False,
                'message': 'No payment method data provided'
            }), 400
        
        # Validate required fields
        payment_method_data = request.json
        if 'name' not in payment_method_data or not payment_method_data['name']:
            return jsonify({
                'success': False,
                'message': 'Payment method name is required'
            }), 400
        
        # Build QBO-formatted payment method data
        qbo_payment_method_data = {
            'Name': payment_method_data['name'],
            'Active': True
        }
        
        # Create the payment method
        created_payment_method = qbo_service.create_payment_method(qbo_payment_method_data)
        
        if created_payment_method:
            return jsonify({
                'success': True,
                'paymentMethod': {
                    'id': created_payment_method.get('Id'),
                    'name': created_payment_method.get('Name')
                }
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to create payment method in QBO'
            }), 500
            
    except Exception as e:
        print(f"Error creating payment method: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error creating payment method: {str(e)}'
        }), 500

@app.route('/donations/clear', methods=['POST'])
def clear_donations():
    """Clear all donations from the session."""
    session['donations'] = []
    return jsonify({'success': True, 'message': 'All donations cleared from session'})

@app.route('/donations/debug', methods=['GET'])
def debug_donations():
    """Debug endpoint to see donation keys and deduplication info."""
    donations = session.get('donations', [])
    
    debug_info = {
        'total_count': len(donations),
        'donations_by_key': {}
    }
    
    # Group donations by their unique keys
    for donation in donations:
        check_no = normalize_check_number(donation.get('Check No.', ''))
        amount = normalize_amount(donation.get('Gift Amount', ''))
        
        if check_no and amount:
            unique_key = f"CHECK_{check_no}_{amount}"
        else:
            donor_name = normalize_donor_name(donation.get('Donor Name', ''))
            gift_date = normalize_date(donation.get('Gift Date', ''))
            unique_key = f"OTHER_{donor_name}_{amount}_{gift_date}"
        
        if unique_key not in debug_info['donations_by_key']:
            debug_info['donations_by_key'][unique_key] = []
        
        debug_info['donations_by_key'][unique_key].append({
            'internalId': donation.get('internalId'),
            'donor': donation.get('Donor Name'),
            'checkNo': donation.get('Check No.'),
            'amount': donation.get('Gift Amount'),
            'date': donation.get('Gift Date'),
            'isMerged': donation.get('isMerged', False),
            'dataSource': donation.get('dataSource')
        })
    
    # Find any duplicate keys (should not exist)
    duplicates = {k: v for k, v in debug_info['donations_by_key'].items() if len(v) > 1}
    debug_info['duplicate_keys'] = duplicates
    debug_info['duplicate_count'] = sum(len(v) - 1 for v in duplicates.values())
    
    return jsonify(debug_info)

if __name__ == '__main__':
    # Display the environment when starting
    print(f"====== Starting with QuickBooks Online {qbo_environment.upper()} environment ======")
    print(f"API Base URL: {qbo_service.api_base}")
    print(f"To change environments, restart with: python src/app.py --env [sandbox|production]")
    print("================================================================")
    
    app.run(debug=True)
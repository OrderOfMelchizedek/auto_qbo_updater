import os
import json
import requests
import argparse
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from werkzeug.utils import secure_filename
import pandas as pd
from dotenv import load_dotenv
from urllib.parse import quote

from utils.gemini_service import GeminiService
from utils.qbo_service import QBOService
from utils.file_processor import FileProcessor

# Load environment variables
load_dotenv()

# Parse command line arguments for QBO environment
parser = argparse.ArgumentParser(description="FOM to QBO Automation App")
parser.add_argument('--env', type=str, choices=['sandbox', 'production'], default=os.getenv('QBO_ENVIRONMENT', 'sandbox'),
                    help='QuickBooks Online environment (sandbox or production)')
args, _ = parser.parse_known_args()

# Use the command-line specified environment
qbo_environment = args.env
print(f"Starting application with QBO environment: {qbo_environment}")

app = Flask(__name__)
app.secret_key = os.urandom(24)  # For session management
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB upload limit

# Create necessary directories
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize services
gemini_service = GeminiService(api_key=os.getenv('GEMINI_API_KEY'))
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
        
        # Store donations in session for later use
        if 'donations' not in session:
            session['donations'] = []
        
        session['donations'].extend(donations)
        
        # Return appropriate response based on success/errors
        if donations:
            return jsonify({
                'success': True,
                'donations': donations,
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
        print(f"Unexpected error in upload processing: {str(e)}")
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
            
            # Prepare sales receipt data
            sales_receipt_data = {
                'CustomerRef': {
                    'value': donation['qboCustomerId']
                },
                'TxnDate': donation.get('Gift Date', donation.get('Check Date', '')),
                'Line': [
                    {
                        'Amount': float(donation.get('Gift Amount', 0)),
                        'DetailType': 'SalesItemLineDetail',
                        'SalesItemLineDetail': {
                            'ItemRef': {
                                'value': '1'  # Default item ID, should be configured
                            }
                        },
                        'Description': donation.get('Memo', '')
                    }
                ],
                'PrivateNote': f"Check No: {donation.get('Check No.', 'N/A')}"
            }
            
            result = qbo_service.create_sales_receipt(sales_receipt_data)
            
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
    
    for i, donation in enumerate(donations):
        # Skip CSV donations and already sent donations
        if donation['dataSource'] == 'CSV' or donation['qbSyncStatus'] == 'Sent':
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
                    continue
            else:
                results.append({
                    'internalId': donation['internalId'],
                    'success': False,
                    'message': 'Customer lookup field is empty'
                })
                continue
        
        # Prepare sales receipt data
        sales_receipt_data = {
            'CustomerRef': {
                'value': donation['qboCustomerId']
            },
            'TxnDate': donation.get('Gift Date', donation.get('Check Date', '')),
            'Line': [
                {
                    'Amount': float(donation.get('Gift Amount', 0)),
                    'DetailType': 'SalesItemLineDetail',
                    'SalesItemLineDetail': {
                        'ItemRef': {
                            'value': '1'  # Default item ID, should be configured
                        }
                    },
                    'Description': donation.get('Memo', '')
                }
            ],
            'PrivateNote': f"Check No: {donation.get('Check No.', 'N/A')}"
        }
        
        result = qbo_service.create_sales_receipt(sales_receipt_data)
        
        if result and 'Id' in result:
            donation['qbSyncStatus'] = 'Sent'
            donation['qboSalesReceiptId'] = result['Id']
            donations[i] = donation
            
            results.append({
                'internalId': donation['internalId'],
                'success': True,
                'salesReceiptId': result['Id']
            })
        else:
            donation['qbSyncStatus'] = 'Error'
            donations[i] = donation
            
            results.append({
                'internalId': donation['internalId'],
                'success': False,
                'message': 'Failed to create sales receipt in QBO'
            })
    
    session['donations'] = donations
    
    return jsonify({
        'success': True,
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

@app.route('/qbo/environment')
def qbo_environment_info():
    """Show current QBO environment information."""
    return jsonify({
        'environment': qbo_service.environment,
        'apiBaseUrl': qbo_service.api_base,
        'authenticated': qbo_service.access_token is not None and qbo_service.realm_id is not None,
        'realmId': qbo_service.realm_id if qbo_service.realm_id else None
    })

if __name__ == '__main__':
    # Display the environment when starting
    print(f"====== Starting with QuickBooks Online {qbo_environment.upper()} environment ======")
    print(f"API Base URL: {qbo_service.api_base}")
    print(f"To change environments, restart with: python src/app.py --env [sandbox|production]")
    print("================================================================")
    
    app.run(debug=True)
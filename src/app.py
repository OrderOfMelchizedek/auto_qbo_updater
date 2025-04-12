import os
import json
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from werkzeug.utils import secure_filename
import pandas as pd
from dotenv import load_dotenv

from utils.gemini_service import GeminiService
from utils.qbo_service import QBOService
from utils.csv_parser import CSVParser
from utils.file_processor import FileProcessor

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.urandom(24)  # For session management
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB upload limit

# Create necessary directories
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize services
gemini_service = GeminiService(api_key=os.getenv('GEMINI_API_KEY'))
qbo_service = QBOService(
    client_id=os.getenv('QBO_CLIENT_ID'),
    client_secret=os.getenv('QBO_CLIENT_SECRET'),
    redirect_uri=os.getenv('QBO_REDIRECT_URI'),
    environment=os.getenv('QBO_ENVIRONMENT')
)
csv_parser = CSVParser()
file_processor = FileProcessor(gemini_service)

# Routes
@app.route('/')
def index():
    """Render the main application page."""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_files():
    """Handle file uploads (images, PDFs, CSV)."""
    if 'files' not in request.files:
        flash('No files selected', 'error')
        return redirect(url_for('index'))
    
    files = request.files.getlist('files')
    
    # Placeholder for extracted donation data
    donations = []
    
    for file in files:
        if file.filename == '':
            continue
        
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        # Process different file types
        file_ext = os.path.splitext(filename)[1].lower()
        
        if file_ext in ['.csv']:
            csv_donations = csv_parser.parse(file_path)
            for donation in csv_donations:
                donation['dataSource'] = 'CSV'
                donation['internalId'] = f"csv_{len(donations)}"
                donation['qbSyncStatus'] = 'Pending'
                donation['qbCustomerStatus'] = 'Unknown'
                donations.append(donation)
        elif file_ext in ['.jpg', '.jpeg', '.png', '.pdf']:
            # Process images and PDFs using Gemini
            extracted_donation = file_processor.process(file_path, file_ext)
            if extracted_donation:
                extracted_donation['dataSource'] = 'LLM'
                extracted_donation['internalId'] = f"llm_{len(donations)}"
                extracted_donation['qbSyncStatus'] = 'Pending'
                extracted_donation['qbCustomerStatus'] = 'Unknown'
                donations.append(extracted_donation)
        
        # Store file temporarily
        # In a production environment, consider more robust file storage
    
    # Store donations in session for later use
    if 'donations' not in session:
        session['donations'] = []
    
    session['donations'].extend(donations)
    
    return jsonify({
        'success': True,
        'donations': donations
    })

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
        flash('Successfully connected to QuickBooks Online', 'success')
    else:
        flash('Failed to connect to QuickBooks Online', 'error')
    
    return redirect(url_for('index'))

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
    
    # Convert donations to DataFrame for easier manipulation
    df = pd.DataFrame(donations)
    
    # Format report similar to the provided examples
    report_data = []
    
    for i, donation in enumerate(donations):
        donor_name = donation.get('Donor Name', 'Unknown Donor')
        address = donation.get('Address - Line 1', '')
        city = donation.get('City', '')
        state = donation.get('State', '')
        zipcode = donation.get('ZIP', '')
        address_line = f"{address}, {city}, {state} {zipcode}" if all([address, city, state, zipcode]) else ''
        
        amount = donation.get('Gift Amount', '0')
        if isinstance(amount, str):
            try:
                amount = float(amount.replace('$', '').replace(',', ''))
            except ValueError:
                amount = 0
        
        gift_date = donation.get('Gift Date', donation.get('Check Date', ''))
        check_no = donation.get('Check No.', '')
        if not check_no and donation.get('dataSource') == 'CSV':
            check_no = 'Online Donation'
        
        memo = donation.get('Memo', '')
        
        report_entry = {
            'index': i + 1,
            'donor_name': donor_name,
            'address': address_line,
            'amount': amount,
            'date': gift_date,
            'check_no': check_no,
            'memo': memo
        }
        
        report_data.append(report_entry)
    
    # Calculate total
    total = sum(entry['amount'] for entry in report_data)
    
    report = {
        'entries': report_data,
        'total': total
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

if __name__ == '__main__':
    app.run(debug=True)
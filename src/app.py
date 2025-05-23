import os
import json
import requests
import argparse
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from werkzeug.utils import secure_filename
import pandas as pd # pandas is used for pd.Timestamp
from dotenv import load_dotenv
from urllib.parse import quote
import re # For normalization
import time # For QBOService token expiry, though QBOService is not modified here

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

# Define model aliases
MODEL_MAPPING = {
    'gemini-flash': 'gemini-2.5-flash-preview-04-17',
    'gemini-pro': 'gemini-2.5-pro-preview-03-25',
    'gemini-2.5-flash-preview-04-17': 'gemini-2.5-flash-preview-04-17',
    'gemini-2.5-pro-preview-03-25': 'gemini-2.5-pro-preview-03-25'
}

gemini_env_model = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash-preview-04-17')
resolved_env_model = MODEL_MAPPING.get(gemini_env_model, gemini_env_model)

cli_parser = argparse.ArgumentParser(description="FOM to QBO Automation App CLI Args")
cli_parser.add_argument('--env', type=str, choices=['sandbox', 'production'],
                    default=os.getenv('QBO_ENVIRONMENT', 'sandbox'),
                    help='QuickBooks Online environment (sandbox or production)')
cli_parser.add_argument('--model', type=str, default=resolved_env_model,
                    choices=list(MODEL_MAPPING.keys()), # Use keys for choices
                    help='Gemini model to use')

if __name__ == '__main__':
    args, _ = cli_parser.parse_known_args()
else:
    args = cli_parser.parse_args([])

qbo_environment_for_services = args.env
gemini_model_name_for_services = MODEL_MAPPING.get(args.model, args.model) # Resolve alias

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', os.urandom(24))
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

gemini_service = GeminiService(
    api_key=os.getenv('GEMINI_API_KEY'),
    model_name=gemini_model_name_for_services
)
# IMPORTANT: For QBOService to work correctly across reloads,
# it needs to be modified to use flask.session for token storage.
# The following instantiation is as before, but its internal state for tokens
# will be unreliable with dev server reloads without session persistence.
qbo_service = QBOService(
    client_id=os.getenv('QBO_CLIENT_ID'),
    client_secret=os.getenv('QBO_CLIENT_SECRET'),
    redirect_uri=os.getenv('QBO_REDIRECT_URI'),
    environment=qbo_environment_for_services
)
file_processor = FileProcessor(gemini_service, qbo_service)

# --- Deduplication Logic Helper Functions ---
def _normalize_text_for_key(text):
    if isinstance(text, (int, float)): text = str(text)
    if not text or not isinstance(text, str): return ""
    text = text.lower().strip()
    # More aggressive cleaning for check numbers if they contain unexpected chars
    # For general text, simple lower and strip is often enough if source is consistent.
    # Check numbers might have noise, so be more specific if needed:
    # if for_check_no: text = re.sub(r'[^a-z0-9\-]', '', text) # Keep only alphanum and hyphen for check_no
    return text

def _normalize_amount_for_key(amount_str):
    if amount_str is None: return None
    try:
        cleaned_amount = str(amount_str).replace('$', '').replace(',', '').strip()
        return float(cleaned_amount)
    except ValueError: return None

def _generate_donation_key(donation):
    check_no_raw = donation.get('Check No.')
    amount_val = _normalize_amount_for_key(donation.get('Gift Amount'))
    gift_date_str = str(donation.get('Gift Date', ''))

    check_no_norm = _normalize_text_for_key(check_no_raw)

    if amount_val is None:
        print(f"Warning: Could not generate a valid key for donation (missing amount): CheckNo='{check_no_raw}', Amount='{donation.get('Gift Amount')}'")
        # Create a unique key for items that can't be properly keyed to avoid losing them,
        # but they won't deduplicate unless this happens for "both" versions.
        return f"unkeyable_{donation.get('Donor Name', '')}_{pd.Timestamp.now().timestamp()}_{id(donation)}"

    # If Check No. is present and not a typical placeholder for online donations
    if check_no_norm and check_no_norm not in ["n/a", "online donation", ""]:
        # Key primarily on Check No. and Amount for check-based donations
        # Adding a prefix to distinguish from date-keyed entries if amounts are same
        return f"CHK_{check_no_norm}|AMT_{amount_val:.2f}"
    else:
        # For online donations or those without a check number, use Gift Date and Amount
        gift_date_norm = ""
        if gift_date_str:
            try:
                parsed_date = pd.to_datetime(gift_date_str, errors='coerce')
                if pd.notna(parsed_date): gift_date_norm = parsed_date.strftime('%Y-%m-%d')
                else: gift_date_norm = _normalize_text_for_key(gift_date_str.split(' ')[0]) # Basic fallback
            except: gift_date_norm = _normalize_text_for_key(gift_date_str.split(' ')[0]) # Broader fallback

        if not gift_date_norm: # If gift date is also missing or unparsable for an "online" type
             print(f"Warning: Missing Gift Date for non-check donation with Amount='{amount_val}'. Key will be less unique.")
             return f"NODATE_AMT_{amount_val:.2f}|DONOR_{_normalize_text_for_key(donation.get('Donor Name'))}" # Less unique key

        return f"DATE_{gift_date_norm}|AMT_{amount_val:.2f}"


SOURCE_PRIORITY = {'PDF': 3, 'JPG': 2, 'CSV': 1}

def _is_value_meaningful(value):
    if value is None: return False
    val_str = str(value).strip().lower()
    return not (not val_str or val_str in ["unknown", "n/a", "none", "unknown address", "unknown city", "un", "00000", "null"])

def _merge_donations(existing_donation, new_donation):
    merged = existing_donation.copy()
    existing_source_priority = SOURCE_PRIORITY.get(existing_donation.get('_source_file_type', '').upper(), 0)
    new_source_priority = SOURCE_PRIORITY.get(new_donation.get('_source_file_type', '').upper(), 0)

    # Fields where we prefer data from the higher priority source if its value is meaningful
    # or if the existing value is not meaningful.
    fields_to_merge = [
        'Salutation', 'Donor Name', 'Memo', 'First Name', 'Last Name', 'Full Name',
        'Organization Name', 'Address - Line 1', 'City', 'State', 'ZIP',
        'customerLookup', # This will be updated by QBO matching later anyway if possible
        'Check Date', 'Gift Date', 'Deposit Date', 'Deposit Method' # Dates and methods might be more accurate from PDF
    ]
    # Critical fields like Amount and Check No are part of the key, so they should match.
    # If they don't, it's a different key.

    for key in fields_to_merge:
        new_value = new_donation.get(key)
        existing_value = merged.get(key) # Use merged's current value for existing

        new_is_meaningful = _is_value_meaningful(new_value)
        existing_is_meaningful = _is_value_meaningful(existing_value)

        if new_is_meaningful and not existing_is_meaningful:
            merged[key] = new_value
        elif new_is_meaningful and existing_is_meaningful:
            if new_source_priority > existing_source_priority:
                merged[key] = new_value
            # If priorities are equal or new is lower, but both are meaningful,
            # we could prefer the longer string for text fields, or just keep existing.
            # For now, if new_source_priority is not greater, we keep existing meaningful value.
            elif new_source_priority == existing_source_priority and isinstance(new_value, str) and isinstance(existing_value, str):
                if len(new_value) > len(existing_value): # Simple heuristic: longer is better for text
                    merged[key] = new_value

    if new_source_priority > existing_source_priority:
        merged['_source_file_type'] = new_donation.get('_source_file_type')
    
    # Ensure Gift Amount and Check No are from the highest priority source if they happen to be in fields_to_merge
    # (though they are primarily key components)
    if new_source_priority > existing_source_priority:
        if _is_value_meaningful(new_donation.get('Gift Amount')):
            merged['Gift Amount'] = new_donation.get('Gift Amount')
        if _is_value_meaningful(new_donation.get('Check No.')):
             merged['Check No.'] = new_donation.get('Check No.')


    return merged

def deduplicate_and_merge_donations(donation_list_with_source):
    if not donation_list_with_source: return []
    final_donations_map = {}
    print(f"Starting deduplication for {len(donation_list_with_source)} extracted items.")
    for current_donation in donation_list_with_source:
        if not isinstance(current_donation, dict):
            print(f"Warning: Skipping non-dictionary item: {current_donation}")
            continue
        key = _generate_donation_key(current_donation)
        
        if key.startswith("unkeyable_") or key.startswith("NODATE_AMT_"): # Treat these as unique for now
            unique_placeholder_key = f"{key}_{id(current_donation)}" # Ensure truly unique map key
            print(f"  Adding unkeyable/problematic donation as unique with key '{unique_placeholder_key}': {current_donation.get('Donor Name')}")
            final_donations_map[unique_placeholder_key] = current_donation
            continue

        if key not in final_donations_map:
            final_donations_map[key] = current_donation
            print(f"  Added new donation with key '{key}' from source '{current_donation.get('_source_file_type')}': {current_donation.get('Donor Name')}")
        else:
            existing_donation = final_donations_map[key]
            print(f"  Duplicate key '{key}' found. Existing: '{existing_donation.get('Donor Name')}' (src: {existing_donation.get('_source_file_type')}), New: '{current_donation.get('Donor Name')}' (src: {current_donation.get('_source_file_type')}): Merging...")
            merged_donation = _merge_donations(existing_donation, current_donation)
            final_donations_map[key] = merged_donation
            print(f"    Merged result for key '{key}', final Donor Name: '{merged_donation.get('Donor Name')}', final source: '{merged_donation.get('_source_file_type')}'")
    final_list = list(final_donations_map.values())
    print(f"Deduplication complete. {len(final_list)} unique donations remaining.")
    return final_list
# --- End of Deduplication ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_files():
    try:
        # This check should ideally use a qbo_service method that itself checks session-persisted tokens
        qbo_is_effectively_authed = qbo_service.access_token is not None and qbo_service.realm_id is not None
        # For a more robust check after implementing session tokens in QBOService:
        # qbo_service._ensure_tokens_loaded() # Try to load from session
        # qbo_is_effectively_authed = qbo_service.access_token is not None and qbo_service.realm_id is not None


        if not qbo_is_effectively_authed:
            # This warning relies on the qbo_service instance state.
            # If QBOService uses sessions, this warning will be accurate for the current session.
            print("Warning: QBO not authenticated. Customer matching will be limited/skipped during this upload.")

        if 'files' not in request.files:
            return jsonify({'success': False, 'message': 'No files part in the request'}), 400
        
        files = request.files.getlist('files')
        if not files or all(f.filename == '' for f in files): # Corrected variable name
            return jsonify({'success': False, 'message': 'No files were selected'}), 400

        print(f"Received {len(files)} files for processing in this request:")
        for f_obj in files: # Corrected variable name
            if f_obj.filename: print(f"- {f_obj.filename}")

        all_extracted_donations_from_files = []
        errors = []
        
        for file_idx, file_obj_loop in enumerate(files): # Corrected variable name
            if file_obj_loop.filename == '': continue
            
            print(f"\nProcessing file {file_idx + 1}/{len(files)}: {file_obj_loop.filename}")
            filename = secure_filename(file_obj_loop.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file_obj_loop.save(file_path)
            file_ext = os.path.splitext(filename)[1].lower()

            source_type = "CSV" if file_ext == '.csv' else \
                          "PDF" if file_ext == '.pdf' else \
                          "JPG" if file_ext in ['.jpg', '.jpeg', '.png'] else \
                          "Unknown"

            if source_type != "Unknown":
                # file_processor.process will handle its own QBO auth checks internally
                processed_data_from_file = file_processor.process(file_path, file_ext)
                
                if processed_data_from_file:
                    current_file_items = processed_data_from_file if isinstance(processed_data_from_file, list) else [processed_data_from_file]
                    
                    for item in current_file_items:
                        if isinstance(item, dict):
                           item['_source_file_type'] = source_type
                        else:
                            print(f"Warning: Non-dict item found: {item} from {filename}")
                            continue 
                    all_extracted_donations_from_files.extend(current_file_items)
                    print(f"  Extracted {len(current_file_items)} potential items from {filename}.")
                else:
                    msg = f"No donation data extracted from {filename} by file_processor."
                    print(f"  {msg}")
                    errors.append(msg)
            else:
                msg = f"Unsupported file type: {file_ext} for file {filename}"
                print(f"  {msg}")
                errors.append(msg)
        
        if not all_extracted_donations_from_files:
            print("No data extracted from any files after initial processing.")
        
        final_donations_for_session = deduplicate_and_merge_donations(all_extracted_donations_from_files)
        
        # For this upload, we replace the session donations with the current batch.
        # If you wanted to append to an ongoing list, you'd load from session first.
        session['donations'] = [] 
        next_internal_id_start = 0 

        finalized_new_donations = []
        for idx, donation_dict in enumerate(final_donations_for_session):
            if isinstance(donation_dict, dict): 
                donation_dict['internalId'] = f"id_{next_internal_id_start + idx}"
                donation_dict['qbSyncStatus'] = donation_dict.get('qbSyncStatus', 'Pending')
                if 'qbCustomerStatus' not in donation_dict: # Avoid overwriting status from file_processor's matching
                    donation_dict['qbCustomerStatus'] = 'Unknown'
                donation_dict.pop('_source_file_type', None) 
                finalized_new_donations.append(donation_dict)
            else:
                print(f"Warning: Item in final_donations_for_session is not a dict: {donation_dict}")
        
        session['donations'] = finalized_new_donations
        session.modified = True

        if finalized_new_donations:
            return jsonify({
                'success': True,
                'donations': finalized_new_donations,
                'message': f"Successfully processed. Displaying {len(finalized_new_donations)} unique entries.",
                'warnings': errors if errors else None,
                'qboAuthenticated': qbo_is_effectively_authed # Report auth state at START of upload
            })
        elif errors:
             return jsonify({
                'success': False,
                'message': "No valid donation data extracted. " + ", ".join(errors),
                'qboAuthenticated': qbo_is_effectively_authed
            }), 400
        else:
            return jsonify({
                'success': True,
                'donations': [],
                'message': "No new donation data was found in the uploaded files.",
                'qboAuthenticated': qbo_is_effectively_authed
            })

    except Exception as e:
        print(f"Unexpected error in upload processing: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'An unexpected server error occurred: {str(e)}'}), 500

# --- Other routes remain mostly the same ---
# (Make sure to include all of them from your previous app.py if replacing the whole file)

@app.route('/donations', methods=['GET'])
def get_donations():
    donations = session.get('donations', [])
    return jsonify(donations)

@app.route('/donations/<donation_id>', methods=['PUT'])
def update_donation(donation_id):
    donations_in_session = session.get('donations', [])
    donation_data_from_request = request.json
    updated = False
    for i, donation_in_s in enumerate(donations_in_session):
        if donation_in_s.get('internalId') == donation_id:
            donations_in_session[i] = donation_data_from_request
            session['donations'] = donations_in_session
            session.modified = True
            updated = True
            break
    if updated: return jsonify({'success': True, 'message': f'Donation {donation_id} updated.'})
    else: return jsonify({'success': False, 'message': f'Donation {donation_id} not found.'}), 404

@app.route('/donations/remove-invalid', methods=['POST'])
def remove_invalid_donations():
    donations_in_session = session.get('donations', [])
    if not request.json or 'invalidIds' not in request.json:
        return jsonify({'success': False, 'message': 'No invalid IDs provided'}), 400
    invalid_ids_to_remove = request.json['invalidIds']
    if not invalid_ids_to_remove or not isinstance(invalid_ids_to_remove, list):
        return jsonify({'success': False, 'message': 'Invalid IDs must be a non-empty list'}), 400
    initial_count = len(donations_in_session)
    valid_donations_after_removal = [d for d in donations_in_session if d.get('internalId') not in invalid_ids_to_remove]
    removed_count = initial_count - len(valid_donations_after_removal)
    session['donations'] = valid_donations_after_removal
    session.modified = True
    print(f"Removed {removed_count} invalid donations from session based on IDs: {invalid_ids_to_remove}")
    return jsonify({'success': True, 'removedCount': removed_count})

@app.route('/qbo/status')
def qbo_status():
    # This should ideally trigger _ensure_tokens_loaded() in qbo_service if it were session-aware
    # For now, it reflects the global qbo_service instance's state.
    # qbo_service._ensure_tokens_loaded() # If QBOService is modified for sessions
    is_authed = qbo_service.access_token is not None and qbo_service.realm_id is not None
    return jsonify({
        'authenticated': is_authed,
        'realmId': qbo_service.realm_id if is_authed else None,
        'tokenExpiry': qbo_service.token_expires_at if is_authed else None,
        'environment': qbo_service.environment
    })

@app.route('/qbo/authorize')
def authorize_qbo():
    authorization_url = qbo_service.get_authorization_url()
    return redirect(authorization_url)

@app.route('/qbo/callback')
def qbo_callback():
    code = request.args.get('code')
    realmId = request.args.get('realmId') # Ensure realmId is consistently cased
    state = request.args.get('state')

    if code and realmId:
        # Assuming get_tokens in qbo_service is modified to save to flask.session
        if qbo_service.get_tokens(code, realmId): # Pass realmId here
            session['qbo_just_connected'] = True
            flash('Successfully connected to QuickBooks Online.', 'success')
            # Optionally pre-fetch some data if needed immediately after auth
            # try:
            #     qbo_service.get_all_customers() # Example
            # except Exception as e:
            #     flash(f'Error fetching initial QBO data: {str(e)}', 'warning')
        else:
            flash('Failed to obtain tokens from QuickBooks Online. Please try again.', 'error')
    else:
        flash('QuickBooks Online connection failed (missing code or realmId). Please try again.', 'error')
    
    # Script to notify opener window (app.js) and close popup
    return """
    <!DOCTYPE html><html><head><title>QBO Auth</title></head><body>
    <script type="text/javascript">
        if (window.opener && window.opener.checkQBOAuthStatus) {
            window.opener.checkQBOAuthStatus();
        }
        window.close();
    </script>
    Processing QBO login... You can close this window.
    </body></html>
    """

@app.route('/qbo/environment')
def qbo_environment_info():
    # qbo_service._ensure_tokens_loaded() # If QBOService is modified for sessions
    is_authed = qbo_service.access_token is not None and qbo_service.realm_id is not None
    return jsonify({
        'environment': qbo_service.environment,
        'apiBaseUrl': qbo_service.api_base,
        'authenticated': is_authed,
        'realmId': qbo_service.realm_id if is_authed else None
    })

@app.route('/save', methods=['POST'])
def save_changes():
    if request.json and 'donations' in request.json:
        session['donations'] = request.json['donations']
        session.modified = True
        return jsonify({'success': True, 'message': 'Donation data saved to session.'})
    return jsonify({'success': False, 'message': 'No donation data provided'}), 400

# --- Stubs for other QBO routes - ENSURE YOU MERGE YOUR FULL IMPLEMENTATIONS ---
@app.route('/qbo/customer/<donation_id>', methods=['GET'])
def find_qbo_customer_route(donation_id): # Renamed to avoid conflict with function name
    # This route needs to be fully implemented as in your original file
    # It should use session-aware qbo_service
    return jsonify({'success': False, 'message': 'find_customer route not fully implemented in this snippet'})

@app.route('/qbo/customers/all', methods=['GET'])
def get_all_qbo_customers_route(): # Renamed
    return jsonify({'success': False, 'message': 'get_all_customers route not fully implemented in this snippet'})

@app.route('/qbo/customer/manual-match/<donation_id>', methods=['POST'])
def manual_match_qbo_customer_route(donation_id): # Renamed
    return jsonify({'success': False, 'message': 'manual_match_customer route not fully implemented in this snippet'})

@app.route('/qbo/customer/create/<donation_id>', methods=['POST'])
def create_qbo_customer_route(donation_id): # Renamed
    return jsonify({'success': False, 'message': 'create_customer route not fully implemented in this snippet'})

@app.route('/qbo/customer/update/<donation_id>', methods=['PUT'])
def update_qbo_customer_route(donation_id): # Renamed
    return jsonify({'success': False, 'message': 'update_customer route not fully implemented in this snippet'})

@app.route('/qbo/sales-receipt/preview/<donation_id>', methods=['POST'])
def preview_qbo_sales_receipt_route(donation_id): # Renamed
    return jsonify({'success': False, 'message': 'preview_sales_receipt route not fully implemented in this snippet'})

@app.route('/qbo/sales-receipt/<donation_id>', methods=['POST'])
def create_qbo_sales_receipt_route(donation_id): # Renamed
    return jsonify({'success': False, 'message': 'create_sales_receipt route not fully implemented in this snippet'})

@app.route('/qbo/sales-receipt/batch', methods=['POST'])
def create_batch_qbo_sales_receipts_route(): # Renamed
    return jsonify({'success': False, 'message': 'create_batch_sales_receipts route not fully implemented in this snippet'})

@app.route('/report/generate', methods=['GET'])
def generate_qbo_report_route(): # Renamed
    return jsonify({'success': False, 'message': 'generate_report route not fully implemented in this snippet'})

@app.route('/qbo/items/all', methods=['GET'])
def get_all_qbo_items_route(): # Renamed
    return jsonify({'success': False, 'message': 'get_all_items route not fully implemented in this snippet'})

@app.route('/qbo/item/create', methods=['POST'])
def create_qbo_item_route(): # Renamed
    return jsonify({'success': False, 'message': 'create_item route not fully implemented in this snippet'})

@app.route('/qbo/accounts/all', methods=['GET'])
def get_all_qbo_accounts_route(): # Renamed
    return jsonify({'success': False, 'message': 'get_all_accounts route not fully implemented in this snippet'})

@app.route('/qbo/account/create', methods=['POST'])
def create_qbo_account_route(): # Renamed
    return jsonify({'success': False, 'message': 'create_account route not fully implemented in this snippet'})

@app.route('/qbo/payment-methods/all', methods=['GET'])
def get_all_qbo_payment_methods_route(): # Renamed
    return jsonify({'success': False, 'message': 'get_all_payment_methods route not fully implemented in this snippet'})

@app.route('/qbo/payment-method/create', methods=['POST'])
def create_qbo_payment_method_route(): # Renamed
    return jsonify({'success': False, 'message': 'create_payment_method route not fully implemented in this snippet'})


if __name__ == '__main__':
    print(f"====== Starting Flask App (app.py) with QBO Env: {qbo_environment_for_services.upper()} ======")
    print(f"API Base URL: {qbo_service.api_base}")
    print(f"Using Gemini model: {gemini_model_name_for_services}")
    print("================================================================")
    # IMPORTANT: For development, use_reloader=False can help stabilize auth state
    # if session-based token management in QBOService isn't fully implemented yet.
    # However, the session-based approach is the robust long-term solution.
    app.run(debug=True, host='0.0.0.0', port=int(os.getenv('PORT', 5000)) #, use_reloader=False # Temporary for auth testing
           )
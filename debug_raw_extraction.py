#!/usr/bin/env python3
"""Show raw extraction results before deduplication and matching"""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

# Set up environment
from dotenv import load_dotenv

load_dotenv()

from src.utils.gemini_adapter_v2 import GeminiAdapterV2

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("No API key found")
    exit(1)

# Create adapter
adapter = GeminiAdapterV2(api_key)

# Process files and show raw extraction
files = [
    ("tests/e2e/dummy files/2025-05-17-12-48-17.pdf", "PDF"),
    ("tests/e2e/dummy files/2025-05-17 12.50.27-1.jpg", "JPG"),
]

all_extractions = []

for file_path, file_type in files:
    print(f"\n{'='*80}")
    print(f"EXTRACTING FROM: {file_path}")
    print(f"{'='*80}\n")

    try:
        payments = adapter.extract_payments(file_path)

        # Convert PaymentRecord objects to dict for JSON display
        payments_dict = []
        for p in payments:
            payment_dict = {
                "payment_info": {
                    "payment_method": p.payment_info.payment_method,
                    "check_no": p.payment_info.check_no,
                    "payment_ref": p.payment_info.payment_ref,
                    "amount": p.payment_info.amount,
                    "payment_date": p.payment_info.payment_date,
                    "check_date": p.payment_info.check_date,
                    "deposit_date": p.payment_info.deposit_date,
                    "postmark_date": p.payment_info.postmark_date,
                    "deposit_method": p.payment_info.deposit_method,
                    "memo": p.payment_info.memo,
                },
                "payer_info": {
                    "aliases": p.payer_info.aliases,
                    "salutation": p.payer_info.salutation,
                    "organization_name": p.payer_info.organization_name,
                },
                "contact_info": {
                    "address_line_1": p.contact_info.address_line_1,
                    "city": p.contact_info.city,
                    "state": p.contact_info.state,
                    "zip": p.contact_info.zip,
                    "email": p.contact_info.email,
                    "phone": p.contact_info.phone,
                },
            }
            payments_dict.append(payment_dict)
            all_extractions.append((file_type, payment_dict))

        print(json.dumps(payments_dict, indent=2))
        print(f"\nExtracted {len(payments)} payments from {file_type}")

    except Exception as e:
        print(f"Error: {e}")

# Show specific payment we're interested in
print(f"\n{'='*80}")
print("LOOKING FOR PAYMENT WITH REF/CHECK 0003517031:")
print(f"{'='*80}\n")

found = False
for source, payment in all_extractions:
    check = payment["payment_info"].get("check_no", "")
    ref = payment["payment_info"].get("payment_ref", "")

    if "3517031" in str(check) or "3517031" in str(ref):
        found = True
        print(f"Found in {source}:")
        print(json.dumps(payment, indent=2))

if not found:
    print("Not found in raw extractions")

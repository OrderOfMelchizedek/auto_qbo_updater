#!/usr/bin/env python3
"""Show raw extraction results clearly"""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from dotenv import load_dotenv

load_dotenv()

from src.utils.gemini_adapter_v2 import GeminiAdapterV2

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("No API key found")
    exit(1)

adapter = GeminiAdapterV2(api_key)

# First, extract from PDF
print("=" * 80)
print("PDF EXTRACTION (tests/e2e/dummy files/2025-05-17-12-48-17.pdf)")
print("=" * 80)

pdf_payments = adapter.extract_payments("tests/e2e/dummy files/2025-05-17-12-48-17.pdf")
pdf_data = []

for p in pdf_payments:
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
    pdf_data.append(payment_dict)

print(json.dumps(pdf_data, indent=2))

# Then extract from JPG
print("\n\n" + "=" * 80)
print("JPG EXTRACTION (tests/e2e/dummy files/2025-05-17 12.50.27-1.jpg)")
print("=" * 80)

jpg_payments = adapter.extract_payments("tests/e2e/dummy files/2025-05-17 12.50.27-1.jpg")
jpg_data = []

for p in jpg_payments:
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
    jpg_data.append(payment_dict)

print(json.dumps(jpg_data, indent=2))

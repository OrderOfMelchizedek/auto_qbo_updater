#!/usr/bin/env python3
"""Debug how Jo Fintel got matched to check 3517031"""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from dotenv import load_dotenv

load_dotenv()

from src.utils.gemini_adapter_v3 import GeminiAdapterV3

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("No API key found")
    exit(1)

# Extract with V3 to see raw data
adapter = GeminiAdapterV3(api_key)

print("=" * 80)
print("V3 RAW EXTRACTION - Looking for check numbers containing '3517'")
print("=" * 80)

files = ["tests/e2e/dummy files/2025-05-17-12-48-17.pdf", "tests/e2e/dummy files/2025-05-17 12.50.27-1.jpg"]

try:
    payments = adapter.extract_payments_batch(files)

    print(f"\nTotal extracted: {len(payments)} payments")
    print("\nPayments with '3517' in check/ref number:")

    found = False
    for i, p in enumerate(payments):
        check = p.payment_info.check_no or ""
        ref = p.payment_info.payment_ref or ""

        if "3517" in str(check) or "3517" in str(ref):
            found = True
            print(f"\nPayment {i+1}:")
            print(f"  Check no: {check}")
            print(f"  Payment ref: {ref}")
            print(f"  Amount: ${p.payment_info.amount}")
            print(f"  Organization: {p.payer_info.organization_name}")
            print(f"  Aliases: {p.payer_info.aliases}")
            print(f"  Memo: {p.payment_info.memo}")
            print(
                f"  Address: {p.contact_info.address_line_1}, {p.contact_info.city}, {p.contact_info.state} {p.contact_info.zip}"
            )

    if not found:
        print("\nNo payments found with '3517' in check/ref number")

except Exception as e:
    print(f"Error: {e}")
    import traceback

    traceback.print_exc()

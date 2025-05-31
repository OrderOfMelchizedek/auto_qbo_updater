#!/usr/bin/env python3
"""Debug actual extraction to find why we have 5 payments instead of 4"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

# Set up environment
from dotenv import load_dotenv

load_dotenv()

from src.utils.enhanced_file_processor_v2 import EnhancedFileProcessorV2
from src.utils.gemini_adapter_v2 import GeminiAdapterV2

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("No API key found")
    exit(1)

# Create services
gemini_service = GeminiAdapterV2(api_key)
processor = EnhancedFileProcessorV2(gemini_service, None)

# Process files
files = [
    ("tests/e2e/dummy files/2025-05-17-12-48-17.pdf", ".pdf"),
    ("tests/e2e/dummy files/2025-05-17 12.50.27-1.jpg", ".jpg"),
]

# Step 1: Extract from each file separately
all_payments = []
for file_path, file_type in files:
    try:
        payments = gemini_service.extract_payments(file_path)
        print(f"\n{file_path}:")
        print(f"Extracted {len(payments)} payments")

        for i, p in enumerate(payments):
            ref = p.payment_info.payment_ref or ""
            check = p.payment_info.check_no or ""
            amount = p.payment_info.amount
            org = p.payer_info.organization_name or ""
            aliases = p.payer_info.aliases or []

            print(f"\n  Payment {i+1}:")
            print(f"    Check no: {check}")
            print(f"    Payment ref: {ref}")
            print(f"    Amount: {amount}")
            if org:
                print(f"    Organization: {org}")
            if aliases:
                print(f"    Aliases: {aliases}")

            # Look for the problematic payment
            if "3517031" in str(ref) or "3517031" in str(check):
                print(f"    *** CONTAINS 3517031 ***")

        all_payments.extend(payments)
    except Exception as e:
        print(f"Error: {e}")

print(f"\n\nTotal extracted: {len(all_payments)} payments")

# Step 2: Test deduplication
print("\n\nTesting deduplication...")
deduplicated = processor._deduplicate_payments(all_payments)
print(f"After deduplication: {len(deduplicated)} payments")

# Check what survived deduplication
print("\nPayments after deduplication:")
for i, p in enumerate(deduplicated):
    ref = p.payment_info.payment_ref or ""
    check = p.payment_info.check_no or ""
    amount = p.payment_info.amount
    org = p.payer_info.organization_name or ""
    aliases = p.payer_info.aliases or []

    print(f"\n  Payment {i+1}:")
    print(f"    Check/Ref: {check or ref}")
    print(f"    Amount: {amount}")
    if org:
        print(f"    Organization: {org}")
    elif aliases:
        print(f"    Aliases: {aliases[0] if aliases else 'None'}")

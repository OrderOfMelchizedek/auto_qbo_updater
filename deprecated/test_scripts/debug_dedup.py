#!/usr/bin/env python3
"""Debug deduplication issue with payment ref 0003517031"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(".") / "src"))

import os

from src.utils.enhanced_file_processor_v2 import EnhancedFileProcessorV2
from src.utils.gemini_adapter_v2 import GeminiAdapterV2

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("No API key")
    exit(1)

# Create processor
adapter = GeminiAdapterV2(api_key)
processor = EnhancedFileProcessorV2(adapter, None)

# Extract from both files
pdf_path = "tests/e2e/dummy files/2025-05-17-12-48-17.pdf"
jpg_path = "tests/e2e/dummy files/2025-05-17 12.50.27-1.jpg"

print("Extracting from PDF...")
pdf_payments = adapter.extract_payments(pdf_path)
print(f"PDF extracted: {len(pdf_payments)} payments")

print("\nExtracting from JPG...")
jpg_payments = adapter.extract_payments(jpg_path)
print(f"JPG extracted: {len(jpg_payments)} payments")

# Combine all payments
all_payments = pdf_payments + jpg_payments
print(f"\nTotal before dedup: {len(all_payments)}")

# Look for the problematic payment
print("\nSearching for payment with ref containing '3517031':")
found_count = 0
for i, p in enumerate(all_payments):
    # Check both payment_ref and check_no fields
    ref = p.payment_info.payment_ref or ""
    check = p.payment_info.check_no or ""

    if "3517031" in str(ref) or "3517031" in str(check):
        found_count += 1
        print(f"\n--- Payment {i+1} (found #{found_count}) ---")
        print(f"Payment ref: '{p.payment_info.payment_ref}'")
        print(f"Check no: '{p.payment_info.check_no}'")
        print(f"Amount: {p.payment_info.amount}")
        print(f"Organization: '{p.payer_info.organization_name}'")
        print(f"Aliases: {p.payer_info.aliases}")

        # Create the dedup key
        if p.payment_info.check_no:
            key = f"CHECK_{p.payment_info.check_no}_{p.payment_info.amount}"
        elif p.payment_info.payment_ref:
            key = f"REF_{p.payment_info.payment_ref}_{p.payment_info.amount}"
        else:
            key = "NO_KEY"
        print(f"Dedup key: {key}")

# Now test deduplication
print("\n\nTesting deduplication...")
deduped = processor._deduplicate_payments(all_payments)
print(f"After dedup: {len(deduped)} payments")

# Check if the duplicate was removed
print("\nChecking deduped list for '3517031':")
found_count = 0
for i, p in enumerate(deduped):
    ref = p.payment_info.payment_ref or ""
    check = p.payment_info.check_no or ""

    if "3517031" in str(ref) or "3517031" in str(check):
        found_count += 1
        print(f"\n--- Deduped payment {i+1} (found #{found_count}) ---")
        print(f"Payment ref: '{p.payment_info.payment_ref}'")
        print(f"Check no: '{p.payment_info.check_no}'")
        print(f"Organization: '{p.payer_info.organization_name}'")

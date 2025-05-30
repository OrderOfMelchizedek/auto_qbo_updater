#!/usr/bin/env python3
"""Test to understand the deduplication issue"""

# Create mock PaymentRecord objects to test deduplication
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class MockPaymentInfo:
    check_no: Optional[str] = None
    payment_ref: Optional[str] = None
    amount: float = 0.0


@dataclass
class MockPayerInfo:
    organization_name: Optional[str] = None
    aliases: Optional[List[str]] = None


@dataclass
class MockPayment:
    payment_info: MockPaymentInfo
    payer_info: MockPayerInfo


# Create test payments that represent the issue
payments = [
    # Payment 1: DAFgivingSGOs with ref 0003517031
    MockPayment(
        payment_info=MockPaymentInfo(payment_ref="0003517031", amount=600.0),
        payer_info=MockPayerInfo(organization_name="DAFgivingSGOs"),
    ),
    # Payment 2: Empty payer with ref 0003517031 (duplicate!)
    MockPayment(
        payment_info=MockPaymentInfo(payment_ref="0003517031", amount=600.0), payer_info=MockPayerInfo()  # Empty!
    ),
    # Payment 3: Different payment with similar number
    MockPayment(
        payment_info=MockPaymentInfo(check_no="3517037", amount=600.0),
        payer_info=MockPayerInfo(organization_name="Gustafson"),
    ),
]

# Simulate the V2 deduplication logic
seen = set()
deduplicated = []

print("Testing V2 deduplication logic:\n")

for i, payment in enumerate(payments):
    print(f"Payment {i+1}:")
    print(f"  Ref: {payment.payment_info.payment_ref}")
    print(f"  Check: {payment.payment_info.check_no}")
    print(f"  Amount: {payment.payment_info.amount}")
    print(f"  Org: {payment.payer_info.organization_name}")

    # Create unique key (following V2 logic)
    if payment.payment_info.check_no:
        key = f"CHECK_{payment.payment_info.check_no}_{payment.payment_info.amount}"
    elif payment.payment_info.payment_ref:
        key = f"REF_{payment.payment_info.payment_ref}_{payment.payment_info.amount}"
    else:
        key = None
        print("  Key: NO KEY - will be included!")

    if key:
        print(f"  Key: {key}")
        if key not in seen:
            seen.add(key)
            deduplicated.append(payment)
            print("  Action: ADDED")
        else:
            print("  Action: SKIPPED (duplicate)")
    else:
        deduplicated.append(payment)
        print("  Action: ADDED (no key)")
    print()

print(f"\nResult: {len(deduplicated)} payments after deduplication")
print(f"Expected: 2 payments (the two 0003517031 should be merged)")
print(f"Actual: {'CORRECT' if len(deduplicated) == 2 else 'INCORRECT'}")

# Show what SHOULD happen
print("\n\nWhat SHOULD happen:")
print("1. Payment 1 and 2 have the same key: REF_0003517031_600.0")
print("2. They should be MERGED (keeping the one with more data)")
print("3. Payment 3 has a different key: CHECK_3517037_600.0")
print("4. Final result: 2 payments total")

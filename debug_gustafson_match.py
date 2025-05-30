#!/usr/bin/env python3
"""Debug why Gustafson matches to Fintel"""

import csv
from pathlib import Path

# Load CSV and look for Gustafson
csv_path = Path("Friends of Mwangaza_Customer Contact List - All Fields.csv")

print("Looking for customers with 'Gustafson' in DisplayName...")
print("=" * 80)

gustafson_customers = []
with open(csv_path, "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        customer_name = row.get("Customer", "")
        if "gustafson" in customer_name.lower():
            gustafson_customers.append(
                {
                    "Customer": customer_name,
                    "First": row.get("First name", ""),
                    "Last": row.get("Last name", ""),
                    "Company": row.get("Company", ""),
                    "Full name": row.get("Full name", ""),
                }
            )

print(f"Found {len(gustafson_customers)} customers with 'Gustafson':")
for c in gustafson_customers:
    print(f"\n  Customer (DisplayName): {c['Customer']}")
    print(f"  First: {c['First']}")
    print(f"  Last: {c['Last']}")
    print(f"  Company: {c['Company']}")
    print(f"  Full name: {c['Full name']}")

# Now test the matching logic
print("\n" + "=" * 80)
print("Testing alias 'Gustafson' against customers:")
print("=" * 80)

# Import the actual matching logic
import sys

sys.path.insert(0, str(Path(".") / "src"))
from src.utils.alias_matcher import AliasMatcher


# Create a mock QBO service
class MockQBO:
    def __init__(self, customers):
        self.customers = customers

    def get_all_customers(self, use_cache=True):
        return self.customers


# Convert CSV to QBO format
customers = []
with open(csv_path, "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        customer_name = row.get("Customer", "")
        customers.append(
            {
                "Id": str(hash(customer_name) % 10000),
                "DisplayName": customer_name,
                "GivenName": row.get("First name", ""),
                "FamilyName": row.get("Last name", ""),
                "CompanyName": row.get("Company", ""),
            }
        )

# Test matching
qbo = MockQBO(customers)
matcher = AliasMatcher(qbo)

# Create a mock payment with alias "Gustafson"
from src.models.payment import ContactInfo, PayerInfo, PaymentInfo, PaymentRecord

payment = PaymentRecord(
    payment_info=PaymentInfo(payment_method="handwritten_check", check_no="3517031", amount=600.0),
    payer_info=PayerInfo(aliases=["Gustafson"]),
    contact_info=ContactInfo(),
)

# Try to match
results = matcher.match_payment_batch([payment])
matched_payment, matched_customer = results[0]

if matched_customer:
    print(f"\nAlias 'Gustafson' matched to:")
    print(f"  DisplayName: {matched_customer['DisplayName']}")
    print(f"  ID: {matched_customer['Id']}")
else:
    print("\nNo match found for 'Gustafson'")

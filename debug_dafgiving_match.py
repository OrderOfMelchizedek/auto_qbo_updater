#!/usr/bin/env python3
"""Debug why DAFgivingSGOs is matching to a customer with empty display name"""

import csv
from pathlib import Path

# Load CSV and find DAFgiving related entries
csv_path = Path("Friends of Mwangaza_Customer Contact List - All Fields.csv")

print("Searching for DAFgiving related customers in CSV...\n")

with open(csv_path, "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)

    found_count = 0
    for row in reader:
        # Check various fields for DAFgiving
        customer_name = row.get("Customer", "")
        company = row.get("Company", "")
        full_name = row.get("Full name", "")

        # Look for DAF in any field
        if any("daf" in str(field).lower() for field in [customer_name, company, full_name]):
            found_count += 1
            print(f"Entry {found_count}:")
            print(f"  Customer: '{customer_name}'")
            print(f"  Company: '{company}'")
            print(f"  Full name: '{full_name}'")
            print(f"  First: '{row.get('First name', '')}'")
            print(f"  Last: '{row.get('Last name', '')}'")
            print()

            # Check if this might be the empty display name case
            if not customer_name or customer_name.strip() == "":
                print("  *** This has EMPTY customer name! ***")

            if found_count >= 10:  # Limit output
                break

if found_count == 0:
    print("No DAFgiving entries found in CSV")
else:
    print(f"\nFound {found_count} DAF-related entries")

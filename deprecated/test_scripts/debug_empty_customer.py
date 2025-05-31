#!/usr/bin/env python3
"""Find CSV entries with empty Customer field"""

import csv
from pathlib import Path

csv_path = Path("Friends of Mwangaza_Customer Contact List - All Fields.csv")

print("Looking for entries with empty Customer field but data in other fields...\n")

with open(csv_path, "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)

    empty_customer_count = 0
    for i, row in enumerate(reader):
        customer_name = row.get("Customer", "")

        # Check if Customer is empty but other fields have data
        if not customer_name or customer_name.strip() == "":
            company = row.get("Company", "")
            full_name = row.get("Full name", "")
            first_name = row.get("First name", "")
            last_name = row.get("Last name", "")

            # Skip completely empty rows
            if any([company, full_name, first_name, last_name]):
                empty_customer_count += 1
                print(f"Row {i+1} has empty Customer field:")
                print(f"  Company: '{company}'")
                print(f"  Full name: '{full_name}'")
                print(f"  First: '{first_name}'")
                print(f"  Last: '{last_name}'")

                # Check if this could be DAF
                if "daf" in company.lower():
                    print("  *** This has DAF in company! ***")

                print()

                if empty_customer_count >= 10:
                    break

print(f"\nFound {empty_customer_count} entries with empty Customer field but other data")

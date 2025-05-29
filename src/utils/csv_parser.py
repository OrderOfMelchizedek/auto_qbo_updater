import csv
import datetime
import os
from typing import Any, Dict, List


class CSVParser:
    """Parser for CSV files containing donation information."""

    def parse(self, csv_path: str) -> List[Dict[str, Any]]:
        """Parse a CSV file containing donation data.

        Args:
            csv_path: Path to the CSV file

        Returns:
            List of dictionaries containing donation data
        """
        donations = []

        try:
            # List of encodings to try
            encodings = ["utf-8-sig", "utf-8", "latin-1", "cp1252"]
            sample = None

            # Try different encodings until one works
            for encoding in encodings:
                try:
                    with open(csv_path, "r", newline="", encoding=encoding) as csvfile:
                        sample = csvfile.read(4096)  # Read a larger sample
                    print(f"Successfully read file with encoding: {encoding}")
                    break
                except UnicodeDecodeError:
                    print(f"Failed to read with encoding: {encoding}")
                    continue

            if sample is None:
                raise ValueError(
                    f"Could not read file with any of the attempted encodings: {encodings}"
                )

            # Try to detect common delimiters in order of likelihood
            possible_delimiters = [",", ";", "\t", "|"]
            delimiter = None

            # Print the first few characters of sample for diagnosis
            print(
                f"CSV sample (first 100 chars): '{sample[:100].replace('\n', '\\n').replace('\r', '\\r')}'"
            )

            # Check if CSV sniffer can detect the delimiter
            try:
                dialect = csv.Sniffer().sniff(sample, delimiters=possible_delimiters)
                delimiter = dialect.delimiter
                print(f"Detected delimiter: '{delimiter}'")
            except Exception as sniff_err:
                print(f"CSV Sniffer error: {str(sniff_err)}")
                # If sniffer fails, try to determine the delimiter by counting occurrences
                counts = {d: sample.count(d) for d in possible_delimiters}
                print(f"Delimiter counts: {counts}")
                if any(counts.values()):
                    delimiter = max(counts.items(), key=lambda x: x[1])[0]
                    print(f"Estimated delimiter: '{delimiter}'")
                else:
                    # Fallback to comma if no delimiters found
                    delimiter = ","
                    print(f"No delimiters found, defaulting to comma")

            # Store the successful encoding to use later
            successful_encoding = encoding

            # Open the file again for actual parsing
            with open(csv_path, "r", newline="", encoding=successful_encoding) as csvfile:
                # Create a dictionary reader with the detected or fallback delimiter
                reader = csv.DictReader(csvfile, delimiter=delimiter)

                # Check if we have column headers
                fieldnames = reader.fieldnames
                if not fieldnames:
                    raise ValueError("No column headers found in CSV file")

                # Standard expected header mappings
                header_mappings = {
                    # Map various possible CSV column names to our standardized field names
                    "name": "Donor Name",
                    "donor_name": "Donor Name",
                    "donor": "Donor Name",
                    "full_name": "Full Name",
                    "donor_full_name": "Full Name",
                    "first_name": "First Name",
                    "fname": "First Name",
                    "last_name": "Last Name",
                    "lname": "Last Name",
                    "amount": "Gift Amount",
                    "donation_amount": "Gift Amount",
                    "gift_amount": "Gift Amount",
                    "donation": "Gift Amount",
                    "date": "Gift Date",
                    "donation_date": "Gift Date",
                    "gift_date": "Gift Date",
                    "address": "Address - Line 1",
                    "address1": "Address - Line 1",
                    "street": "Address - Line 1",
                    "city": "City",
                    "state": "State",
                    "zip": "ZIP",
                    "zipcode": "ZIP",
                    "postal_code": "ZIP",
                    "memo": "Memo",
                    "notes": "Memo",
                    "comment": "Memo",
                    "organization": "Organization Name",
                    "org_name": "Organization Name",
                    "organization_name": "Organization Name",
                    "check_number": "Check No.",
                    "check_no": "Check No.",
                    "check_num": "Check No.",
                }

                # Process each row
                for row in reader:
                    donation = {}

                    # Map CSV fields to our standardized fields
                    for csv_field, value in row.items():
                        if csv_field.lower() in header_mappings:
                            std_field = header_mappings[csv_field.lower()]
                            donation[std_field] = value
                        else:
                            # Just keep the original header if no mapping exists
                            donation[csv_field] = value

                    # Set default values if missing
                    if "Deposit Method" not in donation:
                        donation["Deposit Method"] = "Online Donation"

                    if "Deposit Date" not in donation:
                        donation["Deposit Date"] = datetime.datetime.now().strftime("%m/%d/%Y")

                    # Generate customerLookup field if missing
                    if "customerLookup" not in donation:
                        if "Last Name" in donation and "First Name" in donation:
                            donation["customerLookup"] = (
                                f"{donation['Last Name']}, {donation['First Name']}"
                            )
                        elif "Organization Name" in donation and "City" in donation:
                            donation["customerLookup"] = (
                                f"{donation['Organization Name']} {donation['City']}"
                            )
                        elif "Donor Name" in donation:
                            parts = donation["Donor Name"].split()
                            if len(parts) > 1:
                                last_name = parts[-1]
                                first_name = " ".join(parts[:-1])
                                donation["customerLookup"] = f"{last_name}, {first_name}"
                            else:
                                donation["customerLookup"] = donation["Donor Name"]

                    donations.append(donation)

            return donations

        except Exception as e:
            print(f"Error parsing CSV file {csv_path}: {str(e)}")
            return []

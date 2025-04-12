import csv
import os
import datetime
from typing import List, Dict, Any

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
            with open(csv_path, 'r', newline='', encoding='utf-8-sig') as csvfile:
                # Try to detect the dialect
                dialect = csv.Sniffer().sniff(csvfile.read(1024))
                csvfile.seek(0)
                
                # Read the header row
                reader = csv.reader(csvfile, dialect)
                headers = next(reader)
                
                # Create a dictionary reader to handle headers
                csvfile.seek(0)
                reader = csv.DictReader(csvfile, dialect=dialect)
                
                # Standard expected header mappings
                header_mappings = {
                    # Map various possible CSV column names to our standardized field names
                    'name': 'Donor Name',
                    'donor_name': 'Donor Name',
                    'donor': 'Donor Name',
                    'full_name': 'Full Name',
                    'donor_full_name': 'Full Name',
                    'first_name': 'First Name',
                    'fname': 'First Name',
                    'last_name': 'Last Name',
                    'lname': 'Last Name',
                    'amount': 'Gift Amount',
                    'donation_amount': 'Gift Amount',
                    'gift_amount': 'Gift Amount',
                    'donation': 'Gift Amount',
                    'date': 'Gift Date',
                    'donation_date': 'Gift Date',
                    'gift_date': 'Gift Date',
                    'address': 'Address - Line 1',
                    'address1': 'Address - Line 1',
                    'street': 'Address - Line 1',
                    'city': 'City',
                    'state': 'State',
                    'zip': 'ZIP',
                    'zipcode': 'ZIP',
                    'postal_code': 'ZIP',
                    'memo': 'Memo',
                    'notes': 'Memo',
                    'comment': 'Memo',
                    'organization': 'Organization Name',
                    'org_name': 'Organization Name',
                    'organization_name': 'Organization Name',
                    'check_number': 'Check No.',
                    'check_no': 'Check No.',
                    'check_num': 'Check No.',
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
                    if 'Deposit Method' not in donation:
                        donation['Deposit Method'] = 'Online Donation'
                    
                    if 'Deposit Date' not in donation:
                        donation['Deposit Date'] = datetime.datetime.now().strftime('%m/%d/%Y')
                    
                    # Generate customerLookup field if missing
                    if 'customerLookup' not in donation:
                        if 'Last Name' in donation and 'First Name' in donation:
                            donation['customerLookup'] = f"{donation['Last Name']}, {donation['First Name']}"
                        elif 'Organization Name' in donation and 'City' in donation:
                            donation['customerLookup'] = f"{donation['Organization Name']} {donation['City']}"
                        elif 'Donor Name' in donation:
                            parts = donation['Donor Name'].split()
                            if len(parts) > 1:
                                last_name = parts[-1]
                                first_name = ' '.join(parts[:-1])
                                donation['customerLookup'] = f"{last_name}, {first_name}"
                            else:
                                donation['customerLookup'] = donation['Donor Name']
                    
                    donations.append(donation)
            
            return donations
        
        except Exception as e:
            print(f"Error parsing CSV file {csv_path}: {str(e)}")
            return []
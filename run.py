#!/usr/bin/env python
# Run script to properly handle Python imports

import os
import sys
import argparse

# Add the current directory to Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import the app and run it
from src.app import app

if __name__ == '__main__':
    # Parse command line arguments, similar to src/app.py
    parser = argparse.ArgumentParser(description="FOM to QBO Automation App")
    parser.add_argument('--env', type=str, choices=['sandbox', 'production'], 
                        default=os.getenv('QBO_ENVIRONMENT', 'sandbox'),
                        help='QuickBooks Online environment (sandbox or production)')
    
    args = parser.parse_args()
    
    # Print startup info
    print(f"====== Starting with QuickBooks Online {args.env.upper()} environment ======")
    print(f"API Base URL: {'https://sandbox-quickbooks.api.intuit.com/v3/company/' if args.env == 'sandbox' else 'https://quickbooks.api.intuit.com/v3/company/'}")
    print(f"To change environments, restart with: python run.py --env [sandbox|production]")
    print("================================================================")
    
    # Run the Flask app
    app.run(debug=True)
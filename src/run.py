#!/usr/bin/env python
# Run script to properly handle Python imports

import os
import sys
import argparse

# Add the current directory to Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Parse command line arguments, similar to src/app.py
parser = argparse.ArgumentParser(description="FOM to QBO Automation App")
parser.add_argument('--env', type=str, choices=['sandbox', 'production'], 
                    default=os.getenv('QBO_ENVIRONMENT', 'sandbox'),
                    help='QuickBooks Online environment (sandbox or production)')
parser.add_argument('--model', type=str, default='gemini-flash',
                    choices=['gemini-flash', 'gemini-pro', 'gemini-2.5-flash-preview-05-20', 'gemini-2.5-pro-preview-05-06', 
                             'gemini-2.5-flash-preview-04-17', 'gemini-2.5-pro-preview-03-25'],
                    help='Gemini model to use (flash for faster responses, pro for better quality)')

# Parse arguments before importing app to set environment variables properly
args = parser.parse_args()

# Map model aliases to full model names
MODEL_MAPPING = {
    'gemini-flash': 'gemini-2.5-flash-preview-05-20',
    'gemini-pro': 'gemini-2.5-pro-preview-05-06',
    # Include the full model names as keys for consistency
    'gemini-2.5-flash-preview-05-20': 'gemini-2.5-flash-preview-05-20',
    'gemini-2.5-pro-preview-05-06': 'gemini-2.5-pro-preview-05-06',
    # Keep old model names for backward compatibility
    'gemini-2.5-flash-preview-04-17': 'gemini-2.5-flash-preview-04-17',
    'gemini-2.5-pro-preview-03-25': 'gemini-2.5-pro-preview-03-25'
}

# Resolve the model name from the alias
model_name = MODEL_MAPPING.get(args.model, 'gemini-2.5-flash-preview-05-20')

# Set environment variables for the app to use
os.environ['QBO_ENVIRONMENT'] = args.env
os.environ['GEMINI_MODEL'] = model_name

# Import the app after setting environment variables
from app import app

if __name__ == '__main__':    
    # Print startup info
    print(f"====== Starting with QuickBooks Online {args.env.upper()} environment ======")
    print(f"API Base URL: {'https://sandbox-quickbooks.api.intuit.com/v3/company/' if args.env == 'sandbox' else 'https://quickbooks.api.intuit.com/v3/company/'}")
    
    # Show model info (both alias and full name if using an alias)
    if args.model in ['gemini-flash', 'gemini-pro']:
        print(f"Using Gemini model: {args.model} ({model_name})")
    else:
        print(f"Using Gemini model: {args.model}")
        
    print(f"To change settings, restart with: python run.py --env [sandbox|production] --model [gemini-flash|gemini-pro]")
    print("================================================================")
    
    # Run the Flask app
    app.run(debug=True)
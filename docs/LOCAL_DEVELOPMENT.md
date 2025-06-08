# Local Development Guide

This guide explains how to run the QuickBooks Donation Manager locally with full functionality using test data.

## Setting Up Local Development Mode

### 1. Enable Local Dev Mode

Add the following to your `.env` file:

```bash
LOCAL_DEV_MODE=true
GEMINI_API_KEY=your_actual_gemini_api_key
```

### 2. What Local Dev Mode Does

When `LOCAL_DEV_MODE=true`:
- The app automatically uses CSV test data instead of QuickBooks API
- No QuickBooks authentication is required
- The UI shows "Using Local CSV Data" instead of the QuickBooks connection button
- Customer matching works against the test CSV file

### 3. Test Data Location

The test customer data is located at:
```
src/tests/test_files/customer_contact_list.csv
```

This CSV contains sample customers in QuickBooks format with:
- Customer names (in "Lastname, Firstname" format)
- Addresses
- Email addresses
- Phone numbers

### 4. How It Works

1. When you upload donation documents, they are processed normally through Gemini
2. Instead of searching QuickBooks, the app searches the CSV file
3. The matching algorithm works exactly as in production
4. You'll see match results and "New Customer" statuses in the table

### 5. Adding Test Customers

To add more test customers, edit the CSV file and add rows with these columns:
- `Customer` - Full name in "Lastname, Firstname" format
- `First Name` - Customer's first name
- `Last Name` - Customer's last name
- `Company Name` - For organization donors
- `Billing Street` - Street address
- `Billing City` - City
- `Billing State` - State (2-letter code)
- `Billing ZIP` - ZIP code
- `Email` - Email address
- `Phone` - Phone number

### 6. Testing Tips

1. **Test Matching**: The test CSV includes names like "Collins, Jonelle" which should match donations from "Jonelle R Collins"
2. **Test New Customers**: Upload donations with names not in the CSV to see "New Customer" status
3. **Test Organizations**: The CSV includes organizations like "Southeastern Pennsylvania Synod ELCA"

### 7. Differences from Production

In local dev mode:
- No real QuickBooks data is accessed
- No OAuth2 authentication flow
- Data is read-only (can't update QuickBooks)
- Limited to customers in the CSV file

### 8. Switching Modes

To switch between modes:
- Local testing: Set `LOCAL_DEV_MODE=true`
- Production mode: Set `LOCAL_DEV_MODE=false` (or remove it)

The app will automatically detect the mode on startup.

USER: Find the documentation for the Google Gemini API and give me a primer on how to utilize structured outputs (I want to use a gemini 2.5 flash model).

ASSISTANT: I'll help you find the documentation for the Google Gemini API and provide a primer on using structured outputs with Gemini 2.5 Flash.Let me fetch the official documentation page for more details on structured outputs with Gemini:Let me search for specific examples with Gemini 2.5 Flash:Based on my research, here's a comprehensive primer on utilizing structured outputs with Google Gemini 2.5 Flash:

## Google Gemini API Structured Outputs Primer

### Overview

Gemini generates unstructured text by default, but some applications require structured text. For these use cases, you can constrain Gemini to respond with JSON, a structured data format suitable for automated processing. Structured outputs ensure that the model's responses always follow a predefined schema, making it easier to parse and integrate into your applications.

### Key Concepts

1. **Response MIME Types**: application/json: output JSON as defined in the response schema (useful for structured output requirements) text/x.enum: output an enum value as defined in the response schema (useful for classification tasks)

2. **Schema Definition**: The Schema represents a select subset of the OpenAPI 3.0 Schema object with support for various data types including string, integer, number, boolean, array, and object.

3. **Property Ordering**: the order of properties is important. By default, the API orders properties alphabetically and does not preserve the order in which the properties are defined. You can use the `propertyOrdering` field to ensure consistent ordering.

### Installation

First, install the Google Generative AI Python SDK:

```bash
pip install google-generativeai
```

### Basic Example with Gemini 2.5 Flash

Here's a simple example of using structured outputs with Gemini 2.5 Flash:

```python
import os
from google import genai
from pydantic import BaseModel

# Set up your API key
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)

# Define your schema using Pydantic
class Recipe(BaseModel):
    recipe_name: str
    ingredients: list[str]
    steps: list[str]
    prep_time_minutes: int

# Use Gemini 2.5 Flash with structured output
response = client.models.generate_content(
    model="gemini-2.5-flash-preview-04-17",  # Latest preview version
    contents="Give me a recipe for chocolate chip cookies",
    config={
        "response_mime_type": "application/json",
        "response_schema": Recipe,
    },
)

# The response will be automatically parsed
recipe = response.parsed
print(f"Recipe: {recipe.recipe_name}")
print(f"Prep time: {recipe.prep_time_minutes} minutes")
```

### Advanced Schema Example

For more complex structures with nested objects:

```python
from typing import List, Optional
from pydantic import BaseModel

class Address(BaseModel):
    street: str
    city: str
    country: str
    postal_code: Optional[str] = None

class Person(BaseModel):
    name: str
    age: int
    email: str
    addresses: List[Address]

# Generate structured data
response = client.models.generate_content(
    model="gemini-2.5-flash-preview-04-17",
    contents="Extract person information from: John Doe, 30 years old, email: john@example.com, lives at 123 Main St, New York, USA 10001",
    config={
        "response_mime_type": "application/json",
        "response_schema": Person,
    },
)

person_data = response.parsed
```

### Using Enum for Classification

The output is one plain-text enum value that the model selects from a list of values that are defined in the provided response schema.

```python
from enum import Enum

class MovieGenre(str, Enum):
    DRAMA = "drama"
    COMEDY = "comedy"
    DOCUMENTARY = "documentary"
    ACTION = "action"
    HORROR = "horror"

response = client.models.generate_content(
    model="gemini-2.5-flash-preview-04-17",
    contents="Classify this movie description: A group of scientists discover a deadly virus that turns people into zombies.",
    config={
        "response_mime_type": "text/x.enum",
        "response_schema": MovieGenre,
    },
)

genre = response.text  # Will be one of the enum values
print(f"Genre: {genre}")
```

### Using the Instructor Library

For more advanced structured output capabilities, you can use the Instructor library:

```python
pip install instructor google-generativeai
```

```python
import instructor
import google.generativeai as genai
from pydantic import BaseModel

# Configure with Instructor
client = instructor.from_gemini(
    client=genai.GenerativeModel(
        model_name="models/gemini-2.5-flash-latest",
    ),
)

class User(BaseModel):
    name: str
    age: int
    occupation: str

# Extract structured data
user = client.chat.completions.create(
    messages=[
        {
            "role": "user",
            "content": "Extract: Jason is 25 years old and works as a software engineer.",
        }
    ],
    response_model=User,
)

print(user)  # User(name='Jason', age=25, occupation='software engineer')
```

### Best Practices

1. **Schema Design**: Design your Pydantic models carefully to capture all necessary information while maintaining clarity

2. **Property Ordering**: Use the `propertyOrdering` field when the order of properties matters for your application

3. **Error Handling**: Always implement error handling for cases where the model might not return valid structured data

4. **Validation**: Use Pydantic's built-in validation features to ensure data quality

5. **Complex Schemas**: A complex schema can result in an InvalidArgument: 400 error. Complexity might come from long property names, long array length limits, enums with many values

### Generation Configuration

You can customize the model's behavior with additional parameters:

```python
response = client.models.generate_content(
    model="gemini-2.5-flash-preview-04-17",
    contents="Your prompt here",
    config={
        "response_mime_type": "application/json",
        "response_schema": YourSchema,
        "temperature": 0.2,  # Lower for more deterministic outputs
        "max_output_tokens": 1000,
        "top_p": 0.8,
    },
)
```

### Thinking Mode (New in 2.5)

Gemini 2.5 Flash is our first fully hybrid reasoning model, giving developers the ability to turn thinking on or off. You can control the thinking budget:

```python
from google import genai

response = client.models.generate_content(
    model="gemini-2.5-flash-preview-04-17",
    contents="Complex reasoning task here",
    config=genai.types.GenerateContentConfig(
        thinking_config=genai.types.ThinkingConfig(
            thinking_budget=1024  # 0 to 24576 tokens
        ),
        response_mime_type="application/json",
        response_schema=YourSchema,
    )
)
```

This gives you a solid foundation for working with structured outputs in Gemini 2.5 Flash. The key is defining clear schemas and using the appropriate response MIME type for your use case.

USER: I'm building an app that extracts key information from user-uploaded scanned checks and documents. I want to use Gemini's structured outputs to extract the key information from the user-uploaded files and put it into a particular json schema. Show me how I might do that.

<background> The user will scan and upload images of the following:

_Checks_ Some checks will either be personal checks (you can tell if key details like the amount and the date are handwritten) or printed checks (usually issued by an organization and printed; these usually will not have the amounts handwritten). Pay close attention to the amount on the check (it will be listed numerically and spelled out, as checks usually are), the check no (usually a number found in the upper right corner) and any memos. Note the check date as well. Checks will also typically have the donor (and possibly their spouse's) name and address that you can use as a backup if you fail to find address information from the envelope.

_Envelopes_ The user will upload the envelopes that the donations came in. This is critical for verifying donor contact information. First ensure that the return address on the envelope matches the donor's entry in the customer contact list; if it doesn't, it may mean that the donor has moved and the user needs to update the address in the contact list. The return address supersedes all other addresses (including any addresses written on the check). Also note if there is any additional contact information (e.g. phone number, email) that is not in the customer contact list. Finally, note any memo that the donor writes (it may not be written on the check).

_User Record_ The user may handwrite a list of donations in the current deposit, typically in columns. At a minimum there will be a check no. and gift amount, but sometimes the user will record an item no. and and the donor name. The check no. written on the user record is authoritative; when merging entries, ensure that the check no. for each entry is in the user record.

_Online Donations_ The user may upload a .csv file containing a list of online donations. In these cases, use the Payment_Ref in lieu of the Check No. </background>

<json_schema> All output must be a json object with the following structure: _Payment Info_ - Payment Method (REQUIRED) - Check No. (REQUIRED for checks) - Payment_Ref (REQUIRED for online donations) - Amount (REQUIRED) - Payment Date (REQUIRED) - Check Date - Postmark Date - Deposit Date - Deposit Method - Memo

_Payer Info_ - Aliases (REQUIRED for non-organizations) - Salutation - Organization Name (REQUIRED for organizations)

_Contact Info_ - Address - Line 1 - City - State - ZIP - Email - Phone </json_schema>

<key_descriptions> Here is a description of each field to be extracted:

_Payment Method_ This can be a handwritten check, a printed check, or an online payment.

_Check No._ The check number for the payment. Usually four digits (for personal checks) but sometimes can be more (especially for pre-printed checks). If the Payment method is a check, Check No. is REQUIRED.

_Payment Ref_ Online donations have a Payment Reference No. instead of a Check no. Payment Ref is REQUIRED for all online donations.

_Amount_ The amount of the payment. If found on the check, it will be written as a number and spelled out. Make absolutely certain that this is recorded accurately. This is REQUIRED.

_Payment Date_ The date that a payment was made. This is REQUIRED. This is recorded differently depending on the payment method. - Handwritten Check - Let this be the postmark date; if the postmark date is unavailable, then use the check date. - Printed Check - Let this be the date printed on the check. - Online Payment - Let this be whatever date the transaction was recorded on

_Check Date_ The date written on the check.

_Postmark Date_ The date of the postmark. You will find this on the envelope.

_Deposit Date_ The date that the payment was deposited into the bank. Usually will be written on the user's record or perhaps on a deposit slip.

_Deposit Method_ - For checks: ATM Deposit (or Mobile deposit if specified by the user) - For online donations: Online (specify Stripe or Paypal if that information is available).

_Memo_ Any memo written on the check, or a summary of any information included with the payment.

_Aliases_ This is the name of the payer. Let this be a list where multiple versions of a payer's full name can be stored. Aliases for "John A. Smith" would include ["John Smith","J. Smith","Smith, John", "John A. Smith", "Smith, John A."]. At least one alias is REQUIRED if the payer is not an organization.

_Salutation_ This is how the payer is to be addressed. Infer this from their details (e.g. John and Jane Smith would be Mr. & Mrs.). Can be one or any combination of the following: - Mr. - Ms. - Mr. & Mrs. - Dr. - Rev. - Any other title which can be inferred from the given materials

_Organization Name_ The name of the organization making the donation. Get this from the customer contact list. This is REQUIRED for organizations.

_Address - Line 1_ The street address of the payer.

_City_ Address city.

_State_ The two-digit state code typically found in any U.S. address.

_ZIP_ A five-digit numerical postal code typically found in any U.S. address. Sometimes there is an additional four-digit extension; this can usually be ignored. NOTE: Be sure to format this as text so that leading zeros are preserved. </key_descriptions>

ASSISTANT: I'll help you build an app to extract key information from scanned checks and documents using Gemini's structured outputs. Here's a comprehensive implementation:

```python
import os
import base64
import json
from typing import List, Optional, Union, Literal
from datetime import datetime
from enum import Enum
import pandas as pd
from pydantic import BaseModel, Field, validator
import google.generativeai as genai
from pathlib import Path

# Configure Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

# Define Enums for controlled values
class PaymentMethod(str, Enum):
    HANDWRITTEN_CHECK = "handwritten_check"
    PRINTED_CHECK = "printed_check"
    ONLINE_PAYMENT = "online_payment"

class DepositMethod(str, Enum):
    ATM_DEPOSIT = "ATM Deposit"
    MOBILE_DEPOSIT = "Mobile Deposit"
    ONLINE_STRIPE = "Online - Stripe"
    ONLINE_PAYPAL = "Online - PayPal"
    ONLINE = "Online"

# Define Pydantic models for structured output
class PaymentInfo(BaseModel):
    payment_method: PaymentMethod = Field(description="Type of payment: handwritten_check, printed_check, or online_payment")
    check_no: Optional[str] = Field(None, description="Check number (required for checks)")
    payment_ref: Optional[str] = Field(None, description="Payment reference number (required for online donations)")
    amount: float = Field(description="Payment amount in dollars")
    payment_date: str = Field(description="Date payment was made (format: YYYY-MM-DD)")
    check_date: Optional[str] = Field(None, description="Date written on check (format: YYYY-MM-DD)")
    postmark_date: Optional[str] = Field(None, description="Postmark date from envelope (format: YYYY-MM-DD)")
    deposit_date: Optional[str] = Field(None, description="Date deposited to bank (format: YYYY-MM-DD)")
    deposit_method: Optional[DepositMethod] = Field(None, description="Method of deposit")
    memo: Optional[str] = Field(None, description="Any memo or notes from check or envelope")

    @validator('check_no')
    def validate_check_no(cls, v, values):
        if 'payment_method' in values and values['payment_method'] in [PaymentMethod.HANDWRITTEN_CHECK, PaymentMethod.PRINTED_CHECK]:
            if not v:
                raise ValueError("Check number is required for check payments")
        return v

    @validator('payment_ref')
    def validate_payment_ref(cls, v, values):
        if 'payment_method' in values and values['payment_method'] == PaymentMethod.ONLINE_PAYMENT:
            if not v:
                raise ValueError("Payment reference is required for online payments")
        return v

class PayerInfo(BaseModel):
    aliases: Optional[List[str]] = Field(None, description="List of name variations for individual donors")
    salutation: Optional[str] = Field(None, description="Title/salutation (Mr., Ms., Dr., etc.)")
    organization_name: Optional[str] = Field(None, description="Organization name if applicable")

    @validator('aliases', 'organization_name')
    def validate_payer_type(cls, v, values):
        # Either aliases or organization_name must be present
        if not v and not values.get('organization_name') and not values.get('aliases'):
            raise ValueError("Either aliases (for individuals) or organization_name must be provided")
        return v

class ContactInfo(BaseModel):
    address_line_1: Optional[str] = Field(None, description="Street address")
    city: Optional[str] = Field(None, description="City")
    state: Optional[str] = Field(None, description="Two-letter state code")
    zip: Optional[str] = Field(None, description="5-digit ZIP code as text")
    email: Optional[str] = Field(None, description="Email address")
    phone: Optional[str] = Field(None, description="Phone number")

    @validator('zip')
    def validate_zip(cls, v):
        if v and len(v) < 5:
            # Pad with leading zeros if needed
            v = v.zfill(5)
        return v

class DonationRecord(BaseModel):
    payment_info: PaymentInfo
    payer_info: PayerInfo
    contact_info: ContactInfo

class DonationExtractor:
    def __init__(self, model_name: str = "gemini-2.0-flash-preview"):
        """Initialize the donation extractor with Gemini model."""
        self.model = genai.GenerativeModel(model_name)

    def encode_image(self, image_path: str) -> str:
        """Encode image to base64 for Gemini API."""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    def extract_from_check(self, check_image_path: str, envelope_image_path: Optional[str] = None) -> DonationRecord:
        """Extract information from check and optional envelope images."""

        # Prepare the prompt
        prompt = """
        Analyze the provided check image (and envelope if provided) to extract donation information.

        For the check:
        - Identify if it's handwritten (amount and date are handwritten) or printed
        - Extract the check number (usually in upper right corner)
        - Extract the amount (both numeric and written versions should match)
        - Extract the date on the check
        - Extract any memo information
        - Extract payer name and address if visible

        For the envelope (if provided):
        - Extract the return address (this supersedes any address on the check)
        - Extract the postmark date
        - Look for any additional contact info (phone, email)
        - Note any additional memos or notes

        Payment Date Logic:
        - For handwritten checks: Use postmark date if available, otherwise use check date
        - For printed checks: Use the date printed on the check

        Return the extracted information in the specified JSON format.
        """

        # Prepare images
        parts = [prompt]

        # Add check image
        check_image = genai.upload_file(check_image_path, mime_type="image/jpeg")
        parts.append(check_image)

        # Add envelope image if provided
        if envelope_image_path:
            envelope_image = genai.upload_file(envelope_image_path, mime_type="image/jpeg")
            parts.append(envelope_image)

        # Generate response with structured output
        response = self.model.generate_content(
            contents=parts,
            generation_config={
                "response_mime_type": "application/json",
                "response_schema": DonationRecord,
                "temperature": 0.1,  # Low temperature for accuracy
            }
        )

        # Clean up uploaded files
        check_image.delete()
        if envelope_image_path:
            envelope_image.delete()

        return response.parsed

    def extract_from_user_record(self, record_image_path: str) -> List[dict]:
        """Extract information from handwritten user records."""

        prompt = """
        Analyze this handwritten user record of donations.
        Extract the following information for each entry:
        - Check number (this is authoritative - use this over any other check numbers)
        - Gift amount
        - Item number (if present)
        - Donor name (if present)

        Return a list of entries with check_no and amount at minimum.
        """

        # Define schema for user record entries
        class UserRecordEntry(BaseModel):
            check_no: str
            amount: float
            item_no: Optional[str] = None
            donor_name: Optional[str] = None

        class UserRecordList(BaseModel):
            entries: List[UserRecordEntry]

        # Upload and process image
        record_image = genai.upload_file(record_image_path, mime_type="image/jpeg")

        response = self.model.generate_content(
            contents=[prompt, record_image],
            generation_config={
                "response_mime_type": "application/json",
                "response_schema": UserRecordList,
                "temperature": 0.1,
            }
        )

        record_image.delete()

        return [entry.dict() for entry in response.parsed.entries]

    def extract_from_csv(self, csv_path: str) -> List[DonationRecord]:
        """Extract information from online donation CSV files."""

        # Read CSV file
        df = pd.read_csv(csv_path)

        # Prepare CSV content for Gemini
        csv_content = df.to_string()

        prompt = f"""
        Analyze this CSV file containing online donations.

        CSV Content:
        {csv_content}

        For each row, extract:
        - Use Payment_Ref as the payment reference number
        - Amount
        - Transaction date as payment_date
        - Donor information (name, email, etc.)
        - Set payment_method as "online_payment"
        - Set deposit_method as "Online" (specify Stripe or PayPal if evident)

        Return a list of DonationRecord objects.
        """

        class DonationRecordList(BaseModel):
            donations: List[DonationRecord]

        response = self.model.generate_content(
            contents=prompt,
            generation_config={
                "response_mime_type": "application/json",
                "response_schema": DonationRecordList,
                "temperature": 0.1,
            }
        )

        return response.parsed.donations

    def merge_records(self,
                     check_records: List[DonationRecord],
                     user_record_entries: List[dict]) -> List[DonationRecord]:
        """Merge check records with user record entries, using check numbers from user records as authoritative."""

        # Create a mapping of check numbers from user records
        user_record_map = {entry['check_no']: entry for entry in user_record_entries}

        merged_records = []

        for record in check_records:
            check_no = record.payment_info.check_no

            if check_no in user_record_map:
                # Update with authoritative check number and amount from user record
                user_entry = user_record_map[check_no]
                record.payment_info.check_no = user_entry['check_no']
                record.payment_info.amount = user_entry['amount']

            merged_records.append(record)

        return merged_records

    def process_batch(self,
                     check_images: List[str],
                     envelope_images: List[str] = None,
                     user_record_image: str = None,
                     csv_file: str = None) -> List[DonationRecord]:
        """Process a batch of donation documents."""

        all_records = []

        # Process checks and envelopes
        if check_images:
            envelope_images = envelope_images or [None] * len(check_images)

            for check_img, envelope_img in zip(check_images, envelope_images):
                try:
                    record = self.extract_from_check(check_img, envelope_img)
                    all_records.append(record)
                except Exception as e:
                    print(f"Error processing check {check_img}: {e}")

        # Process user record if provided
        user_entries = []
        if user_record_image:
            try:
                user_entries = self.extract_from_user_record(user_record_image)
            except Exception as e:
                print(f"Error processing user record: {e}")

        # Merge with user record data if available
        if user_entries and all_records:
            all_records = self.merge_records(all_records, user_entries)

        # Process CSV file for online donations
        if csv_file:
            try:
                csv_records = self.extract_from_csv(csv_file)
                all_records.extend(csv_records)
            except Exception as e:
                print(f"Error processing CSV file: {e}")

        return all_records

# Example usage
def main():
    # Initialize extractor
    extractor = DonationExtractor()

    # Example: Process a single check with envelope
    check_record = extractor.extract_from_check(
        check_image_path="path/to/check.jpg",
        envelope_image_path="path/to/envelope.jpg"
    )

    print("Extracted donation record:")
    print(json.dumps(check_record.dict(), indent=2))

    # Example: Process batch of documents
    all_records = extractor.process_batch(
        check_images=["check1.jpg", "check2.jpg"],
        envelope_images=["envelope1.jpg", "envelope2.jpg"],
        user_record_image="user_record.jpg",
        csv_file="online_donations.csv"
    )

    # Save results to JSON
    with open("donation_records.json", "w") as f:
        json.dump([record.dict() for record in all_records], f, indent=2)

    print(f"Processed {len(all_records)} donation records")

if __name__ == "__main__":
    main()
```

I've created a comprehensive implementation for extracting donation information from scanned documents using Gemini's structured outputs. Here are the key features:

## Key Components:

### 1. **Structured Data Models**

- Uses Pydantic models to define the exact JSON schema you specified
- Includes validation to ensure required fields are present (e.g., check numbers for checks, payment references for online donations)
- Handles the specific business logic for different payment types

### 2. **Document Processing**

The `DonationExtractor` class handles different document types:

- **Checks & Envelopes**: Uses Gemini's multimodal capabilities to analyze images
- **User Records**: Extracts handwritten lists with authoritative check numbers
- **CSV Files**: Processes online donation data

### 3. **Smart Field Extraction**

- Implements the payment date logic (postmark > check date for handwritten checks)
- Prioritizes envelope addresses over check addresses
- Uses user record check numbers as authoritative

### 4. **Batch Processing**

- Process multiple documents at once
- Merge data from different sources
- Handle errors gracefully

## Usage Example:

```python
# Initialize the extractor
extractor = DonationExtractor(model_name="gemini-2.5-flash-latest")

# Process a single check
record = extractor.extract_from_check(
    check_image_path="check.jpg",
    envelope_image_path="envelope.jpg"  # Optional
)

# Process a batch with all document types
records = extractor.process_batch(
    check_images=["check1.jpg", "check2.jpg"],
    envelope_images=["env1.jpg", "env2.jpg"],
    user_record_image="handwritten_list.jpg",
    csv_file="stripe_donations.csv"
)
```

## Additional Utilities You Might Want:
```python
# Additional utility functions for donation processing

from typing import List, Dict, Optional
import re
from datetime import datetime
from difflib import SequenceMatcher

class DonationUtilities:
    """Helper utilities for donation processing."""

    @staticmethod
    def generate_aliases(full_name: str) -> List[str]:
        """Generate common name variations for a donor."""
        aliases = [full_name]

        # Split name into parts
        parts = full_name.strip().split()
        if len(parts) < 2:
            return aliases

        # Common variations
        if len(parts) == 2:
            first, last = parts
            aliases.extend([
                f"{last}, {first}",  # Last, First
                f"{first[0]}. {last}",  # F. Last
                f"{last}, {first[0]}.",  # Last, F.
            ])
        elif len(parts) == 3:
            first, middle, last = parts
            aliases.extend([
                f"{first} {last}",  # First Last (no middle)
                f"{last}, {first}",  # Last, First
                f"{last}, {first} {middle}",  # Last, First Middle
                f"{first} {middle[0]}. {last}",  # First M. Last
                f"{first[0]}. {last}",  # F. Last
                f"{last}, {first[0]}.",  # Last, F.
            ])

        # Remove duplicates while preserving order
        seen = set()
        unique_aliases = []
        for alias in aliases:
            if alias not in seen:
                seen.add(alias)
                unique_aliases.append(alias)

        return unique_aliases

    @staticmethod
    def infer_salutation(names: List[str]) -> str:
        """Infer appropriate salutation from donor names."""
        # Check for titles in names
        titles = {
            'dr': 'Dr.',
            'doctor': 'Dr.',
            'rev': 'Rev.',
            'reverend': 'Rev.',
            'pastor': 'Pastor',
            'rabbi': 'Rabbi',
            'prof': 'Prof.',
            'professor': 'Prof.'
        }

        for name in names:
            lower_name = name.lower()
            for title_key, title_value in titles.items():
                if title_key in lower_name:
                    return title_value

        # Check for couple (multiple names with "and" or "&")
        if any(' and ' in name.lower() or ' & ' in name for name in names):
            return "Mr. & Mrs."

        # Default based on single name
        if names:
            # Simple gender inference (not perfect, but reasonable default)
            first_name = names[0].split()[0].lower()
            common_female_names = ['mary', 'patricia', 'jennifer', 'linda', 'elizabeth',
                                 'barbara', 'susan', 'jessica', 'sarah', 'karen']
            if first_name in common_female_names:
                return "Ms."

        return "Mr."

    @staticmethod
    def validate_address(address_data: Dict[str, str]) -> Dict[str, str]:
        """Validate and clean address data."""
        cleaned = {}

        # Clean and validate each field
        if address_data.get('address_line_1'):
            cleaned['address_line_1'] = address_data['address_line_1'].strip()

        if address_data.get('city'):
            cleaned['city'] = address_data['city'].strip().title()

        if address_data.get('state'):
            state = address_data['state'].strip().upper()
            # Ensure it's a 2-letter code
            if len(state) == 2:
                cleaned['state'] = state

        if address_data.get('zip'):
            zip_code = re.sub(r'[^\d]', '', address_data['zip'])
            if len(zip_code) >= 5:
                cleaned['zip'] = zip_code[:5]  # Use only 5-digit ZIP

        return cleaned

    @staticmethod
    def match_donor_to_database(extracted_name: str,
                              database_names: List[str],
                              threshold: float = 0.8) -> Optional[str]:
        """Match extracted donor name to existing database entry."""
        best_match = None
        best_score = 0

        extracted_lower = extracted_name.lower().strip()

        for db_name in database_names:
            db_lower = db_name.lower().strip()

            # Check exact match first
            if extracted_lower == db_lower:
                return db_name

            # Use sequence matching for fuzzy matching
            score = SequenceMatcher(None, extracted_lower, db_lower).ratio()

            # Check if last names match (common for family donations)
            extracted_parts = extracted_lower.split()
            db_parts = db_lower.split()
            if extracted_parts and db_parts:
                if extracted_parts[-1] == db_parts[-1]:  # Last names match
                    score += 0.2  # Boost score

            if score > best_score and score >= threshold:
                best_score = score
                best_match = db_name

        return best_match

    @staticmethod
    def format_currency(amount: float) -> str:
        """Format amount as currency string."""
        return f"${amount:,.2f}"

    @staticmethod
    def parse_handwritten_amount(amount_text: str) -> Optional[float]:
        """Parse potentially messy handwritten amount text."""
        # Remove common currency symbols and commas
        cleaned = re.sub(r'[$,]', '', amount_text.strip())

        # Try to find a number pattern
        number_pattern = r'(\d+\.?\d*)'
        match = re.search(number_pattern, cleaned)

        if match:
            try:
                return float(match.group(1))
            except ValueError:
                return None

        return None

    @staticmethod
    def merge_contact_info(primary: Dict, secondary: Dict) -> Dict:
        """Merge contact information, preferring primary source."""
        merged = primary.copy()

        # Add any missing fields from secondary
        for key, value in secondary.items():
            if key not in merged or not merged[key]:
                merged[key] = value

        return merged

# Example usage with validation workflow
class DonationValidator:
    """Validate extracted donations against business rules."""

    def __init__(self):
        self.utils = DonationUtilities()

    def validate_donation(self, donation: Dict) -> List[str]:
        """Validate a donation record and return any issues."""
        issues = []

        # Check required fields
        payment_info = donation.get('payment_info', {})

        if not payment_info.get('amount'):
            issues.append("Missing required amount")
        elif payment_info['amount'] <= 0:
            issues.append("Amount must be positive")

        payment_method = payment_info.get('payment_method')
        if payment_method in ['handwritten_check', 'printed_check']:
            if not payment_info.get('check_no'):
                issues.append("Check number required for check payments")
        elif payment_method == 'online_payment':
            if not payment_info.get('payment_ref'):
                issues.append("Payment reference required for online payments")

        # Validate payer info
        payer_info = donation.get('payer_info', {})
        if not payer_info.get('aliases') and not payer_info.get('organization_name'):
            issues.append("Either donor name or organization required")

        # Validate dates
        date_fields = ['payment_date', 'check_date', 'postmark_date', 'deposit_date']
        for field in date_fields:
            if payment_info.get(field):
                try:
                    datetime.strptime(payment_info[field], '%Y-%m-%d')
                except ValueError:
                    issues.append(f"Invalid date format for {field}")

        return issues

# Streamlit UI example (if you want a web interface)
def create_donation_ui():
    """Example Streamlit UI for donation processing."""
    import streamlit as st

    st.title("Donation Document Processor")

    # File uploaders
    st.header("Upload Documents")

    check_files = st.file_uploader(
        "Upload Check Images",
        type=['jpg', 'jpeg', 'png'],
        accept_multiple_files=True
    )

    envelope_files = st.file_uploader(
        "Upload Envelope Images (optional)",
        type=['jpg', 'jpeg', 'png'],
        accept_multiple_files=True
    )

    user_record = st.file_uploader(
        "Upload User Record (optional)",
        type=['jpg', 'jpeg', 'png']
    )

    csv_file = st.file_uploader(
        "Upload Online Donations CSV (optional)",
        type=['csv']
    )

    if st.button("Process Documents"):
        with st.spinner("Processing documents..."):
            # Initialize extractor
            extractor = DonationExtractor()

            # Process files
            # (Implementation would save uploaded files temporarily and process)

            st.success("Processing complete!")

            # Display results in a table
            # st.dataframe(results_df)
```
## Key Implementation Tips:

### 1. **Handling Multiple Document Types**

Since you're processing different document types (checks, envelopes, user records, CSVs), consider creating separate prompts optimized for each:

```python
# Specialized prompts for each document type
CHECK_PROMPT = """
Focus on:
- Check number (upper right corner)
- Amount (numeric and written - they must match)
- Date on check
- Memo line
- Account holder name and address
Identify if handwritten vs printed by looking at the amount and date fields.
"""

ENVELOPE_PROMPT = """
Priority: Return address (this supersedes all other addresses)
Also extract:
- Postmark date
- Any handwritten notes
- Additional contact info (phone, email)
"""
```

### 2. **Error Handling and Validation**

Add robust validation for critical fields:

```python
def validate_amount_consistency(numeric_amount: str, written_amount: str) -> bool:
    """Ensure numeric and written amounts match on checks."""
    # Convert written amount to number and compare
    # This is crucial for check processing
```

### 3. **Batch Processing Optimization**

For better performance with multiple documents:

```python
# Use Gemini's batch API for multiple images
batch_config = {
    "response_mime_type": "application/json",
    "response_schema": DonationRecordList,
    "temperature": 0.1,
    "max_output_tokens": 2000,
}
```

### 4. **Address Reconciliation**

Since addresses can come from multiple sources with different priorities:

```python
def reconcile_addresses(check_address, envelope_address, database_address):
    # Priority: Envelope > Check > Database
    if envelope_address and is_valid_address(envelope_address):
        return envelope_address
    elif check_address and is_valid_address(check_address):
        return check_address
    else:
        return database_address
```

### 5. **Deployment Considerations**

- **API Rate Limits**: Implement retry logic and rate limiting
- **File Size**: Optimize images before sending to Gemini (compress, resize)
- **Caching**: Cache results to avoid reprocessing identical documents
- **Audit Trail**: Log all extractions for verification

### 6. **Testing Strategy**

Create test cases for:

- Different check types (personal, business, handwritten, printed)
- Edge cases (damaged documents, poor handwriting)
- Various CSV formats from different payment processors

The structured output feature of Gemini ensures you'll get consistent JSON responses that match your schema, making it much easier to integrate into your application workflow. The key is providing clear, detailed prompts and using appropriate temperature settings (low for accuracy).

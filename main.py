import json
import os
import shutil
import firebase_admin
import pandas as pd
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from firebase_admin import credentials, firestore
from firebase_admin import storage
from typing import List
from google import genai
from google.genai import types

# Initialize FastAPI App
app = FastAPI()

# Enable CORS for all domains
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure upload folder
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Google Gemini API Key (use environment variable for security)
GENAI_API_KEY = "AIzaSyA_VO838RjbYn0lc4x9Z-Srw5gXWC3Ubzs"
client = genai.Client(api_key=GENAI_API_KEY)

# Allowed file extensions
ALLOWED_EXTENSIONS = {"pdf"}

# Initialize Firebase Firestore
cred = credentials.Certificate(
    "serviceAccountKey.json"
)  # 🔹 Download Firebase Admin SDK JSON file from Firebase Console
firebase_admin.initialize_app(
    cred,
    {
        "storageBucket": "auto-extract-pdf.firebasestorage.app"  # 🔹 Set your Firebase Storage bucket
    },
)
db = firestore.client()


def is_valid_file(file: UploadFile):
    """Check if file is a valid PDF."""
    return (
        file.filename.split(".")[-1].lower() in ALLOWED_EXTENSIONS
        and file.content_type == "application/pdf"
    )


def process_invoice(file_path: str, file_name: str):
    """Processes a single invoice using Gemini API."""
    try:
        # Upload file to Google Gemini API
        uploaded_file = client.files.upload(file=file_path)
        files = [
            client.files.upload(file="training_invoices/3DUA.pdf"),
            client.files.upload(file="training_invoices/SVST.pdf"),
            client.files.upload(file="training_invoices/MODE.pdf"),
            client.files.upload(file="training_invoices/KAHA.pdf"),
            client.files.upload(file="training_invoices/KEHE.pdf"),
            client.files.upload(file="training_invoices/RMMG.PDF"),
            client.files.upload(file="training_invoices/BYOGO.pdf"),
            client.files.upload(file="training_invoices/RAMG.pdf"),
            client.files.upload(file="training_invoices/HANS.pdf"),
            client.files.upload(file="training_invoices/HANS.pdf"),
            client.files.upload(file="training_invoices/BORA.pdf"),
            client.files.upload(file="training_invoices/SVST.pdf"),
        ]
        model = "gemini-2.0-flash-exp"
        contents = [
            types.Content(
                role="user",
                parts=[
                    types.Part.from_uri(
                        file_uri=files[0].uri,
                        mime_type=files[0].mime_type,
                    ),
                    types.Part.from_text(
                        text="""The attached document is an invoice recevied by me, I would like to extract the following information from the invoice - PO Number, PO Date, Invoice Date, Invoice Number, Total Product Price, Taxes, Dropshipping Fees, Shipping Charges, Other Charges, CC Charges, Paypal/ Payoneer Fees, Discounts, Final Amount Payable. the output has to be in structured format"""
                    ),
                ],
            ),
            types.Content(
                role="model",
                parts=[
                    types.Part.from_text(
                        text="""{
  \"PO Number\": \"3DUA-2890\",
  \"PO Date\": null,
  \"Invoice Date\": \"3/3/2025\",
  \"Invoice Number\": \"V1815159\",
  \"Total Product Price\": \"98.08\",
  \"Taxes\": \"0.00\",
  \"Dropshipping Fees\": null,
  \"Shipping Charges\": null,
  \"Other Charges\": null,
  \"CC Charges\": null,
  \"Paypal/ Payoneer Fees\": null,
  \"Discounts\": null,
  \"Final Amount Payable\": \"98.08\"
}"""
                    ),
                ],
            ),
            types.Content(
                role="user",
                parts=[
                    types.Part.from_uri(
                        file_uri=files[1].uri,
                        mime_type=files[1].mime_type,
                    ),
                    types.Part.from_text(
                        text="""You are given an invoice that can contain various headings or labels for the same fields. Your task is to extract the following fields in a structured JSON format. Note that each field can appear under multiple different names or synonyms in the invoice. Use your best judgment to match these synonyms to the correct field. If a field is not found, please return `null`.

**Fields and Possible Synonyms**:

1. **Invoice Date**
   - Possible synonyms: \"Document Date\", \"Doc Dt\", \"Post Date\", \"Charge Date\"

2. **Invoice Number**
   - Possible synonyms: \"Document Number\", \"Doc No\", \"Inv Number\", \"Invoice\"

3. **Actual Product Price**
   - Possible synonyms: \"Mentioned Amount against Item Code or Item Details\", \"Unit Price\", \"Invoice Amount\", \"Overdue Amount\", \"Current Charges\", \"Ext or Extended Price\", \"Charges\"

4. **Actual Sales Tax Paid**
   - Possible synonyms: \"Sales tax\", \"Vat\", \"Total Tax\", \"Tax charges\"

5. **Actual Dropship Fees**
   - Possible synonyms: \"Drop Ship Fees\", \"DSF\"

6. **Actual Shipping Charges**
   - Possible synonyms: \"Shipping & Handling Charges\", \"Freight Charges\", \"S&H\", \"Handling Fees\", \"Shipping fees\"

7. **Actual Other Charges**
   - Possible synonyms: \"Miscellaneous charges\", \"Charges\", \"Other Fees\"

8. **CC Fees in Invoice**
   - Possible synonyms: \"Credit Card Processing Fees\", \"CC\", \"Credit Card Fee\"

9. **Paypal Fee / Pioneer Fee in invoice**
   - Possible synonyms: \"Paypal Fees\"

10. **Actual Discount Received**
   - Possible synonyms: \"Disc %\", \"Discount Price\", \"Discount Amount\"

11. **Gross Payable Price**
   - Possible synonyms: \"Total Invoice Amount\", \"Total USD Amount\", \"Total Charges\", \"Total of Ext or Extended Price\", \"Total Amount\"

**Required JSON Output**:
```json
{
  \"Invoice Date\": \"String or null\",
  \"Invoice Number\": \"String or null\",
\"PO Number: \"String or null\"
\"PO Date\": \"String or null\"
  \"Actual Product Price\": \"Float or null\",
  \"Actual Sales Tax Paid\": \"Float or null\",
  \"Actual Dropship Fees\": \"Float or null\",
  \"Actual Shipping Charges\": \"Float or null\",
  \"Actual Other Charges\": \"Float or null\",
  \"CC Fees in Invoice\": \"Float or null\",
  \"Paypal / Pioneer Fee in invoice\": \"Float or null\",
  \"Actual Discount Received\": \"Float or null\",
  \"Gross Payable Price\": \"Float or null\"
}
When reading the invoice, if you see any of these synonyms, please assign the corresponding value to the appropriate field. If a field is not mentioned at all, assign null to that field. If a synonym or label appears multiple times or mentioned as unit value, sum or compute the relevant amount if not provided directly. It can also happen that the invoice may mention multiple PO numbers, in such cases you need to split it into those many line items."""
                    ),
                ],
            ),
            types.Content(
                role="model",
                parts=[
                    types.Part.from_text(
                        text="""{
  \"Invoice Date\": \"09/03/24\",
  \"Invoice Number\": \"207095\",
\"PO Number\": \"09/03/2024 DROPSHIP\",
\"PO Date\": \"09/03/24\",
  \"Actual Product Price\": 168.00,
  \"Actual Sales Tax Paid\": null,
  \"Actual Dropship Fees\": null,
  \"Actual Shipping Charges\": 0.00,
  \"Actual Other Charges\": 3.50,
  \"CC Fees in Invoice\": null,
  \"Paypal / Pioneer Fee in invoice\": null,
  \"Actual Discount Received\": null,
  \"Gross Payable Price\": 423.50
}"""
                    ),
                ],
            ),
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(
                        text="""you missed this line \"PO Reference: SVST-20395 to SVST-20398 -- Total 4 orders.\" in the invoice, this meant that you should have split each line item into a separate set of record"""
                    ),
                ],
            ),
            types.Content(
                role="model",
                parts=[
                    types.Part.from_text(
                        text="""[
  {
    \"Invoice Date\": \"09/03/24\",
    \"Invoice Number\": \"207095\",
    \"PO Number\": \"SVST-20395\",
    \"PO Date\": \"09/03/24\",
    \"Actual Product Price\": 168.00,
    \"Actual Sales Tax Paid\": null,
    \"Actual Dropship Fees\": null,
    \"Actual Shipping Charges\": 0.00,
    \"Actual Other Charges\": 3.50,
    \"CC Fees in Invoice\": null,
    \"Paypal / Pioneer Fee in invoice\": null,
    \"Actual Discount Received\": null,
    \"Gross Payable Price\": 423.50
  },
  {
    \"Invoice Date\": \"09/03/24\",
    \"Invoice Number\": \"207095\",
    \"PO Number\": \"SVST-20396\",
    \"PO Date\": \"09/03/24\",
    \"Actual Product Price\": 168.00,
    \"Actual Sales Tax Paid\": null,
    \"Actual Dropship Fees\": null,
    \"Actual Shipping Charges\": 0.00,
    \"Actual Other Charges\": 3.50,
    \"CC Fees in Invoice\": null,
    \"Paypal / Pioneer Fee in invoice\": null,
    \"Actual Discount Received\": null,
    \"Gross Payable Price\": 423.50
  },
  {
    \"Invoice Date\": \"09/03/24\",
    \"Invoice Number\": \"207095\",
    \"PO Number\": \"SVST-20397\",
    \"PO Date\": \"09/03/24\",
    \"Actual Product Price\": 168.00,
    \"Actual Sales Tax Paid\": null,
    \"Actual Dropship Fees\": null,
    \"Actual Shipping Charges\": 0.00,
    \"Actual Other Charges\": 3.50,
    \"CC Fees in Invoice\": null,
    \"Paypal / Pioneer Fee in invoice\": null,
    \"Actual Discount Received\": null,
    \"Gross Payable Price\": 423.50
  },
  {
    \"Invoice Date\": \"09/03/24\",
    \"Invoice Number\": \"207095\",
    \"PO Number\": \"SVST-20398\",
    \"PO Date\": \"09/03/24\",
    \"Actual Product Price\": 168.00,
    \"Actual Sales Tax Paid\": null,
    \"Actual Dropship Fees\": null,
    \"Actual Shipping Charges\": 0.00,
    \"Actual Other Charges\": 3.50,
    \"CC Fees in Invoice\": null,
    \"Paypal / Pioneer Fee in invoice\": null,
    \"Actual Discount Received\": null,
    \"Gross Payable Price\": 423.50
  }
]"""
                    ),
                ],
            ),
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(
                        text="""each items product price is different but you have mentioned same amount 168. Also when splitting records you should always verify whether the total of all entries match with the invoice total which over here is 423.50"""
                    ),
                ],
            ),
            types.Content(
                role="model",
                parts=[
                    types.Part.from_text(
                        text="""[
  {
    \"Invoice Date\": \"09/03/24\",
    \"Invoice Number\": \"207095\",
    \"PO Number\": \"SVST-20395\",
    \"PO Date\": \"09/03/24\",
    \"Actual Product Price\": 168.00,
    \"Actual Sales Tax Paid\": null,
    \"Actual Dropship Fees\": null,
    \"Actual Shipping Charges\": 0.00,
    \"Actual Other Charges\": 0.00,
    \"CC Fees in Invoice\": null,
    \"Paypal / Pioneer Fee in invoice\": null,
    \"Actual Discount Received\": null,
    \"Gross Payable Price\": null
  },
  {
    \"Invoice Date\": \"09/03/24\",
    \"Invoice Number\": \"207095\",
    \"PO Number\": \"SVST-20396\",
    \"PO Date\": \"09/03/24\",
    \"Actual Product Price\": 86.00,
    \"Actual Sales Tax Paid\": null,
    \"Actual Dropship Fees\": null,
    \"Actual Shipping Charges\": 0.00,
    \"Actual Other Charges\": 0.00,
    \"CC Fees in Invoice\": null,
    \"Paypal / Pioneer Fee in invoice\": null,
    \"Actual Discount Received\": null,
    \"Gross Payable Price\": null
  },
  {
    \"Invoice Date\": \"09/03/24\",
    \"Invoice Number\": \"207095\",
    \"PO Number\": \"SVST-20397\",
    \"PO Date\": \"09/03/24\",
    \"Actual Product Price\": 150.00,
    \"Actual Sales Tax Paid\": null,
    \"Actual Dropship Fees\": null,
    \"Actual Shipping Charges\": 0.00,
    \"Actual Other Charges\": 0.00,
    \"CC Fees in Invoice\": null,
    \"Paypal / Pioneer Fee in invoice\": null,
    \"Actual Discount Received\": null,
    \"Gross Payable Price\": null
  },
  {
    \"Invoice Date\": \"09/03/24\",
    \"Invoice Number\": \"207095\",
    \"PO Number\": \"SVST-20398\",
    \"PO Date\": \"09/03/24\",
    \"Actual Product Price\": 16.00,
    \"Actual Sales Tax Paid\": null,
    \"Actual Dropship Fees\": null,
    \"Actual Shipping Charges\": 0.00,
    \"Actual Other Charges\": 3.50,
    \"CC Fees in Invoice\": null,
    \"Paypal / Pioneer Fee in invoice\": null,
    \"Actual Discount Received\": null,
    \"Gross Payable Price\": null
  }
]"""
                    ),
                ],
            ),
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(
                        text="""Gross Payable Price is the total for the item, it cannot be null"""
                    ),
                ],
            ),
            types.Content(
                role="model",
                parts=[
                    types.Part.from_text(
                        text="""[
  {
    \"Invoice Date\": \"09/03/24\",
    \"Invoice Number\": \"207095\",
    \"PO Number\": \"SVST-20395\",
    \"PO Date\": \"09/03/24\",
    \"Actual Product Price\": 168.00,
    \"Actual Sales Tax Paid\": null,
    \"Actual Dropship Fees\": null,
    \"Actual Shipping Charges\": 0.00,
    \"Actual Other Charges\": 0.00,
    \"CC Fees in Invoice\": null,
    \"Paypal / Pioneer Fee in invoice\": null,
    \"Actual Discount Received\": null,
    \"Gross Payable Price\": 168.00
  },
  {
    \"Invoice Date\": \"09/03/24\",
    \"Invoice Number\": \"207095\",
    \"PO Number\": \"SVST-20396\",
    \"PO Date\": \"09/03/24\",
    \"Actual Product Price\": 86.00,
    \"Actual Sales Tax Paid\": null,
    \"Actual Dropship Fees\": null,
    \"Actual Shipping Charges\": 0.00,
    \"Actual Other Charges\": 0.00,
    \"CC Fees in Invoice\": null,
    \"Paypal / Pioneer Fee in invoice\": null,
    \"Actual Discount Received\": null,
    \"Gross Payable Price\": 86.00
  },
  {
    \"Invoice Date\": \"09/03/24\",
    \"Invoice Number\": \"207095\",
    \"PO Number\": \"SVST-20397\",
    \"PO Date\": \"09/03/24\",
    \"Actual Product Price\": 150.00,
    \"Actual Sales Tax Paid\": null,
    \"Actual Dropship Fees\": null,
    \"Actual Shipping Charges\": 0.00,
    \"Actual Other Charges\": 0.00,
    \"CC Fees in Invoice\": null,
    \"Paypal / Pioneer Fee in invoice\": null,
    \"Actual Discount Received\": null,
    \"Gross Payable Price\": 150.00
  },
  {
    \"Invoice Date\": \"09/03/24\",
    \"Invoice Number\": \"207095\",
    \"PO Number\": \"SVST-20398\",
    \"PO Date\": \"09/03/24\",
    \"Actual Product Price\": 16.00,
    \"Actual Sales Tax Paid\": null,
    \"Actual Dropship Fees\": null,
    \"Actual Shipping Charges\": 0.00,
    \"Actual Other Charges\": 3.50,
    \"CC Fees in Invoice\": null,
    \"Paypal / Pioneer Fee in invoice\": null,
    \"Actual Discount Received\": null,
    \"Gross Payable Price\": 19.50
  }
]"""
                    ),
                ],
            ),
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(
                        text="""in this invoice handling charges of 3.5 should have been applied equally across all items"""
                    ),
                ],
            ),
            types.Content(
                role="model",
                parts=[
                    types.Part.from_text(
                        text="""[
  {
    \"Invoice Date\": \"09/03/24\",
    \"Invoice Number\": \"207095\",
    \"PO Number\": \"SVST-20395\",
    \"PO Date\": \"09/03/24\",
    \"Actual Product Price\": 168.00,
    \"Actual Sales Tax Paid\": null,
    \"Actual Dropship Fees\": null,
    \"Actual Shipping Charges\": 0.00,
    \"Actual Other Charges\": 0.875,
    \"CC Fees in Invoice\": null,
    \"Paypal / Pioneer Fee in invoice\": null,
    \"Actual Discount Received\": null,
    \"Gross Payable Price\": 168.875
  },
  {
    \"Invoice Date\": \"09/03/24\",
    \"Invoice Number\": \"207095\",
    \"PO Number\": \"SVST-20396\",
    \"PO Date\": \"09/03/24\",
    \"Actual Product Price\": 86.00,
    \"Actual Sales Tax Paid\": null,
    \"Actual Dropship Fees\": null,
    \"Actual Shipping Charges\": 0.00,
    \"Actual Other Charges\": 0.875,
    \"CC Fees in Invoice\": null,
    \"Paypal / Pioneer Fee in invoice\": null,
    \"Actual Discount Received\": null,
    \"Gross Payable Price\": 86.875
  },
  {
    \"Invoice Date\": \"09/03/24\",
    \"Invoice Number\": \"207095\",
    \"PO Number\": \"SVST-20397\",
    \"PO Date\": \"09/03/24\",
    \"Actual Product Price\": 150.00,
    \"Actual Sales Tax Paid\": null,
    \"Actual Dropship Fees\": null,
    \"Actual Shipping Charges\": 0.00,
    \"Actual Other Charges\": 0.875,
    \"CC Fees in Invoice\": null,
    \"Paypal / Pioneer Fee in invoice\": null,
    \"Actual Discount Received\": null,
    \"Gross Payable Price\": 150.875
  },
  {
    \"Invoice Date\": \"09/03/24\",
    \"Invoice Number\": \"207095\",
    \"PO Number\": \"SVST-20398\",
    \"PO Date\": \"09/03/24\",
    \"Actual Product Price\": 16.00,
    \"Actual Sales Tax Paid\": null,
    \"Actual Dropship Fees\": null,
    \"Actual Shipping Charges\": 0.00,
    \"Actual Other Charges\": 0.875,
    \"CC Fees in Invoice\": null,
    \"Paypal / Pioneer Fee in invoice\": null,
    \"Actual Discount Received\": null,
    \"Gross Payable Price\": 16.875
  }
]"""
                    ),
                ],
            ),
            types.Content(
                role="user",
                parts=[
                    types.Part.from_uri(
                        file_uri=files[2].uri,
                        mime_type=files[2].mime_type,
                    ),
                    types.Part.from_text(text="""Process this invoice"""),
                ],
            ),
            types.Content(
                role="model",
                parts=[
                    types.Part.from_text(
                        text="""[
  {
    \"Invoice Date\": \"10/01/24\",
    \"Invoice Number\": \"82315\",
    \"PO Number\": \"MODE-1730\",
    \"PO Date\": \"2024-09-30\",
    \"Actual Product Price\": 37.50,
    \"Actual Sales Tax Paid\": 0.00,
    \"Actual Dropship Fees\": null,
    \"Actual Shipping Charges\": 0.00,
    \"Actual Other Charges\": 0.00,
    \"CC Fees in Invoice\": null,
    \"Paypal / Pioneer Fee in invoice\": null,
    \"Actual Discount Received\": 0.00,
    \"Gross Payable Price\": 37.50
  }
]"""
                    ),
                ],
            ),
            types.Content(
                role="user",
                parts=[
                    types.Part.from_uri(
                        file_uri=files[3].uri,
                        mime_type=files[3].mime_type,
                    ),
                    types.Part.from_uri(
                        file_uri=files[4].uri,
                        mime_type=files[4].mime_type,
                    ),
                    types.Part.from_uri(
                        file_uri=files[5].uri,
                        mime_type=files[5].mime_type,
                    ),
                    types.Part.from_text(text="""Process these invoices"""),
                ],
            ),
            types.Content(
                role="model",
                parts=[
                    types.Part.from_text(
                        text="""[
  {
    \"Invoice Date\": \"03/04/25\",
    \"Invoice Number\": \"408709\",
    \"PO Number\": \"RMMG-1033\",
    \"PO Date\": \"03/04/2025\",
    \"Actual Product Price\": 239.90,
    \"Actual Sales Tax Paid\": null,
    \"Actual Dropship Fees\": null,
    \"Actual Shipping Charges\": null,
    \"Actual Other Charges\": null,
    \"CC Fees in Invoice\": null,
    \"Paypal / Pioneer Fee in invoice\": null,
    \"Actual Discount Received\": null,
    \"Gross Payable Price\": 59.98
  },
  {
    \"Invoice Date\": \"03/04/25\",
    \"Invoice Number\": \"0934147\",
    \"PO Number\": \"000012460052\",
    \"PO Date\": null,
    \"Actual Product Price\": 52.08,
    \"Actual Sales Tax Paid\": 0.00,
    \"Actual Dropship Fees\": null,
    \"Actual Shipping Charges\": null,
    \"Actual Other Charges\": 51.56,
    \"CC Fees in Invoice\": null,
    \"Paypal / Pioneer Fee in invoice\": null,
    \"Actual Discount Received\": null,
    \"Gross Payable Price\": 85.54
  },
  {
    \"Invoice Date\": \"1/31/2025\",
    \"Invoice Number\": \"J2502-363\",
    \"PO Number\": \"SALES 2024\",
    \"PO Date\": null,
    \"Actual Product Price\": null,
    \"Actual Sales Tax Paid\": 0.00,
    \"Actual Dropship Fees\": null,
    \"Actual Shipping Charges\": 0.00,
    \"Actual Other Charges\": null,
    \"CC Fees in Invoice\": null,
    \"Paypal / Pioneer Fee in invoice\": null,
    \"Actual Discount Received\": null,
    \"Gross Payable Price\": 4956.80
  },
  {
    \"Invoice Date\": \"10/01/24\",
    \"Invoice Number\": \"82315\",
    \"PO Number\": \"MODE-1730\",
    \"PO Date\": null,
    \"Actual Product Price\": 37.50,
    \"Actual Sales Tax Paid\": 0.00,
    \"Actual Dropship Fees\": null,
    \"Actual Shipping Charges\": null,
    \"Actual Other Charges\": null,
    \"CC Fees in Invoice\": null,
    \"Paypal / Pioneer Fee in invoice\": null,
    \"Actual Discount Received\": 0.00,
    \"Gross Payable Price\": 37.50
  }
]"""
                    ),
                ],
            ),
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(
                        text="""In RMMG - you have missed the discount provided - 75% on 239.9, as mentioned earlier gross payable price is a computed field, all other fields have to be added and discount received field should be substracted.  In KEHE, the final invoice value is 51.56, the actual product price is 52.08, discount is 0.52, the amount mentioned as attached invoices is actually related to other invoices that may have been sent along with this invoice. and Pay this amount also is related to all invoices total. In case of KAHA, you see that generally the PO number is uses the prefix like in this case is KAHA (name of the document) and there what vendor has done is consolidated all the PO's mentioned PO in item description column and prepared single invoice. But we need to split for each PO number as our accounting system need invoice data PO number-wise """
                    ),
                ],
            ),
            types.Content(
                role="model",
                parts=[
                    types.Part.from_text(
                        text="""[
  {
    \"Invoice Date\": \"03/04/25\",
    \"Invoice Number\": \"408709\",
    \"PO Number\": \"RMMG-1033\",
    \"PO Date\": \"03/04/2025\",
    \"Actual Product Price\": 239.90,
    \"Actual Sales Tax Paid\": null,
    \"Actual Dropship Fees\": null,
    \"Actual Shipping Charges\": null,
    \"Actual Other Charges\": null,
    \"CC Fees in Invoice\": null,
    \"Paypal / Pioneer Fee in invoice\": null,
    \"Actual Discount Received\": 179.925,
    \"Gross Payable Price\": 59.98
  },
  {
    \"Invoice Date\": \"03/04/25\",
    \"Invoice Number\": \"0934147\",
    \"PO Number\": null,
    \"PO Date\": null,
    \"Actual Product Price\": 52.08,
    \"Actual Sales Tax Paid\": 0.00,
    \"Actual Dropship Fees\": null,
    \"Actual Shipping Charges\": null,
    \"Actual Other Charges\": null,
    \"CC Fees in Invoice\": null,
    \"Paypal / Pioneer Fee in invoice\": null,
    \"Actual Discount Received\": 0.00,
    \"Gross Payable Price\": 52.08
  },
  {
    \"Invoice Date\": \"1/31/2025\",
    \"Invoice Number\": \"J2502-363\",
    \"PO Number\": \"SALES 2024 09-12\",
    \"PO Date\": null,
    \"Actual Product Price\": null,
    \"Actual Sales Tax Paid\": 0.00,
    \"Actual Dropship Fees\": null,
    \"Actual Shipping Charges\": 0.00,
    \"Actual Other Charges\": null,
    \"CC Fees in Invoice\": null,
    \"Paypal / Pioneer Fee in invoice\": null,
    \"Actual Discount Received\": null,
    \"Gross Payable Price\": 4956.80
  },
  {
    \"Invoice Date\": \"10/01/24\",
    \"Invoice Number\": \"82315\",
    \"PO Number\": \"MODE-1730\",
    \"PO Date\": null,
    \"Actual Product Price\": 37.50,
    \"Actual Sales Tax Paid\": 0.00,
    \"Actual Dropship Fees\": null,
    \"Actual Shipping Charges\": null,
    \"Actual Other Charges\": null,
    \"CC Fees in Invoice\": null,
    \"Paypal / Pioneer Fee in invoice\": null,
    \"Actual Discount Received\": 0.00,
    \"Gross Payable Price\": 37.50
  }
]"""
                    ),
                ],
            ),
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(
                        text="""you did not split J2502-363 into each PO item (mentioned as item description)"""
                    ),
                ],
            ),
            types.Content(
                role="model",
                parts=[
                    types.Part.from_text(
                        text="""[
  {
    \"Invoice Date\": \"03/04/25\",
    \"Invoice Number\": \"408709\",
    \"PO Number\": \"RMMG-1033\",
    \"PO Date\": \"03/04/2025\",
    \"Actual Product Price\": 239.90,
    \"Actual Sales Tax Paid\": null,
    \"Actual Dropship Fees\": null,
    \"Actual Shipping Charges\": null,
    \"Actual Other Charges\": null,
    \"CC Fees in Invoice\": null,
    \"Paypal / Pioneer Fee in invoice\": null,
    \"Actual Discount Received\": 179.925,
    \"Gross Payable Price\": 59.98
  },
  {
    \"Invoice Date\": \"03/04/25\",
    \"Invoice Number\": \"0934147\",
    \"PO Number\": null,
    \"PO Date\": null,
    \"Actual Product Price\": 52.08,
    \"Actual Sales Tax Paid\": 0.00,
    \"Actual Dropship Fees\": null,
    \"Actual Shipping Charges\": null,
    \"Actual Other Charges\": null,
    \"CC Fees in Invoice\": null,
    \"Paypal / Pioneer Fee in invoice\": null,
    \"Actual Discount Received\": 0.00,
    \"Gross Payable Price\": 52.08
  },
{
\"Invoice Date\": \"1/31/2025\",
\"Invoice Number\": \"J2502-363\",
\"PO Number\": \"SALES 2024 09-12\",
\"PO Date\": null,
\"Actual Product Price\": 49.00,
\"Actual Sales Tax Paid\": 0.00,
\"Actual Dropship Fees\": null,
\"Actual Shipping Charges\": 0.00,
\"Actual Other Charges\": null,
\"CC Fees in Invoice\": null,
\"Paypal / Pioneer Fee in invoice\": null,
\"Actual Discount Received\": null,
\"Gross Payable Price\": 49.00
  },
 {
\"Invoice Date\": \"1/31/2025\",
\"Invoice Number\": \"J2502-363\",
\"PO Number\": \"SALES 2024 09-12\",
\"PO Date\": null,
\"Actual Product Price\": 31.00,
\"Actual Sales Tax Paid\": 0.00,
\"Actual Dropship Fees\": null,
\"Actual Shipping Charges\": 0.00,
\"Actual Other Charges\": null,
\"CC Fees in Invoice\": null,
\"Paypal / Pioneer Fee in invoice\": null,
\"Actual Discount Received\": null,
\"Gross Payable Price\": 31.00
  },
   {
\"Invoice Date\": \"1/31/2025\",
\"Invoice Number\": \"J2502-363\",
\"PO Number\": \"SALES 2024 09-12\",
\"PO Date\": null,
\"Actual Product Price\": 23.50,
\"Actual Sales Tax Paid\": 0.00,
\"Actual Dropship Fees\": null,
\"Actual Shipping Charges\": 0.00,
\"Actual Other Charges\": null,
\"CC Fees in Invoice\": null,
\"Paypal / Pioneer Fee in invoice\": null,
\"Actual Discount Received\": null,
\"Gross Payable Price\": 23.50
  },
{
\"Invoice Date\": \"1/31/2025\",
\"Invoice Number\": \"J2502-363\",
\"PO Number\": \"SALES 2024 09-12\",
\"PO Date\": null,
\"Actual Product Price\": 16.00,
\"Actual Sales Tax Paid\": 0.00,
\"Actual Dropship Fees\": null,
\"Actual Shipping Charges\": 0.00,
\"Actual Other Charges\": null,
\"CC Fees in Invoice\": null,
\"Paypal / Pioneer Fee in invoice\": null,
\"Actual Discount Received\": null,
\"Gross Payable Price\": 16.00
  },
 {
\"Invoice Date\": \"1/31/2025\",
\"Invoice Number\": \"J2502-363\",
\"PO Number\": \"SALES 2024 09-12\",
\"PO Date\": null,
\"Actual Product Price\": 31.00,
\"Actual Sales Tax Paid\": 0.00,
\"Actual Dropship Fees\": null,
\"Actual Shipping Charges\": 0.00,
\"Actual Other Charges\": null,
\"CC Fees in Invoice\": null,
\"Paypal / Pioneer Fee in invoice\": null,
\"Actual Discount Received\": null,
\"Gross Payable Price\": 31.00
  },
  {
\"Invoice Date\": \"1/31/2025\",
\"Invoice Number\": \"J2502-363\",
\"PO Number\": \"SALES 2024 09-12\",
\"PO Date\": null,
\"Actual Product Price\": 29.50,
\"Actual Sales Tax Paid\": 0.00,
\"Actual Dropship Fees\": null,
\"Actual Shipping Charges\": 0.00,
\"Actual Other Charges\": null,
\"CC Fees in Invoice\": null,
\"Paypal / Pioneer Fee in invoice\": null,
\"Actual Discount Received\": null,
\"Gross Payable Price\": 29.50
  },
{
\"Invoice Date\": \"1/31/2025\",
\"Invoice Number\": \"J2502-363\",
\"PO Number\": \"SALES 2024 09-12\",
\"PO Date\": null,
\"Actual Product Price\": 29.50,
\"Actual Sales Tax Paid\": 0.00,
\"Actual Dropship Fees\": null,
\"Actual Shipping Charges\": 0.00,
\"Actual Other Charges\": null,
\"CC Fees in Invoice\": null,
\"Paypal / Pioneer Fee in invoice\": null,
\"Actual Discount Received\": null,
\"Gross Payable Price\": 29.50
  },
   {
\"Invoice Date\": \"1/31/2025\",
\"Invoice Number\": \"J2502-363\",
\"PO Number\": \"SALES 2024 09-12\",
\"PO Date\": null,
\"Actual Product Price\": 23.50,
\"Actual Sales Tax Paid\": 0.00,
\"Actual Dropship Fees\": null,
\"Actual Shipping Charges\": 0.00,
\"Actual Other Charges\": null,
\"CC Fees in Invoice\": null,
\"Paypal / Pioneer Fee in invoice\": null,
\"Actual Discount Received\": null,
\"Gross Payable Price\": 23.50
  },
{
\"Invoice Date\": \"1/31/2025\",
\"Invoice Number\": \"J2502-363\",
\"PO Number\": \"SALES 2024 09-12\",
\"PO Date\": null,
\"Actual Product Price\": 23.50,
\"Actual Sales Tax Paid\": 0.00,
\"Actual Dropship Fees\": null,
\"Actual Shipping Charges\": 0.00,
\"Actual Other Charges\": null,
\"CC Fees in Invoice\": null,
\"Paypal / Pioneer Fee in invoice\": null,
\"Actual Discount Received\": null,
\"Gross Payable Price\": 23.50
  },
   {
\"Invoice Date\": \"1/31/2025\",
\"Invoice Number\": \"J2502-363\",
\"PO Number\": \"SALES 2024 09-12\",
\"PO Date\": null,
\"Actual Product Price\": 29.50,
\"Actual Sales Tax Paid\": 0.00,
\"Actual Dropship Fees\": null,
\"Actual Shipping Charges\": 0.00,
\"Actual Other Charges\": null,
\"CC Fees in Invoice\": null,
\"Paypal / Pioneer Fee in invoice\": null,
\"Actual Discount Received\": null,
\"Gross Payable Price\": 29.50
  },
  {
\"Invoice Date\": \"1/31/2025\",
\"Invoice Number\": \"J2502-363\",
\"PO Number\": \"SALES 2024 09-12\",
\"PO Date\": null,
\"Actual Product Price\": 26.80,
\"Actual Sales Tax Paid\": 0.00,
\"Actual Dropship Fees\": null,
\"Actual Shipping Charges\": 0.00,
\"Actual Other Charges\": null,
\"CC Fees in Invoice\": null,
\"Paypal / Pioneer Fee in invoice\": null,
\"Actual Discount Received\": null,
\"Gross Payable Price\": 26.80
  },
  {
\"Invoice Date\": \"1/31/2025\",
\"Invoice Number\": \"J2502-363\",
\"PO Number\": \"SALES 2024 09-12\",
\"PO Date\": null,
\"Actual Product Price\": 22.00,
\"Actual Sales Tax Paid\": 0.00,
\"Actual Dropship Fees\": null,
\"Actual Shipping Charges\": 0.00,
\"Actual Other Charges\": null,
\"CC Fees in Invoice\": null,
\"Paypal / Pioneer Fee in invoice\": null,
\"Actual Discount Received\": null,
\"Gross Payable Price\": 22.00
  },
   {
\"Invoice Date\": \"1/31/2025\",
\"Invoice Number\": \"J2502-363\",
\"PO Number\": \"SALES 2024 09-12\",
\"PO Date\": null,
\"Actual Product Price\": 26.80,
\"Actual Sales Tax Paid\": 0.00,
\"Actual Dropship Fees\": null,
\"Actual Shipping Charges\": 0.00,
\"Actual Other Charges\": null,
\"CC Fees in Invoice\": null,
\"Paypal / Pioneer Fee in invoice\": null,
\"Actual Discount Received\": null,
\"Gross Payable Price\": 26.80
  },
  {
\"Invoice Date\": \"1/31/2025\",
\"Invoice Number\": \"J2502-363\",
\"PO Number\": \"SALES 2024 09-12\",
\"PO Date\": null,
\"Actual Product Price\": 29.50,
\"Actual Sales Tax Paid\": 0.00,
\"Actual Dropship Fees\": null,
\"Actual Shipping Charges\": 0.00,
\"Actual Other Charges\": null,
\"CC Fees in Invoice\": null,
\"Paypal / Pioneer Fee in invoice\": null,
\"Actual Discount Received\": null,
\"Gross Payable Price\": 29.50
  },
   {
\"Invoice Date\": \"1/31/2025\",
\"Invoice Number\": \"J2502-363\",
\"PO Number\": \"SALES 2024 09-12\",
\"PO Date\": null,
\"Actual Product Price\": 26.50,
\"Actual Sales Tax Paid\": 0.00,
\"Actual Dropship Fees\": null,
\"Actual Shipping Charges\": 0.00,
\"Actual Other Charges\": null,
\"CC Fees in Invoice\": null,
\"Paypal / Pioneer Fee in invoice\": null,
\"Actual Discount Received\": null,
\"Gross Payable Price\": 26.50
  },
 {
\"Invoice Date\": \"1/31/2025\",
\"Invoice Number\": \"J2502-363\",
\"PO Number\": \"SALES 2024 09-12\",
\"PO Date\": null,
\"Actual Product Price\": 23.50,
\"Actual Sales Tax Paid\": 0.00,
\"Actual Dropship Fees\": null,
\"Actual Shipping Charges\": 0.00,
\"Actual Other Charges\": null,
\"CC Fees in Invoice\": null,
\"Paypal / Pioneer Fee in invoice\": null,
\"Actual Discount Received\": null,
\"Gross Payable Price\": 23.50
  },
  {
\"Invoice Date\": \"1/31/2025\",
\"Invoice Number\": \"J2502-363\",
\"PO Number\": \"SALES 2024 09-12\",
\"PO Date\": null,
\"Actual Product Price\": 31.00,
\"Actual Sales Tax Paid\": 0.00,
\"Actual Dropship Fees\": null,
\"Actual Shipping Charges\": 0.00,
\"Actual Other Charges\": null,
\"CC Fees in Invoice\": null,
\"Paypal / Pioneer Fee in invoice\": null,
\"Actual Discount Received\": null,
\"Gross Payable Price\": 31.00
  },
 {
\"Invoice Date\": \"1/31/2025\",
\"Invoice Number\": \"J2502-363\",
\"PO Number\": \"SALES 2024 09-12\",
\"PO Date\": null,
\"Actual Product Price\": 26.80,
\"Actual Sales Tax Paid\": 0.00,
\"Actual Dropship Fees\": null,
\"Actual Shipping Charges\": 0.00,
\"Actual Other Charges\": null,
\"CC Fees in Invoice\": null,
\"Paypal / Pioneer Fee in invoice\": null,
\"Actual Discount Received\": null,
\"Gross Payable Price\": 26.80
  },
   {
\"Invoice Date\": \"1/31/2025\",
\"Invoice Number\": \"J2502-363\",
\"PO Number\": \"SALES 2024 09-12\",
\"PO Date\": null,
\"Actual Product Price\": 25.00,
\"Actual Sales Tax Paid\": 0.00,
\"Actual Dropship Fees\": null,
\"Actual Shipping Charges\": 0.00,
\"Actual Other Charges\": null,
\"CC Fees in Invoice\": null,
\"Paypal / Pioneer Fee in invoice\": null,
\"Actual Discount Received\": null,
\"Gross Payable Price\": 25.00
  },
  {
\"Invoice Date\": \"1/31/2025\",
\"Invoice Number\": \"J2502-363\",
\"PO Number\": \"SALES 2024 09-12\",
\"PO Date\": null,
\"Actual Product Price\": 32.00,
\"Actual Sales Tax Paid\": 0.00,
\"Actual Dropship Fees\": null,
\"Actual Shipping Charges\": 0.00,
\"Actual Other Charges\": null,
\"CC Fees in Invoice\": null,
\"Paypal / Pioneer Fee in invoice\": null,
\"Actual Discount Received\": null,
\"Gross Payable Price\": 32.00
  },
  {
\"Invoice Date\": \"1/31/2025\",
\"Invoice Number\": \"J2502-363\",
\"PO Number\": \"SALES 2024 09-12\",
\"PO Date\": null,
\"Actual Product Price\": 23.50,
\"Actual Sales Tax Paid\": 0.00,
\"Actual Dropship Fees\": null,
\"Actual Shipping Charges\": 0.00,
\"Actual Other Charges\": null,
\"CC Fees in Invoice\": null,
\"Paypal / Pioneer Fee in invoice\": null,
\"Actual Discount Received\": null,
\"Gross Payable Price\": 23.50
  },
   {
\"Invoice Date\": \"1/31/2025\",
\"Invoice Number\": \"J2502-363\",
\"PO Number\": \"SALES 2024 09-12\",
\"PO Date\": null,
\"Actual Product Price\": 26.80,
\"Actual Sales Tax Paid\": 0.00,
\"Actual Dropship Fees\": null,
\"Actual Shipping Charges\": 0.00,
\"Actual Other Charges\": null,
\"CC Fees in Invoice\": null,
\"Paypal / Pioneer Fee in invoice\": null,
\"Actual Discount Received\": null,
\"Gross Payable Price\": 26.80
  },
{
\"Invoice Date\": \"1/31/2025\",
\"Invoice Number\": \"J2502-363\",
\"PO Number\": \"SALES 2024 09-12\",
\"PO Date\": null,
\"Actual Product Price\": 23.50,
\"Actual Sales Tax Paid\": 0.00,
\"Actual Dropship Fees\": null,
\"Actual Shipping Charges\": 0.00,
\"Actual Other Charges\": null,
\"CC Fees in Invoice\": null,
\"Paypal / Pioneer Fee in invoice\": null,
\"Actual Discount Received\": null,
\"Gross Payable Price\": 23.50
  },
   {
\"Invoice Date\": \"1/31/2025\",
\"Invoice Number\": \"J2502-363\",
\"PO Number\": \"SALES 2024 09-12\",
\"PO Date\": null,
\"Actual Product Price\": 22.00,
\"Actual Sales Tax Paid\": 0.00,
\"Actual Dropship Fees\": null,
\"Actual Shipping Charges\": 0.00,
\"Actual Other Charges\": null,
\"CC Fees in Invoice\": null,
\"Paypal / Pioneer Fee in invoice\": null,
\"Actual Discount Received\": null,
\"Gross Payable Price\": 22.00
  },
 {
\"Invoice Date\": \"1/31/2025\",
\"Invoice Number\": \"J2502-363\",
\"PO Number\": \"SALES 2024 09-12\",
\"PO Date\": null,
\"Actual Product Price\": 43.00,
\"Actual Sales Tax Paid\": 0.00,
\"Actual Dropship Fees\": null,
\"Actual Shipping Charges\": 0.00,
\"Actual Other Charges\": null,
\"CC Fees in Invoice\": null,
\"Paypal / Pioneer Fee in invoice\": null,
\"Actual Discount Received\": null,
\"Gross Payable Price\": 43.00
  },
  {
\"Invoice Date\": \"1/31/2025\",
\"Invoice Number\": \"J2502-363\",
\"PO Number\": \"SALES 2024 09-12\",
\"PO Date\": null,
\"Actual Product Price\": 43.00,
\"Actual Sales Tax Paid\": 0.00,
\"Actual Dropship Fees\": null,
\"Actual Shipping Charges\": 0.00,
\"Actual Other Charges\": null,
\"CC Fees in Invoice\": null,
\"Paypal / Pioneer Fee in invoice\": null,
\"Actual Discount Received\": null,
\"Gross Payable Price\": 43.00
  },
 {
\"Invoice Date\": \"1/31/2025\",
\"Invoice Number\": \"J2502-363\",
\"PO Number\": \"SALES 2024 09-12\",
\"PO Date\": null,
\"Actual Product Price\": 26.80,
\"Actual Sales Tax Paid\": 0.00,
\"Actual Dropship Fees\": null,
\"Actual Shipping Charges\": 0.00,
\"Actual Other Charges\": null,
\"CC Fees in Invoice\": null,
\"Paypal / Pioneer Fee in invoice\": null,
\"Actual Discount Received\": null,
\"Gross Payable Price\": 26.80
  },
  {
\"Invoice Date\": \"1/31/2025\",
\"Invoice Number\": \"J2502-363\",
\"PO Number\": \"SALES 2024 09-12\",
\"PO Date\": null,
\"Actual Product Price\": 19.00,
\"Actual Sales Tax Paid\": 0.00,
\"Actual Dropship Fees\": null,
\"Actual Shipping Charges\": 0.00,
\"Actual Other Charges\": null,
\"CC Fees in Invoice\": null,
\"Paypal / Pioneer Fee in invoice\": null,
\"Actual Discount Received\": null,
\"Gross Payable Price\": 19.00
  },
   {
\"Invoice Date\": \"1/31/2025\",
\"Invoice Number\": \"J2502-363\",
\"PO Number\": \"SALES 2024 09-12\",
\"PO Date\": null,
\"Actual Product Price\": 23.50,
\"Actual Sales Tax Paid\": 0.00,
\"Actual Dropship Fees\": null,
\"Actual Shipping Charges\": 0.00,
\"Actual Other Charges\": null,
\"CC Fees in Invoice\": null,
\"Paypal / Pioneer Fee in invoice\": null,
\"Actual Discount Received\": null,
\"Gross Payable Price\": 23.50
  },
{
\"Invoice Date\": \"1/31/2025\",
\"Invoice Number\": \"J2502-363\",
\"PO Number\": \"SALES 2024 09-12\",
\"PO Date\": null,
\"Actual Product Price\": 31.00,
\"Actual Sales Tax Paid\": 0.00,
\"Actual Dropship Fees\": null,
\"Actual Shipping Charges\": 0.00,
\"Actual Other Charges\": null,
\"CC Fees in Invoice\": null,
\"Paypal / Pioneer Fee in invoice\": null,
\"Actual Discount Received\": null,
\"Gross Payable Price\": 31.00
  },
   {
\"Invoice Date\": \"1/31/2025\",
\"Invoice Number\": \"J2502-363\",
\"PO Number\": \"SALES 2024 09-12\",
\"PO Date\": null,
\"Actual Product Price\": 46.00,
\"Actual Sales Tax Paid\": 0.00,
\"Actual Dropship Fees\": null,
\"Actual Shipping Charges\": 0.00,
\"Actual Other Charges\": null,
\"CC Fees in Invoice\": null,
\"Paypal / Pioneer Fee in invoice\": null,
\"Actual Discount Received\": null,
\"Gross Payable Price\": 46.00
  },
   {
\"Invoice Date\": \"1/31/2025\",
\"Invoice Number\": \"J2502-363\",
\"PO Number\": \"SALES 2024 09-12\",
\"PO Date\": null,
\"Actual Product Price\": 22.00,
\"Actual Sales Tax Paid\": 0.00,
\"Actual Dropship Fees\": null,
\"Actual Shipping Charges\": 0.00,
\"Actual Other Charges\": null,
\"CC Fees in Invoice\": null,
\"Paypal / Pioneer Fee in invoice\": null,
\"Actual Discount Received\": null,
\"Gross Payable Price\": 22.00
  },
  {
\"Invoice Date\": \"1/31/2025\",
\"Invoice Number\": \"J2502-363\",
\"PO Number\": \"SALES 2024 09-12\",
\"PO Date\": null,
\"Actual Product Price\": 26.50,
\"Actual Sales Tax Paid\": 0.00,
\"Actual Dropship Fees\": null,
\"Actual Shipping Charges\": 0.00,
\"Actual Other Charges\": null,
\"CC Fees in Invoice\": null,
\"Paypal / Pioneer Fee in invoice\": null,
\"Actual Discount Received\": null,
\"Gross Payable Price\": 26.50
  },
   {
\"Invoice Date\": \"1/31/2025\",
\"Invoice Number\": \"J2502-363\",
\"PO Number\": \"SALES 2024 09-12\",
\"PO Date\": null,
\"Actual Product Price\": 46.00,
\"Actual Sales Tax Paid\": 0.00,
\"Actual Dropship Fees\": null,
\"Actual Shipping Charges\": 0.00,
\"Actual Other Charges\": null,
\"CC Fees in Invoice\": null,
\"Paypal / Pioneer Fee in invoice\": null,
\"Actual Discount Received\": null,
\"Gross Payable Price\": 46.00
  },
  {
\"Invoice Date\": \"1/31/2025\",
\"Invoice Number\": \"J2502-363\",
\"PO Number\": \"SALES 2024 09-12\",
\"PO Date\": null,
\"Actual Product Price\": 29.50,
\"Actual Sales Tax Paid\": 0.00,
\"Actual Dropship Fees\": null,
\"Actual Shipping Charges\": 0.00,
\"Actual Other Charges\": null,
\"CC Fees in Invoice\": null,
\"Paypal / Pioneer Fee in invoice\": null,
\"Actual Discount Received\": null,
\"Gross Payable Price\": 29.50
  },
   {
\"Invoice Date\": \"1/31/2025\",
\"Invoice Number\": \"J2502-363\",
\"PO Number\": \"SALES 2024 09-12\",
\"PO Date\": null,
\"Actual Product Price\": 19.60,
\"Actual Sales Tax Paid\": 0.00,
\"Actual Dropship Fees\": null,
\"Actual Shipping Charges\": 0.00,
\"Actual Other Charges\": null,
\"CC Fees in Invoice\": null,
\"Paypal / Pioneer Fee in invoice\": null,
\"Actual Discount Received\": null,
\"Gross Payable Price\": 19.60
  },
   {
\"Invoice Date\": \"1/31/2025\",
\"Invoice Number\": \"J2502-363\",
\"PO Number\": \"SALES 2024 09-12\",
\"PO Date\": null,
\"Actual Product Price\": 30.40,
\"Actual Sales Tax Paid\": 0.00,
\"Actual Dropship Fees\": null,
\"Actual Shipping Charges\": 0.00,
\"Actual Other Charges\": null,
\"CC Fees in Invoice\": null,
\"Paypal / Pioneer Fee in invoice\": null,
\"Actual Discount Received\": null,
\"Gross Payable Price\": 30.40
  },
  {
\"Invoice Date\": \"1/31/2025\",
\"Invoice Number\": \"J2502-363\",
\"PO Number\": \"SALES 2024 09-12\",
\"PO Date\": null,
\"Actual Product Price\": 22.00,
\"Actual Sales Tax Paid\": 0.00,
\"Actual Dropship Fees\": null,
\"Actual Shipping Charges\": 0.00,
\"Actual Other Charges\": null,
\"CC Fees in Invoice\": null,
\"Paypal / Pioneer Fee in invoice\": null,
\"Actual Discount Received\": null,
\"Gross Payable Price\": 22.00
  },
 {
\"Invoice Date\": \"1/31/2025\",
\"Invoice Number\": \"J2502-363\",
\"PO Number\": \"SALES 2024 09-12\",
\"PO Date\": null,
\"Actual Product Price\": 19.60,
\"Actual Sales Tax Paid\": 0.00,
\"Actual Dropship Fees\": null,
\"Actual Shipping Charges\": 0.00,
\"Actual Other Charges\": null,
\"CC Fees in Invoice\": null,
\"Paypal / Pioneer Fee in invoice\": null,
\"Actual Discount Received\": null,
\"Gross Payable Price\": 19.60
  },
  {
\"Invoice Date\": \"1/31/2025\",
\"Invoice Number\": \"J2502-363\",
\"PO Number\": \"SALES 2024 09-12\",
\"PO Date\": null,
\"Actual Product Price\": 29.50,
\"Actual Sales Tax Paid\": 0.00,
\"Actual Dropship Fees\": null,
\"Actual Shipping Charges\": 0.00,
\"Actual Other Charges\": null,
\"CC Fees in Invoice\": null,
\"Paypal / Pioneer Fee in invoice\": null,
\"Actual Discount Received\": null,
\"Gross Payable Price\": 29.50
  },
   {
\"Invoice Date\": \"1/31/2025\",
\"Invoice Number\": \"J2502-363\",
\"PO Number\": \"SALES 2024 09-12\",
\"PO Date\": null,
\"Actual Product Price\": 23.50,
\"Actual Sales Tax Paid\": 0.00,
\"Actual Dropship Fees\": null,
\"Actual Shipping Charges\": 0.00,
\"Actual Other Charges\": null,
\"CC Fees in Invoice\": null,
\"Paypal / Pioneer Fee in invoice\": null,
\"Actual Discount Received\": null,
\"Gross Payable Price\": 23.50
  },
{
\"Invoice Date\": \"1/31/2025\",
\"Invoice Number\": \"J2502-363\",
\"PO Number\": \"SALES 2024 09-12\",
\"PO Date\": null,
\"Actual Product Price\": 29.50,
\"Actual Sales Tax Paid\": 0.00,
\"Actual Dropship Fees\": null,
\"Actual Shipping Charges\": 0.00,
\"Actual Other Charges\": null,
\"CC Fees in Invoice\": null,
\"Paypal / Pioneer Fee in invoice\": null,
\"Actual Discount Received\": null,
\"Gross Payable Price\": 29.50
  },
   {
\"Invoice Date\": \"1/31/2025\",
\"Invoice Number\": \"J2502-363\",
\"PO Number\": \"SALES 2024 09-12\",
\"PO Date\": null,
\"Actual Product Price\": 23.50,
\"Actual Sales Tax Paid\": 0.00,
\"Actual Dropship Fees\": null,
\"Actual Shipping Charges\": 0.00,
\"Actual Other Charges\": null,
\"CC Fees in Invoice\": null,
\"Paypal / Pioneer Fee in invoice\": null,
\"Actual Discount Received\": null,
\"Gross Payable Price\": 23.50
  },
  {
\"Invoice Date\": \"1/31/2025\",
\"Invoice Number\": \"J2502-363\",
\"PO Number\": \"SALES 2024 09-12\",
\"PO Date\": null,
\"Actual Product Price\": 25.00,
\"Actual Sales Tax Paid\": 0.00,
\"Actual Dropship Fees\": null,
\"Actual Shipping Charges\": 0.00,
\"Actual Other Charges\": null,
\"CC Fees in Invoice\": null,
\"Paypal / Pioneer Fee in invoice\": null,
\"Actual Discount Received\": null,
\"Gross Payable Price\": 25.00
  },
  {
\"Invoice Date\": \"1/31/2025\",
\"Invoice Number\": \"J2502-363\",
\"PO Number\": \"SALES 2024 09-12\",
\"PO Date\": null,
\"Actual Product Price\": 26.80,
\"Actual Sales Tax Paid\": 0.00,
\"Actual Dropship Fees\": null,
\"Actual Shipping Charges\": 0.00,
\"Actual Other Charges\": null,
\"CC Fees in Invoice\": null,
\"Paypal / Pioneer Fee in invoice\": null,
\"Actual Discount Received\": null,
\"Gross Payable Price\": 26.80
  },
  {
\"Invoice Date\": \"1/31/2025\",
\"Invoice Number\": \"J2502-363\",
\"PO Number\": \"SALES 2024 09-12\",
\"PO Date\": null,
\"Actual Product Price\": 22.00,
\"Actual Sales Tax Paid\": 0.00,
\"Actual Dropship Fees\": null,
\"Actual Shipping Charges\": 0.00,
\"Actual Other Charges\": null,
\"CC Fees in Invoice\": null,
\"Paypal / Pioneer Fee in invoice\": null,
\"Actual Discount Received\": null,
\"Gross Payable Price\": 22.00
  },
   {
\"Invoice Date\": \"1/31/2025\",
\"Invoice Number\": \"J2502-363\",
\"PO Number\": \"SALES 2024 09-12\",
\"PO Date\": null,
\"Actual Product Price\": 53.60,
\"Actual Sales Tax Paid\": 0.00,
\"Actual Dropship Fees\": null,
\"Actual Shipping Charges\": 0.00,
\"Actual Other Charges\": null,
\"CC Fees in Invoice\": null,
\"Paypal / Pioneer Fee in invoice\": null,
\"Actual Discount Received\": null,
\"Gross Payable Price\": 53.60
  },
  {
\"Invoice Date\": \"1/31/2025\",
\"Invoice Number\": \"J2502-363\",
\"PO Number\": \"SALES 2024 09-12\",
\"PO Date\": null,
\"Actual Product Price\": 29.50,
\"Actual Sales Tax Paid\": 0.00,
\"Actual Dropship Fees\": null,
\"Actual Shipping Charges\": 0.00,
\"Actual Other Charges\": null,
\"CC Fees in Invoice\": null,
\"Paypal / Pioneer Fee in invoice\": null,
\"Actual Discount Received\": null,
\"Gross Payable Price\": 29.50
  },
  {
\"Invoice Date\": \"1/31/2025\",
\"Invoice Number\": \"J2502-363\",
\"PO Number\": \"SALES 2024 09-12\",
\"PO Date\": null,
\"Actual Product Price\": 31.00,
\"Actual Sales Tax Paid\": 0.00,
\"Actual Dropship Fees\": null,
\"Actual Shipping Charges\": 0.00,
\"Actual Other Charges\": null,
\"CC Fees in Invoice\": null,
\"Paypal / Pioneer Fee in invoice\": null,
\"Actual Discount Received\":"""
                    ),
                ],
            ),
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(
                        text="""PO number should be picked from item description, also if you are not able to complete the entire invoice in one output can you split the output to complete the entire invoice using memory."""
                    ),
                ],
            ),
            types.Content(
                role="model",
                parts=[
                    types.Part.from_text(
                        text="""[
  {
    \"Invoice Date\": \"03/04/25\",
    \"Invoice Number\": \"408709\",
    \"PO Number\": \"RMMG-1033\",
    \"PO Date\": \"03/04/2025\",
    \"Actual Product Price\": 239.90,
    \"Actual Sales Tax Paid\": null,
    \"Actual Dropship Fees\": null,
    \"Actual Shipping Charges\": null,
    \"Actual Other Charges\": null,
    \"CC Fees in Invoice\": null,
    \"Paypal / Pioneer Fee in invoice\": null,
    \"Actual Discount Received\": 179.925,
    \"Gross Payable Price\": 59.98
  },
  {
    \"Invoice Date\": \"03/04/25\",
    \"Invoice Number\": \"0934147\",
    \"PO Number\": null,
    \"PO Date\": null,
    \"Actual Product Price\": 52.08,
    \"Actual Sales Tax Paid\": 0.00,
    \"Actual Dropship Fees\": null,
    \"Actual Shipping Charges\": null,
    \"Actual Other Charges\": null,
    \"CC Fees in Invoice\": null,
    \"Paypal / Pioneer Fee in invoice\": null,
    \"Actual Discount Received\": 0.00,
    \"Gross Payable Price\": 52.08
  },
  {
    \"Invoice Date\": \"1/31/2025\",
    \"Invoice Number\": \"J2502-363\",
    \"PO Number\": \"KAHA-1132\",
    \"PO Date\": null,
    \"Actual Product Price\": 49.00,
    \"Actual Sales Tax Paid\": 0.00,
    \"Actual Dropship Fees\": null,
    \"Actual Shipping Charges\": 0.00,
    \"Actual Other Charges\": null,
    \"CC Fees in Invoice\": null,
    \"Paypal / Pioneer Fee in invoice\": null,
    \"Actual Discount Received\": null,
    \"Gross Payable Price\": 49.00
  },
  {
    \"Invoice Date\": \"1/31/2025\",
    \"Invoice Number\": \"J2502-363\",
    \"PO Number\": \"KAHA-1133\",
    \"PO Date\": null,
    \"Actual Product Price\": 31.00,
    \"Actual Sales Tax Paid\": 0.00,
    \"Actual Dropship Fees\": null,
    \"Actual Shipping Charges\": 0.00,
    \"Actual Other Charges\": null,
    \"CC Fees in Invoice\": null,
    \"Paypal / Pioneer Fee in invoice\": null,
    \"Actual Discount Received\": null,
    \"Gross Payable Price\": 31.00
  },
  {
    \"Invoice Date\": \"1/31/2025\",
    \"Invoice Number\": \"J2502-363\",
    \"PO Number\": \"KAHA-1134\",
    \"PO Date\": null,
    \"Actual Product Price\": 23.50,
    \"Actual Sales Tax Paid\": 0.00,
    \"Actual Dropship Fees\": null,
    \"Actual Shipping Charges\": 0.00,
    \"Actual Other Charges\": null,
    \"CC Fees in Invoice\": null,
    \"Paypal / Pioneer Fee in invoice\": null,
    \"Actual Discount Received\": null,
    \"Gross Payable Price\": 23.50
  },
  {
    \"Invoice Date\": \"1/31/2025\",
    \"Invoice Number\": \"J2502-363\",
    \"PO Number\": \"KAHA-1135\",
    \"PO Date\": null,
    \"Actual Product Price\": 16.00,
    \"Actual Sales Tax Paid\": 0.00,
    \"Actual Dropship Fees\": null,
    \"Actual Shipping Charges\": 0.00,
    \"Actual Other Charges\": null,
    \"CC Fees in Invoice\": null,
    \"Paypal / Pioneer Fee in invoice\": null,
    \"Actual Discount Received\": null,
    \"Gross Payable Price\": 16.00
  },
  {
    \"Invoice Date\": \"1/31/2025\",
    \"Invoice Number\": \"J2502-363\",
    \"PO Number\": \"KAHA-1136\",
    \"PO Date\": null,
    \"Actual Product Price\": 31.00,
    \"Actual Sales Tax Paid\": 0.00,
    \"Actual Dropship Fees\": null,
    \"Actual Shipping Charges\": 0.00,
    \"Actual Other Charges\": null,
    \"CC Fees in Invoice\": null,
    \"Paypal / Pioneer Fee in invoice\": null,
    \"Actual Discount Received\": null,
    \"Gross Payable Price\": 31.00
  },
  {
    \"Invoice Date\": \"1/31/2025\",
    \"Invoice Number\": \"J2502-363\",
    \"PO Number\": \"KAHA-1137\",
    \"PO Date\": null,
    \"Actual Product Price\": 29.50,
    \"Actual Sales Tax Paid\": 0.00,
    \"Actual Dropship Fees\": null,
    \"Actual Shipping Charges\": 0.00,
    \"Actual Other Charges\": null,
    \"CC Fees in Invoice\": null,
    \"Paypal / Pioneer Fee in invoice\": null,
    \"Actual Discount Received\": null,
    \"Gross Payable Price\": 29.50
  },
  {
    \"Invoice Date\": \"1/31/2025\",
    \"Invoice Number\": \"J2502-363\",
    \"PO Number\": \"KAHA-1138\",
    \"PO Date\": null,
    \"Actual Product Price\": 29.50,
    \"Actual Sales Tax Paid\": 0.00,
    \"Actual Dropship Fees\": null,
    \"Actual Shipping Charges\": 0.00,
    \"Actual Other Charges\": null,
    \"CC Fees in Invoice\": null,
    \"Paypal / Pioneer Fee in invoice\": null,
    \"Actual Discount Received\": null,
    \"Gross Payable Price\": 29.50
  },
  {
    \"Invoice Date\": \"1/31/2025\",
    \"Invoice Number\": \"J2502-363\",
    \"PO Number\": \"KAHA-1139\",
    \"PO Date\": null,
    \"Actual Product Price\": 23.50,
    \"Actual Sales Tax Paid\": 0.00,
    \"Actual Dropship Fees\": null,
    \"Actual Shipping Charges\": 0.00,
    \"Actual Other Charges\": null,
    \"CC Fees in Invoice\": null,
    \"Paypal / Pioneer Fee in invoice\": null,
    \"Actual Discount Received\": null,
    \"Gross Payable Price\": 23.50
  },
  {
    \"Invoice Date\": \"1/31/2025\",
    \"Invoice Number\": \"J2502-363\",
    \"PO Number\": \"KAHA-1140\",
    \"PO Date\": null,
    \"Actual Product Price\": 23.50,
    \"Actual Sales Tax Paid\": 0.00,
    \"Actual Dropship Fees\": null,
    \"Actual Shipping Charges\": 0.00,
    \"Actual Other Charges\": null,
    \"CC Fees in Invoice\": null,
    \"Paypal / Pioneer Fee in invoice\": null,
    \"Actual Discount Received\": null,
    \"Gross Payable Price\": 23.50
  },
  {
    \"Invoice Date\": \"1/31/2025\",
    \"Invoice Number\": \"J2502-363\",
    \"PO Number\": \"KAHA-1141\",
    \"PO Date\": null,
    \"Actual Product Price\": 29.50,
    \"Actual Sales Tax Paid\": 0.00,
    \"Actual Dropship Fees\": null,
    \"Actual Shipping Charges\": 0.00,
    \"Actual Other Charges\": null,
    \"CC Fees in Invoice\": null,
    \"Paypal / Pioneer Fee in invoice\": null,
    \"Actual Discount Received\": null,
    \"Gross Payable Price\": 29.50
  },
  {
    \"Invoice Date\": \"1/31/2025\",
    \"Invoice Number\": \"J2502-363\",
    \"PO Number\": \"KAHA-1142\",
    \"PO Date\": null,
    \"Actual Product Price\": 26.80,
    \"Actual Sales Tax Paid\": 0.00,
    \"Actual Dropship Fees\": null,
    \"Actual Shipping Charges\": 0.00,
    \"Actual Other Charges\": null,
    \"CC Fees in Invoice\": null,
    \"Paypal / Pioneer Fee in invoice\": null,
    \"Actual Discount Received\": null,
    \"Gross Payable Price\": 26.80
  },
  {
    \"Invoice Date\": \"1/31/2025\",
    \"Invoice Number\": \"J2502-363\",
    \"PO Number\": \"KAHA-1143\",
    \"PO Date\": null,
    \"Actual Product Price\": 22.00,
    \"Actual Sales Tax Paid\": 0.00,
    \"Actual Dropship Fees\": null,
    \"Actual Shipping Charges\": 0.00,
    \"Actual Other Charges\": null,
    \"CC Fees in Invoice\": null,
    \"Paypal / Pioneer Fee in invoice\": null,
    \"Actual Discount Received\": null,
    \"Gross Payable Price\": 22.00
  },
  {
    \"Invoice Date\": \"1/31/2025\",
    \"Invoice Number\": \"J2502-363\",
    \"PO Number\": \"KAHA-1144\",
    \"PO Date\": null,
    \"Actual Product Price\": 26.80,
    \"Actual Sales Tax Paid\": 0.00,
    \"Actual Dropship Fees\": null,
    \"Actual Shipping Charges\": 0.00,
    \"Actual Other Charges\": null,
    \"CC Fees in Invoice\": null,
    \"Paypal / Pioneer Fee in invoice\": null,
    \"Actual Discount Received\": null,
    \"Gross Payable Price\": 26.80
  },
  {
    \"Invoice Date\": \"1/31/2025\",
    \"Invoice Number\": \"J2502-363\",
    \"PO Number\": \"KAHA-1145\",
    \"PO Date\": null,
    \"Actual Product Price\": 29.50,
    \"Actual Sales Tax Paid\": 0.00,
    \"Actual Dropship Fees\": null,
    \"Actual Shipping Charges\": 0.00,
    \"Actual Other Charges\": null,
    \"CC Fees in Invoice\": null,
    \"Paypal / Pioneer Fee in invoice\": null,
    \"Actual Discount Received\": null,
    \"Gross Payable Price\": 29.50
  },
  {
    \"Invoice Date\": \"1/31/2025\",
    \"Invoice Number\": \"J2502-363\",
    \"PO Number\": \"KAHA-1146\",
    \"PO Date\": null,
    \"Actual Product Price\": 26.50,
    \"Actual Sales Tax Paid\": 0.00,
    \"Actual Dropship Fees\": null,
    \"Actual Shipping Charges\": 0.00,
    \"Actual Other Charges\": null,
    \"CC Fees in Invoice\": null,
    \"Paypal / Pioneer Fee in invoice\": null,
    \"Actual Discount Received\": null,
    \"Gross Payable Price\": 26.50
  },
  {
    \"Invoice Date\": \"1/31/2025\",
    \"Invoice Number\": \"J2502-363\",
    \"PO Number\": \"KAHA-1147\",
    \"PO Date\": null,
    \"Actual Product Price\": 23.50,
    \"Actual Sales Tax Paid\": 0.00,
    \"Actual Dropship Fees\": null,
    \"Actual Shipping Charges\": 0.00,
    \"Actual Other Charges\": null,
    \"CC Fees in Invoice\": null,
    \"Paypal / Pioneer Fee in invoice\": null,
    \"Actual Discount Received\": null,
    \"Gross Payable Price\": 23.50
  },
  {
    \"Invoice Date\": \"1/31/2025\",
    \"Invoice Number\": \"J2502-363\",
    \"PO Number\": \"KAHA-1148\",
    \"PO Date\": null,
    \"Actual Product Price\": 31.00,
    \"Actual Sales Tax Paid\": 0.00,
    \"Actual Dropship Fees\": null,
    \"Actual Shipping Charges\": 0.00,
    \"Actual Other Charges\": null,
    \"CC Fees in Invoice\": null,
    \"Paypal / Pioneer Fee in invoice\": null,
    \"Actual Discount Received\": null,
    \"Gross Payable Price\": 31.00
  },
  {
    \"Invoice Date\": \"1/31/2025\",
    \"Invoice Number\": \"J2502-363\",
    \"PO Number\": \"KAHA-1149\",
    \"PO Date\": null,
    \"Actual Product Price\": 26.80,
    \"Actual Sales Tax Paid\": 0.00,
    \"Actual Dropship Fees\": null,
    \"Actual Shipping Charges\": 0.00,
    \"Actual Other Charges\": null,
    \"CC Fees in Invoice\": null,
    \"Paypal / Pioneer Fee in invoice\": null,
    \"Actual Discount Received\": null,
    \"Gross Payable Price\": 26.80
  },
  {
    \"Invoice Date\": \"1/31/2025\",
    \"Invoice Number\": \"J2502-363\",
    \"PO Number\": \"KAHA-1150\",
    \"PO Date\": null,
    \"Actual Product Price\": 25.00,
    \"Actual Sales Tax Paid\": 0.00,
    \"Actual Dropship Fees\": null,
    \"Actual Shipping Charges\": 0.00,
    \"Actual Other Charges\": null,
    \"CC Fees in Invoice\": null,
    \"Paypal / Pioneer Fee in invoice\": null,
    \"Actual Discount Received\": null,
    \"Gross Payable Price\": 25.00
  },
  {
    \"Invoice Date\": \"1/31/2025\",
    \"Invoice Number\": \"J2502-363\",
    \"PO Number\": \"KAHA-1151\",
    \"PO Date\": null,
    \"Actual Product Price\": 32.00,
    \"Actual Sales Tax Paid\": 0.00,
    \"Actual Dropship Fees\": null,
    \"Actual Shipping Charges\": 0.00,
    \"Actual Other Charges\": null,
    \"CC Fees in Invoice\": null,
    \"Paypal / Pioneer Fee in invoice\": null,
    \"Actual Discount Received\": null,
    \"Gross Payable Price\": 32.00
  },
  {
    \"Invoice Date\": \"1/31/2025\",
    \"Invoice Number\": \"J2502-363\",
    \"PO Number\": \"KAHA-1152\",
    \"PO Date\": null,
    \"Actual Product Price\": 23.50,
    \"Actual Sales Tax Paid\": 0.00,
    \"Actual Dropship Fees\": null,
    \"Actual Shipping Charges\": 0.00,
    \"Actual Other Charges\": null,
    \"CC Fees in Invoice\": null,
    \"Paypal / Pioneer Fee in invoice\": null,
    \"Actual Discount Received\": null,
    \"Gross Payable Price\": 23.50
  },
  {
    \"Invoice Date\": \"1/31/2025\",
    \"Invoice Number\": \"J2502-363\",
    \"PO Number\": \"KAHA-1153\",
    \"PO Date\": null,
    \"Actual Product Price\": 26.80,
    \"Actual Sales Tax Paid\": 0.00,
    \"Actual Dropship Fees\": null,
    \"Actual Shipping Charges\": 0.00,
    \"Actual Other Charges\": null,
    \"CC Fees in Invoice\": null,
    \"Paypal / Pioneer Fee in invoice\": null,
    \"Actual Discount Received\": null,
    \"Gross Payable Price\": 26.80
  },
  {
    \"Invoice Date\": \"1/31/2025\",
    \"Invoice Number\": \"J2502-363\",
    \"PO Number\": \"KAHA-1154\",
    \"PO Date\": null,
    \"Actual Product Price\": 23.50,
    \"Actual Sales Tax Paid\": 0.00,
    \"Actual Dropship Fees\": null,
    \"Actual Shipping Charges\": 0.00,
    \"Actual Other Charges\": null,
    \"CC Fees in Invoice\": null,
    \"Paypal / Pioneer Fee in invoice\": null,
    \"Actual Discount Received\": null,
    \"Gross Payable Price\": 23.50
  },
  {
    \"Invoice Date\": \"1/31/2025\",
    \"Invoice Number\": \"J2502-363\",
    \"PO Number\": \"KAHA-1155\",
    \"PO Date\": null,
    \"Actual Product Price\": 40.00,
    \"Actual Sales Tax Paid\": 0.00,
    \"Actual Dropship Fees\": null,
    \"Actual Shipping Charges\": 0.00,
    \"Actual Other Charges\": null,
    \"CC Fees in Invoice\": null,
    \"Paypal / Pioneer Fee in invoice\": null,
    \"Actual Discount Received\": null,
    \"Gross Payable Price\": 40.00
  },
  {
    \"Invoice Date\": \"1/31/2025\",
    \"Invoice Number\": \"J2502-363\",
    \"PO Number\": \"KAHA-1156\",
    \"PO Date\": null,
    \"Actual Product Price\": 40.00,
    \"Actual Sales Tax Paid\": 0.00,
    \"Actual Dropship Fees\": null,
    \"Actual Shipping Charges\": 0.00,
    \"Actual Other Charges\": null,
    \"CC Fees in Invoice\": null,
    \"Paypal / Pioneer Fee in invoice\": null,
    \"Actual Discount Received\": null,
    \"Gross Payable Price\": 40.00
  },
  {
    \"Invoice Date\": \"1/31/2025\",
    \"Invoice Number\": \"J2502-363\",
    \"PO Number\": \"KAHA-1157\",
    \"PO Date\": null,
    \"Actual Product Price\": 22.00,
    \"Actual Sales Tax Paid\": 0.00,
    \"Actual Dropship Fees\": null,
    \"Actual Shipping Charges\": 0.00,
    \"Actual Other Charges\": null,
    \"CC Fees in Invoice\": null,
    \"Paypal / Pioneer Fee in invoice\": null,
    \"Actual Discount Received\": null,
    \"Gross Payable Price\": 22.00
  },
  {
    \"Invoice Date\": \"1/31/2025\",
    \"Invoice Number\": \"J2502-363\",
    \"PO Number\": \"KAHA-1158\",
    \"PO Date\": null,
    \"Actual Product Price\": 29.50,
    \"Actual Sales Tax Paid\": 0.00,
    \"Actual Dropship Fees\": null,
    \"Actual Shipping Charges\": 0.00,
    \"Actual Other Charges\": null,
    \"CC Fees in Invoice\": null,
    \"Paypal / Pioneer Fee in invoice\": null,
    \"Actual Discount Received\": null,
    \"Gross Payable Price\": 29.50
  },
  {
    \"Invoice Date\": \"1/31/2025\",
    \"Invoice Number\": \"J2502-363\",
    \"PO Number\": \"KAHA-1159\",
    \"PO Date\": null,
    \"Actual Product Price\": 23.50,
    \"Actual Sales Tax Paid\": 0.00,
    \"Actual Dropship Fees\": null,
    \"Actual Shipping Charges\": 0.00,
    \"Actual Other Charges\": null,
    \"CC Fees in Invoice\": null,
    \"Paypal / Pioneer Fee in invoice\": null,
    \"Actual Discount Received\": null,
    \"Gross Payable Price\": 23.50
  },
  {
    \"Invoice Date\": \"1/31/2025\",
    \"Invoice Number\": \"J2502-363\",
    \"PO Number\": \"KAHA-1160\",
    \"PO Date\": null,
    \"Actual Product Price\": 47.00,
    \"Actual Sales Tax Paid\": 0.00,
    \"Actual Dropship Fees\": null,
    \"Actual Shipping Charges\": 0.00,
    \"Actual Other Charges\": null,
    \"CC Fees in Invoice\": null,
    \"Paypal / Pioneer Fee in invoice\": null,
    \"Actual Discount Received\": null,
    \"Gross Payable Price\": 47.00
  },
  {
    \"Invoice Date\": \"1/31/2025\",
    \"Invoice Number\": \"J2502-363\",
    \"PO Number\": \"KAHA-1161\",
    \"PO Date\": null,
    \"Actual Product Price\": 31.00,
    \"Actual Sales Tax Paid\": 0.00,
    \"Actual Dropship Fees\": null,
    \"Actual Shipping Charges\": 0.00,
    \"Actual Other Charges\": null,
    \"CC Fees in Invoice\": null,
    \"Paypal / Pioneer Fee in invoice\": null,
    \"Actual Discount Received\": null,
    \"Gross Payable Price\": 31.00
  },
  {
    \"Invoice Date\": \"1/31/2025\",
    \"Invoice Number\": \"J2502-363\",
    \"PO Number\": \"KAHA-1162\",
    \"PO Date\": null,
    \"Actual Product Price\": 46.00,
    \"Actual Sales Tax Paid\": 0.00,
    \"Actual Dropship Fees\": null,
    \"Actual Shipping Charges\": 0.00,
    \"Actual Other Charges\": null,
    \"CC Fees in Invoice\": null,
    \"Paypal / Pioneer Fee in invoice\": null,
    \"Actual Discount Received\": null,
    \"Gross Payable Price\": 46.00
  },
  {
    \"Invoice Date\": \"1/31/2025\",
    \"Invoice Number\": \"J2502-363\",
    \"PO Number\": \"KAHA-1163\",
    \"PO Date\": null,
    \"Actual Product Price\": 22.00,
    \"Actual Sales Tax Paid\": 0.00,
    \"Actual Dropship Fees\": null,
    \"Actual Shipping Charges\": 0.00,
    \"Actual Other Charges\": null,
    \"CC Fees in Invoice\": null,
    \"Paypal / Pioneer Fee in invoice\": null,
    \"Actual Discount Received\": null,
    \"Gross Payable Price\": 22.00
  },
  {
    \"Invoice Date\": \"1/31/2025\",
    \"Invoice Number\": \"J2502-363\",
    \"PO Number\": \"KAHA-1164\",
    \"PO Date\": null,
    \"Actual Product Price\": 46.00,
    \"Actual Sales Tax Paid\": 0.00,
    \"Actual Dropship Fees\": null,
    \"Actual Shipping Charges\": 0.00,
    \"Actual Other Charges\": null,
    \"CC Fees in Invoice\": null,
    \"Paypal / Pioneer Fee in invoice\": null,
    \"Actual Discount Received\": null,
    \"Gross Payable Price\": 46.00
  },
  {
    \"Invoice Date\": \"1/31/2025\",
    \"Invoice Number\": \"J2502-363\",
    \"PO Number\": \"KAHA-1165\",
    \"PO Date\": null,
    \"Actual Product Price\": 23.50,
    \"Actual Sales Tax Paid\": 0.00,
    \"Actual Dropship Fees\": null,
    \"Actual Shipping Charges\": 0.00,
    \"Actual Other Charges\": null,
    \"CC Fees in Invoice\": null,
    \"Paypal / Pioneer Fee in invoice\": null,
    \"Actual Discount Received\": null,
    \"Gross Payable Price\": 23.50
  },
  {
    \"Invoice Date\": \"1/31/2025\",
    \"Invoice Number\": \"J2502-363\",
    \"PO Number\": \"KAHA-1166\",
    \"PO Date\": null,
    \"Actual Product Price\": 46.00,
    \"Actual Sales Tax Paid\": 0.00,
    \"Actual Dropship Fees\": null,
    \"Actual Shipping Charges\": 0.00,
    \"Actual Other Charges\": null,
    \"CC Fees in Invoice\": null,
    \"Paypal / Pioneer Fee in invoice\": null,
    \"Actual Discount Received\": null,
    \"Gross Payable Price\": 46.00
  },
  {
    \"Invoice Date\": \"1/31/2025\",
    \"Invoice Number\": \"J2502-363\",
    \"PO Number\": \"KAHA-1167\",
    \"PO Date\": null,
    \"Actual Product Price\": 22.00,
    \"Actual Sales Tax Paid\": 0.00,
    \"Actual Dropship Fees\": null,
    \"Actual Shipping Charges\": 0.00,
    \"Actual Other Charges\": null,
    \"CC Fees in Invoice\": null,
    \"Paypal / Pioneer Fee in invoice\": null,
    \"Actual Discount Received\": null,
    \"Gross Payable Price\": 22.00
  },
  {
    \"Invoice Date\": \"1/31/2025\",
    \"Invoice Number\": \"J2502-363\",
    \"PO Number\": \"KAHA-1168\",
    \"PO Date\": null,
    \"Actual Product Price\": 26.50,
    \"Actual Sales Tax Paid\": 0.00,
    \"Actual Dropship Fees\": null,
    \"Actual Shipping Charges\": 0.00,
    \"Actual Other Charges\": null,
    \"CC Fees in Invoice\": null,
    \"Paypal / Pioneer Fee in invoice\": null,
    \"Actual Discount Received\": null,
    \"Gross Payable Price\": 26.50
  },
  {
    \"Invoice Date\": \"1/31/2025\",
    \"Invoice Number\": \"J2502-363\",
    \"PO Number\": \"KAHA-1169\",
    \"PO Date\": null,
    \"Actual Product Price\": 26.80,
    \"Actual Sales Tax Paid\": 0.00,
    \"Actual Dropship Fees\": null,
    \"Actual Shipping Charges\": 0.00,
    \"Actual Other Charges\": null,
    \"CC Fees in Invoice\": null,
    \"Paypal / Pioneer Fee in invoice\": null,
    \"Actual Discount Received\": null,
    \"Gross Payable Price\": 26.80
  },
  {
    \"Invoice Date\": \"1/31/2025\",
    \"Invoice Number\": \"J2502-363\",
    \"PO Number\": \"KAHA-1170\",
    \"PO Date\": null,
    \"Actual Product Price\": 31.00,
    \"Actual Sales Tax Paid\": 0.00,
    \"Actual Dropship Fees\": null,
    \"Actual Shipping Charges\": 0.00,
    \"Actual Other Charges\": null,
    \"CC Fees in Invoice\": null,
    \"Paypal / Pioneer Fee in invoice\": null,
    \"Actual Discount Received\": null,
    \"Gross Payable Price\": 31.00
  },
  {
    \"Invoice Date\": \"1/31/2025\",
    \"Invoice Number\": \"J2502-363\",
    \"PO Number\": \"KAHA-1171\",
    \"PO Date\": null,
    \"Actual Product Price\": 26.80,
    \"Actual Sales Tax Paid\": 0.00,
    \"Actual Dropship Fees\": null,
    \"Actual Shipping Charges\": 0.00,
    \"Actual Other Charges\": null,
    \"CC Fees in Invoice\": null,
    \"Paypal / Pioneer Fee in invoice\": null,
    \"Actual Discount Received\": null,
    \"Gross Payable Price\": 26.80
  },
  {
    \"Invoice Date\": \"1/31/2025\",
    \"Invoice Number\": \"J2502-363\",
    \"PO Number\": \"KAHA-1172\",
    \"PO Date\": null,
    \"Actual Product Price\": 29.50,
    \"Actual Sales Tax Paid\": 0.00,
    \"Actual Dropship Fees\": null,
    \"Actual Shipping Charges\": 0.00,
    \"Actual Other Charges\": null,
    \"CC Fees in Invoice\": null,
    \"Paypal / Pioneer Fee in invoice\": null,
    \"Actual Discount Received\": null,
    \"Gross Payable Price\": 29.50
  },
  {
    \"Invoice Date\": \"1/31/2025\",
    \"Invoice Number\": \"J2502-363\",
    \"PO Number\": \"KAHA-1173\",
    \"PO Date\": null,
    \"Actual Product Price\": 29.50,
    \"Actual Sales Tax Paid\": 0.00,
    \"Actual Dropship Fees\": null,
    \"Actual Shipping Charges\": 0.00,
    \"Actual Other Charges\": null,
    \"CC Fees in Invoice\": null,
    \"Paypal / Pioneer Fee in invoice\": null,
    \"Actual Discount Received\": null,
    \"Gross Payable Price\": 29.50
  },
  {
    \"Invoice Date\": \"1/31/2025\",
    \"Invoice Number\": \"J2502-363\",
    \"PO Number\": \"KAHA-1174\",
    \"PO Date\": null,
    \"Actual Product Price\": 26.80,
    \"Actual Sales Tax Paid\": 0.00,
    \"Actual Dropship Fees\": null,
    \"Actual Shipping Charges\": 0.00,
    \"Actual Other Charges\": null,
    \"CC Fees in Invoice\": null,
    \"Paypal / Pioneer Fee in invoice\": null,
    \"Actual Discount Received\": null,
    \"Gross Payable Price\": 26.80
  },
  {
    \"Invoice Date\": \"1/31/2025\",
    \"Invoice Number\": \"J2502-363\",
    \"PO Number\": \"KAHA-1175\",
    \"PO Date\": null,
    \"Actual Product Price\": 23.50,
    \"Actual Sales Tax Paid\": 0.00,
    \"Actual Dropship Fees\": null,
    \"Actual Shipping Charges\": 0.00,
    \"Actual Other Charges\": null,
    \"CC Fees in Invoice\": null,
    \"Paypal / Pioneer Fee in invoice\": null,
    \"Actual Discount Received\": null,
    \"Gross Payable Price\": 23.50
  },
  {
    \"Invoice Date\": \"1/31/2025\",
    \"Invoice Number\": \"J2502-363\",
    \"PO Number\": \"KAHA-1176\",
    \"PO Date\": null,
    \"Actual Product Price\": 49.00,
    \"Actual Sales Tax Paid\": 0.00,
    \"Actual Dropship Fees\": null,
    \"Actual Shipping Charges\": 0.00,
    \"Actual Other Charges\": null,
    \"CC Fees in Invoice\": null,
    \"Paypal / Pioneer Fee in invoice\": null,
    \"Actual Discount Received\": null,
    \"Gross Payable Price\": 49.00
  },
  {
    \"Invoice Date\": \"1/31/2025\",
    \"Invoice Number\": \"J2502-363\",
    \"PO Number\": \"KAHA-1177\",
    \"PO Date\": null,
    \"Actual Product Price\": 31.00,
    \"Actual Sales Tax Paid\": 0.00,
    \"Actual Dropship Fees\": null,
    \"Actual Shipping Charges\": 0.00,
    \"Actual Other Charges\": null,
    \"CC Fees in Invoice\": null,
    \"Paypal / Pioneer Fee in invoice\": null,
    \"Actual Discount Received\": null,
    \"Gross Payable Price\": 31.00
  },
  {
    \"Invoice Date\": \"1/31/2025\",
    \"Invoice Number\": \"J2502-363\",
    \"PO Number\": \"KAHA-1178\",
    \"PO Date\": null,
    \"Actual Product Price\": 46.00,
    \"Actual Sales Tax Paid\": 0.00,
    \"Actual Dropship Fees\": null,
    \"Actual Shipping Charges\": 0.00,
    \"Actual Other Charges\": null,
    \"CC Fees in Invoice\": null,"""
                    ),
                ],
            ),
            types.Content(
                role="user",
                parts=[
                    types.Part.from_uri(
                        file_uri=files[6].uri,
                        mime_type=files[6].mime_type,
                    ),
                    types.Part.from_text(text="""Process the attached invoice"""),
                ],
            ),
            types.Content(
                role="model",
                parts=[
                    types.Part.from_text(
                        text="""{
  \"Invoice Date\": \"2024-12-31\",
  \"Invoice Number\": \"BYOGO-103-125\",
  \"PO Number\": \"BYOGO103-125\",
  \"PO Date\": null,
  \"Actual Product Price\": null,
  \"Actual Sales Tax Paid\": null,
  \"Actual Dropship Fees\": null,
  \"Actual Shipping Charges\": null,
  \"Actual Other Charges\": null,
  \"CC Fees in Invoice\": null,
  \"Paypal / Pioneer Fee in invoice\": null,
  \"Actual Discount Received\": null,
  \"Gross Payable Price\": 2345.00
}"""
                    ),
                ],
            ),
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(
                        text="""in case of multiple items like this invoice, you should mention the total of all items product cost in the \"Actual Product Price\" field"""
                    ),
                ],
            ),
            types.Content(
                role="model",
                parts=[
                    types.Part.from_text(
                        text="""{
  \"Invoice Date\": \"2024-12-31\",
  \"Invoice Number\": \"BYOGO-103-125\",
  \"PO Number\": \"BYOGO103-125\",
  \"PO Date\": null,
  \"Actual Product Price\": 2345.00,
  \"Actual Sales Tax Paid\": null,
  \"Actual Dropship Fees\": null,
  \"Actual Shipping Charges\": null,
  \"Actual Other Charges\": null,
  \"CC Fees in Invoice\": null,
  \"Paypal / Pioneer Fee in invoice\": null,
  \"Actual Discount Received\": null,
  \"Gross Payable Price\": 2345.00
}"""
                    ),
                ],
            ),
            types.Content(
                role="user",
                parts=[
                    types.Part.from_uri(
                        file_uri=files[7].uri,
                        mime_type=files[7].mime_type,
                    ),
                    types.Part.from_text(text="""Process this invoice"""),
                ],
            ),
            types.Content(
                role="model",
                parts=[
                    types.Part.from_text(
                        text="""{
  \"Invoice Date\": \"February 28, 2025\",
  \"Invoice Number\": \"0000239431\",
  \"PO Number\": \"RAMG-115\",
  \"PO Date\": \"February 21, 2025\",
  \"Actual Product Price\": 820.00,
  \"Actual Sales Tax Paid\": null,
  \"Actual Dropship Fees\": null,
  \"Actual Shipping Charges\": 0.00,
  \"Actual Other Charges\": null,
  \"CC Fees in Invoice\": null,
  \"Paypal / Pioneer Fee in invoice\": null,
  \"Actual Discount Received\": null,
  \"Gross Payable Price\": 820.00
}"""
                    ),
                ],
            ),
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(
                        text="""this invoice contained a row mentioning pickup fees that should be have been classified as shipping charges and the product price is only 725"""
                    ),
                ],
            ),
            types.Content(
                role="model",
                parts=[
                    types.Part.from_text(
                        text="""{
  \"Invoice Date\": \"February 28, 2025\",
  \"Invoice Number\": \"0000239431\",
  \"PO Number\": \"RAMG-115\",
  \"PO Date\": \"February 21, 2025\",
  \"Actual Product Price\": 725.00,
  \"Actual Sales Tax Paid\": null,
  \"Actual Dropship Fees\": null,
  \"Actual Shipping Charges\": 95.00,
  \"Actual Other Charges\": null,
  \"CC Fees in Invoice\": null,
  \"Paypal / Pioneer Fee in invoice\": null,
  \"Actual Discount Received\": null,
  \"Gross Payable Price\": 820.00
}"""
                    ),
                ],
            ),
            types.Content(
                role="user",
                parts=[
                    types.Part.from_uri(
                        file_uri=files[8].uri,
                        mime_type=files[8].mime_type,
                    ),
                    types.Part.from_text(text="""Process this invoice"""),
                ],
            ),
            types.Content(
                role="model",
                parts=[
                    types.Part.from_text(
                        text="""{
  \"Invoice Date\": \"2/20/2025\",
  \"Invoice Number\": \"16392\",
  \"PO Number\": \"HANS-687\",
  \"PO Date\": null,
  \"Actual Product Price\": null,
  \"Actual Sales Tax Paid\": null,
  \"Actual Dropship Fees\": 25.00,
  \"Actual Shipping Charges\": null,
  \"Actual Other Charges\": null,
  \"CC Fees in Invoice\": null,
  \"Paypal / Pioneer Fee in invoice\": null,
  \"Actual Discount Received\": null,
  \"Gross Payable Price\": 50.95
}"""
                    ),
                ],
            ),
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(
                        text="""you missed the product price of 25.95"""
                    ),
                ],
            ),
            types.Content(
                role="model",
                parts=[
                    types.Part.from_text(
                        text="""{
  \"Invoice Date\": \"2/20/2025\",
  \"Invoice Number\": \"16392\",
  \"PO Number\": \"HANS-687\",
  \"PO Date\": null,
  \"Actual Product Price\": 25.95,
  \"Actual Sales Tax Paid\": null,
  \"Actual Dropship Fees\": 25.00,
  \"Actual Shipping Charges\": null,
  \"Actual Other Charges\": null,
  \"CC Fees in Invoice\": null,
  \"Paypal / Pioneer Fee in invoice\": null,
  \"Actual Discount Received\": null,
  \"Gross Payable Price\": 50.95
}"""
                    ),
                ],
            ),
            types.Content(
                role="user",
                parts=[
                    types.Part.from_uri(
                        file_uri=files[9].uri,
                        mime_type=files[9].mime_type,
                    ),
                    types.Part.from_text(text="""Process this invoice"""),
                ],
            ),
            types.Content(
                role="model",
                parts=[
                    types.Part.from_text(
                        text="""{
\"Invoice Date\": \"2/20/2025\",
\"Invoice Number\": \"16392\",
\"PO Number\": \"HANS-687\",
\"PO Date\": null,
\"Actual Product Price\": 25.95,
\"Actual Sales Tax Paid\": null,
\"Actual Dropship Fees\": 25.00,
\"Actual Shipping Charges\": null,
\"Actual Other Charges\": null,
\"CC Fees in Invoice\": null,
\"Paypal / Pioneer Fee in invoice\": null,
\"Actual Discount Received\": null,
\"Gross Payable Price\": 50.95
}"""
                    ),
                ],
            ),
            types.Content(
                role="user",
                parts=[
                    types.Part.from_uri(
                        file_uri=files[10].uri,
                        mime_type=files[10].mime_type,
                    ),
                    types.Part.from_text(text="""Process this invoice"""),
                ],
            ),
            types.Content(
                role="model",
                parts=[
                    types.Part.from_text(
                        text="""{
\"Invoice Date\": \"3/4/2025\",
\"Invoice Number\": \"5366250\",
\"PO Number\": \"BORA-2392\",
\"PO Date\": null,
\"Actual Product Price\": 96.08,
\"Actual Sales Tax Paid\": null,
\"Actual Dropship Fees\": null,
\"Actual Shipping Charges\": null,
\"Actual Other Charges\": null,
\"CC Fees in Invoice\": null,
\"Paypal / Pioneer Fee in invoice\": null,
\"Actual Discount Received\": null,
\"Gross Payable Price\": 96.08
}"""
                    ),
                ],
            ),
            types.Content(
                role="user",
                parts=[
                    types.Part.from_uri(
                        file_uri=files[11].uri,
                        mime_type=files[11].mime_type,
                    ),
                    types.Part.from_text(text="""PROCESS THIS INVOICE"""),
                ],
            ),
            types.Content(
                role="model",
                parts=[
                    types.Part.from_text(
                        text="""[
    {
        \"Invoice Date\": \"09/03/24\",
        \"Invoice Number\": \"207095\",
        \"PO Number\": \"SVST-20395\",
        \"PO Date\": \"09/03/2024\",
        \"Actual Product Price\": 168.00,
        \"Actual Sales Tax Paid\": null,
        \"Actual Dropship Fees\": null,
        \"Actual Shipping Charges\": 0.00,
        \"Actual Other Charges\": 0.88,
        \"CC Fees in Invoice\": null,
        \"Paypal \\/ Pioneer Fee in invoice\": null,
        \"Actual Discount Received\": null,
        \"Gross Payable Price\": 168.88
    },
    {
        \"Invoice Date\": \"09/03/24\",
        \"Invoice Number\": \"207095\",
        \"PO Number\": \"SVST-20396\",
        \"PO Date\": \"09/03/2024\",
        \"Actual Product Price\": 86.00,
        \"Actual Sales Tax Paid\": null,
        \"Actual Dropship Fees\": null,
        \"Actual Shipping Charges\": 0.00,
        \"Actual Other Charges\": 0.88,
        \"CC Fees in Invoice\": null,
        \"Paypal \\/ Pioneer Fee in invoice\": null,
        \"Actual Discount Received\": null,
        \"Gross Payable Price\": 86.88
    },
    {
        \"Invoice Date\": \"09/03/24\",
        \"Invoice Number\": \"207095\",
        \"PO Number\": \"SVST-20397\",
        \"PO Date\": \"09/03/2024\",
        \"Actual Product Price\": 150.00,
        \"Actual Sales Tax Paid\": null,
        \"Actual Dropship Fees\": null,
        \"Actual Shipping Charges\": 0.00,
        \"Actual Other Charges\": 0.88,
        \"CC Fees in Invoice\": null,
        \"Paypal \\/ Pioneer Fee in invoice\": null,
        \"Actual Discount Received\": null,
        \"Gross Payable Price\": 150.88
    },
    {
        \"Invoice Date\": \"09/03/24\",
        \"Invoice Number\": \"207095\",
        \"PO Number\": \"SVST-20398\",
        \"PO Date\": \"09/03/2024\",
        \"Actual Product Price\": 16.00,
        \"Actual Sales Tax Paid\": null,
        \"Actual Dropship Fees\": null,
        \"Actual Shipping Charges\": 0.00,
        \"Actual Other Charges\": 0.88,
        \"CC Fees in Invoice\": null,
        \"Paypal \\/ Pioneer Fee in invoice\": null,
        \"Actual Discount Received\": null,
        \"Gross Payable Price\": 16.88
    }
]"""
                    ),
                ],
            ),
            types.Content(
                role="user",
                parts=[
                    types.Part.from_uri(
                        file_uri=uploaded_file.uri,
                        mime_type=uploaded_file.mime_type,
                    ),
                    types.Part.from_text(text="""Process this invoice"""),
                ],
            ),
        ]
        generate_content_config = types.GenerateContentConfig(
            temperature=2,
            top_p=0.95,
            top_k=40,
            max_output_tokens=8192,
            response_mime_type="application/json",
        )

        response = client.models.generate_content(
            model=model,
            contents=contents,
            config=generate_content_config,
        )

        # Convert string to valid JSON object
        response_text = response.text if hasattr(response, "text") else str(response)
        parsed_response = json.loads(response_text)

        # Ensure the response is a list and add file name to each item
        if isinstance(parsed_response, list):
            for item in parsed_response:
                item["file_name"] = file_name
        else:
            parsed_response = [{**parsed_response, "file_name": file_name}]

        return parsed_response
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error processing invoice: {str(e)}"
        )


@app.post("/extract_invoices")
async def extract_invoices(files: List[UploadFile] = File(...)):
    for file in files:
        if not is_valid_file(file):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type: {file.filename}. Only PDF allowed.",
            )

        # Save file locally
        file_path = os.path.join(UPLOAD_FOLDER, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        try:
            # Process each invoice individually
            invoice_data = process_invoice(file_path, file.filename)
        except Exception as e:
            # Log error and continue with other files
            print(f"Error processing {file.filename}: {e}")

        # Save data in Firebase Firestore
        for item in invoice_data:
            db.collection("invoices").add(item)

    return {"message": "Invoices processed and saved in Firebase"}


@app.get("/invoices")
async def get_invoices():
    """Fetch all invoices from Firebase Firestore."""
    docs = db.collection("invoices").stream()
    invoices = [{**doc.to_dict(), "id": doc.id} for doc in docs]
    return invoices


@app.put("/update_invoice/{invoice_id}")
async def update_invoice(invoice_id: str, data: dict):
    """Update an invoice in Firebase Firestore."""
    db.collection("invoices").document(invoice_id).update(data)
    return {"message": "Invoice updated successfully"}


@app.get("/download_csv")
async def download_csv():
    """Export invoices as CSV and upload to Firebase Storage."""

    # Fetch invoices from Firestore
    docs = db.collection("invoices").stream()
    invoices = [{**doc.to_dict()} for doc in docs]

    if not invoices:
        raise HTTPException(status_code=404, detail="No invoices found")

    # Convert to DataFrame
    df = pd.DataFrame(invoices)

    # Save CSV locally
    local_csv_path = "invoices_export.csv"
    df.to_csv(local_csv_path, index=False)

    # Upload to Firebase Storage
    bucket = storage.bucket()
    blob = bucket.blob(f"exports/{local_csv_path}")  # Store in 'exports/' folder
    blob.upload_from_filename(local_csv_path)

    # Make the file publicly accessible
    blob.make_public()

    # Generate download URL
    download_url = blob.public_url

    return {"download_url": download_url}


# Run the FastAPI app with Uvicorn
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)

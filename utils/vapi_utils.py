# vapi_utils.py

import requests
import json

# === VAPI CONFIG ===
API_KEY = "8c4cd1a3-67ab-4449-bdeb-90e8dd4238c4"
ASSISTANT_ID = "98d8ba6f-d6e0-4e72-8100-d095a976c474"
PHONE_NUMBER_ID = "d4dfe093-298f-4033-90b6-27602eff8ef4"

BASE_URL = "https://api.vapi.ai"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

def call_vendor(vendor: dict, product_name: str, location: str) -> dict:
    """
    Call a single vendor using Vapi with assistant overrides.
    """

    customer_phone = vendor.get("phone")
    vendor_name = vendor.get("name")

    payload = {
        "type": "outboundPhoneCall",
        "assistantId": ASSISTANT_ID,
        "phoneNumberId": PHONE_NUMBER_ID,
        "customer": {
            "number": customer_phone
        },
        "name": f"Enquiry Call to {vendor_name}",
        "assistantOverrides": {
            "variableValues": {
                "product_name": product_name,
                "store_name": vendor_name,
                "location": location,
                "is_retry": False
            }
        }
    }

    try:
        response = requests.post(
            f"{BASE_URL}/call",
            headers=HEADERS,
            json=payload,
            timeout=30
        )

        response.raise_for_status()
        result = response.json()

        print(f"✅ Call initiated to {vendor_name} ({customer_phone}) | Call ID: {result.get('id')}")
        return {
            "vendor": vendor_name,
            "phone": customer_phone,
            "call_id": result.get("id"),
            "status": result.get("status")
        }

    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to call {vendor_name}: {e}")
        if hasattr(e, "response") and e.response:
            print(f"Response: {e.response.text}")
        return {
            "vendor": vendor_name,
            "phone": customer_phone,
            "error": str(e)
        }

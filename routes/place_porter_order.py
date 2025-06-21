from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import requests
import json
from datetime import datetime
import uuid
from pymongo import MongoClient
import requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import requests
import uuid
import logging
from dotenv import load_dotenv
import os
# Load environment variables from .env file
load_dotenv()

PORTER_API_URL = os.getenv("PORTER_API_URL")
PORTER_API_KEY = os.getenv("PORTER_API_KEY")
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", 30))  # fallback default
# FastAPI router
router = APIRouter()


# MongoDB setup
client = MongoClient(
    "mongodb+srv://sarveshatawane03:y2flIDD1EmOaU5de@cluster0.sssmr.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
)
db = client["porter_orders"]
porter_collection = db["porter_order_details"]

# Pydantic models
class Address(BaseModel):
    apartment_address: str
    street_address1: str
    street_address2: str
    landmark: str
    city: str
    state: str
    pincode: str
    country: str
    lat: float
    lng: float

class PickupDetails(BaseModel):
    address: Address

class DropDetails(BaseModel):
    address: Address

class Instruction(BaseModel):
    type: str
    description: str

class DeliveryInstructions(BaseModel):
    instructions_list: List[Instruction]

class PorterOrderRequest(BaseModel):
    request_id: Optional[str] = None
    delivery_instructions: DeliveryInstructions
    pickup_details: PickupDetails
    drop_details: Optional[DropDetails] = None
    additional_comments: Optional[str] = None
    vendor_id: Optional[str] = None
    vendor_name: Optional[str] = None
    enquiry_id: Optional[str] = None

def generate_request_id() -> str:
    """Generate unique request ID"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    return f"ORDER_{timestamp}_{unique_id}"

def is_json_response(response: requests.Response) -> bool:
    """Check response type"""
    content_type = response.headers.get("content-type", "").lower()
    return "application/json" in content_type

def get_default_drop_address() -> Dict[str, Any]:
    """Fallback drop address"""
    return {
        "apartment_address": "123",
        "street_address1": "Default Drop Location",
        "street_address2": "Business Area",
        "landmark": "Near Main Road",
        "city": "Nashik",
        "state": "Maharashtra",
        "pincode": "422001",
        "country": "India",
        "lat": 19.9975,
        "lng": 73.7898,
        "contact_details": {
            "name": "Drop Contact",
            "phone_number": "+919876543210"
        }
    }

def add_contact_details_to_address(address: Dict[str, Any], default_name: str, default_phone: str) -> Dict[str, Any]:
    """Ensure contact_details exists"""
    if "contact_details" not in address:
        address["contact_details"] = {
            "name": default_name,
            "phone_number": default_phone
        }
    return address

@router.post("/create_porter_order")
async def create_porter_order(order_request: PorterOrderRequest):
    """Main Porter order creation"""
    try:
        request_id = order_request.request_id or generate_request_id()

        pickup_address = order_request.pickup_details.address.dict()
        pickup_address = add_contact_details_to_address(
            pickup_address, 
            f"Pickup - {order_request.vendor_name or 'Vendor'}", 
            "+919999999999"
        )

        if order_request.drop_details:
            drop_address = order_request.drop_details.address.dict()
            drop_address = add_contact_details_to_address(
                drop_address,
                "Drop Contact",
                "+919888888888"
            )
        else:
            drop_address = get_default_drop_address()

        porter_payload = {
            "request_id": str(uuid.uuid4()),
            "delivery_instructions": order_request.delivery_instructions.dict(),
            "pickup_details": {"address": pickup_address},
            "drop_details": {"address": drop_address},
            "additional_comments": order_request.additional_comments or f"Order for {order_request.vendor_name}"
        }

        headers = {
            "x-api-key": PORTER_API_KEY,
            "Content-Type": "application/json"
        }

        response = requests.post(
            "https://pfe-apigw-uat.porter.in/v1/orders/create",
            headers=headers,
            json=porter_payload,
            timeout=REQUEST_TIMEOUT
        )

        response_data = response.json() if is_json_response(response) else {"raw_response": response.text}

        # Print final response
        print("=== FINAL PORTER API RESPONSE ===")
        print(json.dumps(response_data, indent=2))
        # Add this in your create_porter_order function before the requests.post call
        print("=== PORTER REQUEST DEBUG ===")
        print(f"URL: {PORTER_API_URL}")
        print(f"Headers: {headers}")
        print(f"Payload: {json.dumps(porter_payload, indent=2, default=str)}")
        print("=== END DEBUG ===")

        # After the request
        print(f"Response Status: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print(f"Raw Response Text: '{response.text}'")
        # Save to Mongo if success
        if response.status_code in (200, 201):
            porter_collection.insert_one({
                "request_id": request_id,
                "vendor_id": order_request.vendor_id,
                "vendor_name": order_request.vendor_name,
                "enquiry_id": order_request.enquiry_id,
                "porter_payload": porter_payload,
                "porter_response": response_data,
                "created_at": datetime.utcnow()
            })

            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "porter_response": response_data,
                    "request_id": request_id
                }
            )
        else:
            return JSONResponse(
                status_code=response.status_code,
                content={
                    "success": False,
                    "porter_error": response_data,
                    "request_id": request_id
                }
            )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e)
            }
        )
@router.post("/test_porter_curl_simple")
async def test_porter_curl_simple():
    """
    Simple test endpoint that always uses the default test data.
    No request body required.
    """
    
    porter_url = "https://pfe-apigw-uat.porter.in/v1/orders/create"
    headers = {
        "x-api-key": PORTER_API_KEY,
        "Content-Type": "application/json"
    }
    
    payload = {
        "request_id": str(uuid.uuid4()),
        "delivery_instructions": {
            "instructions_list": [
                {
                    "type": "text",
                    "description": "handle with care"
                }
            ]
        },
        "pickup_details": {
            "address": {
                "apartment_address": "27",
                "street_address1": "Sona Towers",
                "street_address2": "Krishna Nagar Industrial Area",
                "landmark": "Hosur Road",
                "city": "Bengaluru",
                "state": "Karnataka",
                "pincode": "560029",
                "country": "India",
                "lat": 12.935025,
                "lng": 77.609261,
                "contact_details": {
                    "name": "Test Pickup User",
                    "phone_number": "+919999999999"
                }
            }
        },
        "drop_details": {
            "address": {
                "apartment_address": "45",
                "street_address1": "Prestige Tech Park",
                "street_address2": "Kadubeesanahalli",
                "landmark": "Near Marathahalli Bridge",
                "city": "Bengaluru",
                "state": "Karnataka",
                "pincode": "560103",
                "country": "India",
                "lat": 12.934533,
                "lng": 77.690114,
                "contact_details": {
                    "name": "Test Drop User",
                    "phone_number": "+919888888888"
                }
            }
        },
        "additional_comments": "This is a test comment"
    }
    
    try:
        response = requests.post(porter_url, headers=headers, json=payload, timeout=30)
        
        return {
            "status_code": response.status_code,
            "request_id": payload["request_id"],
            "response": response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
@router.post("/test_porter_curl")
async def test_porter_curl():
    """Hardcoded test"""
    test_payload = {
        "request_id": generate_request_id(),
        "delivery_instructions": {
            "instructions_list": [
                {"type": "text", "description": "handle with care"}
            ]
        },
        "pickup_details": {
            "address": {
                "apartment_address": "27",
                "street_address1": "Sona Towers",
                "street_address2": "Krishna Nagar Industrial Area",
                "landmark": "Hosur Road",
                "city": "Bengaluru",
                "state": "Karnataka",
                "pincode": "560029",
                "country": "India",
                "lat": 12.935025,
                "lng": 77.609261,
                "contact_details": {
                    "name": "Test Pickup User",
                    "phone_number": "+919999999999"
                }
            }
        },
        "drop_details": {
            "address": {
                "apartment_address": "45",
                "street_address1": "Prestige Tech Park",
                "street_address2": "Kadubeesanahalli",
                "landmark": "Near Marathahalli Bridge",
                "city": "Bengaluru",
                "state": "Karnataka",
                "pincode": "560103",
                "country": "India",
                "lat": 12.934533,
                "lng": 77.690114,
                "contact_details": {
                    "name": "Test Drop User",
                    "phone_number": "+919888888888"
                }
            }
        },
        "additional_comments": "This is a test comment"
    }

    headers = {
        "x-api-key": PORTER_API_KEY,
        "Content-Type": "application/json"
    }

    response = requests.post(
        "https://pfe-apigw-uat.porter.in/v1/orders/create",
        headers=headers,
        json=test_payload,
        timeout=REQUEST_TIMEOUT
    )

    response_data = response.json() if is_json_response(response) else {"raw_response": response.text}
    print(response_data)
        # Print final response
    print("=== FINAL PORTER TEST RESPONSE ===")
    print(json.dumps(response_data, indent=2))

    if response.status_code in (200, 201):
        porter_collection.insert_one({
            "request_id": test_payload["request_id"],
            "porter_payload": test_payload,
            "porter_response": response_data,
            "created_at": datetime.utcnow()
        })

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "porter_response": response_data,
                "request_id": test_payload["request_id"]
            }
        )
    else:
        return JSONResponse(
            status_code=response.status_code,
            content={
                "success": False,
                "porter_error": response_data,
                "request_id": test_payload["request_id"]
            }
        )
    
@router.get("/get_all_porter_orders")
async def get_all_porter_orders():
    """
    Fetch all Porter orders saved in MongoDB.
    """
    try:
        # Fetch all documents
        orders = list(porter_collection.find())

        for order in orders:
            # Convert ObjectId to string
            order["_id"] = str(order["_id"])

            # Convert any datetime fields to string safely
            for key, value in order.items():
                if isinstance(value, datetime):
                    order[key] = value.isoformat()

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "total_orders": len(orders),
                "orders": orders
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e)
            }
        )
import requests
from fastapi import APIRouter, Request

PORTER_API_URL = "https://pfe-apigw-uat.porter.in/v1/get_quote"

@router.post("/get-quote")
async def get_quote(request: Request):
    try:
        body = await request.json()
        print("Received request to get quote")
        print("Request body:", body)

        # Fix the customer field structure
        if "customer" in body and isinstance(body["customer"].get("phone"), str):
            number = body["customer"]["phone"]
            body["customer"]["mobile"] = {
                "country_code": "+91",
                "number": number
            }
            del body["customer"]["phone"]

        response = requests.get(
            "https://pfe-apigw-uat.porter.in/v1/get_quote",
            headers={
                "X-API-KEY": PORTER_API_KEY,
                "Content-Type": "application/json"
            },
            json=body  # sending JSON in GET, like your curl
        )

        print("Response from Porter API:", response.status_code)
        print("Porter response body:", response.text)

        try:
            return JSONResponse(status_code=response.status_code, content=response.json())
        except ValueError:
            return JSONResponse(status_code=response.status_code, content={"error": response.text})

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

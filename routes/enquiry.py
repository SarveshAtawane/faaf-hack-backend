from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from models.schemas import EnquiryRequest
from db.mongo import db
from datetime import datetime
import hashlib
from utils.vapi_utils import call_vendor
import asyncio
import json

router = APIRouter()

# Global list of connected WebSocket clients
active_connections: list[WebSocket] = []

# @router.websocket("/ws/enquiries")
# async def websocket_endpoint(websocket: WebSocket):
#     await websocket.accept()
#     active_connections.append(websocket)
#     try:
#         while True:
#             await websocket.receive_text()  # Ping-pong to keep it alive
#     except WebSocketDisconnect:
#         active_connections.remove(websocket)

# async def broadcast_enquiries_update():
#     """
#     Send all current enquiries to connected clients.
#     """
#     all_docs = []
#     for collection_name in db.list_collection_names():
#         collection = db[collection_name]
#         documents = list(collection.find({}))
#         for doc in documents:
#             doc["_id"] = str(doc["_id"])
#             if "timestamp" in doc:
#                 doc["timestamp"] = doc["timestamp"].isoformat()
#             doc["__collection__"] = collection_name
#         all_docs.extend(documents)

#     payload = json.dumps({"enquiries": all_docs})
#     disconnected = []
#     for conn in active_connections:
#         try:
#             await conn.send_text(payload)
#         except Exception:
#             disconnected.append(conn)

#     for conn in disconnected:
#         active_connections.remove(conn)


@router.post("/enquire")
async def send_enquiry(req: EnquiryRequest):
    normalized_location = req.location.replace(" ", "")
    collection_name = f"{req.product}_{normalized_location}"
    collection = db[collection_name]

    inserted = []
    calls = []

    for vendor in req.vendors:
        unique_key = hashlib.md5(f"{vendor['name']}_{vendor['lat']}_{vendor['lon']}".encode()).hexdigest()

        vendor_doc = {
            "_id": unique_key,
            "product": req.product,
            "additional_details": req.additional_details or "",  # Store additional details
            "location_bucket": f"{vendor['lat']},{vendor['lon']}",
            "name": vendor['name'],
            "address": vendor['address'],
            "phone": vendor['phone'],
            "availability": None,
            "price": None,
            "variants": [],
            "alternatives": [],
            "min_availability_time": None,
            "call_summary": None,
            "timestamp": datetime.utcnow(),
            "call_status": "Calling",
            "call_attempts": 0,
            "is_retry": False,
            "call_duration": None,
            "call_recording": None,
            "call_transcription": None,
            "location": {
                "lat": vendor['lat'],
                "lon": vendor['lon']
            },
            "remarks": "",
            "call_ids": []
        }

        collection.update_one(
            {"_id": unique_key},
            {"$setOnInsert": vendor_doc},
            upsert=True
        )
        print(f"Vendor {vendor['name']} inserted/updated in `{collection_name}` with key {unique_key} successfully.")
        print(f"Vendor document: {vendor_doc}")
        inserted.append(unique_key)
        print(vendor)
        print(f"Calling vendor: {vendor['name']} at {vendor['phone']}")
        print(vendor_doc["additional_details"])
        # Pass additional details to the call_vendor function
        call_result = call_vendor(vendor, req.product, req.location, vendor_doc["additional_details"])
        print(call_result)
        calls.append(call_result)

        call_id = call_result.get("call_id")
        if call_id:
            collection.update_one(
                {"_id": unique_key},
                {"$push": {"call_ids": call_id}}
            )

    # Push update via WebSocket
    # await broadcast_enquiries_update()

    return {
        "message": f"{len(inserted)} vendors processed in `{collection_name}`",
        "inserted": inserted,
        "calls": calls
    }


@router.get("/enquiries")
def get_all_enquiries():
    all_docs = []
    for collection_name in db.list_collection_names():
        collection = db[collection_name]
        documents = list(collection.find({}))
        for doc in documents:
            doc["_id"] = str(doc["_id"])
            if "timestamp" in doc:
                doc["timestamp"] = doc["timestamp"].isoformat()
            doc["__collection__"] = collection_name
        all_docs.extend(documents)
    return JSONResponse(content={"enquiries": all_docs})

import requests
import json

API_KEY = "8c4cd1a3-67ab-4449-bdeb-90e8dd4238c4"
ASSISTANT_ID = "98d8ba6f-d6e0-4e72-8100-d095a976c474"
PHONE_NUMBER_ID = "36491758-d626-4f39-8831-14e3c5614c6a"

BASE_URL = "https://api.vapi.ai"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

def call_vendor(vendor: dict, product_name: str, location: str, details:str) -> dict:
    print(f"Calling vendor: {vendor['name']} at {vendor['phone']}")
    print(f"Product: {product_name}, Location: {location}, Details: {details}")
    customer_phone = "+919527699807"
    if vendor.get('name') == "Rahul Fruits":
        customer_phone = "+917588708498"  # Use a different phone number for this vendor
    else:
        customer_phone = "+919527699807"
    vendor_name = vendor.get("name", "").strip()
    # print(vendor.get("additional_details"))
    payload = {
        "type": "outboundPhoneCall",
        "assistantId": ASSISTANT_ID,
        "phoneNumberId": PHONE_NUMBER_ID,
        "customer": {
            "number": customer_phone
        },
        "name": "Enquiry",
        "assistantOverrides": {
            "variableValues": {
                "product_name": product_name,
                "store_name": vendor_name,
                "location": location,
                "details": details,
                "is_retry": False
            }
        }
    }

    try:
        response = requests.post(f"{BASE_URL}/call", headers=HEADERS, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()
        print(result)
        return {
            "vendor": vendor_name,
            "phone": customer_phone,
            "call_id": result.get("id"),
            "status": result.get("status")
        }
    except requests.exceptions.RequestException as e:
        return {
            "vendor": vendor_name,
            "phone": customer_phone,
            "error": str(e)
        }

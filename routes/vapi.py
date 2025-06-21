# routes/vapi.py

from fastapi import APIRouter, Request
from db.mongo import db
from datetime import datetime
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from models.schemas import EnquiryRequest
from db.mongo import db
from datetime import datetime
import hashlib
from utils.vapi_utils import call_vendor
import asyncio
import json
import logging

router = APIRouter()

# Global list of connected WebSocket clients
# active_connections: list[WebSocket] = []

# @router.websocket("/ws/enquiries")
# async def websocket_endpoint(websocket: WebSocket):
#     await websocket.accept()
#     active_connections.append(websocket)
#     print(f"✅ New WebSocket connection. Total connections: {len(active_connections)}")
    
#     # Send initial data when client connects
#     try:
#         await broadcast_enquiries_update()
#     except Exception as e:
#         print(f"❌ Error sending initial data: {e}")
    
#     try:
#         while True:
#             # Keep connection alive and handle any incoming messages
#             message = await websocket.receive_text()
#             print(f"📨 Received message from client: {message}")
#     except WebSocketDisconnect:
#         if websocket in active_connections:
#             active_connections.remove(websocket)
#         print(f"❌ WebSocket disconnected. Total connections: {len(active_connections)}")
#     except Exception as e:
#         print(f"❌ WebSocket error: {e}")
#         if websocket in active_connections:
#             active_connections.remove(websocket)

# async def broadcast_enquiries_update():
#     """
#     Send all current enquiries to connected clients.
#     """
#     if not active_connections:
#         print("⚠️ No active WebSocket connections to broadcast to")
#         return
    
#     print(f"📡 Broadcasting to {len(active_connections)} active connections...")
    
#     try:
#         all_docs = []
#         collection_names = db.list_collection_names()
#         print(f"📂 Found {len(collection_names)} collections")
        
#         for collection_name in collection_names:
#             collection = db[collection_name]
#             documents = list(collection.find({}))
            
#             for doc in documents:
#                 # Convert ObjectId to string
#                 doc["_id"] = str(doc["_id"])
                
#                 # Convert datetime to ISO string if present
#                 if "timestamp" in doc and hasattr(doc["timestamp"], 'isoformat'):
#                     doc["timestamp"] = doc["timestamp"].isoformat()
                
#                 # Add collection name
#                 doc["__collection__"] = collection_name
                
#             all_docs.extend(documents)
#             print(f"📦 Found {len(documents)} documents in `{collection_name}`")

#         payload = {"enquiries": all_docs}
#         payload_json = json.dumps(payload)
        
#         print(f"📤 Sending payload with {len(all_docs)} total documents")
        
#         # Track disconnected connections
#         disconnected = []
        
#         for conn in active_connections:
#             try:
#                 await conn.send_text(payload_json)
#                 print(f"✅ Successfully sent data to connection")
#             except Exception as e:
#                 print(f"❌ Failed to send to connection: {e}")
#                 disconnected.append(conn)

#         # Remove disconnected connections
#         for conn in disconnected:
#             if conn in active_connections:
#                 active_connections.remove(conn)
        
#         print(f"📡 Broadcast complete. Sent to {len(active_connections)} connections")
        
#     except Exception as e:
#         print(f"❌ Error in broadcast_enquiries_update: {e}")
#         logging.exception("Full error details:")

@router.post("/vapi/webhook")  # Fixed the double slash
async def vapi_webhook_listener(request: Request):
    try:
        body = await request.json()

        print(f"\n{'='*80}")
        print(f"📡 [WEBHOOK RECEIVED] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*80}")

        message = body.get('message', {})
        message_type = message.get('type', 'unknown')

        print(f"👉 MESSAGE TYPE: {message_type}")

        # === 1️⃣  Print "CALL ONGOING" when status update ===
        if message_type == 'status-update':
            status = message.get('status')
            if status == 'ongoing':
                print(f"📞 CALL ONGOING...")

        # === 2️⃣  When call ends, print & update DB ===
        if message_type == 'end-of-call-report':
            analysis = message.get('analysis', {})
            summary = analysis.get('summary')
            structured_data = analysis.get('structuredData')
            recording_url = message.get('recordingUrl')
            duration = message.get('duration')
            
            print(f"\n📝 SUMMARY:\n{summary}")
            print(f"\n📊 STRUCTURED DATA:\n{json.dumps(structured_data, indent=2)}")
            print(f"🎙️ RECORDING URL: {recording_url}")
            print(f"⏱️ DURATION: {duration}")
            
            call_id = message.get('call', {}).get('id')
            print(f"👉 CALL ID: {call_id}")
            
            if not call_id:
                print("❌ No call ID found in webhook")
                return {"status": "error", "message": "No call ID found"}
            
            # ✅  Update the vendor doc containing this call_id
            matched = False
            updated_collection = None
            
            for collection_name in db.list_collection_names():
                collection = db[collection_name]
                vendor_doc = collection.find_one({"call_ids": call_id})
                
                if vendor_doc:
                    matched = True
                    updated_collection = collection_name
                    
                    update_fields = {
                        "call_summary": summary,
                        "call_status": "Completed",
                        "call_duration": duration,
                        "call_recording": recording_url,
                        "call_transcription": summary,
                        "structured_data": structured_data or {},
                        "timestamp": datetime.utcnow()
                    }
                    
                    result = collection.update_one(
                        {"_id": vendor_doc["_id"]},
                        {"$set": update_fields}
                    )
                    
                    print(f"✅ Updated vendor doc in `{collection_name}` with call details & structured data.")
                    print(f"📊 Update result: matched={result.matched_count}, modified={result.modified_count}")
                    
                    # 🚀 CRITICAL: Broadcast the update to WebSocket clients
                    print("📡 Broadcasting update to WebSocket clients...")
                    # await broadcast_enquiries_update()
                    print("✅ Broadcast completed")
                    
                    break

            if not matched:
                print(f"⚠️ No vendor document found with call_id `{call_id}`")
                
                # Debug: Let's see what call_ids exist
                print("🔍 Debugging - Available call_ids in database:")
                for collection_name in db.list_collection_names():
                    collection = db[collection_name]
                    docs_with_call_ids = list(collection.find({"call_ids": {"$exists": True}}, {"call_ids": 1, "name": 1}))
                    for doc in docs_with_call_ids:
                        print(f"  - Collection: {collection_name}, Vendor: {doc.get('name')}, Call IDs: {doc.get('call_ids')}")

        print(f"{'='*80}\n")
        return {"status": "received", "timestamp": datetime.now().isoformat()}

    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        logging.exception("Full webhook error details:")
        return {"status": "error", "message": str(e)}

# Add a test endpoint to manually trigger broadcasts
# @router.get("/test-broadcast")
# async def test_broadcast():
#     """Test endpoint to manually trigger a WebSocket broadcast"""
#     try:
#         await broadcast_enquiries_update()
#         return {"status": "success", "connections": len(active_connections)}
#     except Exception as e:
#         return {"status": "error", "message": str(e)}
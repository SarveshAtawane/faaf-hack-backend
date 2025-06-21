from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from fastapi import APIRouter
# from backend.vendor_app.db import db  # Assuming you have a db module to connect to MongoDB
from db.mongo import db

class PatchVendorRequest(BaseModel):
    collection_name: str
    vendor_id: str
    updates: Dict[str, Any]  # allows flexible update fields
router = APIRouter()

@router.patch("/patch_vendor_data")
def patch_vendor_data(req: PatchVendorRequest):
    try:
        collection = db[req.collection_name]

        update_fields = {}
        for key, value in req.updates.items():
            update_fields[key] = value

        result = collection.update_one(
            {"_id": req.vendor_id},
            {"$set": update_fields}
        )

        if result.matched_count == 0:
            return JSONResponse(status_code=404, content={"message": "Vendor not found"})

        return JSONResponse(status_code=200, content={
            "message": "Vendor data updated successfully",
            "modified_count": result.modified_count
        })

    except Exception as e:
        return JSONResponse(status_code=500, content={"message": str(e)})

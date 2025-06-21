from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.search import router as search_router
from routes.enquiry import router as enquiry_router
from routes.vapi import router as vapi_router   # ✅ ADD THIS
from routes.patch_vendor_data import router as patch_vendor_data   # ✅ ADD THIS
from routes.place_porter_order import router as place_porter_order   # ✅ ADD THIS
app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(search_router)
app.include_router(enquiry_router)
app.include_router(vapi_router)   # ✅ ADD THIS
app.include_router(patch_vendor_data)   # ✅ ADD THIS
app.include_router(place_porter_order, prefix="/api")


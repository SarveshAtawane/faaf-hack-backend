from fastapi import APIRouter
from models.schemas import SearchRequest
from serpapi import GoogleSearch
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
router = APIRouter()
SERP_API_API_KEY = os.getenv("SERP_API_API_KEY")
@router.post("/search")
def search_vendors(req: SearchRequest):
    if "," in req.location:
        lat, lng = req.location.split(",")
        ll = f"@{lat.strip()},{lng.strip()},16z"
    else:
        ll = "@19.9940148,73.804693,16z"

    params = {
        "engine": "google_maps",
        "q": req.query,
        "ll": ll,
        "api_key": SERP_API_API_KEY # put this in .env or config
    }

    search = GoogleSearch(params)
    results = search.get_dict()

    vendors = []
    for r in results.get("local_results", []):
        phone = r.get("phone")
        if phone:
            vendors.append({
                "name": r.get("title"),
                "address": r.get("address"),
                "phone": phone,
                "lat": r.get("gps_coordinates")['latitude'],
                "lon": r.get("gps_coordinates")['longitude']
            })

    return {"results": vendors}

from pydantic import BaseModel
from typing import List, Optional

class SearchRequest(BaseModel):
    query: str
    location: str

class EnquiryRequest(BaseModel):
    product: str
    vendors: List[dict]
    location: str
    additional_details: Optional[str] = ""
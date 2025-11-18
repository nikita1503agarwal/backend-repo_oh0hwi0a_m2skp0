import os
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from database import db, create_document, get_documents

app = FastAPI(title="Armasindo-Inspired Industrial Site API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -----------------------------
# Models (aligned with schemas)
# -----------------------------
class Product(BaseModel):
    title: str
    slug: str
    category: str
    brand: Optional[str] = None
    description: Optional[str] = None
    specs: Optional[List[str]] = None
    images: Optional[List[str]] = None
    featured: bool = False


class Inquiry(BaseModel):
    name: str
    email: str
    company: Optional[str] = None
    phone: Optional[str] = None
    message: str
    product_slug: Optional[str] = None


# -----------------------------
# Utilities
# -----------------------------
import re

def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"[\s-]+", "-", text)
    return text


def serialize(doc: dict) -> dict:
    if not doc:
        return doc
    d = dict(doc)
    if "_id" in d:
        d["id"] = str(d.pop("_id"))
    return d


# -----------------------------
# Basic & health endpoints
# -----------------------------
@app.get("/")
def read_root():
    return {"message": "Industrial API running", "version": "1.0"}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": "❌ Not Set",
        "database_name": "❌ Not Set",
        "connection_status": "Not Connected",
        "collections": [],
    }
    try:
        from database import db as _db
        if _db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = _db.name if hasattr(_db, "name") else "✅ Set"
            response["connection_status"] = "Connected"
            try:
                response["collections"] = _db.list_collection_names()
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️ Connected but Error: {str(e)[:80]}"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:80]}"
    return response


# -----------------------------
# Products Endpoints
# -----------------------------
@app.get("/products", response_model=List[Product])
def list_products(category: Optional[str] = None, featured: Optional[bool] = None):
    if db is None:
        # Fallback static items if DB not configured
        sample = _sample_products()
        items = sample
    else:
        filter_obj = {}
        if category:
            filter_obj["category"] = category
        if featured is not None:
            filter_obj["featured"] = featured
        docs = get_documents("product", filter_obj)
        items = [serialize(d) for d in docs]
        if not items:
            # Seed samples on first run
            for p in _sample_products():
                try:
                    db["product"].update_one({"slug": p["slug"]}, {"$setOnInsert": p}, upsert=True)
                except Exception:
                    pass
            docs = get_documents("product", filter_obj)
            items = [serialize(d) for d in docs]
    # Coerce to Product model
    return [Product(**{k: v for k, v in item.items() if k in Product.model_fields}) for item in items]


@app.get("/products/{slug}", response_model=Product)
def get_product(slug: str):
    if db is None:
        for p in _sample_products():
            if p["slug"] == slug:
                return Product(**{k: v for k, v in p.items() if k in Product.model_fields})
        raise HTTPException(status_code=404, detail="Product not found")
    doc = db["product"].find_one({"slug": slug})
    if not doc:
        raise HTTPException(status_code=404, detail="Product not found")
    data = serialize(doc)
    return Product(**{k: v for k, v in data.items() if k in Product.model_fields})


# -----------------------------
# Inquiry (Contact) Endpoints
# -----------------------------
class InquiryResponse(BaseModel):
    status: str
    received_at: datetime


@app.post("/contact", response_model=InquiryResponse)
@app.post("/submit-inquiry", response_model=InquiryResponse)
def submit_inquiry(inquiry: Inquiry):
    payload = inquiry.model_dump()
    if db is not None:
        payload["created_at"] = datetime.utcnow()
        try:
            create_document("inquiry", payload)
        except Exception:
            # Best-effort; still respond success to keep UX smooth
            pass
    return InquiryResponse(status="received", received_at=datetime.utcnow())


# -----------------------------
# Sample data
# -----------------------------

def _sample_products() -> List[dict]:
    return [
        {
            "title": "Industrial Circuit Breaker 3P 100A",
            "slug": "industrial-circuit-breaker-3p-100a",
            "category": "Power Distribution",
            "brand": "ProGuard",
            "description": "Rugged molded-case circuit breaker for industrial panels with high interrupt capacity.",
            "specs": [
                "Rated current: 100A",
                "Poles: 3",
                "Voltage: 415VAC",
                "Breaking capacity: 36kA",
                "Compliance: IEC 60947-2",
            ],
            "images": [
                "https://images.unsplash.com/photo-1581094794329-c8112a89af12?q=80&w=1200&auto=format&fit=crop",
            ],
            "featured": True,
        },
        {
            "title": "Metallic Cable Tray Ladder Type",
            "slug": "metallic-cable-tray-ladder",
            "category": "Cable Management",
            "brand": "SteelFlex",
            "description": "Heavy-duty galvanized steel ladder cable tray for factories and plants.",
            "specs": [
                "Material: GI steel",
                "Width: 300mm",
                "Height: 100mm",
                "Finish: Hot-dip galvanized",
                "Accessories: Bends, tees, reducers",
            ],
            "images": [
                "https://images.unsplash.com/photo-1581090464777-f3220bbe1b8b?q=80&w=1200&auto=format&fit=crop",
            ],
            "featured": True,
        },
        {
            "title": "Programmable Logic Controller (PLC)",
            "slug": "programmable-logic-controller-plc",
            "category": "Automation",
            "brand": "AutoCore",
            "description": "Compact PLC for machine automation with Ethernet and Modbus.",
            "specs": [
                "I/O: 24 DI, 16 DO, 4 AI",
                "Protocols: Modbus TCP/RTU",
                "Programming: Ladder/Structured Text",
                "Comms: 2x RS485, 1x Ethernet",
            ],
            "images": [
                "https://images.unsplash.com/photo-1581092578034-95c2a5b9c9d7?q=80&w=1200&auto=format&fit=crop",
            ],
            "featured": False,
        },
    ]


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

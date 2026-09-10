import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import settings
from app.database import engine, Base, SessionLocal
from app.models.database_models import User, Product, Rule
from app.auth.jwt_handler import hash_password

from app.api import auth, scans, analysis, products, compliance, reports, inspections, rules

# Initialize Database Tables
Base.metadata.create_all(bind=engine)

def seed_database():
    db = SessionLocal()
    try:
        # Seed Users
        if db.query(User).count() == 0:
            db.add_all([
                User(
                    id="usr_consumer_01",
                    email="consumer@scanshield.gov.in",
                    password_hash=hash_password("consumer123"),
                    full_name="Standard Consumer",
                    role="CONSUMER"
                ),
                User(
                    id="usr_inspector_01",
                    email="inspector@scanshield.gov.in",
                    password_hash=hash_password("inspector123"),
                    full_name="Inspector Rajesh Sharma",
                    role="INSPECTOR",
                    badge_number="LM-INSP-2026-884"
                ),
                User(
                    id="usr_admin_01",
                    email="admin@scanshield.gov.in",
                    password_hash=hash_password("admin123"),
                    full_name="System Administrator",
                    role="ADMIN",
                    badge_number="LM-ADM-001"
                )
            ])

        # Seed Demo Product
        if db.query(Product).count() == 0:
            db.add(Product(
                id="prd_lays_classic_01",
                product_name="Lay's Classic Potato Chips",
                brand_name="Lay's",
                category="Snacks & Namkeen",
                manufacturer="PepsiCo India Holdings Pvt. Ltd., Village Channo, Patiala - 147 105, India",
                net_quantity="52 g",
                mrp="₹ 20.00 (Inclusive of all taxes)",
                mfg_date="15 Jun 2024",
                best_before="14 Dec 2024",
                consumer_care="1800 22 4020, consumercare@pepsico.com",
                fssai_license="10014063000346",
                country_of_origin="India",
                barcode="8901499007567"
            ))

        # Seed Rules
        if db.query(Rule).count() == 0:
            from app.rules.repository import LEGAL_METROLOGY_RULES
            for r in LEGAL_METROLOGY_RULES:
                db.add(Rule(
                    id=r["id"],
                    rule_code=r["rule_code"],
                    name=r["name"],
                    category=r["category"],
                    requirement=r["requirement"],
                    validation_logic=r["validation_logic"],
                    severity=r["severity"],
                    version=r["version"],
                    active=r["active"]
                ))
        db.commit()
    except Exception as e:
        print(f"Seed database warning: {e}")
    finally:
        db.close()

seed_database()

app = FastAPI(
    title="ScanShield Compliance Platform API",
    description="Legal Metrology Packaged Commodity AI Compliance API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(auth.router)
app.include_router(scans.router)
app.include_router(analysis.router)
app.include_router(products.router)
app.include_router(compliance.router)
app.include_router(reports.router)
app.include_router(inspections.router)
app.include_router(rules.router)

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# Static file mounts
storage_dir = os.path.join(PROJECT_ROOT, "storage")
if os.path.exists(storage_dir):
    app.mount("/storage", StaticFiles(directory=storage_dir), name="storage")

ref_img_path = os.path.join(PROJECT_ROOT, "reference Image")
if os.path.exists(ref_img_path):
    app.mount("/reference Image", StaticFiles(directory=ref_img_path), name="reference_images")

frontend_dir = os.path.join(PROJECT_ROOT, "frontend")
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="frontend_static")

@app.get("/")
def read_root():
    index_path = os.path.join(frontend_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "ScanShield Backend API is Running", "docs": "/docs"}

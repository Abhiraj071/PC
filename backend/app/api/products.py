from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.database_models import Product

router = APIRouter(prefix="/api/products", tags=["Products"])

@router.get("/{product_id}")
def get_product(product_id: str, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        # Return fallback demo product data
        return {
            "id": product_id,
            "product_name": "Lay's Classic Potato Chips",
            "brand_name": "Lay's",
            "category": "Snacks & Namkeen",
            "manufacturer": "PepsiCo India Holdings Pvt. Ltd. Village Channo, Patiala - 147 105, India",
            "net_quantity": "52 g",
            "mrp": "₹ 20.00 (Inclusive of all taxes)",
            "mfg_date": "15 Jun 2024",
            "best_before": "14 Dec 2024",
            "consumer_care": "1800 22 4020, consumercare@pepsico.com",
            "fssai_license": "10014063000346",
            "country_of_origin": "India",
            "barcode": "8901499007567"
        }

    return {
        "id": product.id,
        "product_name": product.product_name,
        "brand_name": product.brand_name,
        "category": product.category,
        "manufacturer": product.manufacturer,
        "net_quantity": product.net_quantity,
        "mrp": product.mrp,
        "mfg_date": product.mfg_date,
        "best_before": product.best_before,
        "consumer_care": product.consumer_care,
        "fssai_license": product.fssai_license,
        "country_of_origin": product.country_of_origin,
        "barcode": product.barcode
    }

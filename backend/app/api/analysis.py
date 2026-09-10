import os
import glob
import json
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.models.database_models import Scan, ExtractedData
from app.ocr.extractor import OCRExtractor
from app.ai.info_extractor import AIInfoExtractor

router = APIRouter(prefix="/api/analysis", tags=["Analysis"])

ocr_extractor = OCRExtractor()
ai_extractor = AIInfoExtractor()

@router.post("/{scan_id}")
def run_analysis(scan_id: str, db: Session = Depends(get_db)):
    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    if not scan:
        if scan_id == "scn_demo":
            demo_structured = {
                "product_name": "Classic Potato Chips",
                "brand_name": "Lay's",
                "mrp": "₹ 20.00 (Inclusive of all taxes)",
                "net_quantity": "52 g",
                "manufacturer": "PepsiCo India Holdings Pvt. Ltd. Village Channo, Patiala - 147 105, India",
                "manufacture_date": "15 Jun 2024",
                "best_before": "14 Dec 2024",
                "consumer_care": "1800 22 4020, consumercare@pepsico.com",
                "fssai_license": "10014063000346",
                "country_of_origin": "India",
                "category": "Snacks & Namkeen",
                "other_declarations": ["Ingredients List", "Nutritional Information", "Vegetarian Logo", "Barcode / GTIN"],
                "confidences": {
                    "mrp": 0.99,
                    "net_quantity": 0.99,
                    "manufacturer": 0.98,
                    "manufacture_date": 0.96,
                    "best_before": 0.97,
                    "consumer_care": 0.95
                }
            }
            return {
                "scan_id": "scn_demo",
                "raw_ocr_text": "Lay's Classic Potato Chips\nNet Wt. 52 g\nMRP ₹ 20.00 (Inclusive of all taxes)",
                "confidence": 0.97,
                "quality": {"is_good_quality": True, "score": 0.95},
                "structured_data": demo_structured
            }
        raise HTTPException(status_code=404, detail="Scan record not found")

    # Find all side photos uploaded for this scan
    upload_pattern = os.path.join(settings.UPLOAD_DIR, f"{scan_id}_*.jpg")
    all_matched = glob.glob(upload_pattern)

    # Exclude _preprocessed.jpg and deduplicate _label.jpg if distinct side files exist
    non_label_sides = [p for p in all_matched if not p.endswith(f"{scan_id}_label.jpg") and not p.endswith("_preprocessed.jpg")]
    if non_label_sides:
        side_images = non_label_sides
    elif all_matched:
        side_images = [p for p in all_matched if not p.endswith("_preprocessed.jpg")]
    else:
        primary = scan.original_image_path or scan.preprocessed_image_path
        side_images = [primary] if (primary and os.path.exists(primary)) else []

    extracted_sections = []
    confidences = []
    qualities = []

    for img_path in side_images:
        res = ocr_extractor.extract(img_path)
        norm_txt = (res.get("normalized_text") or "").strip()
        if norm_txt:
            extracted_sections.append(norm_txt)
            if res.get("confidence", 0) > 0:
                confidences.append(res["confidence"])
        if res.get("quality"):
            qualities.append(res["quality"])

    # If side images yielded no text, also try the preprocessed image
    if not extracted_sections and scan.preprocessed_image_path and os.path.exists(scan.preprocessed_image_path):
        res_prep = ocr_extractor.extract(scan.preprocessed_image_path)
        norm_txt = (res_prep.get("normalized_text") or "").strip()
        if norm_txt:
            extracted_sections.append(norm_txt)
            if res_prep.get("confidence", 0) > 0:
                confidences.append(res_prep["confidence"])

    if not extracted_sections:
        raise HTTPException(
            status_code=400,
            detail="No readable text detected on the package label. Please ensure the label is clear, well-lit, and not blurred, then try again."
        )

    # Combine all extracted text across all product packaging sides
    raw_ocr_text = "\n\n--- PACKAGING SECTION ---\n\n".join(extracted_sections)
    avg_confidence = round(sum(confidences) / len(confidences), 2) if confidences else 0.85

    # AI Information Extraction on real aggregated OCR text
    structured_info = ai_extractor.extract_structured_info(raw_ocr_text)

    # Store Extracted Data in DB
    existing_ext = db.query(ExtractedData).filter(ExtractedData.scan_id == scan_id).first()
    if existing_ext:
        existing_ext.raw_ocr_text = raw_ocr_text
        existing_ext.confidence = avg_confidence
        existing_ext.extracted_json = json.dumps(structured_info)
    else:
        ext_record = ExtractedData(
            id=f"ext_{uuid.uuid4().hex[:12]}",
            scan_id=scan_id,
            raw_ocr_text=raw_ocr_text,
            confidence=avg_confidence,
            extracted_json=json.dumps(structured_info)
        )
        db.add(ext_record)

    scan.status = "PROCESSED"
    db.commit()

    return {
        "scan_id": scan_id,
        "raw_ocr_text": raw_ocr_text,
        "confidence": avg_confidence,
        "quality": qualities[0] if qualities else {},
        "structured_data": structured_info
    }

@router.get("/{scan_id}")
def get_analysis(scan_id: str, db: Session = Depends(get_db)):
    ext = db.query(ExtractedData).filter(ExtractedData.scan_id == scan_id).first()
    if not ext:
        return run_analysis(scan_id, db)

    return {
        "scan_id": scan_id,
        "raw_ocr_text": ext.raw_ocr_text,
        "confidence": ext.confidence,
        "structured_data": json.loads(ext.extracted_json)
    }

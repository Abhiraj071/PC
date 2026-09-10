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
        raise HTTPException(status_code=404, detail="Scan record not found")

    # Find all side photos uploaded for this scan
    upload_pattern = os.path.join(settings.UPLOAD_DIR, f"{scan_id}_*.jpg")
    side_images = glob.glob(upload_pattern)

    if not side_images:
        primary = scan.original_image_path or scan.preprocessed_image_path
        if primary and os.path.exists(primary):
            side_images = [primary]

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

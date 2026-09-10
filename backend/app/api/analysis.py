import json
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
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

    image_to_process = scan.preprocessed_image_path or scan.original_image_path

    # OCR Extraction
    ocr_res = ocr_extractor.extract(image_to_process)

    if not ocr_res.get("is_valid_label", True):
        raise HTTPException(
            status_code=400,
            detail="No product packaging label detected in this photo. A human face, selfie, or non-packaging photo cannot be processed. Please take a clear photo of a product package label containing Legal Metrology declarations."
        )

    raw_ocr_text = ocr_res["normalized_text"]
    confidence = ocr_res["confidence"]

    # AI Information Extraction
    structured_info = ai_extractor.extract_structured_info(raw_ocr_text)

    # Store Extracted Data in DB
    existing_ext = db.query(ExtractedData).filter(ExtractedData.scan_id == scan_id).first()
    if existing_ext:
        existing_ext.raw_ocr_text = raw_ocr_text
        existing_ext.confidence = confidence
        existing_ext.extracted_json = json.dumps(structured_info)
    else:
        ext_record = ExtractedData(
            id=f"ext_{uuid.uuid4().hex[:12]}",
            scan_id=scan_id,
            raw_ocr_text=raw_ocr_text,
            confidence=confidence,
            extracted_json=json.dumps(structured_info)
        )
        db.add(ext_record)

    scan.status = "PROCESSED"
    db.commit()

    return {
        "scan_id": scan_id,
        "raw_ocr_text": raw_ocr_text,
        "confidence": confidence,
        "quality": ocr_res.get("quality", {}),
        "structured_data": structured_info
    }

@router.get("/{scan_id}")
def get_analysis(scan_id: str, db: Session = Depends(get_db)):
    ext = db.query(ExtractedData).filter(ExtractedData.scan_id == scan_id).first()
    if not ext:
        # Trigger analysis automatically if not run yet
        return run_analysis(scan_id, db)

    return {
        "scan_id": scan_id,
        "raw_ocr_text": ext.raw_ocr_text,
        "confidence": ext.confidence,
        "structured_data": json.loads(ext.extracted_json)
    }

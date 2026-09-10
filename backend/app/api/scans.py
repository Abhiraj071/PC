import os
import uuid
import shutil
from typing import Optional, List
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, Form
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.models.database_models import Scan, User
from app.auth.jwt_handler import get_current_user
from app.image_processing.preprocessor import preprocess_image

router = APIRouter(prefix="/api/scans", tags=["Scans"])

@router.post("")
def upload_scan(
    file: Optional[UploadFile] = File(None),
    files: Optional[List[UploadFile]] = File(None),
    sides: Optional[List[str]] = Form(None),
    barcode: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    scan_id = f"scn_{uuid.uuid4().hex[:12]}"
    filename = f"{scan_id}_label.jpg"
    original_path = os.path.join(settings.UPLOAD_DIR, filename)

    # Use multi-file list if provided, otherwise fallback to single file
    upload_list = []
    if files and len(files) > 0:
        upload_list = [f for f in files if f and f.filename]
    elif file and file.filename:
        upload_list = [file]

    saved_files = []
    if upload_list:
        for idx, up_file in enumerate(upload_list):
            side_tag = "front"
            if sides and idx < len(sides) and sides[idx]:
                side_tag = str(sides[idx]).strip()
            elif idx > 0:
                side_tag = f"side_{idx}"
            
            side_filename = f"{scan_id}_{side_tag}.jpg"
            side_path = os.path.join(settings.UPLOAD_DIR, side_filename)
            with open(side_path, "wb") as buffer:
                shutil.copyfileobj(up_file.file, buffer)
            saved_files.append(side_path)

        # Primary label file is the first side image (usually front)
        shutil.copyfile(saved_files[0], original_path)
    else:
        # Create a blank 400x400 image placeholder if no file attached
        import cv2
        import numpy as np
        blank = np.zeros((400, 400, 3), dtype=np.uint8)
        cv2.imwrite(original_path, blank)
        saved_files.append(original_path)

    # Preprocess primary image
    preprocessed_filename = f"{scan_id}_preprocessed.jpg"
    preprocessed_path = preprocess_image(original_path, preprocessed_filename)

    scan = Scan(
        id=scan_id,
        user_id=current_user.id if current_user else None,
        product_id=None,
        original_image_path=original_path,
        preprocessed_image_path=preprocessed_path,
        barcode_data=barcode,
        status="UPLOADED"
    )
    db.add(scan)
    db.commit()
    db.refresh(scan)

    return {
        "scan_id": scan.id,
        "status": scan.status,
        "original_image_path": f"/storage/uploads/{filename}",
        "preprocessed_image_path": f"/storage/preprocessed/{preprocessed_filename}",
        "barcode_data": scan.barcode_data,
        "side_count": len(saved_files),
        "created_at": scan.created_at
    }

@router.get("/{scan_id}")
def get_scan(scan_id: str, db: Session = Depends(get_db)):
    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    if not scan:
        if scan_id == "scn_demo":
            return {
                "scan_id": "scn_demo",
                "product_id": "prd_lays_classic_01",
                "original_image_url": "",
                "preprocessed_image_url": None,
                "barcode_data": "8901499007567",
                "status": "COMPLETED",
                "created_at": None
            }
        raise HTTPException(status_code=404, detail="Scan record not found")
    
    orig_name = os.path.basename(scan.original_image_path)
    prep_name = os.path.basename(scan.preprocessed_image_path) if scan.preprocessed_image_path else ""

    return {
        "scan_id": scan.id,
        "product_id": scan.product_id,
        "original_image_url": f"/storage/uploads/{orig_name}",
        "preprocessed_image_url": f"/storage/preprocessed/{prep_name}" if prep_name else None,
        "barcode_data": scan.barcode_data,
        "status": scan.status,
        "created_at": scan.created_at
    }

import uuid
import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.database_models import ConsumerReport, Scan, Product, User, Inspection
from app.schemas.pydantic_schemas import ReportCreateRequest
from app.auth.jwt_handler import get_current_user

router = APIRouter(prefix="/api/reports", tags=["Consumer Reports"])

@router.post("")
def create_report(
    req: ReportCreateRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    scan = db.query(Scan).filter(Scan.id == req.scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan ID not found")

    report_id = f"rpt_{uuid.uuid4().hex[:12]}"
    report_number = f"CR-2026-{uuid.uuid4().hex[:5].upper()}"

    report = ConsumerReport(
        id=report_id,
        report_number=report_number,
        user_id=current_user.id if current_user else "usr_consumer_01",
        scan_id=req.scan_id,
        product_id=scan.product_id or "prd_lays_classic_01",
        issue_title=req.issue_title,
        issue_description=req.issue_description,
        user_comment=req.user_comment,
        status="UNDER_REVIEW"
    )
    db.add(report)

    # Initialize associated pending inspection
    inspection = Inspection(
        id=f"insp_{uuid.uuid4().hex[:12]}",
        report_id=report_id,
        decision="PENDING"
    )
    db.add(inspection)
    db.commit()
    db.refresh(report)

    return {
        "report_id": report.id,
        "report_number": report.report_number,
        "scan_id": report.scan_id,
        "status": report.status,
        "issue_title": report.issue_title,
        "user_comment": report.user_comment,
        "created_at": report.created_at
    }

@router.get("")
def list_reports(db: Session = Depends(get_db), current_user: Optional[User] = Depends(get_current_user)):
    reports = db.query(ConsumerReport).order_by(ConsumerReport.created_at.desc()).all()
    res = []
    for r in reports:
        prod = db.query(Product).filter(Product.id == r.product_id).first()
        res.append({
            "report_id": r.id,
            "report_number": r.report_number,
            "scan_id": r.scan_id,
            "product_name": prod.product_name if prod else "Lay's Classic Potato Chips",
            "issue_title": r.issue_title,
            "status": r.status,
            "created_at": r.created_at
        })
    return res

@router.get("/{report_id}")
def get_report_details(report_id: str, db: Session = Depends(get_db)):
    report = db.query(ConsumerReport).filter(ConsumerReport.id == report_id).first()
    if not report:
        # Fallback to search by report number or report ID prefix
        report = db.query(ConsumerReport).filter(ConsumerReport.report_number == report_id).first()
    
    if not report:
        raise HTTPException(status_code=404, detail="Consumer report not found")

    prod = db.query(Product).filter(Product.id == report.product_id).first()
    inspection = db.query(Inspection).filter(Inspection.report_id == report.id).first()

    return {
        "report_id": report.id,
        "report_number": report.report_number,
        "scan_id": report.scan_id,
        "product": {
            "name": prod.product_name if prod else "Lay's Classic Potato Chips",
            "brand": prod.brand_name if prod else "Lay's",
            "mrp": prod.mrp if prod else "₹ 20.00 (Inclusive of all taxes)",
            "manufacturer": prod.manufacturer if prod else "PepsiCo India Holdings Pvt. Ltd."
        },
        "issue_title": report.issue_title,
        "issue_description": report.issue_description,
        "user_comment": report.user_comment,
        "status": report.status,
        "created_at": report.created_at,
        "inspection": {
            "decision": inspection.decision if inspection else "PENDING",
            "remarks": inspection.remarks if inspection else None,
            "pdf_report_path": inspection.pdf_report_path if inspection else None
        }
    }

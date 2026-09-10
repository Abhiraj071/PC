import os
import json
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.database_models import Inspection, ConsumerReport, Scan, Product, ExtractedData, ComplianceResult, ComplianceCheck, User
from app.schemas.pydantic_schemas import InspectionDecisionRequest
from app.auth.jwt_handler import get_current_user
from app.reports.pdf_generator import generate_pdf_report

router = APIRouter(prefix="/api/inspections", tags=["Inspector Workstation"])

@router.get("")
def list_inspections(db: Session = Depends(get_db)):
    inspections = db.query(Inspection).order_by(Inspection.inspected_at.desc()).all()
    res = []
    for insp in inspections:
        report = db.query(ConsumerReport).filter(ConsumerReport.id == insp.report_id).first()
        prod_name = "Lay's Classic Potato Chips"
        if report and report.product_id:
            p = db.query(Product).filter(Product.id == report.product_id).first()
            if p:
                prod_name = p.product_name

        res.append({
            "inspection_id": insp.id,
            "report_id": insp.report_id,
            "report_number": report.report_number if report else "CR-2026-1001",
            "product_name": prod_name,
            "decision": insp.decision,
            "remarks": insp.remarks,
            "pdf_report_path": f"/storage/reports/{os.path.basename(insp.pdf_report_path)}" if insp.pdf_report_path else None,
            "inspected_at": insp.inspected_at
        })
    return res

@router.get("/{inspection_id}")
def get_inspection_workspace(inspection_id: str, db: Session = Depends(get_db)):
    insp = db.query(Inspection).filter(Inspection.id == inspection_id).first()
    if not insp:
        # Fallback search by report_id
        insp = db.query(Inspection).filter(Inspection.report_id == inspection_id).first()

    if not insp:
        raise HTTPException(status_code=404, detail="Inspection record not found")

    report = db.query(ConsumerReport).filter(ConsumerReport.id == insp.report_id).first()
    scan = db.query(Scan).filter(Scan.id == report.scan_id).first() if report else None
    prod = db.query(Product).filter(Product.id == report.product_id).first() if report else None
    ext = db.query(ExtractedData).filter(ExtractedData.scan_id == report.scan_id).first() if report else None
    comp = db.query(ComplianceResult).filter(ComplianceResult.scan_id == report.scan_id).first() if report else None
    checks = db.query(ComplianceCheck).filter(ComplianceCheck.compliance_result_id == comp.id).all() if comp else []

    orig_image = f"/storage/uploads/{os.path.basename(scan.original_image_path)}" if scan and scan.original_image_path else "/reference Image/2.png"

    return {
        "inspection_id": insp.id,
        "report_id": insp.report_id,
        "report_number": report.report_number if report else "CR-2026-1001",
        "product": {
            "product_name": prod.product_name if prod else "Lay's Classic Potato Chips",
            "brand_name": prod.brand_name if prod else "Lay's",
            "manufacturer": prod.manufacturer if prod else "PepsiCo India Holdings Pvt. Ltd.",
            "mrp": prod.mrp if prod else "₹ 20.00 (Inclusive of all taxes)",
            "net_quantity": prod.net_quantity if prod else "52 g",
            "mfg_date": prod.mfg_date if prod else "15 Jun 2024",
            "best_before": prod.best_before if prod else "14 Dec 2024"
        },
        "extracted_data": json.loads(ext.extracted_json) if ext else {},
        "original_image_url": orig_image,
        "compliance": {
            "status": comp.status if comp else "COMPLIANT",
            "checks_passed": comp.checks_passed if comp else 6,
            "issues_found": comp.issues_found if comp else 0,
            "checks": [{"rule_code": c.rule_code, "check_name": c.check_name, "status": c.status, "details": c.details} for c in checks]
        },
        "decision": insp.decision,
        "remarks": insp.remarks,
        "pdf_report_path": f"/storage/reports/{os.path.basename(insp.pdf_report_path)}" if insp.pdf_report_path else None
    }

@router.post("/{inspection_id}/decision")
def make_inspection_decision(
    inspection_id: str,
    req: InspectionDecisionRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    insp = db.query(Inspection).filter(Inspection.id == inspection_id).first()
    if not insp:
        insp = db.query(Inspection).filter(Inspection.report_id == inspection_id).first()

    if not insp:
        raise HTTPException(status_code=404, detail="Inspection record not found")

    report = db.query(ConsumerReport).filter(ConsumerReport.id == insp.report_id).first()
    prod = db.query(Product).filter(Product.id == report.product_id).first() if report else None
    comp = db.query(ComplianceResult).filter(ComplianceResult.scan_id == report.scan_id).first() if report else None
    checks = db.query(ComplianceCheck).filter(ComplianceCheck.compliance_result_id == comp.id).all() if comp else []

    insp.decision = req.decision
    insp.remarks = req.remarks or "Verified and decision submitted by Legal Metrology Inspector."
    insp.inspector_id = current_user.id if current_user else "usr_inspector_01"

    if report:
        report.status = "VERIFIED" if req.decision == "CONFIRMED" else "REJECTED"

    # Generate Digital Inspection PDF Report
    pdf_filename = f"inspection_report_{insp.id}.pdf"
    pdf_data = {
        "report_id": report.id if report else "CR-2026-1001",
        "report_number": report.report_number if report else "CR-2026-1001",
        "created_at": report.created_at.strftime("%Y-%m-%d %H:%M:%S") if report else "2026-09-09 18:00:00",
        "inspector_name": current_user.full_name if current_user else "Inspector Rajesh Sharma",
        "badge_number": current_user.badge_number if (current_user and current_user.badge_number) else "LM-INSP-2026-884",
        "product_name": prod.product_name if prod else "Lay's Classic Potato Chips",
        "brand_name": prod.brand_name if prod else "Lay's",
        "manufacturer": prod.manufacturer if prod else "PepsiCo India Holdings Pvt. Ltd. Village Channo, Patiala - 147 105, India",
        "mrp": prod.mrp if prod else "₹ 20.00 (Inclusive of all taxes)",
        "net_quantity": prod.net_quantity if prod else "52 g",
        "mfg_date": prod.mfg_date if prod else "15 Jun 2024",
        "best_before": prod.best_before if prod else "14 Dec 2024",
        "checks": [{"rule_code": c.rule_code, "check_name": c.check_name, "status": c.status, "details": c.details} for c in checks],
        "decision": req.decision,
        "remarks": insp.remarks
    }

    generated_path = generate_pdf_report(pdf_data, pdf_filename)
    insp.pdf_report_path = generated_path
    db.commit()

    return {
        "inspection_id": insp.id,
        "report_id": insp.report_id,
        "decision": insp.decision,
        "remarks": insp.remarks,
        "pdf_report_url": f"/storage/reports/{pdf_filename}",
        "inspected_at": insp.inspected_at
    }

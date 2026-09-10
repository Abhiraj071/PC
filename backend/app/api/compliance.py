import json
import uuid
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.database_models import Scan, ExtractedData, ComplianceResult, ComplianceCheck, Violation
from app.compliance.rule_engine import ComplianceEngine
from app.api.analysis import get_analysis

router = APIRouter(prefix="/api/compliance", tags=["Compliance"])

engine = ComplianceEngine()

@router.post("/check/{scan_id}")
def check_compliance(
    scan_id: str,
    payload: Optional[Dict[str, Any]] = Body(None),
    db: Session = Depends(get_db)
):
    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    if not scan and scan_id != "scn_demo":
        raise HTTPException(status_code=404, detail="Scan record not found")

    ext_record = db.query(ExtractedData).filter(ExtractedData.scan_id == scan_id).first() if scan else None
    
    if payload and len(payload) > 0:
        structured_info = payload
        confidence = 0.98
    elif ext_record:
        structured_info = json.loads(ext_record.extracted_json)
        confidence = ext_record.confidence
    else:
        # Fallback to analysis
        analysis_data = get_analysis(scan_id, db)
        structured_info = analysis_data["structured_data"]
        confidence = analysis_data["confidence"]

    # Run Legal Metrology Rule Engine
    res = engine.evaluate_compliance(structured_info, ocr_confidence=confidence)

    # Delete existing compliance result for this scan if re-running
    if scan:
        existing_res = db.query(ComplianceResult).filter(ComplianceResult.scan_id == scan_id).first()
        if existing_res:
            db.query(ComplianceCheck).filter(ComplianceCheck.compliance_result_id == existing_res.id).delete()
            db.query(Violation).filter(Violation.compliance_result_id == existing_res.id).delete()
            db.delete(existing_res)
            db.commit()

    comp_id = f"cmp_{uuid.uuid4().hex[:12]}"
    comp_record = ComplianceResult(
        id=comp_id,
        scan_id=scan_id if scan else "scn_demo",
        status=res["status"],
        checks_passed=res["checks_passed"],
        issues_found=res["issues_found"],
        overall_confidence=res["overall_confidence"],
        highlights_json=json.dumps(res["highlights"])
    )
    db.add(comp_record)

    # Save individual checks
    for check_item in res["checks"]:
        chk = ComplianceCheck(
            id=f"chk_{uuid.uuid4().hex[:12]}",
            compliance_result_id=comp_id,
            rule_code=check_item["rule_code"],
            check_name=check_item["check_name"],
            status=check_item["status"],
            confidence=check_item["confidence"],
            details=check_item["details"]
        )
        db.add(chk)

    # Save violations
    for viol_item in res["violations"]:
        viol = Violation(
            id=f"viol_{uuid.uuid4().hex[:12]}",
            compliance_result_id=comp_id,
            rule_code=viol_item["rule_code"],
            field=viol_item["field"],
            issue_description=viol_item["issue_description"],
            severity=viol_item["severity"],
            evidence_bounding_box=json.dumps({"x": 280, "y": 420, "w": 420, "h": 120})
        )
        db.add(viol)

    if scan:
        scan.status = "COMPLETED"
    db.commit()

    return {
        "scan_id": scan_id,
        "compliance_id": comp_id,
        "status": res["status"],
        "checks_passed": res["checks_passed"],
        "issues_found": res["issues_found"],
        "overall_confidence": res["overall_confidence"],
        "highlights": res["highlights"],
        "checks": res["checks"],
        "violations": res["violations"]
    }

@router.get("/{scan_id}")
def get_compliance(scan_id: str, db: Session = Depends(get_db)):
    comp = db.query(ComplianceResult).filter(ComplianceResult.scan_id == scan_id).first()
    if not comp:
        return check_compliance(scan_id, payload=None, db=db)

    checks = db.query(ComplianceCheck).filter(ComplianceCheck.compliance_result_id == comp.id).all()
    violations = db.query(Violation).filter(Violation.compliance_result_id == comp.id).all()

    return {
        "scan_id": scan_id,
        "compliance_id": comp.id,
        "status": comp.status,
        "checks_passed": comp.checks_passed,
        "issues_found": comp.issues_found,
        "overall_confidence": comp.overall_confidence,
        "highlights": json.loads(comp.highlights_json) if comp.highlights_json else [],
        "checks": [{"rule_code": c.rule_code, "check_name": c.check_name, "status": c.status, "confidence": c.confidence, "details": c.details} for c in checks],
        "violations": [{"rule_code": v.rule_code, "field": v.field, "issue_description": v.issue_description, "severity": v.severity, "evidence_bounding_box": json.loads(v.evidence_bounding_box) if v.evidence_bounding_box else None} for v in violations]
    }

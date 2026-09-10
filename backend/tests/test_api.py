import os
import uuid
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_read_root():
    response = client.get("/")
    assert response.status_code == 200

def test_auth_login():
    email = f"testuser_{uuid.uuid4().hex[:8]}@scanshield.gov.in"
    password = "testpassword123"
    
    # 1. Register fresh user
    reg_res = client.post(
        "/api/auth/register",
        json={"email": email, "password": password, "full_name": "Test User", "role": "CONSUMER"}
    )
    assert reg_res.status_code == 200

    # 2. Login user
    response = client.post(
        "/api/auth/login",
        json={"email": email, "password": password}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["role"] == "CONSUMER"

def test_get_rules():
    response = client.get("/api/rules")
    assert response.status_code == 200
    rules = response.json()
    assert len(rules) >= 10
    assert any(r["rule_code"] == "LM-MRP-004" for r in rules)

def test_scan_and_compliance_flow():
    # 1. Upload scan with packaging image
    ref_image_path = r"c:\Users\Hi-Rich\Desktop\ScanShield\reference Image\2.png"
    if os.path.exists(ref_image_path):
        with open(ref_image_path, "rb") as f:
            scan_res = client.post("/api/scans", files={"file": ("label.png", f, "image/png")})
    else:
        scan_res = client.post("/api/scans")
    
    assert scan_res.status_code == 200
    scan_data = scan_res.json()
    scan_id = scan_data["scan_id"]
    assert scan_id.startswith("scn_")

    # 2. Run analysis
    analysis_res = client.post(f"/api/analysis/{scan_id}")
    assert analysis_res.status_code == 200
    ext_data = analysis_res.json()
    assert "structured_data" in ext_data
    assert "raw_ocr_text" in ext_data
    assert len(ext_data["raw_ocr_text"]) > 10

    # 3. Compliance Check
    comp_res = client.post(f"/api/compliance/check/{scan_id}")
    assert comp_res.status_code == 200
    comp_data = comp_res.json()
    assert comp_data["status"] in ["COMPLIANT", "NEEDS_REVIEW", "NON_COMPLIANT"]
    assert len(comp_data["checks"]) >= 6

    # 4. Create Consumer Report
    report_res = client.post(
        "/api/reports",
        json={
            "scan_id": scan_id,
            "issue_title": "Label Readability Query",
            "user_comment": "Testing automated consumer report creation."
        }
    )
    assert report_res.status_code == 200
    rpt_data = report_res.json()
    report_id = rpt_data["report_id"]
    assert rpt_data["status"] == "UNDER_REVIEW"

    # 5. Inspector Verification & Decision
    decision_res = client.post(
        f"/api/inspections/{report_id}/decision",
        json={
            "decision": "CONFIRMED",
            "remarks": "Verified by Inspector during automated test run."
        }
    )
    assert decision_res.status_code == 200
    insp_data = decision_res.json()
    assert insp_data["decision"] == "CONFIRMED"
    assert "pdf_report_url" in insp_data

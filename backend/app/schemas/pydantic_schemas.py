import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr, Field, ConfigDict

# User Schemas
class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: Optional[str] = "CONSUMER" # CONSUMER, INSPECTOR, ADMIN
    badge_number: Optional[str] = None

class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str
    role: str
    full_name: str

class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    badge_number: Optional[str] = None
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)

# Scan Schemas
class ScanCreateResponse(BaseModel):
    scan_id: str
    status: str
    original_image_path: str
    created_at: datetime.datetime

# Extracted Product Data
class StructuredProductData(BaseModel):
    product_name: str
    brand_name: str
    mrp: str
    net_quantity: str
    manufacturer: str
    manufacture_date: Optional[str] = None
    best_before: Optional[str] = None
    consumer_care: Optional[str] = None
    fssai_license: Optional[str] = None
    country_of_origin: Optional[str] = "India"
    category: Optional[str] = "Packaged Goods"
    other_declarations: List[str] = []

class ExtractionResponse(BaseModel):
    scan_id: str
    raw_ocr_text: str
    confidence: float
    structured_data: StructuredProductData

# Compliance Schemas
class ComplianceCheckItem(BaseModel):
    rule_code: str
    check_name: str
    status: str # PASS, FAIL, NEEDS_REVIEW, NOT_DETECTED
    confidence: float
    details: Optional[str] = None

class ViolationItem(BaseModel):
    rule_code: str
    field: str
    issue_description: str
    severity: str
    evidence_bounding_box: Optional[Dict[str, Any]] = None

class ComplianceResultResponse(BaseModel):
    scan_id: str
    status: str # COMPLIANT, NON_COMPLIANT, NEEDS_REVIEW
    checks_passed: int
    issues_found: int
    overall_confidence: float
    highlights: List[str]
    checks: List[ComplianceCheckItem]
    violations: List[ViolationItem]

# Consumer Report Schemas
class ReportCreateRequest(BaseModel):
    scan_id: str
    issue_title: str
    issue_description: Optional[str] = None
    user_comment: Optional[str] = None

class ReportResponse(BaseModel):
    report_id: str
    report_number: str
    scan_id: str
    issue_title: str
    status: str # UNDER_REVIEW, VERIFIED, RESOLVED, REJECTED
    user_comment: Optional[str] = None
    created_at: datetime.datetime
    product_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

# Inspection Verification Schemas
class InspectionDecisionRequest(BaseModel):
    decision: str # CONFIRMED, REJECTED, NEEDS_FURTHER_VERIFICATION
    remarks: Optional[str] = None

class InspectionResponse(BaseModel):
    inspection_id: str
    report_id: str
    decision: str
    remarks: Optional[str] = None
    pdf_report_url: Optional[str] = None
    inspected_at: datetime.datetime

# Rule Management Schemas
class RuleItem(BaseModel):
    id: str
    rule_code: str
    name: str
    category: str
    requirement: str
    validation_logic: str
    severity: str
    version: str
    active: bool

    model_config = ConfigDict(from_attributes=True)

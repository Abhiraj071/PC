import datetime
from sqlalchemy import Column, String, Float, Integer, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(String(64), primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(String(32), nullable=False, default="CONSUMER") # CONSUMER, INSPECTOR, ADMIN
    badge_number = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.now)

    scans = relationship("Scan", back_populates="user")
    reports = relationship("ConsumerReport", back_populates="user")


class Product(Base):
    __tablename__ = "products"

    id = Column(String(64), primary_key=True)
    product_name = Column(String(255), nullable=False)
    brand_name = Column(String(255), nullable=False)
    category = Column(String(128), nullable=False)
    manufacturer = Column(String(255), nullable=False)
    net_quantity = Column(String(64), nullable=False)
    mrp = Column(String(64), nullable=False)
    mfg_date = Column(String(64), nullable=True)
    best_before = Column(String(64), nullable=True)
    consumer_care = Column(Text, nullable=True)
    fssai_license = Column(String(64), nullable=True)
    country_of_origin = Column(String(128), default="India")
    barcode = Column(String(128), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.now)

    scans = relationship("Scan", back_populates="product")


class Rule(Base):
    __tablename__ = "rules"

    id = Column(String(64), primary_key=True)
    rule_code = Column(String(64), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    category = Column(String(128), nullable=False)
    requirement = Column(Text, nullable=False)
    validation_logic = Column(Text, nullable=False)
    severity = Column(String(32), default="high")
    version = Column(String(32), default="1.0")
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.now)


class Scan(Base):
    __tablename__ = "scans"

    id = Column(String(64), primary_key=True)
    user_id = Column(String(64), ForeignKey("users.id"), nullable=True)
    product_id = Column(String(64), ForeignKey("products.id"), nullable=True)
    original_image_path = Column(String(512), nullable=False)
    preprocessed_image_path = Column(String(512), nullable=True)
    barcode_data = Column(String(255), nullable=True)
    status = Column(String(64), default="UPLOADED") # UPLOADED, PROCESSED, COMPLETED, FAILED
    created_at = Column(DateTime, default=datetime.datetime.now)

    user = relationship("User", back_populates="scans")
    product = relationship("Product", back_populates="scans")
    extracted_data = relationship("ExtractedData", back_populates="scan", uselist=False)
    compliance_result = relationship("ComplianceResult", back_populates="scan", uselist=False)


class ExtractedData(Base):
    __tablename__ = "extracted_data"

    id = Column(String(64), primary_key=True)
    scan_id = Column(String(64), ForeignKey("scans.id"), nullable=False)
    raw_ocr_text = Column(Text, nullable=True)
    confidence = Column(Float, default=0.0)
    extracted_json = Column(Text, nullable=False) # JSON payload string
    created_at = Column(DateTime, default=datetime.datetime.now)

    scan = relationship("Scan", back_populates="extracted_data")


class ComplianceResult(Base):
    __tablename__ = "compliance_results"

    id = Column(String(64), primary_key=True)
    scan_id = Column(String(64), ForeignKey("scans.id"), nullable=False)
    status = Column(String(64), nullable=False) # COMPLIANT, NON_COMPLIANT, NEEDS_REVIEW
    checks_passed = Column(Integer, default=0)
    issues_found = Column(Integer, default=0)
    overall_confidence = Column(Float, default=0.0)
    highlights_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.now)

    scan = relationship("Scan", back_populates="compliance_result")
    checks = relationship("ComplianceCheck", back_populates="compliance_result")
    violations = relationship("Violation", back_populates="compliance_result")


class ComplianceCheck(Base):
    __tablename__ = "compliance_checks"

    id = Column(String(64), primary_key=True)
    compliance_result_id = Column(String(64), ForeignKey("compliance_results.id"), nullable=False)
    rule_code = Column(String(64), nullable=False)
    check_name = Column(String(255), nullable=False)
    status = Column(String(32), nullable=False) # PASS, FAIL, NEEDS_REVIEW, NOT_DETECTED
    confidence = Column(Float, default=0.0)
    details = Column(Text, nullable=True)

    compliance_result = relationship("ComplianceResult", back_populates="checks")


class Violation(Base):
    __tablename__ = "violations"

    id = Column(String(64), primary_key=True)
    compliance_result_id = Column(String(64), ForeignKey("compliance_results.id"), nullable=False)
    rule_code = Column(String(64), nullable=False)
    field = Column(String(128), nullable=False)
    issue_description = Column(Text, nullable=False)
    severity = Column(String(32), nullable=False)
    evidence_bounding_box = Column(Text, nullable=True)

    compliance_result = relationship("ComplianceResult", back_populates="violations")


class ConsumerReport(Base):
    __tablename__ = "consumer_reports"

    id = Column(String(64), primary_key=True)
    report_number = Column(String(64), unique=True, nullable=False)
    user_id = Column(String(64), ForeignKey("users.id"), nullable=True)
    scan_id = Column(String(64), ForeignKey("scans.id"), nullable=False)
    product_id = Column(String(64), ForeignKey("products.id"), nullable=True)
    issue_title = Column(String(255), nullable=False)
    issue_description = Column(Text, nullable=True)
    status = Column(String(64), default="UNDER_REVIEW") # UNDER_REVIEW, VERIFIED, RESOLVED, REJECTED
    user_comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.now)

    user = relationship("User", back_populates="reports")
    inspection = relationship("Inspection", back_populates="report", uselist=False)


class Inspection(Base):
    __tablename__ = "inspections"

    id = Column(String(64), primary_key=True)
    report_id = Column(String(64), ForeignKey("consumer_reports.id"), nullable=False)
    inspector_id = Column(String(64), ForeignKey("users.id"), nullable=True)
    decision = Column(String(64), default="PENDING") # PENDING, CONFIRMED, REJECTED, NEEDS_FURTHER_VERIFICATION
    remarks = Column(Text, nullable=True)
    pdf_report_path = Column(String(512), nullable=True)
    inspected_at = Column(DateTime, default=datetime.datetime.now)

    report = relationship("ConsumerReport", back_populates="inspection")

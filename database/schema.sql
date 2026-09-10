-- ScanShield Packaged Commodity Compliance Platform
-- PostgreSQL / SQLite DDL Schema Definition

CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(64) PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    role VARCHAR(32) NOT NULL DEFAULT 'CONSUMER', -- CONSUMER, INSPECTOR, ADMIN
    badge_number VARCHAR(64),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS products (
    id VARCHAR(64) PRIMARY KEY,
    product_name VARCHAR(255) NOT NULL,
    brand_name VARCHAR(255) NOT NULL,
    category VARCHAR(128) NOT NULL,
    manufacturer VARCHAR(255) NOT NULL,
    net_quantity VARCHAR(64) NOT NULL,
    mrp VARCHAR(64) NOT NULL,
    mfg_date VARCHAR(64),
    best_before VARCHAR(64),
    consumer_care TEXT,
    fssai_license VARCHAR(64),
    country_of_origin VARCHAR(128) DEFAULT 'India',
    barcode VARCHAR(128),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS rules (
    id VARCHAR(64) PRIMARY KEY,
    rule_code VARCHAR(64) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    category VARCHAR(128) NOT NULL,
    requirement TEXT NOT NULL,
    validation_logic TEXT NOT NULL,
    severity VARCHAR(32) NOT NULL DEFAULT 'high', -- high, medium, low
    version VARCHAR(32) NOT NULL DEFAULT '1.0',
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS rule_versions (
    id VARCHAR(64) PRIMARY KEY,
    rule_id VARCHAR(64) NOT NULL REFERENCES rules(id),
    version VARCHAR(32) NOT NULL,
    requirement TEXT NOT NULL,
    effective_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS scans (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64) REFERENCES users(id),
    product_id VARCHAR(64) REFERENCES products(id),
    original_image_path VARCHAR(512) NOT NULL,
    preprocessed_image_path VARCHAR(512),
    barcode_data VARCHAR(255),
    status VARCHAR(64) NOT NULL DEFAULT 'UPLOADED', -- UPLOADED, PROCESSED, COMPLETED, FAILED
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS extracted_data (
    id VARCHAR(64) PRIMARY KEY,
    scan_id VARCHAR(64) NOT NULL REFERENCES scans(id),
    raw_ocr_text TEXT,
    confidence FLOAT DEFAULT 0.0,
    extracted_json TEXT NOT NULL, -- JSON string of extracted declarations
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS compliance_results (
    id VARCHAR(64) PRIMARY KEY,
    scan_id VARCHAR(64) NOT NULL REFERENCES scans(id),
    status VARCHAR(64) NOT NULL, -- COMPLIANT, NON_COMPLIANT, NEEDS_REVIEW
    checks_passed INT DEFAULT 0,
    issues_found INT DEFAULT 0,
    overall_confidence FLOAT DEFAULT 0.0,
    highlights_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS compliance_checks (
    id VARCHAR(64) PRIMARY KEY,
    compliance_result_id VARCHAR(64) NOT NULL REFERENCES compliance_results(id),
    rule_code VARCHAR(64) NOT NULL,
    check_name VARCHAR(255) NOT NULL,
    status VARCHAR(32) NOT NULL, -- PASS, FAIL, NEEDS_REVIEW, NOT_DETECTED
    confidence FLOAT DEFAULT 0.0,
    details TEXT
);

CREATE TABLE IF NOT EXISTS violations (
    id VARCHAR(64) PRIMARY KEY,
    compliance_result_id VARCHAR(64) NOT NULL REFERENCES compliance_results(id),
    rule_code VARCHAR(64) NOT NULL,
    field VARCHAR(128) NOT NULL,
    issue_description TEXT NOT NULL,
    severity VARCHAR(32) NOT NULL,
    evidence_bounding_box TEXT
);

CREATE TABLE IF NOT EXISTS evidence (
    id VARCHAR(64) PRIMARY KEY,
    scan_id VARCHAR(64) NOT NULL REFERENCES scans(id),
    cropped_image_path VARCHAR(512),
    bounding_box_json TEXT,
    confidence FLOAT DEFAULT 0.0,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS consumer_reports (
    id VARCHAR(64) PRIMARY KEY,
    report_number VARCHAR(64) UNIQUE NOT NULL,
    user_id VARCHAR(64) REFERENCES users(id),
    scan_id VARCHAR(64) NOT NULL REFERENCES scans(id),
    product_id VARCHAR(64) REFERENCES products(id),
    issue_title VARCHAR(255) NOT NULL,
    issue_description TEXT,
    status VARCHAR(64) NOT NULL DEFAULT 'UNDER_REVIEW', -- UNDER_REVIEW, VERIFIED, RESOLVED, REJECTED
    user_comment TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS inspections (
    id VARCHAR(64) PRIMARY KEY,
    report_id VARCHAR(64) NOT NULL REFERENCES consumer_reports(id),
    inspector_id VARCHAR(64) REFERENCES users(id),
    decision VARCHAR(64) DEFAULT 'PENDING', -- PENDING, CONFIRMED, REJECTED, NEEDS_FURTHER_VERIFICATION
    remarks TEXT,
    pdf_report_path VARCHAR(512),
    inspected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

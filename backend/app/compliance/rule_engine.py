import re
from typing import Dict, Any, List
from app.rules.repository import RuleRepository

class RuleLoader:
    def __init__(self):
        self.repo = RuleRepository()
        
    def load_rules(self) -> List[dict]:
        return self.repo.get_active_rules()

class RuleSelector:
    def select_rules_for_product(self, product_data: dict, all_rules: List[dict]) -> List[dict]:
        category = product_data.get("category", "").lower()
        selected = []
        for r in all_rules:
            # All 10 packaged commodity rules apply to consumer commodities
            selected.append(r)
        return selected

class MandatoryFieldChecker:
    def check(self, field_name: str, value: Any) -> str:
        if value is None or str(value).strip() == "" or str(value).strip().lower() in ["null", "none", "not detected"]:
            return "NOT_DETECTED"
        return "PASS"

class MRPValidator:
    def validate(self, mrp: str) -> dict:
        if not mrp or mrp == "NOT_DETECTED":
            return {"status": "NOT_DETECTED", "details": "MRP declaration not found on package label"}
        
        mrp_str = str(mrp).lower()
        has_taxes = "tax" in mrp_str or "inclusive" in mrp_str or "incl" in mrp_str
        has_currency = any(sym in str(mrp) for sym in ["₹", "Rs", "INR"])
        has_decimal = bool(re.search(r'\d+\.\d{2}', str(mrp))) or bool(re.search(r'\d+', str(mrp)))

        if has_taxes and has_currency and has_decimal:
            return {"status": "PASS", "details": "MRP declared correctly as per Rule 6(1)(e) with currency symbol and inclusive of all taxes"}
        elif has_currency and has_decimal:
            return {"status": "NEEDS_REVIEW", "details": "MRP declared with price, but tax declaration text may be incomplete"}
        else:
            return {"status": "FAIL", "details": "MRP declaration does not comply with mandatory Rule 6 format"}

class QuantityValidator:
    def validate(self, qty: str) -> dict:
        if not qty or qty == "NOT_DETECTED":
            return {"status": "NOT_DETECTED", "details": "Net quantity declaration not detected"}
        
        # Check standard units: g, kg, ml, l, L, count, N
        match = re.search(r'\b\d+(?:\.\d+)?\s*(g|kg|ml|l|L|m|cm|count|N|n)\b', str(qty))
        if match:
            return {"status": "PASS", "details": f"Net quantity ({qty}) declared in standard metric unit"}
        return {"status": "NEEDS_REVIEW", "details": f"Net quantity ({qty}) requires unit verification"}

class DateValidator:
    def validate(self, mfg_date: str, best_before: str) -> dict:
        if not mfg_date or mfg_date == "NOT_DETECTED":
            return {"status": "NOT_DETECTED", "details": "Month and year of manufacture/packing not detected"}
        return {"status": "PASS", "details": f"Manufacture date ({mfg_date}) and Best Before ({best_before or 'N/A'}) declared"}

class ManufacturerValidator:
    def validate(self, mfg: str) -> dict:
        if not mfg or mfg == "NOT_DETECTED":
            return {"status": "NOT_DETECTED", "details": "Manufacturer / Packer name and address not detected"}
        if len(str(mfg).strip()) > 10:
            return {"status": "PASS", "details": f"Manufacturer details declared: {mfg[:60]}..."}
        return {"status": "NEEDS_REVIEW", "details": "Manufacturer details detected but address appears incomplete"}

class ConsumerCareValidator:
    def validate(self, cc: str) -> dict:
        if not cc or cc == "NOT_DETECTED":
            return {"status": "NOT_DETECTED", "details": "Consumer care details (phone/email) not detected"}
        
        has_phone = bool(re.search(r'\d{8,12}', str(cc)))
        has_email = "@" in str(cc)
        if has_phone or has_email:
            return {"status": "PASS", "details": f"Consumer care contact declared ({cc})"}
        return {"status": "NEEDS_REVIEW", "details": "Consumer care details present but contact number or email format needs verification"}

class ReadabilityChecker:
    def check(self, confidence: float) -> dict:
        if confidence >= 0.85:
            return {"status": "PASS", "details": "Text information is clear and highly readable"}
        elif confidence >= 0.65:
            return {"status": "NEEDS_REVIEW", "details": "Text size appears smaller or image lighting may impair readability"}
        return {"status": "FAIL", "details": "Low readability detected on principal display panel"}

class ViolationDetector:
    def detect_violations(self, checks: List[dict]) -> List[dict]:
        violations = []
        for c in checks:
            if c["status"] == "FAIL":
                violations.append({
                    "rule_code": c["rule_code"],
                    "field": c["check_name"],
                    "issue_description": c["details"],
                    "severity": "high"
                })
            elif c["status"] == "NEEDS_REVIEW":
                violations.append({
                    "rule_code": c["rule_code"],
                    "field": c["check_name"],
                    "issue_description": c["details"],
                    "severity": "medium"
                })
        return violations

class ComplianceScorer:
    def score(self, checks: List[dict]) -> dict:
        passed = sum(1 for c in checks if c["status"] == "PASS")
        fails = sum(1 for c in checks if c["status"] == "FAIL")
        reviews = sum(1 for c in checks if c["status"] in ["NEEDS_REVIEW", "NOT_DETECTED"])

        if fails > 0:
            overall_status = "NON_COMPLIANT"
        elif reviews > 0:
            overall_status = "NEEDS_REVIEW"
        else:
            overall_status = "COMPLIANT"

        return {
            "status": overall_status,
            "checks_passed": passed,
            "issues_found": fails + reviews,
            "total_checks": len(checks)
        }

class ComplianceEngine:
    def __init__(self):
        self.loader = RuleLoader()
        self.selector = RuleSelector()
        self.mrp_validator = MRPValidator()
        self.qty_validator = QuantityValidator()
        self.date_validator = DateValidator()
        self.mfg_validator = ManufacturerValidator()
        self.cc_validator = ConsumerCareValidator()
        self.readability_checker = ReadabilityChecker()
        self.violation_detector = ViolationDetector()
        self.scorer = ComplianceScorer()

    def evaluate_compliance(self, structured_data: dict, ocr_confidence: float = 0.95) -> dict:
        all_rules = self.loader.load_rules()
        selected_rules = self.selector.select_rules_for_product(structured_data, all_rules)
        
        checks = []

        # 1. Manufacturer check (LM-NAME-001)
        mfg_res = self.mfg_validator.validate(structured_data.get("manufacturer"))
        checks.append({
            "rule_code": "LM-NAME-001",
            "check_name": "Manufacturer / Packer / Importer",
            "status": mfg_res["status"],
            "confidence": structured_data.get("confidences", {}).get("manufacturer", 0.95),
            "details": mfg_res["details"]
        })

        # 2. Generic name check (LM-GENERIC-002)
        prod_name = structured_data.get("product_name")
        generic_status = "PASS" if prod_name else "NOT_DETECTED"
        checks.append({
            "rule_code": "LM-GENERIC-002",
            "check_name": "Generic Name of Commodity",
            "status": generic_status,
            "confidence": 0.95,
            "details": f"Product identified as '{prod_name}'" if prod_name else "Generic product name missing"
        })

        # 3. Net quantity check (LM-QTY-003)
        qty_res = self.qty_validator.validate(structured_data.get("net_quantity"))
        checks.append({
            "rule_code": "LM-QTY-003",
            "check_name": "Net Quantity",
            "status": qty_res["status"],
            "confidence": structured_data.get("confidences", {}).get("net_quantity", 0.95),
            "details": qty_res["details"]
        })

        # 4. MRP check (LM-MRP-004)
        mrp_res = self.mrp_validator.validate(structured_data.get("mrp"))
        checks.append({
            "rule_code": "LM-MRP-004",
            "check_name": "MRP (incl. of all taxes)",
            "status": mrp_res["status"],
            "confidence": structured_data.get("confidences", {}).get("mrp", 0.95),
            "details": mrp_res["details"]
        })

        # 5. Manufacture date check (LM-DATE-005)
        date_res = self.date_validator.validate(structured_data.get("manufacture_date"), structured_data.get("best_before"))
        checks.append({
            "rule_code": "LM-DATE-005",
            "check_name": "Manufacture Date",
            "status": date_res["status"],
            "confidence": structured_data.get("confidences", {}).get("manufacture_date", 0.95),
            "details": date_res["details"]
        })

        # 6. Best Before / Expiry Date (LM-EXP-008)
        exp_val = structured_data.get("best_before")
        exp_status = "PASS" if exp_val and exp_val != "NOT_DETECTED" else "NEEDS_REVIEW"
        checks.append({
            "rule_code": "LM-EXP-008",
            "check_name": "Best Before / Use By",
            "status": exp_status,
            "confidence": structured_data.get("confidences", {}).get("best_before", 0.95),
            "details": f"Expiry date declared as '{exp_val}'" if exp_status == "PASS" else "Best Before date needs label verification"
        })

        # 7. Consumer Care details (LM-CC-006)
        cc_res = self.cc_validator.validate(structured_data.get("consumer_care"))
        checks.append({
            "rule_code": "LM-CC-006",
            "check_name": "Consumer Care Details",
            "status": cc_res["status"],
            "confidence": structured_data.get("confidences", {}).get("consumer_care", 0.95),
            "details": cc_res["details"]
        })

        # 8. Readability check (LM-FONT-010)
        read_res = self.readability_checker.check(ocr_confidence)
        checks.append({
            "rule_code": "LM-FONT-010",
            "check_name": "Text Readability & Font Size",
            "status": read_res["status"],
            "confidence": ocr_confidence,
            "details": read_res["details"]
        })

        scoring = self.scorer.score(checks)
        violations = self.violation_detector.detect_violations(checks)

        highlights = []
        if scoring["status"] == "COMPLIANT":
            highlights = [
                "All mandatory declarations found",
                "Label format is as per Legal Metrology rules",
                "Text information is clear and readable",
                "No critical issues detected"
            ]
        elif scoring["status"] == "NEEDS_REVIEW":
            highlights = [
                f"{scoring['issues_found']} declaration(s) need inspector review",
                "Some text size or field formats need label verification",
                "Product overall compliant with basic declarations"
            ]
        else:
            highlights = [
                "Critical Legal Metrology violation detected",
                "Mandatory declaration missing or non-compliant",
                "Consumer reporting recommended"
            ]

        return {
            "status": scoring["status"],
            "checks_passed": scoring["checks_passed"],
            "issues_found": scoring["issues_found"],
            "overall_confidence": round(ocr_confidence, 2),
            "highlights": highlights,
            "checks": checks,
            "violations": violations
        }

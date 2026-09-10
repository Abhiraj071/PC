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
        selected = []
        for r in all_rules:
            selected.append(r)
        return selected

class MandatoryFieldChecker:
    def check(self, field_name: str, value: Any) -> str:
        if value is None or str(value).strip() == "" or str(value).strip().lower() in ["null", "none", "not detected"]:
            return "FAIL"
        return "PASS"

class MRPValidator:
    def validate(self, mrp: str) -> dict:
        if not mrp or str(mrp).strip() == "" or str(mrp).strip().lower() in ["null", "none", "not detected"]:
            return {
                "status": "FAIL",
                "details": "Mandatory MRP declaration missing on package (Violation of Rule 6(1)(e))"
            }
        
        mrp_str = str(mrp).lower()
        has_taxes = "tax" in mrp_str or "inclusive" in mrp_str or "incl" in mrp_str
        has_currency = any(sym in str(mrp) for sym in ["₹", "Rs", "INR", "rs"])
        has_number = bool(re.search(r'\d+(?:\.\d{1,2})?', str(mrp)))

        if has_currency and has_number and has_taxes:
            return {
                "status": "PASS",
                "details": f"MRP declared correctly as per Rule 6(1)(e) with currency symbol and inclusive of all taxes ({mrp})"
            }
        elif has_currency and has_number:
            return {
                "status": "NEEDS_REVIEW",
                "details": f"MRP price detected ({mrp}), but 'inclusive of all taxes' statement is missing or unclear (Rule 6(1)(e))"
            }
        else:
            return {
                "status": "FAIL",
                "details": f"MRP declaration '{mrp}' does not comply with mandatory Rule 6(1)(e) format"
            }

class QuantityValidator:
    def validate(self, qty: str) -> dict:
        if not qty or str(qty).strip() == "" or str(qty).strip().lower() in ["null", "none", "not detected"]:
            return {
                "status": "FAIL",
                "details": "Mandatory Net Quantity declaration missing (Violation of Rule 6(1)(c))"
            }
        
        # Check standard units: g, kg, ml, l, L, count, N, units, pieces, pens
        match = re.search(r'\b\d+(?:\.\d+)?\s*(g|kg|gm|gms|ml|mL|l|L|ltr|count|N|n|pieces?|pcs|units?|u|gel\s*pens?|pens?|pencils?|items?)\b', str(qty), re.IGNORECASE)
        if match:
            return {
                "status": "PASS",
                "details": f"Net quantity ({qty}) declared in standard metric/number unit as per Rule 6(1)(c)"
            }
        return {
            "status": "NEEDS_REVIEW",
            "details": f"Net quantity ({qty}) requires unit verification under Legal Metrology standards"
        }

class DateValidator:
    def validate(self, mfg_date: str, best_before: str) -> dict:
        if not mfg_date or str(mfg_date).strip() == "" or str(mfg_date).strip().lower() in ["null", "none", "not detected"]:
            return {
                "status": "FAIL",
                "details": "Mandatory month and year of manufacture/packing not detected (Violation of Rule 6(1)(d))"
            }
        
        date_clean = mfg_date.replace('\n', ' ').strip()
        bb_clean = (best_before or '').replace('\n', ' ').strip()
        bb_part = f" and Best Before ({bb_clean})" if bb_clean else ""
        return {
            "status": "PASS",
            "details": f"Manufacture date ({date_clean}){bb_part} declared as per Rule 6(1)(d)"
        }

class ManufacturerValidator:
    def validate(self, mfg: str) -> dict:
        if not mfg or str(mfg).strip() == "" or str(mfg).strip().lower() in ["null", "none", "not detected"]:
            return {
                "status": "FAIL",
                "details": "Mandatory Manufacturer / Packer name and address missing (Violation of Rule 6(1)(a))"
            }
        mfg_clean = mfg.replace('\n', ' ').strip()
        if len(mfg_clean) > 12:
            return {
                "status": "PASS",
                "details": f"Manufacturer details declared: {mfg_clean[:60]}..."
            }
        return {
            "status": "NEEDS_REVIEW",
            "details": "Manufacturer details detected but address appears incomplete under Rule 6(1)(a)"
        }

class ConsumerCareValidator:
    def validate(self, cc: str) -> dict:
        if not cc or str(cc).strip() == "" or str(cc).strip().lower() in ["null", "none", "not detected"]:
            return {
                "status": "FAIL",
                "details": "Mandatory Consumer Care contact details not detected (Violation of Rule 6(1)(f))"
            }
        
        digits_only = re.sub(r'\D', '', str(cc))
        has_phone = 8 <= len(digits_only) <= 12 or bool(re.search(r'\b(?:1800|1860)[\s-]?\d{2,4}[\s-]?\d{3,5}\b', str(cc)))
        has_email = "@" in str(cc)
        if has_phone or has_email:
            cc_clean = cc.replace('\n', ' ').strip()
            return {
                "status": "PASS",
                "details": f"Consumer care contact declared ({cc_clean})"
            }
        return {
            "status": "NEEDS_REVIEW",
            "details": "Consumer care details present but contact number or email format needs verification"
        }

class ReadabilityChecker:
    def check(self, confidence: float) -> dict:
        if confidence >= 0.70:
            return {
                "status": "PASS",
                "details": "Text declarations are clear and highly readable"
            }
        elif confidence >= 0.40:
            return {
                "status": "NEEDS_REVIEW",
                "details": "Moderate text clarity; verify principal display panel font size against Rule 7"
            }
        return {
            "status": "FAIL",
            "details": "Low text readability on label; declarations may violate minimum font size rules"
        }

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
        reviews = sum(1 for c in checks if c["status"] == "NEEDS_REVIEW")

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
        checks = []

        # 1. Manufacturer check (LM-NAME-001 / Rule 6(1)(a))
        mfg_val = structured_data.get("manufacturer")
        mfg_res = self.mfg_validator.validate(mfg_val)
        checks.append({
            "rule_code": "LM-NAME-001",
            "check_name": "Manufacturer / Packer / Importer",
            "status": mfg_res["status"],
            "confidence": structured_data.get("confidences", {}).get("manufacturer", 0.95 if mfg_val else 0.0),
            "details": mfg_res["details"]
        })

        # 2. Generic commodity name check (LM-GENERIC-002 / Rule 6(1)(b))
        prod_name = (structured_data.get("product_name") or "").strip()
        if prod_name and len(prod_name) > 2:
            generic_status = "PASS"
            generic_details = f"Product identified as '{prod_name}'"
            generic_conf = 0.95
        else:
            generic_status = "FAIL"
            generic_details = "Mandatory generic name of commodity missing (Violation of Rule 6(1)(b))"
            generic_conf = 0.0
        checks.append({
            "rule_code": "LM-GENERIC-002",
            "check_name": "Generic Name of Commodity",
            "status": generic_status,
            "confidence": generic_conf,
            "details": generic_details
        })

        # 3. Net quantity check (LM-QTY-003 / Rule 6(1)(c))
        qty_val = structured_data.get("net_quantity")
        qty_res = self.qty_validator.validate(qty_val)
        checks.append({
            "rule_code": "LM-QTY-003",
            "check_name": "Net Quantity",
            "status": qty_res["status"],
            "confidence": structured_data.get("confidences", {}).get("net_quantity", 0.95 if qty_val else 0.0),
            "details": qty_res["details"]
        })

        # 4. MRP check (LM-MRP-004 / Rule 6(1)(e))
        mrp_val = structured_data.get("mrp")
        mrp_res = self.mrp_validator.validate(mrp_val)
        checks.append({
            "rule_code": "LM-MRP-004",
            "check_name": "MRP (incl. of all taxes)",
            "status": mrp_res["status"],
            "confidence": structured_data.get("confidences", {}).get("mrp", 0.95 if mrp_val else 0.0),
            "details": mrp_res["details"]
        })

        # 5. Manufacture date check (LM-DATE-005 / Rule 6(1)(d))
        mfg_date_val = structured_data.get("manufacture_date")
        exp_date_val = structured_data.get("best_before")
        date_res = self.date_validator.validate(mfg_date_val, exp_date_val)
        checks.append({
            "rule_code": "LM-DATE-005",
            "check_name": "Manufacture Date",
            "status": date_res["status"],
            "confidence": structured_data.get("confidences", {}).get("manufacture_date", 0.95 if mfg_date_val else 0.0),
            "details": date_res["details"]
        })

        # 6. Best Before / Expiry Date (LM-EXP-008)
        exp_val = (exp_date_val or "").strip()
        category = structured_data.get("category", "")
        if exp_val and len(exp_val) > 2:
            exp_status = "PASS"
            exp_details = f"Expiry / Best Before declared as '{exp_val.replace(chr(10), ' ')}'"
            exp_conf = structured_data.get("confidences", {}).get("best_before", 0.95)
        elif category in ["Stationery & Office Supplies", "Electronics & Appliances", "Hardware & Tools", "Garments & Textiles"]:
            exp_status = "PASS"
            exp_details = "Not mandatory for non-perishable / stationery commodities (Exempt under Rule 6(1)(d))"
            exp_conf = 0.95
        else:
            exp_status = "NEEDS_REVIEW"
            exp_details = "Best Before / Expiry date not detected on label"
            exp_conf = 0.0
        checks.append({
            "rule_code": "LM-EXP-008",
            "check_name": "Best Before / Use By",
            "status": exp_status,
            "confidence": exp_conf,
            "details": exp_details
        })

        # 7. Consumer Care details (LM-CC-006 / Rule 6(1)(f))
        cc_val = structured_data.get("consumer_care")
        cc_res = self.cc_validator.validate(cc_val)
        checks.append({
            "rule_code": "LM-CC-006",
            "check_name": "Consumer Care Details",
            "status": cc_res["status"],
            "confidence": structured_data.get("confidences", {}).get("consumer_care", 0.95 if cc_val else 0.0),
            "details": cc_res["details"]
        })

        # 8. Readability check (LM-FONT-010 / Rule 7)
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
                "All mandatory Rule 6 declarations found on package label",
                "Net quantity, MRP (incl. of taxes), and manufacturer verified",
                "Text information is clear and complies with Rule 7 readability",
                "No Legal Metrology violations detected"
            ]
        elif scoring["status"] == "NEEDS_REVIEW":
            highlights = [
                f"{scoring['issues_found']} declaration(s) require inspector or consumer verification",
                "Some mandatory fields or unit formats need label confirmation",
                "Product overall partially compliant with basic declarations"
            ]
        else:
            highlights = [
                f"{scoring['issues_found']} Legal Metrology violation(s) detected!",
                "Mandatory declaration(s) missing or non-compliant under Rule 6",
                "Consumer concern report or official regulatory inspection recommended"
            ]

        # Calculate overall confidence
        valid_confs = [c["confidence"] for c in checks if c["confidence"] > 0]
        overall_conf = round(sum(valid_confs) / len(valid_confs), 2) if valid_confs else round(ocr_confidence, 2)

        return {
            "status": scoring["status"],
            "checks_passed": scoring["checks_passed"],
            "issues_found": scoring["issues_found"],
            "total_checks": scoring["total_checks"],
            "overall_confidence": overall_conf,
            "highlights": highlights,
            "checks": checks,
            "violations": violations
        }

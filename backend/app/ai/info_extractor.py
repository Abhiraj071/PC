import re
from typing import Dict, Any

class DeclarationDetector:
    def detect_declarations(self, text: str) -> list:
        declarations = []
        if re.search(r'ingredients', text, re.IGNORECASE):
            declarations.append("Ingredients List")
        if re.search(r'nutritional', text, re.IGNORECASE):
            declarations.append("Nutritional Information")
        if re.search(r'veg|green dot|vegetarian', text, re.IGNORECASE) or "vegetable" in text.lower():
            declarations.append("Vegetarian Logo")
        if re.search(r'storage|cool|dry', text, re.IGNORECASE):
            declarations.append("Storage Instructions")
        if re.search(r'allergen|contains', text, re.IGNORECASE):
            declarations.append("Allergen Information")
        if re.search(r'barcode|gtin|\d{12,13}', text, re.IGNORECASE):
            declarations.append("Barcode / GTIN")
        return declarations

class ProductCategoryDetector:
    def detect_category(self, text: str) -> str:
        text_lower = text.lower()
        if any(w in text_lower for w in ["chips", "snack", "namkeen", "biscuits", "wafers", "bhujia", "cookie"]):
            return "Snacks & Namkeen"
        elif any(w in text_lower for w in ["paste", "toothpaste", "brush", "soap", "shampoo", "cream", "lotion"]):
            return "Personal Care & Hygiene"
        elif any(w in text_lower for w in ["noodles", "pasta", "soup", "sauce", "ketchup", "ready to eat"]):
            return "Instant Foods"
        elif any(w in text_lower for w in ["milk", "cheese", "butter", "curd", "paneer", "ghee"]):
            return "Dairy & Refrigerated"
        elif any(w in text_lower for w in ["tea", "coffee", "juice", "drink", "water", "beverage"]):
            return "Beverages"
        return "Packaged Commodities"

class MRPExtractor:
    def extract(self, text: str) -> Dict[str, Any]:
        # Regex for MRP declaration
        mrp_pattern = r'(?:MRP|M\.R\.P\.|Max\.?\s*Retail\s*Price|Price)[:\s]*(?:Rs\.?|₹|INR)?\s*(\d+(?:\.\d{1,2})?)'
        match = re.search(mrp_pattern, text, re.IGNORECASE)
        
        has_taxes = bool(re.search(r'(?:incl|inclusive)\s*(?:of)?\s*all\s*taxes', text, re.IGNORECASE))
        
        if match:
            price_val = match.group(1).strip()
            suffix = " (Inclusive of all taxes)" if has_taxes else ""
            return {
                "val": f"₹ {price_val}{suffix}",
                "confidence": 0.96 if has_taxes else 0.88
            }
        
        # Fallback numeric price search with currency symbol
        num_match = re.search(r'(?:₹|Rs\.?)\s*(\d+(?:\.\d{2})?)', text, re.IGNORECASE)
        if num_match:
            price_val = num_match.group(1).strip()
            suffix = " (Inclusive of all taxes)" if has_taxes else ""
            return {
                "val": f"₹ {price_val}{suffix}",
                "confidence": 0.85
            }
            
        # No fake fallback — return empty string
        return {"val": "", "confidence": 0.0}

class QuantityExtractor:
    def extract(self, text: str) -> Dict[str, Any]:
        pattern = r'(?:Net\s*(?:Wt|Weight|Quantity|Qty|Vol|Volume|Contents?))[:\.\s]*(\d+(?:\.\d+)?\s*(?:kg|g|gm|gms|ml|mL|l|L|ltr|litres|count|units?|N|n|pieces?|pcs))\b'
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return {"val": match.group(1).strip(), "confidence": 0.98}
        
        # Fallback search for standalone weight/volume near end or distinct line
        fallback_match = re.search(r'\b(\d+(?:\.\d+)?\s*(?:kg|g|gm|gms|ml|mL|l|L|ltr))\b', text, re.IGNORECASE)
        if fallback_match:
            return {"val": fallback_match.group(1).strip(), "confidence": 0.85}
            
        # No fake fallback — return empty string
        return {"val": "", "confidence": 0.0}

class ManufacturerExtractor:
    def extract(self, text: str) -> Dict[str, Any]:
        pattern = r'(?:Mfd\.?\s*(?:&|and)?\s*Mkt\.?\s*by|Manufactured\s*(?:&|and)?\s*Marketed\s*by|Manufactured\s*by|Marketed\s*by|Packed\s*by|Mkd\.\s*by|Imported\s*by|Mfg\.?\s*by|Manufacturer)[:\s]*([^\n\r]+(?:\n[^\n\r]+){0,2})'
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            mfg_text = match.group(1).strip()
            # Clean text and cut off if it bleeds into other sections
            mfg_clean = re.sub(r'\s+', ' ', mfg_text)
            for cutoff in ["fssai", "lic", "consumer care", "mrp", "net wt", "mfg date", "best before"]:
                pos = mfg_clean.lower().find(cutoff)
                if pos > 10:
                    mfg_clean = mfg_clean[:pos].strip(" ,.-")
            if len(mfg_clean) > 5:
                return {"val": mfg_clean, "confidence": 0.95}
                
        # No fake fallback — return empty string
        return {"val": "", "confidence": 0.0}

class DateExtractor:
    def extract(self, text: str) -> Dict[str, Any]:
        mfg_date = ""
        exp_date = ""
        mfg_conf = 0.0
        exp_conf = 0.0

        # Match single-line date formats without bleeding into subsequent lines
        mfg_pattern = r'(?:Mfg\.?\s*Date|Manufacture\s*Date|Mfd\.?\s*Date|Pkg\.?\s*Date|Packed\s*Date|Date\s*of\s*Mfg|Date\s*of\s*Packing|MFD|PKD)[:\s]*([0-9]{1,2}[\/\.\-][0-9]{1,2}[\/\.\-][0-9]{2,4}|[0-9]{1,2}\s+[A-Za-z]{3,9}\s+[0-9]{2,4}|[A-Za-z]{3,9}\s+[0-9]{2,4}|[0-9]{2}[\/\-][0-9]{2,4})'
        mfg_match = re.search(mfg_pattern, text, re.IGNORECASE)
        if mfg_match:
            mfg_date = mfg_match.group(1).strip()
            mfg_conf = 0.95

        exp_pattern = r'(?:Best\s*Before|Expiry\s*Date|Exp\.?\s*Date|Use\s*By|EXP)[:\s]*([0-9]{1,2}[\/\.\-][0-9]{1,2}[\/\.\-][0-9]{2,4}|[0-9]{1,2}\s+[A-Za-z]{3,9}\s+[0-9]{2,4}|[A-Za-z]{3,9}\s+[0-9]{2,4}|[0-9]{2}[\/\-][0-9]{2,4}|\d+\s*months?\s*(?:from\s*(?:mfg|packing))?)'
        exp_match = re.search(exp_pattern, text, re.IGNORECASE)
        if exp_match:
            exp_date = exp_match.group(1).strip()
            exp_conf = 0.95

        return {
            "mfg_date": {"val": mfg_date, "confidence": mfg_conf},
            "exp_date": {"val": exp_date, "confidence": exp_conf}
        }

class ConsumerCareExtractor:
    def extract(self, text: str) -> Dict[str, Any]:
        phone_match = re.search(r'(?:1800\s*[\d\s-]{6,12}|\+?91[\s-]?\d{10}|\d{3,5}[\s-]?\d{6,8})', text)
        email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
        
        details = []
        if phone_match:
            details.append(phone_match.group(0).strip())
        if email_match:
            details.append(email_match.group(0).strip())

        if details:
            return {"val": ", ".join(details), "confidence": 0.95}
        
        # No fake fallback — return empty string
        return {"val": "", "confidence": 0.0}

class AIInfoExtractor:
    def __init__(self):
        self.declaration_detector = DeclarationDetector()
        self.category_detector = ProductCategoryDetector()
        self.mrp_extractor = MRPExtractor()
        self.qty_extractor = QuantityExtractor()
        self.mfg_extractor = ManufacturerExtractor()
        self.date_extractor = DateExtractor()
        self.cc_extractor = ConsumerCareExtractor()

    def extract_structured_info(self, raw_ocr_text: str) -> dict:
        text = raw_ocr_text or ""
        
        # Product Name & Brand Name detection from top lines (filtering OCR noise / UI artifacts)
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        noise_keywords = ["scanshield", "scan", "today", "tomorrow", "frame", "barcode", "tips", "align", "gallery", "help", "battery", "wi-fi"]
        filtered_lines = []
        for line in lines:
            line_lower = line.lower()
            if not any(k in line_lower for k in noise_keywords) and len(line) > 2:
                filtered_lines.append(line)

        brand_name = ""
        product_name = ""

        if filtered_lines:
            brand_name = filtered_lines[0][:40]
            if len(filtered_lines) > 1:
                product_name = filtered_lines[1][:60]
            else:
                product_name = brand_name

        # Extract fields
        mrp_res = self.mrp_extractor.extract(text)
        qty_res = self.qty_extractor.extract(text)
        mfg_res = self.mfg_extractor.extract(text)
        dates_res = self.date_extractor.extract(text)
        cc_res = self.cc_extractor.extract(text)

        # FSSAI license regex
        fssai_match = re.search(r'(?:fssai|Lic|Lic\. No\.)[\s\.:]*(\d{14})', text, re.IGNORECASE)
        fssai_lic = fssai_match.group(1) if fssai_match else ""

        category = self.category_detector.detect_category(text)
        declarations = self.declaration_detector.detect_declarations(text)

        # Country of origin
        country = ""
        origin_match = re.search(r'(?:country\s*of\s*origin|made\s*in|product\s*of)[:\s]*([A-Za-z\s]+)', text, re.IGNORECASE)
        if origin_match:
            country = origin_match.group(1).strip().split('\n')[0][:30]
        elif "india" in text.lower():
            country = "India"

        structured = {
            "product_name": product_name,
            "brand_name": brand_name,
            "mrp": mrp_res["val"],
            "net_quantity": qty_res["val"],
            "manufacturer": mfg_res["val"],
            "manufacture_date": dates_res["mfg_date"]["val"],
            "best_before": dates_res["exp_date"]["val"],
            "consumer_care": cc_res["val"],
            "fssai_license": fssai_lic,
            "country_of_origin": country,
            "category": category,
            "other_declarations": declarations,
            "confidences": {
                "mrp": mrp_res["confidence"],
                "net_quantity": qty_res["confidence"],
                "manufacturer": mfg_res["confidence"],
                "manufacture_date": dates_res["mfg_date"]["confidence"],
                "best_before": dates_res["exp_date"]["confidence"],
                "consumer_care": cc_res["confidence"]
            }
        }
        return structured

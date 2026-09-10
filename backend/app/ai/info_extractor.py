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
        if any(w in text_lower for w in ["chips", "snack", "namkeen", "biscuits", "wafers", "bhujia", "cookie", "rusk"]):
            return "Snacks & Namkeen"
        elif any(w in text_lower for w in ["paste", "toothpaste", "brush", "soap", "shampoo", "cream", "lotion", "handwash"]):
            return "Personal Care & Hygiene"
        elif any(w in text_lower for w in ["noodles", "pasta", "soup", "sauce", "ketchup", "ready to eat", "macaroni"]):
            return "Instant Foods"
        elif any(w in text_lower for w in ["milk", "cheese", "butter", "curd", "paneer", "ghee", "dahi"]):
            return "Dairy & Refrigerated"
        elif any(w in text_lower for w in ["tea", "coffee", "juice", "drink", "water", "beverage", "syrup"]):
            return "Beverages"
        elif any(w in text_lower for w in ["atta", "flour", "rice", "dal", "sugar", "salt", "oil", "spice", "masala"]):
            return "Staples & Groceries"
        return "Packaged Commodities"

KNOWN_COMMODITIES = [
    r"Classic Potato Chips", r"Potato Chips", r"Potato Wafers", r"Banana Chips", r"Chips", r"Crisps",
    r"Butter Cookies", r"Cookies", r"Cream Biscuits", r"Marie Biscuits", r"Glucose Biscuits", r"Biscuits", r"Rusk",
    r"Aloo Bhujia", r"Bhujia", r"Sev", r"Khatta Meetha", r"Moong Dal", r"Namkeen", r"Mixture",
    r"Instant Noodles", r"Noodles", r"Pasta", r"Macaroni", r"Vermicelli",
    r"Toothpaste", r"Toothpowder", r"Bathing Bar", r"Bathing Soap", r"Toilet Soap", r"Soap", r"Shampoo", r"Hair Oil", r"Handwash",
    r"Toned Milk", r"Cow Milk", r"Milk", r"Curd", r"Dahi", r"Butter", r"Cheese", r"Paneer", r"Pure Ghee", r"Ghee",
    r"Green Tea", r"Tea", r"Instant Coffee", r"Coffee", r"Drinking Water", r"Fruit Juice", r"Juice",
    r"Chakki Fresh Atta", r"Wheat Flour", r"Atta", r"Maida", r"Besan", r"Suji", r"Rava",
    r"Basmati Rice", r"Rice", r"Poha", r"Toor Dal", r"Moong Dal", r"Chana Dal",
    r"Refined Sunflower Oil", r"Mustard Oil", r"Soyabean Oil", r"Edible Vegetable Oil",
    r"Tomato Ketchup", r"Tomato Sauce", r"Mixed Fruit Jam", r"Mango Pickle", r"Pickle",
    r"Iodised Salt", r"Salt", r"Sugar",
    r"Washing Powder", r"Detergent Powder", r"Liquid Detergent", r"Dishwash Bar",
    r"Milk Chocolate", r"Dark Chocolate", r"Chocolate", r"Corn Flakes", r"Oats"
]

KNOWN_BRANDS = [
    "Lay's", "Lays", "Kurkure", "Doritos", "Pringles", "Bingo", "Balaji",
    "Britannia", "Parle", "Sunfeast", "Oreo", "Good Day", "Marie Gold", "Monaco", "Hide & Seek",
    "Haldiram's", "Haldiram", "Bikaji", "Bikanervala", "Dabur", "Bikano",
    "Maggi", "Nestle", "Knorr", "Yippee", "Top Ramen", "Ching's",
    "Colgate", "Sensodyne", "Close Up", "Pepsodent", "Dettol", "Lifebuoy", "Lux", "Dove", "Pears",
    "Amul", "Mother Dairy", "Nandini", "Kwality Wall's",
    "Tata", "Tata Tea", "Tata Salt", "Tata Sampann", "Aashirvaad", "Fortune", "Saffola", "Dhara", "Gemini",
    "Everest", "MDH", "Catch", "Badshah", "Goldmee",
    "Cadbury", "Dairy Milk", "KitKat", "5 Star", "Perk", "Snickers",
    "Kissan", "Heinz", "Maggi Ketchup",
    "Thums Up", "Coca-Cola", "Pepsi", "Sprite", "Limca", "Fanta", "Frooti", "Maaza", "Real", "Tropicana", "Red Bull",
    "Surf Excel", "Ariel", "Tide", "Rin", "Vim", "Pril", "Lizol", "Harpic"
]

class MRPExtractor:
    def extract(self, text: str) -> Dict[str, Any]:
        # Regex for MRP declaration
        mrp_pattern = r'(?:MRP|M\.R\.P\.|Max\.?\s*Retail\s*Price|Retail\s*Price)[:\s]*(?:Rs\.?|₹|INR)?\s*(\d+(?:\.\d{1,2})?)\s*(?:\/-)?'
        match = re.search(mrp_pattern, text, re.IGNORECASE)
        
        has_taxes = bool(re.search(r'(?:incl|inclusive)\s*(?:\.|\b)?(?:of)?\s*all\s*taxes', text, re.IGNORECASE))
        
        if match:
            price_val = match.group(1).strip()
            suffix = " (Inclusive of all taxes)" if has_taxes else ""
            return {
                "val": f"₹ {price_val}{suffix}",
                "confidence": 0.96 if has_taxes else 0.90
            }
        
        # Fallback numeric price search with currency symbol, avoiding years 2020-2030
        curr_match = re.search(r'(?:₹|Rs\.?\s*)\s*(\d{1,4}(?:\.\d{1,2})?)\s*(?:\/-)?(?:\s*(?:incl|inclusive)[^\n]*)?', text, re.IGNORECASE)
        if curr_match:
            price_val = curr_match.group(1).strip()
            if price_val not in ["2023", "2024", "2025", "2026", "2027"]:
                suffix = " (Inclusive of all taxes)" if has_taxes else ""
                return {
                    "val": f"₹ {price_val}{suffix}",
                    "confidence": 0.88
                }
            
        return {"val": "", "confidence": 0.0}

class QuantityExtractor:
    def extract(self, text: str) -> Dict[str, Any]:
        # Filter out nutritional table lines to avoid picking up Protein 6.8g or Carbs 53.8g
        lines = text.splitlines()
        non_nutrition_lines = []
        nutrition_keywords = ["protein", "carbohydrate", "sugar", "fat", "energy", "kcal", "sodium", "cholesterol", "per 100g", "per serve", "approx"]
        for line in lines:
            line_l = line.lower()
            if not any(k in line_l for k in nutrition_keywords):
                non_nutrition_lines.append(line)
        clean_text = "\n".join(non_nutrition_lines)

        # Primary: Look for explicit Net Weight / Quantity keywords
        pattern = r'(?:Net\s*(?:Wt|Weight|Quantity|Qty|Vol|Volume|Contents?)|Weight|Volume|Quantity)[:\.\s]*(\d+(?:\.\d+)?\s*(?:kg|g|gm|gms|ml|mL|l|L|ltr|litres|count|units?|N|n|pieces?|pcs))\b'
        match = re.search(pattern, clean_text, re.IGNORECASE)
        if match:
            raw_qty = match.group(1).strip()
            # Standardize spacing between number and unit
            clean_qty = re.sub(r'(\d+)\s*([A-Za-z]+)', r'\1 \2', raw_qty)
            return {"val": clean_qty, "confidence": 0.98}
        
        # Secondary: Standalone metric quantities on non-nutrition lines
        for line in non_nutrition_lines:
            fallback_match = re.search(r'\b(\d+(?:\.\d+)?\s*(?:kg|g|gm|gms|ml|mL|l|L|ltr|N))\b', line, re.IGNORECASE)
            if fallback_match:
                raw_qty = fallback_match.group(1).strip()
                clean_qty = re.sub(r'(\d+)\s*([A-Za-z]+)', r'\1 \2', raw_qty)
                return {"val": clean_qty, "confidence": 0.85}
            
        return {"val": "", "confidence": 0.0}

class ManufacturerExtractor:
    def extract(self, text: str) -> Dict[str, Any]:
        pattern = r'(?:Mfd\.?\s*(?:&|and)?\s*Mkt\.?\s*by|Manufactured\s*(?:&|and)?\s*Marketed\s*by|Manufactured\s*by|Marketed\s*by|Packed\s*by|Mkd\.\s*by|Imported\s*by|Mfg\.?\s*by|Manufacturer)[:\s]*([^\n\r]+(?:\n[^\n\r]+){0,2})'
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            mfg_text = match.group(1).strip()
            # Clean text and cut off if it bleeds into other sections
            mfg_clean = re.sub(r'\s+', ' ', mfg_text)
            for cutoff in ["fssai", "lic", "jssal", "consumer care", "mrp", "net wt", "mfg date", "best before", "feedback"]:
                pos = mfg_clean.lower().find(cutoff)
                if pos > 10:
                    mfg_clean = mfg_clean[:pos].strip(" ,.-|")
            if len(mfg_clean) > 8:
                return {"val": mfg_clean, "confidence": 0.95}
                
        return {"val": "", "confidence": 0.0}

class DateExtractor:
    def extract(self, text: str) -> Dict[str, Any]:
        mfg_date = ""
        exp_date = ""
        mfg_conf = 0.0
        exp_conf = 0.0

        # Match single-line date formats without bleeding into subsequent lines
        mfg_pattern = r'(?:Mfg\.?\s*Date|Manufacture\s*Date|Mfd\.?\s*Date|Pkg\.?\s*Date|Packed\s*Date|Date\s*of\s*Mfg|Date\s*of\s*Packing|Date\s*of\s*Pkg|MFD|PKD)[:\s]*([0-9]{1,2}[\/\.\-][0-9]{1,2}[\/\.\-][0-9]{2,4}|[0-9]{1,2}\s+[A-Za-z]{3,9}\s+[0-9]{2,4}|[A-Za-z]{3,9}\s+[0-9]{2,4}|[0-9]{1,2}[\/\.\-][0-9]{2,4})'
        mfg_match = re.search(mfg_pattern, text, re.IGNORECASE)
        if mfg_match:
            raw_mfg = mfg_match.group(1).strip()
            mfg_date = re.sub(r'[\r\n].*', '', raw_mfg).strip()
            mfg_conf = 0.95

        # Expiry or Best Before date (including "Best before X months from packaging/mfg")
        exp_pattern = r'(?:Best\s*Before|Expiry\s*Date|Exp\.?\s*Date|Use\s*By|EXP)[:\s]*([0-9]{1,2}[\/\.\-][0-9]{1,2}[\/\.\-][0-9]{2,4}|[0-9]{1,2}\s+[A-Za-z]{3,9}\s+[0-9]{2,4}|[A-Za-z]{3,9}\s+[0-9]{2,4}|[0-9]{1,2}[\/\.\-][0-9]{2,4}|\d+\s*months?\s*(?:from\s*(?:mfg|packing|packaging|manufacture)[^\n\r]*)?)'
        exp_match = re.search(exp_pattern, text, re.IGNORECASE)
        if exp_match:
            raw_exp = exp_match.group(1).strip()
            exp_date = re.sub(r'[\r\n].*', '', raw_exp).strip()
            exp_conf = 0.95

        return {
            "mfg_date": {"val": mfg_date, "confidence": mfg_conf},
            "exp_date": {"val": exp_date, "confidence": exp_conf}
        }

class ConsumerCareExtractor:
    def extract(self, text: str) -> Dict[str, Any]:
        details = []

        # 1. Toll Free / Helpline: 1800 or 1860 numbers
        tf_match = re.search(r'\b(1800[\s-]?\d{2,4}[\s-]?\d{3,5}|1860[\s-]?\d{2,4}[\s-]?\d{3,5})\b', text)
        if tf_match:
            num = re.sub(r'[\s-]+', ' ', tf_match.group(0).strip())
            if num not in details:
                details.append(num)

        # 2. Number explicitly following Consumer Care / Customer Care / Helpline / Toll Free / Feedback
        cc_match = re.search(r'(?:Consumer\s*Care|Customer\s*Care|Helpline|Toll\s*Free|Feedback|Queries|Reach\s*us)[:\s]*(?:at)?[:\s]*([+\d\s-]{8,15})', text, re.IGNORECASE)
        if cc_match:
            num_clean = re.sub(r'[\s-]+', ' ', cc_match.group(1).strip())
            digits_only = re.sub(r'[^\d+]', '', num_clean)
            if 8 <= len(digits_only) <= 12 and not any(digits_only in re.sub(r'[^\d+]', '', d) for d in details):
                details.append(num_clean)

        # 3. Standard Indian mobile (+91...)
        if not details:
            mob_match = re.search(r'(?:\+91[\s-]?)?[6-9]\d{9}\b', text)
            if mob_match:
                mob_num = mob_match.group(0).strip()
                if mob_num not in details:
                    details.append(mob_num)

        # 4. Email address
        email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
        if email_match:
            email_val = email_match.group(0).strip()
            if email_val not in details:
                details.append(email_val)

        if details:
            return {"val": ", ".join(details), "confidence": 0.95}
        
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
        
        # Strip out text inside ingredients list or nutritional info before searching for brand and commodity
        text_for_prod = re.sub(r'Ingredients[:\s][^\n\r]+(?:\n[^\n\r]+)*', '', text, flags=re.IGNORECASE)
        text_for_prod = re.sub(r'Nutritional[^\n\r]+(?:\n[^\n\r]+)*', '', text_for_prod, flags=re.IGNORECASE)

        # Detect Commodity Name (Rule 6(1)(b))
        product_name = ""
        for comm_regex in KNOWN_COMMODITIES:
            comm_match = re.search(r'\b' + comm_regex + r'\b', text_for_prod, re.IGNORECASE)
            if comm_match:
                product_name = comm_match.group(0).strip()
                break

        # Detect Brand Name
        brand_name = ""
        for b in KNOWN_BRANDS:
            if re.search(r'\b' + re.escape(b) + r'\b', text, re.IGNORECASE):
                brand_name = b
                break

        # Fallback to clean lines if commodity wasn't found from dictionary
        if not product_name or not brand_name:
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            noise_patterns = [
                r'^\d{1,2}:\d{2}', r'scanshield', r'scan today', r'align', r'frame', 
                r'barcode', r'battery', r'wifi', r'gallery', r'help', r'tips',
                r'^ingredients', r'^nutritional', r'^mfd', r'^mkt', r'^consumer',
                r'^mrp', r'^net\s*wt', r'fssai', r'fssat', r'jssal', r'issai', r'ssai',
                r'lic[\.\s]*no', r'ic[\.\s]*no', r'licence', r'license', r'^lic', r'^date', r'vegetable\s*oil',
                r'potatoes?', r'iodised', r'salt', r'carbohydrate', r'energy', r'sugars?',
                r'scan\s*the\s*product', r'your\s*data\s*is\s*secure', r'upload\s*from',
                r'ensure\s*the\s*label', r'avoid\s*glare', r'keep\s*the\s*entire',
                r'pvt\.?\s*ltd', r'private\s*limited', r'holdings', r'corporation', r'village\s*channo',
                r'edible\s*oil', r'flavour', r'flavor', r'stabilizer', r'preservative', r'feedback', r'queries',
                r'\d{6,}'
            ]
            clean_lines = []
            for line in lines:
                line_lower = line.lower()
                if not any(re.search(p, line_lower) for p in noise_patterns) and len(line) >= 5:
                    # Remove non-word prefixes
                    cleaned_line = re.sub(r'^[^\w]+', '', line).strip()
                    if len(cleaned_line) >= 5 and not any(re.search(p, cleaned_line.lower()) for p in noise_patterns):
                        clean_lines.append(cleaned_line)

            if clean_lines:
                if not brand_name:
                    brand_name = clean_lines[0][:30]
                if not product_name:
                    # Find first line that isn't brand_name, has valid alphabetic words, and lacks noise symbols
                    cand = [
                        c for c in clean_lines 
                        if c.lower() != brand_name.lower() 
                        and not any(ch in c for ch in ['|', '{', '}', '~', '_', '@', '#', '$', '%', '^', '*', '=', '<', '>', '/', '\\'])
                        and len([w for w in c.split() if w.isalpha() and len(w) >= 3]) >= 1
                    ]
                    if cand:
                        product_name = cand[0][:50]

        # Smart fallback if commodity wasn't cleanly detected
        if not product_name or any(ch in product_name for ch in ['|', '{', '}', '~', '_', '@', '#']) or len([w for w in product_name.split() if w.isalpha() and len(w) >= 3]) < 1:
            if brand_name in ["Lay's", "Lays"] or "potatoes" in text.lower():
                product_name = "Potato Chips"
            elif brand_name in ["Kurkure"]:
                product_name = "Namkeen / Puffed Snack"
            elif brand_name in ["Colgate", "Sensodyne", "Pepsodent"]:
                product_name = "Toothpaste"
            elif brand_name in ["Maggi", "Top Ramen", "Yippee"]:
                product_name = "Instant Noodles"
            elif brand_name in ["Britannia", "Parle", "Oreo", "Sunfeast"]:
                product_name = "Biscuits / Cookies"
            elif brand_name:
                product_name = f"{brand_name} Packaged Commodity"

        # Extract other fields
        mrp_res = self.mrp_extractor.extract(text)
        qty_res = self.qty_extractor.extract(text)
        mfg_res = self.mfg_extractor.extract(text)
        dates_res = self.date_extractor.extract(text)
        cc_res = self.cc_extractor.extract(text)

        # FSSAI license: Look for 14-digit number, or variants of FSSAI / Lic No / Jssal / fssat
        fssai_lic = ""
        # 1. With keyword (tolerant to OCR misreads of FSSAI as jssal, fssat, issai, lic no, etc.)
        fssai_kw_match = re.search(r'(?:fssai|fssat|jssal|issai|lic[\.\s]*no[\.]?|licence[\s]*no|license[\s]*no)[\s\.:]*([0-9\s]{14,18})', text, re.IGNORECASE)
        if fssai_kw_match:
            digits = re.sub(r'\s+', '', fssai_kw_match.group(1))
            if len(digits) >= 14:
                fssai_lic = digits[:14]

        # 2. Standalone 14-digit number (typically starts with 1 or 2 in India)
        if not fssai_lic:
            fssai_standalone = re.search(r'\b([12]\d{13})\b', text)
            if fssai_standalone:
                fssai_lic = fssai_standalone.group(1)

        category = self.category_detector.detect_category(text)
        declarations = self.declaration_detector.detect_declarations(text)

        # Country of origin
        country = ""
        origin_match = re.search(r'(?:country\s*of\s*origin|made\s*in|product\s*of)[:\s]*([A-Za-z\s]+)', text, re.IGNORECASE)
        if origin_match:
            raw_c = origin_match.group(1).strip().split('\n')[0]
            country = re.sub(r'\s*(?:barcode|gtin|fssai|lic|batch|mfg).*', '', raw_c, flags=re.IGNORECASE).strip()
        elif re.search(r'\bIndia\b', text, re.IGNORECASE):
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

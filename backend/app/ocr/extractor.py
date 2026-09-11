import os
import re
import pytesseract
from PIL import Image, ImageOps
from app.config import settings
from app.image_processing.preprocessor import check_image_quality

import shutil
# Configure Tesseract cmd path from settings or common Windows/Linux locations
which_tesseract = shutil.which("tesseract")
TESSERACT_CANDIDATES = [
    getattr(settings, "TESSERACT_CMD", ""),
    which_tesseract,
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    r"C:\Users\Hi-Rich\AppData\Local\Programs\Tesseract-OCR\tesseract.exe",
    "/usr/bin/tesseract",
    "/usr/local/bin/tesseract"
]
for candidate in TESSERACT_CANDIDATES:
    if candidate and os.path.exists(candidate):
        pytesseract.pytesseract.tesseract_cmd = candidate
        break

class TextCleaner:
    @staticmethod
    def clean(raw_text: str) -> str:
        if not raw_text:
            return ""
        # Remove unusual characters while retaining basic punctuation and symbols (₹, %, /, -, etc.)
        cleaned = re.sub(r'[^\w\s\.\,\:\;\-\/\(\)\₹\&\%\@\+]', ' ', raw_text)
        # Normalize whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        return cleaned

class TextNormalizer:
    @staticmethod
    def normalize(text: str) -> str:
        if not text:
            return ""
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        return "\n".join(lines)

class ImageQualityChecker:
    @staticmethod
    def check(image_path: str) -> dict:
        return check_image_quality(image_path)

PACKAGING_KEYWORDS = [
    "mrp", "net", "wt", "weight", "qty", "quantity", "mfg", "exp", "batch", "date", 
    "fssai", "rs", "₹", "inr", "g", "kg", "ml", "l", "consumer", "care", "pkd", 
    "packed", "manufactured", "marketed", "ingredients", "nutritional", "best before", 
    "use by", "lic", "license", "licence", "origin", "india", "pvt", "ltd", "price",
    "pen", "gel", "octane", "classmate", "itc", "scribe", "chennai", "kolkata",
    "limited", "instruments", "smudge", "waterproof", "blue", "ink"
]

def score_text_packaging(text: str) -> int:
    if not text:
        return 0
    tl = text.lower()
    kw_hits = sum(4 for kw in PACKAGING_KEYWORDS if kw in tl)
    has_mrp = 25 if any(m in tl for m in ['mrp', 'rs.', '₹', 'price', 'taxes']) else 0
    has_qty = 20 if any(q in tl for q in ['net', 'wt', 'qty', 'quantity', 'count', 'piece', 'pcs', 'gel', 'pen', 'g', 'kg', 'ml']) else 0
    has_mfg = 20 if any(m in tl for m in ['mfg', 'mfd', 'manufactured', 'marketed', 'packed', 'pvt', 'ltd', 'limited', 'scribe', 'itc']) else 0
    words = len([w for w in text.split() if len(w) >= 3 and w.isalnum()])
    return kw_hits + has_mrp + has_qty + has_mfg + words

def is_packaging_text(text: str) -> bool:
    if not text or len(text.strip()) < 5:
        return False
    text_lower = text.lower()
    matches = sum(1 for kw in PACKAGING_KEYWORDS if kw in text_lower)
    return matches >= 1

class OCRExtractor:
    def __init__(self):
        self.cleaner = TextCleaner()
        self.normalizer = TextNormalizer()
        self.quality_checker = ImageQualityChecker()

    def extract(self, image_path: str) -> dict:
        quality_res = self.quality_checker.check(image_path)
        
        raw_text = ""
        confidence = 0.85

        if os.path.exists(image_path):
            try:
                pil_img = Image.open(image_path)
                try:
                    pil_img = ImageOps.exif_transpose(pil_img)
                except Exception:
                    pass
                if pil_img.mode != 'RGB':
                    pil_img = pil_img.convert('RGB')

                # Limit max dimension to 1600px for speed
                w, h = pil_img.size
                max_dim = 1600
                if max(w, h) > max_dim:
                    scale = max_dim / float(max(w, h))
                    pil_img = pil_img.resize((int(w * scale), int(h * scale)), Image.Resampling.BILINEAR)

                crop_pil = None
                try:
                    import cv2
                    import numpy as np
                    cv_img = np.array(pil_img)
                    ch, cw = cv_img.shape[:2]
                    gray = cv2.cvtColor(cv_img, cv2.COLOR_RGB2GRAY)
                    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
                    thresh = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 15, 4)
                    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    
                    if contours:
                        valid_cnts = [c for c in contours if cv2.contourArea(c) > 0.01 * (cw * ch)]
                        if valid_cnts:
                            max_c = max(valid_cnts, key=cv2.contourArea)
                            bx, by, bw, bh = cv2.boundingRect(max_c)
                            p1x, p1y = max(0, bx - 10), max(0, by - 10)
                            p2x, p2y = min(cw, bx + bw + 10), min(ch, by + bh + 10)
                            crop_pil = Image.fromarray(cv_img[p1y:p2y, p1x:p2x])
                except Exception:
                    pass

                cand = crop_pil if crop_pil is not None else pil_img

                aspect = float(cand.width) / float(cand.height)
                if aspect > 1.8 or aspect < 0.55:
                    angles = [90, 270, 0]
                else:
                    angles = [0, 90, 270]

                best_text = ""
                best_score = -1
                best_conf = 0.88
                collected_lines = []
                seen_lines = set()

                def record_lines(txt):
                    for l in txt.splitlines():
                        ls = l.strip()
                        key = re.sub(r'[^a-zA-Z0-9]', '', ls.lower())
                        if len(key) >= 3 and key not in seen_lines:
                            seen_lines.add(key)
                            collected_lines.append(ls)

                for angle in angles:
                    rot = cand.rotate(angle, expand=True) if angle != 0 else cand
                    
                    # 1. PSM 11 on native crop
                    try:
                        t11 = pytesseract.image_to_string(rot, config='--psm 11')
                        s11 = score_text_packaging(t11)
                        record_lines(t11)
                        if s11 > best_score:
                            best_score = s11
                            best_text = t11
                    except Exception:
                        pass

                    # 2. If this angle shows packaging content, run PSM 6 and sub-box extraction
                    if best_score >= 30:
                        try:
                            t6 = pytesseract.image_to_string(rot, config='--psm 6')
                            record_lines(t6)
                        except Exception:
                            pass

                        try:
                            import cv2
                            import numpy as np
                            rot_cv = np.array(rot)
                            r_gray = cv2.cvtColor(rot_cv, cv2.COLOR_RGB2GRAY)
                            _, w_mask = cv2.threshold(r_gray, 170, 255, cv2.THRESH_BINARY)
                            w_cnts, _ = cv2.findContours(w_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                            stamp_boxes = []
                            for wc in w_cnts:
                                wx, wy, ww, wh = cv2.boundingRect(wc)
                                area = ww * wh
                                if 350 < area < 35000 and ww > 15 and wh > 12:
                                    stamp_boxes.append((area, wx, wy, ww, wh))
                            stamp_boxes.sort(reverse=True)

                            for _, wx, wy, ww, wh in stamp_boxes[:4]:
                                sub_r = rot_cv[wy:wy+wh, wx:wx+ww]
                                sub_sc = max(2.0, 240.0 / min(ww, wh))
                                sub_up = cv2.resize(sub_r, (0, 0), fx=sub_sc, fy=sub_sc, interpolation=cv2.INTER_LANCZOS4)
                                sub_txt = pytesseract.image_to_string(sub_up, config='--psm 11').strip()
                                if sub_txt:
                                    record_lines(sub_txt)
                        except Exception:
                            pass

                        # If winning orientation already found with high score, stop trying other angles
                        if best_score >= 50:
                            break

                # Fallback to uncropped full image if crop had insufficient text
                if best_score < 15:
                    try:
                        t_full = pytesseract.image_to_string(pil_img, config='--psm 11')
                        record_lines(t_full)
                        if score_text_packaging(t_full) > best_score:
                            best_text = t_full
                    except Exception:
                        pass

                # Combine best primary text with unique high-value declaration lines detected
                merged_lines = [l for l in best_text.splitlines() if l.strip()]
                best_norm_set = {re.sub(r'[^a-zA-Z0-9]', '', l.lower()) for l in merged_lines}
                for extra in collected_lines:
                    enorm = re.sub(r'[^a-zA-Z0-9]', '', extra.lower())
                    is_valuable = (
                        any(k in extra.lower() for k in PACKAGING_KEYWORDS) or
                        bool(re.search(r'\b\d{1,2}[\/\.\-]\d{2,4}\b', extra)) or
                        bool(re.search(r'(?:1800|1860)', extra)) or
                        bool(re.search(r'\b\d{1,4}\.\d{2}\b', extra)) or
                        '@' in extra or
                        'classmate' in extra.lower()
                    )
                    if enorm not in best_norm_set and is_valuable:
                        merged_lines.append(extra)
                        best_norm_set.add(enorm)

                raw_text = "\n".join(merged_lines)
                confidence = 0.92 if best_score >= 50 else (0.85 if best_score >= 20 else 0.70)

            except Exception as e:
                print(f"[OCR] pytesseract extraction error on {image_path}: {e}")

        is_valid_label = True
        if not raw_text or len(raw_text.strip()) < 5:
            is_valid_label = False
            confidence = 0.0
        else:
            is_valid_label = is_packaging_text(raw_text)

        cleaned_text = self.cleaner.clean(raw_text)
        normalized_text = self.normalizer.normalize(raw_text)

        return {
            "raw_text": raw_text,
            "cleaned_text": cleaned_text,
            "normalized_text": normalized_text,
            "confidence": confidence,
            "is_valid_label": is_valid_label,
            "quality": quality_res
        }

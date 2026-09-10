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

                candidates = []

                # Fast packaging contour detection with bounding box merging
                try:
                    import cv2
                    import numpy as np
                    cv_img = np.array(pil_img)
                    ch, cw = cv_img.shape[:2]
                    gray = cv2.cvtColor(cv_img, cv2.COLOR_RGB2GRAY)
                    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
                    thresh = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 15, 4)
                    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    
                    raw_boxes = []
                    for cnt in contours:
                        bx, by, bw, bh = cv2.boundingRect(cnt)
                        if 0.01 * (cw * ch) < bw * bh < 0.85 * (cw * ch) and bw > 35 and bh > 35:
                            raw_boxes.append([bx, by, bx + bw, by + bh])
                            
                    merged_boxes = []
                    for b in sorted(raw_boxes, key=lambda x: (x[2]-x[0])*(x[3]-x[1]), reverse=True):
                        merged = False
                        for mb in merged_boxes:
                            y_overlap = max(0, min(b[3], mb[3]) - max(b[1], mb[1]))
                            x_dist = max(0, max(b[0], mb[0]) - min(b[2], mb[2]))
                            x_overlap = max(0, min(b[2], mb[2]) - max(b[0], mb[0]))
                            y_dist = max(0, max(b[1], mb[1]) - min(b[3], mb[3]))
                            if (y_overlap > 25 and x_dist < 100) or (x_overlap > 25 and y_dist < 100):
                                mb[0] = min(mb[0], b[0])
                                mb[1] = min(mb[1], b[1])
                                mb[2] = max(mb[2], b[2])
                                mb[3] = max(mb[3], b[3])
                                merged = True
                                break
                        if not merged:
                            merged_boxes.append(b)
                            
                    if raw_boxes:
                        rb0 = sorted(raw_boxes, key=lambda x: (x[2]-x[0])*(x[3]-x[1]), reverse=True)[0]
                        candidates.append(Image.fromarray(cv_img[rb0[1]:rb0[3], rb0[0]:rb0[2]]))

                    if merged_boxes:
                        mb = merged_boxes[0]
                        p1x, p1y = max(0, mb[0] - 10), max(0, mb[1] - 10)
                        p2x, p2y = min(cw, mb[2] + 10), min(ch, mb[3] + 10)
                        crop_pil = Image.fromarray(cv_img[p1y:p2y, p1x:p2x])
                        candidates.append(crop_pil)
                except Exception:
                    pass

                # If no crops detected, fallback to full image
                if not candidates:
                    candidates.append(pil_img)

                best_text = ""
                best_score = -1
                best_conf = 0.85
                collected_lines = []
                seen_lines = set()

                def record_lines(txt):
                    for l in txt.splitlines():
                        ls = l.strip()
                        key = re.sub(r'[^a-zA-Z0-9]', '', ls.lower())
                        if len(key) >= 3 and key not in seen_lines:
                            seen_lines.add(key)
                            collected_lines.append(ls)

                for cand in candidates:
                    min_d = min(cand.width, cand.height)
                    sc = 280.0 / min_d if min_d < 280 else 1.0
                    cand_scaled = cand.resize((int(cand.width * sc), int(cand.height * sc)), Image.Resampling.LANCZOS)

                    # Try primary orientations: 0, 270, 90 (and 180 if needed)
                    for angle in [0, 270, 90]:
                        rot = cand_scaled.rotate(angle, expand=True) if angle != 0 else cand_scaled
                        for psm in [11, 6]:
                            try:
                                data = pytesseract.image_to_data(rot, config=f'--psm {psm}', output_type=pytesseract.Output.DICT, timeout=8)
                                words = [(data['text'][i] or '').strip() for i in range(len(data['text'])) if (data['text'][i] or '').strip()]
                                t = "\n".join(" ".join(words[j:j+8]) for j in range(0, len(words), 8))
                                sc = score_text_packaging(t)
                                record_lines(t)
                                if sc > best_score:
                                    best_score = sc
                                    best_text = t
                                    confs = [int(c) for c in data.get('conf', []) if str(c).isdigit() and int(c) > 0]
                                    if confs:
                                        best_conf = round(sum(confs) / (len(confs) * 100.0), 2)
                            except Exception:
                                pass

                        # Check for white sub-boxes (stamps, dates, MRP badges) in the rotated image
                        try:
                            import cv2
                            import numpy as np
                            rot_cv = np.array(rot)
                            r_gray = cv2.cvtColor(rot_cv, cv2.COLOR_RGB2GRAY)
                            _, w_mask = cv2.threshold(r_gray, 170, 255, cv2.THRESH_BINARY)
                            w_cnts, _ = cv2.findContours(w_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                            for wc in sorted(w_cnts, key=cv2.contourArea, reverse=True)[:8]:
                                wx, wy, ww, wh = cv2.boundingRect(wc)
                                if 350 < ww * wh < 30000 and ww > 15 and wh > 12:
                                    sub_r = rot_cv[wy:wy+wh, wx:wx+ww]
                                    sub_sc = max(2.0, 260.0 / min(ww, wh))
                                    sub_up = cv2.resize(sub_r, (0, 0), fx=sub_sc, fy=sub_sc, interpolation=cv2.INTER_LANCZOS4)
                                    sub_txt = pytesseract.image_to_string(sub_up, config='--psm 11')
                                    if sub_txt and any(k in sub_txt.lower() for k in ['09/', '202', 'mrp', 'mfd', 'net', 'itc', 'care', '1800', '@', 'rs', '₹', 'pen']):
                                        record_lines(sub_txt)
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
                        bool(re.search(r'\b(?:1800|1860)\b', extra)) or
                        bool(re.search(r'\b\d{1,4}\.\d{2}\b', extra))
                    )
                    if enorm not in best_norm_set and is_valuable:
                        merged_lines.append(extra)
                        best_norm_set.add(enorm)

                raw_text = "\n".join(merged_lines)
                confidence = best_conf

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

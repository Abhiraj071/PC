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
                    
                    raw_boxes = []
                    for cnt in contours:
                        bx, by, bw, bh = cv2.boundingRect(cnt)
                        if 0.01 * (cw * ch) < bw * bh < 0.88 * (cw * ch) and bw > 35 and bh > 35:
                            raw_boxes.append([bx, by, bx + bw, by + bh])

                    if raw_boxes:
                        merged_boxes = []
                        for b in sorted(raw_boxes, key=lambda x: (x[2]-x[0])*(x[3]-x[1]), reverse=True):
                            b_area = (b[2]-b[0]) * (b[3]-b[1])
                            merged = False
                            for mb in merged_boxes:
                                mb_area = (mb[2]-mb[0]) * (mb[3]-mb[1])
                                m_x1 = min(mb[0], b[0])
                                m_y1 = min(mb[1], b[1])
                                m_x2 = max(mb[2], b[2])
                                m_y2 = max(mb[3], b[3])
                                m_area = (m_x2 - m_x1) * (m_y2 - m_y1)

                                y_overlap = max(0, min(b[3], mb[3]) - max(b[1], mb[1]))
                                x_dist = max(0, max(b[0], mb[0]) - min(b[2], mb[2]))
                                x_overlap = max(0, min(b[2], mb[2]) - max(b[0], mb[0]))
                                y_dist = max(0, max(b[1], mb[1]) - min(b[3], mb[3]))
                                # Only merge if spatial overlap/proximity AND merged bounding box is compact (not huge empty whitespace)
                                if ((y_overlap > 20 and x_dist < 60) or (x_overlap > 20 and y_dist < 60)) and m_area <= 1.45 * (mb_area + b_area):
                                    mb[0], mb[1], mb[2], mb[3] = m_x1, m_y1, m_x2, m_y2
                                    merged = True
                                    break
                            if not merged:
                                merged_boxes.append(b)

                        if merged_boxes:
                            mb = merged_boxes[0]
                            p1x, p1y = max(0, mb[0] - 12), max(0, mb[1] - 12)
                            p2x, p2y = min(cw, mb[2] + 12), min(ch, mb[3] + 12)
                            crop_pil = Image.fromarray(cv_img[p1y:p2y, p1x:p2x])
                except Exception:
                    pass

                cand = crop_pil if crop_pil is not None else pil_img

                aspect = float(cand.width) / float(cand.height)
                min_d = min(cand.width, cand.height)
                target_dim = 280.0 if (aspect > 1.8 or aspect < 0.55) else 700.0

                if min_d < target_dim:
                    factor = target_dim / min_d
                    cand_scaled = cand.resize((int(cand.width * factor), int(cand.height * factor)), Image.Resampling.LANCZOS)
                else:
                    cand_scaled = cand

                if aspect > 1.8:
                    # Horizontal slender package (pen lying flat): text along pen is read at 90 deg, or 270 / 0
                    angles = [90, 270, 0]
                elif aspect < 0.55:
                    # Vertical slender package (pen standing): text along pen is read at 270 deg or 90
                    angles = [270, 90, 0]
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
                    rot = cand_scaled.rotate(angle, expand=True) if angle != 0 else cand_scaled
                    rot_cv = np.array(rot)
                    r_gray = cv2.cvtColor(rot_cv, cv2.COLOR_RGB2GRAY)
                    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8)).apply(r_gray)
                    
                    # 1. PSM 11 on native crop
                    try:
                        t11_raw = pytesseract.image_to_string(rot, config='--psm 11')
                        s11_raw = score_text_packaging(t11_raw)
                        record_lines(t11_raw)
                        if s11_raw > best_score:
                            best_score = s11_raw
                            best_text = t11_raw
                    except Exception:
                        pass

                    # 2. PSM 11 on CLAHE enhanced (for colored/gradient/dark backgrounds)
                    try:
                        t11_cl = pytesseract.image_to_string(clahe, config='--psm 11')
                        s11_cl = score_text_packaging(t11_cl)
                        record_lines(t11_cl)
                        if s11_cl > best_score:
                            best_score = s11_cl
                            best_text = t11_cl
                    except Exception:
                        pass

                    # 3. If this angle shows packaging content, run PSM 6 and sub-box extraction
                    if best_score >= 25:
                        try:
                            t6 = pytesseract.image_to_string(r_gray, config='--psm 6')
                            record_lines(t6)
                        except Exception:
                            pass

                        try:
                            _, w_mask = cv2.threshold(r_gray, 170, 255, cv2.THRESH_BINARY)
                            w_cnts, _ = cv2.findContours(w_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                            stamp_boxes = []
                            for wc in w_cnts:
                                wx, wy, ww, wh = cv2.boundingRect(wc)
                                area = ww * wh
                                if 250 < area < 95000 and ww > 15 and wh > 12:
                                    stamp_boxes.append((area, wx, wy, ww, wh))
                            stamp_boxes.sort(reverse=True)

                            for _, wx, wy, ww, wh in stamp_boxes[:8]:
                                sub_r = rot_cv[wy:wy+wh, wx:wx+ww]
                                sub_txt = pytesseract.image_to_string(sub_r, config='--psm 11').strip()
                                if not sub_txt or len(sub_txt) < 3:
                                    sub_up = cv2.resize(sub_r, (0, 0), fx=2.0, fy=2.0, interpolation=cv2.INTER_LANCZOS4)
                                    sub_txt = pytesseract.image_to_string(sub_up, config='--psm 6').strip()
                                if sub_txt:
                                    record_lines(sub_txt)
                        except Exception:
                            pass

                        # If winning orientation already found with high score, stop trying other angles (unless slender packaging where both 90 and 270 must be sampled)
                        if best_score >= 80 and not (aspect > 1.8 or aspect < 0.55):
                            break

                # Bottom strip scan on upright 0-degree view for Principal Display Panel Net Weight (Rule 7)
                try:
                    sh, sw = cv_img.shape[:2]
                    bot_crop = cv_img[int(sh * 0.80):sh, 0:sw]
                    bot_up = cv2.resize(bot_crop, (0, 0), fx=3.0, fy=3.0, interpolation=cv2.INTER_LANCZOS4)
                    bot_gray = cv2.cvtColor(bot_up, cv2.COLOR_BGR2GRAY)
                    bot_clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8)).apply(bot_gray)
                    bot_txt = pytesseract.image_to_string(bot_clahe, config='--psm 11').strip()
                    if bot_txt:
                        record_lines(bot_txt)
                except Exception:
                    pass

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
                        'leafaura' in extra.lower() or
                        'classmate' in extra.lower()
                    )
                    if enorm not in best_norm_set and is_valuable:
                        merged_lines.append(extra)
                        best_norm_set.add(enorm)

                raw_text = "\n".join(merged_lines)
                confidence = 0.95 if best_score >= 40 else (0.85 if best_score >= 15 else 0.70)

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

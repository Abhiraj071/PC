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
    "use by", "lic", "license", "licence", "origin", "india", "pvt", "ltd", "price"
]

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
        all_passes_text = []
        conf_scores = []

        if os.path.exists(image_path):
            try:
                pil_img = Image.open(image_path)
                # Auto-orient based on mobile camera EXIF metadata
                try:
                    pil_img = ImageOps.exif_transpose(pil_img)
                except Exception:
                    pass

                # Convert to RGB
                if pil_img.mode != 'RGB':
                    pil_img = pil_img.convert('RGB')

                # Auto-resize if image is excessively large (> 1600px) to prevent slow Tesseract execution
                w, h = pil_img.size
                max_dim = 1600
                if max(w, h) > max_dim:
                    scale = max_dim / float(max(w, h))
                    pil_img = pil_img.resize((int(w * scale), int(h * scale)), Image.Resampling.BILINEAR)

                # Primary Pass: Single-pass image_to_data captures text, layout, and confidence simultaneously
                try:
                    data = pytesseract.image_to_data(pil_img, config='--psm 3', output_type=pytesseract.Output.DICT, timeout=12)
                    conf_list = [int(c) for c in data.get('conf', []) if str(c).isdigit() and int(c) > 0]
                    if conf_list:
                        confidence = round(sum(conf_list) / (len(conf_list) * 100.0), 2)
                    else:
                        confidence = 0.85

                    lines_dict = {}
                    for i, word in enumerate(data.get('text', [])):
                        w_str = (word or '').strip()
                        if not w_str:
                            continue
                        line_key = (data['block_num'][i], data['par_num'][i], data['line_num'][i])
                        if line_key not in lines_dict:
                            lines_dict[line_key] = []
                        lines_dict[line_key].append(w_str)

                    if lines_dict:
                        raw_text = "\n".join(" ".join(words) for words in lines_dict.values())
                except Exception as e1:
                    print(f"[OCR] Primary Pass error: {e1}")

                # Targeted Fallback: Only if primary pass found very little text (< 40 characters)
                if not raw_text or len(raw_text.strip()) < 40:
                    try:
                        import cv2
                        import numpy as np
                        np_img = np.array(pil_img)
                        gray = cv2.cvtColor(np_img, cv2.COLOR_RGB2GRAY)
                        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                        enhanced = clahe.apply(gray)
                        p2_data = pytesseract.image_to_data(enhanced, config='--psm 6', output_type=pytesseract.Output.DICT, timeout=12)
                        
                        p2_lines = {}
                        for i, word in enumerate(p2_data.get('text', [])):
                            w_str = (word or '').strip()
                            if not w_str:
                                continue
                            line_key = (p2_data['block_num'][i], p2_data['par_num'][i], p2_data['line_num'][i])
                            if line_key not in p2_lines:
                                p2_lines[line_key] = []
                            p2_lines[line_key].append(w_str)

                        p2_text = "\n".join(" ".join(words) for words in p2_lines.values())
                        if len(p2_text.strip()) > len(raw_text.strip()):
                            raw_text = p2_text
                            p2_confs = [int(c) for c in p2_data.get('conf', []) if str(c).isdigit() and int(c) > 0]
                            if p2_confs:
                                confidence = round(sum(p2_confs) / (len(p2_confs) * 100.0), 2)
                    except Exception as e2:
                        print(f"[OCR] Enhanced fallback error: {e2}")

            except Exception as e:
                print(f"[OCR] pytesseract extraction error on {image_path}: {e}")

        # Check packaging text
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

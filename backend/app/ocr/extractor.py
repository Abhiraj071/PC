import os
import re
import pytesseract
from PIL import Image, ImageOps
from app.config import settings
from app.image_processing.preprocessor import check_image_quality

# Configure Tesseract cmd path from settings or common Windows/Linux locations
TESSERACT_CANDIDATES = [
    getattr(settings, "TESSERACT_CMD", ""),
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

                # Pass 1: Standard Full-Color OCR (PSM 3 - fully automatic page segmentation)
                try:
                    p1_text = pytesseract.image_to_string(pil_img, config='--psm 3')
                    if p1_text and len(p1_text.strip()) > 0:
                        all_passes_text.append(p1_text)
                except Exception as e1:
                    print(f"[OCR] Pass 1 error: {e1}")

                # Pass 2: Grayscale + CLAHE Contrast Enhancement
                try:
                    import cv2
                    import numpy as np
                    np_img = np.array(pil_img)
                    gray = cv2.cvtColor(np_img, cv2.COLOR_RGB2GRAY)
                    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
                    enhanced = clahe.apply(gray)
                    p2_text = pytesseract.image_to_string(enhanced, config='--psm 11')
                    if p2_text and len(p2_text.strip()) > 0:
                        all_passes_text.append(p2_text)
                except Exception as e2:
                    print(f"[OCR] Pass 2 error: {e2}")

                # Pass 3: Single uniform block mode (PSM 6) for label text blocks
                try:
                    p3_text = pytesseract.image_to_string(pil_img, config='--psm 6')
                    if p3_text and len(p3_text.strip()) > 0:
                        all_passes_text.append(p3_text)
                except Exception as e3:
                    print(f"[OCR] Pass 3 error: {e3}")

                # Merge unique lines across passes while maintaining order
                lines_seen = set()
                merged_lines = []
                for pass_txt in all_passes_text:
                    for line in pass_txt.splitlines():
                        cleaned_line = line.strip()
                        norm_key = re.sub(r'\s+', ' ', cleaned_line.lower())
                        if len(cleaned_line) >= 2 and norm_key not in lines_seen:
                            lines_seen.add(norm_key)
                            merged_lines.append(cleaned_line)

                if merged_lines:
                    raw_text = "\n".join(merged_lines)

                # Confidence calculation
                try:
                    data = pytesseract.image_to_data(pil_img, output_type=pytesseract.Output.DICT)
                    conf_list = [int(c) for c in data.get('conf', []) if str(c).isdigit() and int(c) > 0]
                    if conf_list:
                        confidence = round(sum(conf_list) / (len(conf_list) * 100.0), 2)
                    else:
                        confidence = 0.85
                except Exception:
                    confidence = 0.85

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

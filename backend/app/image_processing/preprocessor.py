import os
import cv2
import numpy as np
from app.config import settings

def check_image_quality(image_path: str) -> dict:
    """
    Evaluates image quality using Laplacian variance blur detection
    and brightness analysis.
    """
    if not os.path.exists(image_path):
        return {"is_good_quality": False, "score": 0.0, "reason": "File not found"}

    img = cv2.imread(image_path)
    if img is None:
        return {"is_good_quality": False, "score": 0.0, "reason": "Invalid image format"}

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Blur detection via Laplacian variance
    variance = cv2.Laplacian(gray, cv2.CV_64F).var()
    
    # Brightness calculation
    brightness = np.mean(gray)
    
    is_blur = variance < 80.0
    is_dark = brightness < 40.0
    is_overexposed = brightness > 220.0
    
    reasons = []
    if is_blur:
        reasons.append("Blurry image detected")
    if is_dark:
        reasons.append("Low lighting")
    if is_overexposed:
        reasons.append("High glare/overexposure")

    is_good = len(reasons) == 0
    score = min(1.0, max(0.2, (variance / 300.0) * (brightness / 128.0)))

    return {
        "is_good_quality": is_good,
        "score": round(score, 2),
        "laplacian_variance": round(variance, 2),
        "brightness": round(brightness, 2),
        "reasons": reasons if reasons else ["Clear and properly captured"]
    }

def correct_rotation(image: np.ndarray) -> np.ndarray:
    """
    Conservatively deskews image based on Hough Lines if a consistent, slight tilt (< 12 degrees) is detected.
    Avoids misrotating on diagonal packaging graphic artwork.
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, 100, minLineLength=120, maxLineGap=10)
    
    if lines is None:
        return image

    angles = []
    for line in lines:
        coords = line.ravel()
        if len(coords) >= 4:
            x1, y1, x2, y2 = coords[:4]
            angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
            # Only consider slight tilt to avoid mistaking packaging art for camera tilt
            if abs(angle) < 12.0:
                angles.append(angle)
            
    if len(angles) < 4:
        return image

    median_angle = float(np.median(angles))
    if abs(median_angle) < 0.75:
        return image

    h, w = image.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, median_angle, 1.0)
    rotated = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    return rotated

def enhance_image(image: np.ndarray) -> np.ndarray:
    """
    Applies CLAHE (Contrast Limited Adaptive Histogram Equalization) and denoising.
    """
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced_gray = clahe.apply(gray)
    denoised = cv2.medianBlur(enhanced_gray, 3)
    return denoised

def crop_label(image: np.ndarray) -> np.ndarray:
    """
    Safely crops dark borders or background only if packaging covers nearly the full frame.
    Never aggressively crops away valid packaging declarations.
    """
    # Keep full image to ensure no mandatory declaration text is discarded
    return image

def preprocess_image(input_path: str, output_filename: str) -> str:
    """
    Full pipeline: Load -> Quality Check -> Deskew -> Enhance -> Save Preprocessed File.
    """
    if not os.path.exists(input_path):
        return input_path

    img = cv2.imread(input_path)
    if img is None:
        return input_path

    # Rotate correction (conservative)
    img = correct_rotation(img)

    # Enhance contrast and readability across full package
    enhanced_gray = enhance_image(img)

    output_path = os.path.join(settings.PREPROCESSED_DIR, output_filename)
    cv2.imwrite(output_path, enhanced_gray)
    return output_path

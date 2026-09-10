import os
from pydantic import ConfigDict
from pydantic_settings import BaseSettings

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

class Settings(BaseSettings):
    APP_NAME: str = "ScanShield"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    
    JWT_SECRET: str = "scanshield_super_secret_jwt_key_2026_sih"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    
    DATABASE_URL: str = f"sqlite:///{os.path.join(PROJECT_ROOT, 'scanshield.db').replace('\\', '/')}"
    
    UPLOAD_DIR: str = os.path.join(PROJECT_ROOT, "storage", "uploads")
    PREPROCESSED_DIR: str = os.path.join(PROJECT_ROOT, "storage", "preprocessed")
    REPORT_DIR: str = os.path.join(PROJECT_ROOT, "storage", "reports")
    
    TESSERACT_CMD: str = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

    model_config = ConfigDict(env_file=".env", extra="ignore")

settings = Settings()

# Ensure storage directories exist
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.PREPROCESSED_DIR, exist_ok=True)
os.makedirs(settings.REPORT_DIR, exist_ok=True)

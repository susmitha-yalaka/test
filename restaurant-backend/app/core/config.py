import os
from typing import Optional, List
from dotenv import load_dotenv

# Load variables from .env into environment
load_dotenv()

# === WhatsApp / Meta ===
VERIFY_TOKEN: str = os.getenv("VERIFY_TOKEN", "")
WABA_TOKEN: str = os.getenv("WABA_TOKEN", "")
PHONE_NUMBER_ID: str = os.getenv("PHONE_NUMBER_ID", "")
APP_SECRET: Optional[str] = os.getenv("APP_SECRET")

# === App ===
GRAPH_API_VERSION: str = os.getenv("GRAPH_API_VERSION", "v21.0")
MENU_PDF_URL: str = os.getenv("MENU_PDF_URL", "")
FOLLOWUP_TEXT: Optional[str] = os.getenv("FOLLOWUP_TEXT")
SEND_FOLLOWUP: bool = os.getenv("SEND_FOLLOWUP", "true").lower() in ["1", "true", "yes"]

# === CORS ===
# Parse comma-separated list (e.g. CORS_ALLOW_ORIGINS="http://localhost:3000,http://127.0.0.1:5173")
CORS_ALLOW_ORIGINS: List[str] = [
    origin.strip() for origin in os.getenv("CORS_ALLOW_ORIGINS", "*").split(",")
]

# === Base URL (optional, if you want to reference your own service) ===
BASE_URL: str = os.getenv("BASE_URL", "")

RESTAURANT_BASE_URL: str = os.getenv("RESTAURANT_BASE_URL", "")
DATABASE_URL = os.getenv("DATABASE_URL")

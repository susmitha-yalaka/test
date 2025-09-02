import os
from typing import Optional, List
from dotenv import load_dotenv

# Load variables from .env into environment
load_dotenv()

# === WhatsApp / Meta ===
VERIFY_TOKEN: str = os.getenv("VERIFY_TOKEN", "")
WHATSAPP_TOKEN: str = os.getenv("WHATSAPP_TOKEN", "")
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
FLOW_NAME = os.getenv("FLOW_NAME")
TARGET_WA_NUMBER = os.getenv("TARGET_WA_NUMBER")
# Menu generation/cache
CACHE_DIR = os.getenv("MENU_CACHE_DIR", "cache")
EXCEL_FILENAME = os.getenv("MENU_EXCEL_FILENAME", "menu.xlsx")
PDF_FILENAME = os.getenv("MENU_PDF_FILENAME", "menu.pdf")
LOGO_PATH = os.getenv("MENU_LOGO_PATH", "logo.png")
CURRENCY_PREFIX = os.getenv("MENU_CURRENCY_PREFIX", "₹")

# Google Drive source (optional; if unset, we’ll use local excel file)
DRIVE_SA_FILE = os.getenv("DRIVE_SA_FILE", "")          # path to service-account json
DRIVE_FILE_ID = os.getenv("DRIVE_FILE_ID", "")
FLOW_NAME = os.getenv("FLOW_NAME", "")
FLOW_ID = os.getenv("FLOW_ID", "")

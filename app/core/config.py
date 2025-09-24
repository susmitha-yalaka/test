import os
from typing import Optional

from dotenv import load_dotenv

# Load variables from .env into environment
load_dotenv()

# === WhatsApp / Meta ===
VERIFY_TOKEN: str = os.getenv("VERIFY_TOKEN", "")
WHATSAPP_TOKEN: str = os.getenv("WHATSAPP_TOKEN", "")
WABA_ID: str = os.getenv("WABA_ID", "")
PHONE_NUMBER_ID: str = os.getenv("PHONE_NUMBER_ID", "")
APP_SECRET: Optional[str] = os.getenv("APP_SECRET")

# === App ===
GRAPH_API_VERSION: str = os.getenv("GRAPH_API_VERSION", "v21.0")
FOLLOWUP_TEXT: Optional[str] = os.getenv("FOLLOWUP_TEXT")
SEND_FOLLOWUP: bool = os.getenv("SEND_FOLLOWUP", "true").lower() in ["1", "true", "yes"]

# === Base URL (optional, if you want to reference your own service) ===
BASE_URL: str = os.getenv("BASE_URL", "")

DATABASE_URL = os.getenv("DATABASE_URL")
FLOW_NAME = os.getenv("FLOW_NAME")
TARGET_WA_NUMBER = os.getenv("TARGET_WA_NUMBER")
FLOW_ID = os.getenv("FLOW_ID", "")

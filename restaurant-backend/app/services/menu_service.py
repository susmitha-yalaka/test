import hashlib
import io
from pathlib import Path
from typing import Dict, Optional, Tuple
import json

import anyio
import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Flowable, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.units import inch

from app.core import config

# Optional Google Drive imports only if configured
if config.DRIVE_SA_FILE and config.DRIVE_FILE_ID:
    from googleapiclient.discovery import build  # type: ignore
    from google.oauth2 import service_account    # type: ignore


CACHE_DIR = Path(config.CACHE_DIR)
EXCEL_PATH = CACHE_DIR / config.EXCEL_FILENAME
PDF_PATH = CACHE_DIR / config.PDF_FILENAME
META_PATH = CACHE_DIR / "menu_meta.json"      # stores md5 + modifiedTime
LOCK_PATH = CACHE_DIR / ".menu.lock"


class Dot(Flowable):
    def __init__(self, size=8, color=colors.green):
        super().__init__()
        self.size = size
        self.color = color
        self.width = self.size
        self.height = self.size

    def draw(self):
        self.canv.setFillColor(self.color)
        self.canv.circle(self.size/2, self.size/2, self.size/2, fill=1)


async def _drive_get_metadata() -> Optional[Dict]:
    if not (config.DRIVE_SA_FILE and config.DRIVE_FILE_ID):
        return None

    def _inner():
        creds = service_account.Credentials.from_service_account_file(
            config.DRIVE_SA_FILE,
            scopes=["https://www.googleapis.com/auth/drive.readonly"]
        )
        svc = build("drive", "v3", credentials=creds)
        return svc.files().get(fileId=config.DRIVE_FILE_ID, fields="md5Checksum,modifiedTime,name,mimeType").execute()
    return await anyio.to_thread.run_sync(_inner)


async def _drive_download_excel() -> bytes:
    def _inner() -> bytes:
        creds = service_account.Credentials.from_service_account_file(
            config.DRIVE_SA_FILE,
            scopes=["https://www.googleapis.com/auth/drive.readonly"]
        )
        svc = build("drive", "v3", credentials=creds)
        buf = io.BytesIO()
        req = svc.files().get_media(fileId=config.DRIVE_FILE_ID)
        downloader = build("drive", "v3", credentials=creds)._http  # not used; keep simple
        # Use Google API's MediaIoBaseDownload via request.execute(media_body), safer:
        from googleapiclient.http import MediaIoBaseDownload  # type: ignore
        downloader = MediaIoBaseDownload(buf, req)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        return buf.getvalue()
    return await anyio.to_thread.run_sync(_inner)


def _load_meta() -> Dict:
    if META_PATH.exists():
        try:
            return json.loads(META_PATH.read_text())
        except Exception:
            return {}
    return {}


def _save_meta(meta: Dict) -> None:
    META_PATH.write_text(json.dumps(meta, indent=2))


def _md5(data: bytes) -> str:
    h = hashlib.md5()
    h.update(data)
    return h.hexdigest()


async def refresh_excel_if_needed() -> Tuple[bool, str]:
    """
    Returns (updated, reason)
    - If Drive is configured: compare md5Checksum/modifiedTime to local; download if changed.
    - Else: ensure local EXCEL_PATH exists.
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    if config.DRIVE_SA_FILE and config.DRIVE_FILE_ID:
        remote = await _drive_get_metadata()
        if not remote:
            return (False, "drive_metadata_unavailable")

        meta = _load_meta()
        remote_md5 = remote.get("md5Checksum")
        remote_mtime = remote.get("modifiedTime")
        if meta.get("md5Checksum") == remote_md5 and EXCEL_PATH.exists():
            return (False, "no_change")

        data = await _drive_download_excel()
        EXCEL_PATH.write_bytes(data)
        _save_meta({"md5Checksum": _md5(data), "modifiedTime": remote_mtime})
        return (True, "downloaded")

    # No Drive: just check local presence
    if not EXCEL_PATH.exists():
        raise FileNotFoundError(f"Excel not found at {EXCEL_PATH}. Provide local file or configure Drive.")
    return (False, "local_only")


def _find_item_column(df: pd.DataFrame) -> str:
    for col in ["Dish Name", "Item Name", "Item"]:
        if col in df.columns:
            return col
    raise ValueError("Excel must contain one of: 'Dish Name', 'Item Name', 'Item'.")


def _generate_menu_pdf_sync(excel_path: Path, logo_path: str, output_path: Path) -> None:
    df = pd.read_excel(excel_path)
    df.columns = df.columns.str.strip()
    item_col = _find_item_column(df)
    for col in ['Category', 'Subcategory', 'Type', 'Price', 'Description']:
        if col not in df.columns:
            df[col] = ''

    df['Category'] = df['Category'].astype(str).str.strip().str.title()
    df['Subcategory'] = df['Subcategory'].astype(str).str.strip().str.title()
    df['Type'] = df['Type'].astype(str).str.strip().str.title()

    fixed_order = ['Starters', 'Main Course', 'Desserts']
    others = sorted([c for c in df['Category'].unique() if c not in fixed_order])
    order = fixed_order + others
    df['Category'] = pd.Categorical(df['Category'], categories=order, ordered=True)

    doc = SimpleDocTemplate(str(output_path), pagesize=A4, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='ItemName', fontSize=14, leading=16, spaceAfter=2, spaceBefore=2))
    styles.add(ParagraphStyle(name='Description', fontSize=10, leading=12, fontName='Helvetica-Oblique',
                              textColor=colors.darkgrey, spaceAfter=8))
    styles.add(ParagraphStyle(name='Subcategory', fontSize=16, leading=18, textColor=colors.HexColor("#1E90FF"),
                              spaceBefore=12, spaceAfter=6, leftIndent=10, fontName='Helvetica-Bold'))

    elements = []
    logo_p = Path(logo_path)
    if logo_p.exists():
        elements.append(Image(str(logo_p), width=1.5*inch, height=1.5*inch, hAlign='CENTER'))

    elements.append(Paragraph("Dheeraj Balabadra", ParagraphStyle(
        name="RestaurantName", fontSize=28, leading=32, alignment=1, textColor=colors.darkred, spaceAfter=20
    )))

    palette = {"Starters": colors.HexColor("#FF8C00"), "Main Course": colors.HexColor("#8B0000"), "Desserts": colors.HexColor("#A0522D")}
    default_color = colors.HexColor("#555555")

    grouped = df.groupby('Category', observed=False)
    for cat in order:
        if cat not in grouped.groups:
            continue
        items = grouped.get_group(cat).copy()
        items['VegSort'] = items['Type'].str.lower().apply(lambda x: 0 if x == 'veg' else 1)
        items = items.sort_values(['VegSort', 'Subcategory', item_col])

        cat_color = palette.get(cat, default_color)
        elements.append(Paragraph(f"<b>{cat}</b>", ParagraphStyle(
            name='CategoryHeader', fontSize=18, alignment=1, textColor=colors.whitesmoke,
            backColor=cat_color, spaceBefore=12, spaceAfter=12, leading=22
        )))

        for subcat, sub in items.groupby('Subcategory'):
            if str(subcat).strip():
                elements.append(Paragraph(str(subcat), styles['Subcategory']))

            for _, row in sub.iterrows():
                veg = str(row["Type"]).strip().lower() == "veg"
                dot = Dot(size=8, color=(colors.green if veg else colors.red))

                item_name = Paragraph(str(row.get(item_col, "")), styles['ItemName'])
                price_val = row.get('Price', '')
                price_str = f"{config.CURRENCY_PREFIX}{int(price_val)}" if price_val != '' and pd.notnull(price_val) else ""
                price = Paragraph(price_str, styles['ItemName'])
                desc_val = row.get('Description', '')
                description = Paragraph(str(desc_val) if pd.notnull(desc_val) else '', styles['Description'])

                table = Table([[dot, item_name, price]], colWidths=[10, 400, 70], hAlign='LEFT')
                table.setStyle(TableStyle([
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('LEFTPADDING', (0, 0), (-1, -1), 0),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                    ('TOPPADDING', (0, 0), (-1, -1), 0),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
                ]))
                elements.append(table)
                elements.append(description)

        elements.append(Spacer(1, 18))

    footer = """
    <b>Address:</b> 123 Foodie Street, Flavor Town, India<br/>
    <b>Contact:</b> +91-9876543210 | <b>Email:</b> contact@gourmetgarden.com<br/>
    <b>Opening Hours:</b> Mon - Sun: 11:00 AM to 11:00 PM
    """
    elements.append(Paragraph(footer, ParagraphStyle(name="Footer", fontSize=10, alignment=1, textColor=colors.grey, spaceBefore=30)))
    doc.build(elements)


async def generate_pdf_if_needed() -> Tuple[bool, str]:
    """
    Ensures the menu PDF exists and is fresh.
    Returns (updated, reason)
    """
    updated, reason = await refresh_excel_if_needed()

    # lock to avoid concurrent builds
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    async with anyio.FileLock(str(LOCK_PATH)):
        if updated or not PDF_PATH.exists():
            # Run heavy build on a worker thread
            await anyio.to_thread.run_sync(_generate_menu_pdf_sync, EXCEL_PATH, config.LOGO_PATH, PDF_PATH)
            return True, "pdf_built"
    return False, reason


def get_pdf_path() -> Path:
    return PDF_PATH.resolve()


def get_status() -> Dict:
    meta = _load_meta()
    return {
        "excel_exists": EXCEL_PATH.exists(),
        "pdf_exists": PDF_PATH.exists(),
        "excel_md5": meta.get("md5Checksum"),
        "pdf_path": str(PDF_PATH.resolve()) if PDF_PATH.exists() else None,
    }

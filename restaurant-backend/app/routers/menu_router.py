from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from app.services.menu_service import generate_pdf_if_needed, get_pdf_path, get_status

router = APIRouter(prefix="", tags=["menu"])


@router.get("/menu")
async def get_menu_pdf():
    _, _ = await generate_pdf_if_needed()
    pdf = get_pdf_path()
    if not pdf.exists():
        raise HTTPException(500, "Menu PDF not available")
    return FileResponse(str(pdf), media_type="application/pdf", filename="menu.pdf")


@router.get("/menu/status")
def menu_status():
    return JSONResponse(get_status())

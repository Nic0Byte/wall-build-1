"""
Routes Frontend per Wall-Build
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from utils.config import BLOCK_WIDTHS, BLOCK_HEIGHT

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/")
async def serve_frontend(request: Request):
    """
    Dashboard principale - la verifica di autenticazione viene gestita dal JavaScript frontend.
    Il token è memorizzato nel localStorage del browser e non è accessibile lato server.
    """
    try:
        return FileResponse("templates/index.html")
    except Exception as e:
        print(f"❌ Errore servendo dashboard: {e}")
        return RedirectResponse(url="/login", status_code=302)

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Pagina di login del sistema."""
    return templates.TemplateResponse("login.html", {"request": request})

@router.get("/progetti", response_class=HTMLResponse)
async def progetti_page(request: Request):
    """Pagina progetti - richiede autenticazione lato client."""
    try:
        return templates.TemplateResponse("progetti.html", {"request": request})
    except Exception as e:
        print(f"❌ Errore servendo pagina progetti: {e}")
        return RedirectResponse(url="/login", status_code=302)

@router.get("/upload", response_class=HTMLResponse)
async def upload_page(request: Request):
    """Pagina upload - richiede autenticazione lato client."""
    try:
        return templates.TemplateResponse("base_protected.html", {
            "request": request,
            "title": "Upload File"
        })
    except Exception as e:
        print(f"❌ Errore servendo pagina upload: {e}")
        return RedirectResponse(url="/login", status_code=302)

@router.get("/health")
async def health():
    """Health check pubblico."""
    import datetime
    return {
        "status": "ok", 
        "timestamp": datetime.datetime.now(),
        "auth_system": "active",
        "version": "1.0.0"
    }

@router.get("/api/config/blocks")
async def get_blocks_config():
    """Restituisce la configurazione dinamica dei blocchi."""
    return JSONResponse({
        "block_widths": BLOCK_WIDTHS,
        "block_height": BLOCK_HEIGHT,
        "block_widths_string": ",".join(map(str, BLOCK_WIDTHS))
    })
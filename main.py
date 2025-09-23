import io
import os
import json
import math
import xml.etree.ElementTree as ET
import re
import datetime
import tempfile
import uuid
import base64
from typing import List, Tuple, Dict, Optional, Union
from collections import defaultdict

from shapely.geometry import Polygon, MultiPolygon, LinearRing, box, mapping, shape
from shapely.ops import unary_union
from shapely.validation import explain_validity

# Optional deps (guarded)
try:
    import svgpathtools  # type: ignore
except Exception:  # pragma: no cover
    svgpathtools = None

# Optional plotting
try:
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend
except Exception:  # pragma: no cover
    plt = None
    patches = None

# Local imports
from parsers import parse_dwg_wall, parse_svg_wall, parse_wall_file
from utils.file_manager import setup_output_directories, get_organized_output_path, generate_unique_filename
from exporters.json_exporter import export_to_json
from exporters.pdf_exporter import export_to_pdf, REPORTLAB_AVAILABLE as reportlab_available
from exporters.labels import create_block_labels, create_detailed_block_labels
from exporters.dxf_exporter import (
    export_to_dxf,
    pack_wall,
    opt_pass,
    summarize_blocks as summarize_blocks_helper,
    EZDXF_AVAILABLE as ezdxf_available,
)
from utils.geometry_utils import snap, snap_bounds, polygon_holes, sanitize_polygon, ensure_multipolygon, SNAP_MM
from utils.config import (
    SCARTO_CUSTOM_MM, AREA_EPS, COORD_EPS, DISPLAY_MM_PER_M,
    MICRO_REST_MM, KEEP_OUT_MM, SPLIT_MAX_WIDTH_MM,
    BLOCK_HEIGHT, BLOCK_WIDTHS, SIZE_TO_LETTER, BLOCK_ORDERS, SESSIONS,
    get_block_schema_from_frontend, get_default_block_schema  # NEW: Block customization functions
)

# Alias dalle utility di export
summarize_blocks = summarize_blocks_helper


def generate_preview_image(
    wall_polygon: Polygon,
    placed: List[Dict],
    customs: List[Dict],
    apertures: Optional[List[Polygon]] = None,
    color_theme: Optional[Dict] = None,
    block_config: Optional[Dict] = None,
    width: int = 800,
    height: int = 600,
) -> str:
    """Genera immagine preview come stringa base64."""
    if not plt or not patches:
        return ""

    color_theme = color_theme or {}

    if block_config:
        size_to_letter = block_config.get("size_to_letter", {})
        print(
            "[DEBUG] Preview block config:",
            block_config.get("block_widths", "N/A"),
            block_config.get("block_height", "N/A"),
        )
    else:
        size_to_letter = {}
        print("[WARN] Preview using default block config")

    wall_color = color_theme.get("wallOutlineColor", "#1E40AF")
    wall_line_width = color_theme.get("wallLineWidth", 2)
    standard_block_color = color_theme.get("standardBlockColor", "#E5E7EB")
    standard_block_border = color_theme.get("standardBlockBorder", "#374151")
    custom_piece_color = color_theme.get("customPieceColor", "#F3E8FF")
    custom_piece_border = color_theme.get("customPieceBorder", "#7C3AED")
    door_window_color = color_theme.get("doorWindowColor", "#FEE2E2")
    door_window_border = color_theme.get("doorWindowBorder", "#DC2626")

    print(f"[DEBUG] Preview colors: wall={wall_color}, blocks={standard_block_color}")

    try:
        fig, ax = plt.subplots(figsize=(width / 100, height / 100), dpi=100)
        ax.set_aspect("equal")

        minx, miny, maxx, maxy = wall_polygon.bounds
        margin = max((maxx - minx), (maxy - miny)) * 0.05
        ax.set_xlim(minx - margin, maxx + margin)
        ax.set_ylim(miny - margin, maxy + margin)

        x, y = wall_polygon.exterior.xy
        ax.plot(x, y, color=wall_color, linewidth=wall_line_width, label="Parete")

        if block_config and size_to_letter:
            detailed_std_labels, detailed_custom_labels = create_detailed_block_labels(
                placed,
                customs,
                size_to_letter,
            )
            print(f"[DEBUG] Preview using custom size_to_letter: {size_to_letter}")
        else:
            detailed_std_labels, detailed_custom_labels = create_detailed_block_labels(placed, customs)
            print("[DEBUG] Preview using default size_to_letter mapping")

        for i, blk in enumerate(placed):
            rect = patches.Rectangle(
                (blk["x"], blk["y"]),
                blk["width"],
                blk["height"],
                facecolor=standard_block_color,
                edgecolor=standard_block_border,
                linewidth=0.5,
            )
            ax.add_patch(rect)

            label_info = detailed_std_labels.get(i)
            if not label_info:
                continue

            bl_x = blk["x"] + blk["width"] * 0.1
            bl_y = blk["y"] + blk["height"] * 0.2
            tr_x = blk["x"] + blk["width"] * 0.9
            tr_y = blk["y"] + blk["height"] * 0.8

            category = label_info["display"]["bottom_left"]
            number = label_info["display"]["top_right"]

            fontsize_cat = min(12, max(6, blk["width"] / 150))
            ax.text(
                bl_x,
                bl_y,
                category,
                ha="left",
                va="bottom",
                fontsize=fontsize_cat,
                fontweight="bold",
                color="#dc2626",
            )

            fontsize_num = min(10, max(4, blk["width"] / 200))
            ax.text(
                tr_x,
                tr_y,
                number,
                ha="right",
                va="top",
                fontsize=fontsize_num,
                fontweight="normal",
                color="#2563eb",
            )

        for i, cust in enumerate(customs):
            try:
                poly = shape(cust["geometry"])
            except Exception:
                continue

            patch = patches.Polygon(
                list(poly.exterior.coords),
                facecolor=custom_piece_color,
                edgecolor=custom_piece_border,
                linewidth=0.8,
                hatch="//",
                alpha=0.8,
            )
            ax.add_patch(patch)

            label_info = detailed_custom_labels.get(i)
            if not label_info:
                continue

            bl_x = cust["x"] + cust["width"] * 0.1
            bl_y = cust["y"] + cust["height"] * 0.2
            tr_x = cust["x"] + cust["width"] * 0.9
            tr_y = cust["y"] + cust["height"] * 0.8

            category = label_info["display"]["bottom_left"]
            number = label_info["display"]["top_right"]

            fontsize_cat = min(10, max(5, cust["width"] / 120))
            ax.text(
                bl_x,
                bl_y,
                category,
                ha="left",
                va="bottom",
                fontsize=fontsize_cat,
                fontweight="bold",
                color="#16a34a",
            )

            fontsize_num = min(8, max(4, cust["width"] / 150))
            ax.text(
                tr_x,
                tr_y,
                number,
                ha="right",
                va="top",
                fontsize=fontsize_num,
                fontweight="normal",
                color="#065f46",
            )

        if apertures:
            for ap in apertures:
                x, y = ap.exterior.xy
                ax.plot(x, y, color=door_window_border, linestyle="--", linewidth=2)
                ax.fill(x, y, color=door_window_color, alpha=0.15)

        ax.set_title("Preview Costruzione Parete", fontsize=12, fontweight="bold", color="#1f2937")
        ax.grid(True, alpha=0.3, color="#9ca3af")
        ax.tick_params(axis="both", which="major", labelsize=8, colors="#6b7280")

        img_buffer = io.BytesIO()
        fig.savefig(
            img_buffer,
            format="png",
            dpi=100,
            bbox_inches="tight",
            facecolor="white",
            edgecolor="none",
            pad_inches=0.1,
        )
        img_buffer.seek(0)
        plt.close(fig)

        encoded = base64.b64encode(img_buffer.getvalue()).decode("utf-8")
        return f"data:image/png;base64,{encoded}"

    except Exception as exc:
        print(f"[WARN] Errore generazione preview: {exc}")
        return ""
# NEW: Enhanced packing with automatic measurements
try:
    from core.enhanced_packing import (
        EnhancedPackingCalculator,
        enhance_packing_with_automatic_measurements,
        calculate_automatic_project_parameters
    )
    ENHANCED_PACKING_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Enhanced packing non disponibile: {e}")
    EnhancedPackingCalculator = None
    enhance_packing_with_automatic_measurements = None
    calculate_automatic_project_parameters = None
    ENHANCED_PACKING_AVAILABLE = False

# Optional dependencies
# ────────────────────────────────────────────────────────────────────────────────

# Alternative DWG parser
try:
    import dxfgrabber
    dxfgrabber_available = True
    print("[OK] dxfgrabber caricato - Supporto DWG avanzato disponibile")
except ImportError:
    dxfgrabber_available = False
    print("[WARNING] dxfgrabber non installato. Parser DWG avanzato non disponibile.")

# ---- FastAPI (kept in same file as requested) ----
try:
    from fastapi import FastAPI, UploadFile, File, Form, HTTPException, WebSocket, WebSocketDisconnect, Request, Response, Depends
    from fastapi.responses import JSONResponse, FileResponse, StreamingResponse, HTMLResponse, RedirectResponse
    from fastapi.staticfiles import StaticFiles
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.templating import Jinja2Templates
    from pydantic import BaseModel
    import uvicorn
    
    # Import sistema di autenticazione
    from api.routes import router as auth_router
    from api.auth import get_current_active_user
    from database.services import cleanup_expired_sessions
    from api.models import User
except Exception:  # pragma: no cover
    FastAPI = None  # type: ignore

# ────────────────────────────────────────────────────────────────────────────────
# Pydantic Models per API
# ────────────────────────────────────────────────────────────────────────────────
class PackingConfig(BaseModel):
    block_widths: List[int] = BLOCK_WIDTHS
    block_height: int = BLOCK_HEIGHT
    row_offset: Optional[int] = 826
    snap_mm: float = SNAP_MM
    keep_out_mm: float = KEEP_OUT_MM

class PackingResult(BaseModel):
    session_id: str
    status: str
    wall_bounds: List[float]
    blocks_standard: List[Dict]
    blocks_custom: List[Dict]
    apertures: List[Dict]
    summary: Dict
    config: Dict
    metrics: Dict
    saved_file_path: Optional[str] = None  # Path to saved project file
    # NEW: Enhanced measurements
    automatic_measurements: Optional[Dict] = None
    production_parameters: Optional[Dict] = None

class EnhancedPackingConfig(BaseModel):
    """Configurazione estesa con parametri automatici misure"""
    # Parametri standard
    block_widths: List[int] = BLOCK_WIDTHS
    block_height: int = BLOCK_HEIGHT
    row_offset: Optional[int] = 826
    snap_mm: float = SNAP_MM
    keep_out_mm: float = KEEP_OUT_MM
    
    # NEW: Parametri materiali automatici
    material_thickness_mm: Optional[int] = 18
    guide_width_mm: Optional[int] = 75
    guide_type: Optional[str] = "75mm"
    
    # NEW: Parametri parete
    wall_position: Optional[str] = "new"  # "new", "attached"
    is_attached_to_existing: Optional[bool] = False
    ceiling_height_mm: Optional[int] = 2700
    
    # NEW: Parametri avanzati
    enable_automatic_calculations: bool = True
    enable_moretti_calculation: bool = True
    enable_cost_estimation: bool = True

def build_run_params(row_offset: Optional[int] = None) -> Dict:
    """Raccoglie i parametri di run da serializzare nel JSON."""
    return {
        "block_widths_mm": BLOCK_WIDTHS,
        "block_height_mm": BLOCK_HEIGHT,
        "row_offset_mm": int(row_offset) if row_offset is not None else None,
        "snap_mm": SNAP_MM,
        "keep_out_mm": KEEP_OUT_MM,
        "split_max_width_mm": SPLIT_MAX_WIDTH_MM,
        "scarto_custom_mm": SCARTO_CUSTOM_MM,
        "row_aware_merge": True,
        "orders_tried": BLOCK_ORDERS,
    }

# ────────────────────────────────────────────────────────────────────────────────
# DWG parsing (IMPLEMENTAZIONE COMPLETA)
# ────────────────────────────────────────────────────────────────────────────────
# Parsing DWG/SVG delegato ai moduli parsers (vedi parsers/).
# Calculate metrics
# ────────────────────────────────────────────────────────────────────────────────
def calculate_metrics(placed: List[Dict], customs: List[Dict], wall_area: float) -> Dict:
    """Calcola metriche di qualità del packing."""
    total_blocks = len(placed) + len(customs)
    if total_blocks == 0:
        return {"efficiency": 0, "waste_ratio": 0, "complexity": 0}
    
    standard_area = sum(p["width"] * p["height"] for p in placed)
    custom_area = sum(c["width"] * c["height"] for c in customs)
    
    return {
        "efficiency": len(placed) / total_blocks if total_blocks > 0 else 0,
        "waste_ratio": custom_area / wall_area if wall_area > 0 else 0,
        "complexity": len([c for c in customs if c.get("ctype") == 2]),
        "total_area_coverage": (standard_area + custom_area) / wall_area if wall_area > 0 else 0
    }

# ────────────────────────────────────────────────────────────────────────────────
# FastAPI – Sistema con Autenticazione Sicura
# ────────────────────────────────────────────────────────────────────────────────
app = None
templates = None

if FastAPI:
    # Configurazione FastAPI con sicurezza
    app = FastAPI(
        title="Parete TAKTAK® - Sistema Professionale",
        description="Sistema sicuro per progettazione pareti con autenticazione avanzata",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc"
    )
    
    # Setup templates
    templates = Jinja2Templates(directory="templates")
    
    # CORS middleware per consentire richieste dal frontend
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # In produzione specificare domini
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include authentication routes
    app.include_router(auth_router, prefix="/api/v1")
    
    # Cleanup sessioni scadute all'avvio
    try:
        expired_cleaned = cleanup_expired_sessions()
        print(f"🧹 Pulizia iniziale: {expired_cleaned} sessioni scadute rimosse")
    except Exception as e:
        print(f"⚠️ Errore pulizia sessioni: {e}")
    
    # ===== FRONTEND STATIC FILES =====
    
    @app.get("/")
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
    
    @app.get("/login", response_class=HTMLResponse)
    async def login_page(request: Request):
        """Pagina di login del sistema."""
        return templates.TemplateResponse("login.html", {"request": request})
    
    # ===== PAGINE PROTETTE =====
    
    @app.get("/progetti", response_class=HTMLResponse)
    async def progetti_page(request: Request):
        """Pagina progetti - richiede autenticazione lato client."""
        try:
            return templates.TemplateResponse("progetti.html", {"request": request})
        except Exception as e:
            print(f"❌ Errore servendo pagina progetti: {e}")
            return RedirectResponse(url="/login", status_code=302)
    
    @app.get("/upload", response_class=HTMLResponse)
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
    
    # Mount static files - solo se la directory esiste
    import os
    if os.path.exists("static"):
        app.mount("/static", StaticFiles(directory="static"), name="static")
    
    # ===== HEALTH CHECK =====
    
    @app.get("/health")
    async def health():
        """Health check pubblico."""
        return {
            "status": "ok", 
            "timestamp": datetime.datetime.now(),
            "auth_system": "active",
            "version": "1.0.0"
        }
    
    # ===== PROJECT FILE MANAGEMENT =====
    
    async def save_project_file(file: UploadFile, session_id: str, user_id: int) -> str:
        """
        Salva fisicamente il file caricato per permettere il riutilizzo futuro.
        """
        import os
        import shutil
        from pathlib import Path
        
        # Crea directory per i progetti salvati
        base_dir = Path("output/saved_projects")
        user_dir = base_dir / f"user_{user_id}"
        user_dir.mkdir(parents=True, exist_ok=True)
        
        # Nome file con session_id per unicità
        file_extension = Path(file.filename).suffix
        saved_filename = f"{session_id}_{file.filename}"
        saved_path = user_dir / saved_filename
        
        # Reset del file pointer
        await file.seek(0)
        
        # Salva il file
        with open(saved_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        print(f"💾 File salvato: {saved_path}")
        return str(saved_path)
    
    def get_saved_project_file_path(project_id: int, user_id: int, filename: str) -> Optional[str]:
        """
        Recupera il percorso del file salvato per un progetto specifico.
        """
        from pathlib import Path
        from database.models import SavedProject
        from database.config import get_db_session
        
        try:
            with get_db_session() as db:
                project = db.query(SavedProject)\
                           .filter(SavedProject.id == project_id)\
                           .filter(SavedProject.user_id == user_id)\
                           .filter(SavedProject.is_active == True)\
                           .first()
                
                if project and project.file_path:
                    file_path = Path(project.file_path)
                    if file_path.exists():
                        return str(file_path)
                    else:
                        print(f"⚠️ File del progetto non trovato: {file_path}")
                        return None
                        
        except Exception as e:
            print(f"❌ Errore nel recupero file progetto: {e}")
            return None
        
        return None
    
    # ===== WEB UI API ENDPOINTS PROTETTI =====
    
    @app.post("/api/upload", response_model=PackingResult, dependencies=[Depends(get_current_active_user)])
    async def upload_and_process(
        file: UploadFile = File(...),
        row_offset: int = Form(826),
        block_widths: str = Form("1239,826,413"),
        project_name: str = Form("Progetto Parete"),
        color_theme: str = Form("{}"),
        block_dimensions: str = Form("{}"),  # NEW: Block dimensions from frontend
        current_user: User = Depends(get_current_active_user)
    ):
        """
        Upload SVG/DWG e processamento completo con preview - PROTETTO DA AUTENTICAZIONE.
        """
        try:
            # Log dell'attività dell'utente
            print(f"📁 File '{file.filename}' caricato da utente: {current_user.username}")
            
            # Validazione file
            file_ext = file.filename.lower().split('.')[-1] if '.' in file.filename else ''
            supported_formats = ['svg', 'dwg', 'dxf']
            
            if file_ext not in supported_formats:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Formato file non supportato. Formati accettati: {', '.join(supported_formats).upper()}"
                )
            
            if file.size and file.size > 10 * 1024 * 1024:  # 10MB limit
                raise HTTPException(status_code=400, detail="File troppo grande (max 10MB)")
            
            # Lettura file
            file_bytes = await file.read()
            if not file_bytes:
                raise HTTPException(status_code=400, detail="File vuoto")
            
            # Parse parametri blocchi (backward compatibility)
            try:
                widths = [int(w.strip()) for w in block_widths.split(',') if w.strip()]
                if not widths:
                    widths = BLOCK_WIDTHS
            except ValueError:
                widths = BLOCK_WIDTHS
            
            # 🔧 NEW: Parse dimensioni blocchi personalizzate (implementazione della tua idea!)
            try:
                import json
                block_config = json.loads(block_dimensions) if block_dimensions else {}
                print(f"📦 [DEBUG] Block dimensions received: {block_config}")
                
                # Determina schema blocchi da usare (standard vs custom)
                block_schema = get_block_schema_from_frontend(block_config)
                
                # Estrai dimensioni effettive da usare
                final_widths = block_schema["block_widths"]
                final_height = block_schema["block_height"]
                final_size_to_letter = block_schema["size_to_letter"]
                
                print(f"🎯 Schema blocchi scelto: {block_schema['schema_type']}")
                print(f"   📏 Dimensioni: {final_widths}×{final_height}")
                print(f"   🔤 Mappatura: {final_size_to_letter}")
                
            except (ValueError, json.JSONDecodeError):
                print("⚠️ Block dimensions parsing failed, using defaults")
                block_schema = get_default_block_schema()
                final_widths = BLOCK_WIDTHS
                final_height = BLOCK_HEIGHT
                final_size_to_letter = SIZE_TO_LETTER
            
            # Parse tema colori
            try:
                color_config = json.loads(color_theme) if color_theme else {}
                print(f"🎨 [DEBUG] Color theme received: {color_config}")
            except (ValueError, json.JSONDecodeError):
                color_config = {}
                print("⚠️ Color theme parsing failed, using defaults")
            
            # Parse file (SVG o DWG)
            wall, apertures = parse_wall_file(file_bytes, file.filename)
            
            # Packing con dimensioni personalizzate
            placed, custom = pack_wall(
                wall, 
                final_widths,  # 🔧 USA LE DIMENSIONI PERSONALIZZATE!
                final_height,  # 🔧 USA L'ALTEZZA PERSONALIZZATA!
                row_offset=row_offset,
                apertures=apertures if apertures else None
            )
            
            # Ottimizzazione
            placed, custom = opt_pass(placed, custom, final_widths)  # 🔧 ANCHE QUI!
            
            # Calcola metriche
            summary = summarize_blocks(placed, final_size_to_letter)  # 🔧 Passa mapping personalizzato
            metrics = calculate_metrics(placed, custom, wall.area)
            
            # Genera session ID
            session_id = str(uuid.uuid4())
            
            # Salva in sessione (con info utente e file bytes per salvare dopo)
            SESSIONS[session_id] = {
                "wall_polygon": wall,
                "apertures": apertures,
                "placed": placed,
                "customs": custom,
                "summary": summary,
                "config": {
                    "block_widths": final_widths,  # 🔧 USA DIMENSIONI PERSONALIZZATE
                    "block_height": final_height,  # 🔧 USA ALTEZZA PERSONALIZZATA  
                    "size_to_letter": final_size_to_letter,  # 🔧 USA MAPPATURA PERSONALIZZATA
                    "block_schema": block_schema,  # 🔧 SALVA SCHEMA COMPLETO
                    "row_offset": row_offset,
                    "project_name": project_name,
                    "color_theme": color_config
                },
                "metrics": metrics,
                "timestamp": datetime.datetime.now(),
                "user_id": current_user.id,
                "username": current_user.username,
                "original_filename": file.filename,
                "file_bytes": file_bytes  # Store file bytes for later saving
            }
            
            # Formatta response
            minx, miny, maxx, maxy = wall.bounds
            
            return PackingResult(
                session_id=session_id,
                status="success",
                wall_bounds=[minx, miny, maxx, maxy],
                blocks_standard=[
                    {
                        "id": i,
                        "x": float(p["x"]),
                        "y": float(p["y"]),
                        "width": float(p["width"]),
                        "height": float(p["height"]),
                        "type": p["type"]
                    }
                    for i, p in enumerate(placed)
                ],
                blocks_custom=[
                    {
                        "id": i,
                        "x": float(c["x"]),
                        "y": float(c["y"]),
                        "width": float(c["width"]),
                        "height": float(c["height"]),
                        "type": c["type"],
                        "ctype": c.get("ctype", 2),
                        "geometry": c["geometry"]
                    }
                    for i, c in enumerate(custom)
                ],
                apertures=[
                    {
                        "bounds": list(ap.bounds)
                    }
                    for ap in (apertures or [])
                ],
                summary=summary,
                config={
                    "block_widths": final_widths,  # 🔧 Dimensioni personalizzate
                    "block_height": final_height,  # 🔧 Altezza personalizzata
                    "size_to_letter": final_size_to_letter,  # 🔧 Mappatura personalizzata
                    "block_schema": block_schema,  # 🔧 Schema completo
                    "row_offset": row_offset,
                    "project_name": project_name
                },
                metrics=metrics,
                saved_file_path=None  # Will be set when project is actually saved
            )
            
        except Exception as e:
            print(f"❌ Errore upload: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/api/reconfigure")
    async def reconfigure_packing(
        session_id: str = Form(...),
        row_offset: int = Form(826),
        block_widths: str = Form("1239,826,413"),
        block_dimensions: str = Form("{}")  # NEW: Block dimensions for reconfigure
    ):
        """
        Riconfigurazione parametri su sessione esistente.
        """
        try:
            if session_id not in SESSIONS:
                raise HTTPException(status_code=404, detail="Sessione non trovata")
            
            session = SESSIONS[session_id]
            
            # Parse parametri blocchi (backward compatibility)
            try:
                widths = [int(w.strip()) for w in block_widths.split(',') if w.strip()]
                if not widths:
                    widths = BLOCK_WIDTHS
            except ValueError:
                widths = BLOCK_WIDTHS
            
            # 🔧 NEW: Parse dimensioni blocchi personalizzate per riconfigurazione
            try:
                import json
                block_config = json.loads(block_dimensions) if block_dimensions else {}
                print(f"📦 [RECONFIG] Block dimensions received: {block_config}")
                
                # Determina schema blocchi da usare (standard vs custom)
                block_schema = get_block_schema_from_frontend(block_config)
                
                # Estrai dimensioni effettive da usare
                final_widths = block_schema["block_widths"]
                final_height = block_schema["block_height"]
                final_size_to_letter = block_schema["size_to_letter"]
                
                print(f"🎯 [RECONFIG] Schema blocchi scelto: {block_schema['schema_type']}")
                print(f"   📏 Dimensioni: {final_widths}×{final_height}")
                
            except (ValueError, json.JSONDecodeError):
                print("⚠️ [RECONFIG] Block dimensions parsing failed, using defaults")
                block_schema = get_default_block_schema()
                final_widths = BLOCK_WIDTHS
                final_height = BLOCK_HEIGHT
                final_size_to_letter = SIZE_TO_LETTER
            
            # Re-packing con dimensioni personalizzate
            wall = session["wall_polygon"]
            apertures = session["apertures"]
            
            placed, custom = pack_wall(
                wall, 
                final_widths,  # 🔧 USA DIMENSIONI PERSONALIZZATE!
                final_height,  # 🔧 USA ALTEZZA PERSONALIZZATA!
                row_offset=row_offset,
                apertures=apertures if apertures else None
            )
            
            placed, custom = opt_pass(placed, custom, final_widths)  # 🔧 ANCHE QUI!
            
            # Aggiorna sessione con dimensioni personalizzate
            summary = summarize_blocks(placed, final_size_to_letter)  # 🔧 Passa mapping personalizzato
            metrics = calculate_metrics(placed, custom, wall.area)
            
            session.update({
                "placed": placed,
                "customs": custom,
                "summary": summary,
                "metrics": metrics,
                "config": {
                    **session["config"],
                    "block_widths": final_widths,  # 🔧 USA DIMENSIONI PERSONALIZZATE
                    "block_height": final_height,  # 🔧 USA ALTEZZA PERSONALIZZATA
                    "size_to_letter": final_size_to_letter,  # 🔧 USA MAPPATURA PERSONALIZZATA
                    "block_schema": block_schema,  # 🔧 SALVA SCHEMA COMPLETO
                    "row_offset": row_offset
                }
            })
            
            return {"status": "success", "session_id": session_id}
            
        except Exception as e:
            print(f"❌ Errore reconfig: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/preview/{session_id}")
    async def get_preview_image(session_id: str):
        """
        Genera immagine preview per sessione.
        """
        try:
            if session_id not in SESSIONS:
                raise HTTPException(status_code=404, detail="Sessione non trovata")
            
            session = SESSIONS[session_id]
            
            # Genera preview
            preview_base64 = generate_preview_image(
                session["wall_polygon"],
                session["placed"],
                session["customs"],
                session["apertures"],
                session["config"].get("color_theme", {}),
                session["config"]  # 🔧 Passa la configurazione blocchi personalizzati
            )
            
            if not preview_base64:
                raise HTTPException(status_code=500, detail="Errore generazione preview")
            
            return {"image": preview_base64}
            
        except Exception as e:
            print(f"❌ Errore preview: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/download/{session_id}/{format}")
    async def download_result(session_id: str, format: str):
        """
        Download risultati in vari formati.
        """
        try:
            if session_id not in SESSIONS:
                raise HTTPException(status_code=404, detail="Sessione non trovata")
            
            session = SESSIONS[session_id]
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            
            if format.lower() == "json":
                # Export JSON
                filename = f"distinta_{session_id[:8]}_{timestamp}.json"
                json_path = export_to_json(
                    session["summary"],
                    session["customs"],
                    session["placed"],
                    out_path=filename,
                    params=build_run_params(session["config"]["row_offset"]),
                    block_config=session["config"]  # 🔧 Passa la configurazione blocchi personalizzati
                )
                
                return FileResponse(
                    json_path,
                    media_type="application/json",
                    filename=filename
                )
                
            elif format.lower() == "pdf":
                # Export PDF
                if not reportlab_available:
                    raise HTTPException(status_code=501, detail="Export PDF non disponibile")
                
                filename = f"report_{session_id[:8]}_{timestamp}.pdf"
                pdf_path = export_to_pdf(
                    session["summary"],
                    session["customs"],
                    session["placed"],
                    session["wall_polygon"],
                    session["apertures"],
                    project_name=session["config"]["project_name"],
                    out_path=filename,
                    params=build_run_params(session["config"]["row_offset"]),
                    block_config=session["config"]  # 🔧 Passa la configurazione blocchi personalizzati
                )
                
                return FileResponse(
                    pdf_path,
                    media_type="application/pdf",
                    filename=filename
                )
                
            elif format.lower() == "dxf":
                # Export DXF
                if not ezdxf_available:
                    raise HTTPException(status_code=501, detail="Export DXF non disponibile")
                
                filename = f"schema_{session_id[:8]}_{timestamp}.dxf"
                dxf_path = export_to_dxf(
                    session["summary"],
                    session["customs"],
                    session["placed"],
                    session["wall_polygon"],
                    session["apertures"],
                    project_name=session["config"]["project_name"],
                    out_path=filename,
                    params=build_run_params(session["config"]["row_offset"]),
                    color_theme=session["config"].get("color_theme", {}),
                    block_config=session["config"]  # 🔧 Passa la configurazione blocchi personalizzati
                )
                
                return FileResponse(
                    dxf_path,
                    media_type="application/dxf",
                    filename=filename
                )
                
            else:
                raise HTTPException(status_code=400, detail="Formato non supportato")
                
        except Exception as e:
            print(f"❌ Errore download: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/session/{session_id}")
    async def get_session_info(session_id: str):
        """
        Ottieni informazioni sessione.
        """
        try:
            if session_id not in SESSIONS:
                raise HTTPException(status_code=404, detail="Sessione non trovata")
            
            session = SESSIONS[session_id]
            wall = session["wall_polygon"]
            minx, miny, maxx, maxy = wall.bounds
            
            return {
                "session_id": session_id,
                "wall_bounds": [minx, miny, maxx, maxy],
                "summary": session["summary"],
                "custom_count": len(session["customs"]),
                "metrics": session["metrics"],
                "config": session["config"],
                "timestamp": session["timestamp"]
            }
            
        except Exception as e:
            print(f"❌ Errore session info: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # ===== BACKWARD COMPATIBILITY - API ORIGINALI =====
    
    @app.post("/pack")
    async def pack_from_json(payload: Dict):
        """
        Body JSON atteso:
        {
          "polygon": [[x,y], ...],
          "apertures": [ [[...]], [[...]] ],
          "block_widths": [1239,826,413],      # opzionale
          "block_height": 495,                 # opzionale
          "row_offset": 826                    # opzionale
        }
        """
        try:
            poly = Polygon(payload["polygon"])
            poly = sanitize_polygon(poly)

            apertures = []
            for ap in payload.get("apertures", []):
                apertures.append(Polygon(ap))

            widths = payload.get("block_widths", BLOCK_WIDTHS)
            height = int(payload.get("block_height", BLOCK_HEIGHT))
            row_offset = payload.get("row_offset", 826)

            placed, custom = pack_wall(poly, widths, height, row_offset=row_offset,
                                       apertures=apertures if apertures else None)
            placed, custom = opt_pass(placed, custom, widths)

            summary = summarize_blocks(placed)
            out_path = export_to_json(summary, custom, placed, out_path="distinta_wall.json", params=build_run_params(row_offset=row_offset))

            return JSONResponse({
                "summary": summary,
                "custom_count": len(custom),
                "json_path": out_path
            })
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=400)

    @app.post("/upload-file")
    async def pack_from_file(file: UploadFile = File(...),
                            row_offset: int = Form(826)):
        """
        Carica un file CAD (SVG/DWG/DXF) e calcola il packing.
        """
        try:
            # Validazione formato
            file_ext = file.filename.lower().split('.')[-1] if '.' in file.filename else ''
            supported_formats = ['svg', 'dwg', 'dxf']
            
            if file_ext not in supported_formats:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Formato non supportato. Formati accettati: {', '.join(supported_formats.upper())}"
                )
            
            file_bytes = await file.read()
            wall, apertures = parse_wall_file(file_bytes, file.filename)
            widths = BLOCK_WIDTHS
            height = BLOCK_HEIGHT

            placed, custom = pack_wall(wall, widths, height, row_offset=row_offset,
                                       apertures=apertures if apertures else None)
            placed, custom = opt_pass(placed, custom, widths)
            summary = summarize_blocks(placed)
            out_path = export_to_json(summary, custom, placed, out_path="distinta_wall.json", params=build_run_params(row_offset=row_offset))
            return JSONResponse({"summary": summary, "custom_count": len(custom), "json_path": out_path})
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=400)

    @app.post("/upload-svg")
    async def pack_from_svg(file: UploadFile = File(...),
                            row_offset: int = Form(826)):
        """
        Carica un SVG (schema tuo) e calcola il packing.
        DEPRECATED: Usa /upload-file per supporto multi-formato.
        """
        try:
            svg_bytes = await file.read()
            wall, apertures = parse_svg_wall(svg_bytes)
            widths = BLOCK_WIDTHS
            height = BLOCK_HEIGHT

            placed, custom = pack_wall(wall, widths, height, row_offset=row_offset,
                                       apertures=apertures if apertures else None)
            placed, custom = opt_pass(placed, custom, widths)
            summary = summarize_blocks(placed)
            out_path = export_to_json(summary, custom, placed, out_path="distinta_wall.json", params=build_run_params(row_offset=row_offset))
            return JSONResponse({"summary": summary, "custom_count": len(custom), "json_path": out_path})
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=400)

# ────────────────────────────────────────────────────────────────────────────────
# Enhanced Packing Endpoints (NEW)
# ────────────────────────────────────────────────────────────────────────────────

    @app.post("/pack-enhanced")
    async def pack_with_automatic_measurements(payload: Dict, current_user: User = Depends(get_current_active_user)):
        """
        Packing potenziato con calcolo automatico delle misure.
        Implementa la logica del documento: materiale + guide = chiusura.
        """
        try:
            # Estrai geometria parete
            poly = Polygon(payload["polygon"])
            poly = sanitize_polygon(poly)

            apertures = []
            for ap in payload.get("apertures", []):
                apertures.append(Polygon(ap))

            # Parametri packing standard
            widths = payload.get("block_widths", BLOCK_WIDTHS)
            height = int(payload.get("block_height", BLOCK_HEIGHT))
            row_offset = payload.get("row_offset", 826)

            # Configurazione materiali e calcoli automatici
            material_config = payload.get("material_config", {})
            enable_enhanced = material_config.get("enable_automatic_calculations", True)

            # Esegui packing standard
            placed, custom = pack_wall(poly, widths, height, row_offset=row_offset,
                                     apertures=apertures if apertures else None)
            placed, custom = opt_pass(placed, custom, widths)
            summary = summarize_blocks(placed)

            # Prepara risultato base
            session_id = str(uuid.uuid4())
            wall_bounds = list(poly.bounds)
            
            result = {
                "session_id": session_id,
                "status": "success", 
                "wall_bounds": wall_bounds,
                "blocks_standard": placed,
                "blocks_custom": custom,
                "apertures": [{"bounds": list(ap.bounds)} for ap in apertures],
                "summary": summary,
                "config": {
                    "block_widths": widths,
                    "block_height": height,
                    "row_offset": row_offset,
                    "material_config": material_config
                },
                "metrics": {
                    "total_blocks": len(placed) + len(custom),
                    "wall_area_m2": poly.area / 1_000_000,
                    "coverage_percent": _calculate_coverage_percentage(poly, placed, custom)
                }
            }

            # NUOVO: Aggiungi calcoli automatici se abilitati e disponibili
            if enable_enhanced and ENHANCED_PACKING_AVAILABLE:
                try:
                    print("🧮 Calcolo automatico misure in corso...")
                    enhanced_result = enhance_packing_with_automatic_measurements(result, material_config)
                    
                    # Aggiungi parametri automatici al risultato
                    result.update(enhanced_result)
                    
                    print(f"✅ Spessore chiusura calcolato: {enhanced_result.get('automatic_measurements', {}).get('closure_calculation', {}).get('closure_thickness_mm', 'N/A')}mm")
                    
                except Exception as e:
                    print(f"⚠️ Errore calcoli automatici: {e}")
                    result["automatic_measurements_error"] = str(e)

            # Export risultati
            params = build_run_params(row_offset=row_offset)
            if enable_enhanced and "automatic_measurements" in result:
                params.update({
                    "automatic_measurements": result["automatic_measurements"],
                    "enhanced_packing": True
                })

            out_path = export_to_json(summary, custom, placed, out_path="enhanced_packing_result.json", params=params)
            result["saved_file_path"] = out_path

            return JSONResponse(result)
            
        except Exception as e:
            print(f"❌ Errore pack-enhanced: {e}")
            return JSONResponse({"error": str(e)}, status_code=400)

    @app.post("/calculate-measurements")
    async def calculate_automatic_measurements(payload: Dict, current_user: User = Depends(get_current_active_user)):
        """Calcola solo le misure automatiche senza eseguire il packing."""
        try:
            if not ENHANCED_PACKING_AVAILABLE:
                return JSONResponse({"error": "Calcoli automatici non disponibili"}, status_code=503)

            poly = Polygon(payload["polygon"])
            poly = sanitize_polygon(poly) 
            material_config = payload.get("material_config", {})

            result = calculate_automatic_project_parameters(poly, material_config)
            
            return JSONResponse({
                "status": "success",
                "measurements": result,
                "wall_dimensions": {
                    "width_mm": poly.bounds[2] - poly.bounds[0],
                    "height_mm": poly.bounds[3] - poly.bounds[1],
                    "area_m2": poly.area / 1_000_000
                }
            })
            
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=400)

def _calculate_coverage_percentage(wall_polygon: Polygon, standard_blocks: List[Dict], custom_blocks: List[Dict]) -> float:
    """Calcola percentuale di copertura dei blocchi sulla parete."""
    
    try:
        wall_area = wall_polygon.area
        if wall_area == 0:
            return 0.0
        
        total_block_area = 0
        
        for block in standard_blocks + custom_blocks:
            block_width = block.get("width", 0)
            block_height = block.get("height", 0)
            total_block_area += block_width * block_height
        
        coverage = (total_block_area / wall_area) * 100
        return min(100.0, max(0.0, coverage))  # Clamp tra 0 e 100
        
    except Exception:
        return 0.0

# ────────────────────────────────────────────────────────────────────────────────
# CLI demo (mantenuto per test)
# ────────────────────────────────────────────────────────────────────────────────
def _demo():
    print("🚀 Demo Costruttore Pareti a Blocchi")
    print("=" * 50)
    
    # Demo parete trapezoidale con due porte
    wall_exterior = Polygon([(0,0), (12000,0), (12000,4500), (0,2500), (0,0)])
    porta1 = Polygon([(2000,0), (3200,0), (3200,2200), (2000,2200)])
    porta2 = Polygon([(8500,0), (9700,0), (9700,2200), (8500,2200)])

    placed, custom = pack_wall(wall_exterior, BLOCK_WIDTHS, BLOCK_HEIGHT,
                               row_offset=826, apertures=[porta1, porta2])
    summary = summarize_blocks(placed)

    print("🔨 Distinta base blocchi standard:")
    for k, v in summary.items():
        print(f"  • {v} × {k}")
    print(f"\n✂️ Pezzi custom totali: {len(custom)}")

    # Calcola metriche
    metrics = calculate_metrics(placed, custom, wall_exterior.area)
    print(f"\n📊 Metriche:")
    print(f"  • Efficienza: {metrics['efficiency']:.1%}")
    print(f"  • Waste ratio: {metrics['waste_ratio']:.1%}")
    print(f"  • Complessità: {metrics['complexity']} pezzi CU2")

    # Genera nomi file unici con timestamp
    json_filename = generate_unique_filename("distinta_demo", ".json", "trapezoidale")
    pdf_filename = generate_unique_filename("report_demo", ".pdf", "trapezoidale") 
    dxf_filename = generate_unique_filename("schema_demo", ".dxf", "trapezoidale")

    out = export_to_json(summary, custom, placed, out_path=json_filename, params=build_run_params(row_offset=826))
    print(f"📄 JSON scritto in: {out}")

    # Test export PDF
    if reportlab_available:
        try:
            pdf_path = export_to_pdf(summary, custom, placed, wall_exterior, 
                                   apertures=[porta1, porta2],
                                   project_name="Demo Parete Trapezoidale", 
                                   out_path=pdf_filename,
                                   params=build_run_params(row_offset=826))
            print(f"📄 PDF demo generato: {pdf_path}")
        except Exception as e:
            print(f"⚠️ Errore PDF demo: {e}")
    else:
        print("⚠️ ReportLab non disponibile per export PDF")

    # Test export DXF SENZA SOVRAPPOSIZIONI
    if ezdxf_available:
        try:
            dxf_path = export_to_dxf(summary, custom, placed, wall_exterior, 
                                   apertures=[porta1, porta2],
                                   project_name="Demo Parete Trapezoidale", 
                                   out_path=dxf_filename,
                                   params=build_run_params(row_offset=826))
            print(f"📐 DXF demo SENZA SOVRAPPOSIZIONI generato: {dxf_path}")
        except Exception as e:
            print(f"⚠️ Errore DXF demo: {e}")
    else:
        print("⚠️ ezdxf non disponibile per export DXF")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        _demo()
    elif len(sys.argv) > 1 and sys.argv[1] == "server":
        # Avvia server FastAPI
        if app:
            print("🚀 Avvio server Web UI...")
            print("🌐 Apri il browser su: http://localhost:8000")
            print("🛑 Premi Ctrl+C per fermare il server")
            
            # Reload solo se richiesto esplicitamente con --dev
            use_reload = len(sys.argv) > 2 and sys.argv[2] == "--dev"
            if use_reload:
                print("🔧 Modalità sviluppo: auto-reload attivo")
            
            uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=use_reload)
        else:
            print("❌ FastAPI non disponibile")
    else:
        print("Uso: python main.py [demo|server] [--dev]")
        print("  demo     - Esegui demo CLI")
        print("  server   - Avvia server web")
        print("  --dev    - Modalità sviluppo con auto-reload (solo con server)")
        print("\n🧱 MIGLIORAMENTI DXF:")
        print("  ✅ Layout intelligente con DXFLayoutManager")
        print("  ✅ Zone calcolate automaticamente senza sovrapposizioni")
        print("  ✅ Margini adattivi basati su contenuto")
        print("  ✅ Controllo overflow per tabelle e schema taglio")
        print("  ✅ Titoli e sezioni ben separate e leggibili")



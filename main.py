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

# Logging strutturato
from utils.logging_config import get_logger, log_operation, info, warning, error

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
from exporters.dxf_exporter import export_to_dxf, EZDXF_AVAILABLE as ezdxf_available
from core.wall_builder import pack_wall, opt_pass
from utils.block_utils import summarize_blocks as summarize_blocks_helper
from utils.geometry_utils import snap, snap_bounds, polygon_holes, sanitize_polygon, ensure_multipolygon, SNAP_MM
from utils.config import (
    SCARTO_CUSTOM_MM, AREA_EPS, COORD_EPS, DISPLAY_MM_PER_M,
    MICRO_REST_MM, KEEP_OUT_MM, SPLIT_MAX_WIDTH_MM,
    BLOCK_HEIGHT, BLOCK_WIDTHS, SIZE_TO_LETTER, BLOCK_ORDERS, SESSIONS,
    get_block_schema_from_frontend, get_default_block_schema  # NEW: Block customization functions
)
from utils.preview_generator import generate_preview_image

# Alias dalle utility di export
summarize_blocks = summarize_blocks_helper


# Alias dalle utility di export
summarize_blocks = summarize_blocks_helper


# NEW: Enhanced packing with automatic measurements
try:
    from core.enhanced_packing import (
        EnhancedPackingCalculator,
        enhance_packing_with_automatic_measurements,
        calculate_automatic_project_parameters
    )
    ENHANCED_PACKING_AVAILABLE = True
except ImportError as e:
    warning("Enhanced packing non disponibile", error=str(e))
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
    info("dxfgrabber caricato - Supporto DWG avanzato disponibile")
except ImportError:
    dxfgrabber_available = False
    warning("dxfgrabber non installato. Parser DWG avanzato non disponibile.")

# ---- FastAPI (kept in same file as requested) ----
try:
    from fastapi import FastAPI, UploadFile, File, Form, HTTPException, WebSocket, WebSocketDisconnect, Request, Response, Depends
    from fastapi.responses import JSONResponse, FileResponse, StreamingResponse, HTMLResponse, RedirectResponse
    from fastapi.staticfiles import StaticFiles
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.templating import Jinja2Templates
    from pydantic import BaseModel
    import uvicorn
    
    # Import routes refactorizzate
    from api.routes import frontend_router, packing_router, files_router, legacy_router
    from api.auth_routes import router as auth_router  # Routes di autenticazione
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
    
    # Include all refactored routes  
    app.include_router(frontend_router)
    app.include_router(packing_router, prefix="/api")
    app.include_router(files_router, prefix="/api")
    app.include_router(legacy_router, prefix="/api")
    app.include_router(auth_router, prefix="/api/v1")  # Authentication routes
    
    # Cleanup sessioni scadute all'avvio
    try:
        expired_cleaned = cleanup_expired_sessions()
        info("Pulizia iniziale completata", expired_sessions_cleaned=expired_cleaned)
    except Exception as e:
        error("Errore pulizia sessioni", error=str(e))
    
    # ===== INCLUDE ROUTES REFACTORED =====
    from api.routes import frontend_router, packing_router, files_router, legacy_router
    
    app.include_router(frontend_router)
    app.include_router(packing_router, prefix="/api")
    app.include_router(files_router, prefix="/api")
    app.include_router(legacy_router)
    
    # Mount static files - solo se la directory esiste
    import os
    if os.path.exists("static"):
        app.mount("/static", StaticFiles(directory="static"), name="static")
    
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
        
        info("File salvato", file_path=str(saved_path), user_id=user_id, session_id=session_id)
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
                        warning("File del progetto non trovato", file_path=str(file_path))
                        return None
                        
        except Exception as e:
            error("Errore nel recupero file progetto", error=str(e), project_id=project_id)
            return None
        
        return None
    
        return None
    
    # ===== ROUTES MOVED TO api/routes/ =====
    
# ────────────────────────────────────────────────────────────────────────────────
# CLI demo (mantenuto per test)
# ────────────────────────────────────────────────────────────────────────────────
def _demo():
    logger = get_logger("demo")
    logger.info("🚀 Demo Costruttore Pareti a Blocchi")
    
    with log_operation("demo_packing"):
        # Demo parete trapezoidale con due porte
        wall_exterior = Polygon([(0,0), (12000,0), (12000,4500), (0,2500), (0,0)])
        porta1 = Polygon([(2000,0), (3200,0), (3200,2200), (2000,2200)])
        porta2 = Polygon([(8500,0), (9700,0), (9700,2200), (8500,2200)])

        placed, custom = pack_wall(wall_exterior, BLOCK_WIDTHS, BLOCK_HEIGHT,
                                   row_offset=826, apertures=[porta1, porta2])
        summary = summarize_blocks(placed)

        logger.info("Distinta base blocchi standard")
        for k, v in summary.items():
            logger.info(f"Blocco {k}", quantity=v)
        
        logger.info("Pezzi custom totali", count=len(custom))

        # Calcola metriche
        metrics = calculate_metrics(placed, custom, wall_exterior.area)
        logger.info("Metriche calcolate", 
                   efficiency=f"{metrics['efficiency']:.1%}",
                   waste_ratio=f"{metrics['waste_ratio']:.1%}",
                   complexity=metrics['complexity'])

    # Genera nomi file unici con timestamp
    json_filename = generate_unique_filename("distinta_demo", ".json", "trapezoidale")
    pdf_filename = generate_unique_filename("report_demo", ".pdf", "trapezoidale") 
    dxf_filename = generate_unique_filename("schema_demo", ".dxf", "trapezoidale")

    out = export_to_json(summary, custom, placed, out_path=json_filename, params=build_run_params(row_offset=826))
    logger.info("JSON demo generato", file_path=out)

    # Test export PDF
    if reportlab_available:
        try:
            pdf_path = export_to_pdf(summary, custom, placed, wall_exterior, 
                                   apertures=[porta1, porta2],
                                   project_name="Demo Parete Trapezoidale", 
                                   out_path=pdf_filename,
                                   params=build_run_params(row_offset=826))
            logger.info("PDF demo generato", file_path=pdf_path)
        except Exception as e:
            error("Errore PDF demo", error=str(e))
    else:
        warning("ReportLab non disponibile per export PDF")

    # Test export DXF SENZA SOVRAPPOSIZIONI
    if ezdxf_available:
        try:
            dxf_path = export_to_dxf(summary, custom, placed, wall_exterior, 
                                   apertures=[porta1, porta2],
                                   project_name="Demo Parete Trapezoidale", 
                                   out_path=dxf_filename,
                                   params=build_run_params(row_offset=826))
            logger.info("DXF demo generato", file_path=dxf_path)
        except Exception as e:
            error("Errore DXF demo", error=str(e))
    else:
        warning("ezdxf non disponibile per export DXF")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        _demo()
    elif len(sys.argv) > 1 and sys.argv[1] == "server":
        # Avvia server FastAPI
        if app:
            info("🚀 Avvio server Web UI...")
            info("🌐 Apri il browser su: http://localhost:8000")
            info("🛑 Premi Ctrl+C per fermare il server")
            
            # Reload solo se richiesto esplicitamente con --dev
            use_reload = len(sys.argv) > 2 and sys.argv[2] == "--dev"
            if use_reload:
                info("🔧 Modalità sviluppo: auto-reload attivo")
            
            uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=use_reload)
        else:
            error("❌ FastAPI non disponibile")
    else:
        info("Uso: python main.py [demo|server] [--dev]")
        info("  demo     - Esegui demo CLI")
        info("  server   - Avvia server web")
        info("  --dev    - Modalità sviluppo con auto-reload (solo con server)")
        info("🧱 MIGLIORAMENTI DXF:")
        info("  ✅ Layout intelligente con DXFLayoutManager")
        info("  ✅ Zone calcolate automaticamente senza sovrapposizioni")
        info("  ✅ Margini adattivi basati su contenuto")
        info("  ✅ Controllo overflow per tabelle e schema taglio")
        info("  ✅ Titoli e sezioni ben separate e leggibili")



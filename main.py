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
from utils.geometry_utils import snap, snap_bounds, polygon_holes, sanitize_polygon, ensure_multipolygon, SNAP_MM
from utils.config import (
    SCARTO_CUSTOM_MM, AREA_EPS, COORD_EPS, DISPLAY_MM_PER_M,
    MICRO_REST_MM, KEEP_OUT_MM, SPLIT_MAX_WIDTH_MM,
    BLOCK_HEIGHT, BLOCK_WIDTHS, SIZE_TO_LETTER, BLOCK_ORDERS, SESSIONS,
    get_block_schema_from_frontend, get_default_block_schema  # NEW: Block customization functions
)

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

# Optional PDF generation
try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import mm
    from reportlab.lib.colors import black, gray, green, red, blue, white
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.graphics.shapes import Drawing, Rect, String
    from reportlab.graphics import renderPDF
    from reportlab.lib import colors
    reportlab_available = True
except ImportError:
    print(" reportlab non installato. Export PDF non disponibile.")
    reportlab_available = False

# ────────────────────────────────────────────────────────────────────────────────
# Optional dependencies
# ────────────────────────────────────────────────────────────────────────────────

# Optional DXF generation
try:
    import ezdxf
    from ezdxf import colors as dxf_colors
    from ezdxf.enums import TextEntityAlignment
    ezdxf_available = True
except ImportError:
    print(" ezdxf non installato. Export DXF non disponibile.")
    ezdxf_available = False

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
def export_to_dxf(summary: Dict[str, int], 
                  customs: List[Dict], 
                  placed: List[Dict], 
                  wall_polygon: Polygon,
                  apertures: Optional[List[Polygon]] = None,
                  project_name: str = "Progetto Parete",
                  out_path: str = "schema_taglio.dxf",
                  params: Optional[Dict] = None,
                  color_theme: Optional[Dict] = None) -> str:
    """
    Genera DXF con layout: SOPRA assemblato completo + SOTTO schema taglio raggruppato.
    """
    if not ezdxf_available:
        raise RuntimeError("ezdxf non disponibile. Installa con: pip install ezdxf")
    
    # Usa il sistema di organizzazione automatica
    organized_path = get_organized_output_path(out_path, 'dxf')
    
    try:
        # Crea nuovo documento DXF
        doc = ezdxf.new('R2010')
        msp = doc.modelspace()
        
        # Setup layer professionali
        _setup_dxf_layers(doc, color_theme)
        
        # Calcola bounds wall per reference
        minx, miny, maxx, maxy = wall_polygon.bounds
        wall_width = maxx - minx
        wall_height = maxy - miny
        
        # ===== LAYOUT SEMPLIFICATO: SOPRA + SOTTO =====
        layout = DXFLayoutManager(wall_width, wall_height)
        
        # 1. LAYOUT PRINCIPALE assemblato (zona superiore)
        main_zone = layout.add_zone("main", wall_width, wall_height)
        _draw_main_layout(msp, wall_polygon, placed, customs, apertures, main_zone)
        
        # 2. SCHEMA TAGLIO raggruppato (zona inferiore con separazione)
        cutting_width = wall_width  # Stessa larghezza del main
        cutting_height = _calculate_cutting_height_grouped_all(summary, customs, placed)
        cutting_zone = layout.add_zone("cutting", cutting_width, cutting_height, 
                                     anchor="below", ref_zone="main", margin=2000)  # Separazione aumentata
        _draw_cutting_schema_fixed(msp, customs, cutting_zone)
        
        # 3. CARTIGLIO compatto (angolo basso destro)
        cartridge_width = 2000
        cartridge_height = 1000
        cartridge_zone = layout.add_zone("cartridge", cartridge_width, cartridge_height,
                                       anchor="below_right", ref_zone="cutting", margin=500)
        _draw_compact_cartridge(msp, project_name, summary, customs, params, cartridge_zone)
        
        # Salva documento
        doc.saveas(organized_path)
        print(f" DXF con layout SOPRA+SOTTO generato: {organized_path}")
        print(f" Layout totale: {layout.get_total_width():.0f} x {layout.get_total_height():.0f} mm")
        return organized_path
        
    except Exception as e:
        print(f" Errore generazione DXF: {e}")
        raise


class DXFLayoutManager:
    """Gestisce il layout DXF evitando sovrapposizioni."""
    
    def __init__(self, base_width: float, base_height: float):
        self.zones = {}
        self.base_width = base_width
        self.base_height = base_height
        self.total_bounds = [0, 0, 0, 0]  # minx, miny, maxx, maxy
        
    def add_zone(self, name: str, width: float, height: float, 
                 anchor: str = "topleft", ref_zone: str = None, margin: float = 500) -> Dict:
        """
        Aggiunge una zona calcolando automaticamente la posizione senza sovrapposizioni.
        
        anchor options:
        - "topleft": (0, 0) - default
        - "right_of": a destra della zona ref
        - "below": sotto la zona ref  
        - "below_right": sotto e a destra della zona ref
        - "bottom": in fondo a tutto
        """
        
        if anchor == "topleft" or ref_zone is None:
            # Prima zona o posizione assoluta
            x, y = 0, 0
            
        elif anchor == "right_of" and ref_zone in self.zones:
            ref = self.zones[ref_zone]
            x = ref['x'] + ref['width'] + margin
            y = ref['y']
            
        elif anchor == "below" and ref_zone in self.zones:
            ref = self.zones[ref_zone]
            x = ref['x']
            y = ref['y'] - height - margin
            
        elif anchor == "below_right" and ref_zone in self.zones:
            ref = self.zones[ref_zone]
            x = ref['x'] + ref['width'] - width  # Allineato a destra
            y = ref['y'] - height - margin
            
        elif anchor == "bottom":
            # In fondo rispetto a tutte le zone esistenti
            x = 0
            y = min(zone['y'] - zone['height'] for zone in self.zones.values()) - margin - height
            
        else:
            # Fallback
            x, y = 0, 0
            
        zone = {
            'name': name,
            'x': x,
            'y': y,
            'width': width,
            'height': height,
            'anchor': anchor,
            'ref_zone': ref_zone
        }
        
        self.zones[name] = zone
        self._update_total_bounds(zone)
        
        print(f" Zona '{name}': {width:.0f}x{height:.0f} @ ({x:.0f}, {y:.0f})")
        return zone
    
    def _update_total_bounds(self, zone: Dict):
        """Aggiorna i bounds totali del layout."""
        minx = min(self.total_bounds[0], zone['x'])
        miny = min(self.total_bounds[1], zone['y'] - zone['height'])
        maxx = max(self.total_bounds[2], zone['x'] + zone['width'])
        maxy = max(self.total_bounds[3], zone['y'])
        self.total_bounds = [minx, miny, maxx, maxy]
    
    def get_total_width(self) -> float:
        return self.total_bounds[2] - self.total_bounds[0]
    
    def get_total_height(self) -> float:
        return self.total_bounds[3] - self.total_bounds[1]


def _calculate_cutting_height_grouped_all(summary: Dict[str, int], customs: List[Dict], placed: List[Dict]) -> float:
    """Calcola altezza necessaria per schema di taglio completo (standard + custom)."""
    
    # Conta tutte le categorie (standard + custom)
    total_categories = 0
    
    # Categorie standard dal summary
    total_categories += len(summary)
    
    # Categorie custom raggruppate per dimensioni
    custom_categories = {}
    for custom in customs:
        width = round(custom['width'])
        height = round(custom['height'])
        key = f"{width}x{height}"
        if key not in custom_categories:
            custom_categories[key] = 1
        else:
            custom_categories[key] += 1
    
    total_categories += len(custom_categories)
    
    # Calcola layout griglia con sezioni più grandi
    sections_per_row = 2  # Ridotto a 2 per dare più spazio
    rows_needed = (total_categories + sections_per_row - 1) // sections_per_row
    
    section_height = 900  # Altezza maggiore per ogni sezione
    title_space = 800     # Spazio per titoli
    margin_between_rows = 150  # Maggior margine tra righe
    
    total_height = title_space + (rows_needed * section_height) + ((rows_needed - 1) * margin_between_rows)
    return max(total_height, 2000)  # Minimo 2000mm per più spazio


def _calculate_cutting_height_grouped(customs: List[Dict]) -> float:
    """Calcola altezza necessaria per schema di taglio raggruppato per categoria."""
    if not customs:
        return 1000
    
    # Raggruppa per categoria per calcolare numero di sezioni
    categories = {}
    for custom in customs:
        width = round(custom['width'])
        height = round(custom['height'])
        key = f"{width}x{height}"
        if key not in categories:
            categories[key] = 1
        else:
            categories[key] += 1
    
    # Calcola layout griglia
    num_categories = len(categories)
    sections_per_row = 3  # Max 3 sezioni per riga
    rows_needed = (num_categories + sections_per_row - 1) // sections_per_row
    
    section_height = 700  # Altezza per ogni sezione
    title_space = 800     # Spazio per titoli
    margin_between_rows = 100
    
    total_height = title_space + (rows_needed * section_height) + ((rows_needed - 1) * margin_between_rows)
    return max(total_height, 1500)  # Minimo 1500mm


def _draw_compact_cartridge(msp, project_name: str, summary: Dict[str, int], 
                          customs: List[Dict], params: Optional[Dict], zone: Dict):
    """Disegna cartiglio compatto nella zona assegnata."""
    offset_x = zone['x']
    offset_y = zone['y']
    
    # Rettangolo cartiglio
    msp.add_lwpolyline([
        (offset_x, offset_y - zone['height']),
        (offset_x + zone['width'], offset_y - zone['height']),
        (offset_x + zone['width'], offset_y),
        (offset_x, offset_y),
        (offset_x, offset_y - zone['height'])
    ], dxfattribs={"layer": "CARTIGLIO"})
    
    # Titolo progetto
    msp.add_text(project_name.upper(), height=100, dxfattribs={
        "layer": "TESTI",
        "style": "Standard"
    }).set_placement((offset_x + zone['width']/2, offset_y - 150),
                    align=TextEntityAlignment.MIDDLE_CENTER)
    
    # Informazioni essenziali
    now = datetime.datetime.now()
    total_standard = sum(summary.values())
    total_custom = len(customs)
    
    # Calcola categorie senza f-string nidificata
    categories_count = len(set(f"{round(c['width'])}x{round(c['height'])}" for c in customs))
    
    info_lines = [
        f"Data: {now.strftime('%d/%m/%Y')}",
        f"Blocchi Std: {total_standard}",
        f"Pezzi Custom: {total_custom}",
        f"Tot Categorie: {categories_count}"
    ]
    
    for i, line in enumerate(info_lines):
        msp.add_text(line, height=60, dxfattribs={
            "layer": "TESTI",
            "style": "Standard"
        }).set_placement((offset_x + 100, offset_y - 300 - i * 100),
                        align=TextEntityAlignment.BOTTOM_LEFT)


def _calculate_cutting_height(customs: List[Dict]) -> float:
    """Calcola altezza necessaria per schema di taglio."""
    if not customs:
        return 1000
    
    # Simula layout taglio per calcolare altezza
    rows = _optimize_cutting_layout(customs)
    row_height = 600  # Altezza base per riga
    margin = 100
    
    total_height = len(rows) * (row_height + margin) + 800  # +800 per titolo e margini
    return max(total_height, 1500)  # Minimo 1500mm


def _calculate_tables_height(summary: Dict[str, int], customs: List[Dict]) -> float:
    """Calcola altezza necessaria per le tabelle."""
    std_rows = len(summary) + 2  # +2 per header e totale
    custom_rows = len(customs) + 1  # +1 per header
    
    row_height = 200  # Altezza riga tabella
    title_height = 300  # Altezza titoli
    margin = 200
    
    std_table_height = std_rows * row_height + title_height
    custom_table_height = custom_rows * row_height + title_height
    
    # Tabelle affiancate, prendiamo la più alta
    max_table_height = max(std_table_height, custom_table_height)
    
    return max_table_height + margin * 2


def _draw_main_layout(msp, wall_polygon: Polygon, placed: List[Dict], customs: List[Dict], 
                     apertures: Optional[List[Polygon]], zone: Dict):
    """Disegna il layout principale della parete."""
    offset_x = zone['x']
    offset_y = zone['y']
    
    # Contorno parete
    _draw_wall_outline(msp, wall_polygon, offset_x, offset_y)
    
    # Aperture
    if apertures:
        _draw_apertures(msp, apertures, offset_x, offset_y)
    
    # Blocchi
    _draw_standard_blocks(msp, placed, offset_x, offset_y)
    _draw_custom_blocks(msp, customs, offset_x, offset_y)
    
    # Quote principali
    _add_main_dimensions(msp, wall_polygon, offset_x, offset_y)
    
    # Titolo sezione - SPOSTATO PIÙ IN ALTO
    msp.add_text("LAYOUT PARETE PRINCIPALE", height=300, dxfattribs={
        "layer": "TESTI",
        "style": "Standard"
    }).set_placement((offset_x + zone['width']/2, offset_y + zone['height'] + 800), 
                    align=TextEntityAlignment.MIDDLE_CENTER)


def _draw_cutting_schema_fixed(msp, customs: List[Dict], zone: Dict):
    """Disegna schema di taglio con TUTTI i blocchi (standard + custom) raggruppati per categoria."""
    offset_x = zone['x']
    offset_y = zone['y']
    
    # Titolo sezione
    msp.add_text("SCHEMA DI TAGLIO COMPLETO", height=300, dxfattribs={
        "layer": "TESTI",
        "style": "Standard"
    }).set_placement((offset_x + zone['width']/2, offset_y + zone['height'] + 600), 
                    align=TextEntityAlignment.MIDDLE_CENTER)
    
    msp.add_text("TUTTI I BLOCCHI RAGGRUPPATI PER CATEGORIA", height=200, dxfattribs={
        "layer": "TESTI",
        "style": "Standard"
    }).set_placement((offset_x + zone['width']/2, offset_y + zone['height'] + 300), 
                    align=TextEntityAlignment.MIDDLE_CENTER)
    
    # FORZA la creazione delle categorie con fallback completo
    try:
        from block_grouping import BlockGrouping
        grouping = BlockGrouping()
        
        # Simula dei blocchi standard tipici se non ci sono placed disponibili
        fake_placed = [
            {'width': 1239, 'height': 495},  # Standard A
            {'width': 826, 'height': 495},   # Standard B  
            {'width': 413, 'height': 495}    # Standard C
        ]
        
        # Crea le etichette che popolano automaticamente le categorie
        std_labels, custom_labels = grouping.create_grouped_labels(fake_placed, customs)
        
        # Ora ottieni il riassunto completo
        all_categories = grouping.get_category_summary()
        print(f" Categorie create: {len(all_categories)}")
        
        # Converte il formato summary in formato compatibile
        category_data = {}
        for category_letter, info in all_categories.items():
            # Trova un blocco rappresentativo
            if info['type'] == 'standard':
                # Crea blocco standard rappresentativo
                dims = info['dimensions'].split('x')
                representative = {
                    'width': int(dims[0]),
                    'height': int(dims[1])
                }
            else:
                # Trova il primo custom di questa categoria
                representative = None
                for i, custom in enumerate(customs):
                    if i in custom_labels and custom_labels[i]['category'] == category_letter:
                        representative = custom
                        break
                if not representative and customs:
                    representative = customs[0]  # Fallback
            
            if representative:
                category_data[category_letter] = {
                    'representative': representative,
                    'count': info['count'],
                    'type': info['type'],
                    'dimensions': info['dimensions']
                }
        
        all_categories = category_data
        
    except Exception as e:
        print(f" Errore creazione categorie: {e}")
        # Fallback: raggruppa solo i custom
        all_categories = {}
        for i, custom in enumerate(customs):
            width = round(custom['width'])
            height = round(custom['height'])
            key = f"D"  # Categoria D per custom
            
            if key not in all_categories:
                all_categories[key] = {
                    'representative': custom,
                    'count': 1,
                    'type': 'custom',
                    'dimensions': f"{width}×{height}"
                }
            else:
                all_categories[key]['count'] += 1
    
    if not all_categories:
        msp.add_text("NESSUN BLOCCO DA VISUALIZZARE", height=150, dxfattribs={
            "layer": "TESTI",
            "style": "Standard"
        }).set_placement((offset_x + zone['width']/2, offset_y + zone['height']/2), 
                        align=TextEntityAlignment.MIDDLE_CENTER)
        return
    
    # Assegna lettere alle categorie (A, B, C per standard; D, E, F... per custom)
    category_letters = []
    current_letter = ord('A')  # Inizia da A
    
    # Ordina categorie: prima standard, poi custom
    sorted_categories = sorted(all_categories.items(), key=lambda x: (x[1]['type'] == 'custom', x[0]))
    
    for key, category_info in sorted_categories:
        letter = chr(current_letter)
        category_info['letter'] = letter
        category_letters.append((letter, category_info))
        current_letter += 1
        if current_letter > ord('Z'):  # Se finiscono le lettere, ricomincia da AA
            current_letter = ord('A')
    
    # Layout dei pezzi rappresentativi con SPAZIO MAGGIORE
    current_x = offset_x + 100  # Margine sinistro ridotto
    current_y = offset_y + zone['height'] - 800  # Partenza dall'alto
    section_height = 900  # AUMENTATO da 700 a 900
    section_width = 1000  # AUMENTATO da 800 a 1000
    margin_x = 150  # Margine orizzontale ridotto
    
    sections_per_row = max(1, int((zone['width'] - 200) / (section_width + margin_x)))  # Calcola quante sezioni per riga
    
    section_count = 0
    
    for letter, category_info in category_letters:
        # Calcola posizione sezione
        row = section_count // sections_per_row
        col = section_count % sections_per_row
        
        section_x = offset_x + 100 + col * (section_width + margin_x)
        section_y = current_y - row * (section_height + 150)  # Maggior spazio tra righe
        
        # Controlla se la sezione entra nella zona
        if section_y - section_height < offset_y:
            break  # Non entra più, stop
        
        # Disegna intestazione sezione come nell'immagine
        header_height = 150  # AUMENTATO da 120 a 150
        
        # Rettangolo intestazione
        msp.add_lwpolyline([
            (section_x, section_y),
            (section_x + section_width, section_y),
            (section_x + section_width, section_y - header_height),
            (section_x, section_y - header_height),
            (section_x, section_y)
        ], dxfattribs={"layer": "CARTIGLIO"})
        
        # Testi intestazione (come nell'immagine)
        tipo_base = "INTERO" if category_info['type'] == 'standard' else "CUSTOM"
        msp.add_text(f"PEZZO BASE: {tipo_base}", height=90, dxfattribs={
            "layer": "TESTI",
            "style": "Standard"
        }).set_placement((section_x + 60, section_y - 40), align=TextEntityAlignment.BOTTOM_LEFT)
        
        msp.add_text(f"NOME: {letter}", height=90, dxfattribs={
            "layer": "TESTI", 
            "style": "Standard"
        }).set_placement((section_x + 500, section_y - 40), align=TextEntityAlignment.BOTTOM_LEFT)
        
        msp.add_text("PZ", height=70, dxfattribs={
            "layer": "TESTI",
            "style": "Standard"
        }).set_placement((section_x + section_width - 80, section_y - 40), align=TextEntityAlignment.BOTTOM_LEFT)
        
        # Area contenuto pezzo - PIÙ GRANDE
        content_height = section_height - header_height
        content_y = section_y - header_height
        
        # Rettangolo bordo contenuto
        msp.add_lwpolyline([
            (section_x, content_y),
            (section_x + section_width, content_y),
            (section_x + section_width, content_y - content_height),
            (section_x, content_y - content_height),
            (section_x, content_y)
        ], dxfattribs={"layer": "CARTIGLIO"})
        
        # Disegna il pezzo rappresentativo al centro - DIMENSIONI PIÙ GRANDI
        rep = category_info['representative']
        max_piece_width = section_width - 200   # Più spazio per il pezzo
        max_piece_height = content_height - 150  # Più spazio per il pezzo
        
        # Scala il pezzo mantenendo le proporzioni
        piece_width = min(rep['width'], max_piece_width)
        piece_height = min(rep['height'], max_piece_height)
        
        # Se il pezzo è troppo grande, scala proporzionalmente
        if piece_width > max_piece_width or piece_height > max_piece_height:
            scale_w = max_piece_width / rep['width']
            scale_h = max_piece_height / rep['height']
            scale = min(scale_w, scale_h)
            piece_width = rep['width'] * scale
            piece_height = rep['height'] * scale
        
        # Centra il pezzo nell'area contenuto
        piece_x = section_x + (section_width - piece_width) / 2
        piece_y = content_y - (content_height - piece_height) / 2
        
        # Colore diverso per standard vs custom
        block_color = 1 if category_info['type'] == 'standard' else 3  # Rosso per std, Verde per custom
        
        # Rettangolo pezzo
        msp.add_lwpolyline([
            (piece_x, piece_y),
            (piece_x + piece_width, piece_y),
            (piece_x + piece_width, piece_y - piece_height),
            (piece_x, piece_y - piece_height),
            (piece_x, piece_y)
        ], dxfattribs={"layer": "TAGLIO", "color": block_color})
        
        # Etichetta lettera al centro del pezzo - PIÙ GRANDE
        center_piece_x = piece_x + piece_width / 2
        center_piece_y = piece_y - piece_height / 2
        
        msp.add_text(letter, height=200, dxfattribs={  # AUMENTATO da 150 a 200
            "layer": "TESTI",
            "style": "Standard",
            "color": block_color
        }).set_placement((center_piece_x, center_piece_y), align=TextEntityAlignment.MIDDLE_CENTER)
        
        # Quote dimensioni - PIÙ VISIBILI
        msp.add_text(f"{rep['width']:.0f}", height=80, dxfattribs={  # AUMENTATO da 60 a 80
            "layer": "QUOTE"
        }).set_placement((center_piece_x, piece_y + 70), align=TextEntityAlignment.MIDDLE_CENTER)
        
        msp.add_text(f"{rep['height']:.0f}", height=80, dxfattribs={  # AUMENTATO da 60 a 80
            "layer": "QUOTE"
        }).set_placement((piece_x - 70, center_piece_y), align=TextEntityAlignment.MIDDLE_CENTER)
        
        # Quantità in grande (angolo destro) - PIÙ GRANDE
        quantity_x = section_x + section_width - 120
        quantity_y = content_y - content_height / 2
        
        msp.add_text(str(category_info['count']), height=250, dxfattribs={  # AUMENTATO da 200 a 250
            "layer": "TESTI",
            "style": "Standard",
            "color": block_color
        }).set_placement((quantity_x, quantity_y), align=TextEntityAlignment.MIDDLE_CENTER)
        
        section_count += 1


def _draw_tables_section(msp, summary: Dict[str, int], customs: List[Dict], placed: List[Dict], zone: Dict):
    """Disegna sezione tabelle nella zona assegnata."""
    offset_x = zone['x']
    offset_y = zone['y']
    
    # Dividi zona in due colonne per le tabelle
    col_width = zone['width'] / 2 - 200  # -200 per margini
    
    # TABELLA BLOCCHI STANDARD (colonna sinistra)
    std_zone = {
        'x': offset_x,
        'y': offset_y + zone['height'],
        'width': col_width,
        'height': zone['height']
    }
    _draw_standard_blocks_table_fixed(msp, summary, placed, std_zone)
    
    # TABELLA CUSTOM (colonna destra)
    custom_zone = {
        'x': offset_x + col_width + 200,
        'y': offset_y + zone['height'],
        'width': col_width,
        'height': zone['height']
    }
    _draw_custom_dimensions_table_fixed(msp, customs, custom_zone)


def _draw_standard_blocks_table_fixed(msp, summary: Dict[str, int], placed: List[Dict], zone: Dict):
    """Disegna tabella blocchi standard con raggruppamento categorizzato."""
    offset_x = zone['x']
    offset_y = zone['y']
    
    # Titolo
    msp.add_text("BLOCCHI STANDARD (RAGGRUPPATI)", height=150, dxfattribs={
        "layer": "TESTI",
        "style": "Standard"
    }).set_placement((offset_x + zone['width']/2, offset_y - 100), align=TextEntityAlignment.MIDDLE_CENTER)
    
    # Usa il nuovo sistema per ottenere categorie
    try:
        if get_block_category_summary:
            categories = get_block_category_summary()
            # Filtra solo categorie standard
            std_categories = {k: v for k, v in categories.items() if v['type'] == 'standard'}
        else:
            # Fallback al sistema legacy
            std_categories = {}
            for blk in placed:
                letter = SIZE_TO_LETTER.get(int(blk["width"]), "X")
                if letter not in std_categories:
                    std_categories[letter] = {
                        'count': 0,
                        'type': 'standard',
                        'dimensions': f"{blk['width']}×{blk['height']}"
                    }
                std_categories[letter]['count'] += 1
    except:
        # Doppio fallback
        std_categories = {'A': {'count': len(placed), 'type': 'standard', 'dimensions': '1239×495'}}
    
    # Setup tabella
    headers = ["CATEGORIA", "QTÀ", "DIMENSIONI", "TIPO"]
    col_widths = [zone['width'] * 0.25, zone['width'] * 0.2, zone['width'] * 0.35, zone['width'] * 0.2]
    row_height = 200
    
    start_y = offset_y - 300
    
    # Header
    current_x = offset_x
    for i, (header, width) in enumerate(zip(headers, col_widths)):
        msp.add_lwpolyline([
            (current_x, start_y),
            (current_x + width, start_y),
            (current_x + width, start_y - row_height),
            (current_x, start_y - row_height),
            (current_x, start_y)
        ], dxfattribs={"layer": "CARTIGLIO"})
        
        msp.add_text(header, height=80, dxfattribs={
            "layer": "TESTI",
            "style": "Standard"
        }).set_placement((current_x + width/2, start_y - row_height/2), 
                        align=TextEntityAlignment.MIDDLE_CENTER)
        current_x += width
    
    # Righe dati (ordinate per categoria)
    sorted_categories = sorted(std_categories.items())
    
    for i, (category, details) in enumerate(sorted_categories):
        current_y = start_y - (i + 2) * row_height  # +2 per saltare header
        current_x = offset_x
        
        # Controlla se la riga entra nella zona
        if current_y < offset_y - zone['height']:
            break
        
        row_data = [
            f"Tipo {category}",           # Categoria con descrizione
            str(details['count']),        # Quantità
            details['dimensions'],        # Dimensioni
            "Standard"                    # Tipo
        ]
        
        for j, (data, width) in enumerate(zip(row_data, col_widths)):
            msp.add_lwpolyline([
                (current_x, current_y),
                (current_x + width, current_y),
                (current_x + width, current_y - row_height),
                (current_x, current_y - row_height),
                (current_x, current_y)
            ], dxfattribs={"layer": "CARTIGLIO"})
            
            msp.add_text(str(data), height=70, dxfattribs={
                "layer": "TESTI",
                "style": "Standard"
            }).set_placement((current_x + width/2, current_y - row_height/2),
                            align=TextEntityAlignment.MIDDLE_CENTER)
            current_x += width


def _draw_custom_dimensions_table_fixed(msp, customs: List[Dict], zone: Dict):
    """Disegna tabella custom con raggruppamento categorizzato."""
    if not customs:
        return
    
    offset_x = zone['x']
    offset_y = zone['y']
    
    # Titolo
    msp.add_text("PEZZI CUSTOM (RAGGRUPPATI)", height=150, dxfattribs={
        "layer": "TESTI",
        "style": "Standard"
    }).set_placement((offset_x + zone['width']/2, offset_y - 100), align=TextEntityAlignment.MIDDLE_CENTER)
    
    # Usa il nuovo sistema per ottenere categorie custom
    try:
        if get_block_category_summary:
            categories = get_block_category_summary()
            # Filtra solo categorie custom
            custom_categories = {k: v for k, v in categories.items() if v['type'] == 'custom'}
        else:
            # Fallback: raggruppa manualmente per dimensioni simili
            custom_categories = {}
            tolerance = 5  # mm
            category_letter = 'D'  # Inizia da D per custom
            
            for i, custom in enumerate(customs):
                width = round(custom['width'])
                height = round(custom['height'])
                
                # Cerca categoria esistente con dimensioni simili
                found_category = None
                for cat, info in custom_categories.items():
                    try:
                        existing_dims = info['dimensions'].split('×')
                        existing_w, existing_h = int(existing_dims[0]), int(existing_dims[1])
                        if (abs(width - existing_w) <= tolerance and 
                            abs(height - existing_h) <= tolerance):
                            found_category = cat
                            break
                    except:
                        continue
                
                if found_category:
                    custom_categories[found_category]['count'] += 1
                else:
                    # Nuova categoria
                    custom_categories[category_letter] = {
                        'count': 1,
                        'type': 'custom',
                        'dimensions': f"{width}×{height}"
                    }
                    category_letter = chr(ord(category_letter) + 1)
    except:
        # Doppio fallback
        custom_categories = {'D': {'count': len(customs), 'type': 'custom', 'dimensions': '300×400'}}
    
    # Setup tabella
    headers = ["CATEGORIA", "QTÀ", "DIMENSIONI", "TIPO"]
    col_widths = [zone['width'] * 0.25, zone['width'] * 0.2, zone['width'] * 0.35, zone['width'] * 0.2]
    row_height = 200
    
    start_y = offset_y - 300
    
    # Header
    current_x = offset_x
    for header, width in zip(headers, col_widths):
        msp.add_lwpolyline([
            (current_x, start_y),
            (current_x + width, start_y),
            (current_x + width, start_y - row_height),
            (current_x, start_y - row_height),
            (current_x, start_y)
        ], dxfattribs={"layer": "CARTIGLIO"})
        
        msp.add_text(header, height=80, dxfattribs={
            "layer": "TESTI",
            "style": "Standard"
        }).set_placement((current_x + width/2, start_y - row_height/2),
                        align=TextEntityAlignment.MIDDLE_CENTER)
        current_x += width
    
    # Dati categorie custom
    max_rows = int((zone['height'] - 400) / row_height) - 1  # -1 per header
    display_categories = list(custom_categories.items())[:max_rows]
    
    for i, (category, details) in enumerate(display_categories):
        current_y = start_y - (i + 1) * row_height
        current_x = offset_x
        
        row_data = [
            f"Tipo {category}",        # Categoria
            str(details['count']),     # Quantità
            details['dimensions'],     # Dimensioni
            "Custom"                   # Tipo
        ]
        
        for data, width in zip(row_data, col_widths):
            msp.add_lwpolyline([
                (current_x, current_y),
                (current_x + width, current_y),
                (current_x + width, current_y - row_height),
                (current_x, current_y - row_height),
                (current_x, current_y)
            ], dxfattribs={"layer": "CARTIGLIO"})
            
            msp.add_text(str(data), height=70, dxfattribs={
                "layer": "TESTI",
                "style": "Standard"
            }).set_placement((current_x + width/2, current_y - row_height/2),
                            align=TextEntityAlignment.MIDDLE_CENTER)
            current_x += width
    
    # Nota se ci sono più categorie di quelle visualizzate
    if len(custom_categories) > max_rows:
        msp.add_text(f"... e altre {len(custom_categories) - max_rows} categorie custom", 
                    height=60, dxfattribs={
                        "layer": "TESTI",
                        "style": "Standard"
                    }).set_placement((offset_x + zone['width']/2, 
                                    start_y - (max_rows + 2) * row_height),
                                    align=TextEntityAlignment.MIDDLE_CENTER)


def _draw_professional_cartridge_fixed(msp, project_name: str, summary: Dict[str, int], 
                                     customs: List[Dict], params: Optional[Dict], zone: Dict):
    """Disegna cartiglio nella zona assegnata."""
    offset_x = zone['x']
    offset_y = zone['y']
    
    # Rettangolo cartiglio
    msp.add_lwpolyline([
        (offset_x, offset_y - zone['height']),
        (offset_x + zone['width'], offset_y - zone['height']),
        (offset_x + zone['width'], offset_y),
        (offset_x, offset_y),
        (offset_x, offset_y - zone['height'])
    ], dxfattribs={"layer": "CARTIGLIO"})
    
    # Titolo progetto
    msp.add_text(project_name.upper(), height=120, dxfattribs={
        "layer": "TESTI",
        "style": "Standard"
    }).set_placement((offset_x + zone['width']/2, offset_y - 200),
                    align=TextEntityAlignment.MIDDLE_CENTER)
    
    # Informazioni tecniche
    now = datetime.datetime.now()
    total_standard = sum(summary.values())
    total_custom = len(customs)
    efficiency = total_standard / (total_standard + total_custom) if total_standard + total_custom > 0 else 0
    
    info_lines = [
        f"Data: {now.strftime('%d/%m/%Y %H:%M')}",
        f"Blocchi Standard: {total_standard}",
        f"Pezzi Custom: {total_custom}",
        f"Efficienza: {efficiency:.1%}",
        f"Algoritmo: Greedy + Backtrack"
    ]
    
    for i, line in enumerate(info_lines):
        msp.add_text(line, height=80, dxfattribs={
            "layer": "TESTI",
            "style": "Standard"
        }).set_placement((offset_x + 100, offset_y - 400 - i * 150),
                        align=TextEntityAlignment.BOTTOM_LEFT)


def _draw_legend_and_notes_fixed(msp, zone: Dict):
    """Disegna legenda nella zona assegnata."""
    offset_x = zone['x']
    offset_y = zone['y']
    
    # Titolo
    msp.add_text("LEGENDA E NOTE TECNICHE", height=120, dxfattribs={
        "layer": "TESTI",
        "style": "Standard"
    }).set_placement((offset_x + zone['width']/2, offset_y - 100), 
                    align=TextEntityAlignment.MIDDLE_CENTER)
    
    # Note in due colonne
    col_width = zone['width'] / 2
    
    # Colonna 1: Simboli
    symbols = [
        ("━━", "BLOCCHI_STD", "Blocchi Standard"),
        ("╱╱", "BLOCCHI_CUSTOM", "Pezzi Custom"),
        ("┈┈", "APERTURE", "Aperture"),
        ("↔", "QUOTE", "Quote (mm)")
    ]
    
    for i, (symbol, layer, desc) in enumerate(symbols):
        y_pos = offset_y - 300 - i * 120
        msp.add_text(f"{symbol} {desc}", height=60, dxfattribs={
            "layer": "TESTI",
            "style": "Standard"
        }).set_placement((offset_x + 100, y_pos), align=TextEntityAlignment.BOTTOM_LEFT)
    
    # Colonna 2: Note tecniche
    notes = [
        "• Dimensioni in millimetri",
        "• Tolleranze taglio ±2mm", 
        "• CU1: taglio larghezza da blocco C",
        "• CU2: taglio flessibile da blocco C"
    ]
    
    for i, note in enumerate(notes):
        y_pos = offset_y - 300 - i * 120
        msp.add_text(note, height=60, dxfattribs={
            "layer": "TESTI",
            "style": "Standard"
        }).set_placement((offset_x + col_width + 100, y_pos), 
                        align=TextEntityAlignment.BOTTOM_LEFT)


# ===== FUNZIONI HELPER ESISTENTI (mantengono la stessa logica) =====

def _setup_dxf_layers(doc, color_theme: Optional[Dict] = None):
    """Configura layer professionali con colori personalizzabili."""
    
    # Color mapping da theme a DXF colors
    def theme_color_to_dxf(theme_color, fallback_dxf_color):
        """Converte colore hex del theme in colore DXF."""
        if not theme_color or not isinstance(theme_color, str):
            return fallback_dxf_color
        
        # Mapping semplificato colori comuni
        color_map = {
            '#1E40AF': dxf_colors.BLUE,     # wallOutlineColor default
            '#DC2626': dxf_colors.RED,      # doorWindowBorder default  
            '#374151': dxf_colors.BLACK,    # standardBlockBorder default
            '#7C3AED': dxf_colors.MAGENTA,  # customPieceBorder default
            '#16A34A': dxf_colors.GREEN,    # green variants
        }
        
        return color_map.get(theme_color, fallback_dxf_color)
    
    # Default colors se theme non fornito
    if not color_theme:
        color_theme = {}
    
    layer_config = [
        # (name, theme_key, fallback_color, linetype, lineweight)
        ("PARETE", theme_color_to_dxf(color_theme.get('wallOutlineColor'), dxf_colors.BLUE), "CONTINUOUS", 0.50),
        ("APERTURE", theme_color_to_dxf(color_theme.get('doorWindowBorder'), dxf_colors.RED), "DASHED", 0.30),
        ("BLOCCHI_STD", theme_color_to_dxf(color_theme.get('standardBlockBorder'), dxf_colors.BLACK), "CONTINUOUS", 0.25),
        ("BLOCCHI_CUSTOM", theme_color_to_dxf(color_theme.get('customPieceBorder'), dxf_colors.MAGENTA), "CONTINUOUS", 0.35),
        ("QUOTE", dxf_colors.MAGENTA, "CONTINUOUS", 0.18),
        ("TESTI", dxf_colors.BLACK, "CONTINUOUS", 0.15),
        ("TAGLIO", dxf_colors.CYAN, "CONTINUOUS", 0.40),
        ("CARTIGLIO", dxf_colors.BLACK, "CONTINUOUS", 0.25),
        ("LEGENDA", dxf_colors.BLACK, "CONTINUOUS", 0.20),
    ]
    
    print(f" [DEBUG] Setting up DXF layers with theme colors: {color_theme}")
    
    for name, color, linetype, lineweight in layer_config:
        layer = doc.layers.add(name)
        layer.color = color
        layer.linetype = linetype
        layer.lineweight = int(lineweight * 100)  # Convert to AutoCAD units


def _draw_wall_outline(msp, wall_polygon: Polygon, offset_x: float, offset_y: float):
    """Disegna il contorno della parete principale."""
    # Contorno esterno con linea più spessa
    exterior_coords = [(x + offset_x, y + offset_y) for x, y in wall_polygon.exterior.coords]
    msp.add_lwpolyline(exterior_coords, close=True, dxfattribs={
        "layer": "PARETE",
        "lineweight": 100  # Linea più spessa per visibilità
    })
    
    # Contorni interni (holes)
    for interior in wall_polygon.interiors:
        interior_coords = [(x + offset_x, y + offset_y) for x, y in interior.coords]
        msp.add_lwpolyline(interior_coords, close=True, dxfattribs={
            "layer": "PARETE",
            "lineweight": 80
        })


def _draw_apertures(msp, apertures: List[Polygon], offset_x: float, offset_y: float):
    """Disegna porte e finestre."""
    for i, aperture in enumerate(apertures):
        coords = [(x + offset_x, y + offset_y) for x, y in aperture.exterior.coords]
        msp.add_lwpolyline(coords, close=True, dxfattribs={"layer": "APERTURE"})
        
        # Etichetta apertura
        minx, miny, maxx, maxy = aperture.bounds
        center_x = (minx + maxx) / 2 + offset_x
        center_y = (miny + maxy) / 2 + offset_y
        width = maxx - minx
        height = maxy - miny
        
        label = f"AP{i+1}\n{width:.0f}x{height:.0f}"
        msp.add_text(label, height=150, dxfattribs={
            "layer": "TESTI", 
            "style": "Standard"
        }).set_placement((center_x, center_y), align=TextEntityAlignment.MIDDLE_CENTER)


def _draw_standard_blocks(msp, placed: List[Dict], offset_x: float, offset_y: float):
    """Disegna blocchi standard con etichette raggruppate."""
    # Usa il nuovo sistema di etichettatura dettagliata
    detailed_labels, _ = create_detailed_block_labels(placed, [])
    
    for i, block in enumerate(placed):
        x1 = block['x'] + offset_x
        y1 = block['y'] + offset_y
        x2 = x1 + block['width']
        y2 = y1 + block['height']
        
        # Rettangolo blocco
        msp.add_lwpolyline([
            (x1, y1), (x2, y1), (x2, y2), (x1, y2), (x1, y1)
        ], dxfattribs={"layer": "BLOCCHI_STD"})
        
        # Sistema di etichettatura NUOVO: categoria BL + numero TR
        if i in detailed_labels:
            label_info = detailed_labels[i]
            
            # Posizioni specifiche
            category_x = x1 + 50  # Basso sinistra X
            category_y = y1 + 50  # Basso sinistra Y
            number_x = x2 - 50    # Alto destra X  
            number_y = y2 - 50    # Alto destra Y
            
            # Lettera categoria (basso sinistra) - più grande
            category = label_info['display']['bottom_left']
            msp.add_text(category, height=150, dxfattribs={
                "layer": "TESTI",
                "style": "Standard",
                "color": 1  # Rosso per categoria
            }).set_placement((category_x, category_y), align=TextEntityAlignment.BOTTOM_LEFT)
            
            # Numero progressivo (alto destra) - più piccolo
            number = label_info['display']['top_right']
            msp.add_text(number, height=100, dxfattribs={
                "layer": "TESTI", 
                "style": "Standard",
                "color": 2  # Giallo per numero
            }).set_placement((number_x, number_y), align=TextEntityAlignment.TOP_RIGHT)
            
        else:
            # Fallback: etichetta centrata
            center_x = x1 + block['width'] / 2
            center_y = y1 + block['height'] / 2
            
            std_labels, _ = create_block_labels(placed, [])
            label = std_labels.get(i, f"STD{i+1}")
            
            msp.add_text(label, height=120, dxfattribs={
                "layer": "TESTI",
                "style": "Standard"
            }).set_placement((center_x, center_y), align=TextEntityAlignment.MIDDLE_CENTER)


def _draw_custom_blocks(msp, customs: List[Dict], offset_x: float, offset_y: float):
    """Disegna blocchi custom con etichette raggruppate e info taglio."""
    # Usa il nuovo sistema di etichettatura dettagliata
    _, detailed_labels = create_detailed_block_labels([], customs)
    
    for i, custom in enumerate(customs):
        # Disegna geometria custom
        try:
            poly = shape(custom['geometry'])
            coords = [(x + offset_x, y + offset_y) for x, y in poly.exterior.coords]
            msp.add_lwpolyline(coords, close=True, dxfattribs={"layer": "BLOCCHI_CUSTOM"})
            
            # Calcola bounds per posizionamento etichette
            x1 = custom['x'] + offset_x
            y1 = custom['y'] + offset_y
            x2 = x1 + custom['width']
            y2 = y1 + custom['height']
            
            # Sistema di etichettatura NUOVO: categoria BL + numero TR
            if i in detailed_labels:
                label_info = detailed_labels[i]
                
                # Posizioni specifiche
                category_x = x1 + 40  # Basso sinistra X (margine più piccolo per custom)
                category_y = y1 + 40  # Basso sinistra Y
                number_x = x2 - 40    # Alto destra X  
                number_y = y2 - 40    # Alto destra Y
                
                # Lettera categoria (basso sinistra) - più grande
                category = label_info['display']['bottom_left']
                msp.add_text(category, height=120, dxfattribs={
                    "layer": "TESTI",
                    "style": "Standard",
                    "color": 3  # Verde per categoria custom
                }).set_placement((category_x, category_y), align=TextEntityAlignment.BOTTOM_LEFT)
                
                # Numero progressivo (alto destra) - più piccolo
                number = label_info['display']['top_right']
                msp.add_text(number, height=80, dxfattribs={
                    "layer": "TESTI", 
                    "style": "Standard",
                    "color": 4  # Cyan per numero custom
                }).set_placement((number_x, number_y), align=TextEntityAlignment.TOP_RIGHT)
                
                # Info taglio al centro (opzionale, più piccola)
                center_x = custom['x'] + custom['width'] / 2 + offset_x
                center_y = custom['y'] + custom['height'] / 2 + offset_y
                
                ctype = custom.get('ctype', 2)
                dimensions_text = f"{custom['width']:.0f}×{custom['height']:.0f}\nCU{ctype}"
                
                msp.add_text(dimensions_text, height=60, dxfattribs={
                    "layer": "TESTI",
                    "style": "Standard",
                    "color": 8  # Grigio per info aggiuntive
                }).set_placement((center_x, center_y), align=TextEntityAlignment.MIDDLE_CENTER)
                
            else:
                # Fallback: etichetta centrata legacy
                center_x = custom['x'] + custom['width'] / 2 + offset_x
                center_y = custom['y'] + custom['height'] / 2 + offset_y
                
                _, custom_labels = create_block_labels([], customs)
                label = custom_labels.get(i, f"CU{i+1}")
                
                ctype = custom.get('ctype', 2)
                full_label = f"{label}\n{custom['width']:.0f}x{custom['height']:.0f}\nCU{ctype}"
                
                msp.add_text(full_label, height=90, dxfattribs={
                    "layer": "TESTI",
                    "style": "Standard"
                }).set_placement((center_x, center_y), align=TextEntityAlignment.MIDDLE_CENTER)
            
        except Exception as e:
            print(f" Errore disegno custom {i}: {e}")


def _add_main_dimensions(msp, wall_polygon: Polygon, offset_x: float, offset_y: float):
    """Aggiunge quote principali della parete."""
    minx, miny, maxx, maxy = wall_polygon.bounds
    wall_width = maxx - minx
    wall_height = maxy - miny
    
    # Quota larghezza totale (in basso)
    dim_y = miny + offset_y - 300
    dim = msp.add_linear_dim(
        base=(minx + offset_x, dim_y),
        p1=(minx + offset_x, miny + offset_y),
        p2=(maxx + offset_x, miny + offset_y),
        text=f"{wall_width:.0f}",
        dimstyle="Standard",
        dxfattribs={"layer": "QUOTE"}
    )
    
    # Quota altezza totale (a sinistra)
    dim_x = minx + offset_x - 300
    dim = msp.add_linear_dim(
        base=(dim_x, miny + offset_y),
        p1=(minx + offset_x, miny + offset_y),
        p2=(minx + offset_x, maxy + offset_y),
        text=f"{wall_height:.0f}",
        dimstyle="Standard",
        dxfattribs={"layer": "QUOTE"}
    )


def _optimize_cutting_layout(customs: List[Dict]) -> List[List[int]]:
    """
    Ottimizza il layout di taglio raggruppando pezzi simili.
    Returns: Lista di righe, ogni riga contiene indici dei pezzi.
    """
    if not customs:
        return []
    
    # Ordina pezzi per altezza decrescente, poi larghezza
    sorted_indices = sorted(
        range(len(customs)),
        key=lambda i: (-customs[i]['height'], -customs[i]['width'])
    )
    
    # Raggruppa in righe di altezza simile
    rows = []
    current_row = []
    current_row_height = None
    height_tolerance = 50  # mm
    
    for idx in sorted_indices:
        piece_height = customs[idx]['height']
        
        if (current_row_height is None or 
            abs(piece_height - current_row_height) <= height_tolerance):
            current_row.append(idx)
            current_row_height = piece_height
        else:
            if current_row:
                rows.append(current_row)
            current_row = [idx]
            current_row_height = piece_height
    
    if current_row:
        rows.append(current_row)
    
    return rows


# ────────────────────────────────────────────────────────────────────────────────
# Packing core (ESISTENTE - mantenuto identico)
# ────────────────────────────────────────────────────────────────────────────────
def _mk_std(x: float, y: float, w: int, h: int) -> Dict:
    return {"type": f"std_{w}x{h}", "width": w, "height": h, "x": snap(x), "y": snap(y)}

def _mk_custom(geom: Polygon) -> Dict:
    geom = sanitize_polygon(geom)
    minx, miny, maxx, maxy = geom.bounds
    return {
        "type": "custom",
        "width": snap(maxx - minx),
        "height": snap(maxy - miny),
        "x": snap(minx),
        "y": snap(miny),
        "geometry": mapping(geom)
    }

def _score_solution(placed: List[Dict], custom: List[Dict]) -> Tuple[int, float]:
    """Score lessicografico: (#custom, area_custom_totale)."""
    total_area = 0.0
    for c in custom:
        poly = shape(c["geometry"])
        total_area += poly.area
    return (len(custom), total_area)

def _try_fill(comp: Polygon, y: float, stripe_top: float, widths: List[int], start_x: float) -> Tuple[List[Dict], List[Dict]]:
    """Greedy semplice a partire da start_x con ordine widths."""
    placed: List[Dict] = []
    custom: List[Dict] = []

    seg_minx, _, seg_maxx, _ = comp.bounds
    cursor = snap(start_x)
    y = snap(y)
    stripe_top = snap(stripe_top)

    while cursor < seg_maxx - COORD_EPS:
        placed_one = False
        for bw in widths:
            if cursor + bw <= seg_maxx + COORD_EPS:
                candidate = box(cursor, y, cursor + bw, stripe_top)
                intersec = candidate.intersection(comp)
                if intersec.is_empty or intersec.area < AREA_EPS:
                    continue
                if math.isclose(intersec.area, candidate.area, rel_tol=1e-9):
                    placed.append(_mk_std(cursor, y, bw, BLOCK_HEIGHT))
                else:
                    custom.append(_mk_custom(intersec))
                cursor = snap(cursor + bw)
                placed_one = True
                break
        if not placed_one:
            remaining = comp.intersection(box(cursor, y, seg_maxx, stripe_top))
            if not remaining.is_empty and remaining.area > AREA_EPS:
                custom.append(_mk_custom(remaining))
            break
    return placed, custom

def choose_optimal_block_for_space(remaining_width: float, widths_order: List[int], tolerance: float = 5.0) -> Optional[int]:
    """
     CONTROLLO DINAMICO: Sceglie il blocco ottimale per lo spazio rimanente.
    
    Args:
        remaining_width: Spazio disponibile in mm
        widths_order: Lista delle larghezze disponibili (in ordine di priorità)
        tolerance: Tolleranza per considerare uno spazio "troppo piccolo"
    
    Returns:
        Larghezza del blocco ottimale, o None se conviene creare custom piece
    """
    
    # Se lo spazio è troppo piccolo per qualsiasi blocco standard
    min_width = min(widths_order)
    if remaining_width < min_width + tolerance:
        # Conviene creare un custom piece
        return None
    
    #  ALGORITMO PREDITTIVO: Valuta tutte le combinazioni possibili
    best_option = None
    min_total_waste = float('inf')
    
    # Prova ogni blocco e simula cosa succede dopo
    for width in sorted(widths_order, reverse=True):  # Dal più grande al più piccolo
        if remaining_width >= width + tolerance:
            # Simula il piazzamento di questo blocco
            waste_scenarios = simulate_future_placement(remaining_width, width, widths_order, tolerance)
            
            if waste_scenarios['total_waste'] < min_total_waste:
                min_total_waste = waste_scenarios['total_waste']
                best_option = width
                
    if best_option:
        print(f"    Predittivo: Spazio {remaining_width:.0f}mm → Blocco {best_option}mm (spreco totale: {min_total_waste:.0f}mm)")
        return best_option
    
    # Fallback: usa il più piccolo se entra
    smallest = min(widths_order)
    if remaining_width >= smallest:
        waste = remaining_width - smallest
        print(f"    Fallback: Spazio {remaining_width:.0f}mm → Blocco minimo {smallest}mm (spreco: {waste:.0f}mm)")
        return smallest
    
    # Spazio troppo piccolo
    print(f"    Spazio {remaining_width:.0f}mm troppo piccolo → Custom piece")
    return None

def simulate_future_placement(total_space: float, first_block: int, widths_order: List[int], tolerance: float) -> dict:
    """
     SIMULAZIONE PREDITTIVA: Simula il piazzamento futuro per minimizzare spreco totale.
    
    Args:
        total_space: Spazio totale disponibile
        first_block: Primo blocco da piazzare
        widths_order: Blocchi disponibili
        tolerance: Tolleranza
    
    Returns:
        Dict con informazioni sulla simulazione (total_waste, blocks_count, etc.)
    """
    
    remaining = total_space - first_block
    placed_blocks = [first_block]
    
    # Algoritmo greedy per il resto dello spazio
    while remaining >= min(widths_order) + tolerance:
        best_fit = None
        
        # Trova il blocco più grande che entra
        for width in sorted(widths_order, reverse=True):
            if remaining >= width + tolerance:
                best_fit = width
                break
        
        if best_fit:
            placed_blocks.append(best_fit)
            remaining -= best_fit
        else:
            break
    
    # Calcola metriche della simulazione
    total_waste = remaining
    blocks_count = len(placed_blocks)
    efficiency = (total_space - total_waste) / total_space * 100
    
    return {
        'total_waste': total_waste,
        'blocks_count': blocks_count,
        'efficiency': efficiency,
        'blocks_sequence': placed_blocks,
        'final_remainder': remaining
    }

def choose_optimal_sequence_advanced(remaining_width: float, widths_order: List[int], tolerance: float = 5.0, max_look_ahead: int = 3) -> Optional[int]:
    """
     ALGORITMO PREDITTIVO AVANZATO: Considera sequenze multiple per ottimizzazione globale.
    
    Args:
        remaining_width: Spazio disponibile
        widths_order: Blocchi disponibili  
        tolerance: Tolleranza
        max_look_ahead: Numero massimo di blocchi da considerare in anticipo
    
    Returns:
        Primo blocco della sequenza ottimale
    """
    
    if remaining_width < min(widths_order) + tolerance:
        return None
    
    # Genera tutte le possibili combinazioni di inizio
    best_sequence = None
    min_waste = float('inf')
    
    # Test diverse strategie di inizio
    strategies = [
        "maximize_first",  # Inizia con il blocco più grande
        "balance_sequence", # Bilancia la sequenza
        "minimize_remainder" # Minimizza il resto finale
    ]
    
    for strategy in strategies:
        sequence_result = evaluate_strategy(remaining_width, widths_order, strategy, tolerance, max_look_ahead)
        
        if sequence_result and sequence_result['total_waste'] < min_waste:
            min_waste = sequence_result['total_waste']
            best_sequence = sequence_result
    
    if best_sequence:
        first_block = best_sequence['sequence'][0]
        print(f"    Avanzato: Spazio {remaining_width:.0f}mm → Sequenza {best_sequence['sequence']} (spreco: {min_waste:.0f}mm)")
        return first_block
    
    return None

def evaluate_strategy(space: float, widths: List[int], strategy: str, tolerance: float, max_depth: int) -> Optional[dict]:
    """Valuta una strategia specifica di packing."""
    
    if strategy == "maximize_first":
        # Inizia sempre con il blocco più grande possibile
        return _greedy_sequence(space, sorted(widths, reverse=True), tolerance, max_depth)
    
    elif strategy == "balance_sequence":
        # Cerca un equilibrio tra blocchi grandi e piccoli
        balanced_order = _create_balanced_order(widths)
        return _greedy_sequence(space, balanced_order, tolerance, max_depth)
    
    elif strategy == "minimize_remainder":
        # Prova tutte le permutazioni e scegli quella con minor resto
        return _find_minimal_remainder_sequence(space, widths, tolerance, max_depth)
    
    return None

def _greedy_sequence(space: float, order: List[int], tolerance: float, max_depth: int) -> dict:
    """Algoritmo greedy con ordine specificato."""
    remaining = space
    sequence = []
    
    depth = 0
    while remaining >= min(order) + tolerance and depth < max_depth:
        placed = False
        for width in order:
            if remaining >= width + tolerance:
                sequence.append(width)
                remaining -= width
                placed = True
                depth += 1
                break
        if not placed:
            break
    
    return {
        'sequence': sequence,
        'total_waste': remaining,
        'efficiency': (space - remaining) / space * 100
    }

def _create_balanced_order(widths: List[int]) -> List[int]:
    """Crea un ordine bilanciato alternando blocchi grandi e piccoli."""
    sorted_widths = sorted(widths, reverse=True)
    balanced = []
    
    # Alterna tra grande e piccolo
    for i, width in enumerate(sorted_widths):
        if i % 2 == 0:
            balanced.append(width)
        else:
            balanced.insert(0, width)
    
    return balanced

def _find_minimal_remainder_sequence(space: float, widths: List[int], tolerance: float, max_depth: int) -> dict:
    """Trova la sequenza che minimizza il resto usando ricerca limitata."""
    from itertools import permutations
    
    best_sequence = None
    min_remainder = float('inf')
    
    # Limita le permutazioni per performance
    max_perms = 10
    perm_count = 0
    
    for perm in permutations(widths):
        if perm_count >= max_perms:
            break
            
        result = _greedy_sequence(space, list(perm), tolerance, max_depth)
        if result['total_waste'] < min_remainder:
            min_remainder = result['total_waste']
            best_sequence = result
            
        perm_count += 1
    
    return best_sequence or {'sequence': [], 'total_waste': space, 'efficiency': 0}

def _pack_segment_with_order(comp: Polygon, y: float, stripe_top: float, widths_order: List[int], offset: int = 0) -> Tuple[List[Dict], List[Dict]]:
    """Esegue il packing su un singolo segmento (comp), con offset e ordine blocchi fissati."""
    placed: List[Dict] = []
    custom: List[Dict] = []

    seg_minx, _, seg_maxx, _ = comp.bounds
    seg_minx = snap(seg_minx)
    seg_maxx = snap(seg_maxx)
    y = snap(y)
    stripe_top = snap(stripe_top)

    cursor = seg_minx

    # offset iniziale (se richiesto)
    if offset and cursor + offset <= seg_maxx + COORD_EPS:
        candidate = box(cursor, y, cursor + offset, stripe_top)
        intersec = candidate.intersection(comp)
        if not intersec.is_empty and intersec.area >= AREA_EPS:
            if math.isclose(intersec.area, candidate.area, rel_tol=1e-9):
                placed.append(_mk_std(cursor, y, offset, BLOCK_HEIGHT))
            else:
                custom.append(_mk_custom(intersec))
            cursor = snap(cursor + offset)

    # storico per eventuale backtrack sul micro-resto
    history = []  # (cursor_before, placed_index_len, custom_index_len)
    while cursor < seg_maxx - COORD_EPS:
        history.append((cursor, len(placed), len(custom)))
        
        #  CONTROLLO DINAMICO: Calcola spazio rimanente e scegli blocco ottimale
        remaining_width = seg_maxx - cursor
        
        #  USA ALGORITMO PREDITTIVO AVANZATO
        optimal_width = choose_optimal_sequence_advanced(remaining_width, widths_order, tolerance=5.0, max_look_ahead=3)
        
        # Fallback al controllo dinamico semplice se l'avanzato non trova soluzioni
        if optimal_width is None:
            optimal_width = choose_optimal_block_for_space(remaining_width, widths_order)
        
        placed_one = False
        
        if optimal_width is not None:
            # Prova prima il blocco ottimale suggerito
            if cursor + optimal_width <= seg_maxx + COORD_EPS:
                candidate = box(cursor, y, cursor + optimal_width, stripe_top)
                intersec = candidate.intersection(comp)
                if not intersec.is_empty and intersec.area >= AREA_EPS:
                    if math.isclose(intersec.area, candidate.area, rel_tol=1e-9):
                        placed.append(_mk_std(cursor, y, optimal_width, BLOCK_HEIGHT))
                        cursor = snap(cursor + optimal_width)
                        placed_one = True
                    else:
                        custom.append(_mk_custom(intersec))
                        cursor = snap(cursor + optimal_width)
                        placed_one = True
        
        # Se il blocco ottimale non funziona, fallback all'algoritmo originale
        if not placed_one:
            for bw in widths_order:
                if cursor + bw <= seg_maxx + COORD_EPS:
                    candidate = box(cursor, y, cursor + bw, stripe_top)
                    intersec = candidate.intersection(comp)
                    if intersec.is_empty or intersec.area < AREA_EPS:
                        continue
                    if math.isclose(intersec.area, candidate.area, rel_tol=1e-9):
                        placed.append(_mk_std(cursor, y, bw, BLOCK_HEIGHT))
                    else:
                        custom.append(_mk_custom(intersec))
                    cursor = snap(cursor + bw)
                    placed_one = True
                    break
        
        if not placed_one:
            # residuo a fine segmento
            remaining = comp.intersection(box(cursor, y, seg_maxx, stripe_top))
            rem_width = seg_maxx - cursor
            if rem_width < MICRO_REST_MM and history:
                # backtrack 1 step e prova ordine alternativo fine-coda
                cursor_prev, p_len, c_len = history[-1]
                placed = placed[:p_len]
                custom = custom[:c_len]
                cursor = cursor_prev
                # Use reversed order of current widths_order for backtracking
                alt_order = list(reversed(widths_order))
                p2, c2 = _try_fill(comp, y, stripe_top, alt_order, cursor)
                baseline_custom_area = 0.0
                if not remaining.is_empty and remaining.area > AREA_EPS:
                    baseline_custom_area = remaining.area
                score_backtrack = _score_solution(placed + p2, custom + c2)
                score_baseline = (len(custom) + (1 if baseline_custom_area > 0 else 0), baseline_custom_area)
                if score_backtrack < score_baseline:
                    placed.extend(p2)
                    custom.extend(c2)
                    if p2:
                        last = p2[-1]
                        cursor = snap(last["x"] + last["width"])
                    elif c2:
                        break
                    continue
                else:
                    if baseline_custom_area > AREA_EPS:
                        custom.append(_mk_custom(remaining))
                    break
            else:
                if not remaining.is_empty and remaining.area > AREA_EPS:
                    custom.append(_mk_custom(remaining))
                break

    return placed, custom

def _pack_segment(comp: Polygon, y: float, stripe_top: float, widths: List[int], offset: int = 0) -> Tuple[List[Dict], List[Dict]]:
    """Prova più ordini e sceglie la soluzione migliore per il segmento."""
    best_placed = []
    best_custom = []
    best_score = (10**9, float("inf"))
    
    # Genera ordini dinamici dalle dimensioni passate
    orders = [
        sorted(widths, reverse=True),  # Prima grandi, poi medi, poi piccoli
        sorted(widths)[1:] + [sorted(widths)[0]]  # Prima medi, poi grandi, poi piccoli (se ci sono almeno 2 elementi)
    ]
    
    for order in orders:
        p_try, c_try = _pack_segment_with_order(comp, y, stripe_top, order, offset=offset)
        score = _score_solution(p_try, c_try)
        if score < best_score:
            best_score = score
            best_placed, best_custom = p_try, c_try
    return best_placed, best_custom

def _pack_segment_adaptive(comp: Polygon, y: float, stripe_top: float, widths: List[int], 
                          adaptive_height: float, offset: int = 0) -> Tuple[List[Dict], List[Dict]]:
    """
    Pack segment con altezza adattiva per l'ultima riga.
    Identico a _pack_segment ma con altezza blocchi personalizzata.
    """
    best_placed = []
    best_custom = []
    best_score = (10**9, float("inf"))
    
    # Genera ordini dinamici dalle dimensioni passate
    orders = [
        sorted(widths, reverse=True),  # Prima grandi, poi medi, poi piccoli
        sorted(widths)[1:] + [sorted(widths)[0]]  # Prima medi, poi grandi, poi piccoli (se ci sono almeno 2 elementi)
    ]
    
    for order in orders:
        p_try, c_try = _pack_segment_with_order_adaptive(comp, y, stripe_top, order, 
                                                        adaptive_height, offset=offset)
        score = _score_solution(p_try, c_try)
        if score < best_score:
            best_score = score
            best_placed, best_custom = p_try, c_try
    return best_placed, best_custom

def _pack_segment_with_order_adaptive(comp: Polygon, y: float, stripe_top: float, 
                                     widths_order: List[int], adaptive_height: float, 
                                     offset: int = 0) -> Tuple[List[Dict], List[Dict]]:
    """
    Pack segment con ordine specifico e altezza adattiva.
    """
    minx, _, maxx, _ = comp.bounds
    actual_height = stripe_top - y
    
    # Usa altezza adattiva invece di quella standard
    effective_height = min(adaptive_height, actual_height)
    
    placed = []
    x = minx + offset
    
    while x < maxx:
        #  CONTROLLO DINAMICO ADATTIVO: Calcola spazio rimanente
        remaining_width = maxx - x
        
        #  USA ALGORITMO PREDITTIVO AVANZATO ANCHE PER BLOCCHI ADATTIVI
        optimal_width = choose_optimal_sequence_advanced(remaining_width, widths_order, tolerance=5.0, max_look_ahead=3)
        
        # Fallback al controllo dinamico semplice
        if optimal_width is None:
            optimal_width = choose_optimal_block_for_space(remaining_width, widths_order)
        
        best_width = None
        
        if optimal_width is not None:
            # Prova prima il blocco ottimale
            if x + optimal_width <= maxx:
                candidate = box(x, y, x + optimal_width, y + effective_height)
                if comp.contains(candidate):
                    best_width = optimal_width
        
        # Se il blocco ottimale non funziona, fallback all'algoritmo originale
        if best_width is None:
            for width in widths_order:
                if x + width <= maxx:
                    candidate = box(x, y, x + width, y + effective_height)
                    if comp.contains(candidate):
                        best_width = width
                        break
        
        if best_width is not None:
            placed.append({
                "x": snap(x),
                "y": snap(y),
                "width": best_width,
                "height": snap(effective_height),  # Altezza adattiva!
                "type": f"adaptive_block_{best_width}"
            })
            x += best_width
        else:
            x += min(widths_order)  # Incremento minimo
    
    # Calcola area rimanente per custom pieces
    remaining = comp
    for block in placed:
        block_box = box(block["x"], block["y"], 
                       block["x"] + block["width"], 
                       block["y"] + block["height"])
        remaining = remaining.difference(block_box)
    
    # Genera custom pieces dall'area rimanente
    custom = []
    if remaining.area > AREA_EPS:
        if isinstance(remaining, Polygon):
            custom.append(_mk_custom(remaining))
        else:
            for geom in remaining.geoms:
                if geom.area > AREA_EPS:
                    custom.append(_mk_custom(geom))
    
    return placed, custom

def pack_wall(polygon: Polygon,
              block_widths: List[int],
              block_height: int,
              row_offset: Optional[int] = 826,
              apertures: Optional[List[Polygon]] = None) -> Tuple[List[Dict], List[Dict]]:
    """
    Packer principale con altezza adattiva per ottimizzare l'uso dello spazio.
    """
    polygon = sanitize_polygon(polygon)

    # Aperture dal poligono + eventuali passate a parte
    hole_polys = polygon_holes(polygon)
    ap_list = list(apertures) if apertures else []
    keepout = None
    if hole_polys or ap_list:
        u = unary_union([*hole_polys, *ap_list])
        keepout = u.buffer(KEEP_OUT_MM) if not u.is_empty else None

    minx, miny, maxx, maxy = polygon.bounds
    placed_all: List[Dict] = []
    custom_all: List[Dict] = []

    # CALCOLO OTTIMIZZATO: Determina righe complete e spazio residuo
    total_height = maxy - miny
    complete_rows = int(total_height / block_height)
    remaining_space = total_height - (complete_rows * block_height)
    
    print(f" Algoritmo adattivo: {complete_rows} righe complete, {remaining_space:.0f}mm rimanenti")

    y = miny
    row = 0

    # FASE 1: Processa righe complete con altezza standard
    while row < complete_rows:
        stripe_top = y + block_height
        stripe = box(minx, y, maxx, stripe_top)
        inter = polygon.intersection(stripe)
        if keepout:
            inter = inter.difference(keepout)

        comps = ensure_multipolygon(inter)

        for comp in comps:
            if comp.is_empty or comp.area < AREA_EPS:
                continue

            # offset candidates
            offset_candidates: List[int] = [0] if (row % 2 == 0) else []
            if row % 2 == 1:
                if row_offset is not None:
                    offset_candidates.append(int(row_offset))
                offset_candidates.append(413)

            best_placed = []
            best_custom = []
            best_score = (10**9, float("inf"))

            for off in offset_candidates:
                p_try, c_try = _pack_segment(comp, y, stripe_top, block_widths, offset=off)
                score = _score_solution(p_try, c_try)
                if score < best_score:
                    best_score = score
                    best_placed, best_custom = p_try, c_try

            placed_all.extend(best_placed)
            custom_all.extend(best_custom)

        y = snap(y + block_height)
        row += 1

    # FASE 2: Riga adattiva se spazio sufficiente
    if remaining_space >= 150:  # Minimo ragionevole per blocchi
        adaptive_height = min(remaining_space, block_height)
        print(f" Riga adattiva {row}: altezza={adaptive_height:.0f}mm")
        
        stripe_top = y + adaptive_height
        stripe = box(minx, y, maxx, stripe_top)
        inter = polygon.intersection(stripe)
        if keepout:
            inter = inter.difference(keepout)

        comps = ensure_multipolygon(inter)

        for comp in comps:
            if comp.is_empty or comp.area < AREA_EPS:
                continue

            # offset candidates per riga adattiva
            offset_candidates: List[int] = [0] if (row % 2 == 0) else []
            if row % 2 == 1:
                if row_offset is not None:
                    offset_candidates.append(int(row_offset))
                offset_candidates.append(413)

            best_placed = []
            best_custom = []
            best_score = (10**9, float("inf"))

            for off in offset_candidates:
                # MODIFICA: Usa pack_segment specializzato per altezza adattiva
                p_try, c_try = _pack_segment_adaptive(comp, y, stripe_top, block_widths, 
                                                     adaptive_height, offset=off)
                score = _score_solution(p_try, c_try)
                if score < best_score:
                    best_score = score
                    best_placed, best_custom = p_try, c_try

            placed_all.extend(best_placed)
            custom_all.extend(best_custom)
    else:
        print(f" Spazio rimanente {remaining_space:.0f}mm insufficiente per riga adattiva")

    custom_all = merge_customs_row_aware(custom_all, tol=SCARTO_CUSTOM_MM, row_height=BLOCK_HEIGHT)
    custom_all = split_out_of_spec(custom_all, max_w=SPLIT_MAX_WIDTH_MM)
    return placed_all, validate_and_tag_customs(custom_all)

# ────────────────────────────────────────────────────────────────────────────────
# Optimization (hook - no-op for ora)
# ────────────────────────────────────────────────────────────────────────────────
def opt_pass(placed: List[Dict], custom: List[Dict], block_widths: List[int]) -> Tuple[List[Dict], List[Dict]]:
    return placed, custom

# ────────────────────────────────────────────────────────────────────────────────
# Merge customs (row-aware)
# ────────────────────────────────────────────────────────────────────────────────
def merge_customs_row_aware(customs: List[Dict], tol: float = 5, row_height: int = 495) -> List[Dict]:
    """
    Coalesco customs solo all'interno della stessa fascia orizzontale.
    """
    if not customs:
        return []
    rows: Dict[int, List[Polygon]] = defaultdict(list)
    for c in customs:
        y0 = snap(c["y"])
        row_id = int(round(y0 / row_height))
        poly = shape(c["geometry"]).buffer(0)
        rows[row_id].append(poly)

    out: List[Dict] = []
    for rid, polys in rows.items():
        if not polys:
            continue
        merged = unary_union(polys)
        geoms = [merged] if isinstance(merged, Polygon) else list(merged.geoms)
        for g in geoms:
            if g.area > AREA_EPS:
                out.append(_mk_custom(g))
    return out

def split_out_of_spec(customs: List[Dict], max_w: int = 413, max_h: int = 495) -> List[Dict]:
    """Divide ogni pezzo 'out_of_spec' in più slice verticali."""
    out: List[Dict] = []
    for c in customs:
        w = int(round(c.get("width", 0)))
        h = int(round(c.get("height", 0)))
        if (w <= max_w + SCARTO_CUSTOM_MM) and (h <= max_h + SCARTO_CUSTOM_MM):
            out.append(c)
            continue

        poly = shape(c["geometry"]).buffer(0)
        if poly.is_empty or poly.area <= AREA_EPS:
            continue
        minx, miny, maxx, maxy = poly.bounds

        x0 = minx
        while x0 < maxx - COORD_EPS:
            x1 = min(x0 + max_w, maxx)
            strip = box(x0, miny, x1, maxy)
            piece = poly.intersection(strip).buffer(0)
            if not piece.is_empty and piece.area > AREA_EPS:
                out.append(_mk_custom(piece))
            x0 = x1
    return out

def validate_and_tag_customs(custom: List[Dict]) -> List[Dict]:
    """
    Regole custom: Type 1 ("larghezza"), Type 2 ("flex").
    AGGIORNATO: i blocchi custom possono nascere da tutti i tipi di blocco standard.
    """
    out = []
    max_standard_width = max(BLOCK_WIDTHS)  # 1239mm (blocco grande)
    
    for c in custom:
        w = int(round(c["width"]))
        h = int(round(c["height"]))
        
        # Controlla se supera i limiti massimi (fuori specifica)
        if w >= max_standard_width + SCARTO_CUSTOM_MM or h > 495 + SCARTO_CUSTOM_MM:
            c["ctype"] = "out_of_spec"
            out.append(c)
            continue
        
        # Type 1: blocchi derivati da qualsiasi blocco standard (altezza ≈ 495mm)
        # Ora può essere tagliato da blocchi piccoli, medi, grandi o standard
        if abs(h - 495) <= SCARTO_CUSTOM_MM and w <= max_standard_width + SCARTO_CUSTOM_MM:
            c["ctype"] = 1
        else:
            # Type 2: blocchi con altezza diversa (flex)
            c["ctype"] = 2
        
        out.append(c)
    return out

# ────────────────────────────────────────────────────────────────────────────────
# Labeling (NUOVO SISTEMA RAGGRUPPAMENTO)
# ────────────────────────────────────────────────────────────────────────────────

# Import del nuovo sistema di raggruppamento
try:
    from block_grouping import create_grouped_block_labels, get_block_category_summary, create_block_labels_legacy, group_blocks_by_category, group_custom_blocks_by_category
except ImportError:
    # Fallback se il modulo non è disponibile
    print("⚠️ Modulo block_grouping non disponibile, uso sistema legacy")
    create_grouped_block_labels = None
    get_block_category_summary = None
    create_block_labels_legacy = None

def create_block_labels(placed: List[Dict], custom: List[Dict]) -> Tuple[Dict[int, str], Dict[int, str]]:
    """
    Funzione principale per creare etichette blocchi.
    Usa il nuovo sistema di raggruppamento se disponibile, altrimenti fallback legacy.
    """
    if create_block_labels_legacy is not None:
        # Usa nuovo sistema raggruppato
        return create_block_labels_legacy(placed, custom)
    else:
        # Fallback sistema legacy
        return _create_block_labels_legacy_impl(placed, custom)

def create_detailed_block_labels(placed: List[Dict], custom: List[Dict]) -> Tuple[Dict[int, Dict], Dict[int, Dict]]:
    """
    Versione avanzata che restituisce informazioni dettagliate per il layout.
    Ogni etichetta include info per posizionamento layout (categoria BL + numero TR).
    """
    if create_grouped_block_labels is not None:
        return create_grouped_block_labels(placed, custom)
    else:
        # Fallback: converti etichette legacy in formato dettagliato
        std_labels, custom_labels = _create_block_labels_legacy_impl(placed, custom)
        
        # Converti in formato dettagliato per compatibilità
        detailed_std = {}
        detailed_custom = {}
        
        for i, label in std_labels.items():
            # Estrai categoria e numero da etichetta legacy (es: "A1" -> "A", "1")
            category = label[0] if len(label) > 0 else "X"
            number = label[1:] if len(label) > 1 else "1"
            
            detailed_std[i] = {
                'category': category,
                'number': int(number) if number.isdigit() else 1,
                'full_label': label,
                'display': {
                    'bottom_left': category,
                    'top_right': number,
                    'type': 'standard'
                }
            }
        
        for i, label in custom_labels.items():
            # Custom labels hanno formato "CU1(1)" -> categoria "D", numero "1"
            category = "D"  # Default per custom
            number = "1"
            
            detailed_custom[i] = {
                'category': category,
                'number': int(number),
                'full_label': label,
                'display': {
                    'bottom_left': category,
                    'top_right': number,
                    'type': 'custom'
                }
            }
        
        return detailed_std, detailed_custom

def _create_block_labels_legacy_impl(placed: List[Dict], custom: List[Dict]) -> Tuple[Dict[int, str], Dict[int, str]]:
    """Implementazione legacy del sistema di etichettatura."""
    std_counters = {"A": 0, "B": 0, "C": 0}
    std_labels: Dict[int, str] = {}

    for i, blk in enumerate(placed):
        letter = SIZE_TO_LETTER.get(int(blk["width"]), "X")
        if letter == "X":
            candidates = [(abs(int(blk["width"]) - k), v) for k, v in SIZE_TO_LETTER.items()]
            letter = sorted(candidates, key=lambda t: t[0])[0][1]
        std_counters[letter] += 1
        std_labels[i] = f"{letter}{std_counters[letter]}"

    # Robust: supporta ctype 1/2 e 'out_of_spec' -> 'X' → CUX(...)
    custom_labels: Dict[int, str] = {}
    counts = defaultdict(int)  # keys: 1, 2, 'X'
    for i, c in enumerate(custom):
        ctype = c.get("ctype", 2)
        code = ctype if isinstance(ctype, int) and ctype in (1, 2) else "X"
        counts[code] += 1
        custom_labels[i] = f"CU{code}({counts[code]})"
    return std_labels, custom_labels

# ────────────────────────────────────────────────────────────────────────────────
# Summary & export
# ────────────────────────────────────────────────────────────────────────────────
def summarize_blocks(placed: List[Dict], size_to_letter: Optional[Dict[int, str]] = None) -> Dict[str, int]:
    """
    Riassume blocchi standard raggruppando per tipo, con supporto per mapping personalizzato.
    
    Args:
        placed: Lista blocchi piazzati
        size_to_letter: Mapping opzionale da larghezza a lettera per dimensioni personalizzate
    """
    summary: Dict[str, int] = {}
    
    # Se abbiamo un mapping personalizzato, usa quello per correggere i tipi
    if size_to_letter:
        # Crea mapping intelligente: da larghezza effettiva a larghezza logica
        logical_widths = [int(w) for w in size_to_letter.keys()]
        logical_widths.sort(reverse=True)  # Ordina per dimensione decrescente [1500, 826, 413]
        
        # Trova tutte le larghezze effettive usate nei blocchi
        actual_widths = set()
        for blk in placed:
            if blk["type"].startswith("std_"):
                try:
                    parts = blk["type"].split("_")[1].split("x")
                    actual_width = int(parts[0])
                    actual_widths.add(actual_width)
                except (ValueError, IndexError):
                    pass
        
        actual_widths = sorted(actual_widths, reverse=True)  # Ordina per dimensione decrescente
        
        # Crea mapping: associa la larghezza effettiva più grande con quella logica più grande, etc.
        width_mapping = {}
        for i, actual_width in enumerate(actual_widths):
            if i < len(logical_widths):
                width_mapping[actual_width] = logical_widths[i]
                print(f"🔗 Mapping: {actual_width}mm → {logical_widths[i]}mm (logica)")
    
    for blk in placed:
        block_type = blk["type"]
        
        # Se abbiamo mapping personalizzato, correggi il tipo
        if size_to_letter and block_type.startswith("std_"):
            try:
                # Estrai larghezza dal tipo esistente (es. "std_1239x495" -> 1239)
                parts = block_type.split("_")[1].split("x")
                actual_width = int(parts[0])
                height = int(parts[1])
                
                # Usa il mapping per trovare la larghezza logica
                if actual_width in width_mapping:
                    logical_width = width_mapping[actual_width]
                    block_type = f"std_{logical_width}x{height}"
            except (ValueError, IndexError):
                pass  # Mantieni tipo originale se parsing fallisce
        
        summary[block_type] = summary.get(block_type, 0) + 1
    
    return summary

def export_to_json(summary: Dict[str, int], customs: List[Dict], placed: List[Dict], out_path: str = "distinta_wall.json", params: Optional[Dict] = None) -> str:
    # Usa il sistema di organizzazione automatica
    organized_path = get_organized_output_path(out_path, 'json')
    
    std_labels, custom_labels = create_block_labels(placed, customs)

    data = {
        "schema_version": "1.0",
        "units": "mm",
        "params": (params or {}),
        "standard": {
            std_labels[i]: {
                "type": p["type"],
                "width": int(p["width"]),
                "height": int(p["height"]),
                "x": int(round(p["x"])),
                "y": int(round(p["y"])),
            }
            for i, p in enumerate(placed)
        },
        "custom": [
            {
                "label": custom_labels[i],
                "ctype": c.get("ctype", 2),
                "width": int(round(c["width"])),
                "height": int(round(c["height"])),
                "x": int(round(c["x"])),
                "y": int(round(c["y"])),
                "geometry": c["geometry"],
            }
            for i, c in enumerate(customs)
        ],
        "totals": {
            "standard_counts": summary,
            "custom_count": len(customs)
        }
    }

    with open(organized_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)
    return organized_path

# ────────────────────────────────────────────────────────────────────────────────
# Generate preview image
# ────────────────────────────────────────────────────────────────────────────────
def generate_preview_image(wall_polygon: Polygon, 
                          placed: List[Dict], 
                          customs: List[Dict],
                          apertures: Optional[List[Polygon]] = None,
                          color_theme: Optional[Dict] = None,
                          width: int = 800,
                          height: int = 600) -> str:
    """Genera immagine preview come base64 string."""
    if not plt or not patches:
        return ""
    
    # Default colors se theme non fornito
    if not color_theme:
        color_theme = {}
    
    # Extract colors with fallbacks
    wall_color = color_theme.get('wallOutlineColor', '#1E40AF')
    wall_line_width = color_theme.get('wallLineWidth', 2)
    standard_block_color = color_theme.get('standardBlockColor', '#E5E7EB')
    standard_block_border = color_theme.get('standardBlockBorder', '#374151')
    custom_piece_color = color_theme.get('customPieceColor', '#F3E8FF')
    custom_piece_border = color_theme.get('customPieceBorder', '#7C3AED')
    door_window_color = color_theme.get('doorWindowColor', '#FEE2E2')
    door_window_border = color_theme.get('doorWindowBorder', '#DC2626')
    
    print(f"🎨 [DEBUG] Preview using colors: wall={wall_color}, blocks={standard_block_color}")
        
    try:
        # Setup figura
        fig, ax = plt.subplots(figsize=(width/100, height/100), dpi=100)
        ax.set_aspect('equal')
        
        # Bounds parete
        minx, miny, maxx, maxy = wall_polygon.bounds
        margin = max((maxx-minx), (maxy-miny)) * 0.05
        ax.set_xlim(minx - margin, maxx + margin)
        ax.set_ylim(miny - margin, maxy + margin)
        
        # Contorno parete
        x, y = wall_polygon.exterior.xy
        ax.plot(x, y, color=wall_color, linewidth=wall_line_width, label='Parete')
        
        # Labels per blocchi - NUOVO SISTEMA RAGGRUPPATO
        detailed_std_labels, detailed_custom_labels = create_detailed_block_labels(placed, customs)
        
        # Blocchi standard con nuovo layout
        for i, blk in enumerate(placed):
            rect = patches.Rectangle(
                (blk['x'], blk['y']), blk['width'], blk['height'],
                facecolor=standard_block_color, edgecolor=standard_block_border, linewidth=0.5
            )
            ax.add_patch(rect)
            
            # Layout nuovo: categoria BL + numero TR (per immagini adattato)
            if i in detailed_std_labels:
                label_info = detailed_std_labels[i]
                category = label_info['display']['bottom_left']
                number = label_info['display']['top_right']
                
                # Posizioni adattate per preview
                bl_x = blk['x'] + blk['width'] * 0.1   # 10% da sinistra
                bl_y = blk['y'] + blk['height'] * 0.2  # 20% dal basso
                tr_x = blk['x'] + blk['width'] * 0.9   # 90% da sinistra 
                tr_y = blk['y'] + blk['height'] * 0.8  # 80% dal basso
                
                # Categoria (più grande)
                fontsize_cat = min(12, max(6, blk['width'] / 150))
                ax.text(bl_x, bl_y, category, ha='left', va='bottom',
                       fontsize=fontsize_cat, fontweight='bold', color='#dc2626')
                
                # Numero (più piccolo)
                fontsize_num = min(10, max(4, blk['width'] / 200))
                ax.text(tr_x, tr_y, number, ha='right', va='top',
                       fontsize=fontsize_num, fontweight='normal', color='#2563eb')
            else:
                # Fallback: etichetta centrata
                std_labels, _ = create_block_labels(placed, customs)
                cx = blk['x'] + blk['width'] / 2
                cy = blk['y'] + blk['height'] / 2
                fontsize = min(8, max(4, blk['width'] / 200))
                ax.text(cx, cy, std_labels.get(i, f"STD{i+1}"), ha='center', va='center', 
                       fontsize=fontsize, fontweight='bold', color='#1f2937')
        
        # Blocchi custom con nuovo layout
        for i, cust in enumerate(customs):
            try:
                poly = shape(cust['geometry'])
                patch = patches.Polygon(
                    list(poly.exterior.coords),
                    facecolor=custom_piece_color, edgecolor=custom_piece_border, 
                    linewidth=0.8, hatch='//', alpha=0.8
                )
                ax.add_patch(patch)
                
                # Layout nuovo: categoria BL + numero TR per custom
                if i in detailed_custom_labels:
                    label_info = detailed_custom_labels[i]
                    category = label_info['display']['bottom_left'] 
                    number = label_info['display']['top_right']
                    
                    # Posizioni adattate per preview custom
                    bl_x = cust['x'] + cust['width'] * 0.1
                    bl_y = cust['y'] + cust['height'] * 0.2
                    tr_x = cust['x'] + cust['width'] * 0.9
                    tr_y = cust['y'] + cust['height'] * 0.8
                    
                    # Categoria custom (verde)
                    fontsize_cat = min(10, max(5, cust['width'] / 120))
                    ax.text(bl_x, bl_y, category, ha='left', va='bottom',
                           fontsize=fontsize_cat, fontweight='bold', color='#16a34a')
                    
                    # Numero custom (più piccolo)
                    fontsize_num = min(8, max(4, cust['width'] / 150))
                    ax.text(tr_x, tr_y, number, ha='right', va='top',
                           fontsize=fontsize_num, fontweight='normal', color='#065f46')
                else:
                    # Fallback: etichetta centrata
                    _, custom_labels_fallback = create_block_labels([], customs)
                    cx = cust['x'] + cust['width'] / 2
                    cy = cust['y'] + cust['height'] / 2
                    label = custom_labels_fallback.get(i, f"CU{i+1}")
                    ax.text(cx, cy, label, ha='center', va='center', 
                           fontsize=6, fontweight='bold', color='#15803d')
            except Exception as e:
                print(f"⚠️ Errore rendering custom {i}: {e}")
        
        # Aperture
        if apertures:
            for ap in apertures:
                x, y = ap.exterior.xy
                ax.plot(x, y, color=door_window_border, linestyle='--', linewidth=2)
                ax.fill(x, y, color=door_window_color, alpha=0.15)
        
        # Styling
        ax.set_title('Preview Costruzione Parete', fontsize=12, fontweight='bold', color='#1f2937')
        ax.grid(True, alpha=0.3, color='#9ca3af')
        ax.tick_params(axis='both', which='major', labelsize=8, colors='#6b7280')
        
        # Salva in memoria come base64
        img_buffer = io.BytesIO()
        fig.savefig(img_buffer, format='png', dpi=100, bbox_inches='tight', 
                   facecolor='white', edgecolor='none', pad_inches=0.1)
        img_buffer.seek(0)
        plt.close(fig)
        
        # Converti in base64
        img_base64 = base64.b64encode(img_buffer.getvalue()).decode('utf-8')
        return f"data:image/png;base64,{img_base64}"
        
    except Exception as e:
        print(f"⚠️ Errore generazione preview: {e}")
        return ""

# ────────────────────────────────────────────────────────────────────────────────
# PDF Export (IMPLEMENTAZIONE COMPLETA - mantenuta identica)
# ────────────────────────────────────────────────────────────────────────────────
def export_to_pdf(summary: Dict[str, int], 
                  customs: List[Dict], 
                  placed: List[Dict], 
                  wall_polygon: Polygon,
                  apertures: Optional[List[Polygon]] = None,
                  project_name: str = "Progetto Parete",
                  out_path: str = "report_parete.pdf",
                  params: Optional[Dict] = None) -> str:
    """
    Genera un PDF completo con schema parete + tabelle riassuntive.
    """
    if not reportlab_available:
        raise RuntimeError("reportlab non disponibile. Installa con: pip install reportlab")
    
    # Usa il sistema di organizzazione automatica
    organized_path = get_organized_output_path(out_path, 'pdf')
    
    try:
        # Setup documento
        doc = SimpleDocTemplate(
            organized_path,
            pagesize=A4,
            rightMargin=20*mm,
            leftMargin=20*mm,
            topMargin=25*mm,
            bottomMargin=25*mm
        )
        
        # Raccogli tutti gli elementi
        story = []
        styles = getSampleStyleSheet()
        
        # === PAGINA 1: HEADER + SCHEMA GRAFICO ===
        story.extend(_build_pdf_header(project_name, summary, customs, styles))
        story.append(Spacer(1, 10*mm))
        
        # Schema grafico principale  
        schema_image = _generate_wall_schema_image(wall_polygon, placed, customs, apertures)
        if schema_image:
            story.append(schema_image)
        
        story.append(Spacer(1, 10*mm))
        
        # === TABELLA BLOCCHI STANDARD ===
        if summary:
            story.append(_build_standard_blocks_table(summary, placed, styles))
            story.append(Spacer(1, 8*mm))
        
        # === PAGINA 2: TABELLA CUSTOM (se presente) ===
        if customs:
            story.append(PageBreak())
            story.append(_build_custom_blocks_table(customs, styles))
            story.append(Spacer(1, 8*mm))
        
        # === INFO TECNICHE ===
        if params:
            story.append(_build_technical_info(params, styles))
        
        # Genera PDF
        doc.build(story)
        print(f"✅ PDF generato: {organized_path}")
        return organized_path
        
    except Exception as e:
        print(f"❌ Errore generazione PDF: {e}")
        raise


def _build_pdf_header(project_name: str, summary: Dict[str, int], customs: List[Dict], styles) -> List:
    """Costruisce header del PDF con info progetto."""
    elements = []
    
    # Titolo principale
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Title'],
        fontSize=18,
        spaceAfter=6*mm,
        alignment=TA_CENTER,
        textColor=black
    )
    elements.append(Paragraph(f"<b>{project_name}</b>", title_style))
    
    # Sottotitolo con data
    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Normal'],
        fontSize=12,
        alignment=TA_CENTER,
        textColor=gray,
        spaceAfter=8*mm
    )
    now = datetime.datetime.now()
    elements.append(Paragraph(f"Distinta Base Blocchi - {now.strftime('%d/%m/%Y %H:%M')}", subtitle_style))
    
    # Box riassuntivo
    total_standard = sum(summary.values())
    total_custom = len(customs)
    
    summary_data = [
        ['RIEPILOGO PROGETTO', ''],
        ['Blocchi Standard Totali:', f"{total_standard}"],
        ['Pezzi Custom Totali:', f"{total_custom}"],
        ['Efficienza:', f"{total_standard/(total_standard+total_custom)*100:.1f}%" if total_standard+total_custom > 0 else "N/A"]
    ]
    
    summary_table = Table(summary_data, colWidths=[80*mm, 40*mm])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, 0), black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    
    elements.append(summary_table)
    return elements


def _generate_wall_schema_image(wall_polygon: Polygon, 
                               placed: List[Dict], 
                               customs: List[Dict],
                               apertures: Optional[List[Polygon]] = None) -> Optional[Image]:
    """Genera immagine dello schema parete per il PDF."""
    if not plt or not patches:
        return None
        
    try:
        # Setup figura ad alta risoluzione per PDF
        fig, ax = plt.subplots(figsize=(180/25.4, 120/25.4), dpi=200)
        ax.set_aspect('equal')
        
        # Bounds parete
        minx, miny, maxx, maxy = wall_polygon.bounds
        margin = max((maxx-minx), (maxy-miny)) * 0.05
        ax.set_xlim(minx - margin, maxx + margin)
        ax.set_ylim(miny - margin, maxy + margin)
        
        # Contorno parete
        x, y = wall_polygon.exterior.xy
        ax.plot(x, y, color='blue', linewidth=2, label='Contorno parete')
        
        # Labels per blocchi con nuovo sistema di raggruppamento
        std_labels, custom_labels = create_grouped_block_labels(placed, customs)
        
        # Blocchi standard
        for i, blk in enumerate(placed):
            rect = patches.Rectangle(
                (blk['x'], blk['y']), blk['width'], blk['height'],
                facecolor='lightgray', edgecolor='black', linewidth=0.5
            )
            ax.add_patch(rect)
            
            # Nuovo layout: lettera in basso a sinistra, numero in alto a destra
            label_info = std_labels[i]
            category = label_info['category']
            number = label_info['number']
            
            # Posizioni per lettera e numero
            margin = 3  # pixel di margine
            
            # Lettera in basso a sinistra
            fontsize_letter = min(10, max(6, blk['width'] / 150))
            ax.text(blk['x'] + margin, blk['y'] + margin, category, 
                   ha='left', va='bottom', fontsize=fontsize_letter, 
                   fontweight='bold', color='black',
                   bbox=dict(boxstyle="round,pad=0.1", facecolor='white', alpha=0.9))
            
            # Numero in alto a destra
            fontsize_number = min(8, max(5, blk['width'] / 200))
            ax.text(blk['x'] + blk['width'] - margin, blk['y'] + blk['height'] - margin, 
                   str(number), ha='right', va='top', fontsize=fontsize_number, 
                   fontweight='bold', color='red',
                   bbox=dict(boxstyle="round,pad=0.1", facecolor='white', alpha=0.9))
        
        # Blocchi custom
        for i, cust in enumerate(customs):
            try:
                poly = shape(cust['geometry'])
                patch = patches.Polygon(
                    list(poly.exterior.coords),
                    facecolor='lightgreen', edgecolor='green', 
                    linewidth=0.8, hatch='//', alpha=0.7
                )
                ax.add_patch(patch)
                
                # Label custom con nuovo layout
                label_info = custom_labels[i]
                category = label_info['category']
                number = label_info['number']
                
                margin = 3
                
                # Lettera in basso a sinistra
                fontsize_letter = min(8, max(5, cust['width'] / 150))
                ax.text(cust['x'] + margin, cust['y'] + margin, category, 
                       ha='left', va='bottom', fontsize=fontsize_letter, 
                       fontweight='bold', color='darkgreen',
                       bbox=dict(boxstyle="round,pad=0.1", facecolor='white', alpha=0.9))
                
                # Numero in alto a destra
                fontsize_number = min(6, max(4, cust['width'] / 200))
                ax.text(cust['x'] + cust['width'] - margin, cust['y'] + cust['height'] - margin, 
                       str(number), ha='right', va='top', fontsize=fontsize_number, 
                       fontweight='bold', color='red',
                       bbox=dict(boxstyle="round,pad=0.1", facecolor='white', alpha=0.9))
            except Exception as e:
                print(f"⚠️ Errore rendering custom {i}: {e}")
        
        # Aperture
        if apertures:
            for ap in apertures:
                x, y = ap.exterior.xy
                ax.plot(x, y, color='red', linestyle='--', linewidth=2)
                ax.fill(x, y, color='red', alpha=0.15)
        
        # Styling
        ax.set_title('Schema Costruttivo Parete', fontsize=12, fontweight='bold', pad=10)
        ax.legend(loc='upper right', fontsize=8)
        ax.grid(True, alpha=0.3)
        ax.set_xlabel('mm', fontsize=8)
        ax.set_ylabel('mm', fontsize=8)
        
        # Salva in memoria
        img_buffer = io.BytesIO()
        fig.savefig(img_buffer, format='png', dpi=200, bbox_inches='tight', 
                   facecolor='white', edgecolor='none')
        img_buffer.seek(0)
        plt.close(fig)
        
        # Converti in Image ReportLab
        return Image(img_buffer, width=170*mm, height=110*mm)
        
    except Exception as e:
        print(f"⚠️ Errore generazione schema: {e}")
        return None


def _build_standard_blocks_table(summary: Dict[str, int], placed: List[Dict], styles) -> Table:
    """Costruisce tabella blocchi standard con nuovo sistema di raggruppamento."""
    # Header
    data = [['CATEGORIA', 'QUANTITÀ', 'DIMENSIONI (mm)', 'AREA TOT (m²)']]
    
    # Usa il nuovo sistema di raggruppamento
    grouped_blocks = group_blocks_by_category(placed)
    
    total_area = 0
    total_count = 0
    
    # Ordina le categorie alfabeticamente
    for category in sorted(grouped_blocks.keys()):
        blocks_in_category = grouped_blocks[category]
        count = len(blocks_in_category)
        
        # Prendi le dimensioni dal primo blocco della categoria (sono tutti uguali)
        first_block = blocks_in_category[0]
        width = first_block['width']
        height = first_block['height']
        
        area_m2 = (width * height * count) / 1_000_000
        total_area += area_m2
        total_count += count
        
        data.append([
            f"Categoria {category}",
            str(count),
            f"{width} × {height}",
            f"{area_m2:.2f}"
        ])
    
    # Totale
    data.append(['TOTALE', str(total_count), '', f"{total_area:.2f}"])
    
    table = Table(data, colWidths=[60*mm, 25*mm, 40*mm, 25*mm])
    table.setStyle(TableStyle([
        # Header
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        # Dati
        ('FONTNAME', (0, 1), (-1, -2), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -2), 9),
        ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
        # Totale
        ('BACKGROUND', (0, -1), (-1, -1), colors.lightblue),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        # Bordi
        ('GRID', (0, 0), (-1, -1), 1, black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    
    return table


def _build_custom_blocks_table(customs: List[Dict], styles) -> Table:
    """Costruisce tabella pezzi custom con nuovo sistema di raggruppamento."""
    # Header
    data = [['CATEGORIA CUSTOM', 'QUANTITÀ', 'DIMENSIONI (mm)', 'AREA TOT (m²)']]
    
    # Usa il nuovo sistema di raggruppamento per custom
    grouped_customs = group_custom_blocks_by_category(customs)
    
    total_area = 0
    total_count = 0
    
    # Ordina le categorie alfabeticamente
    for category in sorted(grouped_customs.keys()):
        blocks_in_category = grouped_customs[category]
        count = len(blocks_in_category)
        
        # Prendi le dimensioni dal primo blocco della categoria
        first_block = blocks_in_category[0]
        width = first_block['width']
        height = first_block['height']
        
        area_m2 = (width * height * count) / 1_000_000
        total_area += area_m2
        total_count += count
        
        # Determina il tipo
        ctype = first_block.get('ctype', 2)
        type_str = f"CU{ctype}" if ctype in [1, 2] else "CUX"
        
        data.append([
            f"Categoria {category} ({type_str})",
            str(count),
            f"{width:.0f} × {height:.0f}",
            f"{area_m2:.3f}"
        ])
    
    # Totale
    data.append(['TOTALE', str(total_count), '', f"{total_area:.3f}"])
    
    table = Table(data, colWidths=[35*mm, 20*mm, 35*mm, 35*mm, 25*mm])
    table.setStyle(TableStyle([
        # Header
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkgreen),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        # Dati
        ('FONTNAME', (0, 1), (-1, -2), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -2), 8),
        ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
        # Totale
        ('BACKGROUND', (0, -1), (-1, -1), colors.lightgreen),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        # Bordi
        ('GRID', (0, 0), (-1, -1), 1, black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    
    return table


def _build_technical_info(params: Dict, styles) -> Table:
    """Costruisce tabella info tecniche."""
    data = [['PARAMETRI TECNICI', 'VALORE']]
    
    # Formatta parametri leggibili
    readable_params = [
        ('Algoritmo Packing', 'Greedy + Backtrack'),
        ('Altezza Blocco Standard', f"{params.get('block_height_mm', 495)} mm"),
        ('Larghezze Blocchi', f"{params.get('block_widths_mm', [])}"),
        ('Offset Righe Dispari', f"{params.get('row_offset_mm', 'Auto')} mm"),
        ('Griglia Snap', f"{params.get('snap_mm', 1)} mm"),
        ('Margine Aperture', f"{params.get('keep_out_mm', 2)} mm"),
        ('Merge Custom Row-Aware', f"{params.get('row_aware_merge', True)}"),
        ('Max Larghezza Custom', f"{params.get('split_max_width_mm', 413)} mm"),
    ]
    
    for label, value in readable_params:
        data.append([label, str(value)])
    
    table = Table(data, colWidths=[80*mm, 60*mm])
    table.setStyle(TableStyle([
        # Header
        ('BACKGROUND', (0, 0), (-1, 0), colors.orange),
        ('TEXTCOLOR', (0, 0), (-1, 0), black),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        # Dati
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('ALIGN', (1, 1), (-1, -1), 'LEFT'),
        # Bordi
        ('GRID', (0, 0), (-1, -1), 1, black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    
    return table

# ────────────────────────────────────────────────────────────────────────────────
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
                session["config"].get("color_theme", {})
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
                    params=build_run_params(session["config"]["row_offset"])
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
                    params=build_run_params(session["config"]["row_offset"])
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
                    color_theme=session["config"].get("color_theme", {})
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
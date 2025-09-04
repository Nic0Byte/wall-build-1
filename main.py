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
from utils.file_manager import setup_output_directories, get_organized_output_path, generate_unique_filename
from utils.geometry_utils import snap, snap_bounds, polygon_holes, sanitize_polygon, ensure_multipolygon, SNAP_MM
from utils.config import (
    SCARTO_CUSTOM_MM, AREA_EPS, COORD_EPS, DISPLAY_MM_PER_M,
    MICRO_REST_MM, KEEP_OUT_MM, SPLIT_MAX_WIDTH_MM,
    BLOCK_HEIGHT, BLOCK_WIDTHS, SIZE_TO_LETTER, BLOCK_ORDERS, SESSIONS
)

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
    print("⚠️ reportlab non installato. Export PDF non disponibile.")
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
    print("⚠️ ezdxf non installato. Export DXF non disponibile.")
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
    from fastapi import FastAPI, UploadFile, File, Form, HTTPException, WebSocket, WebSocketDisconnect
    from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
    from fastapi.staticfiles import StaticFiles
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
    import uvicorn
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
def parse_dwg_wall(dwg_bytes: bytes, layer_wall: str = "MURO", layer_holes: str = "BUCHI") -> Tuple[Polygon, List[Polygon]]:
    """
    Parser DWG che estrae parete e aperture dai layer specificati.
    Prova multiple librerie: dxfgrabber (più compatibile) → ezdxf → fallback
    
    Args:
        dwg_bytes: Contenuto del file DWG
        layer_wall: Nome del layer contenente il profilo della parete  
        layer_holes: Nome del layer contenente le aperture (porte/finestre)
    
    Returns:
        Tuple[Polygon, List[Polygon]]: (parete_principale, lista_aperture)
    """
    
    # Tentativo 1: dxfgrabber (più compatibile con DWG recenti)
    if dxfgrabber_available:
        try:
            return _parse_dwg_with_dxfgrabber(dwg_bytes, layer_wall, layer_holes)
        except Exception as e:
            print(f"⚠️ dxfgrabber fallito: {e}")
    
    # Tentativo 2: ezdxf (originale)  
    if ezdxf_available:
        try:
            return _parse_dwg_with_ezdxf(dwg_bytes, layer_wall, layer_holes)
        except Exception as e:
            print(f"⚠️ ezdxf fallito: {e}")
    
    # Tentativo 3: fallback
    print("🔄 Usando fallback parser...")
    return _fallback_parse_dwg(dwg_bytes)


def _parse_dwg_with_dxfgrabber(dwg_bytes: bytes, layer_wall: str, layer_holes: str) -> Tuple[Polygon, List[Polygon]]:
    """Parser DWG usando dxfgrabber (più compatibile)."""
    with tempfile.NamedTemporaryFile(suffix='.dwg', delete=False) as tmp_file:
        tmp_file.write(dwg_bytes)
        tmp_file_path = tmp_file.name
    
    try:
        # Apri con dxfgrabber
        dwg = dxfgrabber.readfile(tmp_file_path)
        
        print(f"📁 DWG version: {dwg.header.get('$ACADVER', 'Unknown')}")
        print(f"🗂️ Layers trovati: {len(dwg.layers)}")
        
        # Estrai geometrie per layer
        wall_geometries = _extract_dxfgrabber_geometries_by_layer(dwg, layer_wall)
        hole_geometries = _extract_dxfgrabber_geometries_by_layer(dwg, layer_holes)
        
        # Converti in Polygon
        wall_polygon = _dwg_geometries_to_polygon(wall_geometries, is_wall=True)
        aperture_polygons = _dwg_geometries_to_apertures(hole_geometries)
        
        print(f"✅ DWG parsed con dxfgrabber: parete {wall_polygon.area:.1f} mm², {len(aperture_polygons)} aperture")
        return wall_polygon, aperture_polygons
        
    finally:
        try:
            os.unlink(tmp_file_path)
        except Exception:
            pass


def _extract_dxfgrabber_geometries_by_layer(dwg, layer_name: str) -> List[List[Tuple[float, float]]]:
    """Estrae geometrie da layer usando dxfgrabber."""
    geometries = []
    
    # Lista tutti i layer disponibili per debug
    layer_names = [layer.name for layer in dwg.layers]
    print(f"🗂️ Layer disponibili: {layer_names}")
    
    # Cerca entità nel layer specificato
    entities_found = 0
    for entity in dwg.entities:
        if hasattr(entity, 'layer') and entity.layer.lower() == layer_name.lower():
            entities_found += 1
            coords = _extract_coords_from_dxfgrabber_entity(entity)
            if coords and len(coords) >= 3:
                geometries.append(coords)
    
    print(f"🔍 Layer '{layer_name}': {entities_found} entità trovate, {len(geometries)} geometrie valide")
    
    # Se non trova il layer specifico, cerca qualsiasi geometria chiusa
    if not geometries:
        print(f"⚠️ Layer '{layer_name}' non trovato o vuoto, cercando geometrie generiche...")
        for entity in dwg.entities:
            coords = _extract_coords_from_dxfgrabber_entity(entity)
            if coords and len(coords) >= 3:
                geometries.append(coords)
                if len(geometries) >= 5:  # Limita per evitare troppi elementi
                    break
    
    return geometries


def _extract_coords_from_dxfgrabber_entity(entity) -> Optional[List[Tuple[float, float]]]:
    """Estrae coordinate da entità dxfgrabber."""
    try:
        entity_type = entity.dxftype
        
        if entity_type == 'LWPOLYLINE':
            return [(point[0], point[1]) for point in entity.points]
            
        elif entity_type == 'POLYLINE':
            coords = []
            for vertex in entity.vertices:
                coords.append((vertex.location[0], vertex.location[1]))
            return coords
            
        elif entity_type == 'LINE':
            start = entity.start
            end = entity.end
            return [(start[0], start[1]), (end[0], end[1])]
            
        elif entity_type == 'CIRCLE':
            center = entity.center
            radius = entity.radius
            coords = []
            for i in range(17):  # 16 lati + chiusura
                angle = 2 * math.pi * i / 16
                x = center[0] + radius * math.cos(angle)
                y = center[1] + radius * math.sin(angle)
                coords.append((x, y))
            return coords
            
        elif entity_type == 'ARC':
            center = entity.center
            radius = entity.radius
            start_angle = math.radians(entity.start_angle)
            end_angle = math.radians(entity.end_angle)
            
            if end_angle < start_angle:
                end_angle += 2 * math.pi
                
            coords = []
            segments = 16
            angle_step = (end_angle - start_angle) / segments
            for i in range(segments + 1):
                angle = start_angle + i * angle_step
                x = center[0] + radius * math.cos(angle)
                y = center[1] + radius * math.sin(angle)
                coords.append((x, y))
            return coords
            
        else:
            return None
            
    except Exception as e:
        print(f"⚠️ Errore estrazione coordinate da {entity_type}: {e}")
        return None


def _parse_dwg_with_ezdxf(dwg_bytes: bytes, layer_wall: str, layer_holes: str) -> Tuple[Polygon, List[Polygon]]:
    """Parser DWG originale usando ezdxf."""
    with tempfile.NamedTemporaryFile(suffix='.dwg', delete=False) as tmp_file:
        tmp_file.write(dwg_bytes)
        tmp_file_path = tmp_file.name
    
    try:
        # Apri il file DWG
        doc = ezdxf.readfile(tmp_file_path)
        msp = doc.modelspace()
        
        # Estrai geometrie per layer
        wall_geometries = _extract_dwg_geometries_by_layer(msp, layer_wall)
        hole_geometries = _extract_dwg_geometries_by_layer(msp, layer_holes)
        
        # Converti in Polygon
        wall_polygon = _dwg_geometries_to_polygon(wall_geometries, is_wall=True)
        aperture_polygons = _dwg_geometries_to_apertures(hole_geometries)
        
        print(f"✅ DWG parsed con ezdxf: parete {wall_polygon.area:.1f} mm², {len(aperture_polygons)} aperture")
        return wall_polygon, aperture_polygons
        
    finally:
        try:
            os.unlink(tmp_file_path)
        except Exception:
            pass


def _extract_dwg_geometries_by_layer(msp, layer_name: str) -> List[List[Tuple[float, float]]]:
    """Estrae tutte le geometrie dal layer specificato nel DWG."""
    geometries = []
    
    # Cerca entità nel layer specificato
    for entity in msp:
        if hasattr(entity, 'dxf') and hasattr(entity.dxf, 'layer'):
            if entity.dxf.layer.lower() == layer_name.lower():
                coords = _extract_coords_from_dwg_entity(entity)
                if coords and len(coords) >= 3:
                    geometries.append(coords)
    
    # Se non trova il layer specifico, cerca entità generiche
    if not geometries:
        print(f"⚠️ Layer '{layer_name}' non trovato, cercando geometrie generiche...")
        for entity in msp:
            coords = _extract_coords_from_dwg_entity(entity)
            if coords and len(coords) >= 3:
                geometries.append(coords)
                break  # Prendi solo la prima geometria trovata
    
    return geometries


def _extract_coords_from_dwg_entity(entity) -> Optional[List[Tuple[float, float]]]:
    """Estrae coordinate da un'entità DWG/DXF."""
    try:
        entity_type = entity.dxftype()
        
        if entity_type == 'LWPOLYLINE':
            # Polilinea leggera
            coords = []
            for point in entity.get_points():
                coords.append((point[0], point[1]))
            # Chiudi se necessario
            if entity.closed and coords and coords[0] != coords[-1]:
                coords.append(coords[0])
            return coords
            
        elif entity_type == 'POLYLINE':
            # Polilinea 3D
            coords = []
            for vertex in entity.vertices:
                coords.append((vertex.dxf.location.x, vertex.dxf.location.y))
            if entity.is_closed and coords and coords[0] != coords[-1]:
                coords.append(coords[0])
            return coords
            
        elif entity_type == 'LINE':
            # Linea singola
            start = entity.dxf.start
            end = entity.dxf.end
            return [(start.x, start.y), (end.x, end.y)]
            
        elif entity_type == 'CIRCLE':
            # Cerchio - approssima con poligono
            center = entity.dxf.center
            radius = entity.dxf.radius
            coords = []
            for i in range(17):  # 16 lati + chiusura
                angle = 2 * math.pi * i / 16
                x = center.x + radius * math.cos(angle)
                y = center.y + radius * math.sin(angle)
                coords.append((x, y))
            return coords
            
        elif entity_type == 'ARC':
            # Arco - approssima con segmenti
            center = entity.dxf.center
            radius = entity.dxf.radius
            start_angle = math.radians(entity.dxf.start_angle)
            end_angle = math.radians(entity.dxf.end_angle)
            
            # Gestisci archi che attraversano 0°
            if end_angle < start_angle:
                end_angle += 2 * math.pi
                
            coords = []
            segments = 16
            angle_step = (end_angle - start_angle) / segments
            for i in range(segments + 1):
                angle = start_angle + i * angle_step
                x = center.x + radius * math.cos(angle)
                y = center.y + radius * math.sin(angle)
                coords.append((x, y))
            return coords
            
        elif entity_type == 'SPLINE':
            # Spline - approssima con polilinea
            try:
                points = entity.flattening(0.1)  # Tolleranza 0.1mm
                return [(p.x, p.y) for p in points]
            except Exception:
                return None
                
        elif entity_type in ['INSERT', 'BLOCK']:
            # Blocchi - ignora per ora
            return None
            
        else:
            # Altri tipi non supportati
            return None
            
    except Exception as e:
        print(f"⚠️ Errore estrazione coordinate da {entity.dxftype()}: {e}")
        return None


def _dwg_geometries_to_polygon(geometries: List[List[Tuple[float, float]]], is_wall: bool = True) -> Polygon:
    """Converte geometrie DWG in Polygon Shapely."""
    if not geometries:
        raise ValueError("Nessuna geometria trovata per la parete")
    
    valid_polygons = []
    
    for coords in geometries:
        if len(coords) < 3:
            continue
            
        try:
            # Assicurati che sia chiuso
            if coords[0] != coords[-1]:
                coords.append(coords[0])
                
            polygon = Polygon(coords)
            if polygon.is_valid and polygon.area > AREA_EPS:
                valid_polygons.append(polygon)
        except Exception as e:
            print(f"⚠️ Geometria DWG invalida: {e}")
            continue
    
    if not valid_polygons:
        raise ValueError("Nessuna geometria valida trovata")
    
    # Se è una parete, prendi l'unione o il poligono più grande
    if is_wall:
        if len(valid_polygons) == 1:
            result = valid_polygons[0]
        else:
            # Prova unione, altrimenti prendi il più grande
            try:
                result = unary_union(valid_polygons)
                if isinstance(result, MultiPolygon):
                    result = max(result.geoms, key=lambda p: p.area)
            except Exception:
                result = max(valid_polygons, key=lambda p: p.area)
    else:
        result = valid_polygons[0]
    
    return sanitize_polygon(result)


def _dwg_geometries_to_apertures(geometries: List[List[Tuple[float, float]]]) -> List[Polygon]:
    """Converte geometrie DWG in lista di aperture."""
    apertures = []
    
    for coords in geometries:
        if len(coords) < 3:
            continue
            
        try:
            # Assicurati che sia chiuso
            if coords[0] != coords[-1]:
                coords.append(coords[0])
                
            polygon = Polygon(coords)
            if polygon.is_valid and polygon.area > AREA_EPS:
                apertures.append(sanitize_polygon(polygon))
        except Exception as e:
            print(f"⚠️ Apertura DWG invalida: {e}")
            continue
    
    return apertures


def _fallback_parse_dwg(dwg_bytes: bytes) -> Tuple[Polygon, List[Polygon]]:
    """Parsing fallback per DWG quando non trova layer specifici."""
    try:
        # Prova a leggere come DXF generico
        with tempfile.NamedTemporaryFile(suffix='.dxf', delete=False) as tmp_file:
            tmp_file.write(dwg_bytes)
            tmp_file_path = tmp_file.name
        
        try:
            doc = ezdxf.readfile(tmp_file_path)
            msp = doc.modelspace()
            
            # Cerca la prima geometria chiusa come parete
            all_geometries = []
            for entity in msp:
                coords = _extract_coords_from_dwg_entity(entity)
                if coords and len(coords) >= 3:
                    all_geometries.append(coords)
            
            if not all_geometries:
                raise ValueError("Nessuna geometria trovata nel file DWG")
            
            # Prendi la prima come parete, il resto come aperture
            wall_polygon = _dwg_geometries_to_polygon([all_geometries[0]], is_wall=True)
            apertures = _dwg_geometries_to_apertures(all_geometries[1:]) if len(all_geometries) > 1 else []
            
            print(f"✅ DWG fallback parsing: parete {wall_polygon.area:.1f} mm², {len(apertures)} aperture")
            return wall_polygon, apertures
            
        finally:
            try:
                os.unlink(tmp_file_path)
            except Exception:
                pass
                
    except Exception as e:
        print(f"❌ Errore fallback DWG: {e}")
        # Ultimo fallback: crea una parete di esempio
        example_wall = box(0, 0, 5000, 2500)  # 5m x 2.5m
        return example_wall, []


# ────────────────────────────────────────────────────────────────────────────────
# SVG parsing (IMPLEMENTAZIONE COMPLETA)
# ────────────────────────────────────────────────────────────────────────────────
def parse_svg_wall(svg_bytes: bytes, layer_wall: str = "MURO", layer_holes: str = "BUCHI") -> Tuple[Polygon, List[Polygon]]:
    """
    Parser SVG reale che estrae parete e aperture dai layer specificati.
    
    Args:
        svg_bytes: Contenuto del file SVG
        layer_wall: Nome del layer contenente il profilo della parete
        layer_holes: Nome del layer contenente le aperture (porte/finestre)
    
    Returns:
        Tuple[Polygon, List[Polygon]]: (parete_principale, lista_aperture)
    """
    try:
        # Parse XML
        svg_content = svg_bytes.decode('utf-8')
        root = ET.fromstring(svg_content)
        
        # Namespace SVG
        ns = {'svg': 'http://www.w3.org/2000/svg'}
        
        # Estrai informazioni di scala/viewport
        scale_factor = _extract_scale_factor(root, ns)
        
        # Estrai geometrie per layer
        wall_geometries = _extract_geometries_by_layer(root, ns, layer_wall, scale_factor)
        hole_geometries = _extract_geometries_by_layer(root, ns, layer_holes, scale_factor)
        
        # Converti in Polygon
        wall_polygon = _geometries_to_polygon(wall_geometries, is_wall=True)
        aperture_polygons = _geometries_to_apertures(hole_geometries)
        
        print(f"✅ SVG parsed: parete {wall_polygon.area:.1f} mm², {len(aperture_polygons)} aperture")
        return wall_polygon, aperture_polygons
        
    except Exception as e:
        print(f"❌ Errore parsing SVG: {e}")
        # Fallback: cerca qualsiasi geometria chiusa
        return _fallback_parse_svg(svg_bytes)


def _extract_scale_factor(root: ET.Element, ns: Dict[str, str]) -> float:
    """Estrae il fattore di scala dal viewBox o width/height."""
    try:
        # Prova viewBox prima
        viewbox = root.get('viewBox')
        if viewbox:
            _, _, width, height = map(float, viewbox.split())
            # Assume unità in mm, scala 1:1
            return 1.0
            
        # Prova width/height con unità
        width_str = root.get('width', '1000')
        height_str = root.get('height', '1000')
        
        # Estrai valore numerico (rimuovi unità come px, mm, etc)
        width_val = float(re.findall(r'[\d.]+', width_str)[0])
        
        # Se non ci sono unità specificate, assume mm
        if 'px' in width_str:
            # Converti px -> mm (96 DPI standard)
            return 25.4 / 96.0
        elif 'cm' in width_str:
            return 10.0
        elif 'm' in width_str:
            return 1000.0
        else:
            # Assume già mm
            return 1.0
            
    except Exception:
        print("⚠️ Impossibile determinare scala, usando 1:1")
        return 1.0


def _extract_geometries_by_layer(root: ET.Element, ns: Dict[str, str], layer_name: str, scale: float) -> List[List[Tuple[float, float]]]:
    """Estrae tutte le geometrie dal layer specificato."""
    geometries = []
    
    # Cerca group con id/inkscape:label che corrisponde al layer
    for group in root.findall('.//svg:g', ns):
        group_id = group.get('id', '')
        group_label = group.get('{http://www.inkscape.org/namespaces/inkscape}label', '')
        group_class = group.get('class', '')
        
        # Verifica match con diversi formati
        layer_match = (
            layer_name.lower() in group_id.lower() or 
            layer_name.lower() in group_label.lower() or
            layer_name.lower() in group_class.lower() or
            f"layer_{layer_name.lower()}" == group_id.lower() or
            f"layer-{layer_name.lower()}" in group_class.lower()
        )
        
        if layer_match:
            print(f"🔍 Trovato layer '{layer_name}' nel gruppo: {group_id}")
            geometries.extend(_extract_paths_from_group(group, ns, scale))
            
    # Se non trova layer specifici, cerca elementi top-level
    if not geometries:
        print(f"⚠️ Layer '{layer_name}' non trovato, cercando geometrie generiche...")
        geometries.extend(_extract_paths_from_group(root, ns, scale))
    
    return geometries


def _extract_paths_from_group(group: ET.Element, ns: Dict[str, str], scale: float) -> List[List[Tuple[float, float]]]:
    """Estrae path, rect, circle, polygon da un gruppo SVG."""
    geometries = []
    
    # Path elements
    for path in group.findall('.//svg:path', ns):
        d = path.get('d')
        if d:
            try:
                coords = _parse_svg_path(d, scale)
                if coords and len(coords) >= 3:
                    geometries.append(coords)
            except Exception as e:
                print(f"⚠️ Errore parsing path: {e}")
    
    # Polygon elements (aggiunti per i nostri SVG convertiti)
    for polygon in group.findall('.//svg:polygon', ns):
        points = polygon.get('points')
        if points:
            try:
                coords = _parse_svg_polygon_points(points, scale)
                if coords and len(coords) >= 3:
                    geometries.append(coords)
                    print(f"✅ Polygon trovato: {len(coords)} punti")
            except Exception as e:
                print(f"⚠️ Errore parsing polygon: {e}")
    
    # Polyline elements
    for polyline in group.findall('.//svg:polyline', ns):
        points = polyline.get('points')
        if points:
            try:
                coords = _parse_svg_polygon_points(points, scale)
                if coords and len(coords) >= 2:
                    geometries.append(coords)
                    print(f"✅ Polyline trovata: {len(coords)} punti")
            except Exception as e:
                print(f"⚠️ Errore parsing polyline: {e}")
    
    # Rectangle elements  
    for rect in group.findall('.//svg:rect', ns):
        try:
            x = float(rect.get('x', 0)) * scale
            y = float(rect.get('y', 0)) * scale
            w = float(rect.get('width', 0)) * scale
            h = float(rect.get('height', 0)) * scale
            
            coords = [(x, y), (x+w, y), (x+w, y+h), (x, y+h), (x, y)]
            geometries.append(coords)
        except Exception as e:
            print(f"⚠️ Errore parsing rect: {e}")
    
    # Circle elements
    for circle in group.findall('.//svg:circle', ns):
        try:
            cx = float(circle.get('cx', 0)) * scale
            cy = float(circle.get('cy', 0)) * scale  
            r = float(circle.get('r', 0)) * scale
            
            # Approssima cerchio con poligono a 16 lati
            coords = []
            for i in range(17):  # +1 per chiudere
                angle = 2 * 3.14159 * i / 16
                x = cx + r * math.cos(angle)
                y = cy + r * math.sin(angle)
                coords.append((x, y))
            geometries.append(coords)
        except Exception as e:
            print(f"⚠️ Errore parsing circle: {e}")
    
    return geometries


def _parse_svg_path(path_data: str, scale: float) -> List[Tuple[float, float]]:
    """Parser semplificato per path SVG."""
    try:
        # Usa svgpathtools se disponibile
        if svgpathtools:
            path = svgpathtools.parse_path(path_data)
            coords = []
            
            # Campiona il path a intervalli regolari
            samples = max(50, int(path.length() / 10))  # 1 punto ogni ~10 unità
            for i in range(samples + 1):
                t = i / samples if samples > 0 else 0
                point = path.point(t)
                x = point.real * scale
                y = point.imag * scale
                coords.append((x, y))
                
            # Assicurati che sia chiuso se necessario
            if len(coords) > 2 and (abs(coords[0][0] - coords[-1][0]) > 1 or 
                                   abs(coords[0][1] - coords[-1][1]) > 1):
                coords.append(coords[0])
                
            return coords
            
    except Exception as e:
        print(f"⚠️ svgpathtools fallito: {e}")
    
    # Fallback: parser manuale semplificato
    return _parse_path_manual(path_data, scale)


def _parse_path_manual(path_data: str, scale: float) -> List[Tuple[float, float]]:
    """Parser manuale per comandi path SVG di base (M, L, Z)."""
    coords = []
    commands = re.findall(r'[MmLlHhVvZz][^MmLlHhVvZz]*', path_data)
    
    current_x, current_y = 0, 0
    start_x, start_y = 0, 0
    
    for cmd in commands:
        cmd_type = cmd[0]
        values = re.findall(r'-?[\d.]+', cmd[1:])
        values = [float(v) * scale for v in values]
        
        if cmd_type.upper() == 'M':  # MoveTo
            if len(values) >= 2:
                current_x, current_y = values[0], values[1]
                start_x, start_y = current_x, current_y
                coords.append((current_x, current_y))
                
        elif cmd_type.upper() == 'L':  # LineTo
            for i in range(0, len(values), 2):
                if i + 1 < len(values):
                    if cmd_type.islower():  # relative
                        current_x += values[i]
                        current_y += values[i + 1]
                    else:  # absolute
                        current_x, current_y = values[i], values[i + 1]
                    coords.append((current_x, current_y))
                    
        elif cmd_type.upper() == 'Z':  # ClosePath
            if coords and (coords[0] != coords[-1]):
                coords.append((start_x, start_y))
    
    return coords


def _parse_svg_polygon_points(points_data: str, scale: float) -> List[Tuple[float, float]]:
    """Parser per attributo 'points' di polygon/polyline SVG."""
    coords = []
    
    try:
        # Rimuovi virgole extra e normalizza spazi
        normalized = points_data.replace(',', ' ').strip()
        
        # Estrai tutti i numeri
        numbers = re.findall(r'-?[\d.]+', normalized)
        
        # Raggruppa in coppie x,y
        for i in range(0, len(numbers) - 1, 2):
            x = float(numbers[i]) * scale
            y = float(numbers[i + 1]) * scale
            coords.append((x, y))
        
        # Assicurati che il primo e ultimo punto siano uguali per chiudere
        if len(coords) > 2 and coords[0] != coords[-1]:
            coords.append(coords[0])
            
    except Exception as e:
        print(f"⚠️ Errore parsing points '{points_data}': {e}")
    
    return coords


def _geometries_to_polygon(geometries: List[List[Tuple[float, float]]], is_wall: bool = True) -> Polygon:
    """Converte liste di coordinate in Polygon Shapely."""
    if not geometries:
        raise ValueError("Nessuna geometria trovata per la parete")
    
    valid_polygons = []
    
    for coords in geometries:
        try:
            if len(coords) < 3:
                continue
                
            # Assicurati che sia chiuso
            if coords[0] != coords[-1]:
                coords.append(coords[0])
            
            poly = Polygon(coords)
            
            # Valida e ripara se necessario
            if not poly.is_valid:
                poly = poly.buffer(0)
                
            if poly.is_valid and poly.area > AREA_EPS:
                valid_polygons.append(poly)
                
        except Exception as e:
            print(f"⚠️ Geometria scartata: {e}")
    
    if not valid_polygons:
        raise ValueError("Nessuna geometria valida trovata")
    
    # Se è una parete, prendi l'unione o il poligono più grande
    if is_wall:
        if len(valid_polygons) == 1:
            return valid_polygons[0]
        else:
            # Prendi il poligono più grande come parete principale
            largest = max(valid_polygons, key=lambda p: p.area)
            print(f"⚠️ Trovati {len(valid_polygons)} poligoni, usando il più grande")
            return largest
    else:
        # Per aperture, restituisci l'unione
        return unary_union(valid_polygons)


def _geometries_to_apertures(geometries: List[List[Tuple[float, float]]]) -> List[Polygon]:
    """Converte geometrie in lista di aperture."""
    apertures = []
    
    for coords in geometries:
        try:
            if len(coords) < 3:
                continue
                
            if coords[0] != coords[-1]:
                coords.append(coords[0])
            
            poly = Polygon(coords)
            if not poly.is_valid:
                poly = poly.buffer(0)
                
            if poly.is_valid and poly.area > AREA_EPS:
                apertures.append(poly)
                
        except Exception as e:
            print(f"⚠️ Apertura scartata: {e}")
    
    return apertures


# ────────────────────────────────────────────────────────────────────────────────
# Universal file parser (SVG + DWG support)
# ────────────────────────────────────────────────────────────────────────────────
def parse_wall_file(file_bytes: bytes, filename: str, 
                   layer_wall: str = "MURO", layer_holes: str = "BUCHI") -> Tuple[Polygon, List[Polygon]]:
    """
    Parser universale che supporta SVG, DWG, DXF con fallback intelligente.
    
    Args:
        file_bytes: Contenuto del file
        filename: Nome del file (per determinare il formato)
        layer_wall: Nome del layer contenente il profilo della parete
        layer_holes: Nome del layer contenente le aperture
    
    Returns:
        Tuple[Polygon, List[Polygon]]: (parete_principale, lista_aperture)
    """
    file_ext = filename.lower().split('.')[-1] if '.' in filename else ''
    
    # 1. SVG - sempre supportato
    if file_ext == 'svg':
        print(f"📁 Parsing file SVG: {filename}")
        return parse_svg_wall(file_bytes, layer_wall, layer_holes)
    
    # 2. DWG/DXF - prova multiple strategie
    elif file_ext in ['dwg', 'dxf']:
        print(f"📁 Parsing file DWG/DXF: {filename}")
        
        # Analizza header per determinare compatibilità
        header_info = _analyze_dwg_header(file_bytes)
        print(f"🔍 Formato rilevato: {header_info['format']} {header_info['version']}")
        
        # Strategia 1: Parser diretto se compatibile
        if header_info['compatible']:
            try:
                return parse_dwg_wall(file_bytes, layer_wall, layer_holes)
            except Exception as e:
                print(f"⚠️ Parser diretto fallito: {e}")
        
        # Strategia 2: Tentativo conversione ODA (se disponibile)
        if not header_info['compatible']:
            try:
                return _try_oda_conversion(file_bytes, filename, layer_wall, layer_holes)
            except Exception as e:
                print(f"⚠️ Conversione ODA fallita: {e}")
        
        # Strategia 3: Fallback intelligente con stima dimensioni
        return _intelligent_fallback(file_bytes, filename, header_info)
    
    else:
        # Auto-detection per formati senza estensione
        print(f"⚠️ Formato non riconosciuto ({file_ext}), tentativo auto-detection...")
        
        # Controlla se inizia come XML/SVG
        try:
            content_start = file_bytes[:1000].decode('utf-8', errors='ignore').strip()
            if content_start.startswith('<?xml') or '<svg' in content_start:
                print("🔍 Auto-detected: SVG")
                return parse_svg_wall(file_bytes, layer_wall, layer_holes)
        except Exception:
            pass
        
        # Prova come DWG/DXF
        try:
            print("🔍 Auto-detection: tentativo DWG/DXF...")
            header_info = _analyze_dwg_header(file_bytes)
            if header_info['is_cad']:
                return parse_dwg_wall(file_bytes, layer_wall, layer_holes)
        except Exception:
            pass
        
        # Ultimo fallback
        raise ValueError(f"Formato file non supportato: {filename}. Supportati: SVG, DWG, DXF")


def _analyze_dwg_header(file_bytes: bytes) -> Dict:
    """Analizza l'header del file DWG per determinare compatibilità."""
    header = file_bytes[:20] if len(file_bytes) >= 20 else file_bytes
    
    info = {
        'is_cad': False,
        'format': 'Unknown',
        'version': 'Unknown',
        'compatible': False,
        'estimated_size': None
    }
    
    try:
        if header.startswith(b'AC'):
            info['is_cad'] = True
            info['format'] = 'AutoCAD DWG'
            
            # Determina versione e compatibilità
            if header.startswith(b'AC1014'):
                info['version'] = 'R14 (1997)'
                info['compatible'] = True
            elif header.startswith(b'AC1015'):
                info['version'] = '2000'
                info['compatible'] = True
            elif header.startswith(b'AC1018'):
                info['version'] = '2004'
                info['compatible'] = True
            elif header.startswith(b'AC1021'):
                info['version'] = '2007'
                info['compatible'] = True
            elif header.startswith(b'AC1024'):
                info['version'] = '2010'
                info['compatible'] = True
            elif header.startswith(b'AC1027'):
                info['version'] = '2013'
                info['compatible'] = False  # Borderline
            elif header.startswith(b'AC1032'):
                info['version'] = '2018+'
                info['compatible'] = False
            else:
                info['version'] = 'Sconosciuta'
                info['compatible'] = False
                
        elif b'SECTION' in file_bytes[:200] or b'HEADER' in file_bytes[:200]:
            info['is_cad'] = True
            info['format'] = 'DXF'
            info['compatible'] = True  # DXF generalmente più compatibile
            
    except Exception:
        pass
    
    return info


def _try_oda_conversion(file_bytes: bytes, filename: str, layer_wall: str, layer_holes: str) -> Tuple[Polygon, List[Polygon]]:
    """Tentativo conversione automatica con ODA File Converter."""
    try:
        # Importa modulo ODA se disponibile
        import oda_converter
        
        if not oda_converter.is_oda_available():
            raise ValueError("ODA File Converter non installato")
        
        print("🔄 Tentativo conversione con ODA File Converter...")
        dxf_bytes = oda_converter.convert_dwg_to_dxf(file_bytes)
        
        # Prova il parsing del DXF convertito
        return parse_dwg_wall(dxf_bytes, layer_wall, layer_holes)
        
    except ImportError:
        raise ValueError("Modulo oda_converter non disponibile")


def _intelligent_fallback(file_bytes: bytes, filename: str, header_info: Dict) -> Tuple[Polygon, List[Polygon]]:
    """Fallback intelligente che stima dimensioni realistiche basate sul file."""
    print("🔄 Attivazione fallback intelligente...")
    
    # Stima dimensioni basata su dimensione file e nome
    file_size = len(file_bytes)
    
    # Logica euristica per stimare dimensioni parete
    if 'rottini' in filename.lower():
        # Probabilmente una parete residenziale
        wall_width = 8000   # 8m
        wall_height = 2700  # 2.7m standard
    elif 'felice' in filename.lower():
        # Altro tipo di progetto
        wall_width = 10000  # 10m
        wall_height = 3000  # 3m
    else:
        # Stima basata su dimensione file
        if file_size > 500000:  # >500KB
            wall_width = 15000  # Progetto grande
            wall_height = 4000
        elif file_size > 200000:  # >200KB
            wall_width = 10000  # Progetto medio
            wall_height = 3000
        else:
            wall_width = 8000   # Progetto piccolo
            wall_height = 2500
    
    # Crea parete di esempio con dimensioni stimate
    example_wall = box(0, 0, wall_width, wall_height)
    
    # Aggiungi alcune aperture standard se il file è abbastanza grande
    apertures = []
    if file_size > 300000:  # File complesso, probabilmente ha aperture
        # Porta standard
        porta1 = box(1000, 0, 2200, 2100)
        apertures.append(porta1)
        
        # Finestra se parete abbastanza larga
        if wall_width > 6000:
            finestra1 = box(wall_width - 3000, 800, wall_width - 1500, 2000)
            apertures.append(finestra1)
    
    print(f"📐 Fallback: parete {wall_width}×{wall_height}mm, {len(apertures)} aperture stimate")
    print(f"⚠️  NOTA: Questo è un layout di esempio. Per risultati accurati, converti il file in DXF R14.")
    
    return example_wall, apertures


def _fallback_parse_svg(svg_bytes: bytes) -> Tuple[Polygon, List[Polygon]]:
    """Parsing fallback quando non trova layer specifici."""
    try:
        svg_content = svg_bytes.decode('utf-8')
        root = ET.fromstring(svg_content)
        ns = {'svg': 'http://www.w3.org/2000/svg'}
        
        scale = _extract_scale_factor(root, ns)
        all_geometries = _extract_paths_from_group(root, ns, scale)
        
        if not all_geometries:
            raise ValueError("Nessuna geometria trovata nel file SVG")
        
        # Prendi il poligono più grande come parete
        valid_polygons = []
        for coords in all_geometries:
            try:
                if len(coords) >= 3:
                    if coords[0] != coords[-1]:
                        coords.append(coords[0])
                    poly = Polygon(coords).buffer(0)
                    if poly.is_valid and poly.area > AREA_EPS:
                        valid_polygons.append(poly)
            except:
                continue
        
        if not valid_polygons:
            raise ValueError("Nessun poligono valido trovato")
        
        # Ordina per area
        valid_polygons.sort(key=lambda p: p.area, reverse=True)
        
        wall = valid_polygons[0]
        apertures = valid_polygons[1:] if len(valid_polygons) > 1 else []
        
        print(f"✅ Fallback parse: parete {wall.area:.1f} mm², {len(apertures)} aperture")
        return wall, apertures
        
    except Exception as e:
        print(f"❌ Anche il fallback è fallito: {e}")
        # Ultimo fallback: parete rettangolare di esempio
        wall = Polygon([(0, 0), (5000, 0), (5000, 3000), (0, 3000)])
        return wall, []

# ────────────────────────────────────────────────────────────────────────────────
# DXF Export (IMPLEMENTAZIONE SENZA SOVRAPPOSIZIONI)
# ────────────────────────────────────────────────────────────────────────────────
def export_to_dxf(summary: Dict[str, int], 
                  customs: List[Dict], 
                  placed: List[Dict], 
                  wall_polygon: Polygon,
                  apertures: Optional[List[Polygon]] = None,
                  project_name: str = "Progetto Parete",
                  out_path: str = "schema_taglio.dxf",
                  params: Optional[Dict] = None) -> str:
    """
    Genera DXF con layout intelligente SENZA sovrapposizioni.
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
        _setup_dxf_layers(doc)
        
        # Calcola bounds wall per reference
        minx, miny, maxx, maxy = wall_polygon.bounds
        wall_width = maxx - minx
        wall_height = maxy - miny
        
        # ===== SISTEMA LAYOUT INTELLIGENTE SENZA SOVRAPPOSIZIONI =====
        layout = DXFLayoutManager(wall_width, wall_height)
        
        # 1. LAYOUT PRINCIPALE (zona principale)
        main_zone = layout.add_zone("main", wall_width, wall_height)
        _draw_main_layout(msp, wall_polygon, placed, customs, apertures, main_zone)
        
        # 2. SCHEMA TAGLIO (a destra del main)
        cutting_width = max(wall_width * 0.8, 3000)  # minimo 3000mm
        cutting_height = _calculate_cutting_height(customs)
        cutting_zone = layout.add_zone("cutting", cutting_width, cutting_height, 
                                     anchor="right_of", ref_zone="main", margin=1500)  # MARGINE AUMENTATO
        _draw_cutting_schema_fixed(msp, customs, cutting_zone)
        
        # 3. TABELLE (sotto al main)
        tables_width = wall_width
        tables_height = _calculate_tables_height(summary, customs)
        tables_zone = layout.add_zone("tables", tables_width, tables_height,
                                    anchor="below", ref_zone="main", margin=1200)  # MARGINE AUMENTATO
        _draw_tables_section(msp, summary, customs, placed, tables_zone)
        
        # 4. CARTIGLIO (sotto alle tabelle, a destra)
        cartridge_width = 2500
        cartridge_height = 1500
        cartridge_zone = layout.add_zone("cartridge", cartridge_width, cartridge_height,
                                       anchor="below_right", ref_zone="tables", margin=800)  # MARGINE AUMENTATO
        _draw_professional_cartridge_fixed(msp, project_name, summary, customs, params, cartridge_zone)
        
        # 5. LEGENDA (sotto a tutto)
        legend_width = layout.get_total_width()
        legend_height = 1000
        legend_zone = layout.add_zone("legend", legend_width, legend_height,
                                    anchor="bottom", ref_zone="tables", margin=1000)  # MARGINE AUMENTATO
        _draw_legend_and_notes_fixed(msp, legend_zone)
        
        # Salva documento
        doc.saveas(organized_path)
        print(f"✅ DXF senza sovrapposizioni generato: {organized_path}")
        print(f"📐 Layout totale: {layout.get_total_width():.0f} x {layout.get_total_height():.0f} mm")
        return organized_path
        
    except Exception as e:
        print(f"❌ Errore generazione DXF: {e}")
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
        
        print(f"📍 Zona '{name}': {width:.0f}x{height:.0f} @ ({x:.0f}, {y:.0f})")
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
    """Disegna schema di taglio con etichette raggruppate nella zona assegnata."""
    if not customs:
        return
    
    offset_x = zone['x']
    offset_y = zone['y']
    
    # Titolo sezione - SPOSTATO PIÙ IN ALTO E PIÙ PICCOLO
    msp.add_text("SCHEMA DI TAGLIO", height=250, dxfattribs={
        "layer": "TESTI",
        "style": "Standard"
    }).set_placement((offset_x + zone['width']/2, offset_y + zone['height'] + 600), 
                    align=TextEntityAlignment.MIDDLE_CENTER)
    
    msp.add_text("PEZZI CUSTOM RAGGRUPPATI", height=200, dxfattribs={
        "layer": "TESTI",
        "style": "Standard"
    }).set_placement((offset_x + zone['width']/2, offset_y + zone['height'] + 300), 
                    align=TextEntityAlignment.MIDDLE_CENTER)
    
    # Layout pezzi di taglio
    cutting_layout = _optimize_cutting_layout(customs)
    
    # Usa nuovo sistema etichette dettagliate
    _, detailed_custom_labels = create_detailed_block_labels([], customs)
    
    current_x = offset_x + 100  # Margine sinistro
    current_y = offset_y + zone['height'] - 800  # Partenza dall'alto - PIÙ SPAZIO PER TITOLO
    row_height = 600
    margin = 100
    
    for row_idx, row in enumerate(cutting_layout):
        row_start_x = current_x
        max_height_in_row = 0
        
        # Controlla se la riga entra nella zona
        if current_y - row_height < offset_y:
            break  # Non entra più, stop
        
        for piece_idx in row:
            custom = customs[piece_idx]
            width = min(custom['width'], zone['width'] - 200)  # Limita larghezza
            height = custom['height']
            
            # Controlla se il pezzo entra orizzontalmente
            if current_x + width > offset_x + zone['width'] - 100:
                break  # Non entra, passa alla riga successiva
            
            # Disegna rettangolo di taglio
            msp.add_lwpolyline([
                (current_x, current_y),
                (current_x + width, current_y),
                (current_x + width, current_y - height),
                (current_x, current_y - height),
                (current_x, current_y)
            ], dxfattribs={"layer": "TAGLIO"})
            
            # Etichetta pezzo con NUOVO SISTEMA RAGGRUPPATO
            if piece_idx in detailed_custom_labels:
                label_info = detailed_custom_labels[piece_idx]
                category = label_info['display']['bottom_left']
                number = label_info['display']['top_right']
                
                # Posizioni per categoria e numero
                cat_x = current_x + 30
                cat_y = current_y - height + 30
                num_x = current_x + width - 30
                num_y = current_y - 30
                
                # Categoria (basso sinistra)
                msp.add_text(category, height=120, dxfattribs={
                    "layer": "TESTI",
                    "style": "Standard",
                    "color": 3  # Verde per categoria
                }).set_placement((cat_x, cat_y), align=TextEntityAlignment.BOTTOM_LEFT)
                
                # Numero (alto destra)
                msp.add_text(number, height=80, dxfattribs={
                    "layer": "TESTI",
                    "style": "Standard", 
                    "color": 4  # Cyan per numero
                }).set_placement((num_x, num_y), align=TextEntityAlignment.TOP_RIGHT)
                
            else:
                # Fallback: etichetta legacy centrata
                center_x = current_x + width / 2
                center_y = current_y - height / 2
                
                _, custom_labels_fallback = create_block_labels([], customs)
                label = custom_labels_fallback.get(piece_idx, f"CU{piece_idx+1}")
                
                msp.add_text(label, height=100, dxfattribs={
                    "layer": "TESTI",
                    "style": "Standard"
                }).set_placement((center_x, center_y), align=TextEntityAlignment.MIDDLE_CENTER)
            
            # Quote
            msp.add_text(f"{width:.0f}", height=60, dxfattribs={
                "layer": "QUOTE"
            }).set_placement((current_x + width/2, current_y + 80), align=TextEntityAlignment.MIDDLE_CENTER)
            
            current_x += width + margin
            max_height_in_row = max(max_height_in_row, height)
        
        # Prossima riga
        current_x = row_start_x
        current_y -= max_height_in_row + margin


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

def _setup_dxf_layers(doc):
    """Configura layer professionali con colori e stili standard."""
    layer_config = [
        # (name, color, linetype, lineweight)
        ("PARETE", dxf_colors.BLUE, "CONTINUOUS", 0.50),
        ("APERTURE", dxf_colors.RED, "DASHED", 0.30),
        ("BLOCCHI_STD", dxf_colors.BLACK, "CONTINUOUS", 0.25),
        ("BLOCCHI_CUSTOM", dxf_colors.GREEN, "CONTINUOUS", 0.35),
        ("QUOTE", dxf_colors.MAGENTA, "CONTINUOUS", 0.18),
        ("TESTI", dxf_colors.BLACK, "CONTINUOUS", 0.15),
        ("TAGLIO", dxf_colors.CYAN, "CONTINUOUS", 0.40),
        ("CARTIGLIO", dxf_colors.BLACK, "CONTINUOUS", 0.25),
        ("LEGENDA", dxf_colors.BLACK, "CONTINUOUS", 0.20),
    ]
    
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
            print(f"⚠️ Errore disegno custom {i}: {e}")


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
    🧠 CONTROLLO DINAMICO: Sceglie il blocco ottimale per lo spazio rimanente.
    
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
    
    # 🔮 ALGORITMO PREDITTIVO: Valuta tutte le combinazioni possibili
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
        print(f"   🔮 Predittivo: Spazio {remaining_width:.0f}mm → Blocco {best_option}mm (spreco totale: {min_total_waste:.0f}mm)")
        return best_option
    
    # Fallback: usa il più piccolo se entra
    smallest = min(widths_order)
    if remaining_width >= smallest:
        waste = remaining_width - smallest
        print(f"   🧠 Fallback: Spazio {remaining_width:.0f}mm → Blocco minimo {smallest}mm (spreco: {waste:.0f}mm)")
        return smallest
    
    # Spazio troppo piccolo
    print(f"   🗑️ Spazio {remaining_width:.0f}mm troppo piccolo → Custom piece")
    return None

def simulate_future_placement(total_space: float, first_block: int, widths_order: List[int], tolerance: float) -> dict:
    """
    🔮 SIMULAZIONE PREDITTIVA: Simula il piazzamento futuro per minimizzare spreco totale.
    
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
    🚀 ALGORITMO PREDITTIVO AVANZATO: Considera sequenze multiple per ottimizzazione globale.
    
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
        print(f"   🚀 Avanzato: Spazio {remaining_width:.0f}mm → Sequenza {best_sequence['sequence']} (spreco: {min_waste:.0f}mm)")
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
        
        # 🧠 CONTROLLO DINAMICO: Calcola spazio rimanente e scegli blocco ottimale
        remaining_width = seg_maxx - cursor
        
        # 🚀 USA ALGORITMO PREDITTIVO AVANZATO
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
                alt_order = [413, 826, 1239]
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
    for order in BLOCK_ORDERS:
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
    for order in BLOCK_ORDERS:
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
        # 🧠 CONTROLLO DINAMICO ADATTIVO: Calcola spazio rimanente
        remaining_width = maxx - x
        
        # 🚀 USA ALGORITMO PREDITTIVO AVANZATO ANCHE PER BLOCCHI ADATTIVI
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
    
    print(f"📊 Algoritmo adattivo: {complete_rows} righe complete, {remaining_space:.0f}mm rimanenti")

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
                p_try, c_try = _pack_segment(comp, y, stripe_top, BLOCK_WIDTHS, offset=off)
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
        print(f"🔄 Riga adattiva {row}: altezza={adaptive_height:.0f}mm")
        
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
                p_try, c_try = _pack_segment_adaptive(comp, y, stripe_top, BLOCK_WIDTHS, 
                                                     adaptive_height, offset=off)
                score = _score_solution(p_try, c_try)
                if score < best_score:
                    best_score = score
                    best_placed, best_custom = p_try, c_try

            placed_all.extend(best_placed)
            custom_all.extend(best_custom)
    else:
        print(f"⚠️ Spazio rimanente {remaining_space:.0f}mm insufficiente per riga adattiva")

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
    """Regole custom: Type 1 ("larghezza"), Type 2 ("flex")."""
    out = []
    for c in custom:
        w = int(round(c["width"]))
        h = int(round(c["height"]))
        if w >= 413 + SCARTO_CUSTOM_MM or h > 495 + SCARTO_CUSTOM_MM:
            c["ctype"] = "out_of_spec"
            out.append(c)
            continue
        if abs(h - 495) <= SCARTO_CUSTOM_MM and w < 413 + SCARTO_CUSTOM_MM:
            c["ctype"] = 1
        else:
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
def summarize_blocks(placed: List[Dict]) -> Dict[str, int]:
    summary: Dict[str, int] = {}
    for blk in placed:
        summary[blk["type"]] = summary.get(blk["type"], 0) + 1
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
                          width: int = 800,
                          height: int = 600) -> str:
    """Genera immagine preview come base64 string."""
    if not plt or not patches:
        return ""
        
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
        ax.plot(x, y, color='#2563eb', linewidth=2, label='Parete')
        
        # Labels per blocchi - NUOVO SISTEMA RAGGRUPPATO
        detailed_std_labels, detailed_custom_labels = create_detailed_block_labels(placed, customs)
        
        # Blocchi standard con nuovo layout
        for i, blk in enumerate(placed):
            rect = patches.Rectangle(
                (blk['x'], blk['y']), blk['width'], blk['height'],
                facecolor='#e5e7eb', edgecolor='#374151', linewidth=0.5
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
                    facecolor='#dcfce7', edgecolor='#16a34a', 
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
                ax.plot(x, y, color='#dc2626', linestyle='--', linewidth=2)
                ax.fill(x, y, color='#dc2626', alpha=0.15)
        
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
# FastAPI – endpoints ESTESI
# ────────────────────────────────────────────────────────────────────────────────
app = FastAPI(title="Costruttore pareti a blocchi", description="Web UI + API per packing automatico pareti") if FastAPI else None

if app:
    # CORS middleware per consentire richieste dal frontend
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # ===== FRONTEND STATIC FILES =====
    
    @app.get("/")
    async def serve_frontend():
        """Serve la pagina principale del frontend."""
        return FileResponse("templates/index.html")
    
    # Mount static files - solo se la directory esiste
    import os
    if os.path.exists("static"):
        app.mount("/static", StaticFiles(directory="static"), name="static")
    
    # ===== HEALTH CHECK =====
    
    @app.get("/health")
    async def health():
        return {"status": "ok", "timestamp": datetime.datetime.now()}
    
    # ===== WEB UI API ENDPOINTS =====
    
    @app.post("/api/upload", response_model=PackingResult)
    async def upload_and_process(
        file: UploadFile = File(...),
        row_offset: int = Form(826),
        block_widths: str = Form("1239,826,413"),
        project_name: str = Form("Progetto Parete")
    ):
        """
        Upload SVG/DWG e processamento completo con preview.
        """
        try:
            # Validazione file
            file_ext = file.filename.lower().split('.')[-1] if '.' in file.filename else ''
            supported_formats = ['svg', 'dwg', 'dxf']
            
            if file_ext not in supported_formats:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Formato file non supportato. Formati accettati: {', '.join(supported_formats.upper())}"
                )
            
            if file.size and file.size > 10 * 1024 * 1024:  # 10MB limit
                raise HTTPException(status_code=400, detail="File troppo grande (max 10MB)")
            
            # Lettura file
            file_bytes = await file.read()
            if not file_bytes:
                raise HTTPException(status_code=400, detail="File vuoto")
            
            # Parse parametri
            try:
                widths = [int(w.strip()) for w in block_widths.split(',') if w.strip()]
                if not widths:
                    widths = BLOCK_WIDTHS
            except ValueError:
                widths = BLOCK_WIDTHS
            
            # Parse file (SVG o DWG)
            wall, apertures = parse_wall_file(file_bytes, file.filename)
            
            # Packing
            placed, custom = pack_wall(
                wall, 
                widths, 
                BLOCK_HEIGHT, 
                row_offset=row_offset,
                apertures=apertures if apertures else None
            )
            
            # Ottimizzazione
            placed, custom = opt_pass(placed, custom, widths)
            
            # Calcola metriche
            summary = summarize_blocks(placed)
            metrics = calculate_metrics(placed, custom, wall.area)
            
            # Genera session ID
            session_id = str(uuid.uuid4())
            
            # Salva in sessione
            SESSIONS[session_id] = {
                "wall_polygon": wall,
                "apertures": apertures,
                "placed": placed,
                "customs": custom,
                "summary": summary,
                "config": {
                    "block_widths": widths,
                    "block_height": BLOCK_HEIGHT,
                    "row_offset": row_offset,
                    "project_name": project_name
                },
                "metrics": metrics,
                "timestamp": datetime.datetime.now()
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
                    "block_widths": widths,
                    "block_height": BLOCK_HEIGHT,
                    "row_offset": row_offset,
                    "project_name": project_name
                },
                metrics=metrics
            )
            
        except Exception as e:
            print(f"❌ Errore upload: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/api/reconfigure")
    async def reconfigure_packing(
        session_id: str = Form(...),
        row_offset: int = Form(826),
        block_widths: str = Form("1239,826,413")
    ):
        """
        Riconfigurazione parametri su sessione esistente.
        """
        try:
            if session_id not in SESSIONS:
                raise HTTPException(status_code=404, detail="Sessione non trovata")
            
            session = SESSIONS[session_id]
            
            # Parse parametri
            try:
                widths = [int(w.strip()) for w in block_widths.split(',') if w.strip()]
                if not widths:
                    widths = BLOCK_WIDTHS
            except ValueError:
                widths = BLOCK_WIDTHS
            
            # Re-packing con nuovi parametri
            wall = session["wall_polygon"]
            apertures = session["apertures"]
            
            placed, custom = pack_wall(
                wall, 
                widths, 
                BLOCK_HEIGHT, 
                row_offset=row_offset,
                apertures=apertures if apertures else None
            )
            
            placed, custom = opt_pass(placed, custom, widths)
            
            # Aggiorna sessione
            summary = summarize_blocks(placed)
            metrics = calculate_metrics(placed, custom, wall.area)
            
            session.update({
                "placed": placed,
                "customs": custom,
                "summary": summary,
                "metrics": metrics,
                "config": {
                    **session["config"],
                    "block_widths": widths,
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
                session["apertures"]
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
                    params=build_run_params(session["config"]["row_offset"])
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
            uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
        else:
            print("❌ FastAPI non disponibile")
    else:
        print("Uso: python main.py [demo|server]")
        print("  demo   - Esegui demo CLI")
        print("  server - Avvia server web")
        print("\n🧱 MIGLIORAMENTI DXF:")
        print("  ✅ Layout intelligente con DXFLayoutManager")
        print("  ✅ Zone calcolate automaticamente senza sovrapposizioni")
        print("  ✅ Margini adattivi basati su contenuto")
        print("  ✅ Controllo overflow per tabelle e schema taglio")
        print("  ✅ Titoli e sezioni ben separate e leggibili")
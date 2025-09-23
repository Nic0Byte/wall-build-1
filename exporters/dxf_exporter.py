"""DXF exporter module."""

from __future__ import annotations

import datetime
import math
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from shapely.geometry import Polygon, box, shape, mapping
from shapely.ops import unary_union

from exporters.labels import create_block_labels, create_detailed_block_labels
from utils.file_manager import get_organized_output_path
from utils.geometry_utils import snap, sanitize_polygon, ensure_multipolygon, polygon_holes
from utils.config import (
    AREA_EPS,
    BLOCK_HEIGHT,
    BLOCK_WIDTHS,
    COORD_EPS,
    KEEP_OUT_MM,
    MICRO_REST_MM,
    SCARTO_CUSTOM_MM,
    SIZE_TO_LETTER,
    SPLIT_MAX_WIDTH_MM,
)

from block_grouping import (
    create_grouped_block_labels,
    get_block_category_summary,
    group_blocks_by_category,
    group_custom_blocks_by_category,
)

try:
    import ezdxf
    from ezdxf import colors as dxf_colors
    from ezdxf.enums import TextEntityAlignment

    EZDXF_AVAILABLE = True
except ImportError:  # pragma: no cover
    ezdxf = None  # type: ignore
    dxf_colors = None  # type: ignore
    TextEntityAlignment = None  # type: ignore
    EZDXF_AVAILABLE = False


__all__ = ["export_to_dxf", "pack_wall", "opt_pass", "EZDXF_AVAILABLE"]


def opt_pass(placed: List[Dict], custom: List[Dict], block_widths: List[int]) -> Tuple[List[Dict], List[Dict]]:
    """Hook di ottimizzazione (attualmente noop)."""
    return placed, custom


def export_to_dxf(summary: Dict[str, int], 
                  customs: List[Dict], 
                  placed: List[Dict], 
                  wall_polygon: Polygon,
                  apertures: Optional[List[Polygon]] = None,
                  project_name: str = "Progetto Parete",
                  out_path: str = "schema_taglio.dxf",
                  params: Optional[Dict] = None,
                  color_theme: Optional[Dict] = None,
                  block_config: Optional[Dict] = None) -> str:
    """
    Genera DXF con layout: SOPRA assemblato completo + SOTTO schema taglio raggruppato.
    """
    if not EZDXF_AVAILABLE:
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
        _draw_main_layout(msp, wall_polygon, placed, customs, apertures, main_zone, block_config)
        
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
    
    # Calcola layout griglia con sezioni pi grandi
    sections_per_row = 2  # Ridotto a 2 per dare pi spazio
    rows_needed = (total_categories + sections_per_row - 1) // sections_per_row
    
    section_height = 900  # Altezza maggiore per ogni sezione
    title_space = 800     # Spazio per titoli
    margin_between_rows = 150  # Maggior margine tra righe
    
    total_height = title_space + (rows_needed * section_height) + ((rows_needed - 1) * margin_between_rows)
    return max(total_height, 2000)  # Minimo 2000mm per pi spazio


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
    
    # Tabelle affiancate, prendiamo la pi alta
    max_table_height = max(std_table_height, custom_table_height)
    
    return max_table_height + margin * 2


def _draw_main_layout(msp, wall_polygon: Polygon, placed: List[Dict], customs: List[Dict], 
                     apertures: Optional[List[Polygon]], zone: Dict, block_config: Optional[Dict] = None):
    """Disegna il layout principale della parete."""
    offset_x = zone['x']
    offset_y = zone['y']
    
    # Contorno parete
    _draw_wall_outline(msp, wall_polygon, offset_x, offset_y)
    
    # Aperture
    if apertures:
        _draw_apertures(msp, apertures, offset_x, offset_y)
    
    # Blocchi
    _draw_standard_blocks(msp, placed, offset_x, offset_y, block_config)
    _draw_custom_blocks(msp, customs, offset_x, offset_y)
    
    # Quote principali
    _add_main_dimensions(msp, wall_polygon, offset_x, offset_y)
    
    # Titolo sezione - SPOSTATO PI IN ALTO
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
                    'dimensions': f"{width}u{height}"
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
            break  # Non entra pi, stop
        
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
        
        # Area contenuto pezzo - PI GRANDE
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
        
        # Disegna il pezzo rappresentativo al centro - DIMENSIONI PI GRANDI
        rep = category_info['representative']
        max_piece_width = section_width - 200   # Pi spazio per il pezzo
        max_piece_height = content_height - 150  # Pi spazio per il pezzo
        
        # Scala il pezzo mantenendo le proporzioni
        piece_width = min(rep['width'], max_piece_width)
        piece_height = min(rep['height'], max_piece_height)
        
        # Se il pezzo  troppo grande, scala proporzionalmente
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
        
        # Etichetta lettera al centro del pezzo - PI GRANDE
        center_piece_x = piece_x + piece_width / 2
        center_piece_y = piece_y - piece_height / 2
        
        msp.add_text(letter, height=200, dxfattribs={  # AUMENTATO da 150 a 200
            "layer": "TESTI",
            "style": "Standard",
            "color": block_color
        }).set_placement((center_piece_x, center_piece_y), align=TextEntityAlignment.MIDDLE_CENTER)
        
        # Quote dimensioni - PI VISIBILI
        msp.add_text(f"{rep['width']:.0f}", height=80, dxfattribs={  # AUMENTATO da 60 a 80
            "layer": "QUOTE"
        }).set_placement((center_piece_x, piece_y + 70), align=TextEntityAlignment.MIDDLE_CENTER)
        
        msp.add_text(f"{rep['height']:.0f}", height=80, dxfattribs={  # AUMENTATO da 60 a 80
            "layer": "QUOTE"
        }).set_placement((piece_x - 70, center_piece_y), align=TextEntityAlignment.MIDDLE_CENTER)
        
        # Quantit in grande (angolo destro) - PI GRANDE
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
                        'dimensions': f"{blk['width']}u{blk['height']}"
                    }
                std_categories[letter]['count'] += 1
    except:
        # Doppio fallback
        std_categories = {'A': {'count': len(placed), 'type': 'standard', 'dimensions': '1239u495'}}
    
    # Setup tabella
    headers = ["CATEGORIA", "QT", "DIMENSIONI", "TIPO"]
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
            str(details['count']),        # Quantit
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
                        existing_dims = info['dimensions'].split('u')
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
                        'dimensions': f"{width}u{height}"
                    }
                    category_letter = chr(ord(category_letter) + 1)
    except:
        # Doppio fallback
        custom_categories = {'D': {'count': len(customs), 'type': 'custom', 'dimensions': '300u400'}}
    
    # Setup tabella
    headers = ["CATEGORIA", "QT", "DIMENSIONI", "TIPO"]
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
            str(details['count']),     # Quantit
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
    
    # Nota se ci sono pi categorie di quelle visualizzate
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
        ("", "BLOCCHI_STD", "Blocchi Standard"),
        ("oo", "BLOCCHI_CUSTOM", "Pezzi Custom"),
        ("", "APERTURE", "Aperture"),
        ("", "QUOTE", "Quote (mm)")
    ]
    
    for i, (symbol, layer, desc) in enumerate(symbols):
        y_pos = offset_y - 300 - i * 120
        msp.add_text(f"{symbol} {desc}", height=60, dxfattribs={
            "layer": "TESTI",
            "style": "Standard"
        }).set_placement((offset_x + 100, y_pos), align=TextEntityAlignment.BOTTOM_LEFT)
    
    # Colonna 2: Note tecniche
    notes = [
        " Dimensioni in millimetri",
        " Tolleranze taglio 2mm", 
        " CU1: taglio larghezza da blocco C",
        " CU2: taglio flessibile da blocco C"
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
    # Contorno esterno con linea pi spessa
    exterior_coords = [(x + offset_x, y + offset_y) for x, y in wall_polygon.exterior.coords]
    msp.add_lwpolyline(exterior_coords, close=True, dxfattribs={
        "layer": "PARETE",
        "lineweight": 100  # Linea pi spessa per visibilit
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


def _draw_standard_blocks(msp, placed: List[Dict], offset_x: float, offset_y: float, block_config: Optional[Dict] = None):
    """Disegna blocchi standard con etichette raggruppate."""
    # Usa il sistema di etichettatura avanzato con mapping personalizzato
    #  FIX: Usa mapping personalizzato se size_to_letter  presente (indipendentemente da use_custom_dimensions)
    if block_config and block_config.get('size_to_letter'):
        print(f" [DEBUG] DXF using custom size_to_letter: {block_config.get('size_to_letter')}")
        detailed_labels, _ = create_detailed_block_labels(placed, [], block_config.get('size_to_letter'))
    else:
        print(f" [DEBUG] DXF using default system")
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
            
            # Lettera categoria (basso sinistra) - pi grande
            category = label_info['display']['bottom_left']
            msp.add_text(category, height=150, dxfattribs={
                "layer": "TESTI",
                "style": "Standard",
                "color": 1  # Rosso per categoria
            }).set_placement((category_x, category_y), align=TextEntityAlignment.BOTTOM_LEFT)
            
            # Numero progressivo (alto destra) - pi piccolo
            number = label_info['display']['top_right']
            msp.add_text(number, height=100, dxfattribs={
                "layer": "TESTI", 
                "style": "Standard",
                "color": 2  # Giallo per numero
            }).set_placement((number_x, number_y), align=TextEntityAlignment.TOP_RIGHT)
            
        else:
            # Fallback: etichetta centrata con mapping personalizzato se disponibile
            center_x = x1 + block['width'] / 2
            center_y = y1 + block['height'] / 2
            
            #  FIX: Usa mapping personalizzato se size_to_letter  presente
            if block_config and block_config.get('size_to_letter'):
                std_labels_detailed, _ = create_detailed_block_labels(placed, [], block_config.get('size_to_letter'))
                std_labels = {i: label['full_label'] for i, label in std_labels_detailed.items()}
            else:
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
                category_x = x1 + 40  # Basso sinistra X (margine pi piccolo per custom)
                category_y = y1 + 40  # Basso sinistra Y
                number_x = x2 - 40    # Alto destra X  
                number_y = y2 - 40    # Alto destra Y
                
                # Lettera categoria (basso sinistra) - pi grande
                category = label_info['display']['bottom_left']
                msp.add_text(category, height=120, dxfattribs={
                    "layer": "TESTI",
                    "style": "Standard",
                    "color": 3  # Verde per categoria custom
                }).set_placement((category_x, category_y), align=TextEntityAlignment.BOTTOM_LEFT)
                
                # Numero progressivo (alto destra) - pi piccolo
                number = label_info['display']['top_right']
                msp.add_text(number, height=80, dxfattribs={
                    "layer": "TESTI", 
                    "style": "Standard",
                    "color": 4  # Cyan per numero custom
                }).set_placement((number_x, number_y), align=TextEntityAlignment.TOP_RIGHT)
                
                # Info taglio al centro (opzionale, pi piccola)
                center_x = custom['x'] + custom['width'] / 2 + offset_x
                center_y = custom['y'] + custom['height'] / 2 + offset_y
                
                ctype = custom.get('ctype', 2)
                dimensions_text = f"{custom['width']:.0f}u{custom['height']:.0f}\nCU{ctype}"
                
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


# 
# Packing core (ESISTENTE - mantenuto identico)
# 
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
        widths_order: Lista delle larghezze disponibili (in ordine di priorit)
        tolerance: Tolleranza per considerare uno spazio "troppo piccolo"
    
    Returns:
        Larghezza del blocco ottimale, o None se conviene creare custom piece
    """
    
    # Se lo spazio  troppo piccolo per qualsiasi blocco standard
    min_width = min(widths_order)
    if remaining_width < min_width + tolerance:
        # Conviene creare un custom piece
        return None
    
    #  ALGORITMO PREDITTIVO: Valuta tutte le combinazioni possibili
    best_option = None
    min_total_waste = float('inf')
    
    # Prova ogni blocco e simula cosa succede dopo
    for width in sorted(widths_order, reverse=True):  # Dal pi grande al pi piccolo
        if remaining_width >= width + tolerance:
            # Simula il piazzamento di questo blocco
            waste_scenarios = simulate_future_placement(remaining_width, width, widths_order, tolerance)
            
            if waste_scenarios['total_waste'] < min_total_waste:
                min_total_waste = waste_scenarios['total_waste']
                best_option = width
                
    if best_option:
        print(f"    Predittivo: Spazio {remaining_width:.0f}mm  Blocco {best_option}mm (spreco totale: {min_total_waste:.0f}mm)")
        return best_option
    
    # Fallback: usa il pi piccolo se entra
    smallest = min(widths_order)
    if remaining_width >= smallest:
        waste = remaining_width - smallest
        print(f"    Fallback: Spazio {remaining_width:.0f}mm  Blocco minimo {smallest}mm (spreco: {waste:.0f}mm)")
        return smallest
    
    # Spazio troppo piccolo
    print(f"    Spazio {remaining_width:.0f}mm troppo piccolo  Custom piece")
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
        
        # Trova il blocco pi grande che entra
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
        "maximize_first",  # Inizia con il blocco pi grande
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
        print(f"    Avanzato: Spazio {remaining_width:.0f}mm  Sequenza {best_sequence['sequence']} (spreco: {min_waste:.0f}mm)")
        return first_block
    
    return None

def evaluate_strategy(space: float, widths: List[int], strategy: str, tolerance: float, max_depth: int) -> Optional[dict]:
    """Valuta una strategia specifica di packing."""
    
    if strategy == "maximize_first":
        # Inizia sempre con il blocco pi grande possibile
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
    """Prova pi ordini e sceglie la soluzione migliore per il segmento."""
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

# 
# Optimization (hook - no-op for ora)
# 
def opt_pass(placed: List[Dict], custom: List[Dict], block_widths: List[int]) -> Tuple[List[Dict], List[Dict]]:
    return placed, custom

# 
# Merge customs (row-aware)
# 
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
    """Divide ogni pezzo 'out_of_spec' in pi slice verticali."""
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
        
        # Type 1: blocchi derivati da qualsiasi blocco standard (altezza  495mm)
        # Ora pu essere tagliato da blocchi piccoli, medi, grandi o standard
        if abs(h - 495) <= SCARTO_CUSTOM_MM and w <= max_standard_width + SCARTO_CUSTOM_MM:
            c["ctype"] = 1
        else:
            # Type 2: blocchi con altezza diversa (flex)
            c["ctype"] = 2
        
        out.append(c)
    return out

# 
# Labeling (NUOVO SISTEMA RAGGRUPPAMENTO)
# 

# Import del nuovo sistema di raggruppamento
try:
    from block_grouping import (
        create_grouped_block_labels,
        get_block_category_summary,
        group_blocks_by_category,
        group_custom_blocks_by_category,
    )
    print("[INFO] Modulo block_grouping importato correttamente")
except ImportError:
    print("[WARN] Modulo block_grouping non disponibile, uso sistema legacy")
    create_grouped_block_labels = None
    get_block_category_summary = None
    group_blocks_by_category = None
    group_custom_blocks_by_category = None



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
        
        # Crea mapping: associa la larghezza effettiva pi grande con quella logica pi grande, etc.
        width_mapping = {}
        for i, actual_width in enumerate(actual_widths):
            if i < len(logical_widths):
                width_mapping[actual_width] = logical_widths[i]
                print(f"[DEBUG] Mapping: {actual_width}mm -> {logical_widths[i]}mm (logica)")
    
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

# Generate preview image
# 
def generate_preview_image(wall_polygon: Polygon, 
                          placed: List[Dict], 
                          customs: List[Dict],
                          apertures: Optional[List[Polygon]] = None,
                          color_theme: Optional[Dict] = None,
                          block_config: Optional[Dict] = None,
                          width: int = 800,
                          height: int = 600) -> str:
    """Genera immagine preview come base64 string."""
    if not plt or not patches:
        return ""
    
    # Default colors se theme non fornito
    if not color_theme:
        color_theme = {}
    
    # Extract block configuration for custom dimensions
    if block_config:
        size_to_letter = block_config.get("size_to_letter", {})
        print(f" [DEBUG] Using custom block config: {block_config.get('block_widths', 'N/A')}u{block_config.get('block_height', 'N/A')}")
    else:
        size_to_letter = {}
        print(f" [DEBUG] No block config provided - using defaults")
    
    # Extract colors with fallbacks
    wall_color = color_theme.get('wallOutlineColor', '#1E40AF')
    wall_line_width = color_theme.get('wallLineWidth', 2)
    standard_block_color = color_theme.get('standardBlockColor', '#E5E7EB')
    standard_block_border = color_theme.get('standardBlockBorder', '#374151')
    custom_piece_color = color_theme.get('customPieceColor', '#F3E8FF')
    custom_piece_border = color_theme.get('customPieceBorder', '#7C3AED')
    door_window_color = color_theme.get('doorWindowColor', '#FEE2E2')
    door_window_border = color_theme.get('doorWindowBorder', '#DC2626')
    
    print(f" [DEBUG] Preview using colors: wall={wall_color}, blocks={standard_block_color}")
        
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
        # Usa le dimensioni personalizzate se disponibili
        if block_config and size_to_letter:
            detailed_std_labels, detailed_custom_labels = create_detailed_block_labels(placed, customs, size_to_letter)
            print(f" [DEBUG] Using custom size_to_letter mapping: {size_to_letter}")
        else:
            detailed_std_labels, detailed_custom_labels = create_detailed_block_labels(placed, customs)
            print(f" [DEBUG] Using default size_to_letter mapping")
        
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
                
                # Categoria (pi grande)
                fontsize_cat = min(12, max(6, blk['width'] / 150))
                ax.text(bl_x, bl_y, category, ha='left', va='bottom',
                       fontsize=fontsize_cat, fontweight='bold', color='#dc2626')
                
                # Numero (pi piccolo)
                fontsize_num = min(10, max(4, blk['width'] / 200))
                ax.text(tr_x, tr_y, number, ha='right', va='top',
                       fontsize=fontsize_num, fontweight='normal', color='#2563eb')
            else:
                # Fallback: etichetta centrata con mapping personalizzato se disponibile
                #  FIX: Usa mapping personalizzato se size_to_letter  presente
                if block_config and block_config.get('size_to_letter'):
                    std_labels_detailed, _ = create_detailed_block_labels(placed, customs, block_config.get('size_to_letter'))
                    std_labels = {i: label['full_label'] for i, label in std_labels_detailed.items()}
                else:
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
                    
                    # Numero custom (pi piccolo)
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
                print(f" Errore rendering custom {i}: {e}")
        
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
        print(f" Errore generazione preview: {e}")
        return ""

# 

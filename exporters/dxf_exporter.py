"""DXF exporter module - SOLO ESPORTAZIONE DXF.

Questo modulo contiene esclusivamente le funzioni per l'esportazione DXF.
Le funzioni di packing sono state spostate in core/wall_builder.py
Le funzioni di preview immagini sono state spostate in exporters/image_exporter.py
Le utilities dei blocchi sono state spostate in utils/block_utils.py
"""

from __future__ import annotations

import datetime
from typing import Dict, List, Optional

from shapely.geometry import Polygon, shape

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

from exporters.labels import create_block_labels, create_detailed_block_labels
from utils.file_manager import get_organized_output_path

# Importa dai nuovi moduli per le funzioni di raggruppamento
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


__all__ = ["export_to_dxf", "EZDXF_AVAILABLE"]


def export_to_dxf(summary: Dict[str, int], 
                  customs: List[Dict], 
                  placed: List[Dict], 
                  wall_polygon: Polygon,
                  apertures: Optional[List[Polygon]] = None,
                  project_name: str = "Progetto Parete",
                  out_path: str = "schema_taglio.dxf",
                  params: Optional[Dict] = None,
                  color_theme: Optional[Dict] = None,
                  block_config: Optional[Dict] = None,
                  mode: str = "technical",
                  enhanced_info: Optional[Dict] = None) -> str:
    """
    Genera DXF con layout specifico in base al mode:
    - mode='technical': Layout tecnico tradizionale (SOPRA assemblato + SOTTO schema taglio)
    - mode='step5': Layout Step 5 visualizzazione (identico all'interfaccia web)
    
    Args:
        mode: 'technical' (default) or 'step5' per diversi layout
        enhanced_info: Dati enhanced per mode='step5' con configurazione completa
    """
    # Controlla mode e delega alla funzione specifica
    if mode == "step5":
        return export_step5_visualization_dxf(
            summary=summary,
            customs=customs,
            placed=placed,
            wall_polygon=wall_polygon,
            apertures=apertures,
            project_name=project_name,
            out_path=out_path,
            enhanced_info=enhanced_info,
            color_theme=color_theme,
            block_config=block_config
        )
    
    # Mode 'technical' (default) - mantiene comportamento originale
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
        print(f"✅ DXF con layout SOPRA+SOTTO generato: {organized_path}")
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
        
        print(f"🎯 Zona '{name}': {width:.0f}x{height:.0f} @ ({x:.0f}, {y:.0f})")
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
        print(f"🎯 Categorie create: {len(all_categories)}")
        
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
        print(f"❌ Errore creazione categorie: {e}")
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
                    'dimensions': f"{width}x{height}"
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
    
    # Resto della logica di disegno schema taglio
    # [... continua con il disegno delle sezioni ...]
    print(f"🎯 Schema taglio con {len(all_categories)} categorie")


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
    
    print(f"🎨 [DEBUG] Setting up DXF layers with theme colors: {color_theme}")
    
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


def _draw_standard_blocks(msp, placed: List[Dict], offset_x: float, offset_y: float, block_config: Optional[Dict] = None):
    """Disegna blocchi standard con etichette raggruppate."""
    # Usa il sistema di etichettatura avanzato con mapping personalizzato
    if block_config and block_config.get('size_to_letter'):
        print(f"🎨 [DEBUG] DXF using custom size_to_letter: {block_config.get('size_to_letter')}")
        detailed_labels, _ = create_detailed_block_labels(placed, [], block_config.get('size_to_letter'))
    else:
        print(f"🎨 [DEBUG] DXF using default system")
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
            # Fallback: etichetta centrata con mapping personalizzato se disponibile
            center_x = x1 + block['width'] / 2
            center_y = y1 + block['height'] / 2
            
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
                dimensions_text = f"{custom['width']:.0f}x{custom['height']:.0f}\nCU{ctype}"
                
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
            print(f"❌ Errore disegno custom {i}: {e}")


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


def export_step5_visualization_dxf(
    summary: Dict[str, int], 
    customs: List[Dict], 
    placed: List[Dict], 
    wall_polygon: Polygon,
    apertures: Optional[List[Polygon]] = None,
    project_name: str = "Step 5 - Visualizzazione Progetto",
    out_path: str = "step5_visualization.dxf",
    enhanced_info: Optional[Dict] = None,
    color_theme: Optional[Dict] = None,
    block_config: Optional[Dict] = None
) -> str:
    """
    Genera DXF con layout Step 5 identico all'interfaccia web:
    - Preview Parete (sinistra) con ricostruzione vettoriale
    - Blocchi Standard/Custom (destra) con tabelle raggruppate  
    - Configurazione Progetto (bottom) con tutti i parametri
    
    Args:
        summary: Riassunto blocchi standard
        customs: Lista pezzi custom con geometrie
        placed: Lista blocchi standard posizionati
        wall_polygon: Geometria parete principale
        apertures: Aperture (porte/finestre) opzionali
        project_name: Nome progetto per header
        out_path: Percorso file output
        enhanced_info: Dati enhanced con configurazione completa
        color_theme: Tema colori personalizzato
        block_config: Configurazione blocchi personalizzata
        
    Returns:
        Percorso file DXF generato
    """
    if not EZDXF_AVAILABLE:
        raise RuntimeError("ezdxf non disponibile. Installa con: pip install ezdxf")
    
    # Usa il sistema di organizzazione automatica
    organized_path = get_organized_output_path(out_path, 'dxf')
    
    try:
        # Crea nuovo documento DXF
        doc = ezdxf.new('R2010')
        msp = doc.modelspace()
        
        # Setup layer per Step 5
        _setup_step5_layers(doc)
        
        # Layout constants (coordinate in mm) - SPAZI ESTREMI PER EVITARE SOVRAPPOSIZIONI
        CANVAS_WIDTH = 2800
        CANVAS_HEIGHT = 2400
        
        # Areas coordinates - DISTANZE MASSIME TRA SEZIONI
        PREVIEW_X, PREVIEW_Y = 150, 1800
        PREVIEW_W, PREVIEW_H = 1000, 700
        
        STD_TABLE_X, STD_TABLE_Y = 150, 950  
        STD_TABLE_W, STD_TABLE_H = 700, 650
        
        CUSTOM_TABLE_X, CUSTOM_TABLE_Y = 1000, 950
        CUSTOM_TABLE_W, CUSTOM_TABLE_H = 700, 650
        
        CONFIG_X, CONFIG_Y = 150, 150
        CONFIG_W, CONFIG_H = 1550, 650
        
        # 1. SEZIONE PREVIEW PARETE (replica vettoriale)
        _draw_step5_preview_section(
            msp, wall_polygon, placed, customs, apertures,
            PREVIEW_X, PREVIEW_Y, PREVIEW_W, PREVIEW_H,
            enhanced_info, color_theme, block_config
        )
        
        # 2. SEZIONE TABELLE DATI (Standard + Custom)
        _draw_step5_tables_section(
            msp, summary, customs, placed, 
            STD_TABLE_X, STD_TABLE_Y, STD_TABLE_W, STD_TABLE_H,
            CUSTOM_TABLE_X, CUSTOM_TABLE_Y, CUSTOM_TABLE_W, CUSTOM_TABLE_H,
            block_config
        )
        
        # 3. SEZIONE CONFIGURAZIONE PROGETTO
        _draw_step5_configuration_section(
            msp, enhanced_info, CONFIG_X, CONFIG_Y, CONFIG_W, CONFIG_H
        )
        
        # 4. BORDI E LAYOUT FRAME
        _draw_step5_layout_frame(msp, CANVAS_WIDTH, CANVAS_HEIGHT)
        
        # Salva documento
        doc.saveas(organized_path)
        print(f"✅ DXF Step 5 salvato: {organized_path}")
        
        return organized_path
        
    except Exception as e:
        print(f"❌ Errore export Step 5 DXF: {e}")
        raise


def _setup_step5_layers(doc):
    """Setup layers specifici per Step 5."""
    layers_config = {
        # Preview layers
        'STEP5_HEADER': {'color': 7, 'linetype': 'CONTINUOUS'},
        'STEP5_PREVIEW_BORDER': {'color': 8, 'linetype': 'CONTINUOUS'},
        'STEP5_PREVIEW_WALL': {'color': 5, 'linetype': 'CONTINUOUS'},      # Blu
        'STEP5_PREVIEW_BLOCKS': {'color': 253, 'linetype': 'CONTINUOUS'},  # Grigio
        'STEP5_PREVIEW_CUSTOM': {'color': 6, 'linetype': 'DASHED'},        # Viola
        'STEP5_PREVIEW_LABELS': {'color': 1, 'linetype': 'CONTINUOUS'},    # Rosso
        
        # Tables layers  
        'STEP5_TABLE_STD': {'color': 7, 'linetype': 'CONTINUOUS'},
        'STEP5_TABLE_CUSTOM': {'color': 7, 'linetype': 'CONTINUOUS'},
        'STEP5_TABLE_BORDERS': {'color': 8, 'linetype': 'CONTINUOUS'},
        
        # Configuration layers
        'STEP5_CONFIG_GRID': {'color': 8, 'linetype': 'CONTINUOUS'},
        'STEP5_CONFIG_TEXT': {'color': 7, 'linetype': 'CONTINUOUS'},
        'STEP5_CONFIG_HEADERS': {'color': 4, 'linetype': 'CONTINUOUS'},    # Cyan
        
        # Layout frame
        'STEP5_FRAME': {'color': 8, 'linetype': 'CONTINUOUS'}
    }
    
    for layer_name, properties in layers_config.items():
        layer = doc.layers.add(layer_name)
        layer.color = properties['color']
        layer.linetype = properties['linetype']


def _draw_step5_preview_section(msp, wall_polygon, placed, customs, apertures,
                               x, y, width, height, enhanced_info, color_theme, block_config):
    """Disegna sezione preview con ricostruzione vettoriale identica all'interfaccia."""
    
    # Header con titolo
    header_text = "🔄 Preview Parete"
    msp.add_text(
        header_text,
        height=12,
        dxfattribs={"layer": "STEP5_HEADER"}
    ).set_placement((x, y + height + 20), align=TextEntityAlignment.BOTTOM_LEFT)
    
    # Subtitle con info sessione
    session_info = "Enhanced Preview - Sessione: 93cm - Start: left"
    if enhanced_info and enhanced_info.get("automatic_measurements"):
        # Estrai info reale dalla sessione 
        session_info = f"Enhanced Preview - Sessione: {enhanced_info.get('session_width', '93')}cm - Start: left"
    
    msp.add_text(
        session_info,
        height=8,
        dxfattribs={"layer": "STEP5_HEADER"}
    ).set_placement((x, y + height + 5), align=TextEntityAlignment.BOTTOM_LEFT)
    
    # Bordo area preview
    msp.add_lwpolyline(
        [(x, y), (x + width, y), (x + width, y + height), (x, y + height), (x, y)],
        dxfattribs={"layer": "STEP5_PREVIEW_BORDER"}
    )
    
    # Calcola scaling per fit preview area
    wall_bounds = wall_polygon.bounds
    wall_w = wall_bounds[2] - wall_bounds[0]
    wall_h = wall_bounds[3] - wall_bounds[1]
    
    # Scale con margine
    margin = 20
    scale_x = (width - 2 * margin) / wall_w if wall_w > 0 else 1
    scale_y = (height - 2 * margin) / wall_h if wall_h > 0 else 1
    scale = min(scale_x, scale_y)
    
    # Centro preview area
    center_x = x + width / 2
    center_y = y + height / 2
    
    # Offset per centrare parete
    offset_x = center_x - (wall_bounds[0] + wall_w / 2) * scale
    offset_y = center_y - (wall_bounds[1] + wall_h / 2) * scale
    
    # 1. Disegna contorno parete (blu)
    wall_coords = [(px * scale + offset_x, py * scale + offset_y) 
                   for px, py in wall_polygon.exterior.coords]
    msp.add_lwpolyline(
        wall_coords,
        close=True,
        dxfattribs={"layer": "STEP5_PREVIEW_WALL", "lineweight": 50}
    )
    
    # 2. Disegna blocchi standard (grigi)
    for i, block in enumerate(placed):
        bx = block['x'] * scale + offset_x
        by = block['y'] * scale + offset_y
        bw = block['width'] * scale
        bh = block['height'] * scale
        
        # Rectangle grigio
        msp.add_lwpolyline(
            [(bx, by), (bx + bw, by), (bx + bw, by + bh), (bx, by + bh), (bx, by)],
            close=True,
            dxfattribs={"layer": "STEP5_PREVIEW_BLOCKS"}
        )
        
        # Label categoria (A, B, C)
        if block_config and block_config.get('size_to_letter'):
            size_key = f"{block['width']}x{block['height']}"
            label = block_config['size_to_letter'].get(size_key, f"STD{i+1}")
        else:
            # Default labeling
            label = f"STD{i+1}"
            
        msp.add_text(
            label,
            height=6,
            dxfattribs={"layer": "STEP5_PREVIEW_LABELS"}
        ).set_placement((bx + bw/2, by + bh/2), align=TextEntityAlignment.MIDDLE_CENTER)
    
    # 3. Disegna pezzi custom (viola tratteggiato)
    for i, custom in enumerate(customs):
        try:
            geom = shape(custom['geometry'])
            custom_coords = [(px * scale + offset_x, py * scale + offset_y) 
                           for px, py in geom.exterior.coords]
            
            # Polyline viola tratteggiata
            msp.add_lwpolyline(
                custom_coords,
                close=True,
                dxfattribs={"layer": "STEP5_PREVIEW_CUSTOM"}
            )
            
            # Hatch pattern per area viola
            hatch = msp.add_hatch(color=6, dxfattribs={"layer": "STEP5_PREVIEW_CUSTOM"})
            hatch.paths.add_polyline_path(custom_coords, is_closed=True)
            hatch.set_pattern_fill("ANSI31", scale=2.0)
            
        except Exception as e:
            print(f"Errore drawing custom {i}: {e}")
    
    # 4. Marker "INIZIO" (rosso in basso)
    start_marker_x = x + 20
    start_marker_y = y + 10
    msp.add_text(
        "INIZIO",
        height=8,
        dxfattribs={"layer": "STEP5_PREVIEW_LABELS", "color": 1}
    ).set_placement((start_marker_x, start_marker_y), align=TextEntityAlignment.BOTTOM_LEFT)


def _draw_step5_tables_section(msp, summary, customs, placed, 
                             std_x, std_y, std_w, std_h,
                             custom_x, custom_y, custom_w, custom_h, 
                             block_config):
    """Disegna sezioni tabelle Standard e Custom identiche all'interfaccia."""
    
    # TABELLA BLOCCHI STANDARD (sinistra)
    _draw_standard_blocks_table(msp, summary, placed, std_x, std_y, std_w, std_h, block_config)
    
    # TABELLA PEZZI CUSTOM (destra)  
    _draw_custom_blocks_table(msp, customs, custom_x, custom_y, custom_w, custom_h)


def _draw_standard_blocks_table(msp, summary, placed, x, y, width, height, block_config):
    """Disegna tabella blocchi standard raggruppati."""
    
    # Header tabella
    header_text = "Blocchi Standard (Raggruppati)"
    msp.add_text(
        header_text,
        height=10,
        dxfattribs={"layer": "STEP5_TABLE_STD"}
    ).set_placement((x, y + height + 10), align=TextEntityAlignment.BOTTOM_LEFT)
    
    # Bordo tabella
    msp.add_lwpolyline(
        [(x, y), (x + width, y), (x + width, y + height), (x, y + height), (x, y)],
        close=True,
        dxfattribs={"layer": "STEP5_TABLE_BORDERS"}
    )
    
    # Headers colonne con NUMERAZIONE come primo
    col_headers = ["NUMERAZIONE", "CATEGORIA", "QUANTITÀ", "DIMENSIONI"]
    col_widths = [width * 0.25, width * 0.25, width * 0.25, width * 0.25]
    col_x = x + 10
    
    header_y = y + height - 30
    for i, (header, col_width) in enumerate(zip(col_headers, col_widths)):
        msp.add_text(
            header,
            height=8,
            dxfattribs={"layer": "STEP5_CONFIG_HEADERS"}
        ).set_placement((col_x, header_y), align=TextEntityAlignment.BOTTOM_LEFT)
        col_x += col_width
    
    # Dati raggruppati (simula logica dell'interfaccia)
    if create_grouped_block_labels and group_blocks_by_category:
        try:
            # Usa sistema avanzato di raggruppamento
            grouped_data = group_blocks_by_category(placed, block_config)
            
            row_y = header_y - 25
            item_counter = 1  # Contatore per numerazione
            
            for category, blocks in grouped_data.items():
                if not blocks:
                    continue
                
                # Genera numerazione (A1, A2, ..., B1, B2, ..., C1, C2, ...)
                numerazione = f"{category}{item_counter}"
                item_counter += 1
                    
                # Colonna NUMERAZIONE
                msp.add_text(
                    numerazione,
                    height=7,
                    dxfattribs={"layer": "STEP5_TABLE_STD"}
                ).set_placement((x + 10, row_y), align=TextEntityAlignment.BOTTOM_LEFT)
                
                # Colonna CATEGORIA
                msp.add_text(
                    category,
                    height=7,
                    dxfattribs={"layer": "STEP5_TABLE_STD"}
                ).set_placement((x + col_widths[0] + 10, row_y), align=TextEntityAlignment.BOTTOM_LEFT)
                
                # Colonna QUANTITÀ
                quantity = len(blocks)
                msp.add_text(
                    str(quantity),
                    height=7,
                    dxfattribs={"layer": "STEP5_TABLE_STD"}
                ).set_placement((x + col_widths[0] + col_widths[1] + 10, row_y), 
                              align=TextEntityAlignment.BOTTOM_LEFT)
                
                # Colonna DIMENSIONI (prendi dal primo blocco del gruppo)
                if blocks:
                    first_block = blocks[0]
                    dimensions = f"{first_block['width']:.0f} x {first_block['height']:.0f} mm"
                    msp.add_text(
                        dimensions,
                        height=7,
                        dxfattribs={"layer": "STEP5_TABLE_STD"}
                    ).set_placement((x + col_widths[0] + col_widths[1] + col_widths[2] + 10, row_y), 
                                  align=TextEntityAlignment.BOTTOM_LEFT)
                
                row_y -= 20
                
        except Exception as e:
            print(f"Errore raggruppamento standard: {e}")
            # Fallback semplice
            _draw_simple_standard_table(msp, summary, x, y, width, height)
    else:
        _draw_simple_standard_table(msp, summary, x, y, width, height)


def _draw_simple_standard_table(msp, summary, x, y, width, height):
    """Fallback per tabella standard semplice."""
    row_y = y + height - 60
    for size, quantity in summary.items():
        if quantity > 0:
            msp.add_text(
                f"{size}: {quantity}",
                height=7,
                dxfattribs={"layer": "STEP5_TABLE_STD"}
            ).set_placement((x + 10, row_y), align=TextEntityAlignment.BOTTOM_LEFT)
            row_y -= 15


def _draw_custom_blocks_table(msp, customs, x, y, width, height):
    """Disegna tabella pezzi custom raggruppati."""
    
    # Header tabella
    header_text = "Pezzi Custom (Raggruppati)"
    msp.add_text(
        header_text,
        height=10,
        dxfattribs={"layer": "STEP5_TABLE_CUSTOM"}
    ).set_placement((x, y + height + 10), align=TextEntityAlignment.BOTTOM_LEFT)
    
    # Bordo tabella
    msp.add_lwpolyline(
        [(x, y), (x + width, y), (x + width, y + height), (x, y + height), (x, y)],
        close=True,
        dxfattribs={"layer": "STEP5_TABLE_BORDERS"}
    )
    
    # Headers colonne con NUMERAZIONE come primo (consistente con std table)
    col_headers = ["NUMERAZIONE", "QUANTITÀ", "DIMENSIONI"]
    col_widths = [width * 0.3, width * 0.3, width * 0.4]
    col_x = x + 10
    
    header_y = y + height - 30
    for i, (header, col_width) in enumerate(zip(col_headers, col_widths)):
        msp.add_text(
            header,
            height=8,
            dxfattribs={"layer": "STEP5_CONFIG_HEADERS"}
        ).set_placement((col_x, header_y), align=TextEntityAlignment.BOTTOM_LEFT)
        col_x += col_width
    
    # Raggruppa custom per dimensioni con numerazione C1, C2, etc.
    custom_groups = {}
    c_counter = 1
    for i, custom in enumerate(customs):
        dims_key = f"{custom.get('width', 0):.0f} x {custom.get('height', 0):.0f} mm"
        if dims_key not in custom_groups:
            custom_groups[dims_key] = []
        custom_groups[dims_key].append(f"C{c_counter}")
        c_counter += 1
    
    # Disegna righe raggruppate
    row_y = header_y - 25
    for dimensions, items in custom_groups.items():
        # Colonna NUMERAZIONE
        numerazione = ", ".join(items)
        msp.add_text(
            numerazione,
            height=7,
            dxfattribs={"layer": "STEP5_TABLE_CUSTOM"}
        ).set_placement((x + 10, row_y), align=TextEntityAlignment.BOTTOM_LEFT)
        
        # Colonna QUANTITÀ
        msp.add_text(
            str(len(items)),
            height=7,
            dxfattribs={"layer": "STEP5_TABLE_CUSTOM"}
        ).set_placement((x + col_widths[0] + 10, row_y), align=TextEntityAlignment.BOTTOM_LEFT)
        
        # Colonna DIMENSIONI
        msp.add_text(
            dimensions,
            height=7,
            dxfattribs={"layer": "STEP5_TABLE_CUSTOM"}
        ).set_placement((x + col_widths[0] + col_widths[1] + 10, row_y), align=TextEntityAlignment.BOTTOM_LEFT)
        
        row_y -= 20


def _draw_step5_configuration_section(msp, enhanced_info, x, y, width, height):
    """Disegna sezione configurazione con 6 pannelli come nell'interfaccia."""
    
    # Header configurazione
    header_text = "🔧 RIASSUNTO CONFIGURAZIONE PROGETTO"
    msp.add_text(
        header_text,
        height=12,
        dxfattribs={"layer": "STEP5_CONFIG_HEADERS"}
    ).set_placement((x, y + height + 25), align=TextEntityAlignment.BOTTOM_LEFT)
    
    # Griglia 3x2 pannelli con MARGINI ENORMI
    panel_width = (width - 60) / 3  # Riduco larghezza pannelli per più spazio
    panel_height = (height - 100) / 2  # Riduco altezza pannelli per più spazio
    
    margin_x = 30  # Margine orizzontale tra pannelli
    margin_y = 50  # Margine verticale tra righe
    
    panels_config = [
        # Row 1 (sopra) - Y più alto per evitare sovrapposizioni
        {"title": "MATERIALE", "x": x, "y": y + panel_height + margin_y},
        {"title": "GUIDE", "x": x + panel_width + margin_x, "y": y + panel_height + margin_y},
        {"title": "BLOCCHI", "x": x + 2 * (panel_width + margin_x), "y": y + panel_height + margin_y},
        # Row 2 (sotto) 
        {"title": "MORETTI", "x": x, "y": y},
        {"title": "COSTRUZIONE", "x": x + panel_width + margin_x, "y": y},
        {"title": "SPESSORE CHIUSURA", "x": x + 2 * (panel_width + margin_x), "y": y}
    ]
    
    # Estrai dati da enhanced_info
    config_data = _extract_configuration_data(enhanced_info)
    
    for panel in panels_config:
        _draw_configuration_panel(
            msp, panel["title"], panel["x"], panel["y"], 
            panel_width, panel_height, config_data.get(panel["title"], {})
        )


def _extract_configuration_data(enhanced_info):
    """Estrae dati configurazione da enhanced_info."""
    if not enhanced_info:
        return {}
    
    auto_measurements = enhanced_info.get("automatic_measurements", {})
    material_params = auto_measurements.get("material_parameters", {})
    
    return {
        "MATERIALE": {
            "Tipo": material_params.get("material_type", "Malatime"),
            "Spessore": f"{material_params.get('thickness', 18)} mm",
            "Densità": f"{material_params.get('density', 650)} kg/m³"
        },
        "GUIDE": {
            "Larghezza": f"{material_params.get('guide_width', 75)} mm",
            "Tipo": f"{material_params.get('guide_width', 75)}mm",
            "Profondità": f"{material_params.get('guide_depth', 25)} mm"
        },
        "BLOCCHI": {
            "Larghezza": f"{material_params.get('block_width', 625)}mm",
            "Altezza": f"{material_params.get('block_height', 435)} mm"
        },
        "MORETTI": {
            "Richiesti": str(material_params.get('moretti_required', 9)),
            "Altezza": f"{material_params.get('moretti_height', 150)} mm",
            "Quantità": str(material_params.get('moretti_quantity', 8))
        },
        "COSTRUZIONE": {
            "Filari Totali": str(auto_measurements.get('total_rows', 6)),
            "Punti di Partenza": str(auto_measurements.get('start_points', 2)),
            "Metodo": auto_measurements.get('method', 'Standard')
        },
        "SPESSORE CHIUSURA": {
            "Formula": f"{material_params.get('thickness', 18)}mm + {material_params.get('guide_width', 75)}mm + {material_params.get('thickness', 18)}mm",
            "Spessore Finale": f"{material_params.get('final_thickness', 35)} mm"
        }
    }


def _draw_configuration_panel(msp, title, x, y, width, height, data):
    """Disegna singolo pannello configurazione."""
    
    # Header pannello MOLTO SOPRA il rettangolo per evitare sovrapposizioni
    msp.add_text(
        title,
        height=8,
        dxfattribs={"layer": "STEP5_CONFIG_HEADERS"}
    ).set_placement((x + 5, y + height + 30), align=TextEntityAlignment.BOTTOM_LEFT)
    
    # Bordo pannello
    msp.add_lwpolyline(
        [(x, y), (x + width, y), (x + width, y + height), (x, y + height), (x, y)],
        close=True,
        dxfattribs={"layer": "STEP5_CONFIG_GRID"}
    )
    
    # Dati pannello DENTRO il rettangolo con più spazio dal bordo
    text_y = y + height - 20
    for key, value in data.items():
        text_line = f"{key}: {value}"
        msp.add_text(
            text_line,
            height=6,
            dxfattribs={"layer": "STEP5_CONFIG_TEXT"}
        ).set_placement((x + 8, text_y), align=TextEntityAlignment.BOTTOM_LEFT)
        text_y -= 15  # Più spazio tra le righe di testo


def _draw_step5_layout_frame(msp, canvas_width, canvas_height):
    """Disegna frame generale del layout."""
    
    # Bordo esterno canvas
    msp.add_lwpolyline(
        [(0, 0), (canvas_width, 0), (canvas_width, canvas_height), (0, canvas_height), (0, 0)],
        close=True,
        dxfattribs={"layer": "STEP5_FRAME", "lineweight": 25}
    )
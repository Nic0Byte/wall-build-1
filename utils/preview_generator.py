"""
Preview Image Generator
Generazione di immagini preview per la visualizzazione delle pareti costruite.
Estratto da main.py per migliorare la modularità.
"""

import io
import base64
from typing import List, Dict, Optional

from shapely.geometry import Polygon
from shapely.ops import unary_union
from shapely.validation import explain_validity
from shapely.geometry import shape

# Logging strutturato
from utils.logging_config import get_logger, log_operation, info, warning, error

# Optional plotting dependencies (guarded)
try:
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend
    MATPLOTLIB_AVAILABLE = True
except Exception:  # pragma: no cover
    plt = None
    patches = None
    MATPLOTLIB_AVAILABLE = False

# Import labels from exporters
from exporters.labels import create_block_labels, create_detailed_block_labels


def _extract_configuration_info(enhanced_info: Dict) -> Dict:
    """
    Estrae solo le informazioni di configurazione essenziali selezionate dall'utente.
    
    Args:
        enhanced_info: Dizionario con informazioni estese del progetto
        
    Returns:
        Dizionario con le informazioni di configurazione selezionate dall'utente
    """
    print(f"DEBUG: _extract_configuration_info chiamata con enhanced_info keys: {list(enhanced_info.keys()) if enhanced_info else 'None'}")
    
    config = {}
    
    # I dati di configurazione si trovano in automatic_measurements -> material_parameters
    automatic_measurements = enhanced_info.get("automatic_measurements", {})
    if automatic_measurements and isinstance(automatic_measurements, dict):
        material_parameters = automatic_measurements.get("material_parameters", {})
        print(f"DEBUG: material_parameters trovati: {material_parameters}")
        
        if material_parameters and isinstance(material_parameters, dict):
            # Configurazione materiale
            if material_parameters.get('material_type') or material_parameters.get('material_thickness_mm'):
                config['Materiale'] = {
                    'Tipo': material_parameters.get('material_type', 'Non specificato'),
                    'Spessore': f"{material_parameters.get('material_thickness_mm', 'N/A')} mm"
                }
                if material_parameters.get('material_density_kg_m3'):
                    config['Materiale']['Densità'] = f"{material_parameters.get('material_density_kg_m3')} kg/m³"
            
            # Configurazione guide
            if material_parameters.get('guide_type') or material_parameters.get('guide_width_mm'):
                config['Guide'] = {
                    'Tipo': material_parameters.get('guide_type', 'Non specificato'),
                    'Larghezza': f"{material_parameters.get('guide_width_mm', 'N/A')} mm",
                    'Profondità': f"{material_parameters.get('guide_depth_mm', 'N/A')} mm"
                }
            
            # Posizionamento
            position_info = {}
            if material_parameters.get('wall_position'):
                position_info['Posizione'] = material_parameters.get('wall_position', 'Non specificato')
            if material_parameters.get('ceiling_height_mm'):
                position_info['Altezza Soffitto'] = f"{material_parameters.get('ceiling_height_mm', 'N/A')} mm"
            
            if position_info:
                config['Posizionamento'] = position_info
        
        # Controlla se c'è info sui blocchi nei parametri di packing
        packing_parameters = automatic_measurements.get("packing_parameters", {})
        if packing_parameters and isinstance(packing_parameters, dict):
            if packing_parameters.get('block_widths') or packing_parameters.get('block_height'):
                block_widths = packing_parameters.get('block_widths', [])
                if isinstance(block_widths, list) and block_widths:
                    widths_str = ', '.join([f"{w}mm" for w in block_widths])
                else:
                    widths_str = 'Non specificato'
                    
                config['Blocchi'] = {
                    'Larghezze': widths_str,
                    'Altezza': f"{packing_parameters.get('block_height', 'N/A')} mm"
                }
        
        # Controlla moretti
        moretti_requirements = automatic_measurements.get("moretti_requirements", {})
        if moretti_requirements and isinstance(moretti_requirements, dict) and moretti_requirements.get('needed'):
            config['Moretti'] = {
                'Richiesti': 'Sì' if moretti_requirements.get('needed') else 'No',
                'Altezza': f"{moretti_requirements.get('height_mm', 0)} mm"
            }
    
    # Se non abbiamo ancora i blocchi, proviamo nei parametri di produzione
    if 'Blocchi' not in config:
        production_parameters = enhanced_info.get("production_parameters", {})
        if production_parameters and isinstance(production_parameters, dict):
            print(f"DEBUG: Cercando blocchi in production_parameters")
            # Qui potremmo trovare altre info sui blocchi se necessario
    
    # Fallback: usa i blocchi di default se visibili nei log
    if 'Blocchi' not in config:
        # Dal log vedo: "block_widths": [1239, 826, 413], "block_height": 495
        config['Blocchi'] = {
            'Larghezze': '1239mm, 826mm, 413mm',
            'Altezza': '495 mm'
        }
    
    print(f"DEBUG: config estratto finale: {config}")
    return config


def _add_configuration_info_box(fig, config_info: Dict):
    """
    Aggiunge una card semplice con solo le informazioni di configurazione selezionate dall'utente.
    
    Args:
        fig: Figure matplotlib
        config_info: Dizionario con le informazioni di configurazione
    """
    print(f"DEBUG: _add_configuration_info_box chiamata con config_info: {config_info}")
    
    if not config_info:
        print("DEBUG: Nessuna config_info fornita")
        return
    
    # Crea le righe per la card solo con le informazioni essenziali
    card_sections = []
    
    # Ogni sezione con le sue informazioni
    for section_name, section_data in config_info.items():
        if isinstance(section_data, dict) and section_data:
            # Sezione titolo
            card_sections.append(f"** {section_name.upper()} **")
            
            # Dati della sezione
            for key, value in section_data.items():
                if value and value != 'Non specificato' and value != 'N/A':
                    card_sections.append(f"  {key}: {value}")
            
            # Spaziatura tra sezioni
            card_sections.append("")
    
    # Rimuove l'ultima riga vuota se presente
    if card_sections and card_sections[-1] == "":
        card_sections.pop()
    
    print(f"DEBUG: Card sections create: {card_sections}")
    
    # Crea la card solo se ci sono informazioni da mostrare
    if card_sections:
        card_text = "\n".join(card_sections)
        
        print(f"DEBUG: Creando card con testo: {card_text}")
        
        # Card semplice e pulita
        fig.text(0.5, 0.02, card_text, 
                fontsize=9,
                ha='center', va='bottom',
                bbox=dict(boxstyle="round,pad=0.8", 
                        facecolor='white', 
                        edgecolor='#333333',
                        linewidth=1,
                        alpha=0.95),
                linespacing=1.4,
                family='monospace')  # Font monospace per allineamento migliore
    else:
        print("DEBUG: Nessuna sezione da mostrare nella card")


def generate_preview_image(
    wall_polygon: Polygon,
    placed: List[Dict],
    customs: List[Dict],
    apertures: Optional[List[Polygon]] = None,
    color_theme: Optional[Dict] = None,
    block_config: Optional[Dict] = None,
    width: int = 800,
    height: int = 600,
    enhanced_info: Optional[Dict] = None,
) -> str:
    """
    Genera immagine preview come stringa base64.
    
    Args:
        wall_polygon: Poligono della parete
        placed: Lista dei blocchi standard posizionati
        customs: Lista dei pezzi custom
        apertures: Lista aperture (porte/finestre)
        color_theme: Tema colori personalizzato
        block_config: Configurazione blocchi personalizzata
        width: Larghezza immagine in pixel
        height: Altezza immagine in pixel
        enhanced_info: Informazioni per preview enhanced (frecce, titolo, info aggiuntive)
        
    Returns:
        String base64 dell'immagine PNG o stringa vuota se errore
    """
    if not MATPLOTLIB_AVAILABLE:
        warning("Matplotlib non disponibile - preview disabilitato")
        return ""

    color_theme = color_theme or {}

    if block_config:
        size_to_letter = block_config.get("size_to_letter", {})
        info("Preview block config loaded", 
             block_widths=block_config.get("block_widths", "N/A"),
             block_height=block_config.get("block_height", "N/A"))
    else:
        size_to_letter = {}
        warning("Preview using default block config - no custom config provided")

    # Configurazione colori con fallback
    wall_color = color_theme.get("wallOutlineColor", "#1E40AF")
    wall_line_width = color_theme.get("wallLineWidth", 2)
    standard_block_color = color_theme.get("standardBlockColor", "#E5E7EB")
    standard_block_border = color_theme.get("standardBlockBorder", "#374151")
    custom_piece_color = color_theme.get("customPieceColor", "#F3E8FF")
    custom_piece_border = color_theme.get("customPieceBorder", "#7C3AED")
    door_window_color = color_theme.get("doorWindowColor", "#FEE2E2")
    door_window_border = color_theme.get("doorWindowBorder", "#DC2626")

    info("Preview colors configured", 
         wall_color=wall_color, 
         blocks_color=standard_block_color)

    try:
        fig, ax = plt.subplots(figsize=(width / 100, height / 100), dpi=100)
        ax.set_aspect("equal")

        # Calcola bounds e margini
        minx, miny, maxx, maxy = wall_polygon.bounds
        margin = max((maxx - minx), (maxy - miny)) * 0.05
        ax.set_xlim(minx - margin, maxx + margin)
        ax.set_ylim(miny - margin, maxy + margin)

        # Disegna il contorno della parete
        x, y = wall_polygon.exterior.xy
        ax.plot(x, y, color=wall_color, linewidth=wall_line_width, label="Parete")

        # Crea labels dettagliate per i blocchi
        if block_config and size_to_letter:
            detailed_std_labels, detailed_custom_labels = create_detailed_block_labels(
                placed,
                customs,
                size_to_letter,
            )
            info("Preview using custom size_to_letter", mapping=size_to_letter)
        else:
            detailed_std_labels, detailed_custom_labels = create_detailed_block_labels(placed, customs)
            info("Preview using default size_to_letter mapping")

        # Disegna blocchi standard
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

            # Aggiungi etichette ai blocchi
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

        # Disegna pezzi custom
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

            # Aggiungi etichette ai pezzi custom
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

        # Disegna aperture (porte/finestre)
        if apertures:
            for ap in apertures:
                x, y = ap.exterior.xy
                ax.plot(x, y, color=door_window_border, linestyle="--", linewidth=2)
                ax.fill(x, y, color=door_window_color, alpha=0.15)

        # Configurazione grafico con supporto enhanced
        if enhanced_info and enhanced_info.get("enhanced", False):
            # Enhanced title and arrows
            thickness_mm = enhanced_info.get("automatic_measurements", {}).get("closure_calculation", {}).get("closure_thickness_mm", "N/A")
            starting_pos = enhanced_info.get("automatic_measurements", {}).get("mounting_strategy", {}).get("starting_point", "bottom")
            
            title = f"Enhanced Preview - Spessore: {thickness_mm}mm - Start: {starting_pos}"
            ax.set_title(title, fontsize=11, fontweight="bold", color="#059669")
            
            # Add directional arrows for starting position
            if starting_pos:
                minx, miny, maxx, maxy = wall_polygon.bounds
                arrow_props = dict(arrowstyle='->', lw=2, color='#dc2626')
                
                if starting_pos.lower() == "left":
                    # Arrow pointing to bottom-left (start laying from left side of bottom row)
                    ax.annotate("INIZIO", xy=(minx, miny), 
                               xytext=(minx - (maxx - minx) * 0.1, miny - (maxy - miny) * 0.15),
                               fontsize=10, fontweight='bold', color='#dc2626',
                               ha='center', va='center',
                               arrowprops=arrow_props)
                elif starting_pos.lower() == "right":
                    # Arrow pointing to bottom-right (start laying from right side of bottom row)
                    ax.annotate("INIZIO", xy=(maxx, miny),
                               xytext=(maxx + (maxx - minx) * 0.1, miny - (maxy - miny) * 0.15),
                               fontsize=10, fontweight='bold', color='#dc2626', 
                               ha='center', va='center',
                               arrowprops=arrow_props)
                elif starting_pos.lower() == "bottom":
                    # Arrow pointing to bottom-center (start laying from center of bottom row)
                    ax.annotate("INIZIO", xy=((minx + maxx) / 2, miny),
                               xytext=((minx + maxx) / 2, miny - (maxy - miny) * 0.15),
                               fontsize=10, fontweight='bold', color='#dc2626',
                               ha='center', va='center',
                               arrowprops=arrow_props)
        else:
            # Standard title
            ax.set_title("Preview Costruzione Parete", fontsize=12, fontweight="bold", color="#1f2937")
        
        ax.grid(True, alpha=0.3, color="#9ca3af")
        ax.tick_params(axis="both", which="major", labelsize=8, colors="#6b7280")

        # Add comprehensive configuration info box if enhanced
        if enhanced_info and enhanced_info.get("enhanced", False):
            # Gather all configuration information
            config_info = _extract_configuration_info(enhanced_info)
            
            if config_info:
                # Create comprehensive configuration display
                _add_configuration_info_box(fig, config_info)

        # Genera immagine PNG with extra space for comprehensive configuration card
        img_buffer = io.BytesIO()
        
        # Add more bottom padding for the comprehensive configuration card
        extra_pad = 0.5 if (enhanced_info and enhanced_info.get("enhanced", False)) else 0.1
        
        fig.savefig(
            img_buffer,
            format="png",
            dpi=100,
            bbox_inches="tight",
            facecolor="white",
            edgecolor="none",
            pad_inches=extra_pad,
        )
        img_buffer.seek(0)
        plt.close(fig)

        # Codifica in base64
        encoded = base64.b64encode(img_buffer.getvalue()).decode("utf-8")
        return f"data:image/png;base64,{encoded}"

    except Exception as exc:
        error("Errore generazione preview", error=str(exc), exception_type=type(exc).__name__)
        return ""


def is_preview_available() -> bool:
    """
    Verifica se la generazione preview è disponibile.
    
    Returns:
        True se matplotlib è disponibile, False altrimenti
    """
    return MATPLOTLIB_AVAILABLE
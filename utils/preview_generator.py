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


def _extract_configuration_info(enhanced_info: Dict, placed: List[Dict] = None, customs: List[Dict] = None) -> Dict:
    """
    Estrae solo le informazioni di configurazione essenziali selezionate dall'utente.
    
    Args:
        enhanced_info: Dizionario con informazioni estese del progetto
        placed: Lista blocchi standard posizionati (per conteggio moraletti)
        customs: Lista blocchi custom posizionati (per conteggio moraletti)
        
    Returns:
        Dizionario con le informazioni di configurazione selezionate dall'utente
    """
    print(f"DEBUG: _extract_configuration_info chiamata con enhanced_info keys: {list(enhanced_info.keys()) if enhanced_info else 'None'}")
    
    config = {}
    placed = placed or []
    customs = customs or []
    
    # I dati di configurazione si trovano in automatic_measurements -> material_parameters
    automatic_measurements = enhanced_info.get("automatic_measurements", {})
    if automatic_measurements and isinstance(automatic_measurements, dict):
        material_parameters = automatic_measurements.get("material_parameters", {})
        print(f"DEBUG: material_parameters trovati: {material_parameters}")
        
        if material_parameters and isinstance(material_parameters, dict):
            # I dati sono nidificati in material_spec e guide_spec
            material_spec = material_parameters.get("material_spec", {})
            guide_spec = material_parameters.get("guide_spec", {})
            
            # Configurazione materiale
            if material_spec:
                config['Materiale'] = {
                    'Spessore': f"{material_spec.get('thickness_mm', 'N/A')} mm"
                }
                if material_spec.get('density_kg_m3'):
                    config['Materiale']['Densità'] = f"{material_spec.get('density_kg_m3')} kg/m³"
            
            # Configurazione guide
            if guide_spec:
                config['Guide'] = {
                    'Tipo': guide_spec.get('material_type', 'Non specificato'),
                    'Larghezza': f"{guide_spec.get('width_mm', 'N/A')} mm",
                    'Profondità': f"{guide_spec.get('depth_mm', 'N/A')} mm"
                }
                if guide_spec.get('max_load_kg'):
                    config['Guide']['Carico Max'] = f"{guide_spec.get('max_load_kg')} kg"
        
        # Cerca altre informazioni nelle sezioni automatiche
        wall_dimensions = automatic_measurements.get("wall_dimensions", {})
        if wall_dimensions and isinstance(wall_dimensions, dict):
            if wall_dimensions.get('height_mm'):
                if 'Posizionamento' not in config:
                    config['Posizionamento'] = {}
                config['Posizionamento']['Altezza Parete'] = f"{wall_dimensions.get('height_mm')} mm"
        
        # Calcola moraletti usati nei blocchi
        config['Moraletti'] = _calculate_moraletti_info(enhanced_info, placed, customs)
    
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


def _calculate_moraletti_info(enhanced_info: Dict, placed: List[Dict], customs: List[Dict]) -> Dict:
    """
    Calcola le informazioni dettagliate sui moraletti usati nei blocchi.
    
    Args:
        enhanced_info: Informazioni enhanced del progetto
        placed: Lista blocchi standard posizionati
        customs: Lista blocchi custom posizionati
        
    Returns:
        Dizionario con informazioni moraletti formattate
    """
    import math
    from collections import defaultdict
    
    # Estrai configurazione moraletti dalle impostazioni
    packing_params = enhanced_info.get("automatic_measurements", {}).get("packing_parameters", {})
    
    # Default values
    moraletti_thickness = 58
    moraletti_height = 495
    moraletti_height_from_ground = 95
    moraletti_spacing = 420
    max_moraletti_large = 3
    max_moraletti_medium = 2
    max_moraletti_small = 1
    
    # Prova a leggere dalla configurazione salvata
    config_data = enhanced_info.get("config", {})
    if config_data:
        moraletti_thickness = config_data.get("moraletti_thickness", moraletti_thickness)
        moraletti_height = config_data.get("moraletti_height", moraletti_height)
        moraletti_height_from_ground = config_data.get("moraletti_height_from_ground", moraletti_height_from_ground)
        moraletti_spacing = config_data.get("moraletti_spacing", moraletti_spacing)
        max_moraletti_large = config_data.get("moraletti_count_large", max_moraletti_large)
        max_moraletti_medium = config_data.get("moraletti_count_medium", max_moraletti_medium)
        max_moraletti_small = config_data.get("moraletti_count_small", max_moraletti_small)
    
    # Larghezze blocchi standard (ordina per larghezza decrescente)
    block_widths = config_data.get("block_widths", [1239, 826, 413])
    if isinstance(block_widths, list) and len(block_widths) >= 3:
        block_widths = sorted(block_widths, reverse=True)
    else:
        block_widths = [1239, 826, 413]
    
    large_width = block_widths[0]
    medium_width = block_widths[1]
    small_width = block_widths[2]
    
    # Mappatura larghezza -> max moraletti
    width_to_max_moraletti = {
        large_width: max_moraletti_large,
        medium_width: max_moraletti_medium,
        small_width: max_moraletti_small
    }
    
    # Mappatura larghezza -> lettera (A, B, C)
    size_to_letter = config_data.get("size_to_letter", {})
    if not size_to_letter:
        size_to_letter = {
            str(large_width): 'A',
            str(medium_width): 'B',
            str(small_width): 'C'
        }
    
    # Funzione per calcolare moraletti per un blocco
    def calculate_moraletti_count(width: float) -> int:
        """Calcola numero moraletti per una larghezza blocco"""
        # Teorico: floor(width / spacing) + 1
        theoretical_count = math.floor(width / moraletti_spacing) + 1
        
        # Applica max per blocchi standard
        if width in width_to_max_moraletti:
            return min(theoretical_count, width_to_max_moraletti[width])
        
        # Per custom, cerca il range più vicino
        for std_width, max_count in width_to_max_moraletti.items():
            if abs(width - std_width) < 50:  # Tolleranza 50mm
                return min(theoretical_count, max_count)
        
        # Fallback: usa theoretical con limite massimo ragionevole
        return min(theoretical_count, 5)
    
    # Conta blocchi standard per tipo
    standard_counts = defaultdict(int)
    standard_moraletti = defaultdict(int)
    
    for block in placed:
        width = block.get('width', 0)
        standard_counts[width] += 1
        moraletti_count = calculate_moraletti_count(width)
        standard_moraletti[width] += moraletti_count
    
    # Conta blocchi custom per dimensione
    custom_counts = defaultdict(int)
    custom_moraletti = defaultdict(int)
    
    for block in customs:
        width = block.get('width', 0)
        height = block.get('height', moraletti_height)
        dim_key = f"{int(width)}×{int(height)}"
        custom_counts[dim_key] += 1
        moraletti_count = calculate_moraletti_count(width)
        custom_moraletti[dim_key] += moraletti_count
    
    # Calcola totale
    total_moraletti = sum(standard_moraletti.values()) + sum(custom_moraletti.values())
    
    # Crea dizionario dettagliato per tipo (per le tabelle frontend)
    moraletti_per_blocco = {}
    
    # Standard blocks: usa larghezza come chiave
    for width in standard_moraletti.keys():
        count = standard_counts[width]
        mor_per_block = standard_moraletti[width] // count if count > 0 else 0
        key = f"std_{int(width)}x{moraletti_height}"
        moraletti_per_blocco[key] = mor_per_block
        print(f"🔧 [DEBUG Backend] Standard: {key} = {mor_per_block} moraletti/blocco (tot: {standard_moraletti[width]}, count: {count})")
    
    # Custom blocks: usa dimensione completa come chiave
    for dim_key in custom_moraletti.keys():
        count = custom_counts[dim_key]
        mor_per_block = custom_moraletti[dim_key] // count if count > 0 else 0
        key = f"custom_{dim_key}"
        moraletti_per_blocco[key] = mor_per_block
        print(f"🔧 [DEBUG Backend] Custom: {key} = {mor_per_block} moraletti/blocco (tot: {custom_moraletti[dim_key]}, count: {count})")
    
    # SEMPLIFICATO: Solo dati totali per la card (il dettaglio per tipo sarà nelle tabelle blocchi)
    lines = []
    lines.append(f"<strong>Configurazione:</strong> {moraletti_thickness}mm × {moraletti_height}mm")
    lines.append(f"<strong>Piedini:</strong> {moraletti_height_from_ground}mm")
    lines.append(f"<strong>Totale Moraletti:</strong> {total_moraletti} pezzi")
    lines.append("<em style='color: #6b7280; font-size: 0.85rem;'>(Dettagli per blocco nelle tabelle sottostanti)</em>")
    
    # Converti in dizionario per compatibilità con _add_configuration_info_box
    return {
        '_raw_lines': lines,  # Usa chiave speciale per gestione custom
        'Configurazione': f"{moraletti_thickness}mm × {moraletti_height}mm",
        'Piedini': f"{moraletti_height_from_ground}mm",
        'Quantità Totale': f"{total_moraletti} pezzi",
        'moraletti_per_blocco': moraletti_per_blocco  # NUOVO: dati dettagliati per frontend
    }


def _add_configuration_info_box(ax, config_info: Dict, bounds):
    """
    Aggiunge una card integrata nel plot con le informazioni di configurazione.
    
    Args:
        ax: Asse matplotlib per il disegno
        config_info: Dizionario con le informazioni di configurazione
        bounds: Bounds del plot (minx, miny, maxx, maxy)
    """
    print(f"DEBUG: _add_configuration_info_box chiamata con config_info: {config_info}")
    
    if not config_info:
        print("DEBUG: Nessuna config_info fornita")
        return
    
    minx, miny, maxx, maxy = bounds
    
    # Crea le righe per la card
    card_lines = []
    
    # Titolo principale
    card_lines.append("CONFIGURAZIONE")
    card_lines.append("-" * 20)
    
    # Ogni sezione con le sue informazioni
    for section_name, section_data in config_info.items():
        if isinstance(section_data, dict) and section_data:
            # Nome sezione
            card_lines.append(f"{section_name.upper()}:")
            
            # Gestione speciale per Moraletti con formato custom
            if '_raw_lines' in section_data:
                # Usa le righe pre-formattate
                for line in section_data['_raw_lines']:
                    if line:  # Salta righe vuote iniziali
                        card_lines.append(f"  {line}")
            else:
                # Dati della sezione standard
                for key, value in section_data.items():
                    if value and value != 'Non specificato' and value != 'N/A':
                        card_lines.append(f"  {key}: {value}")
            
            # Spaziatura tra sezioni
            card_lines.append("")
    
    # Rimuove l'ultima riga vuota se presente
    if card_lines and card_lines[-1] == "":
        card_lines.pop()
    
    print(f"DEBUG: Card lines create: {card_lines}")
    
    # Crea la card solo se ci sono informazioni da mostrare
    if card_lines:
        # Posizionamento della card in basso a destra del plot
        card_width = (maxx - minx) * 0.35  # 35% della larghezza
        card_height = len(card_lines) * 50  # Altezza proporzionale al numero di righe
        
        card_x = maxx - card_width - ((maxx - minx) * 0.05)  # 5% di margine da destra
        card_y = miny + ((maxy - miny) * 0.05)  # 5% di margine dal basso
        
        # Disegna il rettangolo di sfondo della card
        card_rect = patches.Rectangle(
            (card_x, card_y),
            card_width,
            card_height,
            facecolor='white',
            edgecolor='#333333',
            linewidth=1.5,
            alpha=0.95,
            zorder=1000
        )
        ax.add_patch(card_rect)
        
        # Aggiungi il testo riga per riga
        line_height = card_height / len(card_lines)
        for i, line in enumerate(card_lines):
            text_y = card_y + card_height - (i + 0.5) * line_height
            
            # Stile diverso per il titolo
            if i == 0:  # Titolo principale
                fontweight = 'bold'
                fontsize = 12
            elif line.endswith(':'):  # Titoli delle sezioni
                fontweight = 'bold'
                fontsize = 10
            elif line.startswith('-'):  # Linea separatrice
                fontweight = 'normal'
                fontsize = 8
            else:  # Contenuto normale
                fontweight = 'normal'
                fontsize = 9
            
            ax.text(
                card_x + card_width / 2,  # Centrato orizzontalmente
                text_y,
                line,
                fontsize=fontsize,
                fontweight=fontweight,
                ha='center',
                va='center',
                color='#333333',
                zorder=1001,
                family='monospace'
            )
        
        print(f"DEBUG: Card integrata creata alle coordinate ({card_x}, {card_y})")
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

        # Calcola bounds originali e normalizza coordinate
        orig_minx, orig_miny, orig_maxx, orig_maxy = wall_polygon.bounds
        
        # Trasla tutto all'origine per coordinate più gestibili
        from shapely.affinity import translate
        
        # Normalizza la parete
        wall_normalized = translate(wall_polygon, -orig_minx, -orig_miny)
        
        # Normalizza aperture se presenti
        apertures_normalized = []
        if apertures:
            for aperture in apertures:
                apertures_normalized.append(translate(aperture, -orig_minx, -orig_miny))
        
        # Normalizza blocchi posizionati
        placed_normalized = []
        for blk in placed:
            placed_normalized.append({
                **blk,
                'x': blk['x'] - orig_minx,
                'y': blk['y'] - orig_miny
            })
            
        # Normalizza pezzi custom
        customs_normalized = []
        for custom in customs:
            customs_normalized.append({
                **custom,
                'x': custom['x'] - orig_minx,
                'y': custom['y'] - orig_miny
            })

        # Calcola bounds normalizzati e margini (salvali per dopo)
        norm_minx, norm_miny, norm_maxx, norm_maxy = wall_normalized.bounds
        # RIDUCO DRASTICAMENTE I MARGINI - da 5% a 1%
        margin = max((norm_maxx - norm_minx), (norm_maxy - norm_miny)) * 0.01
        # NON impostiamo i limiti ancora - li impostiamo alla fine dopo aver disegnato tutto

        # Disegna il contorno della parete normalizzato
        x, y = wall_normalized.exterior.xy
        ax.plot(x, y, color=wall_color, linewidth=wall_line_width, label="Parete")

        # Crea labels dettagliate per i blocchi (usando quelli originali per le labels)
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

        # Disegna blocchi standard (con coordinate normalizzate)
        for i, blk in enumerate(placed_normalized):
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

        # Disegna pezzi custom (con coordinate normalizzate)
        for i, cust in enumerate(customs_normalized):
            try:
                # Usa la geometria originale ma trasla le coordinate per le etichette
                orig_cust = customs[i]
                poly = shape(orig_cust["geometry"])
                # Trasla la geometria
                poly_normalized = translate(poly, -orig_minx, -orig_miny)
            except Exception:
                continue

            patch = patches.Polygon(
                list(poly_normalized.exterior.coords),
                facecolor=custom_piece_color,
                edgecolor=custom_piece_border,
                linewidth=0.8,
                hatch="//",
                alpha=0.8,
            )
            ax.add_patch(patch)

            # Aggiungi etichette ai pezzi custom (con coordinate normalizzate)
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

        # Disegna aperture (porte/finestre) - con coordinate normalizzate
        if apertures_normalized:
            for ap in apertures_normalized:
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
            
            # Add directional arrows for starting position (usa coordinate normalizzate)
            if starting_pos:
                norm_minx, norm_miny, norm_maxx, norm_maxy = wall_normalized.bounds
                arrow_props = dict(arrowstyle='->', lw=2, color='#dc2626')
                
                if starting_pos.lower() == "left":
                    # Arrow pointing to bottom-left (start laying from left side of bottom row)
                    ax.annotate("INIZIO", xy=(norm_minx, norm_miny), 
                               xytext=(norm_minx - (norm_maxx - norm_minx) * 0.1, norm_miny - (norm_maxy - norm_miny) * 0.15),
                               fontsize=10, fontweight='bold', color='#dc2626',
                               ha='center', va='center',
                               arrowprops=arrow_props)
                elif starting_pos.lower() == "right":
                    # Arrow pointing to bottom-right (start laying from right side of bottom row)
                    ax.annotate("INIZIO", xy=(norm_maxx, norm_miny),
                               xytext=(norm_maxx + (norm_maxx - norm_minx) * 0.1, norm_miny - (norm_maxy - norm_miny) * 0.15),
                               fontsize=10, fontweight='bold', color='#dc2626', 
                               ha='center', va='center',
                               arrowprops=arrow_props)
                elif starting_pos.lower() == "bottom":
                    # Arrow pointing to bottom-center (start laying from center of bottom row)
                    ax.annotate("INIZIO", xy=((norm_minx + norm_maxx) / 2, norm_miny),
                               xytext=((norm_minx + norm_maxx) / 2, norm_miny - (norm_maxy - norm_miny) * 0.15),
                               fontsize=10, fontweight='bold', color='#dc2626',
                               ha='center', va='center',
                               arrowprops=arrow_props)
        else:
            # Standard title
            ax.set_title("Preview Costruzione Parete", fontsize=12, fontweight="bold", color="#1f2937")
        
        ax.grid(True, alpha=0.3, color="#9ca3af")
        ax.tick_params(axis="both", which="major", labelsize=8, colors="#6b7280")
        
        # IMPORTANTE: Impostiamo i limiti degli assi ALLA FINE per evitare che le frecce espandano l'area
        # Questo mantiene il focus sulla parete e evita spazi bianchi indesiderati
        # USA SOLO I BOUNDS DELLA PARETE NORMALIZZATA - ignora tutto il resto
        final_minx, final_miny, final_maxx, final_maxy = wall_normalized.bounds
        tiny_margin = max((final_maxx - final_minx), (final_maxy - final_miny)) * 0.01
        ax.set_xlim(final_minx - tiny_margin, final_maxx + tiny_margin)
        ax.set_ylim(final_miny - tiny_margin, final_maxy + tiny_margin)

        # Add comprehensive configuration info box if enhanced
        if enhanced_info and enhanced_info.get("enhanced", False):
            # Gather all configuration information
            # Estrai informazioni di configurazione (per uso futuro)
            config_info = _extract_configuration_info(enhanced_info, placed, customs)

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
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

        # Configurazione grafico
        ax.set_title("Preview Costruzione Parete", fontsize=12, fontweight="bold", color="#1f2937")
        ax.grid(True, alpha=0.3, color="#9ca3af")
        ax.tick_params(axis="both", which="major", labelsize=8, colors="#6b7280")

        # Genera immagine PNG
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
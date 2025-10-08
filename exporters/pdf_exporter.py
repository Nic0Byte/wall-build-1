"""Exporter per report PDF della parete."""

from __future__ import annotations

import datetime
import io
from typing import Dict, List, Optional

from shapely.geometry import Polygon, shape

from exporters.labels import create_detailed_block_labels
from utils.file_manager import get_organized_output_path
from block_grouping import (
    create_grouped_block_labels,
    group_blocks_by_category,
    group_custom_blocks_by_category,
)

try:  # ReportLab
    from reportlab.lib import colors
    from reportlab.lib.colors import black, gray, white, HexColor
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.lib.pagesizes import A4, A3, landscape
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        Image,
        PageBreak,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
        PageTemplate,
        Frame,
        KeepTogether,
    )
    from reportlab.pdfgen import canvas

    REPORTLAB_AVAILABLE = True
except ImportError:  # pragma: no cover
    REPORTLAB_AVAILABLE = False

try:  # Matplotlib for schema rendering
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches

    MATPLOTLIB_AVAILABLE = True
except Exception:  # pragma: no cover
    plt = None  # type: ignore
    patches = None  # type: ignore
    MATPLOTLIB_AVAILABLE = False


__all__ = ["export_to_pdf", "export_to_pdf_professional", "export_to_pdf_professional_multipage", "REPORTLAB_AVAILABLE"]

# Colori Corporate TAKTAK®
BRAND_BLUE = HexColor("#1B3B6F") if REPORTLAB_AVAILABLE else None
BRAND_GRAY = HexColor("#E5E5E5") if REPORTLAB_AVAILABLE else None
BRAND_GREEN = HexColor("#C6F3C0") if REPORTLAB_AVAILABLE else None
BRAND_ACCENT = HexColor("#FF6B35") if REPORTLAB_AVAILABLE else None


def export_to_pdf(
    summary: Dict[str, int],
    customs: List[Dict],
    placed: List[Dict],
    wall_polygon: Polygon,
    apertures: Optional[List[Polygon]] = None,
    project_name: str = "Progetto Parete",
    out_path: str = "report_parete.pdf",
    params: Optional[Dict] = None,
    block_config: Optional[Dict] = None,
) -> str:
    """Genera un report PDF completo con schema parete e tabelle."""
    if not REPORTLAB_AVAILABLE:
        raise RuntimeError("reportlab non disponibile. Installa con: pip install reportlab")

    organized_path = get_organized_output_path(out_path, "pdf")

    doc = SimpleDocTemplate(
        organized_path,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=25 * mm,
        bottomMargin=25 * mm,
    )

    styles = getSampleStyleSheet()
    story: List = []

    # Header e schema
    story.extend(_build_pdf_header(project_name, summary, customs, styles))
    story.append(Spacer(1, 10 * mm))

    schema_image = _generate_wall_schema_image(wall_polygon, placed, customs, apertures, block_config)
    if schema_image:
        story.append(schema_image)
        story.append(Spacer(1, 10 * mm))

    # Tabelle standard/custom
    if summary:
        story.append(_build_standard_blocks_table(summary, placed, styles, block_config))
        story.append(Spacer(1, 8 * mm))

    if customs:
        story.append(PageBreak())
        story.append(_build_custom_blocks_table(customs, styles))
        story.append(Spacer(1, 8 * mm))

    if params:
        story.append(_build_technical_info(params, styles))

    doc.build(story)
    print(f"[PDF] Report generato: {organized_path}")
    return organized_path


def _build_pdf_header(project_name: str, summary: Dict[str, int], customs: List[Dict], styles) -> List:
    elements: List = []

    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Title"],
        fontSize=18,
        spaceAfter=6 * mm,
        alignment=TA_CENTER,
        textColor=black,
    )
    elements.append(Paragraph(f"<b>{project_name}</b>", title_style))

    subtitle_style = ParagraphStyle(
        "Subtitle",
        parent=styles["Normal"],
        fontSize=12,
        alignment=TA_CENTER,
        textColor=gray,
        spaceAfter=8 * mm,
    )
    now = datetime.datetime.now()
    elements.append(
        Paragraph(
            f"Distinta Base Blocchi - {now.strftime('%d/%m/%Y %H:%M')}",
            subtitle_style,
        )
    )

    total_standard = sum(summary.values())
    total_custom = len(customs)

    summary_data = [
        ["RIEPILOGO PROGETTO", ""],
        ["Blocchi Standard Totali:", f"{total_standard}"],
        ["Pezzi Custom Totali:", f"{total_custom}"],
        [
            "Efficienza:",
            (
                f"{total_standard / (total_standard + total_custom) * 100:.1f}%"
                if total_standard + total_custom > 0
                else "N/A"
            ),
        ],
    ]

    summary_table = Table(summary_data, colWidths=[80 * mm, 40 * mm])
    summary_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("TEXTCOLOR", (0, 0), (-1, 0), black),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("GRID", (0, 0), (-1, -1), 1, black),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )

    elements.append(summary_table)
    return elements


def _generate_wall_schema_image(
    wall_polygon: Polygon,
    placed: List[Dict],
    customs: List[Dict],
    apertures: Optional[List[Polygon]] = None,
    block_config: Optional[Dict] = None,
):
    if not MATPLOTLIB_AVAILABLE:
        return None

    try:
        fig, ax = plt.subplots(figsize=(180 / 25.4, 120 / 25.4), dpi=200)
        ax.set_aspect("equal")

        minx, miny, maxx, maxy = wall_polygon.bounds
        margin = max((maxx - minx), (maxy - miny)) * 0.05
        ax.set_xlim(minx - margin, maxx + margin)
        ax.set_ylim(miny - margin, maxy + margin)

        x, y = wall_polygon.exterior.xy
        ax.plot(x, y, color="blue", linewidth=2, label="Contorno parete")

        if block_config and block_config.get("size_to_letter"):
            detailed_std, detailed_custom = create_detailed_block_labels(
                placed,
                customs,
                block_config.get("size_to_letter"),
            )
        else:
            detailed_std, detailed_custom = create_detailed_block_labels(placed, customs)

        for i, blk in enumerate(placed):
            rect = patches.Rectangle(
                (blk["x"], blk["y"]),
                blk["width"],
                blk["height"],
                facecolor="lightgray",
                edgecolor="black",
                linewidth=0.5,
            )
            ax.add_patch(rect)

            label_info = detailed_std.get(i)
            if not label_info:
                continue

            margin_px = 3
            category = label_info["display"]["bottom_left"]
            number = label_info["display"]["top_right"]

            fontsize_letter = min(10, max(6, blk["width"] / 150))
            ax.text(
                blk["x"] + margin_px,
                blk["y"] + margin_px,
                category,
                ha="left",
                va="bottom",
                fontsize=fontsize_letter,
                fontweight="bold",
                color="black",
                bbox=dict(boxstyle="round,pad=0.1", facecolor="white", alpha=0.9),
            )

            fontsize_number = min(8, max(5, blk["width"] / 200))
            ax.text(
                blk["x"] + blk["width"] - margin_px,
                blk["y"] + blk["height"] - margin_px,
                str(number),
                ha="right",
                va="top",
                fontsize=fontsize_number,
                fontweight="bold",
                color="red",
                bbox=dict(boxstyle="round,pad=0.1", facecolor="white", alpha=0.9),
            )

        for i, cust in enumerate(customs):
            try:
                poly = shape(cust["geometry"])
            except Exception:
                continue

            patch = patches.Polygon(
                list(poly.exterior.coords),
                facecolor="lightgreen",
                edgecolor="green",
                linewidth=0.8,
                hatch="//",
                alpha=0.7,
            )
            ax.add_patch(patch)

            label_info = detailed_custom.get(i)
            if not label_info:
                continue

            margin_px = 3
            category = label_info["display"]["bottom_left"]
            number = label_info["display"]["top_right"]

            fontsize_letter = min(8, max(5, cust["width"] / 150))
            ax.text(
                cust["x"] + margin_px,
                cust["y"] + margin_px,
                category,
                ha="left",
                va="bottom",
                fontsize=fontsize_letter,
                fontweight="bold",
                color="darkgreen",
                bbox=dict(boxstyle="round,pad=0.1", facecolor="white", alpha=0.9),
            )

            fontsize_number = min(6, max(4, cust["width"] / 200))
            ax.text(
                cust["x"] + cust["width"] - margin_px,
                cust["y"] + cust["height"] - margin_px,
                str(number),
                ha="right",
                va="top",
                fontsize=fontsize_number,
                fontweight="bold",
                color="red",
                bbox=dict(boxstyle="round,pad=0.1", facecolor="white", alpha=0.9),
            )

        if apertures:
            for ap in apertures:
                x, y = ap.exterior.xy
                ax.plot(x, y, color="red", linestyle="--", linewidth=2)
                ax.fill(x, y, color="red", alpha=0.15)

        ax.set_title("Schema Costruttivo Parete", fontsize=12, fontweight="bold", pad=10)
        ax.legend(loc="upper right", fontsize=8)
        ax.grid(True, alpha=0.3)
        ax.set_xlabel("mm", fontsize=8)
        ax.set_ylabel("mm", fontsize=8)

        img_buffer = io.BytesIO()
        fig.savefig(
            img_buffer,
            format="png",
            dpi=200,
            bbox_inches="tight",
            facecolor="white",
            edgecolor="none",
        )
        img_buffer.seek(0)
        plt.close(fig)

        return Image(img_buffer, width=170 * mm, height=110 * mm)
    except Exception as exc:  # pragma: no cover - solo logging
        print(f"[WARN] Errore generazione schema PDF: {exc}")
        return None


def _build_standard_blocks_table(
    summary: Dict[str, int],
    placed: List[Dict],
    styles,
    block_config: Optional[Dict] = None,
) -> Table:
    data = [["CATEGORIA", "QUANTITA'", "DIMENSIONI (mm)", "AREA TOT (m^2)"]]

    if block_config and block_config.get("size_to_letter"):
        grouped_blocks = group_blocks_by_category(placed, block_config.get("size_to_letter"))
    else:
        grouped_blocks = group_blocks_by_category(placed)

    total_area = 0.0
    total_count = 0

    for category in sorted(grouped_blocks.keys()):
        blocks_in_category = grouped_blocks[category]
        count = len(blocks_in_category)
        first_block = blocks_in_category[0]
        width = first_block["width"]
        height = first_block["height"]

        area_m2 = (width * height * count) / 1_000_000
        total_area += area_m2
        total_count += count

        data.append(
            [
                f"Categoria {category}",
                str(count),
                f"{width} x {height}",
                f"{area_m2:.2f}",
            ]
        )

    data.append(["TOTALE", str(total_count), "", f"{total_area:.2f}"])

    table = Table(data, colWidths=[60 * mm, 25 * mm, 40 * mm, 25 * mm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.darkblue),
                ("TEXTCOLOR", (0, 0), (-1, 0), white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 10),
                ("FONTNAME", (0, 1), (-1, -2), "Helvetica"),
                ("FONTSIZE", (0, 1), (-1, -2), 9),
                ("ALIGN", (1, 1), (-1, -1), "CENTER"),
                ("BACKGROUND", (0, -1), (-1, -1), colors.lightblue),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 1, black),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    return table


def _build_custom_blocks_table(customs: List[Dict], styles) -> Table:
    data = [["CATEGORIA CUSTOM", "QUANTITA'", "DIMENSIONI (mm)", "AREA TOT (m^2)"]]

    grouped_customs = group_custom_blocks_by_category(customs)

    total_area = 0.0
    total_count = 0

    for category in sorted(grouped_customs.keys()):
        blocks_in_category = grouped_customs[category]
        count = len(blocks_in_category)
        first_block = blocks_in_category[0]
        width = first_block["width"]
        height = first_block["height"]
        area_m2 = (width * height * count) / 1_000_000
        total_area += area_m2
        total_count += count

        ctype = first_block.get("ctype", 2)
        type_str = f"CU{ctype}" if ctype in [1, 2] else "CUX"

        data.append(
            [
                f"Categoria {category} ({type_str})",
                str(count),
                f"{width:.0f} x {height:.0f}",
                f"{area_m2:.3f}",
            ]
        )

    data.append(["TOTALE", str(total_count), "", f"{total_area:.3f}"])

    table = Table(data, colWidths=[35 * mm, 20 * mm, 35 * mm, 35 * mm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.darkgreen),
                ("TEXTCOLOR", (0, 0), (-1, 0), white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 10),
                ("FONTNAME", (0, 1), (-1, -2), "Helvetica"),
                ("FONTSIZE", (0, 1), (-1, -2), 8),
                ("ALIGN", (1, 1), (-1, -1), "CENTER"),
                ("BACKGROUND", (0, -1), (-1, -1), colors.lightgreen),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 1, black),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    return table


def _build_technical_info(params: Dict, styles) -> Table:
    data = [["PARAMETRI TECNICI", "VALORE"]]

    readable_params = [
        ("Algoritmo Packing", "Greedy + Backtrack"),
        ("Altezza Blocco Standard", f"{params.get('block_height_mm', 495)} mm"),
        ("Larghezze Blocchi", f"{params.get('block_widths_mm', [])}"),
        ("Offset Righe Dispari", f"{params.get('row_offset_mm', 'Auto')} mm"),
        ("Griglia Snap", f"{params.get('snap_mm', 1)} mm"),
        ("Margine Aperture", f"{params.get('keep_out_mm', 2)} mm"),
        ("Merge Custom Row-Aware", f"{params.get('row_aware_merge', True)}"),
        ("Max Larghezza Custom", f"{params.get('split_max_width_mm', 413)} mm"),
    ]

    for label, value in readable_params:
        data.append([label, str(value)])

    table = Table(data, colWidths=[80 * mm, 60 * mm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.orange),
                ("TEXTCOLOR", (0, 0), (-1, 0), black),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 10),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 1), (-1, -1), 8),
                ("ALIGN", (1, 1), (-1, -1), "LEFT"),
                ("GRID", (0, 0), (-1, -1), 1, black),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    return table


# ============================================================================
# EXPORT PROFESSIONALE A4 ORIZZONTALE - DISTINTA BASE TAKTAK®
# ============================================================================


def export_to_pdf_professional(
    summary: Dict[str, int],
    customs: List[Dict],
    placed: List[Dict],
    wall_polygon: Polygon,
    apertures: Optional[List[Polygon]] = None,
    project_name: str = "Progetto Parete",
    out_path: str = "distinta_base_professionale.pdf",
    params: Optional[Dict] = None,
    block_config: Optional[Dict] = None,
    author: str = "N. Bovo",
    revision: str = "Rev 1.0",
) -> str:
    """
    Genera DISTINTA BASE PROFESSIONALE in formato A4 ORIZZONTALE (297×210 mm).
    
    Layout ottimizzato per stampa standard con:
    - Header: Logo TAKTAK® + Titolo + Data/Revisione
    - Colonna Sinistra (50%): Schema costruttivo parete
    - Colonna Destra (50%): Tabelle blocchi + Riepilogo + Grafico torta
    - Footer: Tracciabilità file e sistema
    
    Args:
        summary: Riassunto blocchi standard
        customs: Lista pezzi custom
        placed: Blocchi posizionati
        wall_polygon: Geometria parete
        apertures: Aperture opzionali
        project_name: Nome progetto
        out_path: Path output
        params: Parametri tecnici
        block_config: Configurazione blocchi
        author: Nome autore/redattore
        revision: Versione documento
        
    Returns:
        Path del PDF generato
    """
    if not REPORTLAB_AVAILABLE:
        raise RuntimeError("reportlab non disponibile. Installa con: pip install reportlab")

    organized_path = get_organized_output_path(out_path, "pdf")
    
    # A4 ORIZZONTALE (landscape)
    page_width, page_height = landscape(A4)
    
    # Setup documento con callback footer
    doc = SimpleDocTemplate(
        organized_path,
        pagesize=landscape(A4),
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=20 * mm,
    )
    
    # Story elements
    story: List = []
    styles = getSampleStyleSheet()
    
    # === HEADER PROFESSIONALE ===
    story.extend(_build_professional_header(
        project_name, 
        wall_polygon, 
        summary, 
        customs, 
        author, 
        revision, 
        styles
    ))
    story.append(Spacer(1, 5 * mm))
    
    # === LAYOUT 2 COLONNE ===
    # Tabella contenitore 2 colonne: Schema (sx) + Dati (dx)
    
    # COLONNA SINISTRA: Schema costruttivo grande
    schema_img = _generate_professional_wall_schema(
        wall_polygon, 
        placed, 
        customs, 
        apertures, 
        block_config,
        width_mm=130,
        height_mm=140
    )
    
    # COLONNA DESTRA: Riepilogo + Grafico + Tabelle
    right_column_elements = []
    
    # Riepilogo progetto compatto
    right_column_elements.append(_build_compact_summary(summary, customs, wall_polygon, styles))
    right_column_elements.append(Spacer(1, 3 * mm))
    
    # Grafico torta efficienza
    pie_chart = _generate_efficiency_pie_chart(summary, customs)
    if pie_chart:
        right_column_elements.append(pie_chart)
        right_column_elements.append(Spacer(1, 3 * mm))
    
    # Tabelle blocchi raggruppati
    if summary:
        right_column_elements.append(_build_compact_standard_table(summary, placed, styles, block_config))
        right_column_elements.append(Spacer(1, 2 * mm))
    
    if customs:
        right_column_elements.append(_build_compact_custom_table(customs, styles))
        right_column_elements.append(Spacer(1, 2 * mm))
    
    # Parametri tecnici compatti
    if params:
        right_column_elements.append(_build_compact_technical_params(params, styles))
    
    # Combina colonne in tabella layout
    if schema_img:
        layout_table = Table(
            [[schema_img, right_column_elements]],
            colWidths=[135 * mm, 132 * mm]
        )
        layout_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ]))
        story.append(layout_table)
    else:
        # Fallback: solo colonna destra
        for elem in right_column_elements:
            story.append(elem)
    
    # Build con footer callback
    doc.build(
        story,
        onFirstPage=lambda canvas, doc: _draw_professional_footer(
            canvas, doc, project_name, out_path
        ),
        onLaterPages=lambda canvas, doc: _draw_professional_footer(
            canvas, doc, project_name, out_path
        ),
    )
    
    print(f"✅ [PDF] Distinta Base Professionale generata: {organized_path}")
    return organized_path


def _build_professional_header(
    project_name: str,
    wall_polygon: Polygon,
    summary: Dict[str, int],
    customs: List[Dict],
    author: str,
    revision: str,
    styles,
) -> List:
    """Crea header professionale con logo TAKTAK®, titolo, e metadata."""
    elements: List = []
    
    # Calcola dimensioni parete dinamiche
    minx, miny, maxx, maxy = wall_polygon.bounds
    wall_width_m = (maxx - minx) / 1000
    wall_height_m = (maxy - miny) / 1000
    
    # Header table: Logo | Titolo | Metadata
    now = datetime.datetime.now()
    
    # Logo TAKTAK® stilizzato (testo se immagine non disponibile)
    logo_style = ParagraphStyle(
        "Logo",
        parent=styles["Normal"],
        fontSize=16,
        textColor=BRAND_BLUE,
        fontName="Helvetica-Bold",
        alignment=TA_LEFT,
    )
    logo_para = Paragraph("<b>TAKTAK<sup>®</sup></b>", logo_style)
    
    # Titolo centrale
    title_style = ParagraphStyle(
        "TitlePro",
        parent=styles["Title"],
        fontSize=14,
        textColor=BRAND_BLUE,
        fontName="Helvetica-Bold",
        alignment=TA_CENTER,
    )
    title_text = f"<b>DISTINTA BASE BLOCCHI<br/>Parete {wall_width_m:.1f}m × {wall_height_m:.1f}m</b>"
    title_para = Paragraph(title_text, title_style)
    
    # Metadata destra
    meta_style = ParagraphStyle(
        "Meta",
        parent=styles["Normal"],
        fontSize=8,
        textColor=black,
        alignment=TA_RIGHT,
    )
    meta_text = f"""
    Data: {now.strftime('%d/%m/%Y %H:%M')}<br/>
    {revision}<br/>
    Redatto da: {author}
    """
    meta_para = Paragraph(meta_text, meta_style)
    
    # Tabella header
    header_table = Table(
        [[logo_para, title_para, meta_para]],
        colWidths=[60 * mm, 147 * mm, 60 * mm]
    )
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
    ]))
    
    elements.append(header_table)
    
    # Linea separatore blu
    separator_table = Table([[""]], colWidths=[267 * mm])
    separator_table.setStyle(TableStyle([
        ('LINEABOVE', (0, 0), (-1, 0), 2, BRAND_BLUE),
    ]))
    elements.append(separator_table)
    
    return elements


def _generate_professional_wall_schema(
    wall_polygon: Polygon,
    placed: List[Dict],
    customs: List[Dict],
    apertures: Optional[List[Polygon]],
    block_config: Optional[Dict],
    width_mm: int = 130,
    height_mm: int = 140,
):
    """Genera schema costruttivo parete ad alta qualità per layout professionale."""
    if not MATPLOTLIB_AVAILABLE:
        return None
    
    try:
        # DPI alto per stampa professionale
        fig, ax = plt.subplots(figsize=(width_mm / 25.4, height_mm / 25.4), dpi=300)
        ax.set_aspect("equal")
        
        minx, miny, maxx, maxy = wall_polygon.bounds
        margin = max((maxx - minx), (maxy - miny)) * 0.03
        ax.set_xlim(minx - margin, maxx + margin)
        ax.set_ylim(miny - margin, maxy + margin)
        
        # Contorno parete (blu TAKTAK®)
        x, y = wall_polygon.exterior.xy
        ax.plot(x, y, color='#1B3B6F', linewidth=2.5, label="Parete")
        
        # Etichette blocchi
        if block_config and block_config.get("size_to_letter"):
            detailed_std, detailed_custom = create_detailed_block_labels(
                placed, customs, block_config.get("size_to_letter")
            )
        else:
            detailed_std, detailed_custom = create_detailed_block_labels(placed, customs)
        
        # Blocchi standard (grigio)
        for i, blk in enumerate(placed):
            rect = patches.Rectangle(
                (blk["x"], blk["y"]),
                blk["width"],
                blk["height"],
                facecolor="#E5E5E5",
                edgecolor="black",
                linewidth=0.4,
            )
            ax.add_patch(rect)
            
            # Etichetta numerazione operatori
            label_info = detailed_std.get(i)
            if label_info:
                category = label_info["display"]["bottom_left"]
                number = label_info["display"]["top_right"]
                full_label = f"{category}{number}"
                
                # Posizione alto-destra per operatori cantiere
                fontsize = min(7, max(4, blk["width"] / 200))
                ax.text(
                    blk["x"] + blk["width"] - 5,
                    blk["y"] + blk["height"] - 5,
                    full_label,
                    ha="right",
                    va="top",
                    fontsize=fontsize,
                    fontweight="bold",
                    color="red",
                    bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.95, edgecolor="red", linewidth=0.5),
                )
        
        # Pezzi custom (verde con hatch)
        for i, cust in enumerate(customs):
            try:
                poly = shape(cust["geometry"])
                patch = patches.Polygon(
                    list(poly.exterior.coords),
                    facecolor="#90EE90",
                    edgecolor="#228B22",
                    linewidth=0.6,
                    hatch="//",
                    alpha=0.6,
                )
                ax.add_patch(patch)
                
                # Etichetta custom
                label_info = detailed_custom.get(i)
                if label_info:
                    category = label_info["display"]["bottom_left"]
                    number = label_info["display"]["top_right"]
                    full_label = f"{category}{number}"
                    
                    fontsize = min(6, max(4, cust["width"] / 200))
                    ax.text(
                        cust["x"] + cust["width"] - 5,
                        cust["y"] + cust["height"] - 5,
                        full_label,
                        ha="right",
                        va="top",
                        fontsize=fontsize,
                        fontweight="bold",
                        color="#228B22",
                        bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.95, edgecolor="#228B22", linewidth=0.5),
                    )
            except Exception:
                continue
        
        # Aperture (rosso tratteggiato)
        if apertures:
            for ap in apertures:
                x, y = ap.exterior.xy
                ax.plot(x, y, color="red", linestyle="--", linewidth=1.5)
                ax.fill(x, y, color="red", alpha=0.1)
        
        # Titolo e assi
        ax.set_title("Schema Costruttivo Parete - Vista Frontale", fontsize=10, fontweight="bold", pad=8, color='#1B3B6F')
        ax.grid(True, alpha=0.2, linestyle=":", linewidth=0.5)
        ax.set_xlabel("mm", fontsize=7)
        ax.set_ylabel("mm", fontsize=7)
        ax.tick_params(labelsize=6)
        
        # Legenda compatta
        ax.legend(loc="upper right", fontsize=6, framealpha=0.9)
        
        # Salva in buffer
        img_buffer = io.BytesIO()
        fig.savefig(
            img_buffer,
            format="png",
            dpi=300,
            bbox_inches="tight",
            facecolor="white",
            edgecolor="none",
        )
        img_buffer.seek(0)
        plt.close(fig)
        
        return Image(img_buffer, width=width_mm * mm, height=height_mm * mm)
        
    except Exception as exc:
        print(f"⚠️ [WARN] Errore schema professionale: {exc}")
        return None


def _build_compact_summary(summary: Dict[str, int], customs: List[Dict], wall_polygon: Polygon, styles) -> Table:
    """Tabella riepilogo compatta per layout professionale."""
    total_standard = sum(summary.values())
    total_custom = len(customs)
    total_blocks = total_standard + total_custom
    efficiency = (total_standard / total_blocks * 100) if total_blocks > 0 else 0
    
    # Calcola area parete
    area_parete_m2 = wall_polygon.area / 1_000_000
    
    data = [
        ["RIEPILOGO PROGETTO", ""],
        ["Blocchi Standard:", f"{total_standard}"],
        ["Blocchi Custom:", f"{total_custom}"],
        ["Efficienza:", f"{efficiency:.1f}%"],
        ["Area Parete:", f"{area_parete_m2:.2f} m²"],
    ]
    
    table = Table(data, colWidths=[50 * mm, 30 * mm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), BRAND_BLUE),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), "Helvetica-Bold"),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('FONTSIZE', (0, 1), (-1, -1), 7),
        ('ALIGN', (0, 0), (-1, -1), "LEFT"),
        ('GRID', (0, 0), (-1, -1), 0.5, black),
        ('VALIGN', (0, 0), (-1, -1), "MIDDLE"),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    
    return table


def _generate_efficiency_pie_chart(summary: Dict[str, int], customs: List[Dict]):
    """Genera grafico torta Standard vs Custom."""
    if not MATPLOTLIB_AVAILABLE:
        return None
    
    try:
        total_standard = sum(summary.values())
        total_custom = len(customs)
        
        if total_standard + total_custom == 0:
            return None
        
        fig, ax = plt.subplots(figsize=(50 / 25.4, 50 / 25.4), dpi=200)
        
        sizes = [total_standard, total_custom]
        labels = [f'Standard\n{total_standard}', f'Custom\n{total_custom}']
        colors_pie = ['#4A90E2', '#50C878']
        explode = (0.05, 0)
        
        ax.pie(
            sizes,
            explode=explode,
            labels=labels,
            autopct='%1.0f%%',
            colors=colors_pie,
            startangle=90,
            textprops={'fontsize': 8, 'fontweight': 'bold'}
        )
        
        ax.set_title("Standard vs Custom", fontsize=9, fontweight="bold", pad=5)
        
        img_buffer = io.BytesIO()
        fig.savefig(img_buffer, format="png", dpi=200, bbox_inches="tight", facecolor="white")
        img_buffer.seek(0)
        plt.close(fig)
        
        return Image(img_buffer, width=50 * mm, height=50 * mm)
        
    except Exception as exc:
        print(f"⚠️ [WARN] Errore grafico torta: {exc}")
        return None


def _build_compact_standard_table(summary: Dict[str, int], placed: List[Dict], styles, block_config: Optional[Dict]) -> Table:
    """Tabella blocchi standard compatta."""
    data = [["BLOCCHI STANDARD", "Q.tà", "Dimensioni"]]
    
    if block_config and block_config.get("size_to_letter"):
        grouped = group_blocks_by_category(placed, block_config.get("size_to_letter"))
    else:
        grouped = group_blocks_by_category(placed)
    
    for category in sorted(grouped.keys()):
        blocks = grouped[category]
        count = len(blocks)
        first = blocks[0]
        dims = f"{first['width']}×{first['height']}"
        data.append([f"Cat. {category}", str(count), dims])
    
    table = Table(data, colWidths=[40 * mm, 20 * mm, 30 * mm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), BRAND_BLUE),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), "Helvetica-Bold"),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('FONTSIZE', (0, 1), (-1, -1), 7),
        ('ALIGN', (1, 0), (-1, -1), "CENTER"),
        ('GRID', (0, 0), (-1, -1), 0.5, black),
        ('VALIGN', (0, 0), (-1, -1), "MIDDLE"),
        ('LEFTPADDING', (0, 0), (-1, -1), 2),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2),
        ('TOPPADDING', (0, 0), (-1, -1), 1),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
    ]))
    
    return table


def _build_compact_custom_table(customs: List[Dict], styles) -> Table:
    """Tabella pezzi custom compatta."""
    data = [["PEZZI CUSTOM", "Q.tà", "Dimensioni"]]
    
    grouped = group_custom_blocks_by_category(customs)
    
    for category in sorted(grouped.keys()):
        blocks = grouped[category]
        count = len(blocks)
        first = blocks[0]
        dims = f"{first['width']:.0f}×{first['height']:.0f}"
        data.append([f"Cat. {category}", str(count), dims])
    
    table = Table(data, colWidths=[40 * mm, 20 * mm, 30 * mm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkgreen),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), "Helvetica-Bold"),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('FONTSIZE', (0, 1), (-1, -1), 7),
        ('ALIGN', (1, 0), (-1, -1), "CENTER"),
        ('GRID', (0, 0), (-1, -1), 0.5, black),
        ('VALIGN', (0, 0), (-1, -1), "MIDDLE"),
        ('LEFTPADDING', (0, 0), (-1, -1), 2),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2),
        ('TOPPADDING', (0, 0), (-1, -1), 1),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
    ]))
    
    return table


def _build_compact_technical_params(params: Dict, styles) -> Table:
    """Parametri tecnici compatti."""
    data = [["PARAMETRI TECNICI", "VALORE"]]
    
    compact_params = [
        ("Algoritmo", "Greedy + Backtrack"),
        ("Alt. Blocco", f"{params.get('block_height_mm', 495)} mm"),
        ("Offset Righe", f"{params.get('row_offset_mm', 'Auto')} mm"),
        ("Snap Grid", f"{params.get('snap_mm', 1)} mm"),
    ]
    
    for label, value in compact_params:
        data.append([label, str(value)])
    
    table = Table(data, colWidths=[40 * mm, 40 * mm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.orange),
        ('TEXTCOLOR', (0, 0), (-1, 0), black),
        ('FONTNAME', (0, 0), (-1, 0), "Helvetica-Bold"),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('FONTSIZE', (0, 1), (-1, -1), 6),
        ('ALIGN', (0, 0), (-1, -1), "LEFT"),
        ('GRID', (0, 0), (-1, -1), 0.5, black),
        ('VALIGN', (0, 0), (-1, -1), "MIDDLE"),
        ('LEFTPADDING', (0, 0), (-1, -1), 2),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2),
        ('TOPPADDING', (0, 0), (-1, -1), 1),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
    ]))
    
    return table


def _draw_professional_footer(canvas_obj, doc, project_name: str, filename: str):
    """Disegna footer professionale con linea blu e tracciabilità."""
    canvas_obj.saveState()
    
    page_width, page_height = landscape(A4)
    
    # Linea blu separatore
    canvas_obj.setStrokeColor(BRAND_BLUE)
    canvas_obj.setLineWidth(1.5)
    canvas_obj.line(15 * mm, 15 * mm, page_width - 15 * mm, 15 * mm)
    
    # Testo footer
    canvas_obj.setFont('Helvetica', 7)
    canvas_obj.setFillColor(colors.grey)
    
    # Sinistra: progetto e file
    footer_left = f"Distinta Base – {project_name} | File: {filename}"
    canvas_obj.drawString(15 * mm, 11 * mm, footer_left)
    
    # Centro: sistema generatore
    footer_center = "Generato automaticamente con WallBuild TAKTAK® - Sistema di ottimizzazione pareti"
    text_width = canvas_obj.stringWidth(footer_center, 'Helvetica', 7)
    canvas_obj.drawString((page_width - text_width) / 2, 8 * mm, footer_center)
    
    # Destra: paginazione
    footer_right = f"Pag. {doc.page}"
    canvas_obj.drawRightString(page_width - 15 * mm, 11 * mm, footer_right)
    
    canvas_obj.restoreState()


# ============================================================================
# EXPORT PROFESSIONALE A4 LANDSCAPE MULTIPAGINA (3 PAGINE) - TAKTAK®
# ============================================================================


def export_to_pdf_professional_multipage(
    summary: Dict[str, int],
    customs: List[Dict],
    placed: List[Dict],
    wall_polygon: Polygon,
    apertures: Optional[List[Polygon]] = None,
    project_name: str = "Progetto Parete",
    out_path: str = "distinta_base_multipagina.pdf",
    params: Optional[Dict] = None,
    block_config: Optional[Dict] = None,
    author: str = "N. Bovo",
    revision: str = "Rev 1.0",
) -> str:
    """
    Genera DISTINTA BASE PROFESSIONALE MULTIPAGINA (4 pagine A4 orizzontali).
    
    PAGINA 1: Sintesi e Riepilogo Tecnico
    - Header con logo TAKTAK®
    - Tabella riepilogo progetto
    - Grafico torta Standard vs Custom
    - Parametri tecnici
    
    PAGINA 2: Schema Costruttivo Parete FULL-PAGE
    - Schema grafico GRANDE da solo (massima larghezza)
    - Legenda blocchi sotto lo schema
    - Titolo e assi millimetrici
    
    PAGINA 3: Blocchi Standard Dettagliati
    - Tabella completa con: Categoria, Nome, Q.tà, Dimensioni, Numerazione (A1, A2...)
    - Aree totali per categoria
    
    PAGINA 4: Blocchi Custom Dettagliati
    - Tabella completa con: Categoria, Nome, Q.tà, Dimensioni, Numerazione (D1, D2...), Note
    - Aree totali e riepilogo finale
    
    Args:
        summary: Riassunto blocchi standard
        customs: Lista pezzi custom
        placed: Blocchi posizionati
        wall_polygon: Geometria parete
        apertures: Aperture opzionali
        project_name: Nome progetto
        out_path: Path output
        params: Parametri tecnici
        block_config: Configurazione blocchi
        author: Nome autore/redattore
        revision: Versione documento
        
    Returns:
        Path del PDF generato
    """
    if not REPORTLAB_AVAILABLE:
        raise RuntimeError("reportlab non disponibile. Installa con: pip install reportlab")

    organized_path = get_organized_output_path(out_path, "pdf")
    
    # Setup documento A4 landscape
    doc = SimpleDocTemplate(
        organized_path,
        pagesize=landscape(A4),
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=20 * mm,
    )
    
    story: List = []
    styles = getSampleStyleSheet()
    
    # Calcola dimensioni parete per header
    minx, miny, maxx, maxy = wall_polygon.bounds
    wall_width_m = (maxx - minx) / 1000
    wall_height_m = (maxy - miny) / 1000
    
    # ========================================================================
    # PAGINA 1: SINTESI E RIEPILOGO TECNICO (invariata)
    # ========================================================================
    
    story.extend(_build_page1_header(
        project_name, wall_width_m, wall_height_m, author, revision, styles
    ))
    story.append(Spacer(1, 8 * mm))
    
    # Layout 2 colonne per pagina 1
    left_col_p1 = []
    right_col_p1 = []
    
    # Colonna sinistra: Riepilogo + Grafico torta
    left_col_p1.append(_build_full_summary_table(summary, customs, wall_polygon, styles))
    left_col_p1.append(Spacer(1, 5 * mm))
    
    pie_chart = _generate_efficiency_pie_chart_large(summary, customs)
    if pie_chart:
        left_col_p1.append(pie_chart)
    
    # Colonna destra: Parametri tecnici dettagliati
    right_col_p1.append(_build_full_technical_params(params, block_config, styles))
    
    # Combina colonne
    page1_table = Table(
        [[left_col_p1, right_col_p1]],
        colWidths=[133 * mm, 134 * mm]
    )
    page1_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(page1_table)
    
    # Fine pagina 1
    story.append(PageBreak())
    
    # ========================================================================
    # PAGINA 2: SCHEMA COSTRUTTIVO PARETE FULL-PAGE (SOLO IMMAGINE)
    # ========================================================================
    
    # Costruiamo gli elementi della pagina 2 in una lista separata
    page2_elements = []
    page2_elements.extend(_build_page2_header_fullpage(project_name, wall_width_m, wall_height_m, styles))
    page2_elements.append(Spacer(1, 2 * mm))  # Ridotto da 3mm a 2mm
    
    # Schema MOLTO GRANDE full-page - MASSIMA DIMENSIONE POSSIBILE
    print(f"🎨 [DEBUG] Generazione schema pagina 2: matplotlib={'DISPONIBILE' if MATPLOTLIB_AVAILABLE else 'NON DISPONIBILE'}")
    print(f"🎨 [DEBUG] Parametri: wall_polygon={wall_polygon is not None}, placed={len(placed) if placed else 0}, customs={len(customs) if customs else 0}")
    
    schema_fullpage = _generate_wall_schema_fullpage(
        wall_polygon, placed, customs, apertures, block_config,
        width_mm=260,  # MASSIMA larghezza per A4 landscape
        height_mm=120   # RIDOTTO da 135 a 120 per sicurezza
    )
    
    print(f"🎨 [DEBUG] Schema generato: {schema_fullpage is not None}")
    
    if schema_fullpage:
        # Immagine centrata senza troppo spazio
        page2_elements.append(schema_fullpage)
        page2_elements.append(Spacer(1, 2 * mm))  # Ridotto da 3mm a 2mm
        
        # Nota sotto lo schema
        note_style = ParagraphStyle("SchemaNote", parent=styles["Normal"], fontSize=7, textColor=colors.grey, alignment=TA_CENTER)
        page2_elements.append(Paragraph("Schema costruttivo con numerazione blocchi (A1, A2, B1... D1, D2, E1...)", note_style))
    else:
        # Fallback se lo schema non viene generato
        error_style = ParagraphStyle("Error", parent=styles["Normal"], fontSize=14, textColor=colors.red, alignment=TA_CENTER)
        page2_elements.append(Spacer(1, 30 * mm))
        page2_elements.append(Paragraph("<b>⚠️ Schema costruttivo non disponibile</b>", error_style))
        page2_elements.append(Spacer(1, 5 * mm))
        page2_elements.append(Paragraph("Matplotlib non disponibile o errore nella generazione dell'immagine", error_style))
    
    # Aggiungiamo TUTTO in un KeepTogether per forzare header + schema sulla stessa pagina
    # MA NON funziona per immagini grandi, quindi aggiungiamo direttamente alla story
    story.extend(page2_elements)
    
    # Fine pagina 2 - FORZA nuovo breakpoint qui
    story.append(PageBreak())
    
    # ========================================================================
    # PAGINA 3: BLOCCHI STANDARD + CUSTOM + RIEPILOGO FINALE (TUTTO IN UNA PAGINA)
    # ========================================================================
    
    story.extend(_build_page3_combined_header(project_name, styles))
    story.append(Spacer(1, 3 * mm))  # Ridotto da 5mm a 3mm
    
    # BLOCCHI STANDARD con numerazione (tabella compatta)
    story.append(_build_compact_standard_table(summary, placed, styles, block_config))
    story.append(Spacer(1, 3 * mm))  # Ridotto da 4mm a 3mm
    
    # BLOCCHI CUSTOM con numerazione (tabella compatta)
    story.append(_build_compact_custom_table(customs, styles))
    story.append(Spacer(1, 3 * mm))  # Ridotto da 4mm a 3mm
    
    # RIEPILOGO FINALE (barra visiva compatta)
    story.append(_build_final_summary_compact(summary, customs, wall_polygon, styles))
    
    # Build con footer dinamico - total_pages viene calcolato DOPO il build
    # ma dobbiamo stimarlo: con il contenuto attuale sono 4 pagine
    total_pages = 4  # Aggiornato da 3 a 4 perché pagina 3 si estende su 2 pagine
    
    # Classe counter per tracciare le pagine correttamente
    class PageCounter:
        def __init__(self):
            self.count = 0
    
    page_counter = PageCounter()
    
    def on_page(canvas, doc):
        page_counter.count += 1
        _draw_multipage_footer(
            canvas, doc, project_name, out_path, page_counter.count, total_pages
        )
    
    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    
    print(f"✅ [PDF] Distinta Base Multipagina ({total_pages} pagine) generata: {organized_path}")
    return organized_path


# ============================================================================
# FUNZIONI HELPER PER PAGINA 1
# ============================================================================


def _build_page1_header(project_name: str, wall_w: float, wall_h: float, author: str, revision: str, styles) -> List:
    """Header pagina 1 con logo e titolo principale."""
    elements: List = []
    now = datetime.datetime.now()
    
    # Logo TAKTAK® sinistra
    logo_style = ParagraphStyle(
        "LogoPage1", parent=styles["Normal"], fontSize=18,
        textColor=BRAND_BLUE, fontName="Helvetica-Bold", alignment=TA_LEFT
    )
    logo_para = Paragraph("<b>TAKTAK<sup>®</sup></b>", logo_style)
    
    # Titolo centrale grande
    title_style = ParagraphStyle(
        "TitlePage1", parent=styles["Title"], fontSize=16,
        textColor=BRAND_BLUE, fontName="Helvetica-Bold", alignment=TA_CENTER
    )
    title_text = f"<b>DISTINTA BASE BLOCCHI – PARETE {wall_w:.0f}×{wall_h:.0f} m</b>"
    title_para = Paragraph(title_text, title_style)
    
    # Metadata destra
    meta_style = ParagraphStyle(
        "MetaPage1", parent=styles["Normal"], fontSize=9,
        textColor=black, alignment=TA_RIGHT
    )
    meta_text = f"""
    Relazione tecnica e schema costruttivo<br/>
    {revision} | {now.strftime('%d/%m/%Y')}<br/>
    Redatto da: {author}
    """
    meta_para = Paragraph(meta_text, meta_style)
    
    # Tabella header
    header_table = Table([[logo_para, title_para, meta_para]], colWidths=[60 * mm, 147 * mm, 60 * mm])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
    ]))
    elements.append(header_table)
    
    # Linea separatore blu
    separator = Table([[""]], colWidths=[267 * mm])
    separator.setStyle(TableStyle([('LINEABOVE', (0, 0), (-1, 0), 2, BRAND_BLUE)]))
    elements.append(separator)
    
    return elements


def _build_full_summary_table(summary: Dict[str, int], customs: List[Dict], wall_polygon: Polygon, styles) -> Table:
    """Tabella riepilogo completa per pagina 1."""
    total_standard = sum(summary.values())
    total_custom = len(customs)
    total_blocks = total_standard + total_custom
    efficiency = (total_standard / total_blocks * 100) if total_blocks > 0 else 0
    area_m2 = wall_polygon.area / 1_000_000
    
    data = [
        ["RIEPILOGO PROGETTO", ""],
        ["Blocchi Standard Totali:", f"{total_standard}"],
        ["Blocchi Custom Totali:", f"{total_custom}"],
        ["Efficienza:", f"{efficiency:.1f} %"],
        ["Area Parete:", f"{area_m2:.2f} m²"],
    ]
    
    table = Table(data, colWidths=[70 * mm, 40 * mm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), BRAND_BLUE),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), "Helvetica-Bold"),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('ALIGN', (0, 0), (-1, -1), "LEFT"),
        ('GRID', (0, 0), (-1, -1), 0.3, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), "MIDDLE"),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    
    return table


def _generate_efficiency_pie_chart_large(summary: Dict[str, int], customs: List[Dict]):
    """Grafico torta più grande per pagina 1."""
    if not MATPLOTLIB_AVAILABLE:
        return None
    
    try:
        total_standard = sum(summary.values())
        total_custom = len(customs)
        
        if total_standard + total_custom == 0:
            return None
        
        fig, ax = plt.subplots(figsize=(80 / 25.4, 80 / 25.4), dpi=200)
        
        sizes = [total_standard, total_custom]
        labels = [f'Standard\n{total_standard} pz', f'Custom\n{total_custom} pz']
        colors_pie = ['#4A90E2', '#50C878']
        explode = (0.05, 0)
        
        wedges, texts, autotexts = ax.pie(
            sizes, explode=explode, labels=labels, autopct='%1.1f%%',
            colors=colors_pie, startangle=90,
            textprops={'fontsize': 10, 'fontweight': 'bold'}
        )
        
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontsize(11)
        
        ax.set_title("Standard vs Custom", fontsize=12, fontweight="bold", pad=10)
        
        img_buffer = io.BytesIO()
        fig.savefig(img_buffer, format="png", dpi=200, bbox_inches="tight", facecolor="white")
        img_buffer.seek(0)
        plt.close(fig)
        
        return Image(img_buffer, width=80 * mm, height=80 * mm)
        
    except Exception as exc:
        print(f"⚠️ [WARN] Errore grafico torta: {exc}")
        return None


def _build_full_technical_params(params: Optional[Dict], block_config: Optional[Dict], styles) -> Table:
    """Tabella parametri tecnici completa per pagina 1."""
    data = [["PARAMETRI TECNICI", "VALORE"]]
    
    if params:
        full_params = [
            ("Algoritmo Packing", params.get('algorithm', 'Greedy + Backtrack')),
            ("Altezza Blocco Standard", f"{params.get('block_height_mm', 495)} mm"),
            ("Larghezze Blocchi", f"{params.get('block_widths_mm', [1239, 826, 413])}"),
            ("Offset Righe Dispari", f"{params.get('row_offset_mm', 826)} mm"),
            ("Griglia Snap", f"{params.get('snap_mm', 1.0)} mm"),
            ("Margine Aperture", f"{params.get('keep_out_mm', 2.0)} mm"),
            ("Merge Custom Row-Aware", f"{params.get('row_aware_merge', True)}"),
            ("Max Larghezza Custom", f"{params.get('split_max_width_mm', 413)} mm"),
        ]
    else:
        full_params = [
            ("Algoritmo Packing", "Greedy + Backtrack"),
            ("Altezza Blocco", "495 mm"),
            ("Offset Righe", "826 mm"),
            ("Snap Grid", "1.0 mm"),
        ]
    
    for label, value in full_params:
        data.append([label, str(value)])
    
    table = Table(data, colWidths=[70 * mm, 50 * mm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.orange),
        ('TEXTCOLOR', (0, 0), (-1, 0), black),
        ('FONTNAME', (0, 0), (-1, 0), "Helvetica-Bold"),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('ALIGN', (0, 0), (-1, -1), "LEFT"),
        ('GRID', (0, 0), (-1, -1), 0.3, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), "MIDDLE"),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    
    return table


# ============================================================================
# FUNZIONI HELPER PER PAGINA 2
# ============================================================================


def _build_page2_header(project_name: str, wall_w: float, wall_h: float, styles) -> List:
    """Header pagina 2 con titolo schema."""
    elements: List = []
    
    title_style = ParagraphStyle(
        "TitlePage2", parent=styles["Title"], fontSize=14,
        textColor=BRAND_BLUE, fontName="Helvetica-Bold", alignment=TA_CENTER
    )
    title_text = f"<b>Schema Costruttivo Parete – Vista Frontale</b><br/><font size=10>Parete {wall_w:.1f}m × {wall_h:.1f}m</font>"
    title_para = Paragraph(title_text, title_style)
    
    elements.append(title_para)
    
    # Linea separatore
    separator = Table([[""]], colWidths=[267 * mm])
    separator.setStyle(TableStyle([('LINEABOVE', (0, 0), (-1, 0), 1.5, BRAND_BLUE)]))
    elements.append(separator)
    
    return elements


def _generate_wall_schema_large(wall_polygon, placed, customs, apertures, block_config, width_mm=190, height_mm=150):
    """Schema parete grande per pagina 2."""
    # Riusa la logica esistente con dimensioni maggiorate
    return _generate_professional_wall_schema(
        wall_polygon, placed, customs, apertures, block_config,
        width_mm=width_mm, height_mm=height_mm
    )


def _build_mini_standard_table(summary, placed, styles, block_config) -> Table:
    """Mini tabella blocchi standard per pagina 2."""
    data = [["BLOCCHI STD", "Q.tà"]]
    
    if block_config and block_config.get("size_to_letter"):
        grouped = group_blocks_by_category(placed, block_config.get("size_to_letter"))
    else:
        grouped = group_blocks_by_category(placed)
    
    for category in sorted(grouped.keys()):
        count = len(grouped[category])
        data.append([f"Cat. {category}", str(count)])
    
    table = Table(data, colWidths=[40 * mm, 20 * mm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), BRAND_BLUE),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), "Helvetica-Bold"),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('ALIGN', (1, 0), (-1, -1), "CENTER"),
        ('GRID', (0, 0), (-1, -1), 0.3, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), "MIDDLE"),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    
    return table


def _build_mini_custom_table(customs, styles) -> Table:
    """Mini tabella pezzi custom per pagina 2."""
    data = [["PEZZI CUSTOM", "Q.tà"]]
    
    grouped = group_custom_blocks_by_category(customs)
    
    for category in sorted(grouped.keys()):
        count = len(grouped[category])
        data.append([f"Cat. {category}", str(count)])
    
    table = Table(data, colWidths=[40 * mm, 20 * mm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkgreen),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), "Helvetica-Bold"),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('ALIGN', (1, 0), (-1, -1), "CENTER"),
        ('GRID', (0, 0), (-1, -1), 0.3, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), "MIDDLE"),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    
    return table


# ============================================================================
# FUNZIONI HELPER PER PAGINA 2 - SCHEMA FULL-PAGE
# ============================================================================


def _build_page2_header_fullpage(project_name: str, wall_w: float, wall_h: float, styles) -> List:
    """Header pagina 2 con titolo schema full-page."""
    elements: List = []
    
    title_style = ParagraphStyle(
        "TitlePage2Full", parent=styles["Title"], fontSize=14,
        textColor=BRAND_BLUE, fontName="Helvetica-Bold", alignment=TA_CENTER
    )
    title_text = f"<b>Schema Costruttivo Parete – Vista Frontale</b><br/><font size=10>Parete {wall_w:.1f}m × {wall_h:.1f}m – Numerazione Operatori Cantiere</font>"
    title_para = Paragraph(title_text, title_style)
    
    elements.append(title_para)
    
    # Linea separatore
    separator = Table([[""]], colWidths=[267 * mm])
    separator.setStyle(TableStyle([('LINEABOVE', (0, 0), (-1, 0), 1.5, BRAND_BLUE)]))
    elements.append(separator)
    
    return elements


def _generate_wall_schema_fullpage(wall_polygon, placed, customs, apertures, block_config, width_mm=260, height_mm=155):
    """Schema parete FULL-PAGE massima larghezza per pagina 2."""
    if not MATPLOTLIB_AVAILABLE:
        print("❌ Matplotlib non disponibile - schema non può essere generato")
        return None
    
    try:
        # DPI altissimo per stampa professionale
        fig, ax = plt.subplots(figsize=(width_mm / 25.4, height_mm / 25.4), dpi=300)
        ax.set_aspect("equal")
        
        minx, miny, maxx, maxy = wall_polygon.bounds
        margin = max((maxx - minx), (maxy - miny)) * 0.02
        ax.set_xlim(minx - margin, maxx + margin)
        ax.set_ylim(miny - margin, maxy + margin)
        
        # Contorno parete (blu TAKTAK®)
        x, y = wall_polygon.exterior.xy
        ax.plot(x, y, color='#1B3B6F', linewidth=3, label="Contorno Parete", zorder=10)
        
        # Etichette blocchi
        if block_config and block_config.get("size_to_letter"):
            detailed_std, detailed_custom = create_detailed_block_labels(
                placed, customs, block_config.get("size_to_letter")
            )
        else:
            detailed_std, detailed_custom = create_detailed_block_labels(placed, customs)
        
        # Blocchi standard (grigio)
        for i, blk in enumerate(placed):
            rect = patches.Rectangle(
                (blk["x"], blk["y"]),
                blk["width"],
                blk["height"],
                facecolor="#E5E5E5",
                edgecolor="black",
                linewidth=0.5,
                zorder=5
            )
            ax.add_patch(rect)
            
            # Etichetta numerazione GRANDE per operatori
            label_info = detailed_std.get(i)
            if label_info:
                category = label_info["display"]["bottom_left"]
                number = label_info["display"]["top_right"]
                full_label = f"{category}{number}"
                
                # Posizione alto-destra
                fontsize = min(9, max(5, blk["width"] / 180))
                ax.text(
                    blk["x"] + blk["width"] - 8,
                    blk["y"] + blk["height"] - 8,
                    full_label,
                    ha="right",
                    va="top",
                    fontsize=fontsize,
                    fontweight="bold",
                    color="red",
                    bbox=dict(boxstyle="round,pad=0.25", facecolor="white", alpha=0.98, edgecolor="red", linewidth=0.8),
                    zorder=15
                )
        
        # Pezzi custom (verde con hatch)
        for i, cust in enumerate(customs):
            try:
                poly = shape(cust["geometry"])
                patch = patches.Polygon(
                    list(poly.exterior.coords),
                    facecolor="#90EE90",
                    edgecolor="#228B22",
                    linewidth=0.8,
                    hatch="///",
                    alpha=0.65,
                    zorder=5
                )
                ax.add_patch(patch)
                
                # Etichetta custom GRANDE
                label_info = detailed_custom.get(i)
                if label_info:
                    category = label_info["display"]["bottom_left"]
                    number = label_info["display"]["top_right"]
                    full_label = f"{category}{number}"
                    
                    fontsize = min(8, max(5, cust["width"] / 180))
                    ax.text(
                        cust["x"] + cust["width"] - 8,
                        cust["y"] + cust["height"] - 8,
                        full_label,
                        ha="right",
                        va="top",
                        fontsize=fontsize,
                        fontweight="bold",
                        color="#228B22",
                        bbox=dict(boxstyle="round,pad=0.25", facecolor="white", alpha=0.98, edgecolor="#228B22", linewidth=0.8),
                        zorder=15
                    )
            except Exception:
                continue
        
        # Aperture (rosso tratteggiato)
        if apertures:
            for ap in apertures:
                x, y = ap.exterior.xy
                ax.plot(x, y, color="red", linestyle="--", linewidth=2, label="Aperture", zorder=8)
                ax.fill(x, y, color="red", alpha=0.12, zorder=3)
        
        # Titolo e assi
        ax.set_title("Schema Costruttivo con Numerazione Operatori", fontsize=12, fontweight="bold", pad=12, color='#1B3B6F')
        ax.grid(True, alpha=0.25, linestyle=":", linewidth=0.5, zorder=1)
        ax.set_xlabel("Larghezza (mm)", fontsize=9, fontweight="bold")
        ax.set_ylabel("Altezza (mm)", fontsize=9, fontweight="bold")
        ax.tick_params(labelsize=7)
        
        # Legenda
        handles, labels = ax.get_legend_handles_labels()
        by_label = dict(zip(labels, handles))
        ax.legend(by_label.values(), by_label.keys(), loc="upper right", fontsize=7, framealpha=0.95)
        
        # Salva in buffer
        img_buffer = io.BytesIO()
        fig.savefig(
            img_buffer,
            format="png",
            dpi=300,
            bbox_inches="tight",
            facecolor="white",
            edgecolor="none",
        )
        img_buffer.seek(0)
        plt.close(fig)
        
        return Image(img_buffer, width=width_mm * mm, height=height_mm * mm)
        
    except Exception as exc:
        print(f"⚠️ Errore generazione schema: {exc}")
        return None


def _build_full_legend_table(block_config, customs, placed, styles) -> Table:
    """Tabella legenda COMPLETA per pagina 2 sotto lo schema."""
    data = [["CATEGORIA", "DESCRIZIONE", "DIMENSIONI (mm)", "ESEMPIO NUMERAZIONE"]]
    
    # Legenda blocchi standard
    if block_config and block_config.get("size_to_letter"):
        grouped_std = group_blocks_by_category(placed, block_config.get("size_to_letter"))
        for category in sorted(grouped_std.keys()):
            blocks = grouped_std[category]
            first = blocks[0]
            count = len(blocks)
            dims = f"{first['width']} × {first['height']}"
            numbering_example = f"{category}1, {category}2 ... {category}{min(count, 3)}"
            data.append([f"Categoria {category}", "Blocco Standard", dims, numbering_example])
    else:
        data.append(["Categoria A", "Blocco Standard", "1239 × 495", "A1, A2, A3..."])
    
    # Legenda custom
    grouped_custom = group_custom_blocks_by_category(customs)
    for category in sorted(grouped_custom.keys()):
        blocks = grouped_custom[category]
        first = blocks[0]
        count = len(blocks)
        dims = f"{first['width']:.0f} × {first['height']:.0f}"
        numbering_example = f"{category}1, {category}2 ... {category}{min(count, 3)}"
        
        ctype = first.get('ctype', 2)
        desc = "Pezzo Custom - Largh. ridotta" if ctype == 1 else "Pezzo Custom - Alt. ridotta"
        
        data.append([f"Categoria {category}", desc, dims, numbering_example])
    
    table = Table(data, colWidths=[35 * mm, 65 * mm, 40 * mm, 70 * mm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), BRAND_BLUE),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), "Helvetica-Bold"),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('ALIGN', (0, 0), (-1, -1), "LEFT"),
        ('GRID', (0, 0), (-1, -1), 0.3, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), "MIDDLE"),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    
    return table


# ============================================================================
# FUNZIONI HELPER PER PAGINA 3 - BLOCCHI STANDARD
# ============================================================================


def _build_page3_header_standard(project_name: str, styles) -> List:
    """Header pagina 3 con titolo blocchi standard."""
    elements: List = []
    
    title_style = ParagraphStyle(
        "TitlePage3Std", parent=styles["Title"], fontSize=14,
        textColor=BRAND_BLUE, fontName="Helvetica-Bold", alignment=TA_CENTER
    )
    title_text = "<b>Distinta Base – Blocchi Standard</b><br/><font size=10>Elenco completo con numerazione</font>"
    title_para = Paragraph(title_text, title_style)
    
    elements.append(title_para)
    
    # Linea separatore
    separator = Table([[""]], colWidths=[267 * mm])
    separator.setStyle(TableStyle([('LINEABOVE', (0, 0), (-1, 0), 1.5, BRAND_BLUE)]))
    elements.append(separator)
    
    return elements


def _build_standard_table_with_numbering(summary, placed, styles, block_config) -> Table:
    """Tabella COMPLETA blocchi standard con numerazione A1, A2, A3..."""
    data = [["CATEGORIA", "NOME BLOCCO", "Q.TÀ", "DIMENSIONI (mm)", "NUMERAZIONE"]]
    
    # Ottieni etichette dettagliate
    if block_config and block_config.get("size_to_letter"):
        detailed_std, _ = create_detailed_block_labels(placed, [], block_config.get("size_to_letter"))
        grouped = group_blocks_by_category(placed, block_config.get("size_to_letter"))
    else:
        detailed_std, _ = create_detailed_block_labels(placed, [])
        grouped = group_blocks_by_category(placed)
    
    total_count = 0
    
    for category in sorted(grouped.keys()):
        blocks = grouped[category]
        count = len(blocks)
        first = blocks[0]
        width = first['width']
        height = first['height']
        
        # Nome blocco descrittivo
        block_name = f"Blocco Standard {category}"
        
        # Genera numerazione completa (es: A1, A2, A3, ... A25)
        numbering_list = [f"{category}{i+1}" for i in range(count)]
        
        # Se troppi, tronca e mostra esempio
        if len(numbering_list) > 15:
            numbering_display = ", ".join(numbering_list[:10]) + f", ... {category}{count}"
        else:
            numbering_display = ", ".join(numbering_list)
        
        data.append([
            f"Categoria {category}",
            block_name,
            str(count),
            f"{width} × {height}",
            numbering_display
        ])
        
        total_count += count
    
    # Riga totale
    data.append(["TOTALE STANDARD", "—", str(total_count), "—", f"{total_count} blocchi totali"])
    
    table = Table(data, colWidths=[35 * mm, 50 * mm, 25 * mm, 40 * mm, 110 * mm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), BRAND_BLUE),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), "Helvetica-Bold"),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('FONTSIZE', (0, 1), (-1, -2), 8),
        ('BACKGROUND', (0, -1), (-1, -1), colors.lightblue),
        ('FONTNAME', (0, -1), (-1, -1), "Helvetica-Bold"),
        ('FONTSIZE', (0, -1), (-1, -1), 9),
        ('ALIGN', (2, 1), (2, -1), "CENTER"),
        ('GRID', (0, 0), (-1, -1), 0.3, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), "MIDDLE"),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    
    return table


# ============================================================================
# FUNZIONI HELPER PER PAGINA 4 - BLOCCHI CUSTOM
# ============================================================================


def _build_page4_header_custom(project_name: str, styles) -> List:
    """Header pagina 4 con titolo blocchi custom."""
    elements: List = []
    
    title_style = ParagraphStyle(
        "TitlePage4Custom", parent=styles["Title"], fontSize=14,
        textColor=colors.darkgreen, fontName="Helvetica-Bold", alignment=TA_CENTER
    )
    title_text = "<b>Distinta Base – Pezzi Custom</b><br/><font size=10>Elenco completo con numerazione e note</font>"
    title_para = Paragraph(title_text, title_style)
    
    elements.append(title_para)
    
    # Linea separatore verde
    separator = Table([[""]], colWidths=[267 * mm])
    separator.setStyle(TableStyle([('LINEABOVE', (0, 0), (-1, 0), 1.5, colors.darkgreen)]))
    elements.append(separator)
    
    return elements


def _build_custom_table_with_numbering(customs, styles) -> Table:
    """Tabella COMPLETA blocchi custom con numerazione D1, D2, D3..."""
    data = [["CATEGORIA", "NOME PEZZO", "Q.TÀ", "DIMENSIONI (mm)", "NUMERAZIONE", "NOTE"]]
    
    # Ottieni etichette dettagliate
    _, detailed_custom = create_detailed_block_labels([], customs)
    grouped = group_custom_blocks_by_category(customs)
    
    total_count = 0
    
    for category in sorted(grouped.keys()):
        blocks = grouped[category]
        count = len(blocks)
        first = blocks[0]
        width = first['width']
        height = first['height']
        
        # Nome pezzo descrittivo
        piece_name = f"Pezzo Custom {category}"
        
        # Genera numerazione completa (es: D1, D2, D3, ... D7)
        numbering_list = [f"{category}{i+1}" for i in range(count)]
        
        # Se troppi, tronca
        if len(numbering_list) > 10:
            numbering_display = ", ".join(numbering_list[:8]) + f", ... {category}{count}"
        else:
            numbering_display = ", ".join(numbering_list)
        
        # Determina nota
        ctype = first.get('ctype', 2)
        if ctype == 1:
            note = "Larghezza ridotta per adattamento"
        elif ctype == 2:
            note = "Altezza ridotta per adattamento"
        else:
            note = "Forma irregolare personalizzata"
        
        data.append([
            f"Categoria {category}",
            piece_name,
            str(count),
            f"{width:.0f} × {height:.0f}",
            numbering_display,
            note
        ])
        
        total_count += count
    
    # Riga totale
    data.append(["TOTALE CUSTOM", "—", str(total_count), "—", f"{total_count} pezzi totali", "Taglio su misura"])
    
    table = Table(data, colWidths=[32 * mm, 40 * mm, 22 * mm, 35 * mm, 70 * mm, 60 * mm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkgreen),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), "Helvetica-Bold"),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('FONTSIZE', (0, 1), (-1, -2), 8),
        ('BACKGROUND', (0, -1), (-1, -1), BRAND_GREEN),
        ('FONTNAME', (0, -1), (-1, -1), "Helvetica-Bold"),
        ('FONTSIZE', (0, -1), (-1, -1), 9),
        ('ALIGN', (2, 1), (2, -1), "CENTER"),
        ('GRID', (0, 0), (-1, -1), 0.3, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), "MIDDLE"),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    
    return table


# ============================================================================
# FUNZIONI HELPER PER PAGINA 3 - COMPATTA (STANDARD + CUSTOM + RIEPILOGO)
# ============================================================================


def _build_page3_combined_header(project_name: str, styles) -> List:
    """Header pagina 3 con titolo distinta base completa."""
    elements: List = []
    
    title_style = ParagraphStyle(
        "TitlePage3Combined", parent=styles["Title"], fontSize=14,
        textColor=BRAND_BLUE, fontName="Helvetica-Bold", alignment=TA_CENTER
    )
    title_text = "<b>Distinta Base Completa – Blocchi Standard e Custom</b><br/><font size=10>Elenco con numerazione e riepilogo finale</font>"
    title_para = Paragraph(title_text, title_style)
    
    elements.append(title_para)
    
    # Linea separatore
    separator = Table([[""]], colWidths=[267 * mm])
    separator.setStyle(TableStyle([('LINEABOVE', (0, 0), (-1, 0), 1.5, BRAND_BLUE)]))
    elements.append(separator)
    
    return elements


def _build_compact_standard_table(summary, placed, styles, block_config) -> Table:
    """Tabella COMPATTA blocchi standard con numerazione (per pagina 3)."""
    data = [["BLOCCHI STANDARD", "", "", "", ""]]
    data.append(["CATEGORIA", "DIMENSIONI", "Q.TÀ", "AREA m²", "NUMERAZIONE"])
    
    # Ottieni etichette dettagliate
    if block_config and block_config.get("size_to_letter"):
        grouped = group_blocks_by_category(placed, block_config.get("size_to_letter"))
    else:
        grouped = group_blocks_by_category(placed)
    
    total_count = 0
    total_area = 0.0
    
    for category in sorted(grouped.keys()):
        blocks = grouped[category]
        count = len(blocks)
        first = blocks[0]
        width = first['width']
        height = first['height']
        
        # Calcola area
        area_m2 = (width * height * count) / 1_000_000
        total_area += area_m2
        
        # Genera numerazione compatta
        if count <= 8:
            numbering_display = ", ".join([f"{category}{i+1}" for i in range(count)])
        else:
            numbering_display = ", ".join([f"{category}{i+1}" for i in range(5)]) + f", ... {category}{count}"
        
        data.append([
            f"Cat. {category}",
            f"{width}×{height} mm",
            str(count),
            f"{area_m2:.2f}",
            numbering_display
        ])
        
        total_count += count
    
    # Riga totale
    data.append(["TOTALE STANDARD", "—", str(total_count), f"{total_area:.2f}", f"{total_count} blocchi"])
    
    table = Table(data, colWidths=[45 * mm, 40 * mm, 20 * mm, 25 * mm, 137 * mm])
    table.setStyle(TableStyle([
        # Header principale (riga 0)
        ('BACKGROUND', (0, 0), (-1, 0), BRAND_BLUE),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), "Helvetica-Bold"),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('SPAN', (0, 0), (-1, 0)),
        ('ALIGN', (0, 0), (-1, 0), "CENTER"),
        # Subheader (riga 1)
        ('BACKGROUND', (0, 1), (-1, 1), colors.lightblue),
        ('FONTNAME', (0, 1), (-1, 1), "Helvetica-Bold"),
        ('FONTSIZE', (0, 1), (-1, 1), 9),
        ('ALIGN', (0, 1), (-1, 1), "CENTER"),
        # Dati
        ('FONTSIZE', (0, 2), (-1, -2), 8),
        ('ALIGN', (2, 2), (3, -1), "CENTER"),
        # Totale
        ('BACKGROUND', (0, -1), (-1, -1), colors.lightblue),
        ('FONTNAME', (0, -1), (-1, -1), "Helvetica-Bold"),
        ('FONTSIZE', (0, -1), (-1, -1), 9),
        # Griglia
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), "MIDDLE"),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    
    return table


def _build_compact_custom_table(customs, styles) -> Table:
    """Tabella COMPATTA blocchi custom con numerazione (per pagina 3)."""
    data = [["PEZZI CUSTOM", "", "", "", ""]]
    data.append(["CATEGORIA", "DIMENSIONI", "Q.TÀ", "AREA m²", "NUMERAZIONE"])
    
    if not customs:
        data.append(["—", "Nessun pezzo custom", "0", "0.00", "—"])
    else:
        grouped = group_custom_blocks_by_category(customs)
        
        total_count = 0
        total_area = 0.0
        
        for category in sorted(grouped.keys()):
            blocks = grouped[category]
            count = len(blocks)
            first = blocks[0]
            width = first['width']
            height = first['height']
            
            # Calcola area
            area_m2 = (width * height * count) / 1_000_000
            total_area += area_m2
            
            # Genera numerazione compatta
            if count <= 6:
                numbering_display = ", ".join([f"{category}{i+1}" for i in range(count)])
            else:
                numbering_display = ", ".join([f"{category}{i+1}" for i in range(4)]) + f", ... {category}{count}"
            
            data.append([
                f"Cat. {category}",
                f"{width:.0f}×{height:.0f} mm",
                str(count),
                f"{area_m2:.2f}",
                numbering_display
            ])
            
            total_count += count
        
        # Riga totale
        data.append(["TOTALE CUSTOM", "—", str(total_count), f"{total_area:.2f}", f"{total_count} pezzi"])
    
    table = Table(data, colWidths=[45 * mm, 40 * mm, 20 * mm, 25 * mm, 137 * mm])
    table.setStyle(TableStyle([
        # Header principale (riga 0)
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkgreen),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), "Helvetica-Bold"),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('SPAN', (0, 0), (-1, 0)),
        ('ALIGN', (0, 0), (-1, 0), "CENTER"),
        # Subheader (riga 1)
        ('BACKGROUND', (0, 1), (-1, 1), BRAND_GREEN),
        ('FONTNAME', (0, 1), (-1, 1), "Helvetica-Bold"),
        ('FONTSIZE', (0, 1), (-1, 1), 9),
        ('ALIGN', (0, 1), (-1, 1), "CENTER"),
        # Dati
        ('FONTSIZE', (0, 2), (-1, -2), 8),
        ('ALIGN', (2, 2), (3, -1), "CENTER"),
        # Totale
        ('BACKGROUND', (0, -1), (-1, -1), BRAND_GREEN),
        ('FONTNAME', (0, -1), (-1, -1), "Helvetica-Bold"),
        ('FONTSIZE', (0, -1), (-1, -1), 9),
        # Griglia
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), "MIDDLE"),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    
    return table


def _build_final_summary_compact(summary, customs, wall_polygon, styles) -> Table:
    """Riepilogo finale COMPATTO per pagina 3."""
    # Calcola totali
    total_std = sum(summary.values()) if summary else 0
    total_custom = len(customs) if customs else 0
    total_blocks = total_std + total_custom
    
    # Calcola efficienza
    from shapely.geometry import box
    wall_area = wall_polygon.area / 1_000_000  # m²
    
    # Area blocchi standard
    std_area = 0.0
    for key, count in summary.items():
        if 'x' in key.lower():
            parts = key.lower().split('x')
            if len(parts) >= 2:
                try:
                    w = float(parts[0].replace('std_', '').replace('_', ''))
                    h = float(parts[1])
                    std_area += (w * h * count) / 1_000_000
                except:
                    pass
    
    # Area custom
    custom_area = 0.0
    for cust in customs:
        custom_area += (cust['width'] * cust['height']) / 1_000_000
    
    total_covered = std_area + custom_area
    efficiency = (total_covered / wall_area * 100) if wall_area > 0 else 0
    
    # Header
    data = [["RIEPILOGO FINALE PROGETTO", "", "", ""]]
    
    # Dati riepilogo
    data.append(["Totale Blocchi Standard:", str(total_std), "Area Parete:", f"{wall_area:.2f} m²"])
    data.append(["Totale Pezzi Custom:", str(total_custom), "Area Coperta:", f"{total_covered:.2f} m²"])
    data.append(["TOTALE BLOCCHI:", str(total_blocks), "EFFICIENZA:", f"{efficiency:.1f}%"])
    
    table = Table(data, colWidths=[80 * mm, 40 * mm, 70 * mm, 77 * mm])
    table.setStyle(TableStyle([
        # Header
        ('BACKGROUND', (0, 0), (-1, 0), BRAND_BLUE),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), "Helvetica-Bold"),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('SPAN', (0, 0), (-1, 0)),
        ('ALIGN', (0, 0), (-1, 0), "CENTER"),
        # Dati
        ('FONTSIZE', (0, 1), (-1, -2), 9),
        ('FONTNAME', (0, 1), (0, -1), "Helvetica-Bold"),
        ('FONTNAME', (2, 1), (2, -1), "Helvetica-Bold"),
        ('ALIGN', (1, 1), (1, -1), "CENTER"),
        ('ALIGN', (3, 1), (3, -1), "CENTER"),
        # Ultima riga (totale)
        ('BACKGROUND', (0, -1), (-1, -1), BRAND_GREEN),
        ('FONTNAME', (0, -1), (-1, -1), "Helvetica-Bold"),
        ('FONTSIZE', (0, -1), (-1, -1), 11),
        ('ALIGN', (0, -1), (-1, -1), "CENTER"),
        # Griglia
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), "MIDDLE"),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    
    return table


def _build_legend_box(block_config, customs, styles) -> Table:
    """Box legenda per pagina 2."""
    data = [["LEGENDA", ""]]
    
    # Legenda blocchi standard
    if block_config and block_config.get("size_to_letter"):
        for width_str, letter in sorted(block_config['size_to_letter'].items()):
            height = block_config.get('block_height', 495)
            data.append([f"{letter} =", f"Std {width_str}×{height}"])
    else:
        data.append(["A =", "Std 1239×495"])
    
    # Legenda custom (primi 2)
    grouped_custom = group_custom_blocks_by_category(customs)
    for i, (category, blocks) in enumerate(sorted(grouped_custom.items())[:2]):
        first = blocks[0]
        data.append([f"{category} =", f"Custom {first['width']:.0f}×{first['height']:.0f}"])
    
    table = Table(data, colWidths=[20 * mm, 40 * mm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), BRAND_GRAY),
        ('FONTNAME', (0, 0), (-1, 0), "Helvetica-Bold"),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('FONTSIZE', (0, 1), (-1, -1), 7),
        ('ALIGN', (0, 0), (-1, -1), "LEFT"),
        ('GRID', (0, 0), (-1, -1), 0.3, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), "MIDDLE"),
        ('LEFTPADDING', (0, 0), (-1, -1), 2),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2),
        ('TOPPADDING', (0, 0), (-1, -1), 1),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
    ]))
    
    return table


# ============================================================================
# FUNZIONI HELPER PER PAGINA 3
# ============================================================================


def _build_page3_header(project_name: str, styles) -> List:
    """Header pagina 3 con titolo distinta."""
    elements: List = []
    
    title_style = ParagraphStyle(
        "TitlePage3", parent=styles["Title"], fontSize=14,
        textColor=BRAND_BLUE, fontName="Helvetica-Bold", alignment=TA_CENTER
    )
    title_text = "<b>Distinta Base – Dettaglio Blocchi</b>"
    title_para = Paragraph(title_text, title_style)
    
    elements.append(title_para)
    
    # Linea separatore
    separator = Table([[""]], colWidths=[267 * mm])
    separator.setStyle(TableStyle([('LINEABOVE', (0, 0), (-1, 0), 1.5, BRAND_BLUE)]))
    elements.append(separator)
    
    return elements


def _build_detailed_standard_table(summary, placed, styles, block_config) -> Table:
    """Tabella completa blocchi standard con aree per pagina 3."""
    data = [["CATEGORIA", "Q.TÀ", "DIMENSIONI (mm)", "AREA TOT (m²)"]]
    
    if block_config and block_config.get("size_to_letter"):
        grouped = group_blocks_by_category(placed, block_config.get("size_to_letter"))
    else:
        grouped = group_blocks_by_category(placed)
    
    total_count = 0
    total_area = 0.0
    
    for category in sorted(grouped.keys()):
        blocks = grouped[category]
        count = len(blocks)
        first = blocks[0]
        width = first['width']
        height = first['height']
        area_m2 = (width * height * count) / 1_000_000
        
        data.append([
            f"Categoria {category}",
            str(count),
            f"{width} × {height}",
            f"{area_m2:.2f}"
        ])
        
        total_count += count
        total_area += area_m2
    
    data.append(["TOTALE", str(total_count), "—", f"{total_area:.2f}"])
    
    table = Table(data, colWidths=[50 * mm, 30 * mm, 50 * mm, 40 * mm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), BRAND_BLUE),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), "Helvetica-Bold"),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('FONTSIZE', (0, 1), (-1, -2), 9),
        ('BACKGROUND', (0, -1), (-1, -1), colors.lightblue),
        ('FONTNAME', (0, -1), (-1, -1), "Helvetica-Bold"),
        ('ALIGN', (1, 1), (-1, -1), "CENTER"),
        ('GRID', (0, 0), (-1, -1), 0.3, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), "MIDDLE"),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    
    return table


def _build_detailed_custom_table(customs, styles) -> Table:
    """Tabella completa blocchi custom con note per pagina 3."""
    data = [["CATEGORIA", "Q.TÀ", "DIMENSIONI (mm)", "AREA TOT (m²)", "NOTE"]]
    
    grouped = group_custom_blocks_by_category(customs)
    
    total_count = 0
    total_area = 0.0
    
    for category in sorted(grouped.keys()):
        blocks = grouped[category]
        count = len(blocks)
        first = blocks[0]
        width = first['width']
        height = first['height']
        area_m2 = (width * height * count) / 1_000_000
        
        # Determina nota automaticamente
        ctype = first.get('ctype', 2)
        if ctype == 1:
            note = "Larghezza ridotta"
        elif ctype == 2:
            note = "Altezza ridotta"
        else:
            note = "Forma irregolare"
        
        data.append([
            f"Categoria {category}",
            str(count),
            f"{width:.0f} × {height:.0f}",
            f"{area_m2:.3f}",
            note
        ])
        
        total_count += count
        total_area += area_m2
    
    data.append(["TOTALE CUSTOM", str(total_count), "—", f"{total_area:.3f}", "—"])
    
    table = Table(data, colWidths=[35 * mm, 25 * mm, 40 * mm, 35 * mm, 45 * mm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkgreen),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), "Helvetica-Bold"),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('FONTSIZE', (0, 1), (-1, -2), 8),
        ('BACKGROUND', (0, -1), (-1, -1), BRAND_GREEN),
        ('FONTNAME', (0, -1), (-1, -1), "Helvetica-Bold"),
        ('ALIGN', (1, 1), (-1, -1), "CENTER"),
        ('GRID', (0, 0), (-1, -1), 0.3, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), "MIDDLE"),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    
    return table


def _build_final_summary_bar(summary, customs, styles) -> Table:
    """Riepilogo visivo finale per pagina 3."""
    total_standard = sum(summary.values())
    total_custom = len(customs)
    total = total_standard + total_custom
    
    std_percent = (total_standard / total * 100) if total > 0 else 0
    custom_percent = (total_custom / total * 100) if total > 0 else 0
    
    data = [
        ["RIEPILOGO FINALE", ""],
        [f"✓ Blocchi Standard: {total_standard} pz ({std_percent:.1f}%)", ""],
        [f"✓ Pezzi Custom: {total_custom} pz ({custom_percent:.1f}%)", ""],
        [f"✓ Totale Blocchi: {total} pz", ""],
        ["", "Redatto da WallBuild TAKTAK® System"]
    ]
    
    table = Table(data, colWidths=[150 * mm, 100 * mm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), BRAND_GRAY),
        ('FONTNAME', (0, 0), (-1, 0), "Helvetica-Bold"),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('FONTSIZE', (0, 1), (-1, -2), 9),
        ('FONTSIZE', (0, -1), (-1, -1), 8),
        ('TEXTCOLOR', (0, -1), (-1, -1), colors.grey),
        ('ALIGN', (0, 0), (-1, -1), "LEFT"),
        ('ALIGN', (1, -1), (-1, -1), "RIGHT"),
        ('GRID', (0, 0), (-1, -2), 0.3, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), "MIDDLE"),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    
    return table


def _draw_multipage_footer(canvas_obj, doc, project_name: str, filename: str, page_num: int, total_pages: int):
    """Footer con paginazione multipagina (1/4, 2/4, 3/4, 4/4)."""
    canvas_obj.saveState()
    
    page_width, page_height = landscape(A4)
    
    # Linea blu separatore
    canvas_obj.setStrokeColor(BRAND_BLUE)
    canvas_obj.setLineWidth(1.5)
    canvas_obj.line(15 * mm, 15 * mm, page_width - 15 * mm, 15 * mm)
    
    # Testo footer
    canvas_obj.setFont('Helvetica', 7)
    canvas_obj.setFillColor(colors.grey)
    
    # Titolo pagina specifico per 4 pagine
    page_titles = {
        1: "Sintesi e Riepilogo Tecnico",
        2: "Schema Costruttivo Full-Page con Numerazione",
        3: "Distinta Completa - Blocchi Standard e Custom (1/2)",
        4: "Distinta Completa - Blocchi Standard e Custom (2/2)"
    }
    page_title = page_titles.get(page_num, "Distinta Base")
    
    # Sinistra: progetto e titolo pagina
    footer_left = f"Distinta Base – {project_name} | {page_title}"
    canvas_obj.drawString(15 * mm, 11 * mm, footer_left)
    
    # Centro: sistema generatore
    footer_center = "Generato automaticamente con WallBuild TAKTAK® - Sistema di ottimizzazione pareti"
    text_width = canvas_obj.stringWidth(footer_center, 'Helvetica', 7)
    canvas_obj.drawString((page_width - text_width) / 2, 8 * mm, footer_center)
    
    # Destra: paginazione X/Y
    footer_right = f"Pag. {page_num}/{total_pages}"
    canvas_obj.drawRightString(page_width - 15 * mm, 11 * mm, footer_right)
    
    canvas_obj.restoreState()



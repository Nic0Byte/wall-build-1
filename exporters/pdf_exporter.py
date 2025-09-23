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
    from reportlab.lib.colors import black, gray, white
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import A4
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
    )

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


__all__ = ["export_to_pdf", "REPORTLAB_AVAILABLE"]


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



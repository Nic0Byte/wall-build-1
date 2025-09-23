"""Exporter per il formato JSON."""

import json
from typing import Dict, List, Optional

from exporters.labels import create_block_labels, create_detailed_block_labels
from utils.file_manager import get_organized_output_path

__all__ = ["export_to_json"]


def export_to_json(
    summary: Dict[str, int],
    customs: List[Dict],
    placed: List[Dict],
    out_path: str = "distinta_wall.json",
    params: Optional[Dict] = None,
    block_config: Optional[Dict] = None,
) -> str:
    """Serializza dati di parete nel formato JSON organizzato."""
    organized_path = get_organized_output_path(out_path, "json")

    if block_config and block_config.get("size_to_letter"):
        size_to_letter = block_config.get("size_to_letter")
        print(f"[DEBUG] Export JSON using custom size_to_letter: {size_to_letter}")
        std_labels_detailed, custom_labels_detailed = create_detailed_block_labels(placed, customs, size_to_letter)
        std_labels = {i: label["full_label"] for i, label in std_labels_detailed.items()}
        custom_labels = {i: label["full_label"] for i, label in custom_labels_detailed.items()}
    else:
        print("[DEBUG] Export JSON using default labeling system")
        std_labels, custom_labels = create_block_labels(placed, customs)

    data = {
        "schema_version": "1.0",
        "units": "mm",
        "params": params or {},
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
            "custom_count": len(customs),
        },
    }

    with open(organized_path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=True)

    return organized_path

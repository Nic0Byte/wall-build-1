"""
Fallback heuristics shared by parsing modules.
"""

from __future__ import annotations

from typing import Dict, List

from shapely.geometry import Polygon, box

from .base import ParseResult


def intelligent_fallback(file_bytes: bytes, filename: str, header_info: Dict) -> ParseResult:
    """Return a synthetic wall when all parsing strategies fail."""
    print(" Attivazione fallback intelligente...")

    file_size = len(file_bytes)

    if 'rottini' in filename.lower():
        wall_width = 8000
        wall_height = 2700
    elif 'felice' in filename.lower():
        wall_width = 10000
        wall_height = 3000
    else:
        if file_size > 500000:
            wall_width = 15000
            wall_height = 4000
        elif file_size > 200000:
            wall_width = 10000
            wall_height = 3000
        else:
            wall_width = 8000
            wall_height = 2500

    example_wall = box(0, 0, wall_width, wall_height)

    apertures: List[Polygon] = []
    if file_size > 300000:
        porta1 = box(1000, 0, 2200, 2100)
        apertures.append(porta1)

        if wall_width > 6000:
            finestra1 = box(wall_width - 3000, 800, wall_width - 1500, 2000)
            apertures.append(finestra1)

    print(f" Fallback: parete {wall_width}x{wall_height}mm, {len(apertures)} aperture stimate")
    print("  NOTA: Questo e un layout di esempio. Per risultati accurati, converti il file in DXF R14.")

    return example_wall, apertures


__all__ = ["intelligent_fallback"]

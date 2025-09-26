"""
Universal file parsing entrypoints.
"""

from __future__ import annotations

from .base import ParseResult
from .dwg import analyze_dwg_header, parse_dwg_wall, try_oda_conversion
from .fallbacks import intelligent_fallback
from .svg import parse_svg_wall


def parse_wall_file(
    file_bytes: bytes,
    filename: str,
    layer_wall: str = "MURO",
    layer_holes: str = "BUCHI",
) -> ParseResult:
    """Parse SVG, DWG or DXF content returning wall polygon and apertures."""
    file_ext = filename.lower().split('.')[-1] if '.' in filename else ''

    if file_ext == 'svg':
        print(f" Parsing file SVG: {filename}")
        return parse_svg_wall(file_bytes, layer_wall, layer_holes)

    if file_ext in ['dwg', 'dxf']:
        print(f" Parsing file DWG/DXF: {filename}")

        # ODA FIRST STRATEGY - sempre usa ODA per massima compatibilità
        try:
            print(" Utilizzo ODA File Converter per massima precisione...")
            return try_oda_conversion(file_bytes, filename, layer_wall, layer_holes)
        except Exception as exc:
            print(f" ODA fallito: {exc}, tentativo parser diretto...")
            
            # Fallback al parser diretto
            try:
                return parse_dwg_wall(file_bytes, layer_wall, layer_holes)
            except Exception as exc2:
                print(f" Parser diretto fallito: {exc2}")
                
                # Ultimo resort: fallback intelligente
                header_info = analyze_dwg_header(file_bytes)
                print(f" Formato rilevato: {header_info['format']} {header_info['version']}")
                return intelligent_fallback(file_bytes, filename, header_info)

    print(f" Formato non riconosciuto ({file_ext}), tentativo auto-detection...")

    try:
        content_start = file_bytes[:1000].decode('utf-8', errors='ignore').strip()
        if content_start.startswith('<?xml') or '<svg' in content_start:
            print(" Auto-detected: SVG")
            return parse_svg_wall(file_bytes, layer_wall, layer_holes)
    except Exception:
        pass

    try:
        print(" Auto-detection: tentativo DWG/DXF...")
        header_info = analyze_dwg_header(file_bytes)
        if header_info['is_cad']:
            return parse_dwg_wall(file_bytes, layer_wall, layer_holes)
    except Exception:
        pass

    raise ValueError(f"Formato file non supportato: {filename}. Supportati: SVG, DWG, DXF")


__all__ = ["parse_wall_file"]

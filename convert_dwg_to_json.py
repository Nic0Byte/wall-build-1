#!/usr/bin/env python3
"""
Conversione DWG/DXF → JSON con strategia ODA FIRST
Utilizza il sistema di parsing universale migliorato per massima compatibilità.
"""

import sys
import os
import json
from pathlib import Path
from typing import Dict, List, Any

from parsers.universal import parse_wall_file
from oda_converter import is_oda_available
from shapely.geometry import Polygon

def polygon_to_dict(polygon: Polygon) -> Dict[str, Any]:
    """Converte un Polygon Shapely in dizionario JSON serializzabile"""
    if polygon.is_empty:
        return {"type": "polygon", "exterior": [], "holes": [], "area": 0, "perimeter": 0}
    
    # Coordinate esterne
    exterior_coords = list(polygon.exterior.coords)
    
    # Coordinate holes (se presenti)
    holes_coords = []
    if polygon.interiors:
        holes_coords = [list(interior.coords) for interior in polygon.interiors]
    
    return {
        "type": "polygon",
        "exterior": exterior_coords,
        "holes": holes_coords,
        "area": polygon.area,
        "perimeter": polygon.length,
        "bounds": list(polygon.bounds),  # [minx, miny, maxx, maxy]
        "is_valid": polygon.is_valid
    }

def convert_dwg_to_json(input_path: str, output_path: str = None) -> str:
    """
    Converte DWG/DXF in JSON con geometrie precise
    
    Args:
        input_path: Percorso file DWG/DXF di input
        output_path: Percorso file JSON di output (opzionale)
        
    Returns:
        Percorso del file JSON generato
    """
    
    # Validazioni input
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"File non trovato: {input_path}")
    
    input_file = Path(input_path)
    if input_file.suffix.lower() not in ['.dwg', '.dxf']:
        raise ValueError(f"Formato non supportato: {input_file.suffix}. Usa .dwg o .dxf")
    
    # Path di output
    if not output_path:
        output_path = str(input_file.with_suffix('.json'))
    
    print(f"🔄 Conversione {input_file.name} → {Path(output_path).name}")
    print(f"📍 ODA File Converter: {'✅ Disponibile' if is_oda_available() else '❌ Non disponibile'}")
    
    # Lettura file
    with open(input_path, 'rb') as f:
        file_bytes = f.read()
    
    print(f"📄 Dimensione file: {len(file_bytes):,} bytes")
    
    # Parsing con strategia ODA FIRST
    try:
        wall, apertures = parse_wall_file(file_bytes, input_file.name)
        print(f"✅ Parsing completato: parete + {len(apertures)} aperture")
    except Exception as e:
        raise RuntimeError(f"Errore nel parsing CAD: {e}")
    
    # Conversione in formato JSON
    json_data = {
        "metadata": {
            "source_file": input_file.name,
            "format": input_file.suffix.upper(),
            "parser": "ODA_FIRST_strategy",
            "units": "mm",
            "created": "2025-09-26"
        },
        "wall": polygon_to_dict(wall),
        "apertures": [polygon_to_dict(aperture) for aperture in apertures],
        "summary": {
            "wall_area_mm2": wall.area,
            "wall_perimeter_mm": wall.length,
            "apertures_count": len(apertures),
            "total_apertures_area_mm2": sum(ap.area for ap in apertures)
        }
    }
    
    # Salvataggio JSON
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)
    
    print(f"💾 JSON salvato: {output_path}")
    print(f"🏢 Parete: {wall.area:.1f} mm² ({wall.length:.1f} mm perimetro)")
    print(f"🚪 Aperture: {len(apertures)} per {sum(ap.area for ap in apertures):.1f} mm² totali")
    
    return output_path

def main():
    if len(sys.argv) < 2:
        print("Conversione DWG/DXF → JSON con strategia ODA FIRST")
        print()
        print("Uso:")
        print("  python convert_dwg_to_json.py <input.dwg> [output.json]")
        print()
        print("Esempi:")
        print("  python convert_dwg_to_json.py planimetria.dwg")
        print("  python convert_dwg_to_json.py disegno.dxf output_custom.json")
        print()
        print("Note:")
        print("  - Supporta DWG 2018+ tramite ODA File Converter")
        print("  - Se output non specificato: usa nome input con .json")
        print("  - Estrae pareti e aperture con coordinate precise")
        return
    
    input_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    try:
        result_path = convert_dwg_to_json(input_path, output_path)
        print()
        print(f"🎉 Conversione completata con successo!")
        print(f"📁 Output: {result_path}")
        
    except Exception as e:
        print()
        print(f"❌ Errore: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
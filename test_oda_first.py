#!/usr/bin/env python3
"""
Script di test per la strategia ODA FIRST
"""

import sys
import os
from pathlib import Path
from parsers.universal import parse_wall_file
from oda_converter import is_oda_available

def test_oda_first(file_path: str):
    """Test parsing con strategia ODA FIRST"""
    
    if not os.path.exists(file_path):
        print(f"❌ File non trovato: {file_path}")
        return False
    
    print(f"🔧 Test parsing file: {Path(file_path).name}")
    print(f"📍 ODA disponibile: {is_oda_available()}")
    
    try:
        with open(file_path, 'rb') as f:
            file_bytes = f.read()
        
        print(f"📄 Dimensione file: {len(file_bytes):,} bytes")
        
        # Test parsing con strategia ODA FIRST
        wall, apertures = parse_wall_file(file_bytes, Path(file_path).name)
        
        print(f"✅ Parsing riuscito!")
        print(f"🏢 Parete: area {wall.area:.1f} mm², perimetro {wall.length:.1f} mm")
        print(f"🚪 Aperture: {len(apertures)} trovate")
        
        for i, aperture in enumerate(apertures):
            print(f"   Apertura {i+1}: {aperture.area:.1f} mm²")
        
        return True
        
    except Exception as e:
        print(f"❌ Errore parsing: {e}")
        return False

def main():
    if len(sys.argv) != 2:
        print("Uso: python test_oda_first.py <file.dwg>")
        print("\nEsempi:")
        print("  python test_oda_first.py ROTTINI_LAY_REV0.dwg")
        print("  python test_oda_first.py esempio.dxf")
        return
    
    file_path = sys.argv[1]
    success = test_oda_first(file_path)
    
    print()
    if success:
        print("🎉 Test completato con successo!")
    else:
        print("💥 Test fallito!")
        sys.exit(1)

if __name__ == "__main__":
    main()
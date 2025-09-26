#!/usr/bin/env python3
"""
Modulo per gestire conversione DWG → DXF usando ODA File Converter
"""

import os
import subprocess
import tempfile
import shutil
from pathlib import Path

def find_oda_converter():
    """Trova ODA File Converter nel sistema."""
    possible_paths = [
        r"C:\Program Files\ODA\ODAFileConverter 26.8.0\ODAFileConverter.exe",  # Versione attuale
        r"C:\Program Files\ODA\ODAFileConverter_QT5_vc14_dll_24.12\ODAFileConverter.exe",
        r"C:\Program Files (x86)\ODA\ODAFileConverter_QT5_vc14_dll_24.12\ODAFileConverter.exe",
        r"C:\ODA\ODAFileConverter.exe",
        "ODAFileConverter.exe"  # Se è nel PATH
    ]
    
    for path in possible_paths:
        if os.path.exists(path) or (path == "ODAFileConverter.exe" and shutil.which(path)):
            return path
    return None

def convert_dwg_to_dxf(dwg_bytes: bytes) -> bytes:
    """
    Converte file DWG in DXF usando ODA File Converter.
    
    Args:
        dwg_bytes: Contenuto del file DWG
        
    Returns:
        bytes: Contenuto del file DXF convertito
        
    Raises:
        ValueError: Se ODA non è disponibile o conversione fallisce
    """
    oda_path = find_oda_converter()
    if not oda_path:
        raise ValueError("ODA File Converter non trovato. Installare da: https://www.opendesign.com/guestfiles/oda_file_converter")
    
    # Crea directory temporanee
    with tempfile.TemporaryDirectory() as temp_dir:
        input_dir = Path(temp_dir) / "input"
        output_dir = Path(temp_dir) / "output"
        input_dir.mkdir()
        output_dir.mkdir()
        
        # Salva file DWG
        dwg_file = input_dir / "temp.dwg"
        with open(dwg_file, 'wb') as f:
            f.write(dwg_bytes)
        
        # Comando ODA per conversione
        cmd = [
            oda_path,
            str(input_dir),
            str(output_dir),
            "ACAD2018",  # Versione output
            "DXF",       # Formato output
            "0",         # Recurse subdirectories
            "1",         # Audit each file
            "*.dwg"      # File filter
        ]
        
        try:
            # Esegui conversione
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                raise ValueError(f"ODA conversione fallita: {result.stderr}")
            
            # Leggi file DXF convertito
            dxf_file = output_dir / "temp.dxf"
            if not dxf_file.exists():
                raise ValueError("File DXF non generato da ODA")
            
            with open(dxf_file, 'rb') as f:
                return f.read()
                
        except subprocess.TimeoutExpired:
            raise ValueError("Timeout conversione ODA (>30s)")
        except Exception as e:
            raise ValueError(f"Errore conversione ODA: {e}")

def is_oda_available() -> bool:
    """Controlla se ODA File Converter è disponibile."""
    return find_oda_converter() is not None

# Test
if __name__ == "__main__":
    print("🔧 Test ODA File Converter...")
    
    if is_oda_available():
        print("✅ ODA File Converter trovato!")
        oda_path = find_oda_converter()
        print(f"   Percorso: {oda_path}")
        
        # Test con file esistente
        if os.path.exists("ROTTINI_LAY_REV0.dwg"):
            try:
                with open("ROTTINI_LAY_REV0.dwg", 'rb') as f:
                    dwg_bytes = f.read()
                
                print("🔄 Tentativo conversione...")
                dxf_bytes = convert_dwg_to_dxf(dwg_bytes)
                print(f"✅ Conversione riuscita! DXF: {len(dxf_bytes)} bytes")
                
                # Salva per test
                with open("ROTTINI_converted.dxf", 'wb') as f:
                    f.write(dxf_bytes)
                print("💾 File salvato: ROTTINI_converted.dxf")
                
            except Exception as e:
                print(f"❌ Errore conversione: {e}")
        else:
            print("⚠️ File ROTTINI_LAY_REV0.dwg non trovato per test")
    else:
        print("❌ ODA File Converter non trovato")
        print("📥 Scarica da: https://www.opendesign.com/guestfiles/oda_file_converter")

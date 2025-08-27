#!/usr/bin/env python3
"""
🧪 Test del sistema di organizzazione output

Verifica che i file vengano salvati nelle cartelle corrette
per tipologia (json, pdf, dxf, images, svg).
"""

import os
import sys
import tempfile
from pathlib import Path

# Aggiungi la directory parent al path per importare main
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Import del sistema principale
import main

def test_output_organization():
    """Test completo dell'organizzazione automatica dei file di output."""
    
    print("🧪 TEST ORGANIZZAZIONE OUTPUT")
    print("=" * 50)
    
    # 1. Test setup delle directory
    print("\n📁 Test setup directory...")
    dirs = main.setup_output_directories()
    
    expected_dirs = ['json', 'pdf', 'dxf', 'images', 'svg', 'reports', 'schemas', 'temp']
    for dir_type in expected_dirs:
        assert dir_type in dirs, f"Directory {dir_type} mancante"
        assert os.path.exists(dirs[dir_type]), f"Path {dirs[dir_type]} non creato"
        print(f"  ✅ {dir_type}: {dirs[dir_type]}")
    
    # 2. Test auto-detection del tipo file
    print("\n🔍 Test auto-detection tipo file...")
    test_cases = [
        ("distinta.json", "json"),
        ("report.pdf", "pdf"), 
        ("schema.dxf", "dxf"),
        ("preview.png", "images"),
        ("wall.svg", "svg"),
        ("unknown.xyz", "temp")
    ]
    
    for filename, expected_type in test_cases:
        path = main.get_organized_output_path(filename)
        expected_subdir = expected_type
        assert expected_subdir in path, f"File {filename} non in {expected_subdir}: {path}"
        print(f"  ✅ {filename} → {expected_subdir}")
    
    # 3. Test generazione nomi unici
    print("\n🔢 Test generazione nomi unici...")
    import time
    name1 = main.generate_unique_filename("test", ".json", "project1")
    time.sleep(0.001)  # Piccolo delay per garantire unicità
    name2 = main.generate_unique_filename("test", ".json", "project1")
    assert name1 != name2, "Nomi non unici generati"
    assert "project1" in name1, "Project ID non incluso"
    assert ".json" in name1, "Estensione non inclusa"
    print(f"  ✅ Nome1: {name1}")
    print(f"  ✅ Nome2: {name2}")
    
    # 4. Test demo con output organizzato
    print("\n🚀 Test demo con output organizzato...")
    try:
        # Salva directory corrente
        original_cwd = os.getcwd()
        
        # Esegui demo per testare export reali
        main._demo()
        
        # Verifica che i file siano stati creati nelle cartelle corrette
        output_base = "output"
        
        # Controlla file JSON
        json_dir = os.path.join(output_base, "json")
        if os.path.exists(json_dir):
            json_files = [f for f in os.listdir(json_dir) if f.endswith('.json')]
            if json_files:
                print(f"  ✅ File JSON trovati in {json_dir}: {len(json_files)}")
            else:
                print(f"  ⚠️ Nessun file JSON in {json_dir}")
        
        # Controlla file PDF
        pdf_dir = os.path.join(output_base, "pdf") 
        if os.path.exists(pdf_dir):
            pdf_files = [f for f in os.listdir(pdf_dir) if f.endswith('.pdf')]
            if pdf_files:
                print(f"  ✅ File PDF trovati in {pdf_dir}: {len(pdf_files)}")
            else:
                print(f"  ⚠️ Nessun file PDF in {pdf_dir}")
        
        # Controlla file DXF
        dxf_dir = os.path.join(output_base, "dxf")
        if os.path.exists(dxf_dir):
            dxf_files = [f for f in os.listdir(dxf_dir) if f.endswith('.dxf')]
            if dxf_files:
                print(f"  ✅ File DXF trovati in {dxf_dir}: {len(dxf_files)}")
            else:
                print(f"  ⚠️ Nessun file DXF in {dxf_dir}")
                
    except Exception as e:
        print(f"  ⚠️ Errore durante demo: {e}")
    
    print("\n🎯 Test completato!")
    print("\n📊 RISULTATO STRUTTURA OUTPUT:")
    
    # Mostra struttura finale
    output_base = "output"
    if os.path.exists(output_base):
        for root, dirs, files in os.walk(output_base):
            level = root.replace(output_base, '').count(os.sep)
            indent = ' ' * 2 * level
            print(f"{indent}{os.path.basename(root)}/")
            subindent = ' ' * 2 * (level + 1)
            for file in files[:5]:  # Mostra max 5 file per cartella
                print(f"{subindent}{file}")
            if len(files) > 5:
                print(f"{subindent}... e altri {len(files) - 5} file")

if __name__ == "__main__":
    test_output_organization()

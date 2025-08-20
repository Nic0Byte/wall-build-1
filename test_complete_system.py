"""
Test completo del nuovo sistema di parsing con fallback intelligente.
"""

import main
import os
from pathlib import Path


def test_parsing_system():
    """Test del sistema di parsing con tutti i file disponibili."""
    
    print("🧪 TEST SISTEMA PARSING COMPLETO")
    print("=" * 50)
    
    # File di test
    test_files = {
        "test_parete_semplice.svg": "SVG semplice",
        "test_parete_difficile.svg": "SVG complesso", 
        "test_parete_dwg.dwg": "DWG test (compatibile)",
        "ROTTINI_LAY_REV0.dwg": "DWG reale (AC1032)",
        "FELICE_LAY_REV0.dwg": "DWG reale (AC1032)"
    }
    
    results = {}
    
    for filename, description in test_files.items():
        filepath = Path(filename)
        
        if not filepath.exists():
            print(f"⏭️  {filename}: File non trovato")
            continue
            
        print(f"\n📁 Test: {filename} ({description})")
        print("-" * 40)
        
        try:
            # Leggi file
            with open(filepath, 'rb') as f:
                file_bytes = f.read()
            
            print(f"📊 Dimensione file: {len(file_bytes):,} bytes")
            
            # Test parsing
            parete, aperture = main.parse_wall_file(
                file_bytes, 
                filename,
                layer_wall="MURO", 
                layer_holes="BUCHI"
            )
            
            # Analizza risultato
            area_parete = parete.area if hasattr(parete, 'area') else 0
            num_aperture = len(aperture) if aperture else 0
            
            print(f"✅ SUCCESSO!")
            print(f"   📐 Area parete: {area_parete:,.0f} mm²")
            print(f"   🔳 Aperture: {num_aperture}")
            print(f"   📏 Bounds: {parete.bounds}")
            
            results[filename] = {
                'success': True,
                'area': area_parete,
                'apertures': num_aperture,
                'bounds': parete.bounds
            }
            
        except Exception as e:
            print(f"❌ FALLIMENTO: {e}")
            results[filename] = {
                'success': False,
                'error': str(e)
            }
    
    # Riassunto finale
    print("\n" + "=" * 50)
    print("📊 RIASSUNTO TEST")
    print("=" * 50)
    
    successi = sum(1 for r in results.values() if r.get('success', False))
    totale = len(results)
    
    print(f"✅ Successi: {successi}/{totale}")
    
    if successi > 0:
        print("\n🎯 File elaborati con successo:")
        for filename, result in results.items():
            if result.get('success'):
                area = result['area']
                aperture = result['apertures']
                print(f"   • {filename}: {area:,.0f}mm² con {aperture} aperture")
    
    if successi < totale:
        print("\n⚠️  File con problemi:")
        for filename, result in results.items():
            if not result.get('success'):
                print(f"   • {filename}: {result['error']}")
    
    return results


def test_header_analysis():
    """Test analisi header DWG."""
    print("\n🔍 TEST ANALISI HEADER DWG")
    print("=" * 30)
    
    dwg_files = ["ROTTINI_LAY_REV0.dwg", "FELICE_LAY_REV0.dwg"]
    
    for filename in dwg_files:
        filepath = Path(filename)
        if not filepath.exists():
            continue
            
        with open(filepath, 'rb') as f:
            file_bytes = f.read()
        
        # Analizza header
        header_info = main._analyze_dwg_header(file_bytes)
        
        print(f"\n📄 {filename}:")
        print(f"   🔧 Formato: {header_info['format']}")
        print(f"   📅 Versione: {header_info['version']}")
        print(f"   ✅ Compatibile: {header_info['compatible']}")
        print(f"   📁 È CAD: {header_info['is_cad']}")


if __name__ == "__main__":
    # Test completo
    test_header_analysis()
    results = test_parsing_system()
    
    print(f"\n🏁 Test completato! Risultati: {len(results)} file testati")

#!/usr/bin/env python3
"""
Test diretto dell'algoritmo pack_wall per verificare se usa dimensioni custom.
"""

import sys
import os

# Aggiungi il path del modulo
sys.path.insert(0, os.getcwd())

from main import pack_wall, parse_svg_wall
from shapely.geometry import Polygon

def test_pack_wall_dimensions():
    """Test diretto della funzione pack_wall con dimensioni diverse"""
    
    # Carica il file SVG di test
    with open('test_parete_semplice_custom.svg', 'r', encoding='utf-8') as f:
        svg_content = f.read()
    
    wall_polygon, apertures = parse_svg_wall(svg_content)
    print(f"🏠 Wall area: {wall_polygon.area/1000000:.1f} m²")
    print(f"🚪 Apertures: {len(apertures) if apertures else 0}")
    
    # Test configurazioni diverse
    configs = [
        {
            "name": "Standard TAKTAK",
            "block_widths": [1500, 826, 413],
            "block_height": 495
        },
        {
            "name": "Blocchi Piccoli",
            "block_widths": [800, 600, 400], 
            "block_height": 495
        },
        {
            "name": "Blocchi Grandi",
            "block_widths": [2000, 1000, 500],
            "block_height": 495
        }
    ]
    
    results = []
    
    for config in configs:
        print(f"\n🧪 Testing: {config['name']}")
        print(f"   Dimensioni: {config['block_widths']}×{config['block_height']}")
        
        # Chiama pack_wall direttamente 
        placed, custom = pack_wall(
            wall_polygon,
            config['block_widths'],
            config['block_height'],
            row_offset=826,
            apertures=apertures
        )
        
        # Calcola risultati
        total_blocks = len(placed)
        total_custom = len(custom)
        
        # Controlla se ha usato le dimensioni giuste
        used_widths = set()
        for block in placed:
            used_widths.add(int(block['width']))
        
        print(f"   📊 Risultati:")
        print(f"      Blocchi standard: {total_blocks}")
        print(f"      Pezzi custom: {total_custom}")
        print(f"      Larghezze usate: {sorted(used_widths)}")
        print(f"      Larghezze attese: {sorted(config['block_widths'])}")
        
        # Verifica se ha usato le dimensioni corrette
        expected_widths = set(config['block_widths'])
        if used_widths == expected_widths:
            print(f"      ✅ Dimensioni corrette!")
        elif used_widths.issubset({1239, 826, 413}):
            print(f"      ❌ Usa ancora dimensioni standard hardcoded!")
        else:
            print(f"      ⚠️ Dimensioni parzialmente corrette")
        
        results.append({
            'name': config['name'],
            'blocks': total_blocks,
            'custom': total_custom,
            'used_widths': used_widths,
            'expected_widths': expected_widths
        })
    
    # Confronto finale
    print(f"\n📈 CONFRONTO RISULTATI:")
    print("=" * 60)
    for r in results:
        correct = "✅" if r['used_widths'] == r['expected_widths'] else "❌"
        print(f"{r['name']:15} | Blocks: {r['blocks']:3d} | Custom: {r['custom']:2d} | {correct}")
    
    # Verifica differenze
    block_counts = [r['blocks'] for r in results]
    all_same = len(set(block_counts)) == 1
    
    if all_same:
        print(f"\n❌ PROBLEMA: Tutte le configurazioni danno lo stesso numero di blocchi!")
        print(f"   Questo indica che le dimensioni custom non vengono usate.")
    else:
        print(f"\n✅ SUCCESS: Configurazioni diverse danno risultati diversi!")
        print(f"   Le dimensioni custom funzionano correttamente.")
    
    return results

if __name__ == "__main__":
    test_pack_wall_dimensions()

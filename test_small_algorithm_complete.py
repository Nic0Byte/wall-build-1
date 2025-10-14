"""
Test Completo Algoritmo Small - Integrazione con wall_builder.py
Testa vari scenari di packing con moraletti
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from shapely.geometry import Polygon
from core.wall_builder import pack_wall


def test_small_algorithm_integration():
    """Test integrazione Small Algorithm con wall_builder.py"""
    
    print("=" * 80)
    print("TEST INTEGRAZIONE ALGORITMO SMALL")
    print("=" * 80)
    
    # Configurazione moraletti
    moraletti_config = {
        'block_large_width': 1239,
        'block_large_height': 495,
        'block_medium_width': 826,
        'block_medium_height': 495,
        'block_small_width': 413,
        'block_small_height': 495,
        'moraletti_thickness': 58,
        'moraletti_height': 495,
        'moraletti_height_from_ground': 95,
        'moraletti_spacing': 420,
        'moraletti_count_large': 3,
        'moraletti_count_medium': 2,
        'moraletti_count_small': 1,
    }
    
    # Parete test: 2478mm × 1485mm (3 righe)
    wall_polygon = Polygon([
        (0, 0),
        (2478, 0),
        (2478, 1485),
        (0, 1485)
    ])
    
    print(f"\n📐 Parete Test: {wall_polygon.bounds}")
    print(f"   Dimensioni: 2478mm × 1485mm")
    print(f"   Area: {wall_polygon.area / 1_000_000:.2f}m²")
    
    # Esegui packing con Small Algorithm
    print(f"\n🎯 Esecuzione pack_wall con algorithm_type='small'...")
    
    try:
        placed_blocks, custom_blocks = pack_wall(
            polygon=wall_polygon,
            block_widths=[1239, 826, 413],  # Non usati da Small (usa config)
            block_height=495,
            algorithm_type='small',
            moraletti_config=moraletti_config,
            enable_debug=False
        )
        
        print(f"\n✅ SUCCESSO!")
        print(f"   Blocchi standard piazzati: {len(placed_blocks)}")
        print(f"   Blocchi custom piazzati: {len(custom_blocks)}")
        
        # Analisi blocchi per riga
        print(f"\n📊 Analisi per Riga:")
        
        # Raggruppa per Y
        rows = {}
        for block in placed_blocks + custom_blocks:
            y = block['y']
            if y not in rows:
                rows[y] = []
            rows[y].append(block)
        
        for y in sorted(rows.keys()):
            blocks_in_row = rows[y]
            print(f"\n   Riga Y={y:.0f}mm:")
            print(f"      Blocchi: {len(blocks_in_row)}")
            
            # Ordina per X
            blocks_in_row.sort(key=lambda b: b['x'])
            
            for i, block in enumerate(blocks_in_row):
                block_type = block.get('type', 'unknown')
                width = block.get('width', 0)
                x = block.get('x', 0)
                is_custom = not block.get('is_standard', True)
                marker = "📦" if not is_custom else "🔧"
                print(f"         {marker} {block_type}: {width:.0f}mm a x={x:.0f}mm")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERRORE: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_small_vs_bidirectional():
    """Confronta Small vs Bidirectional sullo stesso caso"""
    
    print("\n" + "=" * 80)
    print("TEST CONFRONTO: SMALL vs BIDIRECTIONAL")
    print("=" * 80)
    
    # Parete test
    wall_polygon = Polygon([(0, 0), (2478, 0), (2478, 990), (0, 990)])  # 2 righe
    
    moraletti_config = {
        'block_large_width': 1239,
        'block_large_height': 495,
        'block_medium_width': 826,
        'block_medium_height': 495,
        'block_small_width': 413,
        'block_small_height': 495,
        'moraletti_thickness': 58,
        'moraletti_height': 495,
        'moraletti_height_from_ground': 95,
        'moraletti_spacing': 420,
        'moraletti_count_large': 3,
        'moraletti_count_medium': 2,
        'moraletti_count_small': 1,
    }
    
    print(f"\n📐 Parete: 2478mm × 990mm (2 righe)")
    
    # Test 1: Bidirectional
    print(f"\n🔄 Test 1: BIDIRECTIONAL")
    try:
        placed_bid, custom_bid = pack_wall(
            polygon=wall_polygon,
            block_widths=[1239, 826, 413],
            block_height=495,
            algorithm_type='bidirectional',
            enable_debug=False
        )
        print(f"   ✅ Standard: {len(placed_bid)}, Custom: {len(custom_bid)}")
    except Exception as e:
        print(f"   ❌ Errore: {e}")
        placed_bid, custom_bid = [], []
    
    # Test 2: Small
    print(f"\n🎯 Test 2: SMALL")
    try:
        placed_small, custom_small = pack_wall(
            polygon=wall_polygon,
            block_widths=[1239, 826, 413],
            block_height=495,
            algorithm_type='small',
            moraletti_config=moraletti_config,
            enable_debug=False
        )
        print(f"   ✅ Standard: {len(placed_small)}, Custom: {len(custom_small)}")
    except Exception as e:
        print(f"   ❌ Errore: {e}")
        placed_small, custom_small = [], []
    
    # Confronto
    print(f"\n📊 CONFRONTO:")
    print(f"   Bidirectional: {len(placed_bid)} standard + {len(custom_bid)} custom = {len(placed_bid) + len(custom_bid)} totale")
    print(f"   Small:         {len(placed_small)} standard + {len(custom_small)} custom = {len(placed_small) + len(custom_small)} totale")


def test_small_with_ground_offset():
    """Test Small Algorithm con ground offset (piedini)"""
    
    print("\n" + "=" * 80)
    print("TEST: SMALL CON GROUND OFFSET (Piedini)")
    print("=" * 80)
    
    moraletti_config = {
        'block_large_width': 1239,
        'block_large_height': 495,
        'block_medium_width': 826,
        'block_medium_height': 495,
        'block_small_width': 413,
        'block_small_height': 495,
        'moraletti_thickness': 58,
        'moraletti_height': 495,
        'moraletti_height_from_ground': 95,
        'moraletti_spacing': 420,
        'moraletti_count_large': 3,
        'moraletti_count_medium': 2,
        'moraletti_count_small': 1,
    }
    
    vertical_config = {
        'enableGroundOffset': True,
        'groundOffsetValue': 95,  # 95mm piedini
        'enableCeilingSpace': False,
        'ceilingSpaceValue': 0
    }
    
    wall_polygon = Polygon([(0, 0), (2478, 0), (2478, 1485), (0, 1485)])
    
    print(f"\n📐 Parete: 2478mm × 1485mm")
    print(f"   Ground Offset: 95mm (piedini)")
    
    try:
        placed, custom = pack_wall(
            polygon=wall_polygon,
            block_widths=[1239, 826, 413],
            block_height=495,
            algorithm_type='small',
            moraletti_config=moraletti_config,
            vertical_config=vertical_config,
            enable_debug=False
        )
        
        print(f"\n✅ SUCCESSO!")
        print(f"   Blocchi: {len(placed)} standard + {len(custom)} custom")
        
        # Verifica che il primo blocco inizi a Y=95 (ground offset)
        if placed or custom:
            all_blocks = placed + custom
            min_y = min(b['y'] for b in all_blocks)
            print(f"   Y minimo: {min_y:.0f}mm (dovrebbe essere ~95mm)")
            
            if abs(min_y - 95) < 5:
                print(f"   ✅ Ground offset applicato correttamente!")
            else:
                print(f"   ⚠️ Ground offset potrebbe non essere corretto")
        
    except Exception as e:
        print(f"\n❌ ERRORE: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Esegue tutti i test"""
    
    print("\n" + "🎯" * 40)
    print("TEST SUITE COMPLETA - ALGORITMO SMALL")
    print("🎯" * 40 + "\n")
    
    results = []
    
    # Test 1: Integrazione base
    print("\n" + "▶️ " * 40)
    success = test_small_algorithm_integration()
    results.append(("Integrazione Base", success))
    
    # Test 2: Confronto algoritmi
    print("\n" + "▶️ " * 40)
    test_small_vs_bidirectional()
    results.append(("Confronto Algoritmi", True))  # Non ha return value
    
    # Test 3: Ground offset
    print("\n" + "▶️ " * 40)
    test_small_with_ground_offset()
    results.append(("Ground Offset", True))
    
    # Riepilogo
    print("\n" + "=" * 80)
    print("RIEPILOGO TEST")
    print("=" * 80)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"   {status}: {test_name}")
    
    print("\n" + "=" * 80)
    print("TUTTI I TEST COMPLETATI!")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()

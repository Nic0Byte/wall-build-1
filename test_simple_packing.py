"""
Test semplificato dell'algoritmo sui file SVG convertiti.
"""

import main
from pathlib import Path


def test_simple_packing():
    """Test semplice dell'algoritmo sui file SVG."""
    
    print("🧪 TEST ALGORITMO SEMPLIFICATO")
    print("=" * 40)
    
    files = ["ROTTINI_LAY_REV0.svg", "FELICE_LAY_REV0.svg"]
    
    for filename in files:
        if not Path(filename).exists():
            print(f"⏭️ {filename}: File non trovato")
            continue
            
        print(f"\n📁 Test: {filename}")
        print("-" * 30)
        
        try:
            # 1. Parse SVG
            with open(filename, 'rb') as f:
                svg_bytes = f.read()
            
            parete, aperture = main.parse_wall_file(svg_bytes, filename)
            
            print(f"✅ Parse: {parete.area:,.0f} mm², {len(aperture)} aperture")
            print(f"📏 Bounds: {parete.bounds}")
            
            # 2. Packing
            placed_blocks, custom_pieces = main.pack_wall(
                parete,
                [1239, 826, 413],  # block_widths
                413,               # block_height  
                row_offset=826,
                apertures=aperture
            )
            
            print(f"🧱 Blocchi standard: {len(placed_blocks)}")
            print(f"✂️ Pezzi custom: {len(custom_pieces)}")
            
            # 3. Controllo se ci sono blocchi fuori parete
            problems = 0
            
            for i, block in enumerate(placed_blocks):
                x = block.get('x', 0)
                y = block.get('y', 0) 
                w = block.get('width', 0)
                h = block.get('height', 0)
                
                # Controllo semplice: blocco completamente dentro bounds
                bounds = parete.bounds
                if (x < bounds[0] or y < bounds[1] or 
                    x + w > bounds[2] or y + h > bounds[3]):
                    problems += 1
                    if problems <= 3:  # Mostra solo primi 3
                        print(f"   ⚠️ Blocco {i}: ({x}, {y}) {w}×{h} fuori bounds")
            
            if problems == 0:
                print("✅ Tutti i blocchi dentro la parete")
            else:
                print(f"❌ {problems} blocchi potenzialmente fuori parete")
                
        except Exception as e:
            print(f"❌ Errore: {e}")
    
    print(f"\n🏁 Test completato!")


if __name__ == "__main__":
    test_simple_packing()

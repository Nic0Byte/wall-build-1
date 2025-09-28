#!/usr/bin/env python3
"""
Test dell'algoritmo di packing ottimizzato con logica "a mattoncino"
"""

from shapely.geometry import Polygon
from core.wall_builder import pack_wall

def test_optimized_packing():
    """Test della logica ottimizzata"""
    
    print("🧱 TEST ALGORITMO PACKING OTTIMIZZATO")
    print("=" * 50)
    
    # Parete rettangolare semplice: 6000mm x 2000mm
    wall = Polygon([(0, 0), (6000, 0), (6000, 2000), (0, 2000)])
    
    # Blocchi configurabili
    block_widths = [3000, 1500, 700]  # Grande, Medio, Piccolo
    block_height = 495  # Altezza costante
    row_offset = 1500   # Offset righe dispari = blocco medio
    
    print(f"📐 Parete: {wall.bounds}")
    print(f"📦 Blocchi disponibili: {block_widths} mm")
    print(f"📏 Altezza blocchi: {block_height} mm") 
    print(f"↔️ Offset righe dispari: {row_offset} mm")
    print()
    
    # Esegui packing
    placed, custom = pack_wall(
        wall, 
        block_widths, 
        block_height, 
        row_offset=row_offset
    )
    
    print("🎯 RISULTATI:")
    print(f"   🧱 Blocchi standard: {len(placed)}")
    print(f"   ✂️ Pezzi custom: {len(custom)}")
    print()
    
    # Analisi righe per verificare alternanza
    print("📊 ANALISI RIGHE (logica mattoncino):")
    rows = {}
    for i, block in enumerate(placed):
        row = int(block['y'] // block_height)
        if row not in rows:
            rows[row] = []
        rows[row].append((block['x'], block['width']))
    
    for row_num in sorted(rows.keys()):
        blocks_in_row = sorted(rows[row_num])
        row_type = "PARI" if row_num % 2 == 0 else "DISPARI"
        first_x = blocks_in_row[0][0] if blocks_in_row else 0
        print(f"   Riga {row_num} ({row_type}): inizio x={first_x}, blocchi={len(blocks_in_row)}")
        for x, w in blocks_in_row[:3]:  # primi 3 blocchi
            print(f"      → x={x}, width={w}")
    print()
    
    # Analisi custom pieces per verificare ottimizzazione spreco
    if custom:
        print("✂️ ANALISI CUSTOM PIECES (spreco ottimizzato):")
        total_waste = 0
        for i, piece in enumerate(custom):
            if 'source_block_width' in piece and 'waste' in piece:
                print(f"   Custom {i+1}: {piece['width']}mm da {piece['source_block_width']}mm → spreco: {piece['waste']}mm")
                total_waste += piece['waste']
            else:
                print(f"   Custom {i+1}: {piece['width']}mm (ottimizzazione non applicata)")
        print(f"   💰 SPRECO TOTALE: {total_waste}mm")
    
    return placed, custom

if __name__ == "__main__":
    test_optimized_packing()
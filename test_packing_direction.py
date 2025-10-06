#!/usr/bin/env python3
"""
Test per verificare che l'algoritmo di packing rispetti la direzione starting_direction.
Questo test verifica che tutte le righe seguano la stessa direzione.
"""

import sys
import io
from contextlib import redirect_stdout

from shapely.geometry import Polygon
from core.wall_builder import pack_wall

def test_packing_direction():
    """Test della direzione di packing uniforme"""
    
    print("=" * 80)
    print("TEST DIREZIONE PACKING UNIFORME")
    print("=" * 80)
    
    # Parete rettangolare semplice: 6000mm x 2000mm
    wall = Polygon([(0, 0), (6000, 0), (6000, 2000), (0, 2000)])
    
    # Blocchi configurabili
    block_widths = [1239, 826, 413]
    block_height = 413
    
    print(f"\nParete: {wall.bounds}")
    print(f"Blocchi disponibili: {block_widths} mm")
    print(f"Altezza blocchi: {block_height} mm\n")
    
    # Test 1: Direzione LEFT (tutte le righe da sinistra)
    print("\n" + "=" * 80)
    print("TEST 1: starting_direction='left' - TUTTE LE RIGHE DA SINISTRA")
    print("=" * 80 + "\n")
    
    # Suppress verbose output from pack_wall
    with redirect_stdout(io.StringIO()):
        placed_left, custom_left = pack_wall(
            wall, 
            block_widths, 
            block_height,
            starting_direction='left'
        )
    
    # Analizza righe per verificare che partano da sinistra
    print("Analisi righe (partenza da SINISTRA):")
    rows_left = {}
    for block in placed_left:
        row = int(block['y'] // block_height)
        if row not in rows_left:
            rows_left[row] = []
        rows_left[row].append(block['x'])
    
    all_left_ok = True
    for row_num in sorted(rows_left.keys()):
        first_x = min(rows_left[row_num])
        status = "OK" if first_x < 100 else "FAIL"
        print(f"  Riga {row_num}: primo blocco a x={first_x:.0f} (dovrebbe essere ~0) [{status}]")
        if first_x >= 100:
            all_left_ok = False
    
    if all_left_ok:
        print(f"\n✓ PASSED: Tutte le {len(rows_left)} righe partono da SINISTRA")
        print(f"   Blocchi standard: {len(placed_left)}")
        print(f"   Pezzi custom: {len(custom_left)}")
    else:
        print("\n✗ FAILED: Alcune righe non partono da sinistra!")
        sys.exit(1)
    
    # Test 2: Direzione RIGHT (tutte le righe da destra)
    print("\n" + "=" * 80)
    print("TEST 2: starting_direction='right' - TUTTE LE RIGHE DA DESTRA")
    print("=" * 80 + "\n")
    
    # Suppress verbose output from pack_wall
    with redirect_stdout(io.StringIO()):
        placed_right, custom_right = pack_wall(
            wall, 
            block_widths, 
            block_height,
            starting_direction='right'
        )
    
    # Analizza righe per verificare che partano da destra
    print("Analisi righe (partenza da DESTRA):")
    rows_right = {}
    wall_width = 6000
    for block in placed_right:
        row = int(block['y'] // block_height)
        if row not in rows_right:
            rows_right[row] = []
        right_edge = block['x'] + block['width']
        rows_right[row].append(right_edge)
    
    all_right_ok = True
    for row_num in sorted(rows_right.keys()):
        last_right = max(rows_right[row_num])
        status = "OK" if last_right > wall_width - 100 else "FAIL"
        print(f"  Riga {row_num}: ultimo blocco termina a x={last_right:.0f} (dovrebbe essere ~{wall_width}) [{status}]")
        if last_right <= wall_width - 100:
            all_right_ok = False
    
    if all_right_ok:
        print(f"\n✓ PASSED: Tutte le {len(rows_right)} righe arrivano a DESTRA")
        print(f"   Blocchi standard: {len(placed_right)}")
        print(f"   Pezzi custom: {len(custom_right)}")
    else:
        print("\n✗ FAILED: Alcune righe non arrivano a destra!")
        sys.exit(1)
    
    # Confronto
    print("\n" + "=" * 80)
    print("CONFRONTO TRA LE DUE DIREZIONI")
    print("=" * 80)
    
    print(f"\nDirezione LEFT:  Blocchi={len(placed_left)}, Custom={len(custom_left)}")
    print(f"Direzione RIGHT: Blocchi={len(placed_right)}, Custom={len(custom_right)}")
    
    diff = abs(len(placed_left) - len(placed_right))
    print(f"\nDifferenza numero blocchi: {diff}")
    
    print("\n" + "=" * 80)
    print("✓ TUTTI I TEST COMPLETATI CON SUCCESSO!")
    print("=" * 80)
    print("\nCONCLUSIONE:")
    print("  - Con starting_direction='left': tutte le righe partono da sinistra")
    print("  - Con starting_direction='right': tutte le righe partono da destra")
    print("  - L'algoritmo rispetta correttamente la direzione scelta dall'utente")
    print("=" * 80)


if __name__ == "__main__":
    test_packing_direction()

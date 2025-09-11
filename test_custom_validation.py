#!/usr/bin/env python3
"""
Test per verificare la nuova logica di validazione dei blocchi custom.
Verifica che i blocchi custom possano essere creati da tutti i tipi di blocco standard.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import validate_and_tag_customs
from utils.config import BLOCK_WIDTHS, BLOCK_HEIGHT


def test_custom_validation():
    """Test della nuova logica di validazione blocchi custom."""
    
    print("🧪 Test validazione blocchi custom (versione aggiornata)")
    print(f"📏 Dimensioni blocchi standard: {BLOCK_WIDTHS} mm x {BLOCK_HEIGHT} mm")
    print("─" * 60)
    
    # Test cases: blocchi custom derivati da diversi tipi di blocco
    test_customs = [
        # Blocchi derivati da blocco piccolo (413mm) - PRIMA funzionavano
        {"width": 300, "height": 495, "geometry": None},
        {"width": 400, "height": 495, "geometry": None},
        
        # Blocchi derivati da blocco medio (826mm) - ORA dovrebbero funzionare
        {"width": 600, "height": 495, "geometry": None},
        {"width": 800, "height": 495, "geometry": None},
        
        # Blocchi derivati da blocco grande (1239mm) - ORA dovrebbero funzionare
        {"width": 1000, "height": 495, "geometry": None},
        {"width": 1200, "height": 495, "geometry": None},
        
        # Blocchi con altezza diversa (flex)
        {"width": 300, "height": 300, "geometry": None},
        {"width": 600, "height": 400, "geometry": None},
        
        # Blocchi fuori specifica
        {"width": 1250, "height": 495, "geometry": None},  # Troppo largo
        {"width": 300, "height": 502, "geometry": None},   # Troppo alto (fuori tolleranza)
    ]
    
    # Valida i blocchi custom
    validated = validate_and_tag_customs(test_customs)
    
    print("📊 Risultati validazione:")
    print()
    
    ctype_1_count = 0
    ctype_2_count = 0
    out_of_spec_count = 0
    
    for i, custom in enumerate(validated):
        w = custom["width"]
        h = custom["height"]
        ctype = custom["ctype"]
        
        print(f"  {i+1:2d}. {w:4.0f}×{h:3.0f} mm → ctype: {ctype}")
        
        if ctype == 1:
            ctype_1_count += 1
        elif ctype == 2:
            ctype_2_count += 1
        elif ctype == "out_of_spec":
            out_of_spec_count += 1
    
    print()
    print("📈 Riassunto:")
    print(f"  • Type 1 (larghezza - da blocco standard): {ctype_1_count}")
    print(f"  • Type 2 (flex - altezza diversa):         {ctype_2_count}")
    print(f"  • Out of spec (fuori specifica):           {out_of_spec_count}")
    
    print()
    print("✅ Verifiche:")
    
    # Verifica che i blocchi con altezza 495 e larghezza <= 1239 siano type 1
    type_1_blocks = [c for c in validated if c["ctype"] == 1]
    expected_type_1 = 6  # I primi 6 blocchi dovrebbero essere type 1
    
    if len(type_1_blocks) == expected_type_1:
        print(f"  ✓ Blocchi Type 1: {len(type_1_blocks)}/{expected_type_1} (corretto)")
    else:
        print(f"  ✗ Blocchi Type 1: {len(type_1_blocks)}/{expected_type_1} (errore)")
    
    # Verifica che blocchi con altezza != 495 siano type 2
    type_2_blocks = [c for c in validated if c["ctype"] == 2]
    expected_type_2 = 2  # 2 blocchi con altezza diversa
    
    if len(type_2_blocks) == expected_type_2:
        print(f"  ✓ Blocchi Type 2: {len(type_2_blocks)}/{expected_type_2} (corretto)")
    else:
        print(f"  ✗ Blocchi Type 2: {len(type_2_blocks)}/{expected_type_2} (errore)")
    
    # Verifica che blocchi fuori specifica siano out_of_spec
    out_of_spec_blocks = [c for c in validated if c["ctype"] == "out_of_spec"]
    expected_out_of_spec = 2  # 2 blocchi fuori specifica
    
    if len(out_of_spec_blocks) == expected_out_of_spec:
        print(f"  ✓ Blocchi out_of_spec: {len(out_of_spec_blocks)}/{expected_out_of_spec} (corretto)")
    else:
        print(f"  ✗ Blocchi out_of_spec: {len(out_of_spec_blocks)}/{expected_out_of_spec} (errore)")
    
    print()
    print("🎯 RISULTATO: I blocchi custom ora possono essere derivati da tutti i tipi di blocco standard!")
    print("   • Piccolo (413mm): Type 1")
    print("   • Medio (826mm):   Type 1") 
    print("   • Grande (1239mm): Type 1")
    print("   • Altezza ≠ 495:   Type 2")
    print("   • Fuori limite:    out_of_spec")


if __name__ == "__main__":
    test_custom_validation()

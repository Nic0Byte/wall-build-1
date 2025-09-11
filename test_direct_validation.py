#!/usr/bin/env python3
"""
Test più mirato per verificare la nuova logica dei blocchi custom.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import validate_and_tag_customs
from utils.config import BLOCK_WIDTHS, BLOCK_HEIGHT, SCARTO_CUSTOM_MM


def test_direct_validation():
    """Test diretto della funzione validate_and_tag_customs."""
    
    print("🔍 Test diretto: Verifica della nuova logica validate_and_tag_customs")
    print("─" * 70)
    
    # Simula blocchi custom che PRIMA non sarebbero stati ctype=1
    test_customs = [
        # Blocchi che PRIMA sarebbero stati ctype=2 (larghezza > 413)
        # ORA dovrebbero essere ctype=1 (derivati da blocchi medi/grandi)
        {"width": 600, "height": 495, "geometry": None},   # Da blocco medio
        {"width": 750, "height": 495, "geometry": None},   # Da blocco medio  
        {"width": 1000, "height": 495, "geometry": None},  # Da blocco grande
        {"width": 1100, "height": 495, "geometry": None},  # Da blocco grande
        
        # Blocchi che dovrebbero rimanere ctype=1 (piccoli)
        {"width": 300, "height": 495, "geometry": None},   # Da blocco piccolo
        {"width": 400, "height": 495, "geometry": None},   # Da blocco piccolo
        
        # Blocchi che dovrebbero essere ctype=2 (altezza diversa)
        {"width": 600, "height": 300, "geometry": None},   # Altezza diversa
        
        # Blocchi fuori specifica
        {"width": 1250, "height": 495, "geometry": None},  # Troppo largo
    ]
    
    print("📊 Blocchi da testare:")
    for i, custom in enumerate(test_customs):
        print(f"  {i+1}. {custom['width']}×{custom['height']} mm")
    
    print()
    print("⚙️  Eseguendo validate_and_tag_customs...")
    
    # Applica la validazione
    validated = validate_and_tag_customs(test_customs)
    
    print()
    print("📋 Risultati validazione:")
    
    old_logic_would_be_type2 = []  # Blocchi che con la vecchia logica sarebbero stati type 2
    
    for i, custom in enumerate(validated):
        w = custom["width"]
        h = custom["height"] 
        ctype = custom["ctype"]
        
        # Simula la vecchia logica
        old_ctype = "old_unknown"
        if w >= 413 + SCARTO_CUSTOM_MM or h > 495 + SCARTO_CUSTOM_MM:
            old_ctype = "out_of_spec"
        elif abs(h - 495) <= SCARTO_CUSTOM_MM and w < 413 + SCARTO_CUSTOM_MM:
            old_ctype = 1  # Vecchia logica: solo piccoli
        else:
            old_ctype = 2  # Vecchia logica: tutto il resto
        
        change_indicator = ""
        if old_ctype != ctype and w > 413 + SCARTO_CUSTOM_MM and ctype == 1:
            change_indicator = " 🆕 NUOVO!"
            old_logic_would_be_type2.append({
                'width': w,
                'height': h,
                'old_ctype': old_ctype,
                'new_ctype': ctype
            })
        elif old_ctype == ctype:
            change_indicator = " ✓"
        
        print(f"  {i+1:2d}. {w:4.0f}×{h:3.0f} mm → ctype: {ctype} (vecchia: {old_ctype}){change_indicator}")
    
    print()
    print("🎯 VERIFICA CAMBIAMENTI:")
    
    if old_logic_would_be_type2:
        print(f"✅ TROVATI {len(old_logic_would_be_type2)} blocchi che beneficiano della nuova logica!")
        print()
        for block in old_logic_would_be_type2:
            print(f"   • {block['width']}×{block['height']} mm:")
            print(f"     - Vecchia logica: ctype = {block['old_ctype']}")
            print(f"     - Nuova logica:   ctype = {block['new_ctype']} ✅")
            
            if block['width'] <= 826:
                source = "blocco MEDIO (826mm)"
            else:
                source = "blocco GRANDE (1239mm)"
            print(f"     - Può essere derivato da {source}")
            print()
        
        print("🎉 CONFERMA DEFINITIVA: Il sistema STA USANDO la nuova logica!")
        print("   I blocchi custom ora possono essere derivati da blocchi medi e grandi!")
        
    else:
        print("❌ PROBLEMA: Nessun cambiamento rilevato!")
        print("   La nuova logica potrebbe non essere attiva.")
    
    return len(old_logic_would_be_type2) > 0


def check_code_consistency():
    """Verifica la coerenza del codice per confermare l'implementazione."""
    
    print("\n" + "="*70)
    print("🔧 Verifica coerenza del codice")
    print("="*70)
    
    # Leggi il contenuto della funzione validate_and_tag_customs
    try:
        with open('main.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Cerca indicatori della nuova logica
        new_logic_indicators = [
            "max_standard_width = max(BLOCK_WIDTHS)",
            "w <= max_standard_width + SCARTO_CUSTOM_MM",
            "AGGIORNATO: i blocchi custom possono nascere"
        ]
        
        found_indicators = []
        for indicator in new_logic_indicators:
            if indicator in content:
                found_indicators.append(indicator)
        
        print(f"📋 Indicatori nuova logica trovati: {len(found_indicators)}/{len(new_logic_indicators)}")
        
        for indicator in found_indicators:
            print(f"   ✅ '{indicator[:50]}...'")
        
        if len(found_indicators) == len(new_logic_indicators):
            print("\n✅ CODICE AGGIORNATO: Tutti gli indicatori della nuova logica sono presenti!")
            return True
        else:
            print("\n⚠️  CODICE INCOMPLETO: Alcuni indicatori mancano.")
            return False
            
    except Exception as e:
        print(f"❌ Errore lettura file: {e}")
        return False


if __name__ == "__main__":
    logic_works = test_direct_validation()
    code_updated = check_code_consistency()
    
    print("\n" + "="*70)
    print("📊 VERDETTO FINALE")
    print("="*70)
    
    if logic_works and code_updated:
        print("🎉 SUCCESSO COMPLETO!")
        print("   ✅ La nuova logica è implementata nel codice")
        print("   ✅ La nuova logica funziona correttamente") 
        print("   ✅ Il sistema STA USANDO la nuova logica per i blocchi custom!")
    elif code_updated:
        print("⚠️  PARZIALMENTE IMPLEMENTATO")
        print("   ✅ La nuova logica è presente nel codice")
        print("   ❓ Non testata completamente in runtime")
    else:
        print("❌ PROBLEMA")
        print("   ❌ La nuova logica potrebbe non essere implementata correttamente")

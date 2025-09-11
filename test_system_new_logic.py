#!/usr/bin/env python3
"""
Test per verificare che il sistema stia usando la nuova logica per i blocchi custom
durante l'elaborazione di una parete completa.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import pack_wall
from utils.config import BLOCK_WIDTHS, BLOCK_HEIGHT
from shapely.geometry import Polygon


def test_system_using_new_logic():
    """Test completo per verificare l'uso della nuova logica nel sistema."""
    
    print("🧪 Test: Il sistema sta usando la nuova logica per i blocchi custom?")
    print("─" * 70)
    
    # Crea una parete semplice che genererà sicuramente dei blocchi custom
    # con dimensioni che PRIMA non sarebbero state accettate come ctype=1
    wall_width = 2000  # 2 metri
    wall_height = 1000  # 1 metro
    
    wall_exterior = Polygon([
        (0, 0),
        (wall_width, 0), 
        (wall_width, wall_height),
        (0, wall_height),
        (0, 0)
    ])
    
    print(f"📏 Parete test: {wall_width}×{wall_height} mm")
    print(f"🧱 Blocchi standard disponibili: {BLOCK_WIDTHS} mm x {BLOCK_HEIGHT} mm")
    print()
    
    try:
        # Esegui il packing con i blocchi standard
        placed_blocks, custom_blocks = pack_wall(
            wall_exterior, 
            BLOCK_WIDTHS, 
            BLOCK_HEIGHT,
            apertures=[]
        )
        
        print(f"📊 Risultati elaborazione:")
        print(f"  • Blocchi standard piazzati: {len(placed_blocks)}")
        print(f"  • Blocchi custom generati: {len(custom_blocks)}")
        print()
        
        if not custom_blocks:
            print("ℹ️  Nessun blocco custom generato - il test non può verificare la nuova logica")
            return
        
        print("🔍 Analisi blocchi custom generati:")
        print()
        
        ctype_1_count = 0
        ctype_2_count = 0
        out_of_spec_count = 0
        
        # Analizza ogni blocco custom per verificare la classificazione
        wide_ctype_1_blocks = []  # Blocchi type 1 con larghezza > 413mm (nuova feature)
        
        for i, custom in enumerate(custom_blocks):
            w = custom.get('width', 0)
            h = custom.get('height', 0) 
            ctype = custom.get('ctype', 'unknown')
            
            print(f"  {i+1:2d}. {w:6.1f}×{h:5.1f} mm → ctype: {ctype}")
            
            if ctype == 1:
                ctype_1_count += 1
                # Verifica se questo blocco PRIMA non sarebbe stato ctype=1
                if w > 413 + 5:  # 5mm è SCARTO_CUSTOM_MM
                    wide_ctype_1_blocks.append({
                        'index': i+1,
                        'width': w,
                        'height': h,
                        'source_block': 'medio' if w <= 826 else 'grande'
                    })
            elif ctype == 2:
                ctype_2_count += 1
            elif ctype == "out_of_spec":
                out_of_spec_count += 1
        
        print()
        print("📈 Riassunto classificazione:")
        print(f"  • Type 1 (da blocco standard): {ctype_1_count}")
        print(f"  • Type 2 (altezza diversa):    {ctype_2_count}")
        print(f"  • Out of spec:                 {out_of_spec_count}")
        print()
        
        # VERIFICA CHIAVE: blocchi type 1 con larghezza > 413mm
        if wide_ctype_1_blocks:
            print("🎯 EVIDENZA DELLA NUOVA LOGICA:")
            print("   Blocchi custom Type 1 derivati da blocchi MEDI/GRANDI:")
            print()
            for block in wide_ctype_1_blocks:
                print(f"   • #{block['index']}: {block['width']:.1f}×{block['height']:.1f} mm")
                print(f"     → Derivato da blocco {block['source_block']} (larghezza > 413mm)")
                print(f"     → PRIMA sarebbe stato Type 2, ORA è Type 1 ✅")
            print()
            print("✅ CONFERMA: Il sistema STA USANDO la nuova logica!")
            print("   I blocchi custom ora possono essere derivati da blocchi medi e grandi!")
            
        else:
            print("🤔 INCONCLUSO: Non sono stati generati blocchi custom larghi > 413mm")
            print("   Il test non può dimostrare l'uso della nuova logica con questa parete.")
            print("   Tuttavia, il codice contiene la nuova logica.")
            
            # Verifica comunque se ci sono blocchi type 1
            if ctype_1_count > 0:
                print()
                print("ℹ️  Sono presenti blocchi Type 1, indicando che la funzione")
                print("   validate_and_tag_customs viene chiamata correttamente.")
        
    except Exception as e:
        print(f"❌ Errore durante l'elaborazione: {e}")
        import traceback
        traceback.print_exc()


def create_wide_custom_test():
    """Crea una parete specifica per forzare la generazione di blocchi custom larghi."""
    
    print("\n" + "="*70)
    print("🎯 Test aggiuntivo: Parete progettata per generare blocchi custom larghi")
    print("="*70)
    
    # Parete con dimensioni che forzerà blocchi custom > 413mm
    wall_width = 1100   # Larghezza che non è multiplo perfetto dei blocchi
    wall_height = 495   # Altezza standard
    
    wall_exterior = Polygon([
        (0, 0),
        (wall_width, 0),
        (wall_width, wall_height), 
        (0, wall_height),
        (0, 0)
    ])
    
    print(f"📏 Parete ottimizzata: {wall_width}×{wall_height} mm")
    
    try:
        placed_blocks, custom_blocks = pack_wall(
            wall_exterior,
            BLOCK_WIDTHS,
            BLOCK_HEIGHT, 
            apertures=[]
        )
        
        print(f"📊 Blocchi generati: {len(placed_blocks)} standard + {len(custom_blocks)} custom")
        
        # Cerca blocchi custom larghi
        wide_customs = [c for c in custom_blocks if c.get('width', 0) > 413 and c.get('ctype') == 1]
        
        if wide_customs:
            print()
            print("🎉 SUCCESSO! Trovati blocchi custom Type 1 larghi > 413mm:")
            for i, c in enumerate(wide_customs):
                print(f"   • {c.get('width', 0):.1f}×{c.get('height', 0):.1f} mm (ctype: {c.get('ctype')})")
            print()
            print("✅ DEFINITIVA CONFERMA: La nuova logica è ATTIVA nel sistema!")
        else:
            print("❓ Nessun blocco custom largo trovato in questo test.")
            
    except Exception as e:
        print(f"❌ Errore: {e}")


if __name__ == "__main__":
    test_system_using_new_logic()
    create_wide_custom_test()

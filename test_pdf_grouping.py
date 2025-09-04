#!/usr/bin/env python3

import sys
import os

# Aggiungi il percorso corrente al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from block_grouping import group_blocks_by_category, group_custom_blocks_by_category, create_grouped_block_labels
    print("✅ Modulo block_grouping importato correttamente")
    
    # Test di base
    test_blocks = [
        {'width': 1239, 'height': 495, 'type': '1239'},
        {'width': 1239, 'height': 495, 'type': '1239'},
        {'width': 826, 'height': 495, 'type': '826'},
    ]
    
    grouped = group_blocks_by_category(test_blocks)
    print(f"✅ Raggruppamento funziona: {grouped}")
    
    labels = create_grouped_block_labels(test_blocks, [])
    print(f"✅ Etichette funzionano: {labels}")
    
except Exception as e:
    print(f"❌ Errore nell'importazione: {e}")
    import traceback
    traceback.print_exc()

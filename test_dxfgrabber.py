#!/usr/bin/env python3
try:
    import dxfgrabber
    print('✅ dxfgrabber importato con successo!')
    print(f'Versione: {dxfgrabber.__version__}')
    
    # Test apertura file
    print('🧪 Test lettura ROTTINI_LAY_REV0.dwg...')
    dwg = dxfgrabber.readfile('ROTTINI_LAY_REV0.dwg')
    print('✅ File aperto!')
    print(f'Header version: {dwg.header.get("$ACADVER", "Unknown")}')
    print(f'Layers: {len(dwg.layers)}')
    print(f'Entities: {len(dwg.entities)}')
    
    # Mostra layer
    print("Layer disponibili:")
    for layer in dwg.layers:
        print(f'  - {layer.name}')
        
    # Mostra prime entità
    print("Prime 10 entità:")
    for i, entity in enumerate(dwg.entities[:10]):
        layer_name = getattr(entity, 'layer', 'N/A')
        print(f'  {i+1}. {entity.dxftype} (layer: {layer_name})')
        
    # Cerca layer MURO e BUCHI
    muro_entities = [e for e in dwg.entities if hasattr(e, 'layer') and 'muro' in e.layer.lower()]
    buchi_entities = [e for e in dwg.entities if hasattr(e, 'layer') and 'buchi' in e.layer.lower()]
    
    print(f"\n🔍 Entità layer MURO: {len(muro_entities)}")
    print(f"🔍 Entità layer BUCHI: {len(buchi_entities)}")
        
except ImportError as e:
    print(f'❌ Import error: {e}')
except Exception as e:
    print(f'❌ Errore: {e}')
    import traceback
    traceback.print_exc()

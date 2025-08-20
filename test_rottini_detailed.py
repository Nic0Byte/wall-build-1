#!/usr/bin/env python3
import dxfgrabber

print('🧪 Test lettura ROTTINI_LAY_REV0.dwg...')
dwg = dxfgrabber.readfile('ROTTINI_LAY_REV0.dwg')
print('✅ File letto!')
print(f'Header version: {dwg.header.get("$ACADVER", "Unknown")}')
print(f'Layers: {len(dwg.layers)}')
print(f'Entities: {len(dwg.entities)}')
print()

print('📂 Layer disponibili:')
for layer in dwg.layers:
    print(f'  - {layer.name}')

print()
print('🔍 Prime 10 entità:')
for i, entity in enumerate(dwg.entities[:10]):
    layer_name = getattr(entity, 'layer', 'N/A')
    print(f'  {i+1}. {entity.dxftype} (layer: {layer_name})')

# Cerca layer con MURO o BUCHI
print()
print('🔍 Ricerca layer MURO/BUCHI:')
muro_entities = [e for e in dwg.entities if hasattr(e, 'layer') and 'muro' in e.layer.lower()]
buchi_entities = [e for e in dwg.entities if hasattr(e, 'layer') and 'buchi' in e.layer.lower()]

print(f'Entità con layer MURO: {len(muro_entities)}')
print(f'Entità con layer BUCHI: {len(buchi_entities)}')

# Lista tutti i layer unici
layer_names = set()
for entity in dwg.entities:
    if hasattr(entity, 'layer'):
        layer_names.add(entity.layer)

print(f'Layer unici trovati: {sorted(layer_names)}')

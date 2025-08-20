#!/usr/bin/env python3
"""
Script per creare un file DWG di test con una parete semplice e aperture.
"""

import ezdxf
from ezdxf import colors

# Crea un nuovo documento DXF
doc = ezdxf.new(dxfversion='R2010')
msp = doc.modelspace()

# Crea layer
doc.layers.new(name='MURO', dxfattribs={'color': colors.BLUE})
doc.layers.new(name='BUCHI', dxfattribs={'color': colors.RED})

print("🏗️ Creazione file DWG di test...")

# Disegna il contorno della parete (rettangolo principale)
# Dimensioni: 8000mm x 3000mm (8m x 3m)
wall_points = [
    (0, 0),
    (8000, 0),
    (8000, 3000),
    (0, 3000),
    (0, 0)  # Chiudi il poligono
]

# Crea polilinea per la parete
wall_polyline = msp.add_lwpolyline(wall_points)
wall_polyline.dxf.layer = 'MURO'
wall_polyline.closed = True

# Aggiungi aperture (porte/finestre)
# Porta 1: 1200mm x 2200mm @ posizione (1000, 0)
door1_points = [
    (1000, 0),
    (2200, 0),
    (2200, 2200),
    (1000, 2200),
    (1000, 0)
]

door1_polyline = msp.add_lwpolyline(door1_points)
door1_polyline.dxf.layer = 'BUCHI'
door1_polyline.closed = True

# Finestra 1: 1500mm x 1200mm @ posizione (4000, 800)
window1_points = [
    (4000, 800),
    (5500, 800),
    (5500, 2000),
    (4000, 2000),
    (4000, 800)
]

window1_polyline = msp.add_lwpolyline(window1_points)
window1_polyline.dxf.layer = 'BUCHI'
window1_polyline.closed = True

# Porta 2: 900mm x 2200mm @ posizione (6500, 0)
door2_points = [
    (6500, 0),
    (7400, 0),
    (7400, 2200),
    (6500, 2200),
    (6500, 0)
]

door2_polyline = msp.add_lwpolyline(door2_points)
door2_polyline.dxf.layer = 'BUCHI'
door2_polyline.closed = True

# Aggiungi un cerchio di test
circle = msp.add_circle(center=(3000, 1500), radius=200)
circle.dxf.layer = 'BUCHI'

# Aggiungi testo descrittivo
msp.add_text(
    "Parete Test - 8000x3000mm",
    dxfattribs={
        'layer': 'MURO',
        'height': 200,
        'insert': (100, 3200)
    }
)

# Salva il file
output_file = "test_parete_dwg.dwg"
doc.saveas(output_file)

print(f"✅ File DWG creato: {output_file}")
print("📏 Dimensioni parete: 8000mm x 3000mm")
print("🚪 Aperture:")
print("  - Porta 1: 1200x2200mm @ (1000,0)")
print("  - Finestra: 1500x1200mm @ (4000,800)")
print("  - Porta 2: 900x2200mm @ (6500,0)")
print("  - Cerchio test: R200mm @ (3000,1500)")
print("📂 Layer: MURO (blu), BUCHI (rosso)")

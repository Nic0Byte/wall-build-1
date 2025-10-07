"""
Test rapido per verificare che le aperture vengano sottratte correttamente durante il clipping.
"""

from shapely.geometry import Polygon, box
from shapely.ops import unary_union

# Simula una parete 12000x3500mm
wall = box(0, 0, 12000, 3500)
print(f"Parete originale:")
print(f"  Area: {wall.area:.0f}mm²")
print(f"  Interiors (buchi): {len(wall.interiors)}")
print()

# Simula 2 aperture (finestre)
aperture1 = box(2000, 500, 3000, 2300)  # 1000x1800mm
aperture2 = box(8000, 700, 9200, 2300)  # 1200x1600mm

apertures = [aperture1, aperture2]
print(f"Aperture:")
for i, ap in enumerate(apertures):
    print(f"  Apertura {i+1}: area={ap.area:.0f}mm², bounds={ap.bounds}")
print()

# Filtra aperture (stesso criterio del packing)
wall_area = wall.area
valid_apertures = []

print(f"Filtraggio aperture:")
for i, ap in enumerate(apertures):
    ap_area = ap.area
    area_ratio = ap_area / wall_area
    
    if area_ratio > 0.8:
        print(f"  ❌ Apertura {i+1} SCARTATA: troppo grande ({area_ratio:.1%})")
        continue
    
    if ap_area < 1000:
        print(f"  ❌ Apertura {i+1} SCARTATA: troppo piccola ({ap_area:.0f}mm²)")
        continue
    
    valid_apertures.append(ap)
    print(f"  ✅ Apertura {i+1} VALIDA: {ap_area:.0f}mm² ({area_ratio:.1%})")

print()

# Crea poligono con buchi
if valid_apertures:
    print(f"Creazione poligono con buchi...")
    apertures_union = unary_union(valid_apertures)
    print(f"  Union: type={apertures_union.geom_type}, area={apertures_union.area:.0f}mm²")
    
    wall_with_holes = wall.difference(apertures_union)
    print(f"  Difference: type={wall_with_holes.geom_type}, area={wall_with_holes.area:.0f}mm²")
    
    if wall_with_holes.geom_type == 'Polygon':
        num_holes = len(wall_with_holes.interiors)
        print(f"  🚪 Buchi creati: {num_holes}")
        
        if num_holes > 0:
            for i, interior in enumerate(wall_with_holes.interiors):
                interior_poly = Polygon(interior)
                print(f"     Buco {i+1}: area={interior_poly.area:.0f}mm², bounds={interior_poly.bounds}")
    
    print()
    
    # Test clipping di un blocco che attraversa l'apertura
    # Blocco 1239x495mm che tocca la prima finestra
    test_block = box(2500, 1000, 2500 + 1239, 1000 + 495)
    print(f"Test blocco che attraversa apertura:")
    print(f"  Blocco originale: area={test_block.area:.0f}mm², bounds={test_block.bounds}")
    
    clipped_block = test_block.intersection(wall_with_holes)
    print(f"  Blocco clippato: type={clipped_block.geom_type}, area={clipped_block.area:.0f}mm²")
    
    if not clipped_block.is_empty:
        area_ratio = clipped_block.area / test_block.area
        print(f"  Area rimasta: {area_ratio:.1%}")
        
        if area_ratio < 1.0:
            print(f"  ✅ SUCCESSO! Il blocco è stato tagliato dalla finestra!")
        else:
            print(f"  ❌ ERRORE! Il blocco non è stato tagliato!")
    else:
        print(f"  ⚠️  Blocco completamente dentro l'apertura (eliminato)")

else:
    print(f"Nessuna apertura valida")

print()
print("Test completato!")

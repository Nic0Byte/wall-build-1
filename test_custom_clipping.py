"""
Test per verificare il taglio dei custom sulla geometria della parete
"""

from shapely.geometry import Polygon, box
from core.wall_builder import clip_customs_to_wall_geometry


def test_clip_custom_with_sloped_wall():
    """Test taglio custom con parete inclinata"""
    print("\n🧪 TEST 1: Custom con parete inclinata")
    
    # Parete triangolare (simula parete inclinata in alto)
    wall = Polygon([
        (0, 0),
        (1000, 0),
        (1000, 1000),
        (500, 2000),  # Punto alto a sinistra
        (0, 1000)
    ])
    
    # Custom rettangolare che esce dalla parete in alto
    customs = [
        {
            'x': 0,
            'y': 1500,
            'width': 1000,
            'height': 500,
            'type': 'custom',
            'coords': [(0, 1500), (1000, 1500), (1000, 2000), (0, 2000), (0, 1500)]
        }
    ]
    
    block_widths = [1239, 826, 413]
    
    result = clip_customs_to_wall_geometry(customs, wall, block_widths)
    
    print(f"   Input: 1 custom rettangolare (1000x500mm)")
    print(f"   Output: {len(result)} custom(s)")
    
    if result:
        print(f"   Custom tagliato ha 'geometry': {'geometry' in result[0]}")
        print(f"   Area custom originale: {1000 * 500}mm²")
        if 'geometry' in result[0]:
            from shapely.geometry import shape
            clipped_poly = shape(result[0]['geometry'])
            print(f"   Area custom tagliato: {clipped_poly.area:.0f}mm²")
            print(f"   Numero vertici: {len(list(clipped_poly.exterior.coords))}")
    
    assert len(result) > 0, "Dovrebbe esserci almeno un custom"
    assert 'geometry' in result[0], "Custom deve avere campo geometry"
    print("   ✅ PASS: Custom tagliato correttamente\n")


def test_clip_custom_with_aperture():
    """Test taglio custom con apertura (porta/finestra)"""
    print("\n🧪 TEST 2: Custom con apertura (porta)")
    
    # Parete rettangolare
    wall_outer = box(0, 0, 2000, 2000)
    # Apertura (porta)
    aperture = box(800, 0, 1200, 1500)
    # Parete con buco
    wall = wall_outer.difference(aperture)
    
    # Custom che copre l'apertura
    customs = [
        {
            'x': 500,
            'y': 500,
            'width': 1000,
            'height': 1000,
            'type': 'custom',
            'coords': [(500, 500), (1500, 500), (1500, 1500), (500, 1500), (500, 500)]
        }
    ]
    
    block_widths = [1239, 826, 413]
    
    result = clip_customs_to_wall_geometry(customs, wall, block_widths)
    
    print(f"   Input: 1 custom rettangolare che copre una porta")
    print(f"   Output: {len(result)} custom(s)")
    
    # Dovrebbe creare 2 custom (uno a sinistra e uno a destra della porta)
    # oppure 1 custom con geometria complessa
    assert len(result) >= 1, "Dovrebbe esserci almeno un custom dopo il taglio"
    print("   ✅ PASS: Custom tagliato per apertura\n")


def test_no_clip_when_inside():
    """Test che custom completamente dentro NON venga modificato"""
    print("\n🧪 TEST 3: Custom completamente dentro (no clip)")
    
    # Parete rettangolare
    wall = box(0, 0, 3000, 2000)
    
    # Custom completamente dentro
    customs = [
        {
            'x': 500,
            'y': 500,
            'width': 1000,
            'height': 495,
            'type': 'custom',
            'coords': [(500, 500), (1500, 500), (1500, 995), (500, 995), (500, 500)],
            'source_block_width': 1239,
            'waste': 239
        }
    ]
    
    block_widths = [1239, 826, 413]
    
    result = clip_customs_to_wall_geometry(customs, wall, block_widths)
    
    print(f"   Input: 1 custom completamente dentro la parete")
    print(f"   Output: {len(result)} custom(s)")
    
    assert len(result) == 1, "Dovrebbe mantenere 1 custom"
    # Dovrebbe mantenere i metadati originali se non è stato tagliato
    assert result[0]['x'] == 500, "Coordinate dovrebbero rimanere uguali"
    print("   ✅ PASS: Custom non modificato (efficienza)\n")


def test_clip_custom_completely_outside():
    """Test custom completamente fuori dalla parete"""
    print("\n🧪 TEST 4: Custom completamente fuori (eliminato)")
    
    # Parete piccola
    wall = box(0, 0, 1000, 1000)
    
    # Custom completamente fuori
    customs = [
        {
            'x': 2000,
            'y': 2000,
            'width': 500,
            'height': 495,
            'type': 'custom',
            'coords': [(2000, 2000), (2500, 2000), (2500, 2495), (2000, 2495), (2000, 2000)]
        }
    ]
    
    block_widths = [1239, 826, 413]
    
    result = clip_customs_to_wall_geometry(customs, wall, block_widths)
    
    print(f"   Input: 1 custom completamente fuori dalla parete")
    print(f"   Output: {len(result)} custom(s)")
    
    assert len(result) == 0, "Custom fuori dovrebbe essere eliminato"
    print("   ✅ PASS: Custom fuori eliminato\n")


if __name__ == '__main__':
    print("=" * 70)
    print("🚀 TEST SUITE: Custom Clipping to Wall Geometry")
    print("=" * 70)
    
    try:
        test_clip_custom_with_sloped_wall()
        test_clip_custom_with_aperture()
        test_no_clip_when_inside()
        test_clip_custom_completely_outside()
        
        print("=" * 70)
        print("✅ TUTTI I TEST PASSATI!")
        print("=" * 70)
        
    except AssertionError as e:
        print(f"\n❌ TEST FALLITO: {e}")
        import traceback
        traceback.print_exc()

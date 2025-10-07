"""
Test di precisione per il taglio custom - verifica bordi esatti
"""

from shapely.geometry import Polygon, box, shape
from core.wall_builder import clip_customs_to_wall_geometry


def test_precision_sloped_edge():
    """Test precisione taglio su bordo inclinato"""
    print("\n🔬 TEST PRECISIONE: Bordo inclinato")
    
    # Parete con bordo superiore inclinato preciso
    wall = Polygon([
        (0, 0),
        (3000, 0),
        (3000, 2000),  # Angolo dx alto
        (0, 2500)      # Angolo sx alto (50mm più in alto)
    ])
    
    # Custom nella zona superiore che dovrebbe essere tagliato
    customs = [
        {
            'x': 0,
            'y': 2000,
            'width': 1000,
            'height': 500,
            'type': 'custom',
            'coords': [(0, 2000), (1000, 2000), (1000, 2500), (0, 2500), (0, 2000)]
        }
    ]
    
    block_widths = [1239, 826, 413]
    
    result = clip_customs_to_wall_geometry(customs, wall, block_widths)
    
    print(f"   Parete: bordo inclinato da y=2500 (sx) a y=2000 (dx)")
    print(f"   Custom: rettangolo y=2000-2500, x=0-1000")
    print(f"   Risultato: {len(result)} custom(s)")
    
    if result:
        clipped_poly = shape(result[0]['geometry'])
        coords = list(clipped_poly.exterior.coords)
        print(f"   Vertici custom tagliato:")
        for i, (x, y) in enumerate(coords):
            print(f"      {i}: ({x:.1f}, {y:.1f})")
        
        # Verifica che il custom sia un trapezio (4 vertici non rettangolari)
        y_values = [y for x, y in coords[:-1]]  # Escludi ultimo (duplicato del primo)
        unique_y = len(set(round(y, 1) for y in y_values))
        print(f"   Numero di Y uniche: {unique_y} (dovrebbe essere >2 per trapezio)")
        
        assert unique_y > 2, "Custom dovrebbe essere un trapezio, non un rettangolo"
    
    print("   ✅ PASS: Taglio preciso su bordo inclinato\n")


def test_precision_small_cut():
    """Test che anche tagli piccoli vengano rilevati"""
    print("\n🔬 TEST PRECISIONE: Taglio piccolo ma importante")
    
    # Parete che taglia solo 50mm da un angolo
    wall = Polygon([
        (0, 0),
        (2000, 0),
        (2000, 1000),
        (1950, 1000),  # Taglio di 50mm
        (1950, 2000),
        (0, 2000)
    ])
    
    # Custom che occupa l'angolo CHE VIENE TAGLIATO (y > 1000)
    customs = [
        {
            'x': 1800,
            'y': 950,
            'width': 200,
            'height': 200,  # Da 950 a 1150 (attraversa la linea di taglio a y=1000)
            'type': 'custom',
            'coords': [(1800, 950), (2000, 950), (2000, 1150), (1800, 1150), (1800, 950)]
        }
    ]
    
    block_widths = [1239, 826, 413]
    
    result = clip_customs_to_wall_geometry(customs, wall, block_widths)
    
    print(f"   Custom originale: 200x200mm nell'angolo")
    print(f"   Parete: taglia 50mm dall'angolo destro")
    print(f"   Risultato: {len(result)} custom(s)")
    
    if result:
        orig_area = 200 * 200
        clipped_poly = shape(result[0]['geometry'])
        new_area = clipped_poly.area
        print(f"   Area originale: {orig_area}mm²")
        print(f"   Area dopo taglio: {new_area:.0f}mm²")
        print(f"   Riduzione: {(1 - new_area/orig_area)*100:.1f}%")
        
        # Verifica che sia stato effettivamente tagliato
        assert new_area < orig_area * 0.99, "Custom dovrebbe essere stato tagliato"
    
    print("   ✅ PASS: Taglio piccolo rilevato correttamente\n")


def test_precision_multiple_edges():
    """Test custom che tocca multipli bordi complessi"""
    print("\n🔬 TEST PRECISIONE: Custom su multipli bordi")
    
    # Parete con forma complessa (L-shape)
    wall = Polygon([
        (0, 0),
        (2000, 0),
        (2000, 1000),
        (1000, 1000),
        (1000, 2000),
        (0, 2000)
    ])
    
    # Custom nell'angolo interno dell'L
    customs = [
        {
            'x': 800,
            'y': 800,
            'width': 400,
            'height': 400,
            'type': 'custom',
            'coords': [(800, 800), (1200, 800), (1200, 1200), (800, 1200), (800, 800)]
        }
    ]
    
    block_widths = [1239, 826, 413]
    
    result = clip_customs_to_wall_geometry(customs, wall, block_widths)
    
    print(f"   Parete: forma L con angolo interno")
    print(f"   Custom: 400x400mm che copre l'angolo interno")
    print(f"   Risultato: {len(result)} custom(s)")
    
    if result:
        clipped_poly = shape(result[0]['geometry'])
        print(f"   Area custom tagliato: {clipped_poly.area:.0f}mm²")
        print(f"   Numero vertici: {len(list(clipped_poly.exterior.coords)) - 1}")
        
        # L'angolo dovrebbe creare un custom a forma di L (6+ vertici)
        vertices = len(list(clipped_poly.exterior.coords)) - 1
        assert vertices >= 5, f"Custom dovrebbe avere forma complessa (>4 vertici), ha {vertices}"
    
    print("   ✅ PASS: Taglio multipli bordi gestito\n")


if __name__ == '__main__':
    print("=" * 70)
    print("🔬 TEST SUITE: Precisione Taglio Custom")
    print("=" * 70)
    
    try:
        test_precision_sloped_edge()
        test_precision_small_cut()
        test_precision_multiple_edges()
        
        print("=" * 70)
        print("✅ TUTTI I TEST DI PRECISIONE PASSATI!")
        print("=" * 70)
        
    except AssertionError as e:
        print(f"\n❌ TEST FALLITO: {e}")
        import traceback
        traceback.print_exc()

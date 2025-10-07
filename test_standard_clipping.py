"""
Test per verificare il taglio dei blocchi STANDARD che escono dalla parete
"""

from shapely.geometry import Polygon, box
from core.wall_builder import clip_all_blocks_to_wall_geometry


def test_standard_block_clipped_to_trapezoid():
    """Test blocco standard che esce dalla parete inclinata → diventa custom trapezio"""
    print("\n🧪 TEST 1: Standard esce da parete inclinata → Custom trapezio")
    
    # Parete con bordo superiore inclinato
    wall = Polygon([
        (0, 0),
        (3000, 0),
        (3000, 2000),  # Angolo dx
        (0, 2500)      # Angolo sx (più alto)
    ])
    
    # Blocco standard in alto che esce dalla parete
    placed = [
        {'x': 0, 'y': 2000, 'width': 1239, 'height': 495, 'type': 'std_1239x495'},
    ]
    customs = []
    
    block_widths = [1239, 826, 413]
    
    new_placed, new_customs = clip_all_blocks_to_wall_geometry(
        placed_blocks=placed,
        custom_blocks=customs,
        wall_polygon=wall,
        block_widths=block_widths
    )
    
    print(f"   Input: 1 standard (1239x495) che esce in alto")
    print(f"   Output: {len(new_placed)} standard, {len(new_customs)} custom")
    
    assert len(new_placed) == 0, "Standard tagliato dovrebbe essere rimosso"
    assert len(new_customs) == 1, "Dovrebbe creare 1 custom trapezoidale"
    assert 'geometry' in new_customs[0], "Custom deve avere geometry"
    
    print("   ✅ PASS: Standard → Custom trapezio\n")


def test_standard_block_inside_wall():
    """Test blocco standard completamente dentro → rimane standard"""
    print("\n🧪 TEST 2: Standard dentro parete → rimane Standard")
    
    # Parete grande
    wall = box(0, 0, 5000, 3000)
    
    # Blocco standard completamente dentro
    placed = [
        {'x': 1000, 'y': 1000, 'width': 1239, 'height': 495, 'type': 'std_1239x495'},
    ]
    customs = []
    
    block_widths = [1239, 826, 413]
    
    new_placed, new_customs = clip_all_blocks_to_wall_geometry(
        placed_blocks=placed,
        custom_blocks=customs,
        wall_polygon=wall,
        block_widths=block_widths
    )
    
    print(f"   Input: 1 standard completamente dentro")
    print(f"   Output: {len(new_placed)} standard, {len(new_customs)} custom")
    
    assert len(new_placed) == 1, "Standard dentro dovrebbe rimanere standard"
    assert len(new_customs) == 0, "Non dovrebbero crearsi custom"
    assert new_placed[0]['type'] == 'std_1239x495', "Tipo dovrebbe rimanere std"
    
    print("   ✅ PASS: Standard rimane invariato\n")


def test_standard_with_aperture():
    """Test blocco standard che copre apertura → diventa custom con buco"""
    print("\n🧪 TEST 3: Standard copre apertura → Custom con buco")
    
    # Parete con apertura (porta)
    wall_outer = box(0, 0, 3000, 2500)
    aperture = box(1000, 0, 1400, 2000)  # Porta
    wall = wall_outer.difference(aperture)
    
    # Blocco standard che copre l'apertura
    placed = [
        {'x': 800, 'y': 500, 'width': 826, 'height': 495, 'type': 'std_826x495'},
    ]
    customs = []
    
    block_widths = [1239, 826, 413]
    
    new_placed, new_customs = clip_all_blocks_to_wall_geometry(
        placed_blocks=placed,
        custom_blocks=customs,
        wall_polygon=wall,
        block_widths=block_widths
    )
    
    print(f"   Input: 1 standard che copre apertura")
    print(f"   Output: {len(new_placed)} standard, {len(new_customs)} custom")
    
    # Potrebbe creare 1 custom tagliato o 2 custom (uno per lato della porta)
    assert len(new_customs) >= 1, "Dovrebbe creare custom per gestire l'apertura"
    
    print("   ✅ PASS: Standard → Custom per apertura\n")


def test_multiple_standards_one_clipped():
    """Test multipli standard, solo uno esce → solo uno diventa custom"""
    print("\n🧪 TEST 4: Multipli standard, solo uno esce")
    
    # Parete con bordo superiore tagliato
    wall = Polygon([
        (0, 0),
        (3000, 0),
        (3000, 2000),
        (0, 2000)
    ])
    
    # Due blocchi: uno dentro, uno fuori
    placed = [
        {'x': 0, 'y': 1000, 'width': 1239, 'height': 495, 'type': 'std_1239x495'},  # Dentro
        {'x': 0, 'y': 1800, 'width': 1239, 'height': 495, 'type': 'std_1239x495'},  # Esce (y+h=2295>2000)
    ]
    customs = []
    
    block_widths = [1239, 826, 413]
    
    new_placed, new_customs = clip_all_blocks_to_wall_geometry(
        placed_blocks=placed,
        custom_blocks=customs,
        wall_polygon=wall,
        block_widths=block_widths
    )
    
    print(f"   Input: 2 standard (1 dentro, 1 esce)")
    print(f"   Output: {len(new_placed)} standard, {len(new_customs)} custom")
    
    assert len(new_placed) == 1, "1 standard dovrebbe rimanere"
    assert len(new_customs) == 1, "1 standard dovrebbe diventare custom"
    
    print("   ✅ PASS: Solo standard che esce diventa custom\n")


if __name__ == '__main__':
    print("=" * 70)
    print("🚀 TEST SUITE: Clipping Standard Blocks to Wall")
    print("=" * 70)
    
    try:
        test_standard_block_clipped_to_trapezoid()
        test_standard_block_inside_wall()
        test_standard_with_aperture()
        test_multiple_standards_one_clipped()
        
        print("=" * 70)
        print("✅ TUTTI I TEST PASSATI!")
        print("=" * 70)
        
    except AssertionError as e:
        print(f"\n❌ TEST FALLITO: {e}")
        import traceback
        traceback.print_exc()

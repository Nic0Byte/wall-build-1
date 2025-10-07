"""
Test per verificare il merge di blocchi small into large customs
"""

from core.wall_builder import merge_small_blocks_into_large_customs


def test_merge_consecutive_customs():
    """Test merge di custom consecutivi"""
    print("\n🧪 TEST 1: Merge Custom + Custom consecutivi")
    
    placed = []
    customs = [
        {'x': 0, 'y': 0, 'width': 200, 'height': 495, 'type': 'custom', 'coords': [(0,0), (200,0), (200,495), (0,495), (0,0)]},
        {'x': 200, 'y': 0, 'width': 150, 'height': 495, 'type': 'custom', 'coords': [(200,0), (350,0), (350,495), (200,495), (200,0)]},
    ]
    block_widths = [1239, 826, 413]
    
    new_placed, new_customs = merge_small_blocks_into_large_customs(
        placed_blocks=placed,
        custom_blocks=customs,
        block_widths=block_widths,
        row_height=495
    )
    
    print(f"   Input: {len(customs)} customs separati (200mm + 150mm)")
    print(f"   Output: {len(new_customs)} custom unificato")
    print(f"   Max consentito: {max(block_widths)}mm")
    
    assert len(new_customs) == 1, "Dovrebbe unire i 2 custom in 1"
    assert new_customs[0]['width'] == 350, f"Larghezza dovrebbe essere 350mm, non {new_customs[0]['width']}"
    assert 'geometry' in new_customs[0], "Custom deve avere campo 'geometry' per visualizzazione"
    print("   ✅ PASS: Custom consecutivi uniti correttamente\n")


def test_merge_small_standard_with_custom():
    """Test merge di standard piccolo + custom"""
    print("\n🧪 TEST 2: Merge Standard piccolo + Custom")
    
    placed = [
        {'x': 0, 'y': 0, 'width': 413, 'height': 495, 'type': 'std_413x495'},
    ]
    customs = [
        {'x': 413, 'y': 0, 'width': 200, 'height': 495, 'type': 'custom', 'coords': [(413,0), (613,0), (613,495), (413,495), (413,0)]},
    ]
    block_widths = [1239, 826, 413]
    
    new_placed, new_customs = merge_small_blocks_into_large_customs(
        placed_blocks=placed,
        custom_blocks=customs,
        block_widths=block_widths,
        row_height=495
    )
    
    print(f"   Input: 1 standard (413mm) + 1 custom (200mm)")
    print(f"   Output: {len(new_placed)} placed, {len(new_customs)} custom")
    print(f"   Max consentito: {max(block_widths)}mm")
    
    assert len(new_placed) == 0, "Standard piccolo dovrebbe essere mergiato"
    assert len(new_customs) == 1, "Dovrebbe creare 1 custom unificato"
    assert new_customs[0]['width'] == 613, f"Larghezza dovrebbe essere 613mm, non {new_customs[0]['width']}"
    assert 'geometry' in new_customs[0], "Custom deve avere campo 'geometry' per visualizzazione"
    print("   ✅ PASS: Standard piccolo + Custom uniti correttamente\n")


def test_no_merge_large_standard():
    """Test che standard grandi NON vengano mergiati"""
    print("\n🧪 TEST 3: NO Merge con Standard grande")
    
    placed = [
        {'x': 0, 'y': 0, 'width': 826, 'height': 495, 'type': 'std_826x495'},
    ]
    customs = [
        {'x': 826, 'y': 0, 'width': 200, 'height': 495, 'type': 'custom', 'coords': [(826,0), (1026,0), (1026,495), (826,495), (826,0)]},
    ]
    block_widths = [1239, 826, 413]
    
    new_placed, new_customs = merge_small_blocks_into_large_customs(
        placed_blocks=placed,
        custom_blocks=customs,
        block_widths=block_widths,
        row_height=495
    )
    
    print(f"   Input: 1 standard GRANDE (826mm) + 1 custom (200mm)")
    print(f"   Output: {len(new_placed)} placed, {len(new_customs)} custom")
    
    assert len(new_placed) == 1, "Standard grande NON dovrebbe essere mergiato"
    assert new_placed[0]['width'] == 826, "Standard grande dovrebbe rimanere 826mm"
    assert len(new_customs) == 1, "Custom dovrebbe rimanere separato"
    print("   ✅ PASS: Standard grande NON mergiato (corretto)\n")


def test_limit_max_custom_width():
    """Test che il merge rispetti il limite max(block_widths)"""
    print("\n🧪 TEST 4: Limite MAX Custom Width")
    
    placed = []
    customs = [
        {'x': 0, 'y': 0, 'width': 800, 'height': 495, 'type': 'custom', 'coords': [(0,0), (800,0), (800,495), (0,495), (0,0)]},
        {'x': 800, 'y': 0, 'width': 500, 'height': 495, 'type': 'custom', 'coords': [(800,0), (1300,0), (1300,495), (800,495), (800,0)]},
    ]
    block_widths = [1239, 826, 413]
    
    new_placed, new_customs = merge_small_blocks_into_large_customs(
        placed_blocks=placed,
        custom_blocks=customs,
        block_widths=block_widths,
        row_height=495
    )
    
    print(f"   Input: 2 customs (800mm + 500mm = 1300mm)")
    print(f"   Max consentito: {max(block_widths)}mm")
    print(f"   Output: {len(new_customs)} custom(s)")
    
    # 800 + 500 = 1300 > 1239, quindi NON dovrebbe mergeare
    assert len(new_customs) == 2, "NON dovrebbe unire perché supera max(1239mm)"
    print("   ✅ PASS: Limite MAX rispettato (1300mm > 1239mm non unito)\n")


def test_multiple_rows():
    """Test che blocchi di righe diverse NON vengano mergiati"""
    print("\n🧪 TEST 5: NO Merge tra righe diverse")
    
    placed = []
    customs = [
        {'x': 0, 'y': 0, 'width': 200, 'height': 495, 'type': 'custom', 'coords': [(0,0), (200,0), (200,495), (0,495), (0,0)]},
        {'x': 0, 'y': 495, 'width': 200, 'height': 495, 'type': 'custom', 'coords': [(0,495), (200,495), (200,990), (0,990), (0,495)]},  # Riga diversa
    ]
    block_widths = [1239, 826, 413]
    
    new_placed, new_customs = merge_small_blocks_into_large_customs(
        placed_blocks=placed,
        custom_blocks=customs,
        block_widths=block_widths,
        row_height=495
    )
    
    print(f"   Input: 2 customs su righe diverse (y=0 e y=495)")
    print(f"   Output: {len(new_customs)} custom(s)")
    
    assert len(new_customs) == 2, "NON dovrebbe unire blocchi di righe diverse"
    print("   ✅ PASS: Blocchi di righe diverse NON uniti (corretto)\n")


if __name__ == '__main__':
    print("=" * 70)
    print("🚀 TEST SUITE: Custom Block Merge Post-Processing")
    print("=" * 70)
    
    try:
        test_merge_consecutive_customs()
        test_merge_small_standard_with_custom()
        test_no_merge_large_standard()
        test_limit_max_custom_width()
        test_multiple_rows()
        
        print("=" * 70)
        print("✅ TUTTI I TEST PASSATI!")
        print("=" * 70)
        
    except AssertionError as e:
        print(f"\n❌ TEST FALLITO: {e}")
        import traceback
        traceback.print_exc()

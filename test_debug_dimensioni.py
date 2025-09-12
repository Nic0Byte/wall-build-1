"""
Test diretto delle dimensioni blocchi - Debug dettagliato
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import parse_svg_wall
from utils.config import get_block_schema_from_frontend

def test_different_dimensions():
    """Test con diverse dimensioni per vedere se cambiano davvero"""
    
    # Carica il file SVG di test
    with open('test_parete_semplice_custom.svg', 'rb') as f:
        svg_bytes = f.read()
    
    wall, apertures = parse_svg_wall(svg_bytes)
    print(f"Parete: {wall.area/1_000_000:.1f} m²")
    print(f"Aperture: {sum(a.area for a in apertures)/1_000_000:.1f} m²")
    print(f"Area netta: {(wall.area - sum(a.area for a in apertures))/1_000_000:.1f} m²")
    print()
    
    # Test diverse configurazioni
    configs = [
        {
            'name': 'Standard TAKTAK',
            'dimensions': {'block_widths': [1500, 826, 413], 'block_height': 495}
        },
        {
            'name': 'Blocchi Grandi', 
            'dimensions': {'block_widths': [2000, 1000, 500], 'block_height': 495}
        },
        {
            'name': 'Blocchi Piccoli',
            'dimensions': {'block_widths': [800, 600, 400], 'block_height': 495}
        },
        {
            'name': 'Blocchi Enormi',
            'dimensions': {'block_widths': [3000, 1500, 750], 'block_height': 495}
        }
    ]
    
    for config in configs:
        print(f"=== {config['name']} ===")
        print(f"Input: {config['dimensions']}")
        
        # Verifica che schema viene scelto
        schema = get_block_schema_from_frontend(config['dimensions'])
        print(f"Schema tipo: {schema['schema_type']}")
        print(f"Dimensioni finali: {schema['block_widths']}")
        print(f"Mapping: {schema['size_to_letter']}")
        
        # Calcola area media per blocco
        avg_width = sum(schema['block_widths']) / len(schema['block_widths'])
        avg_area = avg_width * schema['block_height']
        area_netta_mm2 = wall.area - sum(a.area for a in apertures)
        stima_blocchi = int((area_netta_mm2 / avg_area) * 1.2)  # +20% spreco
        
        print(f"Larghezza media: {avg_width:.0f} mm")
        print(f"Area media blocco: {avg_area:.0f} mm²")
        print(f"Stima blocchi: ~{stima_blocchi}")
        print()

if __name__ == "__main__":
    test_different_dimensions()

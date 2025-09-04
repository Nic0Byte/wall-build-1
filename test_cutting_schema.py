#!/usr/bin/env python3
"""Test per verificare lo schema di taglio."""

import sys
sys.path.append('.')

from main import pack_wall, BLOCK_WIDTHS, BLOCK_HEIGHT, export_to_dxf, summarize_blocks
from shapely.geometry import Polygon
from datetime import datetime

def test_cutting_schema():
    """Test dello schema di taglio."""
    print("🧪 Test schema di taglio...")
    
    # Demo parete trapezoidale con due porte  
    wall_exterior = Polygon([(0,0), (12000,0), (12000,4500), (0,2500), (0,0)])
    porta1 = Polygon([(2000,0), (3200,0), (3200,2200), (2000,2200)])
    porta2 = Polygon([(8500,0), (9700,0), (9700,2200), (8500,2200)])

    placed, custom = pack_wall(wall_exterior, BLOCK_WIDTHS, BLOCK_HEIGHT,
                               row_offset=826, apertures=[porta1, porta2])
    
    print(f"✅ Parsing completato: {len(placed)} standard, {len(custom)} custom")
    
    # Export DXF
    project_name = f"test_schema_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    summary = summarize_blocks(placed)
    
    try:
        dxf_path = export_to_dxf(
            summary=summary,
            customs=custom, 
            placed=placed,
            wall_polygon=wall_exterior, 
            apertures=[porta1, porta2],
            project_name=project_name,
            out_path=f"{project_name}.dxf",
            params={'demo': True}
        )
        print(f"✅ DXF generato: {dxf_path}")
    except Exception as e:
        print(f"❌ Errore export: {e}")
        raise

if __name__ == "__main__":
    test_cutting_schema()

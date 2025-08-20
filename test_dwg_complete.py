#!/usr/bin/env python3
import sys
sys.path.append('.')
import main

print('🧪 Test completo del nostro file DWG test...')
try:
    with open('test_parete_dwg.dwg', 'rb') as f:
        dwg_bytes = f.read()
    
    wall, apertures = main.parse_wall_file(dwg_bytes, 'test_parete_dwg.dwg')
    
    # Test packing completo
    placed, custom = main.pack_wall(wall, main.BLOCK_WIDTHS, main.BLOCK_HEIGHT, row_offset=826, apertures=apertures)
    placed, custom = main.opt_pass(placed, custom, main.BLOCK_WIDTHS)
    
    # Calcola metriche  
    summary = main.summarize_blocks(placed)
    metrics = main.calculate_metrics(placed, custom, wall.area)
    
    print('✅ RISULTATI COMPLETI:')
    print(f'   Parete: {wall.area:.0f} mm² ({wall.bounds[2]:.0f}x{wall.bounds[3]:.0f}mm)')
    print(f'   Aperture: {len(apertures)}')
    print(f'   Blocchi standard: {len(placed)}')
    print(f'   Pezzi custom: {len(custom)}')
    print(f'   Efficienza: {metrics["efficiency"]:.1%}')
    print(f'   Spreco: {metrics["waste_ratio"]:.1%}')
    print('   Distinta:')
    for tipo, qty in summary.items():
        print(f'     {qty} × {tipo}')
        
    # Test export JSON
    json_path = main.export_to_json(summary, custom, placed, 'test_result.json', main.build_run_params(826))
    print(f'   JSON esportato: {json_path}')
        
except Exception as e:
    print(f'❌ Errore: {e}')
    import traceback
    traceback.print_exc()

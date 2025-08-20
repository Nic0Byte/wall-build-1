#!/usr/bin/env python3
import sys
sys.path.append('.')
import main
import os

print('🧪 TEST COMPLETO DEI FILE DWG ORIGINALI')
print('=' * 50)

# Test ROTTINI_LAY_REV0.dwg
print('📁 Test ROTTINI_LAY_REV0.dwg...')
try:
    with open('ROTTINI_LAY_REV0.dwg', 'rb') as f:
        dwg_bytes = f.read()
    
    print(f'   📊 File size: {len(dwg_bytes):,} bytes')
    
    # Controlla i primi bytes per vedere il formato
    header = dwg_bytes[:20]
    print(f'   🔍 Header: {header}')
    
    wall, apertures = main.parse_wall_file(dwg_bytes, 'ROTTINI_LAY_REV0.dwg')
    
    print(f'   ✅ Parete parsata: {wall.area:.0f} mm²')
    print(f'   📏 Dimensioni: {wall.bounds[2]:.0f} x {wall.bounds[3]:.0f} mm')
    print(f'   🚪 Aperture: {len(apertures)}')
    
    # Test packing
    placed, custom = main.pack_wall(wall, main.BLOCK_WIDTHS, main.BLOCK_HEIGHT, row_offset=826, apertures=apertures)
    summary = main.summarize_blocks(placed)
    metrics = main.calculate_metrics(placed, custom, wall.area)
    
    print(f'   📦 Blocchi standard: {len(placed)}')
    print(f'   ✂️ Pezzi custom: {len(custom)}')
    print(f'   ⚡ Efficienza: {metrics["efficiency"]:.1%}')
    print(f'   📋 Distinta: {summary}')
    
except Exception as e:
    print(f'   ❌ Errore: {e}')

print()
print('-' * 50)

# Test FELICE_LAY_REV0.dwg  
print('📁 Test FELICE_LAY_REV0.dwg...')
try:
    with open('FELICE_LAY_REV0.dwg', 'rb') as f:
        dwg_bytes = f.read()
    
    print(f'   📊 File size: {len(dwg_bytes):,} bytes')
    
    # Controlla i primi bytes per vedere il formato
    header = dwg_bytes[:20]
    print(f'   🔍 Header: {header}')
    
    wall, apertures = main.parse_wall_file(dwg_bytes, 'FELICE_LAY_REV0.dwg')
    
    print(f'   ✅ Parete parsata: {wall.area:.0f} mm²')
    print(f'   📏 Dimensioni: {wall.bounds[2]:.0f} x {wall.bounds[3]:.0f} mm')
    print(f'   🚪 Aperture: {len(apertures)}')
    
    # Test packing
    placed, custom = main.pack_wall(wall, main.BLOCK_WIDTHS, main.BLOCK_HEIGHT, row_offset=826, apertures=apertures)
    summary = main.summarize_blocks(placed)
    metrics = main.calculate_metrics(placed, custom, wall.area)
    
    print(f'   📦 Blocchi standard: {len(placed)}')
    print(f'   ✂️ Pezzi custom: {len(custom)}')
    print(f'   ⚡ Efficienza: {metrics["efficiency"]:.1%}')
    print(f'   📋 Distinta: {summary}')
    
except Exception as e:
    print(f'   ❌ Errore: {e}')

print()
print('🔍 ANALISI FORMATO FILES:')
for filename in ['ROTTINI_LAY_REV0.dwg', 'FELICE_LAY_REV0.dwg']:
    if os.path.exists(filename):
        with open(filename, 'rb') as f:
            header = f.read(50)
        print(f'{filename}: {header[:20]} ... (primi 20 bytes)')
        
        # Prova a determinare la versione DWG
        if header.startswith(b'AC10'):
            print(f'  -> Versione: AutoCAD R10')
        elif header.startswith(b'AC1012'):
            print(f'  -> Versione: AutoCAD R13')
        elif header.startswith(b'AC1014'):
            print(f'  -> Versione: AutoCAD R14')
        elif header.startswith(b'AC1015'):
            print(f'  -> Versione: AutoCAD 2000')
        elif header.startswith(b'AC1018'):
            print(f'  -> Versione: AutoCAD 2004')
        elif header.startswith(b'AC1021'):
            print(f'  -> Versione: AutoCAD 2007')
        elif header.startswith(b'AC1024'):
            print(f'  -> Versione: AutoCAD 2010')
        elif header.startswith(b'AC1027'):
            print(f'  -> Versione: AutoCAD 2013')
        elif header.startswith(b'AC1032'):
            print(f'  -> Versione: AutoCAD 2018+')
        else:
            print(f'  -> Versione: Sconosciuta o corrotta')

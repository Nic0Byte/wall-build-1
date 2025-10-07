"""
Test per la generazione della Distinta Base Professionale A4 Landscape con logo TAKTAK®

Questo script testa l'export PDF professionale con dati di esempio.
"""

from shapely.geometry import Polygon
from exporters.pdf_exporter import export_to_pdf_professional, REPORTLAB_AVAILABLE

def test_professional_pdf():
    """Genera un PDF professionale di esempio."""
    
    if not REPORTLAB_AVAILABLE:
        print("❌ ReportLab non disponibile. Installa con: pip install reportlab")
        return
    
    # Dati di esempio - TUTTI DINAMICI
    
    # Parete 16m x 5m
    wall_polygon = Polygon([
        (0, 0),
        (16000, 0),
        (16000, 5000),
        (0, 5000),
        (0, 0)
    ])
    
    # Blocchi standard posizionati (esempio con 3 categorie)
    placed = []
    
    # Categoria A: 1239x495 mm
    for i in range(25):
        placed.append({
            'x': (i % 10) * 1300,
            'y': (i // 10) * 500,
            'width': 1239,
            'height': 495
        })
    
    # Categoria B: 826x495 mm
    for i in range(30):
        placed.append({
            'x': (i % 12) * 850,
            'y': 2000 + (i // 12) * 500,
            'width': 826,
            'height': 495
        })
    
    # Categoria C: 413x495 mm
    for i in range(23):
        placed.append({
            'x': (i % 15) * 420,
            'y': 3500 + (i // 15) * 500,
            'width': 413,
            'height': 495
        })
    
    # Summary dinamico
    summary = {
        'std_1239x495': 25,
        'std_826x495': 30,
        'std_413x495': 23
    }
    
    # Pezzi custom (tagliati su misura)
    customs = []
    
    # Custom tipo D: larghezza ridotta
    for i in range(7):
        customs.append({
            'x': 15000,
            'y': i * 500,
            'width': 371,
            'height': 495,
            'ctype': 1,
            'geometry': {
                'type': 'Polygon',
                'coordinates': [[
                    [15000, i * 500],
                    [15371, i * 500],
                    [15371, i * 500 + 495],
                    [15000, i * 500 + 495],
                    [15000, i * 500]
                ]]
            }
        })
    
    # Custom tipo E: altezza ridotta
    for i in range(3):
        customs.append({
            'x': 14000,
            'y': i * 480,
            'width': 1239,
            'height': 475,
            'ctype': 2,
            'geometry': {
                'type': 'Polygon',
                'coordinates': [[
                    [14000, i * 480],
                    [15239, i * 480],
                    [15239, i * 480 + 475],
                    [14000, i * 480 + 475],
                    [14000, i * 480]
                ]]
            }
        })
    
    # Configurazione blocchi dinamica
    block_config = {
        'block_height': 495,
        'block_widths': [1239, 826, 413],
        'size_to_letter': {
            '1239': 'A',
            '826': 'B',
            '413': 'C'
        }
    }
    
    # Parametri tecnici
    params = {
        'block_height_mm': 495,
        'block_widths_mm': [1239, 826, 413],
        'row_offset_mm': 826,
        'snap_mm': 1.0,
        'keep_out_mm': 2.0,
        'row_aware_merge': True,
        'split_max_width_mm': 413
    }
    
    # Aperture (porte/finestre) - esempio
    apertures = [
        Polygon([
            (3000, 0),
            (5000, 0),
            (5000, 2500),
            (3000, 2500),
            (3000, 0)
        ]),
        Polygon([
            (10000, 0),
            (11500, 0),
            (11500, 2200),
            (10000, 2200),
            (10000, 0)
        ])
    ]
    
    # GENERA PDF PROFESSIONALE
    print("\n" + "="*70)
    print("🚀 GENERAZIONE DISTINTA BASE PROFESSIONALE A4 LANDSCAPE")
    print("="*70)
    print(f"📏 Parete: 16.0m × 5.0m")
    print(f"🧱 Blocchi Standard: {sum(summary.values())} ({len(summary)} categorie)")
    print(f"✂️  Pezzi Custom: {len(customs)}")
    print(f"🎨 Logo: TAKTAK®")
    print("="*70 + "\n")
    
    output_path = export_to_pdf_professional(
        summary=summary,
        customs=customs,
        placed=placed,
        wall_polygon=wall_polygon,
        apertures=apertures,
        project_name="Parete 16m × 5m - Test TAKTAK®",
        out_path="distinta_base_taktak_professional.pdf",
        params=params,
        block_config=block_config,
        author="N. Bovo",
        revision="Rev 1.0"
    )
    
    print(f"\n✅ PDF PROFESSIONALE GENERATO CON SUCCESSO!")
    print(f"📄 Percorso: {output_path}")
    print(f"\n💡 Caratteristiche:")
    print(f"   ✓ Formato A4 Orizzontale (297×210 mm)")
    print(f"   ✓ Logo TAKTAK® nel header")
    print(f"   ✓ Layout 2 colonne (Schema + Dati)")
    print(f"   ✓ Grafico torta efficienza")
    print(f"   ✓ Dimensioni blocchi dinamiche")
    print(f"   ✓ Footer tracciabile")
    print(f"   ✓ Colori corporate (#1B3B6F)")
    print("\n" + "="*70)


if __name__ == "__main__":
    test_professional_pdf()

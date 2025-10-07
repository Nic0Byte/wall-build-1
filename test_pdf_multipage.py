"""
Test per la Distinta Base Professionale MULTIPAGINA (3 pagine A4 Landscape)

PAGINA 1: Sintesi e Riepilogo Tecnico
PAGINA 2: Schema Costruttivo Full-Page con Numerazione
PAGINA 3: Blocchi Standard + Blocchi Custom + Riepilogo Finale
"""

from shapely.geometry import Polygon
from exporters.pdf_exporter import export_to_pdf_professional_multipage, REPORTLAB_AVAILABLE

def test_multipage_pdf():
    """Genera PDF professionale multipagina di esempio."""
    
    if not REPORTLAB_AVAILABLE:
        print("❌ ReportLab non disponibile. Installa con: pip install reportlab")
        return
    
    # Dati di esempio IDENTICI al test singolo
    
    # Parete 16m x 5m
    wall_polygon = Polygon([
        (0, 0),
        (16000, 0),
        (16000, 5000),
        (0, 5000),
        (0, 0)
    ])
    
    # Blocchi standard posizionati
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
            'ctype': 1,  # Larghezza ridotta
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
            'ctype': 2,  # Altezza ridotta
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
    
    # Parametri tecnici completi
    params = {
        'algorithm': 'Greedy + Backtrack',
        'block_height_mm': 495,
        'block_widths_mm': [1239, 826, 413],
        'row_offset_mm': 826,
        'snap_mm': 1.0,
        'keep_out_mm': 2.0,
        'row_aware_merge': True,
        'split_max_width_mm': 413
    }
    
    # Aperture (porte/finestre)
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
    
    # GENERA PDF MULTIPAGINA
    print("\n" + "="*80)
    print("🚀 GENERAZIONE DISTINTA BASE PROFESSIONALE MULTIPAGINA (3 PAGINE A4 LANDSCAPE)")
    print("="*80)
    print(f"📄 PAGINA 1: Sintesi e Riepilogo Tecnico")
    print(f"📄 PAGINA 2: Schema Costruttivo Full-Page (260×155mm) con Numerazione")
    print(f"📄 PAGINA 3: Blocchi Standard + Custom + Riepilogo Finale")
    print("="*80)
    print(f"📏 Parete: 16.0m × 5.0m")
    print(f"🧱 Blocchi Standard: {sum(summary.values())} ({len(summary)} categorie)")
    print(f"✂️  Pezzi Custom: {len(customs)}")
    print(f"🎨 Logo: TAKTAK®")
    print(f"📑 Formato: 3 × A4 Orizzontale (297×210 mm)")
    print("="*80 + "\n")
    
    output_path = export_to_pdf_professional_multipage(
        summary=summary,
        customs=customs,
        placed=placed,
        wall_polygon=wall_polygon,
        apertures=apertures,
        project_name="Parete 16m × 5m - Test TAKTAK®",
        out_path="distinta_base_taktak_3pagine_FINALE.pdf",
        params=params,
        block_config=block_config,
        author="N. Bovo",
        revision="Rev 1.0"
    )
    
    print(f"\n✅ PDF MULTIPAGINA GENERATO CON SUCCESSO!")
    print(f"📄 Percorso: {output_path}")
    print(f"\n💡 Caratteristiche:")
    print(f"   ✓ 3 Pagine A4 Orizzontale (297×210 mm)")
    print(f"   ✓ Pagina 1: Riepilogo + Grafico torta + Parametri")
    print(f"   ✓ Pagina 2: Schema FULL-PAGE (260×155mm) + Legenda con numerazione")
    print(f"   ✓ Pagina 3: Blocchi standard + Custom + Riepilogo finale")
    print(f"   ✓ Logo TAKTAK® nel header")
    print(f"   ✓ Footer con paginazione 1/3, 2/3, 3/3")
    print(f"   ✓ Tutti i dati dinamici")
    print(f"   ✓ Colori corporate (#1B3B6F, #C6F3C0)")
    print("\n" + "="*80)


if __name__ == "__main__":
    test_multipage_pdf()

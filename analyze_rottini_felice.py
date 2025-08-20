"""
Analisi approfondita dei file ROTTINI e FELICE per verificare
l'algoritmo di packing e identificare problemi con blocchi che escono.
"""

import main
import json
from pathlib import Path
from shapely.geometry import Polygon, box
import matplotlib.pyplot as plt
import matplotlib.patches as patches


def analyze_file_detailed(filename):
    """Analisi dettagliata di un file DWG."""
    print(f"\n{'='*60}")
    print(f"📁 ANALISI DETTAGLIATA: {filename}")
    print(f"{'='*60}")
    
    filepath = Path(filename)
    if not filepath.exists():
        print(f"❌ File {filename} non trovato")
        return None
    
    # 1. Analisi file raw
    with open(filepath, 'rb') as f:
        file_bytes = f.read()
    
    print(f"📊 Dimensione file: {len(file_bytes):,} bytes")
    
    # 2. Analisi header
    header_info = main._analyze_dwg_header(file_bytes)
    print(f"🔍 Formato: {header_info['format']} {header_info['version']}")
    print(f"✅ Compatibile: {header_info['compatible']}")
    
    # 3. Parsing con fallback
    try:
        parete, aperture = main.parse_wall_file(file_bytes, filename)
        
        print(f"\n📐 GEOMETRIE ESTRATTE:")
        print(f"   🏠 Parete: {parete.area:,.0f} mm² - Bounds: {parete.bounds}")
        print(f"   🔳 Aperture: {len(aperture)} trovate")
        
        for i, apertura in enumerate(aperture):
            print(f"      • Apertura {i+1}: {apertura.area:,.0f} mm² - Bounds: {apertura.bounds}")
        
        # 4. Test packing con diverse configurazioni
        print(f"\n🧱 TEST ALGORITMO PACKING:")
        test_packing_configurations(parete, aperture, filename)
        
        return {
            'parete': parete,
            'aperture': aperture,
            'header': header_info
        }
        
    except Exception as e:
        print(f"❌ Errore parsing: {e}")
        return None


def test_packing_configurations(parete, aperture, filename):
    """Test multiple configurazioni di packing."""
    
    # Configurazioni da testare
    configs = [
        {"offset": 0, "blocks": [1239, 826, 413], "name": "Standard senza offset"},
        {"offset": 413, "blocks": [1239, 826, 413], "name": "Offset 1/3 blocco"},
        {"offset": 826, "blocks": [1239, 826, 413], "name": "Offset 2/3 blocco (default)"},
        {"offset": 620, "blocks": [1239, 826, 413], "name": "Offset metà blocco"},
        {"offset": 826, "blocks": [1000, 800, 600, 400], "name": "Blocchi alternativi"},
    ]
    
    results = []
    
    for config in configs:
        print(f"\n   🧪 Test: {config['name']}")
        try:
            # Calcola packing
            result = main.calculate_wall_packing(
                parete, aperture, 
                row_offset=config["offset"],
                block_widths=config["blocks"]
            )
            
            # Analizza risultato
            total_blocks = sum(result['standard_blocks'].values())
            custom_pieces = len(result['custom_pieces'])
            efficiency = result['metrics']['efficiency']
            coverage = result['metrics']['coverage'] 
            
            # Verifica bounds (problema blocchi che escono)
            bounds_ok = check_blocks_bounds(result, parete)
            
            print(f"      ✅ Blocchi standard: {total_blocks}")
            print(f"      🔧 Pezzi custom: {custom_pieces}")
            print(f"      📊 Efficienza: {efficiency:.1f}%")
            print(f"      📐 Copertura: {coverage:.1f}%")
            print(f"      🎯 Bounds OK: {'✅' if bounds_ok else '❌'}")
            
            if not bounds_ok:
                print(f"      ⚠️  PROBLEMA: Blocchi fuori dai limiti della parete!")
            
            results.append({
                'config': config,
                'result': result,
                'bounds_ok': bounds_ok,
                'efficiency': efficiency
            })
            
        except Exception as e:
            print(f"      ❌ Errore: {e}")
    
    # Trova miglior configurazione
    valid_results = [r for r in results if r['bounds_ok']]
    if valid_results:
        best = max(valid_results, key=lambda x: x['efficiency'])
        print(f"\n   🏆 MIGLIOR CONFIGURAZIONE: {best['config']['name']}")
        print(f"       📊 Efficienza: {best['efficiency']:.1f}%")
        
        # Salva risultato migliore
        save_result(best, filename)
    else:
        print(f"\n   ⚠️  NESSUNA CONFIGURAZIONE VALIDA TROVATA!")
        print(f"       Tutte le configurazioni hanno blocchi fuori dai limiti")


def check_blocks_bounds(result, parete):
    """Verifica che tutti i blocchi siano entro i limiti della parete."""
    parete_bounds = parete.bounds  # (min_x, min_y, max_x, max_y)
    
    # Controlla blocchi standard
    for row in result.get('wall_layout', []):
        for block in row:
            block_bounds = (
                block['x'], block['y'], 
                block['x'] + block['width'], 
                block['y'] + block['height']
            )
            
            # Verifica se il blocco è completamente dentro la parete
            if (block_bounds[0] < parete_bounds[0] or  # x_min
                block_bounds[1] < parete_bounds[1] or  # y_min  
                block_bounds[2] > parete_bounds[2] or  # x_max
                block_bounds[3] > parete_bounds[3]):   # y_max
                return False
    
    # Controlla pezzi custom
    for piece in result.get('custom_pieces', []):
        if hasattr(piece, 'bounds'):
            piece_bounds = piece.bounds
            if (piece_bounds[0] < parete_bounds[0] or
                piece_bounds[1] < parete_bounds[1] or
                piece_bounds[2] > parete_bounds[2] or
                piece_bounds[3] > parete_bounds[3]):
                return False
    
    return True


def save_result(best_result, filename):
    """Salva il miglior risultato per visualizzazione."""
    output_file = f"best_result_{filename.replace('.dwg', '')}.json"
    
    # Converti geometry in dati serializzabili
    serializable_result = {
        'config': best_result['config'],
        'efficiency': best_result['efficiency'],
        'bounds_ok': best_result['bounds_ok'],
        'standard_blocks': best_result['result']['standard_blocks'],
        'custom_pieces_count': len(best_result['result']['custom_pieces']),
        'metrics': best_result['result']['metrics']
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(serializable_result, f, indent=2, ensure_ascii=False)
    
    print(f"   💾 Risultato salvato in: {output_file}")


def create_comparison_visualization():
    """Crea visualizzazione comparativa dei risultati."""
    print(f"\n🎨 CREAZIONE VISUALIZZAZIONE COMPARATIVA")
    
    fig, axes = plt.subplots(1, 2, figsize=(16, 8))
    fig.suptitle('Confronto Algoritmo Packing: ROTTINI vs FELICE', fontsize=16, fontweight='bold')
    
    # Placeholder per ora - implementeremo dopo i test
    for i, ax in enumerate(axes):
        ax.set_title(f'File {"ROTTINI" if i == 0 else "FELICE"}')
        ax.set_xlabel('X (mm)')
        ax.set_ylabel('Y (mm)')
        ax.grid(True, alpha=0.3)
        ax.text(0.5, 0.5, 'Analisi in corso...', 
                ha='center', va='center', transform=ax.transAxes)
    
    plt.tight_layout()
    plt.savefig('packing_comparison.png', dpi=150, bbox_inches='tight')
    print(f"   💾 Visualizzazione salvata: packing_comparison.png")


if __name__ == "__main__":
    print("🔍 ANALISI APPROFONDITA ALGORITMO PACKING")
    print("Verifica problemi con blocchi che escono dai limiti")
    
    # Analizza entrambi i file
    files = ["ROTTINI_LAY_REV0.dwg", "FELICE_LAY_REV0.dwg"]
    
    results = {}
    for filename in files:
        result = analyze_file_detailed(filename)
        if result:
            results[filename] = result
    
    # Crea visualizzazione comparativa
    if results:
        create_comparison_visualization()
    
    print(f"\n🏁 Analisi completata per {len(results)} file")
    print(f"📁 Controlla i file *_result.json per i dettagli")

"""
Test completo dell'algoritmo di packing sui file SVG convertiti.
Verifica se i blocchi "escono" dalla parete e analizza la qualità del risultato.
"""

import sys
import json
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import Rectangle, Polygon as MPLPolygon
import numpy as np

# Import del nostro sistema
import main
from shapely.geometry import Polygon, box


def test_packing_algorithm(svg_file: str, project_name: str):
    """
    Test completo dell'algoritmo di packing su un file SVG.
    
    Args:
        svg_file: Percorso del file SVG
        project_name: Nome del progetto per output
    """
    
    print(f"\n🧪 TEST ALGORITMO: {project_name}")
    print("=" * 50)
    
    # 1. PARSING FILE
    print("📁 1. Parsing file SVG...")
    try:
        with open(svg_file, 'rb') as f:
            file_bytes = f.read()
        
        parete, aperture = main.parse_wall_file(
            file_bytes, 
            svg_file,
            layer_wall="MURO", 
            layer_holes="BUCHI"
        )
        
        print(f"✅ Parsing completato:")
        print(f"   📐 Area parete: {parete.area:,.0f} mm²")
        print(f"   🔳 Aperture: {len(aperture)}")
        print(f"   📏 Bounds parete: {parete.bounds}")
        
    except Exception as e:
        print(f"❌ Errore parsing: {e}")
        return None
    
    # 2. CONFIGURAZIONE PACKING
    print("\n⚙️ 2. Configurazione algoritmo...")
    
    config = {
        'project_name': project_name,
        'row_offset': 826,  # Offset righe dispari
        'block_widths': [1239, 826, 413],  # Dimensioni blocchi standard
        'block_height': 413,  # Altezza blocchi
        'mortar_thickness': 10  # Spessore malta
    }
    
    print(f"   🧱 Blocchi: {config['block_widths']} mm")
    print(f"   📏 Altezza: {config['block_height']} mm")
    print(f"   ↔️ Offset: {config['row_offset']} mm")
    
    # 3. ESECUZIONE PACKING
    print("\n🎯 3. Esecuzione packing...")
    
    try:
        # Usa la funzione corretta pack_wall
        result = main.pack_wall(
            parete, 
            aperture,
            project_name=config['project_name'],
            row_offset=config['row_offset'],
            block_widths=config['block_widths']
        )
        
        # Calcola metriche se non presenti
        if 'summary' not in result:
            # Conta blocchi
            standard_count = 0
            for block_type, block_list in result.get('standard_blocks', {}).items():
                standard_count += len(block_list)
            
            custom_count = len(result.get('custom_pieces', []))
            
            # Calcola area coperta
            total_block_area = 0
            for block_type, block_list in result.get('standard_blocks', {}).items():
                for block in block_list:
                    if 'geometry' in block:
                        geom = block['geometry']
                        total_block_area += geom.get('width', 0) * geom.get('height', 0)
            
            for piece in result.get('custom_pieces', []):
                if 'geometry' in piece:
                    geom = piece['geometry']
                    total_block_area += geom.get('width', 0) * geom.get('height', 0)
            
            # Aggiungi summary
            result['summary'] = {
                'standard_blocks': standard_count,
                'custom_pieces': custom_count,
                'efficiency': (total_block_area / parete.area * 100) if parete.area > 0 else 0,
                'waste': max(0, 100 - (total_block_area / parete.area * 100)) if parete.area > 0 else 0
            }
        
        print(f"✅ Packing completato:")
        print(f"   🧱 Blocchi standard: {result['summary']['standard_blocks']}")
        print(f"   ✂️ Pezzi custom: {result['summary']['custom_pieces']}")
        print(f"   📊 Efficienza: {result['summary']['efficiency']:.1f}%")
        print(f"   🗑️ Spreco: {result['summary']['waste']:.1f}%")
        
    except Exception as e:
        print(f"❌ Errore packing: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    # 4. ANALISI QUALITÀ
    print("\n🔍 4. Analisi qualità risultato...")
    
    quality_issues = analyze_packing_quality(result, parete, aperture, config)
    
    # 5. VISUALIZZAZIONE
    print("\n📊 5. Generazione visualizzazione...")
    
    plot_file = create_detailed_plot(result, parete, aperture, project_name, quality_issues)
    
    # 6. SALVATAGGIO RISULTATI
    print("\n💾 6. Salvataggio risultati...")
    
    # Salva JSON dettagliato
    json_file = f"{project_name.lower()}_result.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Risultati salvati:")
    print(f"   📊 Grafico: {plot_file}")
    print(f"   📋 Dati: {json_file}")
    
    return {
        'result': result,
        'quality_issues': quality_issues,
        'plot_file': plot_file,
        'json_file': json_file
    }


def analyze_packing_quality(result, parete, aperture, config):
    """Analizza la qualità del packing per identificare problemi."""
    
    print("   🔍 Controllo blocchi fuori parete...")
    print("   🔍 Controllo sovrapposizioni...")
    print("   🔍 Controllo gap e spazi vuoti...")
    
    issues = {
        'blocks_outside_wall': [],
        'blocks_in_apertures': [],
        'overlapping_blocks': [],
        'large_gaps': [],
        'quality_score': 0
    }
    
    # Estrai geometrie blocchi
    all_blocks = []
    
    # Blocchi standard
    for block_type, block_list in result.get('standard_blocks', {}).items():
        for block in block_list:
            if 'geometry' in block:
                all_blocks.append({
                    'type': 'standard',
                    'subtype': block_type,
                    'id': block.get('id', 'unknown'),
                    'geometry': block['geometry']
                })
    
    # Pezzi custom
    for piece in result.get('custom_pieces', []):
        if 'geometry' in piece:
            all_blocks.append({
                'type': 'custom',
                'subtype': piece.get('type', 'unknown'),
                'id': piece.get('id', 'unknown'),
                'geometry': piece['geometry']
            })
    
    print(f"   📊 Analisi {len(all_blocks)} blocchi totali...")
    
    # 1. Controllo blocchi fuori parete
    for i, block in enumerate(all_blocks):
        try:
            # Converti geometria in Polygon
            if isinstance(block['geometry'], dict):
                # Assumiamo sia un rettangolo con x, y, width, height
                x = block['geometry'].get('x', 0)
                y = block['geometry'].get('y', 0)
                w = block['geometry'].get('width', 0)
                h = block['geometry'].get('height', 0)
                block_poly = box(x, y, x + w, y + h)
            else:
                continue
            
            # Controlla se è completamente dentro la parete
            if not parete.contains(block_poly):
                # Calcola quanto è fuori
                intersection = parete.intersection(block_poly)
                if intersection.area > 0:
                    outside_ratio = 1 - (intersection.area / block_poly.area)
                    if outside_ratio > 0.1:  # >10% fuori
                        issues['blocks_outside_wall'].append({
                            'block_id': block['id'],
                            'type': block['type'],
                            'outside_ratio': outside_ratio,
                            'geometry': block['geometry']
                        })
                else:
                    # Completamente fuori
                    issues['blocks_outside_wall'].append({
                        'block_id': block['id'],
                        'type': block['type'],
                        'outside_ratio': 1.0,
                        'geometry': block['geometry']
                    })
        
        except Exception as e:
            print(f"   ⚠️ Errore analisi blocco {i}: {e}")
    
    # 2. Controllo blocchi nelle aperture
    for i, block in enumerate(all_blocks):
        try:
            # Converti geometria in Polygon
            if isinstance(block['geometry'], dict):
                x = block['geometry'].get('x', 0)
                y = block['geometry'].get('y', 0)
                w = block['geometry'].get('width', 0)
                h = block['geometry'].get('height', 0)
                block_poly = box(x, y, x + w, y + h)
            else:
                continue
            
            # Controlla intersezione con aperture
            for j, apertura in enumerate(aperture):
                if block_poly.intersects(apertura):
                    intersection = block_poly.intersection(apertura)
                    if intersection.area > 0:
                        overlap_ratio = intersection.area / block_poly.area
                        if overlap_ratio > 0.05:  # >5% sovrapposizione
                            issues['blocks_in_apertures'].append({
                                'block_id': block['id'],
                                'aperture_id': j,
                                'overlap_ratio': overlap_ratio,
                                'geometry': block['geometry']
                            })
        
        except Exception as e:
            print(f"   ⚠️ Errore controllo aperture blocco {i}: {e}")
    
    # 3. Calcolo quality score
    total_issues = (
        len(issues['blocks_outside_wall']) + 
        len(issues['blocks_in_apertures']) + 
        len(issues['overlapping_blocks'])
    )
    
    if len(all_blocks) > 0:
        issues['quality_score'] = max(0, 100 - (total_issues / len(all_blocks)) * 100)
    else:
        issues['quality_score'] = 0
    
    # Report finale
    print(f"   📊 Blocchi fuori parete: {len(issues['blocks_outside_wall'])}")
    print(f"   📊 Blocchi in aperture: {len(issues['blocks_in_apertures'])}")
    print(f"   📊 Quality Score: {issues['quality_score']:.1f}/100")
    
    return issues


def create_detailed_plot(result, parete, aperture, project_name, quality_issues):
    """Crea visualizzazione dettagliata del risultato."""
    
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(20, 16))
    fig.suptitle(f'Analisi Packing: {project_name}', fontsize=16, fontweight='bold')
    
    # 1. LAYOUT GENERALE
    ax1.set_title('Layout Generale', fontweight='bold')
    ax1.set_aspect('equal')
    
    # Disegna parete
    wall_coords = list(parete.exterior.coords)
    wall_polygon = MPLPolygon(wall_coords, fill=False, edgecolor='black', linewidth=2, label='Parete')
    ax1.add_patch(wall_polygon)
    
    # Disegna aperture
    for i, apertura in enumerate(aperture):
        ap_coords = list(apertura.exterior.coords)
        ap_polygon = MPLPolygon(ap_coords, fill=True, facecolor='lightcoral', 
                               edgecolor='red', alpha=0.7, label='Apertura' if i == 0 else '')
        ax1.add_patch(ap_polygon)
    
    # Disegna blocchi
    block_colors = {'standard': 'lightblue', 'custom': 'lightgreen'}
    
    # Blocchi standard
    for block_type, block_list in result.get('standard_blocks', {}).items():
        for block in block_list:
            if 'geometry' in block:
                x = block['geometry'].get('x', 0)
                y = block['geometry'].get('y', 0)
                w = block['geometry'].get('width', 0)
                h = block['geometry'].get('height', 0)
                
                rect = Rectangle((x, y), w, h, 
                               facecolor=block_colors['standard'], 
                               edgecolor='blue', alpha=0.6)
                ax1.add_patch(rect)
    
    # Pezzi custom
    for piece in result.get('custom_pieces', []):
        if 'geometry' in piece:
            x = piece['geometry'].get('x', 0)
            y = piece['geometry'].get('y', 0)
            w = piece['geometry'].get('width', 0)
            h = piece['geometry'].get('height', 0)
            
            rect = Rectangle((x, y), w, h, 
                           facecolor=block_colors['custom'], 
                           edgecolor='green', alpha=0.6)
            ax1.add_patch(rect)
    
    ax1.set_xlim(parete.bounds[0] - 500, parete.bounds[2] + 500)
    ax1.set_ylim(parete.bounds[1] - 500, parete.bounds[3] + 500)
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # 2. PROBLEMI QUALITÀ
    ax2.set_title('Problemi di Qualità', fontweight='bold', color='red')
    ax2.set_aspect('equal')
    
    # Disegna solo parete e aperture
    wall_polygon2 = MPLPolygon(wall_coords, fill=False, edgecolor='black', linewidth=2)
    ax2.add_patch(wall_polygon2)
    
    for apertura in aperture:
        ap_coords = list(apertura.exterior.coords)
        ap_polygon2 = MPLPolygon(ap_coords, fill=True, facecolor='lightcoral', 
                                edgecolor='red', alpha=0.7)
        ax2.add_patch(ap_polygon2)
    
    # Evidenzia blocchi problematici
    problem_count = 0
    
    # Blocchi fuori parete
    for issue in quality_issues['blocks_outside_wall']:
        geom = issue['geometry']
        x, y = geom.get('x', 0), geom.get('y', 0)
        w, h = geom.get('width', 0), geom.get('height', 0)
        
        rect = Rectangle((x, y), w, h, 
                        facecolor='red', edgecolor='darkred', 
                        alpha=0.8, linewidth=2)
        ax2.add_patch(rect)
        
        # Aggiungi testo con percentuale fuori
        outside_pct = issue['outside_ratio'] * 100
        ax2.text(x + w/2, y + h/2, f'{outside_pct:.0f}%', 
                ha='center', va='center', fontweight='bold', color='white')
        problem_count += 1
    
    # Blocchi in aperture
    for issue in quality_issues['blocks_in_apertures']:
        geom = issue['geometry']
        x, y = geom.get('x', 0), geom.get('y', 0)
        w, h = geom.get('width', 0), geom.get('height', 0)
        
        rect = Rectangle((x, y), w, h, 
                        facecolor='orange', edgecolor='darkorange', 
                        alpha=0.8, linewidth=2)
        ax2.add_patch(rect)
        problem_count += 1
    
    ax2.set_xlim(parete.bounds[0] - 500, parete.bounds[2] + 500)
    ax2.set_ylim(parete.bounds[1] - 500, parete.bounds[3] + 500)
    ax2.grid(True, alpha=0.3)
    
    if problem_count == 0:
        ax2.text(0.5, 0.5, '✅ NESSUN PROBLEMA\nRILEVATO', 
                transform=ax2.transAxes, ha='center', va='center',
                fontsize=14, fontweight='bold', color='green',
                bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.8))
    
    # 3. STATISTICHE
    ax3.set_title('Statistiche Dettagliate', fontweight='bold')
    ax3.axis('off')
    
    # Calcola statistiche
    stats_text = f"""
DIMENSIONI PARETE:
• Larghezza: {parete.bounds[2] - parete.bounds[0]:.0f} mm
• Altezza: {parete.bounds[3] - parete.bounds[1]:.0f} mm  
• Area totale: {parete.area:,.0f} mm²

APERTURE:
• Numero: {len(aperture)}
• Area totale: {sum(ap.area for ap in aperture):,.0f} mm²

BLOCCHI:
• Standard: {result['summary']['standard_blocks']}
• Custom: {result['summary']['custom_pieces']}
• Totali: {result['summary']['standard_blocks'] + result['summary']['custom_pieces']}

QUALITÀ:
• Efficienza: {result['summary']['efficiency']:.1f}%
• Spreco: {result['summary']['waste']:.1f}%
• Quality Score: {quality_issues['quality_score']:.1f}/100

PROBLEMI:
• Blocchi fuori parete: {len(quality_issues['blocks_outside_wall'])}
• Blocchi in aperture: {len(quality_issues['blocks_in_apertures'])}
"""
    
    ax3.text(0.05, 0.95, stats_text, transform=ax3.transAxes, 
             verticalalignment='top', fontfamily='monospace', fontsize=11)
    
    # 4. DISTRIBUZIONE BLOCCHI
    ax4.set_title('Distribuzione Blocchi', fontweight='bold')
    
    # Conta blocchi per tipo
    block_counts = {}
    
    # Blocchi standard
    for block_type, block_list in result.get('standard_blocks', {}).items():
        block_counts[f'Standard {block_type}'] = len(block_list)
    
    # Pezzi custom
    custom_types = {}
    for piece in result.get('custom_pieces', []):
        piece_type = piece.get('type', 'Unknown')
        custom_types[piece_type] = custom_types.get(piece_type, 0) + 1
    
    for custom_type, count in custom_types.items():
        block_counts[f'Custom {custom_type}'] = count
    
    # Grafico a barre
    if block_counts:
        labels = list(block_counts.keys())
        values = list(block_counts.values())
        colors = plt.cm.Set3(np.linspace(0, 1, len(labels)))
        
        bars = ax4.bar(labels, values, color=colors)
        ax4.set_ylabel('Quantità')
        ax4.tick_params(axis='x', rotation=45)
        
        # Aggiungi valori sulle barre
        for bar, value in zip(bars, values):
            ax4.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                    str(value), ha='center', va='bottom', fontweight='bold')
    else:
        ax4.text(0.5, 0.5, 'Nessun blocco\ntrovato', transform=ax4.transAxes,
                ha='center', va='center', fontsize=12)
    
    plt.tight_layout()
    
    # Salva grafico
    plot_file = f"{project_name.lower()}_analysis.png"
    plt.savefig(plot_file, dpi=150, bbox_inches='tight')
    plt.show()
    
    return plot_file


def run_complete_analysis():
    """Esegue analisi completa sui file SVG convertiti."""
    
    print("🚀 ANALISI COMPLETA ALGORITMO PACKING")
    print("=" * 60)
    
    # File da testare
    test_files = [
        ("ROTTINI_LAY_REV0.svg", "Rottini"),
        ("FELICE_LAY_REV0.svg", "Felice")
    ]
    
    results = {}
    
    for svg_file, project_name in test_files:
        if not Path(svg_file).exists():
            print(f"⏭️ {svg_file}: File non trovato")
            continue
        
        try:
            result = test_packing_algorithm(svg_file, project_name)
            if result:
                results[project_name] = result
        except Exception as e:
            print(f"❌ Errore test {project_name}: {e}")
    
    # Riassunto finale
    print("\n" + "=" * 60)
    print("📊 RIASSUNTO ANALISI COMPLETA")
    print("=" * 60)
    
    for project_name, result in results.items():
        quality_score = result['quality_issues']['quality_score']
        efficiency = result['result']['summary']['efficiency']
        
        print(f"\n🏗️ {project_name.upper()}:")
        print(f"   📊 Quality Score: {quality_score:.1f}/100")
        print(f"   ⚡ Efficienza: {efficiency:.1f}%")
        print(f"   ❌ Problemi: {len(result['quality_issues']['blocks_outside_wall'])} blocchi fuori")
        print(f"   📁 File: {result['plot_file']}")
        
        # Valutazione
        if quality_score >= 90:
            print(f"   ✅ RISULTATO: ECCELLENTE")
        elif quality_score >= 70:
            print(f"   ⚠️ RISULTATO: BUONO (migliorabile)")
        else:
            print(f"   ❌ RISULTATO: PROBLEMATICO (richiede ottimizzazione)")
    
    return results


if __name__ == "__main__":
    results = run_complete_analysis()

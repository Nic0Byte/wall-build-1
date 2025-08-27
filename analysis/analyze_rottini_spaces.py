"""
Analisi dettagliata degli spazi in ROTTINI per ottimizzare il packing.
Verifica se stiamo lasciando spazi utilizzabili vuoti.
"""

import main
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import Rectangle
import numpy as np


def analyze_rottini_spaces():
    """Analizza in dettaglio gli spazi di ROTTINI."""
    
    print("🔍 ANALISI DETTAGLIATA SPAZI - ROTTINI")
    print("=" * 50)
    
    # Parse file
    with open("ROTTINI_LAY_REV0.svg", 'rb') as f:
        svg_bytes = f.read()
    
    parete, aperture = main.parse_wall_file(svg_bytes, "ROTTINI_LAY_REV0.svg")
    
    print(f"📏 Dimensioni parete: {parete.bounds}")
    print(f"📐 Area parete: {parete.area:,.0f} mm²")
    print(f"🔳 Aperture: {len(aperture)}")
    
    # Analizza aperture in dettaglio
    for i, ap in enumerate(aperture):
        print(f"   Apertura {i+1}: {ap.bounds}, area: {ap.area:,.0f} mm²")
    
    # Calcola area netta
    area_aperture = sum(ap.area for ap in aperture)
    area_netta = parete.area - area_aperture
    print(f"📊 Area netta utilizzabile: {area_netta:,.0f} mm²")
    
    # Test packing con parametri attuali
    print(f"\n🧪 TEST PACKING ATTUALE:")
    placed_blocks, custom_pieces = main.pack_wall(
        parete,
        [1239, 826, 413],  # block_widths
        413,               # block_height
        row_offset=826,
        apertures=aperture
    )
    
    print(f"🧱 Blocchi standard: {len(placed_blocks)}")
    print(f"✂️ Pezzi custom: {len(custom_pieces)}")
    
    # Calcola area coperta
    area_blocchi = 0
    for block in placed_blocks:
        w = block.get('width', 0)
        h = block.get('height', 0)
        area_blocchi += w * h
        
    area_custom = 0
    for piece in custom_pieces:
        if 'area' in piece:
            area_custom += piece['area']
        elif 'width' in piece and 'height' in piece:
            area_custom += piece['width'] * piece['height']
    
    area_totale_coperta = area_blocchi + area_custom
    
    print(f"📊 Area blocchi standard: {area_blocchi:,.0f} mm²")
    print(f"📊 Area pezzi custom: {area_custom:,.0f} mm²")
    print(f"📊 Area totale coperta: {area_totale_coperta:,.0f} mm²")
    print(f"📊 Area non utilizzata: {area_netta - area_totale_coperta:,.0f} mm²")
    print(f"📈 Efficienza: {area_totale_coperta / area_netta * 100:.1f}%")
    
    # Analizza spazio rimanente verticale
    bounds = parete.bounds
    altezza_parete = bounds[3] - bounds[1]  # 2700mm
    
    print(f"\n📏 ANALISI SPAZIO VERTICALE:")
    print(f"   Altezza parete: {altezza_parete:.0f} mm")
    print(f"   Altezza blocco: 413 mm")
    print(f"   Righe teoriche: {altezza_parete / 413:.2f}")
    print(f"   Righe intere: {int(altezza_parete / 413)}")
    print(f"   Spazio ultima riga: {altezza_parete % 413:.0f} mm")
    
    # Calcola Y dell'ultima riga piazzata
    max_y_placed = 0
    for block in placed_blocks:
        y = block.get('y', 0)
        h = block.get('height', 0)
        max_y_placed = max(max_y_placed, y + h)
    
    spazio_non_utilizzato = altezza_parete - max_y_placed
    print(f"   Y massimo piazzato: {max_y_placed:.0f} mm")
    print(f"   Spazio non utilizzato: {spazio_non_utilizzato:.0f} mm")
    
    if spazio_non_utilizzato > 100:  # Se c'è spazio > 10cm
        print(f"   ⚠️  SPAZIO UTILIZZABILE SPRECATO: {spazio_non_utilizzato:.0f} mm!")
        
        # Calcola quanti blocchi ridotti potrebbero entrare
        for altura_ridotta in [300, 250, 200, 150, 100]:
            if spazio_non_utilizzato >= altura_ridotta:
                larghezza_parete = bounds[2] - bounds[0]  # 8000mm
                blocchi_extra = int(larghezza_parete / 413)  # Usando larghezza minima blocco
                area_extra = blocchi_extra * 413 * altura_ridotta
                print(f"     Con blocchi {altura_ridotta}mm: +{blocchi_extra} blocchi, +{area_extra:,.0f} mm²")
    
    return {
        'parete': parete,
        'aperture': aperture,
        'placed_blocks': placed_blocks,
        'custom_pieces': custom_pieces,
        'area_netta': area_netta,
        'area_coperta': area_totale_coperta,
        'spazio_non_utilizzato': spazio_non_utilizzato,
        'efficienza': area_totale_coperta / area_netta * 100
    }


def test_optimized_packing():
    """Testa packing ottimizzato per utilizzare meglio lo spazio."""
    
    print(f"\n🔧 TEST PACKING OTTIMIZZATO")
    print("=" * 40)
    
    # Parse file
    with open("ROTTINI_LAY_REV0.svg", 'rb') as f:
        svg_bytes = f.read()
    
    parete, aperture = main.parse_wall_file(svg_bytes, "ROTTINI_LAY_REV0.svg")
    
    # Test con controlli meno stringenti
    print("🧪 Test 1: Controlli meno stringenti (60% invece di 80%)")
    
    # Modifica temporaneamente il controllo nel pack_wall
    # Per ora, testiamo con blocchi di altezza ridotta per l'ultima riga
    
    bounds = parete.bounds
    altezza_parete = bounds[3] - bounds[1]
    spazio_ultima_riga = altezza_parete % 413
    
    results = []
    
    # Test con diverse soglie
    for soglia in [0.3, 0.4, 0.5, 0.6, 0.7, 0.8]:
        try:
            # Simula il controllo con diverse soglie
            min_height_required = 413 * soglia
            
            if spazio_ultima_riga >= min_height_required:
                status = f"✅ PASSA (spazio: {spazio_ultima_riga:.0f} >= soglia: {min_height_required:.0f})"
            else:
                status = f"❌ BLOCCA (spazio: {spazio_ultima_riga:.0f} < soglia: {min_height_required:.0f})"
            
            results.append({
                'soglia': soglia,
                'min_height': min_height_required,
                'passa': spazio_ultima_riga >= min_height_required,
                'status': status
            })
            
            print(f"   Soglia {soglia*100:.0f}%: {status}")
            
        except Exception as e:
            print(f"   Soglia {soglia*100:.0f}%: ❌ Errore: {e}")
    
    # Trova soglia ottimale
    soglie_valide = [r for r in results if r['passa']]
    if soglie_valide:
        migliore = max(soglie_valide, key=lambda x: x['soglia'])
        print(f"\n🎯 Soglia ottimale: {migliore['soglia']*100:.0f}% (min: {migliore['min_height']:.0f}mm)")
        print(f"   Utilizza spazio di {spazio_ultima_riga:.0f}mm rimanente")
    else:
        print(f"\n⚠️ Nessuna soglia permette di utilizzare lo spazio rimanente")
    
    return results


def visualize_space_usage():
    """Visualizza l'uso dello spazio in ROTTINI."""
    
    print(f"\n📊 VISUALIZZAZIONE USO SPAZIO")
    print("=" * 35)
    
    # Parse e packing
    with open("ROTTINI_LAY_REV0.svg", 'rb') as f:
        svg_bytes = f.read()
    
    parete, aperture = main.parse_wall_file(svg_bytes, "ROTTINI_LAY_REV0.svg")
    placed_blocks, custom_pieces = main.pack_wall(
        parete, [1239, 826, 413], 413, row_offset=826, apertures=aperture
    )
    
    # Crea visualizzazione
    fig, ax = plt.subplots(1, 1, figsize=(14, 8))
    ax.set_title('ROTTINI - Analisi Uso Spazio Verticale', fontsize=14, fontweight='bold')
    ax.set_aspect('equal')
    
    bounds = parete.bounds
    
    # Disegna parete
    wall_rect = Rectangle((bounds[0], bounds[1]), 
                         bounds[2] - bounds[0], 
                         bounds[3] - bounds[1],
                         fill=False, edgecolor='black', linewidth=3, label='Parete')
    ax.add_patch(wall_rect)
    
    # Disegna aperture
    for i, apertura in enumerate(aperture):
        ap_bounds = apertura.bounds
        ap_rect = Rectangle((ap_bounds[0], ap_bounds[1]),
                           ap_bounds[2] - ap_bounds[0],
                           ap_bounds[3] - ap_bounds[1],
                           fill=True, facecolor='lightcoral', 
                           edgecolor='red', alpha=0.7, 
                           label='Apertura' if i == 0 else '')
        ax.add_patch(ap_rect)
    
    # Disegna blocchi
    max_y_used = 0
    for block in placed_blocks:
        x = block.get('x', 0)
        y = block.get('y', 0)
        w = block.get('width', 0)
        h = block.get('height', 0)
        
        rect = Rectangle((x, y), w, h, 
                        facecolor='lightblue', edgecolor='blue', 
                        alpha=0.6, linewidth=1)
        ax.add_patch(rect)
        
        max_y_used = max(max_y_used, y + h)
    
    # Evidenzia spazio non utilizzato
    spazio_non_utilizzato = bounds[3] - max_y_used
    if spazio_non_utilizzato > 10:  # Se > 1cm
        unused_rect = Rectangle((bounds[0], max_y_used),
                               bounds[2] - bounds[0],
                               spazio_non_utilizzato,
                               fill=True, facecolor='yellow', 
                               edgecolor='orange', alpha=0.8, linewidth=2,
                               label=f'Spazio non utilizzato: {spazio_non_utilizzato:.0f}mm')
        ax.add_patch(unused_rect)
    
    # Linee di riferimento
    ax.axhline(y=max_y_used, color='red', linestyle='--', linewidth=2,
               label=f'Ultima riga: Y={max_y_used:.0f}mm')
    
    # Righe teoriche
    for i in range(int(bounds[3] / 413) + 1):
        y_riga = bounds[1] + i * 413
        if y_riga <= bounds[3]:
            ax.axhline(y=y_riga, color='gray', linestyle=':', alpha=0.5)
            if i > 0:
                ax.text(bounds[0] - 100, y_riga, f'R{i}', ha='center', va='center', fontsize=8)
    
    # Info
    info_text = f"""ROTTINI - Analisi Spazio:
• Altezza parete: {bounds[3]-bounds[1]:.0f}mm
• Altezza blocco: 413mm
• Righe teoriche: {(bounds[3]-bounds[1])/413:.1f}
• Ultima Y usata: {max_y_used:.0f}mm
• Spazio non usato: {spazio_non_utilizzato:.0f}mm
• % spazio sprecato: {spazio_non_utilizzato/(bounds[3]-bounds[1])*100:.1f}%"""
    
    ax.text(0.02, 0.98, info_text, transform=ax.transAxes,
            verticalalignment='top', fontfamily='monospace', 
            fontsize=10, bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
    
    ax.set_xlim(bounds[0] - 300, bounds[2] + 300)
    ax.set_ylim(bounds[1] - 200, bounds[3] + 200)
    ax.legend(loc='upper right')
    ax.grid(True, alpha=0.3)
    ax.set_xlabel('X (mm)')
    ax.set_ylabel('Y (mm)')
    
    # Salva
    plt.savefig('rottini_space_analysis.png', dpi=150, bbox_inches='tight')
    plt.show()
    
    print(f"✅ Visualizzazione salvata: rottini_space_analysis.png")
    print(f"📊 Spazio non utilizzato: {spazio_non_utilizzato:.0f}mm ({spazio_non_utilizzato/(bounds[3]-bounds[1])*100:.1f}%)")


if __name__ == "__main__":
    # Analisi completa
    data = analyze_rottini_spaces()
    
    if data['spazio_non_utilizzato'] > 100:
        print(f"\n⚠️ PROBLEMA CONFERMATO: {data['spazio_non_utilizzato']:.0f}mm di spazio sprecato!")
        test_results = test_optimized_packing()
        visualize_space_usage()
    else:
        print(f"\n✅ Spazio utilizzato efficacemente: solo {data['spazio_non_utilizzato']:.0f}mm rimanenti")

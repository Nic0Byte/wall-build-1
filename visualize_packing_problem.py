"""
Visualizzazione del problema dei blocchi che escono dalla parete.
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import Rectangle
import main


def visualize_problem(svg_file: str, title: str):
    """Visualizza il problema del packing."""
    
    print(f"\n🔍 VISUALIZZAZIONE: {title}")
    print("-" * 40)
    
    # Parse
    with open(svg_file, 'rb') as f:
        svg_bytes = f.read()
    
    parete, aperture = main.parse_wall_file(svg_bytes, svg_file)
    
    # Packing
    placed_blocks, custom_pieces = main.pack_wall(
        parete,
        [1239, 826, 413],
        413,
        row_offset=826,
        apertures=aperture
    )
    
    # Crea grafico
    fig, ax = plt.subplots(1, 1, figsize=(16, 10))
    ax.set_title(f'{title} - Problema Blocchi Fuori Parete', fontsize=14, fontweight='bold')
    ax.set_aspect('equal')
    
    # Disegna parete (contorno)
    bounds = parete.bounds
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
    
    # Analizza blocchi
    blocks_inside = 0
    blocks_outside = 0
    
    for i, block in enumerate(placed_blocks):
        x = block.get('x', 0)
        y = block.get('y', 0)
        w = block.get('width', 0)
        h = block.get('height', 0)
        
        # Controlla se è fuori
        is_outside = (x < bounds[0] or y < bounds[1] or 
                     x + w > bounds[2] or y + h > bounds[3])
        
        if is_outside:
            # Blocco fuori - rosso
            color = 'red'
            alpha = 0.8
            blocks_outside += 1
            
            # Aggiungi etichetta con info
            if blocks_outside <= 5:  # Solo primi 5
                ax.text(x + w/2, y + h/2, f'OUT\n{i}', 
                       ha='center', va='center', fontsize=8, 
                       fontweight='bold', color='white')
        else:
            # Blocco dentro - blu
            color = 'lightblue'
            alpha = 0.6
            blocks_inside += 1
        
        rect = Rectangle((x, y), w, h, 
                        facecolor=color, edgecolor='blue', 
                        alpha=alpha, linewidth=1)
        ax.add_patch(rect)
    
    # Disegna custom pieces
    for piece in custom_pieces:
        # I custom pieces dovrebbero essere geometrie più complesse
        # Per ora assumiamo abbiano x, y, width, height
        if 'x' in piece and 'y' in piece:
            x = piece.get('x', 0)
            y = piece.get('y', 0) 
            w = piece.get('width', 100)
            h = piece.get('height', 100)
            
            rect = Rectangle((x, y), w, h,
                           facecolor='lightgreen', edgecolor='green',
                           alpha=0.6, linewidth=1)
            ax.add_patch(rect)
    
    # Aggiungi linee di riferimento per debug
    # Linea altezza massima parete
    ax.axhline(y=bounds[3], color='red', linestyle='--', linewidth=2, 
               label=f'Max Y = {bounds[3]:.0f}mm')
    
    # Linea ultima riga problematica
    last_problematic_y = bounds[3] - 413  # Altezza blocco standard
    ax.axhline(y=last_problematic_y, color='orange', linestyle='--', linewidth=1,
               label=f'Ultima riga sicura = {last_problematic_y:.0f}mm')
    
    # Info nel grafico
    info_text = f"""RISULTATI:
• Parete: {bounds[2]-bounds[0]:.0f}×{bounds[3]-bounds[1]:.0f}mm
• Blocchi dentro: {blocks_inside}
• Blocchi fuori: {blocks_outside}
• Aperture: {len(aperture)}

PROBLEMA:
• Blocchi finiscono a y={bounds[3]-413:.0f}mm
• Altezza blocco: 413mm  
• Spazio rimanente: {bounds[3]-(bounds[3]-413+413):.0f}mm
• Blocchi escono sopra limite!"""
    
    ax.text(0.02, 0.98, info_text, transform=ax.transAxes,
            verticalalignment='top', fontfamily='monospace', 
            fontsize=10, bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
    
    # Imposta limiti
    margin = 200
    ax.set_xlim(bounds[0] - margin, bounds[2] + margin)
    ax.set_ylim(bounds[1] - margin, bounds[3] + margin + 500)  # Extra spazio sopra per vedere blocchi fuori
    
    ax.legend(loc='upper right')
    ax.grid(True, alpha=0.3)
    ax.set_xlabel('X (mm)')
    ax.set_ylabel('Y (mm)')
    
    # Salva
    plot_file = f"{title.lower()}_problem_visualization.png"
    plt.savefig(plot_file, dpi=150, bbox_inches='tight')
    plt.show()
    
    print(f"✅ Visualizzazione salvata: {plot_file}")
    print(f"📊 Blocchi dentro: {blocks_inside}, fuori: {blocks_outside}")
    
    return blocks_inside, blocks_outside


if __name__ == "__main__":
    print("🖼️ VISUALIZZAZIONE PROBLEMI PACKING")
    print("=" * 50)
    
    # Test entrambi i file
    files = [
        ("ROTTINI_LAY_REV0.svg", "Rottini"),
        ("FELICE_LAY_REV0.svg", "Felice")
    ]
    
    total_inside = 0
    total_outside = 0
    
    for svg_file, title in files:
        try:
            inside, outside = visualize_problem(svg_file, title)
            total_inside += inside
            total_outside += outside
        except Exception as e:
            print(f"❌ Errore {title}: {e}")
    
    print(f"\n📊 TOTALE:")
    print(f"   ✅ Blocchi corretti: {total_inside}")
    print(f"   ❌ Blocchi problematici: {total_outside}")
    print(f"   📈 Tasso errore: {total_outside/(total_inside+total_outside)*100:.1f}%")

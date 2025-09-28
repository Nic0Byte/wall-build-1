"""
Image export utilities.

This module contains functions for generating preview images of wall layouts,
extracted from dxf_exporter.py to maintain separation of concerns.
"""

from __future__ import annotations

import base64
import io
from typing import Dict, List, Optional

from shapely.geometry import Polygon, shape

try:
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    plt = None
    patches = None
    MATPLOTLIB_AVAILABLE = False

from exporters.labels import create_block_labels, create_detailed_block_labels


__all__ = ["generate_preview_image", "MATPLOTLIB_AVAILABLE"]


def generate_preview_image(wall_polygon: Polygon, 
                          placed: List[Dict], 
                          customs: List[Dict],
                          apertures: Optional[List[Polygon]] = None,
                          color_theme: Optional[Dict] = None,
                          block_config: Optional[Dict] = None,
                          width: int = 800,
                          height: int = 600) -> str:
    """Genera immagine preview come base64 string."""
    if not plt or not patches:
        return ""
    
    # Default colors se theme non fornito
    if not color_theme:
        color_theme = {}
    
    # Extract block configuration for custom dimensions
    if block_config:
        size_to_letter = block_config.get("size_to_letter", {})
        print(f" [DEBUG] Using custom block config: {block_config.get('block_widths', 'N/A')}x{block_config.get('block_height', 'N/A')}")
    else:
        size_to_letter = {}
        print(f" [DEBUG] No block config provided - using defaults")
    
    # Extract colors with fallbacks
    wall_color = color_theme.get('wallOutlineColor', '#1E40AF')
    wall_line_width = color_theme.get('wallLineWidth', 2)
    standard_block_color = color_theme.get('standardBlockColor', '#E5E7EB')
    standard_block_border = color_theme.get('standardBlockBorder', '#374151')
    custom_piece_color = color_theme.get('customPieceColor', '#F3E8FF')
    custom_piece_border = color_theme.get('customPieceBorder', '#7C3AED')
    door_window_color = color_theme.get('doorWindowColor', '#FEE2E2')
    door_window_border = color_theme.get('doorWindowBorder', '#DC2626')
    
    print(f" [DEBUG] Preview using colors: wall={wall_color}, blocks={standard_block_color}")
        
    try:
        # Setup figura
        fig, ax = plt.subplots(figsize=(width/100, height/100), dpi=100)
        ax.set_aspect('equal')
        
        # Bounds parete
        minx, miny, maxx, maxy = wall_polygon.bounds
        margin = max((maxx-minx), (maxy-miny)) * 0.05
        ax.set_xlim(minx - margin, maxx + margin)
        ax.set_ylim(miny - margin, maxy + margin)
        
        # Contorno parete
        x, y = wall_polygon.exterior.xy
        ax.plot(x, y, color=wall_color, linewidth=wall_line_width, label='Parete')
        
        # Labels per blocchi - NUOVO SISTEMA RAGGRUPPATO
        # Usa le dimensioni personalizzate se disponibili
        if block_config and size_to_letter:
            detailed_std_labels, detailed_custom_labels = create_detailed_block_labels(placed, customs, size_to_letter)
            print(f" [DEBUG] Using custom size_to_letter mapping: {size_to_letter}")
        else:
            detailed_std_labels, detailed_custom_labels = create_detailed_block_labels(placed, customs)
            print(f" [DEBUG] Using default size_to_letter mapping")
        
        # Blocchi standard con nuovo layout
        for i, blk in enumerate(placed):
            rect = patches.Rectangle(
                (blk['x'], blk['y']), blk['width'], blk['height'],
                facecolor=standard_block_color, edgecolor=standard_block_border, linewidth=0.5
            )
            ax.add_patch(rect)
            
            # Layout nuovo: categoria BL + numero TR (per immagini adattato)
            if i in detailed_std_labels:
                label_info = detailed_std_labels[i]
                category = label_info['display']['bottom_left']
                number = label_info['display']['top_right']
                
                # Posizioni adattate per preview
                bl_x = blk['x'] + blk['width'] * 0.1   # 10% da sinistra
                bl_y = blk['y'] + blk['height'] * 0.2  # 20% dal basso
                tr_x = blk['x'] + blk['width'] * 0.9   # 90% da sinistra 
                tr_y = blk['y'] + blk['height'] * 0.8  # 80% dal basso
                
                # Categoria (più grande)
                fontsize_cat = min(12, max(6, blk['width'] / 150))
                ax.text(bl_x, bl_y, category, ha='left', va='bottom',
                       fontsize=fontsize_cat, fontweight='bold', color='#dc2626')
                
                # Numero (più piccolo)
                fontsize_num = min(10, max(4, blk['width'] / 200))
                ax.text(tr_x, tr_y, number, ha='right', va='top',
                       fontsize=fontsize_num, fontweight='normal', color='#2563eb')
            else:
                # Fallback: etichetta centrata con mapping personalizzato se disponibile
                #  FIX: Usa mapping personalizzato se size_to_letter è presente
                if block_config and block_config.get('size_to_letter'):
                    std_labels_detailed, _ = create_detailed_block_labels(placed, customs, block_config.get('size_to_letter'))
                    std_labels = {i: label['full_label'] for i, label in std_labels_detailed.items()}
                else:
                    std_labels, _ = create_block_labels(placed, customs)
                cx = blk['x'] + blk['width'] / 2
                cy = blk['y'] + blk['height'] / 2
                fontsize = min(8, max(4, blk['width'] / 200))
                ax.text(cx, cy, std_labels.get(i, f"STD{i+1}"), ha='center', va='center', 
                       fontsize=fontsize, fontweight='bold', color='#1f2937')
        
        # Blocchi custom con nuovo layout
        for i, cust in enumerate(customs):
            try:
                poly = shape(cust['geometry'])
                patch = patches.Polygon(
                    list(poly.exterior.coords),
                    facecolor=custom_piece_color, edgecolor=custom_piece_border, 
                    linewidth=0.8, hatch='//', alpha=0.8
                )
                ax.add_patch(patch)
                
                # Layout nuovo: categoria BL + numero TR per custom
                if i in detailed_custom_labels:
                    label_info = detailed_custom_labels[i]
                    category = label_info['display']['bottom_left'] 
                    number = label_info['display']['top_right']
                    
                    # Posizioni adattate per preview custom
                    bl_x = cust['x'] + cust['width'] * 0.1
                    bl_y = cust['y'] + cust['height'] * 0.2
                    tr_x = cust['x'] + cust['width'] * 0.9
                    tr_y = cust['y'] + cust['height'] * 0.8
                    
                    # Categoria custom (verde)
                    fontsize_cat = min(10, max(5, cust['width'] / 120))
                    ax.text(bl_x, bl_y, category, ha='left', va='bottom',
                           fontsize=fontsize_cat, fontweight='bold', color='#16a34a')
                    
                    # Numero custom (più piccolo)
                    fontsize_num = min(8, max(4, cust['width'] / 150))
                    ax.text(tr_x, tr_y, number, ha='right', va='top',
                           fontsize=fontsize_num, fontweight='normal', color='#065f46')
                else:
                    # Fallback: etichetta centrata
                    _, custom_labels_fallback = create_block_labels([], customs)
                    cx = cust['x'] + cust['width'] / 2
                    cy = cust['y'] + cust['height'] / 2
                    label = custom_labels_fallback.get(i, f"CU{i+1}")
                    ax.text(cx, cy, label, ha='center', va='center', 
                           fontsize=6, fontweight='bold', color='#15803d')
            except Exception as e:
                print(f" Errore rendering custom {i}: {e}")
        
        # Aperture
        if apertures:
            for ap in apertures:
                x, y = ap.exterior.xy
                ax.plot(x, y, color=door_window_border, linestyle='--', linewidth=2)
                ax.fill(x, y, color=door_window_color, alpha=0.15)
        
        # Styling
        ax.set_title('Preview Costruzione Parete', fontsize=12, fontweight='bold', color='#1f2937')
        ax.grid(True, alpha=0.3, color='#9ca3af')
        ax.tick_params(axis='both', which='major', labelsize=8, colors='#6b7280')
        
        # Salva in memoria come base64
        img_buffer = io.BytesIO()
        fig.savefig(img_buffer, format='png', dpi=100, bbox_inches='tight', 
                   facecolor='white', edgecolor='none', pad_inches=0.1)
        img_buffer.seek(0)
        plt.close(fig)
        
        # Converti in base64
        img_base64 = base64.b64encode(img_buffer.getvalue()).decode('utf-8')
        return f"data:image/png;base64,{img_base64}"
        
    except Exception as e:
        print(f" Errore generazione preview: {e}")
        return ""
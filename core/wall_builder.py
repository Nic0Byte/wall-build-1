"""
Wall building and block packing algorithms.

This module contains the core algorithms for packing blocks into wall structures,
extracted from dxf_exporter.py to maintain separation of concerns.
"""

from __future__ import annotations

import math
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from shapely.geometry import Polygon, box, shape, mapping
from shapely.ops import unary_union

from utils.geometry_utils import snap, sanitize_polygon, ensure_multipolygon, polygon_holes
from utils.config import (
    AREA_EPS,
    BLOCK_HEIGHT,
    BLOCK_WIDTHS,
    COORD_EPS,
    KEEP_OUT_MM,
    MICRO_REST_MM,
    SCARTO_CUSTOM_MM,
    SIZE_TO_LETTER,
    SPLIT_MAX_WIDTH_MM,
)


__all__ = ["pack_wall", "opt_pass", "AlgorithmDebugger"]


class AlgorithmDebugger:
    """
    🔍 SISTEMA DEBUG ALGORITMO
    Traccia e mostra il ragionamento step-by-step dell'algoritmo di packing
    """
    
    def __init__(self, enable_debug: bool = False):
        self.enabled = enable_debug
        self.debug_data = {
            'algorithm_type': 'bidirectional',
            'rows_analysis': [],
            'decisions': [],
            'optimizations': [],
            'final_stats': {}
        }
    
    def log_algorithm_start(self, wall_bounds: tuple, block_widths: List[int], apertures_count: int):
        """Registra inizio algoritmo"""
        if not self.enabled:
            return
            
        self.debug_data['start_info'] = {
            'wall_dimensions': f"{wall_bounds[2]-wall_bounds[0]:.0f}×{wall_bounds[3]-wall_bounds[1]:.0f}mm",
            'wall_area': f"{(wall_bounds[2]-wall_bounds[0]) * (wall_bounds[3]-wall_bounds[1]) / 1000000:.1f}m²",
            'block_sizes': block_widths,
            'apertures_count': apertures_count,
            'algorithm': 'Bidirezionale (sinistra/destra alternato)'
        }
        
        print(f"🔍 DEBUG: Inizio algoritmo bidirezionale")
        print(f"   📏 Parete: {self.debug_data['start_info']['wall_dimensions']}")
        print(f"   📊 Area: {self.debug_data['start_info']['wall_area']}")
        print(f"   🧱 Blocchi: {block_widths}")
        print(f"   🚪 Aperture: {apertures_count}")
    
    def log_row_decision(self, row: int, direction: str, segments_count: int, reasoning: str):
        """Registra decisione per una riga"""
        if not self.enabled:
            return
            
        row_data = {
            'row_number': row,
            'direction': direction,
            'segments': segments_count,
            'reasoning': reasoning,
            'pattern': '←→' if direction == 'left_to_right' else '→←'
        }
        
        self.debug_data['rows_analysis'].append(row_data)
        
        print(f"🔄 RIGA {row}: {row_data['pattern']} direzione {direction}")
        print(f"   🧩 Segmenti: {segments_count}")
        print(f"   💭 Logica: {reasoning}")
    
    def log_segment_packing(self, row: int, segment_id: int, segment_width: float, 
                           blocks_placed: List[Dict], custom_pieces: List[Dict]):
        """Registra risultato packing di un segmento"""
        if not self.enabled:
            return
            
        placed_summary = []
        for block in blocks_placed:
            width = block.get('width', 0)
            placed_summary.append(f"{width}mm")
        
        custom_summary = []
        for custom in custom_pieces:
            width = custom.get('width', 0)
            custom_summary.append(f"{width:.0f}mm(custom)")
        
        segment_data = {
            'row': row,
            'segment': segment_id,
            'width': segment_width,
            'blocks': placed_summary,
            'customs': custom_summary,
            'efficiency': len(blocks_placed) / (len(blocks_placed) + len(custom_pieces)) if (blocks_placed or custom_pieces) else 0
        }
        
        if not hasattr(self, 'current_row_segments'):
            self.current_row_segments = []
        self.current_row_segments.append(segment_data)
        
        pattern_str = " | ".join(placed_summary + custom_summary)
        print(f"   🔧 Segmento {segment_id} ({segment_width:.0f}mm): [{pattern_str}]")
        if custom_pieces:
            print(f"      ✂️ Custom: {len(custom_pieces)} pezzi")
    
    def log_row_complete(self, row: int):
        """Completa analisi di una riga"""
        if not self.enabled:
            return
            
        if hasattr(self, 'current_row_segments'):
            # Aggiungi dati riga ai debug_data
            for row_data in self.debug_data['rows_analysis']:
                if row_data['row_number'] == row:
                    row_data['segments_data'] = self.current_row_segments
                    break
            
            # Reset per prossima riga
            self.current_row_segments = []
        
        print(f"✅ RIGA {row} completata")
    
    def log_optimization(self, optimization_type: str, description: str, benefit: str):
        """Registra ottimizzazione applicata"""
        if not self.enabled:
            return
            
        opt_data = {
            'type': optimization_type,
            'description': description,
            'benefit': benefit
        }
        
        self.debug_data['optimizations'].append(opt_data)
        print(f"⚡ OTTIMIZZAZIONE {optimization_type}: {description} → {benefit}")
    
    def log_final_stats(self, total_blocks: int, total_customs: int, efficiency: float, waste_ratio: float):
        """Registra statistiche finali"""
        if not self.enabled:
            return
            
        self.debug_data['final_stats'] = {
            'total_standard_blocks': total_blocks,
            'total_custom_pieces': total_customs,
            'efficiency_percent': efficiency * 100,
            'waste_ratio_percent': waste_ratio * 100,
            'standard_vs_custom_ratio': f"{total_blocks}:{total_customs}"
        }
        
        print(f"📊 RISULTATO FINALE:")
        print(f"   🧱 Blocchi standard: {total_blocks}")
        print(f"   ✂️ Pezzi custom: {total_customs}")
        print(f"   📈 Efficienza: {efficiency*100:.1f}%")
        print(f"   🗑️ Spreco: {waste_ratio*100:.1f}%")
    
    def get_debug_report(self) -> Dict:
        """Restituisce report completo per frontend"""
        return self.debug_data if self.enabled else {}


def _split_component_into_horizontal_segments(component: Polygon, y: float, stripe_top: float) -> List[Polygon]:
    """
    Divide una componente in segmenti orizzontali continui.
    Questo permette al greedy di lavorare su aree rettangolari anche con aperture.
    """
    segments = []
    
    # Ottieni bounds della componente
    minx, miny, maxx, maxy = component.bounds
    
    # Dividi in strisce verticali di larghezza minima blocco
    min_width = 413  # Larghezza minima blocco
    stripe_width = min_width * 2  # Larghezza strisce per segmentazione
    
    current_x = minx
    while current_x < maxx:
        next_x = min(current_x + stripe_width, maxx)
        
        # Crea rettangolo di test
        test_rect = box(current_x, y, next_x, stripe_top)
        
        # Intersezione con componente
        intersection = component.intersection(test_rect)
        
        if not intersection.is_empty and intersection.area > AREA_EPS:
            if isinstance(intersection, Polygon):
                segments.append(intersection)
            else:
                # MultiPolygon - aggiungi tutti i pezzi
                for geom in intersection.geoms:
                    if isinstance(geom, Polygon) and geom.area > AREA_EPS:
                        segments.append(geom)
        
        current_x = next_x
    
    return segments


def opt_pass(placed: List[Dict], custom: List[Dict], block_widths: List[int]) -> Tuple[List[Dict], List[Dict]]:
    """Hook di ottimizzazione (attualmente noop)."""
    return placed, custom


def _mk_std(x: float, y: float, w: int, h: int) -> Dict:
    return {"type": f"std_{w}x{h}", "width": w, "height": h, "x": snap(x), "y": snap(y)}


def _mk_custom(geom: Polygon, available_widths: List[int] = None) -> Dict:
    """Crea un pezzo custom con ottimizzazione del blocco sorgente."""
    geom = sanitize_polygon(geom)
    minx, miny, maxx, maxy = geom.bounds
    required_width = snap(maxx - minx)
    
    # 🎯 OTTIMIZZAZIONE: Trova il blocco che spreca meno materiale
    source_block_width = required_width  # Default fallback
    if available_widths:
        source_block_width = choose_optimal_source_block_for_custom(required_width, available_widths)
    
    return {
        "type": "custom",
        "width": required_width,
        "height": snap(maxy - miny),
        "x": snap(minx),
        "y": snap(miny),
        "geometry": mapping(geom),
        "source_block_width": source_block_width,  # NUOVO: blocco da cui tagliare
        "waste": source_block_width - required_width  # NUOVO: spreco calcolato
    }


def choose_optimal_source_block_for_custom(required_width: float, available_widths: List[int]) -> int:
    """
    🎯 OTTIMIZZAZIONE CUSTOM PIECES: Sceglie il blocco che minimizza lo spreco.
    
    Args:
        required_width: Larghezza richiesta per il pezzo custom (mm)
        available_widths: Lista blocchi standard disponibili (es. [3000, 1500, 700])
    
    Returns:
        Larghezza del blocco ottimale da cui tagliare (spreco minimo)
    """
    if not available_widths:
        return available_widths[0] if available_widths else required_width
    
    # Filtra solo blocchi abbastanza grandi
    suitable_blocks = [w for w in available_widths if w >= required_width]
    
    if not suitable_blocks:
        # Nessun blocco abbastanza grande - prendi il più grande disponibile
        print(f"⚠️ Custom {required_width:.0f}mm: nessun blocco sufficiente, uso {max(available_widths)}")
        return max(available_widths)
    
    # Trova il blocco con spreco minimo
    optimal_block = min(suitable_blocks, key=lambda w: w - required_width)
    waste = optimal_block - required_width
    
    print(f"✂️ Custom {required_width:.0f}mm: taglio da {optimal_block}mm (spreco: {waste:.0f}mm)")
    return optimal_block


def simulate_future_placement(total_space: float, first_block: int, widths_order: List[int], tolerance: float) -> dict:
    """
    🔮 SIMULAZIONE PREDITTIVA: Simula il piazzamento futuro per minimizzare spreco totale.
    
    Args:
        total_space: Spazio totale disponibile
        first_block: Primo blocco da piazzare
        widths_order: Blocchi disponibili
        tolerance: Tolleranza
    
    Returns:
        Dict con informazioni sulla simulazione (total_waste, blocks_count, etc.)
    """
    
    remaining = total_space - first_block
    placed_blocks = [first_block]
    
    # Algoritmo greedy per il resto dello spazio
    while remaining >= min(widths_order) + tolerance:
        best_fit = None
        
        # Trova il blocco più grande che entra
        for width in sorted(widths_order, reverse=True):
            if remaining >= width + tolerance:
                best_fit = width
                break
        
        if best_fit:
            placed_blocks.append(best_fit)
            remaining -= best_fit
        else:
            break
    
    # Calcola metriche della simulazione
    total_waste = remaining
    blocks_count = len(placed_blocks)
    efficiency = (total_space - total_waste) / total_space * 100
    
    return {
        'total_waste': total_waste,
        'blocks_count': blocks_count,
        'efficiency': efficiency,
        'blocks_sequence': placed_blocks,
        'final_remainder': remaining
    }


def _pack_segment_bidirectional(comp: Polygon, y: float, stripe_top: float, 
                               widths_order: List[int], direction: str = 'left_to_right',
                               debugger: Optional[AlgorithmDebugger] = None) -> Tuple[List[Dict], List[Dict]]:
    """
    🔄 ALGORITMO BIDIREZIONALE - NUOVO SISTEMA MATTONCINO
    
    Supporta due direzioni:
    - 'left_to_right': Da sinistra a destra (righe pari)
    - 'right_to_left': Da destra a sinistra (righe dispari)
    
    Questo crea un effetto mattoncino naturale senza offset artificiali!
    """
    placed: List[Dict] = []
    custom: List[Dict] = []

    seg_minx, _, seg_maxx, _ = comp.bounds
    seg_minx = snap(seg_minx)
    seg_maxx = snap(seg_maxx)
    y = snap(y)
    stripe_top = snap(stripe_top)

    if direction == 'left_to_right':
        # 🧱 DIREZIONE CLASSICA: Sinistra → Destra
        cursor = seg_minx
        
        while cursor < seg_maxx - COORD_EPS:
            spazio_rimanente = seg_maxx - cursor
            placed_one = False
            
            # Prova blocchi in ordine: più grande → più piccolo
            for block_width in widths_order:
                if block_width <= spazio_rimanente + COORD_EPS:
                    candidate = box(cursor, y, cursor + block_width, stripe_top)
                    intersec = candidate.intersection(comp)
                    
                    if not intersec.is_empty and intersec.area >= AREA_EPS:
                        if intersec.area / candidate.area >= 0.95:
                            # Blocco standard perfetto
                            placed.append(_mk_std(cursor, y, block_width, BLOCK_HEIGHT))
                            cursor = snap(cursor + block_width)
                            placed_one = True
                            break
                        else:
                            # Spazio non perfetto - crea pezzo custom
                            custom.append(_mk_custom(intersec, widths_order))
                            cursor = snap(cursor + block_width)
                            placed_one = True
                            break
            
            if not placed_one:
                # Spazio rimanente troppo piccolo per qualsiasi blocco standard
                if spazio_rimanente > MICRO_REST_MM:
                    remaining_box = box(cursor, y, seg_maxx, stripe_top)
                    remaining_intersec = remaining_box.intersection(comp)
                    if not remaining_intersec.is_empty and remaining_intersec.area >= AREA_EPS:
                        custom.append(_mk_custom(remaining_intersec, widths_order))
                break
                
    elif direction == 'right_to_left':
        # 🧱 DIREZIONE NUOVA: Destra → Sinistra
        cursor = seg_maxx
        
        while cursor > seg_minx + COORD_EPS:
            spazio_rimanente = cursor - seg_minx
            placed_one = False
            
            # Prova blocchi in ordine: più grande → più piccolo
            for block_width in widths_order:
                if block_width <= spazio_rimanente + COORD_EPS:
                    # Posiziona blocco DA DESTRA
                    candidate = box(cursor - block_width, y, cursor, stripe_top)
                    intersec = candidate.intersection(comp)
                    
                    if not intersec.is_empty and intersec.area >= AREA_EPS:
                        if intersec.area / candidate.area >= 0.95:
                            # Blocco standard perfetto
                            placed.append(_mk_std(cursor - block_width, y, block_width, BLOCK_HEIGHT))
                            cursor = snap(cursor - block_width)
                            placed_one = True
                            break
                        else:
                            # Spazio non perfetto - crea pezzo custom
                            custom.append(_mk_custom(intersec, widths_order))
                            cursor = snap(cursor - block_width)
                            placed_one = True
                            break
            
            if not placed_one:
                # Spazio rimanente troppo piccolo per qualsiasi blocco standard
                if spazio_rimanente > MICRO_REST_MM:
                    remaining_box = box(seg_minx, y, cursor, stripe_top)
                    remaining_intersec = remaining_box.intersection(comp)
                    if not remaining_intersec.is_empty and remaining_intersec.area >= AREA_EPS:
                        custom.append(_mk_custom(remaining_intersec, widths_order))
                break
    
    # Debug logging se disponibile
    if debugger:
        debugger.log_segment_packing(
            row=getattr(debugger, 'current_row', 0),
            segment_id=getattr(debugger, 'current_segment', 0),
            segment_width=seg_maxx - seg_minx,
            blocks_placed=placed,
            custom_pieces=custom
        )

    return placed, custom


def _pack_segment_with_order(comp: Polygon, y: float, stripe_top: float, widths_order: List[int], offset: int = 0) -> Tuple[List[Dict], List[Dict]]:
    """
    ALGORITMO GREEDY SEMPLICE - UNICO METODO DI POSIZIONAMENTO
    
    1. Vai da sinistra a destra
    2. Per ogni posizione, prova blocchi in ordine: più grande → più piccolo
    3. Usa il primo blocco che si adatta
    4. Se nessun blocco standard si adatta, crea un pezzo custom
    """
    placed: List[Dict] = []
    custom: List[Dict] = []

    seg_minx, _, seg_maxx, _ = comp.bounds
    seg_minx = snap(seg_minx)
    seg_maxx = snap(seg_maxx)
    y = snap(y)
    stripe_top = snap(stripe_top)

    cursor = seg_minx

    # Gestisci offset iniziale per pattern mattoncino
    if offset and cursor + offset <= seg_maxx + COORD_EPS:
        candidate = box(cursor, y, cursor + offset, stripe_top)
        intersec = candidate.intersection(comp)
        if not intersec.is_empty and intersec.area >= AREA_EPS:
            if intersec.area / candidate.area >= 0.95:
                placed.append(_mk_std(cursor, y, offset, BLOCK_HEIGHT))
            else:
                custom.append(_mk_custom(intersec, widths_order))
            cursor = snap(cursor + offset)

    # ===== ALGORITMO GREEDY SEMPLICE - UNICO ALGORITMO =====
    while cursor < seg_maxx - COORD_EPS:
        spazio_rimanente = seg_maxx - cursor
        placed_one = False
        
        # Prova blocchi in ordine di dimensione: più grande → più piccolo
        for block_width in widths_order:
            if block_width <= spazio_rimanente + COORD_EPS:
                candidate = box(cursor, y, cursor + block_width, stripe_top)
                intersec = candidate.intersection(comp)
                
                if not intersec.is_empty and intersec.area >= AREA_EPS:
                    if intersec.area / candidate.area >= 0.95:
                        # Blocco standard perfetto
                        placed.append(_mk_std(cursor, y, block_width, BLOCK_HEIGHT))
                        cursor = snap(cursor + block_width)
                        placed_one = True
                        break
                    else:
                        # Spazio non perfetto - crea pezzo custom
                        custom.append(_mk_custom(intersec, widths_order))
                        cursor = snap(cursor + block_width)
                        placed_one = True
                        break
        
        if not placed_one:
            # Spazio rimanente troppo piccolo per qualsiasi blocco standard
            # Crea un pezzo custom per il resto
            if spazio_rimanente > MICRO_REST_MM:
                remaining_box = box(cursor, y, seg_maxx, stripe_top)
                remaining_intersec = remaining_box.intersection(comp)
                if not remaining_intersec.is_empty and remaining_intersec.area >= AREA_EPS:
                    custom.append(_mk_custom(remaining_intersec, widths_order))
            break

    return placed, custom


def _pack_segment(comp: Polygon, y: float, stripe_top: float, widths: List[int], offset: int = 0) -> Tuple[List[Dict], List[Dict]]:
    """Packing semplice GREEDY: prima i blocchi più grandi."""
    
    # ORDINE FISSO: sempre dal più grande al più piccolo (GREEDY)
    greedy_order = sorted(widths, reverse=True)
    
    return _pack_segment_with_order(comp, y, stripe_top, greedy_order, offset=offset)


def _pack_segment_with_order_adaptive(comp: Polygon, y: float, stripe_top: float, 
                                     widths_order: List[int], adaptive_height: float, 
                                     offset: int = 0) -> Tuple[List[Dict], List[Dict]]:
    """
    Pack segment con ordine specifico e altezza adattiva.
    """
    minx, _, maxx, _ = comp.bounds
    actual_height = stripe_top - y
    
    # Usa altezza adattiva invece di quella standard
    effective_height = min(adaptive_height, actual_height)
    
    placed = []
    x = minx + offset
    
    while x < maxx:
        #  CONTROLLO DINAMICO ADATTIVO: Calcola spazio rimanente
        remaining_width = maxx - x
        
        # GREEDY SEMPLICE: usa primo blocco che si adatta
        optimal_width = None
        for width in widths_order:
            if remaining_width >= width - 5.0:
                optimal_width = width
                break
        
        # Fallback al controllo dinamico semplice
        if optimal_width is None:
            # FALLBACK GIA GESTITO SOPRA - optimal_width rimane None
            pass
        
        best_width = None
        
        if optimal_width is not None:
            # Prova prima il blocco ottimale
            if x + optimal_width <= maxx:
                candidate = box(x, y, x + optimal_width, y + effective_height)
                if comp.contains(candidate):
                    best_width = optimal_width
        
        # Se il blocco ottimale non funziona, fallback all'algoritmo originale
        if best_width is None:
            for width in widths_order:
                if x + width <= maxx:
                    candidate = box(x, y, x + width, y + effective_height)
                    if comp.contains(candidate):
                        best_width = width
                        break
        
        if best_width is not None:
            placed.append({
                "x": snap(x),
                "y": snap(y),
                "width": best_width,
                "height": snap(effective_height),  # Altezza adattiva!
                "type": f"adaptive_block_{best_width}"
            })
            x += best_width
        else:
            x += min(widths_order)  # Incremento minimo
    
    # Calcola area rimanente per custom pieces
    remaining = comp
    for block in placed:
        block_box = box(block["x"], block["y"], 
                       block["x"] + block["width"], 
                       block["y"] + block["height"])
        remaining = remaining.difference(block_box)
    
    # Genera custom pieces dall'area rimanente
    custom = []
    if remaining.area > AREA_EPS:
        if isinstance(remaining, Polygon):
            custom.append(_mk_custom(remaining))
        else:
            for geom in remaining.geoms:
                if geom.area > AREA_EPS:
                    custom.append(_mk_custom(geom))
    
    return placed, custom


def pack_wall(polygon: Polygon,
              block_widths: List[int],
              block_height: int,
              row_offset: Optional[int] = None,  # Deprecato: mantenuto per compatibilità
              apertures: Optional[List[Polygon]] = None,
              enable_debug: bool = False) -> Tuple[List[Dict], List[Dict]]:
    """
    🔄 PACKER PRINCIPALE CON ALGORITMO BIDIREZIONALE
    
    NOVITÀ: 
    - Algoritmo bidirezionale (sinistra/destra alternato) 
    - row_offset deprecato (ignorato)
    - Sistema debug integrato
    - Effetto mattoncino naturale
    """
    
    # Inizializza debugger
    debugger = AlgorithmDebugger(enable_debug)
    debugger.log_algorithm_start(polygon.bounds, block_widths, len(apertures) if apertures else 0)
    
    if row_offset is not None:
        debugger.log_optimization(
            "OFFSET_DEPRECATION", 
            f"row_offset={row_offset} ignorato", 
            "Algoritmo bidirezionale elimina necessità di offset manuale"
        )
    
    print(f"� NUOVO ALGORITMO BIDIREZIONALE:")
    print(f"   📏 Polygon bounds: {polygon.bounds}")
    print(f"   📐 Polygon area: {polygon.area}")
    print(f"   🔲 Polygon valid: {polygon.is_valid}")
    print(f"   📦 Block widths: {block_widths}")
    print(f"   📏 Block height: {block_height}")
    print(f"   🚪 Aperture: {len(apertures) if apertures else 0}")
    print(f"   � Debug: {'ATTIVO' if enable_debug else 'DISATTIVO'}")
    
    polygon = sanitize_polygon(polygon)

    # Aperture dal poligono + eventuali passate a parte
    hole_polys = polygon_holes(polygon)
    ap_list = list(apertures) if apertures else []
    print(f"   🕳️ Holes nel poligono: {len(hole_polys)}")
    print(f"   🚪 Aperture passate: {len(ap_list)}")
    
    # FILTRO CRITICO: Escludi aperture troppo grandi (probabilmente la parete stessa)
    wall_area = polygon.area
    valid_apertures = []
    for i, ap in enumerate(ap_list):
        ap_area = ap.area
        area_ratio = ap_area / wall_area
        print(f"   🔍 Apertura {i}: area={ap_area:.0f}, ratio={area_ratio:.3f}")
        
        if area_ratio > 0.8:  # Se copre più dell'80% è probabilmente la parete stessa
            print(f"   ❌ Apertura {i} SCARTATA: troppo grande (ratio {area_ratio:.1%})")
            continue
        
        if ap_area < 1000:  # Scarta aperture troppo piccole (< 1m²)
            print(f"   ❌ Apertura {i} SCARTATA: troppo piccola ({ap_area:.0f}mm²)")
            continue
            
        valid_apertures.append(ap)
        print(f"   ✅ Apertura {i} VALIDA: {ap_area:.0f}mm² ({area_ratio:.1%})")
    
    print(f"   📊 Aperture valide: {len(valid_apertures)} su {len(ap_list)}")
    
    keepout = None
    if hole_polys or valid_apertures:
        u = unary_union([*hole_polys, *valid_apertures])
        # TEMPORANEO: No buffer per testare
        keepout = u if not u.is_empty else None
        print(f"   ⚠️ BUFFER DISABILITATO per test")
        print(f"   🔲 Area keepout: {keepout.area if keepout else 0:.2f}")
        print(f"   📐 Area poligono: {polygon.area:.2f}")
        if keepout:
            coverage = (keepout.area / polygon.area) * 100
            print(f"   📊 Copertura keepout: {coverage:.1f}%")
    else:
        print(f"   ✅ Nessuna apertura valida trovata")

    minx, miny, maxx, maxy = polygon.bounds
    placed_all: List[Dict] = []
    custom_all: List[Dict] = []

    # CALCOLO OTTIMIZZATO: Determina righe complete e spazio residuo
    total_height = maxy - miny
    complete_rows = int(total_height / block_height)
    remaining_space = total_height - (complete_rows * block_height)
    
    print(f"📊 Algoritmo adattivo: {complete_rows} righe complete, {remaining_space:.0f}mm rimanenti")

    y = miny
    row = 0

    # FASE 1: Processa righe complete con altezza standard
    while row < complete_rows:
        print(f"🔄 Processando riga {row}: y={y:.1f} -> {y + block_height:.1f}")
        
        stripe_top = y + block_height
        stripe = box(minx, y, maxx, stripe_top)
        inter = polygon.intersection(stripe)
        if keepout:
            inter = inter.difference(keepout)

        comps = ensure_multipolygon(inter)
        print(f"   📊 Componenti trovate: {len(comps)}")

        for i, comp in enumerate(comps):
            if comp.is_empty or comp.area < AREA_EPS:
                print(f"   ⚠️ Componente {i} vuota o troppo piccola (area={comp.area:.2f})")
                continue
            
            # ===== NUOVO ALGORITMO BIDIREZIONALE =====
            print(f"   🔧 Processando componente {i}: bounds={comp.bounds}, area={comp.area:.2f}")

            # Determina direzione per algoritmo bidirezionale
            if row % 2 == 0:
                # Riga pari: da sinistra a destra
                direction = 'left_to_right'
                reasoning = "Riga pari - direzione naturale sinistra→destra"
                print(f"   🧱 Riga PARI {row}: ←→ sinistra → destra")
            else:
                # Riga dispari: da destra a sinistra per effetto mattoncino
                direction = 'right_to_left'  
                reasoning = "Riga dispari - inversione per pattern mattoncino naturale"
                print(f"   🧱 Riga DISPARI {row}: →← destra → sinistra")

            # Debug logging
            debugger.current_row = row
            debugger.current_segment = i
            debugger.log_row_decision(row, direction, len(comps), reasoning)

            # NUOVO ALGORITMO: Bidirezionale con debug
            placed_row, custom_row = _pack_segment_bidirectional(
                comp, y, stripe_top, 
                sorted(block_widths, reverse=True),  # GREEDY: grande → piccolo
                direction=direction,
                debugger=debugger
            )
            
            print(f"   ✅ Risultato: {len(placed_row)} placed, {len(custom_row)} custom")
            placed_all.extend(placed_row)
            custom_all.extend(custom_row)

        y = snap(y + block_height)
        row += 1
        
    print(f"✅ FASE 1 completata: {len(placed_all)} blocchi standard totali")

    # FASE 2: Riga adattiva se spazio sufficiente
    if remaining_space >= 150:  # Minimo ragionevole per blocchi
        adaptive_height = min(remaining_space, block_height)
        print(f"🔄 Riga adattiva {row}: altezza={adaptive_height:.0f}mm")
        
        stripe_top = y + adaptive_height
        stripe = box(minx, y, maxx, stripe_top)
        inter = polygon.intersection(stripe)
        if keepout:
            inter = inter.difference(keepout)

        comps = ensure_multipolygon(inter)

        for comp in comps:
            if comp.is_empty or comp.area < AREA_EPS:
                continue

            # ===== GREEDY SEMPLICE ANCHE PER RIGA ADATTIVA =====
            # Determina offset per pattern mattoncino
            if row % 2 == 0:
                # Riga pari: inizia da sinistra
                offset = 0
            else:
                # Riga dispari: usa offset per pattern mattoncino  
                offset = row_offset if row_offset is not None else min(block_widths)

            # CHIAMATA DIRETTA SENZA CONFRONTI
            placed_row, custom_row = _pack_segment_with_order_adaptive(
                comp, y, stripe_top, 
                sorted(block_widths, reverse=True),  # GREEDY: grande → piccolo
                adaptive_height, 
                offset=offset
            )
            
            placed_all.extend(placed_row)
            custom_all.extend(custom_row)
    else:
        print(f"⚠️ Spazio rimanente {remaining_space:.0f}mm insufficiente per riga adattiva")

    custom_all = merge_customs_row_aware(custom_all, tol=SCARTO_CUSTOM_MM, row_height=BLOCK_HEIGHT)
    custom_all = split_out_of_spec(custom_all, max_w=SPLIT_MAX_WIDTH_MM)
    validated_customs = validate_and_tag_customs(custom_all)
    
    # Log statistiche finali per il debug
    total_wall_area = polygon.area
    total_blocks_area = sum(block.get('width', 0) * block.get('height', 0) for block in placed_all)
    total_custom_area = sum(custom.get('width', 0) * custom.get('height', 0) for custom in validated_customs)
    
    efficiency = total_blocks_area / (total_blocks_area + total_custom_area) if (total_blocks_area + total_custom_area) > 0 else 0
    waste_ratio = 1 - ((total_blocks_area + total_custom_area) / total_wall_area) if total_wall_area > 0 else 0
    
    debugger.log_final_stats(len(placed_all), len(validated_customs), efficiency, waste_ratio)
    
    print(f"📊 ALGORITMO BIDIREZIONALE COMPLETATO:")
    print(f"   🧱 Blocchi standard: {len(placed_all)}")
    print(f"   ✂️ Pezzi custom: {len(validated_customs)}")
    print(f"   📈 Efficienza: {efficiency*100:.1f}%")
    print(f"   🗑️ Spreco: {waste_ratio*100:.1f}%")
    
    return placed_all, validated_customs


def merge_customs_row_aware(customs: List[Dict], tol: float = 5, row_height: int = 495) -> List[Dict]:
    """
    Coalesco customs solo all'interno della stessa fascia orizzontale.
    """
    if not customs:
        return []
    rows: Dict[int, List[Polygon]] = defaultdict(list)
    for c in customs:
        y0 = snap(c["y"])
        row_id = int(round(y0 / row_height))
        poly = shape(c["geometry"]).buffer(0)
        rows[row_id].append(poly)

    out: List[Dict] = []
    for rid, polys in rows.items():
        if not polys:
            continue
        merged = unary_union(polys)
        geoms = [merged] if isinstance(merged, Polygon) else list(merged.geoms)
        for g in geoms:
            if g.area > AREA_EPS:
                out.append(_mk_custom(g))
    return out


def split_out_of_spec(customs: List[Dict], max_w: int = 413, max_h: int = 495) -> List[Dict]:
    """Divide ogni pezzo 'out_of_spec' in più slice verticali."""
    out: List[Dict] = []
    for c in customs:
        w = int(round(c.get("width", 0)))
        h = int(round(c.get("height", 0)))
        if (w <= max_w + SCARTO_CUSTOM_MM) and (h <= max_h + SCARTO_CUSTOM_MM):
            out.append(c)
            continue

        poly = shape(c["geometry"]).buffer(0)
        if poly.is_empty or poly.area <= AREA_EPS:
            continue
        minx, miny, maxx, maxy = poly.bounds

        x0 = minx
        while x0 < maxx - COORD_EPS:
            x1 = min(x0 + max_w, maxx)
            strip = box(x0, miny, x1, maxy)
            piece = poly.intersection(strip).buffer(0)
            if not piece.is_empty and piece.area > AREA_EPS:
                out.append(_mk_custom(piece))
            x0 = x1
    return out


def validate_and_tag_customs(custom: List[Dict]) -> List[Dict]:
    """
    Regole custom: Type 1 ("larghezza"), Type 2 ("flex").
    AGGIORNATO: i blocchi custom possono nascere da tutti i tipi di blocco standard.
    """
    out = []
    max_standard_width = max(BLOCK_WIDTHS)  # 1239mm (blocco grande)
    
    for c in custom:
        w = int(round(c["width"]))
        h = int(round(c["height"]))
        
        # Controlla se supera i limiti massimi (fuori specifica)
        if w >= max_standard_width + SCARTO_CUSTOM_MM or h > 495 + SCARTO_CUSTOM_MM:
            c["ctype"] = "out_of_spec"
            out.append(c)
            continue
        
        # Type 1: blocchi derivati da qualsiasi blocco standard (altezza ≈ 495mm)
        # Ora può essere tagliato da blocchi piccoli, medi, grandi o standard
        if abs(h - 495) <= SCARTO_CUSTOM_MM and w <= max_standard_width + SCARTO_CUSTOM_MM:
            c["ctype"] = 1
        else:
            # Type 2: blocchi con altezza diversa (flex)
            c["ctype"] = 2
        
        out.append(c)
    return out
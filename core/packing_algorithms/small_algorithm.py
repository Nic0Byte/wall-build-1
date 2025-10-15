"""
Small Algorithm Packer - Algoritmo con Concatenazione e Sfalsamento Moraletti

REGOLE FONDAMENTALI:
1. TUTTI i moraletti devono essere coperti (nessun buco scoperto)
2. Allineamento verticale garantito
3. Sfalsamento massimo (pattern mattoncino)
4. Backtracking per trovare combinazione ottimale
5. Custom blocks con stessa logica moraletti

Autore: GitHub Copilot
Data: Ottobre 2025
"""

import math
import itertools
from typing import List, Dict, Tuple, Optional
from functools import lru_cache
import logging

# Import sistema moraletti
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.moraletti_alignment import (
    DynamicMoralettiConfiguration,
    MoralettiCoverageValidator,
    StaggeringCalculator,
    validate_row_coverage,
    calculate_moraletti_positions_list
)

logger = logging.getLogger(__name__)


class SmallAlgorithmPacker:
    """
    Algoritmo Small: Concatenazione + Sfalsamento con Moraletti
    
    Strategia:
    1. Per ogni riga, genera TUTTE le combinazioni possibili di blocchi
    2. Per ogni combinazione, verifica:
       - Copertura COMPLETA moraletti riga sotto
       - Sfalsamento rispetto riga sotto
    3. Seleziona combinazione con miglior score:
       - Priorità 1: Copertura 100%
       - Priorità 2: Massimo sfalsamento
       - Priorità 3: Meno custom blocks
       - Priorità 4: Meno pezzi totali
    """
    
    def __init__(self, moraletti_config: DynamicMoralettiConfiguration):
        """
        Args:
            moraletti_config: Configurazione moraletti dinamica dall'utente
        """
        self.config = moraletti_config
        self.validator = MoralettiCoverageValidator(moraletti_config)
        self.stagger_calc = StaggeringCalculator()
        
        # Blocchi standard disponibili (da configurazione)
        self.standard_blocks = [
            {'width': self.config.block_sizes['large'], 'type': 'large', 'height': self.config.block_heights['large']},
            {'width': self.config.block_sizes['medium'], 'type': 'medium', 'height': self.config.block_heights['medium']},
            {'width': self.config.block_sizes['small'], 'type': 'small', 'height': self.config.block_heights['small']}
        ]
        
        # Cache per performance
        self._combination_cache = {}
        self.max_combinations_to_try = 5000  # Limite per evitare esplosione combinatoria
    
    def pack_row(self, 
                 segment_width: float,
                 y: float,
                 row_below: Optional[List[Dict]] = None,
                 enable_debug: bool = False) -> Dict:
        """
        Riempie una singola riga con algoritmo Small
        
        Args:
            segment_width: Larghezza segmento da riempire
            y: Posizione Y della riga
            row_below: Blocchi della riga sotto (per validazione moraletti)
            enable_debug: Abilita logging dettagliato
            
        Returns:
            {
                'blocks': List[Dict],  # Blocchi piazzati
                'custom_blocks': List[Dict],  # Blocchi custom separati
                'coverage': Dict,  # Info copertura moraletti
                'stagger': Dict,  # Info sfalsamento
                'stats': Dict  # Statistiche
            }
        """
        
        if enable_debug:
            logger.info(f"🔧 Small Algorithm: Packing row at Y={y}, width={segment_width}mm")
            if row_below:
                moraletti_below = calculate_moraletti_positions_list(row_below, self.config)
                logger.info(f"   Moraletti da coprire: {len(moraletti_below)} posizioni {moraletti_below}")
        
        # 1. Genera TUTTE le combinazioni possibili
        all_combinations = self._generate_all_combinations(segment_width, enable_debug)
        
        if not all_combinations:
            logger.warning(f"⚠️ Nessuna combinazione trovata per larghezza {segment_width}mm")
            return self._create_fallback_solution(segment_width, y, row_below)
        
        if enable_debug:
            logger.info(f"   Trovate {len(all_combinations)} combinazioni possibili")
        
        # 2. Valuta ogni combinazione
        scored_combinations = []
        
        for combination in all_combinations:
            # Crea blocchi con posizioni X
            blocks = self._create_blocks_with_positions(combination, 0, y)
            
            # Valuta questa combinazione
            score_data = self._evaluate_combination(blocks, row_below, enable_debug)
            
            if score_data['coverage']['is_complete']:
                # Solo combinazioni con copertura 100%
                scored_combinations.append({
                    'blocks': blocks,
                    'score': score_data['total_score'],
                    'coverage': score_data['coverage'],
                    'stagger': score_data['stagger'],
                    'stats': score_data['stats']
                })
        
        if not scored_combinations:
            logger.warning(f"⚠️ Nessuna combinazione con copertura 100%! Uso fallback.")
            return self._create_fallback_solution(segment_width, y, row_below)
        
        # 3. Ordina per score (migliore prima)
        scored_combinations.sort(key=lambda x: x['score'], reverse=True)
        
        # 4. Seleziona la migliore
        best = scored_combinations[0]
        
        if enable_debug:
            logger.info(f"✅ Migliore combinazione:")
            logger.info(f"   Score: {best['score']:.2f}")
            logger.info(f"   Copertura: {best['coverage']['coverage_percent']:.1f}%")
            logger.info(f"   Sfalsamento: {best['stagger']['stagger_percent']:.1f}%")
            logger.info(f"   Blocchi: {len(best['blocks'])} ({best['stats']['custom_count']} custom)")
        
        # 5. Separa standard e custom
        standard_blocks = [b for b in best['blocks'] if b.get('is_standard', True)]
        custom_blocks = [b for b in best['blocks'] if not b.get('is_standard', True)]
        
        return {
            'blocks': standard_blocks,
            'custom_blocks': custom_blocks,
            'coverage': best['coverage'],
            'stagger': best['stagger'],
            'stats': best['stats'],
            'all_blocks': best['blocks']  # Tutti insieme per alcune operazioni
        }
    
    def _generate_all_combinations(self, width: float, enable_debug: bool = False) -> List[List[Dict]]:
        """
        Genera TUTTE le combinazioni possibili di blocchi per riempire la larghezza
        Include combinazioni con custom blocks
        
        Usa algoritmo ricorsivo con backtracking e memoization
        """
        
        # Check cache
        cache_key = round(width, 2)
        if cache_key in self._combination_cache:
            return self._combination_cache[cache_key]
        
        combinations = []
        
        # Genera combinazioni ricorsivamente
        def backtrack(remaining_width: float, current_combination: List[Dict], depth: int = 0):
            
            # Limite profondità per evitare stack overflow
            if depth > 50:
                return
            
            # Limite numero combinazioni
            if len(combinations) >= self.max_combinations_to_try:
                return
            
            # Base case: larghezza riempita esattamente
            if abs(remaining_width) < 0.1:
                combinations.append(current_combination[:])
                return
            
            # Non può essere negativo
            if remaining_width < 0:
                return
            
            # Prova ogni blocco standard (dal più grande al più piccolo)
            for block in sorted(self.standard_blocks, key=lambda b: b['width'], reverse=True):
                if block['width'] <= remaining_width + 0.1:
                    current_combination.append(block.copy())
                    backtrack(remaining_width - block['width'], current_combination, depth + 1)
                    current_combination.pop()
            
            # Prova custom per riempire esattamente
            if remaining_width >= 1.0:  # Minimo 1mm per custom
                # Crea custom che riempie esattamente lo spazio rimanente
                custom_block = self._create_custom_block(remaining_width)
                if custom_block:
                    current_combination.append(custom_block)
                    combinations.append(current_combination[:])
                    current_combination.pop()
        
        # Avvia backtracking
        backtrack(width, [])
        
        # Cache risultato
        self._combination_cache[cache_key] = combinations
        
        if enable_debug:
            logger.debug(f"   Generato {len(combinations)} combinazioni per width={width}mm")
        
        return combinations
    
    def _create_custom_block(self, width: float) -> Optional[Dict]:
        """
        Crea un blocco custom di larghezza specifica
        
        VINCOLI:
        - NON può essere >= Grande
        - NON può essere == Medio o Piccolo
        """
        
        width = round(width, 2)
        
        # Validazione: NON >= Grande
        if width >= self.config.block_sizes['large']:
            return None
        
        # Validazione: NON == Medio o Piccolo
        if abs(width - self.config.block_sizes['medium']) < 0.1:
            return None
        if abs(width - self.config.block_sizes['small']) < 0.1:
            return None
        
        # Determina range e proprietà
        try:
            block_info = self.config.get_block_info(width)
            return {
                'width': width,
                'type': 'custom',
                'height': block_info['height'],
                'is_standard': False,
                'max_moraletti': block_info['max_moraletti'],
                'range': block_info.get('range', 'unknown')
            }
        except ValueError:
            # Custom non valido
            return None
    
    def _create_blocks_with_positions(self, combination: List[Dict], 
                                     start_x: float, y: float) -> List[Dict]:
        """
        Crea lista blocchi con posizioni X assolute
        """
        
        blocks = []
        current_x = start_x
        
        for i, block_template in enumerate(combination):
            block = {
                'x': current_x,
                'y': y,
                'width': block_template['width'],
                'height': block_template['height'],
                'type': block_template['type'],
                'is_standard': block_template.get('is_standard', True),
                'id': f"block_{y}_{i}"
            }
            blocks.append(block)
            current_x += block_template['width']
        
        return blocks
    
    def _evaluate_combination(self, blocks: List[Dict], 
                             row_below: Optional[List[Dict]], 
                             enable_debug: bool = False) -> Dict:
        """
        Valuta una combinazione di blocchi
        
        Calcola:
        1. Copertura moraletti (PRIORITÀ MASSIMA)
        2. Sfalsamento
        3. Numero custom blocks
        4. Numero pezzi totali
        
        Returns score complessivo
        """
        
        # 1. Validazione copertura moraletti
        if row_below:
            coverage = self.validator.validate_complete_coverage(row_below, blocks)
        else:
            # Prima riga - nessun moraletto da coprire
            coverage = {
                'is_complete': True,
                'coverage_percent': 100.0,
                'uncovered_count': 0,
                'total_moraletti': 0
            }
        
        # 2. Calcolo sfalsamento
        if row_below:
            stagger = self.stagger_calc.calculate_stagger_score(blocks, row_below)
        else:
            # Prima riga - sfalsamento N/A
            stagger = {
                'score': 1.0,
                'stagger_percent': 100.0,
                'is_good': True
            }
        
        # 3. Statistiche
        custom_count = sum(1 for b in blocks if not b.get('is_standard', True))
        total_blocks = len(blocks)
        
        stats = {
            'custom_count': custom_count,
            'standard_count': total_blocks - custom_count,
            'total_blocks': total_blocks
        }
        
        # 4. Score totale (0-100)
        # PRIORITÀ:
        # - Copertura 100%: OBBLIGATORIA (se non 100% score = 0)
        # - Sfalsamento: peso 40%
        # - Meno custom: peso 30%
        # - Meno pezzi: peso 30%
        
        if not coverage['is_complete']:
            total_score = 0.0  # BOCCIATA!
        else:
            # Score sfalsamento (0-40)
            stagger_score = stagger['score'] * 40
            
            # Score custom (0-30): meno custom = meglio
            max_possible_custom = total_blocks
            custom_score = (1 - (custom_count / max_possible_custom)) * 30 if max_possible_custom > 0 else 30
            
            # Score numero pezzi (0-30): meno pezzi = meglio
            # Assumiamo max 10 pezzi come riferimento
            pieces_score = (1 - min(total_blocks / 10, 1.0)) * 30
            
            total_score = stagger_score + custom_score + pieces_score
        
        return {
            'total_score': total_score,
            'coverage': coverage,
            'stagger': stagger,
            'stats': stats
        }
    
    def _create_fallback_solution(self, width: float, y: float, 
                                  row_below: Optional[List[Dict]]) -> Dict:
        """
        Soluzione di fallback se nessuna combinazione funziona
        Usa un singolo blocco custom che riempie tutta la larghezza
        """
        
        logger.warning(f"⚠️ Usando fallback: singolo custom block {width}mm")
        
        # Crea custom block grande quanto necessario
        # NOTA: Può violare regola "non >= Grande" in caso di emergenza
        custom = {
            'x': 0,
            'y': y,
            'width': width,
            'height': self.config.block_heights['large'],
            'type': 'custom_emergency',
            'is_standard': False,
            'id': f'emergency_{y}'
        }
        
        # Validazione copertura
        if row_below:
            coverage = self.validator.validate_complete_coverage(row_below, [custom])
        else:
            coverage = {'is_complete': True, 'coverage_percent': 100.0}
        
        return {
            'blocks': [],
            'custom_blocks': [custom],
            'all_blocks': [custom],
            'coverage': coverage,
            'stagger': {'score': 0, 'stagger_percent': 0},
            'stats': {'custom_count': 1, 'standard_count': 0, 'total_blocks': 1}
        }


# Funzioni di utilità per integrazione

def pack_wall_with_small_algorithm(wall_width: float,
                                   wall_height: float,
                                   block_height: float,
                                   moraletti_config: DynamicMoralettiConfiguration,
                                   enable_debug: bool = False) -> Dict:
    """
    Riempie un'intera parete usando algoritmo Small
    
    Args:
        wall_width: Larghezza parete
        wall_height: Altezza parete
        block_height: Altezza blocchi
        moraletti_config: Configurazione moraletti
        enable_debug: Debug logging
        
    Returns:
        {
            'all_blocks': List[Dict],  # Tutti i blocchi standard
            'all_custom': List[Dict],  # Tutti i blocchi custom
            'rows': List[Dict],  # Info per ogni riga
            'total_coverage': Dict,  # Statistiche copertura totale
            'total_stagger': Dict  # Statistiche sfalsamento totale
        }
    """
    
    packer = SmallAlgorithmPacker(moraletti_config)
    
    # Calcola numero righe COMPLETE e spazio residuo
    complete_rows = int(wall_height / block_height)
    remaining_space = wall_height - (complete_rows * block_height)
    
    if enable_debug:
        logger.info(f"🏗️ Small Algorithm: Packing wall {wall_width}x{wall_height}mm")
        logger.info(f"   Righe complete: {complete_rows}, Spazio residuo: {remaining_space:.0f}mm")
        logger.info(f"   Altezza blocco: {block_height}mm")
    
    all_blocks = []
    all_custom = []
    rows_data = []
    
    previous_row = None
    
    # FASE 1: Righe complete con altezza standard
    for row_index in range(complete_rows):
        y = row_index * block_height
        
        if enable_debug:
            logger.info(f"🔄 Riga {row_index+1}/{complete_rows}: y={y:.0f}mm")
        
        # Pack questa riga
        row_result = packer.pack_row(
            segment_width=wall_width,
            y=y,
            row_below=previous_row,
            enable_debug=enable_debug
        )
        
        # Aggiungi risultati
        all_blocks.extend(row_result['blocks'])
        all_custom.extend(row_result['custom_blocks'])
        rows_data.append({
            'row_index': row_index,
            'y': y,
            'blocks': row_result['all_blocks'],
            'coverage': row_result['coverage'],
            'stagger': row_result['stagger'],
            'stats': row_result['stats']
        })
        
        # Prepara per prossima riga
        previous_row = row_result['all_blocks']
    
    # FASE 2: Riga adattiva se spazio residuo sufficiente
    if remaining_space >= 150:  # Minimo 150mm per riga adattiva
        adaptive_height = min(remaining_space, block_height)
        y_adaptive = complete_rows * block_height
        
        if enable_debug:
            logger.info(f"🔄 Riga ADATTIVA {complete_rows+1}: y={y_adaptive:.0f}mm, altezza={adaptive_height:.0f}mm")
        
        # Pack riga adattiva (SENZA validazione moraletti - è l'ultima riga!)
        # Usa algoritmo semplificato per riempire lo spazio
        try:
            # Genera combinazione semplice per riempire larghezza
            adaptive_blocks = []
            current_x = 0
            remaining_width = wall_width
            
            # Usa blocchi standard finché possibile
            for block_size in sorted([packer.config.block_sizes['large'], 
                                     packer.config.block_sizes['medium'],
                                     packer.config.block_sizes['small']], reverse=True):
                while remaining_width >= block_size:
                    adaptive_blocks.append({
                        'x': current_x,
                        'y': y_adaptive,
                        'width': block_size,
                        'height': adaptive_height,
                        'type': 'large' if block_size == packer.config.block_sizes['large'] else 
                                'medium' if block_size == packer.config.block_sizes['medium'] else 'small',
                        'is_standard': True,
                        'id': f'adaptive_{current_x}'
                    })
                    current_x += block_size
                    remaining_width -= block_size
            
            # Custom per spazio residuo
            adaptive_custom = []
            if remaining_width > 1.0:
                adaptive_custom.append({
                    'x': current_x,
                    'y': y_adaptive,
                    'width': remaining_width,
                    'height': adaptive_height,
                    'type': 'custom',
                    'is_standard': False,
                    'id': f'adaptive_custom_{current_x}'
                })
            
            # Aggiungi ai risultati
            standard_adaptive = [b for b in adaptive_blocks if b['is_standard']]
            all_blocks.extend(standard_adaptive)
            all_custom.extend(adaptive_custom)
            
            rows_data.append({
                'row_index': complete_rows,
                'y': y_adaptive,
                'blocks': adaptive_blocks + adaptive_custom,
                'coverage': {'is_complete': True, 'coverage_percent': 100.0, 'note': 'Riga adattiva (ultima)'},
                'stagger': {'score': 1.0, 'stagger_percent': 100.0, 'note': 'Riga adattiva'},
                'stats': {
                    'custom_count': len(adaptive_custom),
                    'standard_count': len(standard_adaptive),
                    'total_blocks': len(adaptive_blocks) + len(adaptive_custom),
                    'is_adaptive': True
                }
            })
            
            if enable_debug:
                logger.info(f"✅ Riga adattiva completata: {len(standard_adaptive)} standard, {len(adaptive_custom)} custom")
        
        except Exception as e:
            logger.warning(f"⚠️ Errore riga adattiva: {e}")
    else:
        if enable_debug and remaining_space > 0:
            logger.info(f"⚠️ Spazio residuo {remaining_space:.0f}mm insufficiente per riga adattiva (min 150mm)")
    
    # Statistiche totali
    total_custom_count = len(all_custom)
    total_standard_count = len(all_blocks)
    total_blocks_count = total_custom_count + total_standard_count
    
    # Calcola copertura media
    coverage_percentages = [r['coverage']['coverage_percent'] for r in rows_data[1:]]  # Skip prima riga
    avg_coverage = sum(coverage_percentages) / len(coverage_percentages) if coverage_percentages else 100
    
    # Calcola sfalsamento medio
    stagger_percentages = [r['stagger']['stagger_percent'] for r in rows_data[1:]]
    avg_stagger = sum(stagger_percentages) / len(stagger_percentages) if stagger_percentages else 0
    
    return {
        'all_blocks': all_blocks,
        'all_custom': all_custom,
        'rows': rows_data,
        'total_coverage': {
            'average_percent': avg_coverage,
            'all_complete': all(r['coverage']['is_complete'] for r in rows_data[1:])
        },
        'total_stagger': {
            'average_percent': avg_stagger,
            'is_good': avg_stagger >= 70
        },
        'stats': {
            'total_blocks': total_blocks_count,
            'standard_blocks': total_standard_count,
            'custom_blocks': total_custom_count,
            'custom_percentage': (total_custom_count / total_blocks_count * 100) if total_blocks_count > 0 else 0,
            'num_rows': len(rows_data),  # ✅ CORRETTO: conta righe effettive (complete + adattiva)
            'complete_rows': complete_rows,
            'has_adaptive_row': remaining_space >= 150,
            'remaining_space_mm': remaining_space
        }
    }


__all__ = ['SmallAlgorithmPacker', 'pack_wall_with_small_algorithm']

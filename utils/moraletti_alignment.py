"""
Sistema di Allineamento Moraletti per Algoritmo Small
Gestisce calcolo posizioni, validazione copertura, concatenazione blocchi

REGOLE FONDAMENTALI:
1. TUTTI i buchi (moraletti) devono essere riempiti/coperti
2. Allineamento verticale tra righe
3. Configurazione completamente dinamica dall'utente
4. Spacing fisso per tutti i blocchi (standard e custom)
"""

import math
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class MoralettoPosition:
    """Posizione di un singolo moraletto"""
    center_x: float  # Posizione centro (da sinistra parete)
    range_start: float  # Inizio range (centro - thickness/2)
    range_end: float  # Fine range (centro + thickness/2)
    block_id: str  # ID del blocco a cui appartiene
    moraletto_index: int  # Indice nel blocco (0, 1, 2, ...)


@dataclass
class BlockMoraletti:
    """Informazioni moraletti di un blocco"""
    block_x: float  # Posizione X blocco nella parete
    block_width: float
    block_type: str  # 'large', 'medium', 'small', 'custom'
    is_standard: bool
    moraletti_count: int
    positions: List[MoralettoPosition]


class DynamicMoralettiConfiguration:
    """
    Configurazione dinamica moraletti caricata dall'utente
    NESSUN VALORE HARDCODED - tutto configurabile
    """
    
    def __init__(self, user_config: Dict):
        """
        user_config = {
            'block_large_width': 1239,
            'block_large_height': 495,
            'block_medium_width': 826,
            'block_medium_height': 495,
            'block_small_width': 413,
            'block_small_height': 495,
            'moraletti_thickness': 58,
            'moraletti_height': 495,
            'moraletti_height_from_ground': 95,
            'moraletti_spacing': 420,
            'moraletti_count_large': 3,
            'moraletti_count_medium': 2,
            'moraletti_count_small': 1,
        }
        """
        
        # Dimensioni blocchi standard (dinamiche)
        self.block_sizes = {
            'large': float(user_config['block_large_width']),
            'medium': float(user_config['block_medium_width']),
            'small': float(user_config['block_small_width'])
        }
        
        self.block_heights = {
            'large': float(user_config['block_large_height']),
            'medium': float(user_config['block_medium_height']),
            'small': float(user_config['block_small_height'])
        }
        
        # Configurazione moraletti (dinamica)
        self.thickness = float(user_config['moraletti_thickness'])
        self.height = float(user_config['moraletti_height'])
        self.height_from_ground = float(user_config['moraletti_height_from_ground'])
        self.spacing = float(user_config['moraletti_spacing'])
        
        # Numero moraletti per tipo (dinamico)
        self.moraletti_counts = {
            'large': int(user_config['moraletti_count_large']),
            'medium': int(user_config['moraletti_count_medium']),
            'small': int(user_config['moraletti_count_small'])
        }
        
        # Validazione configurazione
        self._validate_configuration()
    
    def _validate_configuration(self):
        """Valida che la configurazione sia consistente"""
        
        # 1. Blocchi in ordine decrescente
        if not (self.block_sizes['large'] > self.block_sizes['medium'] > self.block_sizes['small']):
            raise ValueError(
                f"Block sizes must be Large > Medium > Small. "
                f"Got: {self.block_sizes['large']} > {self.block_sizes['medium']} > {self.block_sizes['small']}"
            )
        
        # 2. Spacing positivo
        if self.spacing <= 0:
            raise ValueError(f"Spacing must be positive, got {self.spacing}")
        
        # 3. Thickness positivo
        if self.thickness <= 0:
            raise ValueError(f"Thickness must be positive, got {self.thickness}")
        
        # 4. Moraletti configurati devono poter stare nei blocchi
        for block_type in ['large', 'medium', 'small']:
            width = self.block_sizes[block_type]
            configured_count = self.moraletti_counts[block_type]
            max_possible = math.floor(width / self.spacing) + 1
            
            if configured_count > max_possible:
                raise ValueError(
                    f"Block {block_type} ({width}mm) cannot fit {configured_count} moraletti "
                    f"with spacing {self.spacing}mm. Max possible: {max_possible}"
                )
    
    def get_block_info(self, block_width: float) -> Dict:
        """
        Determina tipo e proprietà del blocco basandosi sulla larghezza
        DINAMICO - usa valori configurati
        """
        
        # Arrotondamento per confronto
        block_width = round(block_width, 2)
        
        # Blocco standard Grande?
        if abs(block_width - self.block_sizes['large']) < 0.1:
            return {
                'type': 'large',
                'width': self.block_sizes['large'],
                'height': self.block_heights['large'],
                'max_moraletti': self.moraletti_counts['large'],
                'is_standard': True
            }
        
        # Blocco standard Medio?
        elif abs(block_width - self.block_sizes['medium']) < 0.1:
            return {
                'type': 'medium',
                'width': self.block_sizes['medium'],
                'height': self.block_heights['medium'],
                'max_moraletti': self.moraletti_counts['medium'],
                'is_standard': True
            }
        
        # Blocco standard Piccolo?
        elif abs(block_width - self.block_sizes['small']) < 0.1:
            return {
                'type': 'small',
                'width': self.block_sizes['small'],
                'height': self.block_heights['small'],
                'max_moraletti': self.moraletti_counts['small'],
                'is_standard': True
            }
        
        # Custom - determina range
        else:
            return self._get_custom_block_info(block_width)
    
    def _get_custom_block_info(self, block_width: float) -> Dict:
        """
        Determina proprietà per blocco custom
        VINCOLI:
        - NON può essere >= Grande
        - NON può essere == Medio o Piccolo
        - Max moraletti dal range dove si trova
        """
        
        # Validazione: custom NON può essere >= Grande
        if block_width >= self.block_sizes['large']:
            raise ValueError(
                f"Custom block {block_width}mm >= Large block "
                f"{self.block_sizes['large']}mm - NOT ALLOWED!"
            )
        
        # Range: tra Medio e Grande
        if block_width > self.block_sizes['medium']:
            return {
                'type': 'custom',
                'width': block_width,
                'height': self.block_heights['large'],
                'max_moraletti': self.moraletti_counts['medium'],  # Max come Medio
                'is_standard': False,
                'range': 'medium-large'
            }
        
        # Range: tra Piccolo e Medio
        elif block_width > self.block_sizes['small']:
            return {
                'type': 'custom',
                'width': block_width,
                'height': self.block_heights['medium'],
                'max_moraletti': self.moraletti_counts['small'],  # Max come Piccolo
                'is_standard': False,
                'range': 'small-medium'
            }
        
        # Range: più piccolo del Piccolo
        else:
            return {
                'type': 'custom',
                'width': block_width,
                'height': self.block_heights['small'],
                'max_moraletti': 1,  # Minimo assoluto
                'is_standard': False,
                'range': 'micro'
            }
    
    def calculate_moraletti_for_block(self, block_width: float, block_x: float = 0, 
                                     block_id: str = None) -> BlockMoraletti:
        """
        Calcola posizioni moraletti per qualsiasi blocco (standard o custom)
        
        REGOLE:
        - Spacing FISSO (configurato) per tutti
        - Primo moraletto: centro a 0mm dal bordo DESTRO
        - Altri: distanziati di spacing verso SINISTRA
        - Max moraletti: da configurazione o range
        """
        
        # Ottieni info blocco
        block_info = self.get_block_info(block_width)
        
        # Calcola numero moraletti teorici con spacing
        theoretical_count = math.floor(block_width / self.spacing) + 1
        
        # Applica limite MAX
        actual_count = min(theoretical_count, block_info['max_moraletti'])
        
        # Calcola posizioni
        positions = []
        half_thickness = self.thickness / 2
        
        for i in range(actual_count):
            # Distanza dal bordo DESTRO del blocco
            distance_from_right = i * self.spacing
            
            # Posizione centro dal bordo SINISTRO del blocco (relativa)
            center_relative = block_width - distance_from_right
            
            # Posizione assoluta nella parete
            center_absolute = block_x + center_relative
            
            # Range occupato
            range_start = center_absolute - half_thickness
            range_end = center_absolute + half_thickness
            
            positions.append(MoralettoPosition(
                center_x=center_absolute,
                range_start=range_start,
                range_end=range_end,
                block_id=block_id or f"block_{block_x}",
                moraletto_index=i
            ))
        
        return BlockMoraletti(
            block_x=block_x,
            block_width=block_width,
            block_type=block_info['type'],
            is_standard=block_info['is_standard'],
            moraletti_count=actual_count,
            positions=positions
        )


class MoralettiCoverageValidator:
    """
    Valida che TUTTI i moraletti siano coperti
    REGOLA FONDAMENTALE: Nessun moraletto può rimanere scoperto
    """
    
    def __init__(self, config: DynamicMoralettiConfiguration):
        self.config = config
    
    def validate_complete_coverage(self, 
                                   row_below: List[Dict],
                                   row_above: List[Dict]) -> Dict:
        """
        Verifica che TUTTI i moraletti della riga sotto siano coperti dalla riga sopra
        
        Args:
            row_below: Lista blocchi riga sotto [{'x': 0, 'width': 1239}, ...]
            row_above: Lista blocchi riga sopra
            
        Returns:
            {
                'is_complete': bool,
                'coverage_percent': float,
                'uncovered_moraletti': List[MoralettoPosition],
                'coverage_map': Dict
            }
        """
        
        # 1. Calcola TUTTI i moraletti della riga sotto
        all_moraletti_below = []
        for block in row_below:
            block_moraletti = self.config.calculate_moraletti_for_block(
                block_width=block['width'],
                block_x=block['x'],
                block_id=block.get('id', f"block_{block['x']}")
            )
            all_moraletti_below.extend(block_moraletti.positions)
        
        if not all_moraletti_below:
            # Nessun moraletto da coprire (prima riga)
            return {
                'is_complete': True,
                'coverage_percent': 100.0,
                'uncovered_moraletti': [],
                'coverage_map': {},
                'total_moraletti': 0
            }
        
        # 2. Per OGNI moraletto, verifica che sia coperto da blocco sopra
        uncovered = []
        coverage_map = {}
        
        for moraletto in all_moraletti_below:
            is_covered = False
            covering_block = None
            
            for block_above in row_above:
                block_left = block_above['x']
                block_right = block_above['x'] + block_above['width']
                
                # Moraletto coperto se il suo CENTRO è dentro il blocco sopra
                # Include piccola tolleranza per bordi
                tolerance = self.config.thickness / 2
                
                if (block_left - tolerance) <= moraletto.center_x <= (block_right + tolerance):
                    is_covered = True
                    covering_block = block_above
                    break
            
            if is_covered:
                coverage_map[moraletto.center_x] = {
                    'moraletto': moraletto,
                    'covered_by': covering_block
                }
            else:
                uncovered.append(moraletto)
        
        # 3. Calcola statistiche
        total_count = len(all_moraletti_below)
        covered_count = total_count - len(uncovered)
        coverage_percent = (covered_count / total_count * 100) if total_count > 0 else 100
        
        return {
            'is_complete': len(uncovered) == 0,
            'coverage_percent': coverage_percent,
            'uncovered_moraletti': uncovered,
            'uncovered_count': len(uncovered),
            'total_moraletti': total_count,
            'covered_count': covered_count,
            'coverage_map': coverage_map
        }
    
    def get_moraletti_positions_for_row(self, row: List[Dict]) -> List[float]:
        """
        Ottieni lista di tutte le posizioni X dei moraletti in una riga
        Utile per debug e visualizzazione
        """
        
        all_positions = []
        for block in row:
            block_moraletti = self.config.calculate_moraletti_for_block(
                block_width=block['width'],
                block_x=block['x']
            )
            all_positions.extend([m.center_x for m in block_moraletti.positions])
        
        return sorted(all_positions)


class StaggeringCalculator:
    """
    Calcola metriche di sfalsamento tra righe
    Sfalsamento = bordi non allineati verticalmente (pattern mattoncino)
    """
    
    @staticmethod
    def calculate_stagger_score(row_above: List[Dict], row_below: List[Dict]) -> Dict:
        """
        Calcola quanto è sfalsata una riga rispetto a quella sotto
        
        Score alto = molto sfalsamento (buono)
        Score basso = poco sfalsamento (cattivo - colonne verticali)
        """
        
        # Trova tutti i bordi (giunti tra blocchi)
        def get_borders(row):
            borders = []
            for i, block in enumerate(row[:-1]):  # Escludi ultimo (bordo parete)
                border_x = block['x'] + block['width']
                borders.append(border_x)
            return borders
        
        borders_below = get_borders(row_below)
        borders_above = get_borders(row_above)
        
        if not borders_above:
            # Riga sopra ha un solo blocco - sfalsamento N/A
            return {
                'score': 1.0,
                'aligned_borders': 0,
                'total_borders': 0,
                'stagger_percent': 100.0,
                'is_good': True
            }
        
        # Conta bordi allineati (cattivo!)
        aligned_count = 0
        tolerance = 10  # mm - tolleranza per considerare allineato
        
        for border_above in borders_above:
            for border_below in borders_below:
                if abs(border_above - border_below) < tolerance:
                    aligned_count += 1
                    break
        
        # Score: percentuale di bordi NON allineati
        total_borders = len(borders_above)
        staggered_borders = total_borders - aligned_count
        stagger_percent = (staggered_borders / total_borders * 100) if total_borders > 0 else 100
        
        return {
            'score': stagger_percent / 100,  # 0-1
            'aligned_borders': aligned_count,
            'total_borders': total_borders,
            'stagger_percent': stagger_percent,
            'is_good': stagger_percent >= 80  # Almeno 80% sfalsato = buono
        }


# Funzioni di utilità per integrazione facile

def create_moraletti_config_from_dict(config_dict: Dict) -> DynamicMoralettiConfiguration:
    """Helper per creare configurazione da dizionario"""
    return DynamicMoralettiConfiguration(config_dict)


def validate_row_coverage(row_below: List[Dict], row_above: List[Dict], 
                         config: DynamicMoralettiConfiguration) -> bool:
    """
    Quick check: verifica se riga sopra copre completamente riga sotto
    Returns: True se TUTTI i moraletti coperti, False altrimenti
    """
    validator = MoralettiCoverageValidator(config)
    result = validator.validate_complete_coverage(row_below, row_above)
    return result['is_complete']


def calculate_moraletti_positions_list(blocks: List[Dict], 
                                       config: DynamicMoralettiConfiguration) -> List[float]:
    """
    Calcola lista semplice di posizioni X dei moraletti per una lista di blocchi
    Utile per debug e visualizzazione
    """
    validator = MoralettiCoverageValidator(config)
    return validator.get_moraletti_positions_for_row(blocks)


# Export principali
__all__ = [
    'DynamicMoralettiConfiguration',
    'MoralettiCoverageValidator',
    'StaggeringCalculator',
    'MoralettoPosition',
    'BlockMoraletti',
    'create_moraletti_config_from_dict',
    'validate_row_coverage',
    'calculate_moraletti_positions_list'
]

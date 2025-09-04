"""
Block Grouping System
Sistema di raggruppamento e categorizzazione dei blocchi per wall-build.

Implementa:
1. Raggruppamento automatico per categoria (stesso tipo/dimensione)
2. Numerazione progressiva A1, A2, A3...
3. Layout con lettera categoria (basso-sinistra) + numero (alto-destra)
4. Supporto blocchi standard e custom con stesse dimensioni
"""

from typing import List, Dict, Tuple, DefaultDict
from collections import defaultdict
from utils.config import SIZE_TO_LETTER, BLOCK_HEIGHT
import string


class BlockGrouping:
    """Gestisce il raggruppamento e categorizzazione dei blocchi."""
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        """Reset contatori e mappature."""
        self.category_counters = defaultdict(int)
        self.block_categories = {}  # block_id -> categoria
        self.category_definitions = {}  # categoria -> info
        self.next_category_letter = 'A'
    
    def create_grouped_labels(self, placed: List[Dict], customs: List[Dict]) -> Tuple[Dict[int, Dict], Dict[int, Dict]]:
        """
        Crea etichette raggruppate per blocchi standard e custom.
        
        Returns:
            (std_labels, custom_labels) dove ogni label è un dict con:
            {
                'category': 'A',      # Lettera categoria (basso-sinistra)  
                'number': 1,          # Numero progressivo (alto-destra)
                'full_label': 'A1',   # Etichetta completa
                'display': {...}      # Info per rendering
            }
        """
        self.reset()
        
        # 1. Raggruppa blocchi per caratteristiche simili
        standard_groups = self._group_standard_blocks(placed)
        custom_groups = self._group_custom_blocks(customs)
        
        # 2. Assegna categorie (lettere) a ogni gruppo
        category_map = self._assign_categories(standard_groups, custom_groups)
        
        # 3. Crea etichette finali
        std_labels = self._create_standard_labels(placed, standard_groups, category_map)
        custom_labels = self._create_custom_labels(customs, custom_groups, category_map)
        
        return std_labels, custom_labels
    
    def _group_standard_blocks(self, placed: List[Dict]) -> Dict[str, List[int]]:
        """Raggruppa blocchi standard per tipo (dimensione)."""
        groups = defaultdict(list)
        
        for i, block in enumerate(placed):
            width = int(block['width'])
            height = int(block['height'])
            
            # Crea chiave gruppo basata su dimensioni
            group_key = f"std_{width}x{height}"
            groups[group_key].append(i)
        
        print(f"📦 Gruppi standard trovati: {dict(groups)}")
        return dict(groups)
    
    def _group_custom_blocks(self, customs: List[Dict]) -> Dict[str, List[int]]:
        """Raggruppa blocchi custom per dimensioni simili."""
        groups = defaultdict(list)
        tolerance = 5  # mm di tolleranza per considerare dimensioni "uguali"
        
        for i, custom in enumerate(customs):
            width = round(custom['width'])
            height = round(custom['height'])
            
            # Cerca gruppo esistente con dimensioni simili
            found_group = None
            for existing_key in groups.keys():
                if existing_key.startswith("custom_"):
                    # Estrai dimensioni esistenti
                    try:
                        parts = existing_key.replace("custom_", "").split("x")
                        existing_w, existing_h = int(parts[0]), int(parts[1])
                        
                        # Controlla se rientra nella tolleranza
                        if (abs(width - existing_w) <= tolerance and 
                            abs(height - existing_h) <= tolerance):
                            found_group = existing_key
                            break
                    except:
                        continue
            
            if found_group:
                groups[found_group].append(i)
            else:
                # Nuovo gruppo
                group_key = f"custom_{width}x{height}"
                groups[group_key].append(i)
        
        print(f"🔧 Gruppi custom trovati: {dict(groups)}")
        return dict(groups)
    
    def _assign_categories(self, std_groups: Dict, custom_groups: Dict) -> Dict[str, str]:
        """
        Assegna lettere categoria ai gruppi.
        A, B, C riservate per standard, D+ per custom.
        """
        category_map = {}
        
        # PRIMA: Assegna A, B, C ai gruppi standard (ordinati per quantità)
        std_sorted = sorted(std_groups.items(), key=lambda x: len(x[1]), reverse=True)
        for i, (group_key, indices) in enumerate(std_sorted):
            if i < 3:  # Solo A, B, C per standard
                letter = chr(ord('A') + i)
                category_map[group_key] = letter
                
                # Salva definizione categoria
                self.category_definitions[letter] = {
                    'group_key': group_key,
                    'count': len(indices),
                    'type': 'standard',
                    'priority': len(indices) * 1000
                }
                
                print(f"📋 Categoria {letter} → {group_key} ({len(indices)} blocchi, tipo: standard)")
        
        # SECONDA: Assegna D, E, F... ai gruppi custom (ordinati per quantità)
        custom_sorted = sorted(custom_groups.items(), key=lambda x: len(x[1]), reverse=True)
        custom_letter_start = 3  # Inizia da D (indice 3)
        
        for i, (group_key, indices) in enumerate(custom_sorted):
            letter_index = custom_letter_start + i
            
            if letter_index < 26:
                letter = string.ascii_uppercase[letter_index]
            else:
                # Dopo Z, usa AA, AB, AC...
                letter = self._generate_extended_letter(letter_index - 26)
            
            category_map[group_key] = letter
            
            # Salva definizione categoria
            self.category_definitions[letter] = {
                'group_key': group_key,
                'count': len(indices),
                'type': 'custom',
                'priority': len(indices) * 10
            }
            
            print(f"📋 Categoria {letter} → {group_key} ({len(indices)} blocchi, tipo: custom)")
        
        return category_map
    
    def _generate_extended_letter(self, index: int) -> str:
        """Genera lettere estese oltre Z: AA, AB, AC..."""
        first = index // 26
        second = index % 26
        return string.ascii_uppercase[first] + string.ascii_uppercase[second]
    
    def _create_standard_labels(self, placed: List[Dict], groups: Dict, category_map: Dict) -> Dict[int, Dict]:
        """Crea etichette per blocchi standard."""
        labels = {}
        
        for group_key, indices in groups.items():
            category = category_map[group_key]
            
            # Numera progressivamente all'interno della categoria
            for position, block_index in enumerate(indices):
                number = position + 1
                
                labels[block_index] = {
                    'category': category,
                    'number': number,
                    'full_label': f"{category}{number}",
                    'group_key': group_key,
                    'display': {
                        'bottom_left': category,     # Lettera categoria
                        'top_right': str(number),    # Numero progressivo
                        'type': 'standard',
                        'dimensions': f"{placed[block_index]['width']:.0f}×{placed[block_index]['height']:.0f}"
                    }
                }
        
        return labels
    
    def _create_custom_labels(self, customs: List[Dict], groups: Dict, category_map: Dict) -> Dict[int, Dict]:
        """Crea etichette per blocchi custom."""
        labels = {}
        
        for group_key, indices in groups.items():
            category = category_map[group_key]
            
            # Numera progressivamente all'interno della categoria
            for position, custom_index in enumerate(indices):
                number = position + 1
                custom = customs[custom_index]
                
                labels[custom_index] = {
                    'category': category,
                    'number': number,
                    'full_label': f"{category}{number}",
                    'group_key': group_key,
                    'display': {
                        'bottom_left': category,     # Lettera categoria
                        'top_right': str(number),    # Numero progressivo
                        'type': 'custom',
                        'ctype': custom.get('ctype', 2),
                        'dimensions': f"{custom['width']:.0f}×{custom['height']:.0f}"
                    }
                }
        
        return labels
    
    def get_category_summary(self) -> Dict[str, Dict]:
        """
        Restituisce riassunto delle categorie per tabelle/export.
        
        Returns:
            Dict[categoria] = {
                'count': numero_blocchi,
                'type': 'standard'|'custom', 
                'dimensions': 'larghezza×altezza',
                'description': descrizione_umana
            }
        """
        summary = {}
        
        for category, info in self.category_definitions.items():
            group_key = info['group_key']
            
            # Estrai dimensioni dal group_key
            if group_key.startswith('std_'):
                dimensions_part = group_key.replace('std_', '')
                block_type = 'standard'
                description = f"Blocco Standard {category}"
            elif group_key.startswith('custom_'):
                dimensions_part = group_key.replace('custom_', '')
                block_type = 'custom'
                description = f"Pezzo Custom {category}"
            else:
                dimensions_part = "unknown"
                block_type = 'unknown'
                description = f"Blocco {category}"
            
            summary[category] = {
                'count': info['count'],
                'type': block_type,
                'dimensions': dimensions_part,
                'description': description,
                'priority': info['priority']
            }
        
        return summary


# ────────────────────────────────────────────────────────────────────────────────
# Funzioni di compatibilità con il sistema esistente
# ────────────────────────────────────────────────────────────────────────────────

# Istanza globale per mantenere stato
_block_grouping = BlockGrouping()

def create_grouped_block_labels(placed: List[Dict], customs: List[Dict]) -> Tuple[Dict[int, Dict], Dict[int, Dict]]:
    """
    Funzione principale per creare etichette raggruppate.
    
    Sostituisce create_block_labels() con il nuovo sistema di raggruppamento.
    """
    return _block_grouping.create_grouped_labels(placed, customs)

def get_block_category_summary() -> Dict[str, Dict]:
    """Ottieni riassunto categorie per tabelle/export."""
    return _block_grouping.get_category_summary()

def create_block_labels_legacy(placed: List[Dict], custom: List[Dict]) -> Tuple[Dict[int, str], Dict[int, str]]:
    """
    Versione legacy per compatibilità con codice esistente.
    Converte le nuove etichette strutturate in stringhe semplici.
    """
    grouped_std, grouped_custom = create_grouped_block_labels(placed, custom)
    
    # Converti in formato legacy (dict[int, str])
    std_labels = {i: label['full_label'] for i, label in grouped_std.items()}
    custom_labels = {i: label['full_label'] for i, label in grouped_custom.items()}
    
    return std_labels, custom_labels


# ────────────────────────────────────────────────────────────────────────────────
# Test e debug
# ────────────────────────────────────────────────────────────────────────────────

def test_block_grouping():
    """Test del sistema di raggruppamento."""
    print("🧪 Test Block Grouping System")
    
    # Dati di test
    test_placed = [
        {'width': 1239, 'height': 495, 'x': 0, 'y': 0},      # A1
        {'width': 1239, 'height': 495, 'x': 1239, 'y': 0},   # A2
        {'width': 826, 'height': 495, 'x': 0, 'y': 495},     # B1
        {'width': 826, 'height': 495, 'x': 826, 'y': 495},   # B2
        {'width': 413, 'height': 495, 'x': 0, 'y': 990},     # C1
    ]
    
    test_customs = [
        {'width': 300, 'height': 400, 'ctype': 1},  # D1 (custom gruppo 1)
        {'width': 305, 'height': 395, 'ctype': 1},  # D2 (stesso gruppo - simili)
        {'width': 500, 'height': 200, 'ctype': 2},  # E1 (custom gruppo 2)
    ]
    
    # Test raggruppamento
    grouping = BlockGrouping()
    std_labels, custom_labels = grouping.create_grouped_labels(test_placed, test_customs)
    
    print("\n📊 Risultati Standard:")
    for i, label in std_labels.items():
        print(f"  Blocco {i}: {label['full_label']} (categoria: {label['category']}, num: {label['number']})")
        print(f"    Display: {label['display']['bottom_left']} (BL) + {label['display']['top_right']} (TR)")
    
    print("\n🔧 Risultati Custom:")
    for i, label in custom_labels.items():
        print(f"  Custom {i}: {label['full_label']} (categoria: {label['category']}, num: {label['number']})")
        print(f"    Display: {label['display']['bottom_left']} (BL) + {label['display']['top_right']} (TR)")
    
    print("\n📋 Riassunto Categorie:")
    summary = grouping.get_category_summary()
    for category, info in summary.items():
        print(f"  {category}: {info['count']} blocchi {info['type']} ({info['dimensions']})")
    
    print("\n✅ Test completato!")


if __name__ == "__main__":
    test_block_grouping()


# Funzioni helper per compatibilità con main.py
def group_blocks_by_category(placed: List[Dict]) -> Dict[str, List[Dict]]:
    """Raggruppa i blocchi per categoria (compatibilità main.py)."""
    grouping = BlockGrouping()
    std_labels, _ = grouping.create_grouped_labels(placed, [])
    
    # Raggruppa per categoria
    categories = defaultdict(list)
    for i, block in enumerate(placed):
        if i in std_labels:
            category = std_labels[i]['category']
            categories[category].append(block)
    
    return dict(categories)


def group_custom_blocks_by_category(customs: List[Dict]) -> Dict[str, List[Dict]]:
    """Raggruppa i blocchi custom per categoria (compatibilità main.py)."""
    grouping = BlockGrouping()
    _, custom_labels = grouping.create_grouped_labels([], customs)
    
    # Raggruppa per categoria
    categories = defaultdict(list)
    for i, block in enumerate(customs):
        if i in custom_labels:
            category = custom_labels[i]['category']
            categories[category].append(block)
    
    return dict(categories)


def create_grouped_block_labels(placed: List[Dict], customs: List[Dict]) -> Tuple[Dict[int, Dict], Dict[int, Dict]]:
    """Crea le etichette raggruppate (compatibilità main.py)."""
    grouping = BlockGrouping()
    return grouping.create_grouped_labels(placed, customs)

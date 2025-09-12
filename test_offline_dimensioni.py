"""
Test Dimensioni Blocchi - Calcolo Offline
Mostra le dimensioni che verrebbero utilizzate per diversi input
"""

def calculate_block_dimensions(input_widths):
    """Calcola le dimensioni finali dei blocchi basandosi sulla logica reale del sistema"""
    
    # Logica ESATTA dal sistema (da utils/config.py)
    BLOCK_WIDTHS = [1239, 826, 413]  # Dimensioni standard operative
    
    # Converti a interi per confronto preciso (come fa il sistema)
    input_widths_int = [int(w) for w in input_widths]
    
    # Ordina entrambe le liste per confronto corretto
    default_widths_sorted = sorted(BLOCK_WIDTHS)
    input_widths_sorted = sorted(input_widths_int)
    
    # Controlla se sono identiche al default (logica del sistema)
    is_default_widths = (input_widths_sorted == default_widths_sorted)
    
    if is_default_widths:
        return {
            'schema': 'STANDARD',
            'input_widths': input_widths,
            'final_widths': BLOCK_WIDTHS,  # Usa le dimensioni standard operative
            'mapping': {1239: 'A', 826: 'B', 413: 'C'}
        }
    else:
        # Schema CUSTOM: il sistema USA DIRETTAMENTE le dimensioni input
        # (non c'è remapping a 1239mm come pensavo inizialmente)
        
        # Crea mapping personalizzato: ordina per dimensione decrescente
        sorted_widths = sorted(input_widths_int, reverse=True)
        custom_mapping = {}
        
        for i, width in enumerate(sorted_widths):
            letter = chr(ord('A') + i)  # A, B, C, D, E...
            custom_mapping[width] = letter
        
        return {
            'schema': 'CUSTOM',
            'input_widths': input_widths,
            'final_widths': input_widths_int,  # USA DIRETTAMENTE le dimensioni input!
            'mapping': custom_mapping
        }

def estimate_blocks_needed(area_m2, block_widths_mm, block_height_mm=495):
    """Stima approssimativa del numero di blocchi necessari"""
    
    # Converti area in mm²
    area_mm2 = area_m2 * 1_000_000
    
    # Calcola area di un blocco (larghezza media)
    avg_width = sum(block_widths_mm) / len(block_widths_mm)
    block_area = avg_width * block_height_mm
    
    # Stima numero blocchi (con fattore di spreco ~20%)
    estimated_blocks = int((area_mm2 / block_area) * 1.2)
    
    return {
        'area_m2': area_m2,
        'avg_block_width': avg_width,
        'block_area_mm2': block_area,
        'estimated_total_blocks': estimated_blocks
    }

def main():
    print("=" * 60)
    print("ANALISI DIMENSIONI BLOCCHI - CALCOLO OFFLINE")
    print("=" * 60)
    print()
    
    # Area di test: 10m x 5m - 2m x 2m = 46 m²
    test_area = 46
    print(f"Area parete test: {test_area} m²")
    print()
    
    # Configurazioni di test
    test_configs = [
        {
            'name': 'TAKTAK Standard',
            'dimensions': [1500, 826, 413],
            'description': 'Dimensioni standard del sistema TAKTAK'
        },
        {
            'name': 'Blocchi Grandi',
            'dimensions': [2000, 1000, 500],
            'description': 'Blocchi più grandi per meno giunti'
        },
        {
            'name': 'Blocchi Piccoli',
            'dimensions': [800, 600, 400],
            'description': 'Blocchi più piccoli per maggiore flessibilità'
        },
        {
            'name': 'Blocchi Enormi',
            'dimensions': [3000, 1500, 750],
            'description': 'Blocchi molto grandi per progetti industriali'
        }
    ]
    
    for i, config in enumerate(test_configs, 1):
        print(f"--- TEST {i}: {config['name']} ---")
        print(f"Descrizione: {config['description']}")
        print(f"Input utente: {config['dimensions']} mm")
        
        # Calcola le dimensioni effettive che userebbe il sistema
        result = calculate_block_dimensions(config['dimensions'])
        
        print(f"Schema: {result['schema']}")
        print(f"Dimensioni effettive utilizzate: {result['final_widths']} mm")
        print(f"Mappatura: {result['mapping']}")
        
        # Stima blocchi necessari con le dimensioni effettive
        estimation = estimate_blocks_needed(test_area, result['final_widths'])
        print(f"Stima blocchi totali: ~{estimation['estimated_total_blocks']}")
        print(f"Larghezza media blocco: {estimation['avg_block_width']:.0f} mm")
        print(f"Area per blocco: {estimation['block_area_mm2']:.0f} mm²")
        print()
    
    print("=" * 60)
    print("DIFFERENZE CHIAVE:")
    print("=" * 60)
    print("1. Schema STANDARD usa dimensioni operative fisse: [1239, 826, 413]")
    print("2. Schema CUSTOM usa DIRETTAMENTE le dimensioni che inserisci!")
    print("3. Le dimensioni custom NON vengono rimappate internamente")
    print("4. Diversi rapporti dimensionali producono quantità molto diverse")
    print("5. Il mapping delle lettere segue l'ordine decrescente (più grande = A)")
    print()
    print("IMPORTANTE:")
    print("- Standard [1239,826,413]: dimensioni ottimizzate per il sistema TAKTAK")
    print("- Custom [2000,1000,500]: blocchi più grandi = meno pezzi ma possibili sprechi") 
    print("- Custom [800,600,400]: blocchi più piccoli = più pezzi ma migliore copertura")
    print("- Custom [3000,1500,750]: blocchi enormi = pochissimi pezzi ma molto spreco")
    print()
    print("CONCLUSIONE:")
    print("Il sistema calcola REALMENTE in modo diverso con dimensioni diverse!")
    print("Non è un'illusione - le quantità cambiano davvero secondo le dimensioni.")

if __name__ == "__main__":
    main()

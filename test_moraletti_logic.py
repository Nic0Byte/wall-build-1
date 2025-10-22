"""
Test isolato della logica di calcolo moraletti
"""
import math
from collections import defaultdict

def calculate_moraletti_info_test(config, placed, customs):
    """Versione standalone per test"""
    
    # Default values
    moraletti_thickness = config.get("moraletti_thickness", 58)
    moraletti_height = config.get("moraletti_height", 495)
    moraletti_height_from_ground = config.get("moraletti_height_from_ground", 95)
    moraletti_spacing = config.get("moraletti_spacing", 420)
    max_moraletti_large = config.get("moraletti_count_large", 3)
    max_moraletti_medium = config.get("moraletti_count_medium", 2)
    max_moraletti_small = config.get("moraletti_count_small", 1)
    
    # Larghezze blocchi standard
    block_widths = sorted(config.get("block_widths", [1239, 826, 413]), reverse=True)
    large_width = block_widths[0]
    medium_width = block_widths[1]
    small_width = block_widths[2]
    
    # Mappatura larghezza -> max moraletti
    width_to_max_moraletti = {
        large_width: max_moraletti_large,
        medium_width: max_moraletti_medium,
        small_width: max_moraletti_small
    }
    
    # Mappatura larghezza -> lettera
    size_to_letter = config.get("size_to_letter", {})
    
    # Funzione per calcolare moraletti per un blocco
    def calculate_moraletti_count(width):
        """Calcola numero moraletti per una larghezza blocco"""
        # Teorico: floor(width / spacing) + 1
        theoretical_count = math.floor(width / moraletti_spacing) + 1
        
        # Applica max per blocchi standard
        if width in width_to_max_moraletti:
            return min(theoretical_count, width_to_max_moraletti[width])
        
        # Per custom, cerca il range più vicino
        for std_width, max_count in width_to_max_moraletti.items():
            if abs(width - std_width) < 50:  # Tolleranza 50mm
                return min(theoretical_count, max_count)
        
        # Fallback: usa theoretical con limite massimo ragionevole
        return min(theoretical_count, 5)
    
    # Conta blocchi standard per tipo
    standard_counts = defaultdict(int)
    standard_moraletti = defaultdict(int)
    
    for block in placed:
        width = block.get('width', 0)
        standard_counts[width] += 1
        moraletti_count = calculate_moraletti_count(width)
        standard_moraletti[width] += moraletti_count
    
    # Conta blocchi custom per dimensione
    custom_counts = defaultdict(int)
    custom_moraletti = defaultdict(int)
    
    for block in customs:
        width = block.get('width', 0)
        height = block.get('height', moraletti_height)
        dim_key = f"{int(width)}×{int(height)}"
        custom_counts[dim_key] += 1
        moraletti_count = calculate_moraletti_count(width)
        custom_moraletti[dim_key] += moraletti_count
    
    # Calcola totale
    total_moraletti = sum(standard_moraletti.values()) + sum(custom_moraletti.values())
    
    # Costruisci le righe di output
    lines = []
    lines.append(f"Configurazione: {moraletti_thickness}mm × {moraletti_height}mm")
    lines.append(f"Piedini: {moraletti_height_from_ground}mm")
    lines.append("")
    lines.append(f"Quantità Totale: {total_moraletti} pezzi")
    lines.append("")
    
    # Standard
    if standard_moraletti:
        lines.append("Standard:")
        # Ordina per larghezza decrescente
        for width in sorted(standard_moraletti.keys(), reverse=True):
            count = standard_counts[width]
            mor_count = standard_moraletti[width]
            mor_per_block = mor_count // count if count > 0 else 0
            
            # Ottieni lettera
            letter = size_to_letter.get(str(int(width)), '?')
            
            lines.append(f"• {letter} ({int(width)}×{moraletti_height}mm): {mor_count} mor. ({count} pz × {mor_per_block})")
        lines.append("")
    
    # Custom
    if custom_moraletti:
        lines.append("Custom:")
        # Ordina alfabeticamente per dimensione
        for dim_key in sorted(custom_moraletti.keys()):
            count = custom_counts[dim_key]
            mor_count = custom_moraletti[dim_key]
            mor_per_block = mor_count // count if count > 0 else 0
            
            # Trova lettera custom
            width_str = dim_key.split('×')[0]
            letter = size_to_letter.get(width_str, '?')
            
            lines.append(f"• {letter} ({dim_key}mm): {mor_count} mor. ({count} pz × {mor_per_block})")
    
    return lines


# Simulazione dati
config = {
    "block_widths": [1239, 826, 413],
    "moraletti_thickness": 58,
    "moraletti_height": 495,
    "moraletti_height_from_ground": 95,
    "moraletti_spacing": 420,
    "moraletti_count_large": 3,
    "moraletti_count_medium": 2,
    "moraletti_count_small": 1,
    "size_to_letter": {
        "1239": "A",
        "826": "B",
        "413": "C",
        "650": "D",
        "380": "E"
    }
}

# Blocchi standard posizionati (esempio)
placed = [
    {"width": 1239, "height": 495, "x": 0, "y": 0},      # A con 3 moraletti
    {"width": 1239, "height": 495, "x": 1239, "y": 0},   # A con 3 moraletti
    {"width": 826, "height": 495, "x": 0, "y": 495},     # B con 2 moraletti
    {"width": 826, "height": 495, "x": 826, "y": 495},   # B con 2 moraletti
    {"width": 826, "height": 495, "x": 1652, "y": 495},  # B con 2 moraletti
    {"width": 413, "height": 495, "x": 0, "y": 990},     # C con 1 moraletto
    {"width": 413, "height": 495, "x": 413, "y": 990},   # C con 1 moraletto
]

# Blocchi custom posizionati (esempio)
customs = [
    {"width": 650, "height": 495, "x": 0, "y": 1485},    # D con 2 moraletti
    {"width": 650, "height": 495, "x": 650, "y": 1485},  # D con 2 moraletti
    {"width": 380, "height": 495, "x": 1300, "y": 1485}, # E con 1 moraletto
]

# Calcola
result_lines = calculate_moraletti_info_test(config, placed, customs)

# Mostra risultato
print("\n" + "=" * 60)
print("TEST CALCOLO MORALETTI CARD STEP 5")
print("=" * 60)
print("\n📊 RISULTATO:\n")

for line in result_lines:
    print(line)

print("\n" + "=" * 60)
print("\n✅ Test completato!")

# Verifica conteggi
print("\n🔍 VERIFICA CONTEGGI ATTESI:")
print("   Standard:")
print("     - A (1239mm): 2 blocchi × 3 mor = 6 moraletti")
print("     - B (826mm): 3 blocchi × 2 mor = 6 moraletti")
print("     - C (413mm): 2 blocchi × 1 mor = 2 moraletti")
print("   Custom:")
print("     - D (650mm): 2 blocchi × 2 mor = 4 moraletti")
print("     - E (380mm): 1 blocco × 1 mor = 1 moraletto")
print("   TOTALE: 6 + 6 + 2 + 4 + 1 = 19 moraletti")

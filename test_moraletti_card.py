"""
Test rapido per verificare il calcolo moraletti nella card dello step 5
"""

# Simulazione dati
enhanced_info = {
    "enhanced": True,
    "config": {
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
    },
    "automatic_measurements": {}
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

# Import funzione
from utils.preview_generator import _calculate_moraletti_info

# Calcola
result = _calculate_moraletti_info(enhanced_info, placed, customs)

# Mostra risultato
print("\n" + "=" * 60)
print("TEST CALCOLO MORALETTI CARD STEP 5")
print("=" * 60)
print("\n📊 RISULTATO:\n")

if '_raw_lines' in result:
    for line in result['_raw_lines']:
        print(line)
else:
    print("ERRORE: formato non previsto")
    print(result)

print("\n" + "=" * 60)
print("\n✅ Test completato!")

# Verifica conteggi
print("\n🔍 VERIFICA CONTEGGI:")
print("   Standard:")
print("     - A (1239mm): 2 blocchi × 3 mor = 6 moraletti")
print("     - B (826mm): 3 blocchi × 2 mor = 6 moraletti")
print("     - C (413mm): 2 blocchi × 1 mor = 2 moraletti")
print("   Custom:")
print("     - D (650mm): 2 blocchi × 2 mor = 4 moraletti")
print("     - E (380mm): 1 blocco × 1 mor = 1 moraletto")
print("   TOTALE: 6 + 6 + 2 + 4 + 1 = 19 moraletti")

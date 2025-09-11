"""
Configuration & Constants
Configurazioni e costanti globali del sistema wall-build.
"""

from typing import List, Dict


# ────────────────────────────────────────────────────────────────────────────────
# Tolerances & Precision Constants
# ────────────────────────────────────────────────────────────────────────────────

SCARTO_CUSTOM_MM = 5          # tolleranza matching tipi custom
AREA_EPS = 1e-3               # area minima per considerare una geometria
COORD_EPS = 1e-6              # precisione coordinate
DISPLAY_MM_PER_M = 1000.0     # conversione mm per metro


# ────────────────────────────────────────────────────────────────────────────────
# Optimization Constants
# ────────────────────────────────────────────────────────────────────────────────

MICRO_REST_MM = 15.0          # soglia per attivare backtrack del resto finale (coda riga)
KEEP_OUT_MM = 2.0             # margine attorno ad aperture per evitare micro-sfridi
SPLIT_MAX_WIDTH_MM = 413      # larghezza max per slice CU2 (profilo rigido) - limite tecnico taglio


# ────────────────────────────────────────────────────────────────────────────────
# Block Library (Standard Blocks in mm)
# ────────────────────────────────────────────────────────────────────────────────

BLOCK_HEIGHT = 495                          # altezza standard blocchi
BLOCK_WIDTHS = [1239, 826, 413]            # larghezze: Grande, Medio, Piccolo
SIZE_TO_LETTER = {1239: "A", 826: "B", 413: "C"}  # mapping dimensione -> lettera


# ────────────────────────────────────────────────────────────────────────────────
# Block Ordering Strategies
# ────────────────────────────────────────────────────────────────────────────────

# Ordini di prova per i blocchi – si sceglie il migliore per il segmento
BLOCK_ORDERS = [
    [1239, 826, 413],  # Prima grandi, poi medi, poi piccoli
    [826, 1239, 413],  # Prima medi, poi grandi, poi piccoli
]


# ────────────────────────────────────────────────────────────────────────────────
# Runtime Storage
# ────────────────────────────────────────────────────────────────────────────────

# Storage per sessioni (in-memory per semplicità)
SESSIONS: Dict[str, Dict] = {}


# ────────────────────────────────────────────────────────────────────────────────
# Default Configuration Builder
# ────────────────────────────────────────────────────────────────────────────────

def get_default_config() -> Dict:
    """
    Restituisce la configurazione di default del sistema.
    
    Returns:
        Dict con tutti i parametri di configurazione
    """
    return {
        "scarto_custom_mm": SCARTO_CUSTOM_MM,
        "area_eps": AREA_EPS,
        "coord_eps": COORD_EPS,
        "display_mm_per_m": DISPLAY_MM_PER_M,
        "micro_rest_mm": MICRO_REST_MM,
        "keep_out_mm": KEEP_OUT_MM,
        "split_max_width_mm": SPLIT_MAX_WIDTH_MM,
        "block_height": BLOCK_HEIGHT,
        "block_widths": BLOCK_WIDTHS,
        "size_to_letter": SIZE_TO_LETTER,
        "block_orders": BLOCK_ORDERS
    }

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
# Block Customization System (Similar to Color Theme System)
# ────────────────────────────────────────────────────────────────────────────────

def get_default_block_schema() -> Dict:
    """
    Restituisce lo schema blocchi di default del sistema.
    
    Returns:
        Dict con le dimensioni standard dei blocchi
    """
    return {
        "block_height": BLOCK_HEIGHT,
        "block_widths": BLOCK_WIDTHS.copy(),  # [1239, 826, 413]
        "size_to_letter": SIZE_TO_LETTER.copy(),  # {1239: "A", 826: "B", 413: "C"}
        "schema_type": "standard"  # Indica che è lo schema di default
    }


def create_custom_block_schema(custom_widths: List[int], custom_height: int = None) -> Dict:
    """
    Crea un nuovo schema blocchi personalizzato.
    
    Args:
        custom_widths: Lista delle larghezze personalizzate [w1, w2, w3]
        custom_height: Altezza personalizzata (opzionale)
        
    Returns:
        Dict con lo schema personalizzato
    """
    if custom_height is None:
        custom_height = BLOCK_HEIGHT
    
    # Crea mapping personalizzato dimensione -> lettera
    # Ordina per dimensione decrescente e assegna A, B, C...
    sorted_widths = sorted(custom_widths, reverse=True)
    custom_size_to_letter = {}
    
    for i, width in enumerate(sorted_widths):
        letter = chr(ord('A') + i)  # A, B, C, D, E...
        custom_size_to_letter[width] = letter
    
    return {
        "block_height": custom_height,
        "block_widths": custom_widths,
        "size_to_letter": custom_size_to_letter,
        "schema_type": "custom"  # Indica che è personalizzato
    }


def get_block_schema_from_frontend(block_dimensions: Dict = None) -> Dict:
    """
    Determina quale schema blocchi usare basandosi sui dati dal frontend.
    
    LOGICA: SE le misure sono uguali al default → usa schema standard
            ALTRIMENTI → crea schema personalizzato
    
    Args:
        block_dimensions: Dati blocchi dal frontend nel formato:
        {
            "block_widths": [w1, w2, w3],
            "block_height": h,
            "block_depth": d  # ignorato per il packing
        }
    
    Returns:
        Dict con lo schema blocchi da utilizzare
    """
    
    # Default fallback
    if not block_dimensions:
        print("📦 Nessuna dimensione personalizzata → Schema STANDARD")
        return get_default_block_schema()
    
    # Estrai dimensioni dal frontend
    frontend_widths = block_dimensions.get("block_widths", BLOCK_WIDTHS)
    frontend_height = block_dimensions.get("block_height", BLOCK_HEIGHT)
    
    # Converti a interi per confronto preciso
    frontend_widths_int = [int(w) for w in frontend_widths]
    frontend_height_int = int(frontend_height)
    
    # Ordina entrambe le liste per confronto corretto
    default_widths_sorted = sorted(BLOCK_WIDTHS)
    frontend_widths_sorted = sorted(frontend_widths_int)
    
    # Controlla se sono identiche al default
    is_default_widths = (frontend_widths_sorted == default_widths_sorted)
    is_default_height = (frontend_height_int == BLOCK_HEIGHT)
    
    if is_default_widths and is_default_height:
        print(f"✅ Dimensioni identiche al default {BLOCK_WIDTHS}×{BLOCK_HEIGHT} → Schema STANDARD")
        return get_default_block_schema()
    else:
        print(f"🔧 Dimensioni personalizzate {frontend_widths_int}×{frontend_height_int} → Schema CUSTOM")
        return create_custom_block_schema(frontend_widths_int, frontend_height_int)


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

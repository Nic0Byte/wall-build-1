"""
Configuration & Constants
Configurazioni e costanti globali del sistema wall-build.
"""

import os
from typing import List, Dict

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()  # Carica variabili da .env se presente
    _ENV_LOADED = True
except ImportError:
    _ENV_LOADED = False

# Helper per leggere variabili ambiente con fallback
def get_env_bool(key: str, default: bool) -> bool:
    """Legge variabile ambiente come boolean con fallback."""
    value = os.getenv(key, str(default)).lower()
    return value in ('true', '1', 'yes', 'on')

def get_env_int(key: str, default: int) -> int:
    """Legge variabile ambiente come int con fallback."""
    try:
        return int(os.getenv(key, str(default)))
    except ValueError:
        return default

def get_env_float(key: str, default: float) -> float:
    """Legge variabile ambiente come float con fallback."""
    try:
        return float(os.getenv(key, str(default)))
    except ValueError:
        return default

def get_env_list_int(key: str, default: List[int]) -> List[int]:
    """Legge lista di interi da env (formato: '1,2,3') con fallback."""
    value = os.getenv(key)
    if not value:
        return default
    try:
        return [int(x.strip()) for x in value.split(',') if x.strip()]
    except ValueError:
        return default


# ────────────────────────────────────────────────────────────────────────────────
# Tolerances & Precision Constants (with environment support)
# ────────────────────────────────────────────────────────────────────────────────

SCARTO_CUSTOM_MM = get_env_int('SCARTO_CUSTOM_MM', 5)          # tolleranza matching tipi custom
AREA_EPS = get_env_float('AREA_EPS', 1e-3)                     # area minima per considerare una geometria
COORD_EPS = get_env_float('COORD_EPS', 1e-6)                   # precisione coordinate
DISPLAY_MM_PER_M = get_env_float('DISPLAY_MM_PER_M', 1000.0)   # conversione mm per metro


# ────────────────────────────────────────────────────────────────────────────────
# Optimization Constants (with environment support)
# ────────────────────────────────────────────────────────────────────────────────

MICRO_REST_MM = get_env_float('MICRO_REST_MM', 15.0)           # soglia per attivare backtrack del resto finale (coda riga)
KEEP_OUT_MM = get_env_float('KEEP_OUT_MM', 2.0)               # margine attorno ad aperture per evitare micro-sfridi
SPLIT_MAX_WIDTH_MM = get_env_int('SPLIT_MAX_WIDTH_MM', 413)    # larghezza max per slice CU2 (profilo rigido) - limite tecnico taglio


# ────────────────────────────────────────────────────────────────────────────────
# Block Library (Standard Blocks in mm - with environment support)
# ────────────────────────────────────────────────────────────────────────────────

BLOCK_HEIGHT = get_env_int('BLOCK_HEIGHT', 495)                      # altezza standard blocchi
BLOCK_WIDTHS = get_env_list_int('BLOCK_WIDTHS', [1239, 826, 413])    # larghezze: Grande, Medio, Piccolo

# Crea mapping dimensione -> lettera dinamicamente
def _create_size_to_letter_mapping(widths: List[int]) -> Dict[int, str]:
    """Crea mapping dimensione -> lettera ordinando per dimensione decrescente."""
    sorted_widths = sorted(widths, reverse=True)
    return {width: chr(ord('A') + i) for i, width in enumerate(sorted_widths)}

SIZE_TO_LETTER = _create_size_to_letter_mapping(BLOCK_WIDTHS)  # mapping dimensione -> lettera


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
# Server & Database Configuration (with environment support)
# ────────────────────────────────────────────────────────────────────────────────

# Server settings
SERVER_HOST = os.getenv('HOST', '0.0.0.0')
SERVER_PORT = get_env_int('PORT', 8000)
DEBUG = get_env_bool('DEBUG', False)
RELOAD = get_env_bool('RELOAD', False)

# CORS settings
CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*').split(',') if os.getenv('CORS_ORIGINS', '*') != '*' else ['*']

# Security
SECRET_KEY = os.getenv('SECRET_KEY', 'wallbuild_secure_secret_key_2024_change_in_production')
JWT_EXPIRE_MINUTES = get_env_int('JWT_EXPIRE_MINUTES', 30)

# Database
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///data/wallbuild.db')
DATABASE_TIMEOUT = get_env_int('DATABASE_TIMEOUT', 20)
DATABASE_ECHO = get_env_bool('DATABASE_ECHO', False)

# Logging
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FORMAT = os.getenv('LOG_FORMAT', 'text')  # text or json
VERBOSE_LOGGING = get_env_bool('VERBOSE_LOGGING', False)

# File Storage
OUTPUT_DIR = os.getenv('OUTPUT_DIR', 'output')
UPLOAD_DIR = os.getenv('UPLOAD_DIR', 'uploads')
MAX_UPLOAD_SIZE = os.getenv('MAX_UPLOAD_SIZE', '50MB')


# ────────────────────────────────────────────────────────────────────────────────
# Environment Info & Debug
# ────────────────────────────────────────────────────────────────────────────────

def get_environment_info() -> Dict:
    """Restituisce informazioni sull'ambiente di configurazione."""
    return {
        "dotenv_loaded": _ENV_LOADED,
        "has_env_file": os.path.exists('.env'),
        "debug_mode": DEBUG,
        "server": f"{SERVER_HOST}:{SERVER_PORT}",
        "database": DATABASE_URL,
        "cors_origins": CORS_ORIGINS,
        "block_config": {
            "widths": BLOCK_WIDTHS,
            "height": BLOCK_HEIGHT,
            "mapping": SIZE_TO_LETTER
        }
    }

def print_configuration_summary():
    """Stampa un riassunto della configurazione caricata."""
    info = get_environment_info()
    print("🔧 Wall-Build Configuration Summary")
    print("=" * 40)
    print(f"📄 Environment file loaded: {'✅' if info['has_env_file'] else '❌'}")
    print(f"🐛 Debug mode: {'✅' if info['debug_mode'] else '❌'}")
    print(f"🌐 Server: {info['server']}")
    print(f"🗄️  Database: {info['database']}")
    print(f"🔒 CORS Origins: {', '.join(info['cors_origins'])}")
    print(f"🧱 Blocks: {info['block_config']['widths']} × {info['block_config']['height']}mm")
    print(f"🔤 Mapping: {info['block_config']['mapping']}")
    print("=" * 40)


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
    Restituisce la configurazione completa del sistema.
    Include sia valori hardcoded che quelli da environment.
    
    Returns:
        Dict con tutti i parametri di configurazione
    """
    return {
        # Algoritmo constants
        "scarto_custom_mm": SCARTO_CUSTOM_MM,
        "area_eps": AREA_EPS,
        "coord_eps": COORD_EPS,
        "display_mm_per_m": DISPLAY_MM_PER_M,
        "micro_rest_mm": MICRO_REST_MM,
        "keep_out_mm": KEEP_OUT_MM,
        "split_max_width_mm": SPLIT_MAX_WIDTH_MM,
        # Block configuration
        "block_height": BLOCK_HEIGHT,
        "block_widths": BLOCK_WIDTHS,
        "size_to_letter": SIZE_TO_LETTER,
        "block_orders": BLOCK_ORDERS,
        # Server configuration
        "server_host": SERVER_HOST,
        "server_port": SERVER_PORT,
        "debug": DEBUG,
        "reload": RELOAD,
        # Security
        "secret_key": SECRET_KEY,
        "jwt_expire_minutes": JWT_EXPIRE_MINUTES,
        # Database
        "database_url": DATABASE_URL,
        "database_timeout": DATABASE_TIMEOUT,
        "database_echo": DATABASE_ECHO,
        # CORS
        "cors_origins": CORS_ORIGINS,
        # Logging
        "log_level": LOG_LEVEL,
        "log_format": LOG_FORMAT,
        "verbose_logging": VERBOSE_LOGGING,
        # Storage
        "output_dir": OUTPUT_DIR,
        "upload_dir": UPLOAD_DIR,
        "max_upload_size": MAX_UPLOAD_SIZE,
        # Environment info
        "environment_info": get_environment_info()
    }

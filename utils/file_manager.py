"""
File Management Utilities
Gestione percorsi di output organizzati e generazione nomi file unici.
"""

import os
import datetime
import uuid
from typing import Dict


def setup_output_directories() -> Dict[str, str]:
    """Crea e restituisce i percorsi delle cartelle di output organizzate."""
    base_output = "output"
    
    # Crea directory principali se non esistono
    os.makedirs(base_output, exist_ok=True)
    
    # Sottocartelle per tipologia
    subdirs = {
        'json': os.path.join(base_output, 'json'),
        'pdf': os.path.join(base_output, 'pdf'), 
        'dxf': os.path.join(base_output, 'dxf'),
        'images': os.path.join(base_output, 'images'),
        'svg': os.path.join(base_output, 'svg'),
        'reports': os.path.join(base_output, 'reports'),
        'schemas': os.path.join(base_output, 'schemas'),
        'temp': os.path.join(base_output, 'temp')
    }
    
    # Crea tutte le sottocartelle
    for subdir in subdirs.values():
        os.makedirs(subdir, exist_ok=True)
    
    return subdirs


def get_organized_output_path(filename: str, file_type: str = None) -> str:
    """
    Determina il percorso organizzato per un file di output.
    
    Args:
        filename: Nome del file
        file_type: Tipo esplicito ('json', 'pdf', 'dxf', 'images', 'svg')
    
    Returns:
        Percorso completo organizzato
    """
    dirs = setup_output_directories()
    
    # Auto-detect tipo da estensione se non specificato
    if not file_type:
        ext = os.path.splitext(filename)[1].lower()
        type_mapping = {
            '.json': 'json',
            '.pdf': 'pdf', 
            '.dxf': 'dxf',
            '.png': 'images',
            '.jpg': 'images',
            '.jpeg': 'images',
            '.svg': 'svg',
            '.gif': 'images',
            '.bmp': 'images'
        }
        file_type = type_mapping.get(ext, 'temp')
    
    # Fallback per tipi non riconosciuti
    if file_type not in dirs:
        file_type = 'temp'
    
    return os.path.join(dirs[file_type], filename)


def generate_unique_filename(base_name: str, extension: str, project_id: str = None) -> str:
    """
    Genera un nome file unico con timestamp e ID progetto.
    
    Args:
        base_name: Nome base (es. 'distinta', 'report', 'schema')
        extension: Estensione file (es. '.json', '.pdf', '.dxf')
        project_id: ID progetto opzionale
    
    Returns:
        Nome file unico
    """
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Aggiungi microsecondi per unicità anche in chiamate rapide
    microsecs = datetime.datetime.now().microsecond // 1000  # millisecondi
    
    if project_id:
        return f"{base_name}_{project_id}_{timestamp}_{microsecs:03d}{extension}"
    else:
        # Genera ID casuale se non fornito
        short_id = uuid.uuid4().hex[:8]
        return f"{base_name}_{short_id}_{timestamp}_{microsecs:03d}{extension}"

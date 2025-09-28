"""
Block utilities and summary functions.

This module contains utility functions for managing and summarizing blocks,
extracted from dxf_exporter.py to maintain separation of concerns.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from utils.config import SIZE_TO_LETTER


__all__ = ["summarize_blocks"]


def summarize_blocks(placed: List[Dict], size_to_letter: Optional[Dict[int, str]] = None) -> Dict[str, int]:
    """
    Riassume blocchi standard raggruppando per tipo, con supporto per mapping personalizzato.
    
    Args:
        placed: Lista blocchi piazzati
        size_to_letter: Mapping opzionale da larghezza a lettera per dimensioni personalizzate
    """
    summary: Dict[str, int] = {}
    
    # Se abbiamo un mapping personalizzato, usa quello per correggere i tipi
    if size_to_letter:
        # Crea mapping intelligente: da larghezza effettiva a larghezza logica
        logical_widths = [int(w) for w in size_to_letter.keys()]
        logical_widths.sort(reverse=True)  # Ordina per dimensione decrescente [1500, 826, 413]
        
        # Trova tutte le larghezze effettive usate nei blocchi
        actual_widths = set()
        for blk in placed:
            if blk["type"].startswith("std_"):
                try:
                    parts = blk["type"].split("_")[1].split("x")
                    actual_width = int(parts[0])
                    actual_widths.add(actual_width)
                except (ValueError, IndexError):
                    pass
        
        actual_widths = sorted(actual_widths, reverse=True)  # Ordina per dimensione decrescente
        
        # Crea mapping: associa la larghezza effettiva più grande con quella logica più grande, etc.
        width_mapping = {}
        for i, actual_width in enumerate(actual_widths):
            if i < len(logical_widths):
                width_mapping[actual_width] = logical_widths[i]
                print(f"[DEBUG] Mapping: {actual_width}mm -> {logical_widths[i]}mm (logica)")
    
    for blk in placed:
        block_type = blk["type"]
        
        # Se abbiamo mapping personalizzato, correggi il tipo
        if size_to_letter and block_type.startswith("std_"):
            try:
                # Estrai larghezza dal tipo esistente (es. "std_1239x495" -> 1239)
                parts = block_type.split("_")[1].split("x")
                actual_width = int(parts[0])
                height = int(parts[1])
                
                # Usa il mapping per trovare la larghezza logica
                if actual_width in width_mapping:
                    logical_width = width_mapping[actual_width]
                    block_type = f"std_{logical_width}x{height}"
            except (ValueError, IndexError):
                pass  # Mantieni tipo originale se parsing fallisce
        
        summary[block_type] = summary.get(block_type, 0) + 1
    
    return summary
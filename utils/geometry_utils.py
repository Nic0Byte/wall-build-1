"""
Geometry Utilities
Funzioni utili per manipolazione di geometrie Shapely.
"""

from typing import List
from shapely.geometry import Polygon, LinearRing, MultiPolygon, box
from shapely.validation import explain_validity


# Default snap grid in millimeters 
SNAP_MM = 1.0


def snap(v: float, grid: float = SNAP_MM) -> float:
    """
    Snap a value to the nearest grid point.
    
    Args:
        v: Value to snap
        grid: Grid size (default SNAP_MM)
    
    Returns:
        Snapped value
    """
    if grid <= 0:
        return v
    return round(v / grid) * grid


def snap_bounds(p: Polygon) -> Polygon:
    """
    Snap polygon bounds to grid.
    
    Args:
        p: Polygon to snap
        
    Returns:
        New polygon with snapped bounds
    """
    minx, miny, maxx, maxy = p.bounds
    return box(snap(minx), snap(miny), snap(maxx), snap(maxy))


def polygon_holes(p: Polygon) -> List[Polygon]:
    """
    Extract interior rings as Polygon objects (apertures).
    
    Args:
        p: Polygon with potential holes
        
    Returns:
        List of hole polygons
    """
    holes = []
    for ring in p.interiors:
        if isinstance(ring, LinearRing) and len(ring.coords) >= 4:
            holes.append(Polygon(ring))
    return holes


def sanitize_polygon(p: Polygon) -> Polygon:
    """
    Sanitize a polygon making it valid.
    
    Args:
        p: Input polygon
        
    Returns:
        Valid polygon
        
    Raises:
        ValueError: If polygon cannot be fixed
    """
    if p.is_valid:
        return p
    fixed = p.buffer(0)
    if fixed.is_valid:
        return fixed
    raise ValueError(f"Polygon invalido: {explain_validity(p)}")


def ensure_multipolygon(geom) -> List[Polygon]:
    """
    Ensure geometry is returned as a list of polygons.
    
    Args:
        geom: Shapely geometry (Polygon or MultiPolygon)
        
    Returns:
        List of polygons
    """
    if isinstance(geom, Polygon):
        return [geom]
    elif isinstance(geom, MultiPolygon):
        return [g for g in geom.geoms if not g.is_empty]
    else:
        return []


def create_inner_offset_polygon(
    original_polygon: Polygon, 
    offset_mm: float
) -> Polygon:
    """
    Crea un poligono parallelo verso l'interno usando buffer negativo.
    Applica offset SOLO al perimetro esterno, preservando eventuali buchi interni.
    
    Args:
        original_polygon: Poligono originale dalla conversione DWG/SVG
        offset_mm: Distanza di offset in millimetri (valore positivo)
                   Il poligono risultante sarà ridotto di questa distanza su tutti i lati
    
    Returns:
        Poligono con offset interno applicato
        
    Raises:
        ValueError: Se offset invalido o risultato vuoto (poligono collassato)
    
    Note:
        - Usa join_style='mitre' per mantenere angoli vivi (parallelo esatto)
        - mitre_limit=3.0 previene sporgenze eccessive su angoli acuti
        - Se il risultato è MultiPolygon, seleziona la geometria più grande
    
    Example:
        >>> square = Polygon([(0,0), (1000,0), (1000,1000), (0,1000)])
        >>> inner = create_inner_offset_polygon(square, 50)
        >>> # Risultato: Polygon([(50,50), (950,50), (950,950), (50,950)])
    """
    if not isinstance(original_polygon, Polygon):
        raise ValueError(f"original_polygon deve essere Polygon, ricevuto {type(original_polygon)}")
    
    if offset_mm < 0:
        raise ValueError(f"offset_mm deve essere positivo, ricevuto {offset_mm}")
    
    if offset_mm == 0:
        return original_polygon  # Nessun offset da applicare
    
    if not original_polygon.is_valid:
        raise ValueError(f"Poligono originale invalido: {explain_validity(original_polygon)}")
    
    # Applica buffer negativo con angoli vivi (mitre join style)
    # mitre_limit controlla la sporgenza massima degli angoli acuti
    inner_polygon = original_polygon.buffer(
        -offset_mm,
        join_style='mitre',  # Mantiene angoli vivi per parallelo esatto
        mitre_limit=3.0      # Limita sporgenze su angoli molto acuti
    )
    
    # Gestisci risultato vuoto (offset troppo grande)
    if inner_polygon.is_empty:
        raise ValueError(
            f"Offset {offset_mm}mm troppo grande: il poligono è collassato. "
            f"Area originale: {original_polygon.area:.2f}mm², "
            f"Perimetro: {original_polygon.length:.2f}mm"
        )
    
    # Se il buffer ha prodotto MultiPolygon, prendi il poligono più grande
    # (può succedere con geometrie complesse o concave)
    if inner_polygon.geom_type == 'MultiPolygon':
        inner_polygon = max(inner_polygon.geoms, key=lambda p: p.area)
        print(f"   ⚠️  Buffer ha prodotto MultiPolygon, selezionata geometria più grande")
    
    # Assicurati che il risultato sia un Polygon valido
    if inner_polygon.geom_type != 'Polygon':
        raise ValueError(
            f"Buffer ha prodotto {inner_polygon.geom_type} invece di Polygon. "
            f"Offset {offset_mm}mm potrebbe essere troppo grande."
        )
    
    # Validazione finale
    if not inner_polygon.is_valid:
        # Tenta pulizia topologica
        inner_polygon = inner_polygon.buffer(0)
        if not inner_polygon.is_valid:
            raise ValueError(f"Poligono offset invalido: {explain_validity(inner_polygon)}")
    
    # Verifica che l'area si sia effettivamente ridotta
    if inner_polygon.area >= original_polygon.area:
        raise ValueError(
            f"Errore logico: area offset ({inner_polygon.area:.2f}) >= area originale ({original_polygon.area:.2f})"
        )
    
    return inner_polygon

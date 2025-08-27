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

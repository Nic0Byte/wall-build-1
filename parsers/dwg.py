"""
DWG parsing utilities extracted from the legacy monolith.
"""

from __future__ import annotations

import math
import os
import tempfile
from typing import Dict, List, Optional, Tuple

from shapely.geometry import MultiPolygon, Polygon, box
from shapely.ops import unary_union

from utils.config import AREA_EPS
from utils.geometry_utils import sanitize_polygon
from .base import ParseResult

try:
    import ezdxf  # type: ignore
    ezdxf_available = True
except ImportError:  # pragma: no cover
    ezdxf = None  # type: ignore
    ezdxf_available = False

try:
    import dxfgrabber  # type: ignore
    dxfgrabber_available = True
except ImportError:  # pragma: no cover
    dxfgrabber = None  # type: ignore
    dxfgrabber_available = False

def parse_dwg_wall(
    dwg_bytes: bytes,
    layer_wall: str = "MURO",
    layer_holes: str = "BUCHI",
) -> ParseResult:
    """Parse a DWG/DXF wall extracting wall polygon and apertures."""

    if dxfgrabber_available:
        try:
            return _parse_dwg_with_dxfgrabber(dwg_bytes, layer_wall, layer_holes)
        except Exception as exc:  # pragma: no cover
            print(f" dxfgrabber fallito: {exc}")

    if ezdxf_available:
        try:
            return _parse_dwg_with_ezdxf(dwg_bytes, layer_wall, layer_holes)
        except Exception as exc:  # pragma: no cover
            print(f" ezdxf fallito: {exc}")

    print(" Usando fallback parser...")
    return _fallback_parse_dwg(dwg_bytes)

def analyze_dwg_header(file_bytes: bytes) -> Dict[str, Optional[object]]:
    """Inspect the DWG header to determine format compatibility."""
    header = file_bytes[:20] if len(file_bytes) >= 20 else file_bytes

    info: Dict[str, Optional[object]] = {
        "is_cad": False,
        "format": "Unknown",
        "version": "Unknown",
        "compatible": False,
        "estimated_size": None,
    }

    try:
        if header.startswith(b"AC"):
            info["is_cad"] = True
            info["format"] = "AutoCAD DWG"

            if header.startswith(b"AC1014"):
                info["version"] = "R14 (1997)"
                info["compatible"] = True
            elif header.startswith(b"AC1015"):
                info["version"] = "2000"
                info["compatible"] = True
            elif header.startswith(b"AC1018"):
                info["version"] = "2004"
                info["compatible"] = True
            elif header.startswith(b"AC1021"):
                info["version"] = "2007"
                info["compatible"] = True
            elif header.startswith(b"AC1024"):
                info["version"] = "2010"
                info["compatible"] = True
            elif header.startswith(b"AC1027"):
                info["version"] = "2013"
                info["compatible"] = False
            elif header.startswith(b"AC1032"):
                info["version"] = "2018+"
                info["compatible"] = False
            else:
                info["version"] = "Sconosciuta"
                info["compatible"] = False

        elif b"SECTION" in file_bytes[:200] or b"HEADER" in file_bytes[:200]:
            info["is_cad"] = True
            info["format"] = "DXF"
            info["compatible"] = True

    except Exception:  # pragma: no cover
        pass

    return info

def try_oda_conversion(
    file_bytes: bytes,
    filename: str,
    layer_wall: str,
    layer_holes: str,
) -> ParseResult:
    """Attempt conversion through ODA File Converter and re-parse."""
    try:
        import oda_converter  # type: ignore
    except ImportError as exc:  # pragma: no cover
        raise ValueError("Modulo oda_converter non disponibile") from exc

    if not oda_converter.is_oda_available():
        raise ValueError("ODA File Converter non installato")

    print(" Tentativo conversione con ODA File Converter...")
    dxf_bytes = oda_converter.convert_dwg_to_dxf(file_bytes)
    return parse_dwg_wall(dxf_bytes, layer_wall, layer_holes)

def _parse_dwg_with_dxfgrabber(
    dwg_bytes: bytes,
    layer_wall: str,
    layer_holes: str,
) -> ParseResult:
    """Parse DWG data using dxfgrabber for improved compatibility."""
    with tempfile.NamedTemporaryFile(suffix=".dwg", delete=False) as tmp_file:
        tmp_file.write(dwg_bytes)
        tmp_path = tmp_file.name

    try:
        assert dxfgrabber is not None  # for type checkers
        dwg = dxfgrabber.readfile(tmp_path)

        print(f" DWG version: {dwg.header.get('$ACADVER', 'Unknown')}")
        print(f" Layers trovati: {len(dwg.layers)}")

        wall_geometries = _extract_dxfgrabber_geometries_by_layer(dwg, layer_wall)
        hole_geometries = _extract_dxfgrabber_geometries_by_layer(dwg, layer_holes)

        if not wall_geometries:
            raise ValueError(f"Nessuna geometria valida trovata per layer '{layer_wall}'")

        wall_polygon = _dwg_geometries_to_polygon(wall_geometries, is_wall=True)
        aperture_polygons = _dwg_geometries_to_apertures(hole_geometries)

        print(
            f" DWG parsed con dxfgrabber: parete {wall_polygon.area:.1f} mm^2, "
            f"{len(aperture_polygons)} aperture"
        )
        return wall_polygon, aperture_polygons

    finally:
        try:
            os.unlink(tmp_path)
        except Exception:  # pragma: no cover
            pass

def _extract_dxfgrabber_geometries_by_layer(dwg, layer_name: str) -> List[List[Tuple[float, float]]]:
    """Collect geometries from a specific layer using dxfgrabber."""
    geometries: List[List[Tuple[float, float]]] = []

    layer_names = [layer.name for layer in dwg.layers]
    print(f" Layer disponibili: {layer_names}")

    entities_found = 0
    for entity in dwg.entities:
        if hasattr(entity, "layer") and entity.layer.lower() == layer_name.lower():
            entities_found += 1
            coords = _extract_coords_from_dxfgrabber_entity(entity)
            if coords and len(coords) >= 3:
                geometries.append(coords)

    print(
        f" Layer '{layer_name}': {entities_found} entita trovate, "
        f"{len(geometries)} geometrie valide"
    )

    # Non usare fallback per le aperture - se il layer è vuoto, probabilmente non ci sono aperture
    if not geometries and layer_name.lower() not in ["buchi", "0", "aperture", "holes"]:
        print(f" Layer '{layer_name}' non trovato o vuoto, cercando geometrie generiche...")
        for entity in dwg.entities:
            coords = _extract_coords_from_dxfgrabber_entity(entity)
            if coords and len(coords) >= 3:
                geometries.append(coords)
                if len(geometries) >= 5:
                    break

    return geometries

def _extract_coords_from_dxfgrabber_entity(entity) -> Optional[List[Tuple[float, float]]]:
    """Convert a dxfgrabber entity into planar coordinates."""
    try:
        entity_type = entity.dxftype

        if entity_type == "LWPOLYLINE":
            return [(point[0], point[1]) for point in entity.points]

        if entity_type == "POLYLINE":
            return [(vertex.location[0], vertex.location[1]) for vertex in entity.vertices]

        if entity_type == "LINE":
            start = entity.start
            end = entity.end
            return [(start[0], start[1]), (end[0], end[1])]

        if entity_type == "CIRCLE":
            center = entity.center
            radius = entity.radius
            coords: List[Tuple[float, float]] = []
            for i in range(17):
                angle = 2 * math.pi * i / 16
                x = center[0] + radius * math.cos(angle)
                y = center[1] + radius * math.sin(angle)
                coords.append((x, y))
            return coords

        if entity_type == "ARC":
            center = entity.center
            radius = entity.radius
            start_angle = math.radians(entity.start_angle)
            end_angle = math.radians(entity.end_angle)

            if end_angle < start_angle:
                end_angle += 2 * math.pi

            coords: List[Tuple[float, float]] = []
            segments = 16
            step = (end_angle - start_angle) / segments
            for i in range(segments + 1):
                angle = start_angle + i * step
                x = center[0] + radius * math.cos(angle)
                y = center[1] + radius * math.sin(angle)
                coords.append((x, y))
            return coords

        return None

    except Exception as exc:  # pragma: no cover
        print(f" Errore estrazione coordinate da {getattr(entity, 'dxftype', 'unknown')}: {exc}")
        return None


def _parse_dwg_with_ezdxf(
    dwg_bytes: bytes,
    layer_wall: str,
    layer_holes: str,
) -> ParseResult:
    """Parse DWG data using ezdxf."""
    with tempfile.NamedTemporaryFile(suffix=".dwg", delete=False) as tmp_file:
        tmp_file.write(dwg_bytes)
        tmp_path = tmp_file.name

    try:
        assert ezdxf is not None
        doc = ezdxf.readfile(tmp_path)
        msp = doc.modelspace()

        wall_geometries = _extract_dwg_geometries_by_layer(msp, layer_wall)
        hole_geometries = _extract_dwg_geometries_by_layer(msp, layer_holes)

        if not wall_geometries:
            raise ValueError(f"Nessuna geometria valida trovata per layer '{layer_wall}'")

        wall_polygon = _dwg_geometries_to_polygon(wall_geometries, is_wall=True)
        aperture_polygons = _dwg_geometries_to_apertures(hole_geometries)

        print(
            f" DWG parsed con ezdxf: parete {wall_polygon.area:.1f} mm^2, "
            f"{len(aperture_polygons)} aperture"
        )
        return wall_polygon, aperture_polygons

    finally:
        try:
            os.unlink(tmp_path)
        except Exception:  # pragma: no cover
            pass


def _extract_dwg_geometries_by_layer(msp, layer_name: str) -> List[List[Tuple[float, float]]]:
    """Collect geometries from a specific layer using ezdxf."""
    geometries: List[List[Tuple[float, float]]] = []

    for entity in msp:
        if hasattr(entity, "dxf") and hasattr(entity.dxf, "layer"):
            if entity.dxf.layer.lower() == layer_name.lower():
                coords = _extract_coords_from_dwg_entity(entity)
                if coords and len(coords) >= 3:
                    geometries.append(coords)

    if not geometries:
        print(f" Layer '{layer_name}' non trovato, cercando geometrie generiche...")
        for entity in msp:
            coords = _extract_coords_from_dwg_entity(entity)
            if coords and len(coords) >= 3:
                geometries.append(coords)
                break

    return geometries


def _extract_coords_from_dwg_entity(entity) -> Optional[List[Tuple[float, float]]]:
    """Convert an ezdxf entity into planar coordinates."""
    try:
        entity_type = entity.dxftype()

        if entity_type == "LWPOLYLINE":
            coords = [(point[0], point[1]) for point in entity.get_points()]
            if getattr(entity, "closed", False) and coords and coords[0] != coords[-1]:
                coords.append(coords[0])
            return coords

        if entity_type == "POLYLINE":
            coords = [(vertex.dxf.location.x, vertex.dxf.location.y) for vertex in entity.vertices]
            if getattr(entity, "is_closed", False) and coords and coords[0] != coords[-1]:
                coords.append(coords[0])
            return coords

        if entity_type == "LINE":
            start = entity.dxf.start
            end = entity.dxf.end
            return [(start.x, start.y), (end.x, end.y)]

        if entity_type == "CIRCLE":
            center = entity.dxf.center
            radius = entity.dxf.radius
            coords: List[Tuple[float, float]] = []
            for i in range(17):
                angle = 2 * math.pi * i / 16
                x = center.x + radius * math.cos(angle)
                y = center.y + radius * math.sin(angle)
                coords.append((x, y))
            return coords

        if entity_type == "ARC":
            center = entity.dxf.center
            radius = entity.dxf.radius
            start_angle = math.radians(entity.dxf.start_angle)
            end_angle = math.radians(entity.dxf.end_angle)

            if end_angle < start_angle:
                end_angle += 2 * math.pi

            coords: List[Tuple[float, float]] = []
            segments = 16
            step = (end_angle - start_angle) / segments
            for i in range(segments + 1):
                angle = start_angle + i * step
                x = center.x + radius * math.cos(angle)
                y = center.y + radius * math.sin(angle)
                coords.append((x, y))
            return coords

        if entity_type == "SPLINE":
            try:
                points = entity.flattening(0.1)
                return [(p.x, p.y) for p in points]
            except Exception:  # pragma: no cover
                return None

        return None

    except Exception as exc:  # pragma: no cover
        print(f" Errore estrazione coordinate da {entity.dxftype()}: {exc}")
        return None


def _dwg_geometries_to_polygon(
    geometries: List[List[Tuple[float, float]]],
    is_wall: bool = True,
) -> Polygon:
    """Convert geometry coordinate lists into a Polygon."""
    if not geometries:
        raise ValueError("Nessuna geometria trovata per la parete")

    valid_polygons: List[Polygon] = []

    for idx, coords in enumerate(geometries):
        print(f"   🔍 Geometria {idx+1}: {len(coords)} coordinate")
        
        if len(coords) < 3:
            print(f"   ❌ Troppo poche coordinate ({len(coords)} < 3)")
            continue

        try:
            # Chiudi il poligono se necessario
            if coords[0] != coords[-1]:
                coords.append(coords[0])

            polygon = Polygon(coords)
            print(f"   📐 Poligono creato: area={polygon.area:.2f}, valid={polygon.is_valid}")
            
            # Se il poligono non è valido, prova a ripararlo con buffer(0)
            if not polygon.is_valid:
                print(f"   🔧 Riparazione poligono con buffer(0)...")
                try:
                    polygon = polygon.buffer(0)
                    print(f"   ✅ Poligono riparato: area={polygon.area:.2f}, valid={polygon.is_valid}")
                except Exception as repair_exc:
                    print(f"   ❌ Riparazione fallita: {repair_exc}")
            
            if polygon.is_valid and polygon.area > AREA_EPS:
                valid_polygons.append(polygon)
                print(f"   ✅ Poligono valido aggiunto! Area finale: {polygon.area:.2f} mm²")
            else:
                print(f"   ⚠️ Poligono scartato: area={polygon.area:.2f} (min={AREA_EPS}), valid={polygon.is_valid}")
                
        except Exception as exc:  # pragma: no cover
            print(f"   ❌ Errore creazione poligono: {exc}")
            import traceback
            print(f"   Traceback: {traceback.format_exc()}")
            continue

    if not valid_polygons:
        print(f" ❌ NESSUN POLIGONO VALIDO trovato su {len(geometries)} geometrie!")
        raise ValueError("Nessuna geometria valida trovata")

    if is_wall:
        if len(valid_polygons) == 1:
            result = valid_polygons[0]
        else:
            try:
                result = unary_union(valid_polygons)
                if isinstance(result, MultiPolygon):
                    result = max(result.geoms, key=lambda poly: poly.area)
            except Exception:
                result = max(valid_polygons, key=lambda poly: poly.area)
    else:
        result = valid_polygons[0]

    return sanitize_polygon(result)


def _dwg_geometries_to_apertures(geometries: List[List[Tuple[float, float]]]) -> List[Polygon]:
    """Convert geometry lists into aperture polygons."""
    apertures: List[Polygon] = []

    for coords in geometries:
        if len(coords) < 3:
            continue

        try:
            if coords[0] != coords[-1]:
                coords.append(coords[0])

            polygon = Polygon(coords)
            if polygon.is_valid and polygon.area > AREA_EPS:
                apertures.append(sanitize_polygon(polygon))
        except Exception as exc:  # pragma: no cover
            print(f" Apertura DWG invalida: {exc}")
            continue

    return apertures


def _fallback_parse_dwg(dwg_bytes: bytes) -> ParseResult:
    """Fallback parser when no layer specific geometry is found."""
    try:
        if not ezdxf_available or ezdxf is None:
            raise ValueError("ezdxf non disponibile")

        with tempfile.NamedTemporaryFile(suffix=".dxf", delete=False) as tmp_file:
            tmp_file.write(dwg_bytes)
            tmp_path = tmp_file.name

        try:
            doc = ezdxf.readfile(tmp_path)
            msp = doc.modelspace()

            all_geometries: List[List[Tuple[float, float]]] = []
            entity_count = 0
            for entity in msp:
                entity_count += 1
                entity_type = entity.dxftype() if hasattr(entity, 'dxftype') else 'unknown'
                coords = _extract_coords_from_dwg_entity(entity)
                if coords:
                    print(f"   Entità {entity_type}: {len(coords)} coordinate")
                    if len(coords) >= 3:
                        all_geometries.append(coords)
                    else:
                        print(f"   ⚠️ Troppo poche coordinate: {coords}")

            print(f" Fallback: trovate {entity_count} entità, {len(all_geometries)} geometrie valide")

            if not all_geometries:
                raise ValueError(f"Nessuna geometria trovata nel file DWG ({entity_count} entità totali)")

            # DEBUG: Stampa le coordinate della prima geometria
            first_geom = all_geometries[0]
            print(f" DEBUG: Prima geometria ha {len(first_geom)} punti")
            print(f" DEBUG: Primi 5 punti: {first_geom[:5]}")

            wall_polygon = _dwg_geometries_to_polygon([all_geometries[0]], is_wall=True)
            apertures = (
                _dwg_geometries_to_apertures(all_geometries[1:])
                if len(all_geometries) > 1
                else []
            )

            print(
                f" DWG fallback parsing: parete {wall_polygon.area:.1f} mm^2, "
                f"{len(apertures)} aperture"
            )
            return wall_polygon, apertures

        finally:
            try:
                os.unlink(tmp_path)
            except Exception:  # pragma: no cover
                pass

    except Exception as exc:
        import traceback
        print(f" Errore fallback DWG: {exc}")
        print(f" Traceback: {traceback.format_exc()}")
        # ❌ FALLBACK HARDCODED - RIMUOVERE IN PRODUZIONE
        print(f"⚠️ ATTENZIONE: Usando box rettangolare hardcoded 5000x2500 - NON ACCURATO!")
        example_wall = box(0, 0, 5000, 2500)
        return example_wall, []


__all__ = [
    "parse_dwg_wall",
    "analyze_dwg_header",
    "try_oda_conversion",
]


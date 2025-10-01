"""
SVG parsing utilities extracted from the legacy monolith.
"""

from __future__ import annotations

import math
import re
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Tuple

from shapely.geometry import MultiPolygon, Polygon
from shapely.ops import unary_union

from utils.config import AREA_EPS
from utils.geometry_utils import sanitize_polygon
from .base import ParseResult

try:
    import svgpathtools  # type: ignore
except Exception:  # pragma: no cover
    svgpathtools = None  # type: ignore


def parse_svg_wall(
    svg_bytes: bytes,
    layer_wall: str = "MURO",
    layer_holes: str = "BUCHI",
) -> ParseResult:
    """Parse an SVG extracting wall and apertures from dedicated layers."""
    try:
        svg_content = svg_bytes.decode("utf-8")
        root = ET.fromstring(svg_content)

        ns = {"svg": "http://www.w3.org/2000/svg"}
        scale_factor = _extract_scale_factor(root, ns)

        wall_geometries = _extract_geometries_by_layer(root, ns, layer_wall, scale_factor)
        hole_geometries = _extract_geometries_by_layer(root, ns, layer_holes, scale_factor)

        wall_polygon = _geometries_to_polygon(wall_geometries, is_wall=True)
        aperture_polygons = _geometries_to_apertures(hole_geometries)

        print(f" SVG parsed: parete {wall_polygon.area:.1f} mm^2, {len(aperture_polygons)} aperture")
        return wall_polygon, aperture_polygons

    except Exception as exc:
        print(f" Errore parsing SVG: {exc}")
        return _fallback_parse_svg(svg_bytes)


def _extract_scale_factor(root: ET.Element, ns: Dict[str, str]) -> float:
    """Determine drawing scale from viewBox or explicit units."""
    try:
        viewbox = root.get("viewBox")
        if viewbox:
            return 1.0

        width_str = root.get("width", "1000")
        width_val = float(re.findall(r"[\d.]+", width_str)[0])  # noqa: F841

        if "px" in width_str:
            return 25.4 / 96.0
        if "cm" in width_str:
            return 10.0
        if "m" in width_str:
            return 1000.0

    except Exception:
        print(" Impossibile determinare scala, usando 1:1")
        return 1.0

    return 1.0


def _extract_geometries_by_layer(
    root: ET.Element,
    ns: Dict[str, str],
    layer_name: str,
    scale: float,
) -> List[List[Tuple[float, float]]]:
    """Collect geometries from an SVG layer or from top-level elements."""
    geometries: List[List[Tuple[float, float]]] = []

    for group in root.findall('.//svg:g', ns):
        group_id = group.get('id', '')
        group_label = group.get('{http://www.inkscape.org/namespaces/inkscape}label', '')
        group_class = group.get('class', '')

        layer_match = (
            layer_name.lower() in group_id.lower()
            or layer_name.lower() in group_label.lower()
            or layer_name.lower() in group_class.lower()
            or f"layer_{layer_name.lower()}" == group_id.lower()
            or f"layer-{layer_name.lower()}" in group_class.lower()
        )

        if layer_match:
            print(f" Trovato layer '{layer_name}' nel gruppo: {group_id}")
            geometries.extend(_extract_paths_from_group(group, ns, scale))

    if not geometries:
        print(f" Layer '{layer_name}' non trovato, cercando geometrie generiche...")
        geometries.extend(_extract_paths_from_group(root, ns, scale))

    return geometries


def _extract_paths_from_group(
    group: ET.Element,
    ns: Dict[str, str],
    scale: float,
) -> List[List[Tuple[float, float]]]:
    """Extract path, polygon, polyline, rect, circle elements."""
    geometries: List[List[Tuple[float, float]]] = []

    for path in group.findall('.//svg:path', ns):
        data = path.get('d')
        if data:
            try:
                coords = _parse_svg_path(data, scale)
                if coords and len(coords) >= 3:
                    geometries.append(coords)
            except Exception as exc:
                print(f" Errore parsing path: {exc}")

    for polygon in group.findall('.//svg:polygon', ns):
        points = polygon.get('points')
        if points:
            try:
                coords = _parse_svg_polygon_points(points, scale)
                if coords and len(coords) >= 3:
                    geometries.append(coords)
                    print(f" Polygon trovato: {len(coords)} punti")
            except Exception as exc:
                print(f" Errore parsing polygon: {exc}")

    for polyline in group.findall('.//svg:polyline', ns):
        points = polyline.get('points')
        if points:
            try:
                coords = _parse_svg_polygon_points(points, scale)
                if coords and len(coords) >= 2:
                    geometries.append(coords)
                    print(f" Polyline trovata: {len(coords)} punti")
            except Exception as exc:
                print(f" Errore parsing polyline: {exc}")

    for rect in group.findall('.//svg:rect', ns):
        try:
            x = float(rect.get('x', 0)) * scale
            y = float(rect.get('y', 0)) * scale
            width = float(rect.get('width', 0)) * scale
            height = float(rect.get('height', 0)) * scale

            coords = [(x, y), (x + width, y), (x + width, y + height), (x, y + height), (x, y)]
            geometries.append(coords)
        except Exception as exc:
            print(f" Errore parsing rect: {exc}")

    for circle in group.findall('.//svg:circle', ns):
        try:
            cx = float(circle.get('cx', 0)) * scale
            cy = float(circle.get('cy', 0)) * scale
            radius = float(circle.get('r', 0)) * scale

            coords: List[Tuple[float, float]] = []
            for i in range(17):
                angle = 2 * math.pi * i / 16
                x = cx + radius * math.cos(angle)
                y = cy + radius * math.sin(angle)
                coords.append((x, y))
            geometries.append(coords)
        except Exception as exc:
            print(f" Errore parsing circle: {exc}")

    return geometries


def _parse_svg_path(path_data: str, scale: float) -> List[Tuple[float, float]]:
    """Parse an SVG path using svgpathtools when available."""
    try:
        if svgpathtools:
            path = svgpathtools.parse_path(path_data)
            coords: List[Tuple[float, float]] = []
            samples = max(50, int(path.length() / 10))
            for i in range(samples + 1):
                t = i / samples if samples > 0 else 0
                point = path.point(t)
                coords.append((point.real * scale, point.imag * scale))

            if len(coords) > 2 and (
                abs(coords[0][0] - coords[-1][0]) > 1
                or abs(coords[0][1] - coords[-1][1]) > 1
            ):
                coords.append(coords[0])

            return coords

    except Exception as exc:
        print(f" svgpathtools fallito: {exc}")

    return _parse_path_manual(path_data, scale)


def _parse_path_manual(path_data: str, scale: float) -> List[Tuple[float, float]]:
    """Simple manual parser for M/L/Z path commands."""
    coords: List[Tuple[float, float]] = []
    commands = re.findall(r'[MmLlHhVvZz][^MmLlHhVvZz]*', path_data)

    current_x, current_y = 0.0, 0.0
    start_x, start_y = 0.0, 0.0

    for cmd in commands:
        cmd_type = cmd[0]
        values = re.findall(r'-?[\d.]+', cmd[1:])
        values = [float(v) * scale for v in values]

        if cmd_type.upper() == 'M':
            if len(values) >= 2:
                current_x, current_y = values[0], values[1]
                start_x, start_y = current_x, current_y
                coords.append((current_x, current_y))

        elif cmd_type.upper() == 'L':
            for i in range(0, len(values), 2):
                if i + 1 < len(values):
                    if cmd_type.islower():
                        current_x += values[i]
                        current_y += values[i + 1]
                    else:
                        current_x, current_y = values[i], values[i + 1]
                    coords.append((current_x, current_y))

        elif cmd_type.upper() == 'Z':
            if coords and coords[0] != coords[-1]:
                coords.append((start_x, start_y))

    return coords

def _parse_svg_polygon_points(points_data: str, scale: float) -> List[Tuple[float, float]]:
    """Parse the points attribute of polygon/polyline elements."""
    coords: List[Tuple[float, float]] = []

    try:
        normalized = points_data.replace(',', ' ').strip()
        numbers = re.findall(r'-?[\d.]+', normalized)

        for i in range(0, len(numbers) - 1, 2):
            x = float(numbers[i]) * scale
            y = float(numbers[i + 1]) * scale
            coords.append((x, y))

        if len(coords) > 2 and coords[0] != coords[-1]:
            coords.append(coords[0])

    except Exception as exc:
        print(f" Errore parsing points '{points_data}': {exc}")

    return coords
def _geometries_to_polygon(
    geometries: List[List[Tuple[float, float]]],
    is_wall: bool = True,
) -> Polygon:
    """Convert coordinate lists into a Polygon."""
    if not geometries:
        raise ValueError("Nessuna geometria trovata per la parete")

    valid_polygons: List[Polygon] = []

    for coords in geometries:
        try:
            if len(coords) < 3:
                continue

            if coords[0] != coords[-1]:
                coords.append(coords[0])

            poly = Polygon(coords)
            if not poly.is_valid:
                poly = poly.buffer(0)

            if poly.is_valid and poly.area > AREA_EPS:
                valid_polygons.append(poly)
        except Exception as exc:
            print(f" Geometria scartata: {exc}")

    # NUOVO: Se non ci sono poligoni validi, prova a connettere segmenti multipli
    if not valid_polygons and len(geometries) > 1:
        print(f"🔗 Nessun poligono valido trovato, tento connessione di {len(geometries)} segmenti...")
        try:
            from utils.geometry_parser import connect_path_segments
            
            connected = connect_path_segments(geometries)
            if len(connected) >= 3:
                # Assicura che il poligono sia chiuso
                if connected[0] != connected[-1]:
                    connected.append(connected[0])
                
                poly = Polygon(connected)
                if not poly.is_valid:
                    poly = poly.buffer(0)
                
                if poly.is_valid and poly.area > AREA_EPS:
                    print(f"✅ Segmenti connessi con successo! Area: {poly.area:.2f}")
                    valid_polygons.append(poly)
                else:
                    print(f"⚠️ Poligono connesso non valido")
            else:
                print(f"⚠️ Connessione ha prodotto solo {len(connected)} punti")
        except Exception as e:
            print(f"⚠️ Errore nella connessione segmenti: {e}")

    if not valid_polygons:
        raise ValueError("Nessuna geometria valida trovata")

    if is_wall:
        if len(valid_polygons) == 1:
            return valid_polygons[0]
        largest = max(valid_polygons, key=lambda poly: poly.area)
        print(f" Trovati {len(valid_polygons)} poligoni, usando il piu grande")
        return largest

    union = unary_union(valid_polygons)
    if isinstance(union, MultiPolygon):
        union = max(union.geoms, key=lambda poly: poly.area)
    return sanitize_polygon(union)
def _geometries_to_apertures(geometries: List[List[Tuple[float, float]]]) -> List[Polygon]:
    """Convert geometry lists into aperture polygons."""
    apertures: List[Polygon] = []

    for coords in geometries:
        try:
            if len(coords) < 3:
                continue

            if coords[0] != coords[-1]:
                coords.append(coords[0])

            poly = Polygon(coords)
            if not poly.is_valid:
                poly = poly.buffer(0)

            if poly.is_valid and poly.area > AREA_EPS:
                apertures.append(poly)
        except Exception as exc:
            print(f" Apertura scartata: {exc}")

    return apertures
def _fallback_parse_svg(svg_bytes: bytes) -> ParseResult:
    """Fallback parser when dedicated layers are missing."""
    try:
        svg_content = svg_bytes.decode('utf-8')
        root = ET.fromstring(svg_content)
        ns = {'svg': 'http://www.w3.org/2000/svg'}

        scale = _extract_scale_factor(root, ns)
        all_geometries = _extract_paths_from_group(root, ns, scale)

        if not all_geometries:
            raise ValueError("Nessuna geometria trovata nel file SVG")

        valid_polygons: List[Polygon] = []
        for coords in all_geometries:
            try:
                if len(coords) >= 3:
                    if coords[0] != coords[-1]:
                        coords.append(coords[0])
                    poly = Polygon(coords).buffer(0)
                    if poly.is_valid and poly.area > AREA_EPS:
                        valid_polygons.append(poly)
            except Exception:
                continue

        if not valid_polygons:
            raise ValueError("Nessun poligono valido trovato")

        valid_polygons.sort(key=lambda poly: poly.area, reverse=True)

        wall = valid_polygons[0]
        apertures = valid_polygons[1:] if len(valid_polygons) > 1 else []

        print(f" Fallback parse: parete {wall.area:.1f} mm^2, {len(apertures)} aperture")
        return wall, apertures

    except Exception as exc:
        print(f" Anche il fallback e fallito: {exc}")
        wall = Polygon([(0, 0), (5000, 0), (5000, 3000), (0, 3000)])
        return wall, []


__all__ = ["parse_svg_wall"]

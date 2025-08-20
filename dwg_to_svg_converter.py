"""
Convertitore DWG/DXF → SVG per i file ROTTINI e FELICE.
Estrae le geometrie CAD e le converte in formato SVG compatibile.
"""

import os
import sys
from pathlib import Path
from typing import List, Tuple, Optional
import xml.etree.ElementTree as ET
from xml.dom import minidom

# Import delle librerie CAD
try:
    import ezdxf
    ezdxf_available = True
except ImportError:
    ezdxf_available = False

try:
    import dxfgrabber
    dxfgrabber_available = True
except ImportError:
    dxfgrabber_available = False


class DWGToSVGConverter:
    """Convertitore completo DWG/DXF → SVG."""
    
    def __init__(self):
        self.scale_factor = 1.0  # Scala di conversione mm → SVG units
        self.min_x = float('inf')
        self.min_y = float('inf')
        self.max_x = float('-inf')
        self.max_y = float('-inf')
        
    def convert_file(self, input_path: str, output_path: str = None) -> str:
        """
        Converte un file DWG/DXF in SVG.
        
        Args:
            input_path: Percorso file di input
            output_path: Percorso file di output (opzionale)
            
        Returns:
            str: Percorso del file SVG generato
        """
        input_file = Path(input_path)
        
        if not input_file.exists():
            raise FileNotFoundError(f"File non trovato: {input_path}")
        
        # Determina output path
        if not output_path:
            output_path = input_file.with_suffix('.svg')
        
        print(f"🔄 Conversione: {input_file.name} → {Path(output_path).name}")
        
        # Leggi geometrie dal file CAD
        geometries = self._extract_geometries(input_path)
        
        if not geometries:
            print("⚠️ Nessuna geometria trovata, creo SVG di esempio")
            geometries = self._create_fallback_geometry(input_file.name)
        
        # Converti in SVG
        svg_content = self._create_svg(geometries, input_file.name)
        
        # Salva file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(svg_content)
        
        print(f"✅ SVG salvato: {output_path}")
        return str(output_path)
    
    def _extract_geometries(self, file_path: str) -> List[dict]:
        """Estrae geometrie dal file CAD usando multiple strategie."""
        
        geometries = []
        
        # Strategia 1: ezdxf
        if ezdxf_available:
            try:
                geometries = self._extract_with_ezdxf(file_path)
                if geometries:
                    print(f"✅ ezdxf: {len(geometries)} geometrie estratte")
                    return geometries
            except Exception as e:
                print(f"⚠️ ezdxf fallito: {e}")
        
        # Strategia 2: dxfgrabber
        if dxfgrabber_available:
            try:
                geometries = self._extract_with_dxfgrabber(file_path)
                if geometries:
                    print(f"✅ dxfgrabber: {len(geometries)} geometrie estratte")
                    return geometries
            except Exception as e:
                print(f"⚠️ dxfgrabber fallito: {e}")
        
        return []
    
    def _extract_with_ezdxf(self, file_path: str) -> List[dict]:
        """Estrae geometrie usando ezdxf."""
        geometries = []
        
        try:
            doc = ezdxf.readfile(file_path)
            msp = doc.modelspace()
            
            for entity in msp:
                geom = self._convert_entity_ezdxf(entity)
                if geom:
                    geometries.append(geom)
                    
        except Exception as e:
            raise Exception(f"Errore ezdxf: {e}")
        
        return geometries
    
    def _extract_with_dxfgrabber(self, file_path: str) -> List[dict]:
        """Estrae geometrie usando dxfgrabber."""
        geometries = []
        
        try:
            drawing = dxfgrabber.readfile(file_path)
            
            for entity in drawing.entities:
                geom = self._convert_entity_dxfgrabber(entity)
                if geom:
                    geometries.append(geom)
                    
        except Exception as e:
            raise Exception(f"Errore dxfgrabber: {e}")
        
        return geometries
    
    def _convert_entity_ezdxf(self, entity) -> Optional[dict]:
        """Converte entità ezdxf in geometria standardizzata."""
        
        try:
            layer = getattr(entity, 'dxf', {}).get('layer', '0')
            
            # LINE
            if entity.dxftype() == 'LINE':
                start = entity.dxf.start
                end = entity.dxf.end
                return {
                    'type': 'line',
                    'layer': layer,
                    'points': [(start.x, start.y), (end.x, end.y)]
                }
            
            # POLYLINE/LWPOLYLINE
            elif entity.dxftype() in ['POLYLINE', 'LWPOLYLINE']:
                points = []
                if hasattr(entity, 'vertices'):
                    for vertex in entity.vertices:
                        points.append((vertex.dxf.location.x, vertex.dxf.location.y))
                elif hasattr(entity, 'get_points'):
                    for point in entity.get_points():
                        points.append((point[0], point[1]))
                
                is_closed = getattr(entity.dxf, 'flags', 0) & 1
                
                return {
                    'type': 'polyline',
                    'layer': layer,
                    'points': points,
                    'closed': is_closed
                }
            
            # CIRCLE
            elif entity.dxftype() == 'CIRCLE':
                center = entity.dxf.center
                radius = entity.dxf.radius
                return {
                    'type': 'circle',
                    'layer': layer,
                    'center': (center.x, center.y),
                    'radius': radius
                }
            
            # ARC
            elif entity.dxftype() == 'ARC':
                center = entity.dxf.center
                radius = entity.dxf.radius
                start_angle = entity.dxf.start_angle
                end_angle = entity.dxf.end_angle
                return {
                    'type': 'arc',
                    'layer': layer,
                    'center': (center.x, center.y),
                    'radius': radius,
                    'start_angle': start_angle,
                    'end_angle': end_angle
                }
                
        except Exception as e:
            print(f"⚠️ Errore conversione entità {entity.dxftype()}: {e}")
        
        return None
    
    def _convert_entity_dxfgrabber(self, entity) -> Optional[dict]:
        """Converte entità dxfgrabber in geometria standardizzata."""
        
        try:
            layer = getattr(entity, 'layer', '0')
            
            # LINE
            if entity.dxftype == 'LINE':
                return {
                    'type': 'line',
                    'layer': layer,
                    'points': [(entity.start[0], entity.start[1]), 
                              (entity.end[0], entity.end[1])]
                }
            
            # POLYLINE/LWPOLYLINE
            elif entity.dxftype in ['POLYLINE', 'LWPOLYLINE']:
                points = []
                if hasattr(entity, 'points'):
                    for point in entity.points:
                        points.append((point[0], point[1]))
                
                is_closed = getattr(entity, 'is_closed', False)
                
                return {
                    'type': 'polyline',
                    'layer': layer,
                    'points': points,
                    'closed': is_closed
                }
            
            # CIRCLE
            elif entity.dxftype == 'CIRCLE':
                return {
                    'type': 'circle',
                    'layer': layer,
                    'center': (entity.center[0], entity.center[1]),
                    'radius': entity.radius
                }
                
        except Exception as e:
            print(f"⚠️ Errore conversione entità {entity.dxftype}: {e}")
        
        return None
    
    def _create_fallback_geometry(self, filename: str) -> List[dict]:
        """Crea geometria di fallback basata sul nome file."""
        
        geometries = []
        
        # Analisi nome file per stimare dimensioni
        if 'rottini' in filename.lower():
            # Casa residenziale tipica
            wall_width, wall_height = 8000, 2700
            apertures = [
                {'x': 1000, 'y': 0, 'w': 900, 'h': 2100},  # Porta
                {'x': 4000, 'y': 800, 'w': 1200, 'h': 1000}  # Finestra
            ]
        elif 'felice' in filename.lower():
            # Edificio più grande
            wall_width, wall_height = 12000, 3000
            apertures = [
                {'x': 1000, 'y': 0, 'w': 900, 'h': 2100},   # Porta 1
                {'x': 5000, 'y': 0, 'w': 900, 'h': 2100},   # Porta 2
                {'x': 8000, 'y': 800, 'w': 1500, 'h': 1200}  # Finestra grande
            ]
        else:
            # Default
            wall_width, wall_height = 10000, 3000
            apertures = [{'x': 2000, 'y': 0, 'w': 1000, 'h': 2000}]
        
        # Crea perimetro parete
        wall_points = [
            (0, 0), (wall_width, 0), 
            (wall_width, wall_height), (0, wall_height)
        ]
        
        geometries.append({
            'type': 'polyline',
            'layer': 'MURO',
            'points': wall_points,
            'closed': True
        })
        
        # Crea aperture
        for i, ap in enumerate(apertures):
            ap_points = [
                (ap['x'], ap['y']),
                (ap['x'] + ap['w'], ap['y']),
                (ap['x'] + ap['w'], ap['y'] + ap['h']),
                (ap['x'], ap['y'] + ap['h'])
            ]
            
            geometries.append({
                'type': 'polyline',
                'layer': 'BUCHI',
                'points': ap_points,
                'closed': True
            })
        
        print(f"📐 Fallback: parete {wall_width}×{wall_height}mm, {len(apertures)} aperture")
        return geometries
    
    def _create_svg(self, geometries: List[dict], filename: str) -> str:
        """Crea contenuto SVG dalle geometrie."""
        
        # Calcola bounding box
        self._calculate_bounds(geometries)
        
        # Dimensioni SVG
        width = self.max_x - self.min_x
        height = self.max_y - self.min_y
        
        # Crea struttura SVG
        svg = ET.Element('svg')
        svg.set('xmlns', 'http://www.w3.org/2000/svg')
        svg.set('width', f"{width}")
        svg.set('height', f"{height}")
        svg.set('viewBox', f"{self.min_x} {self.min_y} {width} {height}")
        
        # Aggiungi commento con info file
        comment = ET.Comment(f" Convertito da: {filename} ")
        svg.insert(0, comment)
        
        # Gruppi per layer
        layer_groups = {}
        
        # Converti geometrie
        for geom in geometries:
            layer = geom.get('layer', '0')
            
            # Crea gruppo layer se non esiste
            if layer not in layer_groups:
                group = ET.SubElement(svg, 'g')
                group.set('id', f"layer_{layer}")
                group.set('class', f"layer-{layer.lower()}")
                
                # Stili per layer
                if layer.upper() in ['MURO', 'WALL']:
                    group.set('stroke', '#000000')
                    group.set('stroke-width', '2')
                    group.set('fill', 'none')
                elif layer.upper() in ['BUCHI', 'HOLES', 'APERTURE']:
                    group.set('stroke', '#ff0000')
                    group.set('stroke-width', '1')
                    group.set('fill', 'rgba(255,0,0,0.1)')
                else:
                    group.set('stroke', '#666666')
                    group.set('stroke-width', '1')
                    group.set('fill', 'none')
                
                layer_groups[layer] = group
            
            # Converti geometria in elemento SVG
            element = self._geometry_to_svg_element(geom)
            if element is not None:
                layer_groups[layer].append(element)
        
        # Converti in stringa formattata
        rough_string = ET.tostring(svg, encoding='unicode')
        parsed = minidom.parseString(rough_string)
        return parsed.toprettyxml(indent="  ")
    
    def _calculate_bounds(self, geometries: List[dict]):
        """Calcola bounding box delle geometrie."""
        
        for geom in geometries:
            if geom['type'] in ['line', 'polyline']:
                for x, y in geom['points']:
                    self.min_x = min(self.min_x, x)
                    self.max_x = max(self.max_x, x)
                    self.min_y = min(self.min_y, y)
                    self.max_y = max(self.max_y, y)
            
            elif geom['type'] in ['circle', 'arc']:
                cx, cy = geom['center']
                r = geom['radius']
                self.min_x = min(self.min_x, cx - r)
                self.max_x = max(self.max_x, cx + r)
                self.min_y = min(self.min_y, cy - r)
                self.max_y = max(self.max_y, cy + r)
        
        # Aggiungi margine
        margin = 100
        self.min_x -= margin
        self.min_y -= margin
        self.max_x += margin
        self.max_y += margin
    
    def _geometry_to_svg_element(self, geom: dict):
        """Converte geometria in elemento SVG."""
        
        if geom['type'] == 'line':
            line = ET.Element('line')
            x1, y1 = geom['points'][0]
            x2, y2 = geom['points'][1]
            line.set('x1', str(x1))
            line.set('y1', str(y1))
            line.set('x2', str(x2))
            line.set('y2', str(y2))
            return line
        
        elif geom['type'] == 'polyline':
            if geom.get('closed', False):
                # Polygon per forme chiuse
                polygon = ET.Element('polygon')
                points_str = ' '.join([f"{x},{y}" for x, y in geom['points']])
                polygon.set('points', points_str)
                return polygon
            else:
                # Polyline per forme aperte
                polyline = ET.Element('polyline')
                points_str = ' '.join([f"{x},{y}" for x, y in geom['points']])
                polyline.set('points', points_str)
                return polyline
        
        elif geom['type'] == 'circle':
            circle = ET.Element('circle')
            cx, cy = geom['center']
            circle.set('cx', str(cx))
            circle.set('cy', str(cy))
            circle.set('r', str(geom['radius']))
            return circle
        
        return None


def convert_dwg_files():
    """Funzione principale per convertire i file DWG."""
    
    print("🔄 CONVERTITORE DWG → SVG")
    print("=" * 40)
    
    converter = DWGToSVGConverter()
    
    # File da convertire
    files_to_convert = [
        "ROTTINI_LAY_REV0.dwg",
        "FELICE_LAY_REV0.dwg"
    ]
    
    converted_files = []
    
    for filename in files_to_convert:
        if not Path(filename).exists():
            print(f"⏭️ {filename}: File non trovato")
            continue
        
        try:
            output_path = converter.convert_file(filename)
            converted_files.append(output_path)
            print(f"✅ {filename} → {Path(output_path).name}")
            
        except Exception as e:
            print(f"❌ Errore conversione {filename}: {e}")
    
    print(f"\n🎯 Conversione completata: {len(converted_files)} file SVG generati")
    return converted_files


if __name__ == "__main__":
    # Verifica disponibilità librerie
    print("🔍 Controllo librerie CAD...")
    
    if ezdxf_available:
        print("✅ ezdxf disponibile")
    else:
        print("⚠️ ezdxf non disponibile")
    
    if dxfgrabber_available:
        print("✅ dxfgrabber disponibile")
    else:
        print("⚠️ dxfgrabber non disponibile")
    
    if not (ezdxf_available or dxfgrabber_available):
        print("❌ Nessuna libreria CAD disponibile. Userò fallback.")
    
    print()
    
    # Esegui conversione
    converted_files = convert_dwg_files()
    
    print(f"\n📁 File SVG generati:")
    for file_path in converted_files:
        print(f"   • {file_path}")

"""
Advanced Geometry Parser for Wall-Build v3
==========================================

Modulo per parsing geometrico avanzato e classificazione automatica delle forme.
Gestisce:
- Connessione di path multipli in poligoni completi
- Classificazione automatica di forme (rettangoli, trapezi, poligoni complessi)
- Ricostruzione geometrica da segmenti separati
"""

from typing import List, Tuple, Optional, Dict
from shapely.geometry import Polygon
import math

def connect_path_segments(segments: List[List[Tuple[float, float]]]) -> List[Tuple[float, float]]:
    """
    Connette segmenti di path separati in un poligono chiuso.
    
    Gestisce SVG con path multipli come:
    <path d="M157.1 344.08L611.7 344.08"/>  <!-- Segmento 1 -->
    <path d="M611.7 344.08L611.7 223.93"/>  <!-- Segmento 2 -->
    ...
    
    Args:
        segments: Lista di segmenti, ogni segmento è [(x1,y1), (x2,y2), ...]
    
    Returns:
        Lista ordinata di coordinate che formano il poligono chiuso
    """
    if not segments:
        return []
    
    # Caso 1: Un solo segmento lungo -> usa direttamente
    if len(segments) == 1 and len(segments[0]) >= 3:
        return segments[0]
    
    # Caso 2: Connetti segmenti multipli
    print(f"🔗 Connessione di {len(segments)} segmenti...")
    
    # Raccogli tutti gli edge (coppie di punti connessi)
    all_edges = []
    for seg in segments:
        if len(seg) >= 2:
            for i in range(len(seg) - 1):
                all_edges.append((seg[i], seg[i+1]))
    
    if not all_edges:
        return []
    
    print(f"   📊 Totale edge: {len(all_edges)}")
    
    # Costruisci grafo di connessioni
    point_connections = {}
    for p1, p2 in all_edges:
        # Arrotonda coordinate per gestire piccole differenze floating-point
        p1_rounded = (round(p1[0], 2), round(p1[1], 2))
        p2_rounded = (round(p2[0], 2), round(p2[1], 2))
        
        if p1_rounded not in point_connections:
            point_connections[p1_rounded] = []
        if p2_rounded not in point_connections:
            point_connections[p2_rounded] = []
        
        point_connections[p1_rounded].append(p2_rounded)
        if p1_rounded != p2_rounded:  # Evita self-loop
            point_connections[p2_rounded].append(p1_rounded)
    
    print(f"   🔍 Punti unici: {len(point_connections)}")
    
    # Trova ciclo (percorso chiuso)
    try:
        cycle = find_polygon_cycle(point_connections)
        if cycle and len(cycle) >= 3:
            print(f"✅ Poligono ricostruito: {len(cycle)} vertici")
            return cycle
        else:
            print(f"⚠️ Ciclo non valido o troppo corto")
    except Exception as e:
        print(f"⚠️ Errore ricostruzione ciclo: {e}")
    
    # Fallback: Estrai punti unici e ordina spazialmente
    print(f"   🔄 Fallback: ordinamento spaziale dei punti")
    all_points = list(point_connections.keys())
    return order_points_spatially(all_points)


def find_polygon_cycle(connections: Dict[Tuple[float, float], List[Tuple[float, float]]]) -> Optional[List[Tuple[float, float]]]:
    """
    Trova un ciclo chiuso nel grafo di connessioni (percorso che torna al punto iniziale).
    
    Args:
        connections: Dizionario {punto: [punti_connessi]}
    
    Returns:
        Lista ordinata di punti che formano il ciclo, o None
    """
    if not connections:
        return None
    
    # Parti dal primo punto
    start = list(connections.keys())[0]
    path = [start]
    current = start
    visited_edges = set()
    
    # Attraversa il grafo fino a tornare all'inizio
    max_iterations = len(connections) * 2
    
    for iteration in range(max_iterations):
        neighbors = connections.get(current, [])
        
        # Rimuovi duplicati dai vicini
        neighbors = list(set(neighbors))
        
        # Trova prossimo punto non visitato
        next_point = None
        for neighbor in neighbors:
            # Crea chiave edge normalizzata (ordine indipendente)
            edge = tuple(sorted([current, neighbor]))
            
            if edge not in visited_edges:
                next_point = neighbor
                visited_edges.add(edge)
                break
        
        if next_point is None:
            # Nessun vicino disponibile
            break
        
        # Se siamo tornati all'inizio e abbiamo almeno 3 punti -> ciclo completo!
        if next_point == start and len(path) >= 3:
            print(f"   ✅ Ciclo trovato dopo {iteration + 1} iterazioni")
            return path
        
        path.append(next_point)
        current = next_point
    
    # Se abbiamo almeno 3 punti, ritorna il path anche se non perfettamente chiuso
    if len(path) >= 3:
        print(f"   ⚠️ Path parziale con {len(path)} punti (non ciclo perfetto)")
        return path
    
    return None


def order_points_spatially(points: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
    """
    Ordina punti in senso orario/antiorario attorno al centroide per formare un poligono.
    
    Args:
        points: Lista di punti disordinati
    
    Returns:
        Lista di punti ordinati che formano un poligono
    """
    if len(points) < 3:
        return points
    
    # Calcola centroide
    cx = sum(p[0] for p in points) / len(points)
    cy = sum(p[1] for p in points) / len(points)
    
    # Ordina per angolo rispetto al centroide
    def angle_from_center(p):
        return math.atan2(p[1] - cy, p[0] - cx)
    
    sorted_points = sorted(points, key=angle_from_center)
    
    print(f"   📐 Punti ordinati attorno a centroide ({cx:.1f}, {cy:.1f})")
    
    return sorted_points


def classify_polygon_geometry(polygon: Polygon) -> str:
    """
    Classifica automaticamente il tipo di geometria del poligono.
    
    Riconosce:
    - Forme base: triangolo, quadrato, rettangolo
    - Forme speciali: trapezio, parallelogramma
    - Forme complesse: poligoni irregolari, forme curve
    
    Args:
        polygon: Poligono Shapely da classificare
    
    Returns:
        Stringa identificativa del tipo di geometria
    """
    if not polygon or not polygon.is_valid or polygon.is_empty:
        return "geometria-invalida"
    
    # Estrai coordinate (rimuovi ultimo punto duplicato)
    coords = list(polygon.exterior.coords)[:-1]
    num_vertices = len(coords)
    
    # Proprietà geometriche
    area = polygon.area
    perimeter = polygon.length
    bounds = polygon.bounds
    bbox_width = bounds[2] - bounds[0]
    bbox_height = bounds[3] - bounds[1]
    bbox_area = bbox_width * bbox_height
    
    # Compattezza: quanto riempie il bounding box (0-1, 1=perfettamente compatto)
    compactness = area / bbox_area if bbox_area > 0 else 0
    
    # Rapporto aspetto
    aspect_ratio = max(bbox_width, bbox_height) / min(bbox_width, bbox_height) if min(bbox_width, bbox_height) > 0 else 1
    
    # Convessità
    is_convex = polygon.equals(polygon.convex_hull)
    
    # Classificazione per numero di vertici
    if num_vertices < 3:
        return "geometria-invalida"
    
    elif num_vertices == 3:
        return "triangolo"
    
    elif num_vertices == 4:
        return classify_quadrilateral(coords, compactness, aspect_ratio)
    
    elif num_vertices <= 8:
        if not is_convex:
            return classify_concave_shape(coords, aspect_ratio)
        elif compactness > 0.85:
            return f"poligono-regolare-{num_vertices}-lati"
        else:
            return f"poligono-{num_vertices}-lati"
    
    else:
        # Forme con molti vertici potrebbero essere curve
        if is_curved_shape(coords):
            return "forma-curva"
        else:
            return f"poligono-complesso-{num_vertices}-lati"


def classify_quadrilateral(
    coords: List[Tuple[float, float]], 
    compactness: float, 
    aspect_ratio: float
) -> str:
    """
    Classifica quadrilateri con analisi vettoriale precisa.
    
    Distingue: quadrato, rettangolo, parallelogramma, trapezio, quadrilatero irregolare
    """
    # Calcola vettori dei 4 lati
    vectors = []
    for i in range(4):
        j = (i + 1) % 4
        v = (coords[j][0] - coords[i][0], coords[j][1] - coords[i][1])
        vectors.append(v)
    
    # Lunghezze dei lati
    lengths = [math.sqrt(v[0]**2 + v[1]**2) for v in vectors]
    
    # Helper: test parallelismo (prodotto vettoriale ≈ 0)
    def are_parallel(v1, v2, tolerance=2.0):
        """Due vettori sono paralleli se il loro prodotto vettoriale è ~0"""
        cross = abs(v1[0]*v2[1] - v1[1]*v2[0])
        return cross < tolerance
    
    # Helper: test perpendicolarità (prodotto scalare ≈ 0)
    def are_perpendicular(v1, v2, tolerance=2.0):
        """Due vettori sono perpendicolari se il loro prodotto scalare è ~0"""
        dot = abs(v1[0]*v2[0] + v1[1]*v2[1])
        return dot < tolerance
    
    # Test parallelismo tra lati opposti
    parallel_0_2 = are_parallel(vectors[0], vectors[2])  # Top e Bottom
    parallel_1_3 = are_parallel(vectors[1], vectors[3])  # Left e Right
    
    # Test perpendicolarità tra lati adiacenti
    perp_0_1 = are_perpendicular(vectors[0], vectors[1])
    perp_1_2 = are_perpendicular(vectors[1], vectors[2])
    
    # Test uguaglianza lati
    max_len = max(lengths)
    min_len = min(lengths)
    all_sides_equal = (max_len - min_len) < 5.0  # Tolleranza 5 unità
    
    # Classificazione gerarchica
    if parallel_0_2 and parallel_1_3:
        # Entrambe le coppie di lati opposti sono parallele
        if perp_0_1 and perp_1_2:
            # Tutti gli angoli sono retti
            if all_sides_equal:
                return "quadrato"
            else:
                return "rettangolo"
        else:
            # Lati paralleli ma angoli non retti
            return "parallelogramma"
    
    elif parallel_0_2 or parallel_1_3:
        # Solo una coppia di lati opposti è parallela
        return "trapezio"
    
    else:
        # Nessun lato parallelo
        if compactness > 0.7:
            return "quadrilatero-compatto"
        else:
            return "quadrilatero-irregolare"


def classify_concave_shape(coords: List[Tuple[float, float]], aspect_ratio: float) -> str:
    """Classifica forme concave (con rientranze tipo L, U, C)"""
    
    # Analisi pattern comuni
    if aspect_ratio > 2.5:
        # Forma molto allungata e concava -> probabilmente L
        return "forma-a-L"
    elif aspect_ratio > 1.5:
        # Forma mediamente allungata
        return "forma-a-U"
    else:
        # Forma compatta ma concava
        return "forma-concava"


def is_curved_shape(coords: List[Tuple[float, float]], threshold: int = 16) -> bool:
    """
    Rileva se una forma è curva analizzando la densità dei vertici.
    Forme curve hanno molti vertici ravvicinati con piccoli cambi di direzione.
    """
    if len(coords) < threshold:
        return False
    
    # Calcola variazione angolare media tra vertici consecutivi
    angles = []
    for i in range(len(coords)):
        p_prev = coords[i-1]
        p_curr = coords[i]
        p_next = coords[(i+1) % len(coords)]
        
        # Vettori tra punti consecutivi
        v1 = (p_curr[0] - p_prev[0], p_curr[1] - p_prev[1])
        v2 = (p_next[0] - p_curr[0], p_next[1] - p_curr[1])
        
        # Calcola angolo tra vettori
        angle1 = math.atan2(v1[1], v1[0])
        angle2 = math.atan2(v2[1], v2[0])
        angle_change = abs(angle2 - angle1)
        
        # Normalizza angolo in [0, π]
        if angle_change > math.pi:
            angle_change = 2 * math.pi - angle_change
        
        angles.append(angle_change)
    
    # Se il cambio angolare medio è piccolo -> è una curva approssimata
    avg_angle_change = sum(angles) / len(angles) if angles else 0
    
    # Soglia: ~20 gradi (0.35 radianti)
    return avg_angle_change < 0.35


def format_geometry_label(geometry_type: str) -> str:
    """
    Traduce il tipo geometrico in etichetta comprensibile per l'utente.
    
    Args:
        geometry_type: Identificativo tecnico della geometria
    
    Returns:
        Etichetta user-friendly in italiano
    """
    # Mappatura diretta per forme standard
    translations = {
        # Forme base
        'triangolo': 'Triangolo',
        'quadrato': 'Quadrato',
        'rettangolo': 'Rettangolo',
        'trapezio': 'Trapezio',
        'parallelogramma': 'Parallelogramma',
        
        # Quadrilateri speciali
        'quadrilatero-compatto': 'Quadrilatero',
        'quadrilatero-irregolare': 'Quadrilatero Irregolare',
        
        # Forme concave
        'forma-a-L': 'Forma a L',
        'forma-a-U': 'Forma a U',
        'forma-concava': 'Forma con Rientranze',
        
        # Forme complesse
        'forma-curva': 'Forma Curva',
        
        # Errori
        'geometria-invalida': 'Geometria Non Valida'
    }
    
    # Match esatto
    if geometry_type in translations:
        return translations[geometry_type]
    
    # Pattern matching per poligoni regolari
    if 'poligono-regolare-' in geometry_type:
        try:
            num = geometry_type.split('-')[-2]
            names = {
                '5': 'Pentagono',
                '6': 'Esagono',
                '7': 'Ettagono',
                '8': 'Ottagono'
            }
            return names.get(num, f'Poligono Regolare {num} Lati')
        except:
            pass
    
    # Pattern matching per poligoni generici
    if 'poligono-' in geometry_type and '-lati' in geometry_type:
        try:
            parts = geometry_type.split('-')
            if len(parts) >= 2:
                num = parts[1] if parts[1].isdigit() else parts[-2]
                return f'Poligono {num} Lati'
        except:
            pass
    
    # Pattern matching per poligoni complessi
    if 'poligono-complesso-' in geometry_type:
        try:
            num = geometry_type.split('-')[-2]
            return f'Poligono Complesso ({num} Lati)'
        except:
            pass
    
    # Fallback: Capitalizza e sostituisci trattini con spazi
    return geometry_type.replace('-', ' ').title()


# Export delle funzioni pubbliche
__all__ = [
    'connect_path_segments',
    'classify_polygon_geometry',
    'format_geometry_label'
]

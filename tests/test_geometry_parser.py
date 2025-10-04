#!/usr/bin/env python3
"""
Test completo del sistema di parsing geometrico avanzato
=========================================================

Testa:
1. Connessione di segmenti multipli SVG
2. Classificazione automatica della geometria
3. Accuratezza dei calcoli di area e perimetro
"""

import sys
sys.path.append('.')

from shapely.geometry import Polygon
from utils.geometry_parser import (
    connect_path_segments,
    classify_polygon_geometry,
    format_geometry_label
)

def test_trapezoid_segments():
    """Test connessione segmenti del trapezio"""
    print("="*60)
    print("TEST 1: Connessione Segmenti Trapezio")
    print("="*60)
    
    # Segmenti del trapezio dal file PROVA_MODULI.svg
    segments = [
        [(157.1, 344.08), (611.7, 344.08)],      # Bottom edge
        [(611.7, 344.08), (611.7, 223.93)],      # Right edge
        [(611.7, 223.93), (157.1, 214.46)],      # Top edge (inclinato!)
        [(157.1, 214.46), (157.1, 344.08)]       # Left edge
    ]
    
    print(f"\n📊 Input: {len(segments)} segmenti separati")
    for i, seg in enumerate(segments, 1):
        print(f"   Segmento {i}: {seg[0]} → {seg[1]}")
    
    # Connetti segmenti
    connected = connect_path_segments(segments)
    
    print(f"\n✅ Output: {len(connected)} vertici connessi")
    for i, point in enumerate(connected, 1):
        print(f"   Vertice {i}: {point}")
    
    # Crea poligono
    if connected[0] != connected[-1]:
        connected.append(connected[0])
    
    polygon = Polygon(connected[:-1])
    
    print(f"\n📐 Geometria Risultante:")
    print(f"   Valido: {polygon.is_valid}")
    print(f"   Area: {polygon.area:.2f} mm²")
    print(f"   Perimetro: {polygon.length:.2f} mm")
    
    # Valori attesi dal nostro test precedente
    expected_area = 56772.72
    expected_perimeter = 1159.07
    
    area_error = abs(polygon.area - expected_area)
    perimeter_error = abs(polygon.length - expected_perimeter)
    
    print(f"\n🎯 Confronto con valori attesi:")
    print(f"   Area attesa: {expected_area:.2f} mm²")
    print(f"   Area ottenuta: {polygon.area:.2f} mm²")
    print(f"   Errore: {area_error:.2f} mm² ({area_error/expected_area*100:.2f}%)")
    
    print(f"\n   Perimetro atteso: {expected_perimeter:.2f} mm")
    print(f"   Perimetro ottenuto: {polygon.length:.2f} mm")
    print(f"   Errore: {perimeter_error:.2f} mm ({perimeter_error/expected_perimeter*100:.2f}%)")
    
    # Verifica precisione
    if area_error < 1.0 and perimeter_error < 1.0:
        print(f"\n✅ TEST PASSATO: Connessione precisa!")
        return True, polygon
    else:
        print(f"\n❌ TEST FALLITO: Errore troppo alto")
        return False, polygon


def test_geometry_classification(polygon):
    """Test classificazione geometria"""
    print("\n" + "="*60)
    print("TEST 2: Classificazione Geometrica")
    print("="*60)
    
    # Classifica
    geometry_type = classify_polygon_geometry(polygon)
    geometry_label = format_geometry_label(geometry_type)
    
    print(f"\n🔍 Analisi Geometrica:")
    coords = list(polygon.exterior.coords)[:-1]
    print(f"   Numero vertici: {len(coords)}")
    print(f"   Area: {polygon.area:.2f} mm²")
    print(f"   Perimetro: {polygon.length:.2f} mm")
    
    bounds = polygon.bounds
    bbox_width = bounds[2] - bounds[0]
    bbox_height = bounds[3] - bounds[1]
    bbox_area = bbox_width * bbox_height
    compactness = polygon.area / bbox_area
    
    print(f"\n📦 Bounding Box:")
    print(f"   Width: {bbox_width:.2f} mm")
    print(f"   Height: {bbox_height:.2f} mm")
    print(f"   Area BB: {bbox_area:.2f} mm²")
    print(f"   Compattezza: {compactness:.2%}")
    
    print(f"\n🏷️ Classificazione:")
    print(f"   Codice: {geometry_type}")
    print(f"   Etichetta: {geometry_label}")
    
    # Verifica che sia classificato come trapezio
    if geometry_type == "trapezio":
        print(f"\n✅ TEST PASSATO: Correttamente classificato come Trapezio!")
        return True
    else:
        print(f"\n❌ TEST FALLITO: Atteso 'trapezio', ottenuto '{geometry_type}'")
        return False


def test_comparison_with_bounding_box(polygon):
    """Test confronto metodo vecchio vs nuovo"""
    print("\n" + "="*60)
    print("TEST 3: Confronto Bounding Box vs Geometria Vera")
    print("="*60)
    
    # Metodo NUOVO (geometria vera)
    area_real = polygon.area
    perimeter_real = polygon.length
    
    # Metodo VECCHIO (bounding box)
    bounds = polygon.bounds
    width_bb = bounds[2] - bounds[0]
    height_bb = bounds[3] - bounds[1]
    area_bb = width_bb * height_bb
    perimeter_bb = 2 * (width_bb + height_bb)
    
    print(f"\n🔹 METODO NUOVO (Geometria Vera):")
    print(f"   Area: {area_real:.2f} mm²")
    print(f"   Perimetro: {perimeter_real:.2f} mm")
    
    print(f"\n📦 METODO VECCHIO (Bounding Box):")
    print(f"   Area: {area_bb:.2f} mm²")
    print(f"   Perimetro: {perimeter_bb:.2f} mm")
    
    area_diff = abs(area_real - area_bb)
    perimeter_diff = abs(perimeter_real - perimeter_bb)
    
    print(f"\n⚖️ DIFFERENZE:")
    print(f"   Area: {area_diff:.2f} mm² ({area_diff/area_bb*100:.1f}%)")
    print(f"   Perimetro: {perimeter_diff:.2f} mm ({perimeter_diff/perimeter_bb*100:.1f}%)")
    
    print(f"\n💡 IMPATTO DEL FIX:")
    if area_diff > 1000:
        print(f"   ✅ Fix significativo! Evitati {area_diff:.0f} mm² di errore")
        print(f"   ✅ Precisione migliorata del {area_diff/area_bb*100:.1f}%")
        return True
    else:
        print(f"   ⚠️ Differenza minima, fix potrebbe non essere necessario per questa forma")
        return False


def test_other_shapes():
    """Test classificazione di altre forme"""
    print("\n" + "="*60)
    print("TEST 4: Classificazione Altre Forme")
    print("="*60)
    
    test_cases = [
        {
            'name': 'Rettangolo',
            'coords': [(0, 0), (100, 0), (100, 50), (0, 50)],
            'expected': 'rettangolo'
        },
        {
            'name': 'Quadrato',
            'coords': [(0, 0), (50, 0), (50, 50), (0, 50)],
            'expected': 'quadrato'
        },
        {
            'name': 'Triangolo',
            'coords': [(0, 0), (100, 0), (50, 86.6)],
            'expected': 'triangolo'
        },
        {
            'name': 'Pentagono',
            'coords': [(50, 0), (97.6, 34.5), (79.4, 90.5), (20.6, 90.5), (2.4, 34.5)],
            'expected': 'poligono-5-lati'
        }
    ]
    
    results = []
    
    for test in test_cases:
        poly = Polygon(test['coords'])
        geometry_type = classify_polygon_geometry(poly)
        geometry_label = format_geometry_label(geometry_type)
        
        passed = geometry_type == test['expected']
        status = "✅" if passed else "❌"
        
        print(f"\n{status} {test['name']}:")
        print(f"   Atteso: {test['expected']}")
        print(f"   Ottenuto: {geometry_type}")
        print(f"   Etichetta: {geometry_label}")
        
        results.append(passed)
    
    all_passed = all(results)
    print(f"\n{'✅ TUTTI I TEST PASSATI' if all_passed else '❌ ALCUNI TEST FALLITI'}")
    print(f"Risultati: {sum(results)}/{len(results)} passati")
    
    return all_passed


def main():
    """Esegui tutti i test"""
    print("\n" + "🧪 " + "="*58)
    print("TEST SUITE: Sistema di Parsing Geometrico Avanzato")
    print("="*60 + "\n")
    
    results = []
    
    # Test 1: Connessione segmenti
    try:
        success, polygon = test_trapezoid_segments()
        results.append(("Connessione Segmenti", success))
    except Exception as e:
        print(f"\n❌ ERRORE TEST 1: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Connessione Segmenti", False))
        return
    
    # Test 2: Classificazione
    try:
        success = test_geometry_classification(polygon)
        results.append(("Classificazione Geometrica", success))
    except Exception as e:
        print(f"\n❌ ERRORE TEST 2: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Classificazione Geometrica", False))
    
    # Test 3: Confronto metodi
    try:
        success = test_comparison_with_bounding_box(polygon)
        results.append(("Confronto Metodi", success))
    except Exception as e:
        print(f"\n❌ ERRORE TEST 3: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Confronto Metodi", False))
    
    # Test 4: Altre forme
    try:
        success = test_other_shapes()
        results.append(("Altre Forme", success))
    except Exception as e:
        print(f"\n❌ ERRORE TEST 4: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Altre Forme", False))
    
    # Sommario finale
    print("\n" + "="*60)
    print("📊 SOMMARIO RISULTATI")
    print("="*60)
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    total_passed = sum(1 for _, passed in results if passed)
    total_tests = len(results)
    
    print(f"\n{'='*60}")
    print(f"Risultato Finale: {total_passed}/{total_tests} test passati")
    print(f"{'='*60}\n")
    
    if total_passed == total_tests:
        print("🎉 TUTTI I TEST SONO PASSATI! Sistema funzionante correttamente.")
        return 0
    else:
        print("⚠️ ALCUNI TEST SONO FALLITI. Rivedere l'implementazione.")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

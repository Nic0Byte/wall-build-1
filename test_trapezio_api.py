#!/usr/bin/env python3
"""
Test script per verificare il fix della geometria con il trapezio SVG
"""

import requests
import json

def test_trapezio_api():
    print("=== TEST API TRAPEZIO ===")
    
    url = 'http://localhost:8000/api/parse-file'
    
    try:
        with open('PROVA_MODULI.svg', 'rb') as f:
            files = {'file': ('PROVA_MODULI.svg', f, 'image/svg+xml')}
            response = requests.post(url, files=files, timeout=30)
            
        print(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            print("\n=== RISPOSTA API ===")
            for key, value in data.items():
                if isinstance(value, (int, float)):
                    print(f"{key}: {value:.2f}")
                else:
                    print(f"{key}: {value}")
            
            print("\n=== VERIFICA FIX GEOMETRIA ===")
            
            if 'wall_area' in data and 'wall_perimeter' in data:
                area = data['wall_area']
                perimeter = data['wall_perimeter']
                
                print(f"🔹 Area geometrica vera: {area:.2f}")
                print(f"🔹 Perimetro geometrico vero: {perimeter:.2f}")
                
                if 'wall_width' in data and 'wall_height' in data:
                    width = data['wall_width']
                    height = data['wall_height']
                    bb_area = width * height
                    bb_perimeter = 2 * (width + height)
                    
                    print(f"\n📦 Calcoli bounding box:")
                    print(f"Width: {width:.2f}")
                    print(f"Height: {height:.2f}")
                    print(f"BB Area: {bb_area:.2f}")
                    print(f"BB Perimetro: {bb_perimeter:.2f}")
                    
                    diff_area = abs(area - bb_area)
                    diff_perim = abs(perimeter - bb_perimeter)
                    
                    print(f"\n⚖️ Differenze:")
                    print(f"Differenza area: {diff_area:.2f} ({diff_area/bb_area*100:.1f}%)")
                    print(f"Differenza perimetro: {diff_perim:.2f} ({diff_perim/bb_perimeter*100:.1f}%)")
                    
                    # Valori attesi dal nostro test manuale
                    expected_area = 56772.72
                    expected_perimeter = 1159.07
                    
                    print(f"\n🎯 Confronto con valori attesi:")
                    print(f"Area attesa: {expected_area:.2f}")
                    print(f"Perimetro atteso: {expected_perimeter:.2f}")
                    
                    area_match = abs(area - expected_area) < 100
                    perimeter_match = abs(perimeter - expected_perimeter) < 10
                    
                    if area_match and perimeter_match:
                        print("✅ FIX GEOMETRIA: PERFETTAMENTE FUNZIONANTE!")
                        print("Il sistema calcola correttamente area e perimetro geometrici")
                    elif diff_area > 1000:
                        print("✅ FIX GEOMETRIA: FUNZIONANTE!")
                        print("Il sistema usa geometria vera invece del bounding box")
                    else:
                        print("❌ FIX GEOMETRIA: NON FUNZIONANTE")
                        print("Il sistema sta ancora usando approssimazioni bounding box")
                else:
                    print("⚠️ Mancano wall_width o wall_height nella risposta")
            else:
                print("❌ Mancano wall_area o wall_perimeter nella risposta")
                print("Il fix potrebbe non essere stato applicato correttamente")
                
        else:
            print(f"❌ Errore HTTP: {response.status_code}")
            print(f"Risposta: {response.text}")
            
    except Exception as e:
        print(f"❌ Errore nel test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_trapezio_api()
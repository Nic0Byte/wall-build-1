"""
Test diretto del parser SVG per debug
"""
import sys
import os

# Aggiungi il path del progetto
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_svg_parsing():
    """Test diretto della funzione di parsing SVG"""
    
    # Importa la funzione dal main
    from main import parse_svg_wall
    
    # Lista dei file da testare
    test_files = [
        'test_dimensioni_blocchi.svg',
        'test_parete_semplice_custom.svg', 
        'test_minimal.svg',
        'tests/test_parete_semplice.svg'  # File di riferimento che sappiamo funziona
    ]
    
    for filename in test_files:
        print(f"\n=== TEST FILE: {filename} ===")
        
        try:
            if os.path.exists(filename):
                with open(filename, 'rb') as f:
                    svg_bytes = f.read()
                
                print(f"File size: {len(svg_bytes)} bytes")
                
                # Prova il parsing
                wall, apertures = parse_svg_wall(svg_bytes)
                
                if wall and wall.is_valid:
                    area_m2 = wall.area / 1_000_000  # converti mm² in m²
                    print(f"✅ SUCCESS: Parete {area_m2:.1f} m², {len(apertures)} aperture")
                    
                    for i, hole in enumerate(apertures):
                        hole_area_m2 = hole.area / 1_000_000
                        print(f"   Apertura {i+1}: {hole_area_m2:.1f} m²")
                else:
                    print("❌ FAILED: Parsing completato ma geometria non valida")
                    
            else:
                print(f"❌ File non trovato: {filename}")
                
        except Exception as e:
            print(f"❌ ERRORE: {e}")

if __name__ == "__main__":
    test_svg_parsing()

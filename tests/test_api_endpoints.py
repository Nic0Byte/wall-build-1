"""
Test API Endpoints Calcolo Automatico Misure
Valida funzionamento endpoint REST per enhanced packing
"""

import requests
import json
import time
import sys

# Test configurazione
BASE_URL = "http://localhost:8000"
TEST_USER = {"username": "test@test.com", "password": "test123"}

def test_calculate_measurements_endpoint():
    """Test endpoint solo calcolo misure"""
    
    # Dati test
    test_payload = {
        "polygon": [
            [0, 0], [5000, 0], [5000, 2700], [0, 2700]
        ],
        "material_config": {
            "material_thickness_mm": 14,
            "guide_width_mm": 75,
            "guide_type": "75mm",
            "wall_position": "attached",
            "is_attached_to_existing": True,
            "ceiling_height_mm": 2700,
            "enable_automatic_calculations": True
        }
    }
    
    try:
        # Login
        login_response = requests.post(f"{BASE_URL}/token", 
                                     data=TEST_USER,
                                     headers={"Content-Type": "application/x-www-form-urlencoded"})
        
        if login_response.status_code != 200:
            print("❌ Login fallito - server non disponibile o credenziali errate")
            return False
        
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test calcolo misure
        response = requests.post(f"{BASE_URL}/calculate-measurements", 
                               json=test_payload,
                               headers=headers)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Endpoint /calculate-measurements funzionante")
            print(f"   Spessore chiusura: {result['measurements']['closure_calculation']['closure_thickness_mm']}mm")
            print(f"   Formula: {result['measurements']['closure_calculation']['formula']}")
            return True
        else:
            print(f"❌ Errore endpoint: {response.status_code}")
            print(f"   Risposta: {response.text}")
            return False
    
    except requests.ConnectionError:
        print("🔌 Server non raggiungibile - avviare con: python main.py server")
        return False
    except Exception as e:
        print(f"❌ Errore test: {e}")
        return False

def test_pack_enhanced_endpoint():
    """Test endpoint packing completo"""
    
    test_payload = {
        "polygon": [
            [0, 0], [3000, 0], [3000, 2400], [0, 2400] 
        ],
        "material_config": {
            "material_thickness_mm": 18,
            "guide_width_mm": 100,
            "guide_type": "100mm",
            "wall_position": "new",
            "is_attached_to_existing": False,
            "ceiling_height_mm": 2700,
            "enable_automatic_calculations": True
        },
        "block_widths": [1239, 826, 413],
        "block_height": 495
    }
    
    try:
        # Login
        login_response = requests.post(f"{BASE_URL}/token", 
                                     data=TEST_USER,
                                     headers={"Content-Type": "application/x-www-form-urlencoded"})
        
        if login_response.status_code != 200:
            print("❌ Login fallito per test pack-enhanced")
            return False
        
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test packing enhanced
        response = requests.post(f"{BASE_URL}/pack-enhanced", 
                               json=test_payload,
                               headers=headers)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Endpoint /pack-enhanced funzionante")
            print(f"   Blocchi totali: {result['metrics']['total_blocks']}")
            print(f"   Copertura: {result['metrics']['coverage_percent']:.1f}%")
            
            if "automatic_measurements" in result:
                print(f"   Calcoli automatici: attivi")
                print(f"   Spessore: {result['automatic_measurements']['closure_calculation']['closure_thickness_mm']}mm")
            
            return True
        else:
            print(f"❌ Errore pack-enhanced: {response.status_code}")
            return False
    
    except requests.ConnectionError:
        print("🔌 Server non raggiungibile per test pack-enhanced")
        return False
    except Exception as e:
        print(f"❌ Errore test pack-enhanced: {e}")
        return False

def main():
    """Esegue tutti i test API"""
    
    print("🌐 Test API Endpoints Calcolo Automatico")
    print("=" * 45)
    print("📝 Nota: Assicurati che il server sia avviato con 'python main.py server'")
    print()
    
    tests_passed = 0
    tests_total = 2
    
    # Test 1: Calcolo misure
    print("🧪 Test 1: Endpoint /calculate-measurements")
    if test_calculate_measurements_endpoint():
        tests_passed += 1
    print()
    
    # Test 2: Packing enhanced  
    print("🧪 Test 2: Endpoint /pack-enhanced")
    if test_pack_enhanced_endpoint():
        tests_passed += 1
    print()
    
    # Risultati
    print("=" * 45)
    print(f"📊 Risultati: {tests_passed}/{tests_total} test passati")
    
    if tests_passed == tests_total:
        print("🎉 Tutti i test API sono passati!")
        print("✅ Sistema enhanced packing completamente funzionante")
    else:
        print("⚠️ Alcuni test falliti")
        print("💡 Verifica che:")
        print("   - Il server sia avviato: python main.py server")
        print("   - L'utente test@test.com esista nel database")
        print("   - Enhanced packing sia disponibile")
    
    return tests_passed == tests_total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
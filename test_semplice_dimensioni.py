"""
Test Dimensioni Blocchi - Versione Semplice ASCII
"""
import requests
import json
import time

BASE_URL = "http://localhost:8000"
LOGIN_URL = f"{BASE_URL}/api/auth/login"  
UPLOAD_URL = f"{BASE_URL}/api/upload"

def login():
    """Login per ottenere token"""
    login_data = {"username": "admin", "password": "admin123"}
    
    response = requests.post(LOGIN_URL, data=login_data)
    if response.status_code == 200:
        print("LOGIN OK")
        return response.cookies
    else:
        print(f"LOGIN FALLITO: {response.status_code}")
        return None

def test_dimensions(cookies, widths, name):
    """Test una configurazione di dimensioni"""
    print(f"\n--- TEST: {name} ---")
    print(f"Dimensioni: {widths}")
    
    # Usa il file SVG di test
    files = {
        'file': ('test_dimensioni_blocchi.svg', 
                open('test_dimensioni_blocchi.svg', 'rb'), 
                'image/svg+xml')
    }
    
    data = {
        'block_widths': ','.join(map(str, widths)),
        'row_offset': 826,
        'project_name': f'Test {name}'
    }
    
    response = requests.post(UPLOAD_URL, files=files, data=data, cookies=cookies)
    
    if response.status_code == 200:
        result = response.json()
        
        # Estrai quantita
        standard = result.get('summary', {}).get('standard', {})
        custom = result.get('summary', {}).get('custom', [])
        
        total_std = sum(standard.values())
        total_custom = len(custom)
        efficiency = result.get('efficiency', 0)
        
        print(f"RISULTATI:")
        print(f"  Standard: {standard}")
        print(f"  Tot Standard: {total_std}")
        print(f"  Tot Custom: {total_custom}")
        print(f"  Efficienza: {efficiency:.1f}%")
        
        return {
            'standard': standard,
            'total_std': total_std,
            'total_custom': total_custom,
            'efficiency': efficiency,
            'name': name,
            'dimensions': widths
        }
    else:
        print(f"ERRORE: {response.status_code}")
        return None

def main():
    print("=" * 50)
    print("TEST QUANTITA BLOCCHI CON DIVERSE DIMENSIONI")
    print("=" * 50)
    
    # Login
    cookies = login()
    if not cookies:
        return
    
    # Test cases
    tests = [
        {'name': 'Standard', 'dims': [1500, 826, 413]},
        {'name': 'Grandi', 'dims': [2000, 1000, 500]},
        {'name': 'Piccoli', 'dims': [800, 600, 400]},
        {'name': 'Enormi', 'dims': [3000, 1500, 750]}
    ]
    
    results = []
    
    for test in tests:
        time.sleep(1)  # Pausa tra i test
        result = test_dimensions(cookies, test['dims'], test['name'])
        if result:
            results.append(result)
    
    # Confronta i risultati
    print("\n" + "=" * 50)
    print("CONFRONTO RISULTATI")
    print("=" * 50)
    
    for r in results:
        print(f"{r['name']:10} -> Tot: {r['total_std']:3d} std, {r['total_custom']:3d} custom, Eff: {r['efficiency']:5.1f}%")
    
    # Verifica che ci siano differenze significative
    std_totals = [r['total_std'] for r in results]
    if len(set(std_totals)) > 1:
        print("\nRISULTATO: DIVERSE DIMENSIONI PRODUCONO QUANTITA DIVERSE! ")
        print("Il sistema calcola correttamente le differenze.")
    else:
        print("\nATTENZIONE: Tutti i test hanno prodotto le stesse quantita.")
        print("Questo potrebbe indicare un problema nel calcolo.")

if __name__ == "__main__":
    main()

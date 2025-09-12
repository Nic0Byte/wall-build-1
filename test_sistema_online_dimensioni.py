"""
Test Confronto Dimensioni Blocchi - Sistema Online
==================================================
Questo script testa il sistema online con diverse dimensioni di blocchi
per verificare che le quantità cambino effettivamente.

Parete test: 10m x 5m con apertura 2m x 2m al centro
Area utile: 10m x 5m - 2m x 2m = 46 m²
"""

import requests
import json
import time
from pathlib import Path

# URL del server (modifica se necessario)
BASE_URL = "http://localhost:8000"
LOGIN_URL = f"{BASE_URL}/api/auth/login"
UPLOAD_URL = f"{BASE_URL}/api/upload"

def login():
    """Login per ottenere il token di autenticazione"""
    login_data = {
        "username": "admin",
        "password": "admin123"
    }
    
    response = requests.post(LOGIN_URL, data=login_data)
    if response.status_code == 200:
        # Estrai token dai cookie o dalla risposta
        print("✅ Login effettuato con successo")
        return response.cookies
    else:
        print(f"❌ Errore login: {response.status_code}")
        return None

def test_block_dimensions(cookies, block_widths, test_name):
    """Test una specifica configurazione di dimensioni blocchi"""
    print(f"\n🔬 Test: {test_name}")
    print(f"📏 Dimensioni blocchi: {block_widths}")
    
    # Prepara i dati per l'upload
    files = {
        'file': ('test_dimensioni_blocchi.svg', 
                open('test_dimensioni_blocchi.svg', 'rb'), 
                'image/svg+xml')
    }
    
    data = {
        'block_widths': ','.join(map(str, block_widths)),
        'row_offset': 826,
        'project_name': f'Test {test_name}'
    }
    
    # Invia la richiesta
    response = requests.post(UPLOAD_URL, files=files, data=data, cookies=cookies)
    
    if response.status_code == 200:
        result = response.json()
        
        # Estrai le quantità dei blocchi standard
        standard_summary = result.get('summary', {}).get('standard', {})
        total_standard = sum(standard_summary.values())
        
        custom_blocks = result.get('summary', {}).get('custom', [])
        total_custom = len(custom_blocks)
        
        print(f"📊 Risultati:")
        print(f"   • Blocchi standard: {standard_summary}")
        print(f"   • Totale standard: {total_standard}")
        print(f"   • Pezzi custom: {total_custom}")
        print(f"   • Efficienza: {result.get('efficiency', 0):.1f}%")
        
        return {
            'standard_summary': standard_summary,
            'total_standard': total_standard,
            'total_custom': total_custom,
            'efficiency': result.get('efficiency', 0)
        }
    else:
        print(f"❌ Errore nella richiesta: {response.status_code}")
        if response.text:
            print(f"   Dettagli: {response.text[:200]}...")
        return None

def main():
    print("🧪 TEST CONFRONTO DIMENSIONI BLOCCHI")
    print("=" * 50)
    
    # Login
    cookies = login()
    if not cookies:
        print("❌ Impossibile proseguire senza login")
        return
    
    # Test case: diverse configurazioni di blocchi
    test_cases = [
        {
            'name': 'Standard TAKTAK',
            'dimensions': [1500, 826, 413],
            'description': 'Dimensioni standard del sistema'
        },
        {
            'name': 'Blocchi Grandi',
            'dimensions': [2000, 1000, 500],
            'description': 'Blocchi più grandi per ridurre quantità'
        },
        {
            'name': 'Blocchi Piccoli',
            'dimensions': [800, 600, 400],
            'description': 'Blocchi più piccoli per aumentare quantità'
        },
        {
            'name': 'Blocchi Enormi',
            'dimensions': [3000, 1500, 750],
            'description': 'Blocchi molto grandi per quantità minima'
        }
    ]
    
    results = []
    
    for test_case in test_cases:
        result = test_block_dimensions(
            cookies, 
            test_case['dimensions'], 
            test_case['name']
        )
        
        if result:
            result['name'] = test_case['name']
            result['dimensions'] = test_case['dimensions']
            results.append(result)
        
        time.sleep(2)  # Pausa tra i test
    
    # Analisi comparativa
    print("\n" + "=" * 60)
    print("📈 ANALISI COMPARATIVA RISULTATI")
    print("=" * 60)
    
    for result in results:
        print(f"\n🏗️  {result['name']} - {result['dimensions']}")
        print(f"   📦 Blocchi standard totali: {result['total_standard']}")
        print(f"   🔧 Pezzi custom: {result['total_custom']}")
        print(f"   ⚡ Efficienza: {result['efficiency']:.1f}%")
    
    # Verifica differenze significative
    if len(results) >= 2:
        print(f"\n🔍 VERIFICA DIFFERENZE:")
        base = results[0]
        for result in results[1:]:
            diff_standard = result['total_standard'] - base['total_standard']
            diff_custom = result['total_custom'] - base['total_custom']
            print(f"   {result['name']} vs {base['name']}:")
            print(f"     • Differenza blocchi standard: {diff_standard:+d}")
            print(f"     • Differenza pezzi custom: {diff_custom:+d}")
            
            if abs(diff_standard) > 0 or abs(diff_custom) > 0:
                print(f"     ✅ DIFFERENZA RILEVATA!")
            else:
                print(f"     ⚠️  NESSUNA DIFFERENZA - POSSIBILE PROBLEMA")

if __name__ == "__main__":
    main()

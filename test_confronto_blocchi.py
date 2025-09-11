#!/usr/bin/env python3
"""
🔬 TEST CONFRONTO NUMERO BLOCCHI
Dimostra che dimensioni diverse producono CALCOLI REALI diversi
per la stessa parete, analizzando il numero effettivo di blocchi.
"""

import requests
import json
import time
from pathlib import Path

def test_dimensioni_blocchi():
    """Testa la stessa parete con dimensioni diverse e confronta i risultati"""
    
    print("🔬 TEST CONFRONTO NUMERO BLOCCHI REALI")
    print("=" * 60)
    print()
    
    # Configurazioni di test
    test_configs = [
        {
            "name": "STANDARD",
            "dimensions": [1500, 826, 413],
            "description": "Dimensioni standard commerciali"
        },
        {
            "name": "GRANDI", 
            "dimensions": [2500, 1500, 750],
            "description": "Blocchi più grandi - dovrebbero servirne MENO"
        },
        {
            "name": "PICCOLI",
            "dimensions": [800, 500, 250], 
            "description": "Blocchi più piccoli - dovrebbero servitne PIÙ"
        }
    ]
    
    results = []
    
    for config in test_configs:
        print(f"📦 TEST {config['name']}: {config['dimensions']}")
        print(f"   {config['description']}")
        print("-" * 40)
        
        # Prepara i dati per la richiesta
        files = {
            'file': open('tests/test_parete_difficile.svg', 'rb')
        }
        
        data = {
            'config': json.dumps({
                "block_widths": config['dimensions'],
                "block_height": 495,
                "block_depth": 100
            }),
            'colors': json.dumps({
                "standardBlockColor": "#e5e7eb",
                "standardBlockBorder": "#374151", 
                "doorWindowColor": "#fee2e2",
                "doorWindowBorder": "#dc2626",
                "wallOutlineColor": "#1e40af",
                "wallLineWidth": 2,
                "customPieceColor": "#f3e8ff",
                "customPieceBorder": "#7c3aed"
            })
        }
        
        try:
            # Invia richiesta al server
            response = requests.post('http://localhost:8000/api/upload', files=files, data=data)
            
            if response.status_code == 200:
                result_data = response.json()
                
                # Estrai informazioni sui blocchi
                summary = result_data.get('summary', {})
                
                # Calcola totale blocchi standard
                total_blocks = 0
                category_details = []
                
                for key, count in summary.items():
                    if key.startswith('std_'):
                        total_blocks += count
                        # Estrai dimensioni dal nome
                        dims = key.replace('std_', '').replace('x495', '')
                        width = dims.split('x')[0] if 'x' in dims else dims
                        category_details.append(f"   • {width}mm: {count} blocchi")
                
                print(f"✅ TOTALE BLOCCHI STANDARD: {total_blocks}")
                print("   Dettaglio per categoria:")
                for detail in category_details:
                    print(detail)
                
                # Salva risultati per confronto
                results.append({
                    'config': config['name'],
                    'dimensions': config['dimensions'],
                    'total_blocks': total_blocks,
                    'details': category_details
                })
                
            else:
                print(f"❌ Errore: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Errore nella richiesta: {e}")
        
        finally:
            files['file'].close()
            
        print()
        time.sleep(1)  # Pausa tra le richieste
    
    # ANALISI COMPARATIVA
    print("🎯 ANALISI COMPARATIVA")
    print("=" * 60)
    
    if len(results) >= 2:
        print("📊 CONFRONTO TOTALI:")
        for result in results:
            print(f"   {result['config']:10} ({result['dimensions']}): {result['total_blocks']:3} blocchi totali")
        
        print()
        print("🔍 VERIFICA LOGICA:")
        
        # Confronta Standard vs Grandi
        standard = next((r for r in results if r['config'] == 'STANDARD'), None)
        grandi = next((r for r in results if r['config'] == 'GRANDI'), None)
        piccoli = next((r for r in results if r['config'] == 'PICCOLI'), None)
        
        if standard and grandi:
            if grandi['total_blocks'] < standard['total_blocks']:
                print(f"   ✅ CORRETTO: Blocchi grandi usano MENO blocchi ({grandi['total_blocks']} vs {standard['total_blocks']})")
            else:
                print(f"   ⚠️  ANOMALO: Blocchi grandi dovrebbero usare meno blocchi")
        
        if standard and piccoli:
            if piccoli['total_blocks'] > standard['total_blocks']:
                print(f"   ✅ CORRETTO: Blocchi piccoli usano PIÙ blocchi ({piccoli['total_blocks']} vs {standard['total_blocks']})")
            else:
                print(f"   ⚠️  ANOMALO: Blocchi piccoli dovrebbero usare più blocchi")
        
        print()
        print("🎯 CONCLUSIONE:")
        if len(set(r['total_blocks'] for r in results)) == len(results):
            print("   ✅ OGNI CONFIGURAZIONE PRODUCE CALCOLI DIVERSI")
            print("   ✅ IL SISTEMA CALCOLA REALMENTE IN BASE ALLE DIMENSIONI")
            print("   ✅ NON STA FALSIFICANDO I RISULTATI")
        else:
            print("   ⚠️  Alcuni risultati sono identici - possibile problema")
    
    else:
        print("❌ Non abbastanza risultati per il confronto")

if __name__ == "__main__":
    test_dimensioni_blocchi()

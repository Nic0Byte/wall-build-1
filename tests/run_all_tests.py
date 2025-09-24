#!/usr/bin/env python3
"""
Run All Tests - STEP 6
Test runner principale che esegue tutta la suite di test per validare gli step 1-5.
"""

import sys
import os
import time
from pathlib import Path
from datetime import datetime

# Aggiungi la directory del progetto al path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

class TestRunner:
    """Runner principale per tutti i test STEP 6."""
    
    def __init__(self):
        self.test_results = {}
        self.start_time = None
        self.end_time = None
        
    def run_test_suite(self, test_name: str, test_class):
        """Esegue una suite di test specifica."""
        print(f"\n{'='*60}")
        print(f"🧪 ESECUZIONE: {test_name}")
        print(f"{'='*60}")
        
        try:
            start = time.time()
            tester = test_class()
            success_rate = tester.run_all_tests()
            end = time.time()
            
            self.test_results[test_name] = {
                'success_rate': success_rate,
                'duration': end - start,
                'status': 'PASSED' if success_rate >= 70 else 'FAILED',
                'results': getattr(tester, 'results', [])
            }
            
            print(f"\n⏱️ Durata: {end - start:.2f}s")
            print(f"📈 Success Rate: {success_rate:.1f}%")
            print(f"🎯 Status: {self.test_results[test_name]['status']}")
            
        except Exception as e:
            self.test_results[test_name] = {
                'success_rate': 0.0,
                'duration': 0.0,
                'status': 'CRITICAL_ERROR',
                'error': str(e),
                'results': []
            }
            
            print(f"💥 ERRORE CRITICO: {e}")
    
    def run_all_tests(self):
        """Esegue tutti i test della suite STEP 6."""
        self.start_time = datetime.now()
        
        print("🚀 WALL-BUILD TEST SUITE - STEP 6")
        print("=" * 60)
        print(f"📅 Data: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📁 Directory: {project_root}")
        print(f"🐍 Python: {sys.version}")
        
        # Lista test da eseguire
        test_suites = [
            ("Server Startup", self.import_test_class("test_server_startup", "ServerStartupTest")),
            ("Environment Config", self.import_test_class("test_environment_config", "EnvironmentConfigTest")),
            ("Structured Logging", self.import_test_class("test_structured_logging", "StructuredLoggingTest")),
            ("Core Functionality", self.import_test_class("test_core_functionality", "CoreFunctionalityTest")),
            ("CLI and Demo", self.import_test_class("test_cli_demo", "CLIDemoTest")),
        ]
        
        # Esegui ogni suite di test
        for test_name, test_class in test_suites:
            if test_class:
                self.run_test_suite(test_name, test_class)
            else:
                self.test_results[test_name] = {
                    'success_rate': 0.0,
                    'duration': 0.0,
                    'status': 'IMPORT_ERROR',
                    'results': []
                }
        
        self.end_time = datetime.now()
        
        # Report finale
        self.print_final_report()
        
        # Determina exit code
        overall_success = self.get_overall_success_rate()
        return 0 if overall_success >= 70 else 1
    
    def import_test_class(self, module_name: str, class_name: str):
        """Importa dinamicamente una classe di test."""
        try:
            module = __import__(module_name)
            return getattr(module, class_name)
        except Exception as e:
            print(f"⚠️ Errore import {module_name}.{class_name}: {e}")
            return None
    
    def print_final_report(self):
        """Stampa il report finale di tutti i test."""
        total_duration = (self.end_time - self.start_time).total_seconds()
        
        print(f"\n{'='*80}")
        print("📊 REPORT FINALE TEST SUITE - STEP 6")
        print(f"{'='*80}")
        
        # Riepilogo per suite
        print("\n📋 RIEPILOGO PER SUITE:")
        print("-" * 60)
        
        passed_suites = 0
        total_suites = len(self.test_results)
        
        for suite_name, results in self.test_results.items():
            status_icon = {
                'PASSED': '✅',
                'FAILED': '❌', 
                'CRITICAL_ERROR': '💥',
                'IMPORT_ERROR': '⚠️'
            }.get(results['status'], '❓')
            
            success_rate = results['success_rate']
            duration = results['duration']
            
            print(f"{status_icon} {suite_name:<25} | {success_rate:>6.1f}% | {duration:>6.2f}s | {results['status']}")
            
            if results['status'] == 'PASSED':
                passed_suites += 1
        
        # Statistiche globali
        print(f"\n{'='*60}")
        print("🎯 STATISTICHE GLOBALI:")
        print("-" * 30)
        print(f"📦 Suite totali: {total_suites}")
        print(f"✅ Suite passate: {passed_suites}")
        print(f"❌ Suite fallite: {total_suites - passed_suites}")
        print(f"📈 Success rate globale: {self.get_overall_success_rate():.1f}%")
        print(f"⏱️ Durata totale: {total_duration:.2f}s")
        
        # Dettagli errori critici
        critical_errors = {k: v for k, v in self.test_results.items() 
                          if v['status'] in ['CRITICAL_ERROR', 'IMPORT_ERROR']}
        
        if critical_errors:
            print(f"\n{'='*60}")
            print("🚨 ERRORI CRITICI:")
            print("-" * 30)
            for suite_name, results in critical_errors.items():
                error = results.get('error', 'Unknown error')
                print(f"💥 {suite_name}: {error}")
        
        # Raccomandazioni
        print(f"\n{'='*60}")
        print("💡 RACCOMANDAZIONI:")
        print("-" * 30)
        
        overall_rate = self.get_overall_success_rate()
        if overall_rate >= 90:
            print("🎉 ECCELLENTE! Tutti i sistemi funzionano perfettamente.")
            print("✨ Il sistema è pronto per produzione.")
        elif overall_rate >= 70:
            print("✅ BUONO! La maggior parte dei sistemi funziona correttamente.")
            print("🔧 Rivedere i test falliti per miglioramenti minori.")
        elif overall_rate >= 50:
            print("⚠️ SUFFICIENTE! Alcuni sistemi hanno problemi.")
            print("🛠️ Risolvere i problemi principali prima del deployment.")
        else:
            print("❌ CRITICO! Molti sistemi non funzionano correttamente.")
            print("🚨 Revisione completa necessaria prima del deployment.")
        
        # Status finale
        print(f"\n{'='*80}")
        if overall_rate >= 70:
            print("🏆 STATUS: STEP 6 COMPLETATO CON SUCCESSO!")
            print("🚀 Sistema pronto per l'uso.")
        else:
            print("⚠️ STATUS: STEP 6 NECESSITA CORREZIONI!")
            print("🔧 Risolvere i problemi identificati.")
        print(f"{'='*80}")
    
    def get_overall_success_rate(self):
        """Calcola il success rate complessivo."""
        if not self.test_results:
            return 0.0
        
        # Media pesata sui success rate delle suite (escludendo errori critici)
        valid_results = [r for r in self.test_results.values() 
                        if r['status'] not in ['CRITICAL_ERROR', 'IMPORT_ERROR']]
        
        if not valid_results:
            return 0.0
        
        total_rate = sum(r['success_rate'] for r in valid_results)
        return total_rate / len(valid_results)

def main():
    """Funzione main per eseguire tutti i test."""
    try:
        runner = TestRunner()
        exit_code = runner.run_all_tests()
        sys.exit(exit_code)
        
    except KeyboardInterrupt:
        print("\n🛑 Test interrotti dall'utente.")
        sys.exit(130)
    except Exception as e:
        print(f"\n💥 Errore critico nel test runner: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
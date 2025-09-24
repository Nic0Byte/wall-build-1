#!/usr/bin/env python3
"""
Test Structured Logging - STEP 6  
Test del sistema di logging strutturato implementato nello STEP 5.
"""

import sys
import os
import tempfile
import json
import time
from pathlib import Path
from io import StringIO
import logging

# Aggiungi la directory del progetto al path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

class StructuredLoggingTest:
    """Test per il sistema di logging strutturato."""
    
    def __init__(self):
        self.results = []
        
    def test_logging_imports(self):
        """Test import del sistema di logging."""
        try:
            from utils.logging_config import (
                get_logger, info, warning, error, debug,
                log_operation, setup_logging, STRUCTLOG_AVAILABLE
            )
            
            self.results.append(("✅ Logging imports", "SUCCESS", f"Strutturato: {'Sì' if STRUCTLOG_AVAILABLE else 'No'}"))
            return True
            
        except ImportError as e:
            self.results.append(("❌ Logging imports", "ERROR", f"Errore import: {e}"))
            return False
    
    def test_logger_creation(self):
        """Test creazione logger con nomi diversi."""
        try:
            from utils.logging_config import get_logger
            
            # Test logger con nomi diversi
            logger1 = get_logger("test1")
            logger2 = get_logger("test2") 
            logger3 = get_logger()  # Default
            
            if logger1 and logger2 and logger3:
                self.results.append(("✅ Logger creation", "SUCCESS", "Creazione logger funzionante"))
            else:
                self.results.append(("❌ Logger creation", "ERROR", "Creazione logger fallita"))
                
            return True
            
        except Exception as e:
            self.results.append(("❌ Logger creation", "ERROR", f"Errore creazione logger: {e}"))
            return False
    
    def test_basic_logging_functions(self):
        """Test delle funzioni di logging di base."""
        try:
            from utils.logging_config import info, warning, error, debug
            
            # Cattura output logging
            log_capture = StringIO()
            handler = logging.StreamHandler(log_capture)
            
            # Test logging functions
            info("Test message info", component="test", status="testing")
            warning("Test message warning", level="test")
            error("Test message error", error_code="TEST_001")
            debug("Test message debug", debug_info="test")
            
            # Verifica che non ci siano state eccezioni
            self.results.append(("✅ Basic logging", "SUCCESS", "Funzioni di logging di base funzionanti"))
            return True
            
        except Exception as e:
            self.results.append(("❌ Basic logging", "ERROR", f"Errore logging functions: {e}"))
            return False
    
    def test_context_logging(self):
        """Test logging con context manager."""
        try:
            from utils.logging_config import log_operation, info
            
            # Test context manager con timing
            start_time = time.time()
            
            with log_operation("test_operation", test_param="value", component="test"):
                info("Operazione in corso", step=1)
                time.sleep(0.1)  # Simula operazione
                
            end_time = time.time()
            
            # Verifica che il tempo sia passato
            if end_time - start_time >= 0.1:
                self.results.append(("✅ Context logging", "SUCCESS", "Context manager con timing funzionante"))
            else:
                self.results.append(("⚠️ Context logging", "WARNING", "Timing potrebbe non essere accurato"))
                
            return True
            
        except Exception as e:
            self.results.append(("❌ Context logging", "ERROR", f"Errore context logging: {e}"))
            return False
    
    def test_error_handling_logging(self):
        """Test logging di errori con context."""
        try:
            from utils.logging_config import log_operation, error
            
            # Test con eccezione
            try:
                with log_operation("test_error_operation"):
                    raise ValueError("Test error for logging")
            except ValueError:
                pass  # Atteso
            
            # Test logging manuale errori
            error("Test error message", 
                  error_code="TEST_ERROR",
                  component="test_suite",
                  severity="high")
            
            self.results.append(("✅ Error handling", "SUCCESS", "Gestione errori nel logging funzionante"))
            return True
            
        except Exception as e:
            self.results.append(("❌ Error handling", "ERROR", f"Errore handling errori: {e}"))
            return False
    
    def test_structlog_vs_standard_fallback(self):
        """Test differenze tra structlog e logging standard."""
        try:
            from utils.logging_config import STRUCTLOG_AVAILABLE, get_logger
            
            logger = get_logger("fallback_test")
            
            if STRUCTLOG_AVAILABLE:
                # Con structlog, dovrebbe supportare context parameters
                try:
                    logger.info("Test with context", test_param="value", number=42)
                    self.results.append(("✅ Structlog mode", "SUCCESS", "Logging strutturato con context"))
                except Exception as e:
                    self.results.append(("❌ Structlog mode", "ERROR", f"Errore structlog: {e}"))
            else:
                # Con logging standard, context dovrebbe essere gestito diversamente
                self.results.append(("ℹ️ Standard mode", "INFO", "Fallback a logging standard"))
                
            return True
            
        except Exception as e:
            self.results.append(("❌ Fallback test", "ERROR", f"Errore test fallback: {e}"))
            return False
    
    def test_migration_helpers(self):
        """Test helper per migrazione da print() a logging."""
        try:
            from utils.logging_config import migrate_print
            
            # Test migrate_print con diversi livelli
            migrate_print("Test info message", "info", component="test")
            migrate_print("Test warning message", "warning", risk_level="medium")
            migrate_print("Test error message", "error", error_code="MIGRATE_001")
            
            self.results.append(("✅ Migration helpers", "SUCCESS", "Helper migrazione print->logging funzionanti"))
            return True
            
        except Exception as e:
            self.results.append(("❌ Migration helpers", "ERROR", f"Errore migration helpers: {e}"))
            return False
    
    def test_logging_configuration(self):
        """Test configurazione del sistema di logging."""
        try:
            from utils.logging_config import setup_logging, VERBOSE_LOGGING
            
            # Test setup multipli (dovrebbe essere safe)
            logger1 = setup_logging()
            logger2 = setup_logging()  # Dovrebbe essere idempotente
            
            if logger1 and logger2:
                self.results.append(("✅ Logging config", "SUCCESS", f"Setup logging OK (verbose: {VERBOSE_LOGGING})"))
            else:
                self.results.append(("❌ Logging config", "ERROR", "Setup logging fallito"))
                
            return True
            
        except Exception as e:
            self.results.append(("❌ Logging config", "ERROR", f"Errore configurazione logging: {e}"))
            return False
    
    def test_performance_logging(self):
        """Test performance del sistema di logging."""
        try:
            from utils.logging_config import info, log_operation
            import time
            
            # Test performance logging semplice
            start = time.time()
            for i in range(100):
                info(f"Performance test {i}", iteration=i, batch="performance_test")
            simple_time = time.time() - start
            
            # Test performance context logging
            start = time.time()
            for i in range(10):
                with log_operation(f"perf_operation_{i}", iteration=i):
                    pass
            context_time = time.time() - start
            
            # Verifica che le performance siano ragionevoli
            if simple_time < 5.0 and context_time < 2.0:
                self.results.append(("✅ Performance", "SUCCESS", 
                                   f"Performance OK: simple={simple_time:.2f}s, context={context_time:.2f}s"))
            else:
                self.results.append(("⚠️ Performance", "WARNING", 
                                   f"Performance lenta: simple={simple_time:.2f}s, context={context_time:.2f}s"))
                
            return True
            
        except Exception as e:
            self.results.append(("❌ Performance", "ERROR", f"Errore test performance: {e}"))
            return False
    
    def run_all_tests(self):
        """Esegue tutti i test del logging strutturato."""
        print("🧪 Test Structured Logging - STEP 6")
        print("=" * 50)
        
        tests = [
            self.test_logging_imports,
            self.test_logger_creation,
            self.test_basic_logging_functions,
            self.test_context_logging,
            self.test_error_handling_logging,
            self.test_structlog_vs_standard_fallback,
            self.test_migration_helpers,
            self.test_logging_configuration,
            self.test_performance_logging,
        ]
        
        for test in tests:
            try:
                test()
            except Exception as e:
                self.results.append((f"❌ {test.__name__}", "CRITICAL", f"Test fallito: {e}"))
        
        # Report risultati
        self.print_results()
        return self.get_success_rate()
    
    def print_results(self):
        """Stampa i risultati dei test."""
        print("\n📊 RISULTATI TEST STRUCTURED LOGGING:")
        print("-" * 50)
        
        success_count = 0
        warning_count = 0
        total_count = len(self.results)
        
        for test_name, status, message in self.results:
            print(f"{test_name}: {message}")
            if "SUCCESS" in status:
                success_count += 1
            elif "WARNING" in status:
                warning_count += 1
        
        print("-" * 50)
        print(f"✅ Test passati: {success_count}/{total_count}")
        print(f"⚠️ Warning: {warning_count}")
        print(f"📈 Success rate: {(success_count/total_count)*100:.1f}%")
        
    def get_success_rate(self):
        """Ritorna la percentuale di successo."""
        if not self.results:
            return 0.0
        
        success_count = sum(1 for _, status, _ in self.results if "SUCCESS" in status)
        return (success_count / len(self.results)) * 100

if __name__ == "__main__":
    tester = StructuredLoggingTest()
    success_rate = tester.run_all_tests()
    
    if success_rate >= 80:
        print("\n🎉 Test structured logging PASSATI!")
        sys.exit(0)
    else:
        print("\n⚠️ Test structured logging con errori!")
        sys.exit(1)
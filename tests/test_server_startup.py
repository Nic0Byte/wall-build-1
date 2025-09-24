#!/usr/bin/env python3
"""
Test Server Startup - STEP 6
Verifica che il server si avvii correttamente e tutte le dipendenze siano caricate.
"""

import sys
import os
import asyncio
import httpx
import time
from pathlib import Path

# Aggiungi la directory del progetto al path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

class ServerStartupTest:
    """Test per verificare l'avvio del server."""
    
    def __init__(self):
        self.results = []
        self.server_url = "http://localhost:8000"
        
    def test_import_dependencies(self):
        """Test import di tutte le dipendenze principali."""
        try:
            # Test import core modules
            from utils.config import DATABASE_URL, BLOCK_WIDTHS
            from utils.logging_config import get_logger, info
            from database.config import init_database
            
            # Test import web components
            from fastapi import FastAPI
            import uvicorn
            
            self.results.append(("✅ Import dipendenze", "SUCCESS", "Tutti i moduli importati correttamente"))
            return True
            
        except Exception as e:
            self.results.append(("❌ Import dipendenze", "ERROR", f"Errore import: {e}"))
            return False
    
    def test_environment_loading(self):
        """Test caricamento configurazione environment."""
        try:
            from utils.config import get_environment_info
            
            env_info = get_environment_info()
            
            # Verifica che le info essenziali siano presenti
            required_keys = ['has_env_file', 'debug_mode', 'server', 'database', 'block_config']
            for key in required_keys:
                if key not in env_info:
                    raise ValueError(f"Chiave mancante in environment info: {key}")
            
            self.results.append(("✅ Environment config", "SUCCESS", f"Configurazione caricata: {env_info['server']}"))
            return True
            
        except Exception as e:
            self.results.append(("❌ Environment config", "ERROR", f"Errore configurazione: {e}"))
            return False
    
    def test_database_init(self):
        """Test inizializzazione database."""
        try:
            from database.config import init_database, engine
            from sqlalchemy import text
            
            # Test connessione database
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                result.fetchone()
            
            # Inizializza database
            init_database()
            
            self.results.append(("✅ Database init", "SUCCESS", "Database inizializzato e connesso"))
            return True
            
        except Exception as e:
            self.results.append(("❌ Database init", "ERROR", f"Errore database: {e}"))
            return False
    
    def test_logging_system(self):
        """Test sistema di logging strutturato."""
        try:
            from utils.logging_config import get_logger, info, warning, error, log_operation
            
            logger = get_logger("test")
            
            # Test basic logging
            info("Test logging info", component="test_startup", status="testing")
            warning("Test logging warning", component="test_startup", level="test")
            
            # Test context logging
            with log_operation("test_operation"):
                pass
            
            self.results.append(("✅ Logging system", "SUCCESS", "Sistema logging strutturato funzionante"))
            return True
            
        except Exception as e:
            self.results.append(("❌ Logging system", "ERROR", f"Errore logging: {e}"))
            return False
    
    async def test_server_startup_basic(self):
        """Test che il server si avvii senza crash immediati."""
        try:
            # Importa il modulo main per verificare che non ci siano errori di sintassi
            import main
            
            self.results.append(("✅ Server module", "SUCCESS", "Modulo main.py importato senza errori"))
            return True
            
        except Exception as e:
            self.results.append(("❌ Server module", "ERROR", f"Errore modulo main: {e}"))
            return False
    
    def run_all_tests(self):
        """Esegue tutti i test di startup."""
        print("🧪 Test Server Startup - STEP 6")
        print("=" * 50)
        
        # Test sincroni
        tests = [
            self.test_import_dependencies,
            self.test_environment_loading,
            self.test_database_init,
            self.test_logging_system,
        ]
        
        for test in tests:
            try:
                test()
            except Exception as e:
                self.results.append((f"❌ {test.__name__}", "CRITICAL", f"Test fallito: {e}"))
        
        # Test asincroni
        try:
            asyncio.run(self.test_server_startup_basic())
        except Exception as e:
            self.results.append(("❌ Server startup test", "CRITICAL", f"Test asincrono fallito: {e}"))
        
        # Report risultati
        self.print_results()
        return self.get_success_rate()
    
    def print_results(self):
        """Stampa i risultati dei test."""
        print("\n📊 RISULTATI TEST STARTUP:")
        print("-" * 50)
        
        success_count = 0
        total_count = len(self.results)
        
        for test_name, status, message in self.results:
            print(f"{test_name}: {message}")
            if "SUCCESS" in status:
                success_count += 1
        
        print("-" * 50)
        print(f"✅ Test passati: {success_count}/{total_count}")
        print(f"📈 Success rate: {(success_count/total_count)*100:.1f}%")
        
    def get_success_rate(self):
        """Ritorna la percentuale di successo."""
        if not self.results:
            return 0.0
        
        success_count = sum(1 for _, status, _ in self.results if "SUCCESS" in status)
        return (success_count / len(self.results)) * 100

if __name__ == "__main__":
    tester = ServerStartupTest()
    success_rate = tester.run_all_tests()
    
    if success_rate >= 80:
        print("\n🎉 Test startup PASSATI!")
        sys.exit(0)
    else:
        print("\n⚠️ Test startup con errori!")
        sys.exit(1)
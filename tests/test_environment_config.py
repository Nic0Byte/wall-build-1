#!/usr/bin/env python3
"""
Test Environment Configuration - STEP 6
Test della configurazione environment e caricamento variabili .env
"""

import sys
import os
import tempfile
from pathlib import Path

# Aggiungi la directory del progetto al path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

class EnvironmentConfigTest:
    """Test per la configurazione environment."""
    
    def __init__(self):
        self.results = []
        
    def test_env_file_template(self):
        """Test presenza e validità del template .env.example."""
        try:
            env_example_path = project_root / ".env.example"
            
            if not env_example_path.exists():
                self.results.append(("❌ .env.example", "ERROR", "File .env.example non trovato"))
                return False
            
            # Leggi contenuto .env.example
            with open(env_example_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Verifica che contenga le sezioni principali
            required_sections = [
                "DATABASE_URL",
                "SECRET_KEY", 
                "DEBUG",
                "CORS_ORIGINS",
                "BLOCK_WIDTHS",
                "BLOCK_HEIGHT"
            ]
            
            missing_sections = []
            for section in required_sections:
                if section not in content:
                    missing_sections.append(section)
            
            if missing_sections:
                self.results.append(("⚠️ .env.example", "WARNING", f"Sezioni mancanti: {missing_sections}"))
            else:
                self.results.append(("✅ .env.example", "SUCCESS", "Template environment completo"))
                
            return True
            
        except Exception as e:
            self.results.append(("❌ .env.example", "ERROR", f"Errore lettura template: {e}"))
            return False
    
    def test_gitignore_env(self):
        """Test che .env sia nel .gitignore."""
        try:
            gitignore_path = project_root / ".gitignore"
            
            if gitignore_path.exists():
                with open(gitignore_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                if '.env' in content:
                    self.results.append(("✅ .gitignore", "SUCCESS", ".env presente in .gitignore"))
                else:
                    self.results.append(("⚠️ .gitignore", "WARNING", ".env non trovato in .gitignore"))
            else:
                self.results.append(("ℹ️ .gitignore", "INFO", "File .gitignore non presente"))
                
            return True
            
        except Exception as e:
            self.results.append(("❌ .gitignore", "ERROR", f"Errore lettura .gitignore: {e}"))
            return False
    
    def test_default_config_values(self):
        """Test che i valori di default siano caricati correttamente."""
        try:
            from utils.config import (
                DATABASE_URL, SECRET_KEY, DEBUG, 
                BLOCK_WIDTHS, BLOCK_HEIGHT, CORS_ORIGINS
            )
            
            # Verifica che i valori non siano None o vuoti
            checks = [
                ("DATABASE_URL", DATABASE_URL, "sqlite:///data/wallbuild.db"),
                ("SECRET_KEY", SECRET_KEY, None),
                ("DEBUG", DEBUG, False),
                ("BLOCK_WIDTHS", BLOCK_WIDTHS, [3000, 1500, 413]),
                ("BLOCK_HEIGHT", BLOCK_HEIGHT, 495),
                ("CORS_ORIGINS", CORS_ORIGINS, ["http://localhost:3000"])
            ]
            
            all_good = True
            for name, value, expected in checks:
                if value is None or (isinstance(value, str) and value == ""):
                    self.results.append(("❌ Default config", "ERROR", f"{name} è None o vuoto"))
                    all_good = False
                elif expected is not None and value != expected:
                    # Solo warning, potrebbero essere customizzazioni valide
                    self.results.append(("ℹ️ Default config", "INFO", f"{name} = {value} (diverso dal default)"))
            
            if all_good:
                self.results.append(("✅ Default config", "SUCCESS", "Tutti i valori di default caricati"))
                
            return True
            
        except Exception as e:
            self.results.append(("❌ Default config", "ERROR", f"Errore caricamento config: {e}"))
            return False
    
    def test_env_file_loading(self):
        """Test caricamento di un file .env personalizzato."""
        try:
            # Crea un file .env temporaneo
            test_env_content = """
# Test environment
DEBUG=true
SECRET_KEY=test_secret_key_123456789
DATABASE_URL=sqlite:///test_database.db
BLOCK_WIDTHS=2000,1000,500
BLOCK_HEIGHT=400
CORS_ORIGINS=http://localhost:3000,http://localhost:8080
"""
            
            env_test_path = project_root / ".env.test"
            
            with open(env_test_path, 'w', encoding='utf-8') as f:
                f.write(test_env_content)
            
            # Ricarica la configurazione (questo è difficile da testare senza restart)
            # Per ora verifichiamo solo che dotenv funzioni
            try:
                from dotenv import load_dotenv
                load_dotenv(env_test_path)
                
                # Verifica che le variabili siano state caricate nell'environment
                if os.getenv('SECRET_KEY') == 'test_secret_key_123456789':
                    self.results.append(("✅ .env loading", "SUCCESS", "Caricamento file .env funzionante"))
                else:
                    self.results.append(("⚠️ .env loading", "WARNING", "File .env caricato ma variabili non riflesse"))
            
            finally:
                # Pulisci file test
                if env_test_path.exists():
                    env_test_path.unlink()
                    
            return True
            
        except ImportError:
            self.results.append(("❌ .env loading", "ERROR", "python-dotenv non disponibile"))
            return False
        except Exception as e:
            self.results.append(("❌ .env loading", "ERROR", f"Errore test .env: {e}"))
            return False
    
    def test_config_helper_functions(self):
        """Test delle funzioni helper per la configurazione."""
        try:
            from utils.config import (
                get_env_bool, get_env_int, get_env_float, 
                get_env_list_int, get_environment_info
            )
            
            # Test con variabili environment temporanee
            os.environ['TEST_BOOL'] = 'true'
            os.environ['TEST_INT'] = '42'
            os.environ['TEST_FLOAT'] = '3.14'
            os.environ['TEST_LIST'] = '100,200,300'
            
            try:
                # Test conversioni
                bool_val = get_env_bool('TEST_BOOL', False)
                int_val = get_env_int('TEST_INT', 0)
                float_val = get_env_float('TEST_FLOAT', 0.0)
                list_val = get_env_list_int('TEST_LIST', [])
                
                if (bool_val == True and int_val == 42 and 
                    abs(float_val - 3.14) < 0.001 and list_val == [100, 200, 300]):
                    self.results.append(("✅ Config helpers", "SUCCESS", "Funzioni helper funzionanti"))
                else:
                    self.results.append(("❌ Config helpers", "ERROR", "Conversioni non corrette"))
                
                # Test environment info
                env_info = get_environment_info()
                if isinstance(env_info, dict) and 'server' in env_info:
                    self.results.append(("✅ Environment info", "SUCCESS", "get_environment_info() funzionante"))
                else:
                    self.results.append(("❌ Environment info", "ERROR", "get_environment_info() non valida"))
                    
            finally:
                # Pulisci variabili test
                for var in ['TEST_BOOL', 'TEST_INT', 'TEST_FLOAT', 'TEST_LIST']:
                    os.environ.pop(var, None)
                    
            return True
            
        except Exception as e:
            self.results.append(("❌ Config helpers", "ERROR", f"Errore helper functions: {e}"))
            return False
    
    def test_database_configuration(self):
        """Test configurazione database."""
        try:
            from utils.config import DATABASE_URL, DATABASE_TIMEOUT, DATABASE_ECHO
            from database.config import engine
            from sqlalchemy import text
            
            # Verifica connessione database
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1 as test"))
                row = result.fetchone()
                
                if row and row[0] == 1:
                    self.results.append(("✅ Database config", "SUCCESS", f"Connessione DB OK: {DATABASE_URL}"))
                else:
                    self.results.append(("❌ Database config", "ERROR", "Query test fallita"))
                    
            return True
            
        except Exception as e:
            self.results.append(("❌ Database config", "ERROR", f"Errore configurazione DB: {e}"))
            return False
    
    def test_security_configuration(self):
        """Test configurazioni di sicurezza."""
        try:
            from utils.config import SECRET_KEY, CORS_ORIGINS, JWT_EXPIRE_MINUTES
            
            # Verifica SECRET_KEY
            if not SECRET_KEY or len(SECRET_KEY) < 32:
                self.results.append(("⚠️ Security config", "WARNING", "SECRET_KEY potrebbe essere troppo corta"))
            else:
                self.results.append(("✅ Security config", "SUCCESS", "SECRET_KEY configurata correttamente"))
            
            # Verifica CORS
            if isinstance(CORS_ORIGINS, list) and len(CORS_ORIGINS) > 0:
                self.results.append(("✅ CORS config", "SUCCESS", f"CORS origins: {CORS_ORIGINS}"))
            else:
                self.results.append(("⚠️ CORS config", "WARNING", "CORS origins non configurate"))
                
            return True
            
        except Exception as e:
            self.results.append(("❌ Security config", "ERROR", f"Errore configurazione sicurezza: {e}"))
            return False
    
    def run_all_tests(self):
        """Esegue tutti i test di configurazione environment."""
        print("🧪 Test Environment Configuration - STEP 6")
        print("=" * 50)
        
        tests = [
            self.test_env_file_template,
            self.test_gitignore_env,
            self.test_default_config_values,
            self.test_env_file_loading,
            self.test_config_helper_functions,
            self.test_database_configuration,
            self.test_security_configuration,
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
        print("\n📊 RISULTATI TEST ENVIRONMENT CONFIG:")
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
    tester = EnvironmentConfigTest()
    success_rate = tester.run_all_tests()
    
    if success_rate >= 75:
        print("\n🎉 Test environment configuration PASSATI!")
        sys.exit(0)
    else:
        print("\n⚠️ Test environment configuration con errori!")
        sys.exit(1)
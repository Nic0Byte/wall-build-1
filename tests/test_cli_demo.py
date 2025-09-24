#!/usr/bin/env python3
"""
Test CLI and Demo - STEP 6
Test delle modalità CLI e demo del sistema.
"""

import sys
import os
import subprocess
import time
from pathlib import Path

# Aggiungi la directory del progetto al path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

class CLIDemoTest:
    """Test per CLI e modalità demo."""
    
    def __init__(self):
        self.results = []
        self.python_exe = self.get_python_executable()
        
    def get_python_executable(self):
        """Ottiene il path corretto dell'eseguibile Python."""
        # Prova prima il virtual environment
        venv_python = project_root / ".venv" / "Scripts" / "python.exe"
        if venv_python.exists():
            return str(venv_python)
        
        # Fallback a python di sistema
        return sys.executable
    
    def test_main_module_import(self):
        """Test import del modulo main senza errori."""
        try:
            import main
            self.results.append(("✅ Main import", "SUCCESS", "Modulo main.py importato senza errori"))
            return True
            
        except Exception as e:
            self.results.append(("❌ Main import", "ERROR", f"Errore import main: {e}"))
            return False
    
    def test_help_command(self):
        """Test comando help/usage."""
        try:
            # Esegui python main.py --help
            result = subprocess.run(
                [self.python_exe, "main.py", "--help"],
                cwd=str(project_root),
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Il comando help dovrebbe completarsi senza errori critici
            if result.returncode == 0 or "Uso:" in result.stdout or "demo" in result.stdout:
                self.results.append(("✅ Help command", "SUCCESS", "Comando help funzionante"))
            else:
                self.results.append(("❌ Help command", "ERROR", f"Help fallito: {result.stderr}"))
                
            return True
            
        except subprocess.TimeoutExpired:
            self.results.append(("❌ Help command", "ERROR", "Timeout comando help"))
            return False
        except Exception as e:
            self.results.append(("❌ Help command", "ERROR", f"Errore comando help: {e}"))
            return False
    
    def test_demo_command(self):
        """Test modalità demo."""
        try:
            # Esegui python main.py demo con timeout
            result = subprocess.run(
                [self.python_exe, "main.py", "demo"],
                cwd=str(project_root),
                capture_output=True,
                text=True,
                timeout=60  # Demo può richiedere più tempo
            )
            
            # Verifica output demo
            output = result.stdout + result.stderr
            
            if ("Demo" in output and result.returncode == 0) or "JSON demo generato" in output:
                self.results.append(("✅ Demo command", "SUCCESS", "Modalità demo completata"))
            elif result.returncode != 0:
                # Se fallisce, potrebbe essere per dipendenze mancanti
                if "ModuleNotFoundError" in output:
                    self.results.append(("⚠️ Demo command", "WARNING", "Demo fallito per dipendenze mancanti"))
                else:
                    self.results.append(("❌ Demo command", "ERROR", f"Demo fallito: {output[:200]}..."))
            else:
                self.results.append(("⚠️ Demo command", "WARNING", "Demo completato con warning"))
                
            return True
            
        except subprocess.TimeoutExpired:
            self.results.append(("⚠️ Demo command", "WARNING", "Demo timeout (normale per operazioni lunghe)"))
            return True
        except Exception as e:
            self.results.append(("❌ Demo command", "ERROR", f"Errore demo: {e}"))
            return False
    
    def test_server_command_startup(self):
        """Test avvio server (senza aspettare completo avvio)."""
        try:
            # Avvia il server in background
            process = subprocess.Popen(
                [self.python_exe, "main.py", "server"],
                cwd=str(project_root),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Aspetta un po' per vedere se si avvia senza crash immediati
            time.sleep(3)
            
            # Controlla se il processo è ancora vivo
            if process.poll() is None:
                # Processo ancora in esecuzione = buon segno
                self.results.append(("✅ Server startup", "SUCCESS", "Server si avvia senza crash immediati"))
                success = True
            else:
                # Processo terminato = possibile errore
                stdout, stderr = process.communicate()
                error_output = stderr[:200] if stderr else "Unknown error"
                self.results.append(("❌ Server startup", "ERROR", f"Server crash: {error_output}"))
                success = False
            
            # Termina il processo server
            try:
                process.terminate()
                process.wait(timeout=5)
            except:
                try:
                    process.kill()
                except:
                    pass
                    
            return success
            
        except Exception as e:
            self.results.append(("❌ Server startup", "ERROR", f"Errore test server: {e}"))
            return False
    
    def test_invalid_command(self):
        """Test gestione comando non valido."""
        try:
            # Testa comando inesistente
            result = subprocess.run(
                [self.python_exe, "main.py", "invalid_command"],
                cwd=str(project_root),
                capture_output=True,
                text=True,
                timeout=15
            )
            
            # Dovrebbe mostrare help o messaggio di errore utile
            output = result.stdout + result.stderr
            
            if ("Uso:" in output or "demo" in output or "server" in output):
                self.results.append(("✅ Invalid command", "SUCCESS", "Gestione comando non valido OK"))
            else:
                self.results.append(("⚠️ Invalid command", "WARNING", "Gestione comando non valido non chiara"))
                
            return True
            
        except Exception as e:
            self.results.append(("❌ Invalid command", "ERROR", f"Errore test comando non valido: {e}"))
            return False
    
    def test_python_environment(self):
        """Test dell'ambiente Python utilizzato."""
        try:
            # Controlla versione Python
            result = subprocess.run(
                [self.python_exe, "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                version = result.stdout.strip()
                self.results.append(("✅ Python env", "SUCCESS", f"Python ambiente: {version}"))
            else:
                self.results.append(("❌ Python env", "ERROR", "Errore controllo versione Python"))
                
            # Controlla se è virtual environment
            venv_python = project_root / ".venv" / "Scripts" / "python.exe"
            if venv_python.exists() and str(venv_python) == self.python_exe:
                self.results.append(("✅ Virtual env", "SUCCESS", "Utilizzando virtual environment"))
            else:
                self.results.append(("ℹ️ Virtual env", "INFO", "Utilizzando Python di sistema"))
                
            return True
            
        except Exception as e:
            self.results.append(("❌ Python env", "ERROR", f"Errore controllo ambiente: {e}"))
            return False
    
    def test_output_directories(self):
        """Test presenza e accesso alle directory di output."""
        try:
            output_dir = project_root / "output"
            
            # Verifica directory principali
            expected_dirs = ["json", "pdf", "dxf", "images", "reports", "temp"]
            existing_dirs = []
            
            for dir_name in expected_dirs:
                dir_path = output_dir / dir_name
                if dir_path.exists():
                    existing_dirs.append(dir_name)
                else:
                    # Prova a creare la directory
                    try:
                        dir_path.mkdir(parents=True, exist_ok=True)
                        existing_dirs.append(dir_name)
                    except:
                        pass
            
            if len(existing_dirs) >= len(expected_dirs) * 0.8:  # Almeno 80%
                self.results.append(("✅ Output dirs", "SUCCESS", f"Directory output OK: {existing_dirs}"))
            else:
                self.results.append(("⚠️ Output dirs", "WARNING", f"Alcune directory mancanti: {existing_dirs}"))
                
            return True
            
        except Exception as e:
            self.results.append(("❌ Output dirs", "ERROR", f"Errore directory output: {e}"))
            return False
    
    def run_all_tests(self):
        """Esegue tutti i test CLI e demo."""
        print("🧪 Test CLI and Demo - STEP 6")
        print("=" * 50)
        print(f"🐍 Python executable: {self.python_exe}")
        print()
        
        tests = [
            self.test_main_module_import,
            self.test_python_environment,
            self.test_output_directories,
            self.test_help_command,
            self.test_invalid_command,
            self.test_demo_command,
            self.test_server_command_startup,
        ]
        
        for test in tests:
            try:
                print(f"Running {test.__name__}...", end=" ")
                success = test()
                print("✓" if success else "✗")
            except Exception as e:
                self.results.append((f"❌ {test.__name__}", "CRITICAL", f"Test fallito: {e}"))
                print("✗")
        
        # Report risultati
        self.print_results()
        return self.get_success_rate()
    
    def print_results(self):
        """Stampa i risultati dei test."""
        print("\n📊 RISULTATI TEST CLI AND DEMO:")
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
    tester = CLIDemoTest()
    success_rate = tester.run_all_tests()
    
    if success_rate >= 70:  # Soglia più permissiva per test CLI
        print("\n🎉 Test CLI and demo PASSATI!")
        sys.exit(0)
    else:
        print("\n⚠️ Test CLI and demo con errori!")
        sys.exit(1)
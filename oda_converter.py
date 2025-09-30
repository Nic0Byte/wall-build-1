#!/usr/bin/env python3
"""
Modulo per gestire conversione DWG → DXF usando ODA File Converter
Cross-platform: Windows, Linux, macOS - ODA SEMPRE OBBLIGATORIO
"""

import os
import subprocess
import tempfile
import shutil
import platform
from pathlib import Path

# Path arrays per ogni sistema operativo
WINDOWS_ODA_PATHS = [
    r"C:\Program Files\ODA\ODAFileConverter 26.8.0\ODAFileConverter.exe",  # Versione più recente
    r"C:\Program Files\ODA\ODAFileConverter_QT5_vc14_dll_24.12\ODAFileConverter.exe",
    r"C:\Program Files (x86)\ODA\ODAFileConverter_QT5_vc14_dll_24.12\ODAFileConverter.exe",
    r"C:\Program Files\ODA\ODAFileConverter.exe",  # Generico
    r"C:\ODA\ODAFileConverter.exe",  # Installazione custom
    "ODAFileConverter.exe"  # Nel PATH di sistema
]

LINUX_ODA_PATHS = [
    # Standard Linux installations  
    "/opt/ODA/ODAFileConverter",                    # Percorso comune
    "/usr/bin/ODAFileConverter",                    # System PATH
    "/usr/local/bin/ODAFileConverter",              # Local install
    "/opt/oda/bin/ODAFileConverter",                # Alternative location
    
    # AppImage portable versions
    "./ODAFileConverter.AppImage",                  # Directory corrente
    "~/Applications/ODAFileConverter.AppImage",     # User applications
    "/opt/appimages/ODAFileConverter.AppImage",     # System AppImages
    
    # Versioned installations (come da documentazione)
    "/opt/ODA/ODAFileConverter_QT6_lnxX64_8.3dll/ODAFileConverter",
    "/usr/share/ODA/ODAFileConverter",
    
    # PATH lookup
    "ODAFileConverter"  # Nel PATH di sistema
]

MACOS_ODA_PATHS = [
    # Standard macOS app locations
    "/Applications/ODA File Converter.app/Contents/MacOS/ODAFileConverter",
    "/Applications/ODAFileConverter.app/Contents/MacOS/ODAFileConverter", 
    
    # Homebrew locations
    "/usr/local/bin/ODAFileConverter",              # Intel Homebrew
    "/opt/homebrew/bin/ODAFileConverter",           # Apple Silicon Homebrew
    
    # User-specific installations
    "~/Applications/ODAFileConverter.app/Contents/MacOS/ODAFileConverter",
    "/usr/local/opt/oda/bin/ODAFileConverter",
    
    # PATH lookup
    "ODAFileConverter"  # Nel PATH di sistema
]

def find_oda_converter():
    """
    Trova ODA File Converter nel sistema in base all'OS.
    Cross-platform: Windows, Linux, macOS
    
    Returns:
        str: Percorso completo all'eseguibile ODA
        None: Se ODA non è trovato
    """
    system = platform.system().lower()
    
    # Seleziona array percorsi in base all'OS
    if system == "windows":
        search_paths = WINDOWS_ODA_PATHS
    elif system == "linux":
        search_paths = LINUX_ODA_PATHS  
    elif system == "darwin":  # macOS
        search_paths = MACOS_ODA_PATHS
    else:
        raise ValueError(f"Sistema operativo non supportato: {system}")
    
    print(f"🔍 Ricerca ODA File Converter su {system.upper()}...")
    
    # Cerca primo percorso esistente e eseguibile
    for path in search_paths:
        # Espandi percorsi utente come ~/Applications
        expanded_path = os.path.expanduser(path)
        
        # Controlla se file esiste ed è eseguibile
        if os.path.exists(expanded_path) and os.access(expanded_path, os.X_OK):
            print(f"✅ ODA trovato: {expanded_path}")
            return expanded_path
            
        # Controlla se è nel PATH (per nomi generici)
        if path in ["ODAFileConverter", "ODAFileConverter.exe"]:
            which_result = shutil.which(path)
            if which_result:
                print(f"✅ ODA trovato nel PATH: {which_result}")
                return which_result
    
    print(f"❌ ODA File Converter NON trovato su {system}")
    return None

def convert_dwg_to_dxf(dwg_bytes: bytes) -> bytes:
    """
    Converte file DWG in DXF usando ODA File Converter.
    METODO A: ODA OBBLIGATORIO - Fail Hard se non disponibile
    
    Args:
        dwg_bytes: Contenuto del file DWG
        
    Returns:
        bytes: Contenuto del file DXF convertito
        
    Raises:
        ValueError: Se ODA non è disponibile o conversione fallisce
        RuntimeError: Se conversione ODA fallisce
    """
    # STEP 1: Trova ODA - OBBLIGATORIO
    oda_path = find_oda_converter()
    if not oda_path:
        system = platform.system()
        raise ValueError(
            f"❌ ODA File Converter OBBLIGATORIO ma non trovato su {system}!\n"
            f"📥 Installa da: https://www.opendesign.com/guestfiles/oda_file_converter\n"
            f"🔧 Supporto: Windows (exe), Linux (RPM/DEB/AppImage), macOS (app)"
        )
    
    print(f"🔄 Conversione DWG→DXF con ODA: {os.path.basename(oda_path)}")
    
    # STEP 2: Esegui conversione ODA
    with tempfile.TemporaryDirectory() as temp_dir:
        input_dir = Path(temp_dir) / "input"
        output_dir = Path(temp_dir) / "output"
        input_dir.mkdir()
        output_dir.mkdir()
        
        # Salva file DWG temporaneo
        dwg_file = input_dir / "input.dwg"
        with open(dwg_file, 'wb') as f:
            f.write(dwg_bytes)
        
        # Comando ODA per conversione
        cmd = [
            oda_path,
            str(input_dir),      # Input directory
            str(output_dir),     # Output directory  
            "ACAD2018",          # Target version
            "DXF",               # Output format
            "0",                 # Recurse subdirectories (0=no)
            "1",                 # Audit each file (1=yes)
            "*.dwg"              # File filter
        ]
        
        try:
            print(f"🚀 Comando ODA: {' '.join(cmd[:3])} ...")
            
            # Esegui conversione con timeout
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=60,  # Timeout aumentato per file grandi
                cwd=temp_dir
            )
            
            if result.returncode != 0:
                raise RuntimeError(
                    f"ODA conversione fallita (exit code: {result.returncode})\n"
                    f"STDERR: {result.stderr}\n"
                    f"STDOUT: {result.stdout}"
                )
            
            # Leggi file DXF convertito
            dxf_file = output_dir / "input.dxf"
            if not dxf_file.exists():
                # Cerca altri possibili nomi file DXF
                dxf_files = list(output_dir.glob("*.dxf"))
                if dxf_files:
                    dxf_file = dxf_files[0]
                else:
                    raise RuntimeError("Nessun file DXF generato da ODA conversion")
            
            with open(dxf_file, 'rb') as f:
                dxf_bytes = f.read()
                
            print(f"✅ Conversione completata: {len(dxf_bytes)} bytes DXF")
            return dxf_bytes
                
        except subprocess.TimeoutExpired:
            raise RuntimeError("Timeout conversione ODA (>60s) - file troppo grande o ODA bloccato")
        except Exception as e:
            raise RuntimeError(f"Errore esecuzione ODA: {e}")

def is_oda_available() -> bool:
    """
    Controlla se ODA File Converter è disponibile.
    
    Returns:
        bool: True se ODA è disponibile, False altrimenti
    """
    return find_oda_converter() is not None

# Test e diagnostica
if __name__ == "__main__":
    print("🔧 Test ODA File Converter Cross-Platform...")
    print(f"💻 Sistema operativo: {platform.system()} {platform.release()}")
    print(f"🏗️ Architettura: {platform.machine()}")
    print()
    
    # Test disponibilità ODA
    if is_oda_available():
        oda_path = find_oda_converter()
        print(f"✅ ODA File Converter TROVATO!")
        print(f"📍 Percorso: {oda_path}")
        print(f"📄 Tipo file: {type(oda_path)}")
        
        # Test eseguibilità
        try:
            result = subprocess.run([oda_path], capture_output=True, timeout=5)
            print(f"🚀 Test esecuzione: OK (exit code: {result.returncode})")
        except subprocess.TimeoutExpired:
            print("🚀 Test esecuzione: OK (timeout atteso)")
        except Exception as e:
            print(f"⚠️ Test esecuzione: Errore - {e}")
        
        # Test con file esistente (se disponibile)
        test_files = ["ROTTINI_LAY_REV0.dwg", "test.dwg", "sample.dwg"]
        test_file = None
        
        for filename in test_files:
            if os.path.exists(filename):
                test_file = filename
                break
        
        if test_file:
            try:
                print(f"🧪 Test conversione con {test_file}...")
                with open(test_file, 'rb') as f:
                    dwg_bytes = f.read()
                
                dxf_bytes = convert_dwg_to_dxf(dwg_bytes)
                
                # Salva risultato per verifica
                output_file = f"{test_file}_converted.dxf"
                with open(output_file, 'wb') as f:
                    f.write(dxf_bytes)
                
                print(f"✅ Test conversione RIUSCITO!")
                print(f"📊 Input: {len(dwg_bytes)} bytes DWG")
                print(f"📊 Output: {len(dxf_bytes)} bytes DXF")
                print(f"💾 Salvato: {output_file}")
                
            except Exception as e:
                print(f"❌ Test conversione FALLITO: {e}")
        else:
            print("⚠️ Nessun file DWG trovato per test conversione")
            print(f"💡 Crea uno di questi file per test: {', '.join(test_files)}")
    
    else:
        system = platform.system().lower()
        print(f"❌ ODA File Converter NON TROVATO su {system.upper()}")
        print()
        print("📥 INSTALLAZIONE RICHIESTA:")
        print("🌐 Scarica da: https://www.opendesign.com/guestfiles/oda_file_converter")
        print()
        
        if system == "windows":
            print("🪟 Windows:")
            print("   - Scarica ODAFileConverter_*.exe")
            print("   - Installa in C:\\Program Files\\ODA\\")
            print("   - Oppure aggiungi al PATH di sistema")
        
        elif system == "linux":
            print("🐧 Linux:")
            print("   - RPM: sudo yum localinstall ODAFileConverter_*.rpm")
            print("   - DEB: sudo gdebi ODAFileConverter_*.deb") 
            print("   - AppImage: ./ODAFileConverter_*.AppImage")
            print("   - Richiede: libxcb-util.so.0 (symlink se necessario)")
            
        elif system == "darwin":
            print("🍎 macOS:")
            print("   - Scarica versione macOS (se disponibile)")
            print("   - Copia in /Applications/")
            print("   - Oppure installa via Homebrew (se supportato)")
        
        print()
        print("🔄 Rilancia questo script dopo l'installazione per verificare")

    print()
    print("🎯 STRATEGIA IMPLEMENTATA: Metodo A - ODA Obbligatorio")
    print("   ✅ Cross-platform: Windows, Linux, macOS")
    print("   ✅ Auto-detection percorsi OS-specific")  
    print("   ✅ Fail hard se ODA non disponibile")
    print("   ✅ Nessun fallback automatico")
    print("   📋 Percorsi ricerca configurabili via array")

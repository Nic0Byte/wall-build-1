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
    """
    system = platform.system().lower()

    if system == "windows":
        search_paths = WINDOWS_ODA_PATHS
    elif system == "linux":
        search_paths = LINUX_ODA_PATHS
    elif system == "darwin":
        search_paths = MACOS_ODA_PATHS
    else:
        raise ValueError(f"Sistema operativo non supportato: {system}")

    print(f"🔍 Ricerca ODA File Converter su {system.upper()}...")

    for path in search_paths:
        expanded_path = os.path.expanduser(path)
        if os.path.exists(expanded_path) and os.access(expanded_path, os.X_OK):
            print(f"✅ ODA trovato: {expanded_path}")
            return expanded_path

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
    Usa xvfb-run su Linux headless.
    """
    oda_path = find_oda_converter()
    if not oda_path:
        system = platform.system()
        raise ValueError(
            f"❌ ODA File Converter OBBLIGATORIO ma non trovato su {system}!\n"
            f"📥 Installa da: https://www.opendesign.com/guestfiles/oda_file_converter\n"
        )

    print(f"🔄 Conversione DWG→DXF con ODA: {os.path.basename(oda_path)}")

    with tempfile.TemporaryDirectory() as temp_dir:
        input_dir = Path(temp_dir) / "input"
        output_dir = Path(temp_dir) / "output"
        input_dir.mkdir()
        output_dir.mkdir()

        dwg_file = input_dir / "input.dwg"
        with open(dwg_file, "wb") as f:
            f.write(dwg_bytes)

        # 👇 differenza qui: su Linux usiamo xvfb-run
        if platform.system().lower() == "linux":
            cmd = [
                "xvfb-run", "-a", oda_path,
                str(input_dir),
                str(output_dir),
                "ACAD2018",
                "DXF",
                "0",
                "1",
                "*.dwg"
            ]
        else:
            cmd = [
                oda_path,
                str(input_dir),
                str(output_dir),
                "ACAD2018",
                "DXF",
                "0",
                "1",
                "*.dwg"
            ]

        try:
            print(f"🚀 Comando ODA: {' '.join(cmd[:3])} ...")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
                cwd=temp_dir
            )

            if result.returncode != 0:
                raise RuntimeError(
                    f"ODA conversione fallita (exit code: {result.returncode})\n"
                    f"STDERR: {result.stderr}\n"
                    f"STDOUT: {result.stdout}"
                )

            dxf_file = output_dir / "input.dxf"
            if not dxf_file.exists():
                dxf_files = list(output_dir.glob("*.dxf"))
                if dxf_files:
                    dxf_file = dxf_files[0]
                else:
                    raise RuntimeError("Nessun file DXF generato da ODA conversion")

            with open(dxf_file, "rb") as f:
                dxf_bytes = f.read()

            print(f"✅ Conversione completata: {len(dxf_bytes)} bytes DXF")
            return dxf_bytes

        except subprocess.TimeoutExpired:
            raise RuntimeError("Timeout conversione ODA (>60s)")
        except Exception as e:
            raise RuntimeError(f"Errore esecuzione ODA: {e}")


def is_oda_available() -> bool:
    return find_oda_converter() is not None


if __name__ == "__main__":
    print("🔧 Test ODA File Converter Cross-Platform...")
    print(f"💻 Sistema operativo: {platform.system()} {platform.release()}")
    print(f"🏗️ Architettura: {platform.machine()}")
    print()

    if is_oda_available():
        oda_path = find_oda_converter()
        print("✅ ODA File Converter TROVATO!")
        print(f"📍 Percorso: {oda_path}")
        try:
            result = subprocess.run([oda_path], capture_output=True, timeout=5)
            print(f"🚀 Test esecuzione: OK (exit code: {result.returncode})")
        except subprocess.TimeoutExpired:
            print("🚀 Test esecuzione: OK (timeout atteso)")
        except Exception as e:
            print(f"⚠️ Test esecuzione: Errore - {e}")
    else:
        print("❌ ODA File Converter NON TROVATO")

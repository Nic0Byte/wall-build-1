"""
Test: Verifica implementazione Opzione 1 (Session Restore)
"""

import sqlite3
from pathlib import Path

def test_schema():
    """Verifica nuovi campi nel database"""
    print("🧪 Test 1: Verifica schema database")
    
    db_path = Path("data/wallbuild.db")
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    cursor.execute("PRAGMA table_info(saved_projects)")
    columns = {column[1]: column[2] for column in cursor.fetchall()}
    
    required_fields = [
        'preview_image',
        'blocks_standard_json',
        'wall_geometry_json',
        'apertures_geometry_json'
    ]
    
    all_ok = True
    for field in required_fields:
        if field in columns:
            print(f"  ✅ {field} (TEXT)")
        else:
            print(f"  ❌ {field} MANCANTE")
            all_ok = False
    
    conn.close()
    return all_ok

def main():
    print("=" * 70)
    print("🧪 TEST: Opzione 1 - Session Restore Implementation")
    print("=" * 70)
    print()
    
    if not test_schema():
        print("\n❌ Test schema fallito!")
        return False
    
    print("\n" + "=" * 70)
    print("✅ SCHEMA DATABASE OK!")
    print("=" * 70)
    print()
    print("📝 Prossimi passi per testare:")
    print("   1. Avvia server: python main.py")
    print("   2. Login ed elabora un nuovo file")
    print("   3. Completa Step 5 (auto-save con geometrie)")
    print("   4. Click 'Riusa':")
    print("      - Preview istantanea ✅")
    print("      - Sessione ripristinata ✅")
    print("      - Download PDF/JSON/DXF disponibili ✅")
    print()
    
    return True

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)

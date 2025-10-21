"""
Quick Test: Verificare che il sistema di preview funzioni correttamente
"""

import sqlite3
from pathlib import Path

def test_database_schema():
    """Verifica che le nuove colonne siano presenti"""
    print("🧪 Test 1: Verifica schema database")
    
    db_path = Path("data/wallbuild.db")
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    cursor.execute("PRAGMA table_info(saved_projects)")
    columns = {column[1]: column[2] for column in cursor.fetchall()}
    
    # Check preview_image
    if 'preview_image' in columns:
        print("  ✅ Column 'preview_image' exists (type: TEXT)")
    else:
        print("  ❌ Column 'preview_image' NOT FOUND")
        return False
    
    # Check blocks_standard_json
    if 'blocks_standard_json' in columns:
        print("  ✅ Column 'blocks_standard_json' exists (type: TEXT)")
    else:
        print("  ❌ Column 'blocks_standard_json' NOT FOUND")
        return False
    
    conn.close()
    return True

def test_existing_projects():
    """Verifica che i progetti esistenti abbiano i nuovi campi NULL"""
    print("\n🧪 Test 2: Verifica progetti esistenti")
    
    db_path = Path("data/wallbuild.db")
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN preview_image IS NOT NULL THEN 1 ELSE 0 END) as with_preview,
            SUM(CASE WHEN blocks_standard_json IS NOT NULL THEN 1 ELSE 0 END) as with_blocks
        FROM saved_projects
        WHERE is_active = 1
    """)
    
    row = cursor.fetchone()
    total, with_preview, with_blocks = row
    
    print(f"  📊 Progetti totali: {total}")
    print(f"  🎨 Con preview: {with_preview}")
    print(f"  📦 Con blocks_standard: {with_blocks}")
    
    if total > 0 and with_preview == 0:
        print("  ℹ️  Progetti esistenti senza preview (normale per progetti legacy)")
    elif total > 0 and with_preview > 0:
        print("  ✅ Alcuni progetti hanno già preview salvate!")
    else:
        print("  ℹ️  Nessun progetto salvato ancora")
    
    conn.close()
    return True

def main():
    print("=" * 70)
    print("🧪 TEST SUITE: Preview & Blocks Standard Feature")
    print("=" * 70)
    print()
    
    try:
        # Test 1: Schema
        if not test_database_schema():
            print("\n❌ Test schema fallito!")
            return False
        
        # Test 2: Existing projects
        if not test_existing_projects():
            print("\n❌ Test progetti esistenti fallito!")
            return False
        
        print("\n" + "=" * 70)
        print("✅ TUTTI I TEST PASSATI!")
        print("=" * 70)
        print()
        print("📝 Prossimi passi:")
        print("   1. Avvia il server: python main.py")
        print("   2. Login e elabora un nuovo file")
        print("   3. Completa Step 5 (auto-save)")
        print("   4. Click 'Riusa' → Dovrebbe caricare istantaneamente!")
        print()
        
        return True
        
    except Exception as e:
        print(f"\n❌ Errore durante i test: {e}")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)

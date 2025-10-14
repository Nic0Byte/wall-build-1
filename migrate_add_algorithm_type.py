"""
Migrazione Database: Aggiunta campo algorithm_type ai SystemProfile

Data: 14 Ottobre 2025
Scopo: Permettere selezione algoritmo di packing (BIG/SMALL) per ogni profilo sistema

Cambiamenti:
- Aggiungi colonna 'algorithm_type' VARCHAR(20) NOT NULL DEFAULT 'small'
- Imposta tutti i profili esistenti su 'small' (residenziale)
"""

import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'wallbuild.db')

def migrate():
    """Esegue la migrazione del database."""
    
    print("🔧 Migrazione Database: Aggiunta algorithm_type a SystemProfile")
    print("=" * 70)
    
    if not os.path.exists(DB_PATH):
        print(f"❌ Database non trovato: {DB_PATH}")
        return False
    
    # Backup
    backup_path = f"{DB_PATH}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    print(f"📦 Creazione backup: {backup_path}")
    
    try:
        import shutil
        shutil.copy2(DB_PATH, backup_path)
        print("✅ Backup creato con successo")
    except Exception as e:
        print(f"⚠️ Errore creazione backup: {e}")
        print("⚠️ Continuare senza backup? (y/n)")
        if input().lower() != 'y':
            return False
    
    # Connessione database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # 1. Verifica se la colonna esiste già
        cursor.execute("PRAGMA table_info(system_profiles)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'algorithm_type' in columns:
            print("⚠️ Colonna 'algorithm_type' già esistente")
            print("✅ Migrazione non necessaria")
            return True
        
        # 2. Aggiungi colonna algorithm_type
        print("\n📝 Aggiunta colonna 'algorithm_type'...")
        cursor.execute("""
            ALTER TABLE system_profiles 
            ADD COLUMN algorithm_type VARCHAR(20) NOT NULL DEFAULT 'small'
        """)
        print("✅ Colonna aggiunta con successo")
        
        # 3. Aggiorna tutti i profili esistenti su 'small'
        cursor.execute("SELECT COUNT(*) FROM system_profiles")
        count = cursor.fetchone()[0]
        
        if count > 0:
            print(f"\n🔄 Aggiornamento {count} profili esistenti a 'small' (default)...")
            cursor.execute("""
                UPDATE system_profiles 
                SET algorithm_type = 'small'
                WHERE algorithm_type IS NULL OR algorithm_type = ''
            """)
            print(f"✅ {cursor.rowcount} profili aggiornati")
        else:
            print("\n📭 Nessun profilo esistente da aggiornare")
        
        # 4. Commit
        conn.commit()
        print("\n✅ Migrazione completata con successo!")
        
        # 5. Verifica
        print("\n🔍 Verifica migrazione...")
        cursor.execute("PRAGMA table_info(system_profiles)")
        columns = cursor.fetchall()
        
        algo_col = [col for col in columns if col[1] == 'algorithm_type']
        if algo_col:
            print(f"✅ Colonna 'algorithm_type' presente:")
            col = algo_col[0]
            print(f"   - Tipo: {col[2]}")
            print(f"   - Default: {col[4]}")
            print(f"   - NOT NULL: {'Sì' if col[3] else 'No'}")
        
        cursor.execute("SELECT id, name, algorithm_type FROM system_profiles")
        profiles = cursor.fetchall()
        
        if profiles:
            print(f"\n📊 Profili nel database ({len(profiles)}):")
            for prof in profiles:
                print(f"   - [{prof[0]}] {prof[1]}: {prof[2]}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Errore durante la migrazione: {e}")
        conn.rollback()
        return False
        
    finally:
        conn.close()
        print("\n" + "=" * 70)

if __name__ == "__main__":
    success = migrate()
    
    if success:
        print("\n🎉 Migrazione completata!")
        print("\n📋 Prossimi passi:")
        print("   1. ✅ Database aggiornato")
        print("   2. 🔄 Riavvia l'applicazione")
        print("   3. 🧪 Testa creazione/modifica profili con selezione algoritmo")
        exit(0)
    else:
        print("\n❌ Migrazione fallita!")
        print("   Controlla i log sopra per dettagli")
        exit(1)

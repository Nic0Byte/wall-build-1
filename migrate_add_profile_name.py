"""
Migration script to add profile_name column to saved_projects table
"""

import sqlite3
import os

def migrate():
    """Add profile_name column to saved_projects table"""
    db_path = os.path.join(os.path.dirname(__file__), 'data', 'wallbuild.db')
    
    if not os.path.exists(db_path):
        print(f"❌ Database non trovato: {db_path}")
        return False
    
    print(f"🔄 Connessione al database: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if column already exists
        cursor.execute("PRAGMA table_info(saved_projects)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'profile_name' in columns:
            print("✅ Colonna 'profile_name' già esistente")
            return True
        
        # Add profile_name column
        print("📝 Aggiunta colonna 'profile_name' a 'saved_projects'...")
        cursor.execute("""
            ALTER TABLE saved_projects 
            ADD COLUMN profile_name VARCHAR(100) DEFAULT 'Sistema Standard'
        """)
        
        conn.commit()
        print("✅ Migrazione completata con successo!")
        print("   - Aggiunta colonna: profile_name (VARCHAR(100))")
        print("   - Valore default: 'Sistema Standard'")
        
        return True
        
    except sqlite3.Error as e:
        print(f"❌ Errore durante la migrazione: {e}")
        conn.rollback()
        return False
        
    finally:
        conn.close()
        print("🔌 Connessione database chiusa")

if __name__ == '__main__':
    print("=" * 60)
    print("MIGRAZIONE: Aggiunta campo profile_name")
    print("=" * 60)
    success = migrate()
    print("=" * 60)
    if success:
        print("✅ MIGRAZIONE COMPLETATA")
    else:
        print("❌ MIGRAZIONE FALLITA")
    print("=" * 60)

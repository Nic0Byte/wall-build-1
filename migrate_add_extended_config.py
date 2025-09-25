#!/usr/bin/env python3
"""
Migration script to add extended_config column to saved_projects table
"""

import sqlite3
import os
from pathlib import Path

def migrate_database():
    """Add extended_config column to saved_projects table"""
    
    # Path del database
    db_path = Path("data/wallbuild.db")
    
    if not db_path.exists():
        print(f"❌ Database non trovato: {db_path}")
        return False
    
    try:
        # Connessione al database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Verifica se la colonna esiste già
        cursor.execute("PRAGMA table_info(saved_projects)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'extended_config' in columns:
            print("✅ Colonna 'extended_config' già presente")
            return True
        
        # Aggiungi la colonna
        print("🔨 Aggiungendo colonna 'extended_config'...")
        cursor.execute("""
            ALTER TABLE saved_projects 
            ADD COLUMN extended_config TEXT
        """)
        
        # Commit delle modifiche
        conn.commit()
        print("✅ Colonna 'extended_config' aggiunta con successo!")
        
        # Verifica che la colonna sia stata aggiunta
        cursor.execute("PRAGMA table_info(saved_projects)")
        columns_after = [row[1] for row in cursor.fetchall()]
        
        if 'extended_config' in columns_after:
            print("✅ Migrazione completata correttamente")
            return True
        else:
            print("❌ Errore: colonna non aggiunta")
            return False
            
    except sqlite3.Error as e:
        print(f"❌ Errore SQLite: {e}")
        return False
    except Exception as e:
        print(f"❌ Errore generico: {e}")
        return False
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print("🚀 Avvio migrazione database...")
    success = migrate_database()
    
    if success:
        print("✅ Migrazione completata con successo!")
        print("🔄 Riavvia il server per utilizzare la nuova colonna")
    else:
        print("❌ Migrazione fallita")
        exit(1)
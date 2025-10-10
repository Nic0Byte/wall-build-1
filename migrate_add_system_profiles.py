"""
Migration: Aggiunge tabella system_profiles
Data: 2025-10-10
Descrizione: Crea la tabella per gestire i profili sistema (preset configurazioni blocchi e moraletti)
"""

import os
import sys
from pathlib import Path

# Aggiungi la root del progetto al path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import create_engine, text
from utils.config import DATABASE_URL
from database.models import Base, SystemProfile
from structlog import get_logger

log = get_logger()

def migrate_up():
    """Crea la tabella system_profiles."""
    engine = create_engine(DATABASE_URL)
    
    try:
        # Crea solo la tabella SystemProfile
        SystemProfile.__table__.create(engine, checkfirst=True)
        log.info("✅ Tabella 'system_profiles' creata con successo")
        
        # Verifica la creazione
        with engine.connect() as conn:
            result = conn.execute(text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='system_profiles'"
            ))
            if result.fetchone():
                log.info("✅ Verifica OK: Tabella 'system_profiles' esiste nel database")
            else:
                log.error("❌ ERRORE: Tabella non trovata dopo la creazione")
                return False
        
        return True
        
    except Exception as e:
        log.error("❌ Errore durante la migrazione", error=str(e))
        return False
    finally:
        engine.dispose()

def migrate_down():
    """Rimuove la tabella system_profiles (rollback)."""
    engine = create_engine(DATABASE_URL)
    
    try:
        with engine.connect() as conn:
            conn.execute(text("DROP TABLE IF EXISTS system_profiles"))
            conn.commit()
        
        log.info("✅ Tabella 'system_profiles' rimossa con successo (rollback)")
        return True
        
    except Exception as e:
        log.error("❌ Errore durante il rollback", error=str(e))
        return False
    finally:
        engine.dispose()

def check_table_exists():
    """Verifica se la tabella esiste già."""
    engine = create_engine(DATABASE_URL)
    
    try:
        with engine.connect() as conn:
            result = conn.execute(text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='system_profiles'"
            ))
            exists = result.fetchone() is not None
            return exists
    finally:
        engine.dispose()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Migration: Aggiunge tabella system_profiles")
    parser.add_argument(
        '--action',
        choices=['up', 'down', 'check'],
        default='up',
        help='Azione da eseguire (up=crea, down=rimuovi, check=verifica)'
    )
    
    args = parser.parse_args()
    
    print("\n" + "="*60)
    print("🔄 Migration: System Profiles Table")
    print("="*60 + "\n")
    
    if args.action == 'check':
        exists = check_table_exists()
        if exists:
            print("✅ La tabella 'system_profiles' esiste già")
        else:
            print("❌ La tabella 'system_profiles' NON esiste")
        sys.exit(0 if exists else 1)
    
    elif args.action == 'down':
        print("⚠️  ATTENZIONE: Stai per rimuovere la tabella 'system_profiles'")
        response = input("Sei sicuro? Digita 'yes' per confermare: ")
        if response.lower() == 'yes':
            success = migrate_down()
            sys.exit(0 if success else 1)
        else:
            print("❌ Operazione annullata")
            sys.exit(1)
    
    else:  # up
        # Controlla se esiste già
        if check_table_exists():
            print("ℹ️  La tabella 'system_profiles' esiste già. Nessuna azione necessaria.")
            sys.exit(0)
        
        print("📝 Creazione tabella 'system_profiles'...")
        success = migrate_up()
        
        if success:
            print("\n✅ Migration completata con successo!\n")
            sys.exit(0)
        else:
            print("\n❌ Migration fallita. Controlla i log per dettagli.\n")
            sys.exit(1)

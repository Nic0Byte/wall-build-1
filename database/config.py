"""
Database Configuration per Wall-Build
Setup SQLAlchemy, connessioni, sessioni
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session as DBSession
from sqlalchemy.pool import StaticPool
from contextlib import contextmanager
from typing import Generator

from .models import Base, User, Session, Project, SavedProject

# ────────────────────────────────────────────────────────────────────────────────
# Configurazione Database
# ────────────────────────────────────────────────────────────────────────────────

# Percorso database SQLite
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATABASE_DIR = os.path.join(BASE_DIR, "data")
DATABASE_FILE = os.path.join(DATABASE_DIR, "wallbuild.db")
DATABASE_URL = f"sqlite:///{DATABASE_FILE}"

# Assicura che la directory esista
os.makedirs(DATABASE_DIR, exist_ok=True)

# Configurazione engine SQLAlchemy
engine = create_engine(
    DATABASE_URL,
    poolclass=StaticPool,
    connect_args={
        "check_same_thread": False,  # Necessario per SQLite con FastAPI
        "timeout": 20
    },
    echo=False  # Cambia a True per debug SQL
)

# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# ────────────────────────────────────────────────────────────────────────────────
# Gestione Database
# ────────────────────────────────────────────────────────────────────────────────

def create_tables():
    """Crea tutte le tabelle del database."""
    print("🗄️ Creazione tabelle database...")
    Base.metadata.create_all(bind=engine)
    print("✅ Tabelle create con successo")

def get_db() -> Generator[DBSession, None, None]:
    """
    Dependency per ottenere una sessione database.
    Usato con FastAPI Depends().
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@contextmanager
def get_db_session() -> Generator[DBSession, None, None]:
    """
    Context manager per sessioni database.
    Usato per operazioni dirette sul database.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_database():
    """Inizializza il database e crea l'utente admin se non esiste."""
    from passlib.context import CryptContext
    from datetime import datetime
    
    # Crea le tabelle
    create_tables()
    
    # Verifica se esiste già un utente admin
    with get_db_session() as db:
        admin_user = db.query(User).filter(User.username == "admin").first()
        
        if not admin_user:
            print("👤 Creazione utente admin...")
            
            # Setup password hashing
            pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
            
            # Crea utente admin
            admin_user = User(
                username="admin",
                email="admin@wallbuild.local",
                full_name="Amministratore Sistema",
                company="Wall-Build System",
                hashed_password=pwd_context.hash("WallBuild2024!"),
                is_active=True,
                is_admin=True,
                created_at=datetime.now()
            )
            
            db.add(admin_user)
            db.commit()
            db.refresh(admin_user)
            
            print("✅ Utente admin creato con successo")
            print("👤 Credenziali admin:")
            print("   Username: admin") 
            print("   Password: WallBuild2024!")
            print("   ⚠️  CAMBIARE LA PASSWORD AL PRIMO ACCESSO!")
        else:
            print("👤 Utente admin già esistente")
    
    print("🗄️ Database inizializzato correttamente")

# ────────────────────────────────────────────────────────────────────────────────
# Utility Functions
# ────────────────────────────────────────────────────────────────────────────────

def reset_database():
    """Cancella e ricrea completamente il database."""
    print("🗑️ Reset database in corso...")
    Base.metadata.drop_all(bind=engine)
    init_database()
    print("✅ Database resettato con successo")

def get_database_info():
    """Restituisce informazioni sul database."""
    with get_db_session() as db:
        user_count = db.query(User).count()
        session_count = db.query(Session).count()  
        project_count = db.query(Project).count()
        saved_project_count = db.query(SavedProject).count()
        
        return {
            "database_file": DATABASE_FILE,
            "users": user_count,
            "sessions": session_count,
            "projects": project_count,
            "saved_projects": saved_project_count
        }

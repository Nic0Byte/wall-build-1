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

# Import centralized configuration
from utils.config import DATABASE_URL, DATABASE_TIMEOUT, DATABASE_ECHO

# Import structured logging
from utils.logging_config import get_logger, info, warning, error

from .models import Base, User, Session, Project, SavedProject
from .material_models import (
    Material, Guide, ProjectMaterialConfig, MaterialRule, ProjectTemplate
)

# ────────────────────────────────────────────────────────────────────────────────
# Configurazione Database (with environment support)
# ────────────────────────────────────────────────────────────────────────────────

# Assicura che la directory del database esista
def _ensure_database_dir():
    """Assicura che la directory del database esista."""
    if DATABASE_URL.startswith('sqlite:///'):
        db_path = DATABASE_URL.replace('sqlite:///', '')
        db_dir = os.path.dirname(db_path)
        if db_dir:  # Solo se c'è una directory specificata
            os.makedirs(db_dir, exist_ok=True)

_ensure_database_dir()

# Configurazione engine SQLAlchemy
engine = create_engine(
    DATABASE_URL,
    poolclass=StaticPool,
    connect_args={
        "check_same_thread": False,  # Necessario per SQLite con FastAPI
        "timeout": DATABASE_TIMEOUT
    },
    echo=DATABASE_ECHO  # Usa valore da environment
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
    logger = get_logger("database")
    logger.info("🗄️ Creazione tabelle database...")
    
    # Import tutti i modelli per assicurarsi che siano registrati
    from .models import Base as MainBase
    from .material_models import Base as MaterialBase
    
    # Crea tabelle principali
    MainBase.metadata.create_all(bind=engine)
    
    # Crea tabelle materiali
    MaterialBase.metadata.create_all(bind=engine)
    
    logger.info("✅ Tabelle create con successo")

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
    
    logger = get_logger("database")
    
    # Crea le tabelle
    create_tables()
    
    # Verifica se esiste già un utente admin
    with get_db_session() as db:
        admin_user = db.query(User).filter(User.username == "admin").first()
        
        if not admin_user:
            logger.info("👤 Creazione utente admin...")
            
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
            
            logger.info("✅ Utente admin creato con successo")
            logger.info("👤 Credenziali admin:")
            logger.info("   Username: admin") 
            logger.info("   Password: WallBuild2024!")
            logger.info("   ⚠️  CAMBIARE LA PASSWORD AL PRIMO ACCESSO!")
        else:
            logger.info("👤 Utente admin già esistente")
    
    # Inizializza il sistema materiali
    try:
        from .material_services import initialize_material_system
        initialize_material_system()
        logger.info("🔧 Sistema materiali inizializzato")
    except Exception as e:
        error("Errore inizializzazione materiali", error=str(e))
    
    logger.info("🗄️ Database inizializzato correttamente")

# ────────────────────────────────────────────────────────────────────────────────
# Utility Functions
# ────────────────────────────────────────────────────────────────────────────────

def reset_database():
    """Cancella e ricrea completamente il database."""
    logger = get_logger("database")
    logger.info("Reset database in corso", operation="database_reset")
    Base.metadata.drop_all(bind=engine)
    init_database()
    logger.info("Database resettato con successo", operation="database_reset", status="completed")

def get_database_info():
    """Restituisce informazioni sul database."""
    with get_db_session() as db:
        user_count = db.query(User).count()
        session_count = db.query(Session).count()  
        project_count = db.query(Project).count()
        saved_project_count = db.query(SavedProject).count()
        
        return {
            "database_url": DATABASE_URL,
            "users": user_count,
            "sessions": session_count,
            "projects": project_count,
            "saved_projects": saved_project_count
        }

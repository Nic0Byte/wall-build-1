"""
Database Services per Wall-Build
Servizi per gestione utenti, sessioni, autenticazione
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from passlib.context import CryptContext

from .models import User, Session as DBSession, Project
from .config import get_db_session

# ────────────────────────────────────────────────────────────────────────────────
# Password Hashing
# ────────────────────────────────────────────────────────────────────────────────

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica password."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hash password."""
    return pwd_context.hash(password)

# ────────────────────────────────────────────────────────────────────────────────
# User Services
# ────────────────────────────────────────────────────────────────────────────────

def get_user_by_username(username: str) -> Optional[User]:
    """Ottiene un utente per username."""
    with get_db_session() as db:
        return db.query(User).filter(User.username == username).first()

def get_user_by_email(email: str) -> Optional[User]:
    """Ottiene un utente per email."""
    with get_db_session() as db:
        return db.query(User).filter(User.email == email).first()

def get_user_by_id(user_id: int) -> Optional[User]:
    """Ottiene un utente per ID."""
    with get_db_session() as db:
        return db.query(User).filter(User.id == user_id).first()

def authenticate_user(username: str, password: str) -> Optional[User]:
    """Autentica un utente."""
    user = get_user_by_username(username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    if not user.is_active:
        return None
    
    # Aggiorna ultimo login
    with get_db_session() as db:
        db_user = db.query(User).filter(User.id == user.id).first()
        if db_user:
            db_user.last_login = datetime.now()
            db.commit()
    
    return user

def create_user(
    username: str,
    email: str, 
    password: str,
    full_name: str = None,
    company: str = None,
    is_admin: bool = False
) -> Optional[User]:
    """Crea un nuovo utente."""
    with get_db_session() as db:
        # Verifica che username ed email siano unici
        if db.query(User).filter(User.username == username).first():
            raise ValueError("Username già esistente")
        
        if db.query(User).filter(User.email == email).first():
            raise ValueError("Email già esistente")
        
        # Crea nuovo utente
        user = User(
            username=username,
            email=email,
            full_name=full_name,
            company=company,
            hashed_password=get_password_hash(password),
            is_active=True,
            is_admin=is_admin,
            created_at=datetime.now()
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
        
        return user

def update_user(
    user_id: int,
    email: str = None,
    full_name: str = None,
    company: str = None,
    is_active: bool = None
) -> Optional[User]:
    """Aggiorna un utente."""
    with get_db_session() as db:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return None
        
        if email is not None:
            # Verifica unicità email
            existing = db.query(User).filter(
                and_(User.email == email, User.id != user_id)
            ).first()
            if existing:
                raise ValueError("Email già esistente")
            user.email = email
        
        if full_name is not None:
            user.full_name = full_name
        if company is not None:
            user.company = company
        if is_active is not None:
            user.is_active = is_active
        
        db.commit()
        db.refresh(user)
        
        return user

def change_password(user_id: int, new_password: str) -> bool:
    """Cambia password utente."""
    with get_db_session() as db:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return False
        
        user.hashed_password = get_password_hash(new_password)
        db.commit()
        
        return True

def get_all_users(skip: int = 0, limit: int = 100) -> List[User]:
    """Ottiene tutti gli utenti (per admin)."""
    with get_db_session() as db:
        return db.query(User).offset(skip).limit(limit).all()

def delete_user(user_id: int) -> bool:
    """Elimina un utente."""
    with get_db_session() as db:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return False
        
        # Elimina anche le sessioni dell'utente
        db.query(DBSession).filter(DBSession.user_id == user_id).delete()
        
        # Elimina l'utente
        db.delete(user)
        db.commit()
        
        return True

# ────────────────────────────────────────────────────────────────────────────────
# Session Services  
# ────────────────────────────────────────────────────────────────────────────────

def create_session(
    user_id: int,
    token_hash: str,
    expires_at: datetime,
    user_agent: str = None,
    ip_address: str = None
) -> DBSession:
    """Crea una nuova sessione."""
    with get_db_session() as db:
        session = DBSession(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            is_active=True,
            user_agent=user_agent,
            ip_address=ip_address,
            created_at=datetime.now()
        )
        
        db.add(session)
        db.commit()
        db.refresh(session)
        
        return session

def get_session_by_token(token_hash: str) -> Optional[DBSession]:
    """Ottiene una sessione per token hash."""
    with get_db_session() as db:
        return db.query(DBSession).filter(
            and_(
                DBSession.token_hash == token_hash,
                DBSession.is_active == True,
                DBSession.expires_at > datetime.now()
            )
        ).first()

def invalidate_session(token_hash: str) -> bool:
    """Invalida una sessione.""" 
    with get_db_session() as db:
        session = db.query(DBSession).filter(DBSession.token_hash == token_hash).first()
        if not session:
            return False
        
        session.is_active = False
        db.commit()
        
        return True

def cleanup_expired_sessions() -> int:
    """Pulisce le sessioni scadute."""
    with get_db_session() as db:
        expired_count = db.query(DBSession).filter(
            DBSession.expires_at < datetime.now()
        ).count()
        
        db.query(DBSession).filter(
            DBSession.expires_at < datetime.now()
        ).delete()
        
        db.commit()
        
        return expired_count

def get_user_sessions(user_id: int, active_only: bool = True) -> List[DBSession]:
    """Ottiene le sessioni di un utente."""
    with get_db_session() as db:
        query = db.query(DBSession).filter(DBSession.user_id == user_id)
        
        if active_only:
            query = query.filter(
                and_(
                    DBSession.is_active == True,
                    DBSession.expires_at > datetime.now()
                )
            )
        
        return query.all()

# ────────────────────────────────────────────────────────────────────────────────
# Project Services
# ────────────────────────────────────────────────────────────────────────────────

def create_project(
    user_id: int,
    name: str,
    description: str = None,
    file_path: str = None
) -> Project:
    """Crea un nuovo progetto."""
    with get_db_session() as db:
        project = Project(
            user_id=user_id,
            name=name,
            description=description,
            file_path=file_path,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            is_active=True
        )
        
        db.add(project)
        db.commit()
        db.refresh(project)
        
        return project

def get_user_projects(user_id: int) -> List[Project]:
    """Ottiene i progetti di un utente."""
    with get_db_session() as db:
        return db.query(Project).filter(
            and_(
                Project.user_id == user_id,
                Project.is_active == True
            )
        ).order_by(Project.updated_at.desc()).all()

def get_project_by_id(project_id: int, user_id: int = None) -> Optional[Project]:
    """Ottiene un progetto per ID."""
    with get_db_session() as db:
        query = db.query(Project).filter(Project.id == project_id)
        
        if user_id is not None:
            query = query.filter(Project.user_id == user_id)
        
        return query.first()

def delete_project(project_id: int, user_id: int) -> bool:
    """Elimina un progetto."""
    with get_db_session() as db:
        project = db.query(Project).filter(
            and_(
                Project.id == project_id,
                Project.user_id == user_id
            )
        ).first()
        
        if not project:
            return False
        
        project.is_active = False
        db.commit()
        
        return True

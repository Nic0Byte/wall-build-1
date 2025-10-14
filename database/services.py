"""
Database Services per Wall-Build
Servizi per gestione utenti, sessioni, autenticazione
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from passlib.context import CryptContext

from .models import User, Session as DBSession, Project, SystemProfile
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

# ────────────────────────────────────────────────────────────────────────────────
# System Profile Services
# ────────────────────────────────────────────────────────────────────────────────

def get_user_profiles(user_id: int) -> List['SystemProfile']:
    """Ottiene tutti i profili sistema di un utente."""
    from .models import SystemProfile
    with get_db_session() as db:
        profiles = db.query(SystemProfile).filter(
            and_(
                SystemProfile.user_id == user_id,
                SystemProfile.is_active == True
            )
        ).order_by(SystemProfile.is_default.desc(), SystemProfile.name).all()
        
        # Detach from session
        db.expunge_all()
        return profiles

def get_profile_by_id(profile_id: int, user_id: int) -> Optional['SystemProfile']:
    """Ottiene un profilo specifico."""
    from .models import SystemProfile
    with get_db_session() as db:
        profile = db.query(SystemProfile).filter(
            and_(
                SystemProfile.id == profile_id,
                SystemProfile.user_id == user_id,
                SystemProfile.is_active == True
            )
        ).first()
        
        if profile:
            db.expunge(profile)
        return profile

def get_default_profile(user_id: int) -> Optional['SystemProfile']:
    """Ottiene il profilo predefinito dell'utente."""
    from .models import SystemProfile
    with get_db_session() as db:
        profile = db.query(SystemProfile).filter(
            and_(
                SystemProfile.user_id == user_id,
                SystemProfile.is_default == True,
                SystemProfile.is_active == True
            )
        ).first()
        
        if profile:
            db.expunge(profile)
        return profile

def create_system_profile(
    user_id: int,
    name: str,
    block_config: str,  # JSON string
    moraletti_config: str,  # JSON string
    description: str = None,
    algorithm_type: str = 'small',
    is_default: bool = False
) -> 'SystemProfile':
    """Crea un nuovo profilo sistema."""
    from .models import SystemProfile
    
    with get_db_session() as db:
        # Se questo profilo è impostato come default, rimuovi flag default da altri
        if is_default:
            db.query(SystemProfile).filter(
                and_(
                    SystemProfile.user_id == user_id,
                    SystemProfile.is_default == True
                )
            ).update({SystemProfile.is_default: False})
        
        # Crea nuovo profilo
        profile = SystemProfile(
            user_id=user_id,
            name=name,
            description=description,
            block_config=block_config,
            moraletti_config=moraletti_config,
            algorithm_type=algorithm_type,
            is_default=is_default,
            is_active=True,
            created_at=datetime.now()
        )
        
        db.add(profile)
        db.commit()
        db.refresh(profile)
        db.expunge(profile)
        
        return profile

def update_system_profile(
    profile_id: int,
    user_id: int,
    name: str = None,
    description: str = None,
    block_config: str = None,
    moraletti_config: str = None,
    algorithm_type: str = None,
    is_default: bool = None
) -> Optional['SystemProfile']:
    """Aggiorna un profilo sistema esistente."""
    from .models import SystemProfile
    
    with get_db_session() as db:
        profile = db.query(SystemProfile).filter(
            and_(
                SystemProfile.id == profile_id,
                SystemProfile.user_id == user_id
            )
        ).first()
        
        if not profile:
            return None
        
        # Se questo profilo diventa default, rimuovi flag da altri
        if is_default and not profile.is_default:
            db.query(SystemProfile).filter(
                and_(
                    SystemProfile.user_id == user_id,
                    SystemProfile.is_default == True,
                    SystemProfile.id != profile_id
                )
            ).update({SystemProfile.is_default: False})
        
        # Aggiorna campi
        if name is not None:
            profile.name = name
        if description is not None:
            profile.description = description
        if block_config is not None:
            profile.block_config = block_config
        if moraletti_config is not None:
            profile.moraletti_config = moraletti_config
        if algorithm_type is not None:
            profile.algorithm_type = algorithm_type
        if is_default is not None:
            profile.is_default = is_default
        
        profile.updated_at = datetime.now()
        
        db.commit()
        db.refresh(profile)
        db.expunge(profile)
        
        return profile

def delete_system_profile(profile_id: int, user_id: int) -> bool:
    """Elimina (soft delete) un profilo sistema."""
    from .models import SystemProfile
    
    with get_db_session() as db:
        profile = db.query(SystemProfile).filter(
            and_(
                SystemProfile.id == profile_id,
                SystemProfile.user_id == user_id
            )
        ).first()
        
        if not profile:
            return False
        
        # Soft delete
        profile.is_active = False
        db.commit()
        
        return True

def ensure_default_profile(user_id: int) -> 'SystemProfile':
    """
    Assicura che l'utente abbia un profilo Default.
    Se non esiste, lo crea con valori standard.
    Chiamato automaticamente al primo login.
    """
    import json
    from .models import SystemProfile
    
    # Verifica se esiste già un profilo default
    default_profile = get_default_profile(user_id)
    if default_profile:
        return default_profile
    
    # Verifica se l'utente ha almeno un profilo
    profiles = get_user_profiles(user_id)
    if profiles:
        # Ha profili ma nessuno è default, imposta il primo come default
        return update_system_profile(
            profile_id=profiles[0].id,
            user_id=user_id,
            is_default=True
        )
    
    # Nessun profilo esistente, crea "Default" con valori standard
    default_block_config = json.dumps({
        "widths": [1239, 826, 413],
        "heights": [495, 495, 495]
    })
    
    default_moraletti_config = json.dumps({
        "thickness": 58,
        "height": 495,
        "heightFromGround": 95,
        "spacing": 420,
        "countLarge": 3,
        "countMedium": 2,
        "countSmall": 1
    })
    
    return create_system_profile(
        user_id=user_id,
        name="Default",
        description="Configurazione standard del sistema",
        block_config=default_block_config,
        moraletti_config=default_moraletti_config,
        is_default=True
    )

# ────────────────────────────────────────────────────────────────────────────────
# System Snapshot Services
# ────────────────────────────────────────────────────────────────────────────────

def get_complete_system_snapshot(user_id: int) -> Dict[str, Any]:
    """
    Recupera uno snapshot completo del sistema per salvataggio con progetto.
    Include tutti i profili sistema e le configurazioni disponibili al momento del salvataggio.
    
    Returns:
        Dict contenente:
        - saved_at: timestamp ISO
        - user_profiles: lista di tutti i profili dell'utente
        - default_profile_id: ID del profilo predefinito (None se non esiste)
    """
    import json
    from datetime import datetime
    
    try:
        # Recupera tutti i profili dell'utente
        profiles = get_user_profiles(user_id)
        default_profile = get_default_profile(user_id)
        
        # Serializza i profili
        profiles_data = []
        for profile in profiles:
            try:
                profiles_data.append({
                    "id": profile.id,
                    "name": profile.name,
                    "description": profile.description,
                    "block_config": json.loads(profile.block_config) if profile.block_config else None,
                    "moraletti_config": json.loads(profile.moraletti_config) if profile.moraletti_config else None,
                    "is_default": profile.is_default,
                    "created_at": profile.created_at.isoformat() if profile.created_at else None,
                    "updated_at": profile.updated_at.isoformat() if profile.updated_at else None
                })
            except Exception as e:
                print(f"⚠️ Errore serializzazione profilo {profile.id}: {e}")
                continue
        
        snapshot = {
            "saved_at": datetime.now().isoformat(),
            "user_profiles": profiles_data,
            "default_profile_id": default_profile.id if default_profile else None,
            "snapshot_version": "1.0"  # Versione del formato snapshot per future migrazioni
        }
        
        print(f"✅ Snapshot creato con successo: {len(profiles_data)} profili")
        return snapshot
        
    except Exception as e:
        # In caso di errore, ritorna snapshot vuoto ma valido
        print(f"⚠️ Errore creazione snapshot sistema: {e}")
        return {
            "saved_at": datetime.now().isoformat(),
            "user_profiles": [],
            "default_profile_id": None,
            "snapshot_version": "1.0",
            "error": str(e)
        }

def get_materials_snapshot() -> Dict[str, Any]:
    """
    Recupera snapshot completo di tutti i materiali disponibili nel database.
    Include blocchi, malte, rivestimenti, ecc.
    
    NOTA: Per ora ritorna struttura vuota, da implementare quando avremo
    tabelle materiali nel database.
    
    Returns:
        Dict contenente i materiali disponibili
    """
    try:
        # Try to import material services if available
        from database.material_services import (
            get_all_blocks,
            get_all_mortars, 
            get_all_coatings
        )
        
        # Recupera tutti i materiali dal database
        blocks = get_all_blocks()
        mortars = get_all_mortars()
        coatings = get_all_coatings()
        
        snapshot = {
            "blocks": [block.to_dict() for block in blocks] if blocks else [],
            "mortars": [mortar.to_dict() for mortar in mortars] if mortars else [],
            "coatings": [coating.to_dict() for coating in coatings] if coatings else [],
            "snapshot_version": "1.0"
        }
        
        return snapshot
        
    except ImportError as e:
        # Material services not yet implemented
        print(f"ℹ️ Material services non ancora implementato: {e}")
        return {
            "blocks": [],
            "mortars": [],
            "coatings": [],
            "snapshot_version": "1.0",
            "note": "Materials database not yet implemented"
        }
    except Exception as e:
        # Se non ci sono tabelle materiali o errore, ritorna snapshot vuoto
        print(f"⚠️ Materiali snapshot non disponibile: {e}")
        return {
            "blocks": [],
            "mortars": [],
            "coatings": [],
            "snapshot_version": "1.0",
            "note": "Materials database error"
        }


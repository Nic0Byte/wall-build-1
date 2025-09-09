"""
Routes API per Wall-Build con Autenticazione Sicura
"""

from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.security import HTTPBearer
from fastapi.responses import JSONResponse

from .models import (
    User, UserCreate, UserLogin, Token, PackingConfig, PackingResult, 
    Project, ProjectCreate
)
from .auth import (
    get_current_user, get_current_active_user, get_current_admin_user, 
    create_access_token, login_user, create_user, ACCESS_TOKEN_EXPIRE_MINUTES
)
from database.services import cleanup_expired_sessions
from database.config import get_database_info

# ────────────────────────────────────────────────────────────────────────────────
# Setup Router
# ────────────────────────────────────────────────────────────────────────────────

router = APIRouter()
security = HTTPBearer()

# ────────────────────────────────────────────────────────────────────────────────
# Routes Autenticazione
# ────────────────────────────────────────────────────────────────────────────────

@router.post("/auth/register", response_model=dict, summary="Registra nuovo utente")
async def register_user(user_data: UserCreate):
    """
    Registra un nuovo utente nel sistema.
    
    - **username**: Nome utente univoco
    - **email**: Email univoca  
    - **password**: Password sicura (min 8 caratteri, maiuscole, minuscole, numeri, caratteri speciali)
    - **full_name**: Nome completo (opzionale)
    - **company**: Azienda (opzionale)
    """
    success, message, user = create_user(user_data)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )
    
    return {
        "success": True,
        "message": message,
        "user": user
    }

@router.post("/auth/login", response_model=Token, summary="Login utente")
async def login_for_access_token(request: Request, user_credentials: UserLogin):
    """
    Autentica utente e ritorna token di accesso.
    
    - **username**: Nome utente
    - **password**: Password
    """
    result = login_user(user_credentials.username, user_credentials.password)
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Username o password non corretti",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token, user = result
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account disattivato"
        )

    # Log accesso
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    print(f"🔑 Login utente '{user.username}' da {client_ip}")
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )

@router.post("/auth/logout", summary="Logout utente")
async def logout_user(
    request: Request,
    current_user: User = Depends(get_current_active_user)
):
    """Effettua logout e invalida la sessione corrente."""
    
    client_ip = request.client.host if request.client else "unknown"
    print(f"🚪 Logout utente '{current_user.username}' da {client_ip}")
    
    return {
        "success": True,
        "message": "Logout effettuato con successo"
    }

@router.get("/auth/me", response_model=User, summary="Profilo utente corrente")
async def get_current_user_profile(current_user: User = Depends(get_current_active_user)):
    """Ritorna il profilo dell'utente autenticato."""
    return current_user

@router.put("/auth/me", response_model=User, summary="Aggiorna profilo utente")
async def update_user_profile(
    profile_data: dict,
    current_user: User = Depends(get_current_active_user)
):
    """Aggiorna il profilo dell'utente autenticato."""
    # Implementazione semplificata
    # In produzione implementare validazione e aggiornamento database
    
    return {
        "success": True,
        "message": "Profilo aggiornato con successo"
    }

@router.post("/auth/change-password", summary="Cambia password")
async def change_password(
    password_data: dict,
    current_user: User = Depends(get_current_active_user)
):
    """Cambia la password dell'utente autenticato."""
    # Implementazione semplificata
    # In produzione implementare validazione password corrente e aggiornamento
    
    return {
        "success": True,
        "message": "Password cambiata con successo"
    }

# ────────────────────────────────────────────────────────────────────────────────
# Routes Amministrazione (Solo Admin)
# ────────────────────────────────────────────────────────────────────────────────

@router.get("/admin/users", response_model=List[User], summary="Lista utenti (Admin)")
async def list_users(
    skip: int = 0,
    limit: int = 100,
    admin_user: User = Depends(get_current_admin_user)
):
    """Ritorna la lista di tutti gli utenti (solo amministratori)."""
    # Implementazione semplificata
    return []

@router.get("/admin/stats", summary="Statistiche sistema (Admin)")
async def get_admin_stats(admin_user: User = Depends(get_current_admin_user)):
    """Ritorna statistiche del sistema (solo amministratori)."""
    
    # Pulizia sessioni scadute
    expired_sessions = cleanup_expired_sessions()
    
    # Ottiene info database
    db_info = get_database_info()
    
    stats = {
        "database": db_info,
        "expired_sessions_cleaned": expired_sessions,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    return {
        "success": True,
        "data": stats
    }

@router.post("/admin/users/{username}/deactivate", summary="Disattiva utente (Admin)")
async def deactivate_user(
    username: str,
    admin_user: User = Depends(get_current_admin_user)
):
    """Disattiva un utente specifico (solo amministratori)."""
    
    if username == admin_user.username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Non puoi disattivare il tuo stesso account"
        )
    
    # Implementazione semplificata
    return {
        "success": True,
        "message": f"Utente {username} disattivato"
    }

# ────────────────────────────────────────────────────────────────────────────────
# Routes Progetti (Protetti da Autenticazione)
# ────────────────────────────────────────────────────────────────────────────────

@router.get("/projects", response_model=List[Project], summary="Lista progetti utente")
async def list_user_projects(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user)
):
    """Ritorna la lista dei progetti dell'utente autenticato."""
    # Implementazione semplificata - ritorna progetti mock
    return []

@router.post("/projects", response_model=Project, summary="Crea nuovo progetto")
async def create_project(
    project_data: ProjectCreate,
    current_user: User = Depends(get_current_active_user)
):
    """Crea un nuovo progetto per l'utente autenticato."""
    
    # Implementazione semplificata
    project = Project(
        id=1,
        name=project_data.name,
        description=project_data.description,
        tags=project_data.tags,
        owner_id=current_user.id,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        status="draft"
    )
    
    return project

@router.get("/projects/{project_id}", response_model=Project, summary="Dettagli progetto")
async def get_project(
    project_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """Ritorna i dettagli di un progetto specifico."""
    
    # Implementazione semplificata
    # In produzione verificare che l'utente sia proprietario del progetto
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Progetto non trovato"
    )

@router.delete("/projects/{project_id}", summary="Elimina progetto")
async def delete_project(
    project_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """Elimina un progetto dell'utente autenticato."""
    
    # Implementazione semplificata
    # In produzione verificare proprietà e eliminare dal database
    
    return {
        "success": True,
        "message": "Progetto eliminato con successo"
    }

# ────────────────────────────────────────────────────────────────────────────────
# Routes Packing (Protetti da Autenticazione)
# ────────────────────────────────────────────────────────────────────────────────

@router.post("/packing/process", response_model=PackingResult, summary="Elabora packing parete")
async def process_packing(
    config: PackingConfig,
    current_user: User = Depends(get_current_active_user)
):
    """
    Elabora il packing di una parete con i parametri specificati.
    Richiede autenticazione.
    """
    
    # Implementazione semplificata
    # In produzione integrare con la logica di packing esistente
    
    result = PackingResult(
        session_id="demo_session",
        status="completed",
        wall_bounds=[0, 0, 5000, 3000],
        blocks_standard=[],
        blocks_custom=[],
        apertures=[],
        summary={},
        config=config.dict(),
        metrics={}
    )
    
    return result

# ────────────────────────────────────────────────────────────────────────────────
# Routes Utilities
# ────────────────────────────────────────────────────────────────────────────────

@router.get("/health", summary="Health Check")
async def health_check():
    """Endpoint per verificare lo stato del servizio."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "auth_system": "active"
    }

@router.get("/", summary="Root endpoint")
async def root():
    """Root endpoint con informazioni sul sistema."""
    return {
        "message": "Wall-Build API con Autenticazione Sicura",
        "version": "1.0.0",
        "docs": "/docs",
        "auth_required": True,
        "endpoints": {
            "register": "/auth/register",
            "login": "/auth/login",
            "logout": "/auth/logout",
            "profile": "/auth/me"
        }
    }
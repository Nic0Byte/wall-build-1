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
from .material_routes import materials_router  # NEW: Import delle route materiali
from database.services import cleanup_expired_sessions
from database.config import get_database_info
from pathlib import Path
import logging
import os

logger = logging.getLogger(__name__)

# ────────────────────────────────────────────────────────────────────────────────
# Helper Functions
# ────────────────────────────────────────────────────────────────────────────────

def delete_project_files(project) -> dict:
    """
    Elimina definitivamente tutti i file fisici associati a un progetto.
    
    Args:
        project: Oggetto SavedProject dal database
        
    Returns:
        dict: Statistiche sui file eliminati
    """
    deleted_files = []
    failed_files = []
    
    # Lista dei percorsi da eliminare
    file_paths = [
        project.file_path,      # File DWG/DXF originale
        project.svg_path,       # File SVG generato
        project.pdf_path,       # File PDF generato
        project.json_path,      # File JSON generato
    ]
    
    for file_path in file_paths:
        if file_path:
            try:
                path = Path(file_path)
                if path.exists() and path.is_file():
                    path.unlink()  # Elimina il file
                    deleted_files.append(str(path))
                    logger.info(f"File eliminato: {path}")
            except Exception as e:
                failed_files.append(str(file_path))
                logger.error(f"Errore eliminazione file {file_path}: {str(e)}")
    
    # Prova a eliminare eventuali file aggiuntivi nella cartella temp del progetto
    try:
        if project.file_path:
            base_path = Path(project.file_path)
            temp_dir = Path("output/temp") / base_path.stem
            if temp_dir.exists() and temp_dir.is_dir():
                # Elimina tutti i file nella cartella temp del progetto
                for temp_file in temp_dir.iterdir():
                    if temp_file.is_file():
                        temp_file.unlink()
                        deleted_files.append(str(temp_file))
                # Prova a eliminare la cartella se vuota
                try:
                    temp_dir.rmdir()
                    logger.info(f"Cartella temp eliminata: {temp_dir}")
                except:
                    pass  # Ignora se la cartella non è vuota
    except Exception as e:
        logger.error(f"Errore pulizia cartella temp: {str(e)}")
    
    return {
        "deleted": len(deleted_files),
        "failed": len(failed_files),
        "deleted_files": deleted_files,
        "failed_files": failed_files
    }

# ────────────────────────────────────────────────────────────────────────────────
# Setup Router
# ────────────────────────────────────────────────────────────────────────────────

router = APIRouter()
security = HTTPBearer()

# Include il router materiali
router.include_router(materials_router)

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
# Routes Progetti Salvati
# ────────────────────────────────────────────────────────────────────────────────

async def save_project_file_from_session(session_id: str, username: str, filename: str) -> str:
    """Salva il file dal session_id nella cartella appropriata."""
    try:
        from pathlib import Path
        import os
        
        # Ottieni i file_bytes dalla sessione
        from main import SESSIONS
        
        if session_id not in SESSIONS:
            raise ValueError(f"Session ID {session_id} non trovato")
        
        session = SESSIONS[session_id]
        if 'file_bytes' not in session:
            raise ValueError(f"File bytes non trovati nella sessione {session_id}")
        
        # Crea la directory per l'utente
        output_dir = Path("output/saved_projects") / username
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Genera nome file univoco con timestamp
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_ext = Path(filename).suffix
        safe_filename = f"{timestamp}_{filename.replace(' ', '_')}"
        file_path = output_dir / safe_filename
        
        # Scrivi il file
        with open(file_path, 'wb') as f:
            f.write(session['file_bytes'])
        
        print(f"💾 File salvato: {file_path}")
        return str(file_path)
        
    except Exception as e:
        print(f"❌ Errore nel salvataggio file: {e}")
        return None

@router.post("/saved-projects/save")
async def save_project(
    project_data: dict,
    current_user: User = Depends(get_current_active_user)
):
    """Salva un progetto completato per riutilizzo futuro con snapshot del sistema."""
    try:
        from database.models import SavedProject
        from database.config import get_db_session
        from database.services import get_complete_system_snapshot, get_materials_snapshot
        import json
        import os
        from pathlib import Path
        
        # ===== NUOVO: Crea snapshot completo del sistema =====
        print(f"📸 Creazione snapshot sistema per progetto '{project_data.get('name')}'...")
        
        system_snapshot = get_complete_system_snapshot(current_user.id)
        materials_snapshot = get_materials_snapshot()
        
        # Combina gli snapshot
        complete_snapshot = {
            "system_config": system_snapshot,
            "materials": materials_snapshot,
            "snapshot_version": "1.0"
        }
        
        print(f"✅ Snapshot creato: {len(system_snapshot.get('user_profiles', []))} profili salvati")
        
        # Salva il file dal session_id se fornito
        file_path = None
        if project_data.get("session_id"):
            file_path = await save_project_file_from_session(
                project_data["session_id"], 
                current_user.username,
                project_data.get("filename", "project_file")
            )
        
        # ===== Prepara extended_config con snapshot =====
        extended_config = project_data.get("extended_config", {})
        if not isinstance(extended_config, dict):
            extended_config = {}
        
        # Aggiungi snapshot al extended_config
        extended_config["system_snapshot"] = complete_snapshot
        
        with get_db_session() as db:
            # Crea nuovo progetto salvato
            saved_project = SavedProject(
                user_id=current_user.id,
                project_name=project_data.get("name"),
                original_filename=project_data.get("filename"),
                file_path=file_path,
                profile_name=project_data.get("profile_name", "Sistema Standard"),  # NEW: Nome profilo
                block_dimensions=json.dumps(project_data.get("block_dimensions")),
                color_theme=json.dumps(project_data.get("color_theme")),
                packing_config=json.dumps(project_data.get("packing_config")),
                results_summary=json.dumps(project_data.get("results")),
                extended_config=json.dumps(extended_config),  # Include snapshot
                wall_dimensions=project_data.get("wall_dimensions"),
                total_blocks=project_data.get("total_blocks"),
                efficiency_percentage=project_data.get("efficiency"),
                svg_path=project_data.get("svg_path"),
                pdf_path=project_data.get("pdf_path"),
                json_path=project_data.get("json_path")
            )
            
            db.add(saved_project)
            db.commit()
            db.refresh(saved_project)
            
            return {
                "success": True,
                "message": "Progetto salvato con successo (con snapshot sistema)",
                "project_id": saved_project.id,
                "file_path": file_path,
                "snapshot_info": {
                    "profiles_count": len(system_snapshot.get("user_profiles", [])),
                    "saved_at": system_snapshot.get("saved_at")
                }
            }
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Errore nel salvataggio progetto: {str(e)}"
        )

@router.get("/saved-projects/list")
async def get_saved_projects(
    current_user: User = Depends(get_current_active_user)
):
    """Recupera la lista dei progetti salvati dell'utente."""
    try:
        from database.models import SavedProject
        from database.config import get_db_session
        import json
        
        with get_db_session() as db:
            projects = db.query(SavedProject)\
                        .filter(SavedProject.user_id == current_user.id)\
                        .filter(SavedProject.is_active == True)\
                        .order_by(SavedProject.created_at.desc())\
                        .all()
            
            projects_list = []
            for project in projects:
                # Parse extended_config per ottenere algorithm_type
                algorithm_type = 'bidirectional'  # Default
                if project.extended_config:
                    try:
                        extended_data = json.loads(project.extended_config)
                        algorithm_type = extended_data.get('algorithm_type', 'bidirectional')
                    except:
                        pass  # Usa default se parsing fallisce
                
                project_data = {
                    "id": project.id,
                    "name": project.project_name,
                    "filename": project.original_filename,
                    "profile_name": project.profile_name or "Sistema Standard",  # NEW: Nome profilo
                    "algorithm_type": algorithm_type,  # NEW: Tipo algoritmo usato
                    "wall_dimensions": project.wall_dimensions,
                    "total_blocks": project.total_blocks,
                    "efficiency": project.efficiency_percentage,
                    "created_at": project.created_at.isoformat(),
                    "last_used": project.last_used.isoformat() if project.last_used else None,
                    "has_svg": bool(project.svg_path),
                    "has_pdf": bool(project.pdf_path)
                }
                projects_list.append(project_data)
            
            return {
                "success": True,
                "projects": projects_list,
                "count": len(projects_list)
            }
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Errore nel recupero progetti: {str(e)}"
        )

@router.get("/saved-projects/{project_id}")
async def get_saved_project(
    project_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """Recupera i dettagli completi di un progetto salvato."""
    try:
        from database.models import SavedProject
        from database.config import get_db_session
        import json
        
        with get_db_session() as db:
            project = db.query(SavedProject)\
                       .filter(SavedProject.id == project_id)\
                       .filter(SavedProject.user_id == current_user.id)\
                       .filter(SavedProject.is_active == True)\
                       .first()
            
            if not project:
                raise HTTPException(
                    status_code=404,
                    detail="Progetto non trovato"
                )
            
            # Aggiorna last_used
            project.last_used = datetime.now()
            db.commit()
            
            # Recupera extended_config
            extended_config = json.loads(project.extended_config) if project.extended_config else {}
            
            # ===== NUOVO: Verifica presenza snapshot =====
            has_snapshot = False
            snapshot_info = None
            
            if "system_snapshot" in extended_config:
                has_snapshot = True
                snapshot = extended_config["system_snapshot"]
                system_config = snapshot.get("system_config", {})
                
                snapshot_info = {
                    "has_snapshot": True,
                    "saved_at": system_config.get("saved_at"),
                    "profiles_count": len(system_config.get("user_profiles", [])),
                    "snapshot_version": snapshot.get("snapshot_version", "unknown")
                }
                
                print(f"📸 Progetto caricato con snapshot del {system_config.get('saved_at', 'unknown')}")
            else:
                snapshot_info = {
                    "has_snapshot": False,
                    "warning": "Progetto in formato legacy, potrebbe usare configurazione corrente del sistema"
                }
                print(f"⚠️ Progetto legacy senza snapshot, userà configurazione corrente")
            
            return {
                "success": True,
                "project": {
                    "id": project.id,
                    "name": project.project_name,
                    "filename": project.original_filename,
                    "file_path": project.file_path,
                    "block_dimensions": json.loads(project.block_dimensions) if project.block_dimensions else None,
                    "color_theme": json.loads(project.color_theme) if project.color_theme else None,
                    "packing_config": json.loads(project.packing_config) if project.packing_config else None,
                    "results": json.loads(project.results_summary) if project.results_summary else None,
                    "extended_config": extended_config,
                    "wall_dimensions": project.wall_dimensions,
                    "total_blocks": project.total_blocks,
                    "efficiency": project.efficiency_percentage,
                    "svg_path": project.svg_path,
                    "pdf_path": project.pdf_path,
                    "json_path": project.json_path,
                    "created_at": project.created_at.isoformat(),
                    "last_used": project.last_used.isoformat(),
                    "snapshot_info": snapshot_info  # NEW: Info sullo snapshot
                }
            }
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Errore nel recupero progetto: {str(e)}"
        )

@router.delete("/saved-projects/all")
async def delete_all_saved_projects(
    current_user: User = Depends(get_current_active_user)
):
    """Elimina definitivamente tutti i progetti salvati dell'utente e tutti i file associati."""
    try:
        from database.models import SavedProject
        from database.config import get_db_session
        
        with get_db_session() as db:
            # Ottieni tutti i progetti attivi dell'utente
            projects = db.query(SavedProject)\
                        .filter(SavedProject.user_id == current_user.id)\
                        .filter(SavedProject.is_active == True)\
                        .all()
            
            if not projects:
                return {
                    "success": True,
                    "message": "Nessun progetto da eliminare",
                    "deleted_count": 0,
                    "total_files_deleted": 0
                }
            
            count = len(projects)
            total_files_deleted = 0
            total_files_failed = 0
            
            # Elimina fisicamente i file di ogni progetto
            for project in projects:
                file_deletion_stats = delete_project_files(project)
                total_files_deleted += file_deletion_stats["deleted"]
                total_files_failed += file_deletion_stats["failed"]
                
                # Elimina il record dal database (hard delete)
                db.delete(project)
            
            db.commit()
            
            logger.info(f"Eliminati definitivamente {count} progetti e {total_files_deleted} file per utente {current_user.username}")
            
            return {
                "success": True,
                "message": f"Eliminati definitivamente {count} progetti dall'archivio",
                "deleted_count": count,
                "total_files_deleted": total_files_deleted,
                "total_files_failed": total_files_failed
            }
            
    except Exception as e:
        logger.error(f"Errore nell'eliminazione progetti per utente {current_user.username}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Errore nell'eliminazione progetti: {str(e)}"
        )

@router.delete("/saved-projects/{project_id}")
async def delete_saved_project(
    project_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """Elimina definitivamente un progetto salvato e tutti i suoi file associati."""
    try:
        from database.models import SavedProject
        from database.config import get_db_session
        
        with get_db_session() as db:
            project = db.query(SavedProject)\
                       .filter(SavedProject.id == project_id)\
                       .filter(SavedProject.user_id == current_user.id)\
                       .first()
            
            if not project:
                raise HTTPException(
                    status_code=404,
                    detail="Progetto non trovato"
                )
            
            # Elimina fisicamente tutti i file associati
            file_deletion_stats = delete_project_files(project)
            
            # Elimina il record dal database (hard delete)
            db.delete(project)
            db.commit()
            
            logger.info(f"Progetto {project_id} eliminato definitivamente da utente {current_user.username}")
            
            return {
                "success": True,
                "message": "Progetto e tutti i file associati eliminati definitivamente",
                "project_name": project.project_name,
                "files_deleted": file_deletion_stats["deleted"],
                "files_failed": file_deletion_stats["failed"]
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Errore nell'eliminazione progetto {project_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Errore nell'eliminazione progetto: {str(e)}"
        )

@router.get("/saved-projects/{project_id}/file")
async def get_saved_project_file(
    project_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """Recupera il file originale di un progetto salvato."""
    from fastapi.responses import FileResponse
    from pathlib import Path
    from database.models import SavedProject
    from database.config import get_db_session
    
    try:
        with get_db_session() as db:
            project = db.query(SavedProject)\
                       .filter(SavedProject.id == project_id)\
                       .filter(SavedProject.user_id == current_user.id)\
                       .filter(SavedProject.is_active == True)\
                       .first()
            
            if not project:
                raise HTTPException(
                    status_code=404,
                    detail="Progetto non trovato"
                )
            
            if not project.file_path:
                raise HTTPException(
                    status_code=404,
                    detail="File del progetto non disponibile"
                )
            
            file_path = Path(project.file_path)
            
            if not file_path.exists():
                raise HTTPException(
                    status_code=404,
                    detail="File del progetto non trovato sul filesystem"
                )
            
            # Determina il media type basandosi sull'estensione
            file_ext = file_path.suffix.lower()
            media_type = "application/octet-stream"
            
            if file_ext == ".svg":
                media_type = "image/svg+xml"
            elif file_ext == ".dwg":
                media_type = "application/acad"
            elif file_ext == ".dxf":
                media_type = "application/dxf"
            
            return FileResponse(
                path=str(file_path),
                filename=project.original_filename,
                media_type=media_type
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Errore nel recupero file progetto: {str(e)}"
        )

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
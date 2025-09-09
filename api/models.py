from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

# ────────────────────────────────────────────────────────────────────────────────
# Modelli Autenticazione
# ────────────────────────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    """Modello per creazione nuovo utente."""
    username: str
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    company: Optional[str] = None

class UserLogin(BaseModel):
    """Modello per login utente."""
    username: str
    password: str

class User(BaseModel):
    """Modello utente (senza password)."""
    id: int
    username: str
    email: str
    full_name: Optional[str] = None
    company: Optional[str] = None
    is_active: bool = True
    is_admin: bool = False
    created_at: datetime
    last_login: Optional[datetime] = None

class UserInDB(User):
    """Modello utente nel database (con password hash)."""
    hashed_password: str

class Token(BaseModel):
    """Modello token di accesso."""
    access_token: str
    token_type: str
    expires_in: int

class TokenData(BaseModel):
    """Dati contenuti nel token."""
    username: Optional[str] = None

# ────────────────────────────────────────────────────────────────────────────────
# Modelli Progetto
# ────────────────────────────────────────────────────────────────────────────────

class ProjectCreate(BaseModel):
    """Modello per creazione progetto."""
    name: str
    description: Optional[str] = None
    tags: Optional[List[str]] = []

class Project(BaseModel):
    """Modello progetto."""
    id: int
    name: str
    description: Optional[str] = None
    tags: List[str] = []
    owner_id: int
    created_at: datetime
    updated_at: datetime
    status: str = "draft"  # draft, active, completed, archived

class PackingConfig(BaseModel):
    """Configurazione parametri di packing."""
    block_widths: List[int] = [1239, 826, 413]
    block_height: int = 495
    row_offset: Optional[int] = 826
    snap_mm: float = 1.0
    keep_out_mm: float = 10.0

class PackingResult(BaseModel):
    """Risultato del packing."""
    session_id: str
    status: str
    wall_bounds: List[float]
    blocks_standard: List[dict]
    blocks_custom: List[dict]
    apertures: List[dict]
    summary: dict
    config: dict
    metrics: dict
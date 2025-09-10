# Modulo di autenticazione semplificato
from database.services import authenticate_user, get_user_by_username
from .models import User, Token
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
import secrets

ACCESS_TOKEN_EXPIRE_MINUTES = 120  # 2 ore invece di 30 minuti
SECRET_KEY = "wallbuild_secure_secret_key_2024_change_in_production"  # In produzione, usare variabile ambiente
ALGORITHM = "HS256"

security = HTTPBearer()

def create_access_token(data, expires_delta=None):
    from datetime import datetime, timedelta
    
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def login_user(username, password):
    from datetime import timedelta
    
    db_user = authenticate_user(username, password)
    if not db_user:
        return None
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": db_user.username},
        expires_delta=access_token_expires
    )
    
    user_model = User(
        id=db_user.id,
        username=db_user.username,
        email=db_user.email,
        full_name=db_user.full_name,
        company=db_user.company,
        is_active=db_user.is_active,
        is_admin=db_user.is_admin,
        created_at=db_user.created_at,
        last_login=db_user.last_login
    )
    
    return access_token, user_model

def create_user(user_data):
    return False, "Not implemented", None

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verifica il token JWT e restituisce il payload."""
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token invalido",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalido",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def get_current_user(payload: dict = Depends(verify_token)):
    """Ottiene l'utente corrente dal token."""
    username = payload.get("sub")
    db_user = get_user_by_username(username)
    
    if db_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Utente non trovato",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return User(
        id=db_user.id,
        username=db_user.username,
        email=db_user.email,
        full_name=db_user.full_name,
        company=db_user.company,
        is_active=db_user.is_active,
        is_admin=db_user.is_admin,
        created_at=db_user.created_at,
        last_login=db_user.last_login
    )

async def get_current_active_user(current_user: User = Depends(get_current_user)):
    """Ottiene l'utente corrente se è attivo."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Utente disattivato"
        )
    return current_user

async def get_current_admin_user(current_user: User = Depends(get_current_active_user)):
    """Ottiene l'utente corrente se è admin."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Privilegi insufficienti"
        )
    return current_user

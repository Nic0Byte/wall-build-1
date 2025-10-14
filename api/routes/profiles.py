"""
API Routes per System Profiles
Gestione profili sistema (preset configurazioni blocchi e moraletti)
"""

import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from database.services import (
    get_user_profiles,
    get_profile_by_id,
    get_default_profile,
    create_system_profile,
    update_system_profile,
    delete_system_profile,
    ensure_default_profile
)
from api.auth import get_current_user
from database.models import User

router = APIRouter(prefix="/api/v1/profiles", tags=["System Profiles"])

# ────────────────────────────────────────────────────────────────────────────────
# Pydantic Models
# ────────────────────────────────────────────────────────────────────────────────

class BlockConfig(BaseModel):
    """Configurazione dimensioni blocchi."""
    widths: List[int] = Field(..., description="Larghezze blocchi in mm [Grande, Medio, Piccolo]")
    heights: List[int] = Field(..., description="Altezze blocchi in mm [Grande, Medio, Piccolo]")

class MoralettiConfig(BaseModel):
    """Configurazione moraletti."""
    thickness: int = Field(..., description="Spessore moraletto in mm")
    height: int = Field(..., description="Altezza moraletto in mm")
    heightFromGround: int = Field(..., description="Altezza da terra (piedini) in mm")
    spacing: int = Field(..., description="Spaziatura tra moraletti in mm")
    countLarge: int = Field(..., description="Numero moraletti blocco grande")
    countMedium: int = Field(..., description="Numero moraletti blocco medio")
    countSmall: int = Field(..., description="Numero moraletti blocco piccolo")

class ProfileCreate(BaseModel):
    """Dati per creare un nuovo profilo."""
    name: str = Field(..., min_length=1, max_length=100, description="Nome profilo")
    description: Optional[str] = Field(None, description="Descrizione opzionale")
    block_config: BlockConfig
    moraletti_config: MoralettiConfig
    algorithm_type: str = Field('small', description="Tipo algoritmo: 'big' (industriale) o 'small' (residenziale)")
    is_default: bool = Field(False, description="Imposta come profilo predefinito")

class ProfileUpdate(BaseModel):
    """Dati per aggiornare un profilo esistente."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    block_config: Optional[BlockConfig] = None
    moraletti_config: Optional[MoralettiConfig] = None
    algorithm_type: Optional[str] = Field(None, description="Tipo algoritmo: 'big' o 'small'")
    is_default: Optional[bool] = None

class ProfileResponse(BaseModel):
    """Risposta con dati profilo."""
    id: int
    name: str
    description: Optional[str]
    block_config: BlockConfig
    moraletti_config: MoralettiConfig
    algorithm_type: str
    is_default: bool
    is_active: bool
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True

class ActivateProfileResponse(BaseModel):
    """Risposta per attivazione profilo con configurazioni."""
    profile_id: int
    profile_name: str
    block_config: BlockConfig
    moraletti_config: MoralettiConfig
    algorithm_type: str
    algorithm_description: str

# ────────────────────────────────────────────────────────────────────────────────
# Helper Functions
# ────────────────────────────────────────────────────────────────────────────────

def _get_algorithm_description(algorithm_type: str) -> str:
    """Restituisce la descrizione dell'algoritmo."""
    descriptions = {
        'big': 'Costruzione Industriale - sfalsamento blocchi',
        'small': 'Costruzione Residenziale - senza sfalsamento blocchi'
    }
    return descriptions.get(algorithm_type, 'Algoritmo sconosciuto')

def _serialize_profile(profile) -> ProfileResponse:
    """Converte un profilo DB in risposta API."""
    return ProfileResponse(
        id=profile.id,
        name=profile.name,
        description=profile.description,
        block_config=json.loads(profile.block_config),
        moraletti_config=json.loads(profile.moraletti_config),
        algorithm_type=getattr(profile, 'algorithm_type', 'small'),  # Default per retro-compatibilità
        is_default=profile.is_default,
        is_active=profile.is_active,
        created_at=profile.created_at.isoformat(),
        updated_at=profile.updated_at.isoformat() if profile.updated_at else profile.created_at.isoformat()
    )

# ────────────────────────────────────────────────────────────────────────────────
# Endpoints
# ────────────────────────────────────────────────────────────────────────────────

@router.get("", response_model=List[ProfileResponse])
async def list_profiles(current_user: User = Depends(get_current_user)):
    """
    Ottiene tutti i profili sistema dell'utente corrente.
    Al primo accesso, crea automaticamente un profilo "Default".
    """
    # Assicura che esista un profilo default
    ensure_default_profile(current_user.id)
    
    # Ottieni tutti i profili
    profiles = get_user_profiles(current_user.id)
    
    return [_serialize_profile(p) for p in profiles]

@router.get("/default", response_model=ProfileResponse)
async def get_user_default_profile(current_user: User = Depends(get_current_user)):
    """Ottiene il profilo predefinito dell'utente."""
    profile = get_default_profile(current_user.id)
    
    if not profile:
        # Crea profilo default se non esiste
        profile = ensure_default_profile(current_user.id)
    
    return _serialize_profile(profile)

@router.get("/{profile_id}", response_model=ProfileResponse)
async def get_profile(
    profile_id: int,
    current_user: User = Depends(get_current_user)
):
    """Ottiene un profilo specifico per ID."""
    profile = get_profile_by_id(profile_id, current_user.id)
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profilo non trovato"
        )
    
    return _serialize_profile(profile)

@router.post("", response_model=ProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_profile(
    profile_data: ProfileCreate,
    current_user: User = Depends(get_current_user)
):
    """Crea un nuovo profilo sistema."""
    try:
        profile = create_system_profile(
            user_id=current_user.id,
            name=profile_data.name,
            description=profile_data.description,
            block_config=json.dumps(profile_data.block_config.dict()),
            moraletti_config=json.dumps(profile_data.moraletti_config.dict()),
            algorithm_type=profile_data.algorithm_type,
            is_default=profile_data.is_default
        )
        
        return _serialize_profile(profile)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Errore durante la creazione del profilo: {str(e)}"
        )

@router.put("/{profile_id}", response_model=ProfileResponse)
async def update_profile(
    profile_id: int,
    profile_data: ProfileUpdate,
    current_user: User = Depends(get_current_user)
):
    """Aggiorna un profilo esistente."""
    # Verifica che il profilo esista e appartenga all'utente
    existing_profile = get_profile_by_id(profile_id, current_user.id)
    if not existing_profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profilo non trovato"
        )
    
    # Prepara i dati da aggiornare
    update_data = {}
    if profile_data.name is not None:
        update_data['name'] = profile_data.name
    if profile_data.description is not None:
        update_data['description'] = profile_data.description
    if profile_data.block_config is not None:
        update_data['block_config'] = json.dumps(profile_data.block_config.dict())
    if profile_data.moraletti_config is not None:
        update_data['moraletti_config'] = json.dumps(profile_data.moraletti_config.dict())
    if profile_data.algorithm_type is not None:
        update_data['algorithm_type'] = profile_data.algorithm_type
    if profile_data.is_default is not None:
        update_data['is_default'] = profile_data.is_default
    
    # Aggiorna
    updated_profile = update_system_profile(
        profile_id=profile_id,
        user_id=current_user.id,
        **update_data
    )
    
    if not updated_profile:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Errore durante l'aggiornamento del profilo"
        )
    
    return _serialize_profile(updated_profile)

@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_profile(
    profile_id: int,
    current_user: User = Depends(get_current_user)
):
    """Elimina un profilo sistema (soft delete)."""
    # Verifica che il profilo esista
    profile = get_profile_by_id(profile_id, current_user.id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profilo non trovato"
        )
    
    # Non permettere eliminazione del profilo default se è l'unico
    if profile.is_default:
        profiles = get_user_profiles(current_user.id)
        if len(profiles) == 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Non puoi eliminare l'unico profilo predefinito"
            )
    
    # Elimina
    success = delete_system_profile(profile_id, current_user.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Errore durante l'eliminazione del profilo"
        )
    
    return None

@router.post("/{profile_id}/activate", response_model=ActivateProfileResponse)
async def activate_profile(
    profile_id: int,
    current_user: User = Depends(get_current_user)
):
    """
    Attiva un profilo: restituisce le sue configurazioni
    per essere applicate al frontend (blocchi + moraletti + algoritmo).
    """
    profile = get_profile_by_id(profile_id, current_user.id)
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profilo non trovato"
        )
    
    algorithm_type = getattr(profile, 'algorithm_type', 'small')
    
    return ActivateProfileResponse(
        profile_id=profile.id,
        profile_name=profile.name,
        block_config=json.loads(profile.block_config),
        moraletti_config=json.loads(profile.moraletti_config),
        algorithm_type=algorithm_type,
        algorithm_description=_get_algorithm_description(algorithm_type)
    )

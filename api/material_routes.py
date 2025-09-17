"""
API Routes per Sistema Parametri Materiali
Endpoints REST per gestire materiali, guide e configurazioni progetti
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, Body
from pydantic import BaseModel
import json

from api.auth import get_current_active_user
from api.models import User
from database.material_services import (
    MaterialService, GuideService, ProjectMaterialConfigService, 
    MaterialCalculationService, MaterialTemplateService
)
from database.material_models import MaterialType, GuideType, WallPosition

# Router per le API materiali
materials_router = APIRouter(prefix="/api/v1/materials", tags=["materials"])

# ────────────────────────────────────────────────────────────────────────────────
# Pydantic Models per le API
# ────────────────────────────────────────────────────────────────────────────────

class MaterialResponse(BaseModel):
    id: int
    name: str
    type: str
    available_thicknesses: List[int]
    density_kg_m3: Optional[float]
    moisture_resistance: bool
    fire_class: Optional[str]
    supplier: Optional[str]
    notes: Optional[str]
    is_active: bool
    created_at: Optional[str]

class GuideResponse(BaseModel):
    id: int
    name: str
    type: str
    width_mm: int
    depth_mm: int
    max_load_kg: Optional[float]
    material_compatibility: List
    manufacturer: Optional[str]
    model_code: Optional[str]
    price_per_meter: Optional[float]
    is_active: bool
    created_at: Optional[str]

class ProjectConfigRequest(BaseModel):
    project_name: str
    material_id: int
    material_thickness_mm: int
    guide_id: int
    wall_position: str = "libera"  # libera, appoggiata_un_lato, etc.
    ceiling_height_mm: Optional[int] = None
    existing_walls_sides: Optional[List[str]] = None

class ProjectConfigResponse(BaseModel):
    id: int
    user_id: int
    project_name: str
    material: Optional[MaterialResponse]
    material_thickness_mm: int
    guide: Optional[GuideResponse]
    closure_thickness_mm: int
    wall_position: str
    ceiling_height_mm: Optional[int]
    existing_walls_sides: List[str]
    special_modules_config: Optional[dict]
    created_at: Optional[str]
    updated_at: Optional[str]

class CalculationRequest(BaseModel):
    material_thickness_mm: int
    guide_width_mm: int
    wall_position: str = "libera"
    existing_walls_sides: Optional[List[str]] = None
    ceiling_height_mm: Optional[int] = None

class CalculationResponse(BaseModel):
    closure_thickness_mm: int
    mounting_strategy: dict
    moretti_parameters: Optional[dict]
    insertion_sequence: dict
    technical_notes: List[str]

# ────────────────────────────────────────────────────────────────────────────────
# Endpoints Materiali
# ────────────────────────────────────────────────────────────────────────────────

@materials_router.get("/", response_model=List[MaterialResponse])
async def get_all_materials(current_user: User = Depends(get_current_active_user)):
    """Restituisce tutti i materiali disponibili."""
    try:
        materials = MaterialService.get_all_materials()
        return materials
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore recupero materiali: {str(e)}")

@materials_router.get("/types")
async def get_material_types(current_user: User = Depends(get_current_active_user)):
    """Restituisce i tipi di materiale disponibili."""
    return {
        "types": [
            {"value": "truciolato", "label": "Truciolato"},
            {"value": "mdf", "label": "MDF"},
            {"value": "compensato", "label": "Compensato"},
            {"value": "osb", "label": "OSB"},
            {"value": "altro", "label": "Altro"}
        ]
    }

@materials_router.get("/{material_id}", response_model=MaterialResponse)
async def get_material_by_id(
    material_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """Restituisce un materiale specifico per ID."""
    try:
        material = MaterialService.get_material_by_id(material_id)
        if not material:
            raise HTTPException(status_code=404, detail="Materiale non trovato")
        return material
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore recupero materiale: {str(e)}")

@materials_router.get("/type/{material_type}", response_model=List[MaterialResponse])
async def get_materials_by_type(
    material_type: str,
    current_user: User = Depends(get_current_active_user)
):
    """Restituisce materiali per tipo."""
    try:
        # Converte stringa in enum
        mat_type = MaterialType(material_type.lower())
        materials = MaterialService.get_materials_by_type(mat_type)
        return materials
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Tipo materiale non valido: {material_type}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore recupero materiali: {str(e)}")

# ────────────────────────────────────────────────────────────────────────────────
# Endpoints Guide
# ────────────────────────────────────────────────────────────────────────────────

@materials_router.get("/guides/", response_model=List[GuideResponse])
async def get_all_guides(current_user: User = Depends(get_current_active_user)):
    """Restituisce tutte le guide disponibili."""
    try:
        guides = GuideService.get_all_guides()
        return guides
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore recupero guide: {str(e)}")

@materials_router.get("/guides/types")
async def get_guide_types(current_user: User = Depends(get_current_active_user)):
    """Restituisce i tipi di guida disponibili."""
    return {
        "types": [
            {"value": "50mm", "label": "Guide 50mm", "width": 50},
            {"value": "75mm", "label": "Guide 75mm", "width": 75},
            {"value": "100mm", "label": "Guide 100mm", "width": 100}
        ]
    }

@materials_router.get("/guides/{guide_id}", response_model=GuideResponse)
async def get_guide_by_id(
    guide_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """Restituisce una guida specifica per ID."""
    try:
        guide = GuideService.get_guide_by_id(guide_id)
        if not guide:
            raise HTTPException(status_code=404, detail="Guida non trovata")
        return guide
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore recupero guida: {str(e)}")

@materials_router.get("/guides/type/{guide_type}", response_model=List[GuideResponse])
async def get_guides_by_type(
    guide_type: str,
    current_user: User = Depends(get_current_active_user)
):
    """Restituisce guide per tipo."""
    try:
        # Converte stringa in enum
        g_type = GuideType(guide_type.lower())
        guides = GuideService.get_guides_by_type(g_type)
        return guides
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Tipo guida non valido: {guide_type}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore recupero guide: {str(e)}")

# ────────────────────────────────────────────────────────────────────────────────
# Endpoints Configurazioni Progetto
# ────────────────────────────────────────────────────────────────────────────────

@materials_router.post("/configs/", response_model=ProjectConfigResponse)
async def create_project_config(
    config_request: ProjectConfigRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Crea una nuova configurazione materiali per un progetto."""
    try:
        # Converte wall_position in enum
        wall_pos = WallPosition(config_request.wall_position.lower())
        
        # Crea configurazione
        config = ProjectMaterialConfigService.create_project_config(
            user_id=current_user.id,
            project_name=config_request.project_name,
            material_id=config_request.material_id,
            material_thickness_mm=config_request.material_thickness_mm,
            guide_id=config_request.guide_id,
            wall_position=wall_pos,
            ceiling_height_mm=config_request.ceiling_height_mm,
            existing_walls_sides=config_request.existing_walls_sides
        )
        
        return config
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore creazione configurazione: {str(e)}")

@materials_router.get("/configs/", response_model=List[ProjectConfigResponse])
async def get_user_project_configs(current_user: User = Depends(get_current_active_user)):
    """Restituisce tutte le configurazioni dell'utente corrente."""
    try:
        configs = ProjectMaterialConfigService.get_user_project_configs(current_user.id)
        return configs
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore recupero configurazioni: {str(e)}")

@materials_router.get("/configs/{project_name}", response_model=ProjectConfigResponse)
async def get_project_config(
    project_name: str,
    current_user: User = Depends(get_current_active_user)
):
    """Restituisce la configurazione di un progetto specifico."""
    try:
        config = ProjectMaterialConfigService.get_project_config(current_user.id, project_name)
        if not config:
            raise HTTPException(status_code=404, detail="Configurazione progetto non trovata")
        return config
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore recupero configurazione: {str(e)}")

# ────────────────────────────────────────────────────────────────────────────────
# Endpoints Calcoli
# ────────────────────────────────────────────────────────────────────────────────

@materials_router.post("/calculate", response_model=CalculationResponse)
async def calculate_project_parameters(
    calc_request: CalculationRequest,
    current_user: User = Depends(get_current_active_user)
):
    """
    Calcola tutti i parametri tecnici per una configurazione.
    Implementa la logica descritta nel documento: spessore + guide = chiusura.
    """
    try:
        # Converte wall_position in enum
        wall_pos = WallPosition(calc_request.wall_position.lower())
        
        # Calcola parametri
        parameters = MaterialCalculationService.calculate_project_parameters(
            material_thickness_mm=calc_request.material_thickness_mm,
            guide_width_mm=calc_request.guide_width_mm,
            wall_position=wall_pos,
            existing_walls_sides=calc_request.existing_walls_sides or [],
            ceiling_height_mm=calc_request.ceiling_height_mm
        )
        
        return parameters
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore calcolo parametri: {str(e)}")

@materials_router.post("/calculate/closure")
async def calculate_closure_thickness(
    material_thickness: int = Body(..., embed=True),
    guide_width: int = Body(..., embed=True),
    current_user: User = Depends(get_current_active_user)
):
    """
    Calcolo semplice spessore chiusura.
    Implementa l'esempio del documento: 14mm + 75mm = 103mm.
    """
    try:
        closure_thickness = ProjectMaterialConfigService.calculate_closure_thickness(
            material_thickness, guide_width
        )
        
        return {
            "material_thickness_mm": material_thickness,
            "guide_width_mm": guide_width,
            "closure_thickness_mm": closure_thickness,
            "calculation": f"{material_thickness}mm + {guide_width}mm = {closure_thickness}mm",
            "example": "Esempio: 14mm (truciolato) + 75mm (guide) = 103mm (chiusura)"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore calcolo chiusura: {str(e)}")

@materials_router.post("/validate")
async def validate_material_guide_combination(
    material_id: int = Body(..., embed=True),
    guide_id: int = Body(..., embed=True), 
    thickness_mm: int = Body(..., embed=True),
    current_user: User = Depends(get_current_active_user)
):
    """Valida una combinazione materiale + guida + spessore."""
    try:
        is_valid, message = ProjectMaterialConfigService.validate_material_guide_combination(
            material_id, guide_id, thickness_mm
        )
        
        return {
            "valid": is_valid,
            "message": message,
            "material_id": material_id,
            "guide_id": guide_id,
            "thickness_mm": thickness_mm
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore validazione: {str(e)}")

# ────────────────────────────────────────────────────────────────────────────────
# Endpoints Template
# ────────────────────────────────────────────────────────────────────────────────

@materials_router.get("/templates/", response_model=List[dict])
async def get_all_templates(current_user: User = Depends(get_current_active_user)):
    """Restituisce tutti i template pubblici."""
    try:
        templates = MaterialTemplateService.get_all_templates()
        return templates
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore recupero template: {str(e)}")

@materials_router.get("/templates/user", response_model=List[dict])
async def get_user_templates(current_user: User = Depends(get_current_active_user)):
    """Restituisce i template dell'utente corrente."""
    try:
        templates = MaterialTemplateService.get_user_templates(current_user.id)
        return templates
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore recupero template utente: {str(e)}")

# ────────────────────────────────────────────────────────────────────────────────
# Endpoints Utilità
# ────────────────────────────────────────────────────────────────────────────────

@materials_router.get("/wall-positions")
async def get_wall_positions(current_user: User = Depends(get_current_active_user)):
    """Restituisce le posizioni parete disponibili."""
    return {
        "positions": [
            {
                "value": "libera",
                "label": "Parete Libera",
                "description": "Parete completamente indipendente"
            },
            {
                "value": "appoggiata_un_lato", 
                "label": "Appoggiata a Un Lato",
                "description": "Parete appoggiata a un muro esistente"
            },
            {
                "value": "appoggiata_due_lati",
                "label": "Appoggiata a Due Lati", 
                "description": "Parete tra due muri esistenti"
            },
            {
                "value": "incassata",
                "label": "Incassata",
                "description": "Parete completamente incassata"
            }
        ]
    }

@materials_router.get("/wall-sides")
async def get_wall_sides(current_user: User = Depends(get_current_active_user)):
    """Restituisce i lati parete disponibili."""
    return {
        "sides": [
            {"value": "left", "label": "Lato Sinistro"},
            {"value": "right", "label": "Lato Destro"}, 
            {"value": "top", "label": "Lato Superiore"},
            {"value": "bottom", "label": "Lato Inferiore"}
        ]
    }

@materials_router.get("/system/info")
async def get_system_info(current_user: User = Depends(get_current_active_user)):
    """Restituisce informazioni sul sistema parametri materiali."""
    try:
        materials = MaterialService.get_all_materials()
        guides = GuideService.get_all_guides()
        templates = MaterialTemplateService.get_all_templates()
        
        return {
            "system": "Parametri Materiali Wall-Build",
            "version": "1.0.0",
            "statistics": {
                "materials_count": len(materials),
                "guides_count": len(guides),
                "templates_count": len(templates)
            },
            "features": [
                "Calcolo automatico spessore chiusura",
                "Validazione combinazioni materiale/guida",
                "Strategia montaggio basata su posizione parete",
                "Calcolo parametri moretti per pareti non a soffitto",
                "Template predefiniti per progetti comuni"
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore recupero info sistema: {str(e)}")
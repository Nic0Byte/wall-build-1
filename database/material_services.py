"""
Servizi per la gestione dei parametri materiali
Logica di business per materiali, guide e configurazioni progetti
"""

from typing import List, Dict, Optional, Tuple
import json
from sqlalchemy.orm import Session
from datetime import datetime

from database.material_models import (
    Material, Guide, ProjectMaterialConfig, MaterialRule, ProjectTemplate,
    MaterialType, GuideType, WallPosition
)
from database.config import get_db_session

class MaterialService:
    """Servizio per la gestione dei materiali."""
    
    @staticmethod
    def get_all_materials() -> List[Dict]:
        """Restituisce tutti i materiali attivi."""
        with get_db_session() as db:
            materials = db.query(Material).filter(Material.is_active == True).all()
            return [MaterialService._material_to_dict(m) for m in materials]
    
    @staticmethod
    def get_material_by_id(material_id: int) -> Optional[Dict]:
        """Restituisce un materiale per ID."""
        with get_db_session() as db:
            material = db.query(Material).filter(
                Material.id == material_id,
                Material.is_active == True
            ).first()
            return MaterialService._material_to_dict(material) if material else None
    
    @staticmethod
    def get_materials_by_type(material_type: MaterialType) -> List[Dict]:
        """Restituisce materiali per tipo."""
        with get_db_session() as db:
            materials = db.query(Material).filter(
                Material.type == material_type,
                Material.is_active == True
            ).all()
            return [MaterialService._material_to_dict(m) for m in materials]
    
    @staticmethod
    def create_material(name: str, material_type: MaterialType, available_thicknesses: List[int], 
                       density_kg_m3: Optional[float] = None, **kwargs) -> Dict:
        """Crea un nuovo materiale."""
        with get_db_session() as db:
            material = Material(
                name=name,
                type=material_type,
                available_thicknesses=json.dumps(available_thicknesses),
                density_kg_m3=density_kg_m3,
                **kwargs
            )
            db.add(material)
            db.commit()
            db.refresh(material)
            return MaterialService._material_to_dict(material)
    
    @staticmethod
    def _material_to_dict(material: Material) -> Dict:
        """Converte un materiale in dizionario."""
        if not material:
            return {}
        
        try:
            thicknesses = json.loads(material.available_thicknesses)
        except:
            thicknesses = []
        
        return {
            "id": material.id,
            "name": material.name,
            "type": material.type.value,
            "available_thicknesses": thicknesses,
            "density_kg_m3": material.density_kg_m3,
            "moisture_resistance": material.moisture_resistance,
            "fire_class": material.fire_class,
            "supplier": material.supplier,
            "notes": material.notes,
            "is_active": material.is_active,
            "created_at": material.created_at.isoformat() if material.created_at else None
        }

class GuideService:
    """Servizio per la gestione delle guide."""
    
    @staticmethod
    def get_all_guides() -> List[Dict]:
        """Restituisce tutte le guide attive."""
        with get_db_session() as db:
            guides = db.query(Guide).filter(Guide.is_active == True).all()
            return [GuideService._guide_to_dict(g) for g in guides]
    
    @staticmethod
    def get_guide_by_id(guide_id: int) -> Optional[Dict]:
        """Restituisce una guida per ID."""
        with get_db_session() as db:
            guide = db.query(Guide).filter(
                Guide.id == guide_id,
                Guide.is_active == True
            ).first()
            return GuideService._guide_to_dict(guide) if guide else None
    
    @staticmethod
    def get_guides_by_type(guide_type: GuideType) -> List[Dict]:
        """Restituisce guide per tipo."""
        with get_db_session() as db:
            guides = db.query(Guide).filter(
                Guide.type == guide_type,
                Guide.is_active == True
            ).all()
            return [GuideService._guide_to_dict(g) for g in guides]
    
    @staticmethod
    def create_guide(name: str, guide_type: GuideType, width_mm: int, depth_mm: int, 
                    max_load_kg: Optional[float] = None, **kwargs) -> Dict:
        """Crea una nuova guida."""
        with get_db_session() as db:
            guide = Guide(
                name=name,
                type=guide_type,
                width_mm=width_mm,
                depth_mm=depth_mm,
                max_load_kg=max_load_kg,
                **kwargs
            )
            db.add(guide)
            db.commit()
            db.refresh(guide)
            return GuideService._guide_to_dict(guide)
    
    @staticmethod
    def _guide_to_dict(guide: Guide) -> Dict:
        """Converte una guida in dizionario."""
        if not guide:
            return {}
        
        try:
            compatibility = json.loads(guide.material_compatibility) if guide.material_compatibility else []
        except:
            compatibility = []
        
        return {
            "id": guide.id,
            "name": guide.name,
            "type": guide.type.value,
            "width_mm": guide.width_mm,
            "depth_mm": guide.depth_mm,
            "max_load_kg": guide.max_load_kg,
            "material_compatibility": compatibility,
            "manufacturer": guide.manufacturer,
            "model_code": guide.model_code,
            "price_per_meter": guide.price_per_meter,
            "is_active": guide.is_active,
            "created_at": guide.created_at.isoformat() if guide.created_at else None
        }

class ProjectMaterialConfigService:
    """Servizio per la gestione delle configurazioni materiali di progetto."""
    
    @staticmethod
    def create_project_config(user_id: int, project_name: str, material_id: int, 
                             material_thickness_mm: int, guide_id: int, 
                             wall_position: WallPosition = WallPosition.LIBERA,
                             ceiling_height_mm: Optional[int] = None,
                             existing_walls_sides: Optional[List[str]] = None) -> Dict:
        """Crea una nuova configurazione di progetto."""
        with get_db_session() as db:
            # Verifica che materiale e guida esistano
            material = db.query(Material).filter(Material.id == material_id).first()
            guide = db.query(Guide).filter(Guide.id == guide_id).first()
            
            if not material or not guide:
                raise ValueError("Materiale o guida non trovati")
            
            # Verifica che lo spessore sia disponibile per il materiale
            available_thicknesses = json.loads(material.available_thicknesses)
            if material_thickness_mm not in available_thicknesses:
                raise ValueError(f"Spessore {material_thickness_mm}mm non disponibile per {material.name}")
            
            config = ProjectMaterialConfig(
                user_id=user_id,
                project_name=project_name,
                material_id=material_id,
                material_thickness_mm=material_thickness_mm,
                guide_id=guide_id,
                wall_position=wall_position,
                ceiling_height_mm=ceiling_height_mm
            )
            
            # Imposta lati con muri esistenti
            if existing_walls_sides:
                config.set_existing_walls_list(existing_walls_sides)
            
            # Calcola automaticamente lo spessore di chiusura
            config.closure_thickness_mm = material_thickness_mm + guide.width_mm
            
            db.add(config)
            db.commit()
            db.refresh(config)
            
            return ProjectMaterialConfigService._config_to_dict(config)
    
    @staticmethod
    def get_project_config(user_id: int, project_name: str) -> Optional[Dict]:
        """Restituisce la configurazione di un progetto."""
        with get_db_session() as db:
            config = db.query(ProjectMaterialConfig).filter(
                ProjectMaterialConfig.user_id == user_id,
                ProjectMaterialConfig.project_name == project_name,
                ProjectMaterialConfig.is_active == True
            ).first()
            return ProjectMaterialConfigService._config_to_dict(config) if config else None
    
    @staticmethod
    def get_user_project_configs(user_id: int) -> List[Dict]:
        """Restituisce tutte le configurazioni di un utente."""
        with get_db_session() as db:
            configs = db.query(ProjectMaterialConfig).filter(
                ProjectMaterialConfig.user_id == user_id,
                ProjectMaterialConfig.is_active == True
            ).order_by(ProjectMaterialConfig.updated_at.desc()).all()
            return [ProjectMaterialConfigService._config_to_dict(c) for c in configs]
    
    @staticmethod
    def calculate_closure_thickness(material_thickness_mm: int, guide_width_mm: int) -> int:
        """Calcola lo spessore di chiusura: materiale + guida + materiale."""
        return (material_thickness_mm * 2) + guide_width_mm
    
    @staticmethod
    def validate_material_guide_combination(material_id: int, guide_id: int, 
                                          thickness_mm: int) -> Tuple[bool, Optional[str]]:
        """Valida una combinazione materiale + guida + spessore."""
        with get_db_session() as db:
            # Controlla se esiste una regola specifica
            rule = db.query(MaterialRule).filter(
                MaterialRule.material_id == material_id,
                MaterialRule.guide_id == guide_id,
                MaterialRule.is_active == True
            ).first()
            
            if rule:
                if not rule.is_compatible:
                    return False, "Combinazione materiale/guida non compatibile"
                
                if rule.min_thickness_mm and thickness_mm < rule.min_thickness_mm:
                    return False, f"Spessore minimo richiesto: {rule.min_thickness_mm}mm"
                
                if rule.max_thickness_mm and thickness_mm > rule.max_thickness_mm:
                    return False, f"Spessore massimo consentito: {rule.max_thickness_mm}mm"
                
                if rule.warning_message:
                    return True, rule.warning_message
            
            return True, None
    
    @staticmethod
    def _config_to_dict(config: ProjectMaterialConfig) -> Dict:
        """Converte una configurazione in dizionario."""
        if not config:
            return {}
        
        return {
            "id": config.id,
            "user_id": config.user_id,
            "project_name": config.project_name,
            "material": MaterialService._material_to_dict(config.material) if config.material else None,
            "material_thickness_mm": config.material_thickness_mm,
            "guide": GuideService._guide_to_dict(config.guide) if config.guide else None,
            "closure_thickness_mm": config.closure_thickness_mm,
            "wall_position": config.wall_position.value,
            "ceiling_height_mm": config.ceiling_height_mm,
            "existing_walls_sides": config.get_existing_walls_list(),
            "special_modules_config": json.loads(config.special_modules_config) if config.special_modules_config else None,
            "created_at": config.created_at.isoformat() if config.created_at else None,
            "updated_at": config.updated_at.isoformat() if config.updated_at else None
        }

class MaterialCalculationService:
    """Servizio per i calcoli relativi ai materiali."""
    
    @staticmethod
    def calculate_project_parameters(material_thickness_mm: int, guide_width_mm: int, 
                                   wall_position: WallPosition, existing_walls_sides: List[str],
                                   ceiling_height_mm: Optional[int] = None) -> Dict:
        """
        Calcola tutti i parametri tecnici per un progetto.
        Implementa la logica descritta nel documento.
        """
        # Calcolo base: spessore chiusura
        closure_thickness_mm = material_thickness_mm + guide_width_mm
        
        # Esempio dal documento: 14mm + 75mm = 103mm
        print(f"🔧 Calcolo: {material_thickness_mm}mm (materiale) + {guide_width_mm}mm (guide) = {closure_thickness_mm}mm (chiusura)")
        
        # Determina strategia di montaggio basata sulla posizione
        mounting_strategy = MaterialCalculationService._determine_mounting_strategy(wall_position, existing_walls_sides)
        
        # Calcola parametri moretti se parete non va a soffitto
        moretti_params = None
        if ceiling_height_mm:
            moretti_params = MaterialCalculationService._calculate_moretti_parameters(
                ceiling_height_mm, closure_thickness_mm
            )
        
        # Calcola sequenza di inserimento moduli
        insertion_sequence = MaterialCalculationService._calculate_insertion_sequence(
            wall_position, existing_walls_sides
        )
        
        return {
            "closure_thickness_mm": closure_thickness_mm,
            "mounting_strategy": mounting_strategy,
            "moretti_parameters": moretti_params,
            "insertion_sequence": insertion_sequence,
            "technical_notes": MaterialCalculationService._generate_technical_notes(
                material_thickness_mm, guide_width_mm, wall_position, existing_walls_sides
            )
        }
    
    @staticmethod
    def _determine_mounting_strategy(wall_position: WallPosition, existing_walls_sides: List[str]) -> Dict:
        """Determina la strategia di montaggio basata sulla posizione della parete."""
        strategy = {
            "type": wall_position.value,
            "start_from_existing_wall": False,
            "anchor_points": [],
            "sequence_priority": []
        }
        
        if wall_position in [WallPosition.APPOGGIATA_UN_LATO, WallPosition.APPOGGIATA_DUE_LATI]:
            strategy["start_from_existing_wall"] = True
            strategy["anchor_points"] = existing_walls_sides.copy()
            
            # Priorità: inizia sempre dai lati fissi
            if "bottom" in existing_walls_sides:
                strategy["sequence_priority"].append("bottom_to_top")
            if "left" in existing_walls_sides:
                strategy["sequence_priority"].append("left_to_right")
            if "right" in existing_walls_sides:
                strategy["sequence_priority"].append("right_to_left")
        
        elif wall_position == WallPosition.INCASSATA:
            strategy["start_from_existing_wall"] = True
            strategy["anchor_points"] = ["bottom", "left", "right"]  # Tutti i lati fissi
            strategy["sequence_priority"] = ["bottom_to_top", "left_to_right"]
        
        else:  # LIBERA
            strategy["start_from_existing_wall"] = False
            strategy["sequence_priority"] = ["optimal_packing"]  # Usa algoritmo standard
        
        return strategy
    
    @staticmethod
    def _calculate_moretti_parameters(ceiling_height_mm: int, closure_thickness_mm: int) -> Dict:
        """Calcola parametri per i moretti quando la parete non arriva al soffitto."""
        # Altezza standard blocchi (dal sistema esistente)
        standard_block_height = 495  # mm
        
        # Calcola quante righe di blocchi entrano
        complete_rows = ceiling_height_mm // standard_block_height
        remaining_height = ceiling_height_mm % standard_block_height
        
        # Parametri moretti
        moretti_needed = remaining_height < standard_block_height and remaining_height > 50
        
        moretti_params = {
            "needed": moretti_needed,
            "height_mm": remaining_height if moretti_needed else 0,
            "thickness_mm": closure_thickness_mm,  # Stesso spessore della chiusura
            "position": "top",  # Sempre in alto
            "complete_block_rows": complete_rows,
            "remaining_space_mm": remaining_height
        }
        
        return moretti_params
    
    @staticmethod
    def _calculate_insertion_sequence(wall_position: WallPosition, existing_walls_sides: List[str]) -> Dict:
        """Calcola la sequenza ottimale di inserimento dei moduli."""
        sequence = {
            "start_point": "auto",
            "direction": "auto",
            "special_instructions": []
        }
        
        if wall_position == WallPosition.APPOGGIATA_UN_LATO:
            if "left" in existing_walls_sides:
                sequence["start_point"] = "left_wall"
                sequence["direction"] = "left_to_right"
            elif "right" in existing_walls_sides:
                sequence["start_point"] = "right_wall"  
                sequence["direction"] = "right_to_left"
            elif "bottom" in existing_walls_sides:
                sequence["start_point"] = "bottom_wall"
                sequence["direction"] = "bottom_to_top"
            
            sequence["special_instructions"].append("Iniziare sempre dalla parete esistente per garantire l'ancoraggio")
        
        elif wall_position == WallPosition.APPOGGIATA_DUE_LATI:
            sequence["start_point"] = "corner"
            sequence["direction"] = "corner_outward"
            sequence["special_instructions"].append("Iniziare dall'angolo tra le due pareti esistenti")
        
        elif wall_position == WallPosition.INCASSATA:
            sequence["start_point"] = "bottom_left_corner"
            sequence["direction"] = "systematic_fill"
            sequence["special_instructions"].append("Riempimento sistematico dal basso verso l'alto, da sinistra a destra")
        
        else:  # LIBERA
            sequence["start_point"] = "optimal"
            sequence["direction"] = "algorithm_optimized"
            sequence["special_instructions"].append("Usa algoritmo di packing ottimizzato")
        
        return sequence
    
    @staticmethod
    def _generate_technical_notes(material_thickness_mm: int, guide_width_mm: int, 
                                wall_position: WallPosition, existing_walls_sides: List[str]) -> List[str]:
        """Genera note tecniche per la configurazione."""
        notes = []
        
        # Nota sul calcolo spessore
        closure_mm = material_thickness_mm + guide_width_mm
        notes.append(f"Spessore chiusura: {material_thickness_mm}mm (materiale) + {guide_width_mm}mm (guide) = {closure_mm}mm")
        
        # Note sulla posizione
        if wall_position != WallPosition.LIBERA:
            notes.append("La parete è vincolata a muri esistenti - seguire la sequenza di montaggio suggerita")
            
            if existing_walls_sides:
                sides_str = ", ".join(existing_walls_sides)
                notes.append(f"Lati con muri esistenti: {sides_str}")
        
        # Avvertimenti specifici
        if guide_width_mm >= material_thickness_mm * 3:
            notes.append("⚠️ Le guide sono molto più larghe del materiale - verificare stabilità")
        
        if closure_mm > 120:
            notes.append("⚠️ Spessore chiusura elevato - considerare l'impatto estetico")
        
        return notes

class MaterialTemplateService:
    """Servizio per la gestione dei template di progetto."""
    
    @staticmethod
    def get_all_templates() -> List[Dict]:
        """Restituisce tutti i template pubblici."""
        with get_db_session() as db:
            templates = db.query(ProjectTemplate).filter(
                ProjectTemplate.is_active == True,
                ProjectTemplate.is_public == True
            ).order_by(ProjectTemplate.usage_count.desc()).all()
            return [MaterialTemplateService._template_to_dict(t) for t in templates]
    
    @staticmethod
    def get_user_templates(user_id: int) -> List[Dict]:
        """Restituisce i template di un utente specifico."""
        with get_db_session() as db:
            templates = db.query(ProjectTemplate).filter(
                ProjectTemplate.created_by_user_id == user_id,
                ProjectTemplate.is_active == True
            ).order_by(ProjectTemplate.created_at.desc()).all()
            return [MaterialTemplateService._template_to_dict(t) for t in templates]
    
    @staticmethod
    def create_default_templates():
        """Crea i template predefiniti del sistema."""
        with get_db_session() as db:
            templates = [
                {
                    "name": "Parete Bagno Standard",
                    "description": "Configurazione tipica per pareti bagno - resistente all'umidità",
                    "default_material_type": MaterialType.MDF,
                    "default_thickness_mm": 18,
                    "default_guide_type": GuideType.GUIDE_75MM,
                    "default_wall_position": WallPosition.APPOGGIATA_UN_LATO,
                    "category": "bagno"
                },
                {
                    "name": "Divisorio Ufficio",
                    "description": "Parete divisoria per uffici - ottimizzata per acustica",
                    "default_material_type": MaterialType.TRUCIOLATO,
                    "default_thickness_mm": 25,
                    "default_guide_type": GuideType.GUIDE_100MM,
                    "default_wall_position": WallPosition.LIBERA,
                    "category": "ufficio"
                },
                {
                    "name": "Parete Cucina",
                    "description": "Parete cucina - materiali resistenti e facili da pulire",
                    "default_material_type": MaterialType.MDF,
                    "default_thickness_mm": 18,
                    "default_guide_type": GuideType.GUIDE_75MM,
                    "default_wall_position": WallPosition.APPOGGIATA_DUE_LATI,
                    "category": "cucina"
                }
            ]
            
            for template_data in templates:
                existing = db.query(ProjectTemplate).filter(
                    ProjectTemplate.name == template_data["name"]
                ).first()
                
                if not existing:
                    template = ProjectTemplate(
                        **template_data,
                        is_public=True,
                        created_by_user_id=None  # Template di sistema
                    )
                    db.add(template)
            
            db.commit()
    
    @staticmethod
    def _template_to_dict(template: ProjectTemplate) -> Dict:
        """Converte un template in dizionario."""
        if not template:
            return {}
        
        try:
            typical_dimensions = json.loads(template.typical_dimensions) if template.typical_dimensions else {}
        except:
            typical_dimensions = {}
        
        return {
            "id": template.id,
            "name": template.name,
            "description": template.description,
            "default_material_type": template.default_material_type.value,
            "default_thickness_mm": template.default_thickness_mm,
            "default_guide_type": template.default_guide_type.value,
            "default_wall_position": template.default_wall_position.value,
            "category": template.category,
            "typical_dimensions": typical_dimensions,
            "usage_count": template.usage_count,
            "is_public": template.is_public,
            "created_at": template.created_at.isoformat() if template.created_at else None
        }

# Funzione di inizializzazione per popolare i dati di base
def initialize_material_system():
    """Inizializza il sistema con materiali e guide di base."""
    
    # Crea materiali di base
    materials_data = [
        {
            "name": "Truciolato Standard",
            "type": MaterialType.TRUCIOLATO,
            "available_thicknesses": [10, 14, 18, 22, 25],
            "density_kg_m3": 650.0,
            "supplier": "Fornitore Standard"
        },
        {
            "name": "MDF Resistente Umidità",
            "type": MaterialType.MDF,
            "available_thicknesses": [12, 16, 18, 22],
            "density_kg_m3": 750.0,
            "moisture_resistance": True,
            "supplier": "Fornitore Premium"
        },
        {
            "name": "OSB Strutturale",
            "type": MaterialType.OSB,
            "available_thicknesses": [12, 15, 18, 22],
            "density_kg_m3": 600.0,
            "supplier": "Fornitore Strutturale"
        }
    ]
    
    # Crea guide di base
    guides_data = [
        {
            "name": "Guida Standard 50mm",
            "type": GuideType.GUIDE_50MM,
            "width_mm": 50,
            "depth_mm": 20,
            "max_load_kg": 25.0,
            "manufacturer": "Produttore A"
        },
        {
            "name": "Guida Media 75mm",
            "type": GuideType.GUIDE_75MM,
            "width_mm": 75,
            "depth_mm": 25,
            "max_load_kg": 40.0,
            "manufacturer": "Produttore A"
        },
        {
            "name": "Guida Pesante 100mm",
            "type": GuideType.GUIDE_100MM,
            "width_mm": 100,
            "depth_mm": 30,
            "max_load_kg": 60.0,
            "manufacturer": "Produttore B"
        }
    ]
    
    try:
        # Crea materiali
        for mat_data in materials_data:
            try:
                MaterialService.create_material(**mat_data)
                print(f"✅ Materiale creato: {mat_data['name']}")
            except Exception as e:
                print(f"⚠️ Materiale '{mat_data['name']}' già esistente o errore: {e}")
        
        # Crea guide
        for guide_data in guides_data:
            try:
                GuideService.create_guide(**guide_data)
                print(f"✅ Guida creata: {guide_data['name']}")
            except Exception as e:
                print(f"⚠️ Guida '{guide_data['name']}' già esistente o errore: {e}")
        
        # Crea template predefiniti
        MaterialTemplateService.create_default_templates()
        print("✅ Template predefiniti creati")
        
        print("🎉 Sistema parametri materiali inizializzato con successo!")
        
    except Exception as e:
        print(f"❌ Errore inizializzazione sistema materiali: {e}")
        raise
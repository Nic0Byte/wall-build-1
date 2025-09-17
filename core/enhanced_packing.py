"""
Integrazione Calcolo Automatico Misure con Sistema di Packing
Estende gli algoritmi di packing esistenti con calcoli automatici delle misure
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from typing import Dict, List, Tuple, Optional, Any
from shapely.geometry import Polygon
import json
import logging

# Import sistema calcolo misure
from core.auto_measurement import (
    AutoMeasurementCalculator,
    MaterialSpec,
    GuideSpec,
    CalculationResult,
    create_calculation_from_config,
    validate_project_measurements
)

# Import database per parametri materiali
try:
    from database.material_services import MaterialParameterService
    from database.material_models import WallPosition, MountingStrategy
except ImportError:
    # Fallback se non disponibile
    MaterialParameterService = None
    WallPosition = None
    MountingStrategy = None

logger = logging.getLogger(__name__)

class EnhancedPackingCalculator:
    """
    Estende il sistema di packing esistente con calcolo automatico delle misure.
    Integra le specifiche del documento italiano con gli algoritmi di ottimizzazione.
    """
    
    def __init__(self, material_service: Optional[Any] = None):
        self.measurement_calculator = AutoMeasurementCalculator()
        self.material_service = material_service or (MaterialParameterService() if MaterialParameterService else None)
        
        # Cache per evitare ricalcoli
        self._calculation_cache = {}
        
    def calculate_enhanced_packing_parameters(self, project_config: Dict, wall_polygon: Polygon) -> Dict:
        """
        Calcola parametri di packing potenziati con misure automatiche.
        
        Args:
            project_config: Configurazione progetto con parametri materiali
            wall_polygon: Poligono della parete da analizzare
            
        Returns:
            Dict con parametri calcolati per il packing
        """
        
        # Estrai dimensioni parete
        minx, miny, maxx, maxy = wall_polygon.bounds
        wall_dimensions = {
            "width_mm": maxx - minx,
            "height_mm": maxy - miny,
            "area_m2": wall_polygon.area / 1_000_000
        }
        
        # Ottieni parametri materiali (da database o config)
        material_params = self._get_material_parameters(project_config)
        
        # Calcola spessore chiusura automaticamente
        closure_calc = self._calculate_closure_dimensions(material_params)
        
        # Determina strategia di montaggio
        mounting_strategy = self._determine_mounting_strategy(project_config, wall_dimensions)
        
        # Calcola parametri moretti se necessari  
        moretti_params = self._calculate_moretti_requirements(wall_dimensions, closure_calc, project_config)
        
        # Calcola fabbisogno materiali
        material_requirements = self.measurement_calculator.calculate_material_requirements(
            wall_dimensions, 
            material_params["material_spec"],
            material_params["guide_spec"],
            moretti_params
        )
        
        # Genera parametri ottimizzati per packing
        packing_params = self._generate_packing_parameters(
            wall_dimensions,
            closure_calc,
            mounting_strategy,
            moretti_params,
            material_requirements
        )
        
        return {
            "wall_dimensions": wall_dimensions,
            "material_parameters": material_params,
            "closure_calculation": closure_calc,
            "mounting_strategy": mounting_strategy,
            "moretti_requirements": moretti_params,
            "material_requirements": material_requirements,
            "packing_parameters": packing_params,
            "technical_notes": self._generate_technical_notes(closure_calc, mounting_strategy, moretti_params),
            "validation": validate_project_measurements(project_config)
        }
    
    def enhance_existing_packing_result(self, packing_result: Dict, project_config: Dict) -> Dict:
        """
        Potenzia un risultato di packing esistente con calcoli automatici delle misure.
        
        Args:
            packing_result: Risultato del packing standard
            project_config: Configurazione progetto
            
        Returns:
            Risultato potenziato con misure automatiche
        """
        
        enhanced_result = packing_result.copy()
        
        # Aggiungi calcoli automatici
        if "wall_bounds" in packing_result:
            wall_bounds = packing_result["wall_bounds"]
            wall_polygon = self._reconstruct_wall_polygon(wall_bounds)
            
            enhanced_params = self.calculate_enhanced_packing_parameters(project_config, wall_polygon)
            enhanced_result["automatic_measurements"] = enhanced_params
            
            # Aggiungi informazioni sui blocchi con misure corrette
            enhanced_result["blocks_with_measurements"] = self._enhance_blocks_with_measurements(
                packing_result.get("blocks_standard", []),
                packing_result.get("blocks_custom", []),
                enhanced_params
            )
            
            # Calcola cutting list con misure automatiche
            enhanced_result["cutting_list"] = self._generate_enhanced_cutting_list(enhanced_params)
            
            # Aggiungi parametri produzione
            enhanced_result["production_parameters"] = self._generate_production_parameters(enhanced_params)
            
        return enhanced_result
    
    def calculate_wall_position_strategy(self, wall_config: Dict) -> Dict:
        """
        Implementa la logica: "iniziare ad inserire i moduli dalla parete che ha fissato"
        per pareti attaccate a pareti esistenti.
        """
        
        wall_position = wall_config.get("wall_position", "new")
        is_attached = wall_config.get("is_attached_to_existing", False)
        fixed_walls = wall_config.get("fixed_walls", [])
        
        strategy = {
            "starting_point": "left",  # Default
            "direction": "left_to_right",
            "mounting_sequence": [],
            "special_considerations": []
        }
        
        if is_attached and fixed_walls:
            # Logica per pareti attaccate - inizia dalla parete fissata
            primary_fixed_wall = fixed_walls[0] if fixed_walls else None
            
            if primary_fixed_wall:
                fixed_position = primary_fixed_wall.get("position", "left")
                
                if fixed_position == "left":
                    strategy["starting_point"] = "left"
                    strategy["direction"] = "left_to_right"
                    strategy["special_considerations"].append("Iniziare dalla parete fissata a sinistra")
                
                elif fixed_position == "right":  
                    strategy["starting_point"] = "right"
                    strategy["direction"] = "right_to_left"
                    strategy["special_considerations"].append("Iniziare dalla parete fissata a destra")
                
                elif fixed_position == "bottom":
                    strategy["starting_point"] = "bottom"
                    strategy["direction"] = "bottom_to_top"
                    strategy["special_considerations"].append("Iniziare dalla base fissata")
                
                strategy["mounting_sequence"].extend([
                    "1. Posizionare guide sulla parete fissata",
                    "2. Verificare allineamento e livello",
                    "3. Procedere con montaggio moduli in sequenza",
                    "4. Controllare collegamenti tra moduli"
                ])
        
        else:
            # Logica per pareti nuove
            strategy["special_considerations"].extend([
                "Parete non attaccata - montaggio libero",
                "Verificare stabilità strutturale", 
                "Considerare punti di ancoraggio aggiuntivi"
            ])
            
            strategy["mounting_sequence"].extend([
                "1. Installare guide perimetrali",
                "2. Verificare squadratura e livello",
                "3. Montare moduli dal centro verso l'esterno", 
                "4. Aggiungere rinforzi se necessario"
            ])
        
        return strategy
    
    def _get_material_parameters(self, config: Dict) -> Dict:
        """Ottiene parametri materiali da database o configurazione."""
        
        cache_key = f"{config.get('material_id', 'default')}_{config.get('guide_id', 'default')}"
        
        if cache_key in self._calculation_cache:
            return self._calculation_cache[cache_key]
        
        # Prova a ottenere da database
        if self.material_service:
            try:
                material_id = config.get("material_id")
                guide_id = config.get("guide_id")
                
                if material_id and guide_id:
                    material = self.material_service.get_material(material_id)
                    guide = self.material_service.get_guide(guide_id)
                    
                    if material and guide:
                        result = {
                            "material_spec": MaterialSpec(
                                thickness_mm=material.thickness_mm,
                                density_kg_m3=material.density_kg_m3,
                                strength_factor=material.strength_factor or 1.0
                            ),
                            "guide_spec": GuideSpec(
                                width_mm=guide.width_mm,
                                depth_mm=guide.depth_mm,
                                max_load_kg=guide.max_load_kg,
                                type=f"{guide.width_mm}mm"
                            ),
                            "source": "database"
                        }
                        
                        self._calculation_cache[cache_key] = result
                        return result
            except Exception as e:
                logger.warning(f"Errore accesso database materiali: {e}")
        
        # Fallback a parametri da configurazione
        result = {
            "material_spec": MaterialSpec(
                thickness_mm=config.get("material_thickness_mm", 18),
                density_kg_m3=config.get("material_density_kg_m3", 650.0),
                strength_factor=config.get("material_strength_factor", 1.0)
            ),
            "guide_spec": GuideSpec(
                width_mm=config.get("guide_width_mm", 75),
                depth_mm=config.get("guide_depth_mm", 25),
                max_load_kg=config.get("guide_max_load_kg", 40.0),
                type=config.get("guide_type", "75mm")
            ),
            "source": "config"
        }
        
        self._calculation_cache[cache_key] = result
        return result
    
    def _calculate_closure_dimensions(self, material_params: Dict) -> CalculationResult:
        """Calcola dimensioni chiusura con formula automatica."""
        
        return self.measurement_calculator.calculate_closure_thickness(
            material_params["material_spec"],
            material_params["guide_spec"]
        )
    
    def _determine_mounting_strategy(self, config: Dict, wall_dimensions: Dict) -> Dict:
        """Determina strategia di montaggio basata su configurazione parete."""
        
        wall_height = wall_dimensions["height_mm"]
        wall_width = wall_dimensions["width_mm"]
        
        # Strategia base
        strategy = {
            "type": "standard",
            "starting_point": config.get("starting_point", "left"),
            "requires_reinforcement": wall_height > 3000,
            "mounting_sequence": [],
            "special_notes": []
        }
        
        # Logica per pareti attaccate 
        if config.get("is_attached_to_existing"):
            strategy.update(self.calculate_wall_position_strategy(config))
            strategy["type"] = "attached"
        
        # Considerazioni altezza
        if wall_height > 3000:
            strategy["special_notes"].append("Parete alta - verificare stabilità")
            strategy["mounting_sequence"].append("Aggiungere rinforzi intermedi")
        
        # Considerazioni larghezza
        if wall_width > 5000:
            strategy["special_notes"].append("Parete larga - considerare giunti di dilatazione")
            strategy["mounting_sequence"].append("Pianificare giunti ogni 4-5m")
        
        return strategy
    
    def _calculate_moretti_requirements(self, wall_dimensions: Dict, closure_calc: CalculationResult,
                                      config: Dict) -> Optional[Dict]:
        """Calcola requisiti moretti per pareti che non arrivano al soffitto."""
        
        ceiling_height = config.get("ceiling_height_mm", self.measurement_calculator.standard_ceiling_height_mm)
        wall_height = wall_dimensions["height_mm"]
        block_height = config.get("block_height_mm", self.measurement_calculator.standard_block_height_mm)
        
        # Calcola righe complete
        complete_rows = int(wall_height / block_height)
        
        return self.measurement_calculator.calculate_moretti_dimensions(
            ceiling_height, 
            closure_calc.closure_thickness_mm,
            complete_rows
        )
    
    def _generate_packing_parameters(self, wall_dimensions: Dict, closure_calc: CalculationResult,
                                   mounting_strategy: Dict, moretti_params: Optional[Dict],
                                   material_requirements: Dict) -> Dict:
        """Genera parametri ottimizzati per algoritmo di packing."""
        
        return {
            "enhanced_block_height": closure_calc.closure_thickness_mm,  # Usa spessore calcolato
            "wall_thickness_mm": closure_calc.closure_thickness_mm,
            "starting_position": mounting_strategy.get("starting_point", "left"),
            "row_direction": mounting_strategy.get("direction", "left_to_right"),
            "requires_moretti": moretti_params.get("needed", False) if moretti_params else False,
            "moretti_height_mm": moretti_params.get("height_mm", 0) if moretti_params else 0,
            "material_efficiency": material_requirements["cost_estimate"].get("efficiency_percent", 85),
            "special_handling": len(mounting_strategy.get("special_considerations", [])) > 0
        }
    
    def _enhance_blocks_with_measurements(self, standard_blocks: List[Dict], custom_blocks: List[Dict],
                                        enhanced_params: Dict) -> Dict:
        """Potenzia blocchi con misure automatiche."""
        
        closure_thickness = enhanced_params["closure_calculation"].closure_thickness_mm
        
        enhanced_standard = []
        for block in standard_blocks:
            enhanced_block = block.copy()
            enhanced_block["thickness_mm"] = closure_thickness
            enhanced_block["volume_m3"] = (
                block.get("width", 0) * 
                block.get("height", 0) * 
                closure_thickness
            ) / 1_000_000_000
            enhanced_standard.append(enhanced_block)
        
        enhanced_custom = []
        for block in custom_blocks:
            enhanced_block = block.copy()  
            enhanced_block["thickness_mm"] = closure_thickness
            enhanced_block["volume_m3"] = (
                block.get("width", 0) * 
                block.get("height", 0) * 
                closure_thickness
            ) / 1_000_000_000
            enhanced_custom.append(enhanced_block)
        
        return {
            "standard": enhanced_standard,
            "custom": enhanced_custom,
            "total_volume_m3": sum(b["volume_m3"] for b in enhanced_standard + enhanced_custom),
            "closure_thickness_mm": closure_thickness
        }
    
    def _generate_enhanced_cutting_list(self, enhanced_params: Dict) -> Dict:
        """Genera lista taglio potenziata con misure automatiche."""
        
        material_req = enhanced_params["material_requirements"]
        closure_calc = enhanced_params["closure_calculation"]
        
        cutting_list = {
            "material_sheets": {
                "thickness_mm": closure_calc.closure_thickness_mm,
                "total_area_m2": material_req["material"]["area_m2"],
                "total_volume_m3": material_req["material"]["volume_m3"],
                "sheets_needed": max(1, int(material_req["material"]["area_m2"] / 3.125))  # Sheet 2.5x1.25m
            },
            "guides": {
                "type": enhanced_params["material_parameters"]["guide_spec"].type,
                "total_length_m": material_req["guides"]["length_m"],
                "pieces": max(1, int(material_req["guides"]["length_m"] / 3.0))  # Guide da 3m
            },
            "cutting_instructions": closure_calc.technical_notes,
            "formula_applied": closure_calc.formula,
            "warnings": closure_calc.warnings
        }
        
        # Aggiungi moretti se necessari
        if enhanced_params["moretti_requirements"].get("needed"):
            moretti = enhanced_params["moretti_requirements"]
            cutting_list["moretti"] = {
                "height_mm": moretti["height_mm"],
                "thickness_mm": closure_calc.closure_thickness_mm,
                "quantity": moretti.get("quantity_estimate", {}).get("pieces", 0),
                "cutting_instructions": moretti.get("cutting_instructions", [])
            }
        
        return cutting_list
    
    def _generate_production_parameters(self, enhanced_params: Dict) -> Dict:
        """Genera parametri per produzione."""
        
        return {
            "closure_thickness_mm": enhanced_params["closure_calculation"].closure_thickness_mm,
            "mounting_strategy": enhanced_params["mounting_strategy"]["type"],
            "starting_position": enhanced_params["mounting_strategy"]["starting_point"],
            "special_requirements": enhanced_params["mounting_strategy"]["special_considerations"],
            "estimated_cost": enhanced_params["material_requirements"]["cost_estimate"]["total_cost"],
            "material_efficiency": enhanced_params["material_requirements"]["cost_estimate"].get("efficiency_percent", 85),
            "production_notes": [
                f"Spessore automatico calcolato: {enhanced_params['closure_calculation'].closure_thickness_mm}mm",
                f"Formula: {enhanced_params['closure_calculation'].formula}",
                "Verificare misure prima della produzione",
                "Mantenere tolleranze di taglio ±2mm"
            ]
        }
    
    def _generate_technical_notes(self, closure_calc: CalculationResult, mounting_strategy: Dict,
                                moretti_params: Optional[Dict]) -> List[str]:
        """Genera note tecniche complete."""
        
        notes = []
        notes.extend(closure_calc.technical_notes)
        notes.extend(mounting_strategy.get("special_considerations", []))
        
        if moretti_params and moretti_params.get("needed"):
            notes.extend(moretti_params.get("mounting_notes", []))
        
        return notes
    
    def _reconstruct_wall_polygon(self, wall_bounds: List[float]) -> Polygon:
        """Ricostruisce poligono parete da bounds."""
        
        if len(wall_bounds) >= 4:
            minx, miny, maxx, maxy = wall_bounds[:4]
            return Polygon([(minx, miny), (maxx, miny), (maxx, maxy), (minx, maxy)])
        
        # Fallback
        return Polygon([(0, 0), (1000, 0), (1000, 1000), (0, 1000)])

# Funzioni di integrazione con sistema esistente
def enhance_packing_with_automatic_measurements(packing_result: Dict, project_config: Dict) -> Dict:
    """
    Funzione di utilità per potenziare risultati di packing esistenti.
    
    Args:
        packing_result: Risultato del sistema di packing standard
        project_config: Configurazione progetto con parametri materiali
        
    Returns:
        Risultato potenziato con calcoli automatici
    """
    
    calculator = EnhancedPackingCalculator()
    return calculator.enhance_existing_packing_result(packing_result, project_config)

def calculate_automatic_project_parameters(wall_polygon: Polygon, material_config: Dict) -> Dict:
    """
    Calcola automaticamente tutti i parametri di un progetto.
    
    Args:
        wall_polygon: Geometria della parete
        material_config: Configurazione materiali
        
    Returns:
        Parametri calcolati automaticamente
    """
    
    calculator = EnhancedPackingCalculator()
    return calculator.calculate_enhanced_packing_parameters(material_config, wall_polygon)

# Test e validazione
if __name__ == "__main__":
    from shapely.geometry import Polygon
    
    print("🔧 Test Integrazione Calcolo Automatico")
    print("="*50)
    
    # Test con poligono esempio
    test_wall = Polygon([(0, 0), (5000, 0), (5000, 2700), (0, 2700)])
    
    test_config = {
        "material_thickness_mm": 14,
        "guide_width_mm": 75,
        "material_density_kg_m3": 650.0,
        "guide_max_load_kg": 40.0,
        "wall_position": "attached",
        "is_attached_to_existing": True,
        "ceiling_height_mm": 2700
    }
    
    calculator = EnhancedPackingCalculator()
    result = calculator.calculate_enhanced_packing_parameters(test_config, test_wall)
    
    print(f"✅ Spessore chiusura: {result['closure_calculation'].closure_thickness_mm}mm")
    print(f"✅ Formula: {result['closure_calculation'].formula}")
    print(f"✅ Strategia montaggio: {result['mounting_strategy']['type']}")
    print(f"✅ Moretti necessari: {result['moretti_requirements'].get('needed', False)}")
    print(f"✅ Costo stimato: €{result['material_requirements']['cost_estimate']['total_cost']}")
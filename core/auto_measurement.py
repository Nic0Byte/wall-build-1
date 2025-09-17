"""
Algoritmi di Calcolo Automatico Misure
Implementa la logica del documento: materiale + guide = chiusura
Include calcoli per moretti e dimensioni corrette
"""

import math
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

class MeasurementUnit(Enum):
    """Unità di misura supportate."""
    MM = "mm"
    CM = "cm"
    M = "m"

@dataclass
class MaterialSpec:
    """Specifiche materiale."""
    thickness_mm: int
    density_kg_m3: float
    strength_factor: float = 1.0
    
@dataclass 
class GuideSpec:
    """Specifiche guide."""
    width_mm: int
    depth_mm: int
    max_load_kg: float
    type: str  # "50mm", "75mm", "100mm"

@dataclass
class CalculationResult:
    """Risultato di un calcolo."""
    closure_thickness_mm: int
    total_thickness_mm: int
    moretti_height_mm: Optional[int]
    technical_notes: List[str]
    warnings: List[str]
    formula: str

class AutoMeasurementCalculator:
    """
    Calcolatore automatico delle misure.
    Implementa la formula principale: spessore_materiale + larghezza_guide = spessore_chiusura
    """
    
    def __init__(self):
        self.tolerance_mm = 2  # Tolleranza standard di taglio
        self.standard_ceiling_height_mm = 2700  # Altezza soffitto standard
        self.standard_block_height_mm = 495   # Altezza blocco standard
    
    def calculate_closure_thickness(self, material: MaterialSpec, guide: GuideSpec) -> CalculationResult:
        """
        Calcola lo spessore di chiusura secondo la formula base.
        Esempio dal documento: 14mm (materiale) + 75mm (guide) = 103mm (chiusura)
        """
        
        # Formula principale
        closure_thickness = material.thickness_mm + guide.width_mm
        
        # Note tecniche
        notes = [
            f"Formula base: {material.thickness_mm}mm (materiale) + {guide.width_mm}mm (guide) = {closure_thickness}mm",
            f"Esempio documento: 14mm + 75mm = 103mm",
            f"Tolleranza taglio: ±{self.tolerance_mm}mm"
        ]
        
        # Avvertimenti
        warnings = []
        
        # Controlli di validità
        if guide.width_mm > material.thickness_mm * 3:
            warnings.append(f"⚠️ Guide molto larghe rispetto al materiale ({guide.width_mm}mm vs {material.thickness_mm}mm)")
        
        if closure_thickness > 150:
            warnings.append(f"⚠️ Spessore chiusura elevato ({closure_thickness}mm) - verificare compatibilità")
        
        if material.thickness_mm < 10:
            warnings.append(f"⚠️ Materiale molto sottile ({material.thickness_mm}mm) - verificare resistenza")
        
        return CalculationResult(
            closure_thickness_mm=closure_thickness,
            total_thickness_mm=closure_thickness,  # Per ora uguale, poi si aggiungono altri elementi
            moretti_height_mm=None,
            technical_notes=notes,
            warnings=warnings,
            formula=f"{material.thickness_mm} + {guide.width_mm} = {closure_thickness}"
        )
    
    def calculate_moretti_dimensions(self, ceiling_height_mm: int, closure_thickness_mm: int, 
                                   complete_rows: int) -> Dict:
        """
        Calcola le dimensioni dei moretti per pareti che non arrivano al soffitto.
        """
        
        # Calcola lo spazio rimanente dopo le righe complete
        used_height = complete_rows * self.standard_block_height_mm
        remaining_height = ceiling_height_mm - used_height
        
        # Determina se servono moretti
        moretti_needed = remaining_height >= 50  # Minimo 50mm per avere senso
        
        if not moretti_needed:
            return {
                "needed": False,
                "height_mm": 0,
                "thickness_mm": closure_thickness_mm,
                "reason": f"Spazio rimanente {remaining_height}mm insufficiente per moretti"
            }
        
        # Calcola dimensioni moretti
        moretti_height = remaining_height - 5  # -5mm per tolleranza montaggio
        
        result = {
            "needed": True,
            "height_mm": moretti_height,
            "thickness_mm": closure_thickness_mm,  # Stesso spessore della chiusura
            "width_mm": self.standard_block_height_mm,  # Larghezza standard
            "quantity_estimate": self._estimate_moretti_quantity(moretti_height, closure_thickness_mm),
            "cutting_instructions": self._generate_moretti_cutting_instructions(moretti_height),
            "mounting_notes": [
                "Montare i moretti nella parte superiore della parete",
                f"Altezza moretti: {moretti_height}mm",
                f"Spessore: {closure_thickness_mm}mm (stesso della chiusura)",
                "Lasciare 5mm di tolleranza per il montaggio"
            ]
        }
        
        return result
    
    def calculate_material_requirements(self, wall_dimensions: Dict, material: MaterialSpec, 
                                      guide: GuideSpec, moretti_params: Optional[Dict] = None) -> Dict:
        """
        Calcola i requisiti totali di materiale per il progetto.
        """
        
        wall_width = wall_dimensions.get("width_mm", 0)
        wall_height = wall_dimensions.get("height_mm", self.standard_ceiling_height_mm)
        wall_area_m2 = (wall_width * wall_height) / 1_000_000
        
        # Calcola volume materiale necessario
        closure_result = self.calculate_closure_thickness(material, guide)
        material_volume_m3 = (wall_area_m2 * material.thickness_mm) / 1000
        
        # Calcola peso
        material_weight_kg = material_volume_m3 * material.density_kg_m3
        
        # Calcola guide necessarie
        wall_perimeter_m = (wall_width + wall_height) * 2 / 1000
        guide_length_m = wall_perimeter_m * 1.1  # +10% per sicurezza
        
        # Includi moretti se necessari
        moretti_volume_m3 = 0
        moretti_weight_kg = 0
        
        if moretti_params and moretti_params.get("needed"):
            moretti_area_m2 = (wall_width * moretti_params["height_mm"]) / 1_000_000
            moretti_volume_m3 = (moretti_area_m2 * material.thickness_mm) / 1000
            moretti_weight_kg = moretti_volume_m3 * material.density_kg_m3
        
        return {
            "material": {
                "volume_m3": material_volume_m3,
                "weight_kg": material_weight_kg,
                "area_m2": wall_area_m2,
                "thickness_mm": material.thickness_mm
            },
            "guides": {
                "length_m": guide_length_m,
                "type": guide.type,
                "width_mm": guide.width_mm
            },
            "moretti": {
                "volume_m3": moretti_volume_m3,
                "weight_kg": moretti_weight_kg,
                "needed": moretti_params.get("needed", False) if moretti_params else False
            },
            "totals": {
                "volume_m3": material_volume_m3 + moretti_volume_m3,
                "weight_kg": material_weight_kg + moretti_weight_kg,
                "closure_thickness_mm": closure_result.closure_thickness_mm
            },
            "cost_estimate": self._estimate_project_cost(
                material_volume_m3 + moretti_volume_m3, 
                guide_length_m
            )
        }
    
    def calculate_cutting_optimization(self, required_pieces: List[Dict], 
                                     material_sheet_size: Dict) -> Dict:
        """
        Ottimizza il taglio per minimizzare gli sprechi di materiale.
        """
        
        sheet_width = material_sheet_size.get("width_mm", 2500)
        sheet_height = material_sheet_size.get("height_mm", 1250)
        sheet_area = sheet_width * sheet_height
        
        # Ordina i pezzi per area decrescente (algoritmo First Fit Decreasing)
        sorted_pieces = sorted(required_pieces, 
                              key=lambda p: p.get("width_mm", 0) * p.get("height_mm", 0), 
                              reverse=True)
        
        # Simula il posizionamento
        sheets_used = []
        current_sheet = {"width": sheet_width, "height": sheet_height, "pieces": [], "remaining_area": sheet_area}
        
        for piece in sorted_pieces:
            piece_width = piece.get("width_mm", 0)
            piece_height = piece.get("height_mm", 0)
            piece_area = piece_width * piece_height
            
            # Controlla se il pezzo entra nel foglio corrente
            if (piece_width <= current_sheet["width"] and 
                piece_height <= current_sheet["height"] and
                piece_area <= current_sheet["remaining_area"]):
                
                # Aggiungi il pezzo al foglio corrente
                current_sheet["pieces"].append(piece)
                current_sheet["remaining_area"] -= piece_area
                
                # Aggiorna dimensioni rimanenti (semplificato)
                current_sheet["width"] -= piece_width
                
            else:
                # Il pezzo non entra, inizia un nuovo foglio
                if current_sheet["pieces"]:
                    sheets_used.append(current_sheet)
                
                current_sheet = {
                    "width": sheet_width - piece_width,
                    "height": sheet_height,
                    "pieces": [piece],
                    "remaining_area": sheet_area - piece_area
                }
        
        # Aggiungi l'ultimo foglio se ha pezzi
        if current_sheet["pieces"]:
            sheets_used.append(current_sheet)
        
        # Calcola statistiche
        total_used_area = sum(sum(p.get("width_mm", 0) * p.get("height_mm", 0) for p in sheet["pieces"]) 
                             for sheet in sheets_used)
        total_sheet_area = len(sheets_used) * sheet_area
        efficiency = (total_used_area / total_sheet_area * 100) if total_sheet_area > 0 else 0
        
        return {
            "sheets_needed": len(sheets_used),
            "sheets_layout": sheets_used,
            "efficiency_percent": round(efficiency, 1),
            "waste_area_mm2": total_sheet_area - total_used_area,
            "total_pieces": len(required_pieces),
            "optimization_notes": [
                f"Efficienza taglio: {efficiency:.1f}%",
                f"Fogli necessari: {len(sheets_used)}",
                f"Area totale utilizzata: {total_used_area/1000:.1f} dm²",
                f"Spreco stimato: {(total_sheet_area - total_used_area)/1000:.1f} dm²"
            ]
        }
    
    def validate_measurement_combination(self, material: MaterialSpec, guide: GuideSpec,
                                       wall_dimensions: Dict) -> Dict:
        """
        Valida una combinazione di misure e identifica potenziali problemi.
        """
        
        issues = []
        warnings = []
        recommendations = []
        
        wall_width = wall_dimensions.get("width_mm", 0)
        wall_height = wall_dimensions.get("height_mm", 0)
        
        # Controllo rapporto spessori
        thickness_ratio = guide.width_mm / material.thickness_mm
        if thickness_ratio > 5:
            issues.append(f"Guide troppo larghe: rapporto {thickness_ratio:.1f}:1")
            recommendations.append("Considerare guide più sottili o materiale più spesso")
        
        # Controllo resistenza strutturale
        wall_area_m2 = (wall_width * wall_height) / 1_000_000
        load_per_m2 = guide.max_load_kg / wall_area_m2 if wall_area_m2 > 0 else 0
        
        if wall_height > 3000 and material.thickness_mm < 18:
            warnings.append("Parete alta con materiale sottile - verificare stabilità")
        
        # Controllo dimensioni standard
        if wall_width % 413 > 50:  # 413 è la larghezza blocco piccolo
            warnings.append("Larghezza parete non ottimale per blocchi standard")
            recommendations.append("Considerare regolare la larghezza per minimizzare gli scarti")
        
        # Calcola spessore chiusura
        closure_result = self.calculate_closure_thickness(material, guide)
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "recommendations": recommendations,
            "closure_thickness_mm": closure_result.closure_thickness_mm,
            "structural_rating": self._calculate_structural_rating(material, guide, wall_dimensions),
            "cost_rating": self._calculate_cost_rating(material, guide),
            "overall_score": self._calculate_overall_score(material, guide, wall_dimensions)
        }
    
    def _estimate_moretti_quantity(self, moretti_height: int, thickness_mm: int) -> Dict:
        """Stima la quantità di moretti necessari."""
        
        # Stima basata su lunghezza tipica parete (5m)
        typical_wall_length_mm = 5000
        moretti_width_mm = 400  # Larghezza tipica moretto
        
        quantity = math.ceil(typical_wall_length_mm / moretti_width_mm)
        
        return {
            "pieces": quantity,
            "total_length_mm": typical_wall_length_mm,
            "piece_width_mm": moretti_width_mm,
            "piece_height_mm": moretti_height,
            "piece_thickness_mm": thickness_mm
        }
    
    def _generate_moretti_cutting_instructions(self, height_mm: int) -> List[str]:
        """Genera istruzioni di taglio per i moretti."""
        
        return [
            f"Tagliare moretti all'altezza di {height_mm}mm",
            "Utilizzare sega circolare o seghetto alternativo",
            "Mantenere tolleranza di taglio ±2mm",
            "Levigare i bordi tagliati",
            "Verificare la misura prima dell'installazione"
        ]
    
    def _estimate_project_cost(self, material_volume_m3: float, guide_length_m: float) -> Dict:
        """Stima il costo del progetto."""
        
        # Prezzi indicativi (da aggiornare con prezzi reali)
        material_cost_per_m3 = 400  # €/m³
        guide_cost_per_m = 15      # €/m
        
        material_cost = material_volume_m3 * material_cost_per_m3
        guide_cost = guide_length_m * guide_cost_per_m
        
        # Costi aggiuntivi
        labor_cost = (material_cost + guide_cost) * 0.5  # 50% dei materiali
        misc_cost = (material_cost + guide_cost) * 0.1   # 10% per viti, colla, etc.
        
        total_cost = material_cost + guide_cost + labor_cost + misc_cost
        
        return {
            "material_cost": round(material_cost, 2),
            "guide_cost": round(guide_cost, 2),
            "labor_cost": round(labor_cost, 2),
            "misc_cost": round(misc_cost, 2),
            "total_cost": round(total_cost, 2),
            "currency": "EUR",
            "note": "Stima indicativa - verificare prezzi correnti"
        }
    
    def _calculate_structural_rating(self, material: MaterialSpec, guide: GuideSpec, 
                                   wall_dimensions: Dict) -> str:
        """Calcola un rating strutturale."""
        
        wall_height = wall_dimensions.get("height_mm", 0)
        
        # Fattori che influenzano la resistenza
        thickness_score = min(material.thickness_mm / 25, 1.0)  # Max score a 25mm
        guide_score = min(guide.max_load_kg / 50, 1.0)          # Max score a 50kg
        height_penalty = max(0, (wall_height - 2500) / 1000)    # Penalità per altezza > 2.5m
        
        total_score = (thickness_score + guide_score - height_penalty) / 2
        
        if total_score >= 0.8:
            return "Eccellente"
        elif total_score >= 0.6:
            return "Buono"
        elif total_score >= 0.4:
            return "Accettabile"
        else:
            return "Insufficiente"
    
    def _calculate_cost_rating(self, material: MaterialSpec, guide: GuideSpec) -> str:
        """Calcola un rating di costo."""
        
        # Logica semplificata - in produzione collegare a database prezzi reali
        thickness_cost = material.thickness_mm * 0.1
        guide_cost = guide.width_mm * 0.05
        
        total_cost = thickness_cost + guide_cost
        
        if total_cost <= 5:
            return "Economico"
        elif total_cost <= 10:
            return "Medio"
        else:
            return "Costoso"
    
    def _calculate_overall_score(self, material: MaterialSpec, guide: GuideSpec, 
                               wall_dimensions: Dict) -> float:
        """Calcola un punteggio complessivo da 1 a 10."""
        
        # Combina diversi fattori
        structural = self._calculate_structural_rating(material, guide, wall_dimensions)
        cost = self._calculate_cost_rating(material, guide)
        
        structural_scores = {"Eccellente": 10, "Buono": 8, "Accettabile": 6, "Insufficiente": 3}
        cost_scores = {"Economico": 10, "Medio": 7, "Costoso": 4}
        
        structural_score = structural_scores.get(structural, 5)
        cost_score = cost_scores.get(cost, 5)
        
        # Media ponderata (strutturale 70%, costo 30%)
        overall = (structural_score * 0.7) + (cost_score * 0.3)
        
        return round(overall, 1)

# Funzioni di utilità per l'integrazione con il sistema esistente
def create_calculation_from_config(config: Dict) -> CalculationResult:
    """
    Crea un calcolo dalle configurazioni del progetto.
    Integrazione con il sistema di configurazione esistente.
    """
    
    material = MaterialSpec(
        thickness_mm=config.get("material_thickness_mm", 18),
        density_kg_m3=config.get("material_density", 650.0),
        strength_factor=config.get("material_strength_factor", 1.0)
    )
    
    guide = GuideSpec(
        width_mm=config.get("guide_width_mm", 75),
        depth_mm=config.get("guide_depth_mm", 25),
        max_load_kg=config.get("guide_max_load", 40.0),
        type=config.get("guide_type", "75mm")
    )
    
    calculator = AutoMeasurementCalculator()
    return calculator.calculate_closure_thickness(material, guide)

def validate_project_measurements(project_config: Dict) -> Dict:
    """
    Valida le misure di un progetto completo.
    """
    
    material = MaterialSpec(
        thickness_mm=project_config.get("material_thickness_mm", 18),
        density_kg_m3=project_config.get("material_density", 650.0)
    )
    
    guide = GuideSpec(
        width_mm=project_config.get("guide_width_mm", 75),
        depth_mm=project_config.get("guide_depth_mm", 25),
        max_load_kg=project_config.get("guide_max_load", 40.0),
        type=project_config.get("guide_type", "75mm")
    )
    
    wall_dimensions = {
        "width_mm": project_config.get("wall_width_mm", 5000),
        "height_mm": project_config.get("wall_height_mm", 2700)
    }
    
    calculator = AutoMeasurementCalculator()
    return calculator.validate_measurement_combination(material, guide, wall_dimensions)

# Esempi di utilizzo e test
if __name__ == "__main__":
    # Test con l'esempio del documento: 14mm + 75mm = 103mm
    
    print("🧮 Test Calcolo Automatico Misure")
    print("="*50)
    
    # Materiale dell'esempio
    truciolato_14mm = MaterialSpec(
        thickness_mm=14,
        density_kg_m3=650.0,
        strength_factor=1.0
    )
    
    # Guide dell'esempio  
    guide_75mm = GuideSpec(
        width_mm=75,
        depth_mm=25,
        max_load_kg=40.0,
        type="75mm"
    )
    
    calculator = AutoMeasurementCalculator()
    
    # Test calcolo chiusura
    result = calculator.calculate_closure_thickness(truciolato_14mm, guide_75mm)
    
    print(f"✅ Formula: {result.formula}")
    print(f"✅ Spessore chiusura: {result.closure_thickness_mm}mm")
    print(f"✅ Note tecniche:")
    for note in result.technical_notes:
        print(f"   • {note}")
    
    if result.warnings:
        print(f"⚠️ Avvertimenti:")
        for warning in result.warnings:
            print(f"   • {warning}")
    
    print()
    
    # Test con diverse combinazioni
    test_combinations = [
        {"material": 10, "guide": 50, "expected": 60},
        {"material": 18, "guide": 75, "expected": 93},
        {"material": 25, "guide": 100, "expected": 125}
    ]
    
    print("🧪 Test combinazioni diverse:")
    for combo in test_combinations:
        mat = MaterialSpec(thickness_mm=combo["material"], density_kg_m3=650.0)
        gui = GuideSpec(width_mm=combo["guide"], depth_mm=20, max_load_kg=30.0, type=f"{combo['guide']}mm")
        
        result = calculator.calculate_closure_thickness(mat, gui)
        
        expected = combo["expected"]
        actual = result.closure_thickness_mm
        status = "✅" if actual == expected else "❌"
        
        print(f"   {status} {combo['material']}mm + {combo['guide']}mm = {actual}mm (atteso: {expected}mm)")
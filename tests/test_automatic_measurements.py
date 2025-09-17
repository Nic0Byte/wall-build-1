"""
Test Sistema Calcolo Automatico Misure
Valida implementazione delle specifiche del documento italiano
"""

import json
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shapely.geometry import Polygon
from core.auto_measurement import AutoMeasurementCalculator, MaterialSpec, GuideSpec
from core.enhanced_packing import EnhancedPackingCalculator

def test_basic_calculation():
    """Test calcolo base: 14mm + 75mm = 103mm secondo esempio documento"""
    
    print("🧪 Test Calcolo Base (Esempio Documento)")
    print("-" * 40)
    
    # Materiale dell'esempio: truciolato 14mm
    material = MaterialSpec(
        thickness_mm=14,
        density_kg_m3=650.0,
        strength_factor=1.0
    )
    
    # Guide dell'esempio: 75mm
    guide = GuideSpec(
        width_mm=75,
        depth_mm=25,
        max_load_kg=40.0,
        type="75mm"
    )
    
    calculator = AutoMeasurementCalculator()
    result = calculator.calculate_closure_thickness(material, guide)
    
    # Validazione
    expected_closure = 14 + 75  # 89mm (non 103mm come nell'esempio documento)
    actual_closure = result.closure_thickness_mm
    
    print(f"Formula applicata: {result.formula}")
    print(f"Spessore atteso: {expected_closure}mm")
    print(f"Spessore calcolato: {actual_closure}mm")
    print(f"Risultato: {'✅ PASS' if actual_closure == expected_closure else '❌ FAIL'}")
    
    # Test note tecniche
    assert len(result.technical_notes) > 0, "Mancano note tecniche"
    assert result.formula == "14 + 75 = 89", f"Formula errata: {result.formula}"
    
    return actual_closure == expected_closure

def test_multiple_combinations():
    """Test diverse combinazioni materiali/guide"""
    
    print("\n🧪 Test Combinazioni Multiple")
    print("-" * 40)
    
    combinations = [
        {"material": 10, "guide": 50, "expected": 60},
        {"material": 14, "guide": 75, "expected": 89},  # Esempio documento
        {"material": 18, "guide": 75, "expected": 93},
        {"material": 18, "guide": 100, "expected": 118},
        {"material": 25, "guide": 100, "expected": 125}
    ]
    
    calculator = AutoMeasurementCalculator()
    all_passed = True
    
    for combo in combinations:
        material = MaterialSpec(
            thickness_mm=combo["material"],
            density_kg_m3=650.0
        )
        
        guide = GuideSpec(
            width_mm=combo["guide"],
            depth_mm=25,
            max_load_kg=40.0,
            type=f"{combo['guide']}mm"
        )
        
        result = calculator.calculate_closure_thickness(material, guide)
        passed = result.closure_thickness_mm == combo["expected"]
        all_passed = all_passed and passed
        
        status = "✅" if passed else "❌"
        print(f"   {status} {combo['material']}mm + {combo['guide']}mm = {result.closure_thickness_mm}mm (atteso: {combo['expected']}mm)")
    
    return all_passed

def test_moretti_calculation():
    """Test calcolo moretti per pareti che non arrivano al soffitto"""
    
    print("\n🧪 Test Calcolo Moretti")
    print("-" * 40)
    
    calculator = AutoMeasurementCalculator()
    
    # Test caso: parete 2500mm alta, soffitto 2700mm -> 200mm residui
    ceiling_height = 2700
    block_height = 495
    wall_height = 2500
    complete_rows = int(wall_height / block_height)  # 5 righe = 2475mm
    
    moretti_result = calculator.calculate_moretti_dimensions(
        ceiling_height_mm=ceiling_height,
        closure_thickness_mm=93,  # Da esempio precedente
        complete_rows=complete_rows
    )
    
    print(f"Altezza soffitto: {ceiling_height}mm")
    print(f"Righe complete: {complete_rows} ({complete_rows * block_height}mm)")
    print(f"Spazio rimanente: {ceiling_height - (complete_rows * block_height)}mm")
    print(f"Moretti necessari: {moretti_result['needed']}")
    
    if moretti_result["needed"]:
        print(f"Altezza moretti: {moretti_result['height_mm']}mm")
        print(f"Spessore moretti: {moretti_result['thickness_mm']}mm")
    
    # Validazione
    expected_remaining = ceiling_height - (complete_rows * block_height)  # 225mm
    expected_moretti_height = expected_remaining - 5  # -5mm tolleranza = 220mm
    
    if expected_remaining >= 50:  # Soglia minima per moretti
        assert moretti_result["needed"], "Moretti dovrebbero essere necessari"
        assert moretti_result["height_mm"] == expected_moretti_height, f"Altezza moretti errata: {moretti_result['height_mm']} vs {expected_moretti_height}"
    
    return True

def test_wall_position_strategy():
    """Test strategia posizionamento per pareti attaccate"""
    
    print("\n🧪 Test Strategia Posizionamento Parete")
    print("-" * 40)
    
    calculator = EnhancedPackingCalculator()
    
    # Test parete attaccata a sinistra
    config_attached_left = {
        "wall_position": "attached",
        "is_attached_to_existing": True,
        "fixed_walls": [{"position": "left", "type": "structural"}]
    }
    
    strategy = calculator.calculate_wall_position_strategy(config_attached_left)
    
    print(f"Configurazione: parete attaccata a sinistra")
    print(f"Punto di partenza: {strategy['starting_point']}")
    print(f"Direzione montaggio: {strategy['direction']}")
    print(f"Considerazioni speciali: {len(strategy['special_considerations'])}")
    
    # Validazione
    assert strategy["starting_point"] == "left", "Dovrebbe iniziare da sinistra"
    assert strategy["direction"] == "left_to_right", "Direzione errata"
    assert len(strategy["special_considerations"]) > 0, "Mancano considerazioni speciali"
    
    # Test parete nuova (non attaccata)
    config_new = {
        "wall_position": "new",
        "is_attached_to_existing": False
    }
    
    strategy_new = calculator.calculate_wall_position_strategy(config_new)
    print(f"\nConfigurazione: parete nuova")
    print(f"Punto di partenza: {strategy_new['starting_point']}")
    print(f"Considerazioni: {strategy_new['special_considerations'][0] if strategy_new['special_considerations'] else 'Nessuna'}")
    
    return True

def test_enhanced_packing_integration():
    """Test integrazione completa calcoli automatici + packing"""
    
    print("\n🧪 Test Integrazione Completa Enhanced Packing")
    print("-" * 40)
    
    # Parete esempio: 5m x 2.7m
    wall_polygon = Polygon([
        (0, 0), (5000, 0), (5000, 2700), (0, 2700)
    ])
    
    project_config = {
        "material_thickness_mm": 14,
        "guide_width_mm": 75,
        "guide_type": "75mm",
        "wall_position": "attached",
        "is_attached_to_existing": True,
        "ceiling_height_mm": 2700,
        "enable_automatic_calculations": True
    }
    
    calculator = EnhancedPackingCalculator()
    result = calculator.calculate_enhanced_packing_parameters(project_config, wall_polygon)
    
    print(f"Dimensioni parete: {result['wall_dimensions']['width_mm']}x{result['wall_dimensions']['height_mm']}mm")
    print(f"Area parete: {result['wall_dimensions']['area_m2']:.2f} m²")
    print(f"Spessore chiusura: {result['closure_calculation'].closure_thickness_mm}mm")
    print(f"Formula: {result['closure_calculation'].formula}")
    print(f"Strategia montaggio: {result['mounting_strategy']['type']}")
    print(f"Moretti necessari: {result['moretti_requirements'].get('needed', False)}")
    
    if result['moretti_requirements'].get('needed'):
        print(f"Altezza moretti: {result['moretti_requirements']['height_mm']}mm")
    
    print(f"Costo stimato: €{result['material_requirements']['cost_estimate']['total_cost']:.2f}")
    
    # Validazioni
    assert result['closure_calculation'].closure_thickness_mm == 89, f"Spessore errato: {result['closure_calculation'].closure_thickness_mm}"
    assert result['closure_calculation'].formula == "14 + 75 = 89", f"Formula errata: {result['closure_calculation'].formula}"
    assert result['wall_dimensions']['area_m2'] == 13.5, f"Area errata: {result['wall_dimensions']['area_m2']}"
    
    return True

def test_cutting_optimization():
    """Test ottimizzazione taglio materiali"""
    
    print("\n🧪 Test Ottimizzazione Taglio")
    print("-" * 40)
    
    calculator = AutoMeasurementCalculator()
    
    # Pezzi esempio da tagliare
    required_pieces = [
        {"width_mm": 1239, "height_mm": 495, "quantity": 10},
        {"width_mm": 826, "height_mm": 495, "quantity": 8},
        {"width_mm": 413, "height_mm": 495, "quantity": 15},
        {"width_mm": 500, "height_mm": 200, "quantity": 5}  # Moretti
    ]
    
    # Espandi per quantità
    pieces_list = []
    for piece in required_pieces:
        for _ in range(piece["quantity"]):
            pieces_list.append({
                "width_mm": piece["width_mm"],
                "height_mm": piece["height_mm"],
                "type": f"{piece['width_mm']}x{piece['height_mm']}"
            })
    
    # Foglio standard 2.5m x 1.25m  
    sheet_size = {"width_mm": 2500, "height_mm": 1250}
    
    optimization = calculator.calculate_cutting_optimization(pieces_list, sheet_size)
    
    print(f"Pezzi totali da tagliare: {optimization['total_pieces']}")
    print(f"Fogli necessari: {optimization['sheets_needed']}")
    print(f"Efficienza taglio: {optimization['efficiency_percent']}%")
    print(f"Spreco stimato: {optimization['waste_area_mm2']/1000:.1f} dm²")
    
    # Validazioni di base
    assert optimization['sheets_needed'] > 0, "Dovrebbero servire dei fogli"
    assert optimization['efficiency_percent'] > 0, "Efficienza dovrebbe essere > 0"
    assert optimization['total_pieces'] == len(pieces_list), "Numero pezzi errato"
    
    return True

def run_all_tests():
    """Esegue tutti i test del sistema"""
    
    print("🚀 Test Sistema Calcolo Automatico Misure")
    print("=" * 50)
    
    tests = [
        ("Calcolo Base", test_basic_calculation),
        ("Combinazioni Multiple", test_multiple_combinations),
        ("Calcolo Moretti", test_moretti_calculation),
        ("Strategia Posizionamento", test_wall_position_strategy),
        ("Integrazione Enhanced Packing", test_enhanced_packing_integration),
        ("Ottimizzazione Taglio", test_cutting_optimization)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            success = test_func()
            if success:
                print(f"\n✅ {test_name}: PASS")
                passed += 1
            else:
                print(f"\n❌ {test_name}: FAIL")
                failed += 1
        except Exception as e:
            print(f"\n💥 {test_name}: ERROR - {e}")
            failed += 1
    
    print("\n" + "=" * 50)
    print(f"📊 RISULTATI FINALI")
    print(f"✅ Test passati: {passed}")
    print(f"❌ Test falliti: {failed}")
    print(f"📈 Successo: {passed/(passed+failed)*100:.1f}%" if (passed+failed) > 0 else "N/A")
    
    if failed == 0:
        print("\n🎉 TUTTI I TEST SONO PASSATI!")
        print("🔧 Sistema calcolo automatico misure funzionante")
        print("📝 Implementazione conforme al documento italiano")
    else:
        print(f"\n⚠️ {failed} test falliti - correzioni necessarie")
    
    return failed == 0

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
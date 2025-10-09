"""
Test veloce per verificare la nuova formula di calcolo dello spessore delle chiusure
Formula corretta: materiale + guida + materiale
"""

# Test della formula nel modulo database
from database.material_services import ProjectMaterialConfigService

# Test 1: Materiale 14mm + Guida 75mm
materiale_14 = 14
guida_75 = 75
risultato_1 = ProjectMaterialConfigService.calculate_closure_thickness(materiale_14, guida_75)
atteso_1 = (14 * 2) + 75  # = 103mm
print(f"Test 1: {materiale_14}mm + {guida_75}mm + {materiale_14}mm")
print(f"  Risultato: {risultato_1}mm")
print(f"  Atteso: {atteso_1}mm")
print(f"  Status: {'✅ PASS' if risultato_1 == atteso_1 else '❌ FAIL'}\n")

# Test 2: Materiale 18mm + Guida 75mm
materiale_18 = 18
guida_75 = 75
risultato_2 = ProjectMaterialConfigService.calculate_closure_thickness(materiale_18, guida_75)
atteso_2 = (18 * 2) + 75  # = 111mm
print(f"Test 2: {materiale_18}mm + {guida_75}mm + {materiale_18}mm")
print(f"  Risultato: {risultato_2}mm")
print(f"  Atteso: {atteso_2}mm")
print(f"  Status: {'✅ PASS' if risultato_2 == atteso_2 else '❌ FAIL'}\n")

# Test 3: Materiale 10mm + Guida 50mm
materiale_10 = 10
guida_50 = 50
risultato_3 = ProjectMaterialConfigService.calculate_closure_thickness(materiale_10, guida_50)
atteso_3 = (10 * 2) + 50  # = 70mm
print(f"Test 3: {materiale_10}mm + {guida_50}mm + {materiale_10}mm")
print(f"  Risultato: {risultato_3}mm")
print(f"  Atteso: {atteso_3}mm")
print(f"  Status: {'✅ PASS' if risultato_3 == atteso_3 else '❌ FAIL'}\n")

# Riepilogo
if risultato_1 == atteso_1 and risultato_2 == atteso_2 and risultato_3 == atteso_3:
    print("=" * 50)
    print("✅ TUTTI I TEST SUPERATI!")
    print("Formula corretta: materiale + guida + materiale")
    print("=" * 50)
else:
    print("=" * 50)
    print("❌ ALCUNI TEST FALLITI")
    print("=" * 50)

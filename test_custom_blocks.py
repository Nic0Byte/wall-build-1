#!/usr/bin/env python3
"""
Test per il sistema di personalizzazione blocchi.
Verifica che la logica "SE misure default → schema standard, ALTRIMENTI → schema custom" funzioni correttamente.
"""

import sys
sys.path.append('.')

from utils.config import (
    get_block_schema_from_frontend, 
    get_default_block_schema, 
    create_custom_block_schema,
    BLOCK_WIDTHS, 
    BLOCK_HEIGHT
)

def test_default_block_detection():
    """Test: dimensioni identiche al default → schema standard."""
    print("\n" + "="*70)
    print("🧪 TEST 1: Dimensioni identiche al default")
    print("="*70)
    
    # Simula dati dal frontend con dimensioni default
    frontend_data = {
        "block_widths": [1239, 826, 413],  # Stesso ordine del default
        "block_height": 495,
        "block_depth": 100  # Ignorato
    }
    
    schema = get_block_schema_from_frontend(frontend_data)
    
    print(f"📦 Dati frontend: {frontend_data}")
    print(f"✅ Schema risultante: {schema['schema_type']}")
    print(f"   📏 Dimensioni: {schema['block_widths']}×{schema['block_height']}")
    print(f"   🔤 Mappatura: {schema['size_to_letter']}")
    
    # Verifica che sia riconosciuto come standard
    assert schema['schema_type'] == 'standard'
    assert schema['block_widths'] == BLOCK_WIDTHS
    assert schema['block_height'] == BLOCK_HEIGHT
    
    print("✅ PASSED: Dimensioni default riconosciute correttamente come standard")


def test_custom_block_detection():
    """Test: dimensioni diverse dal default → schema custom."""
    print("\n" + "="*70)
    print("🧪 TEST 2: Dimensioni personalizzate")
    print("="*70)
    
    # Simula dati dal frontend con dimensioni personalizzate
    frontend_data = {
        "block_widths": [1200, 800, 400],  # Dimensioni diverse!
        "block_height": 500,  # Altezza diversa!
        "block_depth": 120  # Ignorato
    }
    
    schema = get_block_schema_from_frontend(frontend_data)
    
    print(f"📦 Dati frontend: {frontend_data}")
    print(f"🔧 Schema risultante: {schema['schema_type']}")
    print(f"   📏 Dimensioni: {schema['block_widths']}×{schema['block_height']}")
    print(f"   🔤 Mappatura: {schema['size_to_letter']}")
    
    # Verifica che sia riconosciuto come custom
    assert schema['schema_type'] == 'custom'
    assert schema['block_widths'] == [1200, 800, 400]
    assert schema['block_height'] == 500
    
    # Verifica mappatura personalizzata (A=più grande, B=medio, C=più piccolo)
    expected_mapping = {1200: 'A', 800: 'B', 400: 'C'}
    assert schema['size_to_letter'] == expected_mapping
    
    print("✅ PASSED: Dimensioni personalizzate riconosciute correttamente come custom")


def test_order_independence():
    """Test: l'ordine delle dimensioni non importa per il riconoscimento."""
    print("\n" + "="*70)
    print("🧪 TEST 3: Indipendenza dall'ordine")
    print("="*70)
    
    # Dimensioni default ma in ordine diverso
    frontend_data = {
        "block_widths": [413, 1239, 826],  # Ordine diverso!
        "block_height": 495,
        "block_depth": 100
    }
    
    schema = get_block_schema_from_frontend(frontend_data)
    
    print(f"📦 Dati frontend (ordine diverso): {frontend_data}")
    print(f"✅ Schema risultante: {schema['schema_type']}")
    
    # Deve riconoscere come standard anche se l'ordine è diverso
    assert schema['schema_type'] == 'standard'
    
    print("✅ PASSED: Ordine delle dimensioni irrilevante per il riconoscimento")


def test_mixed_custom():
    """Test: una dimensione diversa → schema custom."""
    print("\n" + "="*70)
    print("🧪 TEST 4: Dimensioni miste (alcune uguali, alcune diverse)")
    print("="*70)
    
    # Solo una dimensione diversa
    frontend_data = {
        "block_widths": [1239, 826, 400],  # Solo l'ultima è diversa (413→400)
        "block_height": 495,
        "block_depth": 100
    }
    
    schema = get_block_schema_from_frontend(frontend_data)
    
    print(f"📦 Dati frontend: {frontend_data}")
    print(f"🔧 Schema risultante: {schema['schema_type']}")
    print(f"   📏 Dimensioni: {schema['block_widths']}×{schema['block_height']}")
    print(f"   🔤 Mappatura: {schema['size_to_letter']}")
    
    # Deve essere custom perché una dimensione è diversa
    assert schema['schema_type'] == 'custom'
    
    print("✅ PASSED: Anche una sola dimensione diversa attiva lo schema custom")


def test_no_frontend_data():
    """Test: nessun dato dal frontend → schema standard di default."""
    print("\n" + "="*70)
    print("🧪 TEST 5: Nessun dato dal frontend")
    print("="*70)
    
    schema = get_block_schema_from_frontend(None)
    
    print(f"📦 Dati frontend: None")
    print(f"✅ Schema risultante: {schema['schema_type']}")
    
    # Deve usare il default
    assert schema['schema_type'] == 'standard'
    
    print("✅ PASSED: Fallback al default quando non ci sono dati frontend")


def test_custom_mapping_generation():
    """Test: generazione corretta della mappatura personalizzata."""
    print("\n" + "="*70)
    print("🧪 TEST 6: Generazione mappatura personalizzata")
    print("="*70)
    
    # Test con dimensioni in ordine diverso
    custom_widths = [500, 1500, 750, 200]  # Volutamente disordinato
    
    schema = create_custom_block_schema(custom_widths, 600)
    
    print(f"📦 Larghezze input: {custom_widths}")
    print(f"🔧 Schema generato: {schema}")
    print(f"   📏 Dimensioni ordinate: {sorted(custom_widths, reverse=True)}")
    print(f"   🔤 Mappatura: {schema['size_to_letter']}")
    
    # Verifica che la mappatura assegni A al più grande, B al secondo, etc.
    expected_mapping = {1500: 'A', 750: 'B', 500: 'C', 200: 'D'}
    assert schema['size_to_letter'] == expected_mapping
    
    print("✅ PASSED: Mappatura personalizzata generata correttamente")


def main():
    """Esegue tutti i test."""
    print("🚀 SISTEMA DI PERSONALIZZAZIONE BLOCCHI - TEST SUITE")
    print("Implementazione della logica: SE misure = default → standard, ALTRIMENTI → custom")
    
    try:
        test_default_block_detection()
        test_custom_block_detection() 
        test_order_independence()
        test_mixed_custom()
        test_no_frontend_data()
        test_custom_mapping_generation()
        
        print("\n" + "="*70)
        print("🎉 TUTTI I TEST PASSATI!")
        print("✅ Il sistema di personalizzazione blocchi funziona correttamente")
        print("✅ La logica 'default vs custom' è implementata bene")
        print("="*70)
        
    except Exception as e:
        print(f"\n❌ TEST FALLITO: {e}")
        print("🔧 Controllare l'implementazione in utils/config.py")
        sys.exit(1)


if __name__ == "__main__":
    main()

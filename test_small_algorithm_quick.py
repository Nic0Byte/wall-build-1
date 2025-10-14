"""
Test Rapido Algoritmo Small con Moraletti
Verifica funzionalità base prima di integrare
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.moraletti_alignment import DynamicMoralettiConfiguration
from core.packing_algorithms.small_algorithm import SmallAlgorithmPacker, pack_wall_with_small_algorithm


def test_configurazione_moraletti():
    """Test 1: Creazione configurazione dinamica"""
    print("=" * 70)
    print("TEST 1: Configurazione Moraletti Dinamica")
    print("=" * 70)
    
    config_dict = {
        'block_large_width': 1239,
        'block_large_height': 495,
        'block_medium_width': 826,
        'block_medium_height': 495,
        'block_small_width': 413,
        'block_small_height': 495,
        'moraletti_thickness': 58,
        'moraletti_height': 495,
        'moraletti_height_from_ground': 95,
        'moraletti_spacing': 420,
        'moraletti_count_large': 3,
        'moraletti_count_medium': 2,
        'moraletti_count_small': 1,
    }
    
    try:
        config = DynamicMoralettiConfiguration(config_dict)
        print(f"✅ Configurazione creata correttamente")
        print(f"   Blocchi: Large={config.block_sizes['large']}mm, Medium={config.block_sizes['medium']}mm, Small={config.block_sizes['small']}mm")
        print(f"   Moraletti: Spacing={config.spacing}mm, Thickness={config.thickness}mm")
        print(f"   Counts: Large={config.moraletti_counts['large']}, Medium={config.moraletti_counts['medium']}, Small={config.moraletti_counts['small']}")
        return config
    except Exception as e:
        print(f"❌ Errore: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_calcolo_moraletti_standard(config):
    """Test 2: Calcolo moraletti blocchi standard"""
    print("\n" + "=" * 70)
    print("TEST 2: Calcolo Moraletti Blocchi Standard")
    print("=" * 70)
    
    # Test blocco grande
    print("\n📦 Blocco GRANDE (1239mm):")
    block_moraletti = config.calculate_moraletti_for_block(1239, block_x=0)
    print(f"   Tipo: {block_moraletti.block_type}")
    print(f"   Numero moraletti: {block_moraletti.moraletti_count}")
    print(f"   Posizioni X:")
    for i, pos in enumerate(block_moraletti.positions):
        print(f"      M{i+1}: centro={pos.center_x:.0f}mm, range=[{pos.range_start:.0f}, {pos.range_end:.0f}]")
    
    # Test blocco medio
    print("\n📦 Blocco MEDIO (826mm):")
    block_moraletti = config.calculate_moraletti_for_block(826, block_x=0)
    print(f"   Numero moraletti: {block_moraletti.moraletti_count}")
    for i, pos in enumerate(block_moraletti.positions):
        print(f"      M{i+1}: centro={pos.center_x:.0f}mm")
    
    # Test blocco piccolo
    print("\n📦 Blocco PICCOLO (413mm):")
    block_moraletti = config.calculate_moraletti_for_block(413, block_x=0)
    print(f"   Numero moraletti: {block_moraletti.moraletti_count}")
    for i, pos in enumerate(block_moraletti.positions):
        print(f"      M{i+1}: centro={pos.center_x:.0f}mm")


def main():
    """Esegue test base"""
    print("\n" + "🎯" * 35)
    print("TEST ALGORITMO SMALL CON MORALETTI")
    print("🎯" * 35 + "\n")
    
    # Test 1: Configurazione
    config = test_configurazione_moraletti()
    if not config:
        print("\n❌ Test fallito alla configurazione!")
        return
    
    # Test 2: Moraletti standard
    test_calcolo_moraletti_standard(config)
    
    print("\n" + "=" * 70)
    print("✅ TEST BASE COMPLETATI!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()

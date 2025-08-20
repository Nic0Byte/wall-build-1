"""
Soluzione intelligente per utilizzare lo spazio rimanente:
blocchi con altezza adattiva per l'ultima riga.
"""

import main
from shapely.geometry import box


def test_adaptive_height_packing():
    """Testa packing con altezza adattiva per l'ultima riga."""
    
    print("🔧 TEST PACKING CON ALTEZZA ADATTIVA")
    print("=" * 45)
    
    # Parse file
    with open("ROTTINI_LAY_REV0.svg", 'rb') as f:
        svg_bytes = f.read()
    
    parete, aperture = main.parse_wall_file(svg_bytes, "ROTTINI_LAY_REV0.svg")
    bounds = parete.bounds
    
    print(f"📏 Parete: {bounds[2]-bounds[0]:.0f}×{bounds[3]-bounds[1]:.0f}mm")
    
    # Calcola numero di righe complete
    altezza_blocco = 413
    altezza_parete = bounds[3] - bounds[1]
    
    righe_complete = int(altezza_parete / altezza_blocco)
    spazio_ultima_riga = altezza_parete - (righe_complete * altezza_blocco)
    
    print(f"📊 Righe complete: {righe_complete}")
    print(f"📊 Spazio ultima riga: {spazio_ultima_riga:.0f}mm")
    
    # Strategia 1: Packing con righe complete + ultima riga ridotta
    if spazio_ultima_riga >= 150:  # Minimo ragionevole per blocchi
        print(f"✅ Spazio utilizzabile per ultima riga: {spazio_ultima_riga:.0f}mm")
        
        # Simula packing in due fasi
        print(f"\n🔄 SIMULAZIONE PACKING OTTIMIZZATO:")
        
        # Fase 1: Righe complete
        area_righe_complete = (bounds[2] - bounds[0]) * (righe_complete * altezza_blocco)
        print(f"   📐 Area righe complete: {area_righe_complete:,.0f} mm²")
        
        # Fase 2: Ultima riga con altezza ridotta  
        area_ultima_riga = (bounds[2] - bounds[0]) * spazio_ultima_riga
        print(f"   📐 Area ultima riga: {area_ultima_riga:,.0f} mm²")
        
        # Stima blocchi ultima riga
        larghezza_blocco_min = 413  # Larghezza minima
        blocchi_ultima_riga = int((bounds[2] - bounds[0]) / larghezza_blocco_min)
        area_blocchi_ultima = blocchi_ultima_riga * larghezza_blocco_min * spazio_ultima_riga
        
        print(f"   🧱 Blocchi stimati ultima riga: {blocchi_ultima_riga}")
        print(f"   📊 Area recuperata: {area_blocchi_ultima:,.0f} mm²")
        
        # Calcolo guadagno
        guadagno_percentuale = area_blocchi_ultima / parete.area * 100
        print(f"   📈 Guadagno: {guadagno_percentuale:.1f}% dell'area totale")
        
        return {
            'spazio_utilizzabile': spazio_ultima_riga,
            'blocchi_extra': blocchi_ultima_riga,
            'area_recuperata': area_blocchi_ultima,
            'guadagno_pct': guadagno_percentuale
        }
    else:
        print(f"❌ Spazio troppo piccolo: {spazio_ultima_riga:.0f}mm < 150mm minimo")
        return None


def propose_smart_solution():
    """Propone soluzione intelligente per il problema."""
    
    print(f"\n💡 PROPOSTA SOLUZIONE INTELLIGENTE")
    print("=" * 40)
    
    print("""
🎯 STRATEGIA PROPOSTA:

1. **PACKING A DUE FASI:**
   - Fase 1: Righe complete con blocchi 413mm
   - Fase 2: Ultima riga con blocchi altezza adattiva

2. **CONTROLLI DINAMICI:**
   - Se spazio_rimanente >= 150mm → Utilizza con altezza adattiva
   - Se spazio_rimanente < 150mm → Stop packing
   - Altezza_ultima_riga = min(spazio_disponibile, 413mm)

3. **VANTAGGI:**
   ✅ Nessun blocco fuori parete (altezza <= spazio)
   ✅ Massimo utilizzo spazio disponibile
   ✅ Algoritmo robusto e prevedibile
   ✅ Mantenimento qualità costruttiva

4. **IMPLEMENTAZIONE:**
   - Modifica pack_wall per gestire ultima riga separatamente
   - Blocchi ultima riga: altezza = spazio_rimanente
   - Controllo bounds rigoroso per sicurezza
""")


def test_current_vs_proposed():
    """Confronta risultati attuali vs proposti."""
    
    print(f"\n📊 CONFRONTO SOLUZIONI")
    print("=" * 30)
    
    # Test attuale
    with open("ROTTINI_LAY_REV0.svg", 'rb') as f:
        svg_bytes = f.read()
    
    parete, aperture = main.parse_wall_file(svg_bytes, "ROTTINI_LAY_REV0.svg")
    
    # Packing attuale
    placed_blocks, custom_pieces = main.pack_wall(
        parete, [1239, 826, 413], 413, row_offset=826, apertures=aperture
    )
    
    # Analisi attuale
    area_coperta_attuale = 0
    max_y_attuale = 0
    
    for block in placed_blocks:
        w = block.get('width', 0)
        h = block.get('height', 0)
        y = block.get('y', 0)
        area_coperta_attuale += w * h
        max_y_attuale = max(max_y_attuale, y + h)
    
    bounds = parete.bounds
    spazio_sprecato_attuale = bounds[3] - max_y_attuale
    
    print(f"📈 SOLUZIONE ATTUALE:")
    print(f"   🧱 Blocchi: {len(placed_blocks)}")
    print(f"   📊 Area coperta: {area_coperta_attuale:,.0f} mm²")
    print(f"   🗑️ Spazio sprecato: {spazio_sprecato_attuale:.0f} mm")
    
    # Stima soluzione proposta
    adaptive_result = test_adaptive_height_packing()
    
    if adaptive_result:
        print(f"\n📈 SOLUZIONE PROPOSTA:")
        print(f"   🧱 Blocchi extra: +{adaptive_result['blocchi_extra']}")
        print(f"   📊 Area recuperata: +{adaptive_result['area_recuperata']:,.0f} mm²")
        print(f"   📈 Guadagno: +{adaptive_result['guadagno_pct']:.1f}%")
        print(f"   🗑️ Spazio sprecato: ~0 mm")
        
        print(f"\n🎯 MIGLIORAMENTO:")
        miglioramento = adaptive_result['area_recuperata']
        pct_miglioramento = miglioramento / area_coperta_attuale * 100
        print(f"   📊 +{miglioramento:,.0f} mm² ({pct_miglioramento:.1f}% in più)")
        print(f"   🔧 Riduzione spreco: {spazio_sprecato_attuale:.0f}mm → 0mm")


if __name__ == "__main__":
    # Test completo
    adaptive_result = test_adaptive_height_packing()
    propose_smart_solution()
    test_current_vs_proposed()
    
    print(f"\n🏁 CONCLUSIONE:")
    if adaptive_result and adaptive_result['guadagno_pct'] > 1:
        print(f"✅ Implementazione soluzione adattiva RACCOMANDATA")
        print(f"📈 Guadagno stimato: {adaptive_result['guadagno_pct']:.1f}%")
    else:
        print(f"ℹ️ Soluzione attuale accettabile, miglioramento marginale")

/**
 * Helper functions per configurazione moraletti
 * Utilizzato dal Small Algorithm per packing con moraletti alignment
 */

// ────────────────────────────────────────────────────────────────────────────────
// Funzione per ottenere configurazione moraletti per il backend
// ────────────────────────────────────────────────────────────────────────────────
function getMoralettiConfigForBackend() {
    console.log('📍 Raccogliendo configurazione moraletti per backend...');
    
    // Prova a ottenere da window.currentMoralettiConfig (salvato)
    if (window.currentMoralettiConfig) {
        console.log('✅ Usando configurazione moraletti salvata:', window.currentMoralettiConfig);
        return {
            spacing_mm: window.currentMoralettiConfig.spacing || 420,
            max_moraletti_large: window.currentMoralettiConfig.countLarge || 3,
            max_moraletti_medium: window.currentMoralettiConfig.countMedium || 2,
            max_moraletti_small: window.currentMoralettiConfig.countSmall || 1
        };
    }
    
    // Fallback: leggi direttamente dai campi input
    const spacing = parseInt(document.getElementById('moralettiSpacing')?.value) || 420;
    const countLarge = parseInt(document.getElementById('moralettiCountLarge')?.value) || 3;
    const countMedium = parseInt(document.getElementById('moralettiCountMedium')?.value) || 2;
    const countSmall = parseInt(document.getElementById('moralettiCountSmall')?.value) || 1;
    
    console.log('⚠️ Usando valori moraletti dai campi input (non salvati)');
    return {
        spacing_mm: spacing,
        max_moraletti_large: countLarge,
        max_moraletti_medium: countMedium,
        max_moraletti_small: countSmall
    };
}

console.log('✅ moraletti-helper.js caricato');

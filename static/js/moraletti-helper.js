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
        
        // Default dinamico per spacing: usa blocco più piccolo se disponibile
        const defaultSpacing = window.currentBlockWidths?.[2] || 413;
        
        return {
            // Spaziatura e counts
            spacing_mm: window.currentMoralettiConfig.spacing || defaultSpacing,
            max_moraletti_large: window.currentMoralettiConfig.countLarge || 3,
            max_moraletti_medium: window.currentMoralettiConfig.countMedium || 2,
            max_moraletti_small: window.currentMoralettiConfig.countSmall || 1,
            
            // Dimensioni moraletti
            thickness_mm: window.currentMoralettiConfig.thickness || 58,
            height_mm: window.currentMoralettiConfig.height || 495,
            height_from_ground_mm: window.currentMoralettiConfig.heightFromGround || 95
        };
    }
    
    // Fallback: leggi direttamente dai campi input
    // Default dinamico per spacing
    const defaultSpacing = window.currentBlockWidths?.[2] || 413;
    
    const spacing = parseInt(document.getElementById('moralettiSpacing')?.value) || defaultSpacing;
    const countLarge = parseInt(document.getElementById('moralettiCountLarge')?.value) || 3;
    const countMedium = parseInt(document.getElementById('moralettiCountMedium')?.value) || 2;
    const countSmall = parseInt(document.getElementById('moralettiCountSmall')?.value) || 1;
    
    // Leggi dimensioni moraletti dai campi (se esistono)
    const thickness = parseInt(document.getElementById('moralettiThickness')?.value) || 58;
    const height = parseInt(document.getElementById('moralettiHeight')?.value) || 495;
    const heightFromGround = parseInt(document.getElementById('moralettiHeightFromGround')?.value) || 95;
    
    console.log('⚠️ Usando valori moraletti dai campi input (non salvati)');
    return {
        // Spaziatura e counts
        spacing_mm: spacing,
        max_moraletti_large: countLarge,
        max_moraletti_medium: countMedium,
        max_moraletti_small: countSmall,
        
        // Dimensioni moraletti
        thickness_mm: thickness,
        height_mm: height,
        height_from_ground_mm: heightFromGround
    };
}

console.log('✅ moraletti-helper.js caricato');

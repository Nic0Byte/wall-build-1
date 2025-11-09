// ================================================================
// WALL INNER OFFSET CONFIGURATION SYSTEM
// ================================================================

/**
 * Toggle offset configuration panel visibility
 */
function toggleOffsetPanel() {
    const panel = document.getElementById('offsetPanel');
    const icon = document.getElementById('offsetExpandIcon');
    
    if (!panel || !icon) {
        console.error('❌ Offset panel elements not found');
        return;
    }
    
    const isVisible = panel.style.display !== 'none';
    
    if (isVisible) {
        // Close panel
        panel.style.display = 'none';
        icon.classList.remove('expanded');
        console.log('📐 Offset panel closed');
    } else {
        // Close all other panels first
        if (typeof closeAllSettingsPanels === 'function') {
            closeAllSettingsPanels();
        }
        
        // Open panel
        panel.style.display = 'block';
        icon.classList.add('expanded');
        
        // Initialize offset configuration if not already done
        if (!window.offsetConfigInitialized) {
            initializeOffsetConfiguration();
            window.offsetConfigInitialized = true;
        }
        
        console.log('📐 Offset panel opened');
    }
}

/**
 * Initialize offset configuration from localStorage
 */
function initializeOffsetConfiguration() {
    console.log('📐 Initializing Wall Inner Offset Configuration');
    
    // Load saved configuration from localStorage
    const savedConfig = localStorage.getItem('wallInnerOffsetConfig');
    let config = {
        enabled: false,
        distance_mm: 50
    };
    
    if (savedConfig) {
        try {
            config = JSON.parse(savedConfig);
            console.log('✅ Loaded saved offset config:', config);
        } catch (e) {
            console.warn('⚠️ Error parsing saved offset config, using defaults');
        }
    } else {
        console.log('📦 No saved offset config, using defaults (disabled, 50mm)');
    }
    
    // Apply configuration to UI
    const enableCheckbox = document.getElementById('enableInnerOffset');
    const offsetInput = document.getElementById('offsetDistance');
    const offsetSlider = document.getElementById('offsetSlider');
    const offsetSection = document.getElementById('offsetInputSection');
    
    if (enableCheckbox) {
        enableCheckbox.checked = config.enabled;
        
        // Setup checkbox change handler
        enableCheckbox.addEventListener('change', function() {
            const enabled = this.checked;
            if (offsetSection) {
                offsetSection.style.display = enabled ? 'block' : 'none';
            }
            console.log(`📐 Offset ${enabled ? 'enabled' : 'disabled'}`);
        });
        
        // Trigger initial state
        if (offsetSection) {
            offsetSection.style.display = config.enabled ? 'block' : 'none';
        }
    }
    
    if (offsetInput && offsetSlider) {
        offsetInput.value = config.distance_mm;
        offsetSlider.value = config.distance_mm;
        updateOffsetInfo();
    }
    
    // Store current config globally
    window.currentOffsetConfig = config;
    
    console.log('✅ Offset configuration initialized');
}

/**
 * Update offset info display when value changes
 */
function updateOffsetInfo() {
    const offsetInput = document.getElementById('offsetDistance');
    const offsetSlider = document.getElementById('offsetSlider');
    const display = document.getElementById('offsetValueDisplay');
    
    if (!offsetInput || !display) return;
    
    const value = parseInt(offsetInput.value) || 0;
    
    // Sync slider with input
    if (offsetSlider) {
        offsetSlider.value = value;
    }
    
    // Update display
    display.textContent = `${value}mm`;
    
    console.log(`📐 Offset value updated: ${value}mm`);
}

/**
 * Update offset input when slider changes
 */
function updateOffsetFromSlider() {
    const offsetSlider = document.getElementById('offsetSlider');
    const offsetInput = document.getElementById('offsetDistance');
    
    if (!offsetSlider || !offsetInput) return;
    
    const value = parseInt(offsetSlider.value);
    offsetInput.value = value;
    
    // Update info display
    updateOffsetInfo();
}

/**
 * Save offset configuration to localStorage
 */
function saveOffsetConfiguration() {
    console.log('💾 Saving offset configuration...');
    
    const enableCheckbox = document.getElementById('enableInnerOffset');
    const offsetInput = document.getElementById('offsetDistance');
    const feedback = document.getElementById('offsetSaveFeedback');
    
    if (!enableCheckbox || !offsetInput) {
        console.error('❌ Offset configuration elements not found');
        return;
    }
    
    const config = {
        enabled: enableCheckbox.checked,
        distance_mm: parseInt(offsetInput.value) || 50
    };
    
    // Validate distance
    if (config.distance_mm < 0 || config.distance_mm > 500) {
        alert('⚠️ La distanza di offset deve essere tra 0 e 500 mm');
        return;
    }
    
    try {
        // Save to localStorage
        localStorage.setItem('wallInnerOffsetConfig', JSON.stringify(config));
        
        // Update global variable
        window.currentOffsetConfig = config;
        
        // Show success feedback
        if (feedback) {
            feedback.style.display = 'flex';
            setTimeout(() => {
                feedback.style.display = 'none';
            }, 3000);
        }
        
        console.log('✅ Offset configuration saved:', config);
        
        // Show toast notification if available
        if (typeof app !== 'undefined' && typeof app.showToast === 'function') {
            app.showToast(
                `Offset ${config.enabled ? 'abilitato' : 'disabilitato'} (${config.distance_mm}mm) salvato con successo`,
                'success'
            );
        }
        
    } catch (e) {
        console.error('❌ Error saving offset configuration:', e);
        alert('❌ Errore durante il salvataggio della configurazione offset');
    }
}

/**
 * Get current offset configuration
 * @returns {Object} Current offset config {enabled: boolean, distance_mm: number}
 */
function getCurrentOffsetConfig() {
    // Try global variable first
    if (window.currentOffsetConfig) {
        return window.currentOffsetConfig;
    }
    
    // Try localStorage
    const saved = localStorage.getItem('wallInnerOffsetConfig');
    if (saved) {
        try {
            return JSON.parse(saved);
        } catch (e) {
            console.warn('⚠️ Error parsing offset config from localStorage');
        }
    }
    
    // Default: disabled, 50mm
    return {
        enabled: false,
        distance_mm: 50
    };
}

console.log('✅ Wall Inner Offset Configuration system loaded');

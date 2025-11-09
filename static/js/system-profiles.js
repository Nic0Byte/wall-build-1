/**
 * System Profiles Management
 * Gestisce la creazione, modifica, eliminazione e attivazione dei profili sistema
 */

// ────────────────────────────────────────────────────────────────────────────────
// State Management
// ────────────────────────────────────────────────────────────────────────────────

let systemProfiles = [];
let currentEditingProfileId = null;
let isLoadingProfile = false; // Flag per tracciare se stiamo caricando un profilo

// ────────────────────────────────────────────────────────────────────────────────
// Initialization
// ────────────────────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', function() {
    console.log('📋 Sistema Profili: Inizializzazione...');
    
    // Aspetta che authManager sia pronto
    if (window.authManager && window.authManager.token) {
        console.log('✅ authManager trovato, caricamento profili...');
        loadSystemProfiles();
    } else {
        console.log('⏳ Attesa authManager...');
        // Riprova dopo un breve delay per permettere l'inizializzazione
        setTimeout(() => {
            if (window.authManager && window.authManager.token) {
                console.log('✅ authManager ora disponibile, caricamento profili...');
                loadSystemProfiles();
            } else {
                console.log('⚠️ authManager non disponibile, utente non loggato');
                loadSystemProfiles(); // Prova comunque, gestirà l'assenza di token
            }
        }, 500);
    }
    
    setupProfileEventListeners();
});

function setupProfileEventListeners() {
    // Event listener per selector profilo attivo
    const selector = document.getElementById('activeProfileSelector');
    if (selector) {
        selector.addEventListener('change', function(e) {
            const profileId = parseInt(e.target.value);
            if (profileId) {
                activateProfile(profileId);
                updateProfileDisplay(profileId); // Aggiorna la visualizzazione nello Step 3
                
                // Update current profile name in app instance
                if (window.wallPackingApp && window.systemProfiles) {
                    const profile = window.systemProfiles.find(p => p.id === profileId);
                    if (profile) {
                        window.wallPackingApp.currentProfileName = profile.name;
                        console.log('📋 Profile name aggiornato da selector:', profile.name);
                    }
                }
            }
        });
    }
}

// Funzione per aggiornare la visualizzazione del profilo nello Step 3
function updateProfileDisplay(profileId) {
    const profile = systemProfiles.find(p => p.id === profileId);
    if (!profile) return;
    
    const nameElement = document.getElementById('displayedProfileName');
    const descElement = document.getElementById('displayedProfileDesc');
    const specsElement = document.getElementById('displayedProfileSpecs');
    const blocksCountElement = document.getElementById('displayedBlocksCount');
    const algorithmElement = document.getElementById('displayedAlgorithmType');
    const summarySystemElement = document.getElementById('summarySystem');
    
    if (nameElement) {
        nameElement.textContent = (profile.is_default ? '⭐ ' : '') + profile.name;
    }
    
    if (descElement) {
        descElement.textContent = profile.description || 'Profilo sistema configurato';
    }
    
    if (specsElement && blocksCountElement) {
        // Conta i blocchi configurati
        const blockCount = profile.block_config ? 
            (profile.block_config.widths ? profile.block_config.widths.length : 3) : 3;
        
        blocksCountElement.textContent = `${blockCount} blocchi configurati`;
        specsElement.style.display = 'flex';
    }
    
    // NUOVO: Visualizza algoritmo e SALVA GLOBALMENTE per il packing
    if (algorithmElement) {
        const algorithmType = profile.algorithm_type || 'small';
        const algorithmIcon = algorithmType === 'big' ? '🏭' : '🏠';
        const algorithmName = algorithmType === 'big' ? 
            'BIG - Industriale (sfalsato)' : 
            'SMALL - Residenziale (allineato)';
        
        // 🔥 NUOVO: Salva algorithm_type globalmente per il packing
        window.currentAlgorithmType = algorithmType;
        console.log(`🧠 Algorithm type del profilo attivo: ${algorithmType}`);
        
        algorithmElement.textContent = `${algorithmIcon} ${algorithmName}`;
        algorithmElement.className = `algorithm-badge-inline ${algorithmType}`;
    }
    
    // Aggiorna anche il riepilogo parametri
    if (summarySystemElement) {
        summarySystemElement.textContent = profile.name;
    }
}

// Aggiorna la visualizzazione quando viene caricato il profilo default
function updateDefaultProfileDisplay() {
    const defaultProfile = systemProfiles.find(p => p.is_default);
    if (defaultProfile) {
        updateProfileDisplay(defaultProfile.id);
    }
}

// ────────────────────────────────────────────────────────────────────────────────
// API Calls
// ────────────────────────────────────────────────────────────────────────────────

async function loadSystemProfiles() {
    try {
        const token = getAuthToken();
        
        // Debug: mostra il token trovato
        console.log('🔑 Token trovato:', token ? 'SÌ (lunghezza: ' + token.length + ')' : 'NO');
        
        if (!token) {
            console.log('⚠️ Nessun token di autenticazione, profili non disponibili');
            renderEmptyProfiles();
            return;
        }

        const response = await fetch('/api/v1/profiles', {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        console.log('📡 Response status:', response.status);

        if (response.status === 403 || response.status === 401) {
            console.log('⚠️ Autenticazione richiesta per i profili');
            const errorData = await response.json().catch(() => ({}));
            console.log('Error details:', errorData);
            renderEmptyProfiles();
            return;
        }

        if (!response.ok) {
            throw new Error('Errore caricamento profili');
        }

        systemProfiles = await response.json();
        console.log(`✅ Caricati ${systemProfiles.length} profili`);
        
        renderProfilesList();
        renderProfileSelector();
        updateDefaultProfileDisplay(); // Aggiorna la visualizzazione del profilo default
        
    } catch (error) {
        console.error('❌ Errore caricamento profili:', error);
        renderEmptyProfiles();
    }
}

function renderEmptyProfiles() {
    const container = document.getElementById('systemProfilesList');
    const selector = document.getElementById('activeProfileSelector');
    
    if (container) {
        container.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-lock"></i>
                <p>Effettua il login per gestire i profili sistema</p>
            </div>
        `;
    }
    
    if (selector) {
        selector.innerHTML = '<option value="">Login richiesto</option>';
    }
}

async function activateProfile(profileId) {
    try {
        showToast('Caricamento configurazione...', 'info');
        
        // Imposta il flag per indicare che stiamo caricando un profilo
        isLoadingProfile = true;
        window.isLoadingProfile = true; // Rendi disponibile globalmente
        
        const response = await fetch(`/api/v1/profiles/${profileId}/activate`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${getAuthToken()}`,
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            throw new Error('Errore attivazione profilo');
        }

        const data = await response.json();
        
        console.log('📋 Pre-caricamento dati profilo:', data.profile_name);
        
        // Update current profile name and algorithm_type in app instance
        if (window.wallPackingApp) {
            window.wallPackingApp.currentProfileName = data.profile_name;
            console.log('💾 Profile name aggiornato in app instance:', data.profile_name);
        }
        
        // 🔥 NUOVO: Salva algorithm_type del profilo caricato
        if (data.algorithm_type) {
            window.currentAlgorithmType = data.algorithm_type;
            console.log(`🧠 Algorithm type del profilo caricato: ${data.algorithm_type}`);
        }
        
        // 1. Chiudi tutti i pannelli prima
        if (typeof closeAllSettingsPanels === 'function') {
            closeAllSettingsPanels();
        }
        
        // 2. Apri il pannello "Configurazione Blocchi" PRIMA di applicare i valori
        const blockPanel = document.getElementById('blockDimensionsPanel');
        const blockIcon = document.getElementById('blockDimensionsExpandIcon');
        if (blockPanel && blockIcon) {
            blockPanel.style.display = 'block';
            blockIcon.classList.add('expanded');
            
            // Inizializza se necessario
            if (!window.blockDimensionsInitialized && typeof initializeBlockDimensions === 'function') {
                initializeBlockDimensions();
                window.blockDimensionsInitialized = true;
            }
            
            console.log('📦 Pannello Configurazione Blocchi aperto');
        }
        
        // 3. Aspetta che il DOM sia pronto, poi applica i valori
        setTimeout(() => {
            // Pre-carica configurazione blocchi nei campi (SENZA salvare)
            applyBlockConfig(data.block_config, data.algorithm_type);
            console.log('✅ Dati blocchi pre-caricati nei campi');
            
            // SALVA la configurazione moraletti per applicarla dopo (quando il pannello si aprirà)
            window.pendingMoralettiConfig = data.moraletti_config;
            console.log('💾 Configurazione moraletti salvata per applicazione successiva');
            
            // Aggiorna i preview dei blocchi con le nuove dimensioni
            if (typeof updateBlockPreviews === 'function') {
                updateBlockPreviews();
            }
        }, 300);
        
        // 4. Scroll verso il pannello blocchi per visibilità
        setTimeout(() => {
            const blockCard = document.querySelector('.block-dimensions-card');
            if (blockCard) {
                blockCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
        }, 400);
        
        showToast(`✅ Profilo "${data.profile_name}" caricato. Conferma le configurazioni per applicarle.`, 'success');
        
    } catch (error) {
        console.error('❌ Errore attivazione profilo:', error);
        showToast('Errore nell\'attivazione del profilo', 'error');
    }
}

async function deleteProfile(profileId, profileName) {
    if (!confirm(`Sei sicuro di voler eliminare il profilo "${profileName}"?`)) {
        return;
    }

    try {
        const response = await fetch(`/api/v1/profiles/${profileId}`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${getAuthToken()}`
            }
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Errore eliminazione profilo');
        }

        showToast(`Profilo "${profileName}" eliminato`, 'success');
        await loadSystemProfiles();
        
    } catch (error) {
        console.error('❌ Errore eliminazione profilo:', error);
        showToast(error.message, 'error');
    }
}

// ────────────────────────────────────────────────────────────────────────────────
// Configuration Application
// ────────────────────────────────────────────────────────────────────────────────

function applyBlockConfig(config, algorithmType = 'small') {
    console.log('📦 Applicazione configurazione blocchi:', config);
    console.log('🧠 Algoritmo:', algorithmType);
    
    // Blocco 1
    const block1Width = document.getElementById('block1Width');
    const block1Height = document.getElementById('block1Height');
    
    console.log('🔍 Elementi trovati:', {
        block1Width: !!block1Width,
        block1Height: !!block1Height,
        valori: config
    });
    
    if (block1Width) {
        block1Width.value = config.widths[0];
        console.log('✅ Block1 Width impostato:', block1Width.value);
    }
    if (block1Height) {
        block1Height.value = config.heights[0];
        console.log('✅ Block1 Height impostato:', block1Height.value);
    }
    
    // Blocco 2
    const block2Width = document.getElementById('block2Width');
    const block2Height = document.getElementById('block2Height');
    if (block2Width) {
        block2Width.value = config.widths[1];
        console.log('✅ Block2 Width impostato:', block2Width.value);
    }
    if (block2Height) {
        block2Height.value = config.heights[1];
        console.log('✅ Block2 Height impostato:', block2Height.value);
    }
    
    // Blocco 3
    const block3Width = document.getElementById('block3Width');
    const block3Height = document.getElementById('block3Height');
    if (block3Width) {
        block3Width.value = config.widths[2];
        console.log('✅ Block3 Width impostato:', block3Width.value);
    }
    if (block3Height) {
        block3Height.value = config.heights[2];
        console.log('✅ Block3 Height impostato:', block3Height.value);
    }
    
    // 🏭 Gestisci visibilità blocchi B e C in base all'algoritmo
    toggleBlocksBCVisibilityInStep2(algorithmType);
    
    // Trigger change events per aggiornare UI
    const elements = [block1Width, block1Height, block2Width, block2Height, block3Width, block3Height];
    elements.forEach(el => {
        if (el) {
            el.dispatchEvent(new Event('input', { bubbles: true }));
            el.dispatchEvent(new Event('change', { bubbles: true }));
        }
    });
    
    console.log('✅ Tutti i valori blocchi applicati e eventi triggerati');
}

function applyMoralettiConfig(config) {
    console.log('🔩 Applicazione configurazione moraletti:', config);
    
    // Parametri base
    const thickness = document.getElementById('moralettiThickness');
    const height = document.getElementById('moralettiHeight');
    const heightFromGround = document.getElementById('moralettiHeightFromGround');
    const spacing = document.getElementById('moralettiSpacing');
    
    console.log('🔍 Elementi moraletti trovati:', {
        thickness: !!thickness,
        height: !!height,
        heightFromGround: !!heightFromGround,
        spacing: !!spacing
    });
    
    if (thickness) {
        thickness.value = config.thickness;
        console.log('✅ Thickness impostato:', thickness.value);
    }
    if (height) {
        height.value = config.height;
        console.log('✅ Height impostato:', height.value);
    }
    if (heightFromGround) {
        heightFromGround.value = config.heightFromGround;
        console.log('✅ HeightFromGround impostato:', heightFromGround.value);
    }
    if (spacing) {
        spacing.value = config.spacing;
        console.log('✅ Spacing impostato:', spacing.value);
    }
    
    // Contatori
    const countLarge = document.getElementById('moralettiCountLarge');
    const countMedium = document.getElementById('moralettiCountMedium');
    const countSmall = document.getElementById('moralettiCountSmall');
    
    console.log('🔍 Contatori moraletti trovati:', {
        countLarge: !!countLarge,
        countMedium: !!countMedium,
        countSmall: !!countSmall
    });
    
    if (countLarge) {
        countLarge.value = config.countLarge;
        console.log('✅ CountLarge impostato:', countLarge.value);
    }
    if (countMedium) {
        countMedium.value = config.countMedium;
        console.log('✅ CountMedium impostato:', countMedium.value);
    }
    if (countSmall) {
        countSmall.value = config.countSmall;
        console.log('✅ CountSmall impostato:', countSmall.value);
    }
    
    // Trigger change events
    const elements = [thickness, height, heightFromGround, spacing, countLarge, countMedium, countSmall];
    elements.forEach(el => {
        if (el) {
            el.dispatchEvent(new Event('input', { bubbles: true }));
            el.dispatchEvent(new Event('change', { bubbles: true }));
        }
    });
    
    console.log('✅ Tutti i valori moraletti applicati e eventi triggerati');
}

// ────────────────────────────────────────────────────────────────────────────────
// UI Rendering
// ────────────────────────────────────────────────────────────────────────────────

function renderProfileSelector() {
    const selector = document.getElementById('activeProfileSelector');
    if (!selector) return;
    
    if (systemProfiles.length === 0) {
        selector.innerHTML = '<option value="">Nessun profilo</option>';
        return;
    }
    
    // Trova profilo default
    const defaultProfile = systemProfiles.find(p => p.is_default);
    
    selector.innerHTML = systemProfiles.map(profile => `
        <option value="${profile.id}" ${profile.is_default ? 'selected' : ''}>
            ${profile.is_default ? '⭐ ' : ''}${profile.name}
        </option>
    `).join('');
}

function renderProfilesList() {
    const container = document.getElementById('systemProfilesList');
    if (!container) return;
    
    if (systemProfiles.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-inbox"></i>
                <p>Nessun profilo sistema ancora creato</p>
                <span>Crea il tuo primo profilo usando il pulsante sopra</span>
            </div>
        `;
        return;
    }
    
    container.innerHTML = systemProfiles.map(profile => {
        const blockConfig = profile.block_config;
        const moralettiConfig = profile.moraletti_config;
        const algorithmType = profile.algorithm_type || 'small';
        const algorithmIcon = algorithmType === 'big' ? '🏭' : '🏠';
        const algorithmName = algorithmType === 'big' ? 'Industriale (sfalsato)' : 'Residenziale (allineato)';
        
        // 🏭 Mostra blocchi in base all'algoritmo
        const blocksDisplay = algorithmType === 'big' 
            ? `Tipo A: ${blockConfig.widths[0]}×${blockConfig.heights[0]}mm` 
            : `${blockConfig.widths[0]}×${blockConfig.heights[0]}mm, ${blockConfig.widths[1]}×${blockConfig.heights[1]}mm, ${blockConfig.widths[2]}×${blockConfig.heights[2]}mm`;
        
        return `
            <div class="profile-card" data-profile-id="${profile.id}">
                <div class="profile-header">
                    <div>
                        <h4>${profile.is_default ? '⭐ ' : ''}${profile.name}</h4>
                        ${profile.description ? `<p class="profile-description">${profile.description}</p>` : ''}
                    </div>
                    <div class="profile-actions">
                        <button onclick="editProfile(${profile.id})" class="btn-icon" title="Modifica">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button onclick="deleteProfile(${profile.id}, '${profile.name}')" class="btn-icon" title="Elimina">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </div>
                <div class="profile-details">
                    <div class="detail-section">
                        <strong>🧠 Algoritmo:</strong>
                        <div class="algorithm-badge ${algorithmType}">${algorithmIcon} ${algorithmName}</div>
                    </div>
                    <div class="detail-section">
                        <strong>📦 Blocchi:</strong>
                        <span>${blocksDisplay}</span>
                    </div>
                    <div class="detail-section">
                        <strong>🔩 Moraletti:</strong>
                        <span>${moralettiConfig.countLarge}-${moralettiConfig.countMedium}-${moralettiConfig.countSmall}, Spaziatura ${moralettiConfig.spacing}mm</span>
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

// ────────────────────────────────────────────────────────────────────────────────
// Modal Management
// ────────────────────────────────────────────────────────────────────────────────

function openProfileModal(profileId = null) {
    const modal = document.getElementById('profileModal');
    const title = document.getElementById('profileModalTitle');
    
    if (profileId) {
        // Edit mode
        currentEditingProfileId = profileId;
        const profile = systemProfiles.find(p => p.id === profileId);
        
        if (!profile) {
            showToast('Profilo non trovato', 'error');
            return;
        }
        
        title.textContent = 'Modifica Profilo Sistema';
        populateModalWithProfile(profile);
    } else {
        // Create mode
        currentEditingProfileId = null;
        title.textContent = 'Crea Nuovo Profilo Sistema';
        resetModalFields();
    }
    
    modal.style.display = 'flex';
}

function closeProfileModal() {
    const modal = document.getElementById('profileModal');
    modal.style.display = 'none';
    currentEditingProfileId = null;
}

function populateModalWithProfile(profile) {
    // Info
    document.getElementById('profileName').value = profile.name;
    document.getElementById('profileDescription').value = profile.description || '';
    
    // Blocchi
    const blockConfig = profile.block_config;
    document.getElementById('modalBlock1Width').value = blockConfig.widths[0];
    document.getElementById('modalBlock1Height').value = blockConfig.heights[0];
    document.getElementById('modalBlock2Width').value = blockConfig.widths[1];
    document.getElementById('modalBlock2Height').value = blockConfig.heights[1];
    document.getElementById('modalBlock3Width').value = blockConfig.widths[2];
    document.getElementById('modalBlock3Height').value = blockConfig.heights[2];
    
    // Moraletti
    const moralettiConfig = profile.moraletti_config;
    document.getElementById('modalMoralettiThickness').value = moralettiConfig.thickness;
    document.getElementById('modalMoralettiHeight').value = moralettiConfig.height;
    document.getElementById('modalMoralettiHeightFromGround').value = moralettiConfig.heightFromGround;
    document.getElementById('modalMoralettiSpacing').value = moralettiConfig.spacing;
    document.getElementById('modalMoralettiCountLarge').value = moralettiConfig.countLarge;
    document.getElementById('modalMoralettiCountMedium').value = moralettiConfig.countMedium;
    document.getElementById('modalMoralettiCountSmall').value = moralettiConfig.countSmall;
    
    // Algoritmo
    const algorithmType = profile.algorithm_type || 'small';
    document.getElementById('modalAlgorithmType').value = algorithmType;
    
    // 🏭 Gestione blocchi B e C per algoritmo BIG
    toggleBlocksBCForBigAlgorithm(algorithmType);
    
    // Default
    document.getElementById('modalIsDefault').checked = profile.is_default;
}

function resetModalFields() {
    // Info
    document.getElementById('profileName').value = '';
    document.getElementById('profileDescription').value = '';
    
    // Blocchi (valori default)
    document.getElementById('modalBlock1Width').value = 1239;
    document.getElementById('modalBlock1Height').value = 495;
    document.getElementById('modalBlock2Width').value = 826;
    document.getElementById('modalBlock2Height').value = 495;
    document.getElementById('modalBlock3Width').value = 413;
    document.getElementById('modalBlock3Height').value = 495;
    
    // Moraletti (valori default)
    document.getElementById('modalMoralettiThickness').value = 58;
    document.getElementById('modalMoralettiHeight').value = 495;
    document.getElementById('modalMoralettiHeightFromGround').value = 95;
    document.getElementById('modalMoralettiSpacing').value = 420;
    document.getElementById('modalMoralettiCountLarge').value = 3;
    document.getElementById('modalMoralettiCountMedium').value = 2;
    document.getElementById('modalMoralettiCountSmall').value = 1;
    
    // Algoritmo (default SMALL)
    document.getElementById('modalAlgorithmType').value = 'small';
    
    // 🏭 Abilita blocchi B e C per algoritmo SMALL (default)
    toggleBlocksBCForBigAlgorithm('small');
    
    // Default
    document.getElementById('modalIsDefault').checked = false;
}

async function saveProfile() {
    // Validazione
    const name = document.getElementById('profileName').value.trim();
    if (!name) {
        showToast('Inserisci un nome per il profilo', 'error');
        return;
    }
    
    // Raccogli dati
    const profileData = {
        name: name,
        description: document.getElementById('profileDescription').value.trim() || null,
        block_config: {
            widths: [
                parseInt(document.getElementById('modalBlock1Width').value),
                parseInt(document.getElementById('modalBlock2Width').value),
                parseInt(document.getElementById('modalBlock3Width').value)
            ],
            heights: [
                parseInt(document.getElementById('modalBlock1Height').value),
                parseInt(document.getElementById('modalBlock2Height').value),
                parseInt(document.getElementById('modalBlock3Height').value)
            ]
        },
        moraletti_config: {
            thickness: parseInt(document.getElementById('modalMoralettiThickness').value),
            height: parseInt(document.getElementById('modalMoralettiHeight').value),
            heightFromGround: parseInt(document.getElementById('modalMoralettiHeightFromGround').value),
            spacing: parseInt(document.getElementById('modalMoralettiSpacing').value),
            countLarge: parseInt(document.getElementById('modalMoralettiCountLarge').value),
            countMedium: parseInt(document.getElementById('modalMoralettiCountMedium').value),
            countSmall: parseInt(document.getElementById('modalMoralettiCountSmall').value)
        },
        algorithm_type: document.getElementById('modalAlgorithmType').value,
        is_default: document.getElementById('modalIsDefault').checked
    };
    
    try {
        const url = currentEditingProfileId 
            ? `/api/v1/profiles/${currentEditingProfileId}`
            : '/api/v1/profiles';
        
        const method = currentEditingProfileId ? 'PUT' : 'POST';
        
        const response = await fetch(url, {
            method: method,
            headers: {
                'Authorization': `Bearer ${getAuthToken()}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(profileData)
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Errore salvataggio profilo');
        }
        
        showToast(`✅ Profilo "${name}" salvato con successo!`, 'success');
        closeProfileModal();
        await loadSystemProfiles();
        
    } catch (error) {
        console.error('❌ Errore salvataggio profilo:', error);
        showToast(error.message, 'error');
    }
}

function editProfile(profileId) {
    openProfileModal(profileId);
}

// ────────────────────────────────────────────────────────────────────────────────
// Toggle Panel
// ────────────────────────────────────────────────────────────────────────────────

function toggleSystemProfilesPanel() {
    const panel = document.getElementById('systemProfilesPanel');
    const icon = document.getElementById('systemProfilesExpandIcon');
    
    if (panel.style.display === 'none' || panel.style.display === '') {
        panel.style.display = 'block';
        icon.classList.remove('fa-chevron-down');
        icon.classList.add('fa-chevron-up');
    } else {
        panel.style.display = 'none';
        icon.classList.remove('fa-chevron-up');
        icon.classList.add('fa-chevron-down');
    }
}

// ────────────────────────────────────────────────────────────────────────────────
// Utilities
// ────────────────────────────────────────────────────────────────────────────────

function getAuthToken() {
    // Prova diverse fonti di token in ordine di priorità
    if (window.authManager && window.authManager.token) {
        return window.authManager.token;
    }
    return sessionStorage.getItem('access_token') || 
           sessionStorage.getItem('authToken') || 
           localStorage.getItem('authToken') || 
           '';
}

function showToast(message, type = 'info') {
    // Prova ad usare la funzione globale se disponibile
    if (window.wallPackingApp && typeof window.wallPackingApp.showToast === 'function') {
        window.wallPackingApp.showToast(message, type);
        return;
    }
    
    // Fallback: crea toast semplice
    const toast = document.createElement('div');
    toast.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 15px 20px;
        background: ${type === 'error' ? '#dc3545' : type === 'success' ? '#28a745' : '#17a2b8'};
        color: white;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        z-index: 10000;
        animation: slideIn 0.3s ease;
        max-width: 400px;
    `;
    toast.textContent = message;
    
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// ────────────────────────────────────────────────────────────────────────────────
// 🏭 BIG Algorithm - Gestione Blocchi B e C
// ────────────────────────────────────────────────────────────────────────────────

/**
 * Mostra/nasconde i blocchi B e C in base all'algoritmo selezionato
 * BIG algorithm usa solo blocco A, SMALL usa tutti e 3 i blocchi
 */
function toggleBlocksBCForBigAlgorithm(algorithmType) {
    const block2Section = document.getElementById('modalBlock2Section');
    const block3Section = document.getElementById('modalBlock3Section');
    
    const isBigAlgorithm = algorithmType === 'big';
    
    if (isBigAlgorithm) {
        // 🏭 ALGORITMO BIG: Nascondi blocchi B e C
        if (block2Section) {
            block2Section.style.display = 'none';
        }
        if (block3Section) {
            block3Section.style.display = 'none';
        }
        
        console.log('🏭 ALGORITMO BIG: Solo blocco A visibile. Custom tagliati da blocco A.');
    } else {
        // 🏠 ALGORITMO SMALL: Mostra tutti i blocchi
        if (block2Section) {
            block2Section.style.display = 'block';
        }
        if (block3Section) {
            block3Section.style.display = 'block';
        }
        
        console.log('� ALGORITMO SMALL: Tutti e 3 i blocchi (A, B, C) visibili.');
    }
}

/**
 * Mostra/nasconde i blocchi B e C nello Step 2 in base all'algoritmo del profilo caricato
 * BIG algorithm: solo blocco A visibile
 * SMALL algorithm: tutti i blocchi visibili
 */
function toggleBlocksBCVisibilityInStep2(algorithmType) {
    const block2Section = document.getElementById('block2Section');
    const block3Section = document.getElementById('block3Section');
    
    const isBigAlgorithm = algorithmType === 'big';
    
    // Rimuovi eventuali messaggi precedenti
    const existingInfo = document.querySelector('.big-algorithm-info-step2');
    if (existingInfo) {
        existingInfo.remove();
    }
    
    if (isBigAlgorithm) {
        // 🏭 ALGORITMO BIG: Nascondi blocchi B e C nello Step 2
        if (block2Section) {
            block2Section.style.display = 'none';
        }
        if (block3Section) {
            block3Section.style.display = 'none';
        }
        
        // Aggiungi messaggio informativo nello Step 2
        const blockDimensionsPanel = document.getElementById('blockDimensionsPanel');
        if (blockDimensionsPanel) {
            const info = document.createElement('div');
            info.className = 'big-algorithm-info-step2';
            info.style.cssText = 'margin: 15px 0; padding: 12px; background: #fff3cd; border-left: 4px solid #ffc107; border-radius: 6px; font-size: 0.9em; color: #856404;';
            info.innerHTML = '<strong>🏭 Algoritmo BIG attivo:</strong> Questo profilo usa solo il <strong>blocco A</strong>. I custom verranno tagliati dal blocco A.';
            
            // Inserisci dopo il primo blocco
            const block1Section = blockDimensionsPanel.querySelector('.block-group');
            if (block1Section && block1Section.nextSibling) {
                blockDimensionsPanel.insertBefore(info, block1Section.nextSibling);
            }
        }
        
        console.log('🏭 Step 2: Solo blocco A visibile (Algoritmo BIG)');
    } else {
        // 🏠 ALGORITMO SMALL: Mostra tutti i blocchi nello Step 2
        if (block2Section) {
            block2Section.style.display = 'block';
        }
        if (block3Section) {
            block3Section.style.display = 'block';
        }
        
        console.log('🏠 Step 2: Tutti i blocchi (A, B, C) visibili (Algoritmo SMALL)');
    }
}

// Event listener per cambio algoritmo nel modal
document.addEventListener('DOMContentLoaded', function() {
    const algorithmSelector = document.getElementById('modalAlgorithmType');
    if (algorithmSelector) {
        algorithmSelector.addEventListener('change', function(e) {
            const algorithmType = e.target.value;
            toggleBlocksBCForBigAlgorithm(algorithmType);
        });
    }
});

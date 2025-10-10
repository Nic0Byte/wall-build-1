/**
 * Parete TAKTAK® - Frontend Application
 * Complete client-side logic for SVG processing and wall packing
 */

class WallPackingApp {
    constructor() {
        this.currentFile = null;
        this.currentSessionId = null;
        this.currentData = null;
        this.currentPreviewData = null; // NEW: Store preview data
        this.previewSessionId = null; // NUOVO: Store preview session ID per riutilizzo
        this.currentSection = 'app'; // Track current section
        
        // NUOVO: Cache per le dimensioni calcolate
        this.calculatedDimensions = null;
        this.cachedWallDimensions = null;
        
        // NUOVO: Sistema di misurazione durata transizioni
        this.step1to2Duration = null; // Durata misurata Step 1→2 in millisecondi
        this.step1to2StartTime = null; // Timestamp inizio Step 1→2
        
        // Bind methods
        this.handleFileSelect = this.handleFileSelect.bind(this);
        this.handleDragOver = this.handleDragOver.bind(this);
        this.handleDrop = this.handleDrop.bind(this);
        this.handleNavigation = this.handleNavigation.bind(this);
        
        this.init();
    }
    
    async init() {
        console.log('🚀 Inizializzazione Parete TAKTAK® App');
        this.setupEventListeners();
        this.setupNavigation();
        this.showMainSection('app');
        this.showSection('upload');
        
        // Ensure blocks are unlocked at startup (no file loaded)
        this.unlockBlockDimensionsEditing();
        
        // Initialize navigation state (all sections should be accessible at startup)
        this.updateNavigationState();
        
        // Carica i valori di configurazione dinamici
        await this.loadBlockConfigurationIntoUI();
    }
    
    // ===== NAVIGATION SETUP =====
    
    setupNavigation() {
        // Setup navigation menu
        const navItems = document.querySelectorAll('.nav-item');
        navItems.forEach(item => {
            item.addEventListener('click', this.handleNavigation);
        });
    }
    
    handleNavigation(e) {
        const targetSection = e.currentTarget.dataset.section;
        if (targetSection) {
            // Prevent access to global settings when a file is loaded (projects history should remain accessible)
            if (this.currentFile && targetSection === 'library') {
                this.showToast(
                    'Non puoi accedere alle impostazioni globali dopo aver caricato un file. Inizia un nuovo progetto per modificare le configurazioni.',
                    'warning',
                    5000
                );
                return; // Block navigation
            }
            
            this.showMainSection(targetSection);
            
            // Update active navigation item
            document.querySelectorAll('.nav-item').forEach(item => {
                item.classList.remove('active');
            });
            e.currentTarget.classList.add('active');
            
            // Show/hide header stats based on section
            const headerStats = document.getElementById('headerStats');
            if (headerStats) {
                if (targetSection === 'app' && this.currentData) {
                    headerStats.style.display = 'flex';
                } else {
                    headerStats.style.display = 'none';
                }
            }
        }
    }
    
    showMainSection(sectionName) {
        // Hide all main sections
        const sections = ['appSection', 'librarySection', 'settingsSection'];
        sections.forEach(id => {
            const element = document.getElementById(id);
            if (element) {
                element.classList.remove('active');
            }
        });
        
        // Show target section
        const targetSection = document.getElementById(sectionName + 'Section');
        if (targetSection) {
            targetSection.classList.add('active');
        }
        
        // Update navigation menu to reflect current section
        document.querySelectorAll('.nav-item').forEach(item => {
            item.classList.remove('active');
            if (item.dataset.section === sectionName) {
                item.classList.add('active');
            }
        });
        
        this.currentSection = sectionName;
        
        // Handle section-specific logic
        if (sectionName === 'app') {
            // Restore app state
            if (this.currentData) {
                this.showSection('results');
            } else if (this.currentFile) {
                this.showSection('config');
            } else {
                this.showSection('upload');
            }
        }
    }
    
    // ===== NAVIGATION STATE MANAGEMENT =====
    
    updateNavigationState() {
        // Update navigation items visual state based on whether a file is loaded
        const navItems = document.querySelectorAll('.nav-item');
        navItems.forEach(item => {
            const section = item.dataset.section;
            if (this.currentFile && section === 'library') {
                item.classList.add('disabled');
                item.title = 'Non disponibile dopo aver caricato un file';
            } else {
                item.classList.remove('disabled');
                item.title = '';
            }
        });
    }
    
    // ===== EVENT LISTENERS SETUP =====
    
    setupEventListeners() {
        // File Upload
        const fileInput = document.getElementById('fileInput');
        const uploadArea = document.getElementById('uploadArea');
        const selectFileBtn = document.getElementById('selectFileBtn');
        
        fileInput?.addEventListener('change', (e) => this.handleFileSelect(e));
        uploadArea?.addEventListener('dragover', (e) => this.handleDragOver(e));
        uploadArea?.addEventListener('drop', (e) => this.handleDrop(e));
        uploadArea?.addEventListener('dragleave', (e) => {
            e.target.classList.remove('dragover');
        });
        
        // Separate click handlers to avoid conflicts
        selectFileBtn?.addEventListener('click', (e) => {
            e.stopPropagation();
            fileInput?.click();
        });
        
        uploadArea?.addEventListener('click', (e) => {
            // Only trigger file input if not clicking on the button
            if (!e.target.closest('#selectFileBtn')) {
                fileInput?.click();
            }
        });
        
        // Remove file
        document.getElementById('removeFile')?.addEventListener('click', () => {
            this.removeFile();
        });
        
        // Configuration
        this.setupConfigurationListeners();
        
        // NEW: Project Parameters listeners
        this.setupProjectParametersListeners();
        
        // NUOVO: Setup aggiornamento parametri dinamici
        this.setupRealTimeParametersUpdate();
        
        // NEW: Preview Step listeners
        this.setupPreviewStepListeners();
        
        // Process button
        document.getElementById('processBtn')?.addEventListener('click', () => {
            this.processFile();
        });
        
        // Navigation buttons
        const backToUploadBtn = document.getElementById('backToUpload');
        console.log('🔍 backToUpload button found:', !!backToUploadBtn);
        backToUploadBtn?.addEventListener('click', () => {
            console.log('🔙 backToUpload clicked!');
            this.resetToUpload();
        });
        
        document.getElementById('backToPreviousStep')?.addEventListener('click', () => {
            console.log('🔙 backToPreviousStep clicked!');
            this.showSection('projectParams');
        });
        
        document.getElementById('reconfigureBtn')?.addEventListener('click', () => {
            this.showSection('config');
        });
        
        document.getElementById('newProjectBtn')?.addEventListener('click', () => {
            this.resetApp();
        });
        
        // Download buttons - CORRETTI
        document.getElementById('downloadPDF')?.addEventListener('click', () => {
            console.log('PDF download clicked');
            this.downloadResult('pdf');
        });
        
        document.getElementById('downloadDXF')?.addEventListener('click', () => {
            console.log('DXF download clicked');
            this.downloadResult('dxf-step5');
        });
        
        document.getElementById('downloadJSON')?.addEventListener('click', () => {
            console.log('JSON download clicked');
            this.downloadResult('json');
        });
        
        // Preview controls
        document.getElementById('refreshPreview')?.addEventListener('click', () => {
            this.loadPreview();
        });
        
        document.getElementById('fullscreenPreview')?.addEventListener('click', () => {
            this.openFullscreenPreview();
        });
        
        document.getElementById('closeFullscreen')?.addEventListener('click', () => {
            this.closeFullscreenPreview();
        });
        
        // Modal overlay click to close
        document.getElementById('fullscreenModal')?.addEventListener('click', (e) => {
            if (e.target.id === 'fullscreenModal') {
                this.closeFullscreenPreview();
            }
        });
        
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.closeFullscreenPreview();
            }
            
            // Navigation shortcuts (Ctrl + 1/2/3)
            if (e.ctrlKey && ['1', '2', '3'].includes(e.key)) {
                e.preventDefault();
                const sections = ['app', 'library', 'settings'];
                const sectionIndex = parseInt(e.key) - 1;
                if (sections[sectionIndex]) {
                    // Find and click the corresponding nav item
                    const navItem = document.querySelector(`[data-section="${sections[sectionIndex]}"]`);
                    if (navItem) {
                        navItem.click();
                    }
                }
            }
        });
    }
    
    setupConfigurationListeners() {
        // Offset rimosso: ora gestito automaticamente dall'algoritmo bidirezionale
        
        // NUOVO: Ceiling height automatic calculation listener
        const ceilingHeightInput = document.getElementById('ceilingHeight');
        if (ceilingHeightInput) {
            ceilingHeightInput.addEventListener('change', (e) => {
                const value = parseInt(e.target.value);
                if (value && value > 0) {
                    console.log(`👤 Utente ha modificato altezza soffitto: ${value}mm`);
                    
                    // Aggiorna il display se esiste
                    const displayElement = document.querySelector('.ceiling-height-display');
                    if (displayElement) {
                        displayElement.textContent = `${value}mm (modificato manualmente)`;
                        displayElement.classList.add('user-modified');
                    }
                    
                    // Aggiorna il riassunto configurazione
                    this.updateConfigurationCard();
                }
            });
            
            ceilingHeightInput.addEventListener('focus', (e) => {
                // Quando l'utente clicca sul campo, mostra un suggerimento
                console.log('💡 Campo altezza soffitto selezionato - valore calcolato automaticamente');
            });
        }
    }
    
    // updatePresetButtons rimossa: non più necessaria senza controlli offset manuali
    
    // ===== FILE HANDLING =====
    
    handleFileSelect(e) {
        console.log('🔄 File selected via input');
        const files = e.target.files;
        if (files.length > 0) {
            this.validateAndSetFile(files[0]);
        }
    }

    handleDragOver(e) {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'copy';
        e.target.classList.add('dragover');
    }

    handleDrop(e) {
        console.log('🔄 File dropped');
        e.preventDefault();
        e.target.classList.remove('dragover');
        
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            this.validateAndSetFile(files[0]);
        }
    }    validateAndSetFile(file) {
        console.log('🔍 Validating file:', file.name, file.size + 'bytes', file.type);
        
        // Validation - Updated to support SVG, DWG, DXF
        const fileName = file.name.toLowerCase();
        const supportedFormats = ['.svg', '.dwg', '.dxf'];
        const isValidFormat = supportedFormats.some(format => fileName.endsWith(format));
        
        if (!isValidFormat) {
            this.showToast('Formato non supportato. Usa file SVG, DWG o DXF', 'error');
            console.log('❌ Invalid format:', fileName);
            return;
        }
        
        if (file.size > 10 * 1024 * 1024) { // 10MB
            this.showToast('File troppo grande (max 10MB)', 'error');
            console.log('❌ File too large:', file.size);
            return;
        }
        
        if (file.size === 0) {
            this.showToast('File vuoto', 'error');
            console.log('❌ Empty file');
            return;
        }
        
        console.log('✅ File validation passed');
        
        // Set file
        this.currentFile = file;
        this.showFileInfo(file);
        
        // Update navigation state to disable global settings (projects history remains accessible)
        this.updateNavigationState();
        
        // Show success message and auto-progress to preview
        this.showToast('File caricato con successo', 'success');
        
        // Auto-generate preview
        setTimeout(() => {
            this.showToast('Generazione anteprima conversione...', 'info');
            setTimeout(() => {
                console.log('🔄 About to generate file preview for:', file.name);
                console.log('📋 generateFilePreview function exists:', typeof this.generateFilePreview);
                this.generateFilePreview(file);
            }, 800);
        }, 1200);
    }
    
    removeFile() {
        this.currentFile = null;
        this.currentSessionId = null;
        this.currentData = null;
        this.currentPreviewData = null; // NEW: Clear preview data
        this.previewSessionId = null; // NUOVO: Clear preview session ID
        
        // Reset file input
        const fileInput = document.getElementById('fileInput');
        if (fileInput) fileInput.value = '';
        
        // Hide file info
        const fileInfo = document.getElementById('fileInfo');
        if (fileInfo) fileInfo.style.display = 'none';
        
        // Unlock block dimensions editing when file is removed
        this.unlockBlockDimensionsEditing();
        
        // Update navigation state to re-enable global settings
        this.updateNavigationState();
        
        this.showSection('upload');
        this.showToast('File rimosso', 'info');
    }
    
    showFileInfo(file, resetFlags = true) {
        // Reset project saved flag when new file is loaded (only if not reusing)
        if (resetFlags) {
            this.projectSaved = false;
            this.isReusedProject = false;
        }
        
        const fileInfo = document.getElementById('fileInfo');
        const fileName = document.getElementById('fileName');
        const fileMeta = document.getElementById('fileMeta');
        
        if (fileInfo && fileName && fileMeta) {
            fileName.textContent = file.name;
            
            // Determine file type based on extension
            const ext = file.name.toLowerCase().split('.').pop();
            let fileType = 'Sconosciuto';
            switch (ext) {
                case 'svg': fileType = 'SVG'; break;
                case 'dwg': fileType = 'DWG'; break; 
                case 'dxf': fileType = 'DXF'; break;
            }
            
            fileMeta.textContent = `${this.formatFileSize(file.size)} • ${fileType}`;
            fileInfo.style.display = 'block';
        }
        
        // Hide edit blocks button and show lock message when file is loaded
        this.lockBlockDimensionsEditing();
    }
    
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
    
    // ===== BLOCK DIMENSIONS LOCKING =====
    
    lockBlockDimensionsEditing() {
        const editBlocksBtn = document.getElementById('editBlocksBtn');
        const blocksUsageInfo = document.getElementById('blocksUsageInfo');
        const blocksLockInfo = document.getElementById('blocksLockInfo');
        
        if (editBlocksBtn) {
            editBlocksBtn.style.display = 'none';
        }
        
        if (blocksUsageInfo) {
            blocksUsageInfo.style.display = 'none';
        }
        
        if (blocksLockInfo) {
            blocksLockInfo.style.display = 'block';
        }
        
        console.log('🔒 Dimensioni blocchi bloccate - file caricato');
    }
    
    unlockBlockDimensionsEditing() {
        const editBlocksBtn = document.getElementById('editBlocksBtn');
        const blocksUsageInfo = document.getElementById('blocksUsageInfo');
        const blocksLockInfo = document.getElementById('blocksLockInfo');
        
        if (editBlocksBtn) {
            editBlocksBtn.style.display = 'inline-block';
        }
        
        if (blocksUsageInfo) {
            blocksUsageInfo.style.display = 'block';
        }
        
        if (blocksLockInfo) {
            blocksLockInfo.style.display = 'none';
        }
        
        console.log('🔓 Dimensioni blocchi sbloccate - nessun file caricato');
    }
    
    // ===== API COMMUNICATION =====
    
    async processFile() {
        // CONTROLLO: Se abbiamo un preview session, usa l'endpoint ottimizzato
        if (this.previewSessionId) {
            console.log('🚀 Usando elaborazione OTTIMIZZATA (riutilizzo conversione esistente)');
            return this.processFromPreview();
        }
        
        // FALLBACK: Elaborazione tradizionale se non c'è preview
        if (!this.currentFile) {
            this.showToast('Nessun file selezionato', 'error');
            return;
        }
        
        console.log('⚠️ Usando elaborazione TRADIZIONALE (doppia conversione)');
        
        // Get configuration
        const config = this.getConfiguration();
        
        // Get project parameters (NEW)
        const projectParams = this.projectParameters || this.collectProjectParameters();
        
        // Show loading (solo loading normale, no smart-loading)
        this.showLoading('Elaborazione in corso...', 'Analisi file CAD e calcolo packing automatico con parametri personalizzati');
        
        try {
            // Prepare form data
            const formData = new FormData();
            formData.append('file', this.currentFile);
            // row_offset rimosso: ora calcolato automaticamente dall'algoritmo
            formData.append('block_widths', config.blockWidths);
            formData.append('project_name', config.projectName);
            
            // Add color theme configuration
            const colorTheme = getCurrentColorTheme();
            formData.append('color_theme', JSON.stringify(colorTheme));
            
            // Add block dimensions configuration
            const blockDimensions = getBlockDimensionsForBackend();
            formData.append('block_dimensions', JSON.stringify(blockDimensions));
            
            // NEW: Add project parameters for enhanced packing
            formData.append('material_config', JSON.stringify({
                material_thickness_mm: projectParams.material.thickness_mm,
                material_density_kg_m3: projectParams.material.density_kg_m3,
                material_type: projectParams.material.type,
                guide_width_mm: projectParams.guide.width_mm,
                guide_depth_mm: projectParams.guide.depth_mm,
                guide_type: projectParams.guide.type,
                wall_position: projectParams.wall.position,
                is_attached_to_existing: projectParams.wall.is_attached,
                attachment_points: projectParams.wall.attachment_points,
                ceiling_height_mm: projectParams.ceiling.height_mm,
                enable_moretti_calculation: projectParams.ceiling.enable_moretti_calculation,
                enable_automatic_measurements: projectParams.advanced.enable_automatic_measurements,
                enable_cost_estimation: projectParams.advanced.enable_cost_estimation
            }));
            
            // Make API call to enhanced packing endpoint
            const response = await fetch('/api/enhanced-pack', {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Errore del server');
            }
            
            const result = await response.json();
            
            // Store result
            this.currentSessionId = result.session_id;
            this.currentData = result;
            
            // Update UI (no smart-loading hide needed)
            this.hideLoading();
            this.showResults(result);
            this.loadPreview();
            this.showSection('results');
            
            this.showToast('Packing completato con successo!', 'success');
            
        } catch (error) {
            console.error('Errore processamento:', error);
            
            // Hide loading on error (no smart-loading hide needed)
            this.hideLoading();
            this.showToast(`Errore: ${error.message}`, 'error');
        }
    }

    // NUOVO: Elaborazione ottimizzata che riutilizza i dati di preview
    async processFromPreview() {
        console.log('⚡ Elaborazione OTTIMIZZATA - Riutilizzo conversione esistente');
        console.log('🆔 Preview Session ID:', this.previewSessionId);
        
        // Get configuration
        const config = this.getConfiguration();
        
        // Get project parameters
        const projectParams = this.projectParameters || this.collectProjectParameters();
        
        // Show loading
        this.showLoading('Elaborazione ottimizzata in corso...', 
            'Calcolo packing con dati già convertiti - EVITATA doppia conversione!');
        
        try {
            // Prepare form data per endpoint ottimizzato
            const formData = new FormData();
            formData.append('preview_session_id', this.previewSessionId); // CHIAVE: Riutilizzo dati
            // row_offset rimosso: ora calcolato automaticamente dall'algoritmo
            formData.append('block_widths', config.blockWidths);
            formData.append('project_name', config.projectName);
            
            // Add color theme configuration
            const colorTheme = getCurrentColorTheme();
            formData.append('color_theme', JSON.stringify(colorTheme));
            
            // Add block dimensions configuration
            const blockDimensions = getBlockDimensionsForBackend();
            formData.append('block_dimensions', JSON.stringify(blockDimensions));
            
            // Add project parameters for enhanced packing - DINAMICO COMPLETO
            const enhancedMaterialConfig = {
                // Material parameters - TUTTI DINAMICI
                material_thickness_mm: projectParams.material.thickness_mm,
                material_density_kg_m3: projectParams.material.density_kg_m3,
                material_type: projectParams.material.type,
                material_strength_factor: projectParams.material.strength_factor,
                material_thermal_conductivity: projectParams.material.thermal_conductivity,
                
                // Guide parameters - TUTTI DINAMICI
                guide_width_mm: projectParams.guide.width_mm,
                guide_depth_mm: projectParams.guide.depth_mm,
                guide_type: projectParams.guide.type,
                guide_max_load_kg: projectParams.guide.max_load_kg,
                
                // Wall position parameters - COMPLETI E DINAMICI
                wall_position: projectParams.wall.position,
                is_attached_to_existing: projectParams.wall.is_attached_to_existing,
                attachment_points: projectParams.wall.attachment_points,
                existing_walls_sides: projectParams.wall.existing_walls_sides, // Backend compatibility
                fixed_walls: projectParams.wall.fixed_walls, // Enhanced format
                
                // Ceiling and moretti parameters - DINAMICI
                ceiling_height_mm: projectParams.ceiling.height_mm,
                enable_moretti_calculation: projectParams.ceiling.enable_moretti_calculation,
                moretti_needed_hint: projectParams.ceiling.moretti_needed, // Pre-calcolo frontend
                
                // Advanced options - DINAMICI
                enable_automatic_measurements: projectParams.advanced.enable_automatic_measurements,
                enable_cost_estimation: projectParams.advanced.enable_cost_estimation,
                enable_enhanced_packing: projectParams.advanced.enable_enhanced_packing,
                use_optimized_algorithms: projectParams.advanced.use_optimized_algorithms,
                
                // NUOVO: Parametri calcolati per validazione backend
                calculated_closure_thickness_mm: projectParams.calculated.closure_thickness_mm,
                formula_description: projectParams.calculated.formula_description,
                calculated_starting_point: projectParams.calculated.starting_point,
                
                // NUOVO: Metadata per debugging
                frontend_version: "dynamic_v1.0",
                parameter_collection_timestamp: new Date().toISOString(),
                parameters_source: "frontend_dynamic_collection"
            };
            
            console.log('📤 Invio configurazione enhanced al backend:', enhancedMaterialConfig);
            formData.append('material_config', JSON.stringify(enhancedMaterialConfig));
            
            // CHIAMA ENDPOINT OTTIMIZZATO
            const response = await fetch('/api/enhanced-pack-from-preview', {
                method: 'POST',
                body: formData,
                headers: {
                    'Authorization': `Bearer ${window.authManager.token}`
                }
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Errore del server');
            }
            
            const result = await response.json();
            console.log('✅ Elaborazione ottimizzata completata:', result);
            
            // Check if it was actually optimized
            const wasOptimized = response.headers.get('X-Optimized-From-Preview') === 'true';
            if (wasOptimized) {
                console.log('⚡ CONVERSIONE EVITATA - Riutilizzati dati preview!');
            }
            
            // Store result
            this.currentSessionId = result.session_id;
            this.currentData = result;
            
            // Update UI (no smart-loading hide needed)
            this.hideLoading();
            this.showResults(result);
            this.loadPreview();
            this.showSection('results');
            
            this.showToast(wasOptimized ? 
                'Packing completato con successo! (Elaborazione ottimizzata)' : 
                'Packing completato con successo!', 'success');
            
        } catch (error) {
            console.error('Errore processamento ottimizzato:', error);
            
            // Hide loading on error (no smart-loading hide needed)
            this.hideLoading();
            this.showToast(`Errore elaborazione: ${error.message}`, 'error');
            
            // FALLBACK: Se l'elaborazione ottimizzata fallisce, prova quella tradizionale
            console.log('🔄 Tentativo fallback con elaborazione tradizionale...');
            this.previewSessionId = null; // Reset per evitare loop
            return this.processFile();
        }
    }
    
    // NUOVO: Metodo per calcolare e impostare automaticamente l'altezza soffitto
    setAutomaticCeilingHeight(data) {
        const calculatedHeight = this.getCalculatedCeilingHeight(data);
        if (calculatedHeight) {
            const ceilingInput = document.getElementById('ceilingHeight');
            if (ceilingInput) {
                ceilingInput.value = calculatedHeight;
                console.log(`✅ Altezza soffitto calcolata automaticamente: ${calculatedHeight}mm`);
                
                // Aggiorna il display in real-time se esiste
                const displayElement = document.querySelector('.ceiling-height-display');
                if (displayElement) {
                    displayElement.textContent = `${calculatedHeight}mm (calcolato automaticamente)`;
                }
                
                // NUOVO: Pre-calcola anche le dimensioni reali per la Configuration Card
                const realDimensions = this.getRealWallDimensions(data);
                if (realDimensions) {
                    console.log('✅ Dimensioni reali pareti pre-calcolate:', realDimensions);
                    // Memorizza le dimensioni per uso successivo
                    this.cachedWallDimensions = realDimensions;
                }
                
                // Aggiorna anche il riassunto configurazione
                this.updateConfigurationCard();
            }
        }
    }

    // NUOVO: Metodo per calcolare l'altezza dal file elaborato
    getCalculatedCeilingHeight(data = null) {
        const projectData = data || this.currentData || this.projectData;
        
        if (!projectData) {
            console.log('ℹ️ Nessun dato progetto disponibile per calcolare altezza soffitto');
            return null;
        }
        
        console.log('🔍 Ricerca altezza soffitto nei dati:', projectData);
        
        // 1. Cerca l'altezza nei dati delle pareti
        if (projectData.walls && projectData.walls.length > 0) {
            let maxHeight = 0;
            projectData.walls.forEach((wall, index) => {
                // Controlla wall.height
                if (wall.height && wall.height > maxHeight) {
                    maxHeight = wall.height;
                    console.log(`📏 Altezza trovata in wall[${index}].height: ${wall.height}mm`);
                }
                // Controlla wall.wall_info.height
                if (wall.wall_info && wall.wall_info.height && wall.wall_info.height > maxHeight) {
                    maxHeight = wall.wall_info.height;
                    console.log(`📏 Altezza trovata in wall[${index}].wall_info.height: ${wall.wall_info.height}mm`);
                }
                // Controlla wall.dimensions.height
                if (wall.dimensions && wall.dimensions.height && wall.dimensions.height > maxHeight) {
                    maxHeight = wall.dimensions.height;
                    console.log(`📏 Altezza trovata in wall[${index}].dimensions.height: ${wall.dimensions.height}mm`);
                }
            });
            
            if (maxHeight > 0) {
                console.log(`✅ Altezza soffitto calcolata da pareti: ${Math.round(maxHeight)}mm`);
                return Math.round(maxHeight);
            }
        }
        
        // 2. Controlla nei metadati generali
        if (projectData.metadata) {
            if (projectData.metadata.ceiling_height) {
                console.log(`✅ Altezza trovata in metadata.ceiling_height: ${projectData.metadata.ceiling_height}mm`);
                return Math.round(projectData.metadata.ceiling_height);
            }
            if (projectData.metadata.wall_height) {
                console.log(`✅ Altezza trovata in metadata.wall_height: ${projectData.metadata.wall_height}mm`);
                return Math.round(projectData.metadata.wall_height);
            }
            if (projectData.metadata.height) {
                console.log(`✅ Altezza trovata in metadata.height: ${projectData.metadata.height}mm`);
                return Math.round(projectData.metadata.height);
            }
        }
        
        // 3. Controlla in drawing_bounds se disponibile
        if (projectData.drawing_bounds) {
            if (projectData.drawing_bounds.height) {
                console.log(`✅ Altezza trovata in drawing_bounds.height: ${projectData.drawing_bounds.height}mm`);
                return Math.round(projectData.drawing_bounds.height);
            }
            if (projectData.drawing_bounds.max_y && projectData.drawing_bounds.min_y) {
                const calculatedHeight = projectData.drawing_bounds.max_y - projectData.drawing_bounds.min_y;
                console.log(`✅ Altezza calcolata da drawing_bounds (max_y - min_y): ${calculatedHeight}mm`);
                return Math.round(calculatedHeight);
            }
        }
        
        // 4. Controlla in analysis_results se disponibile
        if (projectData.analysis_results && projectData.analysis_results.wall_analysis) {
            const wallAnalysis = projectData.analysis_results.wall_analysis;
            if (wallAnalysis.average_height) {
                console.log(`✅ Altezza trovata in analysis_results.wall_analysis.average_height: ${wallAnalysis.average_height}mm`);
                return Math.round(wallAnalysis.average_height);
            }
            if (wallAnalysis.max_height) {
                console.log(`✅ Altezza trovata in analysis_results.wall_analysis.max_height: ${wallAnalysis.max_height}mm`);
                return Math.round(wallAnalysis.max_height);
            }
        }
        
        console.log('⚠️ Nessuna altezza trovata nei dati del file. Usando valore di default (2700mm).');
        return null; // Nessuna altezza trovata, usar à default
    }

    // NUOVO: Metodo per calcolare le dimensioni reali delle pareti dal file CAD
    getRealWallDimensions(data = null) {
        const projectData = data || this.currentData || this.projectData;
        
        // Se abbiamo già calcolato le dimensioni e non ci sono nuovi dati, riutilizza
        if (this.calculatedDimensions && !data) {
            console.log('✅ Riutilizzando dimensioni già calcolate:', this.calculatedDimensions);
            return this.calculatedDimensions;
        }
        
        if (!projectData) {
            console.log('ℹ️ Nessun dato progetto disponibile per calcolare dimensioni pareti');
            return null;
        }
        
        console.log('📏 Calcolo dimensioni reali pareti dai dati elaborati:', projectData);
        
        const dimensions = {
            height_mm: 0,
            length_mm: 0,
            thickness_mm: 0,
            area_m2: 0,
            wall_count: 0,
            // NUOVO: Aggiungiamo i campi formattati come nello step 2
            area_total: 0,      // Area Totale (m²)
            max_width: 0,       // Larghezza Massima (mm)
            max_height: 0,      // Altezza Massima (mm)
            apertures_count: 0, // Aperture Rilevate
            perimeter: 0,       // Perimetro (mm)
            geometry_type: 'rettangolare' // Tipo geometria
        };
        
        // 1. PRIORITÀ MASSIMA: Cerca nelle measurements esistenti (come nello step 2)
        if (projectData.measurements) {
            console.log('✅ Trovate measurements dirette dai dati elaborati:', projectData.measurements);
            const m = projectData.measurements;
            
            dimensions.area_total = parseFloat(m.area_total) || 0;
            dimensions.max_width = parseInt(m.max_width) || 0;
            dimensions.max_height = parseInt(m.max_height) || 0;
            dimensions.apertures_count = parseInt(m.apertures_count) || 0;
            dimensions.perimeter = parseInt(m.perimeter) || 0;
            dimensions.geometry_type = m.geometry_type || 'rettangolare';
            
            // Mappa anche nei campi standard
            dimensions.area_m2 = dimensions.area_total;
            dimensions.length_mm = dimensions.max_width;
            dimensions.height_mm = dimensions.max_height;
            
            // MEMORIZZA in cache
            this.calculatedDimensions = dimensions;
            console.log('💾 Dimensioni memorizzate in cache da measurements');
            return dimensions;
        }
        
        // 2. BACKUP: Dati già elaborati dal secondo step (wall_area + wall_bounds)
        if (projectData.wall_area && projectData.wall_bounds) {
            const bounds = projectData.wall_bounds;
            const width = Math.round(bounds.max_x - bounds.min_x);
            const height = Math.round(bounds.max_y - bounds.min_y);
            const area = projectData.wall_area / 1000000; // mm² to m²
            
            dimensions.area_total = parseFloat(area.toFixed(2));
            dimensions.max_width = width;
            dimensions.max_height = height;
            dimensions.apertures_count = projectData.apertures_count || 0;
            
            // 🎯 CORREZIONE CRITICA: Usa il perimetro reale se disponibile, non quello calcolato!
            if (projectData.wall_perimeter && projectData.wall_perimeter > 0) {
                dimensions.perimeter = Math.round(projectData.wall_perimeter);
                console.log(`✅ Usando PERIMETRO REALE: ${dimensions.perimeter}mm`);
            } else {
                dimensions.perimeter = 2 * (width + height); // Fallback solo se non disponibile
                console.log(`⚠️ Usando perimetro calcolato (rettangolare): ${dimensions.perimeter}mm`);
            }
            
            dimensions.geometry_type = 'rettangolare';
            
            // Mappa anche nei campi standard
            dimensions.area_m2 = dimensions.area_total;
            dimensions.length_mm = dimensions.max_width;
            dimensions.height_mm = dimensions.max_height;
            dimensions.wall_count = projectData.walls_count || 1;
            
            console.log(`✅ Dimensioni estratte dai dati elaborati del secondo step:`);
            console.log(`   📐 Area Totale: ${dimensions.area_total} m²`);
            console.log(`   📏 Larghezza Massima: ${dimensions.max_width} mm`);
            console.log(`   📏 Altezza Massima: ${dimensions.max_height} mm`);
            console.log(`   � Aperture Rilevate: ${dimensions.apertures_count} elementi`);
            
            // MEMORIZZA in cache
            this.calculatedDimensions = dimensions;
            console.log('💾 Dimensioni memorizzate in cache da wall_area + wall_bounds');
            return dimensions;
        }
        
        // 3. BACKUP: Cerca nei risultati elaborati (result section)
        if (projectData.result) {
            const result = projectData.result;
            if (result.wall_area && result.wall_bounds) {
                const bounds = result.wall_bounds;
                const width = Math.round(bounds.max_x - bounds.min_x);
                const height = Math.round(bounds.max_y - bounds.min_y);
                const area = result.wall_area / 1000000;
                
                dimensions.area_total = parseFloat(area.toFixed(2));
                dimensions.max_width = width;
                dimensions.max_height = height;
                dimensions.apertures_count = result.apertures_count || 0;
                
                // 🎯 CORREZIONE CRITICA: Usa il perimetro reale se disponibile!
                if (result.wall_perimeter && result.wall_perimeter > 0) {
                    dimensions.perimeter = Math.round(result.wall_perimeter);
                    console.log(`✅ Usando PERIMETRO REALE da result: ${dimensions.perimeter}mm`);
                } else {
                    dimensions.perimeter = 2 * (width + height);
                    console.log(`⚠️ Usando perimetro calcolato da result: ${dimensions.perimeter}mm`);
                }
                
                dimensions.geometry_type = 'rettangolare';
                
                // Mappa nei campi standard
                dimensions.area_m2 = dimensions.area_total;
                dimensions.length_mm = dimensions.max_width;
                dimensions.height_mm = dimensions.max_height;
                dimensions.wall_count = result.walls_count || 1;
                
                console.log(`✅ Dimensioni estratte da projectData.result:`);
                console.log(`   📐 Area: ${dimensions.area_total} m², Dimensioni: ${dimensions.max_width}×${dimensions.max_height}mm`);
                
                // MEMORIZZA in cache
                this.calculatedDimensions = dimensions;
                console.log('💾 Dimensioni memorizzate in cache da projectData.result');
                return dimensions;
            }
        }
        
        // 4. FALLBACK: Calcolo da pareti individuali (metodo originale)
        if (projectData.walls && projectData.walls.length > 0) {
            let totalLength = 0;
            let maxHeight = 0;
            let maxWidth = 0;
            
            projectData.walls.forEach((wall, index) => {
                const wallHeight = wall.height || wall.wall_info?.height || wall.dimensions?.height;
                if (wallHeight && wallHeight > maxHeight) {
                    maxHeight = wallHeight;
                }
                
                const wallLength = wall.length || wall.wall_info?.length || wall.dimensions?.length;
                if (wallLength) {
                    totalLength += wallLength;
                    if (wallLength > maxWidth) maxWidth = wallLength;
                }
            });
            
            if (maxHeight > 0 || maxWidth > 0) {
                const area = maxHeight > 0 && maxWidth > 0 ? (maxHeight * maxWidth) / 1000000 : 0;
                
                dimensions.area_total = parseFloat(area.toFixed(2));
                dimensions.max_width = maxWidth;
                dimensions.max_height = maxHeight;
                dimensions.apertures_count = 0; // Non rilevabili dalle pareti individuali
                dimensions.perimeter = maxWidth > 0 && maxHeight > 0 ? 2 * (maxWidth + maxHeight) : 0;
                dimensions.geometry_type = 'calcolata';
                
                // Mappa nei campi standard
                dimensions.area_m2 = dimensions.area_total;
                dimensions.length_mm = dimensions.max_width;
                dimensions.height_mm = dimensions.max_height;
                dimensions.wall_count = projectData.walls.length;
                
                console.log(`✅ Dimensioni calcolate dalle pareti individuali:`, dimensions);
                
                // MEMORIZZA in cache
                this.calculatedDimensions = dimensions;
                console.log('💾 Dimensioni memorizzate in cache da pareti individuali');
                return dimensions;
            }
        }
        
        console.log('⚠️ Nessuna dimensione valida trovata nei dati del file');
        return null;
    }
    
    async reconfigureAndProcess() {
        if (!this.currentSessionId) {
            this.showToast('Nessuna sessione attiva', 'error');
            return;
        }
        
        const config = this.getConfiguration();
        
        this.showLoading('Riconfigurazione...', 'Ricalcolo con nuovi parametri');
        
        try {
            const formData = new FormData();
            formData.append('session_id', this.currentSessionId);
            // row_offset rimosso: ora calcolato automaticamente dall'algoritmo
            formData.append('block_widths', config.blockWidths);
            
            // Add block dimensions configuration for recalculation
            const blockDimensions = getBlockDimensionsForBackend();
            formData.append('block_dimensions', JSON.stringify(blockDimensions));
            
            const response = await fetch('/api/reconfigure', {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Errore riconfigurazione');
            }
            
            // Reload session data
            await this.loadSessionData(this.currentSessionId);
            
            this.hideLoading();
            this.showSection('results');
            this.showToast('Riconfigurazione completata', 'success');
            
        } catch (error) {
            console.error('Errore riconfigurazione:', error);
            this.hideLoading();
            this.showToast(`Errore: ${error.message}`, 'error');
        }
    }
    
    async loadSessionData(sessionId) {
        // 🚀 SMART LOADING: Avvia loading per caricamento sessione
        window.smartLoading?.showForOperation('sessionLoad', {
            fileName: `Sessione ${sessionId}`,
            onCancel: () => {
                console.log('❌ Caricamento sessione annullato dall\'utente');
            }
        });
        
        try {
            const response = await fetch(`/api/session/${sessionId}`);
            if (!response.ok) {
                throw new Error('Sessione non trovata');
            }
            
            const sessionData = await response.json();
            
            // Fake the result structure for compatibility
            this.currentData = {
                session_id: sessionId,
                summary: sessionData.summary,
                metrics: sessionData.metrics,
                config: sessionData.config,
                wall_bounds: sessionData.wall_bounds,
                blocks_standard: [], // Not needed for display
                blocks_custom: [],   // Not needed for display
                apertures: []        // Not needed for display
            };
            
            // 🚀 SMART LOADING: Operazione completata
            window.smartLoading?.hide();
            
            this.showResults(this.currentData);
            this.loadPreview();
            
        } catch (error) {
            console.error('Errore caricamento sessione:', error);
            
            // 🚀 SMART LOADING: Nascondi loading anche in caso di errore
            window.smartLoading?.hide();
            
            this.showToast(`Errore: ${error.message}`, 'error');
        }
    }
    
    async loadPreview() {
        if (!this.currentSessionId) {
            return;
        }
        
        const previewLoading = document.getElementById('previewLoading');
        const previewImage = document.getElementById('previewImage');
        
        if (previewLoading) previewLoading.style.display = 'block';
        if (previewImage) previewImage.style.display = 'none';
        
        try {
            const response = await fetch(`/api/preview/${this.currentSessionId}`);
            if (!response.ok) {
                throw new Error('Errore generazione preview');
            }
            
            const data = await response.json();
            
            if (previewImage && data.image) {
                previewImage.src = data.image;
                previewImage.style.display = 'block';
            }
            
            if (previewLoading) previewLoading.style.display = 'none';
            
        } catch (error) {
            console.error('Errore preview:', error);
            if (previewLoading) previewLoading.style.display = 'none';
            this.showToast('Errore caricamento preview', 'warning');
        }
    }
    
    async downloadResult(format) {
        console.log(`🔽 Download ${format.toUpperCase()} richiesto`);
        
        if (!this.currentSessionId) {
            this.showToast('Nessuna sessione attiva', 'error');
            console.error('❌ Session ID mancante');
            return;
        }
        
        // Validation format
        const validFormats = ['pdf', 'json', 'dxf', 'dxf-step5'];
        if (!validFormats.includes(format.toLowerCase())) {
            this.showToast(`Formato ${format} non supportato`, 'error');
            return;
        }
        
        try {
            // Show progress
            this.showToast(`Preparazione download ${format.toUpperCase()}...`, 'info');
            
            const url = `/api/download/${this.currentSessionId}/${format}`;
            console.log(`📡 Fetching: ${url}`);
            
            const response = await fetch(url);
            
            console.log(`📊 Response status: ${response.status}`);
            console.log(`📊 Response headers:`, Object.fromEntries(response.headers.entries()));
            
            if (!response.ok) {
                let errorMessage = 'Errore download';
                try {
                    const errorData = await response.json();
                    errorMessage = errorData.detail || errorMessage;
                    console.error('❌ Error data:', errorData);
                } catch (e) {
                    errorMessage = `HTTP ${response.status}: ${response.statusText}`;
                }
                throw new Error(errorMessage);
            }
            
            // Create download link
            const blob = await response.blob();
            console.log(`💾 Blob creato: ${blob.size} bytes, type: ${blob.type}`);
            
            if (blob.size === 0) {
                throw new Error('File vuoto ricevuto dal server');
            }
            
            const downloadUrl = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = downloadUrl;
            
            // Extract filename from response headers or generate one
            const contentDisposition = response.headers.get('content-disposition');
            let filename = `risultato_${this.currentSessionId.slice(0, 8)}_${Date.now()}.${format}`;
            
            if (contentDisposition) {
                const filenameMatch = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
                if (filenameMatch && filenameMatch[1]) {
                    filename = filenameMatch[1].replace(/['"]/g, '');
                }
            }
            
            console.log(`💾 Download filename: ${filename}`);
            
            a.download = filename;
            a.style.display = 'none';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(downloadUrl);
            
            console.log(`✅ Download ${format.toUpperCase()} completato`);
            this.showToast(`Download ${format.toUpperCase()} completato`, 'success');
            
        } catch (error) {
            console.error(`❌ Errore download ${format}:`, error);
            this.showToast(`Errore download ${format}: ${error.message}`, 'error');
        }
    }
    
    // ===== UI STATE MANAGEMENT =====
    
    showSection(sectionName) {
        console.log('🔍 showSection called with:', sectionName, 'currentSection:', this.currentSection);
        
        // Only show sections if we're in the app section
        if (this.currentSection !== 'app') {
            console.log('❌ Not in app section, returning');
            return;
        }
        
        // Hide all sections - UPDATED: included previewSection
        const sections = ['uploadSection', 'previewSection', 'projectParamsSection', 'configSection', 'resultsSection'];
        sections.forEach(id => {
            const element = document.getElementById(id);
            if (element) element.style.display = 'none';
        });
        
        // Show target section
        const targetSectionId = sectionName + 'Section';
        const targetSection = document.getElementById(targetSectionId);
        console.log('🎯 Looking for element with ID:', targetSectionId, 'found:', !!targetSection);
        if (targetSection) {
            targetSection.style.display = 'block';
            console.log('✅ Section shown:', targetSectionId);
        } else {
            console.log('❌ Element not found:', targetSectionId);
        }
        
        // Handle special cases
        if (sectionName === 'config' && this.currentData) {
            // If we have data, add reconfigure handler
            const processBtn = document.getElementById('processBtn');
            if (processBtn) {
                processBtn.innerHTML = '<i class="fas fa-cogs"></i><span>Ricalcola Packing</span>';
                processBtn.onclick = () => this.reconfigureAndProcess();
            }
        } else if (sectionName === 'config') {
            // Reset to normal process button
            const processBtn = document.getElementById('processBtn');
            if (processBtn) {
                processBtn.innerHTML = '<i class="fas fa-cogs"></i><span>Calcola Packing</span>';
                processBtn.onclick = () => this.processFile();
            }
        }
    }
    
    showResults(data) {
        // NUOVO: Calcola e imposta automaticamente l'altezza soffitto se disponibile
        this.setAutomaticCeilingHeight(data);
        
        // Update configuration UI with backend values
        this.updateConfigurationUI(data.config);
        
        // Update header stats
        this.updateHeaderStats(data);
        
        // Update tables CON NUOVO SISTEMA RAGGRUPPAMENTO
        this.updateGroupedStandardTable(data.summary, data.blocks_standard || [], data.config);
        this.updateGroupedCustomTable(data.blocks_custom || []);
        
        // Update configuration card
        this.updateConfigurationCard(data);
        
        // Update metrics
        this.updateMetrics(data.metrics);
        
        // Auto-save project when results are shown
        this.autoSaveProject(data);
    }
    
    updateConfigurationUI(config) {
        // Update row offset slider and value
        if (config && config.row_offset !== undefined) {
            const rowOffsetSlider = document.getElementById('rowOffset');
            const rowOffsetValue = document.getElementById('rowOffsetValue');
            
            if (rowOffsetSlider && rowOffsetValue) {
                rowOffsetSlider.value = config.row_offset;
                rowOffsetValue.textContent = `${config.row_offset} mm`;
                this.updatePresetButtons(config.row_offset.toString());
                console.log(`🔄 UI aggiornata con offset: ${config.row_offset}mm`);
            }
        }
        
        // Update project name if provided
        if (config && config.project_name) {
            const projectNameInput = document.getElementById('projectName');
            if (projectNameInput) {
                projectNameInput.value = config.project_name;
            }
        }
    }
    
    updateHeaderStats(data) {
        // Update results page stats cards (primary location in Step 5)
        const statStandardResults = document.getElementById('statStandardResults');
        const statCustomResults = document.getElementById('statCustomResults');
        const statEfficiencyResults = document.getElementById('statEfficiencyResults');
        
        const totalStandard = Object.values(data.summary || {}).reduce((a, b) => a + b, 0);
        const totalCustom = (data.blocks_custom || []).length;
        const totalBlocks = totalStandard + totalCustom;
        const efficiency = data.metrics?.efficiency || 0;
        
        // Update results page stats cards (shown in Step 5)
        if (statStandardResults && statCustomResults && statEfficiencyResults) {
            statStandardResults.textContent = totalStandard;
            statCustomResults.textContent = totalCustom;
            statEfficiencyResults.textContent = totalBlocks;
        }
        
        // Hide header stats (no longer used)
        const headerStats = document.getElementById('headerStats');
        if (headerStats) {
            headerStats.style.display = 'none';
        }
    }
    
    updateGroupedStandardTable(summary, standardBlocks, sessionConfig = null) {
        const tbody = document.querySelector('#standardTable tbody');
        if (!tbody) return;
        
        tbody.innerHTML = '';
        
        // 🧪 DEBUG: Vedere cosa arriva dal backend
        console.log('� [DEBUG] SessionConfig received:', sessionConfig);
        console.log('🔍 [DEBUG] Summary received:', summary);
        
        // �🔧 NEW: Usa le informazioni del backend se disponibili, altrimenti calcola localmente
        let typeMap;
        let blockDimensionsForBackend;
        
        if (sessionConfig && sessionConfig.block_schema) {
            // Usa le informazioni dal backend (più affidabile)
            console.log('📦 Using backend block schema:', sessionConfig.block_schema);
            typeMap = this.createTypeMapFromBackend(sessionConfig.block_schema);
            blockDimensionsForBackend = {
                block_widths: sessionConfig.block_widths,
                block_height: sessionConfig.block_height
            };
        } else {
            // Fallback: calcola localmente (per compatibilità)
            console.log('📦 Fallback: calculating locally');
            console.log('🔍 [DEBUG] SessionConfig structure:', sessionConfig);
            const currentBlockDimensions = getCurrentBlockDimensions();
            blockDimensionsForBackend = getBlockDimensionsForBackend();
            typeMap = this.createDynamicTypeMap(blockDimensionsForBackend);
        }
        
        console.log('📦 [DEBUG] Final type mapping for standard blocks:', typeMap);
        
        // 🔧 NEW: Aggiorna il titolo e mostra indicatore se si usano dimensioni personalizzate
        this.updateStandardBlocksTitle(blockDimensionsForBackend);
        
        // Raggruppa per categoria mostrando le dimensioni personalizzate
        for (const [type, count] of Object.entries(summary || {})) {
            const typeInfo = typeMap[type] || { 
                name: `Tipo ${type}`, 
                size: 'N/A', 
                category: 'X',
                width: 0,
                height: 0
            };
            
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>
                    <div class="flex items-center space-x-3">
                        <div class="category-badge bg-blue-100 text-blue-800 px-2 py-1 rounded font-bold">${typeInfo.category}</div>
                        <span><strong>${typeInfo.name}</strong></span>
                    </div>
                </td>
                <td class="text-center">
                    <span class="count-badge bg-green-100 text-green-800 px-2 py-1 rounded">${count}</span>
                </td>
                <td>${typeInfo.size} mm</td>
                <td class="text-sm text-gray-600">
                    ${typeInfo.category}1, ${typeInfo.category}2, ..., ${typeInfo.category}${count}
                </td>
            `;
            tbody.appendChild(row);
        }
        
        if (Object.keys(summary || {}).length === 0) {
            const row = document.createElement('tr');
            row.innerHTML = '<td colspan="4" class="text-center text-gray-500">Nessun blocco standard</td>';
            tbody.appendChild(row);
        }
    }
    
    createTypeMapFromBackend(blockSchema) {
        const typeMap = {};
        const sizeToLetter = blockSchema.size_to_letter;
        const height = blockSchema.block_height;
        
        // Crea mapping basato sulle informazioni del backend
        for (const [width, letter] of Object.entries(sizeToLetter)) {
            const widthInt = parseInt(width);
            const typeKey = `std_${widthInt}x${height}`;
            typeMap[typeKey] = {
                name: `Blocco Tipo ${letter}`,
                size: `${widthInt} × ${height}`,
                category: letter,
                width: widthInt,
                height: height
            };
        }
        
        return typeMap;
    }
    
    createDynamicTypeMap(blockDimensionsForBackend) {
        const typeMap = {};
        const widths = blockDimensionsForBackend.block_widths;
        const height = blockDimensionsForBackend.block_height;
        
        // Ordina per dimensione decrescente e assegna lettere A, B, C...
        const sortedWidths = [...widths].sort((a, b) => b - a);
        
        sortedWidths.forEach((width, index) => {
            const letter = String.fromCharCode(65 + index); // A, B, C...
            const typeKey = `std_${width}x${height}`;
            typeMap[typeKey] = {
                name: `Blocco Tipo ${letter}`,
                size: `${width} × ${height}`,
                category: letter,
                width: width,
                height: height
            };
        });
        
        return typeMap;
    }
    
    async updateStandardBlocksTitle(blockDimensions) {
        const titleElement = document.getElementById('standardBlocksTitle');
        const indicatorElement = document.getElementById('customBlocksIndicator');
        
        if (!titleElement || !indicatorElement) return;
        
        // Carica i valori di default dal sistema
        const defaultConfig = await this.loadDefaultBlocksConfig();
        const defaultWidths = defaultConfig.block_widths;
        const defaultHeight = defaultConfig.block_height;
        
        const currentWidths = blockDimensions.block_widths.sort((a, b) => b - a);
        const currentHeight = blockDimensions.block_height;
        
        const isCustom = (
            !this.arraysEqual(currentWidths, defaultWidths.sort((a, b) => b - a)) ||
            currentHeight !== defaultHeight
        );
        
        if (isCustom) {
            titleElement.textContent = 'Blocchi Standard (Dimensioni Personalizzate)';
            indicatorElement.style.display = 'inline-flex';
            indicatorElement.title = `Dimensioni personalizzate: ${currentWidths.join('×')}×${currentHeight}mm`;
        } else {
            titleElement.textContent = 'Blocchi Standard (Raggruppati)';
            indicatorElement.style.display = 'none';
        }
    }
    
    // Helper function to compare arrays
    arraysEqual(a, b) {
        if (a.length !== b.length) return false;
        for (let i = 0; i < a.length; i++) {
            if (a[i] !== b[i]) return false;
        }
        return true;
    }

    updateGroupedCustomTable(customBlocks) {
        const tbody = document.querySelector('#customTable tbody');
        if (!tbody) return;
        
        tbody.innerHTML = '';
        
        // Raggruppa custom per dimensioni simili (simulazione raggruppamento)
        const customGroups = this.groupCustomBlocks(customBlocks);
        
        let categoryLetter = 'D'; // Inizia da D per custom
        
        Object.entries(customGroups).forEach(([dimensions, blocks]) => {
            const count = blocks.length;
            
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>
                    <div class="flex items-center space-x-3">
                        <div class="category-badge bg-green-100 text-green-800 px-2 py-1 rounded font-bold">${categoryLetter}</div>
                        <span><strong>Pezzo Custom ${categoryLetter}</strong></span>
                    </div>
                </td>
                <td class="text-center">
                    <span class="count-badge bg-orange-100 text-orange-800 px-2 py-1 rounded">${count}</span>
                </td>
                <td>${dimensions} mm</td>
                <td class="text-sm text-gray-600">
                    ${blocks.map((b, i) => `${categoryLetter}${i+1}`).join(', ')}
                </td>
            `;
            tbody.appendChild(row);
            
            // Prossima categoria
            categoryLetter = String.fromCharCode(categoryLetter.charCodeAt(0) + 1);
        });
        
        if (customBlocks.length === 0) {
            const row = document.createElement('tr');
            row.innerHTML = '<td colspan="4" class="text-center text-gray-500">Nessun pezzo custom</td>';
            tbody.appendChild(row);
        }
    }
    
    groupCustomBlocks(customBlocks) {
        const groups = {};
        const tolerance = 5; // mm di tolleranza per raggruppare
        
        customBlocks.forEach(block => {
            const width = Math.round(block.width);
            const height = Math.round(block.height);
            const key = `${width} × ${height}`;
            
            // Cerca gruppo esistente con dimensioni simili
            let foundGroup = null;
            for (const [existingKey, existingBlocks] of Object.entries(groups)) {
                const [existingW, existingH] = existingKey.split(' × ').map(Number);
                if (Math.abs(width - existingW) <= tolerance && Math.abs(height - existingH) <= tolerance) {
                    foundGroup = existingKey;
                    break;
                }
            }
            
            if (foundGroup) {
                groups[foundGroup].push(block);
            } else {
                groups[key] = [block];
            }
        });
        
        return groups;
    }

    // FUNZIONI LEGACY PER COMPATIBILITA'
    updateStandardTable(summary) {
        console.log('⚠️ Usando funzione legacy updateStandardTable');
        return this.updateGroupedStandardTable(summary, [], null);
    }

    updateCustomTable(customBlocks) {
        console.log('⚠️ Usando funzione legacy updateCustomTable');
        return this.updateGroupedCustomTable(customBlocks);
    }
    
    updateMetrics(metrics) {
        // Metrics removed as requested
    }
    
    // ===== CONFIGURATION CARD =====
    
    updateConfigurationCard(data) {
        const configCard = document.getElementById('configurationCard');
        if (!configCard) return;
        
        // NUOVO: Se non ci sono dati, prova a usare le dimensioni in cache
        if (!data && this.calculatedDimensions) {
            console.log('🔄 Usando dimensioni dalla cache per Configuration Card:', this.calculatedDimensions);
            data = { 
                measurements: {
                    area_total: this.calculatedDimensions.area_total,
                    max_width: this.calculatedDimensions.max_width,
                    max_height: this.calculatedDimensions.max_height,
                    apertures_count: this.calculatedDimensions.apertures_count,
                    perimeter: this.calculatedDimensions.perimeter,
                    geometry_type: this.calculatedDimensions.geometry_type
                }
            };
        }
        
        console.log('🔧 Aggiornando Configuration Card con parametri dinamici');
        
        // NUOVO: Usa sempre i parametri dinamici dell'utente se disponibili
        let dynamicParams = null;
        try {
            dynamicParams = this.collectProjectParameters();
            console.log('✅ Parametri dinamici raccolti per Configuration Card:', dynamicParams);
        } catch (e) {
            console.log('⚠️ Non riesco a raccogliere parametri dinamici, uso dati backend:', e);
        }
        
        let hasConfigData = false;
        
        // Material section - USA PARAMETRI DINAMICI PRIMA
        const materialSection = document.getElementById('materialSection');
        const materialInfo = document.getElementById('materialInfo');
        let materialText = '';
        
        if (dynamicParams?.material) {
            // USA PARAMETRI DINAMICI DELL'UTENTE
            const mat = dynamicParams.material;
            materialText = `<div class="info-item"><strong>Tipo:</strong> ${mat.type.charAt(0).toUpperCase() + mat.type.slice(1)}</div>`;
            materialText += `<div class="info-item"><strong>Spessore:</strong> ${mat.thickness_mm} mm</div>`;
            materialText += `<div class="info-item"><strong>Densità:</strong> ${mat.density_kg_m3} kg/m³</div>`;
            console.log('✅ Usando parametri dinamici per materiale');
        } else if (data.config_estratto_finale?.Materiale) {
            // Fallback ai dati backend
            const mat = data.config_estratto_finale.Materiale;
            if (mat.Spessore) materialText += `<strong>Spessore:</strong> ${mat.Spessore}<br>`;
            if (mat.Densità) materialText += `<strong>Densità:</strong> ${mat.Densità}<br>`;
            if (mat.Tipo) materialText += `<strong>Tipo:</strong> ${mat.Tipo}<br>`;
        } else {
            // Ultimo fallback
            materialText = `<div class="info-item"><strong>Spessore:</strong> 18 mm</div><div class="info-item"><strong>Densità:</strong> 650 kg/m³</div><div class="info-item"><strong>Tipo:</strong> Standard</div>`;
        }
        
        if (materialInfo) {
            materialInfo.innerHTML = materialText;
            materialSection.style.display = 'block';
            hasConfigData = true;
        }
        
        // Guide section - USA PARAMETRI DINAMICI PRIMA  
        const guideSection = document.getElementById('guideSection');
        const guideInfo = document.getElementById('guideInfo');
        let guideText = '';
        
        if (dynamicParams?.guide) {
            // USA PARAMETRI DINAMICI DELL'UTENTE
            const guide = dynamicParams.guide;
            guideText = `<div class="info-item"><strong>Larghezza:</strong> ${guide.width_mm} mm</div>`;
            guideText += `<div class="info-item"><strong>Tipo:</strong> ${guide.type}</div>`;
            guideText += `<div class="info-item"><strong>Profondità:</strong> ${guide.depth_mm} mm</div>`;
            if (guide.max_load_kg) {
                guideText += `<div class="info-item"><strong>Carico Max:</strong> ${guide.max_load_kg} kg</div>`;
            }
            console.log('✅ Usando parametri dinamici per guide');
        } else if (data.config_estratto_finale?.Guide) {
            // Fallback ai dati backend
            const guide = data.config_estratto_finale.Guide;
            if (guide.Tipo) guideText += `<strong>Tipo:</strong> ${guide.Tipo}<br>`;
            if (guide.Larghezza) guideText += `<strong>Larghezza:</strong> ${guide.Larghezza}<br>`;
            if (guide.Profondità) guideText += `<strong>Profondità:</strong> ${guide.Profondità}<br>`;
        } else {
            // Ultimo fallback
            guideText = `<div class="info-item"><strong>Tipo:</strong> 75mm Standard</div><div class="info-item"><strong>Larghezza:</strong> 75 mm</div><div class="info-item"><strong>Profondità:</strong> 25 mm</div><div class="info-item"><strong>Carico Max:</strong> 40 kg</div>`;
        }
        
        if (guideInfo) {
            guideInfo.innerHTML = guideText;
            guideSection.style.display = 'block';
            hasConfigData = true;
        }
        
        // NUOVO: Spessore Chiusura section - USA PARAMETRI DINAMICI
        const closureSection = document.getElementById('closureSection');
        const closureInfo = document.getElementById('closureInfo');
        let closureText = '';
        
        if (dynamicParams?.calculated) {
            // USA PARAMETRI CALCOLATI DINAMICAMENTE
            const calc = dynamicParams.calculated;
            closureText = `<div class="info-item"><strong>Formula:</strong> ${calc.formula_description}</div>`;
            closureText += `<div class="info-item"><strong>Spessore Finale:</strong> ${calc.closure_thickness_mm} mm</div>`;
            console.log('✅ Usando calcoli dinamici per spessore chiusura');
        } else {
            // Fallback con nuova formula: materiale + guida + materiale
            closureText = `<div class="info-item"><strong>Spessore Finale:</strong> 111 mm</div><div class="info-item"><strong>Formula:</strong> 18mm + 75mm + 18mm = 111mm</div>`;
        }
        
        if (closureInfo) {
            closureInfo.innerHTML = closureText;
            if (closureSection) closureSection.style.display = 'block';
            hasConfigData = true;
        } else {
            // Crea la sezione se non esiste
            this.createClosureSectionInConfigCard(closureText);
        }
        
        // NUOVO: Parete Position section - USA PARAMETRI DINAMICI
        const wallSection = document.getElementById('wallSection');
        const wallInfo = document.getElementById('wallInfo');
        let wallText = '';
        
        if (dynamicParams?.wall) {
            // USA PARAMETRI DINAMICI DELL'UTENTE
            const wall = dynamicParams.wall;
            wallText = `<div class="info-item"><strong>Tipo:</strong> ${wall.position === 'new' ? 'Parete Nuova' : 'Parete Attaccata'}</div>`;
            if (wall.is_attached && wall.attachment_points.length > 0) {
                wallText += `<div class="info-item"><strong>Punti Appoggio:</strong> ${wall.attachment_points.join(', ')}</div>`;
                wallText += `<div class="info-item"><strong>Inizio da:</strong> ${dynamicParams.calculated.starting_point}</div>`;
            }
            console.log('✅ Usando parametri dinamici per configurazione parete');
        } else {
            // Fallback
            wallText = `<div class="info-item"><strong>Tipo:</strong> Parete Nuova</div><div class="info-item"><strong>Inizio da:</strong> sinistra</div>`;
        }
        
        if (wallInfo) {
            wallInfo.innerHTML = wallText;
            if (wallSection) wallSection.style.display = 'block';
            hasConfigData = true;
        } else {
            // Crea la sezione se non esiste
            this.createWallSectionInConfigCard(wallText);
        }
        
        // Block section - con config_estratto_finale
        const blockSection = document.getElementById('blockSection');
        const blockInfo = document.getElementById('blockInfo');
        let blockText = '';
        
        if (data.config_estratto_finale?.Blocchi) {
            const blocchi = data.config_estratto_finale.Blocchi;
            if (blocchi.Larghezze) blockText += `<strong>Larghezze:</strong> ${blocchi.Larghezze}<br>`;
            if (blocchi.Altezza) blockText += `<strong>Altezza:</strong> ${blocchi.Altezza}<br>`;
        } else if (data.config?.block_widths && data.config?.block_height) {
            const widthsStr = Array.isArray(data.config.block_widths) 
                ? data.config.block_widths.join('mm, ') + 'mm'
                : data.config.block_widths;
            blockText = `<strong>Larghezze:</strong> ${widthsStr}<br><strong>Altezza:</strong> ${data.config.block_height} mm<br>`;
        }
        
        // Aggiungi info dai risultati se disponibili
        if (data.result?.block_usage) {
            const totalBlocks = Object.values(data.result.block_usage).reduce((sum, count) => sum + count, 0);
            blockText += `<strong>Totale Blocchi:</strong> ${totalBlocks}<br>`;
            
            // Dettaglio per ogni larghezza
            blockText += `<strong>Utilizzo:</strong><br>`;
            for (const [width, count] of Object.entries(data.result.block_usage)) {
                if (count > 0) {
                    blockText += `• ${width}mm: ${count} pz<br>`;
                }
            }
        }
        
        if (blockText) {
            blockInfo.innerHTML = blockText;
            blockSection.style.display = 'block';
            hasConfigData = true;
        }

        
        // Moretti section - FORZA SEMPRE VISIBILE
        const morettiSection = document.getElementById('morettiSection');
        const morettiInfo = document.getElementById('morettiInfo');
        let morettiText = '';
        
        if (data.config_estratto_finale?.Moretti) {
            const moretti = data.config_estratto_finale.Moretti;
            if (moretti.Richiesti !== undefined) morettiText += `<strong>Richiesti:</strong> ${moretti.Richiesti}<br>`;
            if (moretti.Altezza) morettiText += `<strong>Altezza:</strong> ${moretti.Altezza}<br>`;
            if (moretti.Quantità) morettiText += `<strong>Quantità:</strong> ${moretti.Quantità}`;
        } else {
            const morettiSources = [
                data.enhanced_info?.automatic_measurements?.moretti_requirements,
                data.enhanced_info?.moretti_requirements,
                data.moretti_requirements
            ];
            
            for (const moretti of morettiSources) {
                if (moretti) {
                    if (moretti.needed !== undefined) {
                        morettiText += `<strong>Richiesti:</strong> ${moretti.needed ? 'Sì' : 'No'}<br>`;
                        if (moretti.needed) {
                            if (moretti.height_mm) morettiText += `<strong>Altezza:</strong> ${moretti.height_mm} mm<br>`;
                            if (moretti.count) morettiText += `<strong>Quantità:</strong> ${moretti.count}`;
                        }
                    }
                    break;
                }
            }
        }
        
        // Se non hai dati, mostra placeholder per test
        if (!morettiText) {
            morettiText = `<strong>Richiesti:</strong> Sì<br><strong>Altezza:</strong> 150 mm<br><strong>Quantità:</strong> 8`;
        }
        
        morettiInfo.innerHTML = morettiText;
        morettiSection.style.display = 'block';
        hasConfigData = true;
        
        // Construction section - FORZA SEMPRE VISIBILE
        const constructionSection = document.getElementById('constructionSection');
        const constructionInfo = document.getElementById('constructionInfo');
        let constructionText = '';
        
        if (data.enhanced_info?.construction_details || data.result) {
            if (data.result?.total_rows) constructionText += `<strong>Filari Totali:</strong> ${data.result.total_rows}<br>`;
            if (data.result?.arrow_positions && data.result.arrow_positions.length > 0) {
                constructionText += `<strong>Punti di Partenza:</strong> ${data.result.arrow_positions.length}<br>`;
            }
            if (data.enhanced_info?.construction_details?.construction_method) {
                constructionText += `<strong>Metodo:</strong> ${data.enhanced_info.construction_details.construction_method}`;
            }
        }
        
        // Se non hai dati, mostra placeholder per test
        if (!constructionText) {
            constructionText = `<strong>Filari Totali:</strong> 6<br><strong>Punti di Partenza:</strong> 2<br><strong>Metodo:</strong> Standard`;
        }
        
        constructionInfo.innerHTML = constructionText;
        constructionSection.style.display = 'block';
        hasConfigData = true;
        
        // Show/hide the entire card based on whether we have data
        configCard.style.display = hasConfigData ? 'block' : 'none';
        console.log('🔧 Configuration card updated', { 
            hasConfigData, 
            sectionsVisible: {
                material: materialSection.style.display !== 'none',
                guide: guideSection.style.display !== 'none', 
                block: blockSection.style.display !== 'none',
                moretti: morettiSection.style.display !== 'none',
                construction: constructionSection.style.display !== 'none'
            }
        });
        
        console.log('🔧 Configuration Card aggiornata con parametri dinamici');
    }
    
    // NUOVO: Crea sezione spessore chiusura se non esiste
    createClosureSectionInConfigCard(closureText) {
        const configCard = document.querySelector('.config-info-grid');
        if (configCard) {
            const closureSection = document.createElement('div');
            closureSection.className = 'config-section';
            closureSection.id = 'closureSection';
            closureSection.innerHTML = `
                <h4>Spessore Chiusura</h4>
                <div id="closureInfo">${closureText}</div>
            `;
            configCard.appendChild(closureSection);
            console.log('➕ Sezione spessore chiusura creata dinamicamente');
        }
    }
    
    // NUOVO: Crea sezione configurazione parete se non esiste
    createWallSectionInConfigCard(wallText) {
        const configCard = document.querySelector('.config-info-grid');
        if (configCard) {
            const wallSection = document.createElement('div');
            wallSection.className = 'config-section';
            wallSection.id = 'wallSection';
            wallSection.innerHTML = `
                <h4>Configurazione Parete</h4>
                <div id="wallInfo">${wallText}</div>
            `;
            configCard.appendChild(wallSection);
            console.log('➕ Sezione configurazione parete creata dinamicamente');
        }
    }
    
    // ===== CONFIGURATION =====
    
    async loadDefaultBlocksConfig() {
        try {
            const response = await fetch('/api/config/blocks');
            if (response.ok) {
                const config = await response.json();
                return config;
            }
        } catch (error) {
            console.warn('Errore caricamento configurazione blocchi:', error);
        }
        // Fallback ai valori hardcoded se l'API non è disponibile
        return {
            block_widths: [1239, 826, 413],
            block_height: 495,
            block_widths_string: "1239,826,413"
        };
    }
    
    async getConfiguration() {
        const projectName = document.getElementById('projectName')?.value || 'Progetto Parete';
        // rowOffset rimosso: ora calcolato automaticamente dall'algoritmo bidirezionale
        
        // Carica la configurazione di default dai valori reali del sistema
        const defaultConfig = await this.loadDefaultBlocksConfig();
        
        // Get block dimensions from saved configuration instead of removed input field
        const savedBlockDimensions = getCurrentBlockDimensions();
        const blockWidths = savedBlockDimensions ? 
            `${savedBlockDimensions.block1.width},${savedBlockDimensions.block2.width},${savedBlockDimensions.block3.width}` :
            defaultConfig.block_widths_string;
        
        return {
            projectName,
            blockWidths
        };
    }
    
    async loadBlockConfigurationIntoUI() {
        try {
            const config = await this.loadDefaultBlocksConfig();
            
            // Aggiorna anche i valori nell'HTML hardcoded (card attiva)
            const activeBlock1Dims = document.getElementById('activeBlock1Dims');
            const activeBlock2Dims = document.getElementById('activeBlock2Dims');
            const activeBlock3Dims = document.getElementById('activeBlock3Dims');
            
            if (config.block_widths && config.block_widths.length >= 3) {
                if (activeBlock1Dims) {
                    activeBlock1Dims.textContent = `${config.block_widths[0]}×${config.block_height} mm`;
                }
                if (activeBlock2Dims) {
                    activeBlock2Dims.textContent = `${config.block_widths[1]}×${config.block_height} mm`;
                }
                if (activeBlock3Dims) {
                    activeBlock3Dims.textContent = `${config.block_widths[2]}×${config.block_height} mm`;
                }
            }
            
            console.log('✅ Configurazione blocchi caricata dinamicamente:', config);
        } catch (error) {
            console.warn('⚠️ Errore caricamento configurazione blocchi:', error);
        }
    }
    
    // ===== MODAL HANDLING =====
    
    openFullscreenPreview() {
        const previewImage = document.getElementById('previewImage');
        const fullscreenModal = document.getElementById('fullscreenModal');
        const fullscreenImage = document.getElementById('fullscreenImage');
        
        if (previewImage && fullscreenModal && fullscreenImage && previewImage.src) {
            fullscreenImage.src = previewImage.src;
            fullscreenModal.style.display = 'flex';
        }
    }
    
    closeFullscreenPreview() {
        const fullscreenModal = document.getElementById('fullscreenModal');
        if (fullscreenModal) {
            fullscreenModal.style.display = 'none';
        }
    }
    
    // ===== LOADING STATES =====
    
    showLoading(title = 'Caricamento...', message = 'Operazione in corso') {
        const overlay = document.getElementById('loadingOverlay');
        const titleEl = document.getElementById('loadingTitle');
        const messageEl = document.getElementById('loadingMessage');
        
        if (overlay) overlay.style.display = 'flex';
        if (titleEl) titleEl.textContent = title;
        if (messageEl) messageEl.textContent = message;
    }
    
    hideLoading() {
        const overlay = document.getElementById('loadingOverlay');
        if (overlay) overlay.style.display = 'none';
    }
    
    // ===== NOTIFICATIONS =====
    
    showToast(message, type = 'info', duration = 5000) {
        const container = document.getElementById('toastContainer');
        if (!container) return;
        
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        
        // Add icon based on type
        let icon = '';
        switch (type) {
            case 'success':
                icon = '<i class="fas fa-check-circle"></i>';
                break;
            case 'error':
                icon = '<i class="fas fa-exclamation-circle"></i>';
                break;
            case 'warning':
                icon = '<i class="fas fa-exclamation-triangle"></i>';
                break;
            case 'info':
            default:
                icon = '<i class="fas fa-info-circle"></i>';
                break;
        }
        
        toast.innerHTML = `${icon}<span>${message}</span>`;
        
        container.appendChild(toast);
        
        // Auto remove
        setTimeout(() => {
            if (toast.parentNode) {
                toast.style.transform = 'translateX(100%)';
                setTimeout(() => {
                    if (toast.parentNode) {
                        toast.parentNode.removeChild(toast);
                    }
                }, 300);
            }
        }, duration);
    }
    
    // ===== RESET =====
    
    resetApp() {
        this.currentFile = null;
        this.currentSessionId = null;
        this.currentData = null;
        this.projectSaved = false; // Reset save flag
        this.isReusedProject = false; // Reset reuse flag
        
        // Reset forms
        const fileInput = document.getElementById('fileInput');
        if (fileInput) fileInput.value = '';
        
        const projectName = document.getElementById('projectName');
        if (projectName) projectName.value = 'Progetto Parete';
        
        const rowOffset = document.getElementById('rowOffset');
        if (rowOffset) {
            rowOffset.value = '826';
            const rowOffsetValue = document.getElementById('rowOffsetValue');
            if (rowOffsetValue) rowOffsetValue.textContent = '826 mm';
            this.updatePresetButtons('826');
        }
        
        // Block widths now managed by global settings, not this field
        
        // Hide sections
        const fileInfo = document.getElementById('fileInfo');
        if (fileInfo) fileInfo.style.display = 'none';
        
        const headerStats = document.getElementById('headerStats');
        if (headerStats) headerStats.style.display = 'none';
        
        // Reset process button
        const processBtn = document.getElementById('processBtn');
        if (processBtn) {
            processBtn.innerHTML = '<i class="fas fa-cogs"></i><span>Calcola Packing</span>';
            processBtn.onclick = () => this.processFile();
        }
        
        // Unlock block dimensions editing when app is reset
        this.unlockBlockDimensionsEditing();
        
        // Update navigation state to re-enable global settings
        this.updateNavigationState();
        
        // Show upload section and switch to app
        this.showMainSection('app');
        this.showSection('upload');
        
        this.showToast('Applicazione ripristinata', 'info');
    }
    
    resetToUpload() {
        console.log('🔄 Resetting to upload section...');
        
        // Clear current file but keep configurations
        this.currentFile = null;
        this.currentSessionId = null;
        this.currentData = null;
        
        // Reset file input
        const fileInput = document.getElementById('fileInput');
        if (fileInput) fileInput.value = '';
        
        // Clear file name display
        const fileName = document.getElementById('fileName');
        if (fileName) fileName.textContent = '';
        
        // Hide file info
        const fileInfo = document.getElementById('fileInfo');
        if (fileInfo) fileInfo.style.display = 'none';
        
        const headerStats = document.getElementById('headerStats');
        if (headerStats) headerStats.style.display = 'none';
        
        // Reset upload area to initial state
        const uploadArea = document.getElementById('uploadArea');
        if (uploadArea) {
            uploadArea.classList.remove('has-file');
        }
        
        // Unlock block dimensions editing
        this.unlockBlockDimensionsEditing();
        
        // Update navigation state
        this.updateNavigationState();
        
        // Show upload section
        this.showSection('upload');
        
        this.showToast('File rimosso - pronto per nuovo upload', 'info');
    }
    
    // Auto-save project when processing is complete
    autoSaveProject(data) {
        if (!this.currentFile || !data) {
            console.log('❌ Auto-save bloccato: mancano file o dati');
            return;
        }
        
        if (this.projectSaved) {
            console.log('❌ Auto-save bloccato: progetto già salvato');
            return;
        }
        
        if (this.isReusedProject) {
            console.log('❌ Auto-save bloccato: progetto riutilizzato');
            return;
        }
        
        if (!this.currentSessionId) {
            console.log('❌ Auto-save bloccato: manca session_id');
            return;
        }
        
        console.log('✅ Iniziando auto-save progetto...');
        console.log('📁 File corrente:', this.currentFile.name);
        console.log('🔑 Session ID:', this.currentSessionId);
        
        // Extract project information
        const filename = this.currentFile.name;
        const projectName = filename.replace(/\.(dwg|dxf)$/i, '');
        
        // Calculate totals
        const totalStandard = Object.values(data.summary || {}).reduce((a, b) => a + b, 0);
        const totalCustom = (data.blocks_custom || []).length;
        const totalBlocks = totalStandard + totalCustom;
        
        console.log('📊 Totale blocchi calcolato:', totalBlocks);
        
        // Get efficiency
        const efficiency = data.metrics?.efficiency ? 
            `${Math.round(data.metrics.efficiency * 100)}%` : 'N/A';
        
        // Extract wall dimensions from data if available
        const wallDimensions = data.wall_info ? 
            `${data.wall_info.width}×${data.wall_info.height}mm` : 'N/A';
        
        // Get configuration data
        const config = this.getConfiguration();
        
        // NEW: Get current system profile name
        const activeProfileSelector = document.getElementById('activeProfileSelector');
        const selectedProfileId = activeProfileSelector ? parseInt(activeProfileSelector.value) : null;
        let profileName = 'Sistema Standard'; // Default
        
        if (selectedProfileId && window.systemProfiles) {
            const activeProfile = window.systemProfiles.find(p => p.id === selectedProfileId);
            if (activeProfile) {
                profileName = activeProfile.name;
                console.log('📋 Profilo attivo al salvataggio:', profileName);
            }
        } else {
            // Try to get from displayed profile name
            const displayedProfileName = document.getElementById('displayedProfileName');
            if (displayedProfileName && displayedProfileName.textContent) {
                profileName = displayedProfileName.textContent.replace('⭐ ', '').trim();
                console.log('📋 Profilo dal display:', profileName);
            }
        }
        
        // NEW: Collect extended configuration parameters
        const extendedConfig = {
            // Material configuration (try app instance first, then session data)
            material_config: this.currentMaterialConfig || data.session?.material_config || {},
            
            // Guide specifications  
            guide_spec: this.currentGuideSpec || data.session?.guide_spec || {},
            
            // Wall position settings
            wall_position: this.currentWallPosition || data.session?.wall_position || {},
            
            // Custom dimensions
            custom_dimensions: this.currentCustomDimensions || data.session?.custom_dimensions || {},
            
            // Construction method
            construction_method: this.currentConstructionMethod || data.session?.construction_method || {},
            
            // Moretti settings
            moretti_settings: this.currentMorettiSettings || data.session?.moretti_settings || {},
            
            // Store session data references for debugging
            session_stored: {
                material_config: !!data.session?.material_config,
                guide_spec: !!data.session?.guide_spec,
                wall_position: !!data.session?.wall_position
            }
        };
        
        console.log('🔧 Extended Config per salvataggio:', extendedConfig);
        
        // Get saved file path from session data (this comes from backend after upload)
        const savedFilePath = data.saved_file_path || '';
        console.log('💾 Percorso file salvato per progetto:', savedFilePath);
        
        // Prepare project data for saving
        const projectData = {
            name: projectName,
            filename: filename,
            file_path: savedFilePath, // This is the path where the file was saved on server
            profile_name: profileName, // NEW: Nome profilo/sistema utilizzato
            block_dimensions: getCurrentBlockDimensions(),
            color_theme: getCurrentColorTheme(),
            packing_config: {
                row_offset: config.rowOffset,
                block_widths: config.blockWidths,
                project_name: config.projectName
            },
            extended_config: extendedConfig,  // NEW: Include extended configuration
            results: {
                summary: data.summary,
                blocks_custom: data.blocks_custom,
                metrics: data.metrics
            },
            wall_dimensions: wallDimensions,
            total_blocks: totalBlocks,
            efficiency: efficiency,
            svg_path: data.svg_path || null,
            pdf_path: data.pdf_path || null,
            json_path: data.json_path || null
        };
        
        // Mark as saving to prevent duplicates
        this.projectSaved = true;
        console.log('💾 Salvataggio automatico progetto:', projectName);
        
        // Verifica che l'utente sia autenticato
        const token = sessionStorage.getItem('access_token');
        if (!token) {
            console.log('❌ Auto-save bloccato: utente non autenticato');
            this.showToast('Effettua il login per salvare automaticamente i progetti', 'warning');
            return;
        }
        
        // Save asynchronously (don't wait for result to avoid blocking UI)
        saveCurrentProject(projectData).catch(error => {
            console.warn('Auto-save project failed:', error);
            this.projectSaved = false; // Reset on failure to allow retry
        });
    }
    
    // ===== NEW: PROJECT PARAMETERS SECTION =====
    
    setupProjectParametersListeners() {
        console.log('🔧 Setup Project Parameters Listeners');
        
        // Navigation buttons for project parameters section are now handled in main setupEventListeners
        
        document.getElementById('proceedToConfig')?.addEventListener('click', () => {
            // Validate and collect parameters before proceeding
            const params = this.collectProjectParameters();
            if (this.validateProjectParameters(params)) {
                this.showSection('config');
                this.updateParametersSummary(params);
            }
        });
        
        // Material configuration listeners
        const materialType = document.getElementById('materialType');
        const materialThickness = document.getElementById('materialThickness');
        const materialDensity = document.getElementById('materialDensity');
        
        materialType?.addEventListener('change', () => {
            this.handleMaterialTypeChange();
            this.updateParametersSummary();
        });
        
        materialThickness?.addEventListener('input', debounce(() => {
            this.updateParametersSummary();
        }, 300));
        
        materialDensity?.addEventListener('input', debounce(() => {
            this.updateParametersSummary();
        }, 300));
        
        // Guide configuration listeners
        const guideRadios = document.querySelectorAll('input[name="guideType"]');
        const guideDepth = document.getElementById('guideDepth');
        
        guideRadios.forEach(radio => {
            radio.addEventListener('change', () => {
                this.handleGuideTypeChange();
                this.updateParametersSummary();
            });
        });
        
        guideDepth?.addEventListener('input', debounce(() => {
            this.updateParametersSummary();
        }, 300));
        
        // Wall position configuration listeners
        const wallTypeRadios = document.querySelectorAll('input[name="wallType"]');
        wallTypeRadios.forEach(radio => {
            radio.addEventListener('change', () => {
                this.handleWallTypeChange();
                this.updateParametersSummary();
            });
        });
        
        // Attachment points listeners
        const attachmentCheckboxes = document.querySelectorAll('.attachment-checkbox');
        attachmentCheckboxes.forEach(checkbox => {
            checkbox.addEventListener('change', () => {
                this.handleAttachmentPointsChange();
                this.updateParametersSummary();
            });
        });
        
        // Ceiling height and moretti listeners
        const ceilingHeight = document.getElementById('ceilingHeight');
        const enableMoretti = document.getElementById('enableMoretti');
        
        ceilingHeight?.addEventListener('input', debounce(() => {
            this.updateParametersSummary();
        }, 300));
        
        enableMoretti?.addEventListener('change', () => {
            this.updateParametersSummary();
        });
        
        // Advanced options listeners
        const enableAutoMeasurements = document.getElementById('enableAutoMeasurements');
        const enableCostEstimation = document.getElementById('enableCostEstimation');
        
        enableAutoMeasurements?.addEventListener('change', () => {
            this.updateParametersSummary();
        });
        
        enableCostEstimation?.addEventListener('change', () => {
            this.updateParametersSummary();
        });
        
        // Initialize UI state
        this.initializeProjectParametersUI();
    }
    
    initializeProjectParametersUI() {
        // Set default values and update UI accordingly
        this.handleMaterialTypeChange();
        this.handleGuideTypeChange();
        this.handleWallTypeChange();
        this.updateParametersSummary();
    }
    
    handleMaterialTypeChange() {
        const materialType = document.getElementById('materialType');
        const materialThickness = document.getElementById('materialThickness');
        const materialDensity = document.getElementById('materialDensity');
        
        if (!materialType) return;
        
        // Set default values based on material type
        const materialDefaults = {
            'melamine': { thickness: 18, density: 650 },
            'mdf': { thickness: 16, density: 700 },
            'chipboard': { thickness: 18, density: 650 },
            'plywood': { thickness: 15, density: 550 },
            'custom': { thickness: 18, density: 650 }
        };
        
        const selected = materialType.value;
        const defaults = materialDefaults[selected] || materialDefaults['melamine'];
        
        if (materialThickness) materialThickness.value = defaults.thickness;
        if (materialDensity) materialDensity.value = defaults.density;
    }
    
    handleGuideTypeChange() {
        const selectedGuide = document.querySelector('input[name="guideType"]:checked');
        const guideDepth = document.getElementById('guideDepth');
        
        if (!selectedGuide) return;
        
        // Update guide option visuals
        document.querySelectorAll('.guide-option').forEach(option => {
            option.classList.remove('active');
        });
        
        const selectedOption = selectedGuide.nextElementSibling;
        if (selectedOption) {
            selectedOption.classList.add('active');
        }
        
        // Set default depth based on guide width
        const guideDefaults = {
            '50': 20,
            '75': 25,
            '100': 30
        };
        
        if (guideDepth) {
            guideDepth.value = guideDefaults[selectedGuide.value] || 25;
        }
    }
    
    handleWallTypeChange() {
        const selectedWallType = document.querySelector('input[name="wallType"]:checked');
        const attachmentPoints = document.getElementById('attachmentPoints');
        
        if (!selectedWallType) return;
        
        // Update wall option visuals
        document.querySelectorAll('.wall-option').forEach(option => {
            option.classList.remove('active');
        });
        
        const selectedOption = selectedWallType.nextElementSibling;
        if (selectedOption) {
            selectedOption.classList.add('active');
        }
        
        // Show/hide attachment points configuration
        if (attachmentPoints) {
            if (selectedWallType.value === 'attached') {
                attachmentPoints.style.display = 'block';
            } else {
                attachmentPoints.style.display = 'none';
                // Clear attachment checkboxes when hiding
                const checkboxes = attachmentPoints.querySelectorAll('.attachment-checkbox');
                checkboxes.forEach(checkbox => checkbox.checked = false);
            }
        }
    }
    
    handleAttachmentPointsChange() {
        const checkboxes = document.querySelectorAll('.attachment-checkbox:checked');
        console.log(`📎 Attachment points selected: ${checkboxes.length}`);
    }
    
    collectProjectParameters() {
        console.log('🔧 Raccogliendo parametri di configurazione dinamici...');
        
        // Material parameters - DINAMICI
        const materialType = document.getElementById('materialType')?.value || 'melamine';
        const materialThickness = parseInt(document.getElementById('materialThickness')?.value) || 18;
        const materialDensity = parseInt(document.getElementById('materialDensity')?.value) || 650;
        
        // Guide parameters - DINAMICI con validazione
        const selectedGuide = document.querySelector('input[name="guideType"]:checked');
        const guideType = selectedGuide ? selectedGuide.value : '75';
        const guideDepth = parseInt(document.getElementById('guideDepth')?.value) || 25;
        
        // Wall position parameters - DINAMICI con logica enhanced
        const selectedWallType = document.querySelector('input[name="wallType"]:checked');
        const wallType = selectedWallType ? selectedWallType.value : 'new';
        
        // MIGLIORATO: Raccolta punti di appoggio più robusta
        const attachmentPoints = [];
        const existingWallsSides = []; // Per backend compatibility
        
        if (wallType === 'attached') {
            const checkboxes = document.querySelectorAll('.attachment-checkbox:checked');
            checkboxes.forEach(checkbox => {
                const side = checkbox.id.replace('attach', '').toLowerCase();
                attachmentPoints.push(side);
                existingWallsSides.push(side);
            });
            
            console.log('📍 Punti di appoggio rilevati:', attachmentPoints);
        }
        
        // Ceiling parameters - DINAMICI CON CALCOLO AUTOMATICO
        const ceilingHeight = this.getCalculatedCeilingHeight() || parseInt(document.getElementById('ceilingHeight')?.value) || 2700;
        const enableMoretti = document.getElementById('enableMoretti')?.checked !== false; // Default true
        
        // Advanced parameters - DINAMICI 
        const enableAutoMeasurements = document.getElementById('enableAutoMeasurements')?.checked !== false; // Default true
        const enableCostEstimation = document.getElementById('enableCostEstimation')?.checked !== false; // Default true
        
        // NUOVO: Calcolo automatico spessore chiusura (per validazione frontend)
        // Formula: materiale + guida + materiale
        const calculatedClosureThickness = (materialThickness * 2) + parseInt(guideType);
        
        // NUOVO: Fixed walls configuration per backend
        const fixedWalls = attachmentPoints.map(side => ({
            position: side,
            type: "structural"
        }));
        
        const params = {
            // Material configuration
            material: {
                type: materialType,
                thickness_mm: materialThickness,
                density_kg_m3: materialDensity,
                // NUOVO: Aggiunti per completezza
                strength_factor: 1.0,
                thermal_conductivity: 0.15
            },
            
            // Guide configuration  
            guide: {
                type: `${guideType}mm`,
                width_mm: parseInt(guideType),
                depth_mm: guideDepth,
                // NUOVO: Carico massimo stimato
                max_load_kg: parseInt(guideType) === 50 ? 30 : (parseInt(guideType) === 75 ? 40 : 50)
            },
            
            // Wall position configuration
            wall: {
                position: wallType,
                is_attached: wallType === 'attached',
                is_attached_to_existing: wallType === 'attached', // Backend compatibility
                attachment_points: attachmentPoints,
                existing_walls_sides: existingWallsSides, // Backend compatibility
                fixed_walls: fixedWalls // Enhanced backend format
            },
            
            // Ceiling and moretti configuration
            ceiling: {
                height_mm: ceilingHeight,
                enable_moretti_calculation: enableMoretti,
                // NUOVO: Pre-calcolo se servono moretti
                moretti_needed: enableMoretti && ceilingHeight > 2400
            },
            
            // Advanced options
            advanced: {
                enable_automatic_measurements: enableAutoMeasurements,
                enable_cost_estimation: enableCostEstimation,
                // NUOVO: Opzioni di calcolo
                enable_enhanced_packing: true,
                use_optimized_algorithms: true
            },
            
            // NUOVO: Parametri calcolati (per validazione)
            calculated: {
                closure_thickness_mm: calculatedClosureThickness,
                formula_description: `${materialThickness}mm + ${guideType}mm + ${materialThickness}mm = ${calculatedClosureThickness}mm`,
                starting_point: wallType === 'attached' && attachmentPoints.length > 0 ? attachmentPoints[0] : 'left'
            }
        };
        
        console.log('✅ Parametri raccolti dinamicamente:', params);
        console.log(`📐 Spessore calcolato: ${params.calculated.formula_description}`);
        console.log(`📍 Punto di partenza: ${params.calculated.starting_point}`);
        
        return params;
    }
    
    validateProjectParameters(params) {
        console.log('🔍 Validando parametri dinamici:', params);
        
        // Basic validation with enhanced messages
        if (params.material.thickness_mm < 10 || params.material.thickness_mm > 50) {
            this.showToast('Spessore materiale deve essere tra 10 e 50 mm', 'error');
            return false;
        }
        
        if (params.ceiling.height_mm < 2200 || params.ceiling.height_mm > 4000) {
            this.showToast('Altezza soffitto deve essere tra 2200 e 4000 mm', 'error');
            return false;
        }
        
        // NUOVO: Validazione specifica per pareti attaccate
        if (params.wall.is_attached && params.wall.attachment_points.length === 0) {
            this.showToast('Seleziona almeno un punto di appoggio per pareti attaccate', 'warning');
            return false;
        }
        
        // NUOVO: Validazione guide
        const validGuideWidths = [50, 75, 100];
        if (!validGuideWidths.includes(params.guide.width_mm)) {
            this.showToast('Seleziona una larghezza guide valida (50, 75, 100 mm)', 'error');
            return false;
        }
        
        // NUOVO: Validazione combinazioni materiale + guide
        if (params.material.thickness_mm <= 12 && params.guide.width_mm >= 100) {
            this.showToast('Materiali sottili (≤12mm) non sono compatibili con guide larghe (≥100mm)', 'warning');
            return false;
        }
        
        // NUOVO: Mostra calcolo spessore chiusura in tempo reale
        const calculatedThickness = params.calculated.closure_thickness_mm;
        console.log(`✅ Validazione superata. Spessore chiusura calcolato: ${calculatedThickness}mm`);
        
        // NUOVO: Mostra strategia di montaggio
        if (params.wall.is_attached) {
            console.log(`📍 Strategia montaggio: Iniziare da ${params.calculated.starting_point}`);
        }
        
        return true;
    }
    
    updateParametersSummary(params = null) {
        if (!params) {
            params = this.collectProjectParameters();
        }
        
        // Update summary display
        const summaryMaterial = document.getElementById('summaryMaterial');
        const summaryGuides = document.getElementById('summaryGuides');
        const summaryWallType = document.getElementById('summaryWallType');
        const summarySystem = document.getElementById('summarySystem');
        
        if (summaryMaterial) {
            summaryMaterial.textContent = `${params.material.type.charAt(0).toUpperCase() + params.material.type.slice(1)} ${params.material.thickness_mm}mm`;
        }
        
        if (summaryGuides) {
            summaryGuides.textContent = `${params.guide.width_mm}mm ${params.guide.width_mm === 75 ? 'Standard' : params.guide.width_mm === 50 ? 'Strette' : 'Larghe'}`;
        }
        
        if (summaryWallType) {
            let wallText = params.wall.is_attached ? 'Parete Attaccata' : 'Parete Nuova';
            if (params.wall.is_attached && params.wall.attachment_points.length > 0) {
                wallText += ` (${params.wall.attachment_points.join(', ')})`;
            }
            summaryWallType.textContent = wallText;
        }
        
        // Aggiorna il sistema nel riepilogo (viene settato quando si seleziona un profilo)
        // Il valore viene gestito dalla funzione updateProfileDisplay in system-profiles.js
        
        // NUOVO: Aggiungi elementi calcolati dinamicamente 
        this.updateDynamicCalculatedFields(params);
    }
    
    // NUOVO: Funzione per aggiornare campi calcolati dinamicamente
    updateDynamicCalculatedFields(params) {
        // Update o crea spessore chiusura
        let closureElement = document.getElementById('summaryClosureThickness');
        if (!closureElement) {
            const summaryContent = document.getElementById('paramsSummaryContent');
            if (summaryContent) {
                const closureItem = document.createElement('div');
                closureItem.className = 'summary-item';
                closureItem.innerHTML = `
                    <span class="summary-label">Spessore Chiusura:</span>
                    <span class="summary-value" id="summaryClosureThickness">${params.calculated.closure_thickness_mm}mm</span>
                `;
                summaryContent.appendChild(closureItem);
            }
        } else {
            closureElement.textContent = `${params.calculated.closure_thickness_mm}mm`;
        }
        
        // Update o crea punto di partenza
        let startingElement = document.getElementById('summaryStartingPoint');
        if (!startingElement) {
            const summaryContent = document.getElementById('paramsSummaryContent');
            if (summaryContent) {
                const startingItem = document.createElement('div');
                startingItem.className = 'summary-item';
                startingItem.innerHTML = `
                    <span class="summary-label">Punto di Partenza:</span>
                    <span class="summary-value" id="summaryStartingPoint">Da ${params.calculated.starting_point}</span>
                `;
                summaryContent.appendChild(startingItem);
            }
        } else {
            const startingText = params.wall.is_attached ? 
                `Da ${params.calculated.starting_point}` : 'Da centro/sinistra';
            startingElement.textContent = startingText;
        }
        
        console.log(`📐 Aggiornati campi calcolati: Spessore ${params.calculated.closure_thickness_mm}mm, Start ${params.calculated.starting_point}`);
    }
    
    // NUOVO: Setup listeners per aggiornamento real-time
    setupRealTimeParametersUpdate() {
        console.log('⚡ Setup listeners per aggiornamento parametri in tempo reale');
        
        // Materiale - aggiornamento immediato spessore chiusura
        const materialThickness = document.getElementById('materialThickness');
        materialThickness?.addEventListener('input', debounce(() => {
            const params = this.collectProjectParameters();
            this.updateDynamicCalculatedFields(params);
            console.log(`📏 Nuovo spessore materiale: ${params.material.thickness_mm}mm → Chiusura: ${params.calculated.closure_thickness_mm}mm`);
        }, 200));
        
        // Guide - aggiornamento immediato spessore chiusura
        const guideRadios = document.querySelectorAll('input[name="guideType"]');
        guideRadios.forEach(radio => {
            radio.addEventListener('change', () => {
                const params = this.collectProjectParameters();
                this.updateDynamicCalculatedFields(params);
                console.log(`🔧 Nuova guida: ${params.guide.width_mm}mm → Chiusura: ${params.calculated.closure_thickness_mm}mm`);
            });
        });
        
        // Parete attaccata - aggiornamento immediato punto partenza  
        const wallTypeRadios = document.querySelectorAll('input[name="wallType"]');
        wallTypeRadios.forEach(radio => {
            radio.addEventListener('change', () => {
                const params = this.collectProjectParameters();
                this.updateDynamicCalculatedFields(params);
                console.log(`🏠 Nuova tipologia parete: ${params.wall.position} → Start: ${params.calculated.starting_point}`);
                
                // Mostra/nasconde opzioni attachment
                const attachmentPoints = document.getElementById('attachmentPoints');
                if (attachmentPoints) {
                    attachmentPoints.style.display = params.wall.is_attached ? 'block' : 'none';
                }
            });
        });
        
        // Punti di appoggio - aggiornamento punto partenza
        const attachmentCheckboxes = document.querySelectorAll('.attachment-checkbox');
        attachmentCheckboxes.forEach(checkbox => {
            checkbox.addEventListener('change', () => {
                const params = this.collectProjectParameters();
                this.updateDynamicCalculatedFields(params);
                console.log(`📍 Punti appoggio aggiornati: [${params.wall.attachment_points.join(', ')}] → Start: ${params.calculated.starting_point}`);
            });
        });
        
        console.log('✅ Real-time update listeners configurati');
    }
    
    // ===== NEW: PREVIEW STEP LISTENERS =====
    
    setupPreviewStepListeners() {
        console.log('🔧 Setup Preview Step Listeners');
        
        // Navigation buttons
        document.getElementById('backToUploadFromPreview')?.addEventListener('click', () => {
            console.log('🔙 backToUploadFromPreview clicked!');
            this.resetToUpload();
        });
        
        document.getElementById('acceptPreview')?.addEventListener('click', () => {
            // Proceed to project parameters if preview is acceptable
            if (this.currentPreviewData) {
                this.showSection('projectParams');
            } else {
                this.showToast('Nessuna anteprima disponibile. Ricarica il file.', 'error');
            }
        });
        
        document.getElementById('reprocessFile')?.addEventListener('click', () => {
            // Reload the current file for preview
            if (this.currentFile) {
                this.generateFilePreview(this.currentFile);
            } else {
                this.showToast('Nessun file caricato da riprocessare', 'error');
            }
        });
        
        // Preview controls
        document.getElementById('zoomInPreview')?.addEventListener('click', () => {
            this.zoomPreviewCanvas(1.2);
        });
        
        document.getElementById('zoomOutPreview')?.addEventListener('click', () => {
            this.zoomPreviewCanvas(0.8);
        });
        
        document.getElementById('centerPreview')?.addEventListener('click', () => {
            this.centerPreviewCanvas();
        });
        
        // Canvas mouse interactions for panning
        const previewCanvas = document.getElementById('previewCanvas');
        if (previewCanvas) {
            this.setupCanvasInteractions(previewCanvas);
        }
    }
    
    // ===== NEW: FILE PREVIEW GENERATION =====
    
    async generateFilePreview(file) {
        console.log('�🚨🚨 GENERATE FILE PREVIEW CALLED! 🚨🚨🚨');
        console.log('�🔍 Generating file preview for:', file.name);
        console.log('🔍 File size:', file.size, 'bytes');
        console.log('🔍 File type:', file.type);
        
        // NUOVO: Inizia misurazione durata Step 1→2
        this.step1to2StartTime = performance.now();
        this.processingStartTime = Date.now(); // NUOVO: Timestamp per controlli background
        console.log('⏱️ Iniziata misurazione durata Step 1→2');
        
        // Show loading states
        this.showPreviewLoading(true);
        
        // 🚀 SMART LOADING: Avvia loading per conversione DWG
        window.smartLoading?.showForOperation('dwgConversion', {
            fileName: file.name,
            fileSize: file.size,
            onCancel: () => {
                console.log('❌ Conversione annullata dall\'utente');
                this.showPreviewLoading(false);
            }
        });
        
        try {
            const formData = new FormData();
            formData.append('file', file);
            
            console.log('📡 Sending request to /api/preview-conversion');
            
            const response = await fetch('/api/preview-conversion', {
                method: 'POST',
                body: formData,
                headers: {
                    'Authorization': `Bearer ${window.authManager.token}`
                }
            });
            
            console.log('📡 Response status:', response.status);
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Errore conversione file');
            }
            
            const result = await response.json();
            console.log('✅ Preview data received:', result);
            
            // Store preview data with session ID for reuse
            this.currentPreviewData = result;
            this.previewSessionId = result.preview_session_id; // NUOVO: Store per riutilizzo
            
            // Update UI with preview data PRIMA di mostrare la sezione
            this.updatePreviewUI(result);
            
            // Hide loading and show preview section
            this.showPreviewLoading(false);
            this.showSection('preview');
            
            // NUOVO: 🚀 SMART LOADING rimane attivo fino al completamento totale
            console.log('⏳ L\'animazione continuerà fino al caricamento completo della pagina Step 2...');
            
            // NUOVO: 🚀 Invece di aspettare solo UI + tempo minimo, aspettiamo che tutto sia COMPLETAMENTE pronto
            console.log('⏳ Aspettando completamento totale del processing...');
            
            // Usa waitForCompleteProcessing che aspetta che tutto sia realmente finito
            const startWaitTime = performance.now();
            await this.waitForCompleteProcessing(result);
            
            const actualWaitTime = performance.now() - startWaitTime;
            console.log(`⏱️ Processing completato in ${actualWaitTime.toFixed(0)}ms (${(actualWaitTime/1000).toFixed(1)}s)`);
            
            // 🚀 SMART LOADING: Solo ora nascondi l'animazione (quando tutto è realmente pronto)
            window.smartLoading?.hide();
            
            // NUOVO: Termina misurazione durata Step 1→2
            if (this.step1to2StartTime) {
                this.step1to2Duration = performance.now() - this.step1to2StartTime;
            }
            
        } catch (error) {
            console.error('❌ Preview generation error:', error);
            
            // 🚀 SMART LOADING: Nascondi loading anche in caso di errore
            window.smartLoading?.hide();
            
            this.showPreviewLoading(false);
            this.showToast(`Errore generazione preview: ${error.message}`, 'error');
            
            // Return to upload section on error
            this.showSection('upload');
        }
    }
    
    // NUOVO: Attende che tutti gli elementi dell'UI dello step 2 siano completamente caricati
    async waitForPreviewUIComplete() {
        return new Promise((resolve) => {
            console.log('⏳ Aspettando il caricamento completo dell\'UI dello step 2...');
            
            let checkAttempts = 0;
            const maxAttempts = 60; // Aumentato a 6 secondi (60 * 100ms)
            
            const checkUIComplete = () => {
                checkAttempts++;
                
                // Controlla che tutti gli elementi critici siano visibili e caricati
                const previewCanvas = document.getElementById('previewCanvas');
                const measurementsData = document.getElementById('measurementsData');
                const conversionDetails = document.getElementById('conversionDetails');
                const previewSection = document.getElementById('previewSection');
                
                // Debug dettagliato degli elementi
                console.log(`🔍 [${checkAttempts}/${maxAttempts}] Debug elementi trovati:`, {
                    previewCanvas: !!previewCanvas,
                    measurementsData: !!measurementsData,
                    conversionDetails: !!conversionDetails,
                    previewSection: !!previewSection
                });
                
                // Controlli più flessibili
                const isCanvasLoaded = previewCanvas && 
                    (previewCanvas.width > 0 || previewCanvas.dataset.imageLoaded === 'true' || previewCanvas.dataset.imageLoaded === 'error');
                
                const isMeasurementsVisible = !measurementsData || 
                    (measurementsData.style.display !== 'none' && measurementsData.innerHTML.trim() !== '') ||
                    measurementsData.textContent.length > 0;
                
                const isConversionDetailsVisible = !conversionDetails || 
                    conversionDetails.style.display !== 'none' ||
                    conversionDetails.innerHTML.trim() !== '';
                
                const isPreviewSectionVisible = previewSection && 
                    previewSection.style.display === 'block';
                
                // Criteri più flessibili - almeno canvas e section devono essere ok
                const isUIComplete = isCanvasLoaded && isPreviewSectionVisible;
                
                console.log(`🔍 Check UI completo (${checkAttempts}/${maxAttempts}):`, {
                    canvas: isCanvasLoaded,
                    canvasSize: previewCanvas ? `${previewCanvas.width}x${previewCanvas.height}` : 'N/A',
                    imageLoaded: previewCanvas?.dataset.imageLoaded || 'N/A',
                    measurements: isMeasurementsVisible,
                    conversionDetails: isConversionDetailsVisible,
                    previewSection: isPreviewSectionVisible,
                    complete: isUIComplete
                });
                
                if (isUIComplete) {
                    console.log('✅ UI dello step 2 completamente caricata!');
                    // Aggiungi un delay più lungo per essere sicuri
                    setTimeout(() => resolve(), 300);
                } else if (checkAttempts >= maxAttempts) {
                    console.log('⚠️ Timeout raggiunto - procediamo comunque per evitare hang');
                    resolve();
                } else {
                    // Riprova tra 100ms
                    setTimeout(checkUIComplete, 100);
                }
            };
            
            // Inizia il controllo dopo un delay più lungo per permettere al DOM di aggiornarsi
            setTimeout(checkUIComplete, 500);
        });
    }
    
    // NUOVO: Aspetta che tutto il processing sia completamente terminato (non solo l'UI)
    async waitForCompleteProcessing(previewData) {
        return new Promise((resolve) => {
            console.log('⏳ Aspettando completamento totale del processing...');
            
            let checkAttempts = 0;
            const maxAttempts = 300; // Massimo 30 secondi (300 * 100ms) - Aumentato per essere più sicuri
            const minWaitTime = 3000; // NUOVO: Tempo minimo di attesa (3 secondi)
            const startTime = Date.now();
            
            const checkProcessingComplete = () => {
                checkAttempts++;
                const elapsedTime = Date.now() - startTime;
                
                // 1. Controlla che l'UI sia caricata
                const isUIReady = this.checkUIReady();
                
                // 2. Controlla che tutti i dati siano processati
                const isDataProcessed = this.checkDataProcessed(previewData);
                
                // 3. Controlla che non ci siano operazioni in background
                const areBackgroundOpsComplete = this.checkBackgroundOperations();
                
                // 4. NUOVO: Assicurati che sia passato il tempo minimo
                const isMinTimeElapsed = elapsedTime >= minWaitTime;
                
                const isCompletelyDone = isUIReady && isDataProcessed && areBackgroundOpsComplete && isMinTimeElapsed;
                
                console.log(`🔍 Check processing completo (${checkAttempts}/${maxAttempts}):`, {
                    ui: isUIReady,
                    data: isDataProcessed,
                    background: areBackgroundOpsComplete,
                    minTime: isMinTimeElapsed,
                    elapsed: `${(elapsedTime / 1000).toFixed(1)}s`,
                    complete: isCompletelyDone
                });
                
                if (isCompletelyDone) {
                    console.log('✅ Processing completamente terminato!');
                    resolve();
                } else if (checkAttempts >= maxAttempts) {
                    console.log('⚠️ Timeout processing raggiunto - procediamo comunque');
                    resolve();
                } else {
                    // Riprova tra 100ms
                    setTimeout(checkProcessingComplete, 100);
                }
            };
            
            // Inizia il controllo dopo un delay per permettere all'elaborazione di stabilizzarsi
            setTimeout(checkProcessingComplete, 500);
        });
    }
    
    // Helper: Controlla che l'UI sia pronta - CONTROLLI MOLTO RIGOROSI per Step 2
    checkUIReady() {
        // 1. Elementi principali dello Step 2
        const previewSection = document.getElementById('previewSection');
        const previewCanvas = document.getElementById('previewCanvas');
        const measurementsData = document.getElementById('measurementsData');
        const conversionDetails = document.getElementById('conversionDetails');
        
        // 2. Elementi di controllo e navigazione
        const previewActions = document.querySelector('.preview-actions');
        const navigationButtons = document.getElementById('acceptPreview');
        const previewLoadingMain = document.getElementById('previewLoadingMain');
        
        // 3. Controlli rigorosi STEP BY STEP
        const isSectionVisible = previewSection && 
            previewSection.style.display === 'block' && 
            !previewSection.hidden;
            
        const isCanvasReady = previewCanvas && 
            previewCanvas.style.display !== 'none' &&
            (previewCanvas.width > 0 || previewCanvas.dataset.imageLoaded === 'true') &&
            previewCanvas.offsetWidth > 0 && previewCanvas.offsetHeight > 0;
            
        const areMeasurementsVisible = measurementsData && 
            measurementsData.style.display !== 'none' && 
            measurementsData.innerHTML.trim() !== '' &&
            measurementsData.offsetHeight > 0;
            
        const areDetailsVisible = conversionDetails && 
            conversionDetails.style.display !== 'none' && 
            conversionDetails.innerHTML.trim() !== '' &&
            conversionDetails.offsetHeight > 0;
            
        const areActionsVisible = previewActions && 
            previewActions.offsetHeight > 0 && 
            !previewActions.hidden;
            
        const areNavigationReady = navigationButtons && 
            navigationButtons.offsetHeight > 0 && 
            !navigationButtons.disabled;
            
        const isLoadingHidden = !previewLoadingMain || 
            previewLoadingMain.style.display === 'none' || 
            previewLoadingMain.hidden;
        
        // 4. NUOVO: Verifica che il DOM sia stabile (no resize/reflow in corso)
        const isStable = document.readyState === 'complete' && 
            !document.hidden &&
            previewSection.getBoundingClientRect().height > 0;
        
        const isUIReady = isSectionVisible && isCanvasReady && areMeasurementsVisible && 
                         areDetailsVisible && areActionsVisible && areNavigationReady && 
                         isLoadingHidden && isStable;
        
        console.log(`🔍 checkUIReady() - CONTROLLI RIGOROSI:`, {
            section: isSectionVisible,
            canvas: isCanvasReady,
            canvasSize: previewCanvas ? `${previewCanvas.offsetWidth}x${previewCanvas.offsetHeight}` : 'N/A',
            measurements: areMeasurementsVisible,
            details: areDetailsVisible,
            actions: areActionsVisible,
            navigation: areNavigationReady,
            loadingHidden: isLoadingHidden,
            domStable: isStable,
            overall: isUIReady
        });
        
        return isUIReady;
    }
    
    // Helper: Controlla che tutti i dati siano stati processati
    checkDataProcessed(previewData) {
        if (!previewData) {
            console.log(`❌ checkDataProcessed: No preview data`);
            return false;
        }
        
        // Controlla che tutti i componenti dei dati siano presenti E che l'UI li mostri
        const hasPreviewImage = !!previewData.preview_image;
        const hasMeasurements = !!previewData.measurements;
        const hasConversionDetails = !!previewData.conversion_details;
        const hasSessionId = !!previewData.preview_session_id;
        
        // NUOVO: Controlla anche che i dati siano stati renderizzati nella UI
        const previewCanvas = document.getElementById('previewCanvas');
        const measurementsData = document.getElementById('measurementsData');
        const conversionDetails = document.getElementById('conversionDetails');
        
        const isImageRendered = previewCanvas && 
            (previewCanvas.dataset.imageLoaded === 'true' || previewCanvas.width > 0);
        const areMeasurementsRendered = measurementsData && 
            measurementsData.innerHTML.includes(previewData.measurements?.area_total || '');
        const areDetailsRendered = conversionDetails && 
            conversionDetails.innerHTML.includes('Conversione completata');
        
        const isDataProcessed = hasPreviewImage && hasMeasurements && hasConversionDetails && 
                               hasSessionId && isImageRendered && areMeasurementsRendered && areDetailsRendered;
        
        console.log(`🔍 checkDataProcessed():`, {
            hasImage: hasPreviewImage,
            hasMeasurements: hasMeasurements,
            hasDetails: hasConversionDetails,
            hasSession: hasSessionId,
            imageRendered: isImageRendered,
            measurementsRendered: areMeasurementsRendered,
            detailsRendered: areDetailsRendered,
            overall: isDataProcessed
        });
        
        return isDataProcessed;
    }
    
    // Helper: Controlla che non ci siano operazioni in background
    checkBackgroundOperations() {
        // NUOVO: Controlli più rigorosi per operazioni in background
        
        // 1. Controlla se ci sono fetch attive
        const hasPendingFetches = window.fetch && window.fetch.pending > 0;
        
        // 2. Controlla se ci sono timer/interval attivi (esclusi quelli del sistema)
        const hasActiveTimers = false; // Per ora disabilitato per evitare conflitti
        
        // 3. Controlla se l'immagine del canvas sta ancora caricando
        const previewCanvas = document.getElementById('previewCanvas');
        const isImageStillLoading = previewCanvas && 
            previewCanvas.dataset.imageLoaded !== 'true' && 
            previewCanvas.dataset.imageLoaded !== 'error';
        
        // 4. Controlla se ci sono elementi con loading spinner visibili
        const loadingElements = document.querySelectorAll('.spinner, .loading, [style*="loading"]');
        const hasVisibleLoadings = Array.from(loadingElements).some(el => 
            el.style.display !== 'none' && !el.hidden);
        
        // 5. Aggiungi un delay minimo per dare tempo al rendering
        const minTimeElapsed = Date.now() - (this.processingStartTime || 0) > 2000; // 2 secondi minimo
        
        const areBackgroundOpsComplete = !hasPendingFetches && !hasActiveTimers && 
                                       !isImageStillLoading && !hasVisibleLoadings && minTimeElapsed;
        
        console.log(`🔍 checkBackgroundOperations():`, {
            pendingFetches: hasPendingFetches,
            activeTimers: hasActiveTimers,
            imageLoading: isImageStillLoading,
            visibleLoadings: hasVisibleLoadings,
            minTimeElapsed: minTimeElapsed,
            overall: areBackgroundOpsComplete
        });
        
        return areBackgroundOpsComplete;
    }
    
    // NUOVO: Stima il tempo di processing basato su file e operazione
    estimateProcessingTime(file) {
        if (!file) return 5000; // Default 5 secondi
        
        const fileSize = file.size;
        const fileName = file.name.toLowerCase();
        
        // Stima basata su dimensione file
        let baseTime = 3000; // Base 3 secondi
        
        if (fileSize > 5 * 1024 * 1024) { // > 5MB
            baseTime = 15000; // 15 secondi
        } else if (fileSize > 1 * 1024 * 1024) { // > 1MB
            baseTime = 8000; // 8 secondi
        } else if (fileSize > 500 * 1024) { // > 500KB
            baseTime = 5000; // 5 secondi
        }
        
        // Aggiustamento per tipo file
        if (fileName.endsWith('.dwg')) {
            baseTime *= 2; // DWG più lento
        } else if (fileName.endsWith('.dxf')) {
            baseTime *= 1.5; // DXF medio
        }
        // SVG già veloce, nessun moltiplicatore
        
        // Aggiustamento per platform (se disponibile)
        if (navigator.platform.includes('Linux')) {
            baseTime *= 3; // Linux più lento
        }
        
        console.log(`📊 Stima processing per ${file.name}:`, {
            fileSize: `${(fileSize/1024).toFixed(0)}KB`,
            fileType: fileName.split('.').pop(),
            estimatedTime: `${baseTime}ms (${(baseTime/1000).toFixed(1)}s)`
        });
        
        return baseTime;
    }
    
    showPreviewLoading(show) {
        const loadingElement = document.getElementById('previewLoadingMain');
        const canvasElement = document.getElementById('previewCanvas');
        const measurementsLoading = document.getElementById('measurementsLoading');
        const measurementsData = document.getElementById('measurementsData');
        
        if (show) {
            if (loadingElement) loadingElement.style.display = 'flex';
            if (canvasElement) canvasElement.style.display = 'none';
            if (measurementsLoading) measurementsLoading.style.display = 'flex';
            if (measurementsData) measurementsData.style.display = 'none';
        } else {
            if (loadingElement) loadingElement.style.display = 'none';
            if (canvasElement) canvasElement.style.display = 'block';
            if (measurementsLoading) measurementsLoading.style.display = 'none';
            if (measurementsData) measurementsData.style.display = 'block';
        }
    }
    
    updatePreviewUI(previewData) {
        // Update preview image
        this.renderPreviewImage(previewData.preview_image);
        
        // Update measurements
        this.updateMeasurementsPanel(previewData.measurements);
        
        // Update conversion details
        this.updateConversionDetails(previewData.conversion_details);
        
        // Show validation messages
        this.showValidationMessages(previewData.validation_messages);
    }
    
    renderPreviewImage(imageBase64) {
        const canvas = document.getElementById('previewCanvas');
        const ctx = canvas.getContext('2d');
        
        if (!canvas || !imageBase64) {
            console.warn('❌ Canvas o immagine mancanti per renderPreviewImage');
            return;
        }
        
        console.log('🖼️ Iniziando rendering immagine preview...');
        
        const img = new Image();
        img.onload = () => {
            // Set canvas size based on container
            const container = canvas.parentElement;
            const containerWidth = container.clientWidth - 40; // padding
            const containerHeight = container.clientHeight - 40;
            
            // Calculate scale to fit image in container
            const scaleX = containerWidth / img.width;
            const scaleY = containerHeight / img.height;
            const scale = Math.min(scaleX, scaleY, 1); // Don't scale up
            
            canvas.width = img.width * scale;
            canvas.height = img.height * scale;
            
            // Draw image
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
            
            // Store original dimensions for zoom/pan
            canvas.dataset.originalWidth = img.width;
            canvas.dataset.originalHeight = img.height;
            canvas.dataset.currentScale = scale;
            
            // NUOVO: Marca l'immagine come caricata per il controllo UI completo
            canvas.dataset.imageLoaded = 'true';
            
            console.log('✅ Preview image rendered successfully', {
                originalSize: `${img.width}x${img.height}`,
                canvasSize: `${canvas.width}x${canvas.height}`,
                scale: scale.toFixed(2)
            });
        };
        
        img.onerror = () => {
            console.error('❌ Failed to load preview image');
            this.showToast('Errore caricamento anteprima immagine', 'error');
            
            // NUOVO: Marca comunque come "caricata" per evitare hang
            canvas.dataset.imageLoaded = 'error';
        };
        
        // Set image source (remove data:image prefix if present)
        const imageData = imageBase64.startsWith('data:') ? imageBase64 : `data:image/png;base64,${imageBase64}`;
        img.src = imageData;
        
        console.log('🔄 Image source set, waiting for load...');
    }
    
    updateMeasurementsPanel(measurements) {
        const elements = {
            totalArea: document.getElementById('totalArea'),
            maxWidth: document.getElementById('maxWidth'),
            maxHeight: document.getElementById('maxHeight'),
            aperturesCount: document.getElementById('aperturesCount'),
            wallPerimeter: document.getElementById('wallPerimeter'),
            geometryType: document.getElementById('geometryType')
        };
        
        if (elements.totalArea) elements.totalArea.textContent = `${measurements.area_total} m²`;
        if (elements.maxWidth) elements.maxWidth.textContent = `${measurements.max_width} mm`;
        if (elements.maxHeight) elements.maxHeight.textContent = `${measurements.max_height} mm`;
        if (elements.aperturesCount) elements.aperturesCount.textContent = `${measurements.apertures_count} elementi`;
        if (elements.wallPerimeter) elements.wallPerimeter.textContent = `${measurements.perimeter} mm`;
        if (elements.geometryType) elements.geometryType.textContent = measurements.geometry_type;
    }
    
    updateConversionDetails(details) {
        const elements = {
            originalFileName: document.getElementById('originalFileName'),
            fileFormat: document.getElementById('fileFormat'),
            fileSize: document.getElementById('fileSize'),
            conversionStatus: document.getElementById('conversionStatus')
        };
        
        if (elements.originalFileName) elements.originalFileName.textContent = details.original_filename;
        if (elements.fileFormat) elements.fileFormat.textContent = details.file_format;
        if (elements.fileSize) elements.fileSize.textContent = details.file_size;
        
        // Show conversion details panel
        const detailsPanel = document.getElementById('conversionDetails');
        if (detailsPanel) detailsPanel.style.display = 'block';
    }
    
    showValidationMessages(messages) {
        const container = document.getElementById('validationMessages');
        if (!container) return;
        
        container.innerHTML = '';
        
        messages.forEach(msg => {
            const messageEl = document.createElement('div');
            messageEl.className = `validation-message ${msg.type}`;
            
            const icon = msg.type === 'success' ? 'fa-check-circle' :
                        msg.type === 'warning' ? 'fa-exclamation-triangle' :
                        msg.type === 'error' ? 'fa-times-circle' : 'fa-info-circle';
            
            messageEl.innerHTML = `
                <i class="fas ${icon}"></i>
                <span>${msg.message}</span>
            `;
            
            container.appendChild(messageEl);
        });
    }
    
    // Canvas interaction methods (zoom, pan)
    setupCanvasInteractions(canvas) {
        let isDragging = false;
        let lastX = 0;
        let lastY = 0;
        
        canvas.addEventListener('mousedown', (e) => {
            isDragging = true;
            lastX = e.clientX;
            lastY = e.clientY;
            canvas.style.cursor = 'grabbing';
        });
        
        canvas.addEventListener('mousemove', (e) => {
            if (isDragging) {
                const deltaX = e.clientX - lastX;
                const deltaY = e.clientY - lastY;
                
                // Implement panning logic here if needed
                lastX = e.clientX;
                lastY = e.clientY;
            }
        });
        
        canvas.addEventListener('mouseup', () => {
            isDragging = false;
            canvas.style.cursor = 'move';
        });
        
        canvas.addEventListener('mouseleave', () => {
            isDragging = false;
            canvas.style.cursor = 'move';
        });
    }
    
    zoomPreviewCanvas(factor) {
        const canvas = document.getElementById('previewCanvas');
        if (!canvas) return;
        
        const currentScale = parseFloat(canvas.dataset.currentScale || 1);
        const newScale = Math.max(0.1, Math.min(5, currentScale * factor));
        
        const originalWidth = parseFloat(canvas.dataset.originalWidth || canvas.width);
        const originalHeight = parseFloat(canvas.dataset.originalHeight || canvas.height);
        
        canvas.width = originalWidth * newScale;
        canvas.height = originalHeight * newScale;
        canvas.dataset.currentScale = newScale;
        
        // Re-render image at new scale if we have the data
        if (this.currentPreviewData) {
            this.renderPreviewImage(this.currentPreviewData.preview_image);
        }
    }
    
    centerPreviewCanvas() {
        const canvas = document.getElementById('previewCanvas');
        if (!canvas) return;
        
        // Reset to original size and center
        const container = canvas.parentElement;
        const originalWidth = parseFloat(canvas.dataset.originalWidth || canvas.width);
        const originalHeight = parseFloat(canvas.dataset.originalHeight || canvas.height);
        
        const containerWidth = container.clientWidth - 40;
        const containerHeight = container.clientHeight - 40;
        
        const scaleX = containerWidth / originalWidth;
        const scaleY = containerHeight / originalHeight;
        const scale = Math.min(scaleX, scaleY, 1);
        
        canvas.width = originalWidth * scale;
        canvas.height = originalHeight * scale;
        canvas.dataset.currentScale = scale;
        
        // Re-render
        if (this.currentPreviewData) {
            this.renderPreviewImage(this.currentPreviewData.preview_image);
        }
    }
}

// ===== UTILITY FUNCTIONS =====

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

function throttle(func, limit) {
    let inThrottle;
    return function() {
        const args = arguments;
        const context = this;
        if (!inThrottle) {
            func.apply(context, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    }
}

// ===== INITIALIZATION =====

document.addEventListener('DOMContentLoaded', () => {
    console.log('🎯 DOM Content Loaded - Parete TAKTAK®');
    
    // Initialize app
    window.wallPackingApp = new WallPackingApp();
    
    // Debug: verifica presenza pulsanti download
    setTimeout(() => {
        const buttons = ['downloadPDF', 'downloadDXF', 'downloadJSON'];
        buttons.forEach(btnId => {
            const btn = document.getElementById(btnId);
            if (btn) {
                console.log(`✅ ${btnId} button trovato`);
            } else {
                console.error(`❌ ${btnId} button NON trovato`);
            }
        });
        
        // Verifica navigazione
        const navItems = document.querySelectorAll('.nav-item');
        console.log(`🧭 Trovati ${navItems.length} elementi di navigazione`);
        navItems.forEach((item, index) => {
            console.log(`📍 Nav ${index + 1}: ${item.dataset.section}`);
        });
    }, 1000);
    
    // Global error handler
    window.addEventListener('error', (e) => {
        console.error('Global error:', e.error);
        if (window.wallPackingApp) {
            window.wallPackingApp.showToast('Si è verificato un errore imprevisto', 'error');
            window.wallPackingApp.hideLoading();
        }
    });
    
    // Unhandled promise rejection handler
    window.addEventListener('unhandledrejection', (e) => {
        console.error('Unhandled promise rejection:', e.reason);
        if (window.wallPackingApp) {
            window.wallPackingApp.showToast('Errore di rete o del server', 'error');
            window.wallPackingApp.hideLoading();
        }
    });
    
    // Add smooth scroll behavior for better UX
    document.documentElement.style.scrollBehavior = 'smooth';
    
    // Add loading states for external resources
    const images = document.querySelectorAll('img');
    images.forEach(img => {
        img.addEventListener('load', () => {
            img.style.opacity = '1';
        });
        img.addEventListener('error', () => {
            console.warn('Image failed to load:', img.src);
        });
    });
    
    console.log('✅ Parete TAKTAK® App initialized successfully');
    console.log('🎨 Professional design mode enabled');
    console.log('📱 Responsive layout activated');
    console.log('⌨️ Keyboard shortcuts: Ctrl+1 (App), Ctrl+2 (Libreria), Ctrl+3 (Impostazioni)');
    
    // Initialize color theme system
    initializeColorTheme();
    
    // Initialize active blocks display
    updateActiveBlocksDisplay();
});

// ===== ACTIVE BLOCKS INTEGRATION =====

// Update the active blocks display in configuration section
function updateActiveBlocksDisplay() {
    const currentDimensions = getCurrentBlockDimensions();
    
    // Update dimension displays
    document.getElementById('activeBlock1Dims').textContent = 
        `${currentDimensions.block1.width}×${currentDimensions.block1.height} mm`;
    document.getElementById('activeBlock2Dims').textContent = 
        `${currentDimensions.block2.width}×${currentDimensions.block2.height} mm`;
    document.getElementById('activeBlock3Dims').textContent = 
        `${currentDimensions.block3.width}×${currentDimensions.block3.height} mm`;
    
    // Update mini preview proportions
    updateMiniPreviews(currentDimensions);
    
    console.log('🔄 Active blocks display updated');
}

function updateMiniPreviews(dimensions) {
    const blockTypes = ['block1', 'block2', 'block3'];
    
    blockTypes.forEach((blockType, index) => {
        const preview = document.querySelector(`.block-type${index + 1}`);
        if (preview) {
            const dims = dimensions[blockType];
            const maxDim = Math.max(dims.width, dims.height, dims.depth);
            
            // Scale to fit in mini preview (40x30px max)
            const scale = Math.min(40, maxDim / 5);
            const displayWidth = (dims.width / maxDim) * scale;
            const displayHeight = (dims.height / maxDim) * scale;
            
            preview.style.width = Math.max(20, displayWidth) + 'px';
            preview.style.height = Math.max(15, displayHeight) + 'px';
        }
    });
}

// Open global settings (switch to library section - now containing global settings)
function openBlockLibrary() {
    console.log('⚙️ Opening global settings');
    
    // Check if a file is loaded - if so, prevent access to global settings
    if (window.wallPackingApp && window.wallPackingApp.currentFile) {
        window.wallPackingApp.showToast(
            'Non puoi modificare le impostazioni globali dopo aver caricato un file. Inizia un nuovo progetto per modificare le configurazioni.',
            'warning',
            5000
        );
        return;
    }
    
    // Switch to global settings section (library)
    if (window.wallPackingApp) {
        window.wallPackingApp.showMainSection('library');
        
        // Show toast to guide user
        setTimeout(() => {
            window.wallPackingApp.showToast('Clicca su "Dimensioni Blocchi Standard" per modificare', 'info');
        }, 500);
    }
}

// Listen for block dimension changes to update active display
function onBlockDimensionsChanged() {
    updateActiveBlocksDisplay();
}

// ===== BLOCK DIMENSIONS SYSTEM =====

// Block dimension presets
const blockPresets = {
    standard: {
        block1: { width: 1239, height: 495, depth: 100 },  // Blocco A - Grande
        block2: { width: 826, height: 495, depth: 100 },   // Blocco B - Medio  
        block3: { width: 413, height: 495, depth: 100 }    // Blocco C - Piccolo
    },
    metric: {
        block1: { width: 1200, height: 500, depth: 120 },  // Dimensioni metriche arrotondate
        block2: { width: 800, height: 500, depth: 120 },
        block3: { width: 400, height: 500, depth: 120 }
    },
    compact: {
        block1: { width: 1000, height: 400, depth: 80 },   // Versione compatta
        block2: { width: 650, height: 400, depth: 80 },
        block3: { width: 300, height: 400, depth: 80 }
    }
};

// Close all settings panels
function closeAllSettingsPanels() {
    // Close Block Dimensions panel
    const blockPanel = document.getElementById('blockDimensionsPanel');
    const blockIcon = document.getElementById('blockDimensionsExpandIcon');
    if (blockPanel && blockPanel.style.display !== 'none') {
        restoreSavedDimensions(); // Restore saved values when closing
        blockPanel.style.display = 'none';
        if (blockIcon) blockIcon.classList.remove('expanded');
    }
    
    // Close Color Theme panel
    const colorPanel = document.getElementById('colorSettingsPanel');
    const colorIcon = document.getElementById('colorThemeExpandIcon');
    if (colorPanel && colorPanel.style.display !== 'none') {
        colorPanel.style.display = 'none';
        if (colorIcon) colorIcon.classList.remove('expanded');
    }
    
    // Close Custom Materials panel
    const materialsPanel = document.getElementById('customMaterialsPanel');
    const materialsIcon = document.getElementById('customMaterialsExpandIcon');
    if (materialsPanel && materialsPanel.style.display !== 'none') {
        materialsPanel.style.display = 'none';
        if (materialsIcon) materialsIcon.classList.remove('expanded');
    }
    
    // Close Moraletti panel
    const moralettiPanel = document.getElementById('moralettiPanel');
    const moralettiIcon = document.getElementById('moralettiExpandIcon');
    if (moralettiPanel && moralettiPanel.style.display !== 'none') {
        moralettiPanel.style.display = 'none';
        if (moralettiIcon) moralettiIcon.classList.remove('expanded');
        
        // Also close moraletti visual section
        const visualSection = document.getElementById('moralettiVisualSection');
        if (visualSection) {
            visualSection.style.display = 'none';
        }
    }
}

// Toggle block dimensions panel
function toggleBlockDimensionsPanel() {
    const panel = document.getElementById('blockDimensionsPanel');
    const icon = document.getElementById('blockDimensionsExpandIcon');
    
    if (!panel || !icon) return;
    
    const isVisible = panel.style.display !== 'none';
    
    if (isVisible) {
        // Close panel - restore saved values
        restoreSavedDimensions();
        panel.style.display = 'none';
        icon.classList.remove('expanded');
        console.log('📏 Block dimensions panel closed - restored saved values');
    } else {
        // Close all other panels first
        closeAllSettingsPanels();
        
        // Open panel
        panel.style.display = 'block';
        icon.classList.add('expanded');
        
        // Initialize panel if not already done
        if (!window.blockDimensionsInitialized) {
            setTimeout(() => {
                initializeBlockDimensions();
                window.blockDimensionsInitialized = true;
            }, 100);
        } else {
            // Reload saved values when reopening
            restoreSavedDimensions();
        }
        
        console.log('📏 Block dimensions panel opened');
    }
}

// Restore saved dimensions to input fields
function restoreSavedDimensions() {
    const savedDimensions = localStorage.getItem('blockDimensions');
    let dimensions;
    
    if (savedDimensions) {
        try {
            dimensions = JSON.parse(savedDimensions);
        } catch (e) {
            dimensions = blockPresets.standard;
        }
    } else {
        dimensions = blockPresets.standard;
    }
    
    // Update input fields with saved values
    const blockTypes = ['block1', 'block2', 'block3'];
    const dimensionTypes = ['Width', 'Height', 'Depth'];
    
    blockTypes.forEach(blockType => {
        dimensionTypes.forEach(dimType => {
            const inputId = blockType + dimType;
            const input = document.getElementById(inputId);
            
            if (input) {
                const value = dimensions[blockType][dimType.toLowerCase()] || 100;
                input.value = value;
            }
        });
    });
    
    // Update previews and comparison with saved values
    updateBlockPreviews();
    updateBlockComparison();
    onBlockDimensionsChanged();
}

function initializeBlockDimensions() {
    console.log('📏 Initializing Block Dimensions System');
    
    // Load saved dimensions from localStorage, fallback to system defaults
    const savedDimensions = localStorage.getItem('blockDimensions');
    let currentDimensions;
    
    if (savedDimensions) {
        try {
            currentDimensions = JSON.parse(savedDimensions);
            console.log('📦 Using saved custom block dimensions');
        } catch (e) {
            console.warn('⚠️ Error parsing saved dimensions, using system defaults');
            currentDimensions = blockPresets.standard;
        }
    } else {
        // Use system defaults (matching utils/config.py)
        currentDimensions = blockPresets.standard;
        console.log('📦 Using system default block dimensions (A: 1239×495, B: 826×495, C: 413×495)');
    }
    
    // Setup dimension inputs
    setupDimensionInputs(currentDimensions);
    
    // Update previews and comparison
    updateBlockPreviews();
    updateBlockComparison();
    
    console.log('✅ Block Dimensions System initialized');
}

function setupDimensionInputs(dimensions) {
    const blockTypes = ['block1', 'block2', 'block3'];
    const dimensionTypes = ['Width', 'Height', 'Depth'];
    
    blockTypes.forEach(blockType => {
        dimensionTypes.forEach(dimType => {
            const inputId = blockType + dimType;
            const input = document.getElementById(inputId);
            
            if (input) {
                // Set initial value
                const value = dimensions[blockType][dimType.toLowerCase()] || 100;
                input.value = value;
                
                // Prevent propagation
                input.addEventListener('click', (e) => e.stopPropagation());
                input.addEventListener('focus', (e) => e.stopPropagation());
                
                // Update on change
                input.addEventListener('input', (e) => {
                    e.stopPropagation();
                    updateBlockPreviews();
                    updateBlockComparison();
                    
                    // Update active blocks display in real-time
                    onBlockDimensionsChanged();
                });
            }
        });
    });
    
    // Prevent propagation on the entire panel
    const panel = document.getElementById('blockDimensionsPanel');
    if (panel) {
        panel.addEventListener('click', (e) => e.stopPropagation());
    }
}

function updateBlockPreviews() {
    const blockTypes = ['block1', 'block2', 'block3'];
    
    blockTypes.forEach(blockType => {
        const width = parseFloat(document.getElementById(blockType + 'Width')?.value) || 100;
        const height = parseFloat(document.getElementById(blockType + 'Height')?.value) || 100;
        const depth = parseFloat(document.getElementById(blockType + 'Depth')?.value) || 50;
        
        // Calculate volume in liters
        const volume = (width * height * depth) / 1000000; // mm³ to L
        
        // Estimate weight (assuming concrete density ~2.4 kg/L)
        const weight = volume * 2.4;
        
        // Update volume and weight displays
        const volumeElement = document.getElementById(blockType + 'Volume');
        const weightElement = document.getElementById(blockType + 'Weight');
        
        if (volumeElement) {
            volumeElement.textContent = `Volume: ${volume.toFixed(3)} L`;
        }
        
        if (weightElement) {
            weightElement.textContent = `Peso: ~${weight.toFixed(1)} kg`;
        }
        
        // Update 3D preview size (proportional)
        const previewElement = document.getElementById('preview' + blockType.charAt(0).toUpperCase() + blockType.slice(1));
        if (previewElement) {
            const maxDim = Math.max(width, height, depth);
            
            // Prevent division by zero
            if (maxDim > 0) {
                const scale = Math.min(80, maxDim / 3); // Scale to fit in 80px max
                
                const displayWidth = (width / maxDim) * scale;
                const displayHeight = (height / maxDim) * scale;
                
                previewElement.style.width = displayWidth + 'px';
                previewElement.style.height = displayHeight + 'px';
            }
        }
    });
}

function updateBlockComparison() {
    const block1Volume = calculateBlockVolume('block1');
    const block2Volume = calculateBlockVolume('block2');
    const block3Volume = calculateBlockVolume('block3');
    
    const maxVolume = Math.max(block1Volume, block2Volume, block3Volume);
    
    // Prevent division by zero
    if (maxVolume === 0) {
        return;
    }
    
    // Update comparison bars
    updateComparisonBar('comparisonBar1', 'comparisonRatio1', block1Volume, maxVolume);
    updateComparisonBar('comparisonBar2', 'comparisonRatio2', block2Volume, maxVolume);
    updateComparisonBar('comparisonBar3', 'comparisonRatio3', block3Volume, maxVolume);
}

function calculateBlockVolume(blockType) {
    const width = parseFloat(document.getElementById(blockType + 'Width')?.value) || 100;
    const height = parseFloat(document.getElementById(blockType + 'Height')?.value) || 100;
    const depth = parseFloat(document.getElementById(blockType + 'Depth')?.value) || 50;
    
    return width * height * depth;
}

function updateComparisonBar(barId, ratioId, volume, maxVolume) {
    const bar = document.getElementById(barId);
    const ratio = document.getElementById(ratioId);
    
    if (bar && ratio && maxVolume > 0) {
        const percentage = (volume / maxVolume) * 100;
        bar.style.width = percentage + '%';
        ratio.textContent = Math.round(percentage) + '%';
    }
}

function applyBlockPreset(presetName) {
    console.log(`📏 Applying block preset: ${presetName}`);
    
    const preset = blockPresets[presetName];
    if (!preset) {
        console.error(`❌ Block preset '${presetName}' not found`);
        return;
    }
    
    // Apply all values
    Object.entries(preset).forEach(([blockType, dimensions]) => {
        Object.entries(dimensions).forEach(([dimType, value]) => {
            const inputId = blockType + dimType.charAt(0).toUpperCase() + dimType.slice(1);
            const input = document.getElementById(inputId);
            if (input) {
                input.value = value;
            }
        });
    });
    
    // Update previews and comparison
    updateBlockPreviews();
    updateBlockComparison();
    
    // Update active blocks display
    onBlockDimensionsChanged();
    
    // Show confirmation
    if (window.wallPackingApp) {
        window.wallPackingApp.showToast(`Preset blocchi "${presetName}" applicato`, 'success');
    }
}

function saveBlockDimensions() {
    console.log('💾 Saving block dimensions');
    
    const dimensions = {
        block1: {
            width: parseFloat(document.getElementById('block1Width')?.value) || 100,
            height: parseFloat(document.getElementById('block1Height')?.value) || 100,
            depth: parseFloat(document.getElementById('block1Depth')?.value) || 50
        },
        block2: {
            width: parseFloat(document.getElementById('block2Width')?.value) || 100,
            height: parseFloat(document.getElementById('block2Height')?.value) || 100,
            depth: parseFloat(document.getElementById('block2Depth')?.value) || 50
        },
        block3: {
            width: parseFloat(document.getElementById('block3Width')?.value) || 100,
            height: parseFloat(document.getElementById('block3Height')?.value) || 100,
            depth: parseFloat(document.getElementById('block3Depth')?.value) || 50
        }
    };
    
    // Save to localStorage
    localStorage.setItem('blockDimensions', JSON.stringify(dimensions));
    
    // Apply to current session
    window.currentBlockDimensions = dimensions;
    
    // Update active blocks display in configuration
    updateActiveBlocksDisplay();
    
    // Show confirmation
    if (window.wallPackingApp) {
        window.wallPackingApp.showToast('Dimensioni blocchi salvate e applicate!', 'success');
    }
    
    // Enable moraletti configuration now that blocks are confirmed
    enableMoralettiConfiguration();
    
    console.log('✅ Block dimensions saved:', dimensions);
    
    // Se stiamo caricando un profilo, apri automaticamente il pannello moraletti
    if (window.isLoadingProfile) {
        console.log('🔄 Caricamento profilo in corso - apertura automatica pannello moraletti');
        
        setTimeout(() => {
            // Chiudi il pannello blocchi
            const blockPanel = document.getElementById('blockDimensionsPanel');
            const blockIcon = document.getElementById('blockDimensionsExpandIcon');
            if (blockPanel && blockIcon) {
                blockPanel.style.display = 'none';
                blockIcon.classList.remove('expanded');
            }
            
            // Apri il pannello moraletti
            const moralettiPanel = document.getElementById('moralettiPanel');
            const moralettiIcon = document.getElementById('moralettiExpandIcon');
            if (moralettiPanel && moralettiIcon) {
                moralettiPanel.style.display = 'block';
                moralettiIcon.classList.add('expanded');
                
                // Inizializza se necessario
                if (!window.moralettiInitialized && typeof initializeMoralettiConfiguration === 'function') {
                    initializeMoralettiConfiguration();
                    window.moralettiInitialized = true;
                }
                
                console.log('✅ Pannello moraletti aperto automaticamente');
                
                // Aspetta che il pannello sia completamente aperto, poi riapplica i dati moraletti
                setTimeout(() => {
                    if (window.pendingMoralettiConfig) {
                        console.log('🔄 Riapplicazione dati moraletti nel pannello aperto');
                        
                        // Riapplica la configurazione moraletti che era stata salvata
                        if (typeof applyMoralettiConfig === 'function') {
                            applyMoralettiConfig(window.pendingMoralettiConfig);
                        }
                        
                        // Pulisci la configurazione pendente
                        delete window.pendingMoralettiConfig;
                    }
                    
                    // Scroll verso il pannello moraletti
                    const moralettiCard = document.querySelector('.moraletti-card');
                    if (moralettiCard) {
                        moralettiCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    }
                }, 300);
            }
        }, 500);
    }
}

// Export current block dimensions for use in processing
function getCurrentBlockDimensions() {
    if (window.currentBlockDimensions) {
        return window.currentBlockDimensions;
    }
    
    // Check localStorage for saved dimensions
    const saved = localStorage.getItem('blockDimensions');
    if (saved) {
        try {
            return JSON.parse(saved);
        } catch (e) {
            console.warn('Error parsing saved block dimensions, using defaults');
        }
    }
    
    // Fallback to system defaults (from utils/config.py: BLOCK_WIDTHS + BLOCK_HEIGHT)
    return {
        block1: {
            width: parseFloat(document.getElementById('block1Width')?.value) || 1239,  // A - Grande
            height: parseFloat(document.getElementById('block1Height')?.value) || 495, // BLOCK_HEIGHT
            depth: parseFloat(document.getElementById('block1Depth')?.value) || 100    // Standard depth
        },
        block2: {
            width: parseFloat(document.getElementById('block2Width')?.value) || 826,   // B - Medio
            height: parseFloat(document.getElementById('block2Height')?.value) || 495, // BLOCK_HEIGHT
            depth: parseFloat(document.getElementById('block2Depth')?.value) || 100    // Standard depth
        },
        block3: {
            width: parseFloat(document.getElementById('block3Width')?.value) || 413,   // C - Piccolo
            height: parseFloat(document.getElementById('block3Height')?.value) || 495, // BLOCK_HEIGHT
            depth: parseFloat(document.getElementById('block3Depth')?.value) || 100    // Standard depth
        }
    };
}

// ===== COLOR THEME SYSTEM =====

// Toggle color theme panel
function toggleColorThemePanel() {
    const panel = document.getElementById('colorSettingsPanel');
    const icon = document.getElementById('colorThemeExpandIcon');
    
    if (!panel || !icon) return;
    
    const isVisible = panel.style.display !== 'none';
    
    if (isVisible) {
        // Close panel
        panel.style.display = 'none';
        icon.classList.remove('expanded');
        console.log('🎨 Color theme panel closed');
    } else {
        // Close all other panels first
        closeAllSettingsPanels();
        
        // Open panel
        panel.style.display = 'block';
        icon.classList.add('expanded');
        
        // Initialize panel if not already done
        if (!window.colorThemeInitialized) {
            setTimeout(() => {
                initializeColorTheme();
                window.colorThemeInitialized = true;
            }, 100);
        }
        
        console.log('🎨 Color theme panel opened');
    }
}

// Color presets
const colorPresets = {
    default: {
        standardBlockColor: '#E5E7EB',
        standardBlockBorder: '#374151',
        doorWindowColor: '#FEE2E2',
        doorWindowBorder: '#DC2626',
        wallOutlineColor: '#1E40AF',
        wallLineWidth: 2,
        customPieceColor: '#F3E8FF',
        customPieceBorder: '#7C3AED'
    },
    highContrast: {
        standardBlockColor: '#FFFFFF',
        standardBlockBorder: '#000000',
        doorWindowColor: '#FFFF00',
        doorWindowBorder: '#FF0000',
        wallOutlineColor: '#0000FF',
        wallLineWidth: 3,
        customPieceColor: '#00FF00',
        customPieceBorder: '#800080'
    },
    colorful: {
        standardBlockColor: '#DBEAFE',
        standardBlockBorder: '#1E40AF',
        doorWindowColor: '#FED7D7',
        doorWindowBorder: '#E53E3E',
        wallOutlineColor: '#059669',
        wallLineWidth: 2,
        customPieceColor: '#E9D8FD',
        customPieceBorder: '#805AD5'
    }
};

function initializeColorTheme() {
    console.log('🎨 Initializing Color Theme System');
    
    // Load saved theme or use default
    const savedTheme = localStorage.getItem('wallTheme');
    const currentTheme = savedTheme ? JSON.parse(savedTheme) : colorPresets.default;
    
    // Setup color inputs
    setupColorInputs(currentTheme);
    
    // Setup range slider
    setupRangeSlider();
    
    // Update preview
    updateColorPreview();
    
    console.log('✅ Color Theme System initialized');
}

function setupColorInputs(theme) {
    const colorInputs = [
        'standardBlockColor', 'standardBlockBorder',
        'doorWindowColor', 'doorWindowBorder',
        'wallOutlineColor', 'customPieceColor', 'customPieceBorder'
    ];
    
    colorInputs.forEach(inputId => {
        const colorPicker = document.getElementById(inputId);
        const colorText = document.getElementById(inputId + 'Text');
        
        if (colorPicker && colorText) {
            // Set initial values
            const value = theme[inputId] || colorPresets.default[inputId];
            colorPicker.value = value;
            colorText.value = value;
            
            // Prevent propagation on color controls
            colorPicker.addEventListener('click', (e) => e.stopPropagation());
            colorText.addEventListener('click', (e) => e.stopPropagation());
            
            // Color picker change
            colorPicker.addEventListener('input', (e) => {
                e.stopPropagation();
                const color = e.target.value;
                colorText.value = color;
                updateColorPreview();
            });
            
            // Text input change
            colorText.addEventListener('input', (e) => {
                e.stopPropagation();
                const color = e.target.value;
                if (isValidHexColor(color)) {
                    colorPicker.value = color;
                    updateColorPreview();
                }
            });
        }
    });
    
    // Setup line width
    const wallLineWidth = document.getElementById('wallLineWidth');
    if (wallLineWidth) {
        wallLineWidth.value = theme.wallLineWidth || 2;
        wallLineWidth.addEventListener('click', (e) => e.stopPropagation());
    }
    
    // Prevent propagation on the entire panel
    const panel = document.getElementById('colorSettingsPanel');
    if (panel) {
        panel.addEventListener('click', (e) => e.stopPropagation());
    }
}

function setupRangeSlider() {
    const slider = document.getElementById('wallLineWidth');
    const valueDisplay = document.querySelector('.range-value');
    
    if (slider && valueDisplay) {
        // Prevent propagation
        slider.addEventListener('click', (e) => e.stopPropagation());
        slider.addEventListener('input', (e) => e.stopPropagation());
        
        const updateValue = () => {
            valueDisplay.textContent = slider.value + 'px';
            updateColorPreview();
        };
        
        slider.addEventListener('input', updateValue);
        updateValue(); // Initial update
    }
}

function updateColorPreview() {
    const elements = {
        'previewStandardBlock': {
            bg: 'standardBlockColor',
            border: 'standardBlockBorder'
        },
        'previewDoorWindow': {
            bg: 'doorWindowColor',
            border: 'doorWindowBorder'
        },
        'previewCustomPiece': {
            bg: 'customPieceColor',
            border: 'customPieceBorder'
        },
        'previewWallOutline': {
            border: 'wallOutlineColor'
        }
    };
    
    Object.entries(elements).forEach(([elementId, config]) => {
        const element = document.getElementById(elementId);
        if (element) {
            if (config.bg) {
                const bgColor = document.getElementById(config.bg)?.value;
                if (bgColor) element.style.backgroundColor = bgColor;
            }
            
            if (config.border) {
                const borderColor = document.getElementById(config.border)?.value;
                if (borderColor) element.style.borderColor = borderColor;
                
                // Special handling for wall outline
                if (elementId === 'previewWallOutline') {
                    const lineWidth = document.getElementById('wallLineWidth')?.value || 2;
                    element.style.borderWidth = lineWidth + 'px';
                }
            }
        }
    });
}

function applyPreset(presetName) {
    console.log(`🎨 Applying preset: ${presetName}`);
    
    const preset = colorPresets[presetName];
    if (!preset) {
        console.error(`❌ Preset '${presetName}' not found`);
        return;
    }
    
    // Apply all values
    Object.entries(preset).forEach(([key, value]) => {
        const colorPicker = document.getElementById(key);
        const colorText = document.getElementById(key + 'Text');
        
        if (colorPicker && colorText) {
            colorPicker.value = value;
            colorText.value = value;
        } else if (key === 'wallLineWidth') {
            const slider = document.getElementById('wallLineWidth');
            if (slider) slider.value = value;
        }
    });
    
    // Update range slider display
    setupRangeSlider();
    
    // Update preview
    updateColorPreview();
    
    // Show confirmation
    if (window.wallPackingApp) {
        window.wallPackingApp.showToast(`Preset "${presetName}" applicato`, 'success');
    }
}

function saveColorTheme() {
    console.log('💾 Saving color theme');
    
    const theme = {
        standardBlockColor: document.getElementById('standardBlockColor')?.value,
        standardBlockBorder: document.getElementById('standardBlockBorder')?.value,
        doorWindowColor: document.getElementById('doorWindowColor')?.value,
        doorWindowBorder: document.getElementById('doorWindowBorder')?.value,
        wallOutlineColor: document.getElementById('wallOutlineColor')?.value,
        wallLineWidth: parseInt(document.getElementById('wallLineWidth')?.value) || 2,
        customPieceColor: document.getElementById('customPieceColor')?.value,
        customPieceBorder: document.getElementById('customPieceBorder')?.value
    };
    
    // Save to localStorage
    localStorage.setItem('wallTheme', JSON.stringify(theme));
    
    // Apply to current session
    window.currentColorTheme = theme;
    
    // Show confirmation
    if (window.wallPackingApp) {
        window.wallPackingApp.showToast('Tema salvato con successo!', 'success');
    }
    
    console.log('✅ Color theme saved:', theme);
}

function isValidHexColor(hex) {
    return /^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$/.test(hex);
}

// Export current theme for use in processing
function getCurrentColorTheme() {
    if (window.currentColorTheme) {
        return window.currentColorTheme;
    }
    
    // Fallback to reading from inputs
    return {
        standardBlockColor: document.getElementById('standardBlockColor')?.value || '#E5E7EB',
        standardBlockBorder: document.getElementById('standardBlockBorder')?.value || '#374151',
        doorWindowColor: document.getElementById('doorWindowColor')?.value || '#FEE2E2',
        doorWindowBorder: document.getElementById('doorWindowBorder')?.value || '#DC2626',
        wallOutlineColor: document.getElementById('wallOutlineColor')?.value || '#1E40AF',
        wallLineWidth: parseInt(document.getElementById('wallLineWidth')?.value) || 2,
        customPieceColor: document.getElementById('customPieceColor')?.value || '#F3E8FF',
        customPieceBorder: document.getElementById('customPieceBorder')?.value || '#7C3AED'
    };
}

// ==== CUSTOM MATERIALS CONFIGURATION ====

function toggleCustomMaterialsPanel() {
    const panel = document.getElementById('customMaterialsPanel');
    const icon = document.getElementById('customMaterialsExpandIcon');
    
    if (!panel || !icon) return;
    
    const isVisible = panel.style.display !== 'none';
    
    if (isVisible) {
        // Close panel
        panel.style.display = 'none';
        icon.classList.remove('expanded');
        console.log('📦 Custom materials panel closed');
    } else {
        // Close all other panels first
        closeAllSettingsPanels();
        
        // Open panel
        panel.style.display = 'block';
        icon.classList.add('expanded');
        
        // Load materials
        loadCustomMaterials();
        
        console.log('📦 Custom materials panel opened');
    }
}

function addCustomMaterial() {
    const nameInput = document.getElementById('newMaterialName');
    const thicknessInput = document.getElementById('newMaterialThickness');
    
    const name = nameInput.value.trim();
    const thickness = parseFloat(thicknessInput.value);
    
    // Validation
    if (!name) {
        if (window.wallPackingApp) {
            window.wallPackingApp.showToast('❌ Inserisci il nome del materiale', 'error');
        }
        return;
    }
    
    if (!thickness || thickness < 1 || thickness > 100) {
        if (window.wallPackingApp) {
            window.wallPackingApp.showToast('❌ Inserisci uno spessore valido (1-100mm)', 'error');
        }
        return;
    }
    
    // Get existing materials
    const materials = getCustomMaterials();
    
    // Check for duplicate names
    if (materials.some(m => m.name.toLowerCase() === name.toLowerCase())) {
        if (window.wallPackingApp) {
            window.wallPackingApp.showToast('❌ Esiste già un materiale con questo nome', 'error');
        }
        return;
    }
    
    // Add new material
    const newMaterial = {
        id: Date.now().toString(),
        name: name,
        thickness: thickness,
        createdAt: new Date().toISOString()
    };
    
    materials.push(newMaterial);
    saveCustomMaterials(materials);
    
    // Clear inputs
    nameInput.value = '';
    thicknessInput.value = '';
    
    // Reload list
    loadCustomMaterials();
    
    // Update material selector in Step 3
    updateMaterialSelector();
    
    if (window.wallPackingApp) {
        window.wallPackingApp.showToast(`✅ Materiale "${name}" aggiunto con successo!`, 'success');
    }
    
    console.log('✅ Custom material added:', newMaterial);
}

function deleteCustomMaterial(materialId) {
    console.log('🗑️ deleteCustomMaterial called with ID:', materialId);
    
    const materials = getCustomMaterials();
    const materialToDelete = materials.find(m => m.id === materialId);
    
    if (!materialToDelete) {
        console.error('❌ Material not found:', materialId);
        return;
    }
    
    console.log('✅ Material found:', materialToDelete);
    
    // Show modal with material name
    const modal = document.getElementById('deleteMaterialModal');
    const materialNameSpan = document.getElementById('deleteMaterialName');
    const confirmBtn = document.getElementById('confirmDeleteMaterialBtn');
    
    console.log('Modal elements:', { modal, materialNameSpan, confirmBtn });
    
    if (!modal || !materialNameSpan || !confirmBtn) {
        console.error('❌ Delete modal elements not found!');
        return;
    }
    
    materialNameSpan.textContent = `${materialToDelete.name} (${materialToDelete.thickness}mm)`;
    modal.style.display = 'flex';
    console.log('✅ Modal should be visible now');
    
    // Close modal when clicking outside
    modal.onclick = function(event) {
        if (event.target === modal) {
            closeMaterialDeleteModal();
        }
    };
    
    // Remove any existing event listeners
    const newConfirmBtn = confirmBtn.cloneNode(true);
    confirmBtn.parentNode.replaceChild(newConfirmBtn, confirmBtn);
    
    // Add new event listener for confirmation
    document.getElementById('confirmDeleteMaterialBtn').onclick = function() {
        const updatedMaterials = materials.filter(m => m.id !== materialId);
        saveCustomMaterials(updatedMaterials);
        
        // Close modal
        closeMaterialDeleteModal();
        
        // Reload list
        loadCustomMaterials();
        
        // Update material selector
        updateMaterialSelector();
        
        if (window.wallPackingApp) {
            window.wallPackingApp.showToast(`🗑️ Materiale "${materialToDelete.name}" eliminato`, 'info');
        }
        
        console.log('✅ Custom material deleted:', materialId);
    };
}

function closeMaterialDeleteModal() {
    const modal = document.getElementById('deleteMaterialModal');
    if (modal) {
        modal.style.display = 'none';
        console.log('✅ Modal closed');
    }
}

function loadCustomMaterials() {
    const materials = getCustomMaterials();
    const grid = document.getElementById('customMaterialsList');
    const emptyState = document.getElementById('emptyMaterialsState');
    
    if (!grid) return;
    
    // Clear grid
    grid.innerHTML = '';
    
    if (materials.length === 0) {
        // Show empty state
        grid.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-inbox"></i>
                <p>Nessun materiale personalizzato ancora creato</p>
                <span>Aggiungi il tuo primo materiale usando il form sopra</span>
            </div>
        `;
        return;
    }
    
    // Create material cards
    materials.forEach(material => {
        const card = document.createElement('div');
        card.className = 'material-card';
        card.innerHTML = `
            <div class="material-card-header">
                <h5 class="material-card-title">${escapeHtml(material.name)}</h5>
                <div class="material-card-actions">
                    <button class="material-action-btn delete-btn" onclick="deleteCustomMaterial('${material.id}')" title="Elimina">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
            <div class="material-card-info">
                <i class="fas fa-ruler"></i>
                <span>${material.thickness} mm</span>
            </div>
        `;
        grid.appendChild(card);
    });
}

function getCustomMaterials() {
    const saved = localStorage.getItem('customMaterials');
    if (!saved) return [];
    
    try {
        return JSON.parse(saved);
    } catch (e) {
        console.error('Error parsing custom materials:', e);
        return [];
    }
}

function saveCustomMaterials(materials) {
    localStorage.setItem('customMaterials', JSON.stringify(materials));
}

function updateMaterialSelector() {
    const selector = document.getElementById('materialType');
    if (!selector) return;
    
    // Get default materials (first 4 options)
    const defaultOptions = Array.from(selector.options).slice(0, 4);
    
    // Clear selector
    selector.innerHTML = '';
    
    // Re-add default options
    defaultOptions.forEach(opt => selector.appendChild(opt));
    
    // Add custom materials
    const materials = getCustomMaterials();
    materials.forEach(material => {
        const option = document.createElement('option');
        option.value = `custom_${material.id}`;
        option.textContent = `${material.name} (${material.thickness}mm)`;
        option.dataset.thickness = material.thickness;
        selector.appendChild(option);
    });
    
    console.log('✅ Material selector updated with', materials.length, 'custom materials');
}

function setupMaterialChangeHandler() {
    const selector = document.getElementById('materialType');
    const thicknessInput = document.getElementById('materialThickness');
    
    if (!selector || !thicknessInput) return;
    
    selector.addEventListener('change', function() {
        const selectedOption = this.options[this.selectedIndex];
        
        // Default thicknesses for standard materials
        const defaultThicknesses = {
            'melamine': 18,
            'mdf': 19,
            'chipboard': 18,
            'plywood': 15
        };
        
        if (this.value.startsWith('custom_')) {
            // Custom material - get thickness from option
            thicknessInput.value = selectedOption.dataset.thickness || 18;
        } else {
            // Standard material - use default thickness
            thicknessInput.value = defaultThicknesses[this.value] || 18;
        }
    });
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Get block dimensions for backend processing
function getBlockDimensionsForBackend() {
    const dimensions = getCurrentBlockDimensions();
    
    // Convert to format expected by backend (matching BLOCK_WIDTHS, BLOCK_HEIGHT)
    return {
        block_widths: [
            dimensions.block1.width,
            dimensions.block2.width, 
            dimensions.block3.width
        ],
        block_height: dimensions.block1.height, // Assume uniform height
        block_depth: dimensions.block1.depth    // Standard depth for 3D calculations
    };
}

// Reset to system defaults
function resetToSystemDefaults() {
    console.log('🔄 Resetting to system defaults');
    
    // Apply system defaults (only updates the input fields, does not save)
    applyBlockPreset('standard');
    
    // User must click "Salva Configurazione" to confirm the changes
}

// ===== PAST PROJECTS MANAGEMENT =====

let pastProjectsData = [];

// Toggle Past Projects Panel
function togglePastProjectsPanel() {
    const panel = document.getElementById('pastProjectsPanel');
    const icon = document.getElementById('pastProjectsExpandIcon');
    
    if (!panel || !icon) {
        console.error('Past projects panel elements not found');
        return;
    }
    
    if (panel.style.display === 'none' || panel.style.display === '') {
        panel.style.display = 'block';
        icon.style.transform = 'rotate(180deg)';
        
        // Load projects when opening
        loadPastProjects();
    } else {
        panel.style.display = 'none';
        icon.style.transform = 'rotate(0deg)';
    }
}

// Load Past Projects from API
async function loadPastProjects() {
    const listContainer = document.getElementById('pastProjectsList');
    const emptyState = document.getElementById('emptyProjectsState');
    const countBadge = document.getElementById('projectsCountBadge');
    
    if (!listContainer || !emptyState || !countBadge) {
        console.error('Past projects elements not found in DOM');
        return;
    }
    
    try {
        // Show loading state
        listContainer.innerHTML = `
            <div class="loading-placeholder">
                <i class="fas fa-spinner fa-spin"></i>
                <span>Caricamento progetti...</span>
            </div>
        `;
        emptyState.style.display = 'none';
        
        // Check if user is authenticated
        const token = sessionStorage.getItem('access_token');
        if (!token) {
            console.log('No auth token found, showing empty state');
            showEmptyProjectsState(listContainer, emptyState, countBadge, 'Effettua il login per vedere i tuoi progetti');
            return;
        }
        
        const response = await fetch('/api/v1/saved-projects/list', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (!response.ok) {
            if (response.status === 401) {
                console.log('Authentication failed, showing login message');
                showEmptyProjectsState(listContainer, emptyState, countBadge, 'Sessione scaduta, effettua nuovamente il login');
                return;
            }
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        // Handle successful response
        if (data.success) {
            pastProjectsData = data.projects || [];
            
            // Update count badge
            if (pastProjectsData.length > 0) {
                countBadge.textContent = pastProjectsData.length;
                countBadge.style.display = 'inline-block';
            } else {
                countBadge.style.display = 'none';
            }
            
            renderPastProjects(pastProjectsData);
        } else {
            console.log('API returned success=false, showing empty state');
            showEmptyProjectsState(listContainer, emptyState, countBadge, 'Nessun progetto presente');
        }
        
    } catch (error) {
        console.error('Error loading past projects:', error);
        showEmptyProjectsState(listContainer, emptyState, countBadge, 'Errore nel caricamento progetti');
        
        if (window.wallPackingApp) {
            window.wallPackingApp.showToast('Errore nel caricamento progetti passati', 'error');
        }
    }
}

// Helper function to show empty state
function showEmptyProjectsState(listContainer, emptyState, countBadge, message = 'Nessun progetto presente') {
    listContainer.innerHTML = '';
    emptyState.style.display = 'block';
    countBadge.style.display = 'none';
    
    // Update empty state message if needed
    const emptyMessage = emptyState.querySelector('p');
    if (emptyMessage && message !== 'Nessun progetto presente') {
        emptyMessage.textContent = message;
    }
}

// Render Past Projects List
function renderPastProjects(projects) {
    const listContainer = document.getElementById('pastProjectsList');
    const emptyState = document.getElementById('emptyProjectsState');
    
    if (!listContainer || !emptyState) {
        console.error('Required DOM elements not found');
        return;
    }
    
    if (!projects || projects.length === 0) {
        console.log('No projects to display, showing empty state');
        listContainer.innerHTML = '';
        emptyState.style.display = 'block';
        return;
    }
    
    console.log(`Rendering ${projects.length} projects`);
    emptyState.style.display = 'none';
    
    try {
        const projectsHTML = projects.map(project => {
            // Safely parse dates
            let createdDate = 'Data non disponibile';
            let lastUsed = 'Mai utilizzato';
            
            try {
                if (project.created_at) {
                    createdDate = new Date(project.created_at).toLocaleDateString('it-IT');
                }
                if (project.last_used) {
                    lastUsed = new Date(project.last_used).toLocaleDateString('it-IT');
                }
            } catch (dateError) {
                console.warn('Error parsing dates for project:', project.id, dateError);
            }
            
            // Safely get project name
            const projectName = project.name || project.filename || `Progetto ${project.id}`;
            
            return `
                <div class="project-item" data-project-id="${project.id}">
                    <div class="project-info">
                        <div class="project-name">
                            <i class="fas fa-file-alt"></i>
                            ${projectName}
                        </div>
                        <div class="project-meta">
                            <span title="Data creazione">
                                <i class="fas fa-calendar-plus"></i>
                                ${createdDate}
                            </span>
                            <span title="Ultimo utilizzo">
                                <i class="fas fa-clock"></i>
                                ${lastUsed}
                            </span>
                            <span title="Sistema profilo">
                                <i class="fas fa-cogs"></i>
                                ${project.profile_name || 'Standard'}
                            </span>
                            <span title="Numero blocchi">
                                <i class="fas fa-cubes"></i>
                                ${project.total_blocks || 0} blocchi
                            </span>
                            ${project.wall_dimensions && project.wall_dimensions !== 'N/A' ? 
                                `<span title="Dimensioni parete"><i class="fas fa-expand-arrows-alt"></i> ${project.wall_dimensions}</span>` : ''}
                        </div>
                    </div>
                    <div class="project-actions">
                        <button class="download-file-btn" onclick="downloadProjectFile(${project.id}, event); return false;" title="Scarica file originale">
                            <i class="fas fa-file-download"></i><span> Scarica</span>
                        </button>
                        <button class="reuse-btn" onclick="reuseProject(${project.id}, event); return false;" title="Riusa questo progetto">
                            <i class="fas fa-redo"></i><span> Riusa</span>
                        </button>
                        <button class="delete-project-btn" onclick="deleteProject(${project.id}, event); return false;" title="Elimina progetto">
                            <i class="fas fa-trash"></i><span> Elimina</span>
                        </button>
                    </div>
                </div>
            `;
        }).join('');
        
        listContainer.innerHTML = projectsHTML;
        console.log('Projects rendered successfully');
        
    } catch (error) {
        console.error('Error rendering projects:', error);
        listContainer.innerHTML = `
            <div class="error-state" style="text-align: center; padding: 20px; color: var(--gray-500);">
                <i class="fas fa-exclamation-triangle" style="font-size: 24px; margin-bottom: 10px;"></i>
                <div>Errore nella visualizzazione dei progetti</div>
            </div>
        `;
    }
}

// Reuse Project - NEW LOGIC: Load and process automatically to go directly to results
async function reuseProject(projectId, event) {
    // Prevent event propagation to avoid closing the panel
    if (event) {
        event.stopPropagation();
        event.preventDefault();
    }
    
    console.log(`🔄 Riutilizzo progetto ID: ${projectId}`);
    
    try {
        // Show loading state
        if (window.wallPackingApp) {
            window.wallPackingApp.showToast('Ripristino progetto...', 'info');
            window.wallPackingApp.showLoading('Caricamento progetto salvato...', 'Ripristino file e rielaborazione automatica');
        }
        
        // Step 1: Get project data
        const response = await fetch(`/api/v1/saved-projects/${projectId}`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${sessionStorage.getItem('access_token')}`
            }
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        const project = data.project;
        
        console.log('📦 Progetto recuperato:', project.name);
        
        // Step 2: Restore all configurations first
        await restoreProjectConfigurations(project);
        
        // Step 3: Load file and process automatically to go directly to results
        console.log('🚀 Caricamento file e rielaborazione automatica...');
        await loadAndProcessProjectFile(projectId, project);
        
    } catch (error) {
        console.error('❌ Errore riutilizzo progetto:', error);
        if (window.wallPackingApp) {
            window.wallPackingApp.hideLoading();
            window.wallPackingApp.showToast('Errore nel caricamento progetto', 'error');
        }
    }
}

// Restore project configurations
async function restoreProjectConfigurations(project) {
    console.log('⚙️ Ripristino configurazioni...');
    
    // ===== NUOVO: Gestione Snapshot Sistema =====
    if (project.snapshot_info && project.snapshot_info.has_snapshot) {
        console.log('📸 Progetto con snapshot sistema rilevato!');
        const snapshotInfo = project.snapshot_info;
        
        // Mostra badge snapshot nell'UI
        const snapshotBadge = document.getElementById('snapshotBadge');
        const snapshotBadgeText = document.getElementById('snapshotBadgeText');
        
        if (snapshotBadge && snapshotBadgeText) {
            // Formatta la data
            const savedAt = new Date(snapshotInfo.saved_at);
            const formattedDate = savedAt.toLocaleDateString('it-IT', {
                day: '2-digit',
                month: '2-digit',
                year: 'numeric'
            });
            
            snapshotBadgeText.textContent = `Configurazione snapshot del ${formattedDate}`;
            snapshotBadge.style.display = 'flex';
            
            console.log(`✅ Badge snapshot mostrato: ${formattedDate}`);
            console.log(`📊 Profili salvati nello snapshot: ${snapshotInfo.profiles_count}`);
        }
        
        // Store snapshot info for use during processing
        if (window.wallPackingApp) {
            window.wallPackingApp.currentSnapshot = project.extended_config.system_snapshot;
            console.log('💾 Snapshot salvato in app instance per utilizzo futuro');
        }
        
    } else if (project.snapshot_info && !project.snapshot_info.has_snapshot) {
        console.warn('⚠️ Progetto LEGACY senza snapshot - userà configurazione corrente');
        
        // Mostra badge warning per progetto legacy
        const snapshotBadge = document.getElementById('snapshotBadge');
        const snapshotBadgeText = document.getElementById('snapshotBadgeText');
        
        if (snapshotBadge && snapshotBadgeText) {
            snapshotBadgeText.textContent = '⚠️ Progetto legacy - usa configurazione sistema corrente';
            snapshotBadge.classList.add('legacy');
            snapshotBadge.style.display = 'flex';
        }
    }
    
    // Restore block dimensions
    if (project.block_dimensions) {
        localStorage.setItem('blockDimensions', JSON.stringify(project.block_dimensions));
        window.currentBlockDimensions = project.block_dimensions;
        updateActiveBlocksDisplay();
        console.log('📏 Dimensioni blocchi ripristinate');
    }
    
    // Restore color theme  
    if (project.color_theme) {
        localStorage.setItem('wallTheme', JSON.stringify(project.color_theme));
        window.currentColorTheme = project.color_theme;
        console.log('🎨 Tema colori ripristinato');
    }
    
    // Restore packing configuration in UI
    if (project.packing_config) {
        const config = project.packing_config;
        
        // Project name
        const projectNameInput = document.getElementById('projectName');
        if (projectNameInput && config.project_name) {
            projectNameInput.value = config.project_name;
        }
        
        // Row offset
        if (config.row_offset) {
            const rowOffsetSlider = document.getElementById('rowOffset');
            const rowOffsetValue = document.getElementById('rowOffsetValue');
            if (rowOffsetSlider && rowOffsetValue) {
                rowOffsetSlider.value = config.row_offset;
                rowOffsetValue.textContent = `${config.row_offset} mm`;
                if (window.wallPackingApp && window.wallPackingApp.updatePresetButtons) {
                    window.wallPackingApp.updatePresetButtons(config.row_offset.toString());
                }
            }
        }
        
        // Block widths
        if (config.block_widths) {
            // Block widths are now managed globally, not through this removed field
        }
        
        console.log('⚙️ Configurazioni UI ripristinate');
    }
    
    // NEW: Restore extended configuration
    if (project.extended_config) {
        console.log('🔧 Ripristino extended_config:', project.extended_config);
        
        const extConfig = project.extended_config;
        
        // Store in app instance for later use
        if (window.wallPackingApp) {
            window.wallPackingApp.currentMaterialConfig = extConfig.material_config || {};
            window.wallPackingApp.currentGuideSpec = extConfig.guide_spec || {};
            window.wallPackingApp.currentWallPosition = extConfig.wall_position || {};
            window.wallPackingApp.currentCustomDimensions = extConfig.custom_dimensions || {};
            window.wallPackingApp.currentConstructionMethod = extConfig.construction_method || {};
            window.wallPackingApp.currentMorettiSettings = extConfig.moretti_settings || {};
            
            console.log('✅ Extended config ripristinato in app instance');
        }
        
        // Store in localStorage for persistence
        if (extConfig.material_config) {
            localStorage.setItem('material_config', JSON.stringify(extConfig.material_config));
        }
        if (extConfig.guide_spec) {
            localStorage.setItem('guide_spec', JSON.stringify(extConfig.guide_spec));
        }
        if (extConfig.wall_position) {
            localStorage.setItem('wall_position', JSON.stringify(extConfig.wall_position));
        }
        
        console.log('💾 Extended config salvato in localStorage');
    }
}

// Load file and automatically process to show results immediately
async function loadAndProcessProjectFile(projectId, project) {
    try {
        console.log('📂 Recupero file salvato...');
        
        // Get the saved file from the backend
        const fileResponse = await fetch(`/api/v1/saved-projects/${projectId}/file`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${sessionStorage.getItem('access_token')}`
            }
        });
        
        if (!fileResponse.ok) {
            throw new Error(`Errore nel recupero file: ${fileResponse.status}`);
        }
        
        // Get file as blob
        const fileBlob = await fileResponse.blob();
        
        // Create a File object with the original name
        const file = new File([fileBlob], project.filename, {
            type: getFileTypeFromExtension(project.filename)
        });
        
        console.log(`📄 File recuperato: ${file.name} (${formatFileSize(file.size)})`);
        
        // Set the file in the app
        if (window.wallPackingApp) {
            window.wallPackingApp.currentFile = file;
            window.wallPackingApp.isReusedProject = true; // Mark as reused project to prevent saving
            window.wallPackingApp.showFileInfo(file, false); // false = don't reset flags since we're reusing
            
            // Update navigation state to disable global settings (projects history remains accessible)
            window.wallPackingApp.updateNavigationState();
        }
        
        // Now automatically process the file to go directly to results
        console.log('🔄 Rielaborazione automatica con configurazioni ripristinate...');
        
        if (window.wallPackingApp) {
            // Update loading message
            const loadingTitle = document.getElementById('loadingTitle');
            const loadingMessage = document.getElementById('loadingMessage');
            if (loadingTitle) loadingTitle.textContent = 'Rielaborazione in corso...';
            if (loadingMessage) loadingMessage.textContent = 'Applicazione configurazioni salvate e calcolo packing automatico';
            
            // Directly call processFile to get results
            await window.wallPackingApp.processFile();
            
            // Go to application view (main app section) instead of closing everything
            window.wallPackingApp.showMainSection('app');
            window.wallPackingApp.showSection('results'); // Show results section in app
            
            // Close the past projects panel
            const panel = document.getElementById('pastProjectsPanel');
            const icon = document.getElementById('pastProjectsExpandIcon');
            if (panel && icon) {
                panel.style.display = 'none';
                icon.style.transform = 'rotate(0deg)';
            }
            
            // Show success message
            window.wallPackingApp.showToast(
                `Progetto "${project.name}" ripristinato con successo!`, 
                'success',
                6000
            );
        }
        
    } catch (error) {
        console.error('❌ Errore elaborazione automatica:', error);
        
        // Fallback: show config section with file loaded
        if (window.wallPackingApp) {
            window.wallPackingApp.hideLoading();
            window.wallPackingApp.showToast(
                `Configurazioni ripristinate. Il file è stato caricato, clicca "Calcola Packing" per continuare.`, 
                'warning'
            );
            
            // Switch to config section
            window.wallPackingApp.showMainSection('app');
            window.wallPackingApp.showSection('config');
        }
        
        // Close the past projects panel anyway
        const panel = document.getElementById('pastProjectsPanel');
        const icon = document.getElementById('pastProjectsExpandIcon');
        if (panel && icon) {
            panel.style.display = 'none';
            icon.style.transform = 'rotate(0deg)';
        }
    }
}

// Helper function to get MIME type from file extension
function getFileTypeFromExtension(filename) {
    const ext = filename.toLowerCase().split('.').pop();
    switch (ext) {
        case 'dwg':
            return 'application/acad';
        case 'dxf':
            return 'application/dxf';
        case 'svg':
            return 'image/svg+xml';
        default:
            return 'application/octet-stream';
    }
}

// Helper function to format file size (already exists but ensuring it's available)
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// Download Project File - Scarica il file originale del progetto
async function downloadProjectFile(projectId, event) {
    // Prevent event propagation to avoid closing the panel
    if (event) {
        event.stopPropagation();
        event.preventDefault();
    }
    
    console.log(`📥 Download file per progetto ID: ${projectId}`);
    
    try {
        // Show loading toast
        if (window.wallPackingApp) {
            window.wallPackingApp.showToast('Download in corso...', 'info');
        }
        
        // Get authentication token
        const token = sessionStorage.getItem('access_token');
        if (!token) {
            throw new Error('Autenticazione richiesta');
        }
        
        // Fetch the file
        const response = await fetch(`/api/v1/saved-projects/${projectId}/file`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (!response.ok) {
            if (response.status === 404) {
                throw new Error('File non trovato');
            }
            throw new Error(`Errore download: ${response.status}`);
        }
        
        // Get filename from Content-Disposition header or use default
        const contentDisposition = response.headers.get('Content-Disposition');
        let filename = 'project_file.dwg';
        
        if (contentDisposition) {
            const filenameMatch = contentDisposition.match(/filename="?(.+)"?/i);
            if (filenameMatch && filenameMatch[1]) {
                filename = filenameMatch[1];
            }
        }
        
        // Get the blob
        const blob = await response.blob();
        
        // Create download link
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        a.download = filename;
        
        // Trigger download
        document.body.appendChild(a);
        a.click();
        
        // Cleanup
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        
        console.log(`✅ File scaricato: ${filename}`);
        
        if (window.wallPackingApp) {
            window.wallPackingApp.showToast(`File "${filename}" scaricato con successo`, 'success');
        }
        
    } catch (error) {
        console.error('❌ Errore download file:', error);
        if (window.wallPackingApp) {
            window.wallPackingApp.showToast(error.message || 'Errore nel download del file', 'error');
        }
    }
}

// Delete Project - NO CONFIRMATION, KEEP CARD OPEN
async function deleteProject(projectId, event) {
    // Prevent event propagation to avoid closing the panel
    if (event) {
        event.stopPropagation();
        event.preventDefault();
    }
    
    // Mostra modal di conferma personalizzato
    showDeleteProjectModal(projectId);
}

function showDeleteProjectModal(projectId) {
    // Rimuovi modal esistente se presente
    const existingModal = document.getElementById('deleteProjectModal');
    if (existingModal) {
        existingModal.remove();
    }
    
    // Crea modal HTML
    const modalHTML = `
        <div id="deleteProjectModal" class="delete-modal-overlay" onclick="closeDeleteProjectModal()">
            <div class="delete-modal-content" onclick="event.stopPropagation()">
                <div class="delete-modal-header">
                    <i class="fas fa-exclamation-circle"></i>
                    <h3>Conferma eliminazione</h3>
                </div>
                <div class="delete-modal-body">
                    <p>Sei sicuro di voler eliminare questo progetto?</p>
                </div>
                <div class="delete-modal-actions">
                    <button class="modal-btn-cancel" onclick="closeDeleteProjectModal()">
                        Annulla
                    </button>
                    <button class="modal-btn-confirm" onclick="confirmDeleteProject(${projectId})">
                        Conferma
                    </button>
                </div>
            </div>
        </div>
    `;
    
    document.body.insertAdjacentHTML('beforeend', modalHTML);
}

function closeDeleteProjectModal() {
    const modal = document.getElementById('deleteProjectModal');
    if (modal) {
        modal.remove();
    }
}

async function confirmDeleteProject(projectId) {
    closeDeleteProjectModal();
    
    const token = sessionStorage.getItem('access_token');
    if (!token) {
        console.error('❌ Nessun token trovato');
        if (window.wallPackingApp) {
            window.wallPackingApp.showToast('Sessione scaduta. Effettua il login.', 'warning');
        }
        window.location.href = '/login';
        return;
    }
    
    try {
        const response = await fetch(`/api/v1/saved-projects/${projectId}`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
        }
        
        // Reload projects list
        await loadPastProjects();
        
        if (window.wallPackingApp) {
            window.wallPackingApp.showToast('Progetto eliminato con successo', 'success');
        }
        
    } catch (error) {
        console.error('Error deleting project:', error);
        if (window.wallPackingApp) {
            window.wallPackingApp.showToast(`Errore: ${error.message}`, 'error');
        }
    }
}

// Refresh Past Projects
function refreshPastProjects() {
    loadPastProjects();
}

// Clear All Projects
async function clearAllProjects() {
    console.log('🗑️ clearAllProjects chiamata');
    
    // Debug: Controlla stato autenticazione
    const token = sessionStorage.getItem('access_token');
    const tokenType = sessionStorage.getItem('token_type');
    console.log('🔍 Debug auth state:', {
        hasToken: !!token,
        tokenLength: token ? token.length : 0,
        tokenType: tokenType,
        tokenPreview: token ? token.substring(0, 20) + '...' : 'null'
    });
    
    if (!token) {
        console.error('❌ Nessun token trovato, redirect a login');
        if (window.wallPackingApp) {
            window.wallPackingApp.showToast('Sessione scaduta. Effettua il login.', 'warning');
        }
        window.location.href = '/login';
        return;
    }
    
    // Mostra modal di conferma professionale
    showDeleteConfirmationModal();
}

// Modal di conferma professionale
function showDeleteConfirmationModal() {
    // Rimuovi modal esistente se presente
    const existingModal = document.getElementById('deleteConfirmationModal');
    if (existingModal) {
        existingModal.remove();
    }
    
    // Crea modal HTML
    const modalHTML = `
        <div id="deleteConfirmationModal" class="delete-modal-overlay">
            <div class="delete-modal-card">
                <div class="delete-modal-header">
                    <i class="fas fa-exclamation-triangle"></i>
                    <h3>Conferma Eliminazione</h3>
                </div>
                <div class="delete-modal-body">
                    <p><strong>Attenzione!</strong></p>
                    <p>Stai per eliminare <strong>tutti i progetti salvati</strong> dal tuo archivio.</p>
                    <p>Questa operazione disattiverà permanentemente tutti i tuoi progetti.</p>
                    <div class="delete-confirmation-input">
                        <label for="confirmText">Per confermare, digita: <strong>ELIMINA TUTTO</strong></label>
                        <input type="text" id="confirmText" placeholder="Scrivi qui..." autocomplete="off">
                        <div class="input-feedback" id="inputFeedback"></div>
                    </div>
                </div>
                <div class="delete-modal-footer">
                    <button type="button" class="btn-cancel" onclick="closeDeleteModal()">
                        <i class="fas fa-times"></i> Annulla
                    </button>
                    <button type="button" class="btn-confirm" id="confirmDeleteBtn" disabled onclick="executeDeleteAll()">
                        <i class="fas fa-trash-alt"></i> Elimina Tutto
                    </button>
                </div>
            </div>
        </div>
    `;
    
    // Aggiungi modal al DOM
    document.body.insertAdjacentHTML('beforeend', modalHTML);
    
    // Setup listeners
    const confirmInput = document.getElementById('confirmText');
    const confirmBtn = document.getElementById('confirmDeleteBtn');
    const feedback = document.getElementById('inputFeedback');
    
    confirmInput.addEventListener('input', function() {
        const value = this.value.trim();
        if (value === 'ELIMINA TUTTO') {
            confirmBtn.disabled = false;
            confirmBtn.classList.add('enabled');
            feedback.textContent = '✓ Confermato';
            feedback.className = 'input-feedback success';
        } else if (value.length > 0) {
            confirmBtn.disabled = true;
            confirmBtn.classList.remove('enabled');
            feedback.textContent = '✗ Testo non corretto';
            feedback.className = 'input-feedback error';
        } else {
            confirmBtn.disabled = true;
            confirmBtn.classList.remove('enabled');
            feedback.textContent = '';
            feedback.className = 'input-feedback';
        }
    });
    
    // Focus sull'input
    setTimeout(() => confirmInput.focus(), 100);
    
    // Chiudi con ESC
    document.addEventListener('keydown', function escHandler(e) {
        if (e.key === 'Escape') {
            closeDeleteModal();
            document.removeEventListener('keydown', escHandler);
        }
    });
}

function closeDeleteModal() {
    const modal = document.getElementById('deleteConfirmationModal');
    if (modal) {
        modal.classList.add('closing');
        setTimeout(() => modal.remove(), 300);
    }
}

async function executeDeleteAll() {
    const modal = document.getElementById('deleteConfirmationModal');
    const confirmBtn = document.getElementById('confirmDeleteBtn');
    
    try {
        // Disabilita pulsante e mostra loading
        confirmBtn.disabled = true;
        confirmBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Eliminazione...';
        
        // Ottieni token corretto (usa access_token come il resto del sistema)
        const token = sessionStorage.getItem('access_token');
        if (!token) {
            throw new Error('Sessione scaduta. Effettua nuovamente il login.');
        }
        
        console.log('🔑 Invio richiesta eliminazione progetti...');
        
        const response = await fetch('/api/v1/saved-projects/all', {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
        });
        
        console.log('📡 Response status:', response.status);
        
        if (!response.ok) {
            if (response.status === 401) {
                console.warn('❌ Token non valido o scaduto');
                throw new Error('Sessione scaduta. Effettua nuovamente il login.');
            }
            
            const errorText = await response.text();
            throw new Error(`Errore server: ${response.status} - ${errorText}`);
        }
        
        const result = await response.json();
        handleDeleteSuccess(result);
        
    } catch (error) {
        console.error('❌ Errore nell\'eliminazione progetti:', error);
        
        // Mostra errore nel modal
        confirmBtn.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Errore';
        confirmBtn.style.background = '#dc3545';
        
        setTimeout(() => {
            if (error.message.includes('scaduta') || error.message.includes('login')) {
                closeDeleteModal();
                // Redirect a login
                window.location.href = '/login';
            } else {
                closeDeleteModal();
                if (window.wallPackingApp) {
                    window.wallPackingApp.showToast(`Errore: ${error.message}`, 'error');
                }
            }
        }, 2000);
    }
}

function handleDeleteSuccess(result) {
    console.log('✅ Eliminazione completata:', result);
    
    const confirmBtn = document.getElementById('confirmDeleteBtn');
    confirmBtn.innerHTML = '<i class="fas fa-check"></i> Completato';
    confirmBtn.style.background = '#28a745';
    
    setTimeout(() => {
        closeDeleteModal();
        
        const message = result.deleted_count > 0 
            ? `Eliminati ${result.deleted_count} progetti dall'archivio`
            : 'Nessun progetto da eliminare';
            
        if (window.wallPackingApp) {
            window.wallPackingApp.showToast(message, 'success');
        }
        
        // Ricarica la lista progetti
        setTimeout(() => {
            loadPastProjects();
        }, 500);
    }, 1500);
}

// Save Current Project (called when project is completed)
async function saveCurrentProject(projectData) {
    console.log('💾 saveCurrentProject chiamata con:', projectData);
    
    if (!projectData || !projectData.name) {
        console.warn('❌ Cannot save project: missing project data or name');
        if (window.wallPackingApp) {
            window.wallPackingApp.showToast('Errore: dati progetto mancanti', 'error');
        }
        return false;
    }
    
    try {
        const sessionId = window.wallPackingApp ? window.wallPackingApp.currentSessionId : null;
        
        if (!sessionId) {
            console.warn('❌ Cannot save project: missing session_id');
            if (window.wallPackingApp) {
                window.wallPackingApp.showToast('Errore: sessione non valida', 'error');
            }
            return false;
        }
        
        // Add session_id to access file bytes on server
        const saveData = {
            session_id: sessionId,
            name: projectData.name,
            filename: projectData.filename,
            file_path: projectData.file_path || '', // Will be set by backend
            block_dimensions: getCurrentBlockDimensions(),
            color_theme: getCurrentColorTheme(),
            packing_config: projectData.packing_config || {
                // Fallback configuration
            },
            results: projectData.results,
            wall_dimensions: projectData.wall_dimensions,
            total_blocks: projectData.total_blocks,
            efficiency: projectData.efficiency,
            svg_path: projectData.svg_path,
            pdf_path: projectData.pdf_path,
            json_path: projectData.json_path
        };
        
        console.log('💾 Salvando progetto con session_id:', sessionId);
        console.log('📝 Dati da salvare:', saveData);
        
        // FIXED: Usa sessionStorage invece di localStorage per il token
        const token = sessionStorage.getItem('access_token');
        if (!token) {
            console.warn('❌ Cannot save project: missing authentication token');
            if (window.wallPackingApp) {
                window.wallPackingApp.showToast('Effettua il login per salvare il progetto', 'error');
            }
            return false;
        }
        
        const response = await fetch('/api/v1/saved-projects/save', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify(saveData)
        });
        
        console.log('📡 Response status:', response.status);
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error('❌ Server response error:', errorText);
            throw new Error(`HTTP error! status: ${response.status} - ${errorText}`);
        }
        
        const data = await response.json();
        console.log('✅ Progetto salvato con successo:', data);
        
        if (window.wallPackingApp) {
            window.wallPackingApp.showToast(`Progetto "${projectData.name}" salvato per riutilizzo futuro!`, 'success');
        }
        
        return true;
        
    } catch (error) {
        console.error('❌ Error saving project:', error);
        console.error('❌ Error stack:', error.stack);
        
        let errorMessage = 'Errore nel salvataggio progetto';
        if (error.message.includes('401')) {
            errorMessage = 'Errore di autenticazione - rieffettua il login';
        } else if (error.message.includes('403')) {
            errorMessage = 'Errore di autorizzazione';
        } else if (error.message.includes('500')) {
            errorMessage = 'Errore del server';
        }
        
        if (window.wallPackingApp) {
            window.wallPackingApp.showToast(errorMessage, 'error');
        }
        return false;
    }
}

// Setup search for past projects
document.addEventListener('DOMContentLoaded', function() {
    // Prevent the past projects panel from closing when clicked inside
    const pastProjectsPanel = document.getElementById('pastProjectsPanel');
    if (pastProjectsPanel) {
        pastProjectsPanel.addEventListener('click', function(event) {
            event.stopPropagation();
        });
    }
    
    // Search functionality
    const searchInput = document.getElementById('projectSearchInput');
    if (searchInput) {
        // Prevent search input from closing the panel when clicked
        searchInput.addEventListener('click', function(event) {
            event.stopPropagation();
        });
        
        searchInput.addEventListener('input', function() {
            const searchTerm = this.value.toLowerCase();
            const filteredProjects = pastProjectsData.filter(project => 
                (project.name || project.filename).toLowerCase().includes(searchTerm)
            );
            renderPastProjects(filteredProjects);
        });
    }
});

// ===== MORALETTI CONFIGURATION SYSTEM =====

// Toggle moraletti panel
function toggleMoralettiPanel() {
    const panel = document.getElementById('moralettiPanel');
    const icon = document.getElementById('moralettiExpandIcon');
    
    if (!panel || !icon) return;
    
    const isVisible = panel.style.display !== 'none';
    
    if (isVisible) {
        // Close panel
        panel.style.display = 'none';
        icon.classList.remove('expanded');
        
        // Also close the preview section
        const visualSection = document.getElementById('moralettiVisualSection');
        if (visualSection) {
            visualSection.style.display = 'none';
        }
        
        console.log('🔧 Moraletti panel closed');
    } else {
        // Close all other panels first
        closeAllSettingsPanels();
        
        // Open panel
        panel.style.display = 'block';
        icon.classList.add('expanded');
        
        // Initialize panel if not already done
        if (!window.moralettiInitialized) {
            setTimeout(() => {
                initializeMoralettiConfiguration();
                window.moralettiInitialized = true;
            }, 100);
        }
        
        console.log('🔧 Moraletti panel opened');
    }
}

// Initialize moraletti configuration
function initializeMoralettiConfiguration() {
    console.log('🔧 Initializing Moraletti Configuration System');
    
    // Load saved configuration from localStorage
    const savedConfig = localStorage.getItem('moralettiConfiguration');
    let currentConfig;
    
    if (savedConfig) {
        try {
            currentConfig = JSON.parse(savedConfig);
            console.log('🔧 Using saved moraletti configuration');
        } catch (e) {
            console.warn('⚠️ Error parsing saved moraletti config, using defaults');
            currentConfig = getDefaultMoralettiConfig();
        }
    } else {
        currentConfig = getDefaultMoralettiConfig();
        console.log('🔧 Using default moraletti configuration');
    }
    
    // Apply configuration to UI
    applyMoralettiConfigToUI(currentConfig);
    
    // Setup event listeners
    setupMoralettiEventListeners();
    
    // Update preview
    updateMoralettiPreview();
    
    console.log('✅ Moraletti Configuration System initialized');
}

// Get default moraletti configuration
function getDefaultMoralettiConfig() {
    const blockDimensions = getCurrentBlockDimensions();
    const largestBlock = Math.max(
        blockDimensions.block1.width,
        blockDimensions.block2.width,
        blockDimensions.block3.width
    );
    
    // Use block height from block1 (which controls all heights via synchronization)
    const blockHeight = blockDimensions.block1.height;
    
    return {
        thickness: 58,
        height: blockHeight,  // Moraletti height matches block height
        heightFromGround: 0,
        spacing: Math.floor(largestBlock / 3),  // Preset intelligente
        // Numero moraletti default per tipo blocco
        countLarge: 3,
        countMedium: 2,
        countSmall: 1
    };
}

// Apply moraletti configuration to UI
function applyMoralettiConfigToUI(config) {
    const thicknessInput = document.getElementById('moralettiThickness');
    const heightInput = document.getElementById('moralettiHeight');
    const heightFromGroundInput = document.getElementById('moralettiHeightFromGround');
    const spacingInput = document.getElementById('moralettiSpacing');
    const countLargeInput = document.getElementById('moralettiCountLarge');
    const countMediumInput = document.getElementById('moralettiCountMedium');
    const countSmallInput = document.getElementById('moralettiCountSmall');
    const presetHint = document.getElementById('presetHint');
    const activeSummary = document.getElementById('moralettiActiveSummary');
    
    if (thicknessInput) thicknessInput.value = config.thickness;
    if (heightInput) heightInput.value = config.height;
    if (heightFromGroundInput) heightFromGroundInput.value = config.heightFromGround;
    if (spacingInput) spacingInput.value = config.spacing;
    if (countLargeInput) countLargeInput.value = config.countLarge || 3;
    if (countMediumInput) countMediumInput.value = config.countMedium || 2;
    if (countSmallInput) countSmallInput.value = config.countSmall || 1;
    
    // Update preset display
    if (presetHint) presetHint.textContent = `Spaziatura: ${config.spacing}mm`;
    
    // Update active configuration summary
    if (activeSummary) {
        activeSummary.textContent = `${config.thickness}mm × ${config.height}mm, spaziatura ${config.spacing}mm`;
    }
    
    // Update the visual preview
    updateMoralettiPreview();
}

// Setup moraletti event listeners
function setupMoralettiEventListeners() {
    const inputs = ['moralettiThickness', 'moralettiHeight', 'moralettiHeightFromGround', 'moralettiSpacing', 
                    'moralettiCountLarge', 'moralettiCountMedium', 'moralettiCountSmall'];
    
    inputs.forEach(inputId => {
        const input = document.getElementById(inputId);
        if (input) {
            input.addEventListener('input', () => {
                updateMoralettiPreview();
            });
            
            // Prevent panel from closing when interacting with inputs
            input.addEventListener('click', (e) => e.stopPropagation());
            input.addEventListener('focus', (e) => e.stopPropagation());
        }
    });
}

// Update moraletti preview
function updateMoralettiPreview() {
    console.log('🔧 Updating Moraletti Preview');
    
    // Safely get input values with fallbacks
    const spacingInput = document.getElementById('moralettiSpacing');
    const thicknessInput = document.getElementById('moralettiThickness');
    const heightInput = document.getElementById('moralettiHeight');
    const heightFromGroundInput = document.getElementById('moralettiHeightFromGround');
    
    if (!spacingInput || !thicknessInput || !heightInput || !heightFromGroundInput) {
        console.warn('🔧 Moraletti inputs not ready yet, skipping preview update');
        return;
    }
    
    const spacing = parseInt(spacingInput.value) || 413;
    const thickness = parseInt(thicknessInput.value) || 58;
    const height = parseInt(heightInput.value) || 495;
    const heightFromGround = parseInt(heightFromGroundInput.value) || 0;
    
    console.log('🔧 Current values:', { spacing, thickness, height, heightFromGround });
    
    const blockDimensions = getCurrentBlockDimensions();
    
    // Update summary
    updateMoralettiSummary(thickness, height, spacing);
    
    // Calculate and update visual previews
    updateBlockConfigurationPreviews(blockDimensions, spacing, thickness);
    
    // Update preset hint
    updatePresetHint(blockDimensions);
    
    // Update alignment status
    updateEnhancedAlignmentStatus();
}

// Update moraletti summary
function updateMoralettiSummary(thickness, height, spacing) {
    const summaryElement = document.getElementById('moralettiActiveSummary');
    if (summaryElement) {
        summaryElement.textContent = `${thickness}mm × ${height}mm, spaziatura ${spacing}mm`;
    }
}

// Update block configuration previews
function updateBlockConfigurationPreviews(blockDimensions, spacing, thickness) {
    const configs = [
        {
            id: 'three',
            totalWidth: blockDimensions.block1.width + blockDimensions.block2.width + blockDimensions.block3.width,
            blockWidths: [blockDimensions.block1.width, blockDimensions.block2.width, blockDimensions.block3.width],
            svgViewBox: "0 0 400 120"
        },
        {
            id: 'two', 
            totalWidth: blockDimensions.block1.width + blockDimensions.block2.width,
            blockWidths: [blockDimensions.block1.width, blockDimensions.block2.width],
            svgViewBox: "0 0 300 120"
        },
        {
            id: 'one',
            totalWidth: blockDimensions.block1.width,
            blockWidths: [blockDimensions.block1.width],
            svgViewBox: "0 0 200 120"
        }
    ];
    
    configs.forEach(config => {
        const positions = calculateMoralettiPositionsJS(config.totalWidth, spacing);
        
        // Update width display
        const widthElement = document.getElementById(`${config.id}BlockWidth`);
        if (widthElement) {
            widthElement.textContent = `${config.totalWidth}mm`;
        }
        
        // Update positions text
        const positionsElement = document.getElementById(`${config.id}BlockPositions`);
        if (positionsElement) {
            positionsElement.textContent = `a ${positions.join(', ')}mm`;
        }
        
        // Update SVG visualization
        updateSVGVisualization(config.id, config, positions, thickness, spacing);
    });
}

// Update SVG visualization
function updateSVGVisualization(configId, config, moralettiPositions, thickness, spacing) {
    const svg = document.querySelector(`#${configId}BlockPreview .blocks-svg`);
    if (!svg) return;
    
    // Clear existing content
    svg.innerHTML = '';
    
    const viewBoxWidth = configId === 'three' ? 400 : (configId === 'two' ? 300 : 200);
    const scale = (viewBoxWidth - 20) / config.totalWidth; // Scale to fit with padding
    
    // Draw blocks
    let currentX = 10;
    config.blockWidths.forEach((width, index) => {
        const scaledWidth = width * scale;
        
        const blockRect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
        blockRect.setAttribute('class', `block-rect block${index + 1}`);
        blockRect.setAttribute('x', currentX);
        blockRect.setAttribute('y', '20');
        blockRect.setAttribute('width', scaledWidth);
        blockRect.setAttribute('height', '80');
        blockRect.setAttribute('fill', '#E5E7EB');
        blockRect.setAttribute('stroke', '#374151');
        blockRect.setAttribute('stroke-width', '2');
        
        svg.appendChild(blockRect);
        currentX += scaledWidth;
    });
    
    // Draw moraletti
    moralettiPositions.forEach((position, index) => {
        const scaledX = 10 + (position * scale) - (thickness * scale / 2);
        const scaledThickness = Math.max(6, thickness * scale); // Minimum visible thickness
        
        const moralettoRect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
        moralettoRect.setAttribute('class', 'moraletto-rect');
        moralettoRect.setAttribute('x', scaledX);
        moralettoRect.setAttribute('y', '10');
        moralettoRect.setAttribute('width', scaledThickness);
        moralettoRect.setAttribute('height', '100');
        moralettoRect.setAttribute('fill', '#8B4513');
        moralettoRect.setAttribute('stroke', '#654321');
        moralettoRect.setAttribute('stroke-width', '1');
        
        svg.appendChild(moralettoRect);
        
        // Add dimension text
        const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        text.setAttribute('class', 'dimension-text');
        text.setAttribute('x', scaledX + scaledThickness / 2);
        text.setAttribute('y', '15');
        text.setAttribute('text-anchor', 'middle');
        text.setAttribute('font-size', '10');
        text.setAttribute('fill', '#374151');
        text.textContent = position;
        
        svg.appendChild(text);
    });
}

// Update preset hint
function updatePresetHint(blockDimensions) {
    const largestBlock = Math.max(
        blockDimensions.block1.width,
        blockDimensions.block2.width,
        blockDimensions.block3.width
    );
    const presetSpacing = Math.floor(largestBlock / 3);
    
    const hintElement = document.getElementById('presetHint');
    if (hintElement) {
        hintElement.textContent = `Spaziatura: ${presetSpacing}mm`;
    }
}

// Update enhanced alignment status
function updateEnhancedAlignmentStatus() {
    const alignmentIcon = document.getElementById('enhancedAlignmentIcon');
    const alignmentStatus = document.getElementById('enhancedAlignmentStatus');
    
    if (alignmentIcon && alignmentStatus) {
        // For now, always show positive alignment (the logic guarantees it)
        alignmentIcon.className = 'fas fa-check-circle status-icon';
        alignmentIcon.style.color = '#10B981';
        alignmentStatus.textContent = 'Allineamento verticale garantito';
    }
}

// Calculate moraletti positions (JavaScript version)
// Calculate moraletti positions (JavaScript version) - NUOVA LOGICA Ottobre 2025
// Calculate moraletti positions (JavaScript version) - NUOVA LOGICA Ottobre 2025
function calculateMoralettiPositionsJS(totalWidth, thickness, spacing, count) {
    const positions = [];
    
    for (let i = 0; i < count; i++) {
        // Distanza dal bordo destro: 0mm, spacing, 2*spacing, ...
        const distanceFromRight = i * spacing;
        
        // Converti in posizione dal bordo sinistro
        const positionFromLeft = totalWidth - distanceFromRight;
        
        // Controlla che non si esca dal blocco a sinistra
        if (positionFromLeft - (thickness / 2) >= 0) {
            positions.push(Math.round(positionFromLeft));
        } else {
            break; // Ferma se il moraletto esce dal blocco
        }
    }
    
    return positions;
}

// Update alignment status
function updateAlignmentStatus() {
    const alignmentIcon = document.getElementById('alignmentIcon');
    const alignmentStatus = document.getElementById('alignmentStatus');
    
    if (alignmentIcon && alignmentStatus) {
        // For now, always show positive alignment (the logic guarantees it)
        alignmentIcon.className = 'fas fa-check-circle alignment-icon';
        alignmentIcon.style.color = '#10B981';
        alignmentStatus.textContent = 'Allineamento verticale garantito';
    }
}

// Apply moraletti preset
function applyMoralettiPreset() {
    console.log('🔧 Applying moraletti preset');
    
    const blockDimensions = getCurrentBlockDimensions();
    const largestBlock = Math.max(
        blockDimensions.block1.width,
        blockDimensions.block2.width,
        blockDimensions.block3.width
    );
    
    const presetSpacing = Math.floor(largestBlock / 3);
    
    // Apply preset values to input
    const spacingInput = document.getElementById('moralettiSpacing');
    if (spacingInput) {
        spacingInput.value = presetSpacing;
    }
    
    // Update preset hint
    const presetHint = document.getElementById('presetHint');
    if (presetHint) {
        presetHint.textContent = `Spaziatura: ${presetSpacing}mm`;
    }
    
    // Update preview
    updateMoralettiPreview();
    
    if (window.wallPackingApp) {
        window.wallPackingApp.showToast(`Preset applicato: spaziatura ${presetSpacing}mm (blocco max: ${largestBlock}mm)`, 'success');
    }
}

// Reset moraletti to defaults
function resetMoralettiDefaults() {
    console.log('🔧 Resetting moraletti to defaults');
    
    const defaultConfig = getDefaultMoralettiConfig();
    applyMoralettiConfigToUI(defaultConfig);
    updateMoralettiPreview();
    
    if (window.wallPackingApp) {
        window.wallPackingApp.showToast('Configurazione moraletti ripristinata ai valori di default', 'info');
    }
}

// Save moraletti configuration
function saveMoralettiConfiguration() {
    console.log('💾 Saving moraletti configuration');
    
    const config = {
        thickness: parseInt(document.getElementById('moralettiThickness').value) || 58,
        height: parseInt(document.getElementById('moralettiHeight').value) || 495,
        heightFromGround: parseInt(document.getElementById('moralettiHeightFromGround').value) || 0,
        spacing: parseInt(document.getElementById('moralettiSpacing').value) || 413,
        // Nuovi parametri per numero moraletti per tipo blocco
        countLarge: parseInt(document.getElementById('moralettiCountLarge').value) || 3,
        countMedium: parseInt(document.getElementById('moralettiCountMedium').value) || 2,
        countSmall: parseInt(document.getElementById('moralettiCountSmall').value) || 1
    };
    
    // Save to localStorage
    localStorage.setItem('moralettiConfiguration', JSON.stringify(config));
    localStorage.setItem('moralettiSaved', 'true');
    
    // Apply to current session
    window.currentMoralettiConfig = config;
    
    // Lock the inputs for safety
    lockMoralettiInputs();
    
    if (window.wallPackingApp) {
        window.wallPackingApp.showToast('Configurazione moraletti salvata! Per modificare, riconferma le dimensioni dei blocchi.', 'success');
    }
    
    console.log('✅ Moraletti configuration saved:', config);
    
    // Se stavamo caricando un profilo, resetta il flag e mostra messaggio completamento
    if (window.isLoadingProfile) {
        console.log('✅ Caricamento profilo completato!');
        window.isLoadingProfile = false;
        
        setTimeout(() => {
            if (window.wallPackingApp) {
                window.wallPackingApp.showToast('✅ Profilo caricato completamente! Configurazioni applicate.', 'success');
            }
        }, 1000);
    }
}

// Get current moraletti configuration
function getCurrentMoralettiConfiguration() {
    if (window.currentMoralettiConfig) {
        return window.currentMoralettiConfig;
    }
    
    // Check localStorage for saved configuration
    const saved = localStorage.getItem('moralettiConfiguration');
    if (saved) {
        try {
            return JSON.parse(saved);
        } catch (e) {
            console.warn('Error parsing saved moraletti configuration, using defaults');
        }
    }
    
    // Fallback to defaults
    return getDefaultMoralettiConfig();
}

// ==== NEW MORALETTI FUNCTIONS ====

// Enable moraletti configuration after blocks are confirmed
function enableMoralettiConfiguration() {
    console.log('🔧 Enabling moraletti configuration');
    
    const moralettiCard = document.getElementById('moralettiCardContainer');
    const prerequisiteWarning = document.getElementById('moralettiPrerequisiteWarning');
    const protectionWarning = document.getElementById('moralettiProtectionWarning');
    const resetBtn = document.getElementById('resetMoralettiBtn');
    const saveBtn = document.getElementById('saveMoralettiBtn');
    
    if (moralettiCard) {
        moralettiCard.classList.remove('disabled');
    }
    
    if (prerequisiteWarning) {
        prerequisiteWarning.style.display = 'none';
    }
    
    if (protectionWarning) {
        protectionWarning.style.display = 'none';
    }
    
    // Enable action buttons
    if (resetBtn) {
        resetBtn.disabled = false;
    }
    
    if (saveBtn) {
        saveBtn.disabled = false;
    }
    
    // Unlock moraletti inputs when blocks are reconfirmed
    unlockMoralettiInputs();
    
    // Clear the saved flag so user can modify again
    localStorage.removeItem('moralettiSaved');
    
    // Update localStorage to remember that blocks are configured
    localStorage.setItem('blocksConfigured', 'true');
    
    console.log('✅ Moraletti configuration enabled and unlocked');
}

// Lock moraletti inputs after saving
function lockMoralettiInputs() {
    const inputs = ['moralettiThickness', 'moralettiHeight', 'moralettiHeightFromGround', 'moralettiSpacing'];
    
    inputs.forEach(inputId => {
        const input = document.getElementById(inputId);
        if (input) {
            input.disabled = true;
            input.style.backgroundColor = '#F3F4F6';
            input.style.color = '#6B7280';
        }
    });
    
    // Disable preset button
    const presetBtn = document.querySelector('.preset-action-btn');
    if (presetBtn) {
        presetBtn.disabled = true;
        presetBtn.style.opacity = '0.5';
    }
    
    // Disable action buttons (but keep preview enabled)
    const resetBtn = document.getElementById('resetMoralettiBtn');
    const saveBtn = document.getElementById('saveMoralettiBtn');
    
    if (resetBtn) {
        resetBtn.disabled = true;
    }
    
    if (saveBtn) {
        saveBtn.disabled = true;
    }
}

// Unlock moraletti inputs 
function unlockMoralettiInputs() {
    const inputs = ['moralettiThickness', 'moralettiHeight', 'moralettiHeightFromGround', 'moralettiSpacing'];
    
    inputs.forEach(inputId => {
        const input = document.getElementById(inputId);
        if (input) {
            input.disabled = false;
            input.style.backgroundColor = '';
            input.style.color = '';
        }
    });
    
    // Enable preset button
    const presetBtn = document.querySelector('.preset-action-btn');
    if (presetBtn) {
        presetBtn.disabled = false;
        presetBtn.style.opacity = '1';
    }
    
    // Enable action buttons
    const resetBtn = document.getElementById('resetMoralettiBtn');
    const saveBtn = document.getElementById('saveMoralettiBtn');
    
    if (resetBtn) {
        resetBtn.disabled = false;
    }
    
    if (saveBtn) {
        saveBtn.disabled = false;
    }
}

// Check if blocks are configured on page load
function checkBlocksConfigured() {
    const blocksConfigured = localStorage.getItem('blocksConfigured');
    const savedDimensions = localStorage.getItem('blockDimensions');
    const moralettiSaved = localStorage.getItem('moralettiSaved');
    
    if (blocksConfigured === 'true' && savedDimensions) {
        enableMoralettiConfiguration();
        
        // If moraletti were saved, lock them
        if (moralettiSaved === 'true') {
            setTimeout(() => {
                lockMoralettiInputs();
            }, 500); // Small delay to ensure inputs are loaded
        }
    }
}

// Generate moraletti preview with correct logic
function generateMoralettiPreview() {
    console.log('🔧 Generating moraletti preview');
    
    // First get the input parameters
    const spacingInput = document.getElementById('moralettiSpacing');
    const thicknessInput = document.getElementById('moralettiThickness');
    const heightInput = document.getElementById('moralettiHeight');
    const heightFromGroundInput = document.getElementById('moralettiHeightFromGround');
    
    if (!spacingInput || !thicknessInput || !heightInput || !heightFromGroundInput) {
        console.warn('🔧 Missing input parameters');
        return;
    }
    
    const spacing = parseInt(spacingInput.value) || 413;
    const thickness = parseInt(thicknessInput.value) || 58;
    const height = parseInt(heightInput.value) || 495;
    const heightFromGround = parseInt(heightFromGroundInput.value) || 0;
    
    // Get confirmed block dimensions
    const blockDimensions = getCurrentBlockDimensions();
    
    // Generate preview based on actual blocks according to technical image logic
    generateTechnicalPreview(blockDimensions, spacing, thickness);
    
    // Show visual section
    const visualSection = document.getElementById('moralettiVisualSection');
    if (visualSection) {
        visualSection.style.display = 'block';
    }
    
    // Update summary
    const activeSummary = document.getElementById('moralettiActiveSummary');
    if (activeSummary) {
        activeSummary.textContent = `${thickness}mm × ${height}mm, spaziatura ${spacing}mm`;
    }
}

// Generate technical preview according to the image provided
function generateTechnicalPreview(blockDimensions, spacing, thickness) {
    const previewContainer = document.getElementById('moralettiPreviewContainer');
    if (!previewContainer) return;
    
    // Clear existing content
    previewContainer.innerHTML = '';
    
    // Get moraletti counts from inputs (with defaults)
    const countLarge = parseInt(document.getElementById('moralettiCountLarge')?.value) || 3;
    const countMedium = parseInt(document.getElementById('moralettiCountMedium')?.value) || 2;
    const countSmall = parseInt(document.getElementById('moralettiCountSmall')?.value) || 1;
    
    // Sort blocks by width to determine: large, medium, small
    const blocks = [
        { id: 'block1', width: blockDimensions.block1.width, height: blockDimensions.block1.height },
        { id: 'block2', width: blockDimensions.block2.width, height: blockDimensions.block2.height },
        { id: 'block3', width: blockDimensions.block3.width, height: blockDimensions.block3.height }
    ].sort((a, b) => b.width - a.width); // Sort descending by width
    
    const largeBlock = blocks[0];   // Largest width
    const mediumBlock = blocks[1];  // Medium width
    const smallBlock = blocks[2];   // Smallest width
    
    // Generate preview with configured moraletti counts
    generateBlockPreview(largeBlock, countLarge, 'Blocco Grande', previewContainer, spacing, thickness);
    generateBlockPreview(mediumBlock, countMedium, 'Blocco Medio', previewContainer, spacing, thickness);
    generateBlockPreview(smallBlock, countSmall, 'Blocco Piccolo', previewContainer, spacing, thickness);
}

// Generate individual block preview with correct moraletti positioning
function generateBlockPreview(block, moralettiCount, title, container, spacing, thickness) {
    const previewDiv = document.createElement('div');
    previewDiv.className = 'block-configuration-preview';
    
    // Get height from ground parameter
    const heightFromGroundInput = document.getElementById('moralettiHeightFromGround');
    const heightFromGround = parseInt(heightFromGroundInput?.value) || 0;
    
    // Header
    const header = document.createElement('div');
    header.className = 'config-header';
    header.innerHTML = `
        <span class="config-title">${title}</span>
        <span class="config-width">${block.width}mm</span>
    `;
    
    // NUOVA LOGICA (Ottobre 2025): Posizionamento da DESTRA a SINISTRA
    // Primo moraletto con CENTRO sul bordo destro (0mm dal bordo destro)
    const moralettiPositions = [];
    
    for (let i = 0; i < moralettiCount; i++) {
        // Distanza dal bordo destro: 0mm, 420mm, 840mm, ...
        const distanceFromRight = i * spacing;
        
        // Converti in posizione dal bordo sinistro per rendering
        const positionFromLeft = block.width - distanceFromRight;
        
        // Controlla che non si esca dal blocco a sinistra
        if (positionFromLeft - (thickness / 2) >= 0) {
            moralettiPositions.push(Math.round(positionFromLeft));
        } else {
            break; // Ferma se il moraletto esce dal blocco
        }
    }
    
    // Visual container
    const visualContainer = document.createElement('div');
    visualContainer.className = 'visual-blocks-container';
    
    // Create SVG con spazio per moraletti che escono sopra e sotto - PIÙ GRANDE!
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('class', 'blocks-svg');
    svg.setAttribute('viewBox', '0 0 500 250'); // SVG più grande per visibilità
    svg.setAttribute('preserveAspectRatio', 'xMidYMid meet');
    svg.setAttribute('style', 'min-height: 200px;'); // Altezza minima più grande
    
    // SCALA FISSA DINAMICA - basata sul blocco PIÙ GRANDE disponibile
    // Così tutti i blocchi usano la stessa scala e i moraletti sono allineati!
    const blockSizes = [
        parseInt(document.getElementById('blockWidthLarge')?.value) || 1260,
        parseInt(document.getElementById('blockWidthMedium')?.value) || 840,
        parseInt(document.getElementById('blockWidthSmall')?.value) || 420
    ];
    const maxBlockWidth = Math.max(...blockSizes); // Blocco più grande
    const svgWidth = 480; // Larghezza disponibile nel SVG
    const scale = svgWidth / maxBlockWidth; // Scala fissa per tutti i blocchi!
    
    // Get moraletto height input
    const moralettoHeightInput = document.getElementById('moralettiHeight');
    const moralettoHeight = parseInt(moralettoHeightInput?.value) || 495;
    
    // Calcola altezze moraletto:
    // - heightFromGround (es. 95mm) = piedini SOTTO il blocco
    // - Dentro blocco = moralettoHeight - heightFromGround (es. 495 - 95 = 400mm)
    // - Spazio sopra = Lo spazio che resta nel blocco è per l'INCASTRO del blocco superiore
    const heightBelowBlock = heightFromGround; // Piedini sotto (95mm)
    const heightInsideBlock = moralettoHeight - heightFromGround; // Dentro blocco (400mm)
    
    // Il moraletto NON sporge mai sopra - lo spazio vuoto è per l'incastro
    const heightAboveBlock = 0; // Non disegnato - è spazio vuoto per incastro
    const spaceForInterlocking = block.height - heightInsideBlock; // Spazio per incastro blocco superiore
    
    // Posizioni Y nel SVG (scala proporzionale) - SVG più grande!
    const blockY = 40; // Più in alto visto che non c'è parte sopra
    const blockHeightSvg = 120; // Altezza SVG del blocco più grande per visibilità
    
    // Calcola proporzioni per le altezze nel SVG (basate su altezza blocco reale)
    const svgScale = blockHeightSvg / block.height; // Scala SVG rispetto a dimensioni reali
    const heightBelowSvg = heightBelowBlock * svgScale;
    const heightInsideSvg = heightInsideBlock * svgScale;
    
    // ALLINEA I BLOCCHI A DESTRA - perché i moraletti partono da destra!
    const maxBlockWidthSvg = maxBlockWidth * scale; // Larghezza SVG del blocco più grande
    const blockWidthSvg = block.width * scale; // Larghezza SVG di questo blocco
    const blockX = 10 + (maxBlockWidthSvg - blockWidthSvg); // Allineamento a destra
    
    // Draw block
    const blockRect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
    blockRect.setAttribute('x', blockX);
    blockRect.setAttribute('y', blockY);
    blockRect.setAttribute('width', blockWidthSvg);
    blockRect.setAttribute('height', blockHeightSvg);
    blockRect.setAttribute('fill', '#E5E7EB');
    blockRect.setAttribute('stroke', '#374151');
    blockRect.setAttribute('stroke-width', '2');
    svg.appendChild(blockRect);
    
    // Draw ground line (pavimento) se ci sono piedini
    if (heightFromGround > 0) {
        const groundY = blockY + blockHeightSvg + heightBelowSvg;
        const groundLine = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        groundLine.setAttribute('x1', '5');
        groundLine.setAttribute('y1', groundY);
        groundLine.setAttribute('x2', '495');
        groundLine.setAttribute('y2', groundY);
        groundLine.setAttribute('stroke', '#666');
        groundLine.setAttribute('stroke-width', '3');
        groundLine.setAttribute('stroke-dasharray', '8,4');
        svg.appendChild(groundLine);
        
        // Label per pavimento
        const groundText = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        groundText.setAttribute('x', '10');
        groundText.setAttribute('y', groundY + 18);
        groundText.setAttribute('font-size', '12');
        groundText.setAttribute('font-weight', 'bold');
        groundText.setAttribute('fill', '#666');
        groundText.textContent = '═══ Pavimento ═══';
        svg.appendChild(groundText);
    }
    
    // Draw moraletti con annotazioni dettagliate
    moralettiPositions.forEach((positionFromLeft, index) => {
        const moralettoWidth = 15; // SPESSORE FISSO - lo spessore reale (58mm) è uguale per tutti i blocchi!
        const scaledX = blockX + (positionFromLeft * scale) - (moralettoWidth / 2); // Usa blockX per allineamento
        
        // Calcola distanza dal bordo destro per la label
        const distanceFromRight = block.width - positionFromLeft;
        
        // MORALETTO COMPLETO con 2 PARTI (DENTRO + PIEDINI):
        // Il moraletto parte dall'alto del blocco e scende giù
        
        // 1. PARTE DENTRO IL BLOCCO (400mm) - colore medio
        // Questa parte va dal TOP del blocco verso il basso
        const insideY = blockY + blockHeightSvg - heightInsideSvg; // Parte dal fondo del blocco verso l'alto
        const insideRect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
        insideRect.setAttribute('x', scaledX);
        insideRect.setAttribute('y', insideY);
        insideRect.setAttribute('width', moralettoWidth);
        insideRect.setAttribute('height', heightInsideSvg);
        insideRect.setAttribute('fill', '#8B4513'); // Marrone medio
        insideRect.setAttribute('stroke', '#654321');
        insideRect.setAttribute('stroke-width', '2');
        svg.appendChild(insideRect);
        
        // 2. PIEDINI SOTTO IL BLOCCO (95mm) - colore scuro - ATTACCATI alla parte dentro
        if (heightFromGround > 0) {
            const piediniRect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
            piediniRect.setAttribute('x', scaledX);
            piediniRect.setAttribute('y', blockY + blockHeightSvg); // Parte subito sotto il blocco
            piediniRect.setAttribute('width', moralettoWidth);
            piediniRect.setAttribute('height', heightBelowSvg);
            piediniRect.setAttribute('fill', '#654321'); // Marrone scuro per piedini
            piediniRect.setAttribute('stroke', '#4A2511');
            piediniRect.setAttribute('stroke-width', '2');
            svg.appendChild(piediniRect);
            
            // Annotazione piedini (solo sul primo moraletto per chiarezza)
            if (index === 0) {
                const piediniLabel = document.createElementNS('http://www.w3.org/2000/svg', 'text');
                piediniLabel.setAttribute('x', scaledX + moralettoWidth + 5);
                piediniLabel.setAttribute('y', blockY + blockHeightSvg + (heightBelowSvg / 2));
                piediniLabel.setAttribute('font-size', '12');
                piediniLabel.setAttribute('font-weight', 'bold');
                piediniLabel.setAttribute('fill', '#654321');
                piediniLabel.textContent = `⬇ ${heightFromGround}mm`;
                svg.appendChild(piediniLabel);
            }
            
            // Annotazione dentro blocco (solo sul primo moraletto)
            if (index === 0) {
                const insideLabel = document.createElementNS('http://www.w3.org/2000/svg', 'text');
                insideLabel.setAttribute('x', scaledX + moralettoWidth + 5);
                insideLabel.setAttribute('y', insideY + (heightInsideSvg / 2));
                insideLabel.setAttribute('font-size', '12');
                insideLabel.setAttribute('font-weight', 'bold');
                insideLabel.setAttribute('fill', '#8B4513');
                insideLabel.textContent = `■ ${heightInsideBlock}mm`;
                svg.appendChild(insideLabel);
            }
        }
        
        // Label: mostra distanza dal bordo destro (0mm, 420mm, 840mm...)
        const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        text.setAttribute('x', scaledX + (moralettoWidth / 2));
        text.setAttribute('y', blockY - 10); // Sopra il blocco
        text.setAttribute('text-anchor', 'middle');
        text.setAttribute('font-size', '14');
        text.setAttribute('font-weight', 'bold');
        text.setAttribute('fill', '#1F2937');
        text.textContent = distanceFromRight + 'mm';
        svg.appendChild(text);
    });
    
    visualContainer.appendChild(svg);
    
    // Config info con informazioni dettagliate
    const configInfo = document.createElement('div');
    configInfo.className = 'config-info';
    
    // Calcola distanze e range per ogni moraletto (dal bordo DESTRO)
    const moralettiDetails = moralettiPositions.map((posFromLeft, index) => {
        // Distanza dal bordo destro
        const distanceFromRight = block.width - posFromLeft;
        
        // Range del moraletto (dal bordo destro)
        const moralettoStart = distanceFromRight - (thickness / 2);
        const moralettoEnd = distanceFromRight + (thickness / 2);
        
        return {
            index: index + 1,
            distanceFromRight: Math.round(distanceFromRight),
            start: Math.round(moralettoStart),
            end: Math.round(moralettoEnd)
        };
    });
    
    // Crea lista distanze semplici
    const distances = moralettiDetails.map(m => m.distanceFromRight + 'mm').join(', ');
    
    // Crea lista dettagliata con range
    const detailsHTML = moralettiDetails.map(m => 
        `<div class="moraletto-detail">
            <strong>M${m.index}:</strong> Centro a ${m.distanceFromRight}mm → Range (${m.start}mm, ${m.end}mm)
        </div>`
    ).join('');
    
    let infoHTML = `
        <span class="moraletti-count">${moralettiCount} Moraletti</span>
        <span class="positions-text">Distanze centri dal bordo destro: ${distances}</span>
        <div class="moraletti-ranges" style="margin-top: 8px; font-size: 11px; line-height: 1.6;">
            ${detailsHTML}
        </div>
    `;
    
    // Info dettagliate sulle altezze
    if (heightFromGround > 0 || moralettoHeight > 0) {
        const heightInside = moralettoHeight - heightFromGround;
        const spaceForInterlocking = block.height - heightInside;
        
        infoHTML += `
            <div class="height-details" style="margin-top: 12px; font-size: 12px; border-top: 2px solid #ddd; padding-top: 10px; line-height: 1.8;">
                <div style="font-weight: bold; margin-bottom: 6px;">📏 Composizione Moraletto (${moralettoHeight}mm totale):</div>
                <div style="color: #8B4513;">■ Dentro blocco: ${heightInside}mm</div>
                <div style="color: #654321;">⬇ Piedini sotto blocco: ${heightFromGround}mm</div>
                <div style="margin-top: 8px; padding: 8px; background: #FFF3CD; border-left: 3px solid #FFC107; border-radius: 4px;">
                    <div style="font-weight: bold; color: #856404; margin-bottom: 4px;">🔧 Spazio per incastro blocco superiore:</div>
                    <div style="color: #856404; font-size: 14px; font-weight: bold;">${spaceForInterlocking}mm</div>
                    <div style="font-style: italic; font-size: 11px; color: #666; margin-top: 4px;">
                        (Blocco ${block.height}mm - Moraletto dentro ${heightInside}mm)
                    </div>
                </div>
            </div>
        `;
    }
    
    configInfo.innerHTML = infoHTML;
    visualContainer.appendChild(configInfo);
    
    previewDiv.appendChild(header);
    previewDiv.appendChild(visualContainer);
    container.appendChild(previewDiv);
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    checkBlocksConfigured();
    
    // Update spacing suggestion if blocks are already configured
    setTimeout(() => {
        updateSpacingSuggestion();
    }, 500);
    
    // Setup height synchronization
    setupHeightSynchronization();
    
    // Initialize materials system
    updateMaterialSelector();
    setupMaterialChangeHandler();
});

// ==== HEIGHT SYNCHRONIZATION ====
function setupHeightSynchronization() {
    const block1Height = document.getElementById('block1Height');
    const block2Height = document.getElementById('block2Height');
    const block3Height = document.getElementById('block3Height');
    const moralettiHeight = document.getElementById('moralettiHeight');
    
    if (block1Height && block2Height && block3Height) {
        block1Height.addEventListener('input', function() {
            const heightValue = this.value;
            
            // Synchronize all block heights
            block2Height.value = heightValue;
            block3Height.value = heightValue;
            
            // Also synchronize moraletti height (moraletti should match block height)
            if (moralettiHeight) {
                moralettiHeight.value = heightValue;
                
                // Update moraletti summary with new height
                const thickness = parseInt(document.getElementById('moralettiThickness')?.value) || 58;
                const spacing = parseInt(document.getElementById('moralettiSpacing')?.value) || 413;
                updateMoralettiSummary(thickness, parseInt(heightValue), spacing);
                
                // Update moraletti preview if function exists
                if (typeof generateMoralettiPreview === 'function') {
                    generateMoralettiPreview();
                }
            }
            
            // Update block calculations if the function exists
            if (typeof updateBlockCalculations === 'function') {
                updateBlockCalculations();
            }
        });
    }
}

// ==== NEW AUTO-SUGGESTION FUNCTIONS ====

// Get current block dimensions from inputs
function getCurrentBlockDimensions() {
    const width1 = parseFloat(document.getElementById('block1Width')?.value) || 0;
    const height1 = parseFloat(document.getElementById('block1Height')?.value) || 0;
    const depth1 = parseFloat(document.getElementById('block1Depth')?.value) || 0;
    
    const width2 = parseFloat(document.getElementById('block2Width')?.value) || 0;
    const height2 = parseFloat(document.getElementById('block2Height')?.value) || 0;
    const depth2 = parseFloat(document.getElementById('block2Depth')?.value) || 0;
    
    const width3 = parseFloat(document.getElementById('block3Width')?.value) || 0;
    const height3 = parseFloat(document.getElementById('block3Height')?.value) || 0;
    const depth3 = parseFloat(document.getElementById('block3Depth')?.value) || 0;
    
    if (!width1 || !width2 || !width3) return null;
    
    return {
        block1: { width: width1, height: height1, depth: depth1 },
        block2: { width: width2, height: height2, depth: depth2 },
        block3: { width: width3, height: height3, depth: depth3 }
    };
}

// Update auto-suggestion when blocks change
function updateSpacingSuggestion() {
    const blockDimensions = getCurrentBlockDimensions();
    if (!blockDimensions) return;
    
    const largestBlock = Math.max(
        blockDimensions.block1.width,
        blockDimensions.block2.width,
        blockDimensions.block3.width
    );
    
    const suggestedSpacing = Math.floor(largestBlock / 3);
    
    const suggestedElement = document.getElementById('suggestedSpacing');
    if (suggestedElement) {
        suggestedElement.textContent = suggestedSpacing + 'mm';
    }
    
    return suggestedSpacing;
}

// Enhanced saveBlockDimensions with mandatory moraletti configuration
function saveBlockDimensionsEnhanced() {
    // Get input elements
    const input1 = document.getElementById('block1Width');
    const input2 = document.getElementById('block2Width');
    const input3 = document.getElementById('block3Width');
    
    // Clear previous error states
    [input1, input2, input3].forEach(input => {
        if (input) input.classList.remove('error');
    });
    
    // Validate block dimensions order
    const width1 = parseFloat(input1?.value) || 0;
    const width2 = parseFloat(input2?.value) || 0;
    const width3 = parseFloat(input3?.value) || 0;
    
    // Check: Blocco 1 must be > 0 (not empty or invalid)
    if (width1 <= 0) {
        if (input1) input1.classList.add('error');
        if (window.wallPackingApp) {
            window.wallPackingApp.showToast('❌ Errore: Il Blocco 1 (Grande) non può essere vuoto o minore/uguale a 0', 'error', 5000);
        }
        return;
    }
    
    // Check: Blocco 2 must be > 0
    if (width2 <= 0) {
        if (input2) input2.classList.add('error');
        if (window.wallPackingApp) {
            window.wallPackingApp.showToast('❌ Errore: Il Blocco 2 (Medio) non può essere vuoto o minore/uguale a 0', 'error', 5000);
        }
        return;
    }
    
    // Check: Blocco 3 must be > 0
    if (width3 <= 0) {
        if (input3) input3.classList.add('error');
        if (window.wallPackingApp) {
            window.wallPackingApp.showToast('❌ Errore: Il Blocco 3 (Piccolo) non può essere vuoto o minore/uguale a 0', 'error', 5000);
        }
        return;
    }
    
    // Check: Blocco 1 > Blocco 2 > Blocco 3 (all different)
    if (width1 <= width2) {
        if (input1) input1.classList.add('error');
        if (input2) input2.classList.add('error');
        if (window.wallPackingApp) {
            window.wallPackingApp.showToast('❌ Errore: Il Blocco 1 (Grande) deve avere larghezza maggiore del Blocco 2 (Medio)', 'error', 5000);
        }
        return;
    }
    
    if (width2 <= width3) {
        if (input2) input2.classList.add('error');
        if (input3) input3.classList.add('error');
        if (window.wallPackingApp) {
            window.wallPackingApp.showToast('❌ Errore: Il Blocco 2 (Medio) deve avere larghezza maggiore del Blocco 3 (Piccolo)', 'error', 5000);
        }
        return;
    }
    
    if (width1 === width2 || width2 === width3 || width1 === width3) {
        [input1, input2, input3].forEach(input => {
            if (input) input.classList.add('error');
        });
        if (window.wallPackingApp) {
            window.wallPackingApp.showToast('❌ Errore: Tutti i blocchi devono avere larghezze diverse tra loro', 'error', 5000);
        }
        return;
    }
    
    // Validation passed - save the dimensions
    saveBlockDimensions();
    
    // Update spacing suggestion
    const suggestedSpacing = updateSpacingSuggestion();
    
    // Auto-set the suggested spacing in the input
    const spacingInput = document.getElementById('moralettiSpacing');
    if (spacingInput && suggestedSpacing) {
        spacingInput.value = suggestedSpacing;
    }
    
    // Get the current block height from block1Height (which controls all heights)
    const height = parseFloat(document.getElementById('block1Height')?.value) || 495;
    
    // Update moraletti height to match block height
    const moralettiHeightInput = document.getElementById('moralettiHeight');
    if (moralettiHeightInput) {
        moralettiHeightInput.value = height;
    }
    
    // Update the active summary with suggested values
    const thickness = parseFloat(document.getElementById('moralettiThickness')?.value) || 58;
    const summaryElement = document.getElementById('moralettiActiveSummary');
    if (summaryElement && suggestedSpacing) {
        summaryElement.textContent = `${thickness}mm × ${height}mm, spaziatura ${suggestedSpacing}mm`;
    }
    
    // Show mandatory message
    setTimeout(() => {
        if (window.wallPackingApp) {
            window.wallPackingApp.showToast('⚠️ Ora devi configurare i moraletti prima di procedere!', 'warning', 5000);
        }
        
        // Scroll to moraletti section
        const moralettiCard = document.getElementById('moralettiCardContainer');
        if (moralettiCard) {
            moralettiCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
            
            // Add highlight effect
            moralettiCard.style.boxShadow = '0 0 20px rgba(59, 130, 246, 0.5)';
            moralettiCard.style.border = '3px solid #3B82F6';
            
            setTimeout(() => {
                moralettiCard.style.boxShadow = '';
                moralettiCard.style.border = '';
            }, 3000);
        }
    }, 1000);
}
// ============================================================================
// MANDATORY CONFIGURATION MODAL SYSTEM
// ============================================================================

// Listen for configuration-required event from auth.js
window.addEventListener('configuration-required', (event) => {
    const { has_configured_blocks, has_configured_moraletti } = event.detail;
    showMandatoryConfigModal(has_configured_blocks, has_configured_moraletti);
});

function showMandatoryConfigModal(hasBlocks, hasMoraletti) {
    console.log(' Mostrando modal configurazione obbligatoria');
    
    const modal = document.getElementById('mandatoryConfigModal');
    const blocksWarning = document.getElementById('configBlocksWarning');
    const moralettiWarning = document.getElementById('configMoralettiWarning');
    
    if (!modal) {
        console.error('Modal configurazione obbligatoria non trovato');
        return;
    }
    
    // Show/hide warnings based on what's configured
    if (blocksWarning) {
        blocksWarning.style.display = hasBlocks ? 'none' : 'flex';
        if (hasBlocks) {
            blocksWarning.querySelector('.fa-times-circle').className = 'fas fa-check-circle';
            blocksWarning.querySelector('.fa-check-circle').style.color = '#28a745';
            blocksWarning.style.background = '#d4edda';
            blocksWarning.style.borderLeft = '5px solid #28a745';
        }
    }
    
    if (moralettiWarning) {
        moralettiWarning.style.display = hasMoraletti ? 'none' : 'flex';
        if (hasMoraletti) {
            moralettiWarning.querySelector('.fa-times-circle').className = 'fas fa-check-circle';
            moralettiWarning.querySelector('.fa-check-circle').style.color = '#28a745';
            moralettiWarning.style.background = '#d4edda';
            moralettiWarning.style.borderLeft = '5px solid #28a745';
        }
    }
    
    // Show modal
    modal.style.display = 'flex';
    modal.style.alignItems = 'center';
    modal.style.justifyContent = 'center';
    
    // Block all interactions with the main app
    document.body.style.overflow = 'hidden';
    
    console.log(' Modal configurazione obbligatoria mostrato');
}

function hideMandatoryConfigModal() {
    const modal = document.getElementById('mandatoryConfigModal');
    if (modal) {
        modal.style.display = 'none';
        document.body.style.overflow = 'auto';
    }
}

// Check configuration status and show modal if needed
async function checkAndShowMandatoryConfig() {
    if (!window.authManager || !window.authManager.isAuthenticated()) {
        return;
    }
    
    const user = window.authManager.getCurrentUser();
    if (!user || user.is_admin) {
        return; // Admin users don't need to configure
    }
    
    const needsConfiguration = !user.has_configured_blocks || !user.has_configured_moraletti;
    
    if (needsConfiguration) {
        showMandatoryConfigModal(user.has_configured_blocks, user.has_configured_moraletti);
    }
}

// Setup event listeners when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    // Button to go to global settings
    const goToSettingsBtn = document.getElementById('goToGlobalSettingsBtn');
    if (goToSettingsBtn) {
        goToSettingsBtn.addEventListener('click', () => {
            // Navigate to library section (global settings)
            const navItem = document.querySelector('[data-section="library"]');
            if (navItem) {
                navItem.click();
            }
            
            // Hide modal temporarily (will show again if not configured)
            hideMandatoryConfigModal();
            
            // Scroll to blocks configuration
            setTimeout(() => {
                const blocksCard = document.getElementById('blockConfigCard');
                if (blocksCard) {
                    blocksCard.scrollIntoView({ behavior: 'smooth', block: 'start' });
                    
                    // Highlight the card
                    blocksCard.style.boxShadow = '0 0 25px rgba(59, 130, 246, 0.6)';
                    blocksCard.style.border = '3px solid #3B82F6';
                    
                    setTimeout(() => {
                        blocksCard.style.boxShadow = '';
                        blocksCard.style.border = '';
                    }, 3000);
                }
            }, 500);
        });
    }
    
    // Check configuration status after page load
    setTimeout(() => {
        checkAndShowMandatoryConfig();
    }, 1000);
});

// Update configuration check when user saves configurations
function onConfigurationSaved() {
    if (!window.authManager || !window.authManager.isAuthenticated()) {
        return;
    }
    
    // Refresh user profile to get updated flags
    window.authManager.fetchUserProfile().then(() => {
        const user = window.authManager.getCurrentUser();
        if (user && user.has_configured_blocks && user.has_configured_moraletti) {
            // All configurations completed
            hideMandatoryConfigModal();
            
            if (window.wallPackingApp) {
                window.wallPackingApp.showToast(
                    ' Configurazione completata! Ora puoi utilizzare l\'applicazione.',
                    'success',
                    5000
                );
            }
        } else {
            // Still missing some configurations
            showMandatoryConfigModal(user.has_configured_blocks, user.has_configured_moraletti);
        }
    });
}

console.log(' Sistema di configurazione obbligatoria inizializzato');

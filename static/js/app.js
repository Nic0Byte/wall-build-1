/**
 * Parete TAKTAK® - Frontend Application
 * Complete client-side logic for SVG processing and wall packing
 */

class WallPackingApp {
    constructor() {
        this.currentFile = null;
        this.currentSessionId = null;
        this.currentData = null;
        this.currentSection = 'app'; // Track current section
        
        // Bind methods
        this.handleFileSelect = this.handleFileSelect.bind(this);
        this.handleDragOver = this.handleDragOver.bind(this);
        this.handleDrop = this.handleDrop.bind(this);
        this.handleNavigation = this.handleNavigation.bind(this);
        
        this.init();
    }
    
    init() {
        console.log('🚀 Inizializzazione Parete TAKTAK® App');
        this.setupEventListeners();
        this.setupNavigation();
        this.showMainSection('app');
        this.showSection('upload');
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
    
    // ===== EVENT LISTENERS SETUP =====
    
    setupEventListeners() {
        // File Upload
        const fileInput = document.getElementById('fileInput');
        const uploadArea = document.getElementById('uploadArea');
        
        fileInput?.addEventListener('change', this.handleFileSelect);
        uploadArea?.addEventListener('dragover', this.handleDragOver);
        uploadArea?.addEventListener('drop', this.handleDrop);
        uploadArea?.addEventListener('dragleave', (e) => {
            e.target.classList.remove('dragover');
        });
        uploadArea?.addEventListener('click', () => {
            fileInput?.click();
        });
        
        // Remove file
        document.getElementById('removeFile')?.addEventListener('click', () => {
            this.removeFile();
        });
        
        // Configuration
        this.setupConfigurationListeners();
        
        // Process button
        document.getElementById('processBtn')?.addEventListener('click', () => {
            this.processFile();
        });
        
        // Navigation buttons
        document.getElementById('backToUpload')?.addEventListener('click', () => {
            this.showSection('upload');
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
            this.downloadResult('dxf');
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
        // Row offset slider
        const rowOffsetSlider = document.getElementById('rowOffset');
        const rowOffsetValue = document.getElementById('rowOffsetValue');
        
        rowOffsetSlider?.addEventListener('input', (e) => {
            const value = e.target.value;
            rowOffsetValue.textContent = `${value} mm`;
            this.updatePresetButtons(value);
        });
        
        // Preset buttons
        document.querySelectorAll('.preset-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const value = e.target.dataset.value;
                rowOffsetSlider.value = value;
                rowOffsetValue.textContent = `${value} mm`;
                this.updatePresetButtons(value);
            });
        });
    }
    
    updatePresetButtons(activeValue) {
        document.querySelectorAll('.preset-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.value === activeValue);
        });
    }
    
    // ===== FILE HANDLING =====
    
    handleFileSelect(e) {
        const files = e.target.files;
        if (files.length > 0) {
            this.validateAndSetFile(files[0]);
        }
    }
    
    handleDragOver(e) {
        e.preventDefault();
        e.target.classList.add('dragover');
    }
    
    handleDrop(e) {
        e.preventDefault();
        e.target.classList.remove('dragover');
        
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            this.validateAndSetFile(files[0]);
        }
    }
    
    validateAndSetFile(file) {
        // Validation - Updated to support SVG, DWG, DXF
        const fileName = file.name.toLowerCase();
        const supportedFormats = ['.svg', '.dwg', '.dxf'];
        const isValidFormat = supportedFormats.some(format => fileName.endsWith(format));
        
        if (!isValidFormat) {
            this.showToast('Formato non supportato. Usa file SVG, DWG o DXF', 'error');
            return;
        }
        
        if (file.size > 10 * 1024 * 1024) { // 10MB
            this.showToast('File troppo grande (max 10MB)', 'error');
            return;
        }
        
        if (file.size === 0) {
            this.showToast('File vuoto', 'error');
            return;
        }
        
        // Set file
        this.currentFile = file;
        this.showFileInfo(file);
        
        // Show success message and auto-progress to configuration
        this.showToast('File caricato con successo', 'success');
        
        // Auto-progress with smooth transition
        setTimeout(() => {
            this.showToast('Passaggio alla configurazione...', 'info');
            setTimeout(() => {
                this.showSection('config');
            }, 800);
        }, 1200);
    }
    
    removeFile() {
        this.currentFile = null;
        this.currentSessionId = null;
        this.currentData = null;
        
        // Reset file input
        const fileInput = document.getElementById('fileInput');
        if (fileInput) fileInput.value = '';
        
        // Hide file info
        const fileInfo = document.getElementById('fileInfo');
        if (fileInfo) fileInfo.style.display = 'none';
        
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
    }
    
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
    
    // ===== API COMMUNICATION =====
    
    async processFile() {
        if (!this.currentFile) {
            this.showToast('Nessun file selezionato', 'error');
            return;
        }
        
        // Get configuration
        const config = this.getConfiguration();
        
        // Show loading
        this.showLoading('Elaborazione in corso...', 'Analisi file CAD e calcolo packing automatico');
        
        try {
            // Prepare form data
            const formData = new FormData();
            formData.append('file', this.currentFile);
            formData.append('row_offset', config.rowOffset);
            formData.append('block_widths', config.blockWidths);
            formData.append('project_name', config.projectName);
            
            // Add color theme configuration
            const colorTheme = getCurrentColorTheme();
            formData.append('color_theme', JSON.stringify(colorTheme));
            
            // Make API call
            const response = await fetch('/api/upload', {
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
            
            // Update UI
            this.hideLoading();
            this.showResults(result);
            this.loadPreview();
            this.showSection('results');
            
            this.showToast('Packing completato con successo!', 'success');
            
        } catch (error) {
            console.error('Errore processamento:', error);
            this.hideLoading();
            this.showToast(`Errore: ${error.message}`, 'error');
        }
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
            formData.append('row_offset', config.rowOffset);
            formData.append('block_widths', config.blockWidths);
            
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
            
            this.showResults(this.currentData);
            this.loadPreview();
            
        } catch (error) {
            console.error('Errore caricamento sessione:', error);
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
        const validFormats = ['pdf', 'json', 'dxf'];
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
        // Only show sections if we're in the app section
        if (this.currentSection !== 'app') {
            return;
        }
        
        // Hide all sections
        const sections = ['uploadSection', 'configSection', 'resultsSection'];
        sections.forEach(id => {
            const element = document.getElementById(id);
            if (element) element.style.display = 'none';
        });
        
        // Show target section
        const targetSection = document.getElementById(sectionName + 'Section');
        if (targetSection) {
            targetSection.style.display = 'block';
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
        // Update header stats
        this.updateHeaderStats(data);
        
        // Update tables CON NUOVO SISTEMA RAGGRUPPAMENTO
        this.updateGroupedStandardTable(data.summary, data.blocks_standard || []);
        this.updateGroupedCustomTable(data.blocks_custom || []);
        
        // Update metrics
        this.updateMetrics(data.metrics);
        
        // Auto-save project when results are shown
        this.autoSaveProject(data);
    }
    
    updateHeaderStats(data) {
        const headerStats = document.getElementById('headerStats');
        const statStandard = document.getElementById('statStandard');
        const statCustom = document.getElementById('statCustom');
        const statEfficiency = document.getElementById('statEfficiency');
        
        if (headerStats && statStandard && statCustom && statEfficiency) {
            const totalStandard = Object.values(data.summary || {}).reduce((a, b) => a + b, 0);
            const totalCustom = (data.blocks_custom || []).length;
            const efficiency = data.metrics?.efficiency || 0;
            
            statStandard.textContent = totalStandard;
            statCustom.textContent = totalCustom;
            statEfficiency.textContent = `${Math.round(efficiency * 100)}%`;
            
            // Show stats only if we're in app section
            if (this.currentSection === 'app') {
                headerStats.style.display = 'flex';
            }
        }
    }
    
    updateGroupedStandardTable(summary, standardBlocks) {
        const tbody = document.querySelector('#standardTable tbody');
        if (!tbody) return;
        
        tbody.innerHTML = '';
        
        // Simula raggruppamento per categoria (usa i mapping esistenti per ora)
        const typeMap = {
            'std_1239x495': { name: 'Categoria A', size: '1239 × 495', category: 'A' },
            'std_826x495': { name: 'Categoria B', size: '826 × 495', category: 'B' },
            'std_413x495': { name: 'Categoria C', size: '413 × 495', category: 'C' }
        };
        
        // Raggruppa per categoria mostrando il nuovo formato
        for (const [type, count] of Object.entries(summary || {})) {
            const typeInfo = typeMap[type] || { name: `Categoria ${type}`, size: 'N/A', category: 'X' };
            
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
                        <span><strong>Categoria ${categoryLetter}</strong></span>
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
        return this.updateGroupedStandardTable(summary, []);
    }

    updateCustomTable(customBlocks) {
        console.log('⚠️ Usando funzione legacy updateCustomTable');
        return this.updateGroupedCustomTable(customBlocks);
    }
    
    updateMetrics(metrics) {
        const metricEfficiency = document.getElementById('metricEfficiency');
        const metricWaste = document.getElementById('metricWaste');
        const metricComplexity = document.getElementById('metricComplexity');
        const metricCoverage = document.getElementById('metricCoverage');
        
        if (metricEfficiency) metricEfficiency.textContent = `${Math.round((metrics?.efficiency || 0) * 100)}%`;
        if (metricWaste) metricWaste.textContent = `${Math.round((metrics?.waste_ratio || 0) * 100)}%`;
        if (metricComplexity) metricComplexity.textContent = metrics?.complexity || 0;
        if (metricCoverage) metricCoverage.textContent = `${Math.round((metrics?.total_area_coverage || 0) * 100)}%`;
    }
    
    // ===== CONFIGURATION =====
    
    getConfiguration() {
        const projectName = document.getElementById('projectName')?.value || 'Progetto Parete';
        const rowOffset = parseInt(document.getElementById('rowOffset')?.value || '826');
        const blockWidths = document.getElementById('blockWidths')?.value || '1239,826,413';
        
        return {
            projectName,
            rowOffset,
            blockWidths
        };
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
        
        const blockWidths = document.getElementById('blockWidths');
        if (blockWidths) blockWidths.value = '1239,826,413';
        
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
        
        // Show upload section and switch to app
        this.showMainSection('app');
        this.showSection('upload');
        
        // Update navigation
        document.querySelectorAll('.nav-item').forEach(item => {
            item.classList.remove('active');
            if (item.dataset.section === 'app') {
                item.classList.add('active');
            }
        });
        
        this.showToast('Applicazione ripristinata', 'info');
    }
    
    // Auto-save project when processing is complete
    autoSaveProject(data) {
        if (!this.currentFile || !data || this.projectSaved || this.isReusedProject) {
            return; // Don't save if already saved or if this is a reused project
        }
        
        // Extract project information
        const filename = this.currentFile.name;
        const projectName = filename.replace(/\.(dwg|dxf)$/i, '');
        
        // Calculate totals
        const totalStandard = Object.values(data.summary || {}).reduce((a, b) => a + b, 0);
        const totalCustom = (data.blocks_custom || []).length;
        const totalBlocks = totalStandard + totalCustom;
        
        // Get efficiency
        const efficiency = data.metrics?.efficiency ? 
            `${Math.round(data.metrics.efficiency * 100)}%` : 'N/A';
        
        // Extract wall dimensions from data if available
        const wallDimensions = data.wall_info ? 
            `${data.wall_info.width}×${data.wall_info.height}mm` : 'N/A';
        
        // Get configuration data
        const config = this.getConfiguration();
        
        // Get saved file path from session data (this comes from backend after upload)
        const savedFilePath = data.saved_file_path || '';
        console.log('💾 Percorso file salvato per progetto:', savedFilePath);
        
        // Prepare project data for saving
        const projectData = {
            name: projectName,
            filename: filename,
            file_path: savedFilePath, // This is the path where the file was saved on server
            block_dimensions: getCurrentBlockDimensions(),
            color_theme: getCurrentColorTheme(),
            packing_config: {
                row_offset: config.rowOffset,
                block_widths: config.blockWidths,
                project_name: config.projectName
            },
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
        
        // Save asynchronously (don't wait for result to avoid blocking UI)
        saveCurrentProject(projectData).catch(error => {
            console.warn('Auto-save project failed:', error);
            this.projectSaved = false; // Reset on failure to allow retry
        });
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
        `${currentDimensions.block1.width}×${currentDimensions.block1.height}×${currentDimensions.block1.depth} mm`;
    document.getElementById('activeBlock2Dims').textContent = 
        `${currentDimensions.block2.width}×${currentDimensions.block2.height}×${currentDimensions.block2.depth} mm`;
    document.getElementById('activeBlock3Dims').textContent = 
        `${currentDimensions.block3.width}×${currentDimensions.block3.height}×${currentDimensions.block3.depth} mm`;
    
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

// Open block library (switch to library section)
function openBlockLibrary() {
    console.log('📚 Opening block library');
    
    // Switch to library section
    if (window.wallPackingApp) {
        window.wallPackingApp.showSection('library');
        
        // Show toast to guide user
        setTimeout(() => {
            window.wallPackingApp.showToast('Clicca su "Dimensioni Blocchi Standard" per modificare', 'info');
        }, 500);
    }
}

// Listen for block dimension changes to update active display
function onBlockDimensionsChanged() {
    updateActiveBlocksDisplay();
    
    // Show feedback that changes are reflected
    if (window.wallPackingApp) {
        window.wallPackingApp.showToast('Blocchi aggiornati nell\'applicazione', 'success');
    }
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

// Toggle block dimensions panel
function toggleBlockDimensionsPanel() {
    const panel = document.getElementById('blockDimensionsPanel');
    const icon = document.getElementById('blockDimensionsExpandIcon');
    
    if (!panel || !icon) return;
    
    const isVisible = panel.style.display !== 'none';
    
    if (isVisible) {
        // Close panel
        panel.style.display = 'none';
        icon.classList.remove('expanded');
        console.log('📏 Block dimensions panel closed');
    } else {
        // Open panel
        panel.style.display = 'block';
        icon.classList.add('expanded');
        
        // Initialize panel if not already done
        if (!window.blockDimensionsInitialized) {
            setTimeout(() => {
                initializeBlockDimensions();
                window.blockDimensionsInitialized = true;
            }, 100);
        }
        
        console.log('📏 Block dimensions panel opened');
    }
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
            const scale = Math.min(80, maxDim / 3); // Scale to fit in 80px max
            
            const displayWidth = (width / maxDim) * scale;
            const displayHeight = (height / maxDim) * scale;
            
            previewElement.style.width = displayWidth + 'px';
            previewElement.style.height = displayHeight + 'px';
        }
    });
}

function updateBlockComparison() {
    const block1Volume = calculateBlockVolume('block1');
    const block2Volume = calculateBlockVolume('block2');
    const block3Volume = calculateBlockVolume('block3');
    
    const maxVolume = Math.max(block1Volume, block2Volume, block3Volume);
    
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
    
    if (bar && ratio) {
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
    
    console.log('✅ Block dimensions saved:', dimensions);
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
    
    // Clear localStorage
    localStorage.removeItem('blockDimensions');
    
    // Apply system defaults
    applyBlockPreset('standard');
    
    // Show confirmation
    if (window.wallPackingApp) {
        window.wallPackingApp.showToast('Ripristinate dimensioni sistema (A: 1239×495, B: 826×495, C: 413×495)', 'info');
    }
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
        const token = localStorage.getItem('access_token');
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
            
            // Determine efficiency class
            let efficiencyClass = 'efficiency-low';
            let efficiencyValue = 0;
            if (project.efficiency) {
                try {
                    efficiencyValue = parseFloat(project.efficiency.toString().replace('%', '')) || 0;
                    if (efficiencyValue >= 85) efficiencyClass = 'efficiency-high';
                    else if (efficiencyValue >= 70) efficiencyClass = 'efficiency-medium';
                } catch (effError) {
                    console.warn('Error parsing efficiency for project:', project.id, effError);
                }
            }
            
            // Safely get project name
            const projectName = project.name || project.filename || `Progetto ${project.id}`;
            
            return `
                <div class="project-item" data-project-id="${project.id}">
                    <div class="project-info">
                        <div class="project-name">${projectName}</div>
                        <div class="project-meta">
                            <span><i class="fas fa-calendar"></i> ${createdDate}</span>
                            <span><i class="fas fa-clock"></i> ${lastUsed}</span>
                            <span><i class="fas fa-expand-arrows-alt"></i> ${project.wall_dimensions || 'N/A'}</span>
                            <span><i class="fas fa-cubes"></i> ${project.total_blocks || 0} blocchi</span>
                            ${project.efficiency ? `<span class="efficiency-badge ${efficiencyClass}">
                                <i class="fas fa-chart-line"></i> ${project.efficiency}
                            </span>` : ''}
                        </div>
                    </div>
                    <div class="project-actions">
                        <button class="reuse-btn" onclick="reuseProject(${project.id}, event)">
                            <i class="fas fa-redo"></i> Riusa
                        </button>
                        <button class="delete-project-btn" onclick="deleteProject(${project.id}, event)" title="Elimina progetto">
                            <i class="fas fa-trash"></i>
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
                'Authorization': `Bearer ${localStorage.getItem('access_token')}`
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
            const blockWidthsInput = document.getElementById('blockWidths');
            if (blockWidthsInput) {
                blockWidthsInput.value = config.block_widths;
            }
        }
        
        console.log('⚙️ Configurazioni UI ripristinate');
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
                'Authorization': `Bearer ${localStorage.getItem('access_token')}`
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

// Delete Project - NO CONFIRMATION, KEEP CARD OPEN
async function deleteProject(projectId, event) {
    // Prevent event propagation to avoid closing the panel
    if (event) {
        event.stopPropagation();
        event.preventDefault();
    }
    
    try {
        const response = await fetch(`/api/v1/saved-projects/${projectId}`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('access_token')}`
            }
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        // Reload projects list BUT keep the card open
        loadPastProjects();
        
        if (window.wallPackingApp) {
            window.wallPackingApp.showToast('Progetto eliminato', 'success');
        }
        
    } catch (error) {
        console.error('Error deleting project:', error);
        if (window.wallPackingApp) {
            window.wallPackingApp.showToast('Errore nell\'eliminazione progetto', 'error');
        }
    }
}

// Refresh Past Projects
function refreshPastProjects() {
    loadPastProjects();
}

// Save Current Project (called when project is completed)
async function saveCurrentProject(projectData) {
    if (!projectData || !projectData.name) {
        console.warn('Cannot save project: missing project data or name');
        return false;
    }
    
    try {
        // Add session_id to access file bytes on server
        const saveData = {
            session_id: window.wallPackingApp ? window.wallPackingApp.currentSessionId : null,
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
        
        console.log('💾 Salvando progetto con session_id:', saveData.session_id);
        
        const response = await fetch('/api/v1/saved-projects/save', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('access_token')}`
            },
            body: JSON.stringify(saveData)
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (window.wallPackingApp) {
            window.wallPackingApp.showToast('Progetto salvato per riutilizzo futuro!', 'success');
        }
        
        return true;
        
    } catch (error) {
        console.error('Error saving project:', error);
        if (window.wallPackingApp) {
            window.wallPackingApp.showToast('Errore nel salvataggio progetto', 'error');
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
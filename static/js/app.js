/**
 * Costruttore Pareti - Frontend Application
 * Complete client-side logic for SVG processing and wall packing
 */

class WallPackingApp {
    constructor() {
        this.currentFile = null;
        this.currentSessionId = null;
        this.currentData = null;
        
        // Bind methods
        this.handleFileSelect = this.handleFileSelect.bind(this);
        this.handleDragOver = this.handleDragOver.bind(this);
        this.handleDrop = this.handleDrop.bind(this);
        
        this.init();
    }
    
    init() {
        console.log('🚀 Inizializzazione Wall Packing App');
        this.setupEventListeners();
        this.showSection('upload');
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
        // Validation
        if (!file.name.toLowerCase().endsWith('.svg')) {
            this.showToast('Solo file SVG sono supportati', 'error');
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
        this.showSection('config');
        
        this.showToast('File caricato con successo', 'success');
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
    
    showFileInfo(file) {
        const fileInfo = document.getElementById('fileInfo');
        const fileName = document.getElementById('fileName');
        const fileMeta = document.getElementById('fileMeta');
        
        if (fileInfo && fileName && fileMeta) {
            fileName.textContent = file.name;
            fileMeta.textContent = `${this.formatFileSize(file.size)} • ${file.type || 'SVG'}`;
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
        this.showLoading('Elaborazione in corso...', 'Analisi file SVG e calcolo packing automatico');
        
        try {
            // Prepare form data
            const formData = new FormData();
            formData.append('file', this.currentFile);
            formData.append('row_offset', config.rowOffset);
            formData.append('block_widths', config.blockWidths);
            formData.append('project_name', config.projectName);
            
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
                processBtn.innerHTML = '<span class="btn-icon">⚙️</span> Ricalcola Packing';
                processBtn.onclick = () => this.reconfigureAndProcess();
            }
        } else if (sectionName === 'config') {
            // Reset to normal process button
            const processBtn = document.getElementById('processBtn');
            if (processBtn) {
                processBtn.innerHTML = '<span class="btn-icon">⚙️</span> Calcola Packing';
                processBtn.onclick = () => this.processFile();
            }
        }
    }
    
    showResults(data) {
        // Update header stats
        this.updateHeaderStats(data);
        
        // Update tables
        this.updateStandardTable(data.summary);
        this.updateCustomTable(data.blocks_custom || []);
        
        // Update metrics
        this.updateMetrics(data.metrics);
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
            
            headerStats.style.display = 'flex';
        }
    }
    
    updateStandardTable(summary) {
        const tbody = document.querySelector('#standardTable tbody');
        if (!tbody) return;
        
        tbody.innerHTML = '';
        
        // Block type mappings
        const typeMap = {
            'std_1239x495': { name: 'Tipo A (Grande)', size: '1239 × 495' },
            'std_826x495': { name: 'Tipo B (Medio)', size: '826 × 495' },
            'std_413x495': { name: 'Tipo C (Piccolo)', size: '413 × 495' }
        };
        
        for (const [type, count] of Object.entries(summary || {})) {
            const typeInfo = typeMap[type] || { name: type, size: 'N/A' };
            
            const row = document.createElement('tr');
            row.innerHTML = `
                <td><strong>${typeInfo.name}</strong></td>
                <td class="text-center">${count}</td>
                <td>${typeInfo.size} mm</td>
            `;
            tbody.appendChild(row);
        }
        
        if (Object.keys(summary || {}).length === 0) {
            const row = document.createElement('tr');
            row.innerHTML = '<td colspan="3" class="text-center text-gray-500">Nessun blocco standard</td>';
            tbody.appendChild(row);
        }
    }
    
    updateCustomTable(customBlocks) {
        const tbody = document.querySelector('#customTable tbody');
        if (!tbody) return;
        
        tbody.innerHTML = '';
        
        customBlocks.forEach((block, index) => {
            const row = document.createElement('tr');
            const ctypeDisplay = block.ctype === 1 ? 'CU1' : block.ctype === 2 ? 'CU2' : 'CUX';
            
            row.innerHTML = `
                <td>CU${block.ctype}(${index + 1})</td>
                <td class="text-center">${ctypeDisplay}</td>
                <td>${Math.round(block.width)} × ${Math.round(block.height)} mm</td>
            `;
            tbody.appendChild(row);
        });
        
        if (customBlocks.length === 0) {
            const row = document.createElement('tr');
            row.innerHTML = '<td colspan="3" class="text-center text-gray-500">Nessun pezzo custom</td>';
            tbody.appendChild(row);
        }
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
        toast.textContent = message;
        
        container.appendChild(toast);
        
        // Auto remove
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, duration);
    }
    
    // ===== RESET =====
    
    resetApp() {
        this.currentFile = null;
        this.currentSessionId = null;
        this.currentData = null;
        
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
            processBtn.innerHTML = '<span class="btn-icon">⚙️</span> Calcola Packing';
            processBtn.onclick = () => this.processFile();
        }
        
        // Show upload section
        this.showSection('upload');
        
        this.showToast('Applicazione ripristinata', 'info');
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
    console.log('🎯 DOM Content Loaded');
    
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
    
    console.log('✅ Wall Packing App initialized successfully');
});
/**
 * SMART LOADING SYSTEM 3D
 * Sistema loading universale con animazioni 3D mattoncini
 * Auto-rileva operazioni lente e mostra loading personalizzato
 */

class SmartLoadingSystem {
    constructor() {
        this.isActive = false;
        this.currentOperation = null;
        this.startTime = null;
        this.progressInterval = null;
        this.cancelCallback = null;
        this.isFinishing = false; // NUOVO: Previene chiamate multiple di finish()
        
        // Soglie di attivazione per tipo operazione (ms)
        this.loadingThresholds = {
            fileUpload: 500,
            dwgConversion: 200,      // 🚀 OTTIMIZZATO: Era 1000ms, ora 200ms
            sessionLoad: 400,
            export: 800,
            parsing: 600,
            packing: 300,
            generic: 800
        };
        
        // Profili di progresso per diverse operazioni
        this.progressProfiles = {
            dwgConversion: [
                { step: "🔄 Conversione DWG→DXF", duration: 85, message: "Elaborazione file CAD con ODA..." },
                { step: "📐 Parsing geometrie", duration: 10, message: "Analisi forme e strutture..." },
                { step: "🧱 Calcolo ottimizzazione", duration: 3, message: "Organizzazione blocchi..." },
                { step: "✅ Finalizzazione", duration: 2, message: "Completamento..." }
            ],
            
            fileUpload: [
                { step: "📤 Upload in corso", duration: 70, message: "Trasferimento file..." },
                { step: "🔍 Validazione file", duration: 20, message: "Controllo formato..." },
                { step: "⚙️ Preparazione", duration: 10, message: "Inizializzazione..." }
            ],
            
            sessionLoad: [
                { step: "📂 Caricamento progetto", duration: 60, message: "Recupero dati..." },
                { step: "🔧 Ripristino stato", duration: 30, message: "Ricostruzione interfaccia..." },
                { step: "✅ Completamento", duration: 10, message: "Finalizzazione..." }
            ],
            
            export: [
                { step: "📋 Preparazione export", duration: 20, message: "Organizzazione dati..." },
                { step: "🎨 Generazione contenuto", duration: 60, message: "Creazione file..." },
                { step: "💾 Salvataggio", duration: 20, message: "Scrittura file..." }
            ],
            
            generic: [
                { step: "⏳ Elaborazione", duration: 80, message: "Operazione in corso..." },
                { step: "✅ Completamento", duration: 20, message: "Finalizzazione..." }
            ]
        };
        
        this.init();
    }
    
    init() {
        this.createLoadingHTML();
        this.setupInterceptors();
        this.detectPlatform();
    }
    
    detectPlatform() {
        const userAgent = navigator.userAgent.toLowerCase();
        this.isLinux = userAgent.includes('linux');
        this.isWindows = userAgent.includes('windows');
        this.isMac = userAgent.includes('mac');
    }
    
    createLoadingHTML() {
        const loadingHTML = `
            <div id="smartLoadingOverlay" class="smart-loading-overlay">
                <div class="loading-container-3d">
                    <!-- Particelle animate -->
                    <div class="particles">
                        <div class="particle"></div>
                        <div class="particle"></div>
                        <div class="particle"></div>
                        <div class="particle"></div>
                        <div class="particle"></div>
                    </div>
                    
                    <!-- Animazione 3D Mattoncini -->
                    <div class="wall-animation-3d">
                        <div class="brick-row">
                            <div class="brick"></div>
                            <div class="brick"></div>
                            <div class="brick"></div>
                        </div>
                        <div class="brick-row offset">
                            <div class="brick"></div>
                            <div class="brick"></div>
                            <div class="brick"></div>
                        </div>
                    </div>
                    
                    <!-- Progress Bar Realistica -->
                    <div class="progress-container-3d">
                        <div class="progress-header">
                            <span class="current-step" id="currentStepText">🔄 Caricamento...</span>
                            <span class="progress-percent" id="progressPercent">0%</span>
                        </div>
                        <div class="progress-bar-3d">
                            <div class="progress-fill-3d" id="progressFill"></div>
                        </div>
                        <div class="estimated-time">
                            ⏱️ Tempo stimato: <span class="time-value" id="estimatedTime">calcolando...</span>
                        </div>
                    </div>
                    
                    <!-- Messaggio TAKTAK® -->
                    <div class="taktak-message">
                        ⚡ La tecnologia TAKTAK® sta elaborando...
                    </div>
                    
                    <!-- Pulsante Cancel -->
                    <button class="cancel-btn-3d" id="cancelBtn" onclick="smartLoading.cancel()">
                        ❌ Annulla Operazione
                    </button>
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', loadingHTML);
        
        // References agli elementi
        this.overlay = document.getElementById('smartLoadingOverlay');
        this.stepText = document.getElementById('currentStepText');
        this.progressPercent = document.getElementById('progressPercent');
        this.progressFill = document.getElementById('progressFill');
        this.estimatedTime = document.getElementById('estimatedTime');
        this.cancelBtn = document.getElementById('cancelBtn');
    }
    
    setupInterceptors() {
        // Intercetta fetch requests
        const originalFetch = window.fetch;
        window.fetch = (...args) => {
            const request = originalFetch.apply(window, args);
            this.monitorRequest(request, args[0]);
            return request;
        };
        
        // Intercetta XMLHttpRequest
        const originalOpen = XMLHttpRequest.prototype.open;
        XMLHttpRequest.prototype.open = function(...args) {
            this._startTime = Date.now();
            this._url = args[1];
            return originalOpen.apply(this, args);
        };
        
        const originalSend = XMLHttpRequest.prototype.send;
        XMLHttpRequest.prototype.send = function(...args) {
            const xhr = this;
            const startTime = Date.now();
            
            // Timeout per attivare loading
            const loadingTimeout = setTimeout(() => {
                const operationType = smartLoading.detectOperationType(xhr._url);
                smartLoading.start(operationType, { 
                    url: xhr._url,
                    method: 'xhr'
                });
            }, smartLoading.getThreshold('generic'));
            
            // Cleanup al termine
            const cleanup = () => {
                clearTimeout(loadingTimeout);
                if (smartLoading.isActive) {
                    smartLoading.finish();
                }
            };
            
            xhr.addEventListener('load', cleanup);
            xhr.addEventListener('error', cleanup);
            xhr.addEventListener('abort', cleanup);
            
            return originalSend.apply(this, args);
        };
    }
    
    monitorRequest(request, url) {
        const startTime = Date.now();
        const operationType = this.detectOperationType(url);
        const threshold = this.getThreshold(operationType);
        
        // Timeout per attivare loading
        const loadingTimeout = setTimeout(() => {
            this.start(operationType, { 
                url: url,
                method: 'fetch'
            });
        }, threshold);
        
        // Cleanup al termine
        request.finally(() => {
            clearTimeout(loadingTimeout);
            if (this.isActive) {
                this.finish();
            }
        });
    }
    
    detectOperationType(url) {
        if (!url) return 'generic';
        
        const urlStr = url.toString().toLowerCase();
        
        if (urlStr.includes('upload') || urlStr.includes('file')) {
            return 'fileUpload';
        } else if (urlStr.includes('convert') || urlStr.includes('dwg') || urlStr.includes('dxf')) {
            return 'dwgConversion';
        } else if (urlStr.includes('session') || urlStr.includes('load') || urlStr.includes('restore')) {
            return 'sessionLoad';
        } else if (urlStr.includes('export') || urlStr.includes('download')) {
            return 'export';
        } else if (urlStr.includes('parse') || urlStr.includes('analyze')) {
            return 'parsing';
        } else if (urlStr.includes('pack') || urlStr.includes('optimize')) {
            return 'packing';
        }
        
        return 'generic';
    }
    
    getThreshold(operationType) {
        return this.loadingThresholds[operationType] || this.loadingThresholds.generic;
    }
    
    start(operationType = 'generic', options = {}) {
        if (this.isActive) return;
        
        this.isActive = true;
        this.currentOperation = operationType;
        this.startTime = Date.now();
        
        // NUOVO: Supporto per durata forzata
        this.forcedDuration = options.forceDuration || null;
        
        // Mostra overlay
        this.overlay.classList.add('active');
        
        // Avvia animazione progresso
        this.startProgressAnimation(operationType);
        
        // Setup cancel callback
        this.cancelCallback = options.onCancel;
        
        console.log(`🔄 Smart Loading attivato: ${operationType}${this.forcedDuration ? ` (durata forzata: ${this.forcedDuration}ms)` : ''}`);
    }
    
    startProgressAnimation(operationType) {
        const profile = this.progressProfiles[operationType] || this.progressProfiles.generic;
        let currentStepIndex = 0;
        let currentProgress = 0;
        
        // Calcola durata totale stimata
        let totalEstimatedTime;
        
        if (this.forcedDuration) {
            // NUOVO: Usa durata forzata se specificata
            totalEstimatedTime = this.forcedDuration;
            console.log(`⏱️ Usando durata forzata: ${totalEstimatedTime}ms (${(totalEstimatedTime/1000).toFixed(1)}s)`);
        } else {
            // Calcolo normale basato su profilo
            const baseTime = profile.reduce((sum, step) => sum + step.duration, 0) * 100; // ms base
            const platformMultiplier = this.isLinux ? 5.0 : (this.isWindows ? 1.0 : 1.2); // 🚀 OTTIMIZZATO: Linux molto più lento (30s+)
            totalEstimatedTime = Math.round(baseTime * platformMultiplier);
        }
        
        this.updateEstimatedTime(totalEstimatedTime);
        
        const updateProgress = () => {
            if (!this.isActive) return;
            
            const currentStep = profile[currentStepIndex];
            if (!currentStep) {
                this.finish();
                return;
            }
            
            // Aggiorna step corrente
            this.stepText.textContent = currentStep.step;
            
            // Calcola progresso
            const stepProgress = Math.min(100, currentProgress + (currentStep.duration / profile.length));
            currentProgress = stepProgress;
            
            this.updateProgress(Math.round(stepProgress));
            
            // Aggiorna tempo rimanente
            const elapsed = Date.now() - this.startTime;
            const remaining = Math.max(0, totalEstimatedTime - elapsed);
            this.updateEstimatedTime(remaining);
            
            // Passa al prossimo step
            if (stepProgress >= (currentStepIndex + 1) * (100 / profile.length)) {
                currentStepIndex++;
            }
        };
        
        this.progressInterval = setInterval(updateProgress, 150);
        updateProgress(); // Prima esecuzione immediata
    }
    
    updateProgress(percentage) {
        this.progressPercent.textContent = `${percentage}%`;
        this.progressFill.style.width = `${percentage}%`;
    }
    
    updateEstimatedTime(remainingMs) {
        if (remainingMs <= 0) {
            this.estimatedTime.textContent = 'completamento...';
            return;
        }
        
        if (remainingMs < 1000) {
            this.estimatedTime.textContent = `${remainingMs}ms`;
        } else if (remainingMs < 60000) {
            const seconds = Math.ceil(remainingMs / 1000);
            this.estimatedTime.textContent = `${seconds}s`;
        } else {
            const minutes = Math.floor(remainingMs / 60000);
            const seconds = Math.ceil((remainingMs % 60000) / 1000);
            this.estimatedTime.textContent = `${minutes}m ${seconds}s`;
        }
    }
    
    formatFileSize(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    }
    
    finish() {
        if (!this.isActive) {
            console.log('⚠️ finish() chiamato ma loading non attivo, ignorando');
            return;
        }
        
        if (this.isFinishing) {
            console.log('⚠️ finish() già in corso, ignorando chiamata multipla');
            return;
        }
        
        // NUOVO: Marca che stiamo finendo per evitare chiamate multiple
        this.isFinishing = true;
        
        console.log(`🏁 Iniziando finish() per operazione: ${this.currentOperation}`);
        
        // NUOVO: Gestione durata minima forzata
        if (this.forcedDuration) {
            const elapsedTime = Date.now() - this.startTime;
            const remainingTime = Math.max(0, this.forcedDuration - elapsedTime);
            
            if (remainingTime > 0) {
                console.log(`⏱️ Durata forzata: aspetto ${remainingTime}ms prima di terminare`);
                
                // Aspetta il tempo rimanente prima di terminare
                setTimeout(() => {
                    this.finishInternal();
                }, remainingTime);
                return;
            }
        }
        
        // Termina immediatamente se non c'è durata forzata o è già scaduta
        this.finishInternal();
    }
    
    finishInternal() {
        if (!this.isActive) return;
        
        this.isActive = false;
        
        // Animazione completamento
        this.updateProgress(100);
        this.stepText.textContent = '✅ Completato!';
        this.estimatedTime.textContent = 'fatto!';
        
        // Clear interval
        if (this.progressInterval) {
            clearInterval(this.progressInterval);
            this.progressInterval = null;
        }
        
        // Nascondi overlay dopo breve pausa
        setTimeout(() => {
            this.overlay.classList.remove('active');
            this.reset();
        }, 800);
        
        console.log(`✅ Smart Loading completato: ${this.currentOperation}`);
    }
    
    cancel() {
        if (!this.isActive) return;
        
        if (this.cancelCallback && typeof this.cancelCallback === 'function') {
            this.cancelCallback();
        }
        
        this.stepText.textContent = '❌ Operazione annullata';
        this.updateProgress(0);
        
        setTimeout(() => {
            this.overlay.classList.remove('active');
            this.reset();
        }, 1000);
        
        console.log(`❌ Smart Loading annullato: ${this.currentOperation}`);
    }
    
    reset() {
        this.currentOperation = null;
        this.startTime = null;
        this.cancelCallback = null;
        this.forcedDuration = null; // NUOVO: Reset durata forzata
        this.isFinishing = false; // NUOVO: Reset flag finishing
        
        // Reset UI
        this.stepText.textContent = '🔄 Caricamento...';
        this.progressPercent.textContent = '0%';
        this.progressFill.style.width = '0%';
        this.estimatedTime.textContent = 'calcolando...';
    }
    
    // API pubblica per utilizzo manuale
    showForOperation(operationType, options = {}) {
        this.start(operationType, options);
    }
    
    hide() {
        const caller = new Error().stack.split('\n')[2]?.trim() || 'unknown';
        console.log(`🔍 hide() chiamato da: ${caller}`, {
            isActive: this.isActive,
            isFinishing: this.isFinishing,
            operation: this.currentOperation
        });
        this.finish();
    }
}

// Inizializza sistema globale
const smartLoading = new SmartLoadingSystem();

// Export per utilizzo in altri script
window.smartLoading = smartLoading;

console.log('🚀 Smart Loading System 3D inizializzato');
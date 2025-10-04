// Sistema di Autenticazione JavaScript per Wall-Build
// Gestisce tokens JWT, login automatico, sessioni sicure

class AuthManager {
    constructor() {
        // CAMBIATO: Usa sessionStorage invece di localStorage
        // In questo modo il token viene cancellato alla chiusura del browser
        this.token = sessionStorage.getItem('access_token');
        this.tokenType = sessionStorage.getItem('token_type') || 'bearer';
        this.apiBase = window.location.origin;
        this.currentUser = null;
        
        // Configurazione timeout inattività (30 minuti di default)
        this.inactivityTimeout = 30 * 60 * 1000; // 30 minuti in millisecondi
        this.inactivityTimer = null;
        this.lastActivity = Date.now();
        
        // Setup interceptor per richieste automatiche
        this.setupRequestInterceptor();
        
        // Setup monitoraggio inattività
        this.setupInactivityMonitor();
        
        // Setup listener per chiusura finestra
        this.setupWindowCloseListener();
        
        // Verifica token all'avvio
        this.verifyToken();
    }

    // ────────────────────────────────────────────────────────────────────────────
    // Gestione Token
    // ────────────────────────────────────────────────────────────────────────────

    getAuthHeaders() {
        if (!this.token) return {};
        return {
            'Authorization': `Bearer ${this.token}`,
            'Content-Type': 'application/json'
        };
    }

    setToken(token, tokenType = 'bearer') {
        this.token = token;
        this.tokenType = tokenType;
        // CAMBIATO: Usa sessionStorage invece di localStorage
        sessionStorage.setItem('access_token', token);
        sessionStorage.setItem('token_type', tokenType);
        
        // Resetta il timer di inattività quando si imposta un nuovo token
        this.resetInactivityTimer();
    }

    clearToken() {
        this.token = null;
        this.tokenType = null;
        this.currentUser = null;
        // CAMBIATO: Usa sessionStorage invece di localStorage
        sessionStorage.removeItem('access_token');
        sessionStorage.removeItem('token_type');
        sessionStorage.removeItem('user_data');
        
        // Pulisci anche eventuali dati in localStorage (migrazione da vecchia versione)
        localStorage.removeItem('access_token');
        localStorage.removeItem('token_type');
        localStorage.removeItem('user_data');
        
        // Ferma il timer di inattività
        if (this.inactivityTimer) {
            clearTimeout(this.inactivityTimer);
            this.inactivityTimer = null;
        }
    }

    // ────────────────────────────────────────────────────────────────────────────
    // Autenticazione
    // ────────────────────────────────────────────────────────────────────────────

    async login(username, password) {
        try {
            const response = await fetch(`${this.apiBase}/api/v1/auth/login`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ username, password })
            });

            const data = await response.json();

            if (response.ok) {
                this.setToken(data.access_token, data.token_type);
                await this.fetchUserProfile();
                return { success: true, data };
            } else {
                return { success: false, error: data.detail || 'Errore di login' };
            }
        } catch (error) {
            console.error('Errore login:', error);
            return { success: false, error: 'Errore di connessione' };
        }
    }

    async register(userData) {
        try {
            const response = await fetch(`${this.apiBase}/api/v1/auth/register`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(userData)
            });

            const data = await response.json();

            if (response.ok) {
                return { success: true, data };
            } else {
                return { success: false, error: data.detail || 'Errore di registrazione' };
            }
        } catch (error) {
            console.error('Errore registrazione:', error);
            return { success: false, error: 'Errore di connessione' };
        }
    }

    async logout() {
        try {
            if (this.token) {
                await fetch(`${this.apiBase}/api/v1/auth/logout`, {
                    method: 'POST',
                    headers: this.getAuthHeaders()
                });
            }
        } catch (error) {
            console.error('Errore logout:', error);
        } finally {
            this.clearToken();
            window.location.href = '/login';
        }
    }

    // ────────────────────────────────────────────────────────────────────────────
    // Verifica e Gestione Utente
    // ────────────────────────────────────────────────────────────────────────────

    async verifyToken() {
        if (!this.token) {
            this.redirectToLogin();
            return false;
        }

        try {
            const response = await fetch(`${this.apiBase}/api/v1/auth/me`, {
                headers: this.getAuthHeaders()
            });

            if (response.ok) {
                this.currentUser = await response.json();
                // CAMBIATO: Usa sessionStorage invece di localStorage
                sessionStorage.setItem('user_data', JSON.stringify(this.currentUser));
                return true;
            } else {
                this.clearToken();
                this.redirectToLogin();
                return false;
            }
        } catch (error) {
            console.error('Errore verifica token:', error);
            this.clearToken();
            this.redirectToLogin();
            return false;
        }
    }

    async fetchUserProfile() {
        try {
            const response = await fetch(`${this.apiBase}/api/v1/auth/me`, {
                headers: this.getAuthHeaders()
            });

            if (response.ok) {
                this.currentUser = await response.json();
                // CAMBIATO: Usa sessionStorage invece di localStorage
                sessionStorage.setItem('user_data', JSON.stringify(this.currentUser));
                return this.currentUser;
            }
        } catch (error) {
            console.error('Errore fetch profilo:', error);
        }
        return null;
    }

    getCurrentUser() {
        if (this.currentUser) return this.currentUser;
        
        // CAMBIATO: Usa sessionStorage invece di localStorage
        const userData = sessionStorage.getItem('user_data');
        if (userData) {
            try {
                this.currentUser = JSON.parse(userData);
                return this.currentUser;
            } catch {
                sessionStorage.removeItem('user_data');
            }
        }
        return null;
    }

    // ────────────────────────────────────────────────────────────────────────────
    // Richieste API Sicure
    // ────────────────────────────────────────────────────────────────────────────

    async makeAuthenticatedRequest(url, options = {}) {
        if (!this.token) {
            this.redirectToLogin();
            return null;
        }

        const headers = {
            ...this.getAuthHeaders(),
            ...(options.headers || {})
        };

        try {
            const response = await fetch(url, {
                ...options,
                headers
            });

            // Se unauthorized, prova refresh o redirect
            if (response.status === 401) {
                this.clearToken();
                this.redirectToLogin();
                return null;
            }

            return response;
        } catch (error) {
            console.error('Errore richiesta autenticata:', error);
            return null;
        }
    }

    // Upload file con autenticazione
    async uploadFile(file, additionalData = {}) {
        if (!this.token) {
            this.redirectToLogin();
            return null;
        }

        try {
            const formData = new FormData();
            formData.append('file', file);
            
            // Aggiungi dati aggiuntivi
            Object.keys(additionalData).forEach(key => {
                formData.append(key, additionalData[key]);
            });

            const response = await fetch(`${this.apiBase}/api/upload`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${this.token}`
                    // Non impostare Content-Type per FormData
                },
                body: formData
            });

            if (response.status === 401) {
                this.clearToken();
                this.redirectToLogin();
                return null;
            }

            return response;
        } catch (error) {
            console.error('Errore upload file:', error);
            return null;
        }
    }

    // ────────────────────────────────────────────────────────────────────────────
    // Utilità UI
    // ────────────────────────────────────────────────────────────────────────────

    redirectToLogin() {
        if (window.location.pathname !== '/login') {
            window.location.href = '/login';
        }
    }

    isAuthenticated() {
        return !!(this.token && this.getCurrentUser());
    }

    updateUserInterface() {
        const user = this.getCurrentUser();
        if (!user) return;

        // Aggiorna elementi UI con info utente
        const userNameElements = document.querySelectorAll('[data-user-name]');
        userNameElements.forEach(el => {
            el.textContent = user.full_name || user.username;
        });

        const userEmailElements = document.querySelectorAll('[data-user-email]');
        userEmailElements.forEach(el => {
            el.textContent = user.email;
        });

        const userCompanyElements = document.querySelectorAll('[data-user-company]');
        userCompanyElements.forEach(el => {
            el.textContent = user.company || '-';
        });

        // Mostra/nasconde elementi admin
        const adminElements = document.querySelectorAll('[data-admin-only]');
        adminElements.forEach(el => {
            el.style.display = user.is_admin ? 'block' : 'none';
        });
    }

    // ────────────────────────────────────────────────────────────────────────────
    // Interceptor per richieste automatiche
    // ────────────────────────────────────────────────────────────────────────────

    setupRequestInterceptor() {
        // Intercetta tutte le fetch per aggiungere automaticamente l'auth
        const originalFetch = window.fetch;
        const authManager = this;

        window.fetch = function(url, options = {}) {
            // Se la richiesta è verso le API e abbiamo un token
            if (typeof url === 'string' && 
                (url.startsWith('/api/') || url.includes('/api/')) && 
                authManager.token &&
                !options.headers?.Authorization) {
                
                options.headers = {
                    ...options.headers,
                    'Authorization': `Bearer ${authManager.token}`
                };
            }

            return originalFetch.call(this, url, options).then(response => {
                // Se risposta 401, gestisci automaticamente
                if (response.status === 401 && authManager.token) {
                    authManager.clearToken();
                    authManager.redirectToLogin();
                }
                return response;
            });
        };
    }

    // ────────────────────────────────────────────────────────────────────────────
    // Gestione Errori e Toast
    // ────────────────────────────────────────────────────────────────────────────

    showToast(message, type = 'info') {
        // Crea toast notification
        const toast = document.createElement('div');
        toast.className = `auth-toast auth-toast-${type}`;
        toast.innerHTML = `
            <div class="auth-toast-content">
                <i class="fas fa-${this.getToastIcon(type)}"></i>
                <span>${message}</span>
                <button class="auth-toast-close" onclick="this.parentElement.parentElement.remove()">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `;

        // Aggiungi stili se non esistono
        if (!document.querySelector('#auth-toast-styles')) {
            const styles = document.createElement('style');
            styles.id = 'auth-toast-styles';
            styles.textContent = `
                .auth-toast {
                    position: fixed;
                    top: 20px;
                    right: 20px;
                    background: white;
                    border-radius: 8px;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
                    padding: 16px;
                    z-index: 10000;
                    max-width: 400px;
                    animation: slideIn 0.3s ease;
                }
                .auth-toast-success { border-left: 4px solid #10b981; }
                .auth-toast-error { border-left: 4px solid #ef4444; }
                .auth-toast-warning { border-left: 4px solid #f59e0b; }
                .auth-toast-info { border-left: 4px solid #3b82f6; }
                .auth-toast-content { display: flex; align-items: center; gap: 12px; }
                .auth-toast-close { background: none; border: none; cursor: pointer; color: #6b7280; }
                @keyframes slideIn { from { transform: translateX(100%); } to { transform: translateX(0); } }
            `;
            document.head.appendChild(styles);
        }

        document.body.appendChild(toast);

        // Rimuovi automaticamente dopo 5 secondi
        setTimeout(() => {
            if (toast.parentElement) {
                toast.remove();
            }
        }, 5000);
    }

    getToastIcon(type) {
        switch (type) {
            case 'success': return 'check-circle';
            case 'error': return 'exclamation-circle';
            case 'warning': return 'exclamation-triangle';
            default: return 'info-circle';
        }
    }

    // ────────────────────────────────────────────────────────────────────────────
    // Gestione Inattività e Sessione
    // ────────────────────────────────────────────────────────────────────────────

    /**
     * Setup monitoraggio inattività utente
     * Esegue logout automatico dopo periodo di inattività
     */
    setupInactivityMonitor() {
        // Eventi che indicano attività dell'utente
        const activityEvents = [
            'mousedown', 'mousemove', 'keypress', 
            'scroll', 'touchstart', 'click'
        ];

        // Handler per registrare attività
        const handleActivity = () => {
            this.lastActivity = Date.now();
            this.resetInactivityTimer();
        };

        // Registra listener per tutti gli eventi di attività
        activityEvents.forEach(eventName => {
            document.addEventListener(eventName, handleActivity, true);
        });

        // Avvia il timer iniziale
        this.resetInactivityTimer();

        console.log(`🕐 Monitoraggio inattività attivo (timeout: ${this.inactivityTimeout / 60000} minuti)`);
    }

    /**
     * Resetta il timer di inattività
     */
    resetInactivityTimer() {
        // Pulisci il timer esistente
        if (this.inactivityTimer) {
            clearTimeout(this.inactivityTimer);
        }

        // Solo se abbiamo un token attivo
        if (this.token) {
            // Imposta nuovo timer
            this.inactivityTimer = setTimeout(() => {
                this.handleInactivityTimeout();
            }, this.inactivityTimeout);
        }
    }

    /**
     * Gestisce il timeout per inattività
     */
    handleInactivityTimeout() {
        console.warn('⚠️ Timeout inattività - Esecuzione logout automatico');
        
        // Mostra notifica all'utente
        this.showToast(
            'Sessione scaduta per inattività. Verrai reindirizzato al login.',
            'warning'
        );

        // Esegui logout dopo 2 secondi per dare tempo di vedere il messaggio
        setTimeout(() => {
            this.logout();
        }, 2000);
    }

    /**
     * Configura listener per chiusura finestra/tab
     * Questo garantisce che i dati vengano puliti alla chiusura
     */
    setupWindowCloseListener() {
        window.addEventListener('beforeunload', () => {
            // sessionStorage si pulisce automaticamente, 
            // ma possiamo fare cleanup aggiuntivo se necessario
            console.log('🚪 Chiusura finestra - La sessione verrà cancellata');
        });

        // Gestione visibilità pagina (tab nascosta/visibile)
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                console.log('👁️ Tab nascosta - Pausa monitoraggio attività');
            } else {
                console.log('👁️ Tab visibile - Ripresa monitoraggio attività');
                this.resetInactivityTimer();
            }
        });
    }

    /**
     * Ottiene il tempo rimanente prima del logout per inattività (in secondi)
     */
    getTimeUntilInactivityLogout() {
        if (!this.token) return 0;
        
        const elapsed = Date.now() - this.lastActivity;
        const remaining = this.inactivityTimeout - elapsed;
        
        return Math.max(0, Math.floor(remaining / 1000));
    }
}

// Inizializza il sistema di autenticazione
window.authManager = new AuthManager();

// Export per moduli ES6 se supportato
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AuthManager;
}

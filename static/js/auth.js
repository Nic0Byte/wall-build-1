// Sistema di Autenticazione JavaScript per Wall-Build
// Gestisce tokens JWT, login automatico, sessioni sicure

class AuthManager {
    constructor() {
        this.token = localStorage.getItem('access_token');
        this.tokenType = localStorage.getItem('token_type') || 'bearer';
        this.apiBase = window.location.origin;
        this.currentUser = null;
        
        // Setup interceptor per richieste automatiche
        this.setupRequestInterceptor();
        
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
        localStorage.setItem('access_token', token);
        localStorage.setItem('token_type', tokenType);
    }

    clearToken() {
        this.token = null;
        this.tokenType = null;
        this.currentUser = null;
        localStorage.removeItem('access_token');
        localStorage.removeItem('token_type');
        localStorage.removeItem('user_data');
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
                localStorage.setItem('user_data', JSON.stringify(this.currentUser));
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
                localStorage.setItem('user_data', JSON.stringify(this.currentUser));
                return this.currentUser;
            }
        } catch (error) {
            console.error('Errore fetch profilo:', error);
        }
        return null;
    }

    getCurrentUser() {
        if (this.currentUser) return this.currentUser;
        
        const userData = localStorage.getItem('user_data');
        if (userData) {
            try {
                this.currentUser = JSON.parse(userData);
                return this.currentUser;
            } catch {
                localStorage.removeItem('user_data');
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
}

// Inizializza il sistema di autenticazione
window.authManager = new AuthManager();

// Export per moduli ES6 se supportato
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AuthManager;
}

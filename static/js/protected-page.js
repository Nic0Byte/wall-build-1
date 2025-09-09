/**
 * 🔐 HELPER PER PAGINE PROTETTE
 * 
 * Include questo script in tutte le pagine che richiedono autenticazione.
 * Si occupa automaticamente di verificare l'accesso e aggiunge funzionalità comuni.
 */

(function() {
    'use strict';

    // Aspetta che il DOM e l'AuthManager siano pronti
    function initProtectedPage() {
        // Verifica che AuthManager sia disponibile
        if (!window.authManager) {
            console.error('❌ AuthManager non disponibile - includere auth.js prima di protected-page.js');
            setTimeout(initProtectedPage, 100); // Riprova dopo 100ms
            return;
        }

        // Verifica autenticazione
        if (!isUserAuthenticated()) {
            redirectToLogin();
            return;
        }

        // Inizializza funzionalità per pagine protette
        setupProtectedPageFeatures();
    }

    /**
     * 🔍 Verifica se l'utente è autenticato
     */
    function isUserAuthenticated() {
        const authManager = window.authManager;
        
        // Verifica presenza token
        if (!authManager.token) {
            return false;
        }

        // Verifica se il token non è scaduto (verifica veloce)
        try {
            const payload = JSON.parse(atob(authManager.token.split('.')[1]));
            const now = Math.floor(Date.now() / 1000);
            
            if (payload.exp && payload.exp < now) {
                authManager.clearToken();
                return false;
            }
        } catch (error) {
            authManager.clearToken();
            return false;
        }

        return true;
    }

    /**
     * 🚪 Reindirizza al login con informazioni sulla pagina corrente
     */
    function redirectToLogin() {
        // Salva la pagina corrente per il redirect post-login
        const currentPath = window.location.pathname + window.location.search;
        if (currentPath !== '/login') {
            sessionStorage.setItem('redirect_after_login', currentPath);
        }
        
        window.location.href = '/login';
    }

    /**
     * 🛠️ Setup funzionalità per pagine protette
     */
    function setupProtectedPageFeatures() {
        // 1. Aggiungi pulsante logout se non presente
        addLogoutButton();
        
        // 2. Mostra informazioni utente
        displayUserInfo();
        
        // 3. Setup auto-logout su token scaduto
        setupTokenExpirationCheck();
        
        // 4. Aggiungi stile per elementi di autenticazione
        addAuthStyles();
    }

    /**
     * 🚪 Aggiungi pulsante logout
     */
    function addLogoutButton() {
        // Verifica se già presente
        if (document.querySelector('.auth-logout-btn')) return;

        // Cerca dove inserire il pulsante
        const targetSelectors = [
            'header .container',
            '.header-content',
            '.nav-menu',
            'header',
            '.header'
        ];

        let targetElement = null;
        for (const selector of targetSelectors) {
            targetElement = document.querySelector(selector);
            if (targetElement) break;
        }

        if (targetElement) {
            const logoutContainer = document.createElement('div');
            logoutContainer.className = 'auth-controls';
            logoutContainer.innerHTML = `
                <div class="auth-user-info">
                    <i class="fas fa-user-circle"></i>
                    <span class="auth-username" data-user-name>Utente</span>
                </div>
                <button class="auth-logout-btn" onclick="window.authManager.logout()">
                    <i class="fas fa-sign-out-alt"></i>
                    <span>Logout</span>
                </button>
            `;
            
            targetElement.appendChild(logoutContainer);
        } else {
            // Fallback: aggiungi in posizione fissa
            const fixedLogout = document.createElement('div');
            fixedLogout.className = 'auth-logout-fixed';
            fixedLogout.innerHTML = `
                <button class="auth-logout-btn" onclick="window.authManager.logout()" title="Logout">
                    <i class="fas fa-sign-out-alt"></i>
                </button>
            `;
            document.body.appendChild(fixedLogout);
        }
    }

    /**
     * 👤 Mostra informazioni utente
     */
    function displayUserInfo() {
        const user = window.authManager.getCurrentUser();
        if (!user) return;

        // Aggiorna elementi con data-user-name
        const userNameElements = document.querySelectorAll('[data-user-name]');
        userNameElements.forEach(el => {
            el.textContent = user.username || 'Utente';
        });

        // Aggiorna altri elementi utente se presenti
        const userEmailElements = document.querySelectorAll('[data-user-email]');
        userEmailElements.forEach(el => {
            el.textContent = user.email || '';
        });
    }

    /**
     * ⏰ Verifica periodica della scadenza del token
     */
    function setupTokenExpirationCheck() {
        setInterval(() => {
            if (!isUserAuthenticated()) {
                alert('La tua sessione è scaduta. Verrai reindirizzato al login.');
                window.authManager.logout();
            }
        }, 60000); // Controlla ogni minuto
    }

    /**
     * 🎨 Aggiungi stili CSS per gli elementi di autenticazione
     */
    function addAuthStyles() {
        if (document.querySelector('#auth-styles')) return;

        const styles = document.createElement('style');
        styles.id = 'auth-styles';
        styles.textContent = `
            .auth-controls {
                display: flex;
                align-items: center;
                gap: 15px;
                margin-left: auto;
            }
            
            .auth-user-info {
                display: flex;
                align-items: center;
                gap: 8px;
                color: #666;
                font-size: 14px;
            }
            
            .auth-user-info i {
                font-size: 18px;
                color: #007bff;
            }
            
            .auth-logout-btn {
                background: #dc3545;
                color: white;
                border: none;
                padding: 8px 12px;
                border-radius: 4px;
                cursor: pointer;
                font-size: 14px;
                display: flex;
                align-items: center;
                gap: 6px;
                transition: background-color 0.2s;
            }
            
            .auth-logout-btn:hover {
                background: #c82333;
            }
            
            .auth-logout-fixed {
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 1000;
            }
            
            .auth-logout-fixed .auth-logout-btn {
                padding: 10px;
                border-radius: 50%;
                min-width: 40px;
                min-height: 40px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.2);
            }
            
            .auth-logout-fixed .auth-logout-btn span {
                display: none;
            }
        `;
        document.head.appendChild(styles);
    }

    // 🚀 Avvio automatico quando il DOM è pronto
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initProtectedPage);
    } else {
        initProtectedPage();
    }

    // Export funzioni utili
    window.ProtectedPage = {
        isAuthenticated: isUserAuthenticated,
        redirectToLogin: redirectToLogin,
        addLogoutButton: addLogoutButton,
        displayUserInfo: displayUserInfo
    };

})();

// Inizializzazione automatica
initializeProtectedPage();

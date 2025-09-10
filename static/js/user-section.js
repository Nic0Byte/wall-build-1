/**
 * User Section Simple Manager
 * Gestione semplice: solo nome utente e logout
 */

class UserSectionSimple {
    constructor() {
        this.isMenuOpen = false;
        this.userInfoSimple = null;
        this.userMenuSimple = null;
        this.logoutBtnSimple = null;
        this.userNameSimple = null;
        
        this.initializeElements();
        this.attachEventListeners();
        this.loadUserInfo();
    }
    
    initializeElements() {
        this.userInfoSimple = document.getElementById('userInfoSimple');
        this.userMenuSimple = document.getElementById('userMenuSimple');
        this.logoutBtnSimple = document.getElementById('logoutBtnSimple');
        this.userNameSimple = document.getElementById('userNameSimple');
    }
    
    attachEventListeners() {
        // Toggle menu on click
        if (this.userInfoSimple) {
            this.userInfoSimple.addEventListener('click', (e) => {
                e.stopPropagation();
                this.toggleMenu();
            });
        }
        
        // Close menu when clicking outside
        document.addEventListener('click', (e) => {
            if (this.isMenuOpen && !this.userMenuSimple.contains(e.target)) {
                this.closeMenu();
            }
        });
        
        // Logout functionality
        if (this.logoutBtnSimple) {
            this.logoutBtnSimple.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                this.handleLogout();
            });
        }
    }
    
    toggleMenu() {
        if (this.isMenuOpen) {
            this.closeMenu();
        } else {
            this.openMenu();
        }
    }
    
    openMenu() {
        if (!this.userMenuSimple) return;
        
        this.isMenuOpen = true;
        
        // Calcola la posizione dinamicamente
        const rect = this.userInfoSimple.getBoundingClientRect();
        this.userMenuSimple.style.position = 'fixed';
        this.userMenuSimple.style.top = `${rect.bottom + 8}px`;
        this.userMenuSimple.style.right = `${window.innerWidth - rect.right}px`;
        
        this.userMenuSimple.style.display = 'block';
        this.userInfoSimple.classList.add('active');
        
        setTimeout(() => {
            this.userMenuSimple.classList.add('show');
        }, 10);
    }
    
    closeMenu() {
        if (!this.userMenuSimple) return;
        
        this.isMenuOpen = false;
        this.userMenuSimple.classList.remove('show');
        this.userInfoSimple.classList.remove('active');
        
        setTimeout(() => {
            this.userMenuSimple.style.display = 'none';
        }, 300);
    }
    
    async loadUserInfo() {
        try {
            // Check if authManager is available
            if (typeof window.authManager !== 'undefined') {
                const userInfo = window.authManager.getCurrentUser();
                if (userInfo) {
                    this.updateUserName(userInfo.name || userInfo.username || 'Utente');
                    return;
                }
            }
            
            // Try to fetch from API
            const response = await fetch('/api/v1/auth/me', {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('access_token')}`
                }
            });
            
            if (response.ok) {
                const userData = await response.json();
                this.updateUserName(userData.name || userData.username || 'Utente');
            } else {
                this.updateUserName('Utente TAKTAK');
            }
        } catch (error) {
            console.warn('Error loading user info:', error);
            this.updateUserName('Utente TAKTAK');
        }
    }
    
    updateUserName(name) {
        if (this.userNameSimple) {
            this.userNameSimple.textContent = name;
        }
        console.log('✅ User name loaded:', name);
    }
    
    async handleLogout() {
        try {
            this.closeMenu();
            
            // Use authManager if available
            if (typeof window.authManager !== 'undefined') {
                await window.authManager.logout();
            } else {
                // Fallback logout
                localStorage.removeItem('access_token');
                localStorage.removeItem('user_info');
                window.location.href = '/login';
            }
            
        } catch (error) {
            console.error('Error during logout:', error);
            this.showToast('Errore durante la disconnessione', 'error');
        }
    }
    
    showToast(message, type = 'info') {
        // Use wallPackingApp toast if available
        if (window.wallPackingApp && window.wallPackingApp.showToast) {
            window.wallPackingApp.showToast(message, type);
        } else {
            // Fallback to console log
            console.log(`${type.toUpperCase()}: ${message}`);
        }
    }
}

// Initialize User Section Simple when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    setTimeout(() => {
        window.userSectionSimple = new UserSectionSimple();
        console.log('✅ Simple User Section initialized');
    }, 100);
});

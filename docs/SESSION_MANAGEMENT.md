# 🔐 Gestione Sessioni e Autenticazione

## Panoramica

Il sistema di autenticazione è stato aggiornato per garantire che **ad ogni disconnessione (anche senza logout esplicito) sia necessario rifare il login**.

## Caratteristiche Implementate

### 1. **SessionStorage invece di LocalStorage**

✅ **PRIMA**: I token JWT erano salvati in `localStorage`, persistendo anche dopo la chiusura del browser.

✅ **ADESSO**: I token JWT sono salvati in `sessionStorage`, che viene automaticamente cancellato quando:
- L'utente chiude la finestra/tab del browser
- L'utente chiude completamente il browser
- La sessione del browser termina

```javascript
// File modificati:
// - static/js/auth.js
// - templates/login.html
// - static/js/user-section.js
```

### 2. **Logout Automatico per Inattività**

⏰ **Timeout**: 30 minuti di inattività (configurabile)

Il sistema monitora l'attività dell'utente tramite i seguenti eventi:
- `mousedown`, `mousemove` - movimento mouse
- `keypress` - digitazione tastiera
- `scroll` - scorrimento pagina
- `touchstart` - tocco su dispositivi mobili
- `click` - click del mouse

**Comportamento**:
1. Se l'utente non interagisce per 30 minuti, viene mostrato un avviso
2. Dopo 2 secondi dall'avviso, viene eseguito il logout automatico
3. L'utente viene reindirizzato alla pagina di login

### 3. **Gestione Chiusura Browser**

🚪 **Eventi Monitorati**:
- `beforeunload`: Quando l'utente chiude la finestra/tab
- `visibilitychange`: Quando il tab viene nascosto/mostrato

**Comportamento**:
- Alla chiusura della finestra, il `sessionStorage` viene automaticamente pulito dal browser
- Quando il tab viene nascosto, il monitoraggio dell'attività viene messo in pausa
- Quando il tab viene mostrato nuovamente, il timer di inattività viene resettato

### 4. **Migrazione da LocalStorage a SessionStorage**

🔄 **Compatibilità**: Per garantire una transizione fluida, il sistema:
- Pulisce automaticamente i vecchi token da `localStorage` quando viene fatto logout
- Controlla entrambi gli storage durante il login per rimuovere dati obsoleti

## Configurazione

### Modificare il Timeout di Inattività

Modifica il valore in `static/js/auth.js`:

```javascript
class AuthManager {
    constructor() {
        // ...
        
        // CAMBIA QUESTO VALORE (in millisecondi)
        this.inactivityTimeout = 30 * 60 * 1000; // 30 minuti
        
        // Esempi:
        // 15 minuti: 15 * 60 * 1000
        // 1 ora: 60 * 60 * 1000
        // 2 ore: 120 * 60 * 1000
    }
}
```

## Sicurezza

### Vantaggi del Nuovo Sistema

1. **🔒 Maggiore Sicurezza**: I token non persistono oltre la sessione del browser
2. **🕐 Protezione da Inattività**: Logout automatico su computer condivisi
3. **🚪 Pulizia Automatica**: Nessun dato residuo dopo la chiusura del browser
4. **👥 Multi-Utente**: Sicuro per ambienti con più utenti sullo stesso computer

### Best Practices

1. **Computer Condivisi**: Gli utenti vengono automaticamente disconnessi alla chiusura del browser
2. **Timeout Personalizzato**: Imposta timeout più brevi per ambienti ad alta sicurezza
3. **Notifiche Utente**: Il sistema avvisa l'utente prima del logout per inattività

## Testing

### Testare il Sistema

1. **Test Chiusura Browser**:
   ```
   1. Fai login nell'applicazione
   2. Chiudi completamente il browser
   3. Riapri il browser e vai all'URL dell'app
   4. ✅ Dovresti essere reindirizzato alla pagina di login
   ```

2. **Test Inattività**:
   ```
   1. Fai login nell'applicazione
   2. Non interagire per 30 minuti
   3. ✅ Dopo 30 minuti dovresti vedere un avviso
   4. ✅ Dopo 2 secondi dall'avviso, verrai reindirizzato al login
   ```

3. **Test Chiusura Tab**:
   ```
   1. Fai login nell'applicazione
   2. Chiudi il tab (non il browser)
   3. Apri un nuovo tab e vai all'URL dell'app
   4. ✅ Dovresti essere reindirizzato alla pagina di login
   ```

## Monitoraggio

### Console Log

Il sistema produce log per il debugging:

```javascript
// Esempi di log:
"🕐 Monitoraggio inattività attivo (timeout: 30 minuti)"
"👁️ Tab nascosta - Pausa monitoraggio attività"
"👁️ Tab visibile - Ripresa monitoraggio attività"
"⚠️ Timeout inattività - Esecuzione logout automatico"
"🚪 Chiusura finestra - La sessione verrà cancellata"
```

### API per Debugging

Puoi controllare lo stato della sessione dalla console del browser:

```javascript
// Verifica se l'utente è autenticato
window.authManager.isAuthenticated()

// Ottieni l'utente corrente
window.authManager.getCurrentUser()

// Ottieni il tempo rimanente prima del logout (secondi)
window.authManager.getTimeUntilInactivityLogout()

// Forza logout
window.authManager.logout()
```

## Troubleshooting

### Problema: L'utente viene disconnesso troppo frequentemente

**Soluzione**: Aumenta il valore di `inactivityTimeout` in `auth.js`

### Problema: L'utente rimane loggato dopo la chiusura del browser

**Verifica**:
1. Controlla che non ci siano estensioni del browser che salvano sessionStorage
2. Verifica che il browser non sia in modalità "Ripristina sessione precedente"
3. Controlla i log della console per eventuali errori

### Problema: Il sistema non rileva l'attività dell'utente

**Verifica**:
1. Controlla che gli event listener siano registrati correttamente
2. Verifica la console per log di attività
3. Assicurati che `setupInactivityMonitor()` venga chiamato

## File Modificati

| File | Modifiche |
|------|-----------|
| `static/js/auth.js` | Conversione a sessionStorage + gestione inattività |
| `templates/login.html` | Conversione a sessionStorage |
| `static/js/user-section.js` | Conversione a sessionStorage |
| `static/js/protected-page.js` | (Già compatibile) |

## Retrocompatibilità

Il sistema include pulizia automatica dei vecchi dati da `localStorage` per garantire che:
- Gli utenti esistenti non abbiano problemi
- I vecchi token vengano rimossi
- Non ci siano conflitti tra storage

## Nota Importante

⚠️ **ATTENZIONE**: Con questo sistema, gli utenti dovranno:
- Effettuare il login ogni volta che aprono il browser
- Effettuare il login dopo 30 minuti di inattività

Se questo comportamento è troppo restrittivo per il tuo caso d'uso, considera:
- Aumentare il timeout di inattività
- Implementare un sistema di "Remember Me" con token refresh sicuri
- Usare cookie sicuri invece di sessionStorage

## Supporto

Per domande o problemi, contatta il team di sviluppo o consulta la documentazione completa del sistema di autenticazione.

---
*Ultima modifica: Ottobre 2025*
*Versione: 3.2.1*

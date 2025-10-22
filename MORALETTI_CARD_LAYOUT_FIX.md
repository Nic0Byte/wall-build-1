# Fix Layout Card Moraletti - Scambio Posizione e Dimensioni

## Problema
La card "Moraletti" in Step 5 era troppo piccola per contenere tutte le informazioni dettagliate (configurazione, piedini, quantità totale, e breakdown per tipo di blocco). Era necessario scambiare la posizione con "Configurazione Parete" e ingrandire la card.

## Soluzione Implementata

### 1. CSS Aggiunto (`static/css/style.css`)

Aggiunto nuovo CSS per definire il layout della griglia di configurazione:

```css
/* ===== Configuration Info Grid ===== */
.configuration-card {
    background: white;
    border-radius: 12px;
    padding: 24px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    border: 1px solid #e5e7eb;
}

.config-info-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 20px;
}

.config-section {
    background: #f9fafb;
    padding: 16px;
    border-radius: 8px;
    border: 1px solid #e5e7eb;
}

/* Moraletti section - Occupa 2 colonne per più spazio */
#morettiSection {
    grid-column: span 2;
    min-height: 150px;
}

#morettiSection #morettiInfo {
    max-height: 200px;
    overflow-y: auto;
}
```

**Caratteristiche**:
- Griglia a 3 colonne (`repeat(3, 1fr)`)
- `#morettiSection` occupa 2 colonne (`grid-column: span 2`)
- Scroll verticale automatico se il contenuto supera 200px
- Design responsive per tablet e mobile

### 2. HTML Modificato (`templates/index.html`)

**Ordine Precedente**:
1. Materiale
2. Guide
3. Blocchi
4. **Moraletti** ← era in posizione 4
5. Costruzione
6. (Spessore Chiusura - creato dinamicamente)
7. (Configurazione Parete - creato dinamicamente)

**Nuovo Ordine**:
1. Materiale
2. Guide
3. Blocchi
4. **Configurazione Parete** ← ora in posizione 4
5. Costruzione
6. Spessore Chiusura
7. **Moraletti** ← ora in posizione 7 e occupa 2 colonne

**Modifiche**:
- Spostato `wallSection` e `closureSection` dall'essere creati dinamicamente all'HTML statico
- Spostato `morettiSection` alla fine
- Tutte le sezioni ora presenti nel template HTML iniziale

### 3. JavaScript Modificato (`static/js/app.js`)

Rimossi i controlli che creavano dinamicamente le sezioni `wallSection` e `closureSection`:

**Prima**:
```javascript
if (wallInfo) {
    wallInfo.innerHTML = wallText;
    if (wallSection) wallSection.style.display = 'block';
    hasConfigData = true;
} else {
    // Crea la sezione se non esiste
    this.createWallSectionInConfigCard(wallText);
}
```

**Dopo**:
```javascript
if (wallInfo) {
    wallInfo.innerHTML = wallText;
    if (wallSection) wallSection.style.display = 'block';
    hasConfigData = true;
}
```

Le funzioni `createClosureSectionInConfigCard()` e `createWallSectionInConfigCard()` sono ora obsolete ma lasciate per compatibilità.

## Layout Risultante

```
┌─────────────────────────────────────────────────────┐
│  RIASSUNTO CONFIGURAZIONE PROGETTO                  │
├────────────────┬────────────────┬────────────────────┤
│  MATERIALE     │  GUIDE         │  BLOCCHI           │
├────────────────┼────────────────┼────────────────────┤
│  CONFIGURAZ.   │  COSTRUZIONE   │  SPESSORE          │
│  PARETE        │                │  CHIUSURA          │
├────────────────┴────────────────┼────────────────────┤
│  MORALETTI (2 colonne)          │                    │
│  - Configurazione: 58×495mm     │  (scroll se serve) │
│  - Piedini: 95mm                │                    │
│  - Quantità Totale: 36 pezzi    │                    │
│  - Standard: A(1239mm): 6 pz... │                    │
│  - Custom: D(800×300mm): 2 pz.. │                    │
└─────────────────────────────────┴────────────────────┘
```

## Responsive Design

### Desktop (>1200px)
- Griglia a 3 colonne
- Moraletti occupa 2 colonne

### Tablet (768px - 1200px)
- Griglia a 2 colone
- Moraletti occupa 2 colonne (tutta la larghezza)

### Mobile (<768px)
- Griglia a 1 colonna
- Tutte le sezioni occupano l'intera larghezza

## Test

Per testare le modifiche:

1. Avviare il server
2. Completare un progetto fino a Step 5
3. Verificare che:
   - La card "Moraletti" appaia in fondo
   - Occupi 2 colonne (più larga)
   - Mostri tutte le informazioni (configurazione, piedini, quantità, breakdown)
   - Abbia scroll se il contenuto supera i 200px
   - "Configurazione Parete" appaia prima di "Moraletti"

## File Modificati

1. `static/css/style.css` - Aggiunto CSS per layout griglia
2. `templates/index.html` - Riorganizzate sezioni HTML
3. `static/js/app.js` - Rimossi controlli per creazione dinamica sezioni

## Note

- Il CSS linter segnala un warning su linee vuote in `style.css` (linea 5152), ma non influisce sulla funzionalità
- Le funzioni `createClosureSectionInConfigCard()` e `createWallSectionInConfigCard()` rimangono nel codice ma non vengono più chiamate

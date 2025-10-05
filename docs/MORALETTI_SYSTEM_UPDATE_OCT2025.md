# Aggiornamento Sistema Moraletti - Ottobre 2025

## 📋 Panoramica Modifiche

Il sistema di posizionamento moraletti è stato completamente rivisto per allinearsi alle specifiche tecniche fornite dall'immagine di riferimento.

---

## 🎯 Obiettivi Raggiunti

### 1. **Numero Moraletti Configurabile**
- ✅ Aggiunti 3 nuovi campi input nell'interfaccia
- ✅ Configurazione salvata in localStorage
- ✅ Default: Grande=3, Medio=2, Piccolo=1

### 2. **Nuova Logica di Posizionamento (Da Destra a Sinistra)**
- ✅ Primo moraletto centrato sul bordo **DESTRO** del blocco
- ✅ Moraletti successivi distribuiti verso **SINISTRA** con spaziatura configurabile
- ✅ Formula: `posizione = larghezza_blocco - (thickness/2) - (n * spacing)`

### 3. **Gestione Altezza da Terra (Piedini)**
- ✅ Parametro configurabile per quanto il moraletto sporge SOTTO il blocco
- ✅ Visualizzazione grafica nel preview SVG
- ✅ Parte sotto il blocco evidenziata con colore più scuro

### 4. **Allineamento Verticale**
- ✅ Sistema verifica che moraletti di livelli diversi si allineino
- ✅ Logica compatibile con algoritmo di packing

---

## 📐 Esempio di Calcolo

### Blocco Grande: 1260mm × 495mm
**Configurazione:**
- Larghezza moraletto: 58mm
- Altezza moraletto: 495mm
- Altezza da terra (piedini): 95mm
- Spaziatura: 420mm
- Numero moraletti: 3

**Posizioni calcolate (dal bordo sinistro):**
1. **Moraletto 1**: 1260 - 29 = **1231mm**
   - 29mm fuori dal blocco (destra)
   - 29mm dentro il blocco
   
2. **Moraletto 2**: 1231 - 420 = **811mm**
   
3. **Moraletto 3**: 811 - 420 = **391mm**

**Altezza totale visibile:** 495mm (dentro blocco) + 95mm (piedini sotto) = **590mm**

---

## 🔧 File Modificati

### 1. **`utils/config.py`**

#### Funzione: `calculate_moraletto_positions()`
**Signature cambiata:**
```python
# PRIMA (vecchia)
calculate_moraletto_positions(total_width_mm: int, base_width_mm: int = None, offset_mm: int = None)

# DOPO (nuova)
calculate_moraletto_positions(total_width_mm: int, thickness_mm: int, spacing_mm: int, count: int)
```

**Nuova Logica:**
```python
def calculate_moraletto_positions(total_width_mm: int, thickness_mm: int, spacing_mm: int, count: int) -> List[int]:
    """
    PARTENZA DA DESTRA: Primo moraletto centrato sul bordo destro
    Posizione primo: total_width_mm - (thickness_mm / 2)
    Moraletti successivi: verso SINISTRA sottraendo spacing_mm
    """
    positions = []
    first_position = total_width_mm - (thickness_mm / 2)
    
    for i in range(count):
        position = first_position - (i * spacing_mm)
        if position - (thickness_mm / 2) >= 0:
            positions.append(int(position))
        else:
            break
    
    return positions
```

#### Funzione: `validate_moraletto_alignment()`
**Aggiornata per nuova signature** con parametri `thickness_mm` e `spacing_mm`

---

### 2. **`static/js/app.js`**

#### Funzione: `calculateMoralettiPositionsJS()`
**Signature cambiata:**
```javascript
// PRIMA
calculateMoralettiPositionsJS(totalWidth, baseWidth)

// DOPO
calculateMoralettiPositionsJS(totalWidth, thickness, spacing, count)
```

**Nuova Implementazione:**
```javascript
function calculateMoralettiPositionsJS(totalWidth, thickness, spacing, count) {
    const positions = [];
    const firstPosition = totalWidth - (thickness / 2); // Da DESTRA
    
    for (let i = 0; i < count; i++) {
        const position = firstPosition - (i * spacing);
        if (position - (thickness / 2) >= 0) {
            positions.push(Math.round(position));
        } else {
            break;
        }
    }
    return positions;
}
```

#### Funzione: `generateBlockPreview()`
**Modifiche principali:**
1. Legge parametro `heightFromGround` dagli input
2. ViewBox SVG aumentato a `400x140` per spazio piedini
3. Rendering moraletto diviso in due parti:
   - Parte dentro/sopra blocco
   - Parte sotto blocco (piedini) con colore diverso
4. Aggiunta linea pavimento quando `heightFromGround > 0`

#### Funzione: `generateTechnicalPreview()`
Legge i nuovi contatori:
```javascript
const countLarge = parseInt(document.getElementById('moralettiCountLarge')?.value) || 3;
const countMedium = parseInt(document.getElementById('moralettiCountMedium')?.value) || 2;
const countSmall = parseInt(document.getElementById('moralettiCountSmall')?.value) || 1;
```

#### Funzioni di Configurazione
Aggiornate per includere nuovi parametri:
- `saveMoralettiConfiguration()`: salva countLarge, countMedium, countSmall
- `getDefaultMoralettiConfig()`: include defaults per contatori
- `applyMoralettiConfigToUI()`: applica contatori agli input
- `setupMoralettiEventListeners()`: aggiunge listener per nuovi input

---

### 3. **`templates/index.html`**

#### Nuovi Campi Input
```html
<div class="control-group">
    <label for="moralettiCountLarge">N° Moraletti Blocco Grande</label>
    <input type="number" id="moralettiCountLarge" value="3" min="1" max="5">
</div>

<div class="control-group">
    <label for="moralettiCountMedium">N° Moraletti Blocco Medio</label>
    <input type="number" id="moralettiCountMedium" value="2" min="1" max="5">
</div>

<div class="control-group">
    <label for="moralettiCountSmall">N° Moraletti Blocco Piccolo</label>
    <input type="number" id="moralettiCountSmall" value="1" min="1" max="5">
</div>
```

#### Label Migliorata per Altezza da Terra
```html
<label for="moralettiHeightFromGround">Altezza da Terra (Piedini) (mm)</label>
<div class="auto-suggestion">
    <span>⬇ Quanto il moraletto sporge SOTTO il blocco (es. 95mm = piedini che sollevano il blocco)</span>
</div>
```

#### Spiegazione Sistema Aggiornata
- 8 step dettagliati invece di 5
- Enfasi su posizionamento da DESTRA
- Esempio pratico con numeri
- Spiegazione piedini/altezza da terra

---

## 🎨 Visualizzazione Grafica

### Preview SVG Migliorato
```
┌─────────────────────────────────┐
│  1231mm    811mm    391mm       │ ← Posizioni moraletti
│     │        │        │         │
│  ┌──┴──┐  ┌──┴──┐  ┌──┴──┐     │ ← Parte sopra blocco
│  │  🔩 │  │  🔩 │  │  🔩 │     │
├──┼─────┼──┼─────┼──┼─────┼─────┤ ← Blocco
│  │  🔩 │  │  🔩 │  │  🔩 │     │
│  │  🔩 │  │  🔩 │  │  🔩 │     │
└──┼─────┼──┼─────┼──┼─────┼─────┘ ← Base blocco
   │ 🦶 │  │ 🦶 │  │ 🦶 │         ← Piedini (altezza da terra)
   └─────┘  └─────┘  └─────┘
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ ← Pavimento
```

---

## 🔄 Compatibilità con Packing Algorithm

### Dati Disponibili per l'Algoritmo
Quando salvata, la configurazione moraletti fornisce:

```javascript
{
    thickness: 58,              // Larghezza moraletto
    height: 495,                // Altezza moraletto
    heightFromGround: 95,       // Piedini sotto blocco
    spacing: 420,               // Spaziatura tra moraletti
    countLarge: 3,              // N° moraletti blocco grande
    countMedium: 2,             // N° moraletti blocco medio
    countSmall: 1               // N° moraletti blocco piccolo
}
```

### Calcolo Posizioni nell'Algoritmo
```python
from utils.config import calculate_moraletto_positions

# Per un blocco specifico
positions = calculate_moraletto_positions(
    total_width_mm=1260,
    thickness_mm=58,
    spacing_mm=420,
    count=3
)
# Risultato: [1231, 811, 391]
```

### Validazione Allineamento Verticale
```python
from utils.config import validate_moraletto_alignment

level_configs = [
    {"total_width": 1260, "count": 3},  # Blocco grande
    {"total_width": 840, "count": 2},   # Blocco medio
    {"total_width": 420, "count": 1}    # Blocco piccolo
]

is_aligned = validate_moraletto_alignment(
    level_configurations=level_configs,
    thickness_mm=58,
    spacing_mm=420
)
# Risultato: True (se allineati correttamente)
```

---

## ✅ Testing Consigliato

### Test Case 1: Configurazione Standard
- **Blocchi**: 1260mm, 840mm, 420mm
- **Moraletti**: 3, 2, 1
- **Spaziatura**: 420mm (auto-calcolata)
- **Risultato atteso**: Allineamento verticale perfetto

### Test Case 2: Con Piedini
- **Altezza da terra**: 95mm
- **Risultato atteso**: 
  - Preview mostra piedini sotto blocco
  - Linea pavimento visibile
  - Label indica "⬇ Piedini: 95mm sotto il blocco"

### Test Case 3: Numero Moraletti Custom
- **Grande**: 4 moraletti
- **Medio**: 3 moraletti
- **Piccolo**: 2 moraletti
- **Risultato atteso**: Preview aggiornato con nuovi contatori

---

## 📝 Note Implementative

### Perché da Destra?
L'algoritmo di packing necessita di un sistema di riferimento coerente. Partendo da destra:
- ✅ Allineamento verticale garantito tra livelli
- ✅ Facile calcolo per blocchi di diverse larghezze
- ✅ Compatibile con immagine tecnica fornita

### Altezza da Terra (Piedini)
- Valore **positivo**: mm che sporgono SOTTO il blocco
- Solleva il blocco dal pavimento
- Utile per installazioni con pavimenti irregolari o per ventilazione

### Spaziatura Preset Intelligente
Formula: `larghezza_blocco_grande ÷ 3`
- Per 1260mm → 420mm
- Per 1239mm → 413mm (vecchio standard)
- Garantisce distribuzione equilibrata

---

## 🚀 Prossimi Passi

1. **Integrazione con Algoritmo Packing** ⏳
   - Usare `calculate_moraletto_positions()` nel packing
   - Verificare allineamento verticale durante assemblaggio
   - Considerare piedini nei calcoli altezza

2. **Testing Esteso** ⏳
   - Test con configurazioni edge case
   - Verifica performance con molti moraletti
   - Test allineamento su pareti complesse

3. **Documentazione Utente** ⏳
   - Aggiungere video tutorial
   - Screenshot configurazioni esempio
   - FAQ su moraletti

---

## 👨‍💻 Autore
**GitHub Copilot** - Ottobre 2025

## 📞 Supporto
Per domande o problemi relativi al sistema moraletti, verificare:
1. File di configurazione salvato correttamente
2. Blocchi confermati prima di moraletti
3. Console browser per eventuali errori JavaScript

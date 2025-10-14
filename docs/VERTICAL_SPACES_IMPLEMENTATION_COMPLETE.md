# 🎯 Implementazione Spazio da Terra - COMPLETATA

## 📋 Riepilogo Implementazione

L'implementazione della funzionalità "Spazio da Terra" è stata completata con successo. Il sistema ora supporta il calcolo dello spazio verticale iniziale (piedini/moraletti) per ENTRAMBI gli algoritmi SMALL e BIG.

## ✅ Modifiche Implementate

### 1. Backend - `core/wall_builder.py`

**Funzione**: `pack_wall()` (linea ~597)

**Modifiche**:
```python
def pack_wall(..., vertical_config: Optional[Dict] = None):
    """
    Args:
        vertical_config: {
            'enableGroundOffset': bool,
            'groundOffsetValue': int (mm),
            'enableCeilingSpace': bool,
            'ceilingSpaceValue': int (mm)
        }
    """
    # Default vertical config
    if vertical_config is None:
        vertical_config = {
            'enableGroundOffset': False,
            'groundOffsetValue': 0,
            'enableCeilingSpace': False,
            'ceilingSpaceValue': 0
        }
```

**Logica Implementata**:
```python
# Calcola offset da terra
ground_offset = 0
if vertical_config.get('enableGroundOffset', False):
    ground_offset = vertical_config.get('groundOffsetValue', 0)

# Calcola spazio soffitto
ceiling_space = 0
if vertical_config.get('enableCeilingSpace', False):
    ceiling_space = vertical_config.get('ceilingSpaceValue', 0)

# Calcola limiti reali di packing
miny_adjusted = miny + ground_offset
maxy_adjusted = maxy - ceiling_space
available_height = maxy_adjusted - miny_adjusted

# Usa miny_adjusted come punto di partenza
y = miny_adjusted
complete_rows = int(available_height / block_height)
```

### 2. API - `api/routes/packing.py`

**Modifiche in 3 endpoint**:

1. **`/api/enhanced-pack-from-preview`** (linea ~220)
   - Aggiunto parametro: `vertical_spaces: Optional[str] = Form(None)`
   - Parsing JSON e passaggio a `pack_wall()`

2. **`/api/upload`** (linea ~505)
   - Aggiunto parametro: `vertical_spaces: Optional[str] = Form(None)`
   - Parsing JSON e passaggio a `pack_wall()`

3. **`/api/enhanced-pack`** (linea ~841)
   - Aggiunto parametro: `vertical_spaces: Optional[str] = Form(None)`
   - Parsing JSON e passaggio a `pack_wall()`

**Logica Parsing**:
```python
vertical_config = None
if vertical_spaces:
    try:
        vertical_config = json.loads(vertical_spaces)
        print(f"🔺 Vertical Spaces Config: {vertical_config}")
    except json.JSONDecodeError:
        print(f"⚠️ Errore parsing vertical_spaces, usando default")
        vertical_config = {
            'enableGroundOffset': False,
            'groundOffsetValue': 0,
            'enableCeilingSpace': False,
            'ceilingSpaceValue': 0
        }

# Chiamata a pack_wall
placed, custom = pack_wall(
    ...,
    vertical_config=vertical_config  # ← NUOVO
)
```

### 3. Frontend - `static/js/app.js`

**Modifiche in 2 posizioni**:

1. **Funzione `processFile()`** (linea ~532)
2. **Funzione `processFromPreview()`** (linea ~658)

**Codice Aggiunto**:
```javascript
// NEW: Add vertical spaces configuration
const verticalSpacesConfig = this.getVerticalSpacesConfig();
formData.append('vertical_spaces', JSON.stringify(verticalSpacesConfig));
```

**Funzione Esistente Riutilizzata**:
```javascript
getVerticalSpacesConfig() {
    return {
        enableGroundOffset: enableGroundOffsetCheckbox?.checked ?? true,
        groundOffsetValue: parseInt(groundOffsetValue) || 95,
        enableCeilingSpace: enableCeilingSpaceCheckbox?.checked ?? false,
        ceilingSpaceValue: parseInt(ceilingSpaceValue) || 100
    };
}
```

### 4. Import Aggiornati

**`api/routes/packing.py`**:
```python
from typing import Dict, Optional  # ← Aggiunto Optional
```

## 🔍 Comportamento Implementato

### Quando Ground Offset è ABILITATO (default: 95mm)

1. **Calcolo Start Y**:
   - `start_y = miny + 95mm` (invece di `miny`)

2. **Altezza Disponibile**:
   - `available_height = maxy - (miny + 95mm)`

3. **Righe Complete**:
   - `complete_rows = available_height / block_height`

4. **Risultato Visivo**:
   - Tutti i blocchi iniziano 95mm più in alto
   - Spazio vuoto sotto per i piedini/moraletti

### Quando Ground Offset è DISABILITATO

1. **Calcolo Start Y**:
   - `start_y = miny` (comportamento originale)

2. **Altezza Disponibile**:
   - `available_height = maxy - miny`

3. **Risultato**:
   - Packing inizia dal fondo della parete

## 📊 Flusso Dati Completo

```
FRONTEND (UI)
  ↓
  📥 User abilita/disabilita "Spazio da Terra"
  📥 User imposta valore (95mm default, sincronizzato con moraletti)
  ↓
  📤 getVerticalSpacesConfig() → { enableGroundOffset: true, groundOffsetValue: 95, ... }
  ↓
  📤 FormData.append('vertical_spaces', JSON.stringify(config))
  ↓
API ENDPOINT (/api/enhanced-pack-from-preview, /api/upload, /api/enhanced-pack)
  ↓
  📥 vertical_spaces: Optional[str] = Form(None)
  ↓
  🔧 vertical_config = json.loads(vertical_spaces)
  ↓
  📤 pack_wall(..., vertical_config=vertical_config)
  ↓
CORE ALGORITHM (core/wall_builder.py)
  ↓
  🔧 miny_adjusted = miny + ground_offset (se enabled)
  🔧 available_height = maxy - miny_adjusted
  🔧 y = miny_adjusted (punto di partenza)
  ↓
  🧱 PACKING INIZIA DA Y = miny_adjusted
  🧱 SPAZIO VUOTO SOTTO PER PIEDINI
```

## 🎯 Algoritmi Supportati

✅ **SMALL (🏠 Residenziale)**
- Considera ground offset
- Nessun offset orizzontale tra righe
- Start Y = miny + ground_offset

✅ **BIG (🏭 Industriale)**
- Considera ground offset
- Offset orizzontale tra righe (row_offset)
- Start Y = miny + ground_offset

**Logica**: Ground offset è UNIVERSALE, indipendente dall'algoritmo di packing orizzontale.

## 🧪 Test Consigliati

### Test 1: Ground Offset Abilitato
1. Caricare file DWG/SVG
2. Abilitare "Spazio da Terra" (95mm)
3. Eseguire packing
4. **Verificare**: Primo blocco ha `y ≥ miny + 95`

### Test 2: Ground Offset Disabilitato
1. Caricare stesso file
2. Disabilitare "Spazio da Terra"
3. Eseguire packing
4. **Verificare**: Primo blocco ha `y ≈ miny`

### Test 3: Valori Custom
1. Caricare file
2. Cambiare valore a 50mm
3. Eseguire packing
4. **Verificare**: Primo blocco ha `y ≥ miny + 50`

### Test 4: Algoritmo SMALL vs BIG
1. Testare con SMALL: offset verticale + no offset orizzontale
2. Testare con BIG: offset verticale + offset orizzontale
3. **Verificare**: Entrambi partono da `miny + ground_offset`

## 📝 Note Implementative

### Sincronizzazione con Moraletti
Il valore di default (95mm) è sincronizzato con la configurazione dei moraletti. Quando l'utente modifica l'altezza dei moraletti, il ground offset viene aggiornato automaticamente.

### Backward Compatibility
Se `vertical_spaces` non viene inviato dal frontend (vecchie sessioni, API legacy), il sistema usa il comportamento di default:
```python
vertical_config = {
    'enableGroundOffset': False,
    'groundOffsetValue': 0,
    'enableCeilingSpace': False,
    'ceilingSpaceValue': 0
}
```

### Debug Logging
Il sistema logga:
- `🔺 Ground Offset ABILITATO: Xmm` quando enabled
- `📐 Bounds originali: miny=..., maxy=..., altezza=...mm`
- `📐 Bounds adjusted: miny_adj=..., maxy_adj=..., altezza=...mm`

## 🚀 Prossimi Passi

### Implementazione Ceiling Space (Prossima Feature)
La struttura è già pronta per implementare "Spazio Soffitto":
```python
ceiling_space = 0
if vertical_config.get('enableCeilingSpace', False):
    ceiling_space = vertical_config.get('ceilingSpaceValue', 0)

maxy_adjusted = maxy - ceiling_space
```

### Test End-to-End
1. Caricare file reale (ROTTINI_LAY_REV0.dwg)
2. Configurare materiali e guide
3. Abilitare ground offset
4. Verificare output DXF con coordinate corrette

### Validazione
- Verificare che `available_height > 0` sempre
- Validare che `ground_offset + ceiling_space < total_height`
- Gestire edge case (offset troppo grandi)

## ✅ Checklist Completamento

- [x] Modifica `pack_wall()` signature con `vertical_config`
- [x] Implementazione logica ground offset in `wall_builder.py`
- [x] Aggiunta parametro `vertical_spaces` in 3 endpoint API
- [x] Parsing e validazione JSON in API
- [x] Passaggio `vertical_config` a `pack_wall()` in tutti gli endpoint
- [x] Invio FormData da frontend (2 posizioni)
- [x] Import `Optional` in `packing.py`
- [x] Documentazione completa

## 🎉 Stato

**IMPLEMENTAZIONE COMPLETATA** ✅

Il sistema ora supporta completamente la funzionalità "Spazio da Terra" per entrambi gli algoritmi SMALL e BIG. La feature è pronta per il testing end-to-end.

---

**Data Implementazione**: 2025-01-XX  
**Versione**: v1.0 (Spazio da Terra)  
**Prossima Feature**: Spazio Soffitto (Ceiling Space)

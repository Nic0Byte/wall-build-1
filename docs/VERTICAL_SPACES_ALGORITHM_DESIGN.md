# 🎯 Implementazione "Spazio da Terra" negli Algoritmi SMALL e BIG

## ✅ Decisione Approvata

**ENTRAMBI** gli algoritmi (SMALL e BIG) considereranno il flag "Spazio da Terra" (`enableGroundOffset`).

## 📐 Logica di Implementazione

### 1. **Parametri Vertical Spaces**

Il frontend invia questi parametri al backend:

```javascript
vertical_spaces: {
    enableGroundOffset: true/false,
    groundOffsetValue: 95,  // mm (sincronizzato con moraletti)
    enableCeilingSpace: true/false,
    ceilingSpaceValue: 100  // mm
}
```

### 2. **Calcolo Start Y** (Applicato ad ENTRAMBI gli algoritmi)

```python
def calculate_start_y(wall_bounds, vertical_config):
    """
    Calcola Y iniziale per il packing.
    Applicato sia a SMALL che a BIG.
    """
    minx, miny, maxx, maxy = wall_bounds
    
    # Calcola start Y
    if vertical_config.get('enableGroundOffset', False):
        start_y = miny + vertical_config.get('groundOffsetValue', 0)
    else:
        start_y = miny
    
    return start_y
```

### 3. **Calcolo Altezza Disponibile**

```python
def calculate_available_height(wall_bounds, vertical_config):
    """
    Calcola altezza disponibile per il packing.
    """
    minx, miny, maxx, maxy = wall_bounds
    total_height = maxy - miny
    
    # Sottrai spazio da terra
    if vertical_config.get('enableGroundOffset', False):
        total_height -= vertical_config.get('groundOffsetValue', 0)
    
    # Sottrai spazio soffitto
    if vertical_config.get('enableCeilingSpace', False):
        total_height -= vertical_config.get('ceilingSpaceValue', 0)
    
    return total_height
```

### 4. **Modifica Funzione `pack_wall`**

Aggiungo parametro `vertical_config` alla firma:

```python
def pack_wall(polygon: Polygon,
              block_widths: List[int],
              block_height: int,
              row_offset: Optional[int] = None,
              apertures: Optional[List[Polygon]] = None,
              enable_debug: bool = False,
              starting_direction: str = 'left',
              vertical_config: Optional[Dict] = None) -> Tuple[List[Dict], List[Dict]]:
    """
    PACKER PRINCIPALE CON SPAZI VERTICALI
    
    Args:
        vertical_config: {
            'enableGroundOffset': bool,
            'groundOffsetValue': int (mm),
            'enableCeilingSpace': bool,
            'ceilingSpaceValue': int (mm)
        }
    """
    
    # Default se non specificato
    if vertical_config is None:
        vertical_config = {
            'enableGroundOffset': False,
            'groundOffsetValue': 0,
            'enableCeilingSpace': False,
            'ceilingSpaceValue': 0
        }
    
    # Calcola bounds modificati
    minx, miny, maxx, maxy = polygon.bounds
    
    # Applica offset da terra
    if vertical_config.get('enableGroundOffset', False):
        ground_offset = vertical_config.get('groundOffsetValue', 0)
        miny_adjusted = miny + ground_offset
        print(f"📏 Spazio da terra ATTIVATO: +{ground_offset}mm → start Y = {miny_adjusted:.1f}")
    else:
        miny_adjusted = miny
        print(f"📏 Spazio da terra DISATTIVATO → start Y = {miny}")
    
    # Calcola altezza disponibile
    available_height = maxy - miny_adjusted
    
    # Sottrai spazio soffitto se attivo
    if vertical_config.get('enableCeilingSpace', False):
        ceiling_space = vertical_config.get('ceilingSpaceValue', 0)
        available_height -= ceiling_space
        maxy_adjusted = miny_adjusted + available_height
        print(f"🔽 Spazio soffitto ATTIVATO: -{ceiling_space}mm → end Y = {maxy_adjusted:.1f}")
    else:
        maxy_adjusted = maxy
        print(f"🔽 Spazio soffitto DISATTIVATO → end Y = {maxy}")
    
    print(f"📊 Altezza disponibile per packing: {available_height:.0f}mm")
    
    # IMPORTANTE: Usa bounds adjusted per calcolo righe
    y = miny_adjusted  # ← INIZIA DA ALTEZZA PIEDINI
    
    # Calcola righe complete con altezza disponibile
    complete_rows = int(available_height / block_height)
    remaining_space = available_height - (complete_rows * block_height)
    
    print(f"📊 Con spazi verticali: {complete_rows} righe complete, {remaining_space:.0f}mm rimanenti")
    
    # ... resto del codice rimane uguale ...
```

## 🔧 Modifiche ai File

### 1. **core/wall_builder.py**

**Modifiche**:
- Aggiungere parametro `vertical_config` alla funzione `pack_wall`
- Calcolare `miny_adjusted` e `maxy_adjusted` in base ai flag
- Usare `miny_adjusted` come start Y invece di `miny`
- Calcolare `available_height` con i nuovi bounds

### 2. **api/routes/packing.py**

**Modifiche**:
- Ricevere `vertical_spaces` dal frontend
- Passare `vertical_config` a `pack_wall()`

```python
@router.post("/process")
async def process_file(
    # ... altri parametri ...
    vertical_spaces: Optional[str] = Form(None),  # ← NUOVO
):
    # Parse vertical spaces
    vertical_config = {}
    if vertical_spaces:
        try:
            vertical_config = json.loads(vertical_spaces)
        except:
            vertical_config = {
                'enableGroundOffset': False,
                'groundOffsetValue': 0,
                'enableCeilingSpace': False,
                'ceilingSpaceValue': 0
            }
    
    # Chiama pack_wall con config
    placed, custom = pack_wall(
        wall_exterior,
        widths_list,
        block_schema["block_height"],
        row_offset=row_offset,
        apertures=apertures,
        starting_direction=starting_direction,
        vertical_config=vertical_config  # ← NUOVO
    )
```

### 3. **static/js/app.js**

**Modifiche**:
- Inviare `vertical_spaces` nel FormData

```javascript
// Quando invii il form di process
formData.append('vertical_spaces', JSON.stringify(getVerticalSpacesConfig()));
```

## 📊 Esempio di Funzionamento

### Scenario 1: Solo Spazio da Terra

```
Input:
- Parete: 3000mm altezza
- enableGroundOffset: true
- groundOffsetValue: 95mm
- enableCeilingSpace: false

Calcolo:
- miny_adjusted = 0 + 95 = 95mm
- maxy_adjusted = 3000mm
- available_height = 3000 - 95 = 2905mm
- start Y = 95mm

Risultato:
  0mm   ┌─────────────────┐
        │                 │ ← Spazio vuoto (piedini)
  95mm  ├─────────────────┤ ← INIZIO PACKING
        │ ░░░░░░░░░░░░░░░ │
        │ ░░ BLOCCHI ░░░░ │
        │ ░░░░░░░░░░░░░░░ │
 3000mm └─────────────────┘
```

### Scenario 2: Spazio da Terra + Soffitto

```
Input:
- Parete: 3000mm altezza
- enableGroundOffset: true
- groundOffsetValue: 95mm
- enableCeilingSpace: true
- ceilingSpaceValue: 100mm

Calcolo:
- miny_adjusted = 0 + 95 = 95mm
- available_height = 3000 - 95 - 100 = 2805mm
- maxy_adjusted = 95 + 2805 = 2900mm
- start Y = 95mm
- end Y = 2900mm

Risultato:
  0mm   ┌─────────────────┐
        │                 │ ← Spazio vuoto (piedini)
  95mm  ├─────────────────┤ ← INIZIO PACKING
        │ ░░░░░░░░░░░░░░░ │
        │ ░░ BLOCCHI ░░░░ │
        │ ░░░░░░░░░░░░░░░ │
 2900mm ├─────────────────┤ ← FINE PACKING
        │                 │ ← Spazio vuoto (soffitto)
 3000mm └─────────────────┘
```

### Scenario 3: Nessun Spazio

```
Input:
- Parete: 3000mm altezza
- enableGroundOffset: false
- enableCeilingSpace: false

Calcolo:
- miny_adjusted = 0mm
- maxy_adjusted = 3000mm
- available_height = 3000mm
- start Y = 0mm

Risultato:
  0mm   ┌─────────────────┐ ← INIZIO PACKING
        │ ░░░░░░░░░░░░░░░ │
        │ ░░ BLOCCHI ░░░░ │
        │ ░░░░░░░░░░░░░░░ │
 3000mm └─────────────────┘ ← FINE PACKING
```

## ✅ Checklist Implementazione

- [ ] Modificare `pack_wall()` in `core/wall_builder.py`
- [ ] Aggiungere parametro `vertical_config`
- [ ] Calcolare `miny_adjusted` e `maxy_adjusted`
- [ ] Usare bounds adjusted per calcolo righe
- [ ] Modificare endpoint `/api/v1/process` in `api/routes/packing.py`
- [ ] Ricevere parametro `vertical_spaces` dal Form
- [ ] Parsare JSON e passare a `pack_wall()`
- [ ] Modificare frontend `app.js`
- [ ] Inviare `vertical_spaces` nel FormData
- [ ] Testare con diversi scenari
- [ ] Documentare comportamento

## 🎯 Priorità

1. **Alta**: Modificare `pack_wall()` - algoritmo core
2. **Alta**: Modificare endpoint API - integrazione backend
3. **Media**: Aggiornare frontend - invio parametri
4. **Bassa**: Testing end-to-end
5. **Bassa**: Documentazione utente

---

**Data Design**: 14 Ottobre 2025  
**Versione**: v4.2  
**Feature**: Spazi Verticali negli Algoritmi SMALL e BIG  
**Status**: ⏳ In implementazione  

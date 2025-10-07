# 🔥 FIX CRITICO: Clipping Blocchi con Aperture

**Data:** 7 Ottobre 2025  
**Issue:** Custom blocks entravano dentro finestre/porte durante il clipping  
**Soluzione:** Creazione poligono con buchi prima del clipping

---

## 📋 PROBLEMA ORIGINALE

### Sintomi
- ✅ Durante il **packing**: I blocchi NON entravano nelle aperture (corretto)
- ❌ Durante il **clipping**: I blocchi ATTRAVERSAVANO le aperture (bug critico)

### Root Cause
Il poligono della parete passato al clipping era **SOLIDO** (senza buchi interni):
```
Packing:   wall + apertures (lista separata) → crea keepout → ✅ Funziona
Clipping:  wall (solido, NO apertures)       → NO keepout  → ❌ Fallisce
```

### Analisi Tecnica
```python
# PRIMA (BUGGY):
wall_polygon.interiors  # → 0 buchi
clipped = block.intersection(wall_polygon)  # Interseca con parete solida
# Risultato: blocchi attraversano finestre

# DOPO (FIXED):
wall_with_holes = wall.difference(union(apertures))  # Sottrae aperture
wall_with_holes.interiors  # → 2-3 buchi
clipped = block.intersection(wall_with_holes)  # Interseca con parete forata
# Risultato: blocchi vengono tagliati dalle finestre
```

---

## ✅ SOLUZIONE IMPLEMENTATA

### Opzione Scelta: **A - Polygon.difference()**
Crea il poligono con buchi **prima** del clipping usando l'operazione geometrica `difference()`.

### Vantaggi
- ✅ **Semplice**: Una sola operazione Shapely all'inizio
- ✅ **Robusto**: Gestisce QUALSIASI forma (cerchi, rettangoli, poligoni complessi)
- ✅ **Performance**: Una sola `difference()`, poi riutilizza il poligono per tutti i blocchi
- ✅ **Compatibilità**: Non tocca parser/packing/export, solo clipping

---

## 🔧 MODIFICHE AL CODICE

### 1. `clip_all_blocks_to_wall_geometry()`
**File:** `core/wall_builder.py`

**Nuova signature:**
```python
def clip_all_blocks_to_wall_geometry(
    placed_blocks: List[Dict],
    custom_blocks: List[Dict],
    wall_polygon: Polygon,
    block_widths: List[int],
    apertures: Optional[List[Polygon]] = None  # 🔥 NUOVO!
) -> Tuple[List[Dict], List[Dict]]:
```

**Nuova logica:**
```python
# FASE 0: Crea poligono con buchi
if apertures and len(apertures) > 0:
    # Filtra aperture (>1m², <80% parete)
    valid_apertures = [ap for ap in apertures 
                      if 1000 < ap.area < wall_area * 0.8]
    
    # Unisci e sottrai
    apertures_union = unary_union(valid_apertures)
    wall_with_holes = wall_polygon.difference(apertures_union)
    
    # Gestisci MultiPolygon (aperture sul bordo)
    if wall_with_holes.geom_type == 'MultiPolygon':
        wall_with_holes = max(wall_with_holes.geoms, key=lambda p: p.area)
    
    # Usa il poligono con buchi
    wall_polygon = wall_with_holes
```

### 2. `clip_customs_to_wall_geometry()`
**File:** `core/wall_builder.py`

**Nuova signature:**
```python
def clip_customs_to_wall_geometry(
    custom_blocks: List[Dict],
    wall_polygon: Polygon,
    block_widths: List[int],
    apertures: Optional[List[Polygon]] = None  # 🔥 NUOVO!
) -> List[Dict]:
```

**Stessa logica** di creazione buchi prima del clipping.

### 3. Chiamata da `pack_wall()`
**File:** `core/wall_builder.py` - Line ~832

```python
placed_all, validated_customs = clip_all_blocks_to_wall_geometry(
    placed_blocks=placed_all,
    custom_blocks=validated_customs,
    wall_polygon=polygon,
    block_widths=block_widths,
    apertures=apertures  # 🔥 PASSA LE APERTURE!
)
```

---

## 📊 FILTRO APERTURE

**Criteri (identici al packing):**
1. **Troppo grande**: Area > 80% della parete → SCARTATA
   - Motivo: Probabilmente errore di parsing (parete stessa)
2. **Troppo piccola**: Area < 1000mm² (< 1m²) → SCARTATA
   - Motivo: Fori insignificanti che rallenterebbero il clipping

**Esempio log:**
```
📋 Filtraggio 3 aperture:
   ❌ Apertura 1 SCARTATA: troppo grande (100.0% della parete)
   ✅ Apertura 2 VALIDA: 1800000mm² (4.3%), bounds=(2000, 500, 3000, 2300)
   ✅ Apertura 3 VALIDA: 1920000mm² (4.6%), bounds=(8000, 700, 9200, 2300)
📊 Aperture valide: 2/3
```

---

## 🎯 GESTIONE CASI SPECIALI

### Caso 1: Apertura sul Bordo
**Problema:** `difference()` può creare `MultiPolygon` (parete divisa in 2)

**Soluzione:**
```python
if wall_with_holes.geom_type == 'MultiPolygon':
    largest = max(wall_with_holes.geoms, key=lambda p: p.area)
    wall_with_holes = largest
```
Usa la **parte più grande**, scarta frammenti.

### Caso 2: Aperture Sovrapposte
**Problema:** Due finestre che si toccano

**Soluzione:**  
`unary_union()` le fonde automaticamente → un solo buco grande.

### Caso 3: Forme Complesse
**Problema:** Finestre circolari, poligonali, ecc.

**Soluzione:**  
Shapely `difference()` gestisce automaticamente qualsiasi forma.

---

## 🧪 TESTING

### Test Unitario
**File:** `test_aperture_clipping.py`

**Scenario:** Blocco 1239×495mm che attraversa una finestra 1000×1800mm

**Risultati:**
```
🚪 Buchi creati: 2
   Buco 1: area=1800000mm², bounds=(2000, 500, 3000, 2300)
   Buco 2: area=1920000mm², bounds=(8000, 700, 9200, 2300)

Test blocco che attraversa apertura:
  Blocco originale: area=613305mm²
  Blocco clippato: area=365805mm²
  Area rimasta: 59.6%
  ✅ SUCCESSO! Il blocco è stato tagliato dalla finestra!
```

**Conclusione:** Il blocco perde il 40.4% dell'area (la parte dentro la finestra).

### Test Integrazione
**File:** `test/test_wall_spaced.svg`

**Setup:**
- Parete: 12000×3500mm (42m²)
- 3 aperture rilevate dal parser
- 2 aperture valide dopo filtro

**Verifica:**
1. Upload file SVG
2. Esegui packing con direzione 'left'
3. Controlla log: Deve mostrare `🚪 Buchi interni: 2`
4. Verifica preview: Custom NON devono entrare in finestre

---

## 📝 LOGGING AGGIUNTO

### Durante Filtro Aperture
```
📋 Filtraggio 3 aperture:
   ❌ Apertura 1 SCARTATA: troppo grande (100.0% della parete)
   ✅ Apertura 2 VALIDA: 1800000mm² (4.3%), bounds=(2000, 500, 3000, 2300)
   ✅ Apertura 3 VALIDA: 1920000mm² (4.6%), bounds=(8000, 700, 9200, 2300)
📊 Aperture valide: 2/3
```

### Durante Creazione Buchi
```
🔧 Unendo aperture...
   Union type: MultiPolygon, area: 3720000mm²
✂️  Sottraendo aperture dalla parete...
✅ Poligono con buchi creato:
   Tipo: Polygon
   Area finale: 38280000mm²
   🚪 Buchi interni: 2
      Buco 1: area=1800000mm², bounds=(2000, 500, 3000, 2300)
      Buco 2: area=1920000mm², bounds=(8000, 700, 9200, 2300)
```

### Durante Buffer
```
🧹 Pulizia geometria con buffer(0)...
   ✅ buffer(0) completato, buchi preservati: 2
```

### Warning se Problema
```
⚠️  buffer(0) ha modificato i buchi: 2 → 0
⚠️  Risultato: MultiPolygon con 3 parti
   Usando parte più grande: 35000000mm²
   Parti scartate: 500000mm²
```

---

## 🚀 COMPATIBILITÀ

### Backward Compatible
- ✅ Parametro `apertures` è **opzionale** (`Optional[List[Polygon]] = None`)
- ✅ Se `None` o lista vuota → comportamento identico a prima (no buchi)
- ✅ Parser, packing, export → **ZERO modifiche**

### API Routes
**File:** `api/routes/packing.py`

Nessuna modifica necessaria! Le aperture sono già presenti in `preview_data["apertures"]` e vengono passate automaticamente tramite:
```python
placed_all, validated_customs = pack_wall(
    polygon=wall_exterior,
    apertures=apertures,  # Già presente!
    ...
)
```

---

## 🎓 DETTAGLI TECNICI

### Shapely Operations
1. **`unary_union(apertures)`**: Fonde aperture sovrapposte in una sola geometria
2. **`wall.difference(apertures_union)`**: Sottrae le aperture dalla parete
3. **`polygon.interiors`**: Restituisce i buchi interni (coordinate rings)
4. **`buffer(0)`**: Pulisce topologia mantenendo i buchi

### Geometry Types Gestiti
- `Polygon` con 0+ `interiors` (buchi)
- `MultiPolygon` → usa parte più grande
- `GeometryCollection` → fallback a lista geometrie

### Performance
- **Before:** 0 operazioni extra (ma blocchi entravano in finestre!)
- **After:** 1 `unary_union()` + 1 `difference()` all'inizio del clipping
- **Complessità:** O(N + M) dove N = aperture, M = blocchi (era O(N×M) con Opzione B)

---

## ✅ CHECKLIST IMPLEMENTAZIONE

- [x] Aggiunto parametro `apertures` a `clip_all_blocks_to_wall_geometry()`
- [x] Aggiunto parametro `apertures` a `clip_customs_to_wall_geometry()`
- [x] Implementato filtro aperture (>1m², <80% parete)
- [x] Implementato creazione buchi con `difference()`
- [x] Gestione `MultiPolygon` (usa parte più grande)
- [x] Logging dettagliato per debug
- [x] Test unitario (`test_aperture_clipping.py`)
- [x] Passaggio apertures da `pack_wall()` al clipping
- [x] Verifica sintassi (0 errori)
- [ ] Test integrazione con file reale
- [ ] Verifica su finestre circolari
- [ ] Test produzione con progetti utente

---

## 🐛 DEBUGGING

### Se i blocchi ANCORA entrano nelle finestre:

1. **Verifica aperture rilevate:**
   ```python
   print(f"Aperture: {len(apertures)}")
   for i, ap in enumerate(apertures):
       print(f"  {i+1}: area={ap.area}, bounds={ap.bounds}")
   ```

2. **Verifica filtro:**
   ```
   Cercare log: "📋 Filtraggio X aperture"
   Verificare: "✅ Apertura X VALIDA"
   ```

3. **Verifica buchi creati:**
   ```
   Cercare log: "🚪 Buchi interni: X"
   Se 0 → problema nella sottrazione!
   ```

4. **Verifica buffer(0):**
   ```
   Cercare log: "buffer(0) ha modificato i buchi"
   Se sì → geometria invalida, serve fix
   ```

---

## 📚 RIFERIMENTI

- **Issue originale:** Custom blocks entering window apertures
- **Soluzione discussa:** Options A vs B vs C analysis
- **Test file:** `test/test_wall_spaced.svg` (12000×3500mm, 3 apertures)
- **Shapely docs:** https://shapely.readthedocs.io/en/stable/manual.html#object.difference

---

## 👨‍💻 AUTHOR

**Implementation Date:** 7 Ottobre 2025  
**Tested on:** Python 3.12, Shapely 2.x  
**Status:** ✅ Implementato, ⏳ Pending integration testing

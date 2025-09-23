# 🚪 Requisiti Sistema Porte e Finestre - Wall-Build v3

## 📊 Analisi Stato Attuale vs Requisiti Richiesti

### ✅ Funzionalità Attualmente Implementate

#### 1. Sistema Base Aperture
- **`main.py`**: Funzione `pack_wall()` accetta parametro `apertures: List[Polygon]`
- **`main.py`**: Funzione `_draw_apertures()` per visualizzazione porte/finestre in DXF
- **`parsers/fallbacks.py`**: Creazione aperture di esempio (porta: 1000-2200x2100, finestra: 1500x1200)
- **`templates/index.html`**: Configurazione colori per porte/finestre nell'interfaccia
- **Sistema Keep-Out**: Buffer automatico attorno ad aperture (`KEEP_OUT_MM = 2.0`)

#### 2. Sistema Materiali e Calcoli
- **Calcolo spessore chiusura**: `materiale + guide = chiusura` (es: 14mm + 75mm = 89mm)
- **Sistema moretti**: Calcolo automatico per pareti che non arrivano al soffitto
- **Posizioni parete**: `LIBERA`, `APPOGGIATA_UN_LATO`, `APPOGGIATA_DUE_LATI`, `INCASSATA`
- **Strategie montaggio**: Determinazione punto di partenza basato su muri esistenti

### ❌ Funzionalità Mancanti - Requisiti da Implementare

## 🎯 Specifiche Funzionali Richieste

### 1. **Gestione Intelligente Chiusure Porte/Finestre**

#### 1.1 Logica Decisionale Chiusura
```python
# NUOVO SISTEMA DA IMPLEMENTARE
class DoorWindowClosureManager:
    def determine_closure_decision(self, aperture: Aperture, wall_context: WallContext) -> ClosureDecision:
        """
        Determina se e come chiudere un'apertura basandosi su:
        - Tipo apertura (porta/finestra)  
        - Posizione nella parete
        - Contesto muri esistenti
        - Configurazione progetto
        """
```

#### 1.2 Opzioni di Chiusura Richieste
- **Nessuna chiusura**: Apertura lasciata libera
- **Chiusura parziale superiore**: Solo sopra l'apertura (finestre)
- **Chiusura parziale laterale**: Solo sui lati (porte scorrevoli)
- **Chiusura completa**: Attorno a tutto il perimetro
- **Chiusura intelligente**: Basata su regole automatiche

### 2. **Sistema Calcolo Spessori per Aperture**

#### 2.1 Spessori Differenziati
```python
# NUOVO SISTEMA DA IMPLEMENTARE  
class ApertureThicknessCalculator:
    def calculate_aperture_closure_thickness(self, 
                                           aperture: Aperture,
                                           main_wall_thickness: int,
                                           closure_type: ClosureType) -> ThicknessSpec:
        """
        Calcola spessori specifici per chiusure aperture:
        - Stesso spessore parete principale: per continuità strutturale
        - Spessore ridotto: per ottimizzazione materiale
        - Spessore personalizzato: per esigenze specifiche
        """
```

#### 2.2 Configurazioni Spessore
- **Standard**: Uguale alla parete principale (es: 89mm)
- **Ridotto**: Materiale più sottile per risparmio (es: 10mm + 50mm = 60mm)
- **Personalizzato**: Definito dall'utente per ogni apertura
- **Automatico**: Basato su regole intelligenti (tipo apertura + posizione)

### 3. **Gestione Avanzata Moretti per Aperture**

#### 3.1 Moretti Orizzontali (Sopra Aperture)
```python
# NUOVO SISTEMA DA IMPLEMENTARE
class ApertureMorettiManager:
    def calculate_horizontal_moretti(self, aperture: Aperture, wall_height: int) -> MorettiSpec:
        """
        Calcola moretti orizzontali per spazio sopra porte/finestre:
        - Altezza disponibile sopra apertura
        - Numero righe blocchi standard possibili
        - Altezza moretti per spazio rimanente
        """
```

#### 3.2 Moretti Verticali (Lati Aperture)
```python  
def calculate_vertical_moretti(self, aperture: Aperture, wall_context: WallContext) -> MorettiSpec:
    """
    Calcola moretti verticali per spazi laterali stretti:
    - Spazi < larghezza blocco minimo (413mm)
    - Altezza dall'apertura al soffitto/terra
    - Spessore uguale alla chiusura
    """
```

#### 3.3 Configurazioni Moretti Specifiche
- **Moretti superiori**: Per spazi sopra finestre basse
- **Moretti laterali**: Per spazi stretti ai lati
- **Moretti inferiori**: Per finestre sopraelevate
- **Moretti angolari**: Per aperture vicino agli angoli

### 4. **Sistema Moduli a L per Angoli**

#### 4.1 Riconoscimento Configurazioni L
```python
# NUOVO SISTEMA DA IMPLEMENTARE
class LShapedModuleManager:
    def detect_l_shape_opportunities(self, aperture: Aperture, wall_corner: Corner) -> List[LShapeConfig]:
        """
        Identifica opportunità per moduli a L:
        - Aperture vicine agli angoli (< 826mm dal bordo)
        - Spazio disponibile per braccio L
        - Ottimizzazione rispetto a blocchi separati
        """
```

#### 4.2 Calcolo Moduli L
- **Braccio principale**: Lungo la parete principale
- **Braccio secondario**: Verso l'apertura o l'angolo
- **Ottimizzazione taglio**: Minimizzare scarti da pannello
- **Vincoli strutturali**: Resistenza e stabilità

### 5. **Algoritmo Packing Aperture-Aware**

#### 5.1 Strategia Posizionamento Moduli
```python
# ESTENSIONE SISTEMA ESISTENTE
def pack_wall_with_intelligent_apertures(self, 
                                        wall: Polygon,
                                        apertures: List[Aperture],
                                        project_config: ProjectMaterialConfig) -> PackingResult:
    """
    Packing intelligente considerando:
    1. Analisi chiusure necessarie per ogni apertura
    2. Calcolo spessori differenziati  
    3. Posizionamento ottimale moretti
    4. Integrazione moduli a L
    5. Minimizzazione scarti totali
    """
```

#### 5.2 Priorità Posizionamento
1. **Zone fisse**: Muri esistenti → punto di partenza
2. **Zone aperture**: Chiusure con spessori calcolati
3. **Zone standard**: Riempimento con blocchi normali
4. **Zone moretti**: Spazi rimanenti < blocco minimo

### 6. **Interfaccia Utente Estesa**

#### 6.1 Configurazione Aperture
```html
<!-- NUOVO PANNELLO DA IMPLEMENTARE -->
<div class="aperture-config-panel">
    <h3>🚪 Configurazione Porte e Finestre</h3>
    
    <!-- Per ogni apertura rilevata -->
    <div class="aperture-item">
        <h4>Apertura #1 - Porta (1200x2100mm)</h4>
        
        <div class="closure-options">
            <label>Tipo Chiusura:</label>
            <select class="closure-type">
                <option value="none">Nessuna chiusura</option>
                <option value="partial-top">Solo sopra</option>
                <option value="partial-sides">Solo lati</option>
                <option value="complete">Completa</option>
                <option value="auto">Automatica</option>
            </select>
        </div>
        
        <div class="thickness-options">
            <label>Spessore Chiusura:</label>
            <select class="thickness-type">
                <option value="standard">Standard (89mm)</option>
                <option value="reduced">Ridotto (60mm)</option>
                <option value="custom">Personalizzato</option>
            </select>
        </div>
        
        <div class="moretti-options">
            <label>Gestione Moretti:</label>
            <input type="checkbox" checked> Calcolo automatico
            <input type="checkbox"> Moduli a L se possibile
        </div>
    </div>
</div>
```

#### 6.2 Visualizzazione Avanzata
- **Codifica colori**: Diversi colori per tipi di chiusura
- **Etichette spessori**: Visualizzazione spessori su ogni sezione
- **Linee moretti**: Indicazione posizioni moretti calcolati
- **Zone L**: Evidenziazione moduli a L proposti

### 7. **Sistema Export Esteso**

#### 7.1 Distinta Materiali Dettagliata
```python
# ESTENSIONE EXPORT ESISTENTE
def export_aperture_materials_list(self, packing_result: AperturePackingResult) -> Dict:
    """
    Export dettagliato materiali per aperture:
    - Blocchi standard per parete principale
    - Blocchi per chiusure (con spessori specifici)
    - Moretti orizzontali e verticali
    - Moduli L con dimensioni di taglio
    - Totali per tipologia e spessore
    """
```

#### 7.2 Schemi di Taglio Separati
- **Schema principale**: Blocchi parete standard
- **Schema chiusure**: Blocchi per aperture con spessori diversi
- **Schema moretti**: Tutti i moretti con quote specifiche
- **Schema moduli L**: Pezzi sagomati con misure precise

### 8. **API Endpoints Aggiuntivi**

#### 8.1 Nuovi Endpoints Richiesti
```python
# NUOVI ENDPOINT DA IMPLEMENTARE
@app.post("/pack-apertures-enhanced")
async def pack_with_intelligent_apertures(request: AperturePackingRequest):
    """Packing con gestione intelligente aperture"""

@app.post("/calculate-aperture-closures")  
async def calculate_aperture_closures(apertures: List[Aperture], config: ProjectConfig):
    """Calcolo decisioni chiusure per lista aperture"""

@app.post("/optimize-aperture-moretti")
async def optimize_moretti_for_apertures(wall: Wall, apertures: List[Aperture]):
    """Ottimizzazione posizionamento moretti considerando aperture"""

@app.get("/aperture-presets")
async def get_aperture_configuration_presets():
    """Preset configurazioni comuni per porte/finestre"""
```

## 🔧 Piano Implementazione Proposto

### Fase 1: Core Logic (Priorità Alta)
1. ✅ **ApertureClosureManager**: Logica decisionale chiusure
2. ✅ **ApertureThicknessCalculator**: Calcolo spessori differenziati
3. ✅ **ApertureMorettiManager**: Gestione moretti per aperture

### Fase 2: Algoritmi Avanzati (Priorità Alta)
4. ✅ **LShapedModuleManager**: Sistema moduli a L
5. ✅ **Estensione pack_wall()**: Integrazione logica aperture
6. ✅ **Ottimizzazione packing**: Considerazione spessori multipli

### Fase 3: Interfaccia Utente (Priorità Media)
7. ✅ **Pannelli configurazione**: UI per impostazioni aperture
8. ✅ **Visualizzazione avanzata**: Colori e etichette differenziate
9. ✅ **Preview real-time**: Aggiornamento dinamico configurazioni

### Fase 4: Export e Reporting (Priorità Media)
10. ✅ **Distinte dettagliate**: Export materiali per aperture
11. ✅ **Schemi taglio estesi**: Separazione per tipologia
12. ✅ **Report ottimizzazione**: Analisi risparmi con moduli L

### Fase 5: API e Integrazione (Priorità Bassa)
13. ✅ **Nuovi endpoint**: API per gestione aperture
14. ✅ **Preset configurazioni**: Template comuni
15. ✅ **Documentazione API**: Swagger per nuove funzioni

## 📋 Checklist Validazione Requisiti

### ✅ Requisiti Base Già Soddisfatti
- [x] Sistema materiali con calcolo spessori
- [x] Visualizzazione aperture in DXF
- [x] Buffer sicurezza attorno aperture
- [x] Configurazione colori porte/finestre

### ❌ Requisiti Critici Mancanti  
- [ ] **Logica decisionale chiusure**: Nessun sistema per decidere se/come chiudere
- [ ] **Spessori differenziati**: Un solo spessore per tutta la parete
- [ ] **Moretti per aperture**: Solo moretti generali per altezza parete
- [ ] **Moduli a L**: Nessun sistema per forme complesse
- [ ] **Configurazione UI aperture**: Nessun pannello dedicato
- [ ] **Export dettagliato aperture**: Distinte non distinguono aperture

### ⚠️ Gap Prioritari da Colmare
1. **Sistema decisionale chiusure** - Attualmente tutte le aperture sono trattate uguali
2. **Calcolo spessori multipli** - Un progetto può avere solo un spessore 
3. **Interfaccia configurazione** - Utente non può configurare comportamento aperture
4. **Export differenziato** - Impossibile distinguere materiali per aperture vs parete

## 🎯 Benefici Implementazione Completa

### Per l'Utente
- ✅ **Controllo granulare**: Configurazione specifica ogni apertura
- ✅ **Ottimizzazione materiali**: Spessori ridotti dove possibile
- ✅ **Visualizzazione chiara**: Comprensione immediata progetto
- ✅ **Export professionale**: Distinte dettagliate per produzione

### Per il Sistema  
- ✅ **Flessibilità**: Gestione tutti i casi d'uso reali
- ✅ **Accuratezza**: Calcoli precisi per ogni configurazione
- ✅ **Scalabilità**: Architettura per funzioni future
- ✅ **Integrazione**: Coerenza con sistema esistente

---

# 🔍 AGGIORNAMENTO ANALISI - Requisiti Aggiuntivi

## 🏗️ 4. SISTEMA CONTROPARETI

### ❌ Funzionalità Completamente Mancanti

#### 4.1 Opzione Controparete in Progettazione
**Stato Attuale**: ❌ **ASSENTE**
- Nessuna opzione "controparete" nell'interfaccia utente
- Sistema progettato solo per pareti normali a due facce
- Mancanza totale di logica per pareti monofaccia

#### 4.2 Moduli Prima Fila Speciali  
**Stato Attuale**: ❌ **ASSENTE**
```python
# RICHIESTO - DA IMPLEMENTARE
class ControparetiManager:
    def create_first_row_modules(self):
        """
        Moduli prima fila: moraletti che sporgono SOPRA e SOTTO
        (vs moduli normali che sporgono solo sotto)
        """
```

#### 4.3 Moduli Altri Ruoli Capovolti
**Stato Attuale**: ❌ **ASSENTE**  
```python  
# RICHIESTO - DA IMPLEMENTARE
def flip_modules_for_contropareti(modules: List[Module]) -> List[Module]:
    """
    Tutti i moduli (eccetto prima fila) capovolti:
    moraletti sporgono SOPRA invece che SOTTO
    """
```

#### 4.4 Calcolo Quantità Monofaccia
**Stato Attuale**: ❌ **CRITICO**
- Distinte calcolano sempre moduli a due facce  
- Nessun sistema per quantità ridotte (solo una facciata)
- Export e calcoli costi completamente errati per contropareti

### 📋 Requisiti Contropareti da Implementare
1. ✅ **Opzione UI**: Checkbox "Controparete" in configurazione progetto
2. ✅ **Logica Prima Fila**: Moduli speciali con moraletti bidirezionali  
3. ✅ **Logica Altri Moduli**: Sistema capovolgimento automatico
4. ✅ **Calcolo Quantità**: Divisione per 2 nelle distinte (solo una faccia)
5. ✅ **Fissaggio**: Sistema piastre per ancoraggio a muro esistente
6. ✅ **Export Differenziato**: Distinte e DXF specifici per contropareti

---

## 🎯 5. GESTIONE MODULI A FINE MURO

### ⚠️ Comportamento Attuale vs Richiesto

#### 5.1 Stato Attuale - Algoritmo Esistente
**File**: `main.py` - funzione `pack_wall()`
```python
# COMPORTAMENTO ATTUALE: 
# Sistema cerca di minimizzare pezzi custom, ma può creare blocchi piccoli
# Logica: prova diversi ordini di blocchi standard per ottimizzare
```

#### 5.2 Comportamento Richiesto  
**Richiesta**: ❌ **NON IMPLEMENTATO**
```python
# RICHIESTO - DA MODIFICARE
def end_wall_strategy(remaining_space: float, block_widths: List[int]) -> Dict:
    """
    SEMPRE usare modulo standard PIÙ GRANDE disponibile
    e tagliarlo alla misura esatta fine parete
    NON creare pezzi piccoli standard
    """
```

#### 5.3 Gap Identificato
- **Attuale**: Sistema può piazzare blocco piccolo (413mm) a fine muro
- **Richiesto**: Sempre modulo grande (1239mm) tagliato alla misura necessaria  
- **Impatto**: Meno sprechi di materiale, produzione più efficiente

### � Modifiche Fine Muro Richieste
1. ✅ **Algoritmo End-Wall**: Forzare sempre modulo più grande disponibile
2. ✅ **Taglio Automatico**: Calcolo misura esatta taglio
3. ✅ **Etichettatura**: Indicare "TAGLIO FINE MURO" nelle distinte
4. ✅ **Validazione**: Controllo che non si creino micro-pezzi

---

## 🔧 6. MODULI FORATI E ASSEMBLAGGIO

### ❌ Sistema Moduli Forati - COMPLETAMENTE ASSENTE

#### 6.1 Riconoscimento Moduli Forati
**Stato Attuale**: ❌ **ASSENTE**
```python
# RICHIESTO - DA IMPLEMENTARE COMPLETAMENTE
class ModuliForatiManager:
    def identify_drilled_modules(self, placed_modules: List[Dict]) -> List[Dict]:
        """
        Identifica moduli che necessitano foratura:
        - SEMPRE: Prima fila (per fissaggio base)  
        - OPZIONALE: Ultima fila (scelta progetto per progetto)
        """
```

#### 6.2 Differenziazione Distinte
**Stato Attuale**: ❌ **CRITICO**
- Export non distingue moduli forati da normali
- Produzione non ha info su quali forare
- Nessuna indicazione posizioni fori

#### 6.3 Gestione Ultima Fila Opzionale
**Stato Attuale**: ❌ **ASSENTE**  
```html
<!-- RICHIESTO - DA IMPLEMENTARE -->
<div class="drilling-config">
    <label>
        <input type="checkbox" id="drillLastRow"> 
        Forare ultima fila
    </label>
    <small>Ultima fila con moduli forati o normali</small>
</div>
```

### ❌ Sistema Assemblaggio - LOGICA MANCANTE

#### 6.4 Moduli Non-Assemblabili  
**Stato Attuale**: ❌ **LOGICA ASSENTE**
```python
# RICHIESTO - DA IMPLEMENTARE
class AssemblyManager:
    def determine_assembly_status(self, module: Dict, wall_config: WallConfig) -> str:
        """
        Determina se modulo va pre-assemblato:
        - NON assemblare: ultima fila se va a soffitto
        - NON assemblare: ultima colonna se fissata entrambi i lati  
        - ASSEMBLARE: tutti gli altri casi
        """
```

#### 6.5 Condizioni Non-Assemblaggio Identificate
**Mancanti**:
1. **Ultima fila + soffitto**: Spazio insufficiente per inserimento pre-assemblato
2. **Ultima colonna + muri laterali**: Impossibile inserire modulo già assemblato
3. **Etichettatura distinte**: "DA ASSEMBLARE" vs "MONTAGGIO IN OPERA"

### ❌ Posizioni Moraletti Personalizzate - ASSENTE

#### 6.6 Distanze Moraletti Non-Standard
**Stato Attuale**: ❌ **INFORMAZIONE PERSA**
```python
# RICHIESTO - DA IMPLEMENTARE  
class MorettiPositionManager:
    def calculate_custom_moretti_distances(self, context: Dict) -> List[Dict]:
        """
        Calcola distanze moraletti per:
        - Porte/finestre: distanza adattata all'apertura
        - Fine muro: distanza dal bordo parete  
        - Standard: distanza normale del modulo
        """
```

#### 6.7 Export Distanze Produzione
**Mancante**: Nelle distinte non c'è indicazione distanze specifiche moraletti per produzione corretta

### 📋 Implementazioni Critiche Mancanti
1. ✅ **Sistema Foratura**: Identificazione prima/ultima fila + UI scelta
2. ✅ **Logica Assemblaggio**: Algoritmo condizioni non-assemblaggio  
3. ✅ **Distanze Moraletti**: Calcolo posizioni personalizzate
4. ✅ **Export Produzione**: Distinte con info foratura + assemblaggio
5. ✅ **UI Configurazione**: Pannelli per scelte foratura/assemblaggio

---

## 🎯 PRIORITÀ IMPLEMENTAZIONE AGGIORNATA

### 🔴 Priorità CRITICA (Blocca Produzione)
1. **Sistema Contropareti** - Quantità errate nelle distinte
2. **Moduli Forati** - Produzione non sa quali forare  
3. **Info Assemblaggio** - Perdita efficienza produttiva

### 🟡 Priorità ALTA (Ottimizzazione Importante)
4. **Fine Muro** - Strategia materiali subottimale
5. **Distanze Moraletti** - Precisione produzione

### 🟢 Priorità MEDIA (Miglioramenti)  
6. **Interfacce Utente** - Configurazioni mancanti
7. **Export Avanzati** - Informazioni dettagliate

---

## 📊 ANALISI IMPATTO BUSINESS

### 💰 Costi Attuali Stimati  
- **Contropareti**: Distinte +100% quantità (errore grave)
- **Moduli forati**: Tempo produzione +30% (manca info)  
- **Fine muro**: Spreco materiale ~15%
- **Assemblaggio**: Inefficienza montaggio +20%

### 🎯 Benefici Implementazione Completa
- **Accuracy**: Distinte accurate per tutti i tipi parete
- **Efficiency**: Produzione guidata senza errori
- **Cost**: Riduzione sprechi materiali significativa  
- **Speed**: Montaggio ottimizzato con pre-assemblaggio corretto

---

**📅 Documento creato**: 23/09/2025 15:30  
**🔄 Ultima revisione**: 23/09/2025 15:30  
**📊 Stato implementazione**: Analisi COMPLETA - Gap critici identificati
**🎯 Priorità**: MASSIMA - Blocchi produzione risolti
# Wall-Build API Reference

Documentazione completa di tutte le API REST del sistema Wall-Build con descrizioni dettagliate e firme dei metodi.

## Indice

1. [Autenticazione](#autenticazione)
2. [Gestione Progetti](#gestione-progetti)
3. [Progetti Salvati](#progetti-salvati)
4. [Packing e Elaborazione](#packing-e-elaborazione)
5. [Gestione File](#gestione-file)
6. [Materiali e Guide](#materiali-e-guide)
7. [Profili Sistema](#profili-sistema)
8. [Frontend e Utilità](#frontend-e-utilità)
9. [API Legacy](#api-legacy)

---

## Autenticazione

Tutte le API (eccetto `/auth/register`, `/auth/login` e `/health`) richiedono un token JWT nell'header `Authorization: Bearer <token>`.

### POST `/auth/register`

Registra un nuovo utente nel sistema.

**Body:**
```json
{
  "username": "string",
  "email": "string",
  "password": "string",
  "full_name": "string (opzionale)",
  "company": "string (opzionale)"
}
```

**Validazione Password:**
- Minimo 8 caratteri
- Almeno una maiuscola
- Almeno una minuscola
- Almeno un numero
- Almeno un carattere speciale

**Risposta:**
```json
{
  "success": true,
  "message": "Utente registrato con successo",
  "user": {
    "id": 1,
    "username": "string",
    "email": "string",
    "full_name": "string",
    "company": "string",
    "is_active": true,
    "is_admin": false
  }
}
```

---

### POST `/auth/login`

Autentica l'utente e restituisce un token JWT.

**Body:**
```json
{
  "username": "string",
  "password": "string"
}
```

**Risposta:**
```json
{
  "access_token": "string (JWT token)",
  "token_type": "bearer",
  "expires_in": 3600
}
```

---

### POST `/auth/logout`

Effettua il logout dell'utente corrente.

**Headers:**
- `Authorization: Bearer <token>`

**Risposta:**
```json
{
  "success": true,
  "message": "Logout effettuato con successo"
}
```

---

### GET `/auth/me`

Restituisce il profilo dell'utente autenticato.

**Headers:**
- `Authorization: Bearer <token>`

**Risposta:**
```json
{
  "id": 1,
  "username": "string",
  "email": "string",
  "full_name": "string",
  "company": "string",
  "is_active": true,
  "is_admin": false
}
```

---

### PUT `/auth/me`

Aggiorna il profilo dell'utente autenticato.

**Headers:**
- `Authorization: Bearer <token>`

**Body:**
```json
{
  "full_name": "string (opzionale)",
  "company": "string (opzionale)"
}
```

---

### POST `/auth/change-password`

Cambia la password dell'utente autenticato.

**Headers:**
- `Authorization: Bearer <token>`

**Body:**
```json
{
  "old_password": "string",
  "new_password": "string"
}
```

---

## Amministrazione (Solo Admin)

### GET `/admin/users`

Restituisce la lista di tutti gli utenti (solo amministratori).

**Query Parameters:**
- `skip`: int (default: 0)
- `limit`: int (default: 100)

---

### GET `/admin/stats`

Restituisce statistiche del sistema (solo amministratori).

**Risposta:**
```json
{
  "success": true,
  "data": {
    "database": {
      "size_mb": 12.5,
      "tables": ["users", "saved_projects", "..."]
    },
    "expired_sessions_cleaned": 3,
    "timestamp": "2025-11-23T10:30:00"
  }
}
```

---

### POST `/admin/users/{username}/deactivate`

Disattiva un utente specifico (solo amministratori).

---

## Gestione Progetti

### GET `/projects`

Restituisce la lista dei progetti dell'utente autenticato.

**Query Parameters:**
- `skip`: int (default: 0)
- `limit`: int (default: 100)

---

### POST `/projects`

Crea un nuovo progetto per l'utente autenticato.

**Body:**
```json
{
  "name": "string",
  "description": "string (opzionale)",
  "tags": ["string"] (opzionale)
}
```

---

### GET `/projects/{project_id}`

Restituisce i dettagli di un progetto specifico.

---

### DELETE `/projects/{project_id}`

Elimina un progetto dell'utente autenticato.

---

## Progetti Salvati

### POST `/saved-projects/save`

Salva un progetto completato per riutilizzo futuro con snapshot del sistema.

**Body:**
```json
{
  "name": "string",
  "filename": "string",
  "session_id": "string",
  "profile_name": "string",
  "block_dimensions": {},
  "color_theme": {},
  "packing_config": {},
  "results": {},
  "extended_config": {},
  "wall_dimensions": "string",
  "total_blocks": 150,
  "efficiency": 92.5,
  "svg_path": "string (opzionale)",
  "pdf_path": "string (opzionale)",
  "json_path": "string (opzionale)"
}
```

**Risposta:**
```json
{
  "success": true,
  "message": "Progetto salvato con successo (con snapshot sistema)",
  "project_id": 123,
  "file_path": "/path/to/file",
  "snapshot_info": {
    "profiles_count": 3,
    "saved_at": "2025-11-23T10:30:00"
  }
}
```

**Nota:** Salva automaticamente uno snapshot completo del sistema (profili, materiali, configurazioni) per garantire la riproducibilità del progetto.

---

### GET `/saved-projects/list`

Recupera la lista dei progetti salvati dell'utente.

**Risposta:**
```json
{
  "success": true,
  "projects": [
    {
      "id": 123,
      "name": "Progetto Cucina",
      "filename": "cucina.dwg",
      "profile_name": "Sistema Standard",
      "algorithm_type": "bidirectional",
      "wall_dimensions": "5000x3000",
      "total_blocks": 150,
      "efficiency": 92.5,
      "created_at": "2025-11-23T10:30:00",
      "last_used": "2025-11-23T11:00:00",
      "has_svg": true,
      "has_pdf": true
    }
  ],
  "count": 1
}
```

---

### GET `/saved-projects/{project_id}`

Recupera i dettagli completi di un progetto salvato.

**Risposta:**
```json
{
  "success": true,
  "project": {
    "id": 123,
    "name": "Progetto Cucina",
    "filename": "cucina.dwg",
    "file_path": "/path/to/file",
    "block_dimensions": {},
    "color_theme": {},
    "packing_config": {},
    "results_summary": {},
    "extended_config": {},
    "wall_dimensions": "5000x3000",
    "total_blocks": 150,
    "efficiency": 92.5,
    "svg_path": "/path/to/svg",
    "pdf_path": "/path/to/pdf",
    "json_path": "/path/to/json",
    "created_at": "2025-11-23T10:30:00",
    "last_used": "2025-11-23T11:00:00",
    "snapshot_info": {
      "has_snapshot": true,
      "saved_at": "2025-11-23T10:30:00",
      "profiles_count": 3,
      "snapshot_version": "1.0"
    },
    "preview_image": "base64_png_data",
    "blocks_standard": []
  }
}
```

---

### POST `/saved-projects/{project_id}/restore-session`

Ricrea una sessione temporanea dai dati del progetto salvato per consentire download (PDF, JSON, DXF).

**Risposta:**
```json
{
  "success": true,
  "session_id": "restored_abc123",
  "message": "Sessione ripristinata per progetto 'Progetto Cucina'",
  "data": {
    "blocks_count": 150,
    "custom_count": 5,
    "has_geometry": true
  }
}
```

---

### DELETE `/saved-projects/{project_id}`

Elimina definitivamente un progetto salvato e tutti i suoi file associati.

**Risposta:**
```json
{
  "success": true,
  "message": "Progetto e tutti i file associati eliminati definitivamente",
  "project_name": "Progetto Cucina",
  "files_deleted": 4,
  "files_failed": 0
}
```

---

### DELETE `/saved-projects/all`

Elimina definitivamente tutti i progetti salvati dell'utente e tutti i file associati.

**Risposta:**
```json
{
  "success": true,
  "message": "Eliminati definitivamente 5 progetti dall'archivio",
  "deleted_count": 5,
  "total_files_deleted": 20,
  "total_files_failed": 0
}
```

---

### GET `/saved-projects/{project_id}/file`

Recupera il file originale di un progetto salvato (DWG/DXF/SVG).

**Risposta:** File download diretto

---

## Packing e Elaborazione

### POST `/packing/preview-conversion`

Genera anteprima della conversione del file caricato senza fare il packing. Applica offset poligono se configurato.

**Form Data:**
- `file`: UploadFile (SVG/DWG/DXF)
- `offset_config`: string (JSON opzionale)

**Offset Config:**
```json
{
  "enabled": true,
  "distance_mm": 50
}
```

**Risposta:**
```json
{
  "status": "success",
  "preview_session_id": "abc123",
  "preview_image": "base64_png_data",
  "measurements": {
    "area": 15.5,
    "area_total": "15.50",
    "max_width": "5000",
    "max_height": "3000",
    "apertures_count": "2",
    "perimeter": "16000",
    "geometry_type": "Rettangolare",
    "area_original": 16.0,
    "area_reduced": 15.5,
    "area_reduction_percent": 3.12
  },
  "conversion_details": {
    "original_filename": "parete.dwg",
    "file_format": "DWG",
    "file_size": "245.3 KB",
    "conversion_status": "success"
  },
  "validation_messages": [],
  "raw_bounds": [0, 0, 5000, 3000],
  "raw_area": 15500000,
  "apertures_data": [],
  "offset_applied_mm": 50,
  "offset_error": null,
  "wall_polygon_coords": [],
  "wall_polygon_original_coords": []
}
```

---

### POST `/packing/enhanced-pack-from-preview`

Elaborazione ottimizzata che riutilizza i dati già convertiti dal preview. **Evita la doppia conversione DWG/SVG**.

**Form Data:**
- `preview_session_id`: string (da `/preview-conversion`)
- `row_offset`: int (default: 826)
- `block_widths`: string (es: "1239,826,413")
- `project_name`: string
- `color_theme`: string (JSON)
- `block_dimensions`: string (JSON)
- `material_config`: string (JSON)
- `vertical_spaces`: string (JSON opzionale)
- `algorithm_type`: string ("bidirectional" o "small")
- `moraletti_config`: string (JSON opzionale per Small Algorithm)

**Risposta:**
```json
{
  "session_id": "xyz789",
  "status": "success",
  "wall_bounds": [0, 0, 5000, 3000],
  "wall_area": 15500000,
  "wall_perimeter": 16000,
  "blocks_standard": [],
  "blocks_custom": [],
  "apertures": [],
  "summary": {},
  "config": {},
  "metrics": {},
  "enhanced": true,
  "automatic_measurements": {},
  "blocks_with_measurements": {},
  "cutting_list": {},
  "production_parameters": {}
}
```

---

### POST `/packing/upload`

Upload SVG/DWG e processamento completo con preview (route legacy, preferire `enhanced-pack-from-preview`).

**Form Data:**
- `file`: UploadFile
- `row_offset`: int
- `block_widths`: string
- `project_name`: string
- `color_theme`: string (JSON)
- `block_dimensions`: string (JSON)
- `vertical_spaces`: string (JSON opzionale)
- `offset_config`: string (JSON opzionale)

---

### POST `/packing/enhanced-pack`

Enhanced upload e processamento completo con calcoli automatici delle misure (include parametri materiali).

**Form Data:** Come `/enhanced-pack-from-preview` ma con `file` invece di `preview_session_id`

---

### GET `/packing/preview/{session_id}`

Genera immagine preview per sessione.

**Query Parameters:**
- `color_theme`: string (JSON opzionale per aggiornare i colori)

**Risposta:**
```json
{
  "image": "base64_png_data"
}
```

---

### POST `/packing/reconfigure`

Riconfigurazione parametri su sessione esistente.

**Form Data:**
- `session_id`: string
- `row_offset`: int
- `block_widths`: string

---

## Gestione File

### GET `/files/download/{session_id}/{format}`

Download risultati in vari formati: JSON, PDF, DXF, DXF-STEP5.

**Parametri URL:**
- `session_id`: ID sessione
- `format`: "json" | "pdf" | "dxf" | "dxf-step5"

**Formati Supportati:**

1. **JSON**: Distinta base completa con tutti i blocchi
2. **PDF**: Documento professionale multipage (3 pagine A4 landscape)
   - Pagina 1: Schema parete con blocchi
   - Pagina 2: Distinta materiali e taglio
   - Pagina 3: Note tecniche
3. **DXF**: Schema tecnico CAD (modo technical)
4. **DXF-STEP5**: Visualizzazione Step 5 con misure e dettagli

**Risposta:** File download diretto

---

### GET `/files/session/{session_id}`

Ottiene informazioni sulla sessione.

**Risposta:**
```json
{
  "session_id": "abc123",
  "wall_bounds": [0, 0, 5000, 3000],
  "summary": {},
  "custom_count": 5,
  "metrics": {},
  "config": {},
  "timestamp": "2025-11-23T10:30:00",
  "enhanced": true
}
```

---

## Materiali e Guide

### GET `/api/v1/materials/`

Restituisce tutti i materiali disponibili.

**Risposta:**
```json
[
  {
    "id": 1,
    "name": "Truciolato Standard",
    "type": "truciolare",
    "available_thicknesses": [10, 12, 14, 16, 18, 20, 22, 25],
    "density_kg_m3": 650,
    "moisture_resistance": false,
    "fire_class": "E",
    "supplier": "Fornitore XYZ",
    "notes": "Uso interno",
    "is_active": true,
    "created_at": "2025-11-23T10:00:00"
  }
]
```

---

### GET `/api/v1/materials/types`

Restituisce i tipi di materiale disponibili.

**Risposta:**
```json
{
  "types": [
    {"value": "truciolato", "label": "Truciolato"},
    {"value": "mdf", "label": "MDF"},
    {"value": "compensato", "label": "Compensato"},
    {"value": "osb", "label": "OSB"},
    {"value": "altro", "label": "Altro"}
  ]
}
```

---

### GET `/api/v1/materials/{material_id}`

Restituisce un materiale specifico per ID.

---

### GET `/api/v1/materials/type/{material_type}`

Restituisce materiali filtrati per tipo.

---

### GET `/api/v1/materials/guides/`

Restituisce tutte le guide disponibili.

**Risposta:**
```json
[
  {
    "id": 1,
    "name": "Guida Standard 75mm",
    "type": "75mm",
    "width_mm": 75,
    "depth_mm": 25,
    "max_load_kg": 150,
    "material_compatibility": ["truciolato", "mdf"],
    "manufacturer": "Produttore ABC",
    "model_code": "G75-STD",
    "price_per_meter": 12.50,
    "is_active": true,
    "created_at": "2025-11-23T10:00:00"
  }
]
```

---

### GET `/api/v1/materials/guides/types`

Restituisce i tipi di guida disponibili.

---

### GET `/api/v1/materials/guides/{guide_id}`

Restituisce una guida specifica per ID.

---

### GET `/api/v1/materials/guides/type/{guide_type}`

Restituisce guide filtrate per tipo.

---

### POST `/api/v1/materials/configs/`

Crea una nuova configurazione materiali per un progetto.

**Body:**
```json
{
  "project_name": "Progetto Cucina",
  "material_id": 1,
  "material_thickness_mm": 18,
  "guide_id": 1,
  "wall_position": "libera",
  "ceiling_height_mm": 2700,
  "existing_walls_sides": ["left", "right"]
}
```

---

### GET `/api/v1/materials/configs/`

Restituisce tutte le configurazioni dell'utente corrente.

---

### GET `/api/v1/materials/configs/{project_name}`

Restituisce la configurazione di un progetto specifico.

---

### POST `/api/v1/materials/calculate`

Calcola tutti i parametri tecnici per una configurazione (spessore + guide = chiusura).

**Body:**
```json
{
  "material_thickness_mm": 18,
  "guide_width_mm": 75,
  "wall_position": "libera",
  "existing_walls_sides": ["left"],
  "ceiling_height_mm": 2700
}
```

**Risposta:**
```json
{
  "closure_thickness_mm": 103,
  "mounting_strategy": {
    "type": "freestanding",
    "requires_floor_support": true,
    "requires_ceiling_support": true
  },
  "moretti_parameters": {
    "required": true,
    "height_mm": 150,
    "spacing_mm": 600,
    "quantity": 8
  },
  "insertion_sequence": {
    "step1": "Posizionare guide a pavimento",
    "step2": "Inserire moraletti nelle guide",
    "step3": "Posizionare pannelli laterali"
  },
  "technical_notes": [
    "Verificare planarità pavimento",
    "Controllare verticalità con livella"
  ]
}
```

---

### POST `/api/v1/materials/calculate/closure`

Calcolo semplice spessore chiusura: materiale + guida = chiusura totale.

**Body:**
```json
{
  "material_thickness": 14,
  "guide_width": 75
}
```

**Risposta:**
```json
{
  "material_thickness_mm": 14,
  "guide_width_mm": 75,
  "closure_thickness_mm": 103,
  "calculation": "14mm + 75mm = 103mm",
  "example": "Esempio: 14mm (truciolato) + 75mm (guide) = 103mm (chiusura)"
}
```

---

### POST `/api/v1/materials/validate`

Valida una combinazione materiale + guida + spessore.

**Body:**
```json
{
  "material_id": 1,
  "guide_id": 1,
  "thickness_mm": 18
}
```

---

### GET `/api/v1/materials/templates/`

Restituisce tutti i template pubblici.

---

### GET `/api/v1/materials/templates/user`

Restituisce i template dell'utente corrente.

---

### GET `/api/v1/materials/wall-positions`

Restituisce le posizioni parete disponibili.

**Risposta:**
```json
{
  "positions": [
    {
      "value": "libera",
      "label": "Parete Libera",
      "description": "Parete completamente indipendente"
    },
    {
      "value": "appoggiata_un_lato",
      "label": "Appoggiata a Un Lato",
      "description": "Parete appoggiata a un muro esistente"
    },
    {
      "value": "appoggiata_due_lati",
      "label": "Appoggiata a Due Lati",
      "description": "Parete tra due muri esistenti"
    },
    {
      "value": "incassata",
      "label": "Incassata",
      "description": "Parete completamente incassata"
    }
  ]
}
```

---

### GET `/api/v1/materials/wall-sides`

Restituisce i lati parete disponibili.

---

### GET `/api/v1/materials/system/info`

Restituisce informazioni sul sistema parametri materiali.

**Risposta:**
```json
{
  "system": "Parametri Materiali Wall-Build",
  "version": "1.0.0",
  "statistics": {
    "materials_count": 15,
    "guides_count": 8,
    "templates_count": 5
  },
  "features": [
    "Calcolo automatico spessore chiusura",
    "Validazione combinazioni materiale/guida",
    "Strategia montaggio basata su posizione parete",
    "Calcolo parametri moretti per pareti non a soffitto",
    "Template predefiniti per progetti comuni"
  ]
}
```

---

## Profili Sistema

I profili sistema sono preset di configurazioni (dimensioni blocchi, moraletti, algoritmi) riutilizzabili.

### GET `/api/v1/profiles`

Ottiene tutti i profili sistema dell'utente corrente.

**Risposta:**
```json
[
  {
    "id": 1,
    "name": "Sistema Standard",
    "description": "Configurazione standard per pareti residenziali",
    "block_config": {
      "widths": [1239, 826, 413],
      "heights": [495, 495, 495]
    },
    "moraletti_config": {
      "thickness": 25,
      "height": 150,
      "heightFromGround": 50,
      "spacing": 600,
      "countLarge": 3,
      "countMedium": 2,
      "countSmall": 1
    },
    "algorithm_type": "small",
    "is_default": true,
    "is_active": true,
    "created_at": "2025-11-23T10:00:00",
    "updated_at": "2025-11-23T10:00:00"
  }
]
```

---

### GET `/api/v1/profiles/default`

Ottiene il profilo predefinito dell'utente.

---

### GET `/api/v1/profiles/{profile_id}`

Ottiene un profilo specifico per ID.

---

### POST `/api/v1/profiles`

Crea un nuovo profilo sistema.

**Body:**
```json
{
  "name": "Profilo Custom",
  "description": "Descrizione opzionale",
  "block_config": {
    "widths": [1200, 800, 400],
    "heights": [500, 500, 500]
  },
  "moraletti_config": {
    "thickness": 25,
    "height": 150,
    "heightFromGround": 50,
    "spacing": 600,
    "countLarge": 3,
    "countMedium": 2,
    "countSmall": 1
  },
  "algorithm_type": "small",
  "is_default": false
}
```

---

### PUT `/api/v1/profiles/{profile_id}`

Aggiorna un profilo esistente.

**Body:** Come POST ma tutti i campi sono opzionali.

---

### DELETE `/api/v1/profiles/{profile_id}`

Elimina un profilo sistema (soft delete).

---

### POST `/api/v1/profiles/{profile_id}/activate`

Attiva un profilo: restituisce le sue configurazioni per essere applicate al frontend.

**Risposta:**
```json
{
  "profile_id": 1,
  "profile_name": "Sistema Standard",
  "block_config": {
    "widths": [1239, 826, 413],
    "heights": [495, 495, 495]
  },
  "moraletti_config": {
    "thickness": 25,
    "height": 150,
    "heightFromGround": 50,
    "spacing": 600,
    "countLarge": 3,
    "countMedium": 2,
    "countSmall": 1
  },
  "algorithm_type": "small",
  "algorithm_description": "Costruzione Residenziale - senza sfalsamento blocchi"
}
```

---

## Frontend e Utilità

### GET `/`

Dashboard principale (protetta da autenticazione lato client).

**Risposta:** HTML page

---

### GET `/login`

Pagina di login del sistema.

**Risposta:** HTML page

---

### GET `/progetti`

Pagina progetti (richiede autenticazione lato client).

**Risposta:** HTML page

---

### GET `/upload`

Pagina upload (richiede autenticazione lato client).

**Risposta:** HTML page

---

### GET `/health`

Health check pubblico del servizio.

**Risposta:**
```json
{
  "status": "healthy",
  "timestamp": "2025-11-23T10:30:00",
  "version": "1.0.0",
  "auth_system": "active"
}
```

---

### GET `/api/config/blocks`

Restituisce la configurazione dinamica dei blocchi.

**Risposta:**
```json
{
  "block_widths": [1239, 826, 413],
  "block_height": 495,
  "block_widths_string": "1239,826,413"
}
```

---

## API Legacy

API per retrocompatibilità. **Non consigliate per nuove implementazioni.**

### POST `/legacy/pack`

Packing da payload JSON.

**Body:**
```json
{
  "polygon": [[x, y], ...],
  "apertures": [[[x, y], ...], ...],
  "block_widths": [1239, 826, 413],
  "block_height": 495,
  "row_offset": 826
}
```

---

### POST `/legacy/upload-file`

Carica file CAD e calcola packing (versione semplificata).

**Form Data:**
- `file`: UploadFile
- `row_offset`: int (default: 826)

---

### POST `/legacy/upload-svg`

Carica SVG e calcola packing (DEPRECATED - usare `/upload-file`).

---

## Note Tecniche

### Autenticazione JWT

- **Token Lifetime:** 60 minuti
- **Algorithm:** HS256
- **Storage:** localStorage (browser)
- **Header Format:** `Authorization: Bearer <token>`

### Limiti Upload

- **Dimensione Massima:** 10 MB
- **Formati Supportati:** SVG, DWG, DXF

### Sessioni

Le sessioni sono temporanee e vengono ripulite automaticamente dopo inattività.

### Snapshot Sistema

I progetti salvati includono uno snapshot completo del sistema per garantire la riproducibilità:
- Profili utente
- Configurazioni materiali
- Configurazioni guide
- Parametri di calcolo

Questo permette di ripristinare un progetto anche se le configurazioni del sistema cambiano nel tempo.

---

## Codici di Stato HTTP

- **200 OK:** Operazione completata con successo
- **201 Created:** Risorsa creata con successo
- **204 No Content:** Operazione completata senza contenuto di risposta
- **400 Bad Request:** Richiesta non valida
- **401 Unauthorized:** Autenticazione richiesta
- **403 Forbidden:** Accesso negato
- **404 Not Found:** Risorsa non trovata
- **413 Payload Too Large:** File troppo grande
- **500 Internal Server Error:** Errore interno del server
- **501 Not Implemented:** Funzionalità non implementata

---

## Glossario

- **Packing:** Processo di posizionamento ottimale dei blocchi sulla parete
- **Blocks Standard:** Blocchi standard predefiniti (Grande, Medio, Piccolo)
- **Blocks Custom:** Blocchi tagliati su misura per zone irregolari
- **Aperture:** Porte, finestre o altre aperture nella parete
- **Moraletti:** Elementi strutturali verticali di rinforzo
- **Offset Poligono:** Riduzione del perimetro della parete di una distanza specificata
- **Session:** Contesto temporaneo che mantiene i dati di elaborazione
- **Profile:** Preset di configurazioni riutilizzabili
- **Snapshot:** Fotografia dello stato del sistema al momento del salvataggio

---

**Versione Documento:** 1.0.0  
**Ultima Modifica:** 23 Novembre 2025  
**Sistema:** Wall-Build TAKTAK®

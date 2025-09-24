"""
Routes per operazioni di packing in Wall-Build
"""

import uuid
import datetime
import json
from typing import Dict
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
from fastapi.responses import JSONResponse

from api.auth import get_current_active_user
from api.models import User

router = APIRouter()

@router.post("/upload")
async def upload_and_process(
    file: UploadFile = File(...),
    row_offset: int = Form(826),
    block_widths: str = Form("1239,826,413"),
    project_name: str = Form("Progetto Parete"),
    color_theme: str = Form("{}"),
    block_dimensions: str = Form("{}"),
    current_user: User = Depends(get_current_active_user)
):
    """
    Upload SVG/DWG e processamento completo con preview - PROTETTO DA AUTENTICAZIONE.
    """
    # Import qui per evitare circular imports
    from main import (
        SESSIONS, PackingResult, parse_wall_file, pack_wall, opt_pass, 
        summarize_blocks, calculate_metrics, get_block_schema_from_frontend,
        get_default_block_schema, BLOCK_WIDTHS, BLOCK_HEIGHT, SIZE_TO_LETTER
    )
    
    try:
        # Log dell'attività dell'utente
        print(f"📁 File '{file.filename}' caricato da utente: {current_user.username}")
        
        # Validazione file
        file_ext = file.filename.lower().split('.')[-1] if '.' in file.filename else ''
        supported_formats = ['svg', 'dwg', 'dxf']
        
        if file_ext not in supported_formats:
            raise HTTPException(
                status_code=400, 
                detail=f"Formato file non supportato. Formati accettati: {', '.join(supported_formats).upper()}"
            )
        
        if file.size and file.size > 10 * 1024 * 1024:  # 10MB limit
            raise HTTPException(status_code=400, detail="File troppo grande (max 10MB)")
        
        # Lettura file
        file_bytes = await file.read()
        if not file_bytes:
            raise HTTPException(status_code=400, detail="File vuoto")
        
        # Parse parametri blocchi (backward compatibility)
        try:
            widths = [int(w.strip()) for w in block_widths.split(',') if w.strip()]
            if not widths:
                widths = BLOCK_WIDTHS
        except ValueError:
            widths = BLOCK_WIDTHS
        
        # Parse dimensioni blocchi personalizzate
        try:
            block_config = json.loads(block_dimensions) if block_dimensions else {}
            print(f"📦 [DEBUG] Block dimensions received: {block_config}")
            
            # Determina schema blocchi da usare (standard vs custom)
            block_schema = get_block_schema_from_frontend(block_config)
            
            # Estrai dimensioni effettive da usare
            final_widths = block_schema["block_widths"]
            final_height = block_schema["block_height"]
            final_size_to_letter = block_schema["size_to_letter"]
            
            print(f"🎯 Schema blocchi scelto: {block_schema['schema_type']}")
            print(f"   📏 Dimensioni: {final_widths}×{final_height}")
            print(f"   🔤 Mappatura: {final_size_to_letter}")
            
        except (ValueError, json.JSONDecodeError):
            print("⚠️ Block dimensions parsing failed, using defaults")
            block_schema = get_default_block_schema()
            final_widths = BLOCK_WIDTHS
            final_height = BLOCK_HEIGHT
            final_size_to_letter = SIZE_TO_LETTER
        
        # Parse tema colori
        try:
            color_config = json.loads(color_theme) if color_theme else {}
            print(f"🎨 [DEBUG] Color theme received: {color_config}")
        except (ValueError, json.JSONDecodeError):
            color_config = {}
            print("⚠️ Color theme parsing failed, using defaults")
        
        # Parse file (SVG o DWG)
        wall, apertures = parse_wall_file(file_bytes, file.filename)
        
        # Packing con dimensioni personalizzate
        placed, custom = pack_wall(
            wall, 
            final_widths,
            final_height,
            row_offset=row_offset,
            apertures=apertures if apertures else None
        )
        
        # Ottimizzazione
        placed, custom = opt_pass(placed, custom, final_widths)
        
        # Calcola metriche
        summary = summarize_blocks(placed, final_size_to_letter)
        metrics = calculate_metrics(placed, custom, wall.area)
        
        # Genera session ID
        session_id = str(uuid.uuid4())
        
        # Salva in sessione (con info utente e file bytes per salvare dopo)
        SESSIONS[session_id] = {
            "wall_polygon": wall,
            "apertures": apertures,
            "placed": placed,
            "customs": custom,
            "summary": summary,
            "config": {
                "block_widths": final_widths,
                "block_height": final_height,  
                "size_to_letter": final_size_to_letter,
                "block_schema": block_schema,
                "row_offset": row_offset,
                "project_name": project_name,
                "color_theme": color_config
            },
            "metrics": metrics,
            "timestamp": datetime.datetime.now(),
            "user_id": current_user.id,
            "username": current_user.username,
            "original_filename": file.filename,
            "file_bytes": file_bytes
        }
        
        # Formatta response
        minx, miny, maxx, maxy = wall.bounds
        
        return {
            "session_id": session_id,
            "status": "success",
            "wall_bounds": [minx, miny, maxx, maxy],
            "blocks_standard": [
                {
                    "id": i,
                    "x": float(p["x"]),
                    "y": float(p["y"]),
                    "width": float(p["width"]),
                    "height": float(p["height"]),
                    "type": p["type"]
                }
                for i, p in enumerate(placed)
            ],
            "blocks_custom": [
                {
                    "id": i,
                    "x": float(c["x"]),
                    "y": float(c["y"]),
                    "width": float(c["width"]),
                    "height": float(c["height"]),
                    "type": c["type"],
                    "ctype": c.get("ctype", 2),
                    "geometry": c["geometry"]
                }
                for i, c in enumerate(custom)
            ],
            "apertures": [
                {
                    "bounds": list(ap.bounds)
                }
                for ap in (apertures or [])
            ],
            "summary": summary,
            "config": {
                "block_widths": final_widths,
                "block_height": final_height,
                "size_to_letter": final_size_to_letter,
                "block_schema": block_schema,
                "row_offset": row_offset,
                "project_name": project_name
            },
            "metrics": metrics,
            "saved_file_path": None
        }
        
    except Exception as e:
        print(f"❌ Errore upload: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/preview/{session_id}")
async def get_preview_image(session_id: str):
    """
    Genera immagine preview per sessione.
    """
    # Import qui per evitare circular imports
    from main import SESSIONS, generate_preview_image
    
    try:
        if session_id not in SESSIONS:
            raise HTTPException(status_code=404, detail="Sessione non trovata")
        
        session = SESSIONS[session_id]
        
        # Genera preview
        preview_base64 = generate_preview_image(
            session["wall_polygon"],
            session["placed"],
            session["customs"],
            session["apertures"],
            session["config"].get("color_theme", {}),
            session["config"]
        )
        
        if not preview_base64:
            raise HTTPException(status_code=500, detail="Errore generazione preview")
        
        return {"image": preview_base64}
        
    except Exception as e:
        print(f"❌ Errore preview: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint semplificato per ora - gli altri li sistemiamo dopo
@router.post("/reconfigure")
async def reconfigure_packing(
    session_id: str = Form(...),
    row_offset: int = Form(826),
    block_widths: str = Form("1239,826,413")
):
    """Riconfigurazione parametri su sessione esistente."""
    from main import SESSIONS
    
    try:
        if session_id not in SESSIONS:
            raise HTTPException(status_code=404, detail="Sessione non trovata")
        
        # TODO: Implementare logica di riconfigurazione
        return {"status": "success", "session_id": session_id}
        
    except Exception as e:
        print(f"❌ Errore reconfig: {e}")
        raise HTTPException(status_code=500, detail=str(e))
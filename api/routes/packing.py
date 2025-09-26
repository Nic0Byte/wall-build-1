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

@router.post("/preview-conversion")
async def preview_file_conversion(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user)
):
    """
    Genera solo l'anteprima della conversione del file caricato senza fare il packing.
    Mostra la geometria convertita con le relative misure per validazione utente.
    """
    # Import qui per evitare circular imports
    from main import parse_wall_file, generate_preview_image
    
    try:
        # Log dell'attività dell'utente
        print(f"🔍 Preview conversione per file '{file.filename}' da utente: {current_user.username}")
        
        # Validazione file
        file_ext = file.filename.lower().split('.')[-1] if '.' in file.filename else ''
        supported_formats = ['svg', 'dwg', 'dxf']
        
        if file_ext not in supported_formats:
            raise HTTPException(
                status_code=400, 
                detail=f"Formato file non supportato. Formati accettati: {', '.join(supported_formats).upper()}"
            )
        
        if file.size and file.size > 10 * 1024 * 1024:  # 10MB limit
            raise HTTPException(status_code=413, detail="File troppo grande (max 10MB)")
        
        # Lettura contenuto file
        file_content = await file.read()
        if not file_content:
            raise HTTPException(status_code=400, detail="File vuoto")
        
        # Parse del file per estrarre geometria
        print(f"🔄 Parsing file: {file.filename} ({file_ext.upper()})")
        wall_exterior, apertures = parse_wall_file(file_content, file.filename)
        
        if not wall_exterior or wall_exterior.is_empty:
            raise HTTPException(status_code=400, detail="Nessuna geometria valida trovata nel file")
        
        # Calcola dimensioni e statistiche
        bounds = wall_exterior.bounds
        area = wall_exterior.area
        perimeter = wall_exterior.length
        
        # Calcola tipo di geometria
        coords = list(wall_exterior.exterior.coords)
        is_rectangle = len(coords) == 5 and coords[0] == coords[-1]  # Prima e ultima coordinate uguali
        is_complex = len(apertures) > 0 or not is_rectangle
        
        geometry_type = "Rettangolare"
        if is_complex and apertures:
            geometry_type = f"Complessa con {len(apertures)} aperture"
        elif is_complex:
            geometry_type = "Forma personalizzata"
        
        # Genera preview image senza blocks (solo outline)
        empty_placed = []
        empty_customs = []
        
        # Configurazione base per preview
        config = {
            "project_name": f"Preview - {file.filename}",
            "show_measurements": True,
            "preview_mode": True
        }
        
        preview_base64 = generate_preview_image(
            wall_exterior,
            empty_placed,
            empty_customs, 
            apertures,
            {},  # color_theme vuoto
            config,
            enhanced_info={"enhanced": False, "preview_only": True}
        )
        
        if not preview_base64:
            raise HTTPException(status_code=500, detail="Errore generazione preview")
        
        # Preparazione misure formattate
        measurements = {
            "area_total": f"{area / 1000000:.2f}",  # Converti da mm² a m²
            "max_width": f"{bounds[2] - bounds[0]:.0f}",  # maxx - minx 
            "max_height": f"{bounds[3] - bounds[1]:.0f}",  # maxy - miny
            "apertures_count": f"{len(apertures)}",
            "perimeter": f"{perimeter:.0f}",
            "geometry_type": geometry_type
        }
        
        # Dettagli conversione
        conversion_details = {
            "original_filename": file.filename,
            "file_format": file_ext.upper(),
            "file_size": f"{file.size / 1024:.1f} KB" if file.size else "N/A",
            "conversion_status": "success"
        }
        
        # Messaggi di validazione
        validation_messages = []
        
        # Validazione area
        if area < 1000000:  # < 1 m²
            validation_messages.append({
                "type": "warning",
                "message": "L'area della parete è molto piccola. Verifica che le unità di misura siano corrette."
            })
        elif area > 50000000:  # > 50 m²
            validation_messages.append({
                "type": "warning", 
                "message": "L'area della parete è molto grande. Verifica che le unità di misura siano corrette."
            })
        else:
            validation_messages.append({
                "type": "success",
                "message": "Dimensioni parete nell'intervallo normale."
            })
        
        # Validazione aperture
        if len(apertures) == 0:
            validation_messages.append({
                "type": "info",
                "message": "Nessuna apertura rilevata. La parete sarà completamente riempita con blocchi."
            })
        else:
            validation_messages.append({
                "type": "success", 
                "message": f"{len(apertures)} aperture rilevate correttamente."
            })
        
        # Validazione geometria
        if not is_rectangle and len(apertures) == 0:
            validation_messages.append({
                "type": "info",
                "message": "Geometria parete non rettangolare rilevata. Verranno generati blocchi custom per le zone irregolari."
            })
        
        print(f"✅ Preview generata - Area: {area/1000000:.2f}m², Aperture: {len(apertures)}")
        
        return {
            "status": "success",
            "preview_image": preview_base64,
            "measurements": measurements,
            "conversion_details": conversion_details,
            "validation_messages": validation_messages,
            "raw_bounds": bounds,
            "raw_area": area,
            "apertures_data": [{"bounds": list(ap.bounds)} for ap in apertures]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Errore preview conversione: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Errore interno: {str(e)}")

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
    from shapely.geometry import Polygon
    
    try:
        if session_id not in SESSIONS:
            raise HTTPException(status_code=404, detail="Sessione non trovata")
        
        session = SESSIONS[session_id]
        
        # Check if it's an enhanced session (data is wrapped in "data" key)
        if "data" in session and session.get("enhanced", False):
            # Enhanced session format
            data = session["data"]
            
            # Reconstruct wall_polygon from wall_bounds
            if "wall_bounds" in data:
                wall_bounds = data["wall_bounds"]
                wall_polygon = Polygon([
                    (wall_bounds[0], wall_bounds[1]),  # minx, miny
                    (wall_bounds[2], wall_bounds[1]),  # maxx, miny
                    (wall_bounds[2], wall_bounds[3]),  # maxx, maxy
                    (wall_bounds[0], wall_bounds[3])   # minx, maxy
                ])
            else:
                raise ValueError("wall_bounds non trovati nella sessione enhanced")
            
            # Extract other required data for preview
            placed = data.get("blocks_standard", [])
            customs = data.get("blocks_custom", []) 
            apertures_data = data.get("apertures", [])
            
            # Convert apertures format if needed
            apertures = []
            for ap in apertures_data:
                if "bounds" in ap:
                    bounds = ap["bounds"]
                    apertures.append(Polygon([
                        (bounds[0], bounds[1]),
                        (bounds[2], bounds[1]),
                        (bounds[2], bounds[3]),
                        (bounds[0], bounds[3])
                    ]))
            
            config = data.get("config", {})
            color_theme = config.get("color_theme", {})
            
            # Extract enhanced information
            enhanced_info = {
                "automatic_measurements": data.get("automatic_measurements", {}),
                "blocks_with_measurements": data.get("blocks_with_measurements", {}),
                "cutting_list": data.get("cutting_list", {}),
                "production_parameters": data.get("production_parameters", {}),
                "enhanced": True
            }
        else:
            # Standard session format  
            wall_polygon = session["wall_polygon"]
            placed = session["placed"]
            customs = session["customs"] 
            apertures = session["apertures"]
            color_theme = session["config"].get("color_theme", {})
            config = session["config"]
            enhanced_info = {"enhanced": False}
        
        # Genera preview
        preview_base64 = generate_preview_image(
            wall_polygon,
            placed,
            customs,
            apertures,
            color_theme,
            config,
            enhanced_info=enhanced_info  # Pass enhanced data
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

@router.post("/enhanced-pack")
async def enhanced_upload_and_process(
    file: UploadFile = File(...),
    row_offset: int = Form(826),
    block_widths: str = Form("1239,826,413"),
    project_name: str = Form("Progetto Parete"),
    color_theme: str = Form("{}"),
    block_dimensions: str = Form("{}"),
    material_config: str = Form("{}"),  # NEW: Material configuration parameters
    current_user: User = Depends(get_current_active_user)
):
    """
    Enhanced upload e processamento completo con calcoli automatici delle misure.
    Include parametri materiali, guide, posizionamento parete e calcolo moretti.
    """
    # Import qui per evitare circular imports
    from main import (
        SESSIONS, PackingResult, parse_wall_file, pack_wall, opt_pass, 
        summarize_blocks, calculate_metrics, get_block_schema_from_frontend,
        get_default_block_schema, BLOCK_WIDTHS, BLOCK_HEIGHT, SIZE_TO_LETTER,
        ENHANCED_PACKING_AVAILABLE, enhance_packing_with_automatic_measurements
    )
    
    try:
        # Log dell'attività dell'utente
        print(f"📁 Enhanced processing per file '{file.filename}' da utente: {current_user.username}")
        
        # Validazione file
        file_ext = file.filename.lower().split('.')[-1] if '.' in file.filename else ''
        supported_formats = ['svg', 'dwg', 'dxf']
        
        if file_ext not in supported_formats:
            raise HTTPException(
                status_code=400, 
                detail=f"Formato file non supportato. Formati accettati: {', '.join(supported_formats).upper()}"
            )
        
        if file.size and file.size > 10 * 1024 * 1024:  # 10MB limit
            raise HTTPException(status_code=413, detail="File troppo grande (max 10MB)")
        
        # Parse material configuration
        try:
            material_params = json.loads(material_config) if material_config != "{}" else {}
        except json.JSONDecodeError:
            material_params = {}
        
        print(f"🔧 Material parameters ricevuti: {material_params}")
        
        # Parse block dimensions from frontend
        try:
            block_dims = json.loads(block_dimensions)
        except json.JSONDecodeError:
            block_dims = {}
        
        # Parse color theme
        try:
            theme = json.loads(color_theme)  
        except json.JSONDecodeError:
            theme = {}
        
        # Get block schema (standard o custom)
        block_schema = get_block_schema_from_frontend(block_dims)
        
        # Generate unique session ID
        session_id = str(uuid.uuid4())
        
        # Save file content to memory for processing
        file_content = await file.read()
        await file.seek(0)  # Reset for potential reuse
        
        # Parse wall geometry
        print(f"🔍 Parsing file: {file.filename} ({file_ext})")
        wall_exterior, apertures = parse_wall_file(file_content, file.filename)
        
        if not wall_exterior or wall_exterior.is_empty:
            raise HTTPException(status_code=400, detail="Nessuna geometria valida trovata nel file")
        
        print(f"✅ Geometria parsed - Area parete: {wall_exterior.area/1000000:.2f} m²")
        print(f"📐 Aperture trovate: {len(apertures)}")
        
        # Convert block_widths string to list
        try:
            widths_list = [int(w.strip()) for w in block_widths.split(',') if w.strip()]
        except ValueError:
            widths_list = block_schema["block_widths"]
        
        # ===== ENHANCED PACKING LOGIC =====
        
        # Perform standard packing
        placed, custom = pack_wall(
            wall_exterior, 
            widths_list, 
            block_schema["block_height"],
            row_offset=row_offset, 
            apertures=apertures
        )
        
        # Calculate standard metrics
        summary = summarize_blocks(placed)
        metrics = calculate_metrics(placed, custom, wall_exterior.area)
        
        # Enhanced processing with automatic measurements (if available)
        enhanced_result = None
        if ENHANCED_PACKING_AVAILABLE and material_params:
            print("🚀 Applying enhanced packing with automatic measurements...")
            
            # Prepare standard packing result for enhancement
            standard_result = {
                "session_id": session_id,
                "status": "success",
                "wall_bounds": list(wall_exterior.bounds),
                "blocks_standard": placed,
                "blocks_custom": custom,
                "apertures": [{"bounds": list(ap.bounds)} for ap in apertures],
                "summary": summary,
                "config": {
                    "block_widths": widths_list,
                    "block_height": block_schema["block_height"],
                    "row_offset": row_offset,
                    "project_name": project_name
                },
                "metrics": metrics
            }
            
            # Apply enhanced calculations
            enhanced_result = enhance_packing_with_automatic_measurements(
                standard_result, 
                material_params
            )
            
            print(f"✅ Enhanced calculations completed")
            
        # Prepare final result
        if enhanced_result:
            result = enhanced_result
            result["enhanced"] = True
        else:
            # Fallback to standard result
            result = PackingResult(
                session_id=session_id,
                status="success", 
                wall_bounds=list(wall_exterior.bounds),
                blocks_standard=placed,
                blocks_custom=custom,
                apertures=[{"bounds": list(ap.bounds)} for ap in apertures],
                summary=summary,
                config={
                    "block_widths": widths_list,
                    "block_height": block_schema["block_height"], 
                    "row_offset": row_offset,
                    "project_name": project_name,
                    "block_schema": block_schema["schema_type"],
                    "color_theme": theme
                },
                metrics=metrics
            ).dict()
            result["enhanced"] = False
        
        # Apply optimization if available
        try:
            result = opt_pass(result)
            print("✅ Optimization pass applied")
        except Exception as e:
            print(f"⚠️ Optimization pass failed: {e}")
        
        # Store session
        SESSIONS[session_id] = {
            'data': result,
            'timestamp': datetime.datetime.now(),
            'user_id': current_user.id,
            'username': current_user.username,
            'filename': file.filename,
            'material_config': material_params,  # Store for future reference
            'enhanced': result.get("enhanced", False),
            'file_bytes': file_content,  # IMPORTANTE: salva i bytes del file per il salvataggio progetto
            'original_filename': file.filename
        }
        
        print(f"💾 Enhanced session {session_id} salvata per utente {current_user.username}")
        
        return JSONResponse(
            content=result,
            headers={
                "X-Enhanced-Processing": "true" if result.get("enhanced") else "false",
                "X-Session-ID": session_id
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Errore enhanced processing: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Errore interno del server: {str(e)}")
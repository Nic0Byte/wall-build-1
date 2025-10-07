"""
Routes per gestione file in Wall-Build
"""

import datetime
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter()

@router.get("/download/{session_id}/{format}")
async def download_result(session_id: str, format: str):
    """
    Download risultati in vari formati.
    """
    # Import qui per evitare circular imports
    from main import (
        SESSIONS, export_to_json, export_to_dxf,
        build_run_params, reportlab_available, ezdxf_available
    )
    from exporters.pdf_exporter import export_to_pdf_professional_multipage
    
    try:
        if session_id not in SESSIONS:
            raise HTTPException(status_code=404, detail="Sessione non trovata")
        
        session = SESSIONS[session_id]
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # ===== NUOVO: Gestione formato sessione enhanced vs standard =====
        if "data" in session and session.get("enhanced", False):
            # Sessione enhanced - estrai dati dal campo "data"
            data = session["data"]
            summary = data.get("summary", {})
            customs = data.get("blocks_custom", [])
            placed = data.get("blocks_standard", [])
            wall_polygon = session.get("wall_polygon")  # Salvataggio della geometria originale
            apertures = session.get("apertures", [])  # Salvataggio delle aperture originali
            config = data.get("config", {})
            project_name = config.get("project_name", "Progetto Parete")
            row_offset = config.get("row_offset", 826)
            print(f"🔧 Usando formato enhanced per session {session_id[:8]}")
        else:
            # Sessione standard - formato originale
            summary = session["summary"]
            customs = session["customs"]
            placed = session["placed"]
            wall_polygon = session["wall_polygon"]
            apertures = session["apertures"]
            config = session["config"]
            project_name = config.get("project_name", "Progetto Parete")
            row_offset = config.get("row_offset", 826)
            print(f"🔧 Usando formato standard per session {session_id[:8]}")
        
        if format.lower() == "json":
            # Export JSON
            filename = f"distinta_{session_id[:8]}_{timestamp}.json"
            json_path = export_to_json(
                summary,
                customs,
                placed,
                out_path=filename,
                params=build_run_params(row_offset),
                block_config=config
            )
            
            return FileResponse(
                json_path,
                media_type="application/json",
                filename=filename
            )
            
        elif format.lower() == "pdf":
            # Export PDF PROFESSIONALE MULTIPAGE (3 pagine A4 landscape)
            if not reportlab_available:
                raise HTTPException(status_code=501, detail="Export PDF non disponibile")
            
            filename = f"distinta_base_{session_id[:8]}_{timestamp}.pdf"
            pdf_path = export_to_pdf_professional_multipage(
                summary=summary,
                customs=customs,
                placed=placed,
                wall_polygon=wall_polygon,
                apertures=apertures,
                project_name=project_name,
                out_path=filename,
                params=build_run_params(row_offset),
                block_config=config,
                author="WallBuild TAKTAK®",
                revision="Auto"
            )
            
            return FileResponse(
                pdf_path,
                media_type="application/pdf",
                filename=filename
            )
            
        elif format.lower() == "dxf" or format.lower() == "dxf-step5":
            # Export DXF
            if not ezdxf_available:
                raise HTTPException(status_code=501, detail="Export DXF non disponibile")
            
            # Determina mode e filename in base al formato
            if format.lower() == "dxf-step5":
                mode = "step5"
                filename = f"step5_visual_{session_id[:8]}_{timestamp}.dxf"
                print(f"🎨 Export DXF Step 5 visualization per session {session_id[:8]}")
            else:
                mode = "technical"
                filename = f"schema_{session_id[:8]}_{timestamp}.dxf"
                print(f"📐 Export DXF technical per session {session_id[:8]}")
            
            # Prepara enhanced_info per Step 5
            enhanced_info = None
            if mode == "step5":
                enhanced_info = {
                    "enhanced": True,
                    "session_width": config.get("wall_width", "93"),
                    "automatic_measurements": {
                        "material_parameters": {
                            "material_type": config.get("material_type", "Malatime"),
                            "thickness": config.get("thickness", 18),
                            "density": config.get("density", 650),
                            "guide_width": config.get("guide_width", 75),
                            "guide_depth": config.get("guide_depth", 25),
                            "block_width": config.get("block_width", 625),
                            "block_height": config.get("block_height", 435),
                            "moretti_required": config.get("moretti_required", 9),
                            "moretti_height": config.get("moretti_height", 150),
                            "moretti_quantity": config.get("moretti_quantity", 8),
                            "final_thickness": config.get("final_thickness", 35)
                        },
                        "total_rows": session.get("metrics", {}).get("total_rows", 6),
                        "start_points": session.get("metrics", {}).get("start_points", 2),
                        "method": session.get("metrics", {}).get("method", "Standard")
                    }
                }
                
                # Se sessione enhanced, estrai dati reali
                if "data" in session and session.get("enhanced", False):
                    session_data = session["data"]
                    if "enhanced_info" in session_data:
                        enhanced_info.update(session_data["enhanced_info"])
            
            dxf_path = export_to_dxf(
                summary,
                customs,
                placed,
                wall_polygon,
                apertures,
                project_name=project_name,
                out_path=filename,
                params=build_run_params(row_offset),
                color_theme=config.get("color_theme", {}),
                block_config=config,
                mode=mode,
                enhanced_info=enhanced_info
            )
            
            return FileResponse(
                dxf_path,
                media_type="application/dxf",
                filename=filename
            )
            
        else:
            raise HTTPException(status_code=400, detail="Formato non supportato")
            
    except Exception as e:
        print(f"❌ Errore download: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/session/{session_id}")
async def get_session_info(session_id: str):
    """
    Ottieni informazioni sessione.
    """
    # Import qui per evitare circular imports
    from main import SESSIONS
    
    try:
        if session_id not in SESSIONS:
            raise HTTPException(status_code=404, detail="Sessione non trovata")
        
        session = SESSIONS[session_id]
        
        # ===== NUOVO: Gestione formato sessione enhanced vs standard =====
        if "data" in session and session.get("enhanced", False):
            # Sessione enhanced - estrai dati dal campo "data"
            data = session["data"]
            summary = data.get("summary", {})
            customs = data.get("blocks_custom", [])
            config = data.get("config", {})
            metrics = data.get("metrics", {})
            wall_polygon = session.get("wall_polygon")
            print(f"🔧 Session info enhanced per session {session_id[:8]}")
        else:
            # Sessione standard - formato originale
            summary = session["summary"]
            customs = session["customs"]
            config = session["config"]
            metrics = session["metrics"]
            wall_polygon = session["wall_polygon"]
            print(f"🔧 Session info standard per session {session_id[:8]}")
            
        minx, miny, maxx, maxy = wall_polygon.bounds if wall_polygon else (0, 0, 0, 0)
        
        return {
            "session_id": session_id,
            "wall_bounds": [minx, miny, maxx, maxy],
            "summary": summary,
            "custom_count": len(customs),
            "metrics": metrics,
            "config": config,
            "timestamp": session["timestamp"],
            "enhanced": session.get("enhanced", False)
        }
        
    except Exception as e:
        print(f"❌ Errore session info: {e}")
        raise HTTPException(status_code=500, detail=str(e))
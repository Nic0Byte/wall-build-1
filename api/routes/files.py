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
        SESSIONS, export_to_json, export_to_pdf, export_to_dxf,
        build_run_params, reportlab_available, ezdxf_available
    )
    
    try:
        if session_id not in SESSIONS:
            raise HTTPException(status_code=404, detail="Sessione non trovata")
        
        session = SESSIONS[session_id]
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if format.lower() == "json":
            # Export JSON
            filename = f"distinta_{session_id[:8]}_{timestamp}.json"
            json_path = export_to_json(
                session["summary"],
                session["customs"],
                session["placed"],
                out_path=filename,
                params=build_run_params(session["config"]["row_offset"]),
                block_config=session["config"]
            )
            
            return FileResponse(
                json_path,
                media_type="application/json",
                filename=filename
            )
            
        elif format.lower() == "pdf":
            # Export PDF
            if not reportlab_available:
                raise HTTPException(status_code=501, detail="Export PDF non disponibile")
            
            filename = f"report_{session_id[:8]}_{timestamp}.pdf"
            pdf_path = export_to_pdf(
                session["summary"],
                session["customs"],
                session["placed"],
                session["wall_polygon"],
                session["apertures"],
                project_name=session["config"]["project_name"],
                out_path=filename,
                params=build_run_params(session["config"]["row_offset"]),
                block_config=session["config"]
            )
            
            return FileResponse(
                pdf_path,
                media_type="application/pdf",
                filename=filename
            )
            
        elif format.lower() == "dxf":
            # Export DXF
            if not ezdxf_available:
                raise HTTPException(status_code=501, detail="Export DXF non disponibile")
            
            filename = f"schema_{session_id[:8]}_{timestamp}.dxf"
            dxf_path = export_to_dxf(
                session["summary"],
                session["customs"],
                session["placed"],
                session["wall_polygon"],
                session["apertures"],
                project_name=session["config"]["project_name"],
                out_path=filename,
                params=build_run_params(session["config"]["row_offset"]),
                color_theme=session["config"].get("color_theme", {}),
                block_config=session["config"]
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
        wall = session["wall_polygon"]
        minx, miny, maxx, maxy = wall.bounds
        
        return {
            "session_id": session_id,
            "wall_bounds": [minx, miny, maxx, maxy],
            "summary": session["summary"],
            "custom_count": len(session["customs"]),
            "metrics": session["metrics"],
            "config": session["config"],
            "timestamp": session["timestamp"]
        }
        
    except Exception as e:
        print(f"❌ Errore session info: {e}")
        raise HTTPException(status_code=500, detail=str(e))
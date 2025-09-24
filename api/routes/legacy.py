"""
Routes Legacy per compatibilità backward in Wall-Build
"""

from typing import Dict
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse

router = APIRouter()

@router.post("/pack")
async def pack_from_json(payload: Dict):
    """
    Body JSON atteso:
    {
      "polygon": [[x,y], ...],
      "apertures": [ [[...]], [[...]] ],
      "block_widths": [1239,826,413],      # opzionale
      "block_height": 495,                 # opzionale
      "row_offset": 826                    # opzionale
    }
    """
    # Import qui per evitare circular imports
    from main import (
        BLOCK_WIDTHS, BLOCK_HEIGHT, pack_wall, opt_pass,
        summarize_blocks, export_to_json, build_run_params, sanitize_polygon
    )
    from shapely.geometry import Polygon
    
    try:
        poly = Polygon(payload["polygon"])
        poly = sanitize_polygon(poly)

        apertures = []
        for ap in payload.get("apertures", []):
            apertures.append(Polygon(ap))

        widths = payload.get("block_widths", BLOCK_WIDTHS)
        height = int(payload.get("block_height", BLOCK_HEIGHT))
        row_offset = payload.get("row_offset", 826)

        placed, custom = pack_wall(poly, widths, height, row_offset=row_offset,
                                   apertures=apertures if apertures else None)
        placed, custom = opt_pass(placed, custom, widths)

        summary = summarize_blocks(placed)
        out_path = export_to_json(summary, custom, placed, out_path="distinta_wall.json", params=build_run_params(row_offset=row_offset))

        return JSONResponse({
            "summary": summary,
            "custom_count": len(custom),
            "json_path": out_path
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)

@router.post("/upload-file")
async def pack_from_file(file: UploadFile = File(...),
                        row_offset: int = Form(826)):
    """
    Carica un file CAD (SVG/DWG/DXF) e calcola il packing.
    """
    # Import qui per evitare circular imports
    from main import (
        BLOCK_WIDTHS, BLOCK_HEIGHT, parse_wall_file, pack_wall, 
        opt_pass, summarize_blocks, export_to_json, build_run_params
    )
    
    try:
        # Validazione formato
        file_ext = file.filename.lower().split('.')[-1] if '.' in file.filename else ''
        supported_formats = ['svg', 'dwg', 'dxf']
        
        if file_ext not in supported_formats:
            raise HTTPException(
                status_code=400, 
                detail=f"Formato non supportato. Formati accettati: {', '.join(supported_formats.upper())}"
            )
        
        file_bytes = await file.read()
        wall, apertures = parse_wall_file(file_bytes, file.filename)
        widths = BLOCK_WIDTHS
        height = BLOCK_HEIGHT

        placed, custom = pack_wall(wall, widths, height, row_offset=row_offset,
                                   apertures=apertures if apertures else None)
        placed, custom = opt_pass(placed, custom, widths)
        summary = summarize_blocks(placed)
        out_path = export_to_json(summary, custom, placed, out_path="distinta_wall.json", params=build_run_params(row_offset=row_offset))
        return JSONResponse({"summary": summary, "custom_count": len(custom), "json_path": out_path})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)

@router.post("/upload-svg")
async def pack_from_svg(file: UploadFile = File(...),
                        row_offset: int = Form(826)):
    """
    Carica un SVG (schema tuo) e calcola il packing.
    DEPRECATED: Usa /upload-file per supporto multi-formato.
    """
    # Import qui per evitare circular imports
    from main import (
        BLOCK_WIDTHS, BLOCK_HEIGHT, pack_wall, opt_pass,
        summarize_blocks, export_to_json, build_run_params
    )
    from parsers import parse_svg_wall
    
    try:
        svg_bytes = await file.read()
        wall, apertures = parse_svg_wall(svg_bytes)
        widths = BLOCK_WIDTHS
        height = BLOCK_HEIGHT

        placed, custom = pack_wall(wall, widths, height, row_offset=row_offset,
                                   apertures=apertures if apertures else None)
        placed, custom = opt_pass(placed, custom, widths)
        summary = summarize_blocks(placed)
        out_path = export_to_json(summary, custom, placed, out_path="distinta_wall.json", params=build_run_params(row_offset=row_offset))
        return JSONResponse({"summary": summary, "custom_count": len(custom), "json_path": out_path})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)
"""
Routes per l'applicazione Wall-Build
"""

from .frontend import router as frontend_router
from .packing import router as packing_router
from .files import router as files_router
from .legacy import router as legacy_router

__all__ = [
    "frontend_router",
    "packing_router", 
    "files_router",
    "legacy_router"
]
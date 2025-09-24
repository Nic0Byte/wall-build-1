"""
Logging Configuration per Wall-Build
Setup structlog per logging strutturato e professionale.
"""

import os
import sys
import logging
from typing import Any, Dict
from datetime import datetime

# Import configurazione
from .config import LOG_LEVEL, LOG_FORMAT, VERBOSE_LOGGING, OUTPUT_DIR

# Structured logging
try:
    import structlog
    STRUCTLOG_AVAILABLE = True
except ImportError:
    structlog = None
    STRUCTLOG_AVAILABLE = False

# ────────────────────────────────────────────────────────────────────────────────
# Logger Setup
# ────────────────────────────────────────────────────────────────────────────────

def setup_logging():
    """
    Configura il sistema di logging per Wall-Build.
    Supporta sia logging standard che structlog per output strutturato.
    """
    
    # Crea directory logs se non esiste
    log_dir = os.path.join(OUTPUT_DIR, "../logs")
    os.makedirs(log_dir, exist_ok=True)
    
    # Determina livello di log
    log_level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)
    
    # Configurazione base logging
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(os.path.join(log_dir, "wallbuild.log"))
        ]
    )
    
    if STRUCTLOG_AVAILABLE:
        return _setup_structlog(log_level, log_dir)
    else:
        # Fallback a logging standard
        return _setup_standard_logging()

def _setup_structlog(log_level: int, log_dir: str):
    """Setup structlog con configurazione avanzata."""
    
    # Processors per sviluppo (colorati e leggibili)
    dev_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(colors=True)
    ]
    
    # Processors per produzione (JSON)
    prod_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
    
    # Scegli processors in base al formato
    if LOG_FORMAT.lower() == "json":
        processors = prod_processors
    else:
        processors = dev_processors
    
    # Configura structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.WriteLoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    return structlog.get_logger("wallbuild")

def _setup_standard_logging():
    """Fallback a logging standard se structlog non disponibile."""
    logger = logging.getLogger("wallbuild")
    logger.warning("structlog non disponibile, usando logging standard")
    return logger

# ────────────────────────────────────────────────────────────────────────────────
# Logger Singleton
# ────────────────────────────────────────────────────────────────────────────────

# Logger globale
_logger = None

def get_logger(name: str = "wallbuild"):
    """
    Ottiene il logger configurato.
    
    Args:
        name: Nome del logger (default: "wallbuild")
        
    Returns:
        Logger configurato (structlog o standard)
    """
    global _logger
    if _logger is None:
        _logger = setup_logging()
    
    if STRUCTLOG_AVAILABLE:
        return structlog.get_logger(name)
    else:
        return logging.getLogger(name)

# ────────────────────────────────────────────────────────────────────────────────
# Helper Functions per Context
# ────────────────────────────────────────────────────────────────────────────────

def with_context(**kwargs) -> Dict[str, Any]:
    """
    Crea context per logging strutturato.
    
    Args:
        **kwargs: Context da aggiungere ai log
        
    Returns:
        Dict con context per il logger
    """
    return kwargs

def log_operation(operation: str, **context):
    """
    Logger per operazioni specifiche con timing.
    
    Args:
        operation: Nome operazione
        **context: Context aggiuntivo
        
    Returns:
        Context manager per logging con timing
    """
    logger = get_logger()
    
    class OperationLogger:
        def __init__(self):
            self.start_time = None
            
        def __enter__(self):
            self.start_time = datetime.now()
            
            if STRUCTLOG_AVAILABLE:
                logger.info(
                    f"Starting {operation}",
                    operation=operation,
                    **context
                )
            else:
                # Fallback logging standard
                ctx_str = " ".join(f"{k}={v}" for k, v in context.items()) if context else ""
                msg = f"Starting {operation}" + (f" [{ctx_str}]" if ctx_str else "")
                logger.info(msg)
            return self
            
        def __exit__(self, exc_type, exc_val, exc_tb):
            duration = datetime.now() - self.start_time
            duration_ms = duration.total_seconds() * 1000
            
            if STRUCTLOG_AVAILABLE:
                if exc_type is None:
                    logger.info(
                        f"Completed {operation}",
                        operation=operation,
                        duration_ms=duration_ms,
                        success=True,
                        **context
                    )
                else:
                    logger.error(
                        f"Failed {operation}",
                        operation=operation,
                        duration_ms=duration_ms,
                        success=False,
                        error=str(exc_val),
                        **context
                    )
            else:
                # Fallback logging standard
                ctx_str = " ".join(f"{k}={v}" for k, v in context.items()) if context else ""
                base_ctx = f" [{ctx_str}]" if ctx_str else ""
                
                if exc_type is None:
                    msg = f"Completed {operation} (duration={duration_ms:.1f}ms){base_ctx}"
                    logger.info(msg)
                else:
                    msg = f"Failed {operation} (duration={duration_ms:.1f}ms, error={exc_val}){base_ctx}"
                    logger.error(msg)
    
    return OperationLogger()

def log_request(request_id: str, method: str, path: str, **context):
    """
    Logger specifico per richieste HTTP.
    
    Args:
        request_id: ID univoco richiesta
        method: Metodo HTTP
        path: Path richiesta
        **context: Context aggiuntivo
    """
    logger = get_logger("api")
    logger.info(
        "HTTP Request",
        request_id=request_id,
        method=method,
        path=path,
        **context
    )

def log_packing_operation(session_id: str, filename: str, **context):
    """
    Logger specifico per operazioni di packing.
    
    Args:
        session_id: ID sessione
        filename: Nome file processato
        **context: Context aggiuntivo
    """
    logger = get_logger("packing")
    logger.info(
        "Packing Operation",
        session_id=session_id,
        filename=filename,
        **context
    )

# ────────────────────────────────────────────────────────────────────────────────
# Migration Helper per Print Statements
# ────────────────────────────────────────────────────────────────────────────────

def migrate_print(message: str, level: str = "info", **context):
    """
    Helper per migrare gradualmente da print() a logging.
    
    Args:
        message: Messaggio da loggare
        level: Livello di log (info, warning, error, debug)
        **context: Context aggiuntivo
    """
    logger = get_logger()
    
    # Mantiene output su console se in debug
    if VERBOSE_LOGGING:
        print(f"[{level.upper()}] {message}")
    
    # Log strutturato
    if STRUCTLOG_AVAILABLE:
        log_func = getattr(logger, level.lower(), logger.info)
        log_func(message, **context)
    else:
        # Fallback con logging standard - non passa **context
        if context:
            # Includi il context nel messaggio
            context_str = " ".join(f"{k}={v}" for k, v in context.items())
            full_message = f"{message} [{context_str}]"
        else:
            full_message = message
            
        log_func = getattr(logger, level.lower(), logger.info)
        log_func(full_message)  # Non passare **context a logging standard

# Alias per facilità d'uso
log = get_logger()
info = lambda msg, **ctx: migrate_print(msg, "info", **ctx)
warning = lambda msg, **ctx: migrate_print(msg, "warning", **ctx)
error = lambda msg, **ctx: migrate_print(msg, "error", **ctx)
debug = lambda msg, **ctx: migrate_print(msg, "debug", **ctx)

# ────────────────────────────────────────────────────────────────────────────────
# Configurazione iniziale
# ────────────────────────────────────────────────────────────────────────────────

# Auto-setup quando il modulo viene importato
if __name__ != "__main__":
    try:
        _logger = setup_logging()
        if STRUCTLOG_AVAILABLE:
            info("Structured logging configurato con structlog")
        else:
            info("Logging standard configurato (structlog non disponibile)")
    except Exception as e:
        print(f"Errore configurazione logging: {e}")
        # Fallback a print per evitare crash
        pass
import logging
import logging.config
import os
import json
from datetime import datetime
from typing import Dict, Any
from pathlib import Path


class StructuredFormatter(logging.Formatter):
    """
    Formatter que genera logs en formato JSON estructurado
    para facilitar la integración con sistemas de monitoreo
    """

    def __init__(self):
        super().__init__()

    def format(self, record: logging.LogRecord) -> str:
        """
        Formatea el registro de log como JSON estructurado
        """
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "process": record.process,
            "thread": record.thread,
        }

        # Agregar información adicional si está disponible
        if hasattr(record, 'service'):
            log_entry['service'] = record.service

        if hasattr(record, 'endpoint'):
            log_entry['endpoint'] = record.endpoint

        if hasattr(record, 'method'):
            log_entry['method'] = record.method

        if hasattr(record, 'status_code'):
            log_entry['status_code'] = record.status_code

        if hasattr(record, 'response_time_ms'):
            log_entry['response_time_ms'] = record.response_time_ms

        if hasattr(record, 'user_id'):
            log_entry['user_id'] = record.user_id

        if hasattr(record, 'sheet_id'):
            log_entry['sheet_id'] = record.sheet_id

        if hasattr(record, 'error_code'):
            log_entry['error_code'] = record.error_code

        # Agregar información de excepción si existe
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)

        return json.dumps(log_entry, ensure_ascii=False)


def setup_logging() -> None:
    """
    Configura el sistema de logging con rotación y formato estructurado
    para integración con sistemas de monitoreo
    """
    # Crear directorio de logs si no existe
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Configuración de logging
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "structured": {
                "()": StructuredFormatter,
            },
            "simple": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S"
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "simple",
                "level": "INFO",
                "stream": "ext://sys.stdout"
            },
            "file_all": {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "structured",
                "filename": "logs/app.log",
                "maxBytes": 10485760,  # 10MB
                "backupCount": 10,
                "level": "INFO"
            },
            "file_errors": {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "structured",
                "filename": "logs/errors.log",
                "maxBytes": 10485760,  # 10MB
                "backupCount": 10,
                "level": "ERROR"
            },
            "file_smartsheet": {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "structured",
                "filename": "logs/smartsheet.log",
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5,
                "level": "INFO"
            },
            "file_api": {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "structured",
                "filename": "logs/api.log",
                "maxBytes": 10485760,  # 10MB
                "backupCount": 10,
                "level": "INFO"
            }
        },
        "loggers": {
            "app": {
                "level": "INFO",
                "handlers": ["console", "file_all", "file_errors"],
                "propagate": False
            },
            "app.services.smartsheet_service": {
                "level": "INFO",
                "handlers": ["console", "file_smartsheet", "file_errors"],
                "propagate": False
            },
            "app.api.v1.endpoints.smartsheet": {
                "level": "INFO",
                "handlers": ["console", "file_api", "file_errors"],
                "propagate": False
            },
            "app.utils.query_parser": {
                "level": "INFO",
                "handlers": ["console", "file_smartsheet", "file_errors"],
                "propagate": False
            },
            "uvicorn": {
                "level": "INFO",
                "handlers": ["console", "file_api"],
                "propagate": False
            },
            "uvicorn.access": {
                "level": "INFO",
                "handlers": ["file_api"],
                "propagate": False
            },
            "fastapi": {
                "level": "INFO",
                "handlers": ["console", "file_api"],
                "propagate": False
            }
        },
        "root": {
            "level": "WARNING",
            "handlers": ["console", "file_all"]
        }
    }

    # Aplicar configuración
    logging.config.dictConfig(logging_config)

    # Logger principal de la aplicación
    logger = logging.getLogger("app")
    logger.info("Logging system initialized successfully")
    logger.info(f"Log files will be stored in: {log_dir.absolute()}")


class LoggerAdapter(logging.LoggerAdapter):
    """
    Adapter personalizado para agregar contexto adicional a los logs
    """

    def __init__(self, logger: logging.Logger, extra: Dict[str, Any] = None):
        super().__init__(logger, extra or {})

    def process(self, msg: str, kwargs: Dict[str, Any]) -> tuple:
        """
        Procesa el mensaje y kwargs antes del logging
        """
        # Agregar contexto del adapter
        if self.extra:
            kwargs.setdefault('extra', {}).update(self.extra)

        return msg, kwargs


def get_smartsheet_logger() -> LoggerAdapter:
    """
    Obtiene un logger específico para operaciones de Smartsheet
    """
    base_logger = logging.getLogger("app.services.smartsheet_service")
    return LoggerAdapter(base_logger, {"service": "smartsheet"})


def get_api_logger() -> LoggerAdapter:
    """
    Obtiene un logger específico para operaciones de API
    """
    base_logger = logging.getLogger("app.api.v1.endpoints.smartsheet")
    return LoggerAdapter(base_logger, {"service": "api"})


def log_api_request(logger: logging.Logger, method: str, endpoint: str,
                   status_code: int = None, response_time_ms: int = None,
                   user_id: str = None, **kwargs):
    """
    Registra información de una petición API con contexto estructurado

    Args:
        logger: Logger a usar
        method: Método HTTP
        endpoint: Endpoint accedido
        status_code: Código de respuesta HTTP
        response_time_ms: Tiempo de respuesta en millisegundos
        user_id: ID del usuario (si está autenticado)
        **kwargs: Información adicional
    """
    extra = {
        "method": method,
        "endpoint": endpoint,
        "service": "api"
    }

    if status_code:
        extra["status_code"] = status_code
    if response_time_ms:
        extra["response_time_ms"] = response_time_ms
    if user_id:
        extra["user_id"] = user_id

    extra.update(kwargs)

    if status_code and status_code >= 400:
        logger.error(f"API request failed: {method} {endpoint}", extra=extra)
    else:
        logger.info(f"API request: {method} {endpoint}", extra=extra)


def log_smartsheet_operation(logger: logging.Logger, operation: str,
                            sheet_id: int = None, success: bool = True,
                            response_time_ms: int = None, **kwargs):
    """
    Registra información de una operación de Smartsheet

    Args:
        logger: Logger a usar
        operation: Tipo de operación
        sheet_id: ID de la hoja de Smartsheet
        success: Si la operación fue exitosa
        response_time_ms: Tiempo de respuesta
        **kwargs: Información adicional
    """
    extra = {
        "operation": operation,
        "service": "smartsheet",
        "success": success
    }

    if sheet_id:
        extra["sheet_id"] = sheet_id
    if response_time_ms:
        extra["response_time_ms"] = response_time_ms

    extra.update(kwargs)

    if success:
        logger.info(f"Smartsheet operation successful: {operation}", extra=extra)
    else:
        logger.error(f"Smartsheet operation failed: {operation}", extra=extra)


# Configurar métricas para Prometheus (opcional)

# Prometheus metrics disabled to prevent duplicates
API_REQUESTS_TOTAL = None
API_REQUEST_DURATION = None
SMARTSHEET_OPERATIONS_TOTAL = None
SMARTSHEET_ACTIVE_CONNECTIONS = None

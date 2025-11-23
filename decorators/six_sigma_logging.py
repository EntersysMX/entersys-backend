# 🎯 DECORADORES PARA LOGGING AUTOMÁTICO SIX SIGMA
# Cada método del API tendrá logging automático con métricas detalladas

import time
import json
import functools
import asyncio
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional, Union
from fastapi import Request, HTTPException
import logging

class MethodLogger:
    """Logger especializado para métodos individuales del API"""

    def __init__(self, service_name: str, operation_type: str):
        self.service_name = service_name
        self.operation_type = operation_type
        self.setup_logger()

    def setup_logger(self):
        """Configura logger específico para este método"""
        logger_name = f"six_sigma.methods.{self.service_name}.{self.operation_type}"
        self.logger = logging.getLogger(logger_name)
        self.logger.setLevel(logging.INFO)

        # Handler específico para este método
        handler = logging.FileHandler(f'/app/logs/methods/{self.service_name}_{self.operation_type}.log')
        formatter = logging.Formatter(
            '{"timestamp": "%(asctime)s", "level": "%(levelname)s", '
            '"service": "' + self.service_name + '", '
            '"operation": "' + self.operation_type + '", '
            '"message": %(message)s}'
        )
        handler.setFormatter(formatter)

        if not self.logger.handlers:
            self.logger.addHandler(handler)

    def log_method_execution(self, method_name: str, parameters: Dict[str, Any],
                           result: Any, duration_ms: float, success: bool,
                           error: Optional[Exception] = None):
        """Registra la ejecución de un método con métricas Six Sigma"""

        # Determinar calidad de la ejecución
        quality_analysis = self._analyze_execution_quality(duration_ms, success, error)

        log_data = {
            "event_type": "method_execution",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "method_name": method_name,
            "service": self.service_name,
            "operation_type": self.operation_type,
            "execution_metrics": {
                "duration_ms": duration_ms,
                "success": success,
                "parameters_count": len(parameters),
                "has_error": error is not None,
                "error_type": type(error).__name__ if error else None,
                "error_message": str(error) if error else None
            },
            "six_sigma_analysis": quality_analysis,
            "input_parameters": self._sanitize_parameters(parameters),
            "result_metadata": self._analyze_result(result) if success else None
        }

        # Log según nivel de calidad
        if quality_analysis["sigma_level"] >= 4:
            self.logger.info(json.dumps(log_data))
        elif quality_analysis["sigma_level"] >= 3:
            self.logger.warning(json.dumps(log_data))
        else:
            self.logger.error(json.dumps(log_data))

    def _analyze_execution_quality(self, duration_ms: float, success: bool,
                                 error: Optional[Exception]) -> Dict[str, Any]:
        """Analiza la calidad de ejecución según estándares Six Sigma"""

        # Umbrales específicos por tipo de operación
        thresholds = self._get_operation_thresholds()

        # Análisis de performance
        performance_score = 100
        sigma_level = 6

        if not success:
            performance_score = 0
            sigma_level = 0
        elif duration_ms > thresholds["critical"]:
            performance_score = 10
            sigma_level = 1
        elif duration_ms > thresholds["poor"]:
            performance_score = 25
            sigma_level = 2
        elif duration_ms > thresholds["acceptable"]:
            performance_score = 50
            sigma_level = 3
        elif duration_ms > thresholds["good"]:
            performance_score = 75
            sigma_level = 4
        elif duration_ms > thresholds["excellent"]:
            performance_score = 90
            sigma_level = 5

        # Clasificación de defectos
        defect_type = None
        if not success:
            if isinstance(error, HTTPException):
                defect_type = f"http_error_{error.status_code}"
            elif isinstance(error, TimeoutError):
                defect_type = "timeout_error"
            elif isinstance(error, ConnectionError):
                defect_type = "connection_error"
            else:
                defect_type = "execution_error"
        elif duration_ms > thresholds["acceptable"]:
            defect_type = "performance_defect"

        return {
            "performance_score": performance_score,
            "sigma_level": sigma_level,
            "sla_compliant": success and duration_ms <= thresholds["acceptable"],
            "quality_category": self._get_quality_category(sigma_level),
            "defect_type": defect_type,
            "is_defect": defect_type is not None,
            "execution_thresholds": thresholds,
            "performance_category": self._categorize_performance(duration_ms, thresholds)
        }

    def _get_operation_thresholds(self) -> Dict[str, float]:
        """Obtiene umbrales específicos según el tipo de operación"""

        base_thresholds = {
            "excellent": 500,    # 0.5s
            "good": 1000,        # 1s
            "acceptable": 3000,  # 3s (límite Six Sigma)
            "poor": 5000,        # 5s
            "critical": 10000    # 10s
        }

        # Ajustes por tipo de operación
        if self.operation_type == "health_check":
            return {k: v * 0.2 for k, v in base_thresholds.items()}  # Más estricto
        elif self.operation_type == "data_retrieval":
            return {k: v * 1.5 for k, v in base_thresholds.items()}  # Más permisivo
        elif self.operation_type == "crud":
            return {k: v * 1.2 for k, v in base_thresholds.items()}
        elif self.operation_type == "security":
            return {k: v * 0.8 for k, v in base_thresholds.items()}  # Más estricto
        else:
            return base_thresholds

    def _get_quality_category(self, sigma_level: int) -> str:
        """Obtiene categoría de calidad basada en sigma level"""
        categories = {
            6: "world_class",
            5: "excellent",
            4: "very_good",
            3: "good",
            2: "average",
            1: "poor",
            0: "unacceptable"
        }
        return categories.get(sigma_level, "unacceptable")

    def _categorize_performance(self, duration_ms: float, thresholds: Dict[str, float]) -> str:
        """Categoriza la performance del método"""
        if duration_ms <= thresholds["excellent"]:
            return "excellent"
        elif duration_ms <= thresholds["good"]:
            return "good"
        elif duration_ms <= thresholds["acceptable"]:
            return "acceptable"
        elif duration_ms <= thresholds["poor"]:
            return "poor"
        else:
            return "critical"

    def _sanitize_parameters(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitiza parámetros removiendo información sensible"""
        sanitized = {}
        sensitive_keys = {'password', 'token', 'api_key', 'secret', 'auth', 'credential'}

        for key, value in parameters.items():
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                sanitized[key] = "[REDACTED]"
            elif isinstance(value, (dict, list)) and len(str(value)) > 1000:
                sanitized[key] = f"[LARGE_OBJECT_SIZE:{len(str(value))}]"
            else:
                sanitized[key] = value

        return sanitized

    def _analyze_result(self, result: Any) -> Dict[str, Any]:
        """Analiza el resultado para métricas adicionales"""
        if result is None:
            return {"type": "none", "size": 0}

        result_type = type(result).__name__
        result_size = len(str(result)) if hasattr(result, '__len__') else 1

        metadata = {
            "type": result_type,
            "size": result_size,
            "is_empty": result_size == 0 if hasattr(result, '__len__') else False
        }

        # Análisis específico por tipo
        if hasattr(result, 'dict'):  # Pydantic models
            data = result.dict()
            metadata.update({
                "record_count": len(data.get('data', [])) if 'data' in data else 1,
                "has_pagination": 'offset' in data or 'limit' in data,
                "response_structure": "pydantic_model"
            })
        elif isinstance(result, dict):
            metadata.update({
                "keys_count": len(result.keys()),
                "has_data_array": 'data' in result and isinstance(result['data'], list),
                "record_count": len(result.get('data', [])) if isinstance(result.get('data'), list) else 1
            })
        elif isinstance(result, list):
            metadata.update({
                "record_count": len(result),
                "response_structure": "array"
            })

        return metadata


def six_sigma_log(service_name: str, operation_type: str,
                  method_description: Optional[str] = None):
    """
    Decorador para logging automático Six Sigma en métodos del API

    Args:
        service_name: Nombre del servicio (ej: "smartsheet_service")
        operation_type: Tipo de operación (ej: "data_retrieval", "health_check")
        method_description: Descripción del método (opcional)

    Usage:
        @six_sigma_log("smartsheet_service", "data_retrieval", "Get sheet rows with filtering")
        async def get_sheet_rows(self, sheet_id: int, ...):
            # método implementation
    """
    def decorator(func: Callable) -> Callable:
        method_logger = MethodLogger(service_name, operation_type)

        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                return await _execute_with_logging(func, method_logger, method_description,
                                                 args, kwargs, is_async=True)
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                return _execute_with_logging(func, method_logger, method_description,
                                           args, kwargs, is_async=False)
            return sync_wrapper

    return decorator


async def _execute_with_logging(func: Callable, logger: MethodLogger, description: Optional[str],
                              args: tuple, kwargs: dict, is_async: bool = True) -> Any:
    """Ejecuta función con logging Six Sigma completo"""

    start_time = time.time()
    method_name = func.__name__

    # Preparar parámetros para logging
    all_params = {}

    # Obtener parámetros posicionales
    if hasattr(func, '__code__'):
        param_names = func.__code__.co_varnames[:func.__code__.co_argcount]
        for i, arg in enumerate(args):
            if i < len(param_names):
                param_name = param_names[i]
                if param_name != 'self':  # Excluir self de métodos de clase
                    all_params[param_name] = arg

    # Agregar parámetros con nombre
    all_params.update(kwargs)

    # Agregar contexto de request si está disponible
    request_context = {}
    for arg in args:
        if hasattr(arg, 'state') and hasattr(arg.state, 'request_id'):
            request_context['request_id'] = arg.state.request_id
            break

    result = None
    exception = None
    success = False

    try:
        # Ejecutar función
        if is_async:
            result = await func(*args, **kwargs)
        else:
            result = func(*args, **kwargs)
        success = True

    except Exception as e:
        exception = e
        success = False
        raise

    finally:
        # Calcular duración
        end_time = time.time()
        duration_ms = (end_time - start_time) * 1000

        # Registrar ejecución
        logger.log_method_execution(
            method_name=method_name,
            parameters={**all_params, **request_context},
            result=result,
            duration_ms=duration_ms,
            success=success,
            error=exception
        )

    return result


def business_process_log(process_name: str, expected_duration_ms: float = 3000):
    """
    Decorador especializado para procesos de negocio críticos

    Args:
        process_name: Nombre del proceso de negocio
        expected_duration_ms: Duración esperada en ms (para SLA)
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            process_logger = logging.getLogger(f'six_sigma.business_process.{process_name}')

            # Log inicio del proceso
            process_start_data = {
                "event_type": "business_process_start",
                "process_name": process_name,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "expected_duration_ms": expected_duration_ms,
                "function_name": func.__name__
            }

            process_logger.info(json.dumps(process_start_data))

            try:
                result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
                success = True
                error = None
            except Exception as e:
                success = False
                error = e
                raise
            finally:
                end_time = time.time()
                duration_ms = (end_time - start_time) * 1000

                # Análisis de SLA del proceso de negocio
                sla_breach = duration_ms > expected_duration_ms
                performance_impact = "high" if sla_breach else "normal"

                process_completion_data = {
                    "event_type": "business_process_completion",
                    "process_name": process_name,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "duration_ms": duration_ms,
                    "expected_duration_ms": expected_duration_ms,
                    "sla_breach": sla_breach,
                    "success": success,
                    "performance_impact": performance_impact,
                    "error_info": {
                        "has_error": error is not None,
                        "error_type": type(error).__name__ if error else None,
                        "error_message": str(error) if error else None
                    }
                }

                # Log según resultado
                if success and not sla_breach:
                    process_logger.info(json.dumps(process_completion_data))
                elif sla_breach:
                    process_logger.warning(json.dumps(process_completion_data))
                else:
                    process_logger.error(json.dumps(process_completion_data))

            return result

        return wrapper
    return decorator


class DatabaseOperationLogger:
    """Logger especializado para operaciones de base de datos"""

    def __init__(self):
        self.logger = logging.getLogger('six_sigma.database_operations')
        self.logger.setLevel(logging.INFO)

    def log_query_execution(self, query_type: str, table_name: str, duration_ms: float,
                           rows_affected: int = 0, success: bool = True, error: Optional[Exception] = None):
        """Registra ejecución de queries con métricas de performance"""

        # Análisis de performance de DB
        performance_category = self._categorize_db_performance(query_type, duration_ms)
        slow_query = duration_ms > 1000  # Queries >1s se consideran lentas

        db_log_data = {
            "event_type": "database_operation",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "query_type": query_type,
            "table_name": table_name,
            "execution_metrics": {
                "duration_ms": duration_ms,
                "rows_affected": rows_affected,
                "is_slow_query": slow_query,
                "performance_category": performance_category,
                "success": success
            },
            "six_sigma_analysis": {
                "sla_compliant": not slow_query and success,
                "defect_type": self._classify_db_defect(query_type, duration_ms, success, error),
                "optimization_needed": slow_query or not success
            }
        }

        if success and not slow_query:
            self.logger.info(json.dumps(db_log_data))
        elif slow_query:
            self.logger.warning(json.dumps(db_log_data))
        else:
            self.logger.error(json.dumps(db_log_data))

    def _categorize_db_performance(self, query_type: str, duration_ms: float) -> str:
        """Categoriza performance de queries de DB"""
        thresholds = {
            "SELECT": {"fast": 100, "acceptable": 500, "slow": 1000},
            "INSERT": {"fast": 50, "acceptable": 200, "slow": 500},
            "UPDATE": {"fast": 100, "acceptable": 300, "slow": 800},
            "DELETE": {"fast": 100, "acceptable": 300, "slow": 800}
        }

        query_thresholds = thresholds.get(query_type.upper(), thresholds["SELECT"])

        if duration_ms <= query_thresholds["fast"]:
            return "fast"
        elif duration_ms <= query_thresholds["acceptable"]:
            return "acceptable"
        elif duration_ms <= query_thresholds["slow"]:
            return "slow"
        else:
            return "very_slow"

    def _classify_db_defect(self, query_type: str, duration_ms: float, success: bool,
                          error: Optional[Exception]) -> Optional[str]:
        """Clasifica defectos en operaciones de DB"""
        if not success:
            return f"db_error_{type(error).__name__ if error else 'unknown'}"
        elif duration_ms > 1000:
            return "slow_query"
        return None


# Instancia global para operaciones de DB
db_logger = DatabaseOperationLogger()
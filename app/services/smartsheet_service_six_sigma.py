import smartsheet
import logging
import time
from typing import Dict, List, Optional, Any, Union
from datetime import datetime

from app.core.config import settings
from app.models.smartsheet import (
    SmartsheetRow, SmartsheetRowsData, SmartsheetRowsResponse,
    SmartsheetErrorResponse, SmartsheetAttachment, SmartsheetColumn
)
from app.utils.query_parser import SmartsheetQueryParser, QueryParserError

# Importar sistema de logging Six Sigma
from decorators.six_sigma_logging import six_sigma_log, business_process_log, db_logger


class SmartsheetServiceError(Exception):
    """Excepción personalizada para errores del servicio de Smartsheet"""
    pass


class SmartsheetServiceSixSigma:
    """
    🎯 SERVICIO SMARTSHEET CON LOGGING SIX SIGMA COMPLETO

    Cada método registra métricas detalladas para monitoreo de calidad:
    - Tiempo de respuesta (umbral: ≤3s)
    - Tasa de éxito/error por operación
    - Métricas de performance por endpoint
    - Compliance Six Sigma (99.99966%)
    """

    def __init__(self):
        """Inicializa el servicio de Smartsheet con logging Six Sigma"""
        self.logger = logging.getLogger(__name__)
        self.query_parser = SmartsheetQueryParser()

        try:
            # Inicializar el cliente de Smartsheet
            self.client = smartsheet.Smartsheet(settings.SMARTSHEET_ACCESS_TOKEN)
            self.client.errors_as_exceptions(True)

            # Log de inicialización exitosa con métricas
            self.logger.info({
                "event_type": "service_initialization",
                "service": "smartsheet_service",
                "status": "success",
                "timestamp": datetime.utcnow().isoformat(),
                "api_base_url": settings.SMARTSHEET_API_BASE_URL,
                "six_sigma_tracking": True
            })

        except Exception as e:
            # Log de error de inicialización
            self.logger.error({
                "event_type": "service_initialization",
                "service": "smartsheet_service",
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
                "six_sigma_tracking": True
            })
            raise SmartsheetServiceError(f"Error initializing Smartsheet client: {str(e)}")

    @six_sigma_log("smartsheet_service", "data_retrieval", "Get sheet rows with filtering and pagination")
    @business_process_log("smartsheet_data_extraction", 2500.0)  # SLA: 2.5s para extracción de datos
    async def get_sheet_rows(
        self,
        sheet_id: int,
        limit: int = 100,
        offset: int = 0,
        fields: Optional[str] = None,
        include_attachments: bool = False,
        query_string: Optional[str] = None
    ) -> Union[SmartsheetRowsResponse, SmartsheetErrorResponse]:
        """
        🎯 MÉTODO PRINCIPAL - Obtiene filas con monitoreo Six Sigma completo

        Métricas registradas:
        - Tiempo de respuesta por query
        - Cantidad de registros procesados
        - Eficiencia de filtros aplicados
        - Performance de paginación
        """
        start_time = time.time()
        operation_context = {
            "sheet_id": sheet_id,
            "limit": limit,
            "offset": offset,
            "has_filters": bool(query_string),
            "has_field_selection": bool(fields),
            "include_attachments": include_attachments
        }

        try:
            self._log_operation_start("get_sheet_rows", operation_context)

            # Obtener la hoja completa con todas las filas
            sheet = await self._get_sheet_data(sheet_id, include_attachments)

            if not sheet:
                error_response = SmartsheetErrorResponse(
                    error="SHEET_NOT_FOUND",
                    message=f"Sheet with ID {sheet_id} not found"
                )
                self._log_operation_error("get_sheet_rows", "SHEET_NOT_FOUND", operation_context)
                return error_response

            # Convertir filas a formato de respuesta
            converted_rows = await self._convert_sheet_rows_with_metrics(sheet, include_attachments)

            # Aplicar filtros si se proporcionaron
            if query_string:
                converted_rows = await self._apply_filters_with_metrics(converted_rows, query_string)
                if isinstance(converted_rows, SmartsheetErrorResponse):
                    return converted_rows

            # Aplicar selección de campos si se especificaron
            if fields:
                converted_rows = await self._filter_fields_with_metrics(converted_rows, fields)

            # Aplicar paginación con métricas
            total_rows = len(converted_rows)
            paginated_rows = converted_rows[offset:offset + limit]

            # Convertir a objetos SmartsheetRow
            smartsheet_rows = []
            for row_data in paginated_rows:
                smartsheet_rows.append(SmartsheetRow(**row_data))

            # Crear respuesta con métricas de execution
            execution_time = int((time.time() - start_time) * 1000)

            response_data = SmartsheetRowsData(
                sheet_id=sheet_id,
                total_rows=total_rows,
                returned_rows=len(smartsheet_rows),
                offset=offset,
                limit=limit,
                rows=smartsheet_rows
            )

            response = SmartsheetRowsResponse(
                success=True,
                data=response_data,
                filters_applied=query_string,
                execution_time_ms=execution_time
            )

            # Log de éxito con métricas detalladas
            self._log_operation_success("get_sheet_rows", {
                **operation_context,
                "total_rows": total_rows,
                "returned_rows": len(smartsheet_rows),
                "execution_time_ms": execution_time,
                "data_efficiency": len(smartsheet_rows) / total_rows if total_rows > 0 else 0,
                "performance_category": self._categorize_performance(execution_time)
            })

            return response

        except smartsheet.exceptions.ApiError as e:
            error_context = {
                **operation_context,
                "error_type": "SMARTSHEET_API_ERROR",
                "api_error_code": str(e.error.result.code) if hasattr(e.error, 'result') else None,
                "execution_time_ms": int((time.time() - start_time) * 1000)
            }
            self._log_operation_error("get_sheet_rows", "SMARTSHEET_API_ERROR", error_context)

            return SmartsheetErrorResponse(
                error="SMARTSHEET_API_ERROR",
                error_code=str(e.error.result.code) if hasattr(e.error, 'result') else None,
                message=f"Smartsheet API error: {str(e)}"
            )

        except Exception as e:
            error_context = {
                **operation_context,
                "error_type": "INTERNAL_ERROR",
                "execution_time_ms": int((time.time() - start_time) * 1000)
            }
            self._log_operation_error("get_sheet_rows", "INTERNAL_ERROR", error_context)

            return SmartsheetErrorResponse(
                error="INTERNAL_ERROR",
                message=f"Internal server error: {str(e)}"
            )

    @six_sigma_log("smartsheet_service", "metadata_retrieval", "Get sheet column information")
    async def get_sheet_columns(self, sheet_id: int) -> List[SmartsheetColumn]:
        """
        📊 Obtiene información de columnas con monitoreo Six Sigma

        SLA Target: ≤1s (operación de metadata)
        """
        operation_context = {"sheet_id": sheet_id, "operation": "get_columns"}

        try:
            self._log_operation_start("get_sheet_columns", operation_context)

            sheet = self.client.Sheets.get_sheet(sheet_id, include=['format'])
            columns = []

            for column in sheet.columns:
                column_data = SmartsheetColumn(
                    id=column.id,
                    index=column.index,
                    title=column.title,
                    type=str(column.type),  # Convert EnumeratedValue to string
                    primary=getattr(column, 'primary', False),
                    hidden=getattr(column, 'hidden', False),
                    locked=getattr(column, 'locked', False)
                )
                columns.append(column_data)

            # Log de éxito
            self._log_operation_success("get_sheet_columns", {
                **operation_context,
                "columns_count": len(columns),
                "has_primary_column": any(col.primary for col in columns)
            })

            return columns

        except Exception as e:
            self._log_operation_error("get_sheet_columns", "COLUMN_RETRIEVAL_ERROR", {
                **operation_context,
                "error_message": str(e)
            })
            raise SmartsheetServiceError(f"Error getting sheet columns: {str(e)}")

    @six_sigma_log("smartsheet_service", "health_check", "Service health verification")
    async def health_check(self) -> Dict[str, Any]:
        """
        🔍 Health check con métricas Six Sigma

        SLA Target: ≤200ms (verificación de salud)
        """
        start_time = time.time()

        try:
            # Intentar obtener información del usuario actual
            user_info = self.client.Users.get_current_user()
            response_time_ms = int((time.time() - start_time) * 1000)

            health_data = {
                "status": "healthy",
                "user": user_info.email if hasattr(user_info, 'email') else "unknown",
                "api_base_url": settings.SMARTSHEET_API_BASE_URL,
                "response_time_ms": response_time_ms,
                "timestamp": datetime.utcnow().isoformat(),
                "six_sigma_compliant": response_time_ms <= 200
            }

            # Log health check success
            self._log_operation_success("health_check", {
                "response_time_ms": response_time_ms,
                "api_connectivity": True,
                "user_authenticated": bool(user_info.email if hasattr(user_info, 'email') else False)
            })

            return health_data

        except Exception as e:
            response_time_ms = int((time.time() - start_time) * 1000)

            error_data = {
                "status": "unhealthy",
                "error": str(e),
                "response_time_ms": response_time_ms,
                "timestamp": datetime.utcnow().isoformat(),
                "six_sigma_compliant": False
            }

            # Log health check failure
            self._log_operation_error("health_check", "HEALTH_CHECK_FAILED", {
                "response_time_ms": response_time_ms,
                "error_message": str(e),
                "api_connectivity": False
            })

            return error_data

    @six_sigma_log("smartsheet_service", "data_retrieval", "Fetch raw sheet data from API")
    async def _get_sheet_data(self, sheet_id: int, include_attachments: bool) -> Optional[Any]:
        """
        🔄 Obtiene datos base de la hoja con métricas de conectividad
        """
        api_call_context = {
            "sheet_id": sheet_id,
            "include_attachments": include_attachments,
            "api_operation": "get_sheet"
        }

        try:
            include_params = ['format', 'objectValue']

            if include_attachments:
                include_params.extend(['attachments', 'discussions'])

            # Registrar llamada a API externa
            api_start_time = time.time()

            sheet = self.client.Sheets.get_sheet(
                sheet_id,
                include=include_params
            )

            api_response_time = int((time.time() - api_start_time) * 1000)

            # Log métricas de API call
            self._log_api_call("smartsheet_get_sheet", {
                **api_call_context,
                "api_response_time_ms": api_response_time,
                "rows_retrieved": len(sheet.rows),
                "columns_retrieved": len(sheet.columns),
                "api_sla_compliant": api_response_time <= 2000  # 2s para llamadas externas
            })

            return sheet

        except smartsheet.exceptions.ApiError as e:
            if e.error.result.code == 1006:  # NOT_FOUND
                self._log_api_call("smartsheet_get_sheet", {
                    **api_call_context,
                    "api_result": "NOT_FOUND",
                    "error_code": 1006
                })
                return None
            else:
                self._log_api_call("smartsheet_get_sheet", {
                    **api_call_context,
                    "api_result": "API_ERROR",
                    "error_code": e.error.result.code if hasattr(e.error, 'result') else None,
                    "error_message": str(e)
                })
                raise

    @six_sigma_log("smartsheet_service", "data_processing", "Convert sheet rows to response format")
    async def _convert_sheet_rows_with_metrics(self, sheet: Any, include_attachments: bool) -> List[Dict[str, Any]]:
        """
        🔄 Conversión de filas con métricas de procesamiento
        """
        start_time = time.time()
        converted_rows = []

        # Crear mapeo de ID de columna a nombre
        column_map = {}
        for column in sheet.columns:
            column_map[column.id] = column.title

        # Procesar filas con métricas
        processed_cells = 0
        processed_attachments = 0

        for row in sheet.rows:
            row_data = {
                'id': row.id,
                'row_number': row.row_number,
                'cells': {},
                'attachments': [],
                'created_at': row.created_at,
                'modified_at': row.modified_at,
                'created_by': getattr(row.created_by, 'name', None) if hasattr(row, 'created_by') and row.created_by else None,
                'modified_by': getattr(row.modified_by, 'name', None) if hasattr(row, 'modified_by') and row.modified_by else None
            }

            # Procesar celdas
            for cell in row.cells:
                column_name = column_map.get(cell.column_id, f"Column_{cell.column_id}")
                cell_value = cell.display_value if cell.display_value is not None else cell.value
                row_data['cells'][column_name] = cell_value
                processed_cells += 1

            # Procesar adjuntos si están incluidos
            if include_attachments and hasattr(row, 'attachments') and row.attachments:
                for attachment in row.attachments:
                    attachment_data = {
                        'id': attachment.id,
                        'name': attachment.name,
                        'url': attachment.url if hasattr(attachment, 'url') else None,
                        'attachment_type': attachment.attachment_type if hasattr(attachment, 'attachment_type') else None,
                        'mime_type': attachment.mime_type if hasattr(attachment, 'mime_type') else None,
                        'size_in_kb': attachment.size_in_kb if hasattr(attachment, 'size_in_kb') else None,
                        'created_at': attachment.created_at if hasattr(attachment, 'created_at') else None,
                        'created_by': getattr(attachment.created_by, 'name', None) if hasattr(attachment, 'created_by') and attachment.created_by else None
                    }
                    row_data['attachments'].append(attachment_data)
                    processed_attachments += 1

            converted_rows.append(row_data)

        processing_time_ms = int((time.time() - start_time) * 1000)

        # Log métricas de procesamiento
        self._log_data_processing("row_conversion", {
            "rows_processed": len(converted_rows),
            "cells_processed": processed_cells,
            "attachments_processed": processed_attachments,
            "processing_time_ms": processing_time_ms,
            "processing_rate_rows_per_second": len(converted_rows) / (processing_time_ms / 1000) if processing_time_ms > 0 else 0,
            "processing_efficiency": "high" if processing_time_ms < 1000 else "medium" if processing_time_ms < 3000 else "low"
        })

        return converted_rows

    @six_sigma_log("smartsheet_service", "data_filtering", "Apply dynamic filters to dataset")
    async def _apply_filters_with_metrics(self, rows: List[Dict[str, Any]], query_string: str) -> Union[List[Dict[str, Any]], SmartsheetErrorResponse]:
        """
        🔍 Aplicación de filtros con métricas de eficiencia
        """
        start_time = time.time()
        initial_count = len(rows)

        try:
            condition = self.query_parser.parse_query_string(query_string)
            filtered_rows = self.query_parser.apply_filters(rows, condition)

            filtering_time_ms = int((time.time() - start_time) * 1000)
            final_count = len(filtered_rows)
            filter_efficiency = final_count / initial_count if initial_count > 0 else 0

            # Log métricas de filtrado
            self._log_data_processing("filter_application", {
                "filter_query": query_string,
                "initial_rows": initial_count,
                "filtered_rows": final_count,
                "filter_efficiency": filter_efficiency,
                "filtering_time_ms": filtering_time_ms,
                "filter_selectivity": f"{filter_efficiency * 100:.2f}%",
                "performance_impact": "low" if filtering_time_ms < 500 else "medium" if filtering_time_ms < 1500 else "high"
            })

            return filtered_rows

        except QueryParserError as e:
            # Log error en filtrado
            self._log_operation_error("filter_application", "INVALID_QUERY", {
                "filter_query": query_string,
                "initial_rows": initial_count,
                "error_message": str(e)
            })

            return SmartsheetErrorResponse(
                error="INVALID_QUERY",
                message=f"Invalid query syntax: {str(e)}"
            )

    @six_sigma_log("smartsheet_service", "data_processing", "Apply field selection to dataset")
    async def _filter_fields_with_metrics(self, rows: List[Dict[str, Any]], fields: str) -> List[Dict[str, Any]]:
        """
        📊 Selección de campos con métricas de optimización
        """
        start_time = time.time()
        field_list = [field.strip() for field in fields.split(',')]
        filtered_rows = []

        total_fields_before = 0
        total_fields_after = 0

        for row in rows:
            filtered_row = {
                'id': row['id'],
                'row_number': row['row_number'],
                'cells': {},
                'attachments': row['attachments'],
                'created_at': row['created_at'],
                'modified_at': row['modified_at'],
                'created_by': row['created_by'],
                'modified_by': row['modified_by']
            }

            total_fields_before += len(row['cells'])

            # Incluir solo los campos solicitados
            for field in field_list:
                if field in row['cells']:
                    filtered_row['cells'][field] = row['cells'][field]

            total_fields_after += len(filtered_row['cells'])
            filtered_rows.append(filtered_row)

        processing_time_ms = int((time.time() - start_time) * 1000)
        data_reduction = (total_fields_before - total_fields_after) / total_fields_before if total_fields_before > 0 else 0

        # Log métricas de selección de campos
        self._log_data_processing("field_selection", {
            "requested_fields": field_list,
            "requested_field_count": len(field_list),
            "total_fields_before": total_fields_before,
            "total_fields_after": total_fields_after,
            "data_reduction_percentage": f"{data_reduction * 100:.2f}%",
            "processing_time_ms": processing_time_ms,
            "optimization_impact": "high" if data_reduction > 0.5 else "medium" if data_reduction > 0.2 else "low"
        })

        return filtered_rows

    # ═══════════════════════════════════════════════════════════════
    # MÉTODOS DE LOGGING SIX SIGMA
    # ═══════════════════════════════════════════════════════════════

    def _log_operation_start(self, operation: str, context: Dict[str, Any]):
        """Log inicio de operación con contexto completo"""
        self.logger.info({
            "event_type": "operation_start",
            "operation": operation,
            "service": "smartsheet_service",
            "timestamp": datetime.utcnow().isoformat(),
            "context": context,
            "six_sigma_tracking": True
        })

    def _log_operation_success(self, operation: str, metrics: Dict[str, Any]):
        """Log éxito de operación con métricas Six Sigma"""
        self.logger.info({
            "event_type": "operation_success",
            "operation": operation,
            "service": "smartsheet_service",
            "timestamp": datetime.utcnow().isoformat(),
            "metrics": metrics,
            "six_sigma_tracking": True,
            "quality_level": self._determine_quality_level(metrics.get("execution_time_ms", 0))
        })

    def _log_operation_error(self, operation: str, error_type: str, context: Dict[str, Any]):
        """Log error de operación con contexto de falla"""
        self.logger.error({
            "event_type": "operation_error",
            "operation": operation,
            "service": "smartsheet_service",
            "error_type": error_type,
            "timestamp": datetime.utcnow().isoformat(),
            "context": context,
            "six_sigma_tracking": True,
            "defect_registered": True
        })

    def _log_api_call(self, api_method: str, metrics: Dict[str, Any]):
        """Log llamadas a API externa con métricas de conectividad"""
        self.logger.info({
            "event_type": "external_api_call",
            "api_method": api_method,
            "service": "smartsheet_service",
            "timestamp": datetime.utcnow().isoformat(),
            "api_metrics": metrics,
            "six_sigma_tracking": True
        })

    def _log_data_processing(self, processing_type: str, metrics: Dict[str, Any]):
        """Log procesamiento de datos con métricas de eficiencia"""
        self.logger.info({
            "event_type": "data_processing",
            "processing_type": processing_type,
            "service": "smartsheet_service",
            "timestamp": datetime.utcnow().isoformat(),
            "processing_metrics": metrics,
            "six_sigma_tracking": True
        })

    def _categorize_performance(self, execution_time_ms: int) -> str:
        """Categoriza performance según umbrales Six Sigma"""
        if execution_time_ms <= 1000:
            return "excellent"
        elif execution_time_ms <= 2000:
            return "good"
        elif execution_time_ms <= 3000:
            return "acceptable"
        elif execution_time_ms <= 5000:
            return "poor"
        else:
            return "critical"

    def _determine_quality_level(self, execution_time_ms: int) -> str:
        """Determina nivel de calidad Six Sigma basado en performance"""
        if execution_time_ms <= 500:
            return "six_sigma"
        elif execution_time_ms <= 1000:
            return "five_sigma"
        elif execution_time_ms <= 2000:
            return "four_sigma"
        elif execution_time_ms <= 3000:
            return "three_sigma"
        else:
            return "below_standard"
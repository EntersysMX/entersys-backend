from fastapi import APIRouter, Query, Header, Depends, HTTPException, status
from typing import Optional, Union, List
import logging
import time

from app.models.smartsheet import (
    SmartsheetRowsResponse, SmartsheetErrorResponse, SmartsheetColumn
)
from app.services.smartsheet_service import SmartsheetService, SmartsheetServiceError
from app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


def get_smartsheet_service() -> SmartsheetService:
    """
    Dependency para obtener una instancia del servicio de Smartsheet
    """
    return SmartsheetService()


def validate_api_key(x_api_key: str = Header(..., alias="X-API-Key")) -> str:
    """
    Valida la API key del middleware

    Args:
        x_api_key: API key proporcionada en el header

    Returns:
        API key validada

    Raises:
        HTTPException: Si la API key es inválida
    """
    if x_api_key != settings.MIDDLEWARE_API_KEY:
        logger.warning(f"Invalid API key attempted: {x_api_key[:10]}...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    return x_api_key


@router.get(
    "/sheets/{sheet_id}/rows",
    response_model=Union[SmartsheetRowsResponse, SmartsheetErrorResponse],
    summary="Get rows from Smartsheet",
    description="""
    Retrieves rows from a specific Smartsheet with optional filtering, pagination, and field selection.

    **Query Parameters:**
    - `limit`: Maximum number of rows to return (1-1000, default: 100)
    - `offset`: Starting position for pagination (default: 0)
    - `fields`: Comma-separated list of column names to include
    - `includeAttachments`: Include attachment metadata (default: false)
    - `q`: Query string for dynamic filtering

    **Query Syntax:**
    - Format: `[column_name]:[operator]:[value]`
    - Multiple conditions: `condition1,AND,condition2` or `condition1,OR,condition2`
    - Operators: equals, iequals, contains, icontains, not_equals, is_empty, not_empty, greater_than, less_than

    **Examples:**
    - `Status:equals:Active`
    - `Priority:equals:High,AND,Status:not_equals:Completed`
    - `Name:contains:john,OR,Email:icontains:example.com`
    """
)
async def get_sheet_rows(
    sheet_id: int,
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of rows to return"),
    offset: int = Query(0, ge=0, description="Starting position for pagination"),
    fields: Optional[str] = Query(None, description="Comma-separated column names to include"),
    includeAttachments: bool = Query(False, description="Include attachment metadata"),
    q: Optional[str] = Query(None, description="Query filter string"),
    api_key: str = Depends(validate_api_key),
    smartsheet_service: SmartsheetService = Depends(get_smartsheet_service)
):
    """
    Endpoint principal para obtener filas de una hoja de Smartsheet

    Args:
        sheet_id: ID de la hoja de Smartsheet
        limit: Límite de filas a retornar
        offset: Offset para paginación
        fields: Columnas específicas a incluir
        includeAttachments: Si incluir metadatos de adjuntos
        q: Cadena de filtrado dinámico
        api_key: API key validada
        smartsheet_service: Instancia del servicio de Smartsheet

    Returns:
        SmartsheetRowsResponse o SmartsheetErrorResponse
    """
    start_time = time.time()

    try:
        logger.info(
            f"GET /sheets/{sheet_id}/rows - "
            f"limit={limit}, offset={offset}, fields={fields}, "
            f"includeAttachments={includeAttachments}, query='{q}'"
        )

        # Validar sheet_id
        if sheet_id <= 0:
            logger.warning(f"Invalid sheet_id: {sheet_id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Sheet ID must be a positive integer"
            )

        # Llamar al servicio
        result = await smartsheet_service.get_sheet_rows(
            sheet_id=sheet_id,
            limit=limit,
            offset=offset,
            fields=fields,
            include_attachments=includeAttachments,
            query_string=q
        )

        # Logging según el resultado
        execution_time = int((time.time() - start_time) * 1000)

        if isinstance(result, SmartsheetRowsResponse):
            logger.info(
                f"Successfully processed request for sheet {sheet_id} - "
                f"returned {result.data.returned_rows}/{result.data.total_rows} rows "
                f"in {execution_time}ms"
            )
            return result
        else:
            logger.error(
                f"Error processing request for sheet {sheet_id}: "
                f"{result.error} - {result.message}"
            )
            # Retornar el error con status HTTP apropiado
            if result.error == "SHEET_NOT_FOUND":
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=result.message
                )
            elif result.error == "INVALID_QUERY":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=result.message
                )
            elif result.error == "SMARTSHEET_API_ERROR":
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=result.message
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=result.message
                )

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except SmartsheetServiceError as e:
        logger.error(f"Smartsheet service error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Smartsheet service error: {str(e)}"
        )
    except Exception as e:
        execution_time = int((time.time() - start_time) * 1000)
        logger.error(f"Unexpected error in get_sheet_rows: {str(e)} (took {execution_time}ms)")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error occurred"
        )


@router.get(
    "/sheets/{sheet_id}/columns",
    response_model=List[SmartsheetColumn],
    summary="Get sheet columns",
    description="Retrieves column information from a specific Smartsheet"
)
async def get_sheet_columns(
    sheet_id: int,
    api_key: str = Depends(validate_api_key),
    smartsheet_service: SmartsheetService = Depends(get_smartsheet_service)
):
    """
    Obtiene información sobre las columnas de una hoja de Smartsheet

    Args:
        sheet_id: ID de la hoja de Smartsheet
        api_key: API key validada
        smartsheet_service: Instancia del servicio de Smartsheet

    Returns:
        Lista de columnas de la hoja
    """
    try:
        logger.info(f"GET /sheets/{sheet_id}/columns")

        if sheet_id <= 0:
            logger.warning(f"Invalid sheet_id: {sheet_id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Sheet ID must be a positive integer"
            )

        columns = await smartsheet_service.get_sheet_columns(sheet_id)

        logger.info(f"Successfully retrieved {len(columns)} columns for sheet {sheet_id}")
        return columns

    except SmartsheetServiceError as e:
        logger.error(f"Smartsheet service error getting columns: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Smartsheet service error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error getting sheet columns: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error occurred"
        )



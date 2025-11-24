# app/api/v1/endpoints/qr.py
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import Response
from pydantic import BaseModel, HttpUrl
import logging

from app.utils.qr_utils import generate_qr_code, generate_qr_code_base64

router = APIRouter()
logger = logging.getLogger(__name__)


class QRGenerateRequest(BaseModel):
    """Request model for QR code generation"""
    url: str
    box_size: int = 10
    border: int = 4
    fill_color: str = "black"
    back_color: str = "white"


class QRGenerateResponse(BaseModel):
    """Response model for QR code generation"""
    success: bool
    qr_base64: str
    message: str


@router.post(
    "/generate",
    response_model=QRGenerateResponse,
    summary="Generate QR Code",
    description="""
    Generates a QR code for any URL with Entersys logo in the center.

    **Features:**
    - QR never expires (it's just a URL)
    - Entersys logo automatically added in center
    - High error correction for logo visibility
    - Returns base64 encoded PNG image

    **Usage:**
    - Send a URL to generate QR
    - Receive base64 image ready to display/download
    """
)
async def generate_qr(request: QRGenerateRequest):
    """
    Endpoint para generar códigos QR genéricos para cualquier URL.
    El QR incluye el logo de Entersys en el centro.
    """
    logger.info(f"POST /qr/generate - url={request.url}")

    if not request.url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "success": False,
                "error": "INVALID_INPUT",
                "message": "URL is required"
            }
        )

    try:
        # Generar QR con logo
        qr_base64 = generate_qr_code_base64(
            data=request.url,
            box_size=request.box_size,
            border=request.border,
            fill_color=request.fill_color,
            back_color=request.back_color,
            add_logo=True  # Siempre agregar logo
        )

        logger.info(f"QR code generated successfully for URL: {request.url}")

        return QRGenerateResponse(
            success=True,
            qr_base64=qr_base64,
            message="QR code generated successfully"
        )

    except Exception as e:
        logger.error(f"Error generating QR code: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "error": "GENERATION_ERROR",
                "message": f"Error generating QR code: {str(e)}"
            }
        )


@router.post(
    "/generate/download",
    response_class=Response,
    summary="Generate and Download QR Code",
    description="""
    Generates a QR code and returns it as downloadable PNG image.

    **Features:**
    - Returns PNG file directly
    - Ready to download
    - Includes Entersys logo
    """
)
async def generate_qr_download(request: QRGenerateRequest):
    """
    Endpoint para generar y descargar QR como archivo PNG.
    """
    logger.info(f"POST /qr/generate/download - url={request.url}")

    if not request.url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="URL is required"
        )

    try:
        # Generar QR con logo
        qr_bytes = generate_qr_code(
            data=request.url,
            box_size=request.box_size,
            border=request.border,
            fill_color=request.fill_color,
            back_color=request.back_color,
            add_logo=True
        )

        logger.info(f"QR code download generated for URL: {request.url}")

        # Retornar como imagen PNG descargable
        return Response(
            content=qr_bytes,
            media_type="image/png",
            headers={
                "Content-Disposition": "attachment; filename=qr_code_entersys.png"
            }
        )

    except Exception as e:
        logger.error(f"Error generating QR code download: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating QR code: {str(e)}"
        )

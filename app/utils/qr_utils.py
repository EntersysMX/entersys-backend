# app/utils/qr_utils.py
import qrcode
from qrcode.image.pil import PilImage
from io import BytesIO
import base64
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def generate_qr_code(
    data: str,
    box_size: int = 10,
    border: int = 4,
    fill_color: str = "black",
    back_color: str = "white"
) -> bytes:
    """
    Genera un código QR como imagen PNG en bytes.

    Args:
        data: Datos a codificar en el QR (URL, texto, etc.)
        box_size: Tamaño de cada caja del QR en píxeles
        border: Tamaño del borde en cajas
        fill_color: Color de los módulos del QR
        back_color: Color de fondo del QR

    Returns:
        Imagen PNG del QR en bytes

    Raises:
        ValueError: Si los datos están vacíos
        Exception: Si hay un error generando el QR
    """
    if not data:
        raise ValueError("QR data cannot be empty")

    try:
        # Crear instancia del QR con configuración
        qr = qrcode.QRCode(
            version=1,  # Auto-ajusta basado en datos
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=box_size,
            border=border,
        )

        # Agregar datos al QR
        qr.add_data(data)
        qr.make(fit=True)

        # Generar imagen
        img: PilImage = qr.make_image(fill_color=fill_color, back_color=back_color)

        # Convertir a bytes
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)

        qr_bytes = buffer.getvalue()
        logger.info(f"QR code generated successfully, size: {len(qr_bytes)} bytes")

        return qr_bytes

    except Exception as e:
        logger.error(f"Error generating QR code: {str(e)}")
        raise


def generate_qr_code_base64(
    data: str,
    box_size: int = 10,
    border: int = 4,
    fill_color: str = "black",
    back_color: str = "white"
) -> str:
    """
    Genera un código QR y lo retorna como string base64.

    Args:
        data: Datos a codificar en el QR
        box_size: Tamaño de cada caja del QR en píxeles
        border: Tamaño del borde en cajas
        fill_color: Color de los módulos del QR
        back_color: Color de fondo del QR

    Returns:
        String base64 de la imagen PNG del QR
    """
    qr_bytes = generate_qr_code(
        data=data,
        box_size=box_size,
        border=border,
        fill_color=fill_color,
        back_color=back_color
    )

    return base64.b64encode(qr_bytes).decode('utf-8')


def generate_validation_url(base_url: str, uuid: str) -> str:
    """
    Genera la URL de validación para el código QR.

    Args:
        base_url: URL base de la API (ej: https://api.entersys.mx)
        uuid: UUID del certificado

    Returns:
        URL completa de validación
    """
    return f"{base_url}/api/v1/onboarding/validate?id={uuid}"


def generate_certificate_qr(uuid: str, base_url: str = "https://api.entersys.mx") -> bytes:
    """
    Genera el código QR para un certificado de onboarding.

    Función de conveniencia que combina la generación de URL y QR.

    Args:
        uuid: UUID del certificado
        base_url: URL base de la API

    Returns:
        Imagen PNG del QR en bytes
    """
    validation_url = generate_validation_url(base_url, uuid)

    # Usar colores corporativos de Entersys
    return generate_qr_code(
        data=validation_url,
        box_size=10,
        border=4,
        fill_color="#093D53",  # Color primario de Entersys
        back_color="white"
    )

# app/api/v1/endpoints/onboarding.py
from fastapi import APIRouter, Query, HTTPException, BackgroundTasks, status
from fastapi.responses import RedirectResponse
import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

from app.schemas.onboarding_schemas import (
    OnboardingGenerateRequest,
    OnboardingGenerateResponse,
    OnboardingGenerateData,
    OnboardingErrorResponse
)
from app.services.onboarding_smartsheet_service import (
    OnboardingSmartsheetService,
    OnboardingSmartsheetServiceError
)
from app.utils.qr_utils import generate_certificate_qr
from app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

# Constantes
MINIMUM_SCORE = 80.0
CERTIFICATE_VALIDITY_DAYS = 365
API_BASE_URL = "https://api.entersys.mx"
REDIRECT_VALID = "https://entersys.mx/certificacion-seguridad"
REDIRECT_INVALID = "https://entersys.mx/access-denied"


def get_onboarding_service() -> OnboardingSmartsheetService:
    """Dependency para obtener instancia del servicio"""
    return OnboardingSmartsheetService()


def send_qr_email(
    email_to: str,
    full_name: str,
    qr_image: bytes,
    expiration_date: datetime,
    cert_uuid: str
) -> bool:
    """
    Envía el email con el código QR adjunto.

    Args:
        email_to: Email del destinatario
        full_name: Nombre completo del usuario
        qr_image: Imagen del QR en bytes
        expiration_date: Fecha de vencimiento del certificado
        cert_uuid: UUID del certificado

    Returns:
        True si el email se envió exitosamente
    """
    try:
        # Crear mensaje multipart
        msg = MIMEMultipart('mixed')
        msg['Subject'] = f"Certificado de Seguridad - {full_name}"
        msg['From'] = "Entersys <no-reply@entersys.mx>"
        msg['To'] = email_to

        # Contenido HTML del email
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .container {{
                    background-color: #f9fafb;
                    border-radius: 8px;
                    padding: 30px;
                    margin: 20px 0;
                }}
                .header {{
                    text-align: center;
                    margin-bottom: 30px;
                }}
                h1 {{
                    color: #093D53;
                    font-size: 24px;
                    margin-bottom: 20px;
                }}
                .certificate-info {{
                    background-color: #e8f4f8;
                    border-left: 4px solid #009CA6;
                    padding: 15px;
                    margin: 20px 0;
                    border-radius: 4px;
                }}
                .qr-section {{
                    text-align: center;
                    margin: 30px 0;
                    padding: 20px;
                    background-color: white;
                    border-radius: 8px;
                }}
                .footer {{
                    text-align: center;
                    margin-top: 30px;
                    padding-top: 20px;
                    border-top: 1px solid #e5e7eb;
                    font-size: 12px;
                    color: #6b7280;
                }}
                .highlight {{
                    color: #009CA6;
                    font-weight: bold;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Certificado de Seguridad Industrial</h1>
                </div>

                <p>Estimado/a <strong>{full_name}</strong>,</p>

                <p>Felicitaciones por completar exitosamente el proceso de certificación de seguridad industrial de Entersys.</p>

                <div class="certificate-info">
                    <p><strong>Detalles del Certificado:</strong></p>
                    <ul>
                        <li>ID de Certificado: <span class="highlight">{cert_uuid}</span></li>
                        <li>Fecha de Emisión: <span class="highlight">{datetime.utcnow().strftime('%d/%m/%Y')}</span></li>
                        <li>Válido hasta: <span class="highlight">{expiration_date.strftime('%d/%m/%Y')}</span></li>
                    </ul>
                </div>

                <div class="qr-section">
                    <p><strong>Tu código QR de acceso está adjunto a este correo.</strong></p>
                    <p>Preséntalo al personal de seguridad en cada ingreso a las instalaciones.</p>
                </div>

                <p><strong>Instrucciones:</strong></p>
                <ol>
                    <li>Guarda este correo y el código QR adjunto.</li>
                    <li>Puedes imprimir el QR o mostrarlo desde tu dispositivo móvil.</li>
                    <li>El personal de seguridad escaneará tu código para verificar tu certificación.</li>
                </ol>

                <p>Si tienes alguna pregunta, no dudes en contactarnos.</p>

                <div class="footer">
                    <p>Este es un correo automático, por favor no respondas a este mensaje.</p>
                    <p>&copy; {datetime.utcnow().year} Entersys. Todos los derechos reservados.</p>
                </div>
            </div>
        </body>
        </html>
        """

        # Adjuntar contenido HTML
        html_part = MIMEText(html_content, 'html')
        msg.attach(html_part)

        # Adjuntar imagen QR
        qr_attachment = MIMEBase('image', 'png')
        qr_attachment.set_payload(qr_image)
        encoders.encode_base64(qr_attachment)
        qr_attachment.add_header(
            'Content-Disposition',
            'attachment',
            filename=f'certificado_qr_{cert_uuid[:8]}.png'
        )
        msg.attach(qr_attachment)

        # Enviar email
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)

        logger.info(f"QR email sent successfully to {email_to}")
        return True

    except Exception as e:
        logger.error(f"Error sending QR email to {email_to}: {str(e)}")
        return False


async def update_last_validation_background(
    sheet_id: int,
    row_id: int
) -> None:
    """
    Tarea en background para actualizar la última validación.

    Args:
        sheet_id: ID de la hoja
        row_id: ID de la fila
    """
    try:
        service = OnboardingSmartsheetService()
        await service.update_last_validation(sheet_id, row_id)
        logger.info(f"Background task completed: updated last validation for row {row_id}")
    except Exception as e:
        logger.error(f"Background task failed: {str(e)}")


@router.post(
    "/generate",
    response_model=OnboardingGenerateResponse,
    responses={
        400: {"model": OnboardingErrorResponse, "description": "Score too low or invalid data"},
        500: {"model": OnboardingErrorResponse, "description": "Internal server error"},
        502: {"model": OnboardingErrorResponse, "description": "Smartsheet API error"}
    },
    summary="Generate QR Code Certificate",
    description="""
    Generates a QR code certificate for a user who passed the onboarding evaluation.

    **Triggered by Smartsheet Bridge**

    This endpoint:
    1. Validates that the score is >= 80
    2. Generates a unique UUIDv4 certificate ID
    3. Creates a QR code with the validation URL
    4. Sends the QR code via email to the user
    5. Updates the Smartsheet row with certificate data

    **Required fields:**
    - `row_id`: Smartsheet row ID
    - `full_name`: User's full name
    - `email`: User's email address
    - `score`: Evaluation score (must be >= 80)
    """
)
async def generate_qr_certificate(
    request: OnboardingGenerateRequest
):
    """
    Endpoint para generar un certificado QR de onboarding.
    """
    logger.info(
        f"POST /onboarding/generate - "
        f"row_id={request.row_id}, email={request.email}, score={request.score}"
    )

    # 1. Determinar si el certificado es válido basado en el score
    is_valid = request.score >= MINIMUM_SCORE
    if not is_valid:
        logger.info(
            f"Score below minimum for row {request.row_id}: {request.score} < {MINIMUM_SCORE}. "
            f"Certificate will be generated but marked as invalid."
        )

    try:
        # 2. Generar UUID seguro
        cert_uuid = str(uuid.uuid4())
        logger.info(f"Generated certificate UUID: {cert_uuid}")

        # 3. Calcular fecha de vencimiento
        expiration_date = datetime.utcnow() + timedelta(days=CERTIFICATE_VALIDITY_DAYS)

        # 4. Generar código QR
        qr_image = generate_certificate_qr(cert_uuid, API_BASE_URL)

        # 5. Enviar email con QR adjunto
        email_sent = send_qr_email(
            email_to=request.email,
            full_name=request.full_name,
            qr_image=qr_image,
            expiration_date=expiration_date,
            cert_uuid=cert_uuid
        )

        if not email_sent:
            logger.error(f"Failed to send email to {request.email}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "success": False,
                    "error": "EMAIL_SEND_FAILED",
                    "message": f"Failed to send email to {request.email}"
                }
            )

        # 6. Actualizar Smartsheet
        # Obtener SHEET_ID del environment o usar el proporcionado
        sheet_id = getattr(settings, 'SHEET_ID', None)

        if not sheet_id:
            logger.warning("SHEET_ID not configured, skipping Smartsheet update")
            smartsheet_updated = False
        else:
            try:
                service = get_onboarding_service()
                smartsheet_updated = await service.update_row_with_certificate(
                    sheet_id=int(sheet_id),
                    row_id=request.row_id,
                    cert_uuid=cert_uuid,
                    expiration_date=expiration_date,
                    is_valid=is_valid,
                    score=request.score
                )
            except OnboardingSmartsheetServiceError as e:
                logger.error(f"Smartsheet update failed: {str(e)}")
                # No fallamos el endpoint completo si solo falla Smartsheet
                smartsheet_updated = False

        # 7. Construir respuesta exitosa
        response_data = OnboardingGenerateData(
            cert_uuid=cert_uuid,
            expiration_date=expiration_date.strftime('%Y-%m-%d'),
            email_sent=email_sent,
            smartsheet_updated=smartsheet_updated
        )

        logger.info(
            f"Successfully generated certificate for row {request.row_id}: "
            f"uuid={cert_uuid}, email_sent={email_sent}, smartsheet_updated={smartsheet_updated}"
        )

        return OnboardingGenerateResponse(
            success=True,
            message="QR code generated and sent successfully",
            data=response_data
        )

    except HTTPException:
        raise
    except OnboardingSmartsheetServiceError as e:
        logger.error(f"Smartsheet service error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "success": False,
                "error": "SMARTSHEET_ERROR",
                "message": f"Smartsheet service error: {str(e)}"
            }
        )
    except Exception as e:
        logger.error(f"Unexpected error generating certificate: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "error": "INTERNAL_ERROR",
                "message": f"Internal server error: {str(e)}"
            }
        )


@router.get(
    "/validate",
    response_class=RedirectResponse,
    summary="Validate QR Code Certificate",
    description="""
    Validates a QR code certificate by its UUID.

    **Scanned by Security Personnel**

    This endpoint:
    1. Searches for the certificate in Smartsheet
    2. Checks if the certificate exists and is not expired
    3. If VALID: Updates 'Última Validación' in background, redirects to success page
    4. If INVALID: Redirects to access denied page

    **Response:**
    - HTTP 302 redirect to success or access denied page
    """,
    responses={
        302: {"description": "Redirect to validation result page"}
    }
)
async def validate_qr_certificate(
    background_tasks: BackgroundTasks,
    id: str = Query(..., description="Certificate UUID to validate", min_length=36, max_length=36)
):
    """
    Endpoint para validar un certificado QR de onboarding.
    """
    logger.info(f"GET /onboarding/validate - id={id}")

    # Validar formato UUID
    try:
        uuid.UUID(id)
    except ValueError:
        logger.warning(f"Invalid UUID format: {id}")
        return RedirectResponse(
            url=REDIRECT_INVALID,
            status_code=status.HTTP_302_FOUND
        )

    # Obtener SHEET_ID del environment
    sheet_id = getattr(settings, 'SHEET_ID', None)

    if not sheet_id:
        logger.error("SHEET_ID not configured")
        return RedirectResponse(
            url=REDIRECT_INVALID,
            status_code=status.HTTP_302_FOUND
        )

    try:
        service = get_onboarding_service()

        # Buscar certificado en Smartsheet
        certificate = await service.get_certificate_by_uuid(
            sheet_id=int(sheet_id),
            cert_uuid=id
        )

        if not certificate:
            logger.warning(f"Certificate not found: {id}")
            return RedirectResponse(
                url=REDIRECT_INVALID,
                status_code=status.HTTP_302_FOUND
            )

        # Actualizar última validación en background (siempre que se escanee)
        row_id = certificate.get('row_id')
        if row_id:
            background_tasks.add_task(
                update_last_validation_background,
                int(sheet_id),
                row_id
            )

        # Verificar si el certificado es válido (score >= 80 y no expirado)
        if not service.is_certificate_valid(certificate):
            logger.warning(f"Certificate invalid or expired: {id}")
            return RedirectResponse(
                url=REDIRECT_INVALID,
                status_code=status.HTTP_302_FOUND
            )

        # Redirigir a página de certificación válida
        redirect_url = f"{REDIRECT_VALID}/{id}"
        logger.info(f"Certificate {id} validated successfully, redirecting to {redirect_url}")

        return RedirectResponse(
            url=redirect_url,
            status_code=status.HTTP_302_FOUND
        )

    except OnboardingSmartsheetServiceError as e:
        logger.error(f"Smartsheet error during validation: {str(e)}")
        return RedirectResponse(
            url=REDIRECT_INVALID,
            status_code=status.HTTP_302_FOUND
        )
    except Exception as e:
        logger.error(f"Unexpected error validating certificate: {str(e)}")
        return RedirectResponse(
            url=REDIRECT_INVALID,
            status_code=status.HTTP_302_FOUND
        )

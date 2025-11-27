# app/api/v1/endpoints/onboarding.py
from fastapi import APIRouter, Query, HTTPException, BackgroundTasks, status
from fastapi.responses import RedirectResponse
import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional
import smtplib
import asyncio
from urllib.parse import quote
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

from pydantic import BaseModel
from app.schemas.onboarding_schemas import (
    OnboardingGenerateRequest,
    OnboardingGenerateResponse,
    OnboardingGenerateData,
    OnboardingErrorResponse,
    ExamSubmitRequest,
    ExamSubmitResponse
)


class CertificateInfoResponse(BaseModel):
    """Response model for certificate info endpoint"""
    success: bool
    status: str  # 'approved', 'not_approved', 'expired', 'not_found'
    nombre: str
    vencimiento: str
    score: float
    is_expired: bool
    message: str
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
    cert_uuid: str,
    is_valid: bool = True,
    score: float = 0.0
) -> bool:
    """
    Envía el email con el código QR adjunto.

    Args:
        email_to: Email del destinatario
        full_name: Nombre completo del usuario
        qr_image: Imagen del QR en bytes
        expiration_date: Fecha de vencimiento del certificado
        cert_uuid: UUID del certificado
        is_valid: Si el certificado es válido (score >= 80)
        score: Puntuación obtenida

    Returns:
        True si el email se envió exitosamente
    """
    try:
        # Crear mensaje multipart
        msg = MIMEMultipart('mixed')

        if is_valid:
            msg['Subject'] = f"Onboarding Aprobado - {full_name}"
        else:
            msg['Subject'] = f"Onboarding No Aprobado - {full_name}"

        msg['From'] = "Entersys <no-reply@entersys.mx>"
        msg['To'] = email_to

        # Contenido HTML del email - diferente según si aprobó o no
        if is_valid:
            # Email para certificado aprobado - Branding FEMSA
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
                        background-color: #f9fafb;
                    }}
                    .container {{
                        background-color: #ffffff;
                        border-radius: 8px;
                        padding: 30px;
                        margin: 20px 0;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    }}
                    .header {{
                        text-align: center;
                        margin-bottom: 30px;
                        padding-bottom: 20px;
                        border-bottom: 3px solid #FFC600;
                    }}
                    .logo {{
                        max-height: 50px;
                        margin-bottom: 15px;
                    }}
                    h1 {{
                        color: #1f2937;
                        font-size: 24px;
                        margin: 0;
                    }}
                    .certificate-info {{
                        background-color: #f0fdf4;
                        border-left: 4px solid #16a34a;
                        padding: 15px;
                        margin: 20px 0;
                        border-radius: 4px;
                    }}
                    .qr-section {{
                        text-align: center;
                        margin: 30px 0;
                        padding: 20px;
                        background-color: #f9fafb;
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
                        color: #16a34a;
                        font-weight: bold;
                    }}
                    .accent {{
                        color: #D91E18;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <img src="https://entersys.mx/images/coca-cola-femsa-logo.png" alt="FEMSA" class="logo">
                        <h1>Onboarding Aprobado</h1>
                    </div>

                    <p>Estimado/a <strong>{full_name}</strong>,</p>

                    <p>Tu certificación de Seguridad Industrial ha sido validada correctamente. Has cumplido con todos los requisitos del curso y tu información ha sido aprobada conforme a los estándares de seguridad establecidos.</p>

                    <div class="certificate-info">
                        <p><strong>Detalles de la Certificación:</strong></p>
                        <ul>
                            <li>Calificación: <span class="highlight">{score}%</span></li>
                            <li>Estado: <span class="highlight">APROBADO</span></li>
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

                    <div class="footer">
                        <p>Este es un correo automático, por favor no respondas a este mensaje.</p>
                        <p>&copy; {datetime.utcnow().year} FEMSA - Entersys. Todos los derechos reservados.</p>
                    </div>
                </div>
            </body>
            </html>
            """
        else:
            # Email para certificado NO aprobado - Branding FEMSA
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
                        background-color: #f9fafb;
                    }}
                    .container {{
                        background-color: #ffffff;
                        border-radius: 8px;
                        padding: 30px;
                        margin: 20px 0;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    }}
                    .header {{
                        text-align: center;
                        margin-bottom: 30px;
                        padding-bottom: 20px;
                        border-bottom: 3px solid #FFC600;
                    }}
                    .logo {{
                        max-height: 50px;
                        margin-bottom: 15px;
                    }}
                    h1 {{
                        color: #1f2937;
                        font-size: 24px;
                        margin: 0;
                    }}
                    .result-info {{
                        background-color: #FEE2E2;
                        border-left: 4px solid #D91E18;
                        padding: 15px;
                        margin: 20px 0;
                        border-radius: 4px;
                    }}
                    .qr-section {{
                        text-align: center;
                        margin: 30px 0;
                        padding: 20px;
                        background-color: #f9fafb;
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
                    .highlight-fail {{
                        color: #D91E18;
                        font-weight: bold;
                    }}
                    .next-steps {{
                        background-color: #FEF3C7;
                        border-left: 4px solid #F59E0B;
                        padding: 15px;
                        margin: 20px 0;
                        border-radius: 4px;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <img src="https://entersys.mx/images/coca-cola-femsa-logo.png" alt="FEMSA" class="logo">
                        <h1>Onboarding No Aprobado</h1>
                    </div>

                    <p>Estimado/a <strong>{full_name}</strong>,</p>

                    <p>Tu certificación de Seguridad Industrial no pudo ser validada. La información proporcionada o los requisitos del curso no cumplen con los estándares mínimos de seguridad establecidos.</p>

                    <div class="result-info">
                        <p><strong>Resultado de la Evaluación:</strong></p>
                        <ul>
                            <li>Calificación Obtenida: <span class="highlight-fail">{score}%</span></li>
                            <li>Calificación Mínima Requerida: <span class="highlight-fail">80%</span></li>
                            <li>Estado: <span class="highlight-fail">NO APROBADO</span></li>
                        </ul>
                    </div>

                    <div class="next-steps">
                        <p><strong>Próximos Pasos:</strong></p>
                        <p>Por favor revisa las observaciones enviadas, corrige la información o completa los requisitos faltantes para volver a enviar tu solicitud de validación:</p>
                        <ol>
                            <li>Revisar el material de capacitación nuevamente</li>
                            <li>Solicitar una nueva evaluación a su supervisor</li>
                            <li>Obtener una calificación mínima de 80%</li>
                        </ol>
                    </div>

                    <div class="qr-section">
                        <p><strong>Se adjunta un código QR de referencia.</strong></p>
                        <p>Este código NO es válido para acceso a las instalaciones.</p>
                    </div>

                    <p>Si tiene preguntas sobre el proceso de re-evaluación, contacte a su supervisor o al departamento de seguridad.</p>

                    <div class="footer">
                        <p>Este es un correo automático, por favor no respondas a este mensaje.</p>
                        <p>&copy; {datetime.utcnow().year} FEMSA - Entersys. Todos los derechos reservados.</p>
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


async def update_smartsheet_certificate_background(
    sheet_id: int,
    row_id: int,
    cert_uuid: str,
    expiration_date: datetime,
    is_valid: bool,
    score: float
) -> None:
    """
    Tarea en background para actualizar Smartsheet con datos del certificado.

    Args:
        sheet_id: ID de la hoja
        row_id: ID de la fila
        cert_uuid: UUID del certificado
        expiration_date: Fecha de vencimiento
        is_valid: Si el certificado es válido
        score: Puntuación obtenida
    """
    try:
        service = OnboardingSmartsheetService()
        result = await asyncio.wait_for(
            service.update_row_with_certificate(
                sheet_id=sheet_id,
                row_id=row_id,
                cert_uuid=cert_uuid,
                expiration_date=expiration_date,
                is_valid=is_valid,
                score=score
            ),
            timeout=30.0  # 30 second timeout
        )
        if result:
            logger.info(f"Background task completed: updated Smartsheet for row {row_id}")
        else:
            logger.warning(f"Background task: Smartsheet update returned False for row {row_id}")
    except asyncio.TimeoutError:
        logger.error(f"Background task timeout: Smartsheet update for row {row_id} took too long")
    except Exception as e:
        logger.error(f"Background task failed for row {row_id}: {str(e)}")


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
    request: OnboardingGenerateRequest,
    background_tasks: BackgroundTasks
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
            cert_uuid=cert_uuid,
            is_valid=is_valid,
            score=request.score
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

        # 6. Actualizar Smartsheet en background (no bloquear la respuesta)
        # Obtener SHEET_ID del environment o usar el proporcionado
        sheet_id = getattr(settings, 'SHEET_ID', None)

        if not sheet_id:
            logger.warning("SHEET_ID not configured, skipping Smartsheet update")
            smartsheet_updated = False
        else:
            # Agregar tarea en background para actualizar Smartsheet
            background_tasks.add_task(
                update_smartsheet_certificate_background,
                int(sheet_id),
                request.row_id,
                cert_uuid,
                expiration_date,
                is_valid,
                request.score
            )
            smartsheet_updated = True  # Se actualizará en background
            logger.info(f"Smartsheet update scheduled in background for row {request.row_id}")

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

        # Obtener datos del certificado para mostrarlos en la página
        full_name = certificate.get('Nombre Completo', 'Usuario')
        expiration = certificate.get('Vencimiento', '')
        encoded_name = quote(str(full_name))
        encoded_expiration = quote(str(expiration))

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
            redirect_url = f"{REDIRECT_INVALID}?nombre={encoded_name}&vencimiento={encoded_expiration}"
            return RedirectResponse(
                url=redirect_url,
                status_code=status.HTTP_302_FOUND
            )

        # Redirigir a página de certificación válida
        redirect_url = f"{REDIRECT_VALID}/{id}?nombre={encoded_name}&vencimiento={encoded_expiration}"
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


@router.get(
    "/certificate/{cert_uuid}",
    response_model=CertificateInfoResponse,
    summary="Get Certificate Information",
    description="""
    Returns certificate information for dynamic frontend display.

    **Called by Frontend Page**

    This endpoint:
    1. Searches for the certificate in Smartsheet by UUID
    2. Returns all certificate data as JSON
    3. Updates 'Última Validación' timestamp
    4. Determines status: approved, not_approved, or expired

    **Status Logic:**
    - approved: Score >= 80 AND not expired
    - not_approved: Score < 80
    - expired: Past expiration date
    - not_found: Certificate doesn't exist
    """
)
async def get_certificate_info(
    background_tasks: BackgroundTasks,
    cert_uuid: str
):
    """
    Endpoint para obtener información del certificado de forma dinámica.
    """
    logger.info(f"GET /onboarding/certificate/{cert_uuid}")

    # Validar formato UUID
    try:
        uuid.UUID(cert_uuid)
    except ValueError:
        logger.warning(f"Invalid UUID format: {cert_uuid}")
        return CertificateInfoResponse(
            success=False,
            status="not_found",
            nombre="",
            vencimiento="",
            score=0,
            is_expired=False,
            message="UUID inválido"
        )

    # Obtener SHEET_ID del environment
    sheet_id = getattr(settings, 'SHEET_ID', None)

    if not sheet_id:
        logger.error("SHEET_ID not configured")
        return CertificateInfoResponse(
            success=False,
            status="not_found",
            nombre="",
            vencimiento="",
            score=0,
            is_expired=False,
            message="Configuración del servidor incompleta"
        )

    try:
        service = get_onboarding_service()

        # Buscar certificado en Smartsheet
        certificate = await service.get_certificate_by_uuid(
            sheet_id=int(sheet_id),
            cert_uuid=cert_uuid
        )

        if not certificate:
            logger.warning(f"Certificate not found: {cert_uuid}")
            return CertificateInfoResponse(
                success=False,
                status="not_found",
                nombre="",
                vencimiento="",
                score=0,
                is_expired=False,
                message="Certificado no encontrado"
            )

        # Extraer datos del certificado
        full_name = certificate.get('Nombre Completo', 'Usuario')
        expiration_str = certificate.get('Vencimiento', '')
        score_value = certificate.get('Score', 0)

        # Parsear score
        try:
            score = float(str(score_value).replace('%', '').strip()) if score_value else 0
        except (ValueError, TypeError):
            score = 0

        # Parsear fecha de vencimiento y verificar si expiró
        is_expired = False
        formatted_expiration = expiration_str

        if expiration_str:
            expiration_date = None
            for date_format in ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%m/%d/%y', '%d/%m/%y']:
                try:
                    expiration_date = datetime.strptime(str(expiration_str), date_format)
                    # Handle 2-digit years
                    if expiration_date.year < 100:
                        expiration_date = expiration_date.replace(year=expiration_date.year + 2000)
                    break
                except ValueError:
                    continue

            if expiration_date:
                is_expired = expiration_date.date() < datetime.utcnow().date()
                formatted_expiration = expiration_date.strftime('%d/%m/%Y')

        # Actualizar última validación en background
        row_id = certificate.get('row_id')
        if row_id:
            background_tasks.add_task(
                update_last_validation_background,
                int(sheet_id),
                row_id
            )
            logger.info(f"Scheduled last validation update for row {row_id}")

        # Determinar estado del certificado
        if is_expired:
            status_str = "expired"
            message = "Tu certificación de Seguridad Industrial ha expirado y NO está autorizado para ingresar a las instalaciones. Por favor contacta a tu supervisor para renovar tu certificación."
        elif score < 80:
            status_str = "not_approved"
            message = "Tu certificación de Seguridad Industrial no pudo ser validada. La información proporcionada o los requisitos del curso no cumplen con los estándares mínimos de seguridad establecidos."
        else:
            status_str = "approved"
            message = "Tu certificación de Seguridad Industrial ha sido validada correctamente. Has cumplido con todos los requisitos del curso y tu información ha sido aprobada conforme a los estándares de seguridad establecidos."

        logger.info(f"Certificate {cert_uuid} info retrieved: status={status_str}, score={score}, expired={is_expired}")

        return CertificateInfoResponse(
            success=True,
            status=status_str,
            nombre=str(full_name),
            vencimiento=formatted_expiration,
            score=score,
            is_expired=is_expired,
            message=message
        )

    except OnboardingSmartsheetServiceError as e:
        logger.error(f"Smartsheet error getting certificate info: {str(e)}")
        return CertificateInfoResponse(
            success=False,
            status="not_found",
            nombre="",
            vencimiento="",
            score=0,
            is_expired=False,
            message=f"Error de Smartsheet: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error getting certificate info: {str(e)}")
        return CertificateInfoResponse(
            success=False,
            status="not_found",
            nombre="",
            vencimiento="",
            score=0,
            is_expired=False,
            message=f"Error interno: {str(e)}"
        )


# ============================================
# Endpoint para el formulario público de examen
# ============================================

# Mapeo de columnas de Smartsheet para el examen
EXAM_COLUMN_MAPPING = {
    "Nombre Completo": "nombre_completo",
    "RFC Colaborador": "rfc_colaborador",
    "RFC Empresa": "rfc_empresa",
    "NSS de colaborador": "nss",
    "Tipo de Servicio": "tipo_servicio",
    "Proveedor": "proveedor",
    "Email": "email",
    "Score": "score",
    "Estado": "estado"
}

# Mapeo de preguntas del examen a columnas de Smartsheet
# Usando los IDs de columna directamente para evitar problemas de encoding
EXAM_QUESTION_COLUMNS = {
    1: {"column_id": 2130769435381636, "column_name": "Las siglas PPP corresponden a:"},
    2: {"column_id": 6634369062752132, "column_name": "Poder reconocer peligros y riesgos para reducirlos"},
    3: {"column_id": 4382569249066884, "column_name": "Son tres elementos del equipo de protección person"},
    4: {"column_id": 8886168876437380, "column_name": "Tres acciones que debemos realizar en caso de emer"},
    5: {"column_id": 90075854229380, "column_name": "Es un incidente que tuvo graves consecuencias o im"},
    6: {"column_id": 4593675481599876, "column_name": "Estado patológico o condición, inidentificable, ad"},
    7: {"column_id": 2341875667914628, "column_name": "Establecer zonas de seguridad ¿es parte de las Reg"},
    8: {"column_id": 6845475295285124, "column_name": "Es la principal prioridad de la compañía"},
    9: {"column_id": 1215975761072004, "column_name": "Ejemplo de incidente"},
    10: {"column_id": 5719575388442500, "column_name": "Gravedad y frecuencia con que puede ocurrir un inc"}
}


@router.post(
    "/submit-exam",
    response_model=ExamSubmitResponse,
    summary="Enviar examen de seguridad",
    description="""
    Endpoint público para enviar el examen de certificación de seguridad.

    **Flujo:**
    1. Recibe datos personales y respuestas del examen
    2. Calcula el score basado en respuestas correctas
    3. Inserta una nueva fila en Smartsheet con todos los datos
    4. Retorna si aprobó o no (score >= 80)

    **Nota:** Este endpoint NO genera UUID ni QR. Eso lo maneja Smartsheet Bridge.
    """
)
async def submit_exam(request: ExamSubmitRequest):
    """
    Endpoint para enviar el examen de seguridad y registrar en Smartsheet.
    """
    logger.info(
        f"POST /onboarding/submit-exam - "
        f"email={request.email}, nombre={request.nombre_completo}"
    )

    try:
        # 1. Calcular score basado en respuestas correctas
        correct_count = sum(1 for answer in request.answers if answer.is_correct)
        calculated_score = (correct_count / 10) * 100

        logger.info(f"Score calculado: {calculated_score}% ({correct_count}/10 correctas)")

        # 2. Determinar si aprobó
        approved = calculated_score >= 80
        estado = "Aprobado" if approved else "No Aprobado"

        # 3. Preparar datos para Smartsheet
        sheet_id = getattr(settings, 'SHEET_ID', None)

        if not sheet_id:
            logger.error("SHEET_ID not configured")
            return ExamSubmitResponse(
                success=False,
                approved=False,
                score=calculated_score,
                message="Error de configuración del servidor",
                smartsheet_row_id=None
            )

        # 4. Construir fila para Smartsheet
        service = OnboardingSmartsheetService()

        # Obtener mapeo de columnas (forzar recarga limpiando cache)
        service._column_map = {}
        service._reverse_column_map = {}
        await service._get_column_maps(int(sheet_id))

        # Log de columnas de validación disponibles para debug
        validation_cols = [k for k in service._reverse_column_map.keys() if 'Validacion' in k or 'validacion' in k.lower()]
        logger.info(f"Smartsheet validation columns: {validation_cols}")

        # Verificar que Validacion P2 existe
        if 'Validacion P2' in service._reverse_column_map:
            logger.info(f"Validacion P2 column ID: {service._reverse_column_map['Validacion P2']}")
        else:
            logger.warning("Validacion P2 NOT FOUND in column map!")

        # Construir celdas
        cells = []

        # Columnas que tienen fórmulas en Smartsheet y NO se pueden escribir
        FORMULA_COLUMNS = {"Score", "Estado"}

        # Datos personales (excluir columnas con fórmulas)
        personal_data = {
            "Nombre Completo": request.nombre_completo,
            "RFC Colaborador": request.rfc_colaborador,
            "RFC Empresa": request.rfc_empresa or "",
            "NSS de colaborador": request.nss or "",
            "Tipo de Servicio": request.tipo_servicio or "",
            "Proveedor": request.proveedor,
            "Email": request.email
        }

        for column_name, value in personal_data.items():
            if column_name in service._reverse_column_map and column_name not in FORMULA_COLUMNS:
                cells.append({
                    'column_id': service._reverse_column_map[column_name],
                    'value': value
                })

        # Respuestas del examen - solo guardar las respuestas textuales
        # Las columnas de validación tienen formato condicional y se calculan automáticamente
        # Usamos los IDs de columna directamente para evitar problemas de encoding
        for answer in request.answers:
            question_mapping = EXAM_QUESTION_COLUMNS.get(answer.question_id)

            if not question_mapping:
                logger.warning(f"No mapping found for question {answer.question_id}")
                continue

            # Guardar la respuesta textual usando el column_id directamente
            column_id = question_mapping.get("column_id")
            if column_id:
                cells.append({
                    'column_id': column_id,
                    'value': answer.answer
                })
                logger.info(f"Q{answer.question_id} (col_id={column_id}): {answer.answer}")
            else:
                logger.warning(f"No column_id found for Q{answer.question_id}")

        # 5. Insertar fila en Smartsheet con datos personales y respuestas
        import smartsheet

        new_row = smartsheet.models.Row()
        new_row.to_bottom = True
        new_row.cells = [smartsheet.models.Cell(cell) for cell in cells]

        logger.info(f"Insertando fila con {len(cells)} celdas")
        response = service.client.Sheets.add_rows(int(sheet_id), [new_row])

        if response.message == 'SUCCESS' and response.result:
            row_id = response.result[0].id
            logger.info(f"Fila insertada en Smartsheet: row_id={row_id}")

            message = f"Examen enviado exitosamente. {'¡Felicidades! Has aprobado' if approved else 'No aprobaste'} con {calculated_score:.0f}%."

            return ExamSubmitResponse(
                success=True,
                approved=approved,
                score=calculated_score,
                message=message,
                smartsheet_row_id=row_id
            )
        else:
            logger.error(f"Error insertando fila en Smartsheet: {response.message}")
            return ExamSubmitResponse(
                success=False,
                approved=approved,
                score=calculated_score,
                message="Error al guardar en el sistema. Por favor intenta de nuevo.",
                smartsheet_row_id=None
            )

    except Exception as e:
        logger.error(f"Error en submit-exam: {str(e)}")
        return ExamSubmitResponse(
            success=False,
            approved=False,
            score=0,
            message=f"Error interno: {str(e)}",
            smartsheet_row_id=None
        )

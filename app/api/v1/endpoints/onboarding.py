# app/api/v1/endpoints/onboarding.py
from fastapi import APIRouter, Query, HTTPException, BackgroundTasks, status, UploadFile, File, Form
from fastapi.responses import RedirectResponse, StreamingResponse
import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional, List
import asyncio
from urllib.parse import quote
import os
import io
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

# Gmail API imports
from google.oauth2 import service_account
from googleapiclient.discovery import build

from pydantic import BaseModel
from google.cloud import storage
from app.core.config import settings
from app.schemas.onboarding_schemas import (
    OnboardingGenerateRequest,
    OnboardingGenerateResponse,
    OnboardingGenerateData,
    OnboardingErrorResponse,
    ExamSubmitRequest,
    ExamSubmitResponse,
    ExamStatusResponse,
    SectionResult,
    ResendCertificateRequest,
    ResendCertificateResponse
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
    url_imagen: Optional[str] = None  # URL de la foto de credencial


class CredentialResponse(BaseModel):
    """Response model for virtual credential endpoint"""
    success: bool
    status: str  # 'approved', 'not_approved', 'expired', 'not_found'
    nombre: str
    rfc: str
    proveedor: Optional[str] = None
    tipo_servicio: Optional[str] = None
    nss: Optional[str] = None
    rfc_empresa: Optional[str] = None  # RFC de la empresa
    email: Optional[str] = None
    cert_uuid: Optional[str] = None
    vencimiento: Optional[str] = None
    fecha_emision: Optional[str] = None
    url_imagen: Optional[str] = None  # URL de la foto de credencial en GCS
    is_expired: bool = False
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
MINIMUM_SECTION_SCORE = 80.0  # Mínimo 80% en cada sección para aprobar
CERTIFICATE_VALIDITY_DAYS = 365
MAX_ATTEMPTS = 3
API_BASE_URL = "https://api.entersys.mx"
REDIRECT_VALID = "https://entersys.mx/certificacion-seguridad"
REDIRECT_INVALID = "https://entersys.mx/access-denied"

# Definición de secciones del examen
EXAM_SECTIONS = {
    1: {"name": "Seguridad", "questions": range(1, 11)},    # Preguntas 1-10
    2: {"name": "Inocuidad", "questions": range(11, 21)},   # Preguntas 11-20
    3: {"name": "Ambiental", "questions": range(21, 31)}    # Preguntas 21-30
}


def get_onboarding_service() -> OnboardingSmartsheetService:
    """Dependency para obtener instancia del servicio"""
    return OnboardingSmartsheetService()


def get_gmail_service():
    """
    Crea un servicio de Gmail API usando Service Account con domain-wide delegation.
    El service account impersona a no-reply@entersys.mx para enviar correos.
    """
    # En Docker el archivo está en /app/service-account.json
    # Localmente puede estar en la raíz del proyecto
    SERVICE_ACCOUNT_FILE = os.environ.get(
        "GOOGLE_APPLICATION_CREDENTIALS",
        "/app/service-account.json"
    )

    SCOPES = ['https://www.googleapis.com/auth/gmail.send']
    DELEGATED_USER = settings.SMTP_FROM_EMAIL  # no-reply@entersys.mx

    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=SCOPES
    )

    # Impersonar al usuario delegado
    delegated_credentials = credentials.with_subject(DELEGATED_USER)

    service = build('gmail', 'v1', credentials=delegated_credentials)
    return service


def send_email_via_gmail_api(
    to_emails: List[str],
    subject: str,
    html_content: str,
    attachments: List[dict] = None
) -> bool:
    """
    Envía un email usando Gmail API con Service Account y domain-wide delegation.

    Args:
        to_emails: Lista de emails destinatarios
        subject: Asunto del email
        html_content: Contenido HTML del email
        attachments: Lista de adjuntos [{"filename": "name.png", "content": base64_string}]

    Returns:
        True si el email se envió exitosamente
    """
    try:
        # Crear mensaje MIME
        if attachments:
            msg = MIMEMultipart('mixed')
            html_part = MIMEText(html_content, 'html', 'utf-8')
            msg.attach(html_part)

            # Agregar adjuntos
            for attachment in attachments:
                filename = attachment.get("filename", "attachment")
                content_b64 = attachment.get("content", "")
                try:
                    content_bytes = base64.b64decode(content_b64)
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(content_bytes)
                    encoders.encode_base64(part)
                    part.add_header('Content-Disposition', f'attachment; filename="{filename}"')
                    msg.attach(part)
                except Exception as e:
                    logger.warning(f"Could not attach file {filename}: {e}")
        else:
            msg = MIMEMultipart('alternative')
            html_part = MIMEText(html_content, 'html', 'utf-8')
            msg.attach(html_part)

        msg['Subject'] = subject
        msg['From'] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
        msg['To'] = ', '.join(to_emails)

        # Codificar mensaje para Gmail API
        raw_message = base64.urlsafe_b64encode(msg.as_bytes()).decode('utf-8')

        # Enviar via Gmail API
        service = get_gmail_service()
        message = service.users().messages().send(
            userId='me',
            body={'raw': raw_message}
        ).execute()

        logger.info(f"Email sent successfully via Gmail API to {to_emails}, Message ID: {message.get('id')}")
        return True

    except Exception as e:
        logger.error(f"Error sending email via Gmail API to {to_emails}: {str(e)}")
        return False


def send_email_via_smtp(
    to_emails: List[str],
    subject: str,
    html_content: str,
    attachments: List[dict] = None
) -> bool:
    """
    Wrapper que usa Gmail API para enviar emails.
    Mantiene el nombre de la función por compatibilidad.
    """
    return send_email_via_gmail_api(to_emails, subject, html_content, attachments)


def send_email_via_resend(
    to_emails: List[str],
    subject: str,
    html_content: str,
    attachments: List[dict] = None
) -> bool:
    """
    Envía un email usando SMTP de Gmail/Google Workspace.
    Mantiene el nombre de la función por compatibilidad con el resto del código.

    Args:
        to_emails: Lista de emails destinatarios
        subject: Asunto del email
        html_content: Contenido HTML del email
        attachments: Lista de adjuntos [{"filename": "name.png", "content": base64_string}]

    Returns:
        True si el email se envió exitosamente
    """
    return send_email_via_smtp(to_emails, subject, html_content, attachments)


def send_qr_email(
    email_to: str,
    full_name: str,
    qr_image: bytes,
    expiration_date: datetime,
    cert_uuid: str,
    is_valid: bool = True,
    score: float = 0.0,
    collaborator_data: dict = None,
    section_results: dict = None
) -> bool:
    """
    Envía el email con el código QR y PDF del certificado adjuntos.

    Args:
        email_to: Email del destinatario
        full_name: Nombre completo del usuario
        qr_image: Imagen del QR en bytes
        expiration_date: Fecha de vencimiento del certificado
        cert_uuid: UUID del certificado
        is_valid: Si el certificado es válido (score >= 80)
        score: Puntuación obtenida
        collaborator_data: Datos adicionales del colaborador para el PDF (opcional)
        section_results: Resultados por sección para el PDF (opcional)

    Returns:
        True si el email se envió exitosamente
    """
    try:
        # Definir asunto según resultado
        if is_valid:
            subject = f"Onboarding Aprobado - {full_name}"
        else:
            subject = f"Onboarding No Aprobado - {full_name}"

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
                        max-height: 80px;
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
                            <li>Calificación: <span class="highlight">{score:.2f}%</span></li>
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
                        max-height: 80px;
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
                            <li>Calificación Obtenida: <span class="highlight-fail">{score:.2f}%</span></li>
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

        # Preparar adjuntos
        attachments = []

        # Adjunto QR
        qr_attachment = {
            "filename": f"certificado_qr_{cert_uuid[:8]}.png",
            "content": base64.b64encode(qr_image).decode('utf-8')
        }
        attachments.append(qr_attachment)

        # Generar y adjuntar PDF si está aprobado
        if is_valid:
            try:
                from app.utils.pdf_utils import generate_certificate_pdf

                # Preparar datos para el PDF
                pdf_data = collaborator_data.copy() if collaborator_data else {}
                pdf_data.update({
                    "full_name": full_name,
                    "email": email_to,
                    "cert_uuid": cert_uuid,
                    "vencimiento": expiration_date.strftime('%d/%m/%Y'),
                    "fecha_emision": datetime.utcnow().strftime('%d/%m/%Y'),
                    "is_approved": True,
                })

                # Generar PDF
                pdf_bytes = generate_certificate_pdf(
                    collaborator_data=pdf_data,
                    section_results=section_results,
                    qr_image_bytes=qr_image
                )

                pdf_attachment = {
                    "filename": f"certificado_{cert_uuid[:8]}.pdf",
                    "content": base64.b64encode(pdf_bytes).decode('utf-8')
                }
                attachments.append(pdf_attachment)
                logger.info(f"PDF attachment generated for {email_to}")
            except Exception as e:
                logger.warning(f"Could not generate PDF attachment: {e}")

        # Enviar email via SMTP
        result = send_email_via_resend(
            to_emails=[email_to],
            subject=subject,
            html_content=html_content,
            attachments=attachments
        )

        if result:
            logger.info(f"QR email sent successfully to {email_to}")
        return result

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


def send_third_attempt_alert_email(
    colaborador_data: dict,
    attempts_info: dict
) -> bool:
    """
    Envía un correo de alerta cuando un colaborador alcanza su tercer intento fallido.

    Args:
        colaborador_data: Datos del colaborador (nombre, rfc, email, proveedor, etc.)
        attempts_info: Información de los intentos (total, aprobados, fallidos, registros)

    Returns:
        True si el email se envió exitosamente
    """
    try:
        # Definir asunto y destinatarios
        subject = f"⚠️ ALERTA: Tercer Intento Fallido - {colaborador_data.get('nombre_completo', 'Colaborador')}"
        to_emails = [
            "rodrigo.dalay@entersys.mx",
            "mario.dominguez@entersys.mx",
            "armando.cortes@entersys.mx",
            "giovvani.melchor@entersys.mx"
        ]

        # Generar tabla de historial de intentos
        historial_html = ""
        for i, registro in enumerate(attempts_info.get('registros', []), 1):
            estado_class = "approved" if registro.get('is_approved') else "failed"
            estado_text = "Aprobado" if registro.get('is_approved') else "No Aprobado"
            historial_html += f"""
            <tr class="{estado_class}">
                <td>{i}</td>
                <td>{registro.get('score', 'N/A')}</td>
                <td>{estado_text}</td>
            </tr>
            """

        # Generar tabla de resultados por seccion del intento actual
        secciones_html = ""
        for s in colaborador_data.get('section_results', []):
            sec_class = "approved" if s.get('approved') else "failed"
            sec_estado = "Aprobado" if s.get('approved') else "No Aprobado"
            secciones_html += f"""
                        <tr class="{sec_class}">
                            <td>{s.get('section_name', 'N/A')}</td>
                            <td>{s.get('correct_count', 0)}/{s.get('total_questions', 10)}</td>
                            <td>{s.get('score', 0)}%</td>
                            <td>{sec_estado}</td>
                        </tr>"""

        # Score promedio general
        promedio_general = colaborador_data.get('overall_score', 0)

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
                    max-width: 700px;
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
                    border-bottom: 3px solid #DC2626;
                }}
                .alert-icon {{
                    font-size: 48px;
                    margin-bottom: 10px;
                }}
                h1 {{
                    color: #DC2626;
                    font-size: 24px;
                    margin: 0;
                }}
                .info-box {{
                    background-color: #FEF2F2;
                    border-left: 4px solid #DC2626;
                    padding: 15px;
                    margin: 20px 0;
                    border-radius: 4px;
                }}
                .colaborador-info {{
                    background-color: #F3F4F6;
                    padding: 20px;
                    border-radius: 8px;
                    margin: 20px 0;
                }}
                .colaborador-info h3 {{
                    margin-top: 0;
                    color: #374151;
                    border-bottom: 2px solid #D1D5DB;
                    padding-bottom: 10px;
                }}
                .colaborador-info p {{
                    margin: 8px 0;
                }}
                .colaborador-info strong {{
                    display: inline-block;
                    width: 150px;
                    color: #6B7280;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin: 20px 0;
                }}
                th, td {{
                    padding: 12px;
                    text-align: left;
                    border-bottom: 1px solid #E5E7EB;
                }}
                th {{
                    background-color: #F3F4F6;
                    font-weight: 600;
                    color: #374151;
                }}
                tr.approved td {{
                    color: #059669;
                }}
                tr.failed td {{
                    color: #DC2626;
                }}
                .summary {{
                    display: flex;
                    justify-content: space-around;
                    margin: 20px 0;
                    text-align: center;
                }}
                .summary-item {{
                    padding: 15px 25px;
                    border-radius: 8px;
                }}
                .summary-item.total {{
                    background-color: #EFF6FF;
                    color: #1D4ED8;
                }}
                .summary-item.approved {{
                    background-color: #ECFDF5;
                    color: #059669;
                }}
                .summary-item.failed {{
                    background-color: #FEF2F2;
                    color: #DC2626;
                }}
                .summary-item .number {{
                    font-size: 32px;
                    font-weight: bold;
                }}
                .summary-item .label {{
                    font-size: 12px;
                    text-transform: uppercase;
                }}
                .footer {{
                    text-align: center;
                    margin-top: 30px;
                    padding-top: 20px;
                    border-top: 1px solid #e5e7eb;
                    font-size: 12px;
                    color: #6b7280;
                }}
                .action-needed {{
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
                    <div class="alert-icon">⚠️</div>
                    <h1>Alerta: Tercer Intento Fallido</h1>
                </div>

                <div class="info-box">
                    <p><strong>El siguiente colaborador ha alcanzado su tercer intento fallido</strong> en el examen de certificación de Seguridad Industrial.</p>
                </div>

                <div class="colaborador-info">
                    <h3>Datos del Colaborador</h3>
                    <p><strong>Nombre:</strong> {colaborador_data.get('nombre_completo', 'N/A')}</p>
                    <p><strong>RFC:</strong> {colaborador_data.get('rfc_colaborador', 'N/A')}</p>
                    <p><strong>Email:</strong> {colaborador_data.get('email', 'N/A')}</p>
                    <p><strong>Proveedor:</strong> {colaborador_data.get('proveedor', 'N/A')}</p>
                    <p><strong>Tipo de Servicio:</strong> {colaborador_data.get('tipo_servicio', 'N/A')}</p>
                    <p><strong>RFC Empresa:</strong> {colaborador_data.get('rfc_empresa', 'N/A')}</p>
                    <p><strong>NSS:</strong> {colaborador_data.get('nss', 'N/A')}</p>
                </div>

                <h3>Resumen de Intentos</h3>
                <div class="summary">
                    <div class="summary-item total">
                        <div class="number">{attempts_info.get('total', 0)}</div>
                        <div class="label">Total Intentos</div>
                    </div>
                    <div class="summary-item approved">
                        <div class="number">{attempts_info.get('aprobados', 0)}</div>
                        <div class="label">Aprobados</div>
                    </div>
                    <div class="summary-item failed">
                        <div class="number">{attempts_info.get('fallidos', 0)}</div>
                        <div class="label">Fallidos</div>
                    </div>
                </div>

                <h3>Resultado del Tercer Intento</h3>
                <table>
                    <thead>
                        <tr>
                            <th>Sección</th>
                            <th>Correctas</th>
                            <th>Puntaje</th>
                            <th>Estado</th>
                        </tr>
                    </thead>
                    <tbody>
                        {secciones_html}
                    </tbody>
                </table>
                
                <p style="text-align: center; margin-top: 15px; font-size: 16px;">
                    <strong>Promedio General: {promedio_general:.1f}%</strong>
                </p>

                <div class="action-needed">
                    <p><strong>Acción Requerida:</strong></p>
                    <p>Se recomienda contactar al colaborador o su supervisor para determinar los siguientes pasos, ya que ha fallado el examen en múltiples ocasiones.</p>
                </div>

                <div class="footer">
                    <p>Este es un correo automático generado por el sistema de Onboarding de Seguridad.</p>
                    <p>&copy; {datetime.utcnow().year} FEMSA - Entersys. Todos los derechos reservados.</p>
                </div>
            </div>
        </body>
        </html>
        """

        # Enviar email via Resend
        result = send_email_via_resend(
            to_emails=to_emails,
            subject=subject,
            html_content=html_content
        )

        if result:
            logger.info(f"Third attempt alert email sent for RFC {colaborador_data.get('rfc_colaborador')}")
        return result

    except Exception as e:
        logger.error(f"Error sending third attempt alert email: {str(e)}")
        return False


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


async def generate_certificate_internal(
    row_id: int,
    full_name: str,
    email: str,
    score: float,
    background_tasks: BackgroundTasks,
    collaborator_data: dict = None,
    section_results: dict = None
) -> dict:
    """
    Función interna para generar certificado QR.
    Llamada desde submit-exam cuando el colaborador aprueba.

    Args:
        row_id: ID de la fila en Smartsheet
        full_name: Nombre completo del usuario
        email: Email del usuario
        score: Puntuación obtenida
        background_tasks: BackgroundTasks para envío de email
        collaborator_data: Datos adicionales del colaborador para el PDF (opcional)
        section_results: Resultados por sección para el PDF (opcional)

    Returns:
        Dict con success, cert_uuid, error
    """
    logger.info(
        f"generate_certificate_internal - "
        f"row_id={row_id}, email={email}, score={score}"
    )

    try:
        # 1. Generar UUID seguro
        cert_uuid = str(uuid.uuid4())
        logger.info(f"Generated certificate UUID: {cert_uuid}")

        # 2. Calcular fecha de vencimiento
        expiration_date = datetime.utcnow() + timedelta(days=CERTIFICATE_VALIDITY_DAYS)

        # 3. Generar código QR
        qr_image = generate_certificate_qr(cert_uuid, API_BASE_URL)

        # 4. Actualizar Smartsheet con UUID y fecha de vencimiento
        service = OnboardingSmartsheetService()
        try:
            await service.update_certificate_data(
                row_id=row_id,
                cert_uuid=cert_uuid,
                expiration_date=expiration_date
            )
            logger.info(f"Smartsheet actualizado con certificado UUID={cert_uuid}")
        except Exception as e:
            logger.error(f"Error actualizando Smartsheet con certificado: {str(e)}")
            # Continuar de todas formas para enviar el email

        # 5. Enviar email con QR y PDF en background
        background_tasks.add_task(
            send_qr_email,
            email,
            full_name,
            qr_image,
            expiration_date,
            cert_uuid,
            True,  # is_valid (siempre True porque solo se llama cuando aprueba)
            score,
            collaborator_data,
            section_results
        )
        logger.info(f"Email de certificado con PDF programado para {email}")

        return {
            "success": True,
            "cert_uuid": cert_uuid,
            "expiration_date": expiration_date.strftime('%Y-%m-%d'),
            "email_scheduled": True
        }

    except Exception as e:
        logger.error(f"Error en generate_certificate_internal: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


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
        full_name = certificate.get('Nombre Colaborador', 'Usuario')
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
        full_name = certificate.get('Nombre Colaborador', 'Usuario')
        expiration_str = certificate.get('Vencimiento', '')
        url_imagen = certificate.get('url_imagen', None)  # URL de foto de credencial

        # Obtener el campo "Resultado Examen" (Aprobado/Reprobado) - este es el campo que determina si está aprobado
        resultado_examen = certificate.get('Resultado Examen', '')
        resultado_str = str(resultado_examen).strip().lower() if resultado_examen else ''
        is_approved_result = resultado_str == 'aprobado'

        logger.info(f"Certificate {cert_uuid} - Resultado Examen: '{resultado_examen}', is_approved: {is_approved_result}")

        # Score es solo para mostrar, no para validar
        score_value = certificate.get('Score', 0)
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

        # Determinar estado del certificado basado en "Resultado Examen" y fecha de vencimiento
        if is_expired:
            status_str = "expired"
            message = "Tu certificación de Seguridad Industrial ha expirado y NO está autorizado para ingresar a las instalaciones. Por favor contacta a tu supervisor para renovar tu certificación."
        elif not is_approved_result:
            status_str = "not_approved"
            message = "Tu certificación de Seguridad Industrial no pudo ser validada. La información proporcionada o los requisitos del curso no cumplen con los estándares mínimos de seguridad establecidos."
        else:
            status_str = "approved"
            message = "Tu certificación de Seguridad Industrial ha sido validada correctamente. Has cumplido con todos los requisitos del curso y tu información ha sido aprobada conforme a los estándares de seguridad establecidos."

        logger.info(f"Certificate {cert_uuid} info retrieved: status={status_str}, resultado_examen={resultado_examen}, expired={is_expired}")

        return CertificateInfoResponse(
            success=True,
            status=status_str,
            nombre=str(full_name),
            vencimiento=formatted_expiration,
            score=score,
            is_expired=is_expired,
            message=message,
            url_imagen=url_imagen
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


def resend_approved_certificate_email(
    email_to: str,
    full_name: str,
    cert_uuid: str,
    expiration_date_str: str,
    collaborator_data: dict = None,
    section_results: dict = None
) -> bool:
    """
    Reenvía el correo de certificado aprobado cuando el colaborador ya tiene certificación vigente.

    Args:
        email_to: Email del destinatario
        full_name: Nombre completo del usuario
        cert_uuid: UUID del certificado existente
        expiration_date_str: Fecha de vencimiento como string
        collaborator_data: Datos adicionales del colaborador para el PDF (opcional)
        section_results: Resultados por sección para el PDF (opcional)

    Returns:
        True si el email se envió exitosamente
    """
    try:
        # Generar QR para el certificado existente
        qr_image = generate_certificate_qr(cert_uuid, API_BASE_URL)

        # Parsear fecha de vencimiento
        expiration_date = None
        for date_format in ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%m/%d/%y', '%d/%m/%y']:
            try:
                expiration_date = datetime.strptime(str(expiration_date_str), date_format)
                if expiration_date.year < 100:
                    expiration_date = expiration_date.replace(year=expiration_date.year + 2000)
                break
            except ValueError:
                continue

        if not expiration_date:
            expiration_date = datetime.utcnow() + timedelta(days=365)

        # Definir asunto
        subject = f"Recordatorio: Tu Certificación de Seguridad - {full_name}"

        # Contenido HTML del email recordatorio
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
                    max-height: 80px;
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
                .reminder-box {{
                    background-color: #EFF6FF;
                    border-left: 4px solid #3B82F6;
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
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <img src="https://entersys.mx/images/coca-cola-femsa-logo.png" alt="FEMSA" class="logo">
                    <h1>Tu Certificación de Seguridad</h1>
                </div>

                <p>Estimado/a <strong>{full_name}</strong>,</p>

                <div class="reminder-box">
                    <p><strong>Ya cuentas con una certificación de seguridad vigente.</strong></p>
                    <p>Este es un recordatorio de tu certificación activa. Te reenviamos tu código QR de acceso.</p>
                </div>

                <div class="certificate-info">
                    <p><strong>Detalles de tu Certificación:</strong></p>
                    <ul>
                        <li>Estado: <span class="highlight">VIGENTE</span></li>
                        <li>Válido hasta: <span class="highlight">{expiration_date.strftime('%d/%m/%Y')}</span></li>
                    </ul>
                </div>

                <div class="qr-section">
                    <p><strong>Tu código QR de acceso está adjunto a este correo.</strong></p>
                    <p>Preséntalo al personal de seguridad en cada ingreso a las instalaciones.</p>
                </div>

                <p><strong>Importante:</strong></p>
                <ul>
                    <li>No es necesario volver a realizar el examen mientras tu certificación esté vigente.</li>
                    <li>Recibirás un recordatorio antes de que expire tu certificación.</li>
                    <li>Guarda este correo o el código QR para acceder a las instalaciones.</li>
                </ul>

                <div class="footer">
                    <p>Este es un correo automático, por favor no respondas a este mensaje.</p>
                    <p>&copy; {datetime.utcnow().year} FEMSA - Entersys. Todos los derechos reservados.</p>
                </div>
            </div>
        </body>
        </html>
        """

        # Preparar adjuntos
        attachments = []

        # Adjunto QR
        qr_attachment = {
            "filename": f"certificado_qr_{cert_uuid[:8]}.png",
            "content": base64.b64encode(qr_image).decode('utf-8')
        }
        attachments.append(qr_attachment)

        # Generar y adjuntar PDF si se tienen los datos
        if collaborator_data or section_results:
            try:
                from app.utils.pdf_utils import generate_certificate_pdf

                # Preparar datos para el PDF
                pdf_data = collaborator_data.copy() if collaborator_data else {}
                pdf_data.update({
                    "full_name": full_name,
                    "email": email_to,
                    "cert_uuid": cert_uuid,
                    "vencimiento": expiration_date.strftime('%d/%m/%Y'),
                    "fecha_emision": datetime.utcnow().strftime('%d/%m/%Y'),
                    "is_approved": True,
                })

                # Generar PDF
                pdf_bytes = generate_certificate_pdf(
                    collaborator_data=pdf_data,
                    section_results=section_results,
                    qr_image_bytes=qr_image
                )

                pdf_attachment = {
                    "filename": f"certificado_{cert_uuid[:8]}.pdf",
                    "content": base64.b64encode(pdf_bytes).decode('utf-8')
                }
                attachments.append(pdf_attachment)
                logger.info(f"PDF attachment generated for resend to {email_to}")
            except Exception as e:
                logger.warning(f"Could not generate PDF attachment for resend: {e}")

        # Enviar email via SMTP
        result = send_email_via_resend(
            to_emails=[email_to],
            subject=subject,
            html_content=html_content,
            attachments=attachments
        )

        if result:
            logger.info(f"Certificate reminder email sent successfully to {email_to}")
        return result

    except Exception as e:
        logger.error(f"Error sending certificate reminder email to {email_to}: {str(e)}")
        return False


@router.get(
    "/check-exam-status/{rfc}",
    response_model=ExamStatusResponse,
    summary="Verificar estatus del examen por RFC",
    description="""
    Verifica si un colaborador puede realizar el examen de seguridad.

    **Criterios para poder hacer el examen:**
    - Estatus Examen = 1 en la hoja de Registros
    - No estar ya aprobado con certificación vigente
    - Tener menos de 3 intentos

    **Comportamiento especial:**
    - Si ya está APROBADO y vigente: NO puede hacer examen, se reenvía su certificado por correo
    - Si ya está APROBADO pero expiró (pasó 1 año): SI puede hacer examen para renovar

    **Retorna:**
    - can_take_exam: Si puede hacer el examen
    - attempts_used: Intentos utilizados
    - attempts_remaining: Intentos restantes
    - is_approved: Si ya está aprobado
    - is_expired: Si el certificado aprobado ya expiró
    - certificate_resent: Si se reenvió el certificado por correo
    """
)
async def check_exam_status(rfc: str, background_tasks: BackgroundTasks):
    """
    Verifica el estatus del examen para un RFC.
    Si el colaborador ya tiene certificación vigente, reenvía el certificado por correo.
    """
    logger.info(f"GET /onboarding/check-exam-status/{rfc}")

    if not rfc or len(rfc) < 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="RFC inválido. Debe tener al menos 10 caracteres."
        )

    try:
        service = OnboardingSmartsheetService()
        status_info = await service.check_exam_status(rfc)

        certificate_resent = False

        # Construir mensaje descriptivo
        if status_info["is_approved"] and not status_info.get("is_expired", False):
            # Ya está aprobado y vigente - reenviar certificado
            message = "Ya tienes una certificación de seguridad vigente. Te hemos reenviado tu certificado por correo."

            # Reenviar certificado si tiene los datos necesarios
            cert_uuid = status_info.get("cert_uuid")
            email = status_info.get("email")
            full_name = status_info.get("full_name")
            expiration_date = status_info.get("expiration_date")

            if cert_uuid and email and full_name:
                # Reenviar en background para no bloquear la respuesta
                background_tasks.add_task(
                    resend_approved_certificate_email,
                    email,
                    full_name,
                    cert_uuid,
                    expiration_date or ""
                )
                certificate_resent = True
                logger.info(f"Certificate resend scheduled for RFC {rfc} to {email}")
            else:
                logger.warning(f"Cannot resend certificate for RFC {rfc}: missing data (uuid={cert_uuid}, email={email})")
                message = "Ya tienes una certificación de seguridad vigente. No es necesario volver a realizar el examen."

        elif status_info["is_approved"] and status_info.get("is_expired", False):
            # Aprobado pero expiró - puede renovar
            message = "Tu certificación anterior expiró. Puedes realizar el examen nuevamente para renovarla."

        elif not status_info["can_take_exam"]:
            if status_info["attempts_used"] >= MAX_ATTEMPTS:
                message = f"Has agotado tus {MAX_ATTEMPTS} intentos. Contacta al administrador."
            else:
                message = "No tienes autorización para realizar el examen. Verifica tu estatus."
        else:
            remaining = status_info["attempts_remaining"]
            message = f"Puedes realizar el examen. Te quedan {remaining} intento(s)."

        return ExamStatusResponse(
            can_take_exam=status_info["can_take_exam"],
            rfc=rfc.upper(),
            attempts_used=status_info["attempts_used"],
            attempts_remaining=status_info["attempts_remaining"],
            is_approved=status_info["is_approved"],
            is_expired=status_info.get("is_expired", False),
            last_attempt_date=status_info["last_attempt_date"],
            expiration_date=status_info.get("expiration_date"),
            message=message,
            section_results=status_info["section_results"],
            certificate_resent=certificate_resent
        )

    except OnboardingSmartsheetServiceError as e:
        logger.error(f"Smartsheet error checking exam status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al verificar estatus: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error checking exam status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor"
        )


def calculate_section_results(answers: list) -> tuple:
    """
    Calcula los resultados por sección del examen.

    Args:
        answers: Lista de 30 respuestas con question_id y is_correct

    Returns:
        Tuple de (section_results: list[SectionResult], section_scores: dict, is_approved: bool)
    """
    section_results = []
    section_scores = {}
    all_sections_approved = True

    for section_num, section_info in EXAM_SECTIONS.items():
        section_name = section_info["name"]
        question_range = section_info["questions"]

        # Contar respuestas correctas en esta sección
        correct_in_section = 0
        for answer in answers:
            if answer.question_id in question_range and answer.is_correct:
                correct_in_section += 1

        # Calcular score de la sección (10 preguntas cada una)
        section_score = (correct_in_section / 10) * 100
        section_approved = section_score >= MINIMUM_SECTION_SCORE

        if not section_approved:
            all_sections_approved = False

        section_results.append(SectionResult(
            section_name=section_name,
            section_number=section_num,
            correct_count=correct_in_section,
            total_questions=10,
            score=section_score,
            approved=section_approved
        ))

        # Guardar score para Smartsheet
        section_scores[f"Seccion{section_num}"] = section_score

    return section_results, section_scores, all_sections_approved


@router.post(
    "/submit-exam",
    response_model=ExamSubmitResponse,
    summary="Enviar examen de seguridad (3 secciones)",
    description="""
    Endpoint para enviar el examen de certificación de seguridad.

    **Estructura del examen (30 preguntas, 3 secciones):**
    - Sección 1 (Seguridad): Preguntas 1-10
    - Sección 2 (Inocuidad): Preguntas 11-20
    - Sección 3 (Ambiental): Preguntas 21-30

    **Criterios de aprobación:**
    - Cada sección debe tener mínimo 80% (8/10 correctas)
    - Si falla cualquier sección = Reprobado
    - Máximo 3 intentos por RFC

    **Flujo:**
    1. Verifica que el RFC puede hacer el examen (Estatus Examen = 1)
    2. Calcula score por sección
    3. Guarda resultados en hoja de Registros
    4. Guarda respuestas (Correcto/Incorrecto) en hoja de Respuestas (Bitácora)
    5. Si es el 3er intento fallido, envía alerta y bloquea
    """
)
async def submit_exam(request: ExamSubmitRequest, background_tasks: BackgroundTasks):
    """
    Endpoint para enviar el examen de seguridad con 3 secciones.
    """
    logger.info(
        f"POST /onboarding/submit-exam - "
        f"email={request.email}, nombre={request.nombre_completo}, rfc={request.rfc_colaborador}"
    )

    try:
        service = OnboardingSmartsheetService()

        # 1. Verificar estatus del examen antes de procesar
        status_info = await service.check_exam_status(request.rfc_colaborador)

        if not status_info["can_take_exam"]:
            # Construir mensaje de error apropiado
            if status_info["is_approved"]:
                msg = "Ya aprobaste el examen. No necesitas volver a realizarlo."
            elif status_info["attempts_used"] >= MAX_ATTEMPTS:
                msg = f"Has agotado tus {MAX_ATTEMPTS} intentos. Contacta al administrador."
            else:
                msg = "No tienes autorización para realizar el examen (Estatus Examen != 1)."

            return ExamSubmitResponse(
                success=False,
                approved=False,
                sections=[],
                overall_score=0,
                message=msg,
                attempts_used=status_info["attempts_used"],
                attempts_remaining=status_info["attempts_remaining"],
                can_retry=False
            )

        # 2. Calcular resultados por sección
        section_results, section_scores, is_approved = calculate_section_results(request.answers)

        # Calcular score promedio general
        overall_score = sum(s.score for s in section_results) / 3

        logger.info(
            f"RFC {request.rfc_colaborador}: "
            f"Seccion1={section_scores['Seccion1']}%, "
            f"Seccion2={section_scores['Seccion2']}%, "
            f"Seccion3={section_scores['Seccion3']}%, "
            f"Aprobado={is_approved}"
        )

        # 3. Preparar datos de respuestas para bitácora
        answers_results = [
            {"question_id": a.question_id, "is_correct": a.is_correct}
            for a in request.answers
        ]

        # 4. Guardar resultados en Smartsheet
        # Preparar datos del colaborador para guardar en Smartsheet
        colaborador_data = {
            "nombre_completo": request.nombre_completo,
            "rfc_empresa": request.rfc_empresa,
            "nss": request.nss,
            "tipo_servicio": request.tipo_servicio,
            "proveedor": request.proveedor,
            "email": request.email,
            "url_imagen": request.url_imagen  # URL de la foto de credencial
        }

        save_result = await service.save_exam_results(
            rfc=request.rfc_colaborador,
            section_scores=section_scores,
            is_approved=is_approved,
            answers_results=answers_results,
            existing_row_id=status_info.get("row_id"),
            current_attempts=status_info["attempts_used"],
            colaborador_data=colaborador_data
        )

        new_attempts = save_result["new_attempts"]
        attempts_remaining = max(0, MAX_ATTEMPTS - new_attempts)
        can_retry = not is_approved and attempts_remaining > 0

        # 5. Si APROBÓ: Llamar a la lógica de /generate para crear certificado
        cert_uuid = None
        if is_approved:
            row_id = save_result.get("registros_row_id")

            if row_id:
                logger.info(f"Examen APROBADO para RFC {request.rfc_colaborador} - Generando certificado...")

                # Llamar a la lógica de generación de certificado
                # Preparar section_results como dict para el PDF
                section_results_for_pdf = {
                    "Seguridad": section_scores.get("Seccion1", 0),
                    "Inocuidad": section_scores.get("Seccion2", 0),
                    "Ambiental": section_scores.get("Seccion3", 0),
                }
                try:
                    generate_result = await generate_certificate_internal(
                        row_id=row_id,
                        full_name=request.nombre_completo,
                        email=request.email,
                        score=overall_score,
                        background_tasks=background_tasks,
                        collaborator_data=colaborador_data,
                        section_results=section_results_for_pdf
                    )

                    if generate_result.get("success"):
                        cert_uuid = generate_result.get("cert_uuid")
                        logger.info(f"Certificado generado exitosamente: UUID={cert_uuid}")
                    else:
                        logger.error(f"Error generando certificado: {generate_result.get('error')}")

                except Exception as e:
                    logger.error(f"Error llamando a generate_certificate_internal: {str(e)}")
            else:
                logger.error(f"No se pudo obtener row_id para generar certificado")

        # 6. Verificar si es el tercer intento fallido
        if not is_approved and new_attempts >= MAX_ATTEMPTS:
            logger.warning(
                f"⚠️ TERCER INTENTO FALLIDO detectado para RFC {request.rfc_colaborador}"
            )

            # Preparar datos para alerta
            colaborador_data = {
                "nombre_completo": request.nombre_completo,
                "rfc_colaborador": request.rfc_colaborador,
                "email": request.email,
                "proveedor": request.proveedor,
                "tipo_servicio": request.tipo_servicio or "",
                "rfc_empresa": request.rfc_empresa or "",
                "nss": request.nss or "",
                "section_scores": section_scores,
                "section_results": [s.model_dump() for s in section_results],  # Para mostrar en email
                "overall_score": overall_score
            }

            attempts_info = {
                "total": new_attempts,
                "fallidos": new_attempts,  # Todos fueron fallidos si llegamos al 3er intento
                "registros": []
            }

            # Enviar alerta en background
            background_tasks.add_task(
                send_third_attempt_alert_email,
                colaborador_data,
                attempts_info
            )
            logger.info(f"Alerta de tercer intento programada para RFC {request.rfc_colaborador}")

        # 7. Construir mensaje de respuesta
        if is_approved:
            message = "¡Felicidades! Has aprobado el examen. Recibirás tu certificación por correo."
        else:
            # Identificar secciones reprobadas
            failed_sections = [s.section_name for s in section_results if not s.approved]
            if can_retry:
                message = f"No aprobaste. Sección(es) reprobada(s): {', '.join(failed_sections)}. Te quedan {attempts_remaining} intento(s)."
            else:
                message = f"No aprobaste y has agotado tus {MAX_ATTEMPTS} intentos. Contacta al administrador."

        return ExamSubmitResponse(
            success=True,
            approved=is_approved,
            sections=section_results,
            overall_score=round(overall_score, 2),
            message=message,
            attempts_used=new_attempts,
            attempts_remaining=attempts_remaining,
            can_retry=can_retry
        )

    except OnboardingSmartsheetServiceError as e:
        logger.error(f"Smartsheet error in submit-exam: {str(e)}")
        return ExamSubmitResponse(
            success=False,
            approved=False,
            sections=[],
            overall_score=0,
            message=f"Error al guardar en el sistema: {str(e)}",
            attempts_used=0,
            attempts_remaining=0,
            can_retry=False
        )
    except Exception as e:
        logger.error(f"Unexpected error in submit-exam: {str(e)}")
        return ExamSubmitResponse(
            success=False,
            approved=False,
            sections=[],
            overall_score=0,
            message=f"Error interno: {str(e)}",
            attempts_used=0,
            attempts_remaining=0,
            can_retry=False
        )


@router.post(
    "/upload-photo",
    summary="Subir foto de credencial a GCS",
    description="Sube una foto de credencial a Google Cloud Storage y retorna la URL pública"
)
async def upload_photo(
    file: UploadFile = File(...),
    rfc: str = Form(...)
):
    """
    Sube una foto de credencial a Google Cloud Storage.

    - **file**: Imagen JPG/PNG (máx 5MB)
    - **rfc**: RFC del colaborador (usado para nombrar el archivo)

    Retorna la URL pública de la imagen.
    """
    logger.info(f"POST /onboarding/upload-photo - Subiendo foto para RFC: {rfc}")

    # Validar tipo de archivo
    allowed_types = ['image/jpeg', 'image/png', 'image/jpg']
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tipo de archivo no permitido. Solo se aceptan JPG y PNG."
        )

    # Validar tamaño (5MB máximo)
    contents = await file.read()
    if len(contents) > 5 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo excede el tamaño máximo de 5MB."
        )

    try:
        # Generar nombre único para el archivo
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        extension = file.filename.split('.')[-1] if '.' in file.filename else 'jpg'
        filename = f"credentials/{rfc.upper()}_{timestamp}.{extension}"

        # Inicializar cliente de GCS
        storage_client = storage.Client(project=settings.GCS_PROJECT_ID)
        bucket = storage_client.bucket(settings.GCS_BUCKET_NAME)
        blob = bucket.blob(filename)

        # Subir archivo
        blob.upload_from_string(
            contents,
            content_type=file.content_type
        )

        # El bucket ya tiene acceso público configurado via IAM (uniform bucket-level access)
        # No necesitamos blob.make_public() - construimos la URL directamente
        public_url = f"https://storage.googleapis.com/{settings.GCS_BUCKET_NAME}/{filename}"

        logger.info(f"Foto subida exitosamente: {public_url}")

        return {
            "success": True,
            "url": public_url,
            "filename": filename
        }

    except Exception as e:
        logger.error(f"Error subiendo foto a GCS: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al subir la foto: {str(e)}"
        )


@router.get(
    "/registros",
    summary="Listar todos los registros de la hoja de Smartsheet",
    description="Obtiene todos los registros de la hoja de Registros_OnBoarding"
)
async def list_all_registros():
    """
    Lista todos los registros de la hoja de Smartsheet.
    """
    logger.info("GET /onboarding/registros - Listando todos los registros")

    try:
        service = OnboardingSmartsheetService()
        registros = await service.get_all_registros()

        return {
            "success": True,
            "total": len(registros),
            "registros": registros
        }

    except OnboardingSmartsheetServiceError as e:
        logger.error(f"Smartsheet error listing registros: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al consultar Smartsheet: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error listing registros: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor"
        )


def mask_email(email: str) -> str:
    """Censura un email para mostrar solo los primeros 3 caracteres y el dominio."""
    if not email or '@' not in email:
        return "***"
    local, domain = email.split('@', 1)
    if len(local) <= 3:
        masked = local[0] + '***'
    else:
        masked = local[:3] + '***'
    return f"{masked}@{domain}"


@router.post(
    "/resend-certificate",
    response_model=ResendCertificateResponse,
    summary="Reenviar certificado por RFC y NSS (soporte)",
    description="""
    Endpoint para que soporte reenvíe el certificado a un colaborador.

    **Flujo:**
    1. Recibe RFC + NSS
    2. Busca al colaborador en Smartsheet por RFC
    3. Valida que el NSS coincida (doble verificación de identidad)
    4. Lee el email actual de Smartsheet (el corregido por soporte)
    5. Si resultado = Aprobado → reenvía email con QR
    6. Si resultado = Reprobado → reenvía email de reprobado
    7. Retorna confirmación con email censurado
    """
)
async def resend_certificate(request: ResendCertificateRequest):
    """
    Reenvía el certificado de un colaborador buscando por RFC y validando NSS.
    """
    logger.info(f"POST /onboarding/resend-certificate - RFC={request.rfc}")

    try:
        service = OnboardingSmartsheetService()

        # Buscar colaborador por RFC y validar NSS
        collaborator = await service.get_collaborator_by_rfc_and_nss(request.rfc, request.nss)

        if not collaborator:
            return ResendCertificateResponse(
                success=False,
                message="No se encontró un colaborador con ese RFC y NSS. Verifica los datos."
            )

        email = collaborator.get("email")
        full_name = collaborator.get("full_name", "Colaborador")
        cert_uuid = collaborator.get("cert_uuid")
        vencimiento = collaborator.get("vencimiento", "")
        resultado = str(collaborator.get("resultado", "")).strip()
        is_approved = collaborator.get("is_approved", False)

        if not email:
            return ResendCertificateResponse(
                success=False,
                message="El colaborador no tiene un correo electrónico registrado."
            )

        email_masked = mask_email(email)

        if is_approved and cert_uuid:
            # Reenviar certificado aprobado con QR
            sent = resend_approved_certificate_email(
                email_to=email,
                full_name=full_name,
                cert_uuid=cert_uuid,
                expiration_date_str=str(vencimiento) if vencimiento else ""
            )

            if sent:
                return ResendCertificateResponse(
                    success=True,
                    message=f"Certificado aprobado reenviado exitosamente a {email_masked}",
                    email_masked=email_masked,
                    resultado="Aprobado"
                )
            else:
                return ResendCertificateResponse(
                    success=False,
                    message="Error al enviar el correo. Intenta de nuevo."
                )

        else:
            # Reenviar email de reprobado
            # Generar QR de referencia
            qr_image = generate_certificate_qr(cert_uuid or str(uuid.uuid4()), API_BASE_URL)

            # Calcular score promedio de secciones
            s1 = float(str(collaborator.get("seccion1", 0) or 0).replace('%', '').strip() or 0)
            s2 = float(str(collaborator.get("seccion2", 0) or 0).replace('%', '').strip() or 0)
            s3 = float(str(collaborator.get("seccion3", 0) or 0).replace('%', '').strip() or 0)
            overall_score = (s1 + s2 + s3) / 3 if (s1 or s2 or s3) else 0

            # Parsear fecha de vencimiento
            exp_date = datetime.utcnow() + timedelta(days=365)
            if vencimiento:
                for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y']:
                    try:
                        exp_date = datetime.strptime(str(vencimiento), fmt)
                        break
                    except ValueError:
                        continue

            sent = send_qr_email(
                email_to=email,
                full_name=full_name,
                qr_image=qr_image,
                expiration_date=exp_date,
                cert_uuid=cert_uuid or "N/A",
                is_valid=False,
                score=overall_score
            )

            if sent:
                return ResendCertificateResponse(
                    success=True,
                    message=f"Resultado de examen reenviado exitosamente a {email_masked}",
                    email_masked=email_masked,
                    resultado="Reprobado"
                )
            else:
                return ResendCertificateResponse(
                    success=False,
                    message="Error al enviar el correo. Intenta de nuevo."
                )

    except OnboardingSmartsheetServiceError as e:
        logger.error(f"Smartsheet error in resend-certificate: {str(e)}")
        return ResendCertificateResponse(
            success=False,
            message=f"Error al consultar el sistema: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error in resend-certificate: {str(e)}")
        return ResendCertificateResponse(
            success=False,
            message="Error interno del servidor"
        )


@router.get(
    "/download-certificate/{rfc}",
    summary="Descargar certificado PDF por RFC",
    description="""
    Genera y descarga un certificado PDF para un colaborador aprobado.

    **Flujo:**
    1. Obtiene datos del colaborador por RFC
    2. Obtiene scores por sección
    3. Genera QR del certificado
    4. Genera PDF con datos, resultados y QR
    5. Retorna como descarga directa
    """
)
async def download_certificate_pdf(rfc: str):
    """
    Genera y descarga un certificado PDF para un RFC.
    """
    logger.info(f"GET /onboarding/download-certificate/{rfc}")

    if not rfc or len(rfc) < 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="RFC inválido"
        )

    try:
        from app.utils.pdf_utils import generate_certificate_pdf

        service = OnboardingSmartsheetService()

        # Obtener datos del colaborador
        credential_data = await service.get_credential_data_by_rfc(rfc)
        if not credential_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No se encontró registro para este RFC"
            )

        # Obtener scores por sección
        status_info = await service.check_exam_status(rfc)
        section_results = status_info.get("section_results") if status_info else None

        # Generar QR si tiene cert_uuid
        qr_bytes = None
        cert_uuid = credential_data.get("cert_uuid")
        if cert_uuid:
            try:
                qr_bytes = generate_certificate_qr(cert_uuid, API_BASE_URL)
            except Exception as e:
                logger.warning(f"Could not generate QR for PDF: {e}")

        # Preparar datos del colaborador para el PDF
        pdf_data = {
            "full_name": credential_data.get("full_name", ""),
            "rfc": rfc.upper(),
            "proveedor": credential_data.get("proveedor"),
            "tipo_servicio": credential_data.get("tipo_servicio"),
            "nss": credential_data.get("nss"),
            "rfc_empresa": credential_data.get("rfc_empresa"),
            "email": credential_data.get("email"),
            "cert_uuid": cert_uuid,
            "vencimiento": credential_data.get("vencimiento"),
            "fecha_emision": credential_data.get("fecha_emision"),
            "is_approved": credential_data.get("is_approved", False),
        }

        # Generar PDF
        pdf_bytes = generate_certificate_pdf(
            collaborator_data=pdf_data,
            section_results=section_results,
            qr_image_bytes=qr_bytes
        )

        # Retornar como descarga directa
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="certificado_{rfc.upper()}.pdf"'
            }
        )

    except HTTPException:
        raise
    except OnboardingSmartsheetServiceError as e:
        logger.error(f"Smartsheet error downloading certificate: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al consultar Smartsheet: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error downloading certificate: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor"
        )


@router.get(
    "/credential/{rfc}",
    response_model=CredentialResponse,
    summary="Obtener datos de credencial virtual por RFC",
    description="""
    Obtiene los datos necesarios para generar una credencial virtual.

    **Usado por la página de credencial virtual**

    Retorna:
    - Nombre del colaborador
    - RFC
    - Proveedor/Empresa
    - Tipo de servicio
    - UUID del certificado (para generar QR)
    - Fecha de vencimiento
    - Estado de la certificación
    """
)
async def get_credential_by_rfc(rfc: str):
    """
    Obtiene los datos de credencial virtual para un RFC.
    """
    logger.info(f"GET /onboarding/credential/{rfc}")

    if not rfc or len(rfc) < 10:
        return CredentialResponse(
            success=False,
            status="not_found",
            nombre="",
            rfc=rfc,
            is_expired=False,
            message="RFC inválido"
        )

    try:
        service = OnboardingSmartsheetService()

        # Obtener datos del colaborador por RFC
        credential_data = await service.get_credential_data_by_rfc(rfc)

        if not credential_data:
            return CredentialResponse(
                success=False,
                status="not_found",
                nombre="",
                rfc=rfc.upper(),
                is_expired=False,
                message="No se encontró registro para este RFC"
            )

        # Determinar estado
        is_approved = credential_data.get("is_approved", False)
        is_expired = credential_data.get("is_expired", False)

        if is_approved and not is_expired:
            status = "approved"
            message = "Certificación vigente"
        elif is_approved and is_expired:
            status = "expired"
            message = "Certificación expirada"
        else:
            status = "not_approved"
            message = "Sin certificación aprobada"

        return CredentialResponse(
            success=True,
            status=status,
            nombre=credential_data.get("full_name", ""),
            rfc=rfc.upper(),
            proveedor=credential_data.get("proveedor"),
            tipo_servicio=credential_data.get("tipo_servicio"),
            nss=credential_data.get("nss"),
            rfc_empresa=credential_data.get("rfc_empresa"),
            email=credential_data.get("email"),
            cert_uuid=credential_data.get("cert_uuid"),
            vencimiento=credential_data.get("vencimiento"),
            fecha_emision=credential_data.get("fecha_emision"),
            url_imagen=credential_data.get("url_imagen"),
            is_expired=is_expired,
            message=message
        )

    except OnboardingSmartsheetServiceError as e:
        logger.error(f"Smartsheet error getting credential: {str(e)}")
        return CredentialResponse(
            success=False,
            status="not_found",
            nombre="",
            rfc=rfc.upper(),
            is_expired=False,
            message=f"Error al consultar: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error getting credential: {str(e)}")
        return CredentialResponse(
            success=False,
            status="not_found",
            nombre="",
            rfc=rfc.upper(),
            is_expired=False,
            message="Error interno del servidor"
        )

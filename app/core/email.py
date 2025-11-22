# app/core/email.py
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


def send_email(
    email_to: str,
    subject: str,
    html_content: str,
) -> bool:
    """
    Envía un email usando SMTP de Google Workspace.
    
    Args:
        email_to: Email del destinatario
        subject: Asunto del email
        html_content: Contenido HTML del email
        
    Returns:
        True si el email se envió exitosamente, False en caso contrario
    """
    try:
        # Crear mensaje
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
        msg['To'] = email_to

        # Adjuntar contenido HTML
        html_part = MIMEText(html_content, 'html')
        msg.attach(html_part)

        # Conectar al servidor SMTP
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()  # Habilitar TLS
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
        
        logger.info(f"Email enviado exitosamente a {email_to}")
        return True
        
    except Exception as e:
        logger.error(f"Error al enviar email a {email_to}: {str(e)}")
        return False


def send_password_reset_email(email_to: str, token: str) -> bool:
    """
    Envía un email de recuperación de contraseña.
    
    Args:
        email_to: Email del usuario
        token: Token de recuperación
        
    Returns:
        True si el email se envió exitosamente, False en caso contrario
    """
    reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"
    
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
            .logo {{
                max-width: 150px;
                height: auto;
            }}
            h1 {{
                color: #093D53;
                font-size: 24px;
                margin-bottom: 20px;
            }}
            .button {{
                display: inline-block;
                padding: 12px 30px;
                background-color: #009CA6;
                color: white !important;
                text-decoration: none;
                border-radius: 6px;
                font-weight: 500;
                margin: 20px 0;
            }}
            .button:hover {{
                background-color: #093D53;
            }}
            .footer {{
                text-align: center;
                margin-top: 30px;
                padding-top: 20px;
                border-top: 1px solid #e5e7eb;
                font-size: 12px;
                color: #6b7280;
            }}
            .warning {{
                background-color: #fef3c7;
                border-left: 4px solid #f59e0b;
                padding: 15px;
                margin: 20px 0;
                border-radius: 4px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Recuperación de Contraseña</h1>
            </div>
            
            <p>Hola,</p>
            
            <p>Hemos recibido una solicitud para restablecer la contraseña de tu cuenta en el Panel de Administración de Entersys.</p>
            
            <p>Para restablecer tu contraseña, haz clic en el siguiente botón:</p>
            
            <div style="text-align: center;">
                <a href="{reset_url}" class="button">Restablecer Contraseña</a>
            </div>
            
            <div class="warning">
                <strong>⚠️ Importante:</strong> Este enlace es válido por 24 horas. Si no solicitaste este cambio, puedes ignorar este correo de forma segura.
            </div>
            
            <p>Si el botón no funciona, copia y pega el siguiente enlace en tu navegador:</p>
            <p style="word-break: break-all; color: #009CA6;">{reset_url}</p>
            
            <div class="footer">
                <p>Este es un correo automático, por favor no respondas a este mensaje.</p>
                <p>&copy; 2025 Entersys. Todos los derechos reservados.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return send_email(
        email_to=email_to,
        subject="Recuperación de Contraseña - Entersys Admin",
        html_content=html_content
    )

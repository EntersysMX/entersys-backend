# app/utils/pdf_utils.py
"""
Generación de PDF de credencial estilo tarjeta/gafete corporativo.
Diseño tipo ID card profesional.
"""
import io
import logging
import os
import requests
from datetime import datetime
from typing import Dict, Any, Optional

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor, white, black
from reportlab.lib.utils import ImageReader

logger = logging.getLogger(__name__)

# Colores corporativos
COLOR_RED = HexColor("#D91E18")
COLOR_YELLOW = HexColor("#FFC600")
COLOR_DARK = HexColor("#1a1a1a")
COLOR_GREEN = HexColor("#16a34a")
COLOR_RED_STATUS = HexColor("#dc2626")
COLOR_GRAY = HexColor("#6b7280")
COLOR_GRAY_LIGHT = HexColor("#f5f5f5")
COLOR_GRAY_BORDER = HexColor("#e0e0e0")

# Path al logo
LOGO_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "coca-cola-femsa-logo.png")


def fetch_photo_from_url(url: str) -> Optional[bytes]:
    """Descarga una imagen desde una URL."""
    if not url or not url.startswith(("http://", "https://")):
        return None
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.content
    except Exception as e:
        logger.warning(f"Error fetching photo from {url}: {e}")
    return None


def draw_rounded_rect(c, x, y, width, height, radius, fill_color=None, stroke_color=None, stroke_width=1):
    """Dibuja un rectángulo con esquinas redondeadas."""
    c.saveState()

    path = c.beginPath()
    path.moveTo(x + radius, y)
    path.lineTo(x + width - radius, y)
    path.arcTo(x + width - radius, y, x + width, y + radius, 90)
    path.lineTo(x + width, y + height - radius)
    path.arcTo(x + width - radius, y + height - radius, x + width, y + height, 0)
    path.lineTo(x + radius, y + height)
    path.arcTo(x, y + height - radius, x + radius, y + height, -90)
    path.lineTo(x, y + radius)
    path.arcTo(x, y, x + radius, y + radius, 180)
    path.close()

    if fill_color:
        c.setFillColor(fill_color)
        c.drawPath(path, fill=1, stroke=0)

    if stroke_color:
        c.setStrokeColor(stroke_color)
        c.setLineWidth(stroke_width)
        c.drawPath(path, fill=0, stroke=1)

    c.restoreState()


def generate_certificate_pdf(
    collaborator_data: Dict[str, Any],
    section_results: Optional[Dict[str, Any]] = None,
    qr_image_bytes: Optional[bytes] = None
) -> bytes:
    """
    Genera un PDF de credencial estilo tarjeta ID profesional.
    """
    buffer = io.BytesIO()

    # Crear canvas
    c = canvas.Canvas(buffer, pagesize=letter)
    page_width, page_height = letter

    # Dimensiones de la tarjeta (tamaño credencial grande)
    card_width = 400
    card_height = 550
    card_x = (page_width - card_width) / 2
    card_y = (page_height - card_height) / 2

    is_approved = collaborator_data.get("is_approved", False)
    status_color = COLOR_GREEN if is_approved else COLOR_RED_STATUS
    resultado_text = "APROBADO" if is_approved else "NO APROBADO"

    # Extraer datos
    full_name = collaborator_data.get("full_name", collaborator_data.get("nombre_completo", "N/A"))
    rfc = collaborator_data.get("rfc", collaborator_data.get("rfc_colaborador", "N/A"))
    proveedor = collaborator_data.get("proveedor", "") or "N/A"
    tipo_servicio = collaborator_data.get("tipo_servicio", "") or "N/A"
    nss = collaborator_data.get("nss", "") or "N/A"
    rfc_empresa = collaborator_data.get("rfc_empresa", "") or "N/A"
    email = collaborator_data.get("email", "") or "N/A"
    vencimiento = collaborator_data.get("vencimiento", "N/A")
    fecha_emision = collaborator_data.get("fecha_emision", collaborator_data.get("fecha_examen", "N/A"))
    foto_url = collaborator_data.get("foto_url", "")

    # ══════════════════════════════════════════════════════════════════
    # FONDO DE LA TARJETA
    # ══════════════════════════════════════════════════════════════════

    # Sombra
    c.setFillColor(HexColor("#00000015"))
    draw_rounded_rect(c, card_x + 4, card_y - 4, card_width, card_height, 15, fill_color=HexColor("#cccccc"))

    # Tarjeta principal blanca
    draw_rounded_rect(c, card_x, card_y, card_width, card_height, 15, fill_color=white, stroke_color=COLOR_GRAY_BORDER, stroke_width=2)

    # ══════════════════════════════════════════════════════════════════
    # HEADER ROJO
    # ══════════════════════════════════════════════════════════════════
    header_height = 85
    header_y = card_y + card_height - header_height

    # Fondo rojo del header (con esquinas superiores redondeadas)
    c.saveState()
    path = c.beginPath()
    path.moveTo(card_x, header_y)
    path.lineTo(card_x + card_width, header_y)
    path.lineTo(card_x + card_width, card_y + card_height - 15)
    path.arcTo(card_x + card_width - 15, card_y + card_height - 15, card_x + card_width, card_y + card_height, 0)
    path.lineTo(card_x + 15, card_y + card_height)
    path.arcTo(card_x, card_y + card_height - 15, card_x + 15, card_y + card_height, -90)
    path.lineTo(card_x, header_y)
    path.close()
    c.setFillColor(COLOR_RED)
    c.drawPath(path, fill=1, stroke=0)
    c.restoreState()

    # Logo en el header
    if os.path.exists(LOGO_PATH):
        try:
            logo = ImageReader(LOGO_PATH)
            logo_w, logo_h = 120, 50
            logo_x = card_x + (card_width - logo_w) / 2
            logo_y = header_y + (header_height - logo_h) / 2 + 5
            c.drawImage(logo, logo_x, logo_y, width=logo_w, height=logo_h, preserveAspectRatio=True, mask='auto')
        except Exception as e:
            logger.warning(f"Could not load logo: {e}")
            # Texto alternativo
            c.setFillColor(white)
            c.setFont("Helvetica-Bold", 18)
            c.drawCentredString(card_x + card_width/2, header_y + 40, "COCA-COLA FEMSA")

    # ══════════════════════════════════════════════════════════════════
    # TÍTULO
    # ══════════════════════════════════════════════════════════════════
    title_y = header_y - 35
    c.setFillColor(COLOR_DARK)
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(card_x + card_width/2, title_y, "CREDENCIAL DE SEGURIDAD")

    c.setFillColor(COLOR_GRAY)
    c.setFont("Helvetica", 10)
    c.drawCentredString(card_x + card_width/2, title_y - 15, "Capacitación Onboarding KOF")

    # ══════════════════════════════════════════════════════════════════
    # FOTO DEL COLABORADOR
    # ══════════════════════════════════════════════════════════════════
    photo_size = 110
    photo_x = card_x + (card_width - photo_size) / 2
    photo_y = title_y - photo_size - 30

    # Marco de la foto
    draw_rounded_rect(c, photo_x - 3, photo_y - 3, photo_size + 6, photo_size + 6, 8,
                     fill_color=COLOR_GRAY_LIGHT, stroke_color=COLOR_GRAY_BORDER, stroke_width=2)

    # Foto o placeholder
    photo_drawn = False
    if foto_url:
        photo_bytes = fetch_photo_from_url(foto_url)
        if photo_bytes:
            try:
                photo_buffer = io.BytesIO(photo_bytes)
                photo_img = ImageReader(photo_buffer)
                c.drawImage(photo_img, photo_x, photo_y, width=photo_size, height=photo_size,
                           preserveAspectRatio=True, mask='auto')
                photo_drawn = True
            except Exception as e:
                logger.warning(f"Could not draw photo: {e}")

    if not photo_drawn:
        # Placeholder
        c.setFillColor(COLOR_GRAY)
        c.setFont("Helvetica", 12)
        c.drawCentredString(photo_x + photo_size/2, photo_y + photo_size/2, "SIN FOTO")

    # ══════════════════════════════════════════════════════════════════
    # NOMBRE Y DATOS PRINCIPALES
    # ══════════════════════════════════════════════════════════════════
    info_y = photo_y - 30

    # Nombre
    c.setFillColor(COLOR_DARK)
    c.setFont("Helvetica-Bold", 14)
    name_display = str(full_name).upper()
    if len(name_display) > 35:
        name_display = name_display[:35] + "..."
    c.drawCentredString(card_x + card_width/2, info_y, name_display)

    # RFC
    c.setFillColor(COLOR_GRAY)
    c.setFont("Helvetica", 10)
    c.drawCentredString(card_x + card_width/2, info_y - 18, f"RFC: {rfc}")

    # ══════════════════════════════════════════════════════════════════
    # BADGE DE ESTADO
    # ══════════════════════════════════════════════════════════════════
    badge_y = info_y - 50
    badge_width = 140
    badge_height = 28
    badge_x = card_x + (card_width - badge_width) / 2

    draw_rounded_rect(c, badge_x, badge_y, badge_width, badge_height, 14, fill_color=status_color)

    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(card_x + card_width/2, badge_y + 8, resultado_text)

    # ══════════════════════════════════════════════════════════════════
    # LÍNEA AMARILLA SEPARADORA
    # ══════════════════════════════════════════════════════════════════
    line_y = badge_y - 15
    c.setStrokeColor(COLOR_YELLOW)
    c.setLineWidth(3)
    c.line(card_x + 30, line_y, card_x + card_width - 30, line_y)

    # ══════════════════════════════════════════════════════════════════
    # INFORMACIÓN ADICIONAL EN DOS COLUMNAS
    # ══════════════════════════════════════════════════════════════════
    details_y = line_y - 25
    col1_x = card_x + 35
    col2_x = card_x + card_width/2 + 15

    def draw_field(x, y, label, value, max_chars=22):
        c.setFillColor(COLOR_GRAY)
        c.setFont("Helvetica-Bold", 8)
        c.drawString(x, y, label)
        c.setFillColor(COLOR_DARK)
        c.setFont("Helvetica", 10)
        display_value = str(value)[:max_chars]
        c.drawString(x, y - 12, display_value)

    # Columna izquierda
    draw_field(col1_x, details_y, "EMPRESA", proveedor, 20)
    draw_field(col1_x, details_y - 35, "TIPO DE SERVICIO", tipo_servicio, 20)
    draw_field(col1_x, details_y - 70, "NSS", nss)

    # Columna derecha
    draw_field(col2_x, details_y, "RFC EMPRESA", rfc_empresa)
    draw_field(col2_x, details_y - 35, "CORREO", email, 22)

    # ══════════════════════════════════════════════════════════════════
    # FECHAS Y QR
    # ══════════════════════════════════════════════════════════════════
    bottom_section_y = details_y - 115

    # Fechas a la izquierda
    c.setFillColor(COLOR_GRAY)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(col1_x, bottom_section_y, "FECHA DE EMISIÓN")
    c.setFillColor(COLOR_DARK)
    c.setFont("Helvetica", 10)
    c.drawString(col1_x, bottom_section_y - 12, str(fecha_emision))

    c.setFillColor(COLOR_GRAY)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(col1_x, bottom_section_y - 32, "VIGENTE HASTA")
    c.setFillColor(status_color)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(col1_x, bottom_section_y - 46, str(vencimiento))

    # QR a la derecha
    qr_size = 70
    qr_x = card_x + card_width - qr_size - 40
    qr_y = bottom_section_y - 50

    if qr_image_bytes:
        try:
            qr_buffer = io.BytesIO(qr_image_bytes)
            qr_img = ImageReader(qr_buffer)
            c.drawImage(qr_img, qr_x, qr_y, width=qr_size, height=qr_size)

            c.setFillColor(COLOR_GRAY)
            c.setFont("Helvetica", 7)
            c.drawCentredString(qr_x + qr_size/2, qr_y - 10, "Escanea para verificar")
        except Exception as e:
            logger.warning(f"Could not draw QR: {e}")

    # ══════════════════════════════════════════════════════════════════
    # FOOTER
    # ══════════════════════════════════════════════════════════════════
    footer_y = card_y + 20
    c.setFillColor(COLOR_GRAY)
    c.setFont("Helvetica", 7)
    footer_text = f"Documento generado el {datetime.utcnow().strftime('%d/%m/%Y %H:%M')} UTC · © {datetime.utcnow().year} FEMSA - Entersys"
    c.drawCentredString(card_x + card_width/2, footer_y, footer_text)

    # Guardar página
    c.save()

    pdf_bytes = buffer.getvalue()
    buffer.close()

    logger.info(f"PDF generated successfully, size: {len(pdf_bytes)} bytes")
    return pdf_bytes

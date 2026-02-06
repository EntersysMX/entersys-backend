# app/utils/pdf_utils.py
"""
Generación de PDF de certificado/credencial de seguridad con ReportLab.
Diseño elegante estilo credencial corporativa KOF.
"""
import io
import logging
import os
import requests
from datetime import datetime
from typing import Dict, Any, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch, mm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
)
from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.lib.colors import HexColor

logger = logging.getLogger(__name__)

# Colores corporativos
COLOR_RED = HexColor("#D91E18")
COLOR_RED_DARK = HexColor("#B71C1C")
COLOR_YELLOW = HexColor("#FFC600")
COLOR_DARK = HexColor("#1f2937")
COLOR_GREEN = HexColor("#16a34a")
COLOR_GREEN_DARK = HexColor("#15803d")
COLOR_GREEN_LIGHT = HexColor("#dcfce7")
COLOR_RED_LIGHT = HexColor("#fee2e2")
COLOR_GRAY = HexColor("#6b7280")
COLOR_GRAY_LIGHT = HexColor("#f9fafb")
COLOR_GRAY_BORDER = HexColor("#e5e7eb")
COLOR_WHITE = HexColor("#FFFFFF")

# Path al logo (Coca-Cola FEMSA)
LOGO_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "coca-cola-femsa-logo.png")
# Placeholder para foto
PLACEHOLDER_PHOTO_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "placeholder-user.png")


def fetch_photo_from_url(url: str) -> Optional[bytes]:
    """Descarga una imagen desde una URL."""
    if not url or not url.startswith(("http://", "https://")):
        return None
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.content
        logger.warning(f"Could not fetch photo from {url}: status {response.status_code}")
    except Exception as e:
        logger.warning(f"Error fetching photo from {url}: {e}")
    return None


def generate_certificate_pdf(
    collaborator_data: Dict[str, Any],
    section_results: Optional[Dict[str, Any]] = None,
    qr_image_bytes: Optional[bytes] = None
) -> bytes:
    """
    Genera un PDF de credencial/certificado de seguridad con diseño elegante.

    Args:
        collaborator_data: Datos del colaborador
        section_results: Resultados por sección (opcional)
        qr_image_bytes: Imagen QR en bytes (opcional)

    Returns:
        PDF en bytes
    """
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=30,
        bottomMargin=30
    )

    elements = []
    styles = getSampleStyleSheet()
    page_width = letter[0] - 80  # ancho usable

    is_approved = collaborator_data.get("is_approved", False)
    status_color = COLOR_GREEN if is_approved else COLOR_RED
    status_bg = COLOR_GREEN_LIGHT if is_approved else COLOR_RED_LIGHT
    resultado_text = "APROBADO" if is_approved else "NO APROBADO"

    # === HEADER CON LOGO ===
    if os.path.exists(LOGO_PATH):
        try:
            logo = RLImage(LOGO_PATH, width=140, height=80)
            logo.hAlign = 'CENTER'
            elements.append(logo)
            elements.append(Spacer(1, 6))
        except Exception as e:
            logger.warning(f"Could not load logo: {e}")

    # Línea decorativa roja gruesa
    header_line = Table([['']], colWidths=[page_width])
    header_line.setStyle(TableStyle([
        ('LINEBELOW', (0, 0), (-1, 0), 4, COLOR_RED),
    ]))
    elements.append(header_line)
    elements.append(Spacer(1, 15))

    # === TÍTULO PRINCIPAL ===
    title_style = ParagraphStyle(
        'Title',
        fontSize=24,
        textColor=COLOR_DARK,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold',
        spaceAfter=4,
    )
    subtitle_style = ParagraphStyle(
        'Subtitle',
        fontSize=11,
        textColor=COLOR_GRAY,
        alignment=TA_CENTER,
        spaceAfter=15,
    )

    elements.append(Paragraph("CREDENCIAL DE SEGURIDAD", title_style))
    elements.append(Paragraph("Onboarding KOF · Coca-Cola FEMSA", subtitle_style))

    # === BADGE DE ESTADO ===
    badge_style = ParagraphStyle(
        'Badge',
        fontSize=14,
        textColor=COLOR_WHITE,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold',
    )

    badge_content = [[Paragraph(resultado_text, badge_style)]]
    badge_table = Table(badge_content, colWidths=[160])
    badge_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), status_color),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 20),
        ('RIGHTPADDING', (0, 0), (-1, -1), 20),
    ]))
    badge_table.hAlign = 'CENTER'
    elements.append(badge_table)
    elements.append(Spacer(1, 20))

    # === SECCIÓN: FOTO + DATOS PRINCIPALES ===
    # Extraer datos
    full_name = collaborator_data.get("full_name", collaborator_data.get("nombre_completo", "N/A"))
    rfc = collaborator_data.get("rfc", collaborator_data.get("rfc_colaborador", "N/A"))
    proveedor = collaborator_data.get("proveedor", "")
    tipo_servicio = collaborator_data.get("tipo_servicio", "")
    nss = collaborator_data.get("nss", "")
    rfc_empresa = collaborator_data.get("rfc_empresa", "")
    email = collaborator_data.get("email", "")
    vencimiento = collaborator_data.get("vencimiento", "N/A")
    fecha_emision = collaborator_data.get("fecha_emision", collaborator_data.get("fecha_examen", "N/A"))
    foto_url = collaborator_data.get("foto_url", "")

    # Intentar obtener la foto
    photo_element = None
    if foto_url:
        photo_bytes = fetch_photo_from_url(foto_url)
        if photo_bytes:
            try:
                photo_buffer = io.BytesIO(photo_bytes)
                photo_element = RLImage(photo_buffer, width=100, height=120)
            except Exception as e:
                logger.warning(f"Could not create photo image: {e}")

    # Si no hay foto, usar placeholder o espacio vacío
    if not photo_element:
        # Crear un placeholder gris
        photo_placeholder = Table([['SIN FOTO']], colWidths=[100], rowHeights=[120])
        photo_placeholder.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), COLOR_GRAY_LIGHT),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TEXTCOLOR', (0, 0), (-1, -1), COLOR_GRAY),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOX', (0, 0), (-1, -1), 1, COLOR_GRAY_BORDER),
        ]))
        photo_element = photo_placeholder

    # Estilos para datos
    name_style = ParagraphStyle(
        'Name',
        fontSize=16,
        textColor=COLOR_DARK,
        fontName='Helvetica-Bold',
        leading=20,
    )
    label_style = ParagraphStyle(
        'Label',
        fontSize=8,
        textColor=COLOR_GRAY,
        fontName='Helvetica-Bold',
    )
    value_style = ParagraphStyle(
        'Value',
        fontSize=10,
        textColor=COLOR_DARK,
        fontName='Helvetica',
    )

    # Tabla de datos principales (al lado de la foto)
    main_info = [
        [Paragraph(str(full_name).upper(), name_style)],
        [Spacer(1, 6)],
        [Paragraph("RFC", label_style)],
        [Paragraph(str(rfc), value_style)],
        [Spacer(1, 4)],
        [Paragraph("EMPRESA / PROVEEDOR", label_style)],
        [Paragraph(str(proveedor) if proveedor else "N/A", value_style)],
    ]

    main_info_table = Table(main_info, colWidths=[page_width - 130])
    main_info_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 15),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))

    # Combinar foto + info principal
    if isinstance(photo_element, RLImage):
        photo_cell = photo_element
    else:
        photo_cell = photo_element  # Es la tabla placeholder

    header_row = [[photo_cell, main_info_table]]
    header_table = Table(header_row, colWidths=[110, page_width - 120])
    header_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOX', (0, 0), (0, 0), 1, COLOR_GRAY_BORDER),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 20))

    # === LÍNEA DIVISORIA AMARILLA ===
    yellow_line = Table([['']], colWidths=[page_width])
    yellow_line.setStyle(TableStyle([
        ('LINEBELOW', (0, 0), (-1, 0), 3, COLOR_YELLOW),
    ]))
    elements.append(yellow_line)
    elements.append(Spacer(1, 15))

    # === DATOS ADICIONALES EN DOS COLUMNAS ===
    col_width = (page_width - 20) / 2

    # Columna izquierda
    left_data = []
    if tipo_servicio:
        left_data.append([Paragraph("TIPO DE SERVICIO", label_style)])
        left_data.append([Paragraph(str(tipo_servicio), value_style)])
        left_data.append([Spacer(1, 8)])
    if nss:
        left_data.append([Paragraph("NSS", label_style)])
        left_data.append([Paragraph(str(nss), value_style)])
        left_data.append([Spacer(1, 8)])
    if rfc_empresa:
        left_data.append([Paragraph("RFC EMPRESA", label_style)])
        left_data.append([Paragraph(str(rfc_empresa), value_style)])

    # Columna derecha
    right_data = []
    if email:
        right_data.append([Paragraph("CORREO ELECTRÓNICO", label_style)])
        right_data.append([Paragraph(str(email), value_style)])
        right_data.append([Spacer(1, 8)])
    right_data.append([Paragraph("FECHA DE EMISIÓN", label_style)])
    right_data.append([Paragraph(str(fecha_emision) if fecha_emision else "N/A", value_style)])
    right_data.append([Spacer(1, 8)])

    venc_style = ParagraphStyle(
        'Vencimiento',
        fontSize=12,
        textColor=COLOR_GREEN if is_approved else COLOR_RED,
        fontName='Helvetica-Bold',
    )
    right_data.append([Paragraph("VIGENCIA HASTA", label_style)])
    right_data.append([Paragraph(str(vencimiento) if vencimiento else "N/A", venc_style)])

    left_table = Table(left_data, colWidths=[col_width]) if left_data else None
    right_table = Table(right_data, colWidths=[col_width])

    for tbl in [left_table, right_table]:
        if tbl:
            tbl.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('TOPPADDING', (0, 0), (-1, -1), 0),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ]))

    if left_table:
        two_col_row = [[left_table, right_table]]
        two_col_table = Table(two_col_row, colWidths=[col_width, col_width])
    else:
        two_col_table = right_table

    two_col_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    elements.append(two_col_table)
    elements.append(Spacer(1, 25))

    # === SECCIÓN QR ===
    if qr_image_bytes:
        try:
            qr_buffer = io.BytesIO(qr_image_bytes)
            qr_image = RLImage(qr_buffer, width=100, height=100)

            qr_label = ParagraphStyle(
                'QRLabel',
                fontSize=8,
                textColor=COLOR_GRAY,
                alignment=TA_CENTER,
            )

            qr_section = [
                [qr_image],
                [Spacer(1, 5)],
                [Paragraph("Escanea para verificar autenticidad", qr_label)],
            ]
            qr_table = Table(qr_section, colWidths=[120])
            qr_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ]))
            qr_table.hAlign = 'CENTER'
            elements.append(qr_table)
            elements.append(Spacer(1, 15))
        except Exception as e:
            logger.warning(f"Could not embed QR in PDF: {e}")

    # === FOOTER ===
    footer_line = Table([['']], colWidths=[page_width])
    footer_line.setStyle(TableStyle([
        ('LINEBELOW', (0, 0), (-1, 0), 1, COLOR_GRAY_BORDER),
    ]))
    elements.append(footer_line)
    elements.append(Spacer(1, 10))

    footer_style = ParagraphStyle(
        'Footer',
        fontSize=7,
        textColor=COLOR_GRAY,
        alignment=TA_CENTER,
    )
    elements.append(Paragraph(
        f"Documento generado el {datetime.utcnow().strftime('%d/%m/%Y %H:%M')} UTC",
        footer_style
    ))
    elements.append(Paragraph(
        f"© {datetime.utcnow().year} FEMSA · Entersys. Todos los derechos reservados.",
        footer_style
    ))

    # Build PDF
    try:
        doc.build(elements)
    except Exception as e:
        logger.error(f"Error building PDF: {e}")
        raise

    pdf_bytes = buffer.getvalue()
    buffer.close()

    logger.info(f"PDF generated successfully, size: {len(pdf_bytes)} bytes")
    return pdf_bytes

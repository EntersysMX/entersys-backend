# app/utils/pdf_utils.py
"""
Generación de PDF de credencial de seguridad estilo gafete corporativo.
Diseño compacto en una sola página.
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
from reportlab.lib.colors import HexColor

logger = logging.getLogger(__name__)

# Colores corporativos
COLOR_RED = HexColor("#D91E18")
COLOR_YELLOW = HexColor("#FFC600")
COLOR_DARK = HexColor("#1a1a1a")
COLOR_GREEN = HexColor("#22c55e")
COLOR_GREEN_DARK = HexColor("#16a34a")
COLOR_RED_DARK = HexColor("#dc2626")
COLOR_GRAY = HexColor("#6b7280")
COLOR_GRAY_LIGHT = HexColor("#f3f4f6")
COLOR_GRAY_BORDER = HexColor("#d1d5db")
COLOR_WHITE = HexColor("#FFFFFF")

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


def generate_certificate_pdf(
    collaborator_data: Dict[str, Any],
    section_results: Optional[Dict[str, Any]] = None,
    qr_image_bytes: Optional[bytes] = None
) -> bytes:
    """
    Genera un PDF de credencial estilo gafete corporativo.
    """
    buffer = io.BytesIO()

    # Tamaño carta pero usaremos solo la parte superior
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=50,
        leftMargin=50,
        topMargin=40,
        bottomMargin=40
    )

    elements = []
    page_width = letter[0] - 100

    is_approved = collaborator_data.get("is_approved", False)
    status_color = COLOR_GREEN_DARK if is_approved else COLOR_RED_DARK
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

    # ═══════════════════════════════════════════════════════════════
    # HEADER: Logo centrado
    # ═══════════════════════════════════════════════════════════════
    if os.path.exists(LOGO_PATH):
        try:
            logo = RLImage(LOGO_PATH, width=160, height=91)
            logo.hAlign = 'CENTER'
            elements.append(logo)
        except Exception as e:
            logger.warning(f"Could not load logo: {e}")

    elements.append(Spacer(1, 8))

    # Línea roja superior
    red_line = Table([['']], colWidths=[page_width])
    red_line.setStyle(TableStyle([
        ('LINEBELOW', (0, 0), (-1, 0), 3, COLOR_RED),
    ]))
    elements.append(red_line)
    elements.append(Spacer(1, 15))

    # ═══════════════════════════════════════════════════════════════
    # TÍTULO
    # ═══════════════════════════════════════════════════════════════
    title_style = ParagraphStyle(
        'Title',
        fontSize=20,
        textColor=COLOR_DARK,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold',
        spaceAfter=2,
    )
    elements.append(Paragraph("CREDENCIAL DE SEGURIDAD", title_style))

    subtitle_style = ParagraphStyle(
        'Subtitle',
        fontSize=10,
        textColor=COLOR_GRAY,
        alignment=TA_CENTER,
        spaceAfter=12,
    )
    elements.append(Paragraph("Capacitación Onboarding KOF", subtitle_style))

    # ═══════════════════════════════════════════════════════════════
    # BADGE DE ESTADO
    # ═══════════════════════════════════════════════════════════════
    badge_style = ParagraphStyle(
        'Badge',
        fontSize=12,
        textColor=COLOR_WHITE,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold',
    )
    badge = Table([[Paragraph(resultado_text, badge_style)]], colWidths=[140])
    badge.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), status_color),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    badge.hAlign = 'CENTER'
    elements.append(badge)
    elements.append(Spacer(1, 15))

    # ═══════════════════════════════════════════════════════════════
    # SECCIÓN PRINCIPAL: FOTO + DATOS
    # ═══════════════════════════════════════════════════════════════

    # Obtener foto
    photo_element = None
    if foto_url:
        photo_bytes = fetch_photo_from_url(foto_url)
        if photo_bytes:
            try:
                photo_buffer = io.BytesIO(photo_bytes)
                photo_element = RLImage(photo_buffer, width=90, height=110)
            except Exception as e:
                logger.warning(f"Could not create photo: {e}")

    # Placeholder si no hay foto
    if not photo_element:
        placeholder_style = ParagraphStyle('ph', fontSize=8, textColor=COLOR_GRAY, alignment=TA_CENTER)
        photo_element = Table(
            [[Paragraph("FOTO", placeholder_style)]],
            colWidths=[90], rowHeights=[110]
        )
        photo_element.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), COLOR_GRAY_LIGHT),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOX', (0, 0), (-1, -1), 1, COLOR_GRAY_BORDER),
        ]))

    # Estilos para datos
    name_style = ParagraphStyle('Name', fontSize=14, textColor=COLOR_DARK, fontName='Helvetica-Bold')
    label_style = ParagraphStyle('Label', fontSize=7, textColor=COLOR_GRAY, fontName='Helvetica-Bold')
    value_style = ParagraphStyle('Value', fontSize=9, textColor=COLOR_DARK, fontName='Helvetica')

    # Datos al lado de la foto
    info_data = [
        [Paragraph(str(full_name).upper(), name_style)],
        [Spacer(1, 4)],
        [Paragraph("RFC", label_style)],
        [Paragraph(str(rfc), value_style)],
        [Spacer(1, 2)],
        [Paragraph("EMPRESA", label_style)],
        [Paragraph(str(proveedor)[:40], value_style)],
        [Spacer(1, 2)],
        [Paragraph("TIPO DE SERVICIO", label_style)],
        [Paragraph(str(tipo_servicio)[:35], value_style)],
    ]
    info_table = Table(info_data, colWidths=[page_width - 110])
    info_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))

    # Combinar foto + datos
    main_row = [[photo_element, info_table]]
    main_table = Table(main_row, colWidths=[100, page_width - 110])
    main_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOX', (0, 0), (0, 0), 1, COLOR_GRAY_BORDER),
    ]))
    elements.append(main_table)
    elements.append(Spacer(1, 12))

    # Línea amarilla
    yellow_line = Table([['']], colWidths=[page_width])
    yellow_line.setStyle(TableStyle([
        ('LINEBELOW', (0, 0), (-1, 0), 2, COLOR_YELLOW),
    ]))
    elements.append(yellow_line)
    elements.append(Spacer(1, 10))

    # ═══════════════════════════════════════════════════════════════
    # DATOS ADICIONALES EN GRID
    # ═══════════════════════════════════════════════════════════════
    col_w = page_width / 3

    grid_data = [
        [
            [Paragraph("NSS", label_style), Paragraph(str(nss), value_style)],
            [Paragraph("RFC EMPRESA", label_style), Paragraph(str(rfc_empresa), value_style)],
            [Paragraph("CORREO", label_style), Paragraph(str(email)[:25], value_style)],
        ],
    ]

    # Crear celdas individuales
    cell1 = Table([[Paragraph("NSS", label_style)], [Paragraph(str(nss), value_style)]], colWidths=[col_w])
    cell2 = Table([[Paragraph("RFC EMPRESA", label_style)], [Paragraph(str(rfc_empresa), value_style)]], colWidths=[col_w])
    cell3 = Table([[Paragraph("CORREO", label_style)], [Paragraph(str(email)[:28] + "..." if len(str(email)) > 28 else str(email), value_style)]], colWidths=[col_w])

    for cell in [cell1, cell2, cell3]:
        cell.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))

    grid_row = [[cell1, cell2, cell3]]
    grid_table = Table(grid_row, colWidths=[col_w, col_w, col_w])
    grid_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    elements.append(grid_table)
    elements.append(Spacer(1, 12))

    # ═══════════════════════════════════════════════════════════════
    # FECHAS Y QR
    # ═══════════════════════════════════════════════════════════════
    venc_color = COLOR_GREEN_DARK if is_approved else COLOR_RED_DARK
    venc_style = ParagraphStyle('Venc', fontSize=11, textColor=venc_color, fontName='Helvetica-Bold')

    dates_data = [
        [Paragraph("FECHA DE EMISIÓN", label_style)],
        [Paragraph(str(fecha_emision), value_style)],
        [Spacer(1, 6)],
        [Paragraph("VIGENTE HASTA", label_style)],
        [Paragraph(str(vencimiento), venc_style)],
    ]
    dates_table = Table(dates_data, colWidths=[150])
    dates_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))

    # QR
    qr_element = None
    if qr_image_bytes:
        try:
            qr_buffer = io.BytesIO(qr_image_bytes)
            qr_element = RLImage(qr_buffer, width=85, height=85)
        except Exception as e:
            logger.warning(f"Could not create QR: {e}")

    if qr_element:
        qr_label = ParagraphStyle('QRLabel', fontSize=6, textColor=COLOR_GRAY, alignment=TA_CENTER)
        qr_section = Table([
            [qr_element],
            [Paragraph("Escanea para verificar", qr_label)]
        ], colWidths=[90])
        qr_section.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ]))

        bottom_row = [[dates_table, Spacer(1, 1), qr_section]]
        bottom_table = Table(bottom_row, colWidths=[page_width - 120, 20, 100])
    else:
        bottom_table = dates_table

    bottom_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    elements.append(bottom_table)
    elements.append(Spacer(1, 15))

    # ═══════════════════════════════════════════════════════════════
    # FOOTER
    # ═══════════════════════════════════════════════════════════════
    footer_line = Table([['']], colWidths=[page_width])
    footer_line.setStyle(TableStyle([
        ('LINEBELOW', (0, 0), (-1, 0), 1, COLOR_GRAY_BORDER),
    ]))
    elements.append(footer_line)
    elements.append(Spacer(1, 8))

    footer_style = ParagraphStyle('Footer', fontSize=7, textColor=COLOR_GRAY, alignment=TA_CENTER)
    elements.append(Paragraph(
        f"Documento generado el {datetime.utcnow().strftime('%d/%m/%Y %H:%M')} UTC · © {datetime.utcnow().year} FEMSA - Entersys",
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

# app/utils/pdf_utils.py
"""
Generación de PDF de certificado/credencial de seguridad con ReportLab.
Diseño basado en la credencial KOF aprobada.
"""
import io
import logging
import os
from datetime import datetime
from typing import Dict, Any, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch, mm
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
)
from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.lib.colors import HexColor

logger = logging.getLogger(__name__)

# Colores corporativos
COLOR_RED = HexColor("#D91E18")
COLOR_YELLOW = HexColor("#FFC600")
COLOR_DARK = HexColor("#1f2937")
COLOR_GREEN = HexColor("#16a34a")
COLOR_GREEN_LIGHT = HexColor("#f0fdf4")
COLOR_RED_LIGHT = HexColor("#FEF2F2")
COLOR_GRAY = HexColor("#6b7280")
COLOR_GRAY_LIGHT = HexColor("#f3f4f6")
COLOR_ENTERSYS_BLUE = HexColor("#093D53")

# Path al logo (Coca-Cola FEMSA)
LOGO_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "coca-cola-femsa-logo.png")


def generate_certificate_pdf(
    collaborator_data: Dict[str, Any],
    section_results: Optional[Dict[str, Any]] = None,
    qr_image_bytes: Optional[bytes] = None
) -> bytes:
    """
    Genera un PDF de credencial/certificado de seguridad estilo credencial KOF.

    Args:
        collaborator_data: Datos del colaborador:
            - full_name: Nombre completo
            - rfc: RFC del colaborador
            - proveedor: Proveedor/Empresa
            - tipo_servicio: Tipo de servicio
            - nss: NSS
            - rfc_empresa: RFC de la empresa
            - email: Correo electrónico
            - cert_uuid: UUID del certificado
            - vencimiento: Fecha de vencimiento
            - fecha_emision: Fecha de emisión
            - is_approved: Si está aprobado
        section_results: Resultados por sección (opcional):
            - Seccion1, Seccion2, Seccion3: scores
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
    width = letter[0] - 80  # ancho usable

    # Estilos personalizados
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Title'],
        fontSize=22,
        textColor=COLOR_DARK,
        spaceAfter=6,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )

    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=12,
        textColor=COLOR_GRAY,
        alignment=TA_CENTER,
        spaceAfter=20,
    )

    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=COLOR_DARK,
        spaceBefore=16,
        spaceAfter=8,
        fontName='Helvetica-Bold'
    )

    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=10,
        textColor=COLOR_DARK,
        spaceAfter=4,
    )

    is_approved = collaborator_data.get("is_approved", False)
    resultado_text = "APROBADO" if is_approved else "NO APROBADO"
    status_color = COLOR_GREEN if is_approved else COLOR_RED

    # === HEADER: Logo + Titulo ===
    # Logo si existe (Coca-Cola FEMSA - logo horizontal)
    if os.path.exists(LOGO_PATH):
        try:
            logo = RLImage(LOGO_PATH, width=180, height=60)
            logo.hAlign = 'CENTER'
            elements.append(logo)
            elements.append(Spacer(1, 8))
        except Exception as e:
            logger.warning(f"Could not load logo: {e}")

    # Linea decorativa roja
    red_line_data = [['', '']]
    red_line = Table(red_line_data, colWidths=[width])
    red_line.setStyle(TableStyle([
        ('LINEBELOW', (0, 0), (-1, 0), 3, COLOR_RED),
    ]))
    elements.append(red_line)
    elements.append(Spacer(1, 12))

    # Titulo
    elements.append(Paragraph("Credencial de Seguridad", title_style))
    elements.append(Paragraph("ONBOARDING KOF - Coca-Cola FEMSA", subtitle_style))

    # === BADGE DE ESTADO ===
    status_badge_style = ParagraphStyle(
        'StatusBadge',
        parent=styles['Normal'],
        fontSize=16,
        textColor=colors.white,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold',
        spaceAfter=4,
    )

    badge_data = [[Paragraph(resultado_text, status_badge_style)]]
    badge_table = Table(badge_data, colWidths=[200])
    badge_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), status_color),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('LEFTPADDING', (0, 0), (-1, -1), 20),
        ('RIGHTPADDING', (0, 0), (-1, -1), 20),
        ('ROUNDEDCORNERS', [8, 8, 8, 8]),
    ]))
    badge_table.hAlign = 'CENTER'
    elements.append(badge_table)
    elements.append(Spacer(1, 20))

    # === DATOS DEL COLABORADOR ===
    elements.append(Paragraph("Datos del Colaborador", heading_style))

    # Linea amarilla decorativa
    yellow_line_data = [['', '']]
    yellow_line = Table(yellow_line_data, colWidths=[width])
    yellow_line.setStyle(TableStyle([
        ('LINEBELOW', (0, 0), (-1, 0), 2, COLOR_YELLOW),
    ]))
    elements.append(yellow_line)
    elements.append(Spacer(1, 8))

    # Tabla de datos personales
    label_style = ParagraphStyle(
        'Label',
        parent=styles['Normal'],
        fontSize=9,
        textColor=COLOR_GRAY,
        fontName='Helvetica-Bold',
    )
    value_style = ParagraphStyle(
        'Value',
        parent=styles['Normal'],
        fontSize=11,
        textColor=COLOR_DARK,
        fontName='Helvetica',
    )

    full_name = collaborator_data.get("full_name", "N/A")
    rfc = collaborator_data.get("rfc", collaborator_data.get("rfc_colaborador", "N/A"))
    proveedor = collaborator_data.get("proveedor", "N/A")
    tipo_servicio = collaborator_data.get("tipo_servicio", "N/A")
    nss = collaborator_data.get("nss", "N/A")
    rfc_empresa = collaborator_data.get("rfc_empresa", "N/A")
    email = collaborator_data.get("email", "N/A")
    vencimiento = collaborator_data.get("vencimiento", "N/A")
    fecha_emision = collaborator_data.get("fecha_emision", collaborator_data.get("fecha_examen", "N/A"))

    personal_data = [
        [Paragraph("NOMBRE", label_style), Paragraph(str(full_name), value_style)],
        [Paragraph("RFC", label_style), Paragraph(str(rfc), value_style)],
        [Paragraph("PROVEEDOR / EMPRESA", label_style), Paragraph(str(proveedor) if proveedor else "N/A", value_style)],
        [Paragraph("TIPO DE SERVICIO", label_style), Paragraph(str(tipo_servicio) if tipo_servicio else "N/A", value_style)],
        [Paragraph("NSS", label_style), Paragraph(str(nss) if nss else "N/A", value_style)],
        [Paragraph("RFC EMPRESA", label_style), Paragraph(str(rfc_empresa) if rfc_empresa else "N/A", value_style)],
        [Paragraph("CORREO", label_style), Paragraph(str(email) if email else "N/A", value_style)],
    ]

    personal_table = Table(personal_data, colWidths=[150, width - 160])
    personal_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), COLOR_GRAY_LIGHT),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor("#e5e7eb")),
    ]))
    elements.append(personal_table)
    elements.append(Spacer(1, 16))

    # === QR CODE + FECHAS ===
    qr_and_dates_elements = []

    # Columna de fechas
    date_label_style = ParagraphStyle(
        'DateLabel',
        parent=styles['Normal'],
        fontSize=9,
        textColor=COLOR_GRAY,
        fontName='Helvetica-Bold',
    )
    date_value_style = ParagraphStyle(
        'DateValue',
        parent=styles['Normal'],
        fontSize=11,
        textColor=COLOR_DARK,
        fontName='Helvetica',
    )
    date_value_green = ParagraphStyle(
        'DateValueGreen',
        parent=styles['Normal'],
        fontSize=11,
        textColor=COLOR_GREEN,
        fontName='Helvetica-Bold',
    )

    dates_data = [
        [Paragraph("FECHA DE EMISI\u00d3N", date_label_style)],
        [Paragraph(str(fecha_emision) if fecha_emision else "N/A", date_value_style)],
        [Spacer(1, 8)],
        [Paragraph("VIGENCIA HASTA", date_label_style)],
        [Paragraph(str(vencimiento) if vencimiento else "N/A", date_value_green if is_approved else date_value_style)],
    ]
    dates_table = Table(dates_data, colWidths=[200])
    dates_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))

    # QR code
    qr_element = None
    if qr_image_bytes:
        try:
            qr_buffer = io.BytesIO(qr_image_bytes)
            qr_element = RLImage(qr_buffer, width=120, height=120)
        except Exception as e:
            logger.warning(f"Could not embed QR in PDF: {e}")

    if qr_element:
        bottom_row = [[qr_element, dates_table]]
        bottom_table = Table(bottom_row, colWidths=[140, width - 160])
    else:
        bottom_row = [[dates_table]]
        bottom_table = Table(bottom_row, colWidths=[width])

    bottom_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
    ]))
    elements.append(bottom_table)
    elements.append(Spacer(1, 12))

    if qr_element:
        qr_note_style = ParagraphStyle(
            'QRNote',
            parent=styles['Normal'],
            fontSize=8,
            textColor=COLOR_GRAY,
            alignment=TA_CENTER,
        )
        elements.append(Paragraph("Escanea el c\u00f3digo QR para verificar la autenticidad de esta credencial", qr_note_style))
        elements.append(Spacer(1, 12))

    # === FOOTER ===
    footer_line_data = [['', '']]
    footer_line = Table(footer_line_data, colWidths=[width])
    footer_line.setStyle(TableStyle([
        ('LINEBELOW', (0, 0), (-1, 0), 1, HexColor("#e5e7eb")),
    ]))
    elements.append(footer_line)
    elements.append(Spacer(1, 8))

    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=COLOR_GRAY,
        alignment=TA_CENTER,
    )
    elements.append(Paragraph(
        f"Documento generado autom\u00e1ticamente el {datetime.utcnow().strftime('%d/%m/%Y %H:%M')} UTC",
        footer_style
    ))
    elements.append(Paragraph(
        f"\u00a9 {datetime.utcnow().year} FEMSA - Entersys. Todos los derechos reservados.",
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

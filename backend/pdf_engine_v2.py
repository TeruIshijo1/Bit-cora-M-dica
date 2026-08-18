"""
Motor de generación de PDFs V2 (Hospital Escandón)
===================================================
Generador de notas clínicas y formatos con diseño institucional de alta fidelidad.
Calibración exacta según especificaciones RDLC:
- Hoja Carta: 21.59 cm x 27.94 cm (612 x 792 pt).
- Margen RDLC: Left 0.7cm, Right 0.7cm, Top 0.8cm, Bottom 0.8cm.
- Contenedor Imagen: 20.1 cm x 25.5 cm (569.76 pt x 722.84 pt), Location (0.045cm, 0.15cm).
- Borde: MidnightBlue, Solid, 1.25 pt.
"""

import os
import re
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, TableStyle, KeepTogether
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY

# ─────────────────────────────────────────────────────────────
# RUTAS DE ASSETS OFICIALES (600 DPI INSTITUCIONALES)
# ─────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
POSSIBLE_ASSETS_DIRS = [
    os.path.abspath(os.path.join(BASE_DIR, '..', 'Formatos VERTICAL', 'Encabezado, pie, lateral')),
    os.path.abspath(r'd:\Escritorio\Bitacora_HES\Formatos VERTICAL\Encabezado, pie, lateral')
]

ASSETS_DIR = next((d for d in POSSIBLE_ASSETS_DIRS if os.path.exists(d)), POSSIBLE_ASSETS_DIRS[0])

HEADER_P1_IMG = os.path.join(ASSETS_DIR, 'header_completo_oficial.png')
LOGO_IMG = os.path.join(ASSETS_DIR, 'logo_hes_oficial.png')
FOOTER_CLEAN_IMG = os.path.join(ASSETS_DIR, 'pie_hes_sin_disenador.png')
LATERAL_IMG = os.path.join(ASSETS_DIR, 'lateral_hes_oficial_bold.png')

# ─────────────────────────────────────────────────────────────
# GEOMETRÍA EXACTA RDLC (Carta 21.59 x 27.94 cm)
# ─────────────────────────────────────────────────────────────
PAGE_W, PAGE_H = letter # 612.0 x 792.0 pt (21.59 x 27.94 cm)

# Posición horizontal exacta RDLC (sin desplazamientos laterales)
FRAME_X = 21.12  # 0.7 cm + 0.045 cm = 21.12 pt
FRAME_W = 569.76 # 20.1 cm exactos

FRAME_H = 722.84 # Sin cambio de tamaño (25.5 cm)
FRAME_Y = 47.91  # 42.24 + 5.67 pt

# ─────────────────────────────────────────────────────────────
# PALETA INSTITUCIONAL RDLC
# ─────────────────────────────────────────────────────────────
MIDNIGHT_BLUE = colors.HexColor('#191970')  # MidnightBlue exacto del RDLC
DARK_BLUE = colors.HexColor('#003366')      # Azul oscuro institucional
PRIMARY_BLUE = colors.HexColor('#0056b3')   # Azul médico
BLUE_BAR_COLOR = colors.HexColor('#005FA8') # Azul de la barra del pie
BANNER_BG = colors.HexColor('#e8f4fc')
BANNER_BORDER = colors.HexColor('#b8daff')
BORDER_GREY = colors.HexColor('#dddddd')
TEXT_DARK = colors.HexColor('#111111')
TEXT_MUTED = colors.HexColor('#555555')
RED_ALERT = colors.HexColor('#d93025')


def parse_date_parts(date_str: str):
    """Extrae día, mes, año de cualquier formato."""
    if not date_str:
        return '', '', ''
    m = re.match(r'^(\d{1,2})[\/\-\s]+([A-Za-z0-9]+)[\/\-\s]+(\d{2,4})$', str(date_str).strip())
    if m:
        return m.group(1).zfill(2), m.group(2), m.group(3)
    return str(date_str), '', ''


def parse_time_parts(time_str: str):
    """Extrae hora y minutos."""
    if not time_str:
        return '', ''
    m = re.match(r'^(\d{1,2}):(\d{2})', str(time_str).strip())
    if m:
        return m.group(1).zfill(2), m.group(2)
    return str(time_str), ''


class RDLCCanvas(canvas.Canvas):
    """Canvas de dos pasadas con marco perimetral exacto RDLC (MidnightBlue 1.25pt)."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []
        self.fecha_ingreso = ""
        self.hora_ingreso = ""

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_letterhead(num_pages)
            super().showPage()
        super().save()

    def draw_letterhead(self, total_pages):
        self.saveState()

        # 1. MARCO PERIMETRAL RDLC (MidnightBlue Solid 1.25pt)
        self.setStrokeColor(MIDNIGHT_BLUE)
        self.setLineWidth(1.25)
        self.rect(FRAME_X, FRAME_Y, FRAME_W, FRAME_H, fill=False, stroke=True)

        # 2. ENCABEZADO INSTITUCIONAL (75 pt de alto, alineado al tope del marco)
        head_h = 75.0
        head_y = (FRAME_Y + FRAME_H) - head_h

        if self._pageNumber == 1:
            if os.path.exists(HEADER_P1_IMG):
                self.drawImage(HEADER_P1_IMG, FRAME_X, head_y, width=FRAME_W, height=head_h, mask='auto', preserveAspectRatio=False)

            # Posicionar Fecha y Hora en casillas escaladas a 569.76 pt
            self.setFont("Helvetica-Bold", 7.5)
            self.setFillColor(TEXT_DARK)
            day, month, year = parse_date_parts(self.fecha_ingreso)
            y_base = head_y + 11.2
            scale = FRAME_W / 612.0
            if day:
                self.drawCentredString(FRAME_X + 415.5 * scale, y_base, str(day))
            if month:
                self.drawCentredString(FRAME_X + 446.8 * scale, y_base, str(month))
            if year:
                self.drawCentredString(FRAME_X + 477.5 * scale, y_base, str(year))

            hh, mm = parse_time_parts(self.hora_ingreso)
            if hh:
                self.drawCentredString(FRAME_X + 531.0 * scale, y_base, str(hh))
            if mm:
                self.drawCentredString(FRAME_X + 553.0 * scale, y_base, str(mm))
        else:
            # Encabezado página 2+
            if os.path.exists(LOGO_IMG):
                logo_w = 135
                logo_h = 27
                self.drawImage(LOGO_IMG, FRAME_X + FRAME_W - logo_w - 4, FRAME_Y + FRAME_H - 32, width=logo_w, height=logo_h, mask='auto', preserveAspectRatio=True)

            self.setFont("Helvetica-Bold", 10)
            self.setFillColor(PRIMARY_BLUE)
            self.drawString(FRAME_X + 8, FRAME_Y + FRAME_H - 18, "NOTA DE EVOLUCIÓN DE URGENCIAS")
            self.setFont("Helvetica", 7.5)
            self.setFillColor(TEXT_DARK)
            self.drawString(FRAME_X + 8, FRAME_Y + FRAME_H - 29, "HE-DIRMED-SINPRO-PLT-87/01  (Continuación)")

            self.setStrokeColor(PRIMARY_BLUE)
            self.setLineWidth(1.2)
            self.line(FRAME_X + 6, FRAME_Y + FRAME_H - 34, FRAME_X + FRAME_W - 6, FRAME_Y + FRAME_H - 34)

        # 3. LATERAL DERECHO VERTICAL (Membrete Fundación)
        if os.path.exists(LATERAL_IMG):
            lat_w = 12.0
            lat_h = 560.0
            lat_x = FRAME_X + FRAME_W - lat_w - 2.5
            lat_y = FRAME_Y + 42.0
            self.drawImage(LATERAL_IMG, lat_x, lat_y, width=lat_w, height=lat_h, mask='auto', preserveAspectRatio=False)

        # 4. PIE DE PÁGINA (Integrado sobre el marco inferior)
        if os.path.exists(FOOTER_CLEAN_IMG):
            foot_w = FRAME_W
            foot_h = 38.0
            foot_x = FRAME_X
            foot_y = FRAME_Y + 0.5

            self.drawImage(FOOTER_CLEAN_IMG, foot_x, foot_y, width=foot_w, height=foot_h, mask='auto', preserveAspectRatio=False)

            # Barra azul superior del pie dentro del marco
            self.setFillColor(BLUE_BAR_COLOR)
            self.rect(foot_x, foot_y + foot_h - 4.5, foot_w, 4.5, fill=True, stroke=False)

            # Folio de página institucional
            self.setFont("Helvetica-Bold", 7.5)
            self.setFillColor(PRIMARY_BLUE)
            page_text = f"Página {self._pageNumber} de {total_pages}"
            self.drawRightString(foot_x + foot_w - 6, foot_y + 8, page_text)

        self.restoreState()


def format_clinical_text(raw_text: str) -> str:
    """Convierte texto clínico plano a HTML enriquecido para ReportLab con indentación y viñetas."""
    if not raw_text:
        return ''

    clean = raw_text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    clean = clean.replace('\r\n', '\n').replace('\r', '\n')
    lines = clean.split('\n')
    formatted_lines = []

    for line in lines:
        line_str = line.strip()
        if not line_str:
            continue

        if line_str.startswith(('EXPLORACIÓN FÍSICA:', 'EXPLORACION FISICA:', 'ANÁLISIS / VALORACIÓN:', 'ANALISIS / VALORACION:', 'PLAN TERAPÉUTICO:', 'PLAN TERAPEUTICO:')):
            formatted_lines.append(f"<b><font color='#0056b3'>{line_str}</font></b>")
        elif line_str.startswith(('•', '-', '*')):
            clean_item = line_str.lstrip('•-* ').strip()
            formatted_lines.append(f"&nbsp;&nbsp;&nbsp;&nbsp;•&nbsp;&nbsp;{clean_item}")
        elif re.match(r'^\d+[\.\)]\s*', line_str):
            m = re.match(r'^(\d+[\.\)])\s*(.*)$', line_str)
            if m:
                num_badge = m.group(1)
                rest = m.group(2)
                formatted_lines.append(f"&nbsp;&nbsp;&nbsp;&nbsp;<b>{num_badge}</b>&nbsp;&nbsp;{rest}")
            else:
                formatted_lines.append(line_str)
        else:
            formatted_lines.append(line_str)

    return '<br/>'.join(formatted_lines)


def generate_nota_urgencias(nota_data: dict, pt_data: dict, output_path: str) -> str:
    """
    Genera el PDF oficial de la Nota de Urgencias calibrado exactamente según especificaciones RDLC.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Ancho del contenido de texto: deja 16pt a la derecha para no tocar el lateral vertical
    # y 5pt a la izquierda para separarse del marco perimetral
    content_x = FRAME_X + 5.0
    content_w = FRAME_W - 5.0 - 16.0 # 548.76 pt (~548 pt)

    # Página 1:
    frame_bottom = FRAME_Y + 41.0
    frame_top_p1 = (FRAME_Y + FRAME_H) - 76.5
    frame_h_p1 = frame_top_p1 - frame_bottom

    frame_top_later = (FRAME_Y + FRAME_H) - 38.0
    frame_h_later = frame_top_later - frame_bottom

    frame_p1 = Frame(content_x, frame_bottom, content_w, frame_h_p1, id='p1_frame',
                     leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)

    frame_later = Frame(content_x, frame_bottom, content_w, frame_h_later, id='later_frame',
                        leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)

    template_p1 = PageTemplate(id='FirstPage', frames=frame_p1)
    template_later = PageTemplate(id='LaterPages', frames=frame_later)

    doc = BaseDocTemplate(
        output_path,
        pagesize=letter,
        pageTemplates=[template_p1, template_later]
    )

    # Estilos tipográficos ejecutivos
    style_label = ParagraphStyle('MetaLabel', fontName='Helvetica-Bold', fontSize=7.0, leading=8.6, textColor=TEXT_MUTED)
    style_val = ParagraphStyle('MetaVal', fontName='Helvetica-Bold', fontSize=7.5, leading=9.0, textColor=TEXT_DARK)
    style_val_red = ParagraphStyle('MetaValRed', fontName='Helvetica-Bold', fontSize=7.5, leading=9.0, textColor=RED_ALERT)
    style_soap_h = ParagraphStyle('SoapH', fontName='Helvetica-Bold', fontSize=8.0, leading=9.5, textColor=DARK_BLUE, spaceBefore=2.2, spaceAfter=1.0)
    style_soap_body = ParagraphStyle('SoapB', fontName='Helvetica', fontSize=7.5, leading=9.2, textColor=TEXT_DARK, alignment=TA_JUSTIFY, spaceAfter=1.8)

    story = []

    # ─────────────────────────────────────────────────────────────
    # 1. FICHA DEMOGRÁFICA DEL PACIENTE (PÁGINA 1)
    # ─────────────────────────────────────────────────────────────
    sexo = str(pt_data.get('sexo', '')).upper()
    sex_str = "<b>M</b> [X] &nbsp; <b>F</b> [ ]" if ('M' in sexo and 'F' not in sexo) else ("<b>M</b> [ ] &nbsp; <b>F</b> [X]" if 'F' in sexo else "<b>M</b> [ ] &nbsp; <b>F</b> [ ]")

    turno = str(nota_data.get('turno', 'Matutino')).upper()
    t_mat = "[X]" if 'MAT' in turno else "[ ]"
    t_ves = "[X]" if 'VESP' in turno else "[ ]"
    t_noc = "[X]" if 'NOCT' in turno else "[ ]"
    turno_str = f"<b>Matutino</b> {t_mat} &nbsp;&nbsp; <b>Vespertino</b> {t_ves} &nbsp;&nbsp; <b>Nocturno</b> {t_noc}"

    meta_table_data = [
        # Fila 1: Nombre + Fecha de Nacimiento
        [
            Paragraph('Nombre del Paciente:', style_label),
            Paragraph(f"<b>{pt_data.get('nombre', '').upper()}</b>", style_val),
            Paragraph('Fecha de Nac.:', style_label),
            Paragraph(f"<u>{pt_data.get('dob', '')}</u>", style_val),
            '', ''
        ],
        # Fila 2: Expediente, Cama, Edad, Sexo, Grupo RH
        [
            Paragraph('Expediente:', style_label),
            Paragraph(f"<b>{pt_data.get('mrn', '')}</b> &nbsp;&nbsp; <font color='#555'>Cama:</font> <b>{pt_data.get('cama', '')}</b> &nbsp;&nbsp; <font color='#555'>Edad:</font> <b>{pt_data.get('edad', '')} años</b>", style_val),
            Paragraph('Sexo:', style_label),
            Paragraph(sex_str, style_val),
            Paragraph('Grupo/RH:', style_label),
            Paragraph(f"<b>{pt_data.get('grupo_rh', 'O+')}</b>", style_val)
        ],
        # Fila 3: Alergias (rojo institucional)
        [
            Paragraph('Alergias:', style_label),
            Paragraph(f"<font color='#d93025'><b>{pt_data.get('alergias', 'NEGADAS').upper()}</b></font>", style_val_red),
            '', '', '', ''
        ],
        # Fila 4: Diagnóstico(s)
        [
            Paragraph('Diagnóstico(s):', style_label),
            Paragraph(f"<b>{nota_data.get('diagnostico', '').upper()}</b>", style_val),
            '', '', '', ''
        ],
        # Fila 5: Destino y Egreso
        [
            Paragraph('Destino:', style_label),
            Paragraph(f"<b>{nota_data.get('destino', '')}</b>", style_val),
            Paragraph('Fecha Egreso:', style_label),
            Paragraph(f"{nota_data.get('fecha_egreso', '___/___/___')}", style_val),
            Paragraph('Hora:', style_label),
            Paragraph(f"{nota_data.get('hora_egreso', '__:__')}", style_val)
        ],
        # Fila 6: Fecha de Nota y Turno
        [
            Paragraph('Fecha de Nota:', style_label),
            Paragraph(f"<b>{nota_data.get('fecha', '')}</b> &nbsp;&nbsp;&nbsp;&nbsp; <font color='#555'>Hora:</font> <b>{nota_data.get('hora', '')}</b>", style_val),
            Paragraph('Turno:', style_label),
            Paragraph(turno_str, style_val),
            '', ''
        ]
    ]

    t_meta = Table(meta_table_data, colWidths=[82, 208, 68, 90, 44, 56])
    t_meta.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 0.8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0.8),
        ('LEFTPADDING', (0,0), (-1,-1), 1),
        ('RIGHTPADDING', (0,0), (-1,-1), 1),
        ('SPAN', (1,0), (1,0)),
        ('SPAN', (3,0), (5,0)),
        ('SPAN', (1,1), (1,1)),
        ('SPAN', (1,2), (5,2)),
        ('SPAN', (1,3), (5,3)),
        ('SPAN', (1,4), (1,4)),
        ('SPAN', (1,5), (1,5)),
        ('SPAN', (3,5), (5,5)),
        ('LINEBELOW', (0,0), (-1,0), 0.3, BORDER_GREY),
        ('LINEBELOW', (0,1), (-1,1), 0.3, BORDER_GREY),
        ('LINEBELOW', (0,2), (-1,2), 0.3, BORDER_GREY),
        ('LINEBELOW', (0,3), (-1,3), 0.3, BORDER_GREY),
        ('LINEBELOW', (0,4), (-1,4), 0.3, BORDER_GREY),
        ('LINEBELOW', (0,5), (-1,5), 0.6, PRIMARY_BLUE),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 1.5))

    # ─────────────────────────────────────────────────────────────
    # 2. BANNER: EVOLUCIÓN Y OBSERVACIONES
    # ─────────────────────────────────────────────────────────────
    t_banner = Table(
        [[Paragraph('<b><i>Evolución y observaciones</i></b>', ParagraphStyle('Ban', fontName='Helvetica-BoldOblique', fontSize=8.5, leading=10, textColor=PRIMARY_BLUE, alignment=TA_CENTER))]],
        colWidths=[content_w]
    )
    t_banner.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), BANNER_BG),
        ('BOX', (0,0), (-1,-1), 0.5, BANNER_BORDER),
        ('TOPPADDING', (0,0), (-1,-1), 1.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 1.5),
    ]))
    story.append(t_banner)
    story.append(Spacer(1, 1.5))

    # ─────────────────────────────────────────────────────────────
    # 3. SIGNOS VITALES
    # ─────────────────────────────────────────────────────────────
    v_ta = nota_data.get('vitals_ta', '--')
    v_fc = nota_data.get('vitals_fc', '--')
    v_fr = nota_data.get('vitals_fr', '--')
    v_sat = nota_data.get('vitals_sato2', '--')
    v_peso = nota_data.get('vitals_peso', '--')
    v_talla = nota_data.get('vitals_talla', '--')

    vitals_data = [
        [
            Paragraph('<b>Signos vitales</b>', style_label),
            Paragraph(f"TA: <b>{v_ta}</b>", style_val),
            Paragraph(f"FC: <b>{v_fc}</b>", style_val),
            Paragraph(f"FR: <b>{v_fr}</b>", style_val),
            Paragraph(f"SATO2: <b>{v_sat}%</b>", style_val),
            Paragraph(f"PESO: <b>{v_peso} kg</b>", style_val),
            Paragraph(f"TALLA: <b>{v_talla}</b>", style_val)
        ]
    ]
    t_vitals = Table(vitals_data, colWidths=[70, 79, 79, 79, 80, 80, 81])
    t_vitals.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 1.0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 1.0),
        ('LINEBELOW', (0,0), (-1,-1), 0.5, colors.HexColor('#cccccc')),
    ]))
    story.append(t_vitals)
    story.append(Spacer(1, 1.5))

    # ─────────────────────────────────────────────────────────────
    # 4. CONTENIDO CLINICO SOAP
    # ─────────────────────────────────────────────────────────────
    story.append(Paragraph("<b>(S) Subjetivo:</b>", style_soap_h))
    story.append(Paragraph(format_clinical_text(nota_data.get('subjetivo', '')), style_soap_body))

    story.append(Paragraph("<b>(O) Objetivo:</b>", style_soap_h))
    story.append(Paragraph(format_clinical_text(nota_data.get('objetivo', '')), style_soap_body))

    story.append(Paragraph("<b>(A) Análisis:</b>", style_soap_h))
    story.append(Paragraph(format_clinical_text(nota_data.get('analisis', '')), style_soap_body))

    story.append(Paragraph("<b>(P) Plan (laboratorios solicitados y tratamientos a establecer):</b>", style_soap_h))
    story.append(Paragraph(format_clinical_text(nota_data.get('plan', '')), style_soap_body))

    # ─────────────────────────────────────────────────────────────
    # 5. FIRMAS BAJADAS A LA BASE (JUSTO SOBRE EL PIE)
    # ─────────────────────────────────────────────────────────────
    medico_nombre = str(nota_data.get('medico', '')).upper()
    medico_ced = str(nota_data.get('cedula', 'N/D'))

    sig_col_w = (content_w - 74) / 2 # ~237 pt cada firma

    sig_data = [
        # Fila 0: Espacio en blanco amplio para la firma autógrafa
        [
            Paragraph("&nbsp;", ParagraphStyle('SigBlank', fontName='Helvetica', fontSize=12, leading=16)),
            '',
            Paragraph("&nbsp;", ParagraphStyle('SigBlank', fontName='Helvetica', fontSize=12, leading=16))
        ],
        # Fila 1: Nombre del médico y cédula / MIP
        [
            Paragraph(f"<b>{medico_nombre}</b><br/><font size='7' color='#444'>Céd. Prof. {medico_ced}</font>", ParagraphStyle('SigM', fontName='Helvetica', fontSize=8, leading=9.5, alignment=TA_CENTER)),
            '',
            Paragraph("<br/><font size='7' color='#444'>&nbsp;</font>", ParagraphStyle('SigMIP', fontName='Helvetica', fontSize=8, leading=9.5, alignment=TA_CENTER))
        ],
        # Fila 2: Etiquetas de rol
        [
            Paragraph("<i>Nombre Completo , Firma y Cédulas del Médico</i>", ParagraphStyle('SigL1', fontName='Helvetica-Oblique', fontSize=7.2, leading=8.8, textColor=TEXT_MUTED, alignment=TA_CENTER)),
            '',
            Paragraph("<i>Nombre Completo y Firma del MIP</i>", ParagraphStyle('SigL2', fontName='Helvetica-Oblique', fontSize=7.2, leading=8.8, textColor=TEXT_MUTED, alignment=TA_CENTER))
        ]
    ]

    t_sig = Table(sig_data, colWidths=[sig_col_w, 74, sig_col_w])
    t_sig.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'BOTTOM'),
        ('LINEABOVE', (0,1), (0,1), 1, PRIMARY_BLUE),
        ('LINEABOVE', (2,1), (2,1), 1, PRIMARY_BLUE),
        ('TOPPADDING', (0,0), (-1,0), 6),
        ('BOTTOMPADDING', (0,0), (-1,0), 1),
        ('TOPPADDING', (0,1), (-1,1), 2),
        ('BOTTOMPADDING', (0,1), (-1,1), 1),
        ('TOPPADDING', (0,2), (-1,2), 1),
        ('BOTTOMPADDING', (0,2), (-1,2), 1),
    ]))

    story.append(Spacer(1, 18))
    story.append(KeepTogether([t_sig]))

    # Creador de canvas con datos de ingreso
    def make_canvas(*args, **kwargs):
        c = RDLCCanvas(*args, **kwargs)
        c.fecha_ingreso = pt_data.get('fecha_ingreso', '')
        c.hora_ingreso = pt_data.get('hora_ingreso', '')
        return c

    doc.build(story, canvasmaker=make_canvas)
    return output_path


def generate_test_pdf():
    """Genera PDF de prueba para validación."""
    pt_data = {
        'nombre': 'COMODIN COMODIN COMODIN',
        'dob': '06 Oct 1994',
        'mrn': 'PT-5704',
        'cama': 'Urgencias',
        'edad': '31',
        'sexo': 'M',
        'grupo_rh': 'O+',
        'alergias': 'PENICILINA, SULFAS',
        'fecha_ingreso': '18/08/2026',
        'hora_ingreso': '12:35'
    }

    nota_data = {
        'diagnostico': 'DOLOR ABDOMINAL AGUDO EN FOSA ILIACA DERECHA. SOSPECHA DE APENDICITIS AGUDA.',
        'destino': 'PISO / QUIROFANO',
        'fecha_egreso': '___/___/___',
        'hora_egreso': '__:__',
        'fecha': '18/08/2026',
        'hora': '12:35',
        'turno': 'Matutino',
        'vitals_ta': '130/85',
        'vitals_fc': '92',
        'vitals_fr': '20',
        'vitals_sato2': '96',
        'vitals_peso': '78.5',
        'vitals_talla': '--',
        'subjetivo': (
            'Paciente masculino de 35 anos que acude al servicio de urgencias por presentar '
            'dolor abdominal tipo colico de 12 horas de evolucion, localizado inicialmente en '
            'epigastrio y que posteriormente migro a fosa iliaca derecha.\n'
            'Refiere ademas, un episodio de vomito de contenido gastrico, hiporexia desde el '
            'inicio del cuadro y sensacion de distension abdominal.\n'
            'Niega fiebre cuantificada en casa, niega diarrea, niega sintomas urinarios.\n'
            'Antecedentes: Sin cirugias previas. Alergico a Penicilina y Sulfas. Sin enfermedades '
            'cronico-degenerativas conocidas.'
        ),
        'objetivo': (
            'EXPLORACION FISICA:\n'
            '• Paciente consciente, orientado, algico, en posicion antialgica (decubito lateral '
            'derecho con flexion de miembros pelvicos).\n'
            '• Signos vitales: TA 130/85 mmHg, FC 92 lpm, FR 20 rpm, Temp 38.2 C, SatO2 96%.\n'
            '• Abdomen: Blando, depresible, doloroso a la palpacion profunda en fosa iliaca derecha. '
            'McBurney positivo. Rebote positivo. Rovsing positivo. Psoas positivo.\n'
            '• Peristalsis disminuida.\n'
            '• Sin datos de irritacion peritoneal generalizada.\n'
            '• Extremidades integras, llenado capilar 2 segundos.'
        ),
        'analisis': (
            'ANALISIS / VALORACION:\n'
            'Se trata de paciente masculino con cuadro clinico sugestivo de apendicitis aguda '
            'con base en:\n'
            '1. Migracion del dolor de epigastrio a FID (secuencia cronologica de Murphy).\n'
            '2. Signos apendiculares positivos (McBurney, Rovsing, Psoas).\n'
            '3. Fiebre de 38.2 C y taquicardia como datos de respuesta inflamatoria.\n'
            '4. Escala de Alvarado: 8 puntos (alta probabilidad).\n'
            'Se solicitan: BH completa, QS, EGO, PCR, USG abdominal focalizado en FID.\n'
            'Se mantiene en ayuno y se inicia solucion cristaloide.'
        ),
        'plan': (
            'PLAN TERAPEUTICO:\n'
            '1. Ayuno estricto.\n'
            '2. Solucion Hartmann 1000ml IV para 8 hrs.\n'
            '3. Ketorolaco 30mg IV c/8hrs (analgesia - NO AINES por alergia a sulfas confirmada, '
            'ketorolaco es seguro).\n'
            '4. Ondansetron 4mg IV c/8hrs PRN (antiemetico).\n'
            '5. Omeprazol 40mg IV c/24hrs (proteccion gastrica).\n'
            '6. Solicitar: BH, QS 3, EGO, PCR cuantitativa, TP, TTP, Grupo y Rh.\n'
            '7. Solicitar USG abdominal focalizado en FID.\n'
            '8. Interconsulta a Cirugia General si se confirma diagnostico.\n'
            '9. Vigilancia estrecha de signos vitales cada 2 horas.\n'
            '10. Revalorar con resultados de laboratorio y gabinete.'
        ),
        'medico': 'DR. ALEJANDRO MENDOZA RIVERA',
        'cedula': '12345678',
    }

    out_pdf = os.path.join(BASE_DIR, 'static', 'pdfs', 'TEST_nota_urgencias_final.pdf')
    generate_nota_urgencias(nota_data, pt_data, out_pdf)
    print(f"[OK] Test PDF generated at: {out_pdf}")
    return out_pdf


if __name__ == '__main__':
    generate_test_pdf()

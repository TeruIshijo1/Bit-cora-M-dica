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
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, TableStyle, KeepTogether, CondPageBreak
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY

# ─────────────────────────────────────────────────────────────
# RUTAS DE ASSETS OFICIALES (600 DPI INSTITUCIONALES)
# ─────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
POSSIBLE_ASSETS_DIRS = [
    os.path.abspath(os.path.join(BASE_DIR, '..', 'Formatos VERTICAL', 'Encabezado, pie, lateral')),
    os.path.abspath(r'd:\Escritorio\Bitacora_HES\Formatos VERTICAL\Encabezado, pie, lateral'),
    os.path.abspath(os.path.join(BASE_DIR, 'static', 'official_extracted_assets')),
    os.path.abspath(os.path.join(BASE_DIR, 'static'))
]

def find_asset(*filenames):
    for fn in filenames:
        for d in POSSIBLE_ASSETS_DIRS:
            full_p = os.path.join(d, fn)
            if os.path.exists(full_p):
                return full_p
    return os.path.join(POSSIBLE_ASSETS_DIRS[0], filenames[0])

HEADER_P1_IMG = find_asset('encabezado_perfecto_600dpi.png', 'encabezado_vector_puro_600dpi.png', 'Cabeza1.png')
LOGO_IMG = find_asset('logo_hes_oficial.png', 'official_logo_600dpi.png', 'logo.png')
FOOTER_CLEAN_IMG = find_asset('pie_hes_sin_disenador.png', 'official_footer_600dpi.png')
LATERAL_IMG = find_asset('lateral_hes_oficial_bold.png', 'official_lateral_600dpi.png')

# ─────────────────────────────────────────────────────────────
# GEOMETRÍA EXACTA RDLC (Carta 21.59 x 27.94 cm)
# ─────────────────────────────────────────────────────────────
PAGE_W, PAGE_H = letter # 612.0 x 792.0 pt (21.59 x 27.94 cm)

FRAME_X = 21.12  # 0.7 cm + 0.045 cm = 21.12 pt
FRAME_W = 569.76 # 20.1 cm exactos
FRAME_H = 722.84 # 25.5 cm exactos
FRAME_Y = 42.24  # Posición Y original RDLC exacta (42.24 pt)

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
    m = re.match(r'^(\d{1,2})[\/\-\s]+([A-Za-z0-9]+)[\/\-\s]+(\d{2,4})', str(date_str).strip())
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
        self.doc_info = kwargs.pop('doc_info', {})
        fecha = kwargs.pop('fecha_ingreso', '')
        hora = kwargs.pop('hora_ingreso', '')
        super().__init__(*args, **kwargs)
        self._saved_page_states = []
        self.fecha_ingreso = fecha or self.doc_info.get('fecha_ingreso', '')
        self.hora_ingreso = hora or self.doc_info.get('hora_ingreso', '')

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

        # 1. MARCO PERIMETRAL RDLC (MidnightBlue Solid 1.0pt)
        self.setStrokeColor(MIDNIGHT_BLUE)
        self.setLineWidth(1.0)
        self.rect(FRAME_X, FRAME_Y, FRAME_W, FRAME_H, fill=False, stroke=True)

        # 2. ENCABEZADO INSTITUCIONAL (58 pt de alto, idéntico en todas las hojas)
        head_h = 58.0
        head_y = (FRAME_Y + FRAME_H) - head_h

        if os.path.exists(HEADER_P1_IMG):
            self.drawImage(HEADER_P1_IMG, FRAME_X + 0.5, head_y + 0.5, width=FRAME_W - 1.0, height=head_h - 1.0, preserveAspectRatio=False)

        # Posicionar Fecha y Hora en casillas solo si el formato lo requiere
        if self.doc_info.get('draw_header_dates', False):
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

        # Título dinámico del formato (idéntico en todas las hojas)
        title_lines = self.doc_info.get('title_lines') or []
        if not title_lines:
            single_title = self.doc_info.get('title', '')
            if single_title:
                title_lines = [single_title]
        if title_lines:
            self.setFont("Helvetica-Bold", 8.5)
            self.setFillColor(PRIMARY_BLUE)
            y_txt = head_y + head_h - 18.0
            for line in title_lines:
                self.drawString(FRAME_X + 6.0, y_txt, line)
                y_txt -= 10.5

            # Código del formato fijado en la parte inferior vertical del encabezado con subrayado fino
            code = self.doc_info.get('code', '')
            if code:
                code_y = head_y + 8.0
                line_y = head_y + 6.0
                self.setFont("Helvetica", 6.8)
                self.setFillColor(TEXT_DARK)
                self.drawString(FRAME_X + 6.0, code_y, code)
                code_w = self.stringWidth(code, "Helvetica", 6.8)
                self.setStrokeColor(TEXT_DARK)
                self.setLineWidth(0.6)
                self.line(FRAME_X + 6.0, line_y, FRAME_X + 6.0 + max(code_w + 15.0, 120.0), line_y)

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


def build_signature_table(medico_nombre: str, medico_ced: str, mip_nombre: str, content_w: float, firma_data: dict = None):
    """Construye la tabla de firmas normada con sello biométrico NOM estético para impresión."""
    sig_col_w = (content_w - 74) / 2

    # Si hay firma biométrica verificada
    if firma_data and (firma_data.get('sello_digital') or firma_data.get('hash_sha256')):
        sello_raw = str(firma_data.get('sello_digital') or firma_data.get('hash_sha256') or '')
        sello_resumido = (sello_raw[:28] + '...') if len(sello_raw) > 28 else sello_raw
        fecha_txt = firma_data.get('fecha_hora_firma') or firma_data.get('fecha_hora') or datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        stamp_html = f"""
        <font size='5.8' color='#006633'><b>[✓ FIRMADO BIOMÉTRICAMENTE CON HUELLA]</b></font><br/>
        <font size='5' color='#004d26'><b>NOM-004-SSA3-2012 / NOM-024-SSA3-2012</b></font><br/>
        <font size='4.6' color='#444'><b>Sello:</b> <font face='Courier' size='4.4'>{sello_resumido}</font> | {fecha_txt}</font>
        """
        top_sig_p = Paragraph(stamp_html, ParagraphStyle('SigStamp', fontName='Helvetica', fontSize=5.2, leading=6.5, alignment=TA_CENTER))
    else:
        top_sig_p = Paragraph("&nbsp;", ParagraphStyle('SigBlank', fontName='Helvetica', fontSize=10, leading=14))

    sig_data = [
        [
            top_sig_p,
            '',
            Paragraph("&nbsp;", ParagraphStyle('SigBlank', fontName='Helvetica', fontSize=10, leading=14))
        ],
        [
            Paragraph(f"<b>{medico_nombre}</b><br/><font size='7' color='#444'>Céd. Prof. {medico_ced}</font>", ParagraphStyle('SigM', fontName='Helvetica', fontSize=8, leading=9.5, alignment=TA_CENTER)),
            '',
            Paragraph(f"<b>{mip_nombre or '&nbsp;'}</b><br/><font size='7' color='#444'>&nbsp;</font>", ParagraphStyle('SigMIP', fontName='Helvetica', fontSize=8, leading=9.5, alignment=TA_CENTER))
        ],
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
        ('TOPPADDING', (0,0), (-1,0), 2),
        ('BOTTOMPADDING', (0,0), (-1,0), 1),
        ('TOPPADDING', (0,1), (-1,1), 2),
        ('BOTTOMPADDING', (0,1), (-1,1), 1),
        ('TOPPADDING', (0,2), (-1,2), 1),
        ('BOTTOMPADDING', (0,2), (-1,2), 1),
    ]))
    return t_sig


def generate_nota_urgencias(pt_data: dict, evol1: dict = None, evol2: dict = None, evol3: dict = None, output_path: str = None, is_general: bool = True, firma_data: dict = None) -> str:
    """
    Genera el PDF oficial de la Nota de Urgencias:
    - is_general=True: Imprime el documento general unificado con las 3 evoluciones y 1 sola firma al final.
    - is_general=False: Imprime la nota individual con su propia firma.
    """
    if output_path and os.path.dirname(output_path):
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

    content_x = FRAME_X + 5.0
    content_w = FRAME_W - 5.0 - 16.0 # ~548.76 pt

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

    style_label = ParagraphStyle('MetaLabel', fontName='Helvetica-Bold', fontSize=7.0, leading=8.6, textColor=TEXT_MUTED)
    style_val = ParagraphStyle('MetaVal', fontName='Helvetica-Bold', fontSize=7.5, leading=9.0, textColor=TEXT_DARK)
    style_val_red = ParagraphStyle('MetaValRed', fontName='Helvetica-Bold', fontSize=7.5, leading=9.0, textColor=RED_ALERT)
    style_soap_h = ParagraphStyle('SoapH', fontName='Helvetica-Bold', fontSize=8.0, leading=10.0, textColor=DARK_BLUE, spaceBefore=4.0, spaceAfter=1.5)
    style_soap_body = ParagraphStyle('SoapB', fontName='Helvetica', fontSize=7.5, leading=9.8, textColor=TEXT_DARK, alignment=TA_JUSTIFY, spaceAfter=3.0)

    story = []

    # ─────────────────────────────────────────────────────────────
    # 1. FICHA DEMOGRÁFICA DEL PACIENTE (PÁGINA 1)
    # ─────────────────────────────────────────────────────────────
    sexo = str(pt_data.get('sexo', '')).upper()
    sex_str = "<b>M</b> [X] &nbsp; <b>F</b> [ ]" if ('M' in sexo and 'F' not in sexo) else ("<b>M</b> [ ] &nbsp; <b>F</b> [X]" if 'F' in sexo else "<b>M</b> [ ] &nbsp; <b>F</b> [ ]")

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
            Paragraph(f"<b>{pt_data.get('diagnostico', '').upper()}</b>", style_val),
            '', '', '', ''
        ],
        # Fila 5: Destino y Egreso
        [
            Paragraph('Destino:', style_label),
            Paragraph(f"<b>{pt_data.get('destino', 'OBSERVACIÓN URGENCIAS')}</b>", style_val),
            Paragraph('Fecha Egreso:', style_label),
            Paragraph(f"{pt_data.get('fecha_egreso', '___/___/___')}", style_val),
            Paragraph('Hora:', style_label),
            Paragraph(f"{pt_data.get('hora_egreso', '__:__')}", style_val)
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
        ('LINEBELOW', (0,0), (-1,0), 0.3, BORDER_GREY),
        ('LINEBELOW', (0,1), (-1,1), 0.3, BORDER_GREY),
        ('LINEBELOW', (0,2), (-1,2), 0.3, BORDER_GREY),
        ('LINEBELOW', (0,3), (-1,3), 0.3, BORDER_GREY),
        ('LINEBELOW', (0,4), (-1,4), 0.6, PRIMARY_BLUE),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 2))

    # ─────────────────────────────────────────────────────────────
    # RENDERIZADOR DE EVOLUCIONES
    # ─────────────────────────────────────────────────────────────
    active_evols = [e for e in [evol1, evol2, evol3] if e and (e.get('subjetivo') or e.get('fecha'))]
    if not active_evols and evol1:
        active_evols = [evol1]

    for idx, ev in enumerate(active_evols):
        num = ev.get('num', idx + 1)
        is_cont = (idx > 0)
        
        if is_cont:
            story.append(CondPageBreak(200))
        
        turno = str(ev.get('turno', 'Matutino')).upper()
        t_mat = "[X]" if 'MAT' in turno else "[ ]"
        t_ves = "[X]" if 'VESP' in turno else "[ ]"
        t_noc = "[X]" if 'NOCT' in turno else "[ ]"
        turno_str = f"<b>Matutino</b> {t_mat} &nbsp;&nbsp; <b>Vespertino</b> {t_ves} &nbsp;&nbsp; <b>Nocturno</b> {t_noc}"

        nota_header_data = [
            [
                Paragraph('Fecha de Nota:', style_label),
                Paragraph(f"<b>{ev.get('fecha', '')}</b> &nbsp;&nbsp;&nbsp;&nbsp; <font color='#555'>Hora:</font> <b>{ev.get('hora', '')}</b>", style_val),
                Paragraph('Turno:', style_label),
                Paragraph(turno_str, style_val)
            ]
        ]
        t_nhead = Table(nota_header_data, colWidths=[82, 208, 45, 213])
        t_nhead.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('TOPPADDING', (0,0), (-1,-1), 0.8),
            ('BOTTOMPADDING', (0,0), (-1,-1), 0.8),
            ('LEFTPADDING', (0,0), (-1,-1), 1),
            ('RIGHTPADDING', (0,0), (-1,-1), 1),
        ]))

        ban_text = f"<b><i>Evolución y observaciones {num} {'(Continuación)' if is_cont else ''}</i></b>"
        t_banner = Table(
            [[Paragraph(ban_text, ParagraphStyle('Ban', fontName='Helvetica-BoldOblique', fontSize=8.5, leading=10, textColor=PRIMARY_BLUE, alignment=TA_CENTER))]],
            colWidths=[content_w]
        )
        t_banner.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), BANNER_BG),
            ('BOX', (0,0), (-1,-1), 0.5, BANNER_BORDER),
            ('TOPPADDING', (0,0), (-1,-1), 1.5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 1.5),
        ]))

        v_ta = ev.get('vitals_ta', '--')
        v_fc = ev.get('vitals_fc', '--')
        v_fr = ev.get('vitals_fr', '--')
        v_sat = ev.get('vitals_sato2', '--')
        v_peso = ev.get('vitals_peso', '--')
        v_talla = ev.get('vitals_talla', '--')

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

        evol_header_block = [
            t_nhead,
            Spacer(1, 1.5),
            t_banner,
            Spacer(1, 1.5),
            t_vitals,
            Spacer(1, 2)
        ]
        story.append(KeepTogether(evol_header_block))

        if ev.get('subjetivo'):
            story.append(Paragraph("<b>(S) Subjetivo:</b>", style_soap_h))
            story.append(Paragraph(format_clinical_text(ev.get('subjetivo', '')), style_soap_body))

        if ev.get('objetivo'):
            story.append(Paragraph("<b>(O) Objetivo:</b>", style_soap_h))
            story.append(Paragraph(format_clinical_text(ev.get('objetivo', '')), style_soap_body))

        if ev.get('analisis'):
            story.append(Paragraph("<b>(A) Análisis:</b>", style_soap_h))
            story.append(Paragraph(format_clinical_text(ev.get('analisis', '')), style_soap_body))

        if ev.get('plan'):
            story.append(Paragraph("<b>(P) Plan (laboratorios solicitados y tratamientos a establecer):</b>", style_soap_h))
            story.append(Paragraph(format_clinical_text(ev.get('plan', '')), style_soap_body))

        if not is_general:
            med_nom = str(ev.get('medico', '')).upper()
            med_c = str(ev.get('cedula', 'N/D'))
            mip_nom = str(ev.get('mip', '')).upper()
            t_sig = build_signature_table(med_nom, med_c, mip_nom, content_w, firma_data=firma_data)
            story.append(Spacer(1, 14))
            story.append(KeepTogether([t_sig]))
        else:
            if idx < len(active_evols) - 1:
                story.append(Spacer(1, 18))
                t_div = Table([['']], colWidths=[content_w])
                t_div.setStyle(TableStyle([
                    ('LINEABOVE', (0,0), (-1,-1), 0.75, colors.HexColor('#0056b3')),
                    ('TOPPADDING', (0,0), (-1,-1), 0),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 0),
                ]))
                story.append(t_div)
                story.append(Spacer(1, 16))

    if is_general and active_evols:
        last_ev = active_evols[-1]
        med_nom = str(last_ev.get('medico', '')).upper()
        med_c = str(last_ev.get('cedula', 'N/D'))
        mip_nom = str(last_ev.get('mip', '')).upper()
        
        t_sig = build_signature_table(med_nom, med_c, mip_nom, content_w, firma_data=firma_data)
        story.append(Spacer(1, 22))
        story.append(KeepTogether([t_sig]))

    doc_info = {
        'title': 'NOTA DE EVOLUCIÓN DE URGENCIAS',
        'title_lines': ['NOTA DE EVOLUCIÓN DE URGENCIAS'],
        'code': 'HE-DIRMED-SINPRO-PLT-87/01',
    }

    def make_canvas(*args, **kwargs):
        c = RDLCCanvas(*args, doc_info=doc_info, **kwargs)
        c.fecha_ingreso = pt_data.get('fecha_ingreso', '')
        c.hora_ingreso = pt_data.get('hora_ingreso', '')
        return c

    doc.build(story, canvasmaker=make_canvas)
    return output_path

class CleanConsentCanvas(RDLCCanvas):
    pass

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
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
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

FRAME_W = 569.76 # 20.1 cm exactos
FRAME_H = 722.84 # 25.5 cm exactos
FRAME_X = (PAGE_W - FRAME_W) / 2.0  # 21.12 pt (centrado horizontal perfecto)
FRAME_Y = (PAGE_H - FRAME_H) / 2.0  # 34.58 pt (centrado vertical perfecto)

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

        # 1. ENCABEZADO INSTITUCIONAL (58 pt de alto, idéntico en todas las hojas)
        head_h = 58.0
        head_y = (FRAME_Y + FRAME_H) - head_h

        if os.path.exists(HEADER_P1_IMG):
            self.drawImage(HEADER_P1_IMG, FRAME_X, head_y, width=FRAME_W, height=head_h, preserveAspectRatio=False)

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
            n_lines = len(title_lines)
            f_size = 7.6 if n_lines >= 4 else 8.5
            l_step = 8.8 if n_lines >= 4 else 10.5
            self.setFont("Helvetica-Bold", f_size)
            self.setFillColor(PRIMARY_BLUE)
            y_txt = head_y + head_h - (13.0 if n_lines >= 4 else 16.0)
            for line in title_lines:
                self.drawString(FRAME_X + 6.0, y_txt, line)
                y_txt -= l_step

            # Código del formato fijado en la parte inferior vertical del encabezado con subrayado fino
            code = self.doc_info.get('code', '')
            if code:
                code_y = head_y + 4.5
                line_y = head_y + 3.0
                self.setFont("Helvetica", 6.5)
                self.setFillColor(TEXT_DARK)
                self.drawString(FRAME_X + 6.0, code_y, code)
                code_w = self.stringWidth(code, "Helvetica", 6.5)
                self.setStrokeColor(TEXT_DARK)
                self.setLineWidth(0.6)
                self.line(FRAME_X + 6.0, line_y, FRAME_X + 6.0 + max(code_w + 15.0, 115.0), line_y)

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

            # QR DE VERIFICACIÓN INSTITUCIONAL (Esquina Inferior Derecha)
            qr_data = self.doc_info.get('qr_data') or self.doc_info.get('qr_url')
            draw_qr = bool(qr_data) and self.doc_info.get('draw_qr', True)
            
            if draw_qr:
                try:
                    import qrcode
                    import io
                    from reportlab.lib.utils import ImageReader

                    qr = qrcode.QRCode(box_size=4, border=1)
                    qr.add_data(qr_data)
                    qr.make(fit=True)
                    img_qr = qr.make_image(fill_color="black", back_color="white")
                    buf = io.BytesIO()
                    img_qr.save(buf, format='PNG')
                    buf.seek(0)
                    qr_reader = ImageReader(buf)

                    qr_sz = 25.5
                    qr_x = foot_x + foot_w - qr_sz - 6.0
                    qr_y = foot_y + 3.5

                    # Fondo blanco con marco nítido para asegurar legibilidad perfectamente contenido
                    self.setFillColor(colors.white)
                    self.setStrokeColor(BORDER_GREY)
                    self.setLineWidth(0.5)
                    self.roundRect(qr_x - 1.0, qr_y - 1.0, qr_sz + 2.0, qr_sz + 2.0, 1.2, fill=True, stroke=True)

                    self.drawImage(qr_reader, qr_x, qr_y, width=qr_sz, height=qr_sz, mask='auto')

                    # Metadatos de cotejo a la izquierda del QR
                    self.setFont("Helvetica-Bold", 6.2)
                    self.setFillColor(PRIMARY_BLUE)
                    self.drawRightString(qr_x - 5.0, foot_y + 19.0, f"Página {self._pageNumber} de {total_pages}")

                    self.setFont("Helvetica-Bold", 4.8)
                    self.setFillColor(DARK_BLUE)
                    self.drawRightString(qr_x - 5.0, foot_y + 12.0, "VERIFICACIÓN ECE")

                    self.setFont("Helvetica", 4.2)
                    self.setFillColor(TEXT_MUTED)
                    self.drawRightString(qr_x - 5.0, foot_y + 6.0, "Cotejo NOM-004-SSA3")
                except Exception as eqr:
                    # En caso de excepción, imprimir paginación estándar
                    self.setFont("Helvetica-Bold", 7.5)
                    self.setFillColor(PRIMARY_BLUE)
                    page_text = f"Página {self._pageNumber} de {total_pages}"
                    self.drawRightString(foot_x + foot_w - 6, foot_y + 8, page_text)
            else:
                self.setFont("Helvetica-Bold", 7.5)
                self.setFillColor(PRIMARY_BLUE)
                page_text = f"Página {self._pageNumber} de {total_pages}"
                self.drawRightString(foot_x + foot_w - 6, foot_y + 8, page_text)

        # 5. MARCO PERIMETRAL RDLC (MidnightBlue Solid 1.25pt)
        # Se dibuja al final para garantizar que el marco superior, inferior y lateral quede 100% visible sobre cualquier imagen
        self.setStrokeColor(MIDNIGHT_BLUE)
        self.setLineWidth(1.25)
        self.rect(FRAME_X, FRAME_Y, FRAME_W, FRAME_H, fill=False, stroke=True)

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
    sig_col_w = (content_w - 40.0) / 2.0

    # Sello biométrico médico
    if firma_data and (firma_data.get('sello_digital') or firma_data.get('hash_sha256')):
        sello_raw = str(firma_data.get('sello_digital') or firma_data.get('hash_sha256') or '')
        sello_resumido = (sello_raw[:28] + '...') if len(sello_raw) > 28 else sello_raw
        fecha_txt = firma_data.get('fecha_hora_firma') or firma_data.get('fecha_hora') or datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        stamp_html = f"""
        <font size='5.8' color='#006633'><b>[✔ FIRMADO BIOMÉTRICAMENTE CON HUELLA]</b></font><br/>
        <font size='5' color='#004d26'><b>NOM-004-SSA3-2012 / NOM-024-SSA3-2012</b></font><br/>
        <font size='4.6' color='#444'><b>Sello:</b> <font face='Courier' size='4.4'>{sello_resumido}</font> | {fecha_txt}</font>
        """
        top_sig_p = Paragraph(stamp_html, ParagraphStyle('SigStamp', fontName='Helvetica', fontSize=5.2, leading=6.5, alignment=TA_CENTER))
    else:
        top_sig_p = Paragraph("&nbsp;", ParagraphStyle('SigBlank', fontName='Helvetica', fontSize=8, leading=12))

    # Sello biométrico paciente
    pac_stamp_p = Paragraph("&nbsp;", ParagraphStyle('SigBlank', fontName='Helvetica', fontSize=8, leading=12))
    if firma_data and (firma_data.get('sello_paciente') or firma_data.get('firma_paciente_biometrica')):
        sello_pac_val = str(firma_data.get('sello_paciente') or 'BIO-HES:OK')[:24]
        pac_html = f"""
        <font size='5.2' color='#006633'><b>[✔ AUTORIZADO CON HUELLA BIOMÉTRICA]</b></font><br/>
        <font size='4.2' color='#444'><b>Validación Dactilar:</b> <font face='Courier' size='3.8'>{sello_pac_val}</font></font>
        """
        pac_stamp_p = Paragraph(pac_html, ParagraphStyle('SigStampPac', fontName='Helvetica', fontSize=5.0, leading=6.5, alignment=TA_CENTER))

    # Sello biométrico testigo 1
    test_stamp_p = Paragraph("&nbsp;", ParagraphStyle('SigBlank', fontName='Helvetica', fontSize=8, leading=12))
    if firma_data and (firma_data.get('sello_testigo1') or firma_data.get('firma_testigo1_biometrica')):
        sello_t1_val = str(firma_data.get('sello_testigo1') or 'BIO-HES:OK')[:24]
        test_html = f"""
        <font size='5.2' color='#006633'><b>[✔ TESTIGO - HUELLA BIOMÉTRICA]</b></font><br/>
        <font size='4.2' color='#444'><b>Validación Dactilar:</b> <font face='Courier' size='3.8'>{sello_t1_val}</font></font>
        """
        test_stamp_p = Paragraph(test_html, ParagraphStyle('SigStampT1', fontName='Helvetica', fontSize=5.0, leading=6.5, alignment=TA_CENTER))

    doc_ced_text = f"<br/><font size='6.2' color='#334155'><i><b>CÉD. PROF. {medico_ced}</b></i></font>" if (medico_ced and medico_ced != 'N/D') else ""
    
    has_t1 = bool(firma_data and (firma_data.get('sello_testigo1') or firma_data.get('firma_testigo1_biometrica')))
    has_pac = bool(firma_data and (firma_data.get('sello_paciente') or firma_data.get('firma_paciente_biometrica') or firma_data.get('firmante_paciente')))

    if has_pac or has_t1:
        pac_nom = re.sub(r'\s*\([^)]*\)', '', str(firma_data.get('firmante_paciente') or 'Paciente / Titular')).strip()
        pac_par = firma_data.get('parentesco_paciente') or 'Paciente'
        test_nom = re.sub(r'\s*\([^)]*\)', '', str(firma_data.get('firmante_testigo1') or 'Testigo Presencial')).strip()
        test_par = firma_data.get('parentesco_testigo1') or 'Testigo Presencial'

        pac_txt = f"<b>{pac_nom}</b><br/><font size='6.2' color='#334155'><i><b>Parentesco: {pac_par}</b></i></font>"
        test_txt = f"<b>{test_nom}</b><br/><font size='6.2' color='#334155'><i><b>Parentesco: {test_par}</b></i></font>"

        if has_t1:
            t_top = Table([
                [pac_stamp_p, '', test_stamp_p],
                [Paragraph(pac_txt, ParagraphStyle('SigPac', fontName='Helvetica', fontSize=7.8, leading=9.5, alignment=TA_CENTER)), '', Paragraph(test_txt, ParagraphStyle('SigTest', fontName='Helvetica', fontSize=7.8, leading=9.5, alignment=TA_CENTER))]
            ], colWidths=[sig_col_w, 40.0, sig_col_w])
            t_top.setStyle(TableStyle([
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('VALIGN', (0,0), (-1,0), 'BOTTOM'),
                ('VALIGN', (0,1), (-1,1), 'TOP'),
                ('LINEABOVE', (0,1), (0,1), 0.8, PRIMARY_BLUE),
                ('LINEABOVE', (2,1), (2,1), 0.8, PRIMARY_BLUE),
                ('TOPPADDING', (0,0), (-1,0), 0),
                ('BOTTOMPADDING', (0,0), (-1,0), 0.5),
                ('TOPPADDING', (0,1), (-1,1), 2.5),
                ('BOTTOMPADDING', (0,1), (-1,1), 0),
            ]))

            t_bot = Table([
                [top_sig_p],
                [Paragraph(f"<b>{medico_nombre}</b>{doc_ced_text}", ParagraphStyle('SigM', fontName='Helvetica', fontSize=7.8, leading=9.5, alignment=TA_CENTER))]
            ], colWidths=[sig_col_w], hAlign='CENTER')
            t_bot.setStyle(TableStyle([
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('VALIGN', (0,0), (0,0), 'BOTTOM'),
                ('VALIGN', (0,1), (0,1), 'TOP'),
                ('LINEABOVE', (0,1), (0,1), 0.8, PRIMARY_BLUE),
                ('TOPPADDING', (0,0), (-1,0), 0),
                ('BOTTOMPADDING', (0,0), (-1,0), 0.5),
                ('TOPPADDING', (0,1), (-1,1), 2.5),
                ('BOTTOMPADDING', (0,1), (-1,1), 0),
            ]))

            wrapper = Table([
                [t_top],
                [Spacer(1, 10.0)],
                [t_bot]
            ], colWidths=[content_w], hAlign='CENTER')
            wrapper.setStyle(TableStyle([
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('LEFTPADDING', (0,0), (-1,-1), 0),
                ('RIGHTPADDING', (0,0), (-1,-1), 0),
                ('TOPPADDING', (0,0), (-1,-1), 0),
                ('BOTTOMPADDING', (0,0), (-1,-1), 0),
            ]))
            return wrapper
        else:
            # Solo paciente y médico lado a lado
            sig_data = [
                [pac_stamp_p, '', top_sig_p],
                [Paragraph(pac_txt, ParagraphStyle('SigPac', fontName='Helvetica', fontSize=7.8, leading=9.5, alignment=TA_CENTER)), '', Paragraph(f"<b>{medico_nombre}</b>{doc_ced_text}", ParagraphStyle('SigM', fontName='Helvetica', fontSize=7.8, leading=9.5, alignment=TA_CENTER))]
            ]
            t_sig = Table(sig_data, colWidths=[sig_col_w, 40.0, sig_col_w])
            t_sig.setStyle(TableStyle([
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('VALIGN', (0,0), (-1,0), 'BOTTOM'),
                ('VALIGN', (0,1), (-1,1), 'TOP'),
                ('LINEABOVE', (0,1), (0,1), 0.8, PRIMARY_BLUE),
                ('LINEABOVE', (2,1), (2,1), 0.8, PRIMARY_BLUE),
                ('TOPPADDING', (0,0), (-1,0), 0),
                ('BOTTOMPADDING', (0,0), (-1,0), 0.5),
                ('TOPPADDING', (0,1), (-1,1), 2.5),
                ('BOTTOMPADDING', (0,1), (-1,1), 0),
            ]))
            return t_sig
    else:
        has_mip = bool(mip_nombre and mip_nombre.strip() and mip_nombre.strip().upper() not in ['NONE', 'NULL', 'N/D', ''])

        if has_mip:
            mip_clean = mip_nombre.strip()
            mip_sub_text = "<br/><font size='6.2' color='#334155'><i><b>MÉDICO INTERNO DE PREGRADO / RESIDENTE</b></i></font>"
            sig_data = [
                [top_sig_p, '', Paragraph("&nbsp;", ParagraphStyle('SigBlank', fontName='Helvetica', fontSize=8, leading=12))],
                [Paragraph(f"<b>{medico_nombre}</b>{doc_ced_text}", ParagraphStyle('SigM', fontName='Helvetica', fontSize=7.8, leading=9.5, alignment=TA_CENTER)), '', Paragraph(f"<b>{mip_clean}</b>{mip_sub_text}", ParagraphStyle('SigMIP', fontName='Helvetica', fontSize=7.8, leading=9.5, alignment=TA_CENTER))]
            ]
            t_sig = Table(sig_data, colWidths=[sig_col_w, 40.0, sig_col_w])
            t_sig.setStyle(TableStyle([
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('VALIGN', (0,0), (-1,0), 'BOTTOM'),
                ('VALIGN', (0,1), (-1,1), 'TOP'),
                ('LINEABOVE', (0,1), (0,1), 0.8, PRIMARY_BLUE),
                ('LINEABOVE', (2,1), (2,1), 0.8, PRIMARY_BLUE),
                ('TOPPADDING', (0,0), (-1,0), 0),
                ('BOTTOMPADDING', (0,0), (-1,0), 0.5),
                ('TOPPADDING', (0,1), (-1,1), 2.5),
                ('BOTTOMPADDING', (0,1), (-1,1), 0),
            ]))
            return t_sig
        else:
            single_sig_w = 250.0
            gap_w = max(0, (content_w - single_sig_w) / 2.0)
            sig_data = [
                ['', top_sig_p, ''],
                [
                    '',
                    Paragraph(f"<b>{medico_nombre}</b>{doc_ced_text}", ParagraphStyle('SigM', fontName='Helvetica', fontSize=7.8, leading=9.5, alignment=TA_CENTER)),
                    ''
                ]
            ]
            t_sig = Table(sig_data, colWidths=[gap_w, single_sig_w, gap_w])
            t_sig.setStyle(TableStyle([
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('VALIGN', (0,0), (-1,0), 'BOTTOM'),
                ('VALIGN', (0,1), (-1,1), 'TOP'),
                ('LINEABOVE', (1,1), (1,1), 0.8, PRIMARY_BLUE),
                ('TOPPADDING', (0,0), (-1,0), 0),
                ('BOTTOMPADDING', (0,0), (-1,0), 0.5),
                ('TOPPADDING', (0,1), (-1,1), 2.5),
                ('BOTTOMPADDING', (0,1), (-1,1), 0),
            ]))
            return t_sig


def generate_nota_urgencias(pt_data: dict, evol1: dict = None, evol2: dict = None, evol3: dict = None, output_path: str = None, is_general: bool = True, firma_data: dict = None, evoluciones_list: list = None) -> str:
    """
    Genera el PDF oficial de la Nota de Urgencias:
    - is_general=True: Imprime el documento general unificado con todas las evoluciones consecutivas (1..N) y 1 sola firma al final.
    - is_general=False: Imprime la nota individual con su propia firma.
    """
    if output_path and os.path.dirname(output_path):
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

    content_x = FRAME_X + 16.0
    content_w = FRAME_W - 32.0 - 16.0 # ~521.76 pt

    frame_bottom = FRAME_Y + 41.0
    frame_top_p1 = (FRAME_Y + FRAME_H) - 76.5
    frame_h_p1 = frame_top_p1 - frame_bottom

    frame_top_later = (FRAME_Y + FRAME_H) - 68.0
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

    style_label = ParagraphStyle('MetaLabel', fontName='Helvetica-Bold', fontSize=8.0, leading=10.0, textColor=TEXT_MUTED)
    style_val = ParagraphStyle('MetaVal', fontName='Helvetica-Bold', fontSize=8.5, leading=11.0, textColor=TEXT_DARK)
    style_val_red = ParagraphStyle('MetaValRed', fontName='Helvetica-Bold', fontSize=8.5, leading=11.0, textColor=RED_ALERT)
    style_soap_h = ParagraphStyle('SoapH', fontName='Helvetica-Bold', fontSize=9.2, leading=12.0, textColor=DARK_BLUE, spaceBefore=7.0, spaceAfter=2.5)
    style_soap_body = ParagraphStyle('SoapB', fontName='Helvetica', fontSize=8.8, leading=12.5, textColor=TEXT_DARK, alignment=TA_JUSTIFY, spaceAfter=5.0)

    story = []

    # ─────────────────────────────────────────────────────────────
    # 1. FICHA DEMOGRÁFICA DEL PACIENTE (PÁGINA 1)
    # ─────────────────────────────────────────────────────────────
    sexo = str(pt_data.get('sexo', '')).upper()
    sex_str = "MASCULINO" if ('M' in sexo and 'F' not in sexo) else ("FEMENINO" if 'F' in sexo else "NO ESPECIFICADO")

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
            Paragraph(f"<b>{pt_data.get('mrn', '')}</b> &nbsp;&nbsp; <font color='#555'>Cama:</font> <b>{pt_data.get('cama', '')}</b> &nbsp;&nbsp; <font color='#555'>Edad:</font> <b>{str(pt_data.get('edad', '')).replace('años', '').strip()} años</b>", style_val),
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

    t_meta = Table(meta_table_data, colWidths=[76.0, 195.0, 64.0, 85.0, 44.0, content_w - (76.0 + 195.0 + 64.0 + 85.0 + 44.0)])
    t_meta.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 1.8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 1.8),
        ('LEFTPADDING', (0,0), (-1,-1), 1.5),
        ('RIGHTPADDING', (0,0), (-1,-1), 1.5),
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
    story.append(Spacer(1, 4))

    # ─────────────────────────────────────────────────────────────
    # RENDERIZADOR DE EVOLUCIONES CONSECUTIVAS
    # ─────────────────────────────────────────────────────────────
    if evoluciones_list:
        active_evols = [e for e in evoluciones_list if e and (e.get('subjetivo') or e.get('fecha'))]
    else:
        active_evols = [e for e in [evol1, evol2, evol3] if e and (e.get('subjetivo') or e.get('fecha'))]
    if not active_evols and evol1:
        active_evols = [evol1]

    for idx, ev in enumerate(active_evols):
        num = ev.get('num', idx + 1)
        is_cont = (idx > 0)
        
        if is_cont:
            req_space = 290 if (is_general and idx == len(active_evols) - 1) else 200
            story.append(CondPageBreak(req_space))
        
        turno = str(ev.get('turno', 'Matutino')).upper()
        turno_str = "MATUTINO" if 'MAT' in turno else ("VESPERTINO" if 'VESP' in turno else ("NOCTURNO" if 'NOCT' in turno else turno))

        nota_header_data = [
            [
                Paragraph('Fecha de Nota:', style_label),
                Paragraph(f"<b>{ev.get('fecha', '')}</b> &nbsp;&nbsp;&nbsp;&nbsp; <font color='#555'>Hora:</font> <b>{ev.get('hora', '')}</b>", style_val),
                Paragraph('Turno:', style_label),
                Paragraph(turno_str, style_val)
            ]
        ]
        t_nhead = Table(nota_header_data, colWidths=[76.0, 185.0, 42.0, content_w - (76.0 + 185.0 + 42.0)])
        t_nhead.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('TOPPADDING', (0,0), (-1,-1), 1.8),
            ('BOTTOMPADDING', (0,0), (-1,-1), 1.8),
            ('LEFTPADDING', (0,0), (-1,-1), 1.5),
            ('RIGHTPADDING', (0,0), (-1,-1), 1.5),
        ]))

        ban_text = f"<b><i>Evolución y observaciones {num} {'(Continuación)' if is_cont else ''}</i></b>"
        t_banner = Table(
            [[Paragraph(ban_text, ParagraphStyle('Ban', fontName='Helvetica-BoldOblique', fontSize=8.5, leading=10.5, textColor=PRIMARY_BLUE, alignment=TA_CENTER))]],
            colWidths=[content_w]
        )
        t_banner.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), BANNER_BG),
            ('BOX', (0,0), (-1,-1), 0.5, BANNER_BORDER),
            ('TOPPADDING', (0,0), (-1,-1), 2.2),
            ('BOTTOMPADDING', (0,0), (-1,-1), 2.2),
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
        t_vitals = Table(vitals_data, colWidths=[62.0, 72.0, 72.0, 72.0, 78.0, 80.0, content_w - (62.0 + 72.0 + 72.0 + 72.0 + 78.0 + 80.0)])
        t_vitals.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('TOPPADDING', (0,0), (-1,-1), 1.8),
            ('BOTTOMPADDING', (0,0), (-1,-1), 1.8),
            ('LINEBELOW', (0,0), (-1,-1), 0.5, colors.HexColor('#cccccc')),
        ]))

        evol_header_block = [
            t_nhead,
            Spacer(1, 2.5),
            t_banner,
            Spacer(1, 2.5),
            t_vitals,
            Spacer(1, 3.5)
        ]

        if not is_cont:
            story.extend(evol_header_block)
        else:
            story.append(KeepTogether(evol_header_block))

        soap_parts = []
        if ev.get('subjetivo'):
            soap_parts.append(Paragraph("<b>(S) Subjetivo:</b>", style_soap_h))
            soap_parts.append(Paragraph(format_clinical_text(ev.get('subjetivo', '')), style_soap_body))

        if ev.get('objetivo'):
            soap_parts.append(Paragraph("<b>(O) Objetivo:</b>", style_soap_h))
            soap_parts.append(Paragraph(format_clinical_text(ev.get('objetivo', '')), style_soap_body))

        if ev.get('analisis'):
            soap_parts.append(Paragraph("<b>(A) Análisis:</b>", style_soap_h))
            soap_parts.append(Paragraph(format_clinical_text(ev.get('analisis', '')), style_soap_body))

        if ev.get('plan'):
            soap_parts.append(Paragraph("<b>(P) Plan (laboratorios solicitados y tratamientos a establecer):</b>", style_soap_h))
            soap_parts.append(Paragraph(format_clinical_text(ev.get('plan', '')), style_soap_body))
        
        story.extend(soap_parts)

        if not is_general:
            med_nom = str(ev.get('medico', '')).upper()
            med_c = str(ev.get('cedula', 'N/D'))
            mip_nom = str(ev.get('mip', '')).upper()
            t_sig = build_signature_table(med_nom, med_c, mip_nom, content_w, firma_data=firma_data)
            story.append(Spacer(1, 14))
            story.append(KeepTogether([t_sig]))
        else:
            if idx < len(active_evols) - 1:
                story.append(Spacer(1, 8))
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
        story.append(Spacer(1, 14))
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


def build_biometric_stamp_p(tipo_firmante: str = "PACIENTE", sello_id: str = "BIO-HES:OK", fecha_txt: str = "") -> Paragraph:
    """
    Genera un Paragraph con diseño tipográfico oficial para el Sello Biométrico de Paciente, Familiar o Testigo.
    """
    style_stamp = ParagraphStyle(
        'BioStampUnified',
        fontName='Helvetica',
        fontSize=5.0,
        leading=6.5,
        textColor=colors.HexColor('#006633'),
        alignment=TA_CENTER
    )
    
    tipo_upper = tipo_firmante.upper()
    if "TESTIGO" in tipo_upper:
        titulo_stamp = "[✔ TESTIGO - HUELLA BIOMÉTRICA]"
    elif "RECHAZO" in tipo_upper or "DISENTIMIENTO" in tipo_upper:
        titulo_stamp = "[✔ RECHAZO VALIDADO CON HUELLA]"
    else:
        titulo_stamp = "[✔ AUTORIZADO CON HUELLA BIOMÉTRICA]"

    sello_short = str(sello_id)[:24]
    fecha_part = f" | {fecha_txt}" if fecha_txt else ""
    
    html = f"""
    <font size='5.0' color='#006633'><b>{titulo_stamp}</b></font><br/>
    <font size='4.2' color='#444'><b>Validación Dactilar:</b> <font face='Courier' size='3.8'>{sello_short}</font>{fecha_part}</font>
    """
    return Paragraph(html, style_stamp)


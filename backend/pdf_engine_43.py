# -*- coding: utf-8 -*-
"""
Motor PDF para el Formato 43: Orden de Intubación Endotraqueal / Soporte Ventilatorio
Código: HE-DIRMED-SINPRO-PLT-43
Servicio: Urgencias / Terapia Intensiva / Procedimientos
Conforme a NOM-004-SSA3-2012 y NOM-024-SSA3-2012
"""

import os
import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, TableStyle, KeepTogether
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT

try:
    from .pdf_engine_v2 import (
        CleanConsentCanvas, FRAME_X, FRAME_Y, FRAME_W, FRAME_H,
        TEXT_MUTED, TEXT_DARK, PRIMARY_BLUE, RED_ALERT
    )
except ImportError:
    from pdf_engine_v2 import (
        CleanConsentCanvas, FRAME_X, FRAME_Y, FRAME_W, FRAME_H,
        TEXT_MUTED, TEXT_DARK, PRIMARY_BLUE, RED_ALERT
    )


def generate_consentimiento_43(pt_data: dict, output_path: str, firma_data: dict = None) -> str:
    """
    Genera el PDF del Formato 43: Orden de Intubación Endotraqueal (HE-DIRMED-SINPRO-PLT-43).
    Aplica rigurosamente las reglas globales de espaciado, uso del largo de página y
    distribución geométrica de firmas biométricas.
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    content_x = FRAME_X + 16.0
    content_w = FRAME_W - 32.0 - 16.0  # ~521.76 pt

    frame_bottom = FRAME_Y + 41.0
    frame_top = (FRAME_Y + FRAME_H) - 64.0
    frame_h = frame_top - frame_bottom

    frame_p1 = Frame(content_x, frame_bottom, content_w, frame_h, id='p1_frame',
                     leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)

    template_p1 = PageTemplate(id='FirstPage', frames=frame_p1)

    doc = BaseDocTemplate(
        output_path,
        pagesize=letter,
        pageTemplates=[template_p1]
    )

    # Estilos tipográficos
    style_label = ParagraphStyle('MetaLabel', fontName='Helvetica-Bold', fontSize=7.4, leading=9.5, textColor=TEXT_MUTED)
    style_val = ParagraphStyle('MetaVal', fontName='Helvetica-Bold', fontSize=8.0, leading=10.5, textColor=TEXT_DARK)
    
    style_intro = ParagraphStyle('Intro', fontName='Helvetica', fontSize=8.0, leading=11.0, textColor=TEXT_DARK, alignment=TA_JUSTIFY)
    style_body = ParagraphStyle('Body', fontName='Helvetica', fontSize=7.6, leading=10.4, textColor=TEXT_DARK, alignment=TA_JUSTIFY)
    style_date_city = ParagraphStyle('DateCity', fontName='Helvetica-Bold', fontSize=8.0, leading=10.5, textColor=PRIMARY_BLUE, alignment=TA_RIGHT)
    
    style_sig_name = ParagraphStyle('SigName', fontName='Helvetica-Bold', fontSize=7.8, leading=9.5, textColor=TEXT_DARK, alignment=TA_CENTER)
    style_sig_label = ParagraphStyle('SigLbl', fontName='Helvetica', fontSize=6.5, leading=8.0, textColor=TEXT_MUTED, alignment=TA_CENTER)
    style_sig_stamp = ParagraphStyle('SigStamp', fontName='Helvetica', fontSize=5.2, leading=6.8, textColor=colors.HexColor('#005522'), alignment=TA_CENTER)
    style_sig_blank = ParagraphStyle('SigBlank', fontName='Helvetica', fontSize=6.0, leading=7.0, textColor=colors.transparent, alignment=TA_CENTER)

    story = []

    # 1. Datos Generales del Paciente
    paciente_nombre = pt_data.get('paciente_nombre') or pt_data.get('nombre', '')
    expediente = pt_data.get('expediente') or pt_data.get('mrn', '')
    fecha_nac = pt_data.get('fecha_nacimiento') or pt_data.get('dob', '')
    edad_raw = str(pt_data.get('edad', '')).strip()
    edad_display = f"{edad_raw} años" if edad_raw and "año" not in edad_raw.lower() else (edad_raw or '____')
    medico = pt_data.get('medico_tratante') or pt_data.get('medico_nombre') or pt_data.get('medico') or pt_data.get('n_medico') or (firma_data.get('nombre_medico') if isinstance(firma_data, dict) else None) or ''
    cedula = pt_data.get('cedula') or pt_data.get('medico_cedula') or (firma_data.get('cedula') if isinstance(firma_data, dict) else '') or ''
    servicio = pt_data.get('servicio') or pt_data.get('cama') or 'URGENCIAS / TERAPIA INTENSIVA'
    diagnostico = pt_data.get('diagnostico') or pt_data.get('diagnosticos') or 'INSUFICIENCIA RESPIRATORIA AGUDA / COMPROMISO DE VÍA AÉREA'
    
    fecha_val = pt_data.get('fecha_atencion') or pt_data.get('fecha_ingreso') or pt_data.get('fecha') or datetime.datetime.now().strftime('%d/%m/%Y')
    hora_val = pt_data.get('hora_atencion') or pt_data.get('hora_ingreso') or pt_data.get('hora') or datetime.datetime.now().strftime('%H:%M')

    # Paciente capaz / menor / tutor
    raw_capaz = pt_data.get('paciente_capaz', True)
    if isinstance(raw_capaz, str):
        paciente_capaz = raw_capaz.lower() in ('true', '1', 'si', 'yes')
    elif isinstance(raw_capaz, (int, float)):
        paciente_capaz = bool(raw_capaz)
    else:
        paciente_capaz = bool(raw_capaz)

    pariente = (pt_data.get('pariente') or pt_data.get('representante_legal') or pt_data.get('responsable') or '').strip()
    has_tutor = (not paciente_capaz) or bool(pariente)

    # Nombre del declarante (Paciente o Familiar/Representante Legal)
    if has_tutor:
        declarante = pariente or pt_data.get('declarante') or pt_data.get('declarante_nombre') or pt_data.get('paciente_o_representante') or "Tutor / Representante Legal"
        if declarante == paciente_nombre and pariente:
            declarante = pariente
    else:
        declarante = paciente_nombre

    pt_info_data = [
        [
            Paragraph(f"<b>NOMBRE DEL PACIENTE:</b> {paciente_nombre}", style_val),
            Paragraph(f"<b>FECHA DE NAC:</b> {fecha_nac or '___/___/_____'}", style_val),
            Paragraph(f"<b>EDAD:</b> {edad_display}", style_val),
        ],
        [
            Paragraph(f"<b>EXPEDIENTE:</b> {expediente}", style_val),
            Paragraph(f"<b>MÉDICO TRATANTE:</b> {medico}" + (f"<br/><font size='6.8' color='#555555'>CÉD. PROF. {cedula}</font>" if cedula else ""), style_val),
            Paragraph(f"<b>FECHA / HORA:</b> {fecha_val} {hora_val}", style_val),
        ],
        [
            Paragraph(f"<b>DIAGNÓSTICO:</b> {diagnostico}", style_val),
            Paragraph(f"<b>SERVICIO / ÁREA:</b> {servicio.upper()}", style_val),
            Paragraph(f"<b>ESTADO:</b> <font color='#047857'><b>ORDEN ACTIVA</b></font>", style_val),
        ]
    ]

    t_info = Table(pt_info_data, colWidths=[content_w * 0.42, content_w * 0.36, content_w * 0.22])
    t_info.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.75, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
        ('PADDING', (0, 0), (-1, -1), 3.0),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(t_info)
    story.append(Spacer(1, 10))

    # Parámetros del membrete institucional
    expediente_val = expediente or pt_data.get('pt_num', '')
    pt_num_val = str(pt_data.get('pt_num', '') or expediente or '')

    doc_info = {
        'title_lines': [
            'ORDEN DE INTUBACIÓN',
            'ORDEN Y CONSENTIMIENTO INFORMADO PARA INTUBACIÓN ENDOTRAQUEAL',
            'HOSPITAL ESCANDÓN'
        ],
        'code': 'HE-DIRMED-SINPRO-PLT-43',
        'draw_header_dates': False,
        'fecha_ingreso': fecha_val,
        'hora_ingreso': hora_val,
        'expediente': expediente_val,
        'folio': expediente_val,
        'pt_num': pt_num_val,
        'slot': pt_data.get('slot') or pt_data.get('mrnum') or 1,
        'draw_qr': True
    }

    # Contenido Clínico Oficial
    beneficios = pt_data.get('beneficios') or "Aseguramiento de la vía aérea permeable, soporte ventilatorio mecánico invasivo, optimización de la oxigenación tisular y prevención del paro respiratorio o colapso hemodinámico."
    riesgos = pt_data.get('riesgos') or pt_data.get('principales_riesgos') or "Traumatismo de la vía aérea (laringe, cuerdas vocales, tráquea), broncoaspiración, intubación esofágica o selectiva, broncoespasmo, arritmias, hipotensión, neumotórax o necesidad de ventilación mecánica prolongada."
    alternativas = pt_data.get('alternativas') or "Oxigenoterapia de alto flujo, ventilación mecánica no invasiva (según indicación y estabilidad clínica) o manejo médico conservador."

    # Párrafo 1: Declaración inicial
    p1 = Paragraph(
        f"Yo, <b><u>{declarante}</u></b>, declaro que he sido informado(a), amplia y detalladamente hasta mi total comprensión "
        f"sobre el estado de salud y pronóstico de mi paciente: <b><u>{paciente_nombre}</u></b>, con número de expediente: "
        f"<b><u>{expediente}</u></b>, quien se encuentra en el servicio de: <b><u>{servicio}</u></b>, "
        f"quien cuenta con los siguientes diagnósticos: <b><u>{diagnostico}</u></b>.",
        style_intro
    )
    story.append(p1)
    story.append(Spacer(1, 7))

    # Párrafo 2: Decisión y solicitud del procedimiento
    p2 = Paragraph(
        "Lo anterior mencionado determina que el pronóstico no es favorable, por lo que después de analizarlo, he tomado la decisión de "
        "solicitar que se inicien procedimientos tales como: <b>Intubación endotraqueal</b> y soporte ventilatorio mecánico invasivo.",
        style_body
    )
    story.append(p2)
    story.append(Spacer(1, 7))

    # Párrafo 3: Beneficios y riesgos
    p3 = Paragraph(
        f"Por lo tanto, acepto que solo se utilicen las medidas terapéuticas necesarias y con ello brindar mejor soporte a mi paciente, teniendo "
        f"conocimiento de que los beneficios de realizar el procedimiento propuesto son: <u>{beneficios}</u>; "
        f"así mismo se me ha informado de los riesgos que el procedimiento conlleva, tales como: <u>{riesgos}</u>.",
        style_body
    )
    story.append(p3)
    story.append(Spacer(1, 7))

    # Párrafo 4: Alternativas y deslinde
    p4 = Paragraph(
        f"De igual forma se me explicó que existen otras alternativas: <u>{alternativas}</u>, sin embargo, se ha considerado que el procedimiento "
        f"ya mencionado resulta ser el más conveniente. Declaro que liberamos al equipo de salud del <b>Hospital Escandón Fundación María Ana Mier de Escandón, I.A.P.</b>, "
        f"de cualquier responsabilidad derivada de esta decisión clínica tomada en beneficio del paciente.",
        style_body
    )
    story.append(p4)
    story.append(Spacer(1, 8))

    # Fecha y lugar
    p_fecha = Paragraph(
        f"Dado en la Ciudad de México, a las <b>{hora_val}</b> hrs del día <b>{fecha_val}</b>.",
        style_date_city
    )
    story.append(p_fecha)
    story.append(Spacer(1, 14))

    # =========================================================================
    # SECCIÓN DE FIRMAS Y SELLOS BIOMÉTRICOS (REGLAS GLOBALES)
    # =========================================================================
    testigo1 = pt_data.get('testigo1') or pt_data.get('testigo1_nombre') or pt_data.get('testigo_1') or ''
    testigo2 = pt_data.get('testigo2') or pt_data.get('testigo2_nombre') or pt_data.get('testigo_2') or ''

    if has_tutor:
        autoriza_nombre = pariente or declarante
        if not autoriza_nombre or autoriza_nombre == paciente_nombre:
            autoriza_nombre = pariente or "Tutor / Representante Legal"
        parentesco_pac = pt_data.get('parentesco') or pt_data.get('parentesco_declarante') or pt_data.get('parentesco_paciente') or "Familiar / Representante Legal"
        if str(parentesco_pac).upper() in ('PACIENTE', 'TITULAR', 'DIRECTO'):
            parentesco_pac = "Familiar / Representante Legal"
    else:
        autoriza_nombre = paciente_nombre
        parentesco_pac = "Paciente"

    parentesco_test1 = pt_data.get('parentesco_testigo1') or pt_data.get('parentesco_testigo') or 'Testigo Presencial'
    parentesco_test2 = pt_data.get('parentesco_testigo2') or 'Testigo Presencial'

    sig_col_w = (content_w - 30.0) / 2.0

    # Textos de firmas
    autoriza_sig_text = f"<b>{autoriza_nombre}</b><br/><font size='6.2' color='#334155'><i><b>Parentesco: {parentesco_pac}</b></i></font>" if autoriza_nombre else "<b>Nombre completo y firma del declarante / tutor</b>"
    witness1_sig_text = f"<b>{testigo1}</b><br/><font size='6.2' color='#334155'><i><b>Parentesco: {parentesco_test1}</b></i></font>" if testigo1 else "<b>Nombre completo y firma del testigo 1</b>"
    witness2_sig_text = f"<b>{testigo2}</b><br/><font size='6.2' color='#334155'><i><b>Parentesco: {parentesco_test2}</b></i></font>" if testigo2 else "<b>Nombre completo y firma del testigo 2</b>"
    doctor_sig_text = f"<b>{medico}</b><br/><font size='6.4' color='#334155'><i><b>CÉD. PROF. {cedula}</b></i></font>" if cedula else f"<b>{medico}</b>"

    # Sello Médico
    if firma_data and firma_data.get('sello_digital'):
        sello_resumido = str(firma_data['sello_digital'])[:34] + "..."
        fecha_txt = firma_data.get('fecha_hora_firma') or firma_data.get('fecha_hora') or ''
        med_stamp_html = f"""
        <font size='5.2' color='#006633'><b>[✔ FIRMADO CON HUELLA BIOMÉTRICA]</b></font><br/>
        <font size='4.5' color='#004d26'><b>NOM-004-SSA3-2012 / NOM-024-SSA3-2012</b></font><br/>
        <font size='4.2' color='#444'><b>Sello:</b> <font face='Courier' size='3.8'>{sello_resumido}</font> | {fecha_txt}</font>
        """
        top_med_p = Paragraph(med_stamp_html, style_sig_stamp)
    else:
        top_med_p = Paragraph("&nbsp;", ParagraphStyle('SigSpace', fontName='Helvetica', fontSize=8.0, leading=12.0, textColor=colors.transparent, alignment=TA_CENTER))

    # Sello Paciente / Declarante
    if pt_data.get('firma_paciente_biometrica') or pt_data.get('sello_paciente') or (firma_data and firma_data.get('sello_paciente')):
        sello_pac_val = str(pt_data.get('sello_paciente') or (firma_data and firma_data.get('sello_paciente')) or 'BIO-HES:OK')[:24]
        pac_stamp_html = f"""
        <font size='5.0' color='#006633'><b>[✔ AUTORIZADO CON HUELLA BIOMÉTRICA]</b></font><br/>
        <font size='4.2' color='#444'><b>Validación Dactilar:</b> <font face='Courier' size='3.8'>{sello_pac_val}</font></font>
        """
        pac_sig_p = Paragraph(pac_stamp_html, style_sig_stamp)
    else:
        pac_sig_p = Paragraph("&nbsp;", ParagraphStyle('SigSpace', fontName='Helvetica', fontSize=8.0, leading=12.0, textColor=colors.transparent, alignment=TA_CENTER))

    # REGLA GLOBAL 2: Solo testigos con firma/huella real deben salir
    has_t1 = bool(
        pt_data.get('firma_testigo1_biometrica') or 
        pt_data.get('sello_testigo1') or 
        (firma_data and (firma_data.get('sello_testigo1') or firma_data.get('firma_testigo1_biometrica')))
    )
    has_t2 = bool(
        pt_data.get('firma_testigo2_biometrica') or 
        pt_data.get('sello_testigo2') or 
        (firma_data and (firma_data.get('sello_testigo2') or firma_data.get('firma_testigo2_biometrica')))
    )

    if has_t1:
        sello_test1_val = str(pt_data.get('sello_testigo1') or (firma_data and firma_data.get('sello_testigo1')) or 'BIO-HES:OK')[:24]
        test1_stamp_html = f"""
        <font size='5.0' color='#006633'><b>[✔ TESTIGO 1 - HUELLA BIOMÉTRICA]</b></font><br/>
        <font size='4.2' color='#444'><b>Validación Dactilar:</b> <font face='Courier' size='3.8'>{sello_test1_val}</font></font>
        """
        test1_sig_p = Paragraph(test1_stamp_html, style_sig_stamp)
    else:
        test1_sig_p = Paragraph("&nbsp;", ParagraphStyle('SigSpace', fontName='Helvetica', fontSize=8.0, leading=12.0, textColor=colors.transparent, alignment=TA_CENTER))

    if has_t2:
        sello_test2_val = str(pt_data.get('sello_testigo2') or (firma_data and firma_data.get('sello_testigo2')) or 'BIO-HES:OK')[:24]
        test2_stamp_html = f"""
        <font size='5.0' color='#006633'><b>[✔ TESTIGO 2 - HUELLA BIOMÉTRICA]</b></font><br/>
        <font size='4.2' color='#444'><b>Validación Dactilar:</b> <font face='Courier' size='3.8'>{sello_test2_val}</font></font>
        """
        test2_sig_p = Paragraph(test2_stamp_html, style_sig_stamp)
    else:
        test2_sig_p = Paragraph("&nbsp;", ParagraphStyle('SigSpace', fontName='Helvetica', fontSize=8.0, leading=12.0, textColor=colors.transparent, alignment=TA_CENTER))

    # Determinación de casos de firma:
    # 1. 4 Firmas (has_t1 and has_t2): Cuadrícula 2x2
    if has_t1 and has_t2:
        story.append(Spacer(1, 14.0))
        t_4sigs = Table([
            [pac_sig_p, '', test1_sig_p],
            [Paragraph(autoriza_sig_text, style_sig_name), '', Paragraph(witness1_sig_text, style_sig_name)],
            [top_med_p, '', test2_sig_p],
            [Paragraph(doctor_sig_text, style_sig_name), '', Paragraph(witness2_sig_text, style_sig_name)]
        ], colWidths=[sig_col_w, 30.0, sig_col_w])
        t_4sigs.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,0), 'BOTTOM'),
            ('VALIGN', (0,1), (-1,1), 'TOP'),
            ('VALIGN', (0,2), (-1,2), 'BOTTOM'),
            ('VALIGN', (0,3), (-1,3), 'TOP'),
            ('LINEABOVE', (0,1), (0,1), 0.8, PRIMARY_BLUE),
            ('LINEABOVE', (2,1), (2,1), 0.8, PRIMARY_BLUE),
            ('LINEABOVE', (0,3), (0,3), 0.8, PRIMARY_BLUE),
            ('LINEABOVE', (2,3), (2,3), 0.8, PRIMARY_BLUE),
            ('TOPPADDING', (0,0), (-1,0), 0),
            ('BOTTOMPADDING', (0,0), (-1,0), 0.5),
            ('TOPPADDING', (0,1), (-1,1), 2.5),
            ('BOTTOMPADDING', (0,1), (-1,1), 12.0),
            ('TOPPADDING', (0,2), (-1,2), 0),
            ('BOTTOMPADDING', (0,2), (-1,2), 0.5),
            ('TOPPADDING', (0,3), (-1,3), 2.5),
            ('BOTTOMPADDING', (0,3), (-1,3), 0),
        ]))
        story.append(KeepTogether(t_4sigs))

    # 2. 3 Firmas (has_t1 y no has_t2): REGLA GLOBAL 3 -> La 3ra firma abajo CENTRADA entre las 2 de arriba
    elif has_t1 and not has_t2:
        story.append(Spacer(1, 14.0))
        t_top = Table([
            [pac_sig_p, '', test1_sig_p],
            [Paragraph(autoriza_sig_text, style_sig_name), '', Paragraph(witness1_sig_text, style_sig_name)]
        ], colWidths=[sig_col_w, 30.0, sig_col_w])
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

        # Bottom 1: Médico Tratante (Centrado exactamente)
        t_bot = Table([
            [top_med_p],
            [Paragraph(doctor_sig_text, style_sig_name)]
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

        story.append(KeepTogether([t_top, Spacer(1, 14), t_bot]))

    # 3. 2 Firmas (Sin testigos): Declarante/Paciente y Médico Tratante lado a lado
    else:
        story.append(Spacer(1, 28.0))
        t_pair = Table([
            [pac_sig_p, '', top_med_p],
            [Paragraph(autoriza_sig_text, style_sig_name), '', Paragraph(doctor_sig_text, style_sig_name)]
        ], colWidths=[sig_col_w, 30.0, sig_col_w])
        t_pair.setStyle(TableStyle([
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
        story.append(KeepTogether([t_pair]))

    def make_canvas(*args, **kwargs):
        c = CleanConsentCanvas(*args, doc_info=doc_info, **kwargs)
        return c

    doc.build(story, canvasmaker=make_canvas)
    return output_path

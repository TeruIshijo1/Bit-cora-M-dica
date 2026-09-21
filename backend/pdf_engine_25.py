"""
Motor de Generación PDF Formato 25 con Encabezado Exacto y Firma Biométrica NOM-024
HE-DIRMED-CONSUL-PLT-25 (Revisión Ginecológica, Obstétrica y Consulta Externa)
Hospital Escandón — Ciudad de México
"""

import os
import re
from reportlab.lib.pagesizes import letter
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, TableStyle, KeepTogether
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY

try:
    from backend.pdf_engine_v2 import (
        FRAME_X, FRAME_Y, FRAME_W, FRAME_H, 
        TEXT_MUTED, TEXT_DARK, PRIMARY_BLUE, BORDER_GREY, CleanConsentCanvas
    )
except ModuleNotFoundError:
    from pdf_engine_v2 import (
        FRAME_X, FRAME_Y, FRAME_W, FRAME_H, 
        TEXT_MUTED, TEXT_DARK, PRIMARY_BLUE, BORDER_GREY, CleanConsentCanvas
    )


def generate_consentimiento_25(pt_data: dict, output_path: str = None, firma_data: dict = None) -> str:
    if output_path and os.path.dirname(output_path):
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

    content_x = FRAME_X + 16.0
    content_w = FRAME_W - 32.0 - 16.0  # ~521.76 pt

    frame_bottom = FRAME_Y + 42.0
    frame_top_p1 = (FRAME_Y + FRAME_H) - 64.0
    frame_h_p1 = frame_top_p1 - frame_bottom

    frame_p1 = Frame(content_x, frame_bottom, content_w, frame_h_p1, id='p1_frame',
                     leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)

    p1_template = PageTemplate(id='FirstPage', frames=[frame_p1])

    doc = BaseDocTemplate(
        output_path,
        pagesize=letter,
        leftMargin=FRAME_X,
        rightMargin=letter[0] - (FRAME_X + FRAME_W),
        topMargin=letter[1] - (FRAME_Y + FRAME_H),
        bottomMargin=FRAME_Y,
        pageTemplates=[p1_template]
    )

    patient = pt_data.get('patient', {})
    paciente_nombre = patient.get('name', '') or pt_data.get('paciente_nombre', '')
    fecha_nac = patient.get('dob', '') or pt_data.get('fecha_nacimiento', '')
    edad_raw = str(patient.get('age', '') or pt_data.get('edad', '')).strip()
    edad_display = f"{edad_raw} años" if edad_raw and "año" not in edad_raw.lower() else (edad_raw or '____')
    expediente = patient.get('mrn', '') or f"PT-{pt_data.get('pt_num', '')}"
    medico = pt_data.get('medico_tratante', '') or pt_data.get('n_medico', '')
    cedula_prof = pt_data.get('cedula', '')

    fecha_ingreso = patient.get('fecha_ingreso', '') or pt_data.get('fecha_ingreso', '') or pt_data.get('fecha_atencion', '')
    hora_ingreso = patient.get('hora_ingreso', '') or pt_data.get('hora_ingreso', '') or pt_data.get('hora_atencion', '')

    expediente_val = expediente or pt_data.get('expediente') or pt_data.get('pt_num', '')
    pt_num_val = str(pt_data.get('pt_num', '') or expediente_val or '')

    doc_info = {
        'title': 'CONSENTIMIENTO INFORMADO PARA REVISIÓN GINECOLÓGICA, OBSTÉTRICA, CONSULTA EXTERNA.',
        'title_lines': [
            'CONSENTIMIENTO INFORMADO PARA REVISIÓN',
            'GINECOLÓGICA, OBSTÉTRICA, CONSULTA EXTERNA.'
        ],
        'code': 'HE-DIRMED-CONSUL-PLT-25',
        'norm': 'NOM-004-SSA3-2012',
        'fecha_ingreso': fecha_ingreso,
        'hora_ingreso': hora_ingreso,
        'expediente': expediente_val,
        'folio': expediente_val,
        'pt_num': pt_num_val,
        'slot': pt_data.get('slot') or pt_data.get('mrnum') or 1,
        'draw_qr': True
    }

    def canvas_maker(*args, **kwargs):
        return CleanConsentCanvas(*args, doc_info=doc_info, fecha_ingreso=fecha_ingreso, hora_ingreso=hora_ingreso, **kwargs)

    styles = {
        'SectionHeader': ParagraphStyle('SectionHeader', fontName='Helvetica-Bold', fontSize=8.5, leading=11.0, textColor=PRIMARY_BLUE),
        'Body': ParagraphStyle('Body', fontName='Helvetica', fontSize=8.0, leading=11.5, alignment=TA_JUSTIFY, textColor=TEXT_DARK),
        'LegalText': ParagraphStyle('LegalText', fontName='Helvetica', fontSize=7.8, leading=11.2, alignment=TA_JUSTIFY, textColor=TEXT_DARK),
        'LegalFoot': ParagraphStyle('LegalFoot', fontName='Helvetica-Bold', fontSize=6.8, leading=9.0, alignment=TA_CENTER, textColor=TEXT_MUTED),
        
        # Estilos estándar de firmas
        'SigName': ParagraphStyle('SigName', fontName='Helvetica-Bold', fontSize=7.8, leading=9.5, alignment=TA_CENTER, textColor=TEXT_DARK),
        'SigLabel': ParagraphStyle('SigLabel', fontName='Helvetica-Oblique', fontSize=6.8, leading=8.5, alignment=TA_CENTER, textColor=TEXT_MUTED),
        'SigStamp': ParagraphStyle('SigStamp', fontName='Helvetica', fontSize=5.2, leading=6.8, alignment=TA_CENTER),
        'SigBlank': ParagraphStyle('SigBlank', fontName='Helvetica', fontSize=10, leading=12),
    }

    story = []

    # 1. FICHA DEMOGRÁFICA DEL PACIENTE (Inicia en el tope con espaciado limpio)
    story.append(Spacer(1, 4))
    demo_data = [
        [
            Paragraph(f"<b>NOMBRE DEL PACIENTE:</b> {paciente_nombre}", styles['Body']),
            Paragraph(f"<b>FECHA DE NAC:</b> {fecha_nac}", styles['Body']),
            Paragraph(f"<b>EDAD:</b> {edad_display}", styles['Body']),
        ],
        [
            Paragraph(f"<b>EXPEDIENTE:</b> {expediente}", styles['Body']),
            Paragraph(f"<b>MÉDICO TRATANTE:</b> {medico}", styles['Body']),
            Paragraph(f"<b>FECHA / HORA:</b> {fecha_ingreso} {hora_ingreso}", styles['Body']),
        ]
    ]

    t_demo = Table(demo_data, colWidths=[content_w * 0.44, content_w * 0.36, content_w * 0.20])
    t_demo.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.75, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
        ('TOPPADDING', (0, 0), (-1, -1), 4.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4.5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6.0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6.0),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(t_demo)
    story.append(Spacer(1, 10))

    # 2. SECCIÓN 1: PROCEDIMIENTO O INTERVENCIÓN PROYECTADOS
    p_proc_title = Paragraph("<b>Procedimiento o intervención proyectados:</b>", styles['SectionHeader'])
    p_proc_text = Paragraph(
        "Revisión ginecológica u obstétrica (tacto vaginal, tacto rectal, exploración mamaria), hospitalización, "
        "colocación de sondas y catéteres, aplicación de medicamentos, transfusiones sanguíneas, estudios de gabinete "
        "(ultrasonido pélvico y vaginal), tomografía abdominopélvica u otros de ser necesario.",
        styles['Body']
    )
    t_proc = Table([[p_proc_title], [p_proc_text]], colWidths=[content_w])
    t_proc.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.75, colors.HexColor('#CBD5E1')),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#EFF6FF')),
        ('BACKGROUND', (0, 1), (-1, 1), colors.white),
        ('TOPPADDING', (0, 0), (-1, -1), 4.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5.0),
        ('LEFTPADDING', (0, 0), (-1, -1), 6.0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6.0),
    ]))
    story.append(t_proc)
    story.append(Spacer(1, 10))

    # 3. SECCIÓN 2: RIESGOS MÁS FRECUENTES
    p_risk_title = Paragraph("<b>Riesgos más frecuentes inherentes a la hospitalización y a las condiciones del paciente:</b>", styles['SectionHeader'])
    p_risk_text = Paragraph(
        "Dolor, sangrado o hemorragia, daño de órganos vecinos, daño vascular, infecciones nosocomiales, reacciones adversas a "
        "medicamentos o hemoderivados, infección de herida quirúrgica, reacciones anafilácticas, choque anafiláctico.",
        styles['Body']
    )
    t_risk = Table([[p_risk_title], [p_risk_text]], colWidths=[content_w])
    t_risk.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.75, colors.HexColor('#CBD5E1')),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#EFF6FF')),
        ('BACKGROUND', (0, 1), (-1, 1), colors.white),
        ('TOPPADDING', (0, 0), (-1, -1), 4.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5.0),
        ('LEFTPADDING', (0, 0), (-1, -1), 6.0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6.0),
    ]))
    story.append(t_risk)
    story.append(Spacer(1, 10))

    # 4. SECCIÓN 3: DECLARACIÓN DE LIBRE VOLUNTAD Y FUNDAMENTO LEGAL
    decl_p1 = Paragraph(
        "Expreso mi libre voluntad para autorizar el procedimiento o intervención quirúrgica señalada en este documento después de haberme "
        "proporcionado la información completa sobre mi enfermedad y estado actual, la cual fue realizada en forma amplia, precisa y suficiente "
        "en un lenguaje claro y sencillo, informándome sobre los posibles riesgos, complicaciones y secuelas, de igual forma los beneficios. El "
        "médico me informó la existencia de procedimientos alternativos, el derecho a cambiar mi decisión en cualquier momento y manifestarla "
        "antes del procedimiento o intervención. Con el propósito de que mi atención sea adecuada, me comprometo a proporcionar información "
        "completa y veraz, así como seguir las indicaciones médicas.",
        styles['LegalText']
    )
    decl_p2 = Paragraph(
        "Otorgo mi autorización al personal de salud para la atención de contingencias y urgencias derivadas del acto médico señalado "
        "atendiendo al principio de libertad prescriptiva.",
        styles['LegalText']
    )
    decl_foot = Paragraph(
        "CON FUNDAMENTO EN REGLAMENTO DE LA LEY GENERAL DE SALUD EN MATERIA DE PRESTACIÓN DE SERVICIOS DE ATENCIÓN MÉDICA, "
        "ARTÍCULOS 80, 81, 82, 83 Y A LA NORMA OFICIAL MEXICANA NOM-004-SSA3-2012, DEL EXPEDIENTE CLÍNICO numerales 4.2, 10.1, 10.1.3 y apéndice D-17",
        styles['LegalFoot']
    )

    t_decl = Table([[decl_p1], [decl_p2], [decl_foot]], colWidths=[content_w])
    t_decl.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.75, colors.HexColor('#CBD5E1')),
        ('BACKGROUND', (0, 0), (-1, 1), colors.white),
        ('BACKGROUND', (0, 2), (-1, 2), colors.HexColor('#F8FAFC')),
        ('TOPPADDING', (0, 0), (-1, -1), 4.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4.5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6.0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6.0),
    ]))
    story.append(t_decl)
    story.append(Spacer(1, 14))

    # 5. SECCIÓN 4: BLOQUE DE FIRMAS ESTÁNDAR
    pariente = (pt_data.get('pariente') or pt_data.get('representante_legal') or pt_data.get('declarante') or pt_data.get('paciente_o_representante') or '').strip()
    raw_capaz = pt_data.get('paciente_capaz', True)
    if isinstance(raw_capaz, str):
        paciente_capaz = raw_capaz.lower() in ('true', '1', 'si', 'yes')
    elif isinstance(raw_capaz, (int, float)):
        paciente_capaz = bool(raw_capaz)
    else:
        paciente_capaz = bool(raw_capaz)

    if not paciente_capaz:
        parentesco_pac = (pt_data.get('parentesco') or pt_data.get('parentesco_declarante') or pt_data.get('parentesco_paciente') or 'Tutor / Representante Legal').strip()
        if parentesco_pac.upper() in ('PACIENTE', 'TITULAR', 'DIRECTO'):
            parentesco_pac = 'Tutor / Representante Legal'
        paciente_resp = pariente if (pariente and pariente != paciente_nombre) else (pt_data.get('declarante') or 'Tutor / Representante Legal')
    else:
        parentesco_pac = 'Paciente'
        paciente_resp = paciente_nombre

    testigo1_nom = pt_data.get('testigo1', '')
    testigo2_nom = pt_data.get('testigo2', '')

    sig_col_w = (content_w - 40.0) / 2.0

    # Top del médico (Firma biométrica estampada)
    if firma_data and (firma_data.get('sello_digital') or firma_data.get('hash_sha256')):
        sello_raw = str(firma_data.get('sello_digital') or firma_data.get('hash_sha256') or '')
        sello_resumido = (sello_raw[:28] + '...') if len(sello_raw) > 28 else sello_raw
        fecha_txt = firma_data.get('fecha_hora_firma') or firma_data.get('fecha_hora') or ''
        stamp_html = f"""
        <font size='5.5' color='#006633'><b>[✔ FIRMADO BIOMÉTRICAMENTE CON HUELLA]</b></font><br/>
        <font size='4.8' color='#004d26'><b>NOM-004-SSA3-2012 / NOM-024-SSA3-2012</b></font><br/>
        <font size='4.5' color='#444'><b>Sello:</b> <font face='Courier' size='4.2'>{sello_resumido}</font> | {fecha_txt}</font>
        """
        top_med_p = Paragraph(stamp_html, styles['SigStamp'])
    else:
        top_med_p = Paragraph("&nbsp;", styles['SigBlank'])

    # Sello biométrico paciente si existe
    if pt_data.get('firma_paciente_biometrica') or pt_data.get('sello_paciente') or (firma_data and firma_data.get('sello_paciente')):
        sello_pac_val = str(pt_data.get('sello_paciente') or (firma_data and firma_data.get('sello_paciente')) or 'BIO-HES:OK')[:24]
        pac_stamp_html = f"""
        <font size='5.2' color='#006633'><b>[✔ AUTORIZADO CON HUELLA BIOMÉTRICA]</b></font><br/>
        <font size='4.2' color='#444'><b>Validación Dactilar:</b> <font face='Courier' size='3.8'>{sello_pac_val}</font></font>
        """
        pac_sig_p = Paragraph(pac_stamp_html, styles['SigStamp'])
    else:
        pac_sig_p = Paragraph("&nbsp;", styles['SigBlank'])

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

    # Sello biométrico testigo 1 si existe
    if has_t1:
        sello_t1_val = str(pt_data.get('sello_testigo1') or (firma_data and firma_data.get('sello_testigo1')) or 'BIO-HES:OK')[:24]
        t1_stamp_html = f"""
        <font size='5.2' color='#006633'><b>[✔ TESTIGO - HUELLA BIOMÉTRICA]</b></font><br/>
        <font size='4.2' color='#444'><b>Validación Dactilar:</b> <font face='Courier' size='3.8'>{sello_t1_val}</font></font>
        """
        t1_sig_p = Paragraph(t1_stamp_html, styles['SigStamp'])
    else:
        t1_sig_p = Paragraph("&nbsp;", styles['SigBlank'])

    # Sello biométrico testigo 2 si existe
    if has_t2:
        sello_t2_val = str(pt_data.get('sello_testigo2') or (firma_data and firma_data.get('sello_testigo2')) or 'BIO-HES:OK')[:24]
        t2_stamp_html = f"""
        <font size='5.2' color='#006633'><b>[✔ TESTIGO - HUELLA BIOMÉTRICA]</b></font><br/>
        <font size='4.2' color='#444'><b>Validación Dactilar:</b> <font face='Courier' size='3.8'>{sello_t2_val}</font></font>
        """
        t2_sig_p = Paragraph(t2_stamp_html, styles['SigStamp'])
    else:
        t2_sig_p = Paragraph("&nbsp;", styles['SigBlank'])

    parentesco_test1 = pt_data.get('parentesco_testigo1') or 'Testigo Presencial'
    parentesco_test2 = pt_data.get('parentesco_testigo2') or 'Testigo Presencial'
    paciente_clean = re.sub(r'\s*\([^)]*\)', '', str(paciente_resp or '')).strip()
    testigo1_clean = re.sub(r'\s*\([^)]*\)', '', str(testigo1_nom or '')).strip()
    testigo2_clean = re.sub(r'\s*\([^)]*\)', '', str(testigo2_nom or '')).strip()

    doctor_sig_text = f"<b>{medico}</b><br/><font size='6.2' color='#334155'><i><b>CÉD. PROF. {cedula_prof}</b></i></font>" if cedula_prof else f"<b>{medico}</b>"
    patient_sig_text = f"<b>{paciente_clean}</b><br/><font size='6.2' color='#334155'><i><b>Parentesco: {parentesco_pac}</b></i></font>" if paciente_clean else "<b>Nombre completo y firma del paciente o tutor</b>"
    witness1_sig_text = f"<b>{testigo1_clean}</b><br/><font size='6.2' color='#334155'><i><b>Parentesco: {parentesco_test1}</b></i></font>" if testigo1_clean else "<b>Nombre completo del testigo 1</b>"
    witness2_sig_text = f"<b>{testigo2_clean}</b><br/><font size='6.2' color='#334155'><i><b>Parentesco: {parentesco_test2}</b></i></font>" if testigo2_clean else "<b>Nombre completo del testigo 2</b>"

    # Fila 1: Paciente y Médico Tratante
    sig_row1 = [
        [
            pac_sig_p,
            '',
            top_med_p
        ],
        [
            Paragraph(patient_sig_text, styles['SigName']),
            '',
            Paragraph(doctor_sig_text, styles['SigName'])
        ]
    ]

    if has_t1 and has_t2:
        story.append(Spacer(1, 14))
        t_r1 = Table(sig_row1, colWidths=[sig_col_w, 40, sig_col_w])
        t_r1.setStyle(TableStyle([
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
        story.append(t_r1)
        story.append(Spacer(1, 14))
        
        sig_row2 = [
            [t1_sig_p, '', t2_sig_p],
            [Paragraph(witness1_sig_text, styles['SigName']), '', Paragraph(witness2_sig_text, styles['SigName'])]
        ]
        t_r2_styles = [
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,0), 'BOTTOM'),
            ('VALIGN', (0,1), (-1,1), 'TOP'),
            ('LINEABOVE', (0,1), (0,1), 0.8, PRIMARY_BLUE),
            ('LINEABOVE', (2,1), (2,1), 0.8, PRIMARY_BLUE),
            ('TOPPADDING', (0,0), (-1,0), 0),
            ('BOTTOMPADDING', (0,0), (-1,0), 0.5),
            ('TOPPADDING', (0,1), (-1,1), 2.5),
            ('BOTTOMPADDING', (0,1), (-1,1), 0),
        ]
        t_r2 = Table(sig_row2, colWidths=[sig_col_w, 40, sig_col_w])
        t_r2.setStyle(TableStyle(t_r2_styles))
        story.append(t_r2)
    elif has_t1 or has_t2:
        # Caso 2 y 3: Solo 1 testigo firmado -> 3 firmas (Paciente + Testigo arriba, Médico centrado abajo)
        active_test_p = t1_sig_p if has_t1 else t2_sig_p
        active_test_txt = witness1_sig_text if has_t1 else witness2_sig_text
        t_top = Table([
            [pac_sig_p, '', active_test_p],
            [Paragraph(patient_sig_text, styles['SigName']), '', Paragraph(active_test_txt, styles['SigName'])]
        ], colWidths=[sig_col_w, 40, sig_col_w])
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
            [top_med_p],
            [Paragraph(doctor_sig_text, styles['SigName'])]
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

        story.append(Spacer(1, 14))
        story.append(KeepTogether([t_top, Spacer(1, 14), t_bot]))
    else:
        # Sin testigos firmados -> Paciente y Médico lado a lado abajo
        t_r1 = Table(sig_row1, colWidths=[sig_col_w, 40, sig_col_w])
        t_r1.setStyle(TableStyle([
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
        story.append(Spacer(1, 30))
        story.append(t_r1)

    doc.build(story, canvasmaker=canvas_maker)
    return output_path


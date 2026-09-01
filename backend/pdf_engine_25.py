"""
Motor de Generación PDF Formato 25 con Encabezado Exacto y Firma Biométrica NOM-024
HE-DIRMED-CONSUL-PLT-25 (Revisión Ginecológica, Obstétrica y Consulta Externa)
Hospital Escandón — Ciudad de México
"""

import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, TableStyle
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
    paciente_nombre = patient.get('name', '') or pt_data.get('paciente_nombre', 'COMODIN COMODIN COMODIN')
    fecha_nac = patient.get('dob', '') or pt_data.get('fecha_nacimiento', '')
    edad_raw = str(patient.get('age', '') or pt_data.get('edad', '')).strip()
    edad_display = f"{edad_raw} años" if edad_raw and "año" not in edad_raw.lower() else (edad_raw or '____')
    expediente = patient.get('mrn', '') or f"PT-{pt_data.get('pt_num', '')}"
    medico = pt_data.get('medico_tratante', '') or pt_data.get('n_medico', 'DR. JOSE JOSE PRUEBA ENRIQUEZ')
    cedula_prof = pt_data.get('cedula', '') or '7876310/5265849'

    fecha_ingreso = patient.get('fecha_ingreso', '') or pt_data.get('fecha_ingreso', '') or pt_data.get('fecha_atencion', '19/08/2026')
    hora_ingreso = patient.get('hora_ingreso', '') or pt_data.get('hora_ingreso', '') or pt_data.get('hora_atencion', '17:49')

    doc_info = {
        'title': 'CONSENTIMIENTO INFORMADO PARA REVISIÓN GINECOLÓGICA, OBSTÉTRICA, CONSULTA EXTERNA.',
        'title_lines': [
            'CONSENTIMIENTO INFORMADO PARA REVISIÓN',
            'GINECOLÓGICA, OBSTÉTRICA, CONSULTA EXTERNA.'
        ],
        'code': 'HE-DIRMED-CONSUL-PLT-25',
        'norm': 'NOM-004-SSA3-2012',
        'fecha_ingreso': fecha_ingreso,
        'hora_ingreso': hora_ingreso
    }

    def canvas_maker(*args, **kwargs):
        return CleanConsentCanvas(*args, doc_info=doc_info, fecha_ingreso=fecha_ingreso, hora_ingreso=hora_ingreso, **kwargs)

    styles = {
        'SectionHeader': ParagraphStyle('SectionHeader', fontName='Helvetica-Bold', fontSize=8.5, leading=11.0, textColor=PRIMARY_BLUE),
        'Body': ParagraphStyle('Body', fontName='Helvetica', fontSize=8.0, leading=12.0, alignment=TA_JUSTIFY, textColor=TEXT_DARK),
        'LegalText': ParagraphStyle('LegalText', fontName='Helvetica', fontSize=7.8, leading=11.5, alignment=TA_JUSTIFY, textColor=TEXT_DARK),
        'LegalFoot': ParagraphStyle('LegalFoot', fontName='Helvetica-Bold', fontSize=6.5, leading=8.5, alignment=TA_CENTER, textColor=TEXT_MUTED),
        
        # Estilos estándar de firmas
        'SigName': ParagraphStyle('SigName', fontName='Helvetica-Bold', fontSize=8.0, leading=10.0, alignment=TA_CENTER, textColor=TEXT_DARK),
        'SigLabel': ParagraphStyle('SigLabel', fontName='Helvetica-Oblique', fontSize=6.8, leading=8.5, alignment=TA_CENTER, textColor=TEXT_MUTED),
        'SigStamp': ParagraphStyle('SigStamp', fontName='Helvetica', fontSize=5.5, leading=7.0, alignment=TA_CENTER),
        'SigBlank': ParagraphStyle('SigBlank', fontName='Helvetica', fontSize=18, leading=20),
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
    story.append(Spacer(1, 24))

    # 5. SECCIÓN 4: BLOQUE DE FIRMAS ESTÁNDAR
    paciente_resp = pt_data.get('paciente_o_representante', '') or paciente_nombre
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

    # Fila 1: Paciente y Médico Tratante
    sig_row1 = [
        [
            Paragraph("&nbsp;", styles['SigBlank']),
            '',
            top_med_p
        ],
        [
            Paragraph(f"<b>{paciente_resp}</b>", styles['SigName']),
            '',
            Paragraph(f"<b>{medico}</b><br/><font size='7' color='#444'>Céd. Prof. {cedula_prof}</font>", styles['SigName'])
        ],
        [
            Paragraph("Nombre completo y firma del paciente, familiar, tutor o persona legalmente responsable", styles['SigLabel']),
            '',
            Paragraph("Nombre completo, cédula y firma del médico tratante", styles['SigLabel'])
        ]
    ]

    t_r1 = Table(sig_row1, colWidths=[sig_col_w, 40, sig_col_w])
    t_r1.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,0), 'BOTTOM'),
        ('VALIGN', (0,1), (-1,1), 'BOTTOM'),
        ('VALIGN', (0,2), (-1,2), 'TOP'),
        ('LINEABOVE', (0,1), (0,1), 0.8, PRIMARY_BLUE),
        ('LINEABOVE', (2,1), (2,1), 0.8, PRIMARY_BLUE),
        ('BOTTOMPADDING', (0,0), (-1,0), 0),
        ('TOPPADDING', (0,1), (-1,1), 2),
        ('BOTTOMPADDING', (0,1), (-1,1), 3),
        ('TOPPADDING', (0,2), (-1,2), 3),
        ('BOTTOMPADDING', (0,2), (-1,2), 0),
    ]))
    story.append(t_r1)
    story.append(Spacer(1, 22))

    # Fila 2: Testigos 1 y 2
    sig_row2 = [
        [
            Paragraph("&nbsp;", styles['SigBlank']),
            '',
            Paragraph("&nbsp;", styles['SigBlank'])
        ],
        [
            Paragraph(f"<b>{testigo1_nom}</b>" if testigo1_nom else "&nbsp;", styles['SigName']),
            '',
            Paragraph(f"<b>{testigo2_nom}</b>" if testigo2_nom else "&nbsp;", styles['SigName'])
        ],
        [
            Paragraph("Nombre completo y firma del testigo 1", styles['SigLabel']),
            '',
            Paragraph("Nombre completo y firma del testigo 2", styles['SigLabel'])
        ]
    ]

    t_r2 = Table(sig_row2, colWidths=[sig_col_w, 40, sig_col_w])
    t_r2.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,0), 'BOTTOM'),
        ('VALIGN', (0,1), (-1,1), 'BOTTOM'),
        ('VALIGN', (0,2), (-1,2), 'TOP'),
        ('LINEABOVE', (0,1), (0,1), 0.8, PRIMARY_BLUE),
        ('LINEABOVE', (2,1), (2,1), 0.8, PRIMARY_BLUE),
        ('BOTTOMPADDING', (0,0), (-1,0), 0),
        ('TOPPADDING', (0,1), (-1,1), 2),
        ('BOTTOMPADDING', (0,1), (-1,1), 3),
        ('TOPPADDING', (0,2), (-1,2), 3),
        ('BOTTOMPADDING', (0,2), (-1,2), 0),
    ]))
    story.append(t_r2)

    doc.build(story, canvasmaker=canvas_maker)
    return output_path


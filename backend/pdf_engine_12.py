import os
import re
import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, TableStyle, KeepTogether
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY

try:
    from backend.pdf_engine_v2 import (
        RDLCCanvas, CleanConsentCanvas, FRAME_X, FRAME_Y, FRAME_W, FRAME_H, 
        TEXT_MUTED, TEXT_DARK, RED_ALERT, PRIMARY_BLUE, BORDER_GREY
    )
except ModuleNotFoundError:
    from pdf_engine_v2 import (
        RDLCCanvas, CleanConsentCanvas, FRAME_X, FRAME_Y, FRAME_W, FRAME_H, 
        TEXT_MUTED, TEXT_DARK, RED_ALERT, PRIMARY_BLUE, BORDER_GREY
    )

def generate_consentimiento_12(pt_data: dict, output_path: str = None, firma_data: dict = None) -> str:
    """
    Genera el PDF oficial para el Formato 12:
    HE-DIRMED-CONSUL-PLT-12: CARTA DE CONSENTIMIENTO INFORMADO PARA REVISION GINECOLOGICA Y OBSTETRICA HOSPITALIZACION / URGENCIAS.
    """
    if output_path and os.path.dirname(output_path):
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

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

    # Estilos tipográficos institucionales (Optimizados para legibilidad y balance vertical)
    style_label = ParagraphStyle('MetaLabel', fontName='Helvetica-Bold', fontSize=7.5, leading=9.5, textColor=TEXT_MUTED)
    style_val = ParagraphStyle('MetaVal', fontName='Helvetica-Bold', fontSize=8.0, leading=10.5, textColor=TEXT_DARK)
    style_val_red = ParagraphStyle('MetaValRed', fontName='Helvetica-Bold', fontSize=8.0, leading=10.5, textColor=RED_ALERT)
    
    style_norm = ParagraphStyle('NormText', fontName='Helvetica-Oblique', fontSize=7.2, leading=9.5, textColor=colors.HexColor('#555555'), alignment=TA_JUSTIFY)
    style_body = ParagraphStyle('Body', fontName='Helvetica', fontSize=8.0, leading=11.5, textColor=TEXT_DARK, alignment=TA_JUSTIFY)
    style_body_bold = ParagraphStyle('BodyBold', fontName='Helvetica-Bold', fontSize=8.0, leading=11.5, textColor=TEXT_DARK, alignment=TA_JUSTIFY)
    
    style_box_proc = ParagraphStyle('BoxProc', fontName='Helvetica', fontSize=7.8, leading=11.5, textColor=TEXT_DARK, alignment=TA_LEFT)

    style_sig_name = ParagraphStyle('SigName', fontName='Helvetica-Bold', fontSize=7.8, leading=9.5, textColor=TEXT_DARK, alignment=TA_CENTER)
    style_sig_label = ParagraphStyle('SigLbl', fontName='Helvetica', fontSize=6.5, leading=8.2, textColor=TEXT_MUTED, alignment=TA_CENTER)
    style_sig_stamp = ParagraphStyle('SigStamp', fontName='Helvetica', fontSize=5.8, leading=7.2, textColor=colors.HexColor('#005522'), alignment=TA_CENTER)
    style_sig_blank = ParagraphStyle('SigBlank', fontName='Helvetica', fontSize=6.0, leading=7.0, textColor=colors.transparent, alignment=TA_CENTER)

    story = []

    # 1. Datos Generales del Paciente
    paciente_nombre = pt_data.get('paciente_nombre') or pt_data.get('nombre', '')
    expediente = pt_data.get('expediente') or pt_data.get('mrn', '')
    fecha_nac = pt_data.get('fecha_nacimiento') or pt_data.get('dob', '')
    edad_raw = str(pt_data.get('edad', '')).strip()
    edad_display = f"{edad_raw} años" if edad_raw and "año" not in edad_raw.lower() else (edad_raw or '____')
    medico = pt_data.get('medico_tratante') or pt_data.get('n_medico') or ''
    cedula = pt_data.get('cedula', '')
    fecha_val = pt_data.get('fecha_atencion') or pt_data.get('fecha_ingreso') or datetime.datetime.now().strftime('%d/%m/%Y')
    hora_val = pt_data.get('hora_atencion') or pt_data.get('hora_ingreso') or datetime.datetime.now().strftime('%H:%M')

    pt_info_data = [
        [
            Paragraph(f"<b>NOMBRE DEL PACIENTE:</b> {paciente_nombre}", style_val),
            Paragraph(f"<b>FECHA DE NAC:</b> {fecha_nac or '___/___/_____'}", style_val),
            Paragraph(f"<b>EDAD:</b> {edad_display}", style_val),
        ],
        [
            Paragraph(f"<b>EXPEDIENTE:</b> {expediente}", style_val),
            Paragraph(f"<b>MÉDICO TRATANTE:</b> {medico}" + (f"<br/><font size='7.0' color='#555555'>CÉD. PROF. {cedula}</font>" if cedula else ""), style_val),
            Paragraph(f"<b>FECHA / HORA:</b> {fecha_val} {hora_val}", style_val),
        ]
    ]

    t_info = Table(pt_info_data, colWidths=[content_w * 0.44, content_w * 0.36, content_w * 0.20])
    t_info.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.75, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
        ('TOPPADDING', (0, 0), (-1, -1), 4.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4.5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6.0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6.0),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(t_info)
    story.append(Spacer(1, 10))

    # 2. Fundamento Normativo
    norm_txt = (
        "Con fundamento en reglamento de la ley general de salud en materia de prestación de servicios de atención médica, "
        "artículos 80, 81, 82, 83 y a la NORMA OFICIAL MEXICANA NOM-004-SSA3-2012, DEL EXPEDIENTE CLÍNICO numerales 4.2, 10.1, 10.1.3 y apéndice D-17"
    )
    story.append(Paragraph(norm_txt, style_norm))
    story.append(Spacer(1, 8))

    # 3. Diagnóstico y Servicio (Hospitalización / Urgencias)
    diag_txt = pt_data.get('diagnostico') or pt_data.get('diagnosticos') or 'REVISIÓN GINECOLÓGICA Y OBSTÉTRICA'
    servicio = str(pt_data.get('servicio') or pt_data.get('tipo_servicio') or 'URGENCIAS').upper()
    
    is_hosp = "X" if "HOSP" in servicio else "&nbsp;&nbsp;"
    is_urg = "X" if "URG" in servicio or "HOSP" not in servicio else "&nbsp;&nbsp;"

    diag_data = [
        [
            Paragraph("<b>Diagnóstico(s):</b>", style_label),
            Paragraph(f"<b>{diag_txt}</b>", style_val),
            Paragraph(f"Hospitalización ( <b>{is_hosp}</b> ) &nbsp;&nbsp;&nbsp; Urgencias ( <b>{is_urg}</b> )", style_val)
        ]
    ]
    t_diag = Table(diag_data, colWidths=[70, 290, content_w - (70 + 290)])
    t_diag.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_GREY),
        ('BACKGROUND', (0,0), (0,0), colors.HexColor('#F8FAFC')),
        ('PADDING', (0,0), (-1,-1), 4.0),
    ]))
    story.append(t_diag)
    story.append(Spacer(1, 10))

    # 4. Declaración de Voluntad y Riesgos
    beneficios_txt = pt_data.get('beneficios') or "Diagnóstico certero, estabilización materno-fetal, resolución oportuna del cuadro clínico gineco-obstétrico."
    alternativas_txt = pt_data.get('alternativas') or "Manejo médico expectante, tratamiento farmacológico alternativo o diferimiento según evolución clínica."

    legal_p1 = Paragraph(
        "Expreso mi libre voluntad para autorizar el procedimiento o intervención quirúrgica señalada en este documento después de haberme "
        "proporcionado la información completa sobre mi enfermedad y estado actual, la cual fue realizada en forma amplia, precisa y suficiente "
        "en un lenguaje claro y sencillo, informándome sobre los posibles <b>riesgos</b>, complicaciones y secuelas tales como: Dolor, sangrado o "
        "hemorragia, daño de órganos vecinos, daño vascular, infecciones nosocomiales, reacciones adversas a medicamentos o hemoderivados, "
        f"infección de herida quirúrgica, reacciones anafilácticas, choque anafiláctico; de igual forma los <b>beneficios</b> o efectos esperados de este "
        f"procedimiento son: <i>{beneficios_txt}</i>",
        style_body
    )
    story.append(legal_p1)
    story.append(Spacer(1, 8))

    legal_p2 = Paragraph(
        f"El médico me informó la existencia de procedimientos alternativos como: <i>{alternativas_txt}</i>, "
        "el derecho a cambiar mi decisión en cualquier momento y manifestarla antes del procedimiento o intervención. Con el propósito de que "
        "mi atención sea adecuada, me comprometo a proporcionar información completa y veraz, así como seguir las indicaciones médicas.<br/>"
        "Otorgo mi autorización al personal de salud para la atención de contingencias y urgencias derivadas del acto médico señalado atendiendo "
        "al principio de libertad prescriptiva.",
        style_body
    )
    story.append(legal_p2)
    story.append(Spacer(1, 12))

    # 5. Recuadro de Procedimiento o Intervención Proyectados
    proc_box_content = [
        [
            Paragraph(
                "<b>Procedimiento o intervención proyectados:</b><br/>"
                "Revisión ginecológica u obstétrica (tacto vaginal, tacto rectal, exploración mamaria), hospitalización, colocación de sondas y catéteres, "
                "aplicación de medicamentos, transfusiones sanguíneas, estudios de gabinete (ultrasonido pélvico y vaginal), tomografía abdominopélvica "
                "u otros de ser necesario.",
                style_box_proc
            )
        ]
    ]
    t_proc_box = Table(proc_box_content, colWidths=[content_w])
    t_proc_box.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOX', (0,0), (-1,-1), 0.8, PRIMARY_BLUE),
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
        ('PADDING', (0,0), (-1,-1), 6.0),
    ]))
    story.append(t_proc_box)
    story.append(Spacer(1, 14))

    # 6. Bloque de Firmas Dinámico (Solo incluye testigos si cuentan con firma/huella)
    pariente = (pt_data.get('pariente') or pt_data.get('representante_legal') or pt_data.get('declarante') or '').strip()
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
        nom_paciente_o_rep = pariente or pt_data.get('declarante') or 'Tutor / Representante Legal'
    else:
        parentesco_pac = 'Paciente'
        nom_paciente_o_rep = paciente_nombre

    testigo1 = pt_data.get('testigo1', '')
    testigo2 = pt_data.get('testigo2', '')

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

    parentesco_test1 = pt_data.get('parentesco_testigo1') or 'Testigo Presencial'
    parentesco_test2 = pt_data.get('parentesco_testigo2') or 'Testigo Presencial'
    paciente_clean = re.sub(r'\s*\([^)]*\)', '', str(nom_paciente_o_rep or '')).strip()
    testigo1_clean = re.sub(r'\s*\([^)]*\)', '', str(testigo1 or '')).strip()
    testigo2_clean = re.sub(r'\s*\([^)]*\)', '', str(testigo2 or '')).strip()

    sig_col_w = (content_w - 30.0) / 2.0  # ~245 pt

    patient_sig_text = f"<b>{paciente_clean}</b><br/><font size='6.2' color='#334155'><i><b>Parentesco: {parentesco_pac}</b></i></font>" if paciente_clean else "<b>Nombre completo y firma del paciente o tutor</b>"
    witness1_sig_text = f"<b>{testigo1_clean}</b><br/><font size='6.2' color='#334155'><i><b>Parentesco: {parentesco_test1}</b></i></font>" if testigo1_clean else "<b>Nombre completo del testigo 1</b>"
    witness2_sig_text = f"<b>{testigo2_clean}</b><br/><font size='6.2' color='#334155'><i><b>Parentesco: {parentesco_test2}</b></i></font>" if testigo2_clean else "<b>Nombre completo del testigo 2</b>"
    doctor_sig_text = f"<b>{medico}</b><br/><font size='6.2' color='#334155'><i><b>CÉD. PROF. {cedula}</b></i></font>" if cedula else f"<b>{medico}</b>"

    # Sello biométrico médico si existe
    if firma_data and firma_data.get('sello_digital'):
        sello_resumido = str(firma_data['sello_digital'])[:34] + "..."
        fecha_txt = firma_data.get('fecha_hora_firma') or firma_data.get('fecha_hora') or ''
        med_stamp_html = f"""
        <font size='5.5' color='#006633'><b>[✔ FIRMADO CON HUELLA BIOMÉTRICA]</b></font><br/>
        <font size='4.8' color='#004d26'><b>NOM-004-SSA3-2012 / NOM-024-SSA3-2012</b></font><br/>
        <font size='4.5' color='#444'><b>Sello:</b> <font face='Courier' size='4.2'>{sello_resumido}</font> | {fecha_txt}</font>
        """
        top_med_p = Paragraph(med_stamp_html, style_sig_stamp)
    else:
        top_med_p = Paragraph("&nbsp;", ParagraphStyle('SigSpace', fontName='Helvetica', fontSize=8.0, leading=12.0, textColor=colors.transparent, alignment=TA_CENTER))

    # Sello Biométrico Paciente / Representante
    if pt_data.get('firma_paciente_biometrica') or pt_data.get('sello_paciente') or (firma_data and firma_data.get('sello_paciente')):
        sello_pac_val = str(pt_data.get('sello_paciente') or (firma_data and firma_data.get('sello_paciente')) or 'BIO-HES:OK')[:24]
        pac_stamp_html = f"""
        <font size='5.2' color='#006633'><b>[✔ AUTORIZADO CON HUELLA BIOMÉTRICA]</b></font><br/>
        <font size='4.2' color='#444'><b>Validación Dactilar:</b> <font face='Courier' size='3.8'>{sello_pac_val}</font></font>
        """
        pac_sig_p = Paragraph(pac_stamp_html, style_sig_stamp)
    else:
        pac_sig_p = Paragraph("&nbsp;", ParagraphStyle('SigSpace', fontName='Helvetica', fontSize=8.0, leading=12.0, textColor=colors.transparent, alignment=TA_CENTER))

    # Sello Biométrico Testigo 1
    if has_t1:
        sello_test_val = str(pt_data.get('sello_testigo1') or (firma_data and firma_data.get('sello_testigo1')) or 'BIO-HES:OK')[:24]
        test_stamp_html = f"""
        <font size='5.2' color='#006633'><b>[✔ TESTIGO - HUELLA BIOMÉTRICA]</b></font><br/>
        <font size='4.2' color='#444'><b>Validación Dactilar:</b> <font face='Courier' size='3.8'>{sello_test_val}</font></font>
        """
        test_sig_p = Paragraph(test_stamp_html, style_sig_stamp)
    else:
        test_sig_p = Paragraph("&nbsp;", ParagraphStyle('SigSpace', fontName='Helvetica', fontSize=8.0, leading=12.0, textColor=colors.transparent, alignment=TA_CENTER))

    # Sello Biométrico Testigo 2
    if has_t2:
        sello_test2_val = str(pt_data.get('sello_testigo2') or (firma_data and firma_data.get('sello_testigo2')) or 'BIO-HES:OK')[:24]
        test2_stamp_html = f"""
        <font size='5.2' color='#006633'><b>[✔ TESTIGO - HUELLA BIOMÉTRICA]</b></font><br/>
        <font size='4.2' color='#444'><b>Validación Dactilar:</b> <font face='Courier' size='3.8'>{sello_test2_val}</font></font>
        """
        test2_sig_p = Paragraph(test2_stamp_html, style_sig_stamp)
    else:
        test2_sig_p = Paragraph("&nbsp;", ParagraphStyle('SigSpace', fontName='Helvetica', fontSize=8.0, leading=12.0, textColor=colors.transparent, alignment=TA_CENTER))

    sig_space_p = Paragraph("&nbsp;", ParagraphStyle('SigSpace', fontName='Helvetica', fontSize=8.0, leading=12.0, textColor=colors.transparent, alignment=TA_CENTER))

    # Rejilla de Firmas dinámica:
    if has_t1 and has_t2:
        story.append(Spacer(1, 12.0))
        sig_grid = [
            [pac_sig_p, '', top_med_p],
            [Paragraph(patient_sig_text, style_sig_name), '', Paragraph(doctor_sig_text, style_sig_name)],
            [test_sig_p, '', test2_sig_p],
            [Paragraph(witness1_sig_text, style_sig_name), '', Paragraph(witness2_sig_text, style_sig_name)]
        ]
        t_sigs = Table(sig_grid, colWidths=[sig_col_w, 30.0, sig_col_w])
        t_sigs.setStyle(TableStyle([
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
            ('BOTTOMPADDING', (0,1), (-1,1), 14.0),
            ('TOPPADDING', (0,2), (-1,2), 0),
            ('BOTTOMPADDING', (0,2), (-1,2), 0.5),
            ('TOPPADDING', (0,3), (-1,3), 2.5),
            ('BOTTOMPADDING', (0,3), (-1,3), 0),
        ]))
        story.append(KeepTogether(t_sigs))
    elif has_t1 or has_t2:
        story.append(Spacer(1, 12.0))
        active_test_p = test_sig_p if has_t1 else test2_sig_p
        active_test_txt = witness1_sig_text if has_t1 else witness2_sig_text
        t_top = Table([
            [pac_sig_p, '', active_test_p],
            [Paragraph(patient_sig_text, style_sig_name), '', Paragraph(active_test_txt, style_sig_name)]
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

        story.append(KeepTogether([t_top, Spacer(1, 12.0), t_bot]))
    else:
        # Solo Paciente y Médico lado a lado abajo
        story.append(Spacer(1, 30.0))
        sig_grid = [
            [pac_sig_p, '', top_med_p],
            [Paragraph(patient_sig_text, style_sig_name), '', Paragraph(doctor_sig_text, style_sig_name)]
        ]
        t_sigs = Table(sig_grid, colWidths=[sig_col_w, 30.0, sig_col_w])
        t_sigs.setStyle(TableStyle([
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
        story.append(KeepTogether(t_sigs))

    # Parámetros del membrete institucional unificado
    fecha_val = pt_data.get('fecha_atencion') or pt_data.get('fecha_ingreso', '')
    hora_val = pt_data.get('hora_atencion') or pt_data.get('hora_ingreso', '')

    expediente_val = expediente or pt_data.get('expediente') or pt_data.get('pt_num', '')
    pt_num_val = str(pt_data.get('pt_num', '') or expediente_val or '')

    doc_info = {
        'title_lines': [
            'CARTA DE CONSENTIMIENTO INFORMADO',
            'PARA REVISION GINECOLOGICA Y OBSTETRICA',
            'HOSPITALIZACIÓN. URGENCIAS'
        ],
        'code': 'HE-DIRMED-CONSUL-PLT-12',
        'draw_header_dates': False,
        'fecha_ingreso': fecha_val,
        'hora_ingreso': hora_val,
        'expediente': expediente_val,
        'folio': expediente_val,
        'pt_num': pt_num_val,
        'slot': pt_data.get('slot') or pt_data.get('mrnum') or 1,
        'draw_qr': True
    }

    def make_canvas(*args, **kwargs):
        c = CleanConsentCanvas(*args, doc_info=doc_info, fecha_ingreso=fecha_val, hora_ingreso=hora_val, **kwargs)
        return c

    doc.build(story, canvasmaker=make_canvas)
    return output_path

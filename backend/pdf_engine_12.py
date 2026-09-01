import os
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
    style_label = ParagraphStyle('MetaLabel', fontName='Helvetica-Bold', fontSize=7.2, leading=9.5, textColor=TEXT_MUTED)
    style_val = ParagraphStyle('MetaVal', fontName='Helvetica-Bold', fontSize=8.0, leading=10.5, textColor=TEXT_DARK)
    style_val_red = ParagraphStyle('MetaValRed', fontName='Helvetica-Bold', fontSize=8.0, leading=10.5, textColor=RED_ALERT)
    
    style_norm = ParagraphStyle('NormText', fontName='Helvetica-Oblique', fontSize=6.8, leading=9.0, textColor=colors.HexColor('#555555'), alignment=TA_JUSTIFY)
    style_body = ParagraphStyle('Body', fontName='Helvetica', fontSize=8.0, leading=12.0, textColor=TEXT_DARK, alignment=TA_JUSTIFY)
    style_body_bold = ParagraphStyle('BodyBold', fontName='Helvetica-Bold', fontSize=8.0, leading=12.0, textColor=TEXT_DARK, alignment=TA_JUSTIFY)
    
    style_box_proc = ParagraphStyle('BoxProc', fontName='Helvetica', fontSize=7.5, leading=11.0, textColor=TEXT_DARK, alignment=TA_LEFT)

    style_sig_name = ParagraphStyle('SigName', fontName='Helvetica-Bold', fontSize=8.0, leading=10.0, textColor=TEXT_DARK, alignment=TA_CENTER)
    style_sig_label = ParagraphStyle('SigLbl', fontName='Helvetica', fontSize=6.8, leading=8.5, textColor=TEXT_MUTED, alignment=TA_CENTER)
    style_sig_stamp = ParagraphStyle('SigStamp', fontName='Helvetica', fontSize=5.8, leading=7.2, textColor=colors.HexColor('#005522'), alignment=TA_CENTER)
    style_sig_blank = ParagraphStyle('SigBlank', fontName='Helvetica', fontSize=6.0, leading=7.0, textColor=colors.transparent, alignment=TA_CENTER)

    story = []

    # 1. Datos Generales del Paciente
    paciente_nombre = pt_data.get('paciente_nombre') or pt_data.get('nombre', '')
    expediente = pt_data.get('expediente') or pt_data.get('mrn', '')
    fecha_nac = pt_data.get('fecha_nacimiento') or pt_data.get('dob', '')
    edad_raw = str(pt_data.get('edad', '')).strip()
    edad_display = f"{edad_raw} años" if edad_raw and "año" not in edad_raw.lower() else (edad_raw or '____')
    medico = pt_data.get('medico_tratante') or pt_data.get('n_medico', 'DR. JOSE JOSE PRUEBA ENRIQUEZ')
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
    story.append(Spacer(1, 28))

    # 6. Bloque de 4 Firmas (2x2 Grid)
    pariente = pt_data.get('pariente') or pt_data.get('representante_legal', '')
    nom_paciente_o_rep = pariente if pariente else paciente_nombre
    testigo1 = pt_data.get('testigo1', '')
    testigo2 = pt_data.get('testigo2', '')

    sig_col_w = (content_w - 30.0) / 2.0  # ~245 pt

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
        top_med_p = Paragraph("&nbsp;", style_sig_blank)

    sig_grid = [
        # Fila 0: Nombres superiores
        [
            Paragraph(f"<b>{nom_paciente_o_rep}</b>" if nom_paciente_o_rep else "&nbsp;", style_sig_name),
            '',
            Paragraph(f"<b>{testigo1}</b>" if testigo1 else "&nbsp;", style_sig_name)
        ],
        # Fila 1: Etiquetas de cargo fila 1
        [
            Paragraph("Nombre completo y firma del paciente, familiar,<br/>tutor o persona legalmente responsable", style_sig_label),
            '',
            Paragraph("Nombre completo y firma del testigo 1", style_sig_label)
        ],
        # Fila 2: Nombres / Sellos fila 2
        [
            top_med_p if firma_data else Paragraph(f"<b>{medico}</b>" + (f"<br/><font size='6.2'>CÉD: {cedula}</font>" if cedula else ""), style_sig_name),
            '',
            Paragraph(f"<b>{testigo2}</b>" if testigo2 else "&nbsp;", style_sig_name)
        ],
        # Fila 3: Etiquetas de cargo fila 2
        [
            Paragraph("Nombre completo, cédulas y firma<br/>del médico tratante", style_sig_label),
            '',
            Paragraph("Nombre completo y firma del testigo 2", style_sig_label)
        ]
    ]

    t_sigs = Table(sig_grid, colWidths=[sig_col_w, 30.0, sig_col_w])
    t_sigs.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'BOTTOM'),
        ('VALIGN', (0,1), (-1,1), 'TOP'),
        ('VALIGN', (0,3), (-1,3), 'TOP'),
        
        # Línea de firma Paciente/Tutor y Testigo 1
        ('LINEABOVE', (0,1), (0,1), 0.8, PRIMARY_BLUE),
        ('LINEABOVE', (2,1), (2,1), 0.8, PRIMARY_BLUE),
        
        # Línea de firma Médico y Testigo 2
        ('LINEABOVE', (0,3), (0,3), 0.8, PRIMARY_BLUE),
        ('LINEABOVE', (2,3), (2,3), 0.8, PRIMARY_BLUE),
        
        ('TOPPADDING', (0,0), (-1,0), 0),
        ('BOTTOMPADDING', (0,0), (-1,0), 3.0),
        
        ('TOPPADDING', (0,1), (-1,1), 3.0),
        ('BOTTOMPADDING', (0,1), (-1,1), 26.0),
        
        ('TOPPADDING', (0,2), (-1,2), 0),
        ('BOTTOMPADDING', (0,2), (-1,2), 3.0),
        
        ('TOPPADDING', (0,3), (-1,3), 3.0),
        ('BOTTOMPADDING', (0,3), (-1,3), 0),
    ]))

    story.append(KeepTogether(t_sigs))

    # Parámetros del membrete institucional unificado
    fecha_val = pt_data.get('fecha_atencion') or pt_data.get('fecha_ingreso', '')
    hora_val = pt_data.get('hora_atencion') or pt_data.get('hora_ingreso', '')

    doc_info = {
        'title_lines': [
            'CARTA DE CONSENTIMIENTO INFORMADO',
            'PARA REVISION GINECOLOGICA Y OBSTETRICA',
            'HOSPITALIZACIÓN. URGENCIAS'
        ],
        'code': 'HE-DIRMED-CONSUL-PLT-12',
        'draw_header_dates': False,
        'fecha_ingreso': fecha_val,
        'hora_ingreso': hora_val
    }

    def make_canvas(*args, **kwargs):
        c = CleanConsentCanvas(*args, doc_info=doc_info, fecha_ingreso=fecha_val, hora_ingreso=hora_val, **kwargs)
        return c

    doc.build(story, canvasmaker=make_canvas)
    return output_path

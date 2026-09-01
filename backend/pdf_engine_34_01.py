import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, TableStyle, KeepTogether, PageBreak
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

BLUE_BAR_COLOR = colors.HexColor('#005691')
MIDNIGHT_BLUE = colors.HexColor('#191970')

def generate_consentimiento_34_01(pt_data: dict, output_path: str = None, firma_data: dict = None) -> str:
    if output_path and os.path.dirname(output_path):
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

    content_x = FRAME_X + 16.0
    content_w = FRAME_W - 32.0 - 16.0 # ~521.76 pt

    frame_bottom = FRAME_Y + 41.0
    frame_top = (FRAME_Y + FRAME_H) - 64.0
    frame_h = frame_top - frame_bottom

    frame_p1 = Frame(content_x, frame_bottom, content_w, frame_h, id='p1_frame',
                     leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)

    frame_later = Frame(content_x, frame_bottom, content_w, frame_h, id='later_frame',
                        leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)

    template_p1 = PageTemplate(id='FirstPage', frames=frame_p1)
    template_later = PageTemplate(id='LaterPages', frames=frame_later)

    doc = BaseDocTemplate(
        output_path,
        pagesize=letter,
        pageTemplates=[template_p1, template_later]
    )

    # Estilos tipográficos institucionales
    style_label = ParagraphStyle('MetaLabel', fontName='Helvetica-Bold', fontSize=6.8, leading=8.4, textColor=TEXT_MUTED)
    style_val = ParagraphStyle('MetaVal', fontName='Helvetica-Bold', fontSize=7.2, leading=8.8, textColor=TEXT_DARK)
    style_val_red = ParagraphStyle('MetaValRed', fontName='Helvetica-Bold', fontSize=7.2, leading=8.8, textColor=RED_ALERT)
    
    style_section = ParagraphStyle('SecHeader', fontName='Helvetica-Bold', fontSize=7.8, leading=9.8, textColor=PRIMARY_BLUE)
    style_body = ParagraphStyle('Body', fontName='Helvetica', fontSize=7.0, leading=9.0, textColor=TEXT_DARK, alignment=TA_JUSTIFY)
    style_body_bold = ParagraphStyle('BodyBold', fontName='Helvetica-Bold', fontSize=7.0, leading=9.0, textColor=TEXT_DARK, alignment=TA_JUSTIFY)
    
    style_tbl_hdr = ParagraphStyle('TblHdr', fontName='Helvetica-Bold', fontSize=6.8, leading=8.2, textColor=colors.white, alignment=TA_CENTER)
    style_tbl_cell = ParagraphStyle('TblCell', fontName='Helvetica', fontSize=6.5, leading=8.0, textColor=TEXT_DARK, alignment=TA_CENTER)
    style_tbl_cell_left = ParagraphStyle('TblCellL', fontName='Helvetica', fontSize=6.5, leading=8.0, textColor=TEXT_DARK, alignment=TA_LEFT)

    story = []

    # ==================== PÁGINA 1: CONSENTIMIENTO INFORMADO ====================
    # 1. Tabla de Datos Generales del Paciente
    paciente_nombre = pt_data.get('paciente_nombre') or pt_data.get('nombre', '')
    expediente = pt_data.get('expediente') or pt_data.get('mrn', '')
    fecha_nac = pt_data.get('fecha_nacimiento') or pt_data.get('dob', '')
    edad_raw = str(pt_data.get('edad', '')).strip()
    edad = f"{edad_raw} años" if edad_raw and "año" not in edad_raw.lower() else (edad_raw or '')
    sexo = pt_data.get('sexo', '')
    grupo_rh = pt_data.get('grupo_rh') or pt_data.get('gruporh', '')
    alergias = pt_data.get('alergias', 'NEGADAS')
    tipo_int = pt_data.get('tipo_interrogatorio') or pt_data.get('inttyp', 'DIRECTO')
    medico = pt_data.get('medico_tratante') or pt_data.get('nombre_medico_mi', 'DR. JOSE JOSE PRUEBA ENRIQUEZ')
    cedula = pt_data.get('cedula', '')
    fecha_atencion = pt_data.get('fecha_atencion', '')

    pt_info_data = [
        [
            Paragraph("NOMBRE DEL PACIENTE:", style_label),
            Paragraph(f"<b>{paciente_nombre}</b>", style_val),
            Paragraph("FECHA DE NAC:", style_label),
            Paragraph(fecha_nac, style_val),
            Paragraph("EDAD:", style_label),
            Paragraph(edad, style_val),
            Paragraph("SEXO:", style_label),
            Paragraph(sexo, style_val)
        ],
        [
            Paragraph("EXPEDIENTE:", style_label),
            Paragraph(f"<b>{expediente}</b>", style_val),
            Paragraph("GRUPO Y RH:", style_label),
            Paragraph(grupo_rh, style_val),
            Paragraph("ALERGIAS:", style_label),
            Paragraph(alergias, style_val_red),
            Paragraph("INTERROGATORIO:", style_label),
            Paragraph(tipo_int, style_val)
        ],
        [
            Paragraph("MÉDICO TRATANTE:", style_label),
            Paragraph(f"<b>{medico}</b>", style_val),
            Paragraph("CÉDULA:", style_label),
            Paragraph(cedula, style_val),
            Paragraph("FECHA ATENCIÓN:", style_label),
            Paragraph(fecha_atencion, style_val),
            '', ''
        ]
    ]

    t_info = Table(pt_info_data, colWidths=[80, 140, 60, 60, 38, 40, 34, content_w - (80 + 140 + 60 + 60 + 38 + 40 + 34)])
    t_info.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('SPAN', (1,2), (3,2)),
        ('SPAN', (5,2), (7,2)),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_GREY),
        ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#F8FAFC')),
        ('BACKGROUND', (2,0), (2,1), colors.HexColor('#F8FAFC')),
        ('BACKGROUND', (4,0), (4,1), colors.HexColor('#F8FAFC')),
        ('BACKGROUND', (6,0), (6,1), colors.HexColor('#F8FAFC')),
        ('BACKGROUND', (4,2), (4,2), colors.HexColor('#F8FAFC')),
        ('PADDING', (0,0), (-1,-1), 3.0),
    ]))
    story.append(t_info)
    story.append(Spacer(1, 8))

    # 2. Texto Legal Normado de Consentimiento
    pariente = pt_data.get('pariente') or pt_data.get('representante_legal', '')
    yo_paciente = paciente_nombre if not pariente else f"{paciente_nombre} (por conducto de {pariente})"

    legal_p1 = Paragraph(
        f"Yo <b>{paciente_nombre}</b> como Paciente y/o <b>{pariente or '___________________________________'}</b> "
        f"en mi calidad de Representante Legal del Paciente, acepto voluntariamente y autorizo al <b>Dr. {medico}</b> "
        "para que practique en la persona del denominado paciente el estudio de <b>Mesa Inclinada (Tilt Test)</b>. "
        "Es un estudio en el cual se realiza la evaluación de disautonomía y síncope, con un protocolo de dos fases: "
        "una pasiva con una inclinación a 70 grados y una activa con adición de Dinitrato de Isosorbide sublingual. "
        "Ambas fases diseñadas para documentar una respuesta hemodinámica que puede ser vasopresora (disminución de presión arterial) "
        "o cardioinhibitoria (disminución de la frecuencia cardíaca o asistolia) que sugieran disautonomía.",
        style_body
    )

    legal_p2 = Paragraph(
        "<b>Riesgos y Posibles Complicaciones:</b> Las complicaciones pese a ser de baja probabilidad pueden aparecer. "
        "Las más frecuentes son arritmias, infarto del miocardio, eventos vasculares cerebrales, paradas cardiorrespiratorias. "
        "Se pueden presentar reacciones adversas como dolor de cabeza, mareo, fatiga, náuseas, pérdida del estado de alerta. "
        "El estudio se realiza bajo monitorización continua y con el equipo y medicamentos necesarios para tratamiento inmediato en caso de presentar complicaciones.",
        style_body
    )

    legal_p3 = Paragraph(
        "Acepto y autorizo el procedimiento. Mis dudas fueron aclaradas proporcionándome el tiempo suficiente para ello. "
        "Se me explicó que existen otros procedimientos alternativos. Sin embargo, me he decidido por este procedimiento, por lo que estoy autorizando. "
        "Así también que se me ha explicado y he entendido el tipo y contenido del presente documento. "
        "En este acto autorizo al personal de salud del Hospital Escandón para que realice las atenciones en caso de contingencia y urgencias derivadas del procedimiento que se me va a realizar. "
        "Estoy enterado y acepto que requeriré vigilancia y control después del procedimiento, hasta mi total recuperación.",
        style_body
    )

    t_legal = Table([[legal_p1], [legal_p2], [legal_p3]], colWidths=[content_w])
    t_legal.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 0.75, BORDER_GREY),
        ('BACKGROUND', (0,0), (-1,-1), colors.white),
        ('TOPPADDING', (0,0), (-1,-1), 3.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3.5),
        ('LEFTPADDING', (0,0), (-1,-1), 5.0),
        ('RIGHTPADDING', (0,0), (-1,-1), 5.0),
    ]))
    story.append(t_legal)
    story.append(Spacer(1, 14))

    # 3. Bloque de Firmas Página 1
    sig_label = ParagraphStyle('SigLabel', fontName='Helvetica-Oblique', fontSize=6.5, leading=8.0, textColor=TEXT_MUTED, alignment=TA_CENTER)
    sig_name = ParagraphStyle('SigName', fontName='Helvetica-Bold', fontSize=7.8, leading=9.5, alignment=TA_CENTER, textColor=TEXT_DARK)
    sig_stamp = ParagraphStyle('SigStamp', fontName='Helvetica', fontSize=5.2, leading=6.5, alignment=TA_CENTER)
    sig_blank = ParagraphStyle('SigBlank', fontName='Helvetica', fontSize=24, leading=26)

    testigo1_nom = pt_data.get('testigo1', '')
    testigo2_nom = pt_data.get('testigo2', '')

    sig_col_w = (content_w - 40.0) / 2.0

    # Firma biométrica del médico si está activa
    if firma_data and (firma_data.get('sello_digital') or firma_data.get('hash_sha256')):
        sello_raw = str(firma_data.get('sello_digital') or firma_data.get('hash_sha256') or '')
        sello_resumido = (sello_raw[:28] + '...') if len(sello_raw) > 28 else sello_raw
        fecha_txt = firma_data.get('fecha_hora_firma') or firma_data.get('fecha_hora') or ''
        stamp_html = f"""
        <font size='5.8' color='#006633'><b>[✔ FIRMADO BIOMÉTRICAMENTE CON HUELLA]</b></font><br/>
        <font size='5' color='#004d26'><b>NOM-004-SSA3-2012 / NOM-024-SSA3-2012</b></font><br/>
        <font size='4.6' color='#444'><b>Sello:</b> <font face='Courier' size='4.4'>{sello_resumido}</font> | {fecha_txt}</font>
        """
        top_med_p = Paragraph(stamp_html, sig_stamp)
    else:
        top_med_p = Paragraph("&nbsp;", sig_blank)

    has_tutor = bool(pariente) or (not pt_data.get('paciente_capaz', True))

    # Fila 1: Paciente y Representante Legal
    sig_row1 = [
        [
            Paragraph("&nbsp;", sig_blank), '',
            Paragraph("&nbsp;", sig_blank)
        ],
        [
            Paragraph(f"<b>{paciente_nombre}</b>", sig_name), '',
            Paragraph(f"<b>{pariente}</b>" if has_tutor else "&nbsp;", sig_name)
        ],
        [
            Paragraph("Nombre completo y firma del paciente", sig_label), '',
            Paragraph("Nombre completo y firma del representante legal del paciente" if has_tutor else "&nbsp;", sig_label)
        ]
    ]
    t_sig1_styles = [
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,0), 'BOTTOM'),
        ('VALIGN', (0,1), (-1,1), 'BOTTOM'),
        ('VALIGN', (0,2), (-1,2), 'TOP'),
        ('LINEABOVE', (0,1), (0,1), 0.8, PRIMARY_BLUE),
        ('BOTTOMPADDING', (0,0), (-1,0), 0),
        ('TOPPADDING', (0,1), (-1,1), 2),
        ('BOTTOMPADDING', (0,1), (-1,1), 3),
        ('TOPPADDING', (0,2), (-1,2), 3),
        ('BOTTOMPADDING', (0,2), (-1,2), 0),
    ]
    if has_tutor:
        t_sig1_styles.append(('LINEABOVE', (2,1), (2,1), 0.8, PRIMARY_BLUE))

    t_sig1 = Table(sig_row1, colWidths=[sig_col_w, 40, sig_col_w])
    t_sig1.setStyle(TableStyle(t_sig1_styles))
    story.append(t_sig1)
    story.append(Spacer(1, 14))

    # Fila 2: Testigos 1 y 2
    sig_row2 = [
        [
            Paragraph("&nbsp;", sig_blank), '',
            Paragraph("&nbsp;", sig_blank)
        ],
        [
            Paragraph(f"<b>{testigo1_nom}</b>" if testigo1_nom else "&nbsp;", sig_name), '',
            Paragraph(f"<b>{testigo2_nom}</b>" if testigo2_nom else "&nbsp;", sig_name)
        ],
        [
            Paragraph("Nombre completo y firma de testigo 1", sig_label), '',
            Paragraph("Nombre completo y firma de testigo 2", sig_label)
        ]
    ]
    t_sig2 = Table(sig_row2, colWidths=[sig_col_w, 40, sig_col_w])
    t_sig2.setStyle(TableStyle([
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
    story.append(t_sig2)
    story.append(Spacer(1, 14))

    # Fila 3: Médico Tratante
    med_ced_txt = f"Céd. Prof. {cedula}" if cedula else ""
    sig_row3 = [
        [top_med_p],
        [Paragraph(f"<b>{medico}</b><br/><font size='6.8' color='#444'>{med_ced_txt}</font>", sig_name)],
        [Paragraph("DECLARO BAJO PROTESTA DE DECIR VERDAD, QUE HE PROPORCIONADO TODA LA INFORMACIÓN SOBRE EL PROCEDIMIENTO A REALIZAR EN EL PACIENTE.<br/><b>Nombre, firma y Cédula Profesional del Médico</b>", sig_label)]
    ]
    t_sig3 = Table(sig_row3, colWidths=[240])
    t_sig3.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,0), 'BOTTOM'),
        ('VALIGN', (0,1), (-1,1), 'BOTTOM'),
        ('VALIGN', (0,2), (-1,2), 'TOP'),
        ('LINEABOVE', (0,1), (0,1), 0.8, PRIMARY_BLUE),
        ('BOTTOMPADDING', (0,0), (-1,0), 0),
        ('TOPPADDING', (0,1), (-1,1), 2),
        ('BOTTOMPADDING', (0,1), (-1,1), 3),
        ('TOPPADDING', (0,2), (-1,2), 3),
        ('BOTTOMPADDING', (0,2), (-1,2), 0),
    ]))
    story.append(KeepTogether([Table([[t_sig3]], colWidths=[content_w], style=[('ALIGN', (0,0), (-1,-1), 'CENTER')])]))

    # ==================== PÁGINA 2: REPORTE CLÍNICO TILT TEST ====================
    story.append(PageBreak())

    # Barra de Signos Vitales
    ta_val = pt_data.get('ta', '')
    fc_meta = pt_data.get('fc_meta', '')
    f_resp = pt_data.get('f_resp', '')
    temperatura = pt_data.get('temperatura', '')
    peso = pt_data.get('peso', '')
    talla = pt_data.get('talla', '')

    vitals_data = [
        [
            Paragraph("TA:", style_label), Paragraph(ta_val, style_val),
            Paragraph("FC META:", style_label), Paragraph(fc_meta, style_val),
            Paragraph("FR:", style_label), Paragraph(f_resp, style_val),
            Paragraph("T:", style_label), Paragraph(temperatura, style_val),
            Paragraph("PESO:", style_label), Paragraph(f"{peso} kg" if peso else "", style_val),
            Paragraph("TALLA:", style_label), Paragraph(f"{talla} cm" if talla else "", style_val),
        ]
    ]
    t_vitals = Table(vitals_data, colWidths=[28, 60, 50, 50, 25, 45, 20, 45, 40, 50, 40, content_w - (28+60+50+50+25+45+20+45+40+50+40)])
    t_vitals.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_GREY),
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('PADDING', (0,0), (-1,-1), 2.5),
    ]))
    story.append(t_vitals)
    story.append(Spacer(1, 4))

    # Tabla del Protocolo INICICH de 20 Fases / Tiempos
    protocol_intervals = [
        ("Basal", "ta_basal", "fc_basal", "obs_basal"),
        ("Inicio fase pasiva 70°", "ta_p_inicio", "fc_p_inicio", "obs_p_inicio"),
        ("2' 70°", "ta_p_2", "fc_p_2", "obs_p_2"),
        ("4' 70°", "ta_p_4", "fc_p_4", "obs_p_4"),
        ("6' 70°", "ta_p_6", "fc_p_6", "obs_p_6"),
        ("8' 70°", "ta_p_8", "fc_p_8", "obs_p_8"),
        ("10' 70°", "ta_p_10", "fc_p_10", "obs_p_10"),
        ("12' 70°", "ta_p_12", "fc_p_12", "obs_p_12"),
        ("14' 70°", "ta_p_14", "fc_p_14", "obs_p_14"),
        ("16' 70°", "ta_p_16", "fc_p_16", "obs_p_16"),
        ("18' 70°", "ta_p_18", "fc_p_18", "obs_p_18"),
        ("20' 70°", "ta_p_20", "fc_p_20", "obs_p_20"),
        ("Inicio fase activa 70° Isosorbide 5mg", "ta_a_inicio", "fc_a_inicio", "obs_a_inicio"),
        ("2' 70°", "ta_a_2", "fc_a_2", "obs_a_2"),
        ("4' 70°", "ta_a_4", "fc_a_4", "obs_a_4"),
        ("6' 70°", "ta_a_6", "fc_a_6", "obs_a_6"),
        ("8' 70°", "ta_a_8", "fc_a_8", "obs_a_8"),
        ("10' 70°", "ta_a_10", "fc_a_10", "obs_a_10"),
        ("12' 70°", "ta_a_12", "fc_a_12", "obs_a_12"),
        ("14' 70°", "ta_a_14", "fc_a_14", "obs_a_14"),
        ("Final 0°", "ta_final", "fc_final", "obs_final"),
    ]

    proto_table_data = [
        [
            Paragraph("<b>Tiempo / Inclinación</b>", style_tbl_hdr),
            Paragraph("<b>Presión Arterial</b>", style_tbl_hdr),
            Paragraph("<b>FC</b>", style_tbl_hdr),
            Paragraph("<b>Observaciones</b>", style_tbl_hdr)
        ]
    ]

    for label, ta_key, fc_key, obs_key in protocol_intervals:
        ta_item = str(pt_data.get(ta_key, ''))
        fc_item = str(pt_data.get(fc_key, ''))
        obs_item = str(pt_data.get(obs_key, ''))
        proto_table_data.append([
            Paragraph(label, style_tbl_cell_left),
            Paragraph(ta_item, style_tbl_cell),
            Paragraph(fc_item, style_tbl_cell),
            Paragraph(obs_item, style_tbl_cell_left),
        ])

    w_t = 190.0
    w_ta = 75.0
    w_fc = 45.0
    w_obs = content_w - (w_t + w_ta + w_fc)

    t_proto = Table(proto_table_data, colWidths=[w_t, w_ta, w_fc, w_obs])
    t_proto.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.4, BORDER_GREY),
        ('BACKGROUND', (0,0), (-1,0), PRIMARY_BLUE),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 1.2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 1.2),
        ('LEFTPADDING', (0,0), (-1,-1), 3.0),
        ('RIGHTPADDING', (0,0), (-1,-1), 3.0),
    ]))
    story.append(t_proto)
    story.append(Spacer(1, 6))

    # Narrativa Clínica del Estudio
    irm_txt = pt_data.get('irm') or "De acuerdo a sus indicaciones se realizó estudio de Mesa de inclinación en protocolo INICICH en dos fases"
    fbpr_txt = pt_data.get('fbpr') or "asintomática"
    fpr_txt = pt_data.get('fpr') or "mareo y náuseas leves"

    narrative_p1 = Paragraph(
        f"{irm_txt} a su paciente <b>{paciente_nombre}</b>. Se inició monitorización electrocardiográfica y se mantuvo canalización de vena periférica, con solución Hartmann.",
        style_body
    )
    narrative_p2 = Paragraph(
        f"• Durante la fase basal la paciente refirió: <b>{fbpr_txt}</b>, manteniéndose signos vitales estables.<br/>"
        f"• Durante la fase pasiva de 20 minutos refirió: <b>{fpr_txt}</b>. Se mantuvieron signos vitales estables.<br/>"
        "• En fase activa de 15 minutos, se administró Isosorbide 5 mg SL, se mantuvieron signos vitales estables. Se retorna a decúbito supino y se dio por terminado el estudio.",
        style_body
    )

    story.append(narrative_p1)
    story.append(Spacer(1, 2))
    story.append(narrative_p2)
    story.append(Spacer(1, 4))

    # Conclusiones
    c1 = pt_data.get('conclusiones') or pt_data.get('conclusion_1', '')
    c2 = pt_data.get('conclusiones_2') or pt_data.get('conclusion_2', '')
    c3 = pt_data.get('conclusiones_3') or pt_data.get('conclusion_3', '')

    conc_text = "<b>Conclusiones:</b><br/>"
    if c1:
        conc_text += f"<b>1:</b> {c1}<br/>"
    if c2:
        conc_text += f"<b>2:</b> {c2}<br/>"
    if c3:
        conc_text += f"<b>3:</b> {c3}"
    if not (c1 or c2 or c3):
        conc_text += "1: Estudio de mesa inclinada con respuesta hemodinámica normal.<br/>2: Sin evidencia de síncope vasovagal ni disautonomía durante el protocolo."

    story.append(Paragraph(conc_text, style_body))
    story.append(Spacer(1, 8))

    # Firma de Página 2
    sig_med_p2 = [
        [top_med_p],
        [Paragraph(f"<b>{medico}</b><br/><font size='6.8' color='#444'>{med_ced_txt}</font>", sig_name)],
        [Paragraph("Nombre, firma, Cédula Profesional y de Especialidad del Médico", sig_label)]
    ]
    t_med_p2 = Table(sig_med_p2, colWidths=[240])
    t_med_p2.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LINEABOVE', (0,1), (0,1), 0.8, PRIMARY_BLUE),
        ('BOTTOMPADDING', (0,0), (-1,0), 1),
        ('TOPPADDING', (0,1), (-1,1), 2),
        ('BOTTOMPADDING', (0,1), (-1,1), 1),
        ('TOPPADDING', (0,2), (-1,2), 1),
        ('BOTTOMPADDING', (0,2), (-1,2), 1),
    ]))
    story.append(KeepTogether([Table([[t_med_p2]], colWidths=[content_w], style=[('ALIGN', (0,0), (-1,-1), 'CENTER')])]))

    # Document Info para el Canvas
    doc_info = {
        'title': 'CONSENTIMIENTO INFORMADO PARA ESTUDIO DE MESA INCLINADA',
        'title_lines': [
            'CONSENTIMIENTO INFORMADO PARA',
            'ESTUDIO DE MESA INCLINADA'
        ],
        'code': 'HE-DIRMED-CONSUL-PLT-34',
        'draw_header_dates': False
    }

    def make_canvas(*args, **kwargs):
        c = CleanConsentCanvas(*args, doc_info=doc_info, **kwargs)
        c.fecha_ingreso = pt_data.get('fecha_ingreso', '')
        c.hora_ingreso = pt_data.get('hora_ingreso', '')
        return c

    doc.build(story, canvasmaker=make_canvas)
    return output_path

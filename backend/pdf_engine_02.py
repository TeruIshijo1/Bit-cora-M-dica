import os
import re
import datetime
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
        TEXT_MUTED, TEXT_DARK, RED_ALERT, PRIMARY_BLUE, DARK_BLUE, BORDER_GREY,
        letterhead_content_width
    )
except ModuleNotFoundError:
    from pdf_engine_v2 import (
        RDLCCanvas, CleanConsentCanvas, FRAME_X, FRAME_Y, FRAME_W, FRAME_H, 
        TEXT_MUTED, TEXT_DARK, RED_ALERT, PRIMARY_BLUE, DARK_BLUE, BORDER_GREY,
        letterhead_content_width
    )

BLUE_BANNER_BG = colors.HexColor('#EBF3FA')
BLUE_BANNER_BORDER = colors.HexColor('#B8D5E5')

MESES = [
    'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
    'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'
]

def generate_consentimiento_02(pt_data: dict, output_path: str = None, firma_data: dict = None) -> str:
    """
    Genera el PDF oficial para el Formato 02 (HE-DIRMED-CONSUL-PLT-02).
    Estructura unificada de 1 página con aprovechamiento vertical total y tipografía grande:
      1. Ficha del Paciente y Declaración Inicial.
      2. Diagnósticos (Preoperatorio, confirmación, beneficios).
      3. Tratamientos (Médicos, Quirúrgicos, Endoscópicos, Rehabilitación).
      4. Alternativas, Anestesia, Riesgos y Advertencia Legal.
      5. Bloque de Decisión Exclusiva (Autorizo o No Autorizo):
         - Si AUTORIZA: Texto de autorización + Firmas en 2 columnas (Médico al lado de Paciente, Testigo 1 al lado de Testigo 2).
         - Si NO AUTORIZA: Motivo de revocación/negativa + Firmas en 2 columnas (Paciente al lado de Médico, Testigo 1 al lado de Testigo 2).
    """
    if output_path and os.path.dirname(output_path):
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Margen horizontal estricto respetando la barra lateral
    content_x = FRAME_X + 14.0
    content_w = letterhead_content_width(content_x)

    frame_bottom = FRAME_Y + 39.0
    frame_top = (FRAME_Y + FRAME_H) - 59.5
    frame_h = frame_top - frame_bottom # ~624.34 pt

    frame_p1 = Frame(content_x, frame_bottom, content_w, frame_h, id='p1_frame',
                     leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)

    template_p1 = PageTemplate(id='FirstPage', frames=frame_p1)

    doc = BaseDocTemplate(
        output_path,
        pagesize=letter,
        pageTemplates=[template_p1]
    )

    # Tipografía grande, cómoda y elegante para llenar verticalmente la hoja completa
    style_label = ParagraphStyle('MetaLabel', fontName='Helvetica-Bold', fontSize=7.6, leading=9.6, textColor=PRIMARY_BLUE)
    style_val = ParagraphStyle('MetaVal', fontName='Helvetica', fontSize=7.6, leading=9.6, textColor=TEXT_DARK)
    
    style_sec_title = ParagraphStyle('SecTitle', fontName='Helvetica-BoldOblique', fontSize=8.6, leading=10.5, textColor=PRIMARY_BLUE, alignment=TA_CENTER)
    style_body = ParagraphStyle('Body', fontName='Helvetica', fontSize=7.5, leading=9.8, textColor=TEXT_DARK, alignment=TA_JUSTIFY)
    style_body_bold = ParagraphStyle('BodyBold', fontName='Helvetica-Bold', fontSize=7.5, leading=9.8, textColor=TEXT_DARK, alignment=TA_JUSTIFY)
    
    style_item_label = ParagraphStyle('ItemLbl', fontName='Helvetica-Bold', fontSize=7.4, leading=9.5, textColor=PRIMARY_BLUE)
    style_item_text = ParagraphStyle('ItemTxt', fontName='Helvetica', fontSize=7.4, leading=9.5, textColor=TEXT_DARK)

    style_sig_title = ParagraphStyle('SigTitle', fontName='Helvetica-Bold', fontSize=7.2, leading=9.0, textColor=TEXT_DARK)
    style_sig_line = ParagraphStyle('SigLine', fontName='Helvetica', fontSize=6.4, leading=8.0, textColor=TEXT_DARK)
    style_sig_stamp = ParagraphStyle('SigStamp', fontName='Helvetica', fontSize=5.0, leading=6.0, textColor=colors.HexColor('#006633'), alignment=TA_CENTER)

    story = []

    paciente_nombre = (pt_data.get('paciente_nombre') or pt_data.get('nombre') or '').strip()
    expediente = (pt_data.get('expediente') or pt_data.get('mrn') or '').strip()
    fecha_nac = (pt_data.get('fecha_nacimiento') or pt_data.get('dob') or '').strip()
    edad_raw = str(pt_data.get('edad') or '').strip()
    edad = f"{edad_raw} años" if edad_raw and "año" not in edad_raw.lower() else (edad_raw or '')
    medico = (pt_data.get('medico_tratante') or pt_data.get('n_medico') or '').strip()
    cedula = (pt_data.get('cedula') or pt_data.get('cedula_profesional') or '').strip()
    fecha_atencion = pt_data.get('fecha_atencion') or datetime.datetime.now().strftime("%d/%m/%Y")
    hora_atencion = pt_data.get('hora_atencion') or datetime.datetime.now().strftime("%H:%M")

    medico_clean = re.sub(r'^(dr\(a\)\.?|dr\.|dra\.|dr|dra)\s*', '', medico, flags=re.IGNORECASE).strip()
    med_display = f"Dr(a). {medico_clean}" if medico_clean else "Dr(a). Médico Tratante"
    no_autorizo = bool(pt_data.get('no_autorizo') or pt_data.get('tipo') == 'no_autorizo')

    diagnostico = (pt_data.get('diagnostico') or 'DIAGNÓSTICO MÉDICO / QUIRÚRGICO EN ESTUDIO').strip()
    proced_confirmar = (pt_data.get('proced_para_confirmar_diagnost') or pt_data.get('proced_confirmar') or 'Estudios preoperatorios, valoración de riesgo quirúrgico y protocolo anestésico').strip()
    beneficio = (pt_data.get('beneficio_de_dicho_procedimiento') or pt_data.get('beneficios') or 'Resolución terapéutica de la patología de base, preservación funcional y mejora en la calidad de vida').strip()
    trat_medicos = (pt_data.get('tratamientos_medicos') or 'Manejo farmacológico perioperatorio, analgesia y antibioticoterapia profiláctica').strip()
    trat_quirurgicos = (pt_data.get('tratamientos_quirurgicos') or 'Intervención quirúrgica protocolizada bajo técnica aséptica').strip()
    trat_endoscopicos = (pt_data.get('tratamientos_endoscopicos') or 'No requeridos en este tiempo quirúrgico / según hallazgos transoperatorios').strip()
    trat_rehab = (pt_data.get('tratamientos_de_rehabilitacion') or 'Deambulación temprana asistida y cuidados postoperatorios de herida quirúrgica').strip()
    alternativas = (pt_data.get('alternativas') or 'Tratamiento médico expectante o diferimiento según evolución clínica').strip()
    anestesia_val = str(pt_data.get('anestesia') or 'SI').strip().upper()
    tipo_anestesia = (pt_data.get('tipo_de_anestesia') or pt_data.get('tipo_anestesia') or 'General balanceada e intubacion orotraqueal').strip()
    principales_riesgos = (pt_data.get('principales_riesgos') or 'Hemorragia, infección de sitio quirúrgico, lesión de órganos o estructuras vecinas, reacciones adversas a medicamentos o anestésicos, eventos tromboembólicos').strip()
    
    testigo1 = (pt_data.get('testigo1') or pt_data.get('testigo_1') or '').strip()
    testigo2 = (pt_data.get('testigo2') or pt_data.get('testigo_2') or '').strip()
    domicilio_testigo1 = (pt_data.get('domicilio_testigo1') or pt_data.get('domicilio_testigo') or 'Conocido en exp. clínico').strip()
    identificacion_testigo1 = (pt_data.get('identificacion_testigo1') or pt_data.get('identificacion_testigo') or 'INE').strip()
    parentesco_testigo1 = (pt_data.get('parentesco_testigo1') or pt_data.get('parentesco_testigo') or 'Familiar').strip()
    
    domicilio_testigo2 = (pt_data.get('domicilio_testigo2') or 'Conocido en exp. clínico').strip()
    identificacion_testigo2 = (pt_data.get('identificacion_testigo2') or 'INE').strip()
    parentesco_testigo2 = (pt_data.get('parentesco_testigo2') or 'Testigo').strip()

    paciente_capaz = pt_data.get('paciente_capaz', True)
    if isinstance(paciente_capaz, str):
        paciente_capaz = paciente_capaz.lower() in ('true', '1', 'si', 'yes')
    elif isinstance(paciente_capaz, (int, float)):
        paciente_capaz = bool(paciente_capaz)
    pariente = (pt_data.get('pariente') or pt_data.get('representante_legal') or pt_data.get('declarante') or '').strip()
    if not paciente_capaz:
        parentesco_pac = (pt_data.get('parentesco') or pt_data.get('parentesco_declarante') or pt_data.get('parentesco_paciente') or 'Tutor / Representante Legal').strip()
        if parentesco_pac.upper() in ('PACIENTE', 'TITULAR', 'DIRECTO'):
            parentesco_pac = 'Tutor / Representante Legal'
        nom_firmante = pariente or pt_data.get('declarante') or 'TUTOR / REPRESENTANTE LEGAL'
    else:
        parentesco_pac = 'Paciente'
        nom_firmante = paciente_nombre
    domicilio_pac = pt_data.get('domicilio_paciente') or pt_data.get('domicilio_declarante') or 'Conocido en exp. clínico'
    id_pac = pt_data.get('identificacion_paciente') or pt_data.get('identificacion_declarante') or 'INE'

    doc_info = {
        'title_lines': [
            "DISENTIMIENTO / NEGATIVA INFORMADA" if no_autorizo else "CONSENTIMIENTO INFORMADO",
            "AUTORIZACIÓN PARA FINES DE",
            "DIAGNÓSTICO Y/O TRATAMIENTO",
            "MÉDICO/ QUIRÚRGICO"
        ],
        'code': 'HE-DIRMED-CONSUL-PLT-02',
        'expediente': expediente,
        'folio': expediente or pt_data.get('pt_num', ''),
        'pt_num': str(pt_data.get('pt_num') or expediente or ''),
        'slot': pt_data.get('slot') or pt_data.get('mrnum') or 1,
        'qr_data': pt_data.get('qr_data') or pt_data.get('qr_url'),
        'draw_qr': True
    }

    # 1. Tabla de Datos Generales
    pt_info_data = [
        [
            Paragraph("NOMBRE DEL PACIENTE:", style_label),
            Paragraph(f"<b>{paciente_nombre}</b>", style_val),
            Paragraph("FECHA DE NAC:", style_label),
            Paragraph(fecha_nac, style_val),
            Paragraph("EDAD:", style_label),
            Paragraph(edad, style_val)
        ],
        [
            Paragraph("EXPEDIENTE:", style_label),
            Paragraph(f"<b>{expediente}</b>", style_val),
            Paragraph("MÉDICO TRATANTE:", style_label),
            Paragraph(f"<b>{med_display}</b>", style_val),
            Paragraph("FECHA / HORA:", style_label),
            Paragraph(f"{fecha_atencion} {hora_atencion}", style_val)
        ]
    ]
    t_meta = Table(pt_info_data, colWidths=[96.0, 150.0, 68.0, 68.0, 46.0, 105.76])
    t_meta.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
        ('BOX', (0,0), (-1,-1), 0.7, BORDER_GREY),
        ('INNERGRID', (0,0), (-1,-1), 0.3, colors.HexColor('#E2E8F0')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 3.0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3.0),
        ('LEFTPADDING', (0,0), (-1,-1), 4.0),
        ('RIGHTPADDING', (0,0), (-1,-1), 4.0),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 6.0))

    # 2. Declaración Inicial
    p_declara = Paragraph(
        f"Declaro en pleno uso de mis facultades, libre y voluntariamente, que el/la <b>{med_display}</b> "
        f"me comunicó claramente, en forma completa y detallada, el diagnóstico, tratamiento y pronóstico de mi procedimiento.",
        style_body
    )
    story.append(p_declara)
    story.append(Spacer(1, 6.0))

    # 3. Banner Diagnósticos
    t_diag_banner = Table([[Paragraph("Diagnósticos:", style_sec_title)]], colWidths=[content_w])
    t_diag_banner.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), BLUE_BANNER_BG),
        ('BOX', (0,0), (-1,-1), 0.5, BLUE_BANNER_BORDER),
        ('TOPPADDING', (0,0), (-1,-1), 2.0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.0),
    ]))
    story.append(t_diag_banner)
    story.append(Spacer(1, 4.0))

    story.append(Paragraph(f"<b>Diagnóstico clínico / preoperatorio:</b> {diagnostico}", style_body))
    story.append(Spacer(1, 3.5))
    story.append(Paragraph(f"Así mismo se me explicó, que para poder confirmar los diagnósticos anteriormente mencionados, es necesario realizar los siguientes procedimientos: <b>{proced_confirmar}</b>.", style_body))
    story.append(Spacer(1, 3.5))
    story.append(Paragraph(f"Estoy enterado (a) de los beneficios esperados en dicho procedimiento tales como: <b>{beneficio}</b>.", style_body))
    story.append(Spacer(1, 6.0))

    # 4. Banner Tratamientos
    t_trat_banner = Table([[Paragraph("Tratamientos:", style_sec_title)]], colWidths=[content_w])
    t_trat_banner.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), BLUE_BANNER_BG),
        ('BOX', (0,0), (-1,-1), 0.5, BLUE_BANNER_BORDER),
        ('TOPPADDING', (0,0), (-1,-1), 2.0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.0),
    ]))
    story.append(t_trat_banner)
    story.append(Spacer(1, 4.0))

    trat_tbl_data = [
        [Paragraph("<b>Médicos:</b>", style_item_label), Paragraph(trat_medicos, style_item_text)],
        [Paragraph("<b>Quirúrgicos:</b>", style_item_label), Paragraph(trat_quirurgicos, style_item_text)],
        [Paragraph("<b>Endoscópicos:</b>", style_item_label), Paragraph(trat_endoscopicos, style_item_text)],
        [Paragraph("<b>Rehabilitación:</b>", style_item_label), Paragraph(trat_rehab, style_item_text)],
    ]
    t_trat = Table(trat_tbl_data, colWidths=[80.0, content_w - 80.0])
    t_trat.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 1.8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 1.8),
        ('LEFTPADDING', (0,0), (-1,-1), 2.0),
        ('RIGHTPADDING', (0,0), (-1,-1), 2.0),
        ('LINEBELOW', (0,0), (-1,-2), 0.3, colors.HexColor('#E2E8F0')),
    ]))
    story.append(t_trat)
    story.append(Spacer(1, 6.0))

    # 5. Alternativas, Anestesia y Riesgos
    story.append(Paragraph(f"De igual forma se me explicó que existen otras alternativas como: <b>{alternativas}</b>; sin embargo se ha considerado que el procedimiento que se autoriza resultó más conveniente.", style_body))
    story.append(Spacer(1, 3.5))

    requiere_anestesia = "SÍ" if anestesia_val in ('SI', 'S', 'TRUE', '1') else "NO"
    story.append(Paragraph(f"<b>¿Requiere Anestesia?:</b> <b>{requiere_anestesia}</b> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; <b>Tipo de anestesia indicada:</b> {tipo_anestesia}", style_body))
    story.append(Spacer(1, 3.5))

    story.append(Paragraph(f"<b>Principales Riesgos:</b> {principales_riesgos}", style_body))
    story.append(Spacer(1, 4.0))

    story.append(Paragraph(
        "Se me hizo saber, que durante el ejercicio de la medicina y la cirugía, existe la posibilidad de que se presenten los riesgos "
        "mencionados en el apartado anterior, así como otras complicaciones o secuelas, y que los resultados no se pueden garantizar, "
        "existiendo inclusive la posibilidad de defunción.",
        style_body_bold
    ))
    story.append(Spacer(1, 7.0))

    # =========================================================================
    # 6. SECCIÓN DE DECISIÓN: AUTORIZO O NO AUTORIZO
    # =========================================================================
    if not no_autorizo:
        t_aut_banner = Table([[Paragraph("Autorizo", style_sec_title)]], colWidths=[content_w])
        t_aut_banner.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), BLUE_BANNER_BG),
            ('BOX', (0,0), (-1,-1), 0.5, BLUE_BANNER_BORDER),
            ('TOPPADDING', (0,0), (-1,-1), 2.0),
            ('BOTTOMPADDING', (0,0), (-1,-1), 2.0),
        ]))
        story.append(t_aut_banner)
        story.append(Spacer(1, 4.0))

        p_aut_text = Paragraph(
            f"Por lo anterior, al comprender la explicación, al <b>{med_display}</b> "
            f"y al equipo de salud, para que realicen los procedimientos terapéuticos necesarios, para el tratamiento de mi padecimiento.",
            style_body
        )
        story.append(p_aut_text)
        story.append(Spacer(1, 3.0))

        now_dt = datetime.datetime.now()
        dia_str = now_dt.strftime("%d")
        mes_str = MESES[now_dt.month - 1]
        anio_str = now_dt.strftime("%Y")
        story.append(Paragraph(f"<b>Ciudad de México a {dia_str} de {mes_str} de {anio_str}.</b>", ParagraphStyle('LugarFecha', fontName='Helvetica', fontSize=7.0, leading=8.8, textColor=TEXT_DARK, alignment=TA_RIGHT)))
        story.append(Spacer(1, 5.0))

        # Sello biométrico médico
        if firma_data and firma_data.get('sello_digital'):
            sello_resumido = str(firma_data['sello_digital'])[:34] + "..."
            fecha_txt = firma_data.get('fecha_hora_firma') or f"{fecha_atencion} {hora_atencion}"
            med_stamp_html = f"""
            <font size='5.2' color='#006633'><b>[✔ CONSTANCIA MÉDICA Y FEA]</b></font><br/>
            <font size='4.4' color='#004d26'><b>NOM-004-SSA3-2012 / NOM-024-SSA3-2012</b></font><br/>
            <font size='4.2' color='#444'><b>Sello:</b> <font face='Courier' size='3.8'>{sello_resumido}</font> | {fecha_txt}</font>
            """
            stamp_med = Paragraph(med_stamp_html, style_sig_stamp)
        else:
            stamp_med = Paragraph("<font size='5.2' color='#555'><b>Firma del Médico Tratante</b></font>", ParagraphStyle('SignMedBlank', fontName='Helvetica-Oblique', fontSize=5.2, leading=6.5, alignment=TA_CENTER, textColor=TEXT_MUTED))

        # Sello biométrico paciente
        has_pac = bool(
            pt_data.get('firma_paciente_biometrica') or 
            pt_data.get('sello_paciente') or 
            (firma_data and (firma_data.get('sello_paciente') or firma_data.get('firma_paciente_biometrica')))
        )
        if has_pac:
            sello_pac_val = str(pt_data.get('sello_paciente') or (firma_data and firma_data.get('sello_paciente')) or 'BIO-HES:OK')[:24]
            stamp_pac_html = f"""
            <font size='5.2' color='#006633'><b>[✔ AUTORIZADO CON HUELLA BIOMÉTRICA]</b></font><br/>
            <font size='4.4' color='#004d26'><b>NOM-004-SSA3-2012 / NOM-024-SSA3-2012</b></font><br/>
            <font size='4.2' color='#444'><b>Sello:</b> <font face='Courier' size='3.8'>{sello_pac_val}</font> | {fecha_atencion} {hora_atencion}</font>
            """
            stamp_pac = Paragraph(stamp_pac_html, style_sig_stamp)
        else:
            stamp_pac = Paragraph("<font size='5.2' color='#555'><b>Firma del Paciente / Representante</b></font>", ParagraphStyle('SignPacBlank', fontName='Helvetica-Oblique', fontSize=5.2, leading=6.5, alignment=TA_CENTER, textColor=TEXT_MUTED))

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

        # Sello biométrico Testigo 1
        sello_t1_val = str(pt_data.get('sello_testigo1') or (firma_data and firma_data.get('sello_testigo1')) or '')[:24]
        if has_t1:
            stamp_t1_html = f"""
            <font size='5.2' color='#006633'><b>[✔ TESTIGO 1 - HUELLA BIOMÉTRICA]</b></font><br/>
            <font size='4.2' color='#444'><b>Validación Dactilar:</b> <font face='Courier' size='3.8'>{sello_t1_val or 'BIO-HES:OK'}</font></font>
            """
            stamp_t1 = Paragraph(stamp_t1_html, style_sig_stamp)
        else:
            stamp_t1 = Paragraph("&nbsp;", ParagraphStyle('SigEmpty', fontName='Helvetica', fontSize=5.2, leading=6.5))

        # Sello biométrico Testigo 2
        sello_t2_val = str(pt_data.get('sello_testigo2') or (firma_data and firma_data.get('sello_testigo2')) or '')[:24]
        if has_t2:
            stamp_t2_html = f"""
            <font size='5.2' color='#006633'><b>[✔ TESTIGO 2 - HUELLA BIOMÉTRICA]</b></font><br/>
            <font size='4.2' color='#444'><b>Validación Dactilar:</b> <font face='Courier' size='3.8'>{sello_t2_val or 'BIO-HES:OK'}</font></font>
            """
            stamp_t2 = Paragraph(stamp_t2_html, style_sig_stamp)
        else:
            stamp_t2 = Paragraph("&nbsp;", ParagraphStyle('SigEmpty', fontName='Helvetica', fontSize=5.2, leading=6.5))

        half_w = (content_w - 8.0) / 2.0
        
        if has_t1 and has_t2:
            sig_aut_data = [
                # Fila 1: Médico Tratante (Izq) | Paciente o Representante (Der)
                [
                    Paragraph(f"<b>Médico Tratante:</b> <u>{med_display}</u>", style_sig_title),
                    Paragraph(f"<b>Paciente o Representante:</b> <u>{nom_firmante}</u>", style_sig_title)
                ],
                [
                    Paragraph(f"<b>Cédula:</b> {cedula or ''} &nbsp;&nbsp; <b>Fecha:</b> {fecha_atencion}<br/><b>Domicilio:</b> Hospital Escandón &nbsp;&nbsp; <b>ID:</b> CÉD. PROF.", style_sig_line),
                    Paragraph(f"<b>Parentesco:</b> {parentesco_pac} &nbsp;&nbsp; <b>Fecha:</b> {fecha_atencion}<br/><b>Domicilio:</b> {domicilio_pac} &nbsp;&nbsp; <b>ID:</b> {id_pac}", style_sig_line)
                ],
                [
                    stamp_med,
                    stamp_pac
                ],
                [
                    Paragraph(f"<b>Testigo 1:</b> <u>{testigo1}</u>", style_sig_title),
                    Paragraph(f"<b>Testigo 2:</b> <u>{testigo2}</u>", style_sig_title)
                ],
                [
                    Paragraph(f"<b>Parentesco:</b> {parentesco_testigo1} &nbsp;&nbsp; <b>Fecha:</b> {fecha_atencion}<br/><b>Domicilio:</b> {domicilio_testigo1} &nbsp;&nbsp; <b>ID:</b> {identificacion_testigo1}", style_sig_line),
                    Paragraph(f"<b>Parentesco:</b> {parentesco_testigo2} &nbsp;&nbsp; <b>Fecha:</b> {fecha_atencion}<br/><b>Domicilio:</b> {domicilio_testigo2} &nbsp;&nbsp; <b>ID:</b> {identificacion_testigo2}", style_sig_line)
                ],
                [
                    stamp_t1,
                    stamp_t2
                ]
            ]
            t_sig_aut = Table(sig_aut_data, colWidths=[half_w, half_w])
            t_sig_aut.setStyle(TableStyle([
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('TOPPADDING', (0,0), (-1,-1), 2.0),
                ('BOTTOMPADDING', (0,0), (-1,-1), 2.0),
                ('LEFTPADDING', (0,0), (-1,-1), 4.0),
                ('RIGHTPADDING', (0,0), (-1,-1), 4.0),
                ('BACKGROUND', (0,0), (0,2), colors.HexColor('#F8FAFC')),
                ('BACKGROUND', (1,0), (1,2), colors.HexColor('#F8FAFC')),
                ('BOX', (0,0), (0,2), 0.5, colors.HexColor('#CBD5E1')),
                ('BOX', (1,0), (1,2), 0.5, colors.HexColor('#CBD5E1')),
                ('BACKGROUND', (0,3), (0,5), colors.HexColor('#F8FAFC')),
                ('BACKGROUND', (1,3), (1,5), colors.HexColor('#F8FAFC')),
                ('BOX', (0,3), (0,5), 0.5, colors.HexColor('#CBD5E1')),
                ('BOX', (1,3), (1,5), 0.5, colors.HexColor('#CBD5E1')),
            ]))
            story.append(KeepTogether([t_sig_aut]))
        elif has_t1 or has_t2:
            # 3 Firmas: Médico + Paciente arriba, Testigo centrado abajo
            sig_top_data = [
                [
                    Paragraph(f"<b>Médico Tratante:</b> <u>{med_display}</u>", style_sig_title),
                    Paragraph(f"<b>Paciente o Representante:</b> <u>{nom_firmante}</u>", style_sig_title)
                ],
                [
                    Paragraph(f"<b>Cédula:</b> {cedula or ''} &nbsp;&nbsp; <b>Fecha:</b> {fecha_atencion}<br/><b>Domicilio:</b> Hospital Escandón &nbsp;&nbsp; <b>ID:</b> CÉD. PROF.", style_sig_line),
                    Paragraph(f"<b>Parentesco:</b> {parentesco_pac} &nbsp;&nbsp; <b>Fecha:</b> {fecha_atencion}<br/><b>Domicilio:</b> {domicilio_pac} &nbsp;&nbsp; <b>ID:</b> {id_pac}", style_sig_line)
                ],
                [
                    stamp_med,
                    stamp_pac
                ]
            ]
            t_top = Table(sig_top_data, colWidths=[half_w, half_w])
            t_top.setStyle(TableStyle([
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('TOPPADDING', (0,0), (-1,-1), 2.0),
                ('BOTTOMPADDING', (0,0), (-1,-1), 2.0),
                ('LEFTPADDING', (0,0), (-1,-1), 4.0),
                ('RIGHTPADDING', (0,0), (-1,-1), 4.0),
                ('BACKGROUND', (0,0), (0,2), colors.HexColor('#F8FAFC')),
                ('BACKGROUND', (1,0), (1,2), colors.HexColor('#F8FAFC')),
                ('BOX', (0,0), (0,2), 0.5, colors.HexColor('#CBD5E1')),
                ('BOX', (1,0), (1,2), 0.5, colors.HexColor('#CBD5E1')),
            ]))

            t_name = testigo1 if has_t1 else testigo2
            t_par = parentesco_testigo1 if has_t1 else parentesco_testigo2
            t_dom = domicilio_testigo1 if has_t1 else domicilio_testigo2
            t_id = identificacion_testigo1 if has_t1 else identificacion_testigo2
            t_stamp = stamp_t1 if has_t1 else stamp_t2
            t_lbl = "Testigo 1" if has_t1 else "Testigo 2"

            sig_bot_data = [
                [Paragraph(f"<b>{t_lbl}:</b> <u>{t_name}</u>", style_sig_title)],
                [Paragraph(f"<b>Parentesco:</b> {t_par} &nbsp;&nbsp; <b>Fecha:</b> {fecha_atencion}<br/><b>Domicilio:</b> {t_dom} &nbsp;&nbsp; <b>ID:</b> {t_id}", style_sig_line)],
                [t_stamp]
            ]
            t_bot = Table(sig_bot_data, colWidths=[half_w], hAlign='CENTER')
            t_bot.setStyle(TableStyle([
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('TOPPADDING', (0,0), (-1,-1), 2.0),
                ('BOTTOMPADDING', (0,0), (-1,-1), 2.0),
                ('LEFTPADDING', (0,0), (-1,-1), 4.0),
                ('RIGHTPADDING', (0,0), (-1,-1), 4.0),
                ('BACKGROUND', (0,0), (0,2), colors.HexColor('#F8FAFC')),
                ('BOX', (0,0), (0,2), 0.5, colors.HexColor('#CBD5E1')),
            ]))
            story.append(KeepTogether([t_top, Spacer(1, 4.0), t_bot]))
        else:
            # 2 Firmas: Médico y Paciente lado a lado
            sig_aut_data = [
                [
                    Paragraph(f"<b>Médico Tratante:</b> <u>{med_display}</u>", style_sig_title),
                    Paragraph(f"<b>Paciente o Representante:</b> <u>{nom_firmante}</u>", style_sig_title)
                ],
                [
                    Paragraph(f"<b>Cédula:</b> {cedula or ''} &nbsp;&nbsp; <b>Fecha:</b> {fecha_atencion}<br/><b>Domicilio:</b> Hospital Escandón &nbsp;&nbsp; <b>ID:</b> CÉD. PROF.", style_sig_line),
                    Paragraph(f"<b>Parentesco:</b> {parentesco_pac} &nbsp;&nbsp; <b>Fecha:</b> {fecha_atencion}<br/><b>Domicilio:</b> {domicilio_pac} &nbsp;&nbsp; <b>ID:</b> {id_pac}", style_sig_line)
                ],
                [
                    stamp_med,
                    stamp_pac
                ]
            ]
            t_sig_aut = Table(sig_aut_data, colWidths=[half_w, half_w])
            t_sig_aut.setStyle(TableStyle([
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('TOPPADDING', (0,0), (-1,-1), 2.0),
                ('BOTTOMPADDING', (0,0), (-1,-1), 2.0),
                ('LEFTPADDING', (0,0), (-1,-1), 4.0),
                ('RIGHTPADDING', (0,0), (-1,-1), 4.0),
                ('BACKGROUND', (0,0), (0,2), colors.HexColor('#F8FAFC')),
                ('BACKGROUND', (1,0), (1,2), colors.HexColor('#F8FAFC')),
                ('BOX', (0,0), (0,2), 0.5, colors.HexColor('#CBD5E1')),
                ('BOX', (1,0), (1,2), 0.5, colors.HexColor('#CBD5E1')),
            ]))
            story.append(KeepTogether([t_sig_aut]))

    # =========================================================================
    # NO AUTORIZO / DISENTIMIENTO
    # =========================================================================
    else:
        motivo_no_acepto = pt_data.get('motivo_no_acepto') or pt_data.get('motivo_rechazo') or 'Decisión voluntaria tras recibir información completa.'
        
        t_no_banner = Table([[Paragraph("No Autorizo / Revocación del Consentimiento", ParagraphStyle('SecNo', fontName='Helvetica-BoldOblique', fontSize=8.6, leading=10.5, textColor=colors.HexColor('#991B1B'), alignment=TA_CENTER))]], colWidths=[content_w])
        t_no_banner.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#FEE2E2')),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#EF4444')),
            ('TOPPADDING', (0,0), (-1,-1), 2.0),
            ('BOTTOMPADDING', (0,0), (-1,-1), 2.0),
        ]))
        story.append(t_no_banner)
        story.append(Spacer(1, 4.0))

        p_no_text = Paragraph(
            f"Al <b>{med_display}</b> y al cuerpo de salud, a que se me realicen los procedimientos terapéuticos que me han indicado para el tratamiento de mi padecimiento, liberándolos de toda responsabilidad médico-legal. "
            f"El motivo por el cual no acepto es: <u>{motivo_no_acepto}</u>",
            style_body
        )
        story.append(p_no_text)
        story.append(Spacer(1, 3.0))

        now_dt = datetime.datetime.now()
        dia_str = now_dt.strftime("%d")
        mes_str = MESES[now_dt.month - 1]
        anio_str = now_dt.strftime("%Y")
        story.append(Paragraph(f"<b>Ciudad de México a {dia_str} de {mes_str} de {anio_str}.</b>", ParagraphStyle('LugarFecha', fontName='Helvetica', fontSize=7.0, leading=8.8, textColor=TEXT_DARK, alignment=TA_RIGHT)))
        story.append(Spacer(1, 5.0))

        # Sello biométrico médico (Constancia)
        if firma_data and firma_data.get('sello_digital'):
            sello_resumido = str(firma_data['sello_digital'])[:34] + "..."
            fecha_txt = firma_data.get('fecha_hora_firma') or f"{fecha_atencion} {hora_atencion}"
            med_stamp_html = f"""
            <font size='5.2' color='#006633'><b>[✔ CONSTANCIA MÉDICA Y FEA]</b></font><br/>
            <font size='4.4' color='#004d26'><b>NOM-004-SSA3-2012 / ART. 81 REGLAMENTO LGS</b></font><br/>
            <font size='4.2' color='#444'><b>Sello:</b> <font face='Courier' size='3.8'>{sello_resumido}</font> | {fecha_txt}</font>
            """
            stamp_med_no = Paragraph(med_stamp_html, style_sig_stamp)
        else:
            stamp_med_no = Paragraph("<font size='5.2' color='#555'><b>Firma y Sello del Médico</b></font>", ParagraphStyle('SignMed', fontName='Helvetica-Oblique', fontSize=5.2, leading=6.5, alignment=TA_CENTER, textColor=TEXT_MUTED))

        # Sello biométrico Paciente / Negativa
        has_pac_no = bool(
            pt_data.get('firma_paciente_biometrica') or 
            pt_data.get('sello_paciente') or 
            (firma_data and (firma_data.get('sello_paciente') or firma_data.get('firma_paciente_biometrica')))
        )
        if has_pac_no:
            sello_pac_val = str(pt_data.get('sello_paciente') or (firma_data and firma_data.get('sello_paciente')) or 'BIO-HES:OK')[:24]
            stamp_no_html = f"""
            <font size='5.2' color='#991B1B'><b>[✔ NEGATIVA / DISENTIMIENTO CON HUELLA]</b></font><br/>
            <font size='4.4' color='#7F1D1D'><b>NOM-004-SSA3-2012 / ART. 81 REGLAMENTO LGS</b></font><br/>
            <font size='4.2' color='#444'><b>Sello:</b> <font face='Courier' size='3.8'>{sello_pac_val}</font> | {fecha_atencion} {hora_atencion}</font>
            """
            stamp_no_p = Paragraph(stamp_no_html, style_sig_stamp)
        else:
            stamp_no_p = Paragraph("<font size='5.2' color='#555'><b>Firma y Sello del Paciente / Negativa</b></font>", ParagraphStyle('SignNoBlank', fontName='Helvetica-Oblique', fontSize=5.2, leading=6.5, alignment=TA_CENTER, textColor=TEXT_MUTED))

        # Sello biométrico Testigo 1 para No Autorizo
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
        sello_t1_val = str(pt_data.get('sello_testigo1') or (firma_data and firma_data.get('sello_testigo1')) or '')[:24]
        if has_t1:
            stamp_t1_html = f"""
            <font size='5.2' color='#991B1B'><b>[✔ TESTIGO 1 - HUELLA BIOMÉTRICA]</b></font><br/>
            <font size='4.2' color='#444'><b>Validación Dactilar:</b> <font face='Courier' size='3.8'>{sello_t1_val or 'BIO-HES:OK'}</font></font>
            """
            stamp_t1_no = Paragraph(stamp_t1_html, style_sig_stamp)
        else:
            stamp_t1_no = Paragraph("&nbsp;", ParagraphStyle('SigEmpty', fontName='Helvetica', fontSize=5.2, leading=6.5))

        # Sello biométrico Testigo 2 para No Autorizo
        sello_t2_val = str(pt_data.get('sello_testigo2') or (firma_data and firma_data.get('sello_testigo2')) or '')[:24]
        if has_t2:
            stamp_t2_html = f"""
            <font size='5.2' color='#991B1B'><b>[✔ TESTIGO 2 - HUELLA BIOMÉTRICA]</b></font><br/>
            <font size='4.2' color='#444'><b>Validación Dactilar:</b> <font face='Courier' size='3.8'>{sello_t2_val or 'BIO-HES:OK'}</font></font>
            """
            stamp_t2_no = Paragraph(stamp_t2_html, style_sig_stamp)
        else:
            stamp_t2_no = Paragraph("&nbsp;", ParagraphStyle('SigEmpty', fontName='Helvetica', fontSize=5.2, leading=6.5))

        half_w = (content_w - 8.0) / 2.0
        
        if has_t1 and has_t2:
            sig_no_data = [
                # Fila 1: Paciente (Negativa) | Médico (Constancia)
                [
                    Paragraph(f"<b>Paciente o Representante (Negativa):</b> <u>{nom_firmante}</u>", style_sig_title),
                    Paragraph(f"<b>Médico Tratante (Constancia):</b> <u>{med_display}</u>", style_sig_title)
                ],
                [
                    Paragraph(f"<b>Parentesco:</b> {parentesco_pac} &nbsp;&nbsp; <b>Fecha:</b> {fecha_atencion}<br/><b>Domicilio:</b> {domicilio_pac} &nbsp;&nbsp; <b>ID:</b> {id_pac}", style_sig_line),
                    Paragraph(f"<b>Cédula:</b> {cedula or ''} &nbsp;&nbsp; <b>Fecha:</b> {fecha_atencion}<br/><b>Domicilio:</b> Hospital Escandón &nbsp;&nbsp; <b>ID:</b> CÉD. PROF.", style_sig_line)
                ],
                [
                    stamp_no_p,
                    stamp_med_no
                ],
                [
                    Paragraph(f"<b>Testigo 1:</b> <u>{testigo1}</u>", style_sig_title),
                    Paragraph(f"<b>Testigo 2:</b> <u>{testigo2}</u>", style_sig_title)
                ],
                [
                    Paragraph(f"<b>Parentesco:</b> {parentesco_testigo1} &nbsp;&nbsp; <b>Fecha:</b> {fecha_atencion}<br/><b>Domicilio:</b> {domicilio_testigo1} &nbsp;&nbsp; <b>ID:</b> {identificacion_testigo1}", style_sig_line),
                    Paragraph(f"<b>Parentesco:</b> {parentesco_testigo2} &nbsp;&nbsp; <b>Fecha:</b> {fecha_atencion}<br/><b>Domicilio:</b> {domicilio_testigo2} &nbsp;&nbsp; <b>ID:</b> {identificacion_testigo2}", style_sig_line)
                ],
                [
                    stamp_t1_no,
                    stamp_t2_no
                ]
            ]
            t_sig_no = Table(sig_no_data, colWidths=[half_w, half_w])
            t_sig_no.setStyle(TableStyle([
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('TOPPADDING', (0,0), (-1,-1), 2.0),
                ('BOTTOMPADDING', (0,0), (-1,-1), 2.0),
                ('LEFTPADDING', (0,0), (-1,-1), 4.0),
                ('RIGHTPADDING', (0,0), (-1,-1), 4.0),
                ('BACKGROUND', (0,0), (0,2), colors.HexColor('#FEF2F2')),
                ('BACKGROUND', (1,0), (1,2), colors.HexColor('#FEF2F2')),
                ('BOX', (0,0), (0,2), 0.5, colors.HexColor('#FCA5A5')),
                ('BOX', (1,0), (1,2), 0.5, colors.HexColor('#FCA5A5')),
                ('BACKGROUND', (0,3), (0,5), colors.HexColor('#FEF2F2')),
                ('BACKGROUND', (1,3), (1,5), colors.HexColor('#FEF2F2')),
                ('BOX', (0,3), (0,5), 0.5, colors.HexColor('#FCA5A5')),
                ('BOX', (1,3), (1,5), 0.5, colors.HexColor('#FCA5A5')),
            ]))
            story.append(KeepTogether([t_sig_no]))
        elif has_t1 or has_t2:
            # 3 Firmas: Paciente + Médico arriba, Testigo centrado abajo
            sig_top_data = [
                [
                    Paragraph(f"<b>Paciente o Representante (Negativa):</b> <u>{nom_firmante}</u>", style_sig_title),
                    Paragraph(f"<b>Médico Tratante (Constancia):</b> <u>{med_display}</u>", style_sig_title)
                ],
                [
                    Paragraph(f"<b>Parentesco:</b> {parentesco_pac} &nbsp;&nbsp; <b>Fecha:</b> {fecha_atencion}<br/><b>Domicilio:</b> {domicilio_pac} &nbsp;&nbsp; <b>ID:</b> {id_pac}", style_sig_line),
                    Paragraph(f"<b>Cédula:</b> {cedula or ''} &nbsp;&nbsp; <b>Fecha:</b> {fecha_atencion}<br/><b>Domicilio:</b> Hospital Escandón &nbsp;&nbsp; <b>ID:</b> CÉD. PROF.", style_sig_line)
                ],
                [
                    stamp_no_p,
                    stamp_med_no
                ]
            ]
            t_top = Table(sig_top_data, colWidths=[half_w, half_w])
            t_top.setStyle(TableStyle([
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('TOPPADDING', (0,0), (-1,-1), 2.0),
                ('BOTTOMPADDING', (0,0), (-1,-1), 2.0),
                ('LEFTPADDING', (0,0), (-1,-1), 4.0),
                ('RIGHTPADDING', (0,0), (-1,-1), 4.0),
                ('BACKGROUND', (0,0), (0,2), colors.HexColor('#FEF2F2')),
                ('BACKGROUND', (1,0), (1,2), colors.HexColor('#FEF2F2')),
                ('BOX', (0,0), (0,2), 0.5, colors.HexColor('#FCA5A5')),
                ('BOX', (1,0), (1,2), 0.5, colors.HexColor('#FCA5A5')),
            ]))

            t_name = testigo1 if has_t1 else testigo2
            t_par = parentesco_testigo1 if has_t1 else parentesco_testigo2
            t_dom = domicilio_testigo1 if has_t1 else domicilio_testigo2
            t_id = identificacion_testigo1 if has_t1 else identificacion_testigo2
            t_stamp = stamp_t1_no if has_t1 else stamp_t2_no
            t_lbl = "Testigo 1" if has_t1 else "Testigo 2"

            sig_bot_data = [
                [Paragraph(f"<b>{t_lbl}:</b> <u>{t_name}</u>", style_sig_title)],
                [Paragraph(f"<b>Parentesco:</b> {t_par} &nbsp;&nbsp; <b>Fecha:</b> {fecha_atencion}<br/><b>Domicilio:</b> {t_dom} &nbsp;&nbsp; <b>ID:</b> {t_id}", style_sig_line)],
                [t_stamp]
            ]
            t_bot = Table(sig_bot_data, colWidths=[half_w], hAlign='CENTER')
            t_bot.setStyle(TableStyle([
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('TOPPADDING', (0,0), (-1,-1), 2.0),
                ('BOTTOMPADDING', (0,0), (-1,-1), 2.0),
                ('LEFTPADDING', (0,0), (-1,-1), 4.0),
                ('RIGHTPADDING', (0,0), (-1,-1), 4.0),
                ('BACKGROUND', (0,0), (0,2), colors.HexColor('#FEF2F2')),
                ('BOX', (0,0), (0,2), 0.5, colors.HexColor('#FCA5A5')),
            ]))
            story.append(KeepTogether([t_top, Spacer(1, 4.0), t_bot]))
        else:
            # 2 Firmas: Paciente y Médico lado a lado
            sig_no_data = [
                [
                    Paragraph(f"<b>Paciente o Representante (Negativa):</b> <u>{nom_firmante}</u>", style_sig_title),
                    Paragraph(f"<b>Médico Tratante (Constancia):</b> <u>{med_display}</u>", style_sig_title)
                ],
                [
                    Paragraph(f"<b>Parentesco:</b> {parentesco_pac} &nbsp;&nbsp; <b>Fecha:</b> {fecha_atencion}<br/><b>Domicilio:</b> {domicilio_pac} &nbsp;&nbsp; <b>ID:</b> {id_pac}", style_sig_line),
                    Paragraph(f"<b>Cédula:</b> {cedula or ''} &nbsp;&nbsp; <b>Fecha:</b> {fecha_atencion}<br/><b>Domicilio:</b> Hospital Escandón &nbsp;&nbsp; <b>ID:</b> CÉD. PROF.", style_sig_line)
                ],
                [
                    stamp_no_p,
                    stamp_med_no
                ]
            ]
            t_sig_no = Table(sig_no_data, colWidths=[half_w, half_w])
            t_sig_no.setStyle(TableStyle([
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('TOPPADDING', (0,0), (-1,-1), 2.0),
                ('BOTTOMPADDING', (0,0), (-1,-1), 2.0),
                ('LEFTPADDING', (0,0), (-1,-1), 4.0),
                ('RIGHTPADDING', (0,0), (-1,-1), 4.0),
                ('BACKGROUND', (0,0), (0,2), colors.HexColor('#FEF2F2')),
                ('BACKGROUND', (1,0), (1,2), colors.HexColor('#FEF2F2')),
                ('BOX', (0,0), (0,2), 0.5, colors.HexColor('#FCA5A5')),
                ('BOX', (1,0), (1,2), 0.5, colors.HexColor('#FCA5A5')),
            ]))
            story.append(KeepTogether([t_sig_no]))

    canvas_factory = lambda *args, **kwargs: CleanConsentCanvas(*args, doc_info=doc_info, **kwargs)
    doc.build(story, canvasmaker=canvas_factory)
    return output_path

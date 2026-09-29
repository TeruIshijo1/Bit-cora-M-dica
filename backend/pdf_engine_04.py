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
        TEXT_MUTED, TEXT_DARK, RED_ALERT, PRIMARY_BLUE, BORDER_GREY,
        letterhead_content_width
    )
except ModuleNotFoundError:
    from pdf_engine_v2 import (
        RDLCCanvas, CleanConsentCanvas, FRAME_X, FRAME_Y, FRAME_W, FRAME_H, 
        TEXT_MUTED, TEXT_DARK, RED_ALERT, PRIMARY_BLUE, BORDER_GREY,
        letterhead_content_width
    )

def generate_consentimiento_04(pt_data: dict, output_path: str = None, firma_data: dict = None) -> str:
    """
    Genera el PDF oficial para el Formato 04:
    HE-DIRMED-CONSUL-PLT-04: CONSENTIMIENTO INFORMADO PARA COLOCACIÓN DE CATÉTER VENOSO CENTRAL.
    """
    if output_path and os.path.dirname(output_path):
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

    content_x = FRAME_X + 16.0
    content_w = letterhead_content_width(content_x)

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

    # Estilos tipográficos institucionales
    style_label = ParagraphStyle('MetaLabel', fontName='Helvetica-Bold', fontSize=7.5, leading=9.5, textColor=TEXT_MUTED)
    style_val = ParagraphStyle('MetaVal', fontName='Helvetica-Bold', fontSize=8.0, leading=10.5, textColor=TEXT_DARK)
    style_val_red = ParagraphStyle('MetaValRed', fontName='Helvetica-Bold', fontSize=8.0, leading=10.5, textColor=RED_ALERT)
    
    style_autoriza = ParagraphStyle('Autoriza', fontName='Helvetica', fontSize=8.0, leading=10.8, textColor=TEXT_DARK, alignment=TA_JUSTIFY)
    style_body = ParagraphStyle('Body', fontName='Helvetica', fontSize=7.8, leading=10.6, textColor=TEXT_DARK, alignment=TA_JUSTIFY)

    style_sig_name = ParagraphStyle('SigName', fontName='Helvetica-Bold', fontSize=7.8, leading=9.5, textColor=TEXT_DARK, alignment=TA_CENTER)
    style_sig_label = ParagraphStyle('SigLbl', fontName='Helvetica', fontSize=6.5, leading=8.2, textColor=TEXT_MUTED, alignment=TA_CENTER)
    style_sig_stamp = ParagraphStyle('SigStamp', fontName='Helvetica', fontSize=5.2, leading=6.8, textColor=colors.HexColor('#005522'), alignment=TA_CENTER)
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
            Paragraph(f"<b>MÉDICO TRATANTE:</b> {medico}" + (f"<br/><font size='6.8' color='#555555'>CÉD. PROF. {cedula}</font>" if cedula else ""), style_val),
            Paragraph(f"<b>FECHA / HORA:</b> {fecha_val} {hora_val}", style_val),
        ]
    ]

    t_info = Table(pt_info_data, colWidths=[content_w * 0.44, content_w * 0.36, content_w * 0.20])
    t_info.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.75, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
        ('TOPPADDING', (0, 0), (-1, -1), 3.8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3.8),
        ('LEFTPADDING', (0, 0), (-1, -1), 5.0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5.0),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(t_info)
    story.append(Spacer(1, 6.5))

    # 2. Párrafo de Autorización Específica
    autoriza_p = Paragraph(
        f"Autorizo la colocación de catéter venoso central por el Dr. <b>{medico}</b>, en el establecimiento a su cargo.",
        style_autoriza
    )
    story.append(autoriza_p)
    story.append(Spacer(1, 5.5))

    # 3. Objetivo y Técnica
    obj_p = Paragraph(
        "<b>He sido debidamente informada(o)</b> que el procedimiento tiene como <b>objetivo</b> la colocación quirúrgica o por punción de "
        "un catéter en una vena central o periférica y cuya elección depende de las características clínicas y anatómicas, experiencia "
        "del cirujano e indicaciones para su colocación. La técnica para lograrlo, una vez hecha la selección de la vena, es inmovilizar "
        "de acuerdo a la región anatómica a utilizar, uso de una técnica estéril y asepsia/antisepsia de la región. Se puede utilizar la "
        "técnica por punción de la vena con aguja (canalizar) e introducción del catéter establecido, o en el caso de no "
        "tener éxito, el procedimiento quirúrgico de venodisección. Ésta consiste en infiltrar un anestésico local en el sitio del procedimiento, "
        "incisión (corte) con bisturí en la piel, disección para localizar una vena apropiada y venotomía para la introducción del "
        "catéter. Cierre de herida con puntos simples y cobertura impermeable de la herida. Todo lo anterior con el propósito de "
        "establecer una vía estable para la infusión de líquidos parenterales, monitorización de la presión venosa central, administración "
        "de hemoderivados (sangre, plasma, plaquetas y crioprecipitados) y medicamentos, así como toma de muestras sanguíneas.",
        style_body
    )
    story.append(obj_p)
    story.append(Spacer(1, 5.5))

    # 4. Riesgos Potenciales
    riesgos_p = Paragraph(
        "Estoy informado sobre los <b>riesgos potenciales</b> que entraña el procedimiento, siendo éstos: infección, sangrado con la "
        "posibilidad de requerir transfusión de sangre con los riesgos de presentar reacciones a la sangre administrada y de "
        "exposición al VIH/SIDA, hepatitis y otras enfermedades infecciosas, extravasación de soluciones intravenosas o nutrición parenteral a "
        "otras cavidades, obstrucción del retorno venoso, cicatriz quirúrgica, infección de la herida, reacción alérgica a medicamentos "
        "y/o anestésicos, neumotórax, hemotórax, hemoneumotórax, accidentes vasculares, incluyendo fenómenos tromboembólicos del "
        "hígado, riñón, intestino, extremidades. Las complicaciones por este tipo de procedimientos aunque raras pueden llevar hasta "
        "la pérdida de alguna extremidad u órgano o de su función; e inclusive, la muerte. Se me ha informado sobre la posible "
        "necesidad de tener que realizar otros procedimientos quirúrgicos imprevistos, inmediatos o mediatos, en el mismo tiempo "
        "quirúrgico o en otro para resolver las complicaciones que se lleguen a presentar con la consecuente prolongación de la "
        "hospitalización de mi persona/hijo(a) o la necesidad de manejo en salas de Terapia Intensiva en ésta o en otra Institución.",
        style_body
    )
    story.append(riesgos_p)
    story.append(Spacer(1, 5.5))

    # 5. Beneficios
    benef_p = Paragraph(
        "Estoy enterado(a) de los <b>beneficios</b> de la colocación de catéter venoso central como: administración de medicamentos, "
        "líquidos, transfusiones, entre otros, por lo que <b>acepto</b> bajo mi absoluta responsabilidad este procedimiento.",
        style_body
    )
    story.append(benef_p)
    story.append(Spacer(1, 5.0))

    # 6. Alternativas
    alt_p = Paragraph(
        "En igual forma se me explicó que existen otras <b>alternativas</b> como colocación de catéteres periféricos, sin embargo se "
        "ha considerado que el procedimiento que se autoriza resulta ser más conveniente.",
        style_body
    )
    story.append(alt_p)
    story.append(Spacer(1, 5.0))

    # 7. Revocación
    revoc_p = Paragraph(
        "Asimismo, estoy enterado(a) de que en cualquier momento y sin necesidad de dar explicación alguna, puedo revocar por "
        "escrito el seguir recibiendo la atención y/o aplicación médica en cuestión.",
        style_body
    )
    story.append(revoc_p)
    story.append(Spacer(1, 5.0))

    # 8. Entendimiento y Preguntas
    ent_p = Paragraph(
        "Estoy completa y ampliamente informado(a) y <b>entiendo</b> los términos en que se me ha dado la información, habiendo "
        "preguntado la totalidad de las dudas que al respecto me han surgido, además de habérseme aclarado los términos técnicos "
        "que no conocía.",
        style_body
    )
    story.append(ent_p)
    story.append(Spacer(1, 5.0))

    # 9. Autorización de Contingencias
    cont_p = Paragraph(
        "En igual forma <b>autorizo</b> que ante cualquier complicación o efecto adverso durante o después del procedimiento, se "
        "practiquen las técnicas y procedimientos necesarios para la protección de mi vida y mi salud.",
        style_body
    )
    story.append(cont_p)

    # 10. Bloque de Firmas Dinámico (Solo incluye testigos si cuentan con firma/huella)
    pariente = pt_data.get('pariente') or pt_data.get('representante_legal') or pt_data.get('declarante') or ''
    raw_mayor = pt_data.get('paciente_capaz', True)
    if isinstance(raw_mayor, str):
        es_mayor = raw_mayor.lower() in ('true', '1', 'si', 'yes')
    elif isinstance(raw_mayor, (int, float)):
        es_mayor = bool(raw_mayor)
    else:
        es_mayor = bool(raw_mayor)
    has_tutor = bool(pariente) or (not es_mayor)
    testigo1 = pt_data.get('testigo1', '')
    sig_col_w = (content_w - 30.0) / 2.0  # ~245 pt

    has_t1 = bool(
        pt_data.get('firma_testigo1_biometrica') or 
        pt_data.get('sello_testigo1') or 
        (firma_data and (firma_data.get('sello_testigo1') or firma_data.get('firma_testigo1_biometrica')))
    )

    parentesco_tutor = pt_data.get('parentesco') or pt_data.get('parentesco_declarante') or pt_data.get('parentesco_paciente') or 'Tutor / Representante Legal'
    if str(parentesco_tutor).upper() in ('PACIENTE', 'TITULAR', 'DIRECTO'):
        parentesco_tutor = 'Tutor / Representante Legal'
    parentesco_test = pt_data.get('parentesco_testigo1') or pt_data.get('parentesco_testigo') or 'Testigo Presencial'
    paciente_clean = re.sub(r'\s*\([^)]*\)', '', str(paciente_nombre or '')).strip()
    testigo1_clean = re.sub(r'\s*\([^)]*\)', '', str(testigo1 or '')).strip()
    pariente_clean = re.sub(r'\s*\([^)]*\)', '', str(pariente or '')).strip()

    # Textos bajo la línea
    patient_sig_text = f"<b>{paciente_clean}</b><br/><font size='6.0' color='#334155'><i><b>Parentesco: Paciente</b></i></font>" if paciente_clean else "<b>Nombre completo del paciente</b>"
    witness_sig_text = f"<b>{testigo1_clean}</b><br/><font size='6.0' color='#334155'><i><b>Parentesco: {parentesco_test}</b></i></font>" if testigo1_clean else "<b>Nombre completo y firma del testigo</b>"
    tutor_sig_text = f"<b>{pariente_clean}</b><br/><font size='6.0' color='#334155'><i><b>Parentesco: {parentesco_tutor}</b></i></font>" if pariente_clean else "<b>Nombre completo y firma del tutor o representante legal</b>"
    doctor_sig_text = f"<b>{medico}</b><br/><font size='6.0' color='#334155'><i><b>CÉD. PROF. {cedula}</b></i></font>" if cedula else f"<b>{medico}</b>"

    # Sello biométrico médico si existe sobre la línea
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

    # Sello Biométrico Paciente / Representante
    if pt_data.get('firma_paciente_biometrica') or pt_data.get('sello_paciente') or (firma_data and firma_data.get('sello_paciente')):
        sello_pac_val = str(pt_data.get('sello_paciente') or (firma_data and firma_data.get('sello_paciente')) or 'BIO-HES:OK')[:24]
        pac_stamp_html = f"""
        <font size='5.0' color='#006633'><b>[✔ AUTORIZADO CON HUELLA BIOMÉTRICA]</b></font><br/>
        <font size='4.2' color='#444'><b>Validación Dactilar:</b> <font face='Courier' size='3.8'>{sello_pac_val}</font></font>
        """
        pac_sig_p = Paragraph(pac_stamp_html, style_sig_stamp)
    else:
        pac_sig_p = Paragraph("&nbsp;", ParagraphStyle('SigSpace', fontName='Helvetica', fontSize=8.0, leading=12.0, textColor=colors.transparent, alignment=TA_CENTER))

    # Sello Biométrico Testigo 1
    if has_t1:
        sello_test_val = str(pt_data.get('sello_testigo1') or (firma_data and firma_data.get('sello_testigo1')) or 'BIO-HES:OK')[:24]
        test_stamp_html = f"""
        <font size='5.0' color='#006633'><b>[✔ TESTIGO - HUELLA BIOMÉTRICA]</b></font><br/>
        <font size='4.2' color='#444'><b>Validación Dactilar:</b> <font face='Courier' size='3.8'>{sello_test_val}</font></font>
        """
        test_sig_p = Paragraph(test_stamp_html, style_sig_stamp)
    else:
        test_sig_p = Paragraph("&nbsp;", ParagraphStyle('SigSpace', fontName='Helvetica', fontSize=8.0, leading=12.0, textColor=colors.transparent, alignment=TA_CENTER))

    sig_space_p = Paragraph("&nbsp;", ParagraphStyle('SigSpace', fontName='Helvetica', fontSize=8.0, leading=12.0, textColor=colors.transparent, alignment=TA_CENTER))

    if has_tutor and has_t1:
        # Caso 1: Con tutor y testigo firmado -> Cuadrícula 2x2
        story.append(Spacer(1, 14.0))
        sig_grid = [
            [
                pac_sig_p if es_mayor else Paragraph("&nbsp;", style_sig_blank),
                '',
                pac_sig_p if not es_mayor else sig_space_p
            ],
            [
                Paragraph(patient_sig_text if es_mayor else "&nbsp;", style_sig_name),
                '',
                Paragraph(tutor_sig_text, style_sig_name)
            ],
            [
                top_med_p,
                '',
                test_sig_p
            ],
            [
                Paragraph(doctor_sig_text, style_sig_name),
                '',
                Paragraph(witness_sig_text, style_sig_name)
            ]
        ]
        table_styles = [
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
        ]
        t_sigs = Table(sig_grid, colWidths=[sig_col_w, 30.0, sig_col_w])
        t_sigs.setStyle(TableStyle(table_styles))
        story.append(KeepTogether(t_sigs))

    elif has_tutor and not has_t1:
        # Caso 2: Con tutor, pero SIN testigo
        if es_mayor:
            # Paciente + Tutor arriba, Médico abajo centrado
            story.append(Spacer(1, 14.0))
            t_top = Table([
                [pac_sig_p, '', sig_space_p],
                [Paragraph(patient_sig_text, style_sig_name), '', Paragraph(tutor_sig_text, style_sig_name)]
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
            story.append(KeepTogether([t_top, Spacer(1, 12), t_bot]))
        else:
            # Menor de edad: Tutor (Izq) y Médico (Der) lado a lado
            story.append(Spacer(1, 30.0))
            t_pair = Table([
                [pac_sig_p, '', top_med_p],
                [Paragraph(tutor_sig_text, style_sig_name), '', Paragraph(doctor_sig_text, style_sig_name)]
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

    elif has_t1:
        # Caso 3: Paciente Mayor Capaz + Testigo firmado
        story.append(Spacer(1, 14.0))
        t_top = Table([
            [pac_sig_p, '', test_sig_p],
            [Paragraph(patient_sig_text, style_sig_name), '', Paragraph(witness_sig_text, style_sig_name)]
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
        story.append(KeepTogether([t_top, Spacer(1, 12), t_bot]))

    else:
        # Caso 4: Paciente Mayor Capaz SIN testigo -> Paciente y Médico lado a lado abajo
        story.append(Spacer(1, 32.0))
        t_pair = Table([
            [pac_sig_p, '', top_med_p],
            [Paragraph(patient_sig_text, style_sig_name), '', Paragraph(doctor_sig_text, style_sig_name)]
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

    # Parámetros del membrete institucional unificado con QR de verificación
    doc_info = {
        'title_lines': [
            'CONSENTIMIENTO INFORMADO PARA',
            'COLOCACIÓN DE CATÉTER VENOSO',
            'CENTRAL'
        ],
        'code': 'HE-DIRMED-CONSUL-PLT-04',
        'draw_header_dates': False,
        'fecha_ingreso': fecha_val,
        'hora_ingreso': hora_val,
        'expediente': expediente,
        'folio': expediente or pt_data.get('pt_num', ''),
        'pt_num': str(pt_data.get('pt_num', '')),
        'slot': pt_data.get('slot') or pt_data.get('mrnum') or 1,
        'draw_qr': True
    }

    def make_canvas(*args, **kwargs):
        c = CleanConsentCanvas(*args, doc_info=doc_info, fecha_ingreso=fecha_val, hora_ingreso=hora_val, **kwargs)
        return c

    doc.build(story, canvasmaker=make_canvas)
    return output_path

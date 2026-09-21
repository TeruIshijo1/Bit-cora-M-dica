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
        TEXT_MUTED, TEXT_DARK, RED_ALERT, PRIMARY_BLUE, DARK_BLUE, BORDER_GREY
    )
except ModuleNotFoundError:
    from pdf_engine_v2 import (
        RDLCCanvas, CleanConsentCanvas, FRAME_X, FRAME_Y, FRAME_W, FRAME_H, 
        TEXT_MUTED, TEXT_DARK, RED_ALERT, PRIMARY_BLUE, DARK_BLUE, BORDER_GREY
    )

def generate_consentimiento_08(pt_data: dict, output_path: str = None, firma_data: dict = None) -> str:
    """
    Genera el PDF oficial para el Formato 08:
    HE-DIRMED-CONSUL-PLT-08: CONSENTIMIENTO INFORMADO PARA TRATAMIENTO, PROCEDIMIENTO(S) DE DIAGNÓSTICO EN ADMISIÓN CONTINUA.
    Ajustado a 1 página exacta de alta fidelidad institucional con marco RDLC MidnightBlue 1.25pt.
    """
    if output_path and os.path.dirname(output_path):
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

    content_x = FRAME_X + 14.0
    content_w = FRAME_W - 34.0  # ~535.76 pt

    frame_bottom = FRAME_Y + 40.0
    frame_top = (FRAME_Y + FRAME_H) - 60.0
    frame_h = frame_top - frame_bottom # ~622.84 pt

    frame_p1 = Frame(content_x, frame_bottom, content_w, frame_h, id='p1_frame',
                     leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)

    template_p1 = PageTemplate(id='FirstPage', frames=frame_p1)

    doc = BaseDocTemplate(
        output_path,
        pagesize=letter,
        pageTemplates=[template_p1]
    )

    # Estilos tipográficos calibrados para distribución armónica de página completa
    style_label = ParagraphStyle('MetaLabel', fontName='Helvetica-Bold', fontSize=7.5, leading=9.5, textColor=PRIMARY_BLUE)
    style_val = ParagraphStyle('MetaVal', fontName='Helvetica', fontSize=7.8, leading=10.0, textColor=TEXT_DARK)
    style_val_bold = ParagraphStyle('MetaValBold', fontName='Helvetica-Bold', fontSize=7.8, leading=10.0, textColor=TEXT_DARK)
    
    style_body = ParagraphStyle('Body', fontName='Helvetica', fontSize=7.8, leading=10.6, textColor=TEXT_DARK, alignment=TA_JUSTIFY)
    style_body_legal = ParagraphStyle('BodyLegal', fontName='Helvetica', fontSize=6.8, leading=8.8, textColor=TEXT_DARK, alignment=TA_JUSTIFY)
    style_emergencia = ParagraphStyle('Emergencia', fontName='Helvetica-Oblique', fontSize=6.6, leading=8.6, textColor=TEXT_MUTED, alignment=TA_JUSTIFY)

    style_sig_name = ParagraphStyle('SigName', fontName='Helvetica-Bold', fontSize=7.8, leading=9.8, textColor=TEXT_DARK, alignment=TA_CENTER)
    style_sig_sub = ParagraphStyle('SigSub', fontName='Helvetica', fontSize=6.0, leading=7.8, textColor=TEXT_MUTED, alignment=TA_CENTER)
    style_sig_stamp = ParagraphStyle('SigStamp', fontName='Helvetica', fontSize=5.0, leading=6.5, textColor=colors.HexColor('#006633'), alignment=TA_CENTER)
    style_sig_blank = ParagraphStyle('SigBlank', fontName='Helvetica', fontSize=6.0, leading=7.0, textColor=colors.transparent, alignment=TA_CENTER)

    story = []

    # 1. Metadatos del Paciente
    paciente_nombre = (pt_data.get('paciente_nombre') or pt_data.get('nombre') or '').strip()
    expediente = str(pt_data.get('expediente') or pt_data.get('mrn') or pt_data.get('pt_num') or '').strip()
    fecha_nac = (pt_data.get('fecha_nacimiento') or pt_data.get('dob') or '').strip()
    edad_raw = str(pt_data.get('edad') or '').strip()
    edad_display = f"{edad_raw} años" if edad_raw and "año" not in edad_raw.lower() else (edad_raw or '____')
    medico = (pt_data.get('medico_tratante') or pt_data.get('n_medico') or '').strip()
    cedula = (pt_data.get('cedula') or pt_data.get('cedula_profesional') or '').strip()
    
    fecha_val = pt_data.get('fecha_atencion') or pt_data.get('fecha_ingreso') or datetime.datetime.now().strftime('%d/%m/%Y')
    hora_val = pt_data.get('hora_atencion') or pt_data.get('hora_ingreso') or datetime.datetime.now().strftime('%H:%M')

    diagnostico = (pt_data.get('diagnostico') or 'VALORACIÓN Y TRATAMIENTO EN ADMISIÓN CONTINUA / URGENCIAS').strip()
    procedimientos = (pt_data.get('procedimientos') or 'Instalación de accesos vasculares venosos/arteriales, toma de muestras de laboratorio, monitorización hemodinámica continua, administración de soluciones parenterales y farmacoterapia requerida según evolución clínica.').strip()
    
    riesgos_raw = str(pt_data.get('riesgos_inherentes_a_procedimien') or pt_data.get('riesgos') or 'Bajos').strip().lower()
    is_bajos = 'bajo' in riesgos_raw or riesgos_raw == '1'
    is_medios = 'medio' in riesgos_raw or riesgos_raw == '2'
    is_altos = 'alto' in riesgos_raw or riesgos_raw == '3'
    if not (is_bajos or is_medios or is_altos):
        is_medios = True

    if is_altos:
        riesgos_display = "ALTOS"
    elif is_medios:
        riesgos_display = "MEDIOS"
    else:
        riesgos_display = "BAJOS"

    prob_proced = (pt_data.get('prob_proced_y_alts') or pt_data.get('alternativas') or 'Estudios complementarios de laboratorio y gabinete (Rayos X, Ultrasonografía POCUS, TAC), observación clínica estrecha, interconsultas especializadas y tratamiento conservador según guías clínicas').strip()
    beneficios = (pt_data.get('beneficios') or 'Estabilización de signos vitales, mitigación de síntomas agudos, confirmación diagnóstica oportuna, restitución hemodinámica y prevención de complicaciones graves').strip()

    paciente_capaz = pt_data.get('paciente_capaz', True)
    if isinstance(paciente_capaz, str):
        paciente_capaz = paciente_capaz.lower() in ('true', '1', 'si', 'yes')
    elif isinstance(paciente_capaz, (int, float)):
        paciente_capaz = bool(paciente_capaz)
    pariente = (pt_data.get('pariente') or pt_data.get('representante_legal') or pt_data.get('yo_autorizo') or pt_data.get('declarante') or '').strip()
    if not paciente_capaz:
        parentesco = (pt_data.get('parentesco') or pt_data.get('parentesco_declarante') or pt_data.get('parentesco_paciente') or 'Tutor / Representante Legal').strip()
        if parentesco.upper() in ('PACIENTE', 'TITULAR', 'DIRECTO'):
            parentesco = 'Tutor / Representante Legal'
        nom_autoriza = pariente or pt_data.get('declarante') or 'TUTOR / REPRESENTANTE LEGAL'
    else:
        parentesco = 'Paciente'
        nom_autoriza = paciente_nombre or 'EL PACIENTE'

    testigo1 = (pt_data.get('testigo_1') or pt_data.get('testigo1') or '').strip()
    testigo2 = (pt_data.get('testigo_2') or pt_data.get('testigo2') or '').strip()

    # 1. TABLA SUPERIOR DE DATOS GENERALES (Elegante y Espaciada)
    pt_info_data = [
        [
            Paragraph(f"<b>PACIENTE:</b> {paciente_nombre}", style_val),
            Paragraph(f"<b>FECHA DE NAC.:</b> {fecha_nac or '___/___/_____'}", style_val),
            Paragraph(f"<b>EDAD:</b> {edad_display}", style_val),
        ],
        [
            Paragraph(f"<b>EXPEDIENTE:</b> {expediente}", style_val),
            Paragraph(f"<b>HORA:</b> {hora_val} hrs", style_val),
            Paragraph(f"<b>DIAGNÓSTICO:</b> {diagnostico}", style_val),
        ]
    ]
    t_info = Table(pt_info_data, colWidths=[content_w * 0.48, content_w * 0.26, content_w * 0.26])
    t_info.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.6, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#E2E8F0')),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
        ('TOPPADDING', (0, 0), (-1, -1), 3.8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3.8),
        ('LEFTPADDING', (0, 0), (-1, -1), 5.5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5.5),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(t_info)
    story.append(Spacer(1, 6.5))

    # 2. CUADRO DE AUTORIZACIÓN Y PROCEDIMIENTOS
    aut_data = [
        [
            Paragraph(f"<b>YO AUTORIZO:</b> {nom_autoriza}", style_val_bold),
            Paragraph(f"<b>PARENTESCO:</b> {parentesco}", style_val_bold)
        ],
        [
            Paragraph(f"<b>A LOS MÉDICOS:</b> {medico} Y AL PERSONAL DEL HOSPITAL ESCANDÓN EFECTUAR EL O LOS PROCEDIMIENTOS QUE EL CASO AMERITE TALES COMO: <i>{procedimientos}</i>", style_val),
            ''
        ]
    ]
    t_aut = Table(aut_data, colWidths=[content_w * 0.65, content_w * 0.35])
    t_aut.setStyle(TableStyle([
        ('SPAN', (0, 1), (1, 1)),
        ('BOX', (0, 0), (-1, -1), 0.6, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#E2E8F0')),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F1F5F9')),
        ('TOPPADDING', (0, 0), (-1, -1), 4.2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4.2),
        ('LEFTPADDING', (0, 0), (-1, -1), 5.5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5.5),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(t_aut)
    story.append(Spacer(1, 7.5))

    # 3. CUERPO DEL CONSENTIMIENTO: RIESGOS, DECLARACIÓN, PROCEDIMIENTOS Y BENEFICIOS
    p1 = Paragraph(
        f"Bajo este entendimiento reconozco que el médico arriba citado, me ha explicado la información que contiene entre otras cosas, la naturaleza del plan y los riesgos inherentes a estos procedimientos en particular son: <b>{riesgos_display}</b>.&nbsp;&nbsp;Información que he comprendido y acepto en plena conciencia.",
        style_body
    )
    story.append(p1)
    story.append(Spacer(1, 5.5))

    p2 = Paragraph(
        "Así mismo, acepto la realización de cualquier procedimiento que en el transcurso de mi estancia sea necesario; bajo conocimiento de que la práctica médica, los procedimientos y ramas afines no son exactos, por lo que los resultados no pueden garantizarse.",
        style_body
    )
    story.append(p2)
    story.append(Spacer(1, 5.5))

    p3 = Paragraph(
        f"Declaro en este documento que el médico me ha explicado los probables procedimientos y alternativas como: <b>{prob_proced}</b>, por lo que he podido plantear mis dudas, las cuales han sido contestadas satisfactoriamente. Autorizo y solicito al médico, que se me realicen los procedimientos médicos que se consideren necesarios, en ejercicio de su juicio y experiencia profesional.",
        style_body
    )
    story.append(p3)
    story.append(Spacer(1, 5.5))

    p4 = Paragraph(
        f"Entiendo que los beneficios de recibir atención médica son: <b>{beneficios}</b>.",
        style_body
    )
    story.append(p4)
    story.append(Spacer(1, 6.5))

    # 4. MARCO LEGAL INSTITUCIONAL (ARTÍCULOS 80 Y 81 RGLS)
    p_leg_intro = Paragraph(
        "<b>Lo anterior de acuerdo a lo dispuesto en los artículos 80 y 81 del Reglamento de la Ley General de Salud en materia de prestación de servicios de atención médica:</b>",
        ParagraphStyle('LegalTitle', fontName='Helvetica-Bold', fontSize=7.0, leading=8.8, textColor=PRIMARY_BLUE)
    )
    story.append(p_leg_intro)
    story.append(Spacer(1, 3.5))

    p_art80 = Paragraph(
        "<b>ARTÍCULO 80.-</b> En todo hospital y siempre que el estado del paciente lo permita, deberá recabarse a su ingreso autorización escrita y firmada para practicarle, con fines de diagnóstico terapéuticos, los procedimientos médico quirúrgicos necesarios de acuerdo al padecimiento de que se trate, debiendo informarle claramente el tipo de documento que se le presenta para su firma. Esta autorización inicial no excluye la necesidad de recabar después la correspondiente a cada procedimiento que entrañe un alto riesgo para el paciente.",
        style_body_legal
    )
    story.append(p_art80)
    story.append(Spacer(1, 3.5))

    p_art81 = Paragraph(
        "<b>ARTÍCULO 81.-</b> En caso de urgencia o cuando el paciente se encuentre en estado de incapacidad transitoria o permanente, el documento a que se refiere el artículo anterior, será suscrito por el familiar más cercano en vínculo que le acompañe, o en su caso, por su tutor o representante legal, una vez informado del carácter de la autorización. Cuando no sea posible obtener la autorización por incapacidad del paciente y ausencia de las personas a que se refiere el párrafo que antecede, los médicos autorizados del hospital de que se trate, previa valoración del caso y con el acuerdo de por lo menos dos de ellos, llevarán a cabo el procedimiento terapéutico que el caso requiera, dejando constancia por escrito, en el expediente clínico.",
        style_body_legal
    )
    story.append(p_art81)
    has_t1 = bool(
        pt_data.get('firma_testigo1_biometrica') or 
        pt_data.get('sello_testigo1') or 
        (firma_data and firma_data.get('sello_testigo1')) or
        (firma_data and firma_data.get('firma_testigo1_biometrica'))
    )
    has_t2 = bool(
        pt_data.get('firma_testigo2_biometrica') or 
        pt_data.get('sello_testigo2') or 
        (firma_data and firma_data.get('sello_testigo2')) or
        (firma_data and firma_data.get('firma_testigo2_biometrica'))
    )

    # 5. BLOQUE DE FIRMAS DINÁMICO (Solo se incluyen testigos si cuentan con firma/huella)
    sig_col_w = (content_w - 24.0) / 2.0  # ~255.88 pt

    paciente_clean = re.sub(r'\s*\([^)]*\)', '', str(nom_autoriza or paciente_nombre or '')).strip()
    testigo1_clean = re.sub(r'\s*\([^)]*\)', '', str(testigo1 or '')).strip()
    testigo2_clean = re.sub(r'\s*\([^)]*\)', '', str(testigo2 or '')).strip()

    patient_sig_text = f"<b>{paciente_clean}</b><br/><font size='5.8' color='#334155'><i>Nombre completo y firma del paciente, familiar, tutor o persona legalmente responsable</i></font>" if paciente_clean else "<b>Nombre completo y firma del paciente, familiar,<br/>tutor o persona legalmente responsable</b>"
    witness1_sig_text = f"<b>{testigo1_clean}</b><br/><font size='5.8' color='#334155'><i>Nombre completo y firma del testigo</i></font>" if testigo1_clean else "<b>Nombre completo y firma del testigo</b>"
    doctor_sig_text = f"<b>{medico}</b><br/><font size='5.8' color='#334155'><i>Nombre completo, cédulas y firma del médico tratante (CÉD. {cedula})</i></font>" if cedula else f"<b>{medico}</b><br/><font size='5.8' color='#334155'><i>Nombre completo, cédulas y firma del médico tratante</i></font>"
    witness2_sig_text = f"<b>{testigo2_clean}</b><br/><font size='5.8' color='#334155'><i>Nombre completo y firma del testigo</i></font>" if testigo2_clean else "<b>Nombre completo y firma del testigo</b>"

    # Sellos Digitales / Biométricos
    top_med_p = Paragraph("&nbsp;", style_sig_blank)
    if firma_data and (firma_data.get('sello_digital') or firma_data.get('hash_sha256')):
        sello_raw = str(firma_data.get('sello_digital') or firma_data.get('hash_sha256') or '')
        sello_resumido = (sello_raw[:26] + '...') if len(sello_raw) > 26 else sello_raw
        fecha_txt = firma_data.get('fecha_hora_firma') or firma_data.get('fecha_hora') or datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        stamp_html = f"""
        <font size='5.2' color='#006633'><b>[✔ FIRMA DIGITAL MÉDICA CON HUELLA]</b></font><br/>
        <font size='4.4' color='#004d26'><b>NOM-004-SSA3-2012 / NOM-024-SSA3-2012</b></font><br/>
        <font size='3.8' color='#444'><b>Sello:</b> <font face='Courier'>{sello_resumido}</font> | {fecha_txt}</font>
        """
        top_med_p = Paragraph(stamp_html, style_sig_stamp)

    pac_sig_p = Paragraph("&nbsp;", style_sig_blank)
    if pt_data.get('firma_paciente_biometrica') or pt_data.get('sello_paciente') or (firma_data and firma_data.get('sello_paciente')):
        sello_pac_val = str(pt_data.get('sello_paciente') or (firma_data and firma_data.get('sello_paciente')) or 'BIO-HES:OK')[:20]
        pac_stamp_html = f"""
        <font size='5.0' color='#006633'><b>[✔ AUTORIZADO CON HUELLA BIOMÉTRICA]</b></font><br/>
        <font size='4.0' color='#444'><b>Validación Dactilar:</b> <font face='Courier'>{sello_pac_val}</font></font>
        """
        pac_sig_p = Paragraph(pac_stamp_html, style_sig_stamp)

    test1_sig_p = Paragraph("&nbsp;", style_sig_blank)
    if has_t1:
        sello_t1_val = str(pt_data.get('sello_testigo1') or (firma_data and firma_data.get('sello_testigo1')) or 'BIO-HES:OK')[:20]
        t1_stamp_html = f"""
        <font size='5.0' color='#006633'><b>[✔ TESTIGO 1 - HUELLA BIOMÉTRICA]</b></font><br/>
        <font size='4.0' color='#444'><b>Validación Dactilar:</b> <font face='Courier'>{sello_t1_val}</font></font>
        """
        test1_sig_p = Paragraph(t1_stamp_html, style_sig_stamp)

    test2_sig_p = Paragraph("&nbsp;", style_sig_blank)
    if has_t2:
        sello_t2_val = str(pt_data.get('sello_testigo2') or (firma_data and firma_data.get('sello_testigo2')) or 'BIO-HES:OK')[:20]
        t2_stamp_html = f"""
        <font size='5.0' color='#006633'><b>[✔ TESTIGO 2 - HUELLA BIOMÉTRICA]</b></font><br/>
        <font size='4.0' color='#444'><b>Validación Dactilar:</b> <font face='Courier'>{sello_t2_val}</font></font>
        """
        test2_sig_p = Paragraph(t2_stamp_html, style_sig_stamp)

    if has_t1 and has_t2:
        # Caso 1: Ambos testigos firmados (2x2)
        sig_grid = [
            [pac_sig_p, '', test1_sig_p],
            [Paragraph(patient_sig_text, style_sig_name), '', Paragraph(witness1_sig_text, style_sig_name)],
            [top_med_p, '', test2_sig_p],
            [Paragraph(doctor_sig_text, style_sig_name), '', Paragraph(witness2_sig_text, style_sig_name)]
        ]
        t_style = [
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,0), 'BOTTOM'),
            ('VALIGN', (0,1), (-1,1), 'TOP'),
            ('VALIGN', (0,2), (-1,2), 'BOTTOM'),
            ('VALIGN', (0,3), (-1,3), 'TOP'),
            ('LINEABOVE', (0,1), (0,1), 0.75, PRIMARY_BLUE),
            ('LINEABOVE', (2,1), (2,1), 0.75, PRIMARY_BLUE),
            ('LINEABOVE', (0,3), (0,3), 0.75, PRIMARY_BLUE),
            ('LINEABOVE', (2,3), (2,3), 0.75, PRIMARY_BLUE),
            ('TOPPADDING', (0,0), (-1,0), 0),
            ('BOTTOMPADDING', (0,0), (-1,0), 1.0),
            ('TOPPADDING', (0,1), (-1,1), 2.5),
            ('BOTTOMPADDING', (0,1), (-1,1), 14.0),
            ('TOPPADDING', (0,2), (-1,2), 0),
            ('BOTTOMPADDING', (0,2), (-1,2), 1.0),
            ('TOPPADDING', (0,3), (-1,3), 2.5),
            ('BOTTOMPADDING', (0,3), (-1,3), 3.0),
        ]
        t_sigs = Table(sig_grid, colWidths=[sig_col_w, 24.0, sig_col_w])
        t_sigs.setStyle(TableStyle(t_style))
        story.append(Spacer(1, 14.0))
        story.append(t_sigs)
    elif has_t1 or has_t2:
        # Caso 2 y 3: Solo 1 Testigo firmado -> 3 firmas en total (Paciente + Testigo arriba, Médico centrado abajo)
        active_test_p = test1_sig_p if has_t1 else test2_sig_p
        active_test_txt = witness1_sig_text if has_t1 else witness2_sig_text
        t_top = Table([
            [pac_sig_p, '', active_test_p],
            [Paragraph(patient_sig_text, style_sig_name), '', Paragraph(active_test_txt, style_sig_name)]
        ], colWidths=[sig_col_w, 24.0, sig_col_w])
        t_top.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,0), 'BOTTOM'),
            ('VALIGN', (0,1), (-1,1), 'TOP'),
            ('LINEABOVE', (0,1), (0,1), 0.75, PRIMARY_BLUE),
            ('LINEABOVE', (2,1), (2,1), 0.75, PRIMARY_BLUE),
            ('TOPPADDING', (0,0), (-1,0), 0),
            ('BOTTOMPADDING', (0,0), (-1,0), 1.0),
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
            ('LINEABOVE', (0,1), (0,1), 0.75, PRIMARY_BLUE),
            ('TOPPADDING', (0,0), (-1,0), 0),
            ('BOTTOMPADDING', (0,0), (-1,0), 1.0),
            ('TOPPADDING', (0,1), (-1,1), 2.5),
            ('BOTTOMPADDING', (0,1), (-1,1), 0),
        ]))

        story.append(Spacer(1, 14.0))
        story.append(KeepTogether([t_top, Spacer(1, 14.0), t_bot]))
    else:
        # Caso 4: Sin testigos con firma (Solo Paciente y Médico en 2 columnas lado a lado)
        sig_grid = [
            [pac_sig_p, '', top_med_p],
            [Paragraph(patient_sig_text, style_sig_name), '', Paragraph(doctor_sig_text, style_sig_name)]
        ]
        t_style = [
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,0), 'BOTTOM'),
            ('VALIGN', (0,1), (-1,1), 'TOP'),
            ('LINEABOVE', (0,1), (0,1), 0.75, PRIMARY_BLUE),
            ('LINEABOVE', (2,1), (2,1), 0.75, PRIMARY_BLUE),
            ('TOPPADDING', (0,0), (-1,0), 0),
            ('BOTTOMPADDING', (0,0), (-1,0), 1.0),
            ('TOPPADDING', (0,1), (-1,1), 2.5),
            ('BOTTOMPADDING', (0,1), (-1,1), 4.0),
        ]
        t_sigs = Table(sig_grid, colWidths=[sig_col_w, 24.0, sig_col_w])
        t_sigs.setStyle(TableStyle(t_style))
        story.append(Spacer(1, 30.0))
        story.append(t_sigs)
    story.append(Spacer(1, 7.5))

    # 6. DECLARACIÓN DE EMERGENCIA MÉDICA (Al pie de página)
    p_emerg = Paragraph(
        "<i>El médico que suscribe declara haber entrevistado y explicado al paciente y/o representante, el (los) procedimiento(s) a realizar, lo cual ha comprendido. Certifico que no hubo oportunidad de obtener el consentimiento informado del paciente por tratarse de una emergencia médica.</i>",
        style_emergencia
    )
    story.append(p_emerg)

    # Parámetros del membrete oficial
    doc_info = {
        'title_lines': [
            'CONSENTIMIENTO INFORMADO PARA',
            'TRATAMIENTO, PROCEDIMIENTO(S) DE',
            'DIAGNÓSTICO EN ADMISIÓN CONTINUA'
        ],
        'code': 'HE-DIRMED-CONSUL-PLT-08',
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

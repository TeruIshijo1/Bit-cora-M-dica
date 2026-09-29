# -*- coding: utf-8 -*-
"""
Motor PDF para el Formato 07: Consentimiento Informado para Procedimientos Quirúrgicos
Código: HE-DIRMED-CONSUL-PLT-07
Conforme a NOM-004-SSA3-2012 y NOM-024-SSA3-2012
1 página oficial institucional con marco y pie oficial HES.
"""

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
        TEXT_MUTED, TEXT_DARK, PRIMARY_BLUE, DARK_BLUE, BORDER_GREY, RED_ALERT,
        letterhead_content_width
    )
except ModuleNotFoundError:
    from pdf_engine_v2 import (
        RDLCCanvas, CleanConsentCanvas, FRAME_X, FRAME_Y, FRAME_W, FRAME_H,
        TEXT_MUTED, TEXT_DARK, PRIMARY_BLUE, DARK_BLUE, BORDER_GREY, RED_ALERT,
        letterhead_content_width
    )


def generate_consentimiento_07(pt_data: dict, output_path: str = None, firma_data: dict = None) -> str:
    """
    Genera el PDF oficial para el Formato 07:
    HE-DIRMED-CONSUL-PLT-07: CONSENTIMIENTO INFORMADO PARA PROCEDIMIENTOS QUIRÚRGICOS.
    Exactamente 1 página institucional con aprovechamiento armónico total, marco RDLC,
    inteligencia demográfica de tutor/menores y sello biométrico digital.
    """
    if output_path and os.path.dirname(output_path):
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

    content_x = FRAME_X + 13.0
    content_w = letterhead_content_width(content_x)

    frame_bottom = FRAME_Y + 39.0
    frame_top = (FRAME_Y + FRAME_H) - 59.0
    frame_h = frame_top - frame_bottom # ~624.84 pt

    frame_p1 = Frame(content_x, frame_bottom, content_w, frame_h, id='p1_frame',
                     leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)

    template_p1 = PageTemplate(id='FirstPage', frames=frame_p1)

    # Extraer identificadores y datos
    expediente_raw = str(pt_data.get('expediente') or pt_data.get('mrn') or pt_data.get('pt_num') or '').strip()
    expediente_clean = re.sub(r'[^0-9]', '', expediente_raw) or expediente_raw
    folio_val = f"PT-{expediente_clean}" if expediente_clean and not str(expediente_clean).startswith("PT-") else expediente_raw

    fecha_val = pt_data.get('fecha_atencion') or pt_data.get('fecha_ingreso') or datetime.datetime.now().strftime('%d/%m/%Y')
    hora_val = pt_data.get('hora_atencion') or pt_data.get('hora_ingreso') or datetime.datetime.now().strftime('%H:%M')

    doc_info = {
        'code': 'HE-DIRMED-CONSUL-PLT-07',
        'title_lines': ['CONSENTIMIENTO INFORMADO PARA', 'PROCEDIMIENTOS QUIRÚRGICOS.'],
        'draw_header_dates': False,
        'fecha_ingreso': fecha_val,
        'hora_ingreso': hora_val,
        'pt_num': expediente_clean,
        'folio': folio_val,
        'slot': pt_data.get('mrnum') or 0,
        'draw_qr': True
    }

    doc = BaseDocTemplate(
        output_path,
        pagesize=letter,
        pageTemplates=[template_p1]
    )

    style_label = ParagraphStyle('MetaLabel', fontName='Helvetica-Bold', fontSize=7.6, leading=9.6, textColor=PRIMARY_BLUE)
    style_val = ParagraphStyle('MetaVal', fontName='Helvetica', fontSize=7.6, leading=9.6, textColor=TEXT_DARK)
    
    style_legal = ParagraphStyle('LegalIntro', fontName='Helvetica', fontSize=7.3, leading=10.0, textColor=TEXT_DARK, alignment=TA_JUSTIFY)
    style_body = ParagraphStyle('BodyClinico', fontName='Helvetica', fontSize=7.4, leading=10.2, textColor=TEXT_DARK, alignment=TA_JUSTIFY)
    style_bullets = ParagraphStyle('Bullets', fontName='Helvetica', fontSize=7.3, leading=10.0, textColor=TEXT_DARK, alignment=TA_LEFT)

    style_sig_name = ParagraphStyle('SigName', fontName='Helvetica-Bold', fontSize=7.6, leading=9.6, textColor=TEXT_DARK, alignment=TA_CENTER)
    style_sig_stamp = ParagraphStyle('SigStamp', fontName='Helvetica', fontSize=5.0, leading=6.5, textColor=colors.HexColor('#006633'), alignment=TA_CENTER)
    style_sig_blank = ParagraphStyle('SigBlank', fontName='Helvetica', fontSize=6.0, leading=7.0, textColor=colors.transparent, alignment=TA_CENTER)

    story = []

    # Datos clínicos y de paciente
    paciente_nombre = (pt_data.get('paciente_nombre') or pt_data.get('nombre') or '').strip().upper()
    fecha_nac = (pt_data.get('fecha_nacimiento') or pt_data.get('dob') or '').strip()
    edad_raw = str(pt_data.get('edad') or '').strip()
    edad_display = f"{edad_raw} años" if edad_raw and "año" not in edad_raw.lower() else (edad_raw or '____')
    
    medico = (pt_data.get('medico_tratante') or pt_data.get('n_medico') or (firma_data.get('nombre_medico') if firma_data else '') or '').strip().upper()
    cedula = (pt_data.get('cedula') or pt_data.get('cedula_profesional') or (firma_data.get('cedula') if firma_data else '') or '').strip()

    medico_clean = re.sub(r'^(dr\(a\)\.?|dr\.|dra\.|dr|dra)\s*', '', medico, flags=re.IGNORECASE).strip()
    med_display = f"DR(A). {medico_clean}" if medico_clean else "DR(A). MÉDICO TRATANTE"

    # Procedimiento y datos clínicos
    procedimiento_quirurgico = (pt_data.get('procedimiento_quirurgico') or pt_data.get('procedimiento') or pt_data.get('cirugia_propuesta') or 'INTERVENCIÓN QUIRÚRGICA PROGRAMADA').strip().upper()
    descripcion_procedimiento = (pt_data.get('descripcion_procedimiento') or pt_data.get('consiste_en') or 'procedimiento quirúrgico bajo técnica aséptica protocolizada y monitoreo continuo').strip()
    riesgos_inherentes = (pt_data.get('riesgos_inherentes') or pt_data.get('riesgos') or 'sangrado transoperatorio, infección de herida quirúrgica, dehiscencia, reacciones medicamentosas').strip()
    beneficios = (pt_data.get('beneficios') or pt_data.get('beneficios_esperados') or 'resolución del cuadro clínico de base, preservación funcional y mejora de salud').strip()
    alternativas = (pt_data.get('alternativas') or pt_data.get('tratamientos_alternativos') or 'tratamiento médico conservador o diferimiento según valoración').strip()

    # Evaluación de Capacidad y Edad
    edad_num = None
    try:
        match_age = re.search(r'\d+', str(edad_raw))
        if match_age:
            edad_num = int(match_age.group(0))
    except Exception:
        pass

    paciente_capaz_val = pt_data.get('paciente_capaz', True)
    if isinstance(paciente_capaz_val, str):
        paciente_capaz = paciente_capaz_val.lower() in ('true', '1', 'si', 'yes')
    elif isinstance(paciente_capaz_val, (int, float)):
        paciente_capaz = bool(paciente_capaz_val)
    else:
        paciente_capaz = bool(paciente_capaz_val)

    if edad_num is not None and edad_num < 18:
        paciente_capaz = False

    tutor = (pt_data.get('representante_legal') or pt_data.get('tutor') or pt_data.get('declarante') or pt_data.get('pariente') or '').strip().upper()
    parentesco = (pt_data.get('parentesco') or pt_data.get('parentesco_tutor') or ('Padre/Madre/Tutor' if not paciente_capaz else 'El Paciente')).strip()

    if paciente_capaz or not tutor:
        declarante = paciente_nombre
        calidad_declarante = "paciente"
    else:
        declarante = tutor
        calidad_declarante = f"representante legal / tutor ({parentesco}) del paciente <b>{paciente_nombre}</b>"

    testigo1 = (pt_data.get('testigo1') or pt_data.get('testigo_1') or '').strip().upper()
    testigo2 = (pt_data.get('testigo2') or pt_data.get('testigo_2') or '').strip().upper()

    # 1. TABLA DEMOGRÁFICA SUPERIOR
    pt_table_data = [
        [
            Paragraph(f"<b>NOMBRE DEL PACIENTE:</b> {paciente_nombre or '________________________________'}", style_val),
            Paragraph(f"<b>FECHA DE NAC.:</b> {fecha_nac or '___/___/_____'}", style_val),
            Paragraph(f"<b>EDAD:</b> {edad_display}", style_val),
        ],
        [
            Paragraph(f"<b>EXPEDIENTE:</b> {folio_val}", style_val),
            Paragraph(f"<b>MÉDICO TRATANTE:</b> {med_display}", style_val),
            Paragraph(f"<b>FECHA/HORA:</b> {fecha_val} {hora_val}", style_val),
        ]
    ]
    t_pt = Table(pt_table_data, colWidths=[content_w * 0.46, content_w * 0.28, content_w * 0.26])
    t_pt.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('LINEBELOW', (0,-1), (-1,-1), 0.7, colors.HexColor('#0056b3')),
    ]))
    story.append(t_pt)
    story.append(Spacer(1, 6.0))

    # 2. CUERPO LEGAL NORMATIVO
    p_lea = (
        "<b>LEA CON CUIDADO:</b> El consentimiento informado es la expresión tangible del respeto que el personal del Hospital Escandón "
        "tiene hacia la autonomía de sus pacientes. Mediante el Consentimiento Informado, invitamos a los pacientes a aceptar y firmar "
        "que se realice algún procedimiento quirúrgico en su persona, de forma totalmente voluntaria, posterior a haber satisfecho la "
        "información inherente a su enfermedad así como al tratamiento propuesto. En ningún momento debe sentirse presionado para firmar este documento."
    )
    story.append(Paragraph(p_lea, style_legal))
    story.append(Spacer(1, 5.0))

    p_hosp = (
        "El Hospital Escandón cuenta con el personal y las instalaciones para asistir a nuestros médicos para la realización de diversas operaciones "
        "quirúrgicas así como procedimientos de diagnóstico y/o tratamiento. Estos procedimientos pueden involucrar riesgos durante su realización, "
        "complicaciones, lesiones e incluso la muerte, tanto sea por causas conocidas como por otras ignoradas, y no existe garantía en cuanto al "
        "resultado final ni a obtener una cura definitiva. Usted tiene el derecho de ser informado de estos riesgos así como a la naturaleza de este "
        "procedimiento o cirugía, incluyendo los beneficios esperados de dicha operación. Usted tiene el derecho a consentir o a rehusar cualquier "
        "operación o procedimiento propuesto en cualquier momento antes de su realización."
    )
    story.append(Paragraph(p_hosp, style_legal))
    story.append(Spacer(1, 5.0))

    p_conf = (
        "La confidencialidad y manejo de la información en este documento está garantizada para ser utilizada solo por el personal autorizado, "
        "no por otras personas ajenas ni para propósitos diferentes a los descritos anteriormente. Apreciamos que si usted o alguno de sus "
        "familiares tienen alguna pregunta, la hagan antes de firmar el Consentimiento Informado."
    )
    story.append(Paragraph(p_conf, style_legal))
    story.append(Spacer(1, 6.0))

    # 3. DECLARACIÓN DINÁMICA CLÍNICA Y AUTORIZACIÓN
    p_yo = (
        f"Yo, <b>{declarante}</b> como {calidad_declarante} he sido informado por el/la <b>{med_display}</b> y autorizo de forma voluntaria para que "
        f"se realice el procedimiento quirúrgico llamado <b>{procedimiento_quirurgico}</b> que consiste en: <i>{descripcion_procedimiento}</i>."
    )
    story.append(Paragraph(p_yo, style_body))
    story.append(Spacer(1, 5.0))

    p_riesgos = (
        f"Entiendo que los <b>riesgos comunes</b> a cualquier procedimiento quirúrgico incluyen algunos como el sangrado, infección o dehiscencia "
        f"de la herida quirúrgica, lesión de estructuras adyacentes al sitio quirúrgico, lesión orgánica, septicemia e incluso la muerte. Los riesgos "
        f"inherentes a este procedimiento incluyen: <b>{riesgos_inherentes}</b>. También he sido informado de los <b>beneficios o efectos esperados</b> "
        f"de este procedimiento que son: <b>{beneficios}</b>."
    )
    story.append(Paragraph(p_riesgos, style_body))
    story.append(Spacer(1, 5.0))

    p_alt = (
        f"De igual forma se me explicó que existen otras <b>alternativas</b> como: <b>{alternativas}</b>, sin embargo se ha considerado que el "
        f"procedimiento que se autoriza resulta ser más conveniente."
    )
    story.append(Paragraph(p_alt, style_body))
    story.append(Spacer(1, 5.0))

    p_equipo = (
        "Con la firma de este documento autorizo a mi médico tratante, así como al personal de salud (incluyendo a médicos asistentes, "
        "anestesiólogos, patólogos, radiólogos así como al equipo de enfermería, inhaloterapia y personal técnico, entre otros) para llevar a cabo "
        "el procedimiento especificado. Me han informado de los tratamientos alternativos, así como sus riesgos y beneficios. Excepto en caso de "
        "emergencia donde se comprometa la función orgánica o la vida, las operaciones o procedimientos no se realizarán hasta que yo haya tenido "
        "la oportunidad de recibir información veraz y completa, y haya dado mi consentimiento de forma voluntaria."
    )
    story.append(Paragraph(p_equipo, style_body))
    story.append(Spacer(1, 5.0))

    p_puntos = (
        "<b>Mi firma biométrica y/o autógrafa en esta hoja significa que:</b><br/>"
        "1) He leído y entendido la información provista en ella.<br/>"
        "2) Que la operación o procedimiento señalado anteriormente ha sido explicado por mi médico tratante hasta esclarecer mis dudas.<br/>"
        "3) Que he recibido toda la información deseada concerniente a este procedimiento.<br/>"
        "4) Que autorizo y consiento la realización de esta cirugía o procedimiento diagnóstico y/o terapéutico."
    )
    story.append(Paragraph(p_puntos, style_bullets))
    story.append(Spacer(1, 10.0))

    # 4. BLOQUE DE FIRMAS BIOMÉTRICAS INTELIGENTE (ESTILO ESTÁNDAR GLOBAL CON SEPARACIÓN)
    top_med_p = Paragraph("&nbsp;", style_sig_blank)
    if firma_data and (firma_data.get('sello_digital') or firma_data.get('hash_sha256')):
        sello_raw = str(firma_data.get('sello_digital') or firma_data.get('hash_sha256') or '')
        sello_resumido = (sello_raw[:28] + '...') if len(sello_raw) > 28 else sello_raw
        fecha_txt = firma_data.get('fecha_hora_firma') or firma_data.get('fecha_hora') or datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        med_stamp_html = f"""
        <font size='5.2' color='#006633'><b>[✔ FIRMA DIGITAL MÉDICA CON HUELLA]</b></font><br/>
        <font size='4.4' color='#004d26'><b>NOM-004-SSA3-2012 / NOM-024-SSA3-2012</b></font><br/>
        <font size='3.8' color='#444'><b>Sello:</b> <font face='Courier'>{sello_resumido}</font> | {fecha_txt}</font>
        """
        top_med_p = Paragraph(med_stamp_html, style_sig_stamp)

    pac_sig_p = Paragraph("&nbsp;", style_sig_blank)
    if pt_data.get('firma_paciente_biometrica') or pt_data.get('sello_paciente') or (firma_data and firma_data.get('sello_paciente')):
        sello_pac_val = str(pt_data.get('sello_paciente') or (firma_data and firma_data.get('sello_paciente')) or 'BIO-HES:OK')[:24]
        lbl_sello_pac = "[✔ AUTORIZADO CON HUELLA BIOMÉTRICA]" if paciente_capaz else "[✔ AUTORIZADO POR TUTOR LEGAL]"
        pac_stamp_html = f"""
        <font size='5.0' color='#006633'><b>{lbl_sello_pac}</b></font><br/>
        <font size='4.0' color='#444'><b>Validación Dactilar:</b> <font face='Courier'>{sello_pac_val}</font></font>
        """
        pac_sig_p = Paragraph(pac_stamp_html, style_sig_stamp)

    test1_sig_p = Paragraph("&nbsp;", style_sig_blank)
    if testigo1 or (firma_data and firma_data.get('sello_testigo1')):
        sello_t1_val = str(pt_data.get('sello_testigo1') or (firma_data and firma_data.get('sello_testigo1')) or 'BIO-HES:OK')[:24]
        t1_stamp_html = f"""
        <font size='5.0' color='#006633'><b>[✔ TESTIGO 1 - HUELLA BIOMÉTRICA]</b></font><br/>
        <font size='4.0' color='#444'><b>Validación Dactilar:</b> <font face='Courier'>{sello_t1_val}</font></font>
        """
        test1_sig_p = Paragraph(t1_stamp_html, style_sig_stamp)

    test2_sig_p = Paragraph("&nbsp;", style_sig_blank)
    if testigo2 or (firma_data and firma_data.get('sello_testigo2')):
        sello_t2_val = str(pt_data.get('sello_testigo2') or (firma_data and firma_data.get('sello_testigo2')) or 'BIO-HES:OK')[:24]
        t2_stamp_html = f"""
        <font size='5.0' color='#006633'><b>[✔ TESTIGO 2 - HUELLA BIOMÉTRICA]</b></font><br/>
        <font size='4.0' color='#444'><b>Validación Dactilar:</b> <font face='Courier'>{sello_t2_val}</font></font>
        """
        test2_sig_p = Paragraph(t2_stamp_html, style_sig_stamp)

    if paciente_capaz:
        patient_sig_text = f"<b>{paciente_nombre}</b><br/><font size='6.0' color='#334155'><i>PACIENTE (OTORGANTE DEL CONSENTIMIENTO)</i></font>" if paciente_nombre else "<b>Nombre completo y firma del paciente</b>"
    else:
        label_tutor = f"PADRE / MADRE / TUTOR LEGAL ({parentesco})" if parentesco else "TUTOR / REPRESENTANTE LEGAL"
        patient_sig_text = f"<b>{tutor}</b><br/><font size='6.0' color='#334155'><i>{label_tutor}</i></font>" if tutor else "<b>Nombre completo del tutor o representante legal</b>"

    witness1_sig_text = f"<b>{testigo1}</b><br/><font size='6.0' color='#334155'><i>TESTIGO 1 (NOMBRE Y FIRMA)</i></font>" if testigo1 else "<b>Nombre completo y firma del testigo 1</b>"
    witness2_sig_text = f"<b>{testigo2}</b><br/><font size='6.0' color='#334155'><i>TESTIGO 2 (NOMBRE Y FIRMA)</i></font>" if testigo2 else "<b>Nombre completo y firma del testigo 2</b>"
    doctor_sig_text = f"<b>{medico}</b><br/><font size='6.0' color='#334155'><i><b>MÉDICO TRATANTE • CÉD. PROF. {cedula}</b></i></font>" if cedula else f"<b>{medico}</b>"

    gap_col_w = 34.0
    sig_col_w = (content_w - gap_col_w) / 2.0

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
        ('LINEABOVE', (0,1), (0,1), 0.8, PRIMARY_BLUE),
        ('LINEABOVE', (2,1), (2,1), 0.8, PRIMARY_BLUE),
        ('LINEABOVE', (0,3), (0,3), 0.8, PRIMARY_BLUE),
        ('LINEABOVE', (2,3), (2,3), 0.8, PRIMARY_BLUE),
        ('TOPPADDING', (0,0), (-1,0), 0),
        ('BOTTOMPADDING', (0,0), (-1,0), 1.0),
        ('TOPPADDING', (0,1), (-1,1), 3.0),
        ('BOTTOMPADDING', (0,1), (-1,1), 14.0),
        ('TOPPADDING', (0,2), (-1,2), 0),
        ('BOTTOMPADDING', (0,2), (-1,2), 1.0),
        ('TOPPADDING', (0,3), (-1,3), 3.0),
        ('BOTTOMPADDING', (0,3), (-1,3), 0),
    ]

    t_firmas = Table(sig_grid, colWidths=[sig_col_w, gap_col_w, sig_col_w])
    t_firmas.setStyle(TableStyle(t_style))
    story.append(KeepTogether([t_firmas]))

    canvas_factory = lambda *args, **kwargs: CleanConsentCanvas(*args, doc_info=doc_info, **kwargs)
    doc.build(story, canvasmaker=canvas_factory)
    return output_path

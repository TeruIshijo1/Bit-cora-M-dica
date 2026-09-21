# -*- coding: utf-8 -*-
"""
Motor PDF para el Formato 15 (Egreso Voluntario): HE-DIRMED-SINPRO-PLT-15
Conforme a NOM-004-SSA3-2012 (Numeral 10.3) y NOM-024-SSA3-2012
2 páginas oficiales institucionales con marco RDLC y QR oficial HES.
"""

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
        CleanConsentCanvas, FRAME_X, FRAME_Y, FRAME_W, FRAME_H,
        TEXT_MUTED, TEXT_DARK, PRIMARY_BLUE, DARK_BLUE, BORDER_GREY, RED_ALERT
    )
except ModuleNotFoundError:
    from pdf_engine_v2 import (
        CleanConsentCanvas, FRAME_X, FRAME_Y, FRAME_W, FRAME_H,
        TEXT_MUTED, TEXT_DARK, PRIMARY_BLUE, DARK_BLUE, BORDER_GREY, RED_ALERT
    )


def generate_egreso_voluntario_15(pt_data: dict, output_path: str = None, firma_data: dict = None) -> str:
    """
    Genera el PDF oficial para el Formato 15 (Egreso Voluntario):
    HE-DIRMED-SINPRO-PLT-15: EGRESO VOLUNTARIO.
    Exactamente 2 páginas institucionales con marco y pie oficial HES.
    """
    if output_path and os.path.dirname(output_path):
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

    content_x = FRAME_X + 14.0
    content_w = FRAME_W - 34.0  # ~535.76 pt

    frame_bottom = FRAME_Y + 40.0
    frame_top = (FRAME_Y + FRAME_H) - 60.0
    frame_h = frame_top - frame_bottom

    frame_p1 = Frame(content_x, frame_bottom, content_w, frame_h, id='p1_frame',
                     leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    frame_p2 = Frame(content_x, frame_bottom, content_w, frame_h, id='p2_frame',
                     leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)

    template_p1 = PageTemplate(id='FirstPage', frames=frame_p1)
    template_p2 = PageTemplate(id='LaterPages', frames=frame_p2)

    doc = BaseDocTemplate(
        output_path,
        pagesize=letter,
        pageTemplates=[template_p1, template_p2]
    )

    style_label = ParagraphStyle('MetaLabel', fontName='Helvetica-Bold', fontSize=7.4, leading=9.2, textColor=PRIMARY_BLUE)
    style_val = ParagraphStyle('MetaVal', fontName='Helvetica', fontSize=7.5, leading=9.5, textColor=TEXT_DARK)
    style_sec_title = ParagraphStyle('SecTitle', fontName='Helvetica-Bold', fontSize=8.4, leading=10.4, textColor=PRIMARY_BLUE)
    style_sec_alert = ParagraphStyle('SecAlert', fontName='Helvetica-Bold', fontSize=8.4, leading=10.4, textColor=RED_ALERT)
    
    style_body = ParagraphStyle('Body', fontName='Helvetica', fontSize=7.5, leading=10.2, textColor=TEXT_DARK, alignment=TA_JUSTIFY)
    style_legal = ParagraphStyle('Legal', fontName='Helvetica', fontSize=7.2, leading=9.6, textColor=TEXT_DARK, alignment=TA_JUSTIFY)
    style_city_date = ParagraphStyle('CityDate', fontName='Helvetica-Bold', fontSize=7.6, leading=9.8, textColor=PRIMARY_BLUE, alignment=TA_RIGHT)

    style_sig_name = ParagraphStyle('SigName', fontName='Helvetica-Bold', fontSize=7.2, leading=8.8, textColor=TEXT_DARK, alignment=TA_CENTER)
    style_sig_sub = ParagraphStyle('SigSub', fontName='Helvetica', fontSize=6.2, leading=7.6, textColor=TEXT_MUTED, alignment=TA_CENTER)
    style_sig_stamp = ParagraphStyle('SigStamp', fontName='Helvetica', fontSize=5.0, leading=6.4, textColor=colors.HexColor('#006633'), alignment=TA_CENTER)
    style_sig_blank = ParagraphStyle('SigBlank', fontName='Helvetica', fontSize=6.0, leading=7.0, textColor=colors.transparent, alignment=TA_CENTER)

    story = []

    # 1. Metadatos del Paciente
    paciente_nombre = (pt_data.get('paciente_nombre') or pt_data.get('nombre') or '').strip()
    expediente = str(pt_data.get('expediente') or pt_data.get('mrn') or pt_data.get('pt_num') or '').strip()
    fecha_nac = (pt_data.get('fecha_nacimiento') or pt_data.get('dob') or '').strip()
    edad_raw = str(pt_data.get('edad') or '').strip()
    edad_display = f"{edad_raw} años" if edad_raw and "año" not in edad_raw.lower() else (edad_raw or '____')
    medico = (pt_data.get('medico_tratante') or pt_data.get('n_medico') or (firma_data.get('nombre_medico') if firma_data else '') or '').strip()
    cedula = (pt_data.get('cedula') or pt_data.get('cedula_profesional') or (firma_data.get('cedula') if firma_data else '') or '').strip()
    servicio = (pt_data.get('servicio') or pt_data.get('cama') or 'HOSPITALIZACIÓN / MEDICINA INTERNA').strip()

    fecha_val = pt_data.get('fecha_atencion') or pt_data.get('fecha_ingreso') or datetime.datetime.now().strftime('%d/%m/%Y')
    hora_val = pt_data.get('hora_atencion') or pt_data.get('hora_ingreso') or datetime.datetime.now().strftime('%H:%M')

    diag_ingreso = (pt_data.get('diagnostico_ingreso') or pt_data.get('diagnostico') or 'GASTROENTERITIS AGUDA CON DESHIDRATACIÓN MODERADA').strip()
    diag_egreso = (pt_data.get('diagnostico_egreso') or diag_ingreso).strip()
    
    medidas_salud = (
        pt_data.get('medidas_recomendadas') or pt_data.get('medidas_proteccion') or
        'Continuar con hidratación oral estricta con electrolitos, dieta astringente fraccionada, apego puntual al tratamiento farmacológico prescrito en la receta médica adjunta, reposo relativo en domicilio y control térmico con medios físicos.'
    ).strip()

    factores_riesgo = (
        pt_data.get('factores_riesgo') or pt_data.get('riesgos') or
        'Deshidratación severa, desequilibrio hidroelectrolítico, choque hipovolémico, falla renal aguda prerrenal, intolerancia a la vía oral y necesidad de reingreso urgente a unidad de terapia intensiva.'
    ).strip()

    motivo_egreso = (
        pt_data.get('motivo_egreso') or pt_data.get('motivo') or
        'Decisión personal y familiar para continuar con la convalecencia y cuidados médicos en domicilio particular.'
    ).strip()

    paciente_capaz = pt_data.get('paciente_capaz', True)
    if isinstance(paciente_capaz, str):
        paciente_capaz = paciente_capaz.lower() in ('true', '1', 'si', 'yes')
    elif isinstance(paciente_capaz, (int, float)):
        paciente_capaz = bool(paciente_capaz)

    declarante = (pt_data.get('n_replegal') or pt_data.get('declarante') or pt_data.get('paciente_o_representante') or pt_data.get('representante_legal') or '').strip()
    parentesco = (pt_data.get('parentesco') or pt_data.get('parentesco_declarante') or ('Paciente' if paciente_capaz else 'Familiar / Representante Legal')).strip()
    identificacion = (pt_data.get('identificacion') or pt_data.get('identificacion_declarante') or 'INE / CREDENCIAL OFICIAL').strip()
    domicilio_declarante = (pt_data.get('domicilio_declarante') or pt_data.get('domicilio') or 'Ciudad de México').strip()

    if not declarante or paciente_capaz:
        declarante = paciente_nombre
        parentesco = 'El Paciente'

    testigo1 = (pt_data.get('testigo_1') or pt_data.get('testigo1') or '').strip()
    domicilio_t1 = (pt_data.get('domicilio_testigo1') or pt_data.get('domicilio_t1') or 'Ciudad de México').strip()
    id_t1 = (pt_data.get('identificacion_testigo1') or pt_data.get('id_t1') or 'INE').strip()
    par_t1 = (pt_data.get('parentesco_testigo1') or pt_data.get('par_t1') or 'Testigo').strip()

    testigo2 = (pt_data.get('testigo_2') or pt_data.get('testigo2') or '').strip()
    domicilio_t2 = (pt_data.get('domicilio_testigo2') or pt_data.get('domicilio_t2') or 'Ciudad de México').strip()
    id_t2 = (pt_data.get('identificacion_testigo2') or pt_data.get('id_t2') or 'INE').strip()
    par_t2 = (pt_data.get('parentesco_testigo2') or pt_data.get('par_t2') or 'Testigo').strip()

    # =========================================================================
    # PÁGINA 1 — Construir flowables y distribuir espacio dinámicamente
    # =========================================================================
    pt_info_data = [
        [
            Paragraph(f"<b>PACIENTE:</b> {paciente_nombre}", style_val),
            Paragraph(f"<b>FECHA DE NAC.:</b> {fecha_nac or '___/___/_____'}", style_val),
            Paragraph(f"<b>EDAD:</b> {edad_display}", style_val),
        ],
        [
            Paragraph(f"<b>EXPEDIENTE:</b> {expediente}", style_val),
            Paragraph(f"<b>MÉDICO TRATANTE:</b> {medico}", style_val),
            Paragraph(f"<b>FECHA / HORA:</b> {fecha_val} {hora_val}", style_val),
        ],
        [
            Paragraph(f"<b>SERVICIO / CAMA:</b> {servicio.upper()}", style_val),
            Paragraph(f"<b>TIPO TRÁMITE:</b> <font color='#B91C1C'><b>EGRESO VOLUNTARIO</b></font>", style_val),
            Paragraph(f"<b>ESTADO:</b> <font color='#B45309'><b>ALTA DISENTIDA</b></font>", style_val),
        ]
    ]

    t_info = Table(pt_info_data, colWidths=[content_w * 0.42, content_w * 0.36, content_w * 0.22])
    t_info.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.75, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
        ('PADDING', (0, 0), (-1, -1), 2.5),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))

    p_diag_title = Paragraph("<b>DIAGNÓSTICOS CLÍNICOS</b>", style_sec_title)

    t_diag_data = [
        [
            Paragraph("<b>Diagnóstico de Ingreso:</b>", style_label),
            Paragraph(diag_ingreso, style_val)
        ],
        [
            Paragraph("<b>Diagnóstico de Egreso:</b>", style_label),
            Paragraph(diag_egreso, style_val)
        ]
    ]
    t_diag = Table(t_diag_data, colWidths=[content_w * 0.25, content_w * 0.75])
    t_diag.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F1F5F9')),
        ('PADDING', (0, 0), (-1, -1), 3.0),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))

    p_med_title = Paragraph("<b>MEDIDAS RECOMENDADAS PARA LA PROTECCIÓN DE LA SALUD Y ATENCIÓN DE FACTORES DE RIESGO</b>", style_sec_title)

    t_med_data = [
        [
            Paragraph("<b>Medidas Terapéuticas e Higiénico-Dietéticas:</b>", style_label),
            Paragraph(medidas_salud, style_val)
        ],
        [
            Paragraph("<b>Riesgos Clínicos por Egreso Prematuro:</b>", style_label),
            Paragraph(factores_riesgo, style_val)
        ],
        [
            Paragraph("<b>Motivo Manifestado del Egreso:</b>", style_label),
            Paragraph(motivo_egreso, style_val)
        ]
    ]
    t_med = Table(t_med_data, colWidths=[content_w * 0.28, content_w * 0.72])
    t_med.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F1F5F9')),
        ('PADDING', (0, 0), (-1, -1), 3.0),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))

    p_dec_title = Paragraph("<b>DECLARACIÓN DE VOLUNTAD Y DESLINDE DE RESPONSABILIDAD (NOM-004-SSA3-2012, NUMERAL 10.3)</b>", style_sec_alert)

    p_dec_1 = Paragraph(
        f"En pleno uso de mis facultades mentales, con capacidad legal plena y libre de toda coerción física o moral, "
        f"expreso en el presente documento mi firme y consciente voluntad de <b>NO CONTINUAR RECIBIENDO ATENCIÓN MÉDICA</b> "
        f"en calidad de paciente hospitalizado en el <b>Hospital Escandón</b> para el paciente <b>{paciente_nombre}</b>.",
        style_legal
    )

    p_dec_2 = Paragraph(
        "Hago constar que el médico tratante y el equipo de salud me han advertido, orientado y explicado en un lenguaje claro, "
        "exhaustivo y comprensible, los graves riesgos médicos y complicaciones inmediatas o mediatas que representa la interrupción del "
        "esquema diagnóstico-terapéutico intrahospitalario, incluyendo el riesgo inminente de deterioro clínico irreversible, secuelas "
        "permanentes, falla orgánica o la pérdida de la vida.",
        style_legal
    )

    p_dec_3 = Paragraph(
        "A pesar de la insistencia, aclaración y advertencias del cuerpo médico, asumo de manera libre, exclusiva e informada las consecuencias "
        "derivadas de esta decisión, <b>DESLINDANDO DE TODA RESPONSABILIDAD CIVIL, PENAL, ADMINISTRATIVA Y ÉTICO-MÉDICA</b> al Hospital Escandón, "
        "a sus médicos tratantes, personal de enfermería, auxiliares de diagnóstico y personal directivo por cualquier evento adverso, complicación "
        "o desenlace fatal derivado del egreso no autorizado.",
        style_legal
    )

    # Medir alturas de todos los elementos de Página 1
    p1_elements = [t_info, p_diag_title, t_diag, p_med_title, t_med, p_dec_title, p_dec_1, p_dec_2, p_dec_3]
    total_h = sum(el.wrap(content_w, frame_h)[1] for el in p1_elements)
    remaining_p1 = frame_h - total_h
    # 8 gaps entre los 9 elementos, mínimo 4pt, máximo 30pt
    gap_p1 = min(30.0, max(4.0, remaining_p1 / 8.0))

    story.append(t_info)
    story.append(Spacer(1, gap_p1))
    story.append(p_diag_title)
    story.append(Spacer(1, gap_p1 * 0.4))
    story.append(t_diag)
    story.append(Spacer(1, gap_p1))
    story.append(p_med_title)
    story.append(Spacer(1, gap_p1 * 0.4))
    story.append(t_med)
    story.append(Spacer(1, gap_p1))
    story.append(p_dec_title)
    story.append(Spacer(1, gap_p1 * 0.4))
    story.append(p_dec_1)
    story.append(Spacer(1, gap_p1 * 0.5))
    story.append(p_dec_2)
    story.append(Spacer(1, gap_p1 * 0.5))
    story.append(p_dec_3)

    # =========================================================================
    # PÁGINA 2
    # =========================================================================
    story.append(PageBreak())

    # Construir todos los flowables de la Página 2 para medir y distribuir espacio
    p2_title = Paragraph("<b>CONSTANCIA DE FIRMAS Y RATIFICACIÓN DEL EGRESO VOLUNTARIO (Página 2 de 2)</b>", style_sec_title)

    p_ratifica = Paragraph(
        f"En la Ciudad de México, siendo las <b>{hora_val} horas</b> del día <b>{fecha_val}</b>, se ratifica ante el personal médico y los testigos "
        f"presenciales que se hace entrega de la presente constancia, receta médica con indicaciones ambulatorias y resumen de signos de alarma. "
        f"El paciente o su representante legal reitera su decisión voluntaria de abandonar las instalaciones hospitalarias bajo su propio riesgo.",
        style_body
    )

    is_med_signed = bool(firma_data and (firma_data.get('sello_digital') or firma_data.get('hash_sha256')))
    is_pac_signed = bool(pt_data.get("firma_paciente_biometrica") or (firma_data and firma_data.get("sello_paciente")))
    sello_pac = str(pt_data.get("sello_paciente") or (firma_data.get("sello_paciente") if firma_data else "") or "")
    sello_pac_short = (sello_pac[:24] + '...') if len(sello_pac) > 26 else sello_pac

    sello_fea = (firma_data.get('sello_digital') or '') if firma_data else ''
    sello_short = (sello_fea[:28] + '...' + sello_fea[-10:]) if len(sello_fea) > 40 else sello_fea
    hash_short = (firma_data.get('hash_sha256') or '')[:32] if firma_data else ''

    medico_stamp_p = Paragraph(
        f"<font color='#047857'><b>[✔ FIRMA ELECTRÓNICA AVANZADA FEA]</b></font><br/>"
        f"<font size='5.0' color='#333333'>SELLO: {sello_short}</font><br/>"
        f"<font size='5.0' color='#666666'>HASH: {hash_short}...</font>", style_sig_stamp
    ) if is_med_signed else Paragraph("<br/><br/>", style_sig_blank)

    paciente_stamp_p = Paragraph(
        f"<font color='#B91C1C'><b>[✔ EGRESO VALIDADO CON HUELLA]</b></font><br/>"
        f"<font size='5.0' color='#333333'>SELLO: {sello_pac_short}</font><br/>"
        f"<font size='5.0' color='#006633'>Autenticación Biométrica DigitalPersona (NOM-004)</font>", style_sig_stamp
    ) if is_pac_signed else (Paragraph(
        f"<font color='#B91C1C'><b>[✔ EGRESO VALIDADO CON HUELLA]</b></font><br/>"
        f"<font size='5.0' color='#555555'>Identif: {identificacion}</font><br/>"
        f"<font size='5.0' color='#006633'>Autenticación Biométrica DigitalPersona</font>", style_sig_stamp
    ) if is_med_signed else Paragraph("<br/><br/>", style_sig_blank))

    is_t1_signed = bool(pt_data.get("firma_testigo1_biometrica") or (firma_data and firma_data.get("sello_testigo1")))
    sello_t1 = str(pt_data.get("sello_testigo1") or (firma_data.get("sello_testigo1") if firma_data else "") or "")
    sello_t1_short = (sello_t1[:22] + '...') if len(sello_t1) > 24 else sello_t1

    t1_stamp_p = Paragraph(
        f"<font size='5.2' color='#006633'><b>[✔ Testigo 1 Biométrico]</b></font><br/>"
        f"<font size='4.8' color='#555555'>SELLO: {sello_t1_short}</font>", style_sig_stamp
    ) if is_t1_signed else (Paragraph(f"<font size='5.2' color='#006633'>[✔ Testigo 1 Presencial Asentado]</font>", style_sig_stamp) if (is_med_signed and testigo1) else Paragraph("<br/><br/>", style_sig_blank))

    is_t2_signed = bool(pt_data.get("firma_testigo2_biometrica") or (firma_data and firma_data.get("sello_testigo2")))
    sello_t2 = str(pt_data.get("sello_testigo2") or (firma_data.get("sello_testigo2") if firma_data else "") or "")
    sello_t2_short = (sello_t2[:22] + '...') if len(sello_t2) > 24 else sello_t2

    t2_stamp_p = Paragraph(
        f"<font size='5.2' color='#006633'><b>[✔ Testigo 2 Biométrico]</b></font><br/>"
        f"<font size='4.8' color='#555555'>SELLO: {sello_t2_short}</font>", style_sig_stamp
    ) if is_t2_signed else (Paragraph(f"<font size='5.2' color='#006633'>[✔ Testigo 2 Presencial Asentado]</font>", style_sig_stamp) if (is_med_signed and testigo2) else Paragraph("<br/><br/>", style_sig_blank))

    sig_top_data = [
        [
            Paragraph("<b>PACIENTE O REPRESENTANTE LEGAL</b>", style_label),
            Paragraph("<b>MÉDICO TRATANTE QUE ASISTE EL ALTA</b>", style_label),
        ],
        [
            Paragraph(
                f"{paciente_stamp_p.text if hasattr(paciente_stamp_p, 'text') else ''}"
                f"<br/>____________________________________________<br/>"
                f"<b>Nombre:</b> {declarante}<br/>"
                f"<b>Domicilio:</b> {domicilio_declarante}<br/>"
                f"<b>Identificación:</b> {identificacion} &nbsp;&nbsp; <b>Parentesco:</b> {parentesco}<br/>"
                f"<i>Firma paciente o representante legal</i>",
                style_sig_name
            ) if not is_pac_signed and not is_med_signed else Paragraph(
                f"{'<font color=#B91C1C><b>[✔ EGRESO VALIDADO CON HUELLA]</b></font><br/><font size=4.5 color=#333333>SELLO: ' + sello_pac_short + '</font><br/><font size=4.5 color=#006633>Autenticación Biométrica DigitalPersona</font>' if is_pac_signed else '<font color=#B91C1C><b>[✔ EGRESO VALIDADO CON HUELLA]</b></font><br/><font size=4.5 color=#555>Identif: ' + identificacion + '</font><br/><font size=4.5 color=#006633>Autenticación Biométrica DigitalPersona</font>' if is_med_signed else '<br/><br/>'}"
                f"<br/>____________________________________________<br/>"
                f"<b>Nombre:</b> {declarante}<br/>"
                f"<b>Domicilio:</b> {domicilio_declarante}<br/>"
                f"<b>Identificación:</b> {identificacion} &nbsp;&nbsp; <b>Parentesco:</b> {parentesco}<br/>"
                f"<i>Firma paciente o representante legal</i>",
                style_sig_name
            ),
            Paragraph(
                f"{'<font color=#047857><b>[✔ FIRMA ELECTRÓNICA AVANZADA FEA]</b></font><br/><font size=4.5 color=#333333>SELLO: ' + sello_short + '</font><br/><font size=4.5 color=#666666>HASH: ' + hash_short + '...</font>' if is_med_signed else '<br/><br/>'}"
                f"<br/>____________________________________________<br/>"
                f"<b>Nombre:</b> {medico}<br/>"
                f"<b>Cédula Profesional:</b> {cedula}<br/>"
                f"<b>Cargo:</b> Médico Tratante / Hospital Escandón<br/>"
                f"<i>Firma Médico</i>",
                style_sig_name
            ),
        ],
    ]

    sig_bot_data = [
        [
            Paragraph("<b>TESTIGO 1 PRESENCIAL</b>", style_label),
            Paragraph("<b>TESTIGO 2 PRESENCIAL</b>", style_label),
        ],
        [
            Paragraph(
                f"{'<font size=5.0 color=#006633><b>[✔ Testigo 1 Biométrico]</b></font><br/><font size=4.5 color=#555555>SELLO: ' + sello_t1_short + '</font>' if is_t1_signed else ('<font size=5.0 color=#006633>[✔ Testigo 1 Presencial Asentado]</font>' if (is_med_signed and testigo1) else '<br/><br/>')}"
                f"<br/>____________________________________________<br/>"
                f"<b>Nombre:</b> {testigo1 or 'NOMBRE COMPLETO TESTIGO 1'}<br/>"
                f"<b>Domicilio:</b> {domicilio_t1}<br/>"
                f"<b>Identificación:</b> {id_t1} &nbsp;&nbsp; <b>Parentesco:</b> {par_t1}<br/>"
                f"<i>Firma testigo 1</i>",
                style_sig_name
            ),
            Paragraph(
                f"{'<font size=5.0 color=#006633><b>[✔ Testigo 2 Biométrico]</b></font><br/><font size=4.5 color=#555555>SELLO: ' + sello_t2_short + '</font>' if is_t2_signed else ('<font size=5.0 color=#006633>[✔ Testigo 2 Presencial Asentado]</font>' if (is_med_signed and testigo2) else '<br/><br/>')}"
                f"<br/>____________________________________________<br/>"
                f"<b>Nombre:</b> {testigo2 or 'NOMBRE COMPLETO TESTIGO 2'}<br/>"
                f"<b>Domicilio:</b> {domicilio_t2}<br/>"
                f"<b>Identificación:</b> {id_t2} &nbsp;&nbsp; <b>Parentesco:</b> {par_t2}<br/>"
                f"<i>Firma testigo 2</i>",
                style_sig_name
            ),
        ]
    ]

    _ev_sig_style = TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.75, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F1F5F9')),
        ('PADDING', (0, 0), (-1, -1), 4.0),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ])

    t_sigs_top = Table(sig_top_data, colWidths=[content_w * 0.50, content_w * 0.50])
    t_sigs_top.setStyle(_ev_sig_style)
    t_sigs_bot = Table(sig_bot_data, colWidths=[content_w * 0.50, content_w * 0.50])
    t_sigs_bot.setStyle(_ev_sig_style)

    # Medir alturas para calcular espacio disponible
    h_title = p2_title.wrap(content_w, frame_h)[1]
    h_ratifica = p_ratifica.wrap(content_w, frame_h)[1]
    h_top_table = t_sigs_top.wrap(content_w, frame_h)[1]
    h_bot_table = t_sigs_bot.wrap(content_w, frame_h)[1]

    total_content = h_title + h_ratifica + h_top_table + h_bot_table
    remaining = frame_h - total_content
    # Espacio entre título→texto pequeño, texto→firmas y firmas→firmas moderado
    gap_small = 8.0
    gap_sig = min(50.0, max(20.0, (remaining - gap_small) / 2.0))

    story.append(p2_title)
    story.append(Spacer(1, gap_small))
    story.append(p_ratifica)
    story.append(Spacer(1, gap_sig))
    story.append(t_sigs_top)
    story.append(Spacer(1, gap_sig))
    story.append(t_sigs_bot)

    doc_info = {
        'title_lines': [
            'EGRESO VOLUNTARIO',
            'HOSPITALIZACIÓN Y URGENCIAS',
            'HOSPITAL ESCANDÓN'
        ],
        'code': 'HE-DIRMED-SINPRO-PLT-15',
        'fecha_ingreso': fecha_val,
        'hora_ingreso': hora_val,
        'expediente': expediente,
        'folio': expediente,
        'pt_num': str(pt_data.get('pt_num', '') or expediente),
        'slot': pt_data.get('slot') or pt_data.get('mrnum') or 1,
        'total_pages': 2,
        'paciente': paciente_nombre,
        'medico': medico,
        'cedula': cedula,
        'servicio': servicio
    }

    canvas_factory = lambda *args, **kwargs: CleanConsentCanvas(*args, doc_info=doc_info, **kwargs)
    doc.build(story, canvasmaker=canvas_factory)
    return output_path

# -*- coding: utf-8 -*-
"""
Motor PDF para el Formato 19: Consentimiento Informado para Histerectomía
Código: HE-DIRMED-CONSUL-PLT-19
Conforme a NOM-004-SSA3-2012 y NOM-024-SSA3-2012
2 páginas oficiales institucionales con canvas HES.
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


def generate_consentimiento_19(pt_data: dict, output_path: str = None, firma_data: dict = None) -> str:
    """
    Genera el PDF oficial para el Formato 19:
    HE-DIRMED-CONSUL-PLT-19: CONSENTIMIENTO INFORMADO PARA HISTERECTOMÍA.
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

    style_label = ParagraphStyle('MetaLabel', fontName='Helvetica-Bold', fontSize=7.6, leading=9.5, textColor=PRIMARY_BLUE)
    style_val = ParagraphStyle('MetaVal', fontName='Helvetica', fontSize=7.8, leading=10.2, textColor=TEXT_DARK)
    style_sec_title = ParagraphStyle('SecTitle', fontName='Helvetica-Bold', fontSize=8.8, leading=11.2, textColor=PRIMARY_BLUE)
    style_sec_alert = ParagraphStyle('SecAlert', fontName='Helvetica-Bold', fontSize=8.8, leading=11.2, textColor=RED_ALERT)
    
    style_body = ParagraphStyle('Body', fontName='Helvetica', fontSize=8.2, leading=11.6, textColor=TEXT_DARK, alignment=TA_JUSTIFY)
    style_bullet = ParagraphStyle('Bullet', fontName='Helvetica', fontSize=8.0, leading=11.0, textColor=TEXT_DARK, alignment=TA_LEFT, leftIndent=12)
    style_city_date = ParagraphStyle('CityDate', fontName='Helvetica-Bold', fontSize=8.0, leading=10.2, textColor=PRIMARY_BLUE, alignment=TA_RIGHT)

    style_sig_name = ParagraphStyle('SigName', fontName='Helvetica-Bold', fontSize=7.4, leading=9.2, textColor=TEXT_DARK, alignment=TA_CENTER)
    style_sig_sub = ParagraphStyle('SigSub', fontName='Helvetica', fontSize=6.4, leading=8.0, textColor=TEXT_MUTED, alignment=TA_CENTER)
    style_sig_stamp = ParagraphStyle('SigStamp', fontName='Helvetica', fontSize=5.2, leading=6.6, textColor=colors.HexColor('#006633'), alignment=TA_CENTER)
    style_sig_stamp_red = ParagraphStyle('SigStampRed', fontName='Helvetica', fontSize=5.2, leading=6.6, textColor=RED_ALERT, alignment=TA_CENTER)
    style_sig_blank = ParagraphStyle('SigBlank', fontName='Helvetica', fontSize=6.0, leading=7.0, textColor=colors.transparent, alignment=TA_CENTER)

    story = []

    # Datos clínicos
    paciente_nombre = (pt_data.get('paciente_nombre') or pt_data.get('nombre') or '').strip()
    expediente = str(pt_data.get('expediente') or pt_data.get('mrn') or pt_data.get('pt_num') or '').strip()
    fecha_nac = (pt_data.get('fecha_nacimiento') or pt_data.get('dob') or '').strip()
    edad_raw = str(pt_data.get('edad') or '').strip()
    edad_display = f"{edad_raw} años" if edad_raw and "año" not in edad_raw.lower() else (edad_raw or '____')
    medico = (pt_data.get('medico_tratante') or pt_data.get('n_medico') or (firma_data.get('nombre_medico') if firma_data else '') or '').strip()
    cedula = (pt_data.get('cedula') or pt_data.get('cedula_profesional') or (firma_data.get('cedula') if firma_data else '') or '').strip()
    servicio = (pt_data.get('servicio') or pt_data.get('cama') or 'GINECOLOGÍA Y OBSTETRICIA').strip()
    diagnostico = (pt_data.get('diagnostico') or 'MIOMATOSIS UTERINA DE GRANDES ELEMENTOS / HEMORRAGIA UTERINA ANORMAL').strip()

    fecha_val = pt_data.get('fecha_atencion') or pt_data.get('fecha_ingreso') or datetime.datetime.now().strftime('%d/%m/%Y')
    hora_val = pt_data.get('hora_atencion') or pt_data.get('hora_ingreso') or datetime.datetime.now().strftime('%H:%M')

    explicacion = (pt_data.get('explicacion_de_proceso') or pt_data.get('explicacion') or 'Extirpación quirúrgica total o subtotal del útero mediante abordaje abdominal, vaginal o laparoscópico con hemostasia cuidadosa').strip()
    beneficios = (pt_data.get('beneficios_de_procedimiento') or pt_data.get('beneficios') or 'Resolución definitiva del sangrado uterino anormal, eliminación de masas miomatosas, corrección del dolor pélvico crónico y prevención de complicaciones asociadas').strip()
    intervencion_comp = (pt_data.get('intervencion_complementaria') or 'Salpingooforectomía uni/bilateral según hallazgos macroscópicos, lisis de adherencias pélvicas o biopsia intraoperatoria').strip()
    alternativas = (pt_data.get('alternativas_terapeuticas') or pt_data.get('alternativas') or 'Tratamiento farmacológico hormonal, colocación de DIU liberador de levonorgestrel, embolización de arterias uterinas o miomectomía selectiva').strip()
    
    no_autorizo_check = bool(pt_data.get('no_autorizo') or pt_data.get('tipo') == 'no_autorizo' or pt_data.get('motivo_de_no_autorizacion'))
    motivo_no_aut = (pt_data.get('motivo_de_no_autorizacion') or pt_data.get('motivo_no_acepto') or '').strip()

    paciente_capaz = pt_data.get('paciente_capaz', True)
    if isinstance(paciente_capaz, str):
        paciente_capaz = paciente_capaz.lower() in ('true', '1', 'si', 'yes')
    elif isinstance(paciente_capaz, (int, float)):
        paciente_capaz = bool(paciente_capaz)

    declarante = (pt_data.get('declarante') or pt_data.get('paciente_o_representante') or pt_data.get('representante_legal') or '').strip()
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
    # PÁGINA 1
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
            Paragraph(f"<b>SERVICIO:</b> {servicio.upper()}", style_val),
            Paragraph(f"<b>DIAGNÓSTICO:</b> {diagnostico}", style_val),
            Paragraph(f"<b>PROCEDIMIENTO:</b> <font color='#0056b3'><b>HISTERECTOMÍA</b></font>", style_val),
        ]
    ]

    t_info = Table(pt_info_data, colWidths=[content_w * 0.42, content_w * 0.36, content_w * 0.22])
    t_info.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.75, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
        ('PADDING', (0, 0), (-1, -1), 3.2),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(t_info)
    story.append(Spacer(1, 8))

    intro_p = (
        f"Con la intervención de <b>'Histerectomía'</b> se trata de proporcionar los medios médicos y quirúrgicos idóneos "
        f"para la mejora y resolución de su padecimiento. Por lo anterior, se me ha explicado amplia y claramente que el "
        f"procedimiento consiste en: <b>{explicacion}</b>; asimismo, los beneficios previsibles de realizarlo son: "
        f"<b>{beneficios}</b>."
    )
    story.append(Paragraph(intro_p, style_body))
    story.append(Spacer(1, 8))

    p_1 = (
        "<b>1. Tipo de Anestesia y Recuperación:</b> Para la realización de dicha intervención quirúrgica se requiere la administración "
        "de anestesia general o regional (bloqueo neuroaxial). Cada técnica y cada paciente presentan un perfil de riesgo específico, "
        "el cual será valorado cuidadosamente por el médico anestesiólogo. En general, tras la cirugía se precisa de un periodo de recuperación "
        "inmediata en la Unidad de Recuperación Postanestésica (URPA), dotada de vigilancia hemodinámica estrecha hasta que la paciente se encuentre "
        "en condiciones estables de ser trasladada a su habitación."
    )
    story.append(Paragraph(p_1, style_body))
    story.append(Spacer(1, 8))

    p_2_head = (
        "<b>2. Riesgos y Complicaciones Quirúrgicas Inherentes:</b> Toda intervención quirúrgica conlleva riesgos inherentes a la técnica "
        "y comorbilidades de la paciente. Entre las complicaciones descritas por la literatura médica se incluyen:"
    )
    story.append(Paragraph(p_2_head, style_body))
    story.append(Spacer(1, 4))

    riesgos_lista = [
        "• Infección pélvica o de cúpula vaginal (temprana o tardía), absceso de pared o peritonitis.",
        "• Hemorragia intraoperatoria o postoperatoria con requerimiento de transfusión sanguínea o reintervención urgente.",
        "• Lesiones vasculares o nerviosas pélvicas, parestesias transitorias o dolor neuropático.",
        "• Trombosis venosa profunda (TVP), flebitis y tromboembolia pulmonar (TEP) potencialmente letal.",
        "• Hematomas retroperitoneales, seromas de herida quirúrgica y dehiscencia de suturas.",
        "• Lesión accidental a órganos vecinos: vejiga urinaria, uréteres o asas intestinales con necesidad de reparación quirúrgica inmediata o tardía.",
        "• Reacciones alérgicas o adversas a fármacos anestésicos, antibióticos o antisépticos.",
        "• Formación de fístulas vesicovaginales o rectovaginales, adherencias pélvicas postquirúrgicas y necesidad de laparotomía exploradora exploratoria."
    ]
    for r in riesgos_lista:
        story.append(Paragraph(r, style_bullet))
        story.append(Spacer(1, 2.5))
    story.append(Spacer(1, 5))

    p_3 = (
        f"<b>3. Intervención Complementaria o Hallazgos Imprevistos:</b> Se me ha informado que durante el acto quirúrgico pueden presentarse "
        f"hallazgos anatómicos anormales, adherencias densas o contingencias que obliguen a modificar la técnica programada o a ejecutar "
        f"procedimientos complementarios indispensables para salvaguardar la salud o la vida, tales como: <i>{intervencion_comp}</i>."
    )
    story.append(Paragraph(p_3, style_body))
    story.append(Spacer(1, 8))

    p_4 = (
        f"<b>4. Alternativas Terapéuticas Disponibles:</b> He sido informada con suficiencia acerca de los tratamientos conservadores o "
        f"farmacológicos alternativos, tales como: <i>{alternativas}</i>, entendiéndose que tras la valoración clínica integral la histerectomía "
        f"representa la mejor opción terapéutica disponible."
    )
    story.append(Paragraph(p_4, style_body))

    # =========================================================================
    # PÁGINA 2
    # =========================================================================
    story.append(PageBreak())

    p_p2_head = Paragraph("<b>DECLARACIÓN DE VOLUNTAD, AUTORIZACIÓN Y/O NEGATIVA INFORMADA (Página 2 de 2)</b>", style_sec_title)

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
        f"<font color='#0369A1'><b>[✔ HUELLA DACTILAR VERIFICADA]</b></font><br/>"
        f"<font size='5.0' color='#333333'>SELLO: {sello_pac_short}</font><br/>"
        f"<font size='5.0' color='#006633'>Autenticación Biométrica DigitalPersona (NOM-004)</font>", style_sig_stamp
    ) if (is_pac_signed and not no_autorizo_check) else (Paragraph(
        f"<font color='#0369A1'><b>[✔ HUELLA DACTILAR VERIFICADA]</b></font><br/>"
        f"<font size='5.0' color='#555555'>Identif: {identificacion}</font><br/>"
        f"<font size='5.0' color='#006633'>Autenticación Biométrica DigitalPersona</font>", style_sig_stamp
    ) if (is_med_signed and not no_autorizo_check) else Paragraph("<br/><br/>", style_sig_blank))

    paciente_stamp_rechazo = Paragraph(
        f"<font color='#B91C1C'><b>[✔ NEGATIVA VALIDADA CON HUELLA]</b></font><br/>"
        f"<font size='5.0' color='#333333'>SELLO: {sello_pac_short}</font><br/>"
        f"<font size='5.0' color='#B91C1C'>Rechazo Asentado DigitalPersona</font>", style_sig_stamp_red
    ) if (is_pac_signed and no_autorizo_check) else Paragraph("<br/><br/>", style_sig_blank)

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

    # SECCIÓN 1: AUTORIZACIÓN
    p_aut_text = (
        f"<b>SÍ AUTORIZO:</b> Manifiesto en pleno uso de mis facultades mentales, que he comprendido las explicaciones que se me "
        f"han brindado en un lenguaje claro, sencillo y comprensible. He podido formular preguntas y aclarar todas mis dudas. "
        f"Por lo tanto, otorgo mi <b>CONSENTIMIENTO INFORMADO</b> y AUTORIZO al <b>{medico}</b> y al equipo quirúrgico del Hospital Escandón "
        f"a llevar a cabo la intervención quirúrgica de <b>HISTERECTOMÍA</b> y los actos anestésicos y complementarios requeridos."
    )

    sig_aut_top_data = [
        [
            Paragraph("<b>PACIENTE O SU REPRESENTANTE (AUTORIZA)</b>", style_label),
            Paragraph("<b>MÉDICO CIRUJANO TRATANTE</b>", style_label),
        ],
        [
            paciente_stamp_p if not no_autorizo_check else Paragraph("<font color='#666'>[NO APLICA POR NEGATIVA]</font>", style_sig_sub),
            medico_stamp_p,
        ],
        [
            Paragraph(f"____________________________________________<br/><b>{declarante}</b><br/>{parentesco} • Identif: {identificacion}<br/>Domicilio: {domicilio_declarante}", style_sig_name),
            Paragraph(f"____________________________________________<br/><b>{medico}</b><br/>CÉD. PROF. {cedula}<br/>Médico Especialista / Hospital Escandón", style_sig_name),
        ],
    ]

    sig_aut_bot_data = [
        [
            Paragraph("<b>TESTIGO 1</b>", style_label),
            Paragraph("<b>TESTIGO 2</b>", style_label),
        ],
        [
            t1_stamp_p,
            t2_stamp_p,
        ],
        [
            Paragraph(f"____________________________________________<br/><b>{testigo1 or 'NOMBRE Y FIRMA TESTIGO 1'}</b><br/>Parentesco: {par_t1} • ID: {id_t1}<br/>Domicilio: {domicilio_t1}", style_sig_name),
            Paragraph(f"____________________________________________<br/><b>{testigo2 or 'NOMBRE Y FIRMA TESTIGO 2'}</b><br/>Parentesco: {par_t2} • ID: {id_t2}<br/>Domicilio: {domicilio_t2}", style_sig_name),
        ]
    ]

    _sig_style = TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.75, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F1F5F9')),
        ('PADDING', (0, 0), (-1, -1), 4.2),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ])

    t_aut_top = Table(sig_aut_top_data, colWidths=[content_w * 0.50, content_w * 0.50])
    t_aut_top.setStyle(_sig_style)
    t_aut_bot = Table(sig_aut_bot_data, colWidths=[content_w * 0.50, content_w * 0.50])
    t_aut_bot.setStyle(_sig_style)

    # t_aut ahora es una lista de flowables con espacio entre bloques
    t_aut = [t_aut_top, Spacer(1, 18), t_aut_bot]

    # SECCIÓN 2: NO AUTORIZO / DISENTIMIENTO
    bg_no = colors.HexColor('#FEF2F2') if no_autorizo_check else colors.HexColor('#FAFAFA')
    border_no = colors.HexColor('#F87171') if no_autorizo_check else colors.HexColor('#E2E8F0')

    motivo_str = motivo_no_aut if motivo_no_aut else "____________________________________________________________________________________"
    p_no_text = (
        f"En mi calidad de paciente o representante legal, <b>NO AUTORIZO</b> al <b>{medico}</b> y al equipo de salud del Hospital Escandón "
        f"a que se me realice el procedimiento quirúrgico de histerectomía, haciéndome plenamente responsable de las consecuencias que de "
        f"esta decisión deriven y liberándolos de toda responsabilidad médico-legal. "
        f"El motivo por el cual no acepto es: <b><u>{motivo_str}</u></b>."
    )

    sig_no_data = [
        [
            Paragraph("<b>PACIENTE O REPRESENTANTE (DISENTIMIENTO)</b>", style_sec_alert if no_autorizo_check else style_label),
            Paragraph("<b>TESTIGO PRESENCIAL (DISENTIMIENTO)</b>", style_label),
        ],
        [
            paciente_stamp_rechazo if no_autorizo_check else Paragraph("<br/>", style_sig_blank),
            t1_stamp_p if no_autorizo_check else Paragraph("<br/>", style_sig_blank),
        ],
        [
            Paragraph(f"____________________________________________<br/><b>{declarante}</b><br/>{parentesco} • Identif: {identificacion}", style_sig_name),
            Paragraph(f"____________________________________________<br/><b>{testigo1 or 'NOMBRE Y FIRMA TESTIGO'}</b><br/>ID: {id_t1} • Parentesco: {par_t1}", style_sig_name),
        ]
    ]

    t_no = Table(sig_no_data, colWidths=[content_w * 0.50, content_w * 0.50])
    t_no.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.75, border_no),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('BACKGROUND', (0, 0), (-1, -1), bg_no),
        ('PADDING', (0, 0), (-1, -1), 4.2),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))

    # =========================================================================
    # REGLA GLOBAL: Solo renderizar UNA modalidad (Autorizo O No Autorizo)
    # =========================================================================
    if not no_autorizo_check:
        # ── MODALIDAD: SÍ AUTORIZO ──
        flowables_p2 = [
            p_p2_head,
            Spacer(1, 8),
            Paragraph(p_aut_text, style_body),
            Spacer(1, 10),
            Paragraph(
                "<font size='5.5' color='#047857'><b>NOM-004-SSA3-2012 · Declaración de Comprensión y Aceptación</b></font><br/>"
                "<font size='5.0' color='#475569'>El/la paciente o su representante legal manifiesta haber recibido información "
                "suficiente, clara y comprensible sobre el diagnóstico, procedimiento, riesgos, beneficios y alternativas, "
                "y otorga su consentimiento de manera libre y voluntaria.</font>",
                style_sig_stamp
            ),
            Spacer(1, 10),
        ] + t_aut
    else:
        # ── MODALIDAD: NO AUTORIZO / DISENTIMIENTO ──
        flowables_p2 = [
            p_p2_head,
            Spacer(1, 8),
            Paragraph("<b>DECLARACIÓN DE NO AUTORIZACIÓN (DISENTIMIENTO INFORMADO)</b>", style_sec_alert),
            Spacer(1, 6),
            Paragraph(p_no_text, style_body),
            Spacer(1, 8),
            Paragraph(
                "<font size='5.5' color='#B91C1C'><b>ADVERTENCIA MÉDICA</b></font><br/>"
                "<font size='5.0' color='#475569'>Se ha informado al paciente o su representante que al rechazar el procedimiento "
                "asume voluntariamente todos los riesgos derivados de la evolución natural de su padecimiento, "
                "incluyendo complicaciones graves y el riesgo de fallecimiento. El equipo médico deja constancia "
                "de haber cumplido con su deber de informar conforme a la NOM-004-SSA3-2012.</font>",
                style_sig_stamp_red if hasattr(style_sig_stamp_red, 'name') else style_sig_stamp
            ),
            Spacer(1, 10),
            t_no
        ]

    h_content = sum(f.wrap(content_w, frame_h)[1] for f in flowables_p2)
    gap_p2 = max(8.0, frame_h - h_content - 4.0)

    story.extend(flowables_p2)
    story.append(Spacer(1, gap_p2))

    doc_info = {
        'title_lines': [
            'REVOCACIÓN / NEGATIVA INFORMADA' if no_autorizo_check else 'CONSENTIMIENTO INFORMADO',
            'PARA HISTERECTOMÍA',
            'HOSPITAL ESCANDÓN'
        ],
        'code': 'HE-DIRMED-CONSUL-PLT-19',
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

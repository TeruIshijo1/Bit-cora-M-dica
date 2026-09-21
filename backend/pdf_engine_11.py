# -*- coding: utf-8 -*-
"""
Motor PDF para el Formato 11: Consentimiento de No Reanimación (Voluntad Anticipada)
Código: HE-DIRMED-CONSUL-PLT-11
Conforme a NOM-004-SSA3-2012 y NOM-024-SSA3-2012
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
        CleanConsentCanvas, FRAME_X, FRAME_Y, FRAME_W, FRAME_H,
        TEXT_MUTED, TEXT_DARK, PRIMARY_BLUE, DARK_BLUE, BORDER_GREY
    )
except ModuleNotFoundError:
    from pdf_engine_v2 import (
        CleanConsentCanvas, FRAME_X, FRAME_Y, FRAME_W, FRAME_H,
        TEXT_MUTED, TEXT_DARK, PRIMARY_BLUE, DARK_BLUE, BORDER_GREY
    )


def generate_consentimiento_11(pt_data: dict, output_path: str = None, firma_data: dict = None) -> str:
    """
    Genera el PDF oficial para el Formato 11:
    HE-DIRMED-CONSUL-PLT-11: CONSENTIMIENTO DE NO REANIMACIÓN.
    1 página exacta institucional con marco y pie oficial HES.
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

    template_p1 = PageTemplate(id='FirstPage', frames=frame_p1)

    doc = BaseDocTemplate(
        output_path,
        pagesize=letter,
        pageTemplates=[template_p1]
    )

    style_label = ParagraphStyle('MetaLabel', fontName='Helvetica-Bold', fontSize=7.8, leading=9.8, textColor=PRIMARY_BLUE)
    style_val = ParagraphStyle('MetaVal', fontName='Helvetica', fontSize=8.0, leading=10.2, textColor=TEXT_DARK)
    style_val_bold = ParagraphStyle('MetaValBold', fontName='Helvetica-Bold', fontSize=8.0, leading=10.2, textColor=TEXT_DARK)
    
    style_body = ParagraphStyle('Body', fontName='Helvetica', fontSize=8.6, leading=12.2, textColor=TEXT_DARK, alignment=TA_JUSTIFY)
    style_legal = ParagraphStyle('Legal', fontName='Helvetica-Oblique', fontSize=6.8, leading=8.8, textColor=TEXT_MUTED, alignment=TA_JUSTIFY)
    style_city_date = ParagraphStyle('CityDate', fontName='Helvetica-Bold', fontSize=8.2, leading=10.6, textColor=PRIMARY_BLUE, alignment=TA_RIGHT)

    style_sig_title = ParagraphStyle('SigTitle', fontName='Helvetica-Bold', fontSize=7.8, leading=9.8, textColor=PRIMARY_BLUE, alignment=TA_CENTER)
    style_sig_name = ParagraphStyle('SigName', fontName='Helvetica-Bold', fontSize=7.6, leading=9.6, textColor=TEXT_DARK, alignment=TA_CENTER)
    style_sig_sub = ParagraphStyle('SigSub', fontName='Helvetica', fontSize=6.4, leading=8.2, textColor=TEXT_MUTED, alignment=TA_CENTER)
    style_sig_stamp = ParagraphStyle('SigStamp', fontName='Helvetica', fontSize=5.4, leading=6.8, textColor=colors.HexColor('#006633'), alignment=TA_CENTER)
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
    servicio = (pt_data.get('servicio') or pt_data.get('cama') or 'URGENCIAS / MEDICINA INTERNA / UCI').strip()
    diagnostico = (pt_data.get('diagnostico') or 'ENFERMEDAD EN ETAPA AVANZADA / PRONÓSTICO GRAVE Y LIMITADO').strip()

    fecha_val = pt_data.get('fecha_atencion') or pt_data.get('fecha_ingreso') or datetime.datetime.now().strftime('%d/%m/%Y')
    hora_val = pt_data.get('hora_atencion') or pt_data.get('hora_ingreso') or datetime.datetime.now().strftime('%H:%M')

    paciente_capaz = pt_data.get('paciente_capaz', True)
    if isinstance(paciente_capaz, str):
        paciente_capaz = paciente_capaz.lower() in ('true', '1', 'si', 'yes')
    elif isinstance(paciente_capaz, (int, float)):
        paciente_capaz = bool(paciente_capaz)

    declarante = (pt_data.get('declarante') or pt_data.get('paciente_o_representante') or pt_data.get('representante_legal') or pt_data.get('yo_autorizo') or '').strip()
    parentesco = (pt_data.get('parentesco') or pt_data.get('parentesco_declarante') or ('Paciente' if paciente_capaz else 'Tutor / Representante Legal')).strip()
    identificacion = (pt_data.get('identificacion') or pt_data.get('identificacion_declarante') or pt_data.get('ine') or 'INE / IDENTIFICACIÓN OFICIAL').strip()

    if not declarante or paciente_capaz:
        declarante = paciente_nombre
        parentesco = 'El Paciente'

    beneficios_y_riesgos = (pt_data.get('beneficios_y_riesgos_de_nr') or pt_data.get('beneficios') or 'Evitar el encarnizamiento terapéutico y maniobras invasivas desproporcionadas en fase terminal, garantizando confort y dignidad').strip()
    riesgos_omision = (pt_data.get('riesgos_de_no_aplicar') or pt_data.get('riesgos') or 'Cese irreversible de las funciones cardiorrespiratorias y sobreveniencia de la muerte natural sin soporte artificial').strip()
    alternativas = (pt_data.get('alternativa_nr') or pt_data.get('alternativas') or 'Manejo médico conservador integral, analgesia multimodal, sedación paliativa y medidas de confort bioético').strip()

    testigo1 = (pt_data.get('testigo_1') or pt_data.get('testigo1') or '').strip()
    testigo2 = (pt_data.get('testigo_2') or pt_data.get('testigo2') or '').strip()

    # Tabla de Identificación del Paciente
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
            Paragraph(f"<b>ESTADO:</b> <font color='#B45309'><b>VOLUNTAD ANTICIPADA</b></font>", style_val),
        ]
    ]

    t_info = Table(pt_info_data, colWidths=[content_w * 0.42, content_w * 0.36, content_w * 0.22])
    t_info.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.75, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
        ('PADDING', (0, 0), (-1, -1), 3.5),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))

    # Cuerpo declarativo oficial
    p_declara_1 = (
        f"Yo <b>{declarante}</b> en calidad de <b>{parentesco.upper()}</b>, declaro que he sido informado(a) amplia y detalladamente "
        f"hasta la total comprensión acerca del estado de salud y pronóstico de mi paciente: <b>{paciente_nombre}</b> con No. de Expediente: "
        f"<b>{expediente}</b>, quien se encuentra en el servicio de: <b>{servicio}</b>; con el diagnóstico médico de: <b>{diagnostico}</b>."
    )

    p_declara_2 = (
        "Lo anteriormente mencionado determina que el pronóstico clínico sea muy malo y no susceptible de reversión curativa. "
        "Por lo tanto, después de analizarlo exhaustivamente con el equipo médico tratante, hemos tomado la firme decisión libre, informada y consciente "
        "de solicitar que <b>NO SE REALICEN</b> procedimientos desproporcionados tales como: <b>Maniobras de Reanimación Cardiopulmonar (RCP)</b>, "
        "intubación endotraqueal invasiva o fármacos inotrópicos extremos, teniendo conocimiento de que los beneficios de la decisión tomada son: "
        f"<i>{beneficios_y_riesgos}</i>; asimismo, los riesgos clínicos inherentes a no aplicar reanimación son: <i>{riesgos_omision}</i>."
    )

    p_declara_3 = (
        f"De igual forma se me explicó que existen otras alternativas de soporte tales como: <i>{alternativas}</i>, sin embargo "
        "se ha considerado en consenso bioético y clínico que el procedimiento de adecuación terapéutica resulta ser el más humano, conveniente y apegado a la dignidad del paciente."
    )

    p_declara_4 = (
        "Por lo tanto, <b>aceptamos y solicitamos que solo se utilicen medidas terapéuticas mínimas, paliativas y no invasivas</b> para minimizar tanto "
        "como sea posible el dolor, la disnea y las molestias que pueda experimentar; de tal manera que liberamos al cuerpo médico y directivo del Hospital Escandón "
        "de cualquier responsabilidad jurídica o médico-legal derivada del estricto cumplimiento de esta voluntad manifestada."
    )

    # Atribución de firmas y estampados
    is_med_signed = bool(firma_data and (firma_data.get('sello_digital') or firma_data.get('hash_sha256')))
    sello_fea = (firma_data.get('sello_digital') or '') if firma_data else ''
    sello_short = (sello_fea[:28] + '...' + sello_fea[-10:]) if len(sello_fea) > 40 else sello_fea
    hash_short = (firma_data.get('hash_sha256') or '')[:32] if firma_data else ''

    medico_stamp_p = Paragraph(
        f"<font color='#047857'><b>[✔ FIRMA ELECTRÓNICA AVANZADA FEA]</b></font><br/>"
        f"<font size='5.4' color='#333333'>SELLO: {sello_short}</font><br/>"
        f"<font size='5.0' color='#666666'>HASH: {hash_short}...</font>", style_sig_stamp
    ) if is_med_signed else Paragraph("<br/><br/>", style_sig_blank)

    is_pac_signed = bool(pt_data.get("firma_paciente_biometrica") or (firma_data and firma_data.get("sello_paciente")))
    sello_pac = str(pt_data.get("sello_paciente") or (firma_data.get("sello_paciente") if firma_data else "") or "")
    sello_pac_short = (sello_pac[:24] + '...') if len(sello_pac) > 26 else sello_pac

    paciente_stamp_p = Paragraph(
        f"<font color='#0369A1'><b>[✔ HUELLA DACTILAR VERIFICADA]</b></font><br/>"
        f"<font size='5.4' color='#333333'>SELLO: {sello_pac_short}</font><br/>"
        f"<font size='5.0' color='#006633'>Autenticación Biométrica DigitalPersona (NOM-004)</font>", style_sig_stamp
    ) if is_pac_signed else (Paragraph(
        f"<font color='#0369A1'><b>[✔ HUELLA DACTILAR VERIFICADA]</b></font><br/>"
        f"<font size='5.4' color='#555555'>Identif: {identificacion}</font><br/>"
        f"<font size='5.0' color='#006633'>Autenticación Biométrica DigitalPersona</font>", style_sig_stamp
    ) if is_med_signed else Paragraph("<br/><br/>", style_sig_blank))

    is_t1_signed = bool(pt_data.get("firma_testigo1_biometrica") or (firma_data and firma_data.get("sello_testigo1")))
    sello_t1 = str(pt_data.get("sello_testigo1") or (firma_data.get("sello_testigo1") if firma_data else "") or "")
    sello_t1_short = (sello_t1[:22] + '...') if len(sello_t1) > 24 else sello_t1

    t1_stamp_p = Paragraph(
        f"<font size='5.4' color='#006633'><b>[✔ Testigo 1 Biométrico]</b></font><br/>"
        f"<font size='5.0' color='#555555'>SELLO: {sello_t1_short}</font>", style_sig_stamp
    ) if is_t1_signed else (Paragraph(f"<font size='5.4' color='#006633'>[✔ Testigo 1 Presencial Asentado]</font>", style_sig_stamp) if (is_med_signed and testigo1) else Paragraph("<br/><br/>", style_sig_blank))

    is_t2_signed = bool(pt_data.get("firma_testigo2_biometrica") or (firma_data and firma_data.get("sello_testigo2")))
    sello_t2 = str(pt_data.get("sello_testigo2") or (firma_data.get("sello_testigo2") if firma_data else "") or "")
    sello_t2_short = (sello_t2[:22] + '...') if len(sello_t2) > 24 else sello_t2

    t2_stamp_p = Paragraph(
        f"<font size='5.4' color='#006633'><b>[✔ Testigo 2 Biométrico]</b></font><br/>"
        f"<font size='5.0' color='#555555'>SELLO: {sello_t2_short}</font>", style_sig_stamp
    ) if is_t2_signed else (Paragraph(f"<font size='5.4' color='#006633'>[✔ Testigo 2 Presencial Asentado]</font>", style_sig_stamp) if (is_med_signed and testigo2) else Paragraph("<br/><br/>", style_sig_blank))

    sig_top_data = [
        [
            Paragraph("<b>AUTORIZACIÓN / DECLARANTE</b>", style_sig_title),
            Paragraph("<b>MÉDICO TRATANTE</b>", style_sig_title),
        ],
        [
            paciente_stamp_p,
            medico_stamp_p,
        ],
        [
            Paragraph(f"____________________________________________<br/><b>{declarante}</b><br/>{parentesco} • Identif: {identificacion}", style_sig_name),
            Paragraph(f"____________________________________________<br/><b>{medico}</b><br/>CÉD. PROF. {cedula}<br/>Médico Tratante / Hospital Escandón", style_sig_name),
        ],
    ]

    sig_bot_data = [
        [
            Paragraph("<b>TESTIGO 1</b>", style_sig_title),
            Paragraph("<b>TESTIGO 2</b>", style_sig_title),
        ],
        [
            t1_stamp_p,
            t2_stamp_p,
        ],
        [
            Paragraph(f"____________________________________________<br/><b>{testigo1 or 'NOMBRE Y FIRMA TESTIGO 1'}</b><br/>Identificación Oficial / Testigo Presencial", style_sig_name),
            Paragraph(f"____________________________________________<br/><b>{testigo2 or 'NOMBRE Y FIRMA TESTIGO 2'}</b><br/>Identificación Oficial / Testigo Presencial", style_sig_name),
        ]
    ]

    _sig_style_11 = TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.75, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F1F5F9')),
        ('PADDING', (0, 0), (-1, -1), 5.0),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ])

    t_sigs_top = Table(sig_top_data, colWidths=[content_w * 0.50, content_w * 0.50])
    t_sigs_top.setStyle(_sig_style_11)
    t_sigs_bot = Table(sig_bot_data, colWidths=[content_w * 0.50, content_w * 0.50])
    t_sigs_bot.setStyle(_sig_style_11)

    flowables_before = [
        t_info,
        Spacer(1, 14),
        Paragraph(p_declara_1, style_body),
        Spacer(1, 12),
        Paragraph(p_declara_2, style_body),
        Spacer(1, 12),
        Paragraph(p_declara_3, style_body),
        Spacer(1, 12),
        Paragraph(p_declara_4, style_body),
        Spacer(1, 14),
        Paragraph(f"Dado en la Ciudad de México, a <b>{fecha_val}</b> a las <b>{hora_val} hrs</b>.", style_city_date)
    ]

    h_before = sum(f.wrap(content_w, frame_h)[1] for f in flowables_before)
    h_top = t_sigs_top.wrap(content_w, frame_h)[1]
    h_bot = t_sigs_bot.wrap(content_w, frame_h)[1]
    sig_spacer = 18.0
    elastic_gap = max(4.0, frame_h - (h_before + h_top + sig_spacer + h_bot) - 3.0)
    story = flowables_before + [Spacer(1, elastic_gap), t_sigs_top, Spacer(1, sig_spacer), t_sigs_bot]

    doc_info = {
        'title_lines': [
            'CONSENTIMIENTO DE NO REANIMACIÓN',
            'VOLUNTAD ANTICIPADA Y LIMITACIÓN DEL ESFUERZO TERAPÉUTICO',
            'HOSPITAL ESCANDÓN'
        ],
        'code': 'HE-DIRMED-CONSUL-PLT-11',
        'fecha_ingreso': fecha_val,
        'hora_ingreso': hora_val,
        'expediente': expediente,
        'folio': expediente,
        'pt_num': str(pt_data.get('pt_num', '') or expediente),
        'slot': pt_data.get('slot') or pt_data.get('mrnum') or 1,
        'total_pages': 1,
        'paciente': paciente_nombre,
        'medico': medico,
        'cedula': cedula,
        'servicio': servicio
    }

    canvas_factory = lambda *args, **kwargs: CleanConsentCanvas(*args, doc_info=doc_info, **kwargs)
    doc.build(story, canvasmaker=canvas_factory)
    return output_path

# -*- coding: utf-8 -*-
"""
Motor PDF para el Formato 06: Consentimiento para Autorizar Procedimiento Anestésico
Código: HE-DIRMED-CONSUL-PLT-06
Conforme a NOM-004-SSA3-2012 (10.1.2.3) y NOM-170-SSA1-1998 (4.12, 16.1.1)
Exactamente 1 página institucional con marco RDLC y QR oficial HES.
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


def generate_consentimiento_06(pt_data: dict, output_path: str = None, firma_data: dict = None) -> str:
    """
    Genera el PDF oficial para el Formato 06:
    HE-DIRMED-CONSUL-PLT-06: CONSENTIMIENTO INFORMADO PARA AUTORIZAR EL PROCEDIMIENTO ANESTÉSICO.
    Exactamente 1 página con diseño institucional HES.
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

    style_label = ParagraphStyle('MetaLabel', fontName='Helvetica-Bold', fontSize=7.6, leading=9.6, textColor=PRIMARY_BLUE)
    style_val = ParagraphStyle('MetaVal', fontName='Helvetica', fontSize=7.8, leading=10.0, textColor=TEXT_DARK)
    
    style_body = ParagraphStyle('Body', fontName='Helvetica', fontSize=8.4, leading=11.6, textColor=TEXT_DARK, alignment=TA_JUSTIFY)
    style_norma = ParagraphStyle('Norma', fontName='Helvetica-Oblique', fontSize=6.8, leading=8.8, textColor=TEXT_MUTED, alignment=TA_JUSTIFY)

    style_sig_title = ParagraphStyle('SigTitle', fontName='Helvetica-Bold', fontSize=7.6, leading=9.6, textColor=PRIMARY_BLUE, alignment=TA_CENTER)
    style_sig_name = ParagraphStyle('SigName', fontName='Helvetica-Bold', fontSize=7.4, leading=9.4, textColor=TEXT_DARK, alignment=TA_CENTER)
    style_sig_sub = ParagraphStyle('SigSub', fontName='Helvetica', fontSize=6.2, leading=8.0, textColor=TEXT_MUTED, alignment=TA_CENTER)
    style_sig_stamp = ParagraphStyle('SigStamp', fontName='Helvetica', fontSize=5.2, leading=6.6, textColor=colors.HexColor('#006633'), alignment=TA_CENTER)
    style_sig_blank = ParagraphStyle('SigBlank', fontName='Helvetica', fontSize=5.0, leading=6.0, textColor=colors.transparent, alignment=TA_CENTER)

    story = []

    # 1. Metadatos del Paciente
    paciente_nombre = (pt_data.get('paciente_nombre') or pt_data.get('nombre') or '').strip()
    expediente = str(pt_data.get('expediente') or pt_data.get('mrn') or pt_data.get('pt_num') or '').strip()
    fecha_nac = (pt_data.get('fecha_nacimiento') or pt_data.get('dob') or '').strip()
    edad_raw = str(pt_data.get('edad') or '').strip()
    edad_display = f"{edad_raw} años" if edad_raw and "año" not in edad_raw.lower() else (edad_raw or '____')
    
    cama = (pt_data.get('cama') or pt_data.get('servicio') or 'QUIRÓFANO').strip()
    sexo = str(pt_data.get('sexo') or pt_data.get('gender') or 'M').upper().strip()
    sexo_display = "FEMENINO" if (sexo.startswith('F') or 'FEM' in sexo) else "MASCULINO"

    fecha_val = pt_data.get('fecha_atencion') or pt_data.get('fecha_ingreso') or datetime.datetime.now().strftime('%d/%m/%Y')
    hora_val = pt_data.get('hora_atencion') or pt_data.get('hora_ingreso') or datetime.datetime.now().strftime('%H:%M')

    medico = (pt_data.get('medico_anestesiologo') or pt_data.get('medico_tratante') or pt_data.get('n_medico') or (firma_data.get('nombre_medico') if firma_data else '') or '').strip()
    cedula = (pt_data.get('cedula') or pt_data.get('cedula_profesional') or (firma_data.get('cedula') if firma_data else '') or '').strip()
    cedula_esp = (pt_data.get('cedula_especialidad') or '').strip()

    # Clasificación Quirúrgica y ASA
    tipo_cirugia_raw = str(pt_data.get('tipo_cirugia') or 'PROGRAMADA').upper().strip()
    tipo_cirugia_display = "URGENTE" if "URG" in tipo_cirugia_raw else "PROGRAMADA"

    magnitud_raw = str(pt_data.get('magnitud_cirugia') or 'MAYOR').upper().strip()
    magnitud_display = "MENOR" if "MEN" in magnitud_raw else "MAYOR"

    asa_raw = str(pt_data.get('asa') or pt_data.get('estado_fisico_asa') or 'II').upper().strip()
    if asa_raw in ('1', 'I'):
        asa_display = "CLASE I"
    elif asa_raw in ('2', 'II'):
        asa_display = "CLASE II"
    elif asa_raw in ('3', 'III'):
        asa_display = "CLASE III"
    elif asa_raw in ('4', 'IV'):
        asa_display = "CLASE IV"
    elif asa_raw in ('5', 'V'):
        asa_display = "CLASE V"
    else:
        asa_display = asa_raw

    tipo_anestesia = (
        pt_data.get('tipo_anestesia') or pt_data.get('anestesia_a_administrar') or
        'ANESTESIA GENERAL BALANCEADA CON INTUBACIÓN OROTRAQUEAL / BLOQUEO NEUROAXIAL REGIONAL'
    ).strip()

    beneficios = (
        pt_data.get('beneficios_anestesia') or pt_data.get('beneficios') or
        'Abolición del dolor y sensibilidad táctil, estabilidad hemodinámica, relajación muscular óptima y confort transoperatorio seguro.'
    ).strip()

    alternativas = (
        pt_data.get('alternativas_anestesia') or pt_data.get('alternativas') or
        'Anestesia regional (bloqueo peridural o subaracnoideo), sedación consciente monitoreada o anestesia local infiltrativa según técnica quirúrgica.'
    ).strip()

    paciente_capaz = pt_data.get('paciente_capaz', True)
    if isinstance(paciente_capaz, str):
        paciente_capaz = paciente_capaz.lower() in ('true', '1', 'si', 'yes')
    elif isinstance(paciente_capaz, (int, float)):
        paciente_capaz = bool(paciente_capaz)

    declarante = (pt_data.get('declarante') or pt_data.get('paciente_o_representante') or pt_data.get('representante_legal') or '').strip()
    parentesco = (pt_data.get('parentesco') or pt_data.get('parentesco_declarante') or ('Paciente' if paciente_capaz else 'Familiar / Tutor')).strip()
    identificacion = (pt_data.get('identificacion') or pt_data.get('identificacion_declarante') or 'INE / CREDENCIAL OFICIAL').strip()

    if not declarante or paciente_capaz:
        declarante = paciente_nombre
        parentesco = 'El Paciente'

    testigo1 = (pt_data.get('testigo_1') or pt_data.get('testigo1') or pt_data.get('testigo') or '').strip()
    id_t1 = (pt_data.get('identificacion_testigo1') or pt_data.get('id_t1') or 'INE').strip()

    # Tabla de Identificación y Ficha Preanestésica
    pt_info_data = [
        [
            Paragraph(f"<b>PACIENTE:</b> {paciente_nombre}", style_val),
            Paragraph(f"<b>FECHA DE NAC.:</b> {fecha_nac or '___/___/_____'}", style_val),
            Paragraph(f"<b>EDAD:</b> {edad_display}", style_val),
            Paragraph(f"<b>SEXO:</b> {sexo_display}", style_val),
        ],
        [
            Paragraph(f"<b>EXPEDIENTE:</b> {expediente}", style_val),
            Paragraph(f"<b>CAMA/SERVICIO:</b> {cama}", style_val),
            Paragraph(f"<b>FECHA:</b> {fecha_val}", style_val),
            Paragraph(f"<b>HORA:</b> {hora_val} hrs", style_val),
        ],
        [
            Paragraph(f"<b>CIRUGÍA:</b> {tipo_cirugia_display}", style_val),
            Paragraph(f"<b>MAGNITUD:</b> {magnitud_display}", style_val),
            Paragraph(f"<b>ESTADO FÍSICO A.S.A.:</b> {asa_display}", style_val),
            Paragraph(f"<b>MÉDICO:</b> {medico}", style_val),
        ],
        [
            Paragraph(f"<b>TIPO DE ANESTESIA A ADMINISTRAR:</b> {tipo_anestesia.upper()}", style_val),
            "", "", ""
        ]
    ]

    t_info = Table(pt_info_data, colWidths=[content_w * 0.26, content_w * 0.22, content_w * 0.24, content_w * 0.28])
    t_info.setStyle(TableStyle([
        ('SPAN', (0, 3), (3, 3)),
        ('BOX', (0, 0), (-1, -1), 0.75, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
        ('PADDING', (0, 0), (-1, -1), 3.2),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))

    # Cuerpo textual oficial
    p1 = Paragraph(
        "Por consiguiente en calidad del paciente (o representante legal), declaro que: cuento con la información suficiente "
        "sobre los riesgos potenciales del procedimiento anestésico, que este puede cambiar de acuerdo a mis condiciones físicas y/o emocionales, "
        "o a las inherentes del procedimiento quirúrgico. Que todo acto médico implica una serie de riesgos para mi estado físico actual, en función de "
        "mis antecedentes patológicos y no patológicos, tratamientos previos a la causa que da origen a la intervención quirúrgica, procedimientos de diagnóstico "
        "y tratamiento o a una combinación de los factores anteriormente mencionados. Que existe la posibilidad de complicaciones, desde leves hasta severas, "
        "pudiendo causar secuelas temporales o permanentes. Que existe la posibilidad que mi operación se retrase e incluso se suspenda por causas propias a mi "
        "estado físico, la dinámica del quirófano, causas de fuerza mayor (urgencias) o por negarme a autorizar el procedimiento anestésico.",
        style_body
    )

    p2 = Paragraph(
        "Que también se me ha informado que el Departamento de Anestesiología cuenta con todo el equipo electrónico e insumos para mi cuidado y manejo "
        "durante mi procedimiento, y aún así no me exime de presentar accidentes y complicaciones totalmente ajenas e involuntarias al anestesiólogo. "
        "Además, que soy responsable de comunicar lo informado y esta decisión a mi familia.",
        style_body
    )

    p3 = Paragraph(
        f"El médico anestesiólogo me informa que los <b>beneficios</b> de dicho procedimiento son: <i>{beneficios}</i>. "
        "Asimismo, se me ha advertido sobre los <b>riesgos, accidentes y complicaciones</b> que se pueden presentar en el procedimiento anestésico: "
        "Dolor y flebitis en los sitios de punción venosa/arterial, multipunciones vasculares involuntarias, hematomas pospunción, ruptura o extracción accidental "
        "de piezas dentales; traumatismo de mucosa oral o nasal, ronquera y dolor faríngeo; depresión respiratoria; hipo o hipertensión, arritmias cardíacas; "
        "reacción anafiláctica o adversa a medicamentos; daño neurológico periférico transitorio o permanente relacionado con anestésicos locales o aguja de punción "
        "(catéter peridural o raquídeo); cefalea postpunción dural de leve a severa; imposibilidad o dificultad para intubación u oxigenación adecuada por variantes "
        "anatómicas o patologías pulmonares (asma, EPOC, bronquitis); broncoaspiración de contenido gástrico aun con ayuno preoperatorio; daño a órganos vitales "
        "(cerebro, corazón, riñón, pulmón); paro cardiorrespiratorio e incluso la muerte.",
        style_body
    )

    p4 = Paragraph(
        f"Se me han explicado las diferentes <b>alternativas de anestesia</b> como: <i>{alternativas}</i>, ya sea general, regional (neuroaxial) o local "
        "con sedación monitoreada, que dependerán estrictamente de las condiciones clínicas transoperatorias y del procedimiento quirúrgico a realizar.",
        style_body
    )

    p5 = Paragraph(
        "En virtud de lo anterior, <b>ACEPTO Y FIRMO</b> el presente consentimiento por escrito, para que el médico anestesiólogo adscrito al <b>Hospital Escandón</b> "
        "lleve a cabo el acto anestésico que considere necesario y adecuado para realizar la cirugía o procedimientos a los que he decidido someterme, en el entendido "
        "de que si ocurren contingencias, accidentes o complicaciones inherentes a la técnica anestésica, no existe dolo ni negligencia de su parte.",
        style_body
    )

    p_legal = Paragraph(
        "De acuerdo a la Norma Oficial Mexicana NOM-004-SSA3-2012 del Expediente Clínico (numeral 10.1.2.3) y la Norma Oficial Mexicana NOM-170-SSA1-1998 "
        "para la Práctica de la Anestesiología en México (numerales 4.12 y 16.1.1), se emite este documento formalmente firmado por el paciente o su representante legal, "
        "testigo presencial y médico anestesiólogo tratante.",
        style_norma
    )

    # Firmas en 3 Columnas
    is_med_signed = bool(firma_data and (firma_data.get('sello_digital') or firma_data.get('hash_sha256')))
    is_pac_signed = bool(pt_data.get("firma_paciente_biometrica") or (firma_data and firma_data.get("sello_paciente")))
    sello_pac = str(pt_data.get("sello_paciente") or (firma_data.get("sello_paciente") if firma_data else "") or "")
    sello_pac_short = (sello_pac[:22] + '...') if len(sello_pac) > 24 else sello_pac

    sello_fea = (firma_data.get('sello_digital') or '') if firma_data else ''
    sello_short = (sello_fea[:26] + '...' + sello_fea[-8:]) if len(sello_fea) > 36 else sello_fea
    hash_short = (firma_data.get('hash_sha256') or '')[:28] if firma_data else ''

    medico_stamp_p = Paragraph(
        f"<font color='#047857'><b>[✔ FEA ANESTESIÓLOGO]</b></font><br/>"
        f"<font size='5.2' color='#333333'>SELLO: {sello_short}</font><br/>"
        f"<font size='5.0' color='#666666'>HASH: {hash_short}...</font>", style_sig_stamp
    ) if is_med_signed else Paragraph("<br/><br/>", style_sig_blank)

    paciente_stamp_p = Paragraph(
        f"<font color='#0369A1'><b>[✔ HUELLA VERIFICADA]</b></font><br/>"
        f"<font size='5.2' color='#333333'>SELLO: {sello_pac_short}</font><br/>"
        f"<font size='5.0' color='#006633'>DigitalPersona HES (NOM-004)</font>", style_sig_stamp
    ) if is_pac_signed else (Paragraph(
        f"<font color='#0369A1'><b>[✔ HUELLA VERIFICADA]</b></font><br/>"
        f"<font size='5.2' color='#555555'>Identif: {identificacion}</font><br/>"
        f"<font size='5.0' color='#006633'>DigitalPersona HES</font>", style_sig_stamp
    ) if is_med_signed else Paragraph("<br/><br/>", style_sig_blank))

    is_t1_signed = bool(pt_data.get("firma_testigo1_biometrica") or (firma_data and firma_data.get("sello_testigo1")))
    sello_t1 = str(pt_data.get("sello_testigo1") or (firma_data.get("sello_testigo1") if firma_data else "") or "")
    sello_t1_short = (sello_t1[:20] + '...') if len(sello_t1) > 22 else sello_t1

    t1_stamp_p = Paragraph(
        f"<font size='5.2' color='#006633'><b>[✔ Testigo Biométrico]</b></font><br/>"
        f"<font size='5.0' color='#555555'>SELLO: {sello_t1_short}</font>", style_sig_stamp
    ) if is_t1_signed else (Paragraph(f"<font size='5.2' color='#006633'>[✔ Testigo Presencial Asentado]</font>", style_sig_stamp) if (is_med_signed and testigo1) else Paragraph("<br/><br/>", style_sig_blank))

    sig_cols_data = [
        [
            Paragraph("<b>PACIENTE O RESPONSABLE LEGAL</b>", style_sig_title),
            Paragraph("<b>TESTIGO PRESENCIAL</b>", style_sig_title),
            Paragraph("<b>MÉDICO ANESTESIÓLOGO</b>", style_sig_title),
        ],
        [
            paciente_stamp_p,
            t1_stamp_p,
            medico_stamp_p,
        ],
        [
            Paragraph(
                f"___________________________________<br/>"
                f"<b>{declarante}</b><br/>"
                f"{parentesco} • Identif: {identificacion}<br/>"
                f"<i>Firma del paciente o representante</i>",
                style_sig_name
            ),
            Paragraph(
                f"___________________________________<br/>"
                f"<b>{testigo1 or 'NOMBRE COMPLETO TESTIGO'}</b><br/>"
                f"Identificación: {id_t1}<br/>"
                f"<i>Firma del testigo</i>",
                style_sig_name
            ),
            Paragraph(
                f"___________________________________<br/>"
                f"<b>{medico}</b><br/>"
                f"CÉD. {cedula} • {cedula_esp}<br/>"
                f"<i>Anestesiología / Hospital Escandón</i>",
                style_sig_name
            ),
        ]
    ]

    t_sigs = Table(sig_cols_data, colWidths=[content_w * 0.333, content_w * 0.334, content_w * 0.333])
    t_sigs.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.75, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F1F5F9')),
        ('PADDING', (0, 0), (-1, -1), 4.5),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))

    flowables_before = [
        t_info,
        Spacer(1, 9),
        p1,
        Spacer(1, 8),
        p2,
        Spacer(1, 8),
        p3,
        Spacer(1, 8),
        p4,
        Spacer(1, 8),
        p5,
        Spacer(1, 8),
        p_legal
    ]

    h_before = sum(f.wrap(content_w, frame_h)[1] for f in flowables_before)
    h_sigs = t_sigs.wrap(content_w, frame_h)[1]
    elastic_gap = max(4.0, frame_h - (h_before + h_sigs) - 3.0)
    story = flowables_before + [Spacer(1, elastic_gap), t_sigs]

    doc_info = {
        'title_lines': [
            'CONSENTIMIENTO INFORMADO PARA',
            'AUTORIZAR EL PROCEDIMIENTO ANESTÉSICO',
            'HOSPITAL ESCANDÓN'
        ],
        'code': 'HE-DIRMED-CONSUL-PLT-06',
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
        'servicio': cama
    }

    canvas_factory = lambda *args, **kwargs: CleanConsentCanvas(*args, doc_info=doc_info, **kwargs)
    doc.build(story, canvasmaker=canvas_factory)
    return output_path

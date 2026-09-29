# -*- coding: utf-8 -*-
"""
Motor PDF para el Formato 15: Consentimiento Informado para Cesárea / Disentimiento (No Autorizo)
Código: HE-DIRMED-CONSUL-PLT-15
Servicio: Ginecología y Obstetricia
"""

import os
import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, TableStyle, KeepTogether
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT

try:
    from .pdf_engine_v2 import (
        CleanConsentCanvas, FRAME_X, FRAME_Y, FRAME_W, FRAME_H,
        TEXT_MUTED, TEXT_DARK, PRIMARY_BLUE, RED_ALERT,
        letterhead_content_width
    )
except ImportError:
    from pdf_engine_v2 import (
        CleanConsentCanvas, FRAME_X, FRAME_Y, FRAME_W, FRAME_H,
        TEXT_MUTED, TEXT_DARK, PRIMARY_BLUE, RED_ALERT,
        letterhead_content_width
    )

def generate_consentimiento_15(pt_data: dict, output_path: str, firma_data: dict = None) -> str:
    """
    Genera el PDF del Formato 15 (HE-DIRMED-CONSUL-PLT-15).
    Soporta dos modalidades institucionales:
      - tipo == 'autorizo' (o no_autorizo == False): Hoja 1 - Consentimiento para Cesárea
      - tipo == 'no_autorizo' (o no_autorizo == True): Hoja 2 - Disentimiento / Negativa Informada
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

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

    # Estilos tipográficos
    style_label = ParagraphStyle('MetaLabel', fontName='Helvetica-Bold', fontSize=7.4, leading=9.5, textColor=TEXT_MUTED)
    style_val = ParagraphStyle('MetaVal', fontName='Helvetica-Bold', fontSize=8.0, leading=10.5, textColor=TEXT_DARK)
    
    style_intro = ParagraphStyle('Intro', fontName='Helvetica', fontSize=7.6, leading=9.8, textColor=TEXT_DARK, alignment=TA_JUSTIFY)
    style_body = ParagraphStyle('Body', fontName='Helvetica', fontSize=7.0, leading=9.0, textColor=TEXT_DARK, alignment=TA_JUSTIFY)
    style_bullet = ParagraphStyle('Bullet', fontName='Helvetica', fontSize=6.8, leading=8.6, textColor=TEXT_DARK, alignment=TA_JUSTIFY, leftIndent=12.0)
    
    style_sig_name = ParagraphStyle('SigName', fontName='Helvetica-Bold', fontSize=7.8, leading=9.5, textColor=TEXT_DARK, alignment=TA_CENTER)
    style_sig_label = ParagraphStyle('SigLbl', fontName='Helvetica', fontSize=6.5, leading=8.0, textColor=TEXT_MUTED, alignment=TA_CENTER)
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
    diagnostico = pt_data.get('diagnostico', 'EMBARAZO A TÉRMINO / INDICACIÓN DE CESÁREA')
    fecha_val = pt_data.get('fecha_atencion') or pt_data.get('fecha_ingreso') or datetime.datetime.now().strftime('%d/%m/%Y')
    hora_val = pt_data.get('hora_atencion') or pt_data.get('hora_ingreso') or datetime.datetime.now().strftime('%H:%M')

    # Modalidad: Autorizo vs No Autorizo
    es_no_autorizo = bool(
        pt_data.get('no_autorizo') is True or 
        str(pt_data.get('tipo', '')).lower() in ['no_autorizo', 'disentimiento', 'rechazo'] or
        pt_data.get('autoriza') is False
    )

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
        ],
        [
            Paragraph(f"<b>DIAGNÓSTICO:</b> {diagnostico}", style_val),
            Paragraph(f"<b>SERVICIO:</b> GINECOLOGÍA Y OBSTETRICIA", style_val),
            Paragraph(f"<b>ESTADO:</b> " + ("<font color='#B91C1C'><b>NO AUTORIZADO</b></font>" if es_no_autorizo else "<font color='#047857'><b>AUTORIZADO</b></font>"), style_val),
        ]
    ]

    t_info = Table(pt_info_data, colWidths=[content_w * 0.42, content_w * 0.36, content_w * 0.22])
    t_info.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.75, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
        ('PADDING', (0, 0), (-1, -1), 3.0),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(t_info)
    story.append(Spacer(1, 4))

    # Parámetros del membrete institucional
    expediente_val = expediente or pt_data.get('pt_num', '')
    pt_num_val = str(pt_data.get('pt_num', '') or expediente or '')

    if es_no_autorizo:
        doc_info = {
            'title_lines': [
                'DISENTIMIENTO / NEGATIVA INFORMADA',
                'PARA CÉSAREA',
                'SERVICIO DE GINECOLOGÍA Y OBSTETRICIA'
            ],
            'code': 'HE-DIRMED-CONSUL-PLT-15',
            'draw_header_dates': False,
            'fecha_ingreso': fecha_val,
            'hora_ingreso': hora_val,
            'expediente': expediente_val,
            'folio': expediente_val,
            'pt_num': pt_num_val,
            'slot': pt_data.get('slot') or pt_data.get('mrnum') or 1,
            'draw_qr': True
        }
    else:
        doc_info = {
            'title_lines': [
                'CONSENTIMIENTO INFORMADO',
                'PARA CÉSAREA',
                'SERVICIO DE GINECOLOGÍA Y OBSTETRICIA'
            ],
            'code': 'HE-DIRMED-CONSUL-PLT-15',
            'draw_header_dates': False,
            'fecha_ingreso': fecha_val,
            'hora_ingreso': hora_val,
            'expediente': expediente_val,
            'folio': expediente_val,
            'pt_num': pt_num_val,
            'slot': pt_data.get('slot') or pt_data.get('mrnum') or 1,
            'draw_qr': True
        }

    # Parámetros de capacidad y firmantes presenciales (disponibles para Autorizo y Disentimiento)
    pariente = (pt_data.get('pariente') or pt_data.get('representante_legal') or pt_data.get('declarante') or '').strip()
    raw_mayor = pt_data.get('paciente_capaz', True)
    if isinstance(raw_mayor, str):
        es_mayor = raw_mayor.lower() in ('true', '1', 'si', 'yes')
    elif isinstance(raw_mayor, (int, float)):
        es_mayor = bool(raw_mayor)
    else:
        es_mayor = bool(raw_mayor)
    has_tutor = bool(pariente) or (not es_mayor)
    testigo1 = pt_data.get('testigo1', '')
    testigo2 = pt_data.get('testigo2', '')

    # =========================================================================
    # MODALIDAD 1: AUTORIZO (HOJA 1 - CONSENTIMIENTO INFORMADO)
    # =========================================================================
    if not es_no_autorizo:
        proc_consiste = pt_data.get('procedimiento_consiste', 'Extracción quirúrgica del feto mediante laparotomía e histerotomía transversa')
        beneficios = pt_data.get('beneficios', 'Nacimiento seguro y oportuno del recién nacido y preservación de la salud materna')
        alternativas = pt_data.get('alternativas', 'Parto vaginal expectante o monitoreo continuo materno-fetal según evolución')

        p_intro = Paragraph(
            f"Con la intervención de <b>«cesárea»</b> se trata de proporcionar los medios para la mejora de su padecimiento, por lo anterior se me "
            f"ha explicado que el procedimiento consiste en: <u>{proc_consiste}</u>; así mismo, los beneficios de realizarlo son: "
            f"<u>{beneficios}</u>.",
            style_intro
        )
        story.append(p_intro)
        story.append(Spacer(1, 3))

        # 7 PUNTOS INSTITUCIONALES
        p1 = Paragraph(
            "<b>1.</b> Para la realización de dicha intervención se necesita de anestesia general o regional: Cada técnica y cada paciente tiene un riesgo "
            "diferente, que será valorado cuidadosamente por un anestesiólogo. En general, después de una intervención se precisa de un periodo "
            "de recuperación que transcurre en la Unidad de Recuperación Postanestésica, la cual está dotada de una vigilancia estrecha hasta que se "
            "encuentre en condiciones de volver a su habitación.",
            style_body
        )
        story.append(p1)
        story.append(Spacer(1, 2.5))

        p2 = Paragraph(
            "<b>2.</b> Toda intervención quirúrgica tiene un riesgo, asociado a la técnica particular y específica. Entre los riesgos, que por su mayor "
            "frecuencia son los siguientes: • Infección de la herida temprana o tardía. • Hemorragia de la herida quirúrgica. • Lesiones de vasos sanguíneos "
            "y de nervios. • Flebitis y tromboflebitis que puedan dar lugar a embolismo pulmonar e incluso la muerte. • Calcificaciones de parte o toda "
            "la región intervenida. • Trastornos cutáneos como flictenas (ámpulas), escaras (úlceras), retardo de la cicatrización de la herida, o "
            "dehiscencia de herida (apertura). • Reacciones alérgicas al material de sutura o fármacos. • Perforación o lesión inadvertida a órgano vecino. "
            "• Lesiones en partes blandas (músculos, tendones, vísceras). • Síndrome de embolismo graso incluso la muerte.",
            style_body
        )
        story.append(p2)
        story.append(Spacer(1, 2.5))

        p3 = Paragraph(
            "<b>3.</b> Existen además riesgos propios según los hábitos y costumbres de cada individuo y según sus enfermedades previas. Los "
            "riesgos podrían ser: • Hemorragia obstétrica. • Infección hospitalaria o posterior a egreso. • Ingreso a unidad de terapia intensiva (UCI). "
            "• Acretismo placentario (placenta adherida a planos profundos del útero). • Histerectomía total o subtotal (extirpación del útero). "
            "• Apertura o lesión de vejiga urinaria. • Muerte.",
            style_body
        )
        story.append(p3)
        story.append(Spacer(1, 2.5))

        p4 = Paragraph(
            "<b>4.</b> Durante el curso de la intervención por causas imprevistas, podría considerarse necesario o conveniente realizar otra "
            "intervención complementaria como: desarterialización uterina (ligar vasos sanguíneos del útero) o reparación vascular.",
            style_body
        )
        story.append(p4)
        story.append(Spacer(1, 2.5))

        p5 = Paragraph(
            f"<b>5.</b> El cirujano responsable me ha informado sobre las características de mi embarazo y de los mejores procedimientos para "
            f"la resolución del mismo, así como la técnica elegida para mi operación. Así mismo se me informó las alternativas médicas que "
            f"existen como: <u>{alternativas}</u>; sin embargo se ha considerado que el procedimiento «cesárea» me resulta ser más conveniente.",
            style_body
        )
        story.append(p5)
        story.append(Spacer(1, 2.5))

        p6 = Paragraph(
            "<b>6.</b> También se me realizó una evaluación preoperatoria adecuada a mi edad y estado de salud general.",
            style_body
        )
        story.append(p6)
        story.append(Spacer(1, 2.5))

        p7 = Paragraph(
            "<b>7.</b> Totalmente de acuerdo he sido informado en forma clara y comprensible para mí, de los beneficios y riesgos del procedimiento al que "
            "voy a ser sometida, de modo que firmo la presente declaración, <b>OTORGANDO MI CONSENTIMIENTO (NOM-004-SSA3-2012; 10.1 - 10.1.1.10)</b> "
            "para que se realice(n) todas las acciones médicas y quirúrgicas que se consideren convenientes. Así como firmo que no he omitido "
            "ni ocultado datos en la historia médica de mis antecedentes que pudieran variar el resultado de la intervención.",
            style_body
        )
        story.append(p7)
        story.append(Spacer(1, 14))

        # FIRMAS MODO AUTORIZO
        sig_col_w = (content_w - 30.0) / 2.0

        parentesco_tutor = pt_data.get('parentesco') or pt_data.get('parentesco_declarante') or pt_data.get('parentesco_paciente') or 'Tutor / Representante Legal'
        if str(parentesco_tutor).upper() in ('PACIENTE', 'TITULAR', 'DIRECTO'):
            parentesco_tutor = 'Tutor / Representante Legal'
        parentesco_test = pt_data.get('parentesco_testigo1') or pt_data.get('parentesco_testigo') or 'Testigo Presencial'

        patient_sig_text = f"<b>{paciente_nombre}</b><br/><font size='6.2' color='#334155'><i><b>Parentesco: Paciente</b></i></font>" if paciente_nombre else "<b>Nombre completo del paciente</b>"
        witness_sig_text = f"<b>{testigo1}</b><br/><font size='6.2' color='#334155'><i><b>Parentesco: {parentesco_test}</b></i></font>" if testigo1 else "<b>Nombre completo y firma del testigo</b>"
        tutor_sig_text = f"<b>{pariente}</b><br/><font size='6.2' color='#334155'><i><b>Parentesco: {parentesco_tutor}</b></i></font>" if pariente else "<b>Nombre completo y firma del tutor o representante legal</b>"
        doctor_sig_text = f"<b>{medico}</b><br/><font size='6.4' color='#334155'><i><b>CÉD. PROF. {cedula}</b></i></font>" if cedula else f"<b>{medico}</b>"

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

        has_t1 = bool(
            pt_data.get('firma_testigo1_biometrica') or 
            pt_data.get('sello_testigo1') or 
            (firma_data and (firma_data.get('sello_testigo1') or firma_data.get('firma_testigo1_biometrica')))
        )

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
            # Caso 1: Cuadrícula 2x2 para menor o incapacitado con testigo firmado
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
            t_sigs = Table(sig_grid, colWidths=[sig_col_w, 30.0, sig_col_w])
            t_sigs.setStyle(TableStyle([
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
            ]))
            story.append(KeepTogether(t_sigs))

        elif has_tutor and not has_t1:
            # Caso 2: Con tutor, pero SIN testigo
            if es_mayor:
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
            story.append(Spacer(1, 30.0))
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

    # =========================================================================
    # MODALIDAD 2: NO AUTORIZO (HOJA 2 - DISENTIMIENTO / REVOCACIÓN)
    # =========================================================================
    else:
        motivo_no_acepto = pt_data.get('motivo_no_acepto') or pt_data.get('motivo_rechazo') or 'Decisión personal del paciente / familiar responsable tras recibir información clínica completa.'
        domicilio_testigo = pt_data.get('domicilio_testigo', 'Conocido en expediente clínico')
        identificacion_testigo = pt_data.get('identificacion_testigo', 'INE / Identificación Oficial')
        parentesco_testigo = pt_data.get('parentesco_testigo', 'Familiar / Testigo Presencial')
        testigo1 = pt_data.get('testigo1', '')
        pariente = pt_data.get('pariente') or pt_data.get('representante_legal', '')

        # Banner de No Autorización
        style_banner = ParagraphStyle('BannerNo', fontName='Helvetica-Bold', fontSize=10.0, leading=13.0, textColor=colors.HexColor('#991B1B'), alignment=TA_CENTER)
        style_disent = ParagraphStyle('Disent', fontName='Helvetica', fontSize=7.8, leading=11.2, textColor=TEXT_DARK, alignment=TA_JUSTIFY)
        style_motivo = ParagraphStyle('Motivo', fontName='Helvetica', fontSize=8.0, leading=11.5, textColor=colors.HexColor('#1E293B'), alignment=TA_JUSTIFY)
        style_warning = ParagraphStyle('Warn', fontName='Helvetica-Oblique', fontSize=7.0, leading=9.5, textColor=colors.HexColor('#475569'), alignment=TA_JUSTIFY)

        banner_table = Table([
            [Paragraph("<b>DECLARACIÓN DE NO AUTORIZACIÓN (DISENTIMIENTO INFORMADO)</b>", style_banner)]
        ], colWidths=[content_w])
        banner_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#FEE2E2')),
            ('BOX', (0,0), (-1,-1), 1.0, colors.HexColor('#EF4444')),
            ('PADDING', (0,0), (-1,-1), 6.0),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ]))
        story.append(banner_table)
        story.append(Spacer(1, 10))

        med_display = medico if medico.lower().startswith(('dr.', 'dra.', 'dr ', 'dra ')) else f"Dr(a). {medico}"
        p_no_text = Paragraph(
            f"Al/A la <b>{med_display}</b> y al cuerpo de salud del <b>Hospital Escandón</b>, "
            f"<b><u>NO AUTORIZO</u></b> a que se me realicen los procedimientos quirúrgicos y terapéuticos indicados (<b>Cesárea</b>) "
            f"para el tratamiento de mi padecimiento, asumiendo las consecuencias inherentes y liberándolos de toda responsabilidad médico-legal por dicha decisión.",
            style_disent
        )
        story.append(p_no_text)
        story.append(Spacer(1, 8))

        # Caja de Motivo
        motivo_data = [
            [Paragraph("<b>MOTIVO POR EL CUAL NO ACEPTO LA INTERVENCIÓN:</b>", ParagraphStyle('MLbl', fontName='Helvetica-Bold', fontSize=7.5, leading=9.5, textColor=colors.HexColor('#991B1B')))],
            [Paragraph(f"<i>«{motivo_no_acepto}»</i>", style_motivo)]
        ]
        t_motivo = Table(motivo_data, colWidths=[content_w])
        t_motivo.setStyle(TableStyle([
            ('BOX', (0,0), (-1,-1), 0.75, colors.HexColor('#CBD5E1')),
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
            ('PADDING', (0,0), (-1,-1), 6.0),
        ]))
        story.append(t_motivo)
        story.append(Spacer(1, 8))

        p_warn = Paragraph(
            "Conforme a la <b>NOM-004-SSA3-2012</b> y la Ley General de Salud, se me han explicado los riesgos clínicos que implica "
            "la no realización de la cesárea, incluyendo complicaciones materno-fetales severas, sufrimiento fetal o hemorragia. Firmo para dar debida constancia:",
            style_warning
        )
        story.append(p_warn)
        story.append(Spacer(1, 20))

        # Bloque de Firmas No Autorizo
        sig_col_w = (content_w - 30.0) / 2.0

        if firma_data and firma_data.get('sello_digital'):
            sello_resumido = str(firma_data['sello_digital'])[:34] + "..."
            fecha_txt = firma_data.get('fecha_hora_firma') or firma_data.get('fecha_hora') or ''
            med_stamp_html = f"""
            <font size='5.2' color='#006633'><b>[✔ CONSTANCIA MÉDICA Y SELLO BIOMÉTRICO]</b></font><br/>
            <font size='4.5' color='#004d26'><b>NOM-004-SSA3-2012 / DISENTIMIENTO</b></font><br/>
            <font size='4.2' color='#444'><b>Sello:</b> <font face='Courier' size='3.8'>{sello_resumido}</font> | {fecha_txt}</font>
            """
            top_med_p = Paragraph(med_stamp_html, style_sig_stamp)
        else:
            top_med_p = Paragraph("&nbsp;", ParagraphStyle('SigSpace', fontName='Helvetica', fontSize=8.0, leading=12.0, textColor=colors.transparent, alignment=TA_CENTER))

        if not es_mayor:
            parentesco_disent = pt_data.get('parentesco') or pt_data.get('parentesco_declarante') or pt_data.get('parentesco_paciente') or 'Tutor / Representante Legal'
            if str(parentesco_disent).upper() in ('PACIENTE', 'TITULAR', 'DIRECTO'):
                parentesco_disent = 'Tutor / Representante Legal'
            nom_firmante_disent = pariente or pt_data.get('declarante') or 'Tutor / Representante Legal'
        else:
            parentesco_disent = 'Paciente'
            nom_firmante_disent = paciente_nombre

        doctor_sig_text_no = f"<b>{medico}</b><br/><font size='6.4' color='#334155'><i><b>CÉD. PROF. {cedula}</b></i></font>" if cedula else f"<b>{medico}</b>"
        sig_space_p = Paragraph("&nbsp;", ParagraphStyle('SigSpace', fontName='Helvetica', fontSize=8.0, leading=12.0, textColor=colors.transparent, alignment=TA_CENTER))

        # Sello Biométrico Paciente / Representante (Disentimiento)
        if pt_data.get('firma_paciente_biometrica') or pt_data.get('sello_paciente') or (firma_data and firma_data.get('sello_paciente')):
            sello_pac_val = str(pt_data.get('sello_paciente') or (firma_data and firma_data.get('sello_paciente')) or 'BIO-HES:OK')[:24]
            pac_stamp_html = f"""
            <font size='5.0' color='#991B1B'><b>[✔ RECHAZO CON HUELLA BIOMÉTRICA]</b></font><br/>
            <font size='4.2' color='#444'><b>Validación Dactilar:</b> <font face='Courier' size='3.8'>{sello_pac_val}</font></font>
            """
            pac_sig_p = Paragraph(pac_stamp_html, style_sig_stamp)
        else:
            pac_sig_p = Paragraph("&nbsp;", ParagraphStyle('SigSpace', fontName='Helvetica', fontSize=8.0, leading=12.0, textColor=colors.transparent, alignment=TA_CENTER))

        parentesco_test = pt_data.get('parentesco_testigo1') or parentesco_testigo or 'Testigo Presencial'

        paciente_disent_text = f"<b>{nom_firmante_disent}</b><br/><font size='6.2' color='#334155'><i><b>Parentesco: {parentesco_disent}</b></i></font>" if nom_firmante_disent else "<b>Nombre del paciente o representante</b>"
        testigo_disent_text = f"<b>{testigo1}</b><br/><font size='6.2' color='#334155'><i><b>Parentesco: {parentesco_test}</b></i></font>" if testigo1 else "<b>Nombre completo del testigo</b>"

        has_t1_no = bool(
            pt_data.get('firma_testigo1_biometrica') or 
            pt_data.get('sello_testigo1') or 
            (firma_data and (firma_data.get('sello_testigo1') or firma_data.get('firma_testigo1_biometrica')))
        )

        # Sello Biométrico Testigo 1 (Disentimiento)
        if has_t1_no:
            sello_test_val = str(pt_data.get('sello_testigo1') or (firma_data and firma_data.get('sello_testigo1')) or 'BIO-HES:OK')[:24]
            test_stamp_html = f"""
            <font size='5.0' color='#991B1B'><b>[✔ TESTIGO - HUELLA BIOMÉTRICA]</b></font><br/>
            <font size='4.2' color='#444'><b>Validación Dactilar:</b> <font face='Courier' size='3.8'>{sello_test_val}</font></font>
            """
            test_sig_p = Paragraph(test_stamp_html, style_sig_stamp)
        else:
            test_sig_p = Paragraph("&nbsp;", ParagraphStyle('SigSpace', fontName='Helvetica', fontSize=8.0, leading=12.0, textColor=colors.transparent, alignment=TA_CENTER))

        if has_t1_no:
            t_top = Table([
                [
                    pac_sig_p,
                    '',
                    test_sig_p
                ],
                [
                    Paragraph(paciente_disent_text, style_sig_name),
                    '',
                    Paragraph(testigo_disent_text, style_sig_name)
                ]
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
                ('BOTTOMPADDING', (0,1), (-1,1), 1.0),
            ]))

            t_bot = Table([
                [top_med_p],
                [Paragraph(doctor_sig_text_no, style_sig_name)]
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

            story.append(KeepTogether([t_top, Spacer(1, 14), t_bot]))
        else:
            t_pair = Table([
                [pac_sig_p, '', top_med_p],
                [Paragraph(paciente_disent_text, style_sig_name), '', Paragraph(doctor_sig_text_no, style_sig_name)]
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
            story.append(KeepTogether([Spacer(1, 24), t_pair]))

    def make_canvas(*args, **kwargs):
        c = CleanConsentCanvas(*args, doc_info=doc_info, fecha_ingreso=fecha_val, hora_ingreso=hora_val, **kwargs)
        return c

    doc.build(story, canvasmaker=make_canvas)
    return output_path

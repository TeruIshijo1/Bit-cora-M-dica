# -*- coding: utf-8 -*-
"""
Motor PDF para el Formato 16: Egreso y Resumen Clínico
Código: HE-DIRMED-SINPRO-PLT-16
Conforme a NOM-004-SSA3-2012 y NOM-024-SSA3-2012
Exactamente 2 páginas oficiales institucionales con marco perimetral RDLC, membrete Fundación Escandón y sello FEA.
"""

import os
import re
import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, TableStyle, PageBreak
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY

try:
    from backend.pdf_engine_v2 import (
        CleanConsentCanvas, FRAME_X, FRAME_Y, FRAME_W, FRAME_H,
        TEXT_MUTED, TEXT_DARK, PRIMARY_BLUE, DARK_BLUE, BORDER_GREY, RED_ALERT,
        letterhead_content_width
    )
except ModuleNotFoundError:
    from pdf_engine_v2 import (
        CleanConsentCanvas, FRAME_X, FRAME_Y, FRAME_W, FRAME_H,
        TEXT_MUTED, TEXT_DARK, PRIMARY_BLUE, DARK_BLUE, BORDER_GREY, RED_ALERT,
        letterhead_content_width
    )


def _respuesta_si_no(value: object) -> str:
    """Devuelve sólo la respuesta elegida, con una presentación legible.

    Los formatos oficiales se llenan desde la bitácora y no necesitan
    imprimir una segunda casilla vacía.  Mantener únicamente la respuesta
    evita que el PDF muestre combinaciones poco legibles como ``[ ] SÍ [X]
    NO`` y conserva el valor clínico original.
    """
    normalized = str(value or "NO").strip().upper()
    affirmative = normalized in {"SI", "SÍ", "S", "1", "TRUE", "VERDADERO"}
    answer = "SÍ" if affirmative else "NO"
    color = "#047857" if affirmative else "#475569"
    return f'<font color="{color}"><b>{answer}</b></font>'


def generate_egreso_resumen_16(pt_data: dict, output_path: str = None, firma_data: dict = None) -> str:
    """
    Genera el PDF oficial para el Formato 16:
    HE-DIRMED-SINPRO-PLT-16: EGRESO Y RESUMEN CLÍNICO.
    Exactamente 2 páginas institucionales con marco RDLC, membrete y firma FEA/biométrica.
    """
    if output_path and os.path.dirname(output_path):
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

    content_x = FRAME_X + 13.0
    content_w = letterhead_content_width(content_x)

    frame_bottom = FRAME_Y + 39.0
    frame_top = (FRAME_Y + FRAME_H) - 59.0
    frame_h = frame_top - frame_bottom  # ~624.84 pt

    frame_p1 = Frame(content_x, frame_bottom, content_w, frame_h, id='p1_frame',
                     leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    frame_p2 = Frame(content_x, frame_bottom, content_w, frame_h, id='p2_frame',
                     leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)

    template_p1 = PageTemplate(id='FirstPage', frames=frame_p1)
    template_p2 = PageTemplate(id='LaterPages', frames=frame_p2)

    # Identificadores y metadatos
    expediente_raw = str(pt_data.get('expediente') or pt_data.get('mrn') or pt_data.get('pt_num') or '').strip()
    expediente_clean = re.sub(r'[^0-9]', '', expediente_raw) or expediente_raw
    folio_val = f"PT-{expediente_clean}" if expediente_clean and not str(expediente_clean).startswith("PT-") else expediente_raw

    fecha_val = pt_data.get('fecha_egreso') or pt_data.get('fecha_atencion') or pt_data.get('fecha_ingreso') or datetime.datetime.now().strftime('%d/%m/%Y')
    hora_val = pt_data.get('hora_egreso') or pt_data.get('hora_atencion') or pt_data.get('hora_ingreso') or datetime.datetime.now().strftime('%H:%M')

    doc_info = {
        'code': 'HE-DIRMED-SINPRO-PLT-16',
        'title_lines': [
            'EGRESO Y RESUMEN CLÍNICO'
        ],
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
        pageTemplates=[template_p1, template_p2]
    )

    # Estilos tipográficos institucionales optimizados para balance vertical
    style_val = ParagraphStyle('MetaVal', fontName='Helvetica', fontSize=8.2, leading=11.5, textColor=TEXT_DARK)
    style_sec_title = ParagraphStyle('SecTitle', fontName='Helvetica-Bold', fontSize=8.4, leading=11.5, textColor=PRIMARY_BLUE)
    style_content = ParagraphStyle('SecContent', fontName='Helvetica', fontSize=8.2, leading=13.0, textColor=TEXT_DARK, alignment=TA_JUSTIFY)

    style_sig_name = ParagraphStyle('SigName', fontName='Helvetica-Bold', fontSize=8.2, leading=11.0, textColor=TEXT_DARK, alignment=TA_CENTER)
    style_sig_stamp = ParagraphStyle('SigStamp', fontName='Helvetica', fontSize=5.6, leading=7.4, textColor=colors.HexColor('#006633'), alignment=TA_CENTER)
    style_sig_blank = ParagraphStyle('SigBlank', fontName='Helvetica', fontSize=6.0, leading=7.0, textColor=colors.transparent, alignment=TA_CENTER)

    story = []

    # Datos del paciente
    paciente_nombre = (pt_data.get('paciente_nombre') or pt_data.get('nombre') or '').strip().upper()
    fecha_nac = (pt_data.get('fecha_nacimiento') or pt_data.get('dob') or '').strip()
    edad_raw = str(pt_data.get('edad') or '').strip()
    edad_display = f"{edad_raw} años" if edad_raw and "año" not in edad_raw.lower() else (edad_raw or '____')

    medico = (pt_data.get('medico_tratante') or pt_data.get('n_medico') or pt_data.get('dr_tratante') or (firma_data.get('nombre_medico') if firma_data else '') or '').strip().upper()
    cedula = (pt_data.get('cedula') or pt_data.get('cedula_profesional') or pt_data.get('cedula_tratante') or (firma_data.get('cedula') if firma_data else '') or '').strip()
    medico_elaboro = (pt_data.get('medico_elaboro') or pt_data.get('n_medico_elaboro') or pt_data.get('dr_elaboro') or medico or '').strip().upper()
    cedula_elaboro = (pt_data.get('cedula_elaboro') or cedula or '').strip()

    medico_clean = re.sub(r'^(dr\(a\)\.?|dr\.|dra\.|dr|dra)\s*', '', medico, flags=re.IGNORECASE).strip()
    med_display = f"DR(A). {medico_clean}" if medico_clean else "DR(A). MÉDICO TRATANTE"

    diag_ingreso = (pt_data.get('diagnostico') or pt_data.get('diag_ingreso') or pt_data.get('diagnostico_ingreso') or 'NO ESPECIFICADO').strip().upper()

    # Signos vitales al egreso
    ta_sis = str(pt_data.get('ta') or pt_data.get('ta_sis') or '___').strip()
    ta_dis = str(pt_data.get('ta_dis') or '___').strip()
    ta_display = f"{ta_sis}/{ta_dis} mmHg" if ta_sis != '___' or ta_dis != '___' else "___/___ mmHg"
    fc_val = str(pt_data.get('pulso') or pt_data.get('fc') or '___').strip()
    fr_val = str(pt_data.get('fr_respi') or pt_data.get('fr') or '___').strip()
    temp_val = str(pt_data.get('temperatura') or pt_data.get('temp') or '___').strip()
    sat_val = str(pt_data.get('sat_oxi') or pt_data.get('spo2') or '___').strip()

    reingreso_val = str(pt_data.get('reingreso') or pt_data.get('REINGRESO') or 'NO').strip().upper()
    reingreso_respuesta = _respuesta_si_no(reingreso_val)

    # Secciones Página 1
    reea_text = (pt_data.get('reea') or pt_data.get('resumen_evolucion') or 'Sin particularidades registradas. Paciente con evolución clínica favorable y respuesta adecuada al tratamiento.').strip()
    mdeh_text = (pt_data.get('mdeh') or pt_data.get('manejo_estancia') or 'Vigilancia hemodinámica continua, control de dolor, monitoreo estrecho de signos vitales y esquema farmacológico institucional.').strip()
    pmq_text = (pt_data.get('pmq') or pt_data.get('procedimientos') or 'No se realizaron procedimientos invasivos mayores durante la estancia hospitalaria.').strip()
    elg_text = (pt_data.get('elg') or pt_data.get('laboratorio_gabinete') or 'Estudios de control en parámetros clínicos esperados para la evolución satisfactoria del paciente.').strip()
    pmt_text = (pt_data.get('pmt') or pt_data.get('plan_manejo') or 'Alta hospitalaria por mejoría clínica con indicaciones médicas domiciliarias, cuidados generales y cita de seguimiento.').strip()
    comp_text = (pt_data.get('complicaciones') or pt_data.get('COMPLICACIONES') or 'Sin complicaciones aparentes durante su estancia hospitalaria.').strip()
    meg_text = (pt_data.get('meg') or pt_data.get('motivo_egreso') or 'Máximo beneficio hospitalario / Curación / Mejoría clínica.').strip()

    # Secciones Página 2
    df_text = (pt_data.get('df') or pt_data.get('diagnostico_final') or pt_data.get('diagnostico_egreso') or diag_ingreso).strip().upper()
    pcpcpe_text = (pt_data.get('pcpcpe') or pt_data.get('problemas_pendientes') or 'Sin problemas clínicos pendientes. Signos vitales estables, adecuada tolerancia a la vía oral y deambulación independiente.').strip()
    rvais_text = (pt_data.get('rvais') or pt_data.get('recomendaciones') or 'Continuar con reposo relativo, estricta vigilancia de datos de alarma y acudir puntualmente a consulta externa de seguimiento.').strip()
    afr_text = (pt_data.get('afr') or pt_data.get('factores_riesgo') or 'Evitar tabaquismo y alcoholismo, mantener dieta balanceada, hidratación adecuada y control de comorbilidades.').strip()
    edu_text = (pt_data.get('edu_pact') or pt_data.get('educacion_paciente') or 'Se orientó ampliamente al paciente y familiares sobre datos de alarma (fiebre, sangrado, dolor agudo, dificultad respiratoria) para acudir de inmediato al servicio de Urgencias.').strip()
    cmep_text = (pt_data.get('cmep') or pt_data.get('medicacion_domicilio') or 'Medicamentos prescritos conforme a la receta médica oficial entregada al egreso hospitalario.').strip()

    c_muerte_text = (pt_data.get('c_muerte') or pt_data.get('causa_muerte') or 'NO APLICA (EGRESO POR MEJORÍA CLÍNICA)').strip().upper()
    necropsia_val = str(pt_data.get('enecropsia') or pt_data.get('necropsia') or 'NO').strip().upper()
    necropsia_respuesta = _respuesta_si_no(necropsia_val)

    # =========================================================================
    # PÁGINA 1: DATOS, SIGNOS Y MANEJO EN ESTANCIA
    # =========================================================================

    # 1. Tabla de metadatos superiores
    pt_table_data = [
        [
            Paragraph(f"<b>NOMBRE DEL PACIENTE:</b> {paciente_nombre or '________________________________'}", style_val),
            Paragraph(f"<b>FECHA DE NAC.:</b> {fecha_nac or '___/___/_____'}", style_val),
            Paragraph(f"<b>EDAD:</b> {edad_display}", style_val)
        ],
        [
            Paragraph(f"<b>EXPEDIENTE:</b> {folio_val}", style_val),
            Paragraph(f"<b>MÉDICO:</b> {med_display}", style_val),
            Paragraph(f"<b>FECHA:</b> {fecha_val}", style_val)
        ],
        [
            Paragraph(f"<b>DIAGNÓSTICO DE INGRESO:</b> {diag_ingreso}", style_val),
            '',
            ''
        ]
    ]
    t_pt = Table(pt_table_data, colWidths=[content_w * 0.46, content_w * 0.32, content_w * 0.22])
    t_pt.setStyle(TableStyle([
        ('SPAN', (0, 2), (2, 2)),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4.0),
        ('TOPPADDING', (0, 0), (-1, -1), 4.0),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('LINEBELOW', (0, -1), (-1, -1), 1.0, PRIMARY_BLUE),
    ]))
    story.append(t_pt)
    story.append(Spacer(1, 10.0))

    # 2. Signos Vitales al Egreso y Reingreso
    vitals_row1 = [
        Paragraph(f"<b>SIGNOS VITALES:</b>", style_sec_title),
        Paragraph(f"<b>T.A.:</b> {ta_display}", style_val),
        Paragraph(f"<b>F.C.:</b> {fc_val} lpm", style_val),
        Paragraph(f"<b>F.R.:</b> {fr_val} rpm", style_val),
        Paragraph(f"<b>TEMP:</b> {temp_val} °C", style_val),
        Paragraph(f"<b>SAT O<sub>2</sub>:</b> {sat_val} %", style_val)
    ]
    t_vitals = Table([vitals_row1], colWidths=[content_w * 0.20, content_w * 0.18, content_w * 0.15, content_w * 0.15, content_w * 0.16, content_w * 0.16])
    t_vitals.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4.0),
        ('TOPPADDING', (0, 0), (-1, -1), 4.0),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(t_vitals)
    story.append(Spacer(1, 8.0))

    # Identificación de reingreso
    p_reingreso = Paragraph(
        f"<b>IDENTIFICACIÓN DE REINGRESO POR MISMA AFECCIÓN EN EL AÑO:</b> &nbsp;&nbsp; {reingreso_respuesta}",
        style_val
    )
    story.append(p_reingreso)
    story.append(Spacer(1, 20.0))

    # Bloques de la Página 1
    p1_blocks = [
        ("Resumen de la evolución y el estado actual:", reea_text),
        ("Manejo durante la estancia hospitalaria:", mdeh_text),
        ("Procedimientos médico-quirúrgicos realizados:", pmq_text),
        ("Estudios de laboratorio o gabinete:", elg_text),
        ("Plan de manejo y tratamiento:", pmt_text),
        ("Complicaciones:", comp_text),
        ("Motivo del egreso:", meg_text),
    ]

    for title, txt in p1_blocks:
        story.append(Paragraph(f"<b>{title.upper()}</b>", style_sec_title))
        story.append(Spacer(1, 3.5))
        story.append(Paragraph(txt if txt else 'Sin particularidades registradas.', style_content))
        story.append(Spacer(1, 20.0))

    # SALTO A PÁGINA 2
    story.append(PageBreak())

    # =========================================================================
    # PÁGINA 2: DIAGNÓSTICO FINAL, CONTINUIDAD Y FIRMAS
    # =========================================================================

    p2_blocks = [
        ("Diagnóstico final:", df_text),
        ("Problemas clínicos pendientes y condiciones del paciente a su egreso:", pcpcpe_text),
        ("Recomendaciones para vigilancia ambulatoria e instrucciones de seguimiento:", rvais_text),
        ("Atención a factores de riesgo:", afr_text),
        ("Educación al paciente y medidas preventivas:", edu_text),
        ("Medicación prescrita al egreso / Medicación domiciliaria:", cmep_text),
    ]

    for title, txt in p2_blocks:
        story.append(Paragraph(f"<b>{title.upper()}</b>", style_sec_title))
        story.append(Spacer(1, 3.5))
        story.append(Paragraph(txt if txt else 'Sin particularidades registradas.', style_content))
        story.append(Spacer(1, 20.0))

    # Sección Defunción y Necropsia integrada en tabla limpia
    defuncion_table_data = [
        [
            Paragraph(f"<b>EN CASO DE DEFUNCIÓN - CAUSA DE LA MUERTE:</b> {c_muerte_text}", style_val)
        ],
        [
            Paragraph(f"<b>ESTUDIO DE NECROPSIA:</b> {necropsia_respuesta}", style_val)
        ]
    ]
    # Un renglón por respuesta evita que la causa de defunción y la necropsia
    # se amontonen cuando la causa ocupa más de una línea.
    t_def = Table(defuncion_table_data, colWidths=[content_w])
    t_def.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4.0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5.0),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(t_def)
    story.append(Spacer(1, 140.0))

    # BLOQUE DE FIRMAS (2 COLUMNAS: MÉDICO ELABORÓ Y MÉDICO TRATANTE)
    doctor_elaboro_sig_text = f"<b>{medico_elaboro}</b><br/><font size='6.4' color='#334155'><i><b>MÉDICO QUE ELABORÓ EL RESUMEN • CÉD. PROF. {cedula_elaboro}</b></i></font>" if cedula_elaboro else f"<b>{medico_elaboro}</b><br/><font size='6.4' color='#334155'><i>MÉDICO QUE ELABORÓ EL RESUMEN</i></font>"
    doctor_tratante_sig_text = f"<b>{medico}</b><br/><font size='6.4' color='#334155'><i><b>MÉDICO TRATANTE • CÉD. PROF. {cedula}</b></i></font>" if cedula else f"<b>{medico}</b><br/><font size='6.4' color='#334155'><i>MÉDICO TRATANTE</i></font>"

    top_med1_p = Paragraph("&nbsp;", style_sig_blank)
    top_med2_p = Paragraph("&nbsp;", style_sig_blank)

    if firma_data and (firma_data.get('sello_digital') or firma_data.get('hash_sha256')):
        sello_raw = str(firma_data.get('sello_digital') or firma_data.get('hash_sha256') or '')
        sello_resumido = (sello_raw[:26] + '...') if len(sello_raw) > 26 else sello_raw
        fecha_txt = firma_data.get('fecha_hora_firma') or firma_data.get('fecha_hora') or datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        stamp_html = f"""
        <font size='5.4' color='#006633'><b>[✔ FIRMA DIGITAL MÉDICA CON HUELLA]</b></font><br/>
        <font size='4.6' color='#004d26'><b>NOM-004-SSA3-2012 / NOM-024-SSA3-2012</b></font><br/>
        <font size='4.0' color='#444'><b>Sello:</b> <font face='Courier'>{sello_resumido}</font> | {fecha_txt}</font>
        """
        top_med1_p = Paragraph(stamp_html, style_sig_stamp)
        top_med2_p = Paragraph(stamp_html, style_sig_stamp)

    gap_col_w = 40.0
    sig_col_w = (content_w - gap_col_w) / 2.0  # ~248.88 pt

    sig_grid = [
        [top_med1_p, '', top_med2_p],
        [Paragraph(doctor_elaboro_sig_text, style_sig_name), '', Paragraph(doctor_tratante_sig_text, style_sig_name)]
    ]
    t_style = [
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,0), 'BOTTOM'),
        ('VALIGN', (0,1), (-1,1), 'TOP'),
        ('LINEABOVE', (0,1), (0,1), 0.8, PRIMARY_BLUE),
        ('LINEABOVE', (2,1), (2,1), 0.8, PRIMARY_BLUE),
        ('TOPPADDING', (0,0), (-1,0), 0),
        ('BOTTOMPADDING', (0,0), (-1,0), 2.0),
        ('TOPPADDING', (0,1), (-1,1), 5.0),
        ('BOTTOMPADDING', (0,1), (-1,1), 5.0),
    ]
    t_sigs = Table(sig_grid, colWidths=[sig_col_w, gap_col_w, sig_col_w])
    t_sigs.setStyle(TableStyle(t_style))
    story.append(t_sigs)

    def make_canvas(*args, **kwargs):
        return CleanConsentCanvas(*args, doc_info=doc_info, fecha_ingreso=fecha_val, hora_ingreso=hora_val, **kwargs)

    doc.build(story, canvasmaker=make_canvas)
    return output_path


if __name__ == '__main__':
    # Test standalone
    sample_data = {
        'paciente_nombre': 'GONZÁLEZ PÉREZ MARÍA ELENA',
        'expediente': 'PT-5704',
        'fecha_nacimiento': '14/05/1982',
        'edad': '44',
        'medico_tratante': 'DR. ROBERTO CASTILLO MORALES',
        'cedula': '7891234',
        'medico_elaboro': 'DRA. ANA KAREN TORRES RÍOS',
        'cedula_elaboro': '9876543',
        'diagnostico': 'COLECISTITIS CRÓNICA LITIÁSICA AGUDIZADA',
        'fecha_egreso': '23/09/2026',
        'hora_egreso': '12:00',
        'ta': '120',
        'ta_dis': '80',
        'pulso': '72',
        'fr_respi': '18',
        'temperatura': '36.5',
        'sat_oxi': '98',
        'reingreso': 'NO',
        'reea': 'Paciente femenino de 44 años con evolución postquirúrgica satisfactoria a colecistectomía laparoscópica. Afebril, tolerando dieta blanda, heridas quirúrgicas limpias y sin datos de sangrado o infección.',
        'mdeh': 'Manejo analgésico postoperatorio, antibioticoterapia profiláctica, hidratación parenteral y deambulación temprana asistida.',
        'pmq': 'Colecistectomía laparoscópica realizada el 21/09/2026 a las 09:30 hrs sin incidentes ni accidentes.',
        'elg': 'Biometría hemática y química sanguínea de control en rangos normales. Pruebas de función hepática con bilirrubinas estables.',
        'pmt': 'Egreso a domicilio por mejoría clínica con analgésicos orales por 5 días y cuidados locales de herida.',
        'complicaciones': 'Ninguna registrada.',
        'meg': 'Máximo beneficio hospitalario / Curación quirúrgica.',
        'df': 'COLECISTITIS CRÓNICA LITIÁSICA RESOLUCIÓN POR COLECISTECTOMÍA LAPAROSCÓPICA',
        'pcpcpe': 'Ninguno pendiente. Heridas quirúrgicas afrontadas adecuadamente, retiro de puntos en 7 días.',
        'rvais': 'Cita en consulta externa de Cirugía General en 7 días para retiro de puntos y valoración integral.',
        'afr': 'Dieta baja en colecistoquinéticos (grasas, irritantes, lácteos enteros) durante 30 días.',
        'edu_pact': 'Se capacitó al paciente y familiar en signos de alarma (fiebre > 38°C, dolor abdominal intenso, ictericia, salida de material purulento por heridas).',
        'cmep': 'Paracetamol 500 mg VO c/8h por 5 días; Ketorolaco 10 mg VO c/8h en caso de dolor moderado por 3 días.',
        'c_muerte': 'NO APLICA',
        'enecropsia': 'NO'
    }
    sample_firma = {
        'sello_digital': 'FEA-HES-9876543210ABCDEF12345678',
        'hash_sha256': 'a1b2c3d4e5f67890123456789abcdef0123456789abcdef0123456789abcdef0',
        'fecha_hora_firma': '23/09/2026 12:00:00',
        'nombre_medico': 'DR. ROBERTO CASTILLO MORALES',
        'cedula': '7891234'
    }
    out = os.path.join(os.path.dirname(__file__), '..', 'scratch', 'TEST_ERC_16.pdf')
    generate_egreso_resumen_16(sample_data, out, firma_data=sample_firma)
    print(f"Generated test PDF at: {out}")

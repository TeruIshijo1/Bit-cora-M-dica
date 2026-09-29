# -*- coding: utf-8 -*-
"""
Motor PDF para el Formato 09: Consentimiento Informado para Transfusión de Hemocomponentes
Código: HE-DIRMED-CONSUL-PLT-09
Conforme a NOM-004-SSA3-2012, NOM-024-SSA3-2012 y NOM-253-SSA1-2012
1 página oficial institucional con distribución armónica total, marco y pie oficial HES.
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
from xml.sax.saxutils import escape

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


def generate_consentimiento_09(pt_data: dict, output_path: str = None, firma_data: dict = None) -> str:
    """
    Genera el PDF oficial para el Formato 09:
    HE-DIRMED-CONSUL-PLT-09: CONSENTIMIENTO INFORMADO PARA TRANSFUSIÓN DE HEMOCOMPONENTES.
    Exactamente 1 página institucional con aprovechamiento armónico total, marco RDLC,
    inteligencia demográfica de tutor/menores y sello biométrico digital.
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

    template_p1 = PageTemplate(id='FirstPage', frames=frame_p1)

    # Extraer identificadores y datos
    expediente_raw = str(pt_data.get('expediente') or pt_data.get('mrn') or pt_data.get('pt_num') or '').strip()
    expediente_clean = re.sub(r'[^0-9]', '', expediente_raw) or expediente_raw
    folio_val = f"PT-{expediente_clean}" if expediente_clean and not str(expediente_clean).startswith("PT-") else expediente_raw

    fecha_val = pt_data.get('fecha_atencion') or pt_data.get('fecha_ingreso') or datetime.datetime.now().strftime('%d/%m/%Y')
    hora_val = pt_data.get('hora_atencion') or pt_data.get('hora_ingreso') or datetime.datetime.now().strftime('%H:%M')

    doc_info = {
        'code': 'HE-DIRMED-CONSUL-PLT-09',
        'title_lines': [
            'CONSENTIMIENTO INFORMADO',
            'AUTORIZACIÓN DE TRANSFUSIÓN',
            'DE HEMOCOMPONENTES'
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
        pageTemplates=[template_p1]
    )

    # Estilos tipográficos calibrados para distribución armónica de página completa
    style_val = ParagraphStyle('MetaVal', fontName='Helvetica', fontSize=8.0, leading=10.8, textColor=TEXT_DARK)
    
    style_auth = ParagraphStyle('AuthIntro', fontName='Helvetica', fontSize=8.0, leading=11.8, textColor=TEXT_DARK, alignment=TA_JUSTIFY)
    style_body = ParagraphStyle('BodyClinico', fontName='Helvetica', fontSize=7.9, leading=11.6, textColor=TEXT_DARK, alignment=TA_JUSTIFY)
    style_components = ParagraphStyle('CompBox', fontName='Helvetica-Bold', fontSize=8.2, leading=12.0, textColor=DARK_BLUE, alignment=TA_LEFT)

    style_sig_name = ParagraphStyle('SigName', fontName='Helvetica-Bold', fontSize=8.0, leading=10.2, textColor=TEXT_DARK, alignment=TA_CENTER)
    style_sig_stamp = ParagraphStyle('SigStamp', fontName='Helvetica', fontSize=5.4, leading=7.2, textColor=colors.HexColor('#006633'), alignment=TA_CENTER)
    style_sig_blank = ParagraphStyle('SigBlank', fontName='Helvetica', fontSize=6.0, leading=7.0, textColor=colors.transparent, alignment=TA_CENTER)

    style_verif_title = ParagraphStyle('VerifTitle', fontName='Helvetica-Bold', fontSize=7.2, leading=9.2, textColor=PRIMARY_BLUE, alignment=TA_LEFT)
    style_verif_body = ParagraphStyle('VerifBody', fontName='Helvetica', fontSize=6.8, leading=9.2, textColor=TEXT_DARK, alignment=TA_LEFT)
    style_verif_sig = ParagraphStyle('VerifSig', fontName='Helvetica-Bold', fontSize=7.2, leading=9.4, textColor=DARK_BLUE, alignment=TA_CENTER)
    style_verif_field = ParagraphStyle('VerifField', fontName='Helvetica', fontSize=6.2, leading=8.0, textColor=TEXT_DARK, alignment=TA_CENTER)
    style_verif_caption = ParagraphStyle('VerifCaption', fontName='Helvetica', fontSize=5.6, leading=7.0, textColor=TEXT_MUTED, alignment=TA_CENTER)

    story = []

    # 1. Datos del Paciente
    paciente_nombre = (pt_data.get('paciente_nombre') or pt_data.get('nombre') or '').strip().upper()
    fecha_nac = (pt_data.get('fecha_nacimiento') or pt_data.get('dob') or '').strip()
    edad_raw = str(pt_data.get('edad') or '').strip()
    edad_display = f"{edad_raw} años" if edad_raw and "año" not in edad_raw.lower() else (edad_raw or '____')

    medico = (pt_data.get('medico_tratante') or pt_data.get('n_medico') or (firma_data.get('nombre_medico') if firma_data else '') or '').strip().upper()
    cedula = (pt_data.get('cedula') or pt_data.get('cedula_profesional') or (firma_data.get('cedula') if firma_data else '') or '').strip()

    medico_clean = re.sub(r'^(dr\(a\)\.?|dr\.|dra\.|dr|dra)\s*', '', medico, flags=re.IGNORECASE).strip()
    med_display = f"DR(A). {medico_clean}" if medico_clean else "DR(A). MÉDICO TRATANTE"

    # Capacidad legal y tutor
    paciente_capaz = pt_data.get('paciente_capaz', True)
    if isinstance(paciente_capaz, str):
        paciente_capaz = paciente_capaz.lower() in ('true', '1', 'si', 'yes')
    elif isinstance(paciente_capaz, (int, float)):
        paciente_capaz = bool(paciente_capaz)

    # Verificación de menor de edad
    try:
        match_age = re.search(r'\d+', str(edad_raw))
        if match_age and int(match_age.group(0)) < 18:
            paciente_capaz = False
    except Exception:
        pass

    pariente = (pt_data.get('representante_legal') or pt_data.get('pariente') or pt_data.get('yo_autorizo') or pt_data.get('declarante') or '').strip().upper()
    if not paciente_capaz:
        parentesco = (pt_data.get('parentesco') or pt_data.get('parentesco_declarante') or 'TUTOR / REPRESENTANTE LEGAL').strip().upper()
        if parentesco in ('PACIENTE', 'TITULAR', 'DIRECTO', 'EL PACIENTE'):
            parentesco = 'TUTOR / REPRESENTANTE LEGAL'
        nom_autoriza = pariente or pt_data.get('declarante') or 'TUTOR / REPRESENTANTE LEGAL'
        calidad_autoriza = f"como familiar, tutor o representante legal ({parentesco}) del paciente <b>{paciente_nombre}</b>"
    else:
        parentesco = 'EL PACIENTE'
        nom_autoriza = paciente_nombre or 'EL PACIENTE'
        calidad_autoriza = "en pleno uso de mis facultades y capacidad legal"

    # Hemocomponentes autorizados
    hemo_autorizados = (
        pt_data.get('acepto_y_autorizo_transfusion_de') or 
        pt_data.get('ACEPTO_Y_AUTORIZO_TRANSFUSION_DE') or 
        pt_data.get('hemocomponentes') or 
        'PAQUETE GLOBULAR / CONCENTRADO ERITROCITARIO / PLASMA FRESCO CONGELADO / PLAQUETAS SEGÚN REQUERIMIENTO CLÍNICO'
    ).strip().upper()

    testigo1 = (pt_data.get('testigo_1') or pt_data.get('TESTIGO_1') or pt_data.get('testigo1') or '').strip().upper()
    testigo2 = (pt_data.get('testigo_2') or pt_data.get('TESTIGO_2') or pt_data.get('testigo2') or '').strip().upper()
    verifico_nombre = (pt_data.get('verifico_nombre') or pt_data.get('personal_verifico') or pt_data.get('enfermeria') or 'PERSONAL DE SALUD / BANCO DE SANGRE').strip().upper()

    # 1. TABLA SUPERIOR DE DATOS GENERALES
    pt_table_data = [
        [
            Paragraph(f"<b>NOMBRE DEL PACIENTE:</b> {paciente_nombre or '________________________________'}", style_val),
            Paragraph(f"<b>FECHA DE NAC.:</b> {fecha_nac or '___/___/_____'}", style_val),
            Paragraph(f"<b>EDAD:</b> {edad_display}", style_val)
        ],
        [
            Paragraph(f"<b>EXPEDIENTE:</b> {folio_val}", style_val),
            Paragraph(f"<b>MÉDICO TRATANTE:</b> {med_display}", style_val),
            Paragraph(f"<b>FECHA / HORA:</b> {fecha_val} {hora_val} hrs", style_val)
        ]
    ]
    t_pt = Table(pt_table_data, colWidths=[content_w * 0.46, content_w * 0.28, content_w * 0.26])
    t_pt.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3.5),
        ('TOPPADDING', (0, 0), (-1, -1), 3.5),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('LINEBELOW', (0, -1), (-1, -1), 0.8, PRIMARY_BLUE),
    ]))
    story.append(t_pt)
    story.append(Spacer(1, 12.0))

    # 2. CLÁUSULA DE AUTORIZACIÓN
    p_auth = Paragraph(
        f"Por este medio y sin presión alguna yo, <b>{nom_autoriza}</b> {calidad_autoriza}, con No. de expediente <b>{folio_val}</b>, "
        f"autorizo expresamente al cuerpo médico de este Hospital para que se realice el procedimiento denominado <b>Transfusión de hemocomponentes</b> "
        f"a cargo del <b>{med_display}</b>, en el establecimiento a su cargo.",
        style_auth
    )
    story.append(p_auth)
    story.append(Spacer(1, 10.0))

    # 3. CUERPO INFORMATIVO Y CLÍNICO
    p_c1 = Paragraph(
        "He sido debidamente informada(o) por parte del médico tratante acerca de la patología que se padece y que requiere tratamiento mediante "
        "transfusión de sangre y/o hemoderivados. Estoy enterado(a) de que la transfusión de hemocomponentes (glóbulos rojos, plaquetas, "
        "plasma fresco congelado y crioprecipitados) tiene como objetivo cubrir la necesidad de aporte externo de componentes sanguíneos necesarios "
        "en cantidad y calidad. Se me ha explicado de forma clara y satisfactoria qué es, cómo se realiza y cuál es el beneficio esperado del procedimiento.",
        style_body
    )
    story.append(p_c1)
    story.append(Spacer(1, 10.0))

    p_c2 = Paragraph(
        "La sangre y hemocomponentes provienen de donantes altruistas y sanos. Cada unidad es estudiada exhaustivamente con técnicas de precisión "
        "para la detección de Hepatitis B, Hepatitis C, Sífilis, V.I.H. (virus de inmunodeficiencia humana), Brucelosis y otros agentes infecciosos conforme a la <b>NOM-253-SSA1-2012</b>.<br/>"
        "Estoy plenamente informado(a) sobre los riesgos potenciales: debido a los límites de detección analítica y al periodo de ventana inmunológica, "
        "existe un riesgo residual mínimo de transmisión de agentes infecciosos (riesgo estimado de VIH 1 en 400,000, Hepatitis C 1 en 100,000 y Hepatitis B 1 en 63,000 unidades transfundidas).",
        style_body
    )
    story.append(p_c2)
    story.append(Spacer(1, 10.0))

    p_c3 = Paragraph(
        "Otro riesgo reconocido de la transfusión es la posibilidad de originar aloinmunización o sensibilización a antígenos celulares y plasmáticos, "
        "lo cual puede desencadenar reacciones transfusionales leves, moderadas o graves. Conozco los riesgos y beneficios de la transfusión de hemocomponentes "
        "y acepto de forma voluntaria la administración de los mismos bajo indicación y vigilancia médica estricta.<br/>"
        "Estoy consciente de que existen alternativas médicas (hierro parenteral, ácido fólico, vitamina B12, eritropoyetina humana recombinante, entre otras); "
        "sin embargo, el juicio clínico del médico tratante determina cuándo la transfusión es la indicación oportuna para preservar la salud o la vida.",
        style_body
    )
    story.append(p_c3)
    story.append(Spacer(1, 10.0))

    p_c4 = Paragraph(
        "He comprendido la información provista, en la que se detallan el procedimiento, riesgos, alternativas y cuidados pre y postransfusionales. "
        "Hago constar que se han respondido satisfactoriamente todas mis dudas respecto a la transfusión de hemocomponentes y, por medio de la presente, "
        "otorgo mi consentimiento informado pleno para la aplicación de las unidades y hemocomponentes que prescriba el médico tratante.",
        style_body
    )
    story.append(p_c4)
    story.append(Spacer(1, 14.0))

    # 4. HEMOCOMPONENTES AUTORIZADOS (Limpio y directo, sin recuadros pesados)
    p_comp = Paragraph(
        f"<font color='#005FA8'><b>ACEPTO Y AUTORIZO LA TRANSFUSIÓN DE:</b></font>&nbsp;&nbsp;<b>{hemo_autorizados}</b>",
        style_components
    )
    story.append(p_comp)
    story.append(Spacer(1, 20.0))

    # 5. SELLOS Y FIRMAS BIOMÉTRICAS DIGITALES (NOM-004 / NOM-024)
    has_t1 = bool(
        pt_data.get('firma_testigo1_biometrica') or 
        pt_data.get('sello_testigo1') or 
        (firma_data and firma_data.get('sello_testigo1')) or
        (firma_data and firma_data.get('firma_testigo1_biometrica')) or
        testigo1
    )
    has_t2 = bool(
        pt_data.get('firma_testigo2_biometrica') or 
        pt_data.get('sello_testigo2') or 
        (firma_data and firma_data.get('sello_testigo2')) or
        (firma_data and firma_data.get('firma_testigo2_biometrica')) or
        testigo2
    )

    paciente_clean = re.sub(r'\s*\([^)]*\)', '', str(nom_autoriza or paciente_nombre or '')).strip().upper()
    testigo1_clean = re.sub(r'\s*\([^)]*\)', '', str(testigo1 or '')).strip().upper()
    testigo2_clean = re.sub(r'\s*\([^)]*\)', '', str(testigo2 or '')).strip().upper()

    if paciente_capaz:
        patient_sig_text = f"<b>{paciente_clean}</b><br/><font size='6.2' color='#334155'><i>PACIENTE (OTORGANTE)</i></font>"
    else:
        label_tutor = f"TUTOR / REPRESENTANTE LEGAL ({parentesco})" if parentesco else "TUTOR / REPRESENTANTE LEGAL"
        patient_sig_text = f"<b>{paciente_clean}</b><br/><font size='6.2' color='#334155'><i>{label_tutor}</i></font>"

    witness1_sig_text = f"<b>{testigo1_clean}</b><br/><font size='6.2' color='#334155'><i>TESTIGO 1 (NOMBRE Y FIRMA)</i></font>" if testigo1_clean else "<b>TESTIGO 1</b><br/><font size='6.2' color='#334155'><i>(NOMBRE Y FIRMA)</i></font>"
    witness2_sig_text = f"<b>{testigo2_clean}</b><br/><font size='6.2' color='#334155'><i>TESTIGO 2 (NOMBRE Y FIRMA)</i></font>" if testigo2_clean else "<b>TESTIGO 2</b><br/><font size='6.2' color='#334155'><i>(NOMBRE Y FIRMA)</i></font>"

    doctor_sig_text = f"<b>{medico}</b><br/><font size='6.2' color='#334155'><i><b>MÉDICO TRATANTE • CÉD. PROF. {cedula}</b></i></font>" if cedula else f"<b>{medico}</b><br/><font size='6.2' color='#334155'><i>MÉDICO TRATANTE</i></font>"

    # Sellos Digitales / Biométricos
    top_med_p = Paragraph("&nbsp;", style_sig_blank)
    if firma_data and (firma_data.get('sello_digital') or firma_data.get('hash_sha256')):
        sello_raw = str(firma_data.get('sello_digital') or firma_data.get('hash_sha256') or '')
        sello_resumido = (sello_raw[:26] + '...') if len(sello_raw) > 26 else sello_raw
        fecha_txt = firma_data.get('fecha_hora_firma') or firma_data.get('fecha_hora') or datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        stamp_html = f"""
        <font size='5.4' color='#006633'><b>[✔ FIRMA DIGITAL MÉDICA CON HUELLA]</b></font><br/>
        <font size='4.6' color='#004d26'><b>NOM-004-SSA3-2012 / NOM-024-SSA3-2012</b></font><br/>
        <font size='4.0' color='#444'><b>Sello:</b> <font face='Courier'>{sello_resumido}</font> | {fecha_txt}</font>
        """
        top_med_p = Paragraph(stamp_html, style_sig_stamp)

    pac_sig_p = Paragraph("&nbsp;", style_sig_blank)
    if pt_data.get('firma_paciente_biometrica') or pt_data.get('sello_paciente') or (firma_data and firma_data.get('sello_paciente')):
        sello_pac_val = str(pt_data.get('sello_paciente') or (firma_data and firma_data.get('sello_paciente')) or 'BIO-HES:OK')[:22]
        lbl_sello_pac = "[✔ AUTORIZADO CON HUELLA BIOMÉTRICA]" if paciente_capaz else "[✔ AUTORIZADO POR TUTOR LEGAL]"
        pac_stamp_html = f"""
        <font size='5.2' color='#006633'><b>{lbl_sello_pac}</b></font><br/>
        <font size='4.2' color='#444'><b>Validación Dactilar:</b> <font face='Courier'>{sello_pac_val}</font></font>
        """
        pac_sig_p = Paragraph(pac_stamp_html, style_sig_stamp)

    test1_sig_p = Paragraph("&nbsp;", style_sig_blank)
    if pt_data.get('firma_testigo1_biometrica') or pt_data.get('sello_testigo1') or (firma_data and firma_data.get('sello_testigo1')):
        sello_t1_val = str(pt_data.get('sello_testigo1') or (firma_data and firma_data.get('sello_testigo1')) or 'BIO-HES:OK')[:22]
        t1_stamp_html = f"""
        <font size='5.2' color='#006633'><b>[✔ TESTIGO 1 - HUELLA BIOMÉTRICA]</b></font><br/>
        <font size='4.2' color='#444'><b>Validación Dactilar:</b> <font face='Courier'>{sello_t1_val}</font></font>
        """
        test1_sig_p = Paragraph(t1_stamp_html, style_sig_stamp)

    test2_sig_p = Paragraph("&nbsp;", style_sig_blank)
    if pt_data.get('firma_testigo2_biometrica') or pt_data.get('sello_testigo2') or (firma_data and firma_data.get('sello_testigo2')):
        sello_t2_val = str(pt_data.get('sello_testigo2') or (firma_data and firma_data.get('sello_testigo2')) or 'BIO-HES:OK')[:22]
        t2_stamp_html = f"""
        <font size='5.2' color='#006633'><b>[✔ TESTIGO 2 - HUELLA BIOMÉTRICA]</b></font><br/>
        <font size='4.2' color='#444'><b>Validación Dactilar:</b> <font face='Courier'>{sello_t2_val}</font></font>
        """
        test2_sig_p = Paragraph(t2_stamp_html, style_sig_stamp)

    # BLOQUE DE FIRMAS CON GRID 2X2 Y SEPARACIÓN BALANCEADA
    gap_col_w = 30.0
    sig_col_w = (content_w - gap_col_w) / 2.0  # ~253.88 pt

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
        ('TOPPADDING', (0,0), (-1,0), 3.0),
        ('BOTTOMPADDING', (0,0), (-1,0), 2.0),
        ('TOPPADDING', (0,1), (-1,1), 3.0),
        ('BOTTOMPADDING', (0,1), (-1,1), 34.0),
        ('TOPPADDING', (0,2), (-1,2), 3.0),
        ('BOTTOMPADDING', (0,2), (-1,2), 2.0),
        ('TOPPADDING', (0,3), (-1,3), 3.0),
        ('BOTTOMPADDING', (0,3), (-1,3), 6.0),
    ]
    t_sigs = Table(sig_grid, colWidths=[sig_col_w, gap_col_w, sig_col_w])
    t_sigs.setStyle(TableStyle(t_style))
    story.append(t_sigs)

    # El bloque de verificación pertenece a esta hoja; reservar sólo una
    # separación breve evita que el contenido final se desborde a una segunda.
    story.append(Spacer(1, 10.0))

    # 6. VERIFICACIÓN PREVIA (HASTA ABAJO, LIMPIO, SIN CUADROS NI BORDES PESADOS)
    verif_left = Paragraph(
        "<b>VERIFICACIÓN PREVIA (SEGURIDAD TRANSFUSIONAL):</b><br/>"
        "<font size='6.4' color='#334155'>El personal médico y/o técnico confirman verbalmente antes de transfundir:<br/>"
        "• La identidad del paciente &nbsp;&nbsp;|&nbsp;&nbsp; • El procedimiento a realizar &nbsp;&nbsp;|&nbsp;&nbsp; • Hemocomponente, grupo y Rh</font>",
        style_verif_body
    )
    special_roles = list(
        (pt_data.get('firmas_especiales_requeridas')
         or (firma_data and firma_data.get('firmas_especiales_requeridas'))
         or [])
    )
    special_signatures = (
        pt_data.get('firmas_especiales')
        or (firma_data and firma_data.get('firmas_especiales'))
        or {}
    )
    special_entries = [special_signatures.get(str(role).upper(), {}) for role in special_roles]
    if special_roles:
        verifier_role = ' / '.join(str(entry.get('etiqueta') or str(role).replace('_', ' ').title()).upper()
                                   for role, entry in zip(special_roles, special_entries))
        verifier_name = '<br/>'.join(
            f"<b>{escape(str(entry.get('etiqueta') or str(role).replace('_', ' ').title()))}:</b> "
            f"{escape(str(entry.get('firmante') or 'Pendiente'))}"
            for role, entry in zip(special_roles, special_entries)
        )
        verifier_user = ' · '.join(escape(str(entry.get('username') or '')) for entry in special_entries if entry.get('username'))
        verifier_date = ' · '.join(escape(str(entry.get('fecha') or '')) for entry in special_entries if entry.get('firmado') and entry.get('fecha'))
        verifier_biometric = bool(special_entries) and all(bool(entry.get('firmado')) for entry in special_entries)
        verifier_pending = not verifier_biometric
    else:
        verifier_role = verifico_nombre or 'PERSONAL DE SALUD / BANCO DE SANGRE'
        verifier_biometric = bool(
            pt_data.get('verifico_firma_biometrica')
            or (firma_data and firma_data.get('verifico_firma_biometrica'))
        )
        verifier_name = escape(str(
            pt_data.get('nombre_personal_banco_sangre')
            or (firma_data and firma_data.get('nombre_personal_banco_sangre'))
            or ''
        ))
        verifier_user = escape(str(
            pt_data.get('usuario_personal_banco_sangre')
            or (firma_data and firma_data.get('usuario_personal_banco_sangre'))
            or ''
        ))
        verifier_date = escape(str(
            pt_data.get('fecha_firma_banco_sangre')
            or (firma_data and firma_data.get('fecha_firma_banco_sangre'))
            or ''
        ))
        verifier_pending = False
    if verifier_biometric:
        verification_mark = Paragraph(
            "<font size='5.2' color='#006633'><b>HUELLA BIOMÉTRICA VERIFICADA</b></font><br/>"
            f"<font size='4.2' color='#475569'>Evidencia de autenticación · no FEA · {verifier_date or 'fecha no disponible'}</font>",
            style_verif_caption,
        )
        verifier_name_line = Paragraph(f"{verifier_name or 'PERSONAL DE SALUD'}", style_verif_field)
        verifier_user_line = Paragraph(f"<b>Usuario:</b> {verifier_user or '—'}", style_verif_field)
    elif verifier_pending:
        verification_mark = Paragraph(
            "<font size='5.0' color='#9a3412'><b>FIRMA BIOMÉTRICA PENDIENTE</b></font><br/>"
            "<font size='4.2' color='#475569'>Se solicitará al firmar el documento · no FEA</font>",
            style_verif_caption,
        )
        verifier_name_line = Paragraph(f"{verifier_name}", style_verif_field)
        verifier_user_line = Paragraph(f"{verifier_user or 'Matrícula: __________________'}", style_verif_field)
    else:
        verification_mark = Table(
            [[Spacer(1, 13.0)], [Paragraph('FIRMA AUTÓGRAFA', style_verif_caption)]],
            colWidths=[content_w * 0.35],
        )
        verification_mark.setStyle(TableStyle([
            ('LINEABOVE', (0, 0), (0, 0), 0.8, PRIMARY_BLUE),
            ('LEFTPADDING', (0, 0), (-1, -1), 5.0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5.0),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))
        verifier_name_line = Paragraph('Nombre: __________________________', style_verif_field)
        verifier_user_line = Paragraph('Matrícula: ________________________', style_verif_field)
    verif_right = Table(
        [
            [Paragraph("<font size='6.4' color='#005FA8'><b>VERIFICÓ</b></font>", style_verif_sig)],
            [Paragraph(f"<font size='6.8'><b>{escape(verifier_role)}</b></font>", style_verif_sig)],
            [verifier_name_line],
            [verification_mark],
            [verifier_user_line],
        ],
        colWidths=[content_w * 0.35],
    )
    verif_right.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1.5),
    ]))

    t_verif = Table([[verif_left, verif_right]], colWidths=[content_w * 0.65, content_w * 0.35])
    t_verif.setStyle(TableStyle([
        ('LINEABOVE', (0, 0), (-1, -1), 0.8, PRIMARY_BLUE),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 6.0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(t_verif)

    def make_canvas(*args, **kwargs):
        return CleanConsentCanvas(*args, doc_info=doc_info, fecha_ingreso=fecha_val, hora_ingreso=hora_val, **kwargs)

    doc.build(story, canvasmaker=make_canvas)
    return output_path


if __name__ == '__main__':
    # Test standalone
    sample_data = {
        'paciente_nombre': 'COMODIN COMODIN COMODIN',
        'expediente': 'PT-5704',
        'fecha_nacimiento': '06 Oct 1994',
        'edad': '31',
        'medico_tratante': 'JOSE JOSE PRUEBA ENRIQUEZ',
        'cedula': 'PRUEBA-99281',
        'acepto_y_autorizo_transfusion_de': 'PAQUETE GLOBULAR + CONCENTRADO PLAQUETARIO',
        'paciente_capaz': True,
        'testigo_1': 'FULANITO DE PRUEBAS',
        'testigo_2': 'PATROCLO PARA PRUEBAS',
        'verifico_nombre': 'PERSONAL DE SALUD / BANCO DE SANGRE',
        'fecha_atencion': '22/09/2026',
        'hora_atencion': '17:17'
    }
    sample_firma = {
        'sello_digital': 'FEA-HES-9876543210ABCDEF12345678',
        'hash_sha256': 'a1b2c3d4e5f67890123456789abcdef0123456789abcdef0123456789abcdef0',
        'fecha_hora_firma': '22/09/2026 17:17:42',
        'nombre_medico': 'JOSE JOSE PRUEBA ENRIQUEZ',
        'cedula': 'PRUEBA-99281',
        'sello_paciente': 'EVIDENCIA_BIOMETRICA',
        'sello_testigo1': 'EVIDENCIA_BIOMETRICA',
        'sello_testigo2': 'EVIDENCIA_BIOMETRICA'
    }
    out = os.path.join(os.path.dirname(__file__), '..', 'scratch', 'TEST_CI_09_HARMONIC.pdf')
    generate_consentimiento_09(sample_data, out, firma_data=sample_firma)
    print(f"Generated test PDF at: {out}")

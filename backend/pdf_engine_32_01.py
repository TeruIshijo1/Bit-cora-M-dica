import os
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
        TEXT_MUTED, TEXT_DARK, RED_ALERT, PRIMARY_BLUE, BORDER_GREY
    )
except ModuleNotFoundError:
    from pdf_engine_v2 import (
        RDLCCanvas, CleanConsentCanvas, FRAME_X, FRAME_Y, FRAME_W, FRAME_H, 
        TEXT_MUTED, TEXT_DARK, RED_ALERT, PRIMARY_BLUE, BORDER_GREY
    )

def generate_consentimiento_32_01(pt_data: dict, output_path: str = None, firma_data: dict = None) -> str:
    if output_path and os.path.dirname(output_path):
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

    content_x = FRAME_X + 16.0
    content_w = FRAME_W - 32.0 - 16.0 # ~521.76 pt

    frame_bottom = FRAME_Y + 41.0
    frame_top_p1 = (FRAME_Y + FRAME_H) - 64.0
    frame_h_p1 = frame_top_p1 - frame_bottom

    frame_top_later = (FRAME_Y + FRAME_H) - 38.0
    frame_h_later = frame_top_later - frame_bottom

    frame_p1 = Frame(content_x, frame_bottom, content_w, frame_h_p1, id='p1_frame',
                     leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)

    frame_later = Frame(content_x, frame_bottom, content_w, frame_h_later, id='later_frame',
                        leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)

    template_p1 = PageTemplate(id='FirstPage', frames=frame_p1)
    template_later = PageTemplate(id='LaterPages', frames=frame_later)

    doc = BaseDocTemplate(
        output_path,
        pagesize=letter,
        pageTemplates=[template_p1, template_later]
    )

    style_label = ParagraphStyle('MetaLabel', fontName='Helvetica-Bold', fontSize=7.0, leading=8.6, textColor=TEXT_MUTED)
    style_val = ParagraphStyle('MetaVal', fontName='Helvetica-Bold', fontSize=7.5, leading=9.0, textColor=TEXT_DARK)
    style_val_red = ParagraphStyle('MetaValRed', fontName='Helvetica-Bold', fontSize=7.5, leading=9.0, textColor=RED_ALERT)
    
    style_title = ParagraphStyle('Title', fontName='Helvetica-Bold', fontSize=11, leading=13, textColor=PRIMARY_BLUE, alignment=TA_LEFT, spaceAfter=8)
    style_body = ParagraphStyle('Body', fontName='Helvetica', fontSize=8.5, leading=11.5, textColor=TEXT_DARK, alignment=TA_JUSTIFY, spaceAfter=6)
    
    story = []

    # Title
    story.append(Paragraph("CONSENTIMIENTO INFORMADO PARA ECOCARDIOGRAMA TRANSESOFÁGICO", style_title))
    
    # ─────────────────────────────────────────────────────────────
    # FICHA DEMOGRÁFICA DEL PACIENTE
    # ─────────────────────────────────────────────────────────────
    sexo = str(pt_data.get('sexo', '')).upper()
    sex_str = "<b>M</b> [X] &nbsp; <b>F</b> [ ]" if ('M' in sexo and 'F' not in sexo) else ("<b>M</b> [ ] &nbsp; <b>F</b> [X]" if 'F' in sexo else "<b>M</b> [ ] &nbsp; <b>F</b> [ ]")

    interrogatorio = str(pt_data.get('tipo_interrogatorio', '')).upper()
    int_dir = "[X]" if 'DIRECTO' in interrogatorio else "[ ]"
    int_ind = "[X]" if 'INDIRECTO' in interrogatorio else "[ ]"
    
    meta_table_data = [
        # Row 1: Nombre + Fecha Nac + Cama
        [
            Paragraph('Nombre del Paciente:', style_label),
            Paragraph(f"<b>{pt_data.get('nombre', '').upper()}</b>", style_val),
            Paragraph('Fecha de Nac.:', style_label),
            Paragraph(f"<u>{pt_data.get('dob', '')}</u>", style_val),
            Paragraph('Cama:', style_label),
            Paragraph(f"<b>{pt_data.get('cama', '')}</b>", style_val)
        ],
        # Row 2: Expediente + Edad + Sexo + Grupo RH
        [
            Paragraph('Expediente:', style_label),
            Paragraph(f"<b>{pt_data.get('mrn', '')}</b> &nbsp;&nbsp; <font color='#555'>Edad:</font> <b>{pt_data.get('edad', '')}</b>", style_val),
            Paragraph('Sexo:', style_label),
            Paragraph(sex_str, style_val),
            Paragraph('Grupo/RH:', style_label),
            Paragraph(f"<b>{pt_data.get('grupo_rh', 'O+')}</b>", style_val)
        ],
        # Row 3: Alergias + Diagnóstico
        [
            Paragraph('Alergias:', style_label),
            Paragraph(f"<font color='#d93025'><b>{pt_data.get('alergias', 'NEGADAS').upper()}</b></font>", style_val_red),
            Paragraph('Diagnóstico:', style_label),
            Paragraph(f"<b>{pt_data.get('diagnostico', '').upper()}</b>", style_val),
            '', ''
        ],
        # Row 4: Tipo Interrogatorio + Médico
        [
            Paragraph('Tipo de interrogatorio:', style_label),
            Paragraph(f"Directo {int_dir} &nbsp;&nbsp; Indirecto {int_ind}", style_val),
            Paragraph('Médico:', style_label),
            Paragraph(f"<b>{pt_data.get('medico_tratante', '').upper()}</b>", style_val),
            Paragraph('Cédula:', style_label),
            Paragraph(f"<b>{pt_data.get('cedula', '')}</b>", style_val)
        ]
    ]

    t_meta = Table(meta_table_data, colWidths=[78, 180, 58, 105, 42, content_w - (78 + 180 + 58 + 105 + 42)])
    t_meta.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 0.8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0.8),
        ('LEFTPADDING', (0,0), (-1,-1), 1),
        ('RIGHTPADDING', (0,0), (-1,-1), 1),
        ('SPAN', (3,2), (5,2)),  # Diagnóstico spans remaining cols
        ('LINEBELOW', (0,0), (-1,0), 0.3, BORDER_GREY),
        ('LINEBELOW', (0,1), (-1,1), 0.3, BORDER_GREY),
        ('LINEBELOW', (0,2), (-1,2), 0.3, BORDER_GREY),
        ('LINEBELOW', (0,3), (-1,3), 0.6, PRIMARY_BLUE),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 10))

    # Consentimiento body
    fecha_doc = pt_data.get('fecha_documento', '___/___/_____')
    story.append(Paragraph(f"<b>Fecha:</b> {fecha_doc}", ParagraphStyle('RightAligned', parent=style_body, alignment=TA_RIGHT)))
    
    paciente_nom = pt_data.get('paciente_o_representante', '') or pt_data.get('nombre', '')
    rep_nom = pt_data.get('representante_legal', '')
    med_nom = pt_data.get('medico_autorizado', '') or pt_data.get('medico_tratante', '')
    
    if rep_nom:
        txt1 = f"Yo <u><b>{paciente_nom}</b></u> como Paciente y <u><b>{rep_nom}</b></u> en mi calidad de Representante Legal del Paciente, acepto voluntariamente y autorizo al Dr. <u><b>{med_nom}</b></u><br/><br/>Para que practique en la persona del denominado paciente el Ecocardiograma transesofágico. Es un estudio que se realiza con el apoyo de un anestesiólogo cardiovascular que da la sedación para la introducción de una sonda a través de la boca y que se avanza al esófago. Por medio de este procedimiento se puede estudiar la anatomía del corazón y la función de manera más detallada."
    else:
        txt1 = f"Yo <u><b>{paciente_nom}</b></u> en mi calidad de Paciente, acepto voluntariamente y autorizo al Dr. <u><b>{med_nom}</b></u><br/><br/>Para que practique en la persona del denominado paciente el Ecocardiograma transesofágico. Es un estudio que se realiza con el apoyo de un anestesiólogo cardiovascular que da la sedación para la introducción de una sonda a través de la boca y que se avanza al esófago. Por medio de este procedimiento se puede estudiar la anatomía del corazón y la función de manera más detallada."
    story.append(Paragraph(txt1, style_body))

    txt2 = "Las complicaciones del procedimiento pueden aparecer en 1 de cada 10000 estudios. Las más frecuentes son hemorragias en cavidad oral, esófago y estomago que se presentan en 1 de cada 5000 estudios, perforación que se presenta en 1 de cada 10000 pacientes. Se pueden presentar reacciones adversas como insuficiencia respiratoria, dolor de cabeza, mareo, fatiga o náusea. El estudio se realiza bajo monitorización y con los medicamentos necesarios para tratamiento en caso de presentar complicaciones."
    story.append(Paragraph(txt2, style_body))

    txt3 = "Acepto y autorizo el procedimiento. Mis dudas fueron aclaradas proporcionándome el tiempo suficiente para ello. Se me explicó que existen otros procedimientos alternativos. Sin embargo, me he decidido por este procedimiento, por lo que estoy autorizando. Así también que se me ha explicado y he entendido el tipo y contenido del presente documento. En este acto autorizo al personal de salud del Hospital Escandón para que realice las atenciones en caso de contingencia y urgencias derivadas del procedimiento que se me va a realizar."
    story.append(Paragraph(txt3, style_body))

    txt4 = "Estoy enterado y acepto que requeriré vigilancia y control después del procedimiento, hasta mi total recuperación."
    story.append(Paragraph(txt4, style_body))

    txt5 = "Declaro que autorizo el presente documento:"
    story.append(Paragraph(txt5, style_body))
    story.append(Spacer(1, 8))

    sig_label = ParagraphStyle('SigLabel', fontName='Helvetica-Oblique', fontSize=7.0, leading=8.5, textColor=TEXT_MUTED, alignment=TA_CENTER)
    sig_name = ParagraphStyle('SigName', fontName='Helvetica-Bold', fontSize=8.0, leading=9.5, alignment=TA_CENTER)
    
    t1_name = pt_data.get('testigo1', '')
    t2_name = pt_data.get('testigo2', '')
    
    sig_col_w = (content_w - 50) / 2  # Two columns with a clean gap
    
    has_tutor = bool(rep_nom) or (not pt_data.get('paciente_capaz', True))

    # --- Row 1: Paciente / Representante Legal ---
    sig_row1 = [
        [
            Paragraph("&nbsp;", ParagraphStyle('Sp1', fontSize=18, leading=18)),
            '',
            Paragraph("&nbsp;", ParagraphStyle('Sp1', fontSize=18, leading=18)),
        ],
        [
            Paragraph(f"<b>{paciente_nom}</b>", sig_name) if paciente_nom else Paragraph("&nbsp;", ParagraphStyle('SpBlank', fontSize=8, leading=9)),
            '',
            Paragraph(f"<b>{rep_nom}</b>", sig_name) if has_tutor else Paragraph("&nbsp;", ParagraphStyle('SpBlank', fontSize=8, leading=9)),
        ],
        [
            Paragraph("Nombre y firma del paciente", sig_label),
            '',
            Paragraph("Nombre y firma del representante legal del paciente" if has_tutor else "&nbsp;", sig_label),
        ]
    ]
    t_r1_styles = [
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LINEABOVE', (0,1), (0,1), 0.8, PRIMARY_BLUE),
        ('BOTTOMPADDING', (0,0), (-1,0), 1),
        ('TOPPADDING', (0,1), (-1,1), 3),
        ('BOTTOMPADDING', (0,1), (-1,1), 1),
        ('TOPPADDING', (0,2), (-1,2), 1),
        ('BOTTOMPADDING', (0,2), (-1,2), 1),
    ]
    if has_tutor:
        t_r1_styles.append(('LINEABOVE', (2,1), (2,1), 0.8, PRIMARY_BLUE))

    t_r1 = Table(sig_row1, colWidths=[sig_col_w, 50, sig_col_w])
    t_r1.setStyle(TableStyle(t_r1_styles))
    story.append(t_r1)
    story.append(Spacer(1, 6))
    
    # --- Row 2: Testigos ---
    sig_row2 = [
        [
            Paragraph("&nbsp;", ParagraphStyle('Sp2', fontSize=18, leading=18)),
            '',
            Paragraph("&nbsp;", ParagraphStyle('Sp2', fontSize=18, leading=18)),
        ],
        [
            Paragraph(f"<b>{t1_name}</b>", sig_name) if t1_name else Paragraph("&nbsp;", ParagraphStyle('SpBlank', fontSize=8, leading=9)),
            '',
            Paragraph(f"<b>{t2_name}</b>", sig_name) if t2_name else Paragraph("&nbsp;", ParagraphStyle('SpBlank', fontSize=8, leading=9)),
        ],
        [
            Paragraph("Nombre y firma de testigo", sig_label),
            '',
            Paragraph("Nombre y firma de testigo", sig_label),
        ]
    ]
    t_r2 = Table(sig_row2, colWidths=[sig_col_w, 50, sig_col_w])
    t_r2.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LINEABOVE', (0,1), (0,1), 0.8, PRIMARY_BLUE),
        ('LINEABOVE', (2,1), (2,1), 0.8, PRIMARY_BLUE),
        ('BOTTOMPADDING', (0,0), (-1,0), 1),
        ('TOPPADDING', (0,1), (-1,1), 3),
        ('BOTTOMPADDING', (0,1), (-1,1), 1),
        ('TOPPADDING', (0,2), (-1,2), 1),
        ('BOTTOMPADDING', (0,2), (-1,2), 1),
    ]))
    story.append(t_r2)
    
    story.append(Spacer(1, 8))
    
    decl_txt = "DECLARO BAJO PROTESTA DE DECIR VERDAD, QUE HE PROPORCIONADO TODA LA INFORMACIÓN SOBRE<br/>EL PROCEDIMIENTO A REALIZAR EN EL PACIENTE."
    story.append(Paragraph(decl_txt, ParagraphStyle('Decl', fontName='Helvetica-BoldOblique', fontSize=7.5, leading=9.5, alignment=TA_CENTER)))
    story.append(Spacer(1, 6))
    
    # --- Doctor signature block (centered, clean line) ---
    firma_data = pt_data.get('firma_data', {})
    med_col_w = content_w * 0.60
    
    if firma_data and (firma_data.get('sello_digital') or firma_data.get('hash_sha256')):
        sello_raw = str(firma_data.get('sello_digital') or firma_data.get('hash_sha256') or '')
        sello_resumido = (sello_raw[:28] + '...') if len(sello_raw) > 28 else sello_raw
        fecha_txt = firma_data.get('fecha_hora_firma') or firma_data.get('fecha_hora') or ''
        stamp_html = f"""
        <font size='5.8' color='#006633'><b>[✓ FIRMADO BIOMÉTRICAMENTE CON HUELLA]</b></font><br/>
        <font size='5' color='#004d26'><b>NOM-004-SSA3-2012 / NOM-024-SSA3-2012</b></font><br/>
        <font size='4.6' color='#444'><b>Sello:</b> <font face='Courier' size='4.4'>{sello_resumido}</font> | {fecha_txt}</font>
        """
        top_sig_p = Paragraph(stamp_html, ParagraphStyle('SigStamp', fontName='Helvetica', fontSize=5.2, leading=6.5, alignment=TA_CENTER))
    else:
        top_sig_p = Paragraph("&nbsp;", ParagraphStyle('SigBlank', fontName='Helvetica', fontSize=18, leading=18))
        
    medico_sig_data = [
        [ top_sig_p ],
        [ Paragraph(f"<b>{pt_data.get('medico_autorizado', '')}</b><br/><font size='7' color='#444'>Céd. Prof. {pt_data.get('cedula', '')}</font>", ParagraphStyle('SigM', fontName='Helvetica', fontSize=8.0, leading=9.5, alignment=TA_CENTER)) ],
        [ Paragraph("<i>Nombre, firma y Cédula Profesional del Médico</i>", sig_label) ]
    ]
    t_med_sig = Table(medico_sig_data, colWidths=[med_col_w])
    t_med_sig.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LINEABOVE', (0,1), (0,1), 0.8, PRIMARY_BLUE),
        ('BOTTOMPADDING', (0,0), (-1,0), 1),
        ('TOPPADDING', (0,1), (-1,1), 3),
        ('BOTTOMPADDING', (0,1), (-1,1), 1),
        ('TOPPADDING', (0,2), (-1,2), 1),
        ('BOTTOMPADDING', (0,2), (-1,2), 1),
    ]))
    
    wrapper = Table([[t_med_sig]], colWidths=[content_w])
    wrapper.setStyle(TableStyle([
        ('ALIGN', (0,0), (0,0), 'CENTER'),
        ('VALIGN', (0,0), (0,0), 'MIDDLE'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(KeepTogether([wrapper]))
    
    doc_info = {
        'title': 'CONSENTIMIENTO INFORMADO PARA ECOCARDIOGRAMA TRANSESOFÁGICO',
        'title_lines': [
            'CONSENTIMIENTO INFORMADO PARA',
            'ECOCARDIOGRAMA TRANSESOFÁGICO'
        ],
        'code': 'HE-DIRMED-SINPRO-PLT-32/01',
    }

    def make_canvas(*args, **kwargs):
        c = CleanConsentCanvas(*args, doc_info=doc_info, **kwargs)
        c.fecha_ingreso = pt_data.get('fecha_ingreso', '')
        c.hora_ingreso = pt_data.get('hora_ingreso', '')
        return c

    doc.build(story, canvasmaker=make_canvas)
    return output_path

if __name__ == "__main__":
    pt_test = {
        'nombre': 'JUAN PEREZ MARTINEZ',
        'dob': '01/01/1980',
        'mrn': 'PT-01234',
        'edad': '45 años',
        'sexo': 'M',
        'grupo_rh': 'O+',
        'alergias': 'PENICILINA',
        'tipo_interrogatorio': 'Directo',
        'medico_tratante': 'DR. CARLOS SLIM',
        'fecha_documento': '25/08/2026',
        'paciente_o_representante': 'JUAN PEREZ MARTINEZ',
        'medico_autorizado': 'DR. ROBERTO GOMEZ BOLAÑOS',
        'fecha_ingreso': '24/08/2026',
        'hora_ingreso': '10:00'
    }
    generate_consentimiento_32_01(pt_test, 'test_32_01.pdf')
    print("PDF Generated successfully")

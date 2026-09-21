import os
import re
from reportlab.lib.pagesizes import letter
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, TableStyle, KeepTogether, PageBreak, NextPageTemplate
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

BLUE_BAR_COLOR = colors.HexColor('#005691')
MIDNIGHT_BLUE = colors.HexColor('#191970')

def generar_pdf_eed(pt_data: dict, force_output_path=None, firma_data: dict = None) -> str:
    pdf_dir = os.path.join(os.path.dirname(__file__), 'static', 'pdfs')
    os.makedirs(pdf_dir, exist_ok=True)
    output_path = force_output_path or os.path.join(pdf_dir, f"CI_EED_{pt_data.get('expediente', 'UNK')}.pdf")
    if firma_data:
        pt_data['firma_data'] = firma_data

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

    style_label = ParagraphStyle('MetaLabel', fontName='Helvetica-Bold', fontSize=7.4, leading=9.0, textColor=TEXT_MUTED)
    style_val = ParagraphStyle('MetaVal', fontName='Helvetica-Bold', fontSize=7.8, leading=9.5, textColor=TEXT_DARK)
    style_val_red = ParagraphStyle('MetaValRed', fontName='Helvetica-Bold', fontSize=7.8, leading=9.5, textColor=RED_ALERT)
    
    style_title = ParagraphStyle('Title', fontName='Helvetica-Bold', fontSize=10.5, leading=12.5, textColor=PRIMARY_BLUE, alignment=TA_CENTER, spaceAfter=8)
    style_subtitle = ParagraphStyle('SubTitle', fontName='Helvetica-Bold', fontSize=8.8, leading=11.0, textColor=MIDNIGHT_BLUE, alignment=TA_CENTER, spaceAfter=6)
    style_body = ParagraphStyle('Body', fontName='Helvetica', fontSize=8.0, leading=11.2, textColor=TEXT_DARK, alignment=TA_JUSTIFY, spaceAfter=8)
    
    story = []

    # ==================== PÁGINA 1: CONSENTIMIENTO ====================
    story.append(Paragraph("CONSENTIMIENTO INFORMADO PARA ECOCARDIOGRAMA DE ESTRÉS CON DOBUTAMINA", style_title))
    
    # Tabla Datos Generales
    pt_info_data = [
        [
            Paragraph("NOMBRE DEL PACIENTE:", style_label), Paragraph(f"<b>{pt_data.get('nombre', '')}</b>", style_val),
            Paragraph("EXPEDIENTE:", style_label), Paragraph(f"<b>{pt_data.get('expediente', '')}</b>", style_val)
        ],
        [
            Paragraph("FECHA:", style_label), Paragraph(pt_data.get("fecha", ""), style_val),
            Paragraph("ALERGIAS:", style_label), Paragraph(pt_data.get("alergias", "NEGADAS"), style_val_red)
        ]
    ]
    t_info = Table(pt_info_data, colWidths=[110, 180, 70, content_w - (110 + 180 + 70)])
    t_info.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
        ('BACKGROUND', (0,0), (0,-1), colors.whitesmoke),
        ('BACKGROUND', (2,0), (2,-1), colors.whitesmoke),
        ('PADDING', (0,0), (-1,-1), 3.5)
    ]))
    story.append(t_info)
    story.append(Spacer(1, 8))

    story.append(Paragraph("DECLARACIÓN DE CONSENTIMIENTO", style_subtitle))
    
    c_text = f"Por medio del presente documento, yo <b>{pt_data.get('responsable', pt_data.get('nombre', ''))}</b>, autorizo al <b>Dr. {pt_data.get('firma_data', {}).get('nombre_medico') or pt_data.get('medico', '')}</b> y al equipo médico del Hospital Escandón para que se me realice el procedimiento denominado <b>ECOCARDIOGRAMA DE ESTRÉS CON DOBUTAMINA</b>."
    story.append(Paragraph(c_text, style_body))
    
    c_text2 = "Se me ha explicado de manera clara, sencilla y comprensible en qué consiste el procedimiento, que su objetivo es evaluar la función del corazón bajo estrés farmacológico, y se me han explicado los riesgos y posibles complicaciones, que incluyen pero no se limitan a: arritmias, variaciones en la presión arterial, dolor torácico, mareo, náusea, y en casos muy raros, infarto agudo al miocardio o paro cardíaco. Comprendo que este procedimiento es necesario para mi diagnóstico o tratamiento."
    story.append(Paragraph(c_text2, style_body))
    
    c_text3 = "Autorizo que se me administren los medicamentos necesarios (como Dobutamina, Atropina, etc.) para la realización del estudio y acepto que he informado de todas mis alergias, padecimientos y medicamentos que consumo actualmente."
    story.append(Paragraph(c_text3, style_body))
    
    c_text4 = "Tengo la libertad de retirar mi consentimiento en cualquier momento antes de la realización del procedimiento, sin que esto afecte mi derecho a recibir atención médica posterior."
    story.append(Paragraph(c_text4, style_body))
    
    story.append(Spacer(1, 10))
    
    # Firmas
    sig_name = ParagraphStyle('SigName', fontName='Helvetica-Bold', fontSize=7.8, leading=9.5, alignment=TA_CENTER)
    sig_space_p = Paragraph("&nbsp;", ParagraphStyle('SigSpace', fontName='Helvetica', fontSize=8.0, leading=12.0, textColor=colors.transparent, alignment=TA_CENTER))
    
    # Sello biométrico paciente si existe
    firma_data = pt_data.get('firma_data', {})
    if pt_data.get('firma_paciente_biometrica') or pt_data.get('sello_paciente') or (firma_data and firma_data.get('sello_paciente')):
        sello_pac_val = str(pt_data.get('sello_paciente') or (firma_data and firma_data.get('sello_paciente')) or 'BIO-HES:OK')[:24]
        pac_stamp_html = f"""
        <font size='5.2' color='#006633'><b>[✔ AUTORIZADO CON HUELLA BIOMÉTRICA]</b></font><br/>
        <font size='4.2' color='#444'><b>Validación Dactilar:</b> <font face='Courier' size='3.8'>{sello_pac_val}</font></font>
        """
        pac_sig_p = Paragraph(pac_stamp_html, ParagraphStyle('SigStampP', fontName='Helvetica', fontSize=5.0, leading=6.5, alignment=TA_CENTER))
    else:
        pac_sig_p = sig_space_p

    sig_col_w = (content_w - 40) / 2
    raw_capaz = pt_data.get('paciente_capaz', True)
    if isinstance(raw_capaz, str):
        paciente_capaz = raw_capaz.lower() in ('true', '1', 'si', 'yes')
    elif isinstance(raw_capaz, (int, float)):
        paciente_capaz = bool(raw_capaz)
    else:
        paciente_capaz = bool(raw_capaz)

    responsable_nom = (pt_data.get('responsable') or pt_data.get('pariente') or pt_data.get('representante_legal') or pt_data.get('declarante') or '').strip()
    has_tutor = bool(responsable_nom) or (not paciente_capaz)

    parentesco_tutor = (pt_data.get('parentesco') or pt_data.get('parentesco_declarante') or pt_data.get('parentesco_paciente') or 'Tutor / Representante Legal').strip()
    if parentesco_tutor.upper() in ('PACIENTE', 'TITULAR', 'DIRECTO'):
        parentesco_tutor = 'Tutor / Representante Legal'

    paciente_clean = re.sub(r'\s*\([^)]*\)', '', str(pt_data.get('nombre', '') or '')).strip()
    resp_clean = re.sub(r'\s*\([^)]*\)', '', str(responsable_nom or ('Tutor / Representante Legal' if not paciente_capaz else ''))).strip()

    paciente_txt = f"<b>{paciente_clean}</b><br/><font size='6.2' color='#334155'><i><b>Parentesco: Paciente</b></i></font>" if paciente_clean else "<b>Nombre completo del paciente</b>"
    resp_txt = f"<b>{resp_clean}</b><br/><font size='6.2' color='#334155'><i><b>Parentesco: {parentesco_tutor}</b></i></font>" if resp_clean else "<b>Nombre completo del familiar o tutor</b>"

    sig_row1 = [
        [
            (pac_sig_p if paciente_capaz else sig_space_p), '',
            (pac_sig_p if has_tutor else sig_space_p),
        ],
        [
            Paragraph(paciente_txt, sig_name), '',
            Paragraph(resp_txt, sig_name),
        ]
    ]
    t_r1 = Table(sig_row1, colWidths=[sig_col_w, 40, sig_col_w])
    t_r1.setStyle(TableStyle([
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
    story.append(t_r1)
    story.append(Spacer(1, 10))
    
    # Firma Médico
    firma_data = pt_data.get('firma_data', {})
    med_col_w = content_w * 0.60
    
    if firma_data and (firma_data.get('sello_digital') or firma_data.get('hash_sha256')):
        sello_raw = str(firma_data.get('sello_digital') or firma_data.get('hash_sha256') or '')
        sello_resumido = (sello_raw[:28] + '...') if len(sello_raw) > 28 else sello_raw
        fecha_txt = firma_data.get('fecha_hora_firma') or pt_data.get('fecha_hora') or ''
        stamp_html = f"<font size='5.8' color='#006633'><b>[✔ FIRMADO BIOMÉTRICAMENTE CON HUELLA]</b></font><br/><font size='5' color='#004d26'><b>NOM-004-SSA3-2012 / NOM-024-SSA3-2012</b></font><br/><font size='4.6' color='#444'><b>Sello:</b> <font face='Courier' size='4.4'>{sello_resumido}</font> | {fecha_txt}</font>"
        top_sig_p = Paragraph(stamp_html, ParagraphStyle('SigStamp', fontName='Helvetica', fontSize=5.2, leading=6.5, alignment=TA_CENTER))
    else:
        top_sig_p = sig_space_p
        
    doc_nom = pt_data.get('firma_data', {}).get('nombre_medico') or pt_data.get('medico', '') or 'Médico Autorizado'
    doc_ced = pt_data.get('firma_data', {}).get('cedula') or pt_data.get('cedula', '')
    doctor_sig_text_eed = f"<b>{doc_nom}</b><br/><font size='6.2' color='#334155'><i><b>CÉD. PROF. {doc_ced}</b></i></font>" if doc_ced else f"<b>{doc_nom}</b>"

    medico_sig_data = [
        [ top_sig_p ],
        [ Paragraph(doctor_sig_text_eed, ParagraphStyle('SigM', fontName='Helvetica', fontSize=7.8, leading=9.5, alignment=TA_CENTER)) ]
    ]
    t_med_sig = Table(medico_sig_data, colWidths=[med_col_w])
    t_med_sig.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (0,0), 'BOTTOM'),
        ('VALIGN', (0,1), (0,1), 'TOP'),
        ('LINEABOVE', (0,1), (0,1), 0.8, PRIMARY_BLUE),
        ('TOPPADDING', (0,0), (-1,0), 0),
        ('BOTTOMPADDING', (0,0), (-1,0), 0.5),
        ('TOPPADDING', (0,1), (-1,1), 2.5),
        ('BOTTOMPADDING', (0,1), (-1,1), 0),
    ]))
    
    wrapper = Table([[t_med_sig]], colWidths=[content_w])
    wrapper.setStyle(TableStyle([
        ('ALIGN', (0,0), (0,0), 'CENTER'),
        ('VALIGN', (0,0), (0,0), 'MIDDLE'),
    ]))
    story.append(KeepTogether([wrapper]))

    # ==================== PÁGINA 2: REPORTE ESTRÉS ====================
    story.append(NextPageTemplate('LaterPages'))
    story.append(PageBreak())

    story.append(Paragraph("REPORTE DE MONITOREO HEMODINÁMICO", style_title))
    story.append(Spacer(1, 6))

    tbl_lbl_style = ParagraphStyle('TblLbl', fontName='Helvetica-Bold', fontSize=7.5, leading=9.5, textColor=MIDNIGHT_BLUE)
    tbl_val_style = ParagraphStyle('TblVal', fontName='Helvetica', fontSize=7.5, leading=9.5)
    tbl_hdr_style = ParagraphStyle('TblHdr', fontName='Helvetica-Bold', fontSize=7.5, leading=9.5, textColor=colors.white, alignment=TA_CENTER)
    tbl_cell_center = ParagraphStyle('TblCellC', fontName='Helvetica', fontSize=7.5, leading=9.5, alignment=TA_CENTER)
    tbl_cell_left = ParagraphStyle('TblCellL', fontName='Helvetica', fontSize=7.5, leading=9.5, alignment=TA_LEFT)

    vitals_data = [
        [Paragraph("TA", tbl_lbl_style), Paragraph(pt_data.get("ta", ""), tbl_val_style), Paragraph("FR", tbl_lbl_style), Paragraph(pt_data.get("fr", ""), tbl_val_style)],
        [Paragraph("FC META", tbl_lbl_style), Paragraph(pt_data.get("fc_meta", ""), tbl_val_style), Paragraph("PESO/TALLA", tbl_lbl_style), Paragraph(f"{pt_data.get('peso', '')} kg / {pt_data.get('talla', '')} m", tbl_val_style)]
    ]
    t_vitals = Table(vitals_data, colWidths=[70, 190, 70, content_w - (70 + 190 + 70)])
    t_vitals.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
        ('BACKGROUND', (0,0), (0,-1), colors.whitesmoke),
        ('BACKGROUND', (2,0), (2,-1), colors.whitesmoke),
        ('PADDING', (0,0), (-1,-1), 3.5)
    ]))
    story.append(t_vitals)
    story.append(Spacer(1, 8))

    col_w_st = 80
    col_w_ta = 70
    col_w_fc = 70
    col_w_so = 70
    col_w_sx = content_w - (col_w_st + col_w_ta + col_w_fc + col_w_so)

    grid_header = [Paragraph("ETAPA", tbl_hdr_style), Paragraph("TA", tbl_hdr_style), Paragraph("FC", tbl_hdr_style), Paragraph("SO2 %", tbl_hdr_style), Paragraph("SÍNTOMAS", tbl_hdr_style)]
    grid_data = [grid_header]
    stages = [
        ("BASAL", "basal"), ("5 mcg", "5mcg"), ("10 mcg", "10mcg"), 
        ("20 mcg", "20mcg"), ("30 mcg", "30mcg"), ("40 mcg", "40mcg"), 
        ("ATROPINA", "atropina")
    ]
    for lbl, suf in stages:
        grid_data.append([
            Paragraph(lbl, tbl_cell_center),
            Paragraph(pt_data.get(f"ta_{suf}", ""), tbl_cell_center),
            Paragraph(pt_data.get(f"fc_{suf}", ""), tbl_cell_center),
            Paragraph(pt_data.get(f"so2_{suf}", ""), tbl_cell_center),
            Paragraph(pt_data.get(f"s_{suf}", ""), tbl_cell_left)
        ])
    
    t_grid = Table(grid_data, colWidths=[col_w_st, col_w_ta, col_w_fc, col_w_so, col_w_sx])
    t_grid.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('BACKGROUND', (0,0), (-1,0), BLUE_BAR_COLOR),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('PADDING', (0,0), (-1,-1), 3.5),
    ]))
    story.append(t_grid)
    story.append(Spacer(1, 8))

    recov_header = [Paragraph("RECUPERACIÓN", tbl_hdr_style), Paragraph("TA", tbl_hdr_style), Paragraph("FC", tbl_hdr_style), Paragraph("SO2 %", tbl_hdr_style), Paragraph("SÍNTOMAS", tbl_hdr_style)]
    recov_data = [recov_header]
    for m in [2, 4]:
        recov_data.append([
            Paragraph(f"{m} MIN", tbl_cell_center),
            Paragraph(pt_data.get(f"ta_{m}min", ""), tbl_cell_center),
            Paragraph(pt_data.get(f"fc_{m}min", ""), tbl_cell_center),
            Paragraph(pt_data.get(f"so2_{m}min", ""), tbl_cell_center),
            Paragraph(pt_data.get(f"sintomas_{m}min", ""), tbl_cell_left)
        ])
    t_recov = Table(recov_data, colWidths=[col_w_st, col_w_ta, col_w_fc, col_w_so, col_w_sx])
    t_recov.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('BACKGROUND', (0,0), (-1,0), PRIMARY_BLUE),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('PADDING', (0,0), (-1,-1), 3.5),
    ]))
    story.append(t_recov)
    story.append(Spacer(1, 10))

    story.append(Paragraph("<b>COMENTARIOS / INCIDENCIAS:</b>", style_subtitle))
    story.append(Spacer(1, 4))
    story.append(Paragraph(pt_data.get("comentarios", "Sin comentarios.") or "Sin comentarios.", style_body))

    expediente_val = pt_data.get('expediente') or pt_data.get('mrn') or pt_data.get('pt_num', '')
    pt_num_val = str(pt_data.get('pt_num', '') or expediente_val or '')

    doc_info = {
        'title': 'CONSENTIMIENTO INFORMADO PARA ECOCARDIOGRAMA DE ESTRÉS CON DOBUTAMINA',
        'title_lines': [
            'CONSENTIMIENTO INFORMADO PARA',
            'ECOCARDIOGRAMA DE ESTRÉS CON DOBUTAMINA'
        ],
        'code': 'HE-DIRMED-SINPRO-PLT-EED',
        'expediente': expediente_val,
        'folio': expediente_val,
        'pt_num': pt_num_val,
        'slot': pt_data.get('slot') or pt_data.get('mrnum') or 1,
        'draw_qr': True
    }

    def make_canvas(*args, **kwargs):
        c = CleanConsentCanvas(*args, doc_info=doc_info, **kwargs)
        c.fecha_ingreso = pt_data.get('fecha_ingreso', '')
        c.hora_ingreso = pt_data.get('hora_ingreso', '')
        return c

    doc.build(story, canvasmaker=make_canvas)
    return output_path

generate_consentimiento_eed = generar_pdf_eed


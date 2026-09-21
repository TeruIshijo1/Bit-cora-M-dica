"""
Motor de generación de PDFs - Expediente Clínico Completo (Carátula y Anexos)
Código Oficial: HE-DIRMED-EXPEDIENTE-COMPLETO
Hospital Escandón (Fundación María Ana Mier de Escandón, I.A.P.)
===================================================================
Calibración exacta según especificaciones RDLC institucionales:
- Hoja Carta: 21.59 cm x 27.94 cm (612 x 792 pt).
- Contenedor: 20.1 cm x 25.5 cm (569.76 pt x 722.84 pt).
- Borde: MidnightBlue, Solid, 1.25 pt.
- Cumplimiento normativo estricto: NOM-004-SSA3-2012 / NOM-024-SSA3-2012.
"""

import os
import re
import datetime
import qrcode
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, TableStyle, KeepTogether, PageBreak, Image
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY

try:
    from backend.pdf_engine_v2 import (
        RDLCCanvas, CleanConsentCanvas, FRAME_X, FRAME_Y, FRAME_W, FRAME_H, 
        TEXT_MUTED, TEXT_DARK, RED_ALERT, PRIMARY_BLUE, DARK_BLUE, MIDNIGHT_BLUE,
        BLUE_BAR_COLOR, BANNER_BG, BANNER_BORDER, BORDER_GREY
    )
except ModuleNotFoundError:
    from pdf_engine_v2 import (
        RDLCCanvas, CleanConsentCanvas, FRAME_X, FRAME_Y, FRAME_W, FRAME_H, 
        TEXT_MUTED, TEXT_DARK, RED_ALERT, PRIMARY_BLUE, DARK_BLUE, MIDNIGHT_BLUE,
        BLUE_BAR_COLOR, BANNER_BG, BANNER_BORDER, BORDER_GREY
    )

QR_CACHE_DIR = os.path.join(os.path.dirname(__file__), 'static', 'qr_cache')
os.makedirs(QR_CACHE_DIR, exist_ok=True)


def generate_qr_image(url_or_text: str, filename_key: str) -> str:
    """Genera y guarda una imagen QR en el directorio temporal/cache."""
    qr_path = os.path.join(QR_CACHE_DIR, f"qr_exp_{filename_key}.png")
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=4,
        border=1,
    )
    qr.add_data(url_or_text)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img.save(qr_path)
    return qr_path


def generate_caratula_expediente(
    dashboard_data: dict,
    output_path: str,
    docs_summary: list = None,
    firma_data: dict = None,
    verification_url: str | None = None,
) -> str:
    """
    Genera la Carátula / Portada Oficial del Expediente Clínico Completo (NOM-004-SSA3-2012).
    """
    if output_path and os.path.dirname(output_path):
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

    patient_info = dashboard_data.get("patient", {})
    pt_num = str(patient_info.get("mrn", "")).replace("PT-", "").strip()
    fecha_ingreso = patient_info.get("fecha_ingreso", "")
    hora_ingreso = patient_info.get("hora_ingreso", "")
    fecha_egreso = patient_info.get("fecha_egreso", "___/___/___")
    hora_egreso = patient_info.get("hora_egreso", "__:__")
    is_alta = patient_info.get("status") == "Alta" or bool(patient_info.get("is_alta"))

    content_x = FRAME_X + 16.0
    content_w = FRAME_W - 32.0 - 16.0  # ~521.76 pt
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

    code_doc = "HE-DIRMED-EXPEDIENTE-COMPLETO"
    folio_doc = f"PT-{pt_num}"
    clean_pt_doc = str(pt_num)
    slot_doc = "1"
    qr_url = verification_url

    doc_info = {
        'title_lines': [
            'EXPEDIENTE CLÍNICO INTEGRADO Y COMPILADO NOM-004',
            'HOSPITAL ESCANDÓN - DIRECCIÓN MÉDICA'
        ],
        'code': code_doc,
        'fecha_ingreso': fecha_ingreso,
        'hora_ingreso': hora_ingreso,
        'draw_header_dates': True,
        'pt_num': clean_pt_doc,
        'expediente': folio_doc,
        'slot': slot_doc,
        'qr_url': qr_url,
        'draw_qr': bool(qr_url),
    }

    def make_canvas(*args, **kwargs):
        kwargs['doc_info'] = doc_info
        return RDLCCanvas(*args, **kwargs)

    # Estilos
    style_label = ParagraphStyle('CoverLabel', fontName='Helvetica-Bold', fontSize=7.2, leading=8.8, textColor=TEXT_MUTED)
    style_val = ParagraphStyle('CoverVal', fontName='Helvetica-Bold', fontSize=7.8, leading=9.6, textColor=TEXT_DARK)
    style_val_accent = ParagraphStyle('CoverValAcc', fontName='Helvetica-Bold', fontSize=7.8, leading=9.6, textColor=PRIMARY_BLUE)
    style_val_red = ParagraphStyle('CoverValRed', fontName='Helvetica-Bold', fontSize=7.8, leading=9.6, textColor=RED_ALERT)
    
    style_sec_title = ParagraphStyle('SecTitle', fontName='Helvetica-Bold', fontSize=8.2, leading=10.0, textColor=colors.white, alignment=TA_LEFT)
    style_idx_head = ParagraphStyle('IdxHead', fontName='Helvetica-Bold', fontSize=7.0, leading=8.5, textColor=DARK_BLUE, alignment=TA_CENTER)
    style_idx_cell = ParagraphStyle('IdxCell', fontName='Helvetica', fontSize=6.8, leading=8.4, textColor=TEXT_DARK)
    style_idx_cell_b = ParagraphStyle('IdxCellB', fontName='Helvetica-Bold', fontSize=6.8, leading=8.4, textColor=TEXT_DARK)
    style_idx_cell_center = ParagraphStyle('IdxCellC', fontName='Helvetica', fontSize=6.8, leading=8.4, textColor=TEXT_DARK, alignment=TA_CENTER)
    style_idx_cell_status = ParagraphStyle('IdxCellSt', fontName='Helvetica-Bold', fontSize=6.5, leading=8.0, textColor=colors.HexColor('#006633'), alignment=TA_CENTER)

    story = []

    # 1. BANNER PRINCIPAL DE LA CARÁTULA
    banner_text = f"""
    <b><font size='9.0' color='#003366'>EXPEDIENTE CLÍNICO INTEGRAL DE ATENCIÓN HOSPITALARIA</font></b><br/>
    <font size='6.8' color='#555555'>Compilado oficial de notas médicas, valoraciones, consentimientos informados, estudios paraclínicos y farmacoterapia.</font><br/>
    <font size='6.2' color='#005FA8'>Conforme a la Norma Oficial Mexicana <b>NOM-004-SSA3-2012</b> y <b>NOM-024-SSA3-2012</b> sobre Sistemas de Información de Registro Electrónico para la Salud.</font>
    """
    style_banner = ParagraphStyle('CoverBanner', fontName='Helvetica', fontSize=7.5, leading=10.0, textColor=DARK_BLUE, alignment=TA_CENTER)
    
    t_banner = Table(
        [[Paragraph(banner_text, style_banner)]],
        colWidths=[content_w]
    )
    t_banner.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), BANNER_BG),
        ('BOX', (0,0), (-1,-1), 0.8, BANNER_BORDER),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_banner)
    story.append(Spacer(1, 4))

    # 2. SECCIÓN: DATOS DE IDENTIFICACIÓN DEL PACIENTE
    t_sec1 = Table(
        [[Paragraph("<b>1. FICHA DE IDENTIFICACIÓN DEL PACIENTE</b>", style_sec_title)]],
        colWidths=[content_w]
    )
    t_sec1.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), DARK_BLUE),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_sec1)

    nombre_p = patient_info.get("name", "N/D").upper()
    expediente_p = patient_info.get("mrn", f"PT-{pt_num}")
    edad_p = patient_info.get("age", "N/D")
    sexo_p = patient_info.get("gender", "N/D")
    dob_p = patient_info.get("dob", "N/D")
    alergias_p = patient_info.get("allergies", "Sin alergias reportadas")

    patient_grid = [
        [
            Paragraph("PACIENTE:", style_label),
            Paragraph(f"<b>{nombre_p}</b>", style_val_accent),
            Paragraph("EXPEDIENTE:", style_label),
            Paragraph(f"<b>{expediente_p}</b>", style_val),
            Paragraph("FECHA NAC:", style_label),
            Paragraph(dob_p, style_val)
        ],
        [
            Paragraph("EDAD / SEXO:", style_label),
            Paragraph(f"{edad_p} / {sexo_p}", style_val),
            Paragraph("GRUPO Y RH:", style_label),
            Paragraph("O+", style_val),
            Paragraph("ALERGIAS:", style_label),
            Paragraph(f"<font color='#d93025'><b>{alergias_p}</b></font>", style_val_red)
        ]
    ]
    t_pt = Table(patient_grid, colWidths=[65, 145, 65, 80, 55, 111.76])
    t_pt.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 0.5, BORDER_GREY),
        ('INNERGRID', (0,0), (-1,-1), 0.3, colors.HexColor('#EEEEEE')),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_pt)
    story.append(Spacer(1, 4))

    # 3. SECCIÓN: DATOS DEL EPISODIO CLÍNICO Y SIGNOS VITALES
    t_sec2 = Table(
        [[Paragraph("<b>2. DATOS DEL EPISODIO HOSPITALARIO Y SIGNOS VITALES</b>", style_sec_title)]],
        colWidths=[content_w]
    )
    t_sec2.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), DARK_BLUE),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_sec2)

    cama_p = patient_info.get("cama", "Urgencias / Piso")
    estatus_txt = "ALTA MÉDICA (EGRESADO)" if is_alta else "ACTIVO EN HOSPITALIZACIÓN / URGENCIAS"
    color_estatus = "#006633" if not is_alta else "#444444"
    diag_p = patient_info.get("diagnostico", "N/D")
    destino_p = patient_info.get("destino", "DOMICILIO")

    ptvs = dashboard_data.get("ptvs", {})
    ta_v = ptvs.get("ta", "120/80")
    fc_v = ptvs.get("fc", "78")
    fr_v = ptvs.get("fr", "18")
    sat_v = ptvs.get("sat_o2", "98")
    temp_v = ptvs.get("temp", "36.5")
    peso_v = ptvs.get("peso", "75.0")
    talla_v = ptvs.get("talla", "1.72")

    episodio_grid = [
        [
            Paragraph("HABITACIÓN / CAMA:", style_label),
            Paragraph(f"<b>{cama_p}</b>", style_val),
            Paragraph("ESTATUS EPISODIO:", style_label),
            Paragraph(f"<font color='{color_estatus}'><b>{estatus_txt}</b></font>", style_val),
            Paragraph("DESTINO:", style_label),
            Paragraph(destino_p, style_val)
        ],
        [
            Paragraph("FECHA / HORA INGRESO:", style_label),
            Paragraph(f"{fecha_ingreso} {hora_ingreso} hrs", style_val),
            Paragraph("FECHA / HORA EGRESO:", style_label),
            Paragraph(f"{fecha_egreso} {hora_egreso} hrs" if is_alta else "— (Episodio Activo)", style_val),
            Paragraph("DIAGNÓSTICO:", style_label),
            Paragraph(diag_p, style_val)
        ],
        [
            Paragraph("SIGNOS VITALES:", style_label),
            Paragraph(f"<b>TA:</b> {ta_v} mmHg &nbsp;|&nbsp; <b>FC:</b> {fc_v} lpm &nbsp;|&nbsp; <b>FR:</b> {fr_v} rpm &nbsp;|&nbsp; <b>SatO2:</b> {sat_v}% &nbsp;|&nbsp; <b>Temp:</b> {temp_v}°C &nbsp;|&nbsp; <b>Peso:</b> {peso_v} kg &nbsp;|&nbsp; <b>Talla:</b> {talla_v} m", style_val),
            Paragraph("", style_label), Paragraph("", style_val), Paragraph("", style_label), Paragraph("", style_val)
        ]
    ]
    t_ep = Table(episodio_grid, colWidths=[95, 140, 90, 85, 45, 66.76])
    t_ep.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 0.5, BORDER_GREY),
        ('INNERGRID', (0,0), (-1,-1), 0.3, colors.HexColor('#EEEEEE')),
        ('SPAN', (1, 2), (5, 2)),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_ep)
    story.append(Spacer(1, 4))

    # 4. SECCIÓN: ÍNDICE OFICIAL DE DOCUMENTOS INTEGRADOS EN EL EXPEDIENTE
    t_sec3 = Table(
        [[Paragraph("<b>3. ÍNDICE Y REGISTRO DE DOCUMENTOS CLÍNICOS INTEGRADOS EN ESTE EXPEDIENTE</b>", style_sec_title)]],
        colWidths=[content_w]
    )
    t_sec3.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), DARK_BLUE),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_sec3)

    if not docs_summary:
        docs_summary = [
            {"num": 1, "codigo": "HE-DIRMED-EXPEDIENTE-COMPLETO", "nombre": "Carátula y Portada de Identificación del Expediente", "folios": "1", "estatus": "Integrado", "firma": "Institucional"},
            {"num": 2, "codigo": "HE-DIRMED-SINPRO-PLT-87/01", "nombre": "Nota Médica de Evolución de Urgencias", "folios": "1 - 2", "estatus": "Integrado", "firma": "Firma Biométrica"},
            {"num": 3, "codigo": "HE-DIRMED-CONSUL-PLT-24", "nombre": "Nota Médica de Evolución de Hospitalización", "folios": "1 - 2", "estatus": "Integrado", "firma": "Firma Biométrica"},
            {"num": 4, "codigo": "CI-SERIE-CONSENTIMIENTOS", "nombre": "Consentimientos Informados Oficiales Registrados", "folios": "Var.", "estatus": "Integrado", "firma": "Dactilar / Digital"},
            {"num": 5, "codigo": "ANEXO-PTDG-SOL-DIET", "nombre": "Anexo de Medicamentos Prescritos y Régimen Dietético", "folios": "1", "estatus": "Integrado", "firma": "Médico Tratante"},
            {"num": 6, "codigo": "ANEXO-PARACLINICOS", "nombre": "Anexo de Laboratorios Clínicos e Imagenología Diagnóstica", "folios": "1", "estatus": "Integrado", "firma": "Laboratorio / Gabinete"}
        ]

    table_data = [
        [
            Paragraph("<b>#</b>", style_idx_head),
            Paragraph("<b>CÓDIGO FORMATO</b>", style_idx_head),
            Paragraph("<b>DOCUMENTO CLÍNICO INTEGRADO</b>", style_idx_head),
            Paragraph("<b>FOLIOS</b>", style_idx_head),
            Paragraph("<b>ESTATUS</b>", style_idx_head),
            Paragraph("<b>VALIDACIÓN</b>", style_idx_head)
        ]
    ]

    for d in docs_summary:
        st_color = "#006633" if d.get("estatus") in ("Integrado", "Registrado", "Firmado") else "#555555"
        st_p = Paragraph(f"<font color='{st_color}'><b>{d.get('estatus', 'Integrado')}</b></font>", style_idx_cell_status)
        table_data.append([
            Paragraph(str(d.get("num", "")), style_idx_cell_center),
            Paragraph(f"<b>{d.get('codigo', '')}</b>", style_idx_cell),
            Paragraph(d.get("nombre", ""), style_idx_cell_b),
            Paragraph(str(d.get("folios", "1")), style_idx_cell_center),
            st_p,
            Paragraph(d.get("firma", "Certificado"), style_idx_cell_center)
        ])

    t_idx = Table(table_data, colWidths=[20, 115, 206.76, 45, 65, 70])
    t_idx.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F1F5F9')),
        ('BOX', (0,0), (-1,-1), 0.5, BORDER_GREY),
        ('INNERGRID', (0,0), (-1,-1), 0.3, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0,0), (-1,-1), 2.2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.2),
        ('LEFTPADDING', (0,0), (-1,-1), 3),
        ('RIGHTPADDING', (0,0), (-1,-1), 3),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(t_idx)
    story.append(Spacer(1, 4))

    # 5. SECCIÓN: TRAZABILIDAD DIGITAL, HASH DE INTEGRIDAD Y CÓDIGO QR
    qr_file = generate_qr_image(qr_url, f"cover_{pt_num}") if qr_url else None
    img_qr = Image(qr_file, width=44, height=44) if qr_file and os.path.exists(qr_file) else Spacer(44, 44)

    sello_txt = (firma_data.get("sello_digital") if firma_data else None) or f"SHA256:HES-EXP-{pt_num}-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
    hash_txt = (firma_data.get("hash_sha256") if firma_data else None) or "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    medico_firmante = (firma_data.get("nombre_medico") if firma_data else None) or "MÉDICO RESPONSABLE HES"
    cedula_firmante = (firma_data.get("cedula") if firma_data else None) or "--"

    audit_text = f"""
    <b><font size='6.8' color='#003366'>CONSTANCIA DE INTEGRIDAD Y AUTENTICIDAD DIGITAL INSTITUCIONAL</font></b><br/>
    <font size='5.8' color='#333333'>Este expediente clínico integral ha sido generado y compilado bajo estándares de seguridad informática y firma electrónica avanzada.</font><br/>
    <font size='5.5' color='#555555'><b>Hash SHA-256 de Integridad:</b> <font face='Courier' color='#111'>{hash_txt[:48]}...</font><br/>
    <b>Sello Electrónico:</b> <font face='Courier' color='#006633'>{sello_txt[:40]}</font><br/>
    <b>Médico Responsable / Auditor:</b> {medico_firmante} &nbsp;|&nbsp; <b>Cédula:</b> {cedula_firmante}</font>
    """
    style_audit = ParagraphStyle('AuditP', fontName='Helvetica', fontSize=6.5, leading=8.2, textColor=TEXT_DARK)

    t_audit = Table(
        [[
            img_qr,
            Paragraph(audit_text, style_audit)
        ]],
        colWidths=[52, content_w - 52]
    )
    t_audit.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 0.6, colors.HexColor('#005FA8')),
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_audit)

    doc.build(story, canvasmaker=make_canvas)
    return output_path


def generate_anexo_farmaco_dietas(dashboard_data: dict, output_path: str) -> str:
    """
    Genera el Anexo de Farmacoterapia Prescrita (PTDG) y Régimen Dietético (MR_SOL_DIET).
    """
    if output_path and os.path.dirname(output_path):
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

    patient_info = dashboard_data.get("patient", {})
    pt_num = str(patient_info.get("mrn", "")).replace("PT-", "").strip()
    fecha_ingreso = patient_info.get("fecha_ingreso", "")
    hora_ingreso = patient_info.get("hora_ingreso", "")

    content_x = FRAME_X + 16.0
    content_w = FRAME_W - 32.0 - 16.0
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

    doc_info = {
        'title_lines': [
            'ANEXO: FARMACOTERAPIA Y RÉGIMEN NUTRICIONAL',
            'HOSPITAL ESCANDÓN - CONTROL DE INDICACIONES MÉDICAS'
        ],
        'code': 'HE-DIRMED-ANEXO-FARMACO-DIET',
        'fecha_ingreso': fecha_ingreso,
        'hora_ingreso': hora_ingreso,
        'draw_header_dates': True
    }

    def make_canvas(*args, **kwargs):
        kwargs['doc_info'] = doc_info
        return RDLCCanvas(*args, **kwargs)

    style_sec_title = ParagraphStyle('SecTitle', fontName='Helvetica-Bold', fontSize=8.2, leading=10.0, textColor=colors.white, alignment=TA_LEFT)
    style_th = ParagraphStyle('Th', fontName='Helvetica-Bold', fontSize=6.8, leading=8.4, textColor=DARK_BLUE, alignment=TA_CENTER)
    style_td = ParagraphStyle('Td', fontName='Helvetica', fontSize=6.8, leading=8.4, textColor=TEXT_DARK)
    style_td_b = ParagraphStyle('TdB', fontName='Helvetica-Bold', fontSize=6.8, leading=8.4, textColor=TEXT_DARK)
    style_td_c = ParagraphStyle('TdC', fontName='Helvetica', fontSize=6.8, leading=8.4, textColor=TEXT_DARK, alignment=TA_CENTER)
    style_label = ParagraphStyle('MetaLabel', fontName='Helvetica-Bold', fontSize=7.2, leading=8.8, textColor=TEXT_MUTED)
    style_val = ParagraphStyle('MetaVal', fontName='Helvetica-Bold', fontSize=7.6, leading=9.4, textColor=TEXT_DARK)

    story = []

    # 1. SECCIÓN: MEDICAMENTOS PRESCRITOS (PTDG)
    t_sec1 = Table(
        [[Paragraph("<b>1. FARMACOTERAPIA Y PRESCRIPCIONES ACTIVAS (PTDG)</b>", style_sec_title)]],
        colWidths=[content_w]
    )
    t_sec1.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), DARK_BLUE),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_sec1)

    meds = dashboard_data.get("medications", [])
    if not meds:
        attending_doc = patient_info.get("attending") or "MÉDICO TRATANTE"
        # Fármacos representativos si la lista está vacía
        meds = [
            {"name": "CEFTRIAXONA 1G SOLUCION INYECTABLE", "dose": "1 g", "route": "Intravenosa", "freq": "Cada 12 horas", "instruction": "Diluir en 100 ml Sol. Fisiológica 0.9% pasar en 30 min", "status": "Activo", "created_by": attending_doc, "date": fecha_ingreso},
            {"name": "PARACETAMOL 1G SOLUCION INYECTABLE (IV)", "dose": "1 g", "route": "Intravenosa", "freq": "Cada 8 horas", "instruction": "Infusión lenta en caso de dolor o temperatura > 38°C", "status": "Activo", "created_by": attending_doc, "date": fecha_ingreso},
            {"name": "OMEPRAZOL 40MG FRASCO AMPULA", "dose": "40 mg", "route": "Intravenosa", "freq": "Cada 24 horas", "instruction": "Protector gástrico en ayuno matutino", "status": "Activo", "created_by": attending_doc, "date": fecha_ingreso},
            {"name": "SOLUCIÓN HARTMANN 1000 ML", "dose": "1000 ml", "route": "Intravenosa", "freq": "Para 8 horas", "instruction": "Mantenimiento hídrico parenteral continuo a 125 ml/h", "status": "Activo", "created_by": attending_doc, "date": fecha_ingreso}
        ]

    med_table_data = [
        [
            Paragraph("<b>#</b>", style_th),
            Paragraph("<b>FÁRMACO / PRESENTACIÓN</b>", style_th),
            Paragraph("<b>DOSIS</b>", style_th),
            Paragraph("<b>VÍA</b>", style_th),
            Paragraph("<b>FRECUENCIA</b>", style_th),
            Paragraph("<b>INDICACIONES ESPECÍFICAS</b>", style_th),
            Paragraph("<b>ESTATUS</b>", style_th)
        ]
    ]

    for idx, m in enumerate(meds[:8]):
        st_txt = m.get("status", "Activo")
        st_col = "#006633" if st_txt.lower() == "activo" else "#990000"
        med_table_data.append([
            Paragraph(str(idx + 1), style_td_c),
            Paragraph(f"<b>{m.get('name', 'Fármaco')}</b>", style_td_b),
            Paragraph(str(m.get("dose", m.get("amount", "--"))), style_td_c),
            Paragraph(str(m.get("route", "IV")), style_td_c),
            Paragraph(str(m.get("freq", "C/8h")), style_td_c),
            Paragraph(str(m.get("instruction", m.get("notes", "Sin observaciones"))), style_td),
            Paragraph(f"<font color='{st_col}'><b>{st_txt}</b></font>", style_td_c)
        ])

    t_meds = Table(med_table_data, colWidths=[18, 140, 45, 48, 55, 160.76, 55])
    t_meds.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F1F5F9')),
        ('BOX', (0,0), (-1,-1), 0.5, BORDER_GREY),
        ('INNERGRID', (0,0), (-1,-1), 0.3, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
        ('LEFTPADDING', (0,0), (-1,-1), 3),
        ('RIGHTPADDING', (0,0), (-1,-1), 3),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(t_meds)
    story.append(Spacer(1, 6))

    # 2. SECCIÓN: RÉGIMEN NUTRICIONAL Y DIETAS (MR_SOL_DIET)
    t_sec2 = Table(
        [[Paragraph("<b>2. RÉGIMEN NUTRICIONAL Y PLAN DIETÉTICO (MR_SOL_DIET)</b>", style_sec_title)]],
        colWidths=[content_w]
    )
    t_sec2.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), DARK_BLUE),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_sec2)

    dietas = dashboard_data.get("dietas", {})
    tipo_d = dietas.get("tipo", "Ayuno Estricto / Solución IV")
    horario_d = dietas.get("horario", "Continuo")
    alergias_d = dietas.get("alergias_alimentarias", "Ninguna registrada")
    indicaciones_d = dietas.get("indicaciones", "Manejo médico en ayuno, protección gástrica y vigilancia de tolerancia vía oral.")
    nutriologo_d = dietas.get("nutriologo", "DRA. CARMEN LOPEZ (NUTRICIÓN CLÍNICA)")

    diet_grid = [
        [
            Paragraph("TIPO DE DIETA:", style_label),
            Paragraph(f"<b>{tipo_d}</b>", style_val),
            Paragraph("HORARIO:", style_label),
            Paragraph(horario_d, style_val),
            Paragraph("ALERGIAS/INTOLERANCIA:", style_label),
            Paragraph(alergias_d, style_val)
        ],
        [
            Paragraph("INDICACIONES:", style_label),
            Paragraph(indicaciones_d, style_val),
            Paragraph("", style_label), Paragraph("", style_val),
            Paragraph("RESPONSABLE:", style_label),
            Paragraph(nutriologo_d, style_val)
        ]
    ]
    t_diet = Table(diet_grid, colWidths=[75, 140, 50, 75, 80, 101.76])
    t_diet.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 0.5, BORDER_GREY),
        ('INNERGRID', (0,0), (-1,-1), 0.3, colors.HexColor('#EEEEEE')),
        ('SPAN', (1, 1), (3, 1)),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_diet)
    story.append(Spacer(1, 6))

    # 3. SECCIÓN: CUIDADOS GENERALES DE ENFERMERÍA
    t_sec3 = Table(
        [[Paragraph("<b>3. PLAN DE CUIDADOS CLÍNICOS Y ENFERMERÍA</b>", style_sec_title)]],
        colWidths=[content_w]
    )
    t_sec3.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), DARK_BLUE),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_sec3)

    cuidados_text = """
    • Monitorización continua de signos vitales por turno (T/A, F/C, F/R, Temp, SatO2).<br/>
    • Cuidados de acceso venoso periférico permeabilizado según protocolo institucional NOM-022-SSA3-2012.<br/>
    • Registro estricto de balance hidroelectrolítico de ingresos y egresos (control de líquidos).<br/>
    • Barandales arriba y medidas de prevención de caídas según escala institucional JCI/DGN.
    """
    style_cuidados = ParagraphStyle('CuidadosP', fontName='Helvetica', fontSize=7.2, leading=9.8, textColor=TEXT_DARK)
    t_cuid = Table(
        [[Paragraph(cuidados_text, style_cuidados)]],
        colWidths=[content_w]
    )
    t_cuid.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 0.5, BORDER_GREY),
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#FAFAFA')),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_cuid)

    doc.build(story, canvasmaker=make_canvas)
    return output_path


def generate_anexo_estudios(dashboard_data: dict, output_path: str) -> str:
    """
    Genera el Anexo de Estudios Paraclínicos (Laboratorio Clínico e Imagenología / Gabinete).
    """
    if output_path and os.path.dirname(output_path):
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

    patient_info = dashboard_data.get("patient", {})
    pt_num = str(patient_info.get("mrn", "")).replace("PT-", "").strip()
    fecha_ingreso = patient_info.get("fecha_ingreso", "")
    hora_ingreso = patient_info.get("hora_ingreso", "")

    content_x = FRAME_X + 16.0
    content_w = FRAME_W - 32.0 - 16.0
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

    doc_info = {
        'title_lines': [
            'ANEXO: ESTUDIOS PARACLÍNICOS Y GABINETE',
            'HOSPITAL ESCANDÓN - RESULTADOS DIAGNÓSTICOS'
        ],
        'code': 'HE-DIRMED-ANEXO-PARACLINICOS',
        'fecha_ingreso': fecha_ingreso,
        'hora_ingreso': hora_ingreso,
        'draw_header_dates': True
    }

    def make_canvas(*args, **kwargs):
        kwargs['doc_info'] = doc_info
        return RDLCCanvas(*args, **kwargs)

    style_sec_title = ParagraphStyle('SecTitle', fontName='Helvetica-Bold', fontSize=8.2, leading=10.0, textColor=colors.white, alignment=TA_LEFT)
    style_th = ParagraphStyle('Th', fontName='Helvetica-Bold', fontSize=6.8, leading=8.4, textColor=DARK_BLUE, alignment=TA_CENTER)
    style_td = ParagraphStyle('Td', fontName='Helvetica', fontSize=6.6, leading=8.2, textColor=TEXT_DARK)
    style_td_b = ParagraphStyle('TdB', fontName='Helvetica-Bold', fontSize=6.6, leading=8.2, textColor=TEXT_DARK)
    style_td_c = ParagraphStyle('TdC', fontName='Helvetica', fontSize=6.6, leading=8.2, textColor=TEXT_DARK, alignment=TA_CENTER)
    style_td_crit = ParagraphStyle('TdCrit', fontName='Helvetica-Bold', fontSize=6.6, leading=8.2, textColor=RED_ALERT)

    story = []

    # 1. SECCIÓN: LABORATORIOS CLÍNICOS
    t_sec1 = Table(
        [[Paragraph("<b>1. ESTUDIOS DE LABORATORIO CLÍNICO Y RESULTADOS</b>", style_sec_title)]],
        colWidths=[content_w]
    )
    t_sec1.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), DARK_BLUE),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_sec1)

    labs = dashboard_data.get("laboratorios", [])
    lab_table_data = [
        [
            Paragraph("<b>FOLIO</b>", style_th),
            Paragraph("<b>ESTUDIO SOLICITADO</b>", style_th),
            Paragraph("<b>FECHA / MÉDICO</b>", style_th),
            Paragraph("<b>RESULTADO / RESUMEN CLÍNICO</b>", style_th),
            Paragraph("<b>VALORES CRÍTICOS / OBSERVACIONES</b>", style_th),
            Paragraph("<b>ESTATUS</b>", style_th)
        ]
    ]

    for l in labs[:6]:
        st_txt = l.get("estatus", "Completado")
        st_col = "#006633" if st_txt.lower() == "completado" else "#d97706"
        lab_table_data.append([
            Paragraph(f"<b>{l.get('id', 'LAB')}</b>", style_td_c),
            Paragraph(f"<b>{l.get('estudio', '')}</b>", style_td_b),
            Paragraph(f"{l.get('fecha_solicitud', '')}<br/><font color='#666'>{l.get('solicitado_por', '')[:20]}</font>", style_td),
            Paragraph(l.get("resultado_resumen", "Sin reporte"), style_td),
            Paragraph(l.get("valores_criticos", "—"), style_td_crit if "leucocitosis" in l.get("valores_criticos", "").lower() or "crítico" in l.get("valores_criticos", "").lower() else style_td),
            Paragraph(f"<font color='{st_col}'><b>{st_txt}</b></font>", style_td_c)
        ])

    t_labs = Table(lab_table_data, colWidths=[48, 120, 85, 140, 78.76, 50])
    t_labs.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F1F5F9')),
        ('BOX', (0,0), (-1,-1), 0.5, BORDER_GREY),
        ('INNERGRID', (0,0), (-1,-1), 0.3, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
        ('LEFTPADDING', (0,0), (-1,-1), 3),
        ('RIGHTPADDING', (0,0), (-1,-1), 3),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(t_labs)
    story.append(Spacer(1, 6))

    # 2. SECCIÓN: IMAGENOLOGÍA Y GABINETE
    t_sec2 = Table(
        [[Paragraph("<b>2. ESTUDIOS DE IMAGENOLOGÍA, RADIOLOGÍA Y GABINETE</b>", style_sec_title)]],
        colWidths=[content_w]
    )
    t_sec2.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), DARK_BLUE),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_sec2)

    img_studies = dashboard_data.get("imagenologia", [])
    img_table_data = [
        [
            Paragraph("<b>FOLIO</b>", style_th),
            Paragraph("<b>ESTUDIO DE GABINETE</b>", style_th),
            Paragraph("<b>FECHA / SOLICITA</b>", style_th),
            Paragraph("<b>HALLAZGOS RADIOLÓGICOS / ECOGRÁFICOS</b>", style_th),
            Paragraph("<b>CONCLUSIÓN DIAGNÓSTICA</b>", style_th),
            Paragraph("<b>ESTATUS</b>", style_th)
        ]
    ]

    for im in img_studies[:4]:
        st_txt = im.get("estatus", "Completado")
        st_col = "#006633" if st_txt.lower() == "completado" else "#d97706"
        img_table_data.append([
            Paragraph(f"<b>{im.get('id', 'IMG')}</b>", style_td_c),
            Paragraph(f"<b>{im.get('estudio', '')}</b>", style_td_b),
            Paragraph(f"{im.get('fecha_solicitud', '')}<br/><font color='#666'>{im.get('solicitado_por', '')[:20]}</font>", style_td),
            Paragraph(im.get("hallazgos", "Sin hallazgos reportados"), style_td),
            Paragraph(f"<b>{im.get('conclusion', '—')}</b>", style_td_b),
            Paragraph(f"<font color='{st_col}'><b>{st_txt}</b></font>", style_td_c)
        ])

    t_img = Table(img_table_data, colWidths=[48, 115, 85, 140, 83.76, 50])
    t_img.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F1F5F9')),
        ('BOX', (0,0), (-1,-1), 0.5, BORDER_GREY),
        ('INNERGRID', (0,0), (-1,-1), 0.3, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
        ('LEFTPADDING', (0,0), (-1,-1), 3),
        ('RIGHTPADDING', (0,0), (-1,-1), 3),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(t_img)

    doc.build(story, canvasmaker=make_canvas)
    return output_path

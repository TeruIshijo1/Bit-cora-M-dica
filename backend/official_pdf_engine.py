import os
import io
import pypdf
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, Frame, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

TEMPLATE_PDF_PATH = os.path.abspath(r'd:\Escritorio\Bitacora_HES\Formatos VERTICAL\87_01_NOTA DE EVOLUCION DE URGENCIAS.pdf')

def get_soap_story(evol):
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'SoapTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=9.5,
        textColor=colors.HexColor('#003366'),
        spaceAfter=1
    )
    body_style = ParagraphStyle(
        'SoapBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.5,
        leading=9,
        textColor=colors.HexColor('#111111'),
        spaceAfter=4,
        alignment=4
    )
    
    story = []
    if evol.get('subjetivo'):
        story.append(Paragraph("<b>(S) Subjetivo:</b> " + evol['subjetivo'].replace('\n', '<br/>'), body_style))
    if evol.get('objetivo'):
        story.append(Paragraph("<b>(O) Objetivo:</b> " + evol['objetivo'].replace('\n', '<br/>'), body_style))
    if evol.get('analisis'):
        story.append(Paragraph("<b>(A) Análisis:</b> " + evol['analisis'].replace('\n', '<br/>'), body_style))
    if evol.get('plan'):
        story.append(Paragraph("<b>(P) Plan (laboratorios solicitados y tratamientos a establecer):</b><br/>" + evol['plan'].replace('\n', '<br/>'), body_style))
        
    return story

def render_page1_overlay(pt_data, evol1, evol2):
    packet = io.BytesIO()
    c = canvas.Canvas(packet, pagesize=letter)
    
    # --- DEMOGRÁFICOS ---
    c.setFont("Helvetica-Bold", 8.5)
    c.drawString(410, 714, str(pt_data.get('fecha_ingreso', '')))
    c.drawString(515, 714, str(pt_data.get('hora_ingreso', '')))
    
    c.setFont("Helvetica-Bold", 9)
    c.drawString(110, 688, str(pt_data.get('nombre', '')).upper())
    c.drawString(485, 688, str(pt_data.get('dob', '')))
    
    c.setFont("Helvetica-Bold", 8.5)
    c.drawString(75, 674, str(pt_data.get('mrn', '')))
    c.drawString(155, 674, str(pt_data.get('cama', '')))
    c.drawString(205, 674, str(pt_data.get('edad', '')))
    
    sexo = str(pt_data.get('sexo', '')).upper()
    if 'M' in sexo and 'F' not in sexo:
        c.drawString(263, 674, "X")
    elif 'F' in sexo:
        c.drawString(290, 674, "X")
        
    c.drawString(375, 674, str(pt_data.get('grupo_rh', 'O+')))
    
    c.setFillColor(colors.HexColor('#d93025'))
    c.setFont("Helvetica-Bold", 8)
    c.drawString(460, 674, str(pt_data.get('alergias', ''))[:35].upper())
    c.setFillColor(colors.black)
    
    c.setFont("Helvetica-Bold", 8)
    c.drawString(85, 658, str(pt_data.get('diagnostico', ''))[:110].upper())
    
    c.drawString(60, 643, str(pt_data.get('destino', ''))[:40].upper())
    c.drawString(340, 643, str(pt_data.get('fecha_egreso', '___/___/___')))
    c.drawString(470, 643, str(pt_data.get('hora_egreso', '__:__')))
    
    # --- EVOLUCIÓN 1 ---
    if evol1 and (evol1.get('subjetivo') or evol1.get('fecha')):
        c.setFont("Helvetica-Bold", 8.5)
        c.drawString(225, 626, str(evol1.get('fecha', '')))
        c.drawString(335, 626, str(evol1.get('hora', '')))
        
        t1 = str(evol1.get('turno', '')).upper()
        if 'MAT' in t1: c.drawString(427, 626, "X")
        elif 'VESP' in t1: c.drawString(482, 626, "X")
        elif 'NOCT' in t1: c.drawString(540, 626, "X")
        
        c.setFont("Helvetica-Bold", 8)
        c.drawString(100, 594, str(evol1.get('vitals_ta', '--')))
        c.drawString(160, 594, str(evol1.get('vitals_fc', '--')))
        c.drawString(220, 594, str(evol1.get('vitals_fr', '--')))
        c.drawString(295, 594, str(evol1.get('vitals_sato2', '--')))
        c.drawString(380, 594, str(evol1.get('vitals_peso', '--')))
        c.drawString(460, 594, str(evol1.get('vitals_talla', '--')))
        
        if evol1.get('medico'):
            c.drawCentredString(150, 365, str(evol1.get('medico', '')).upper())
            c.setFont("Helvetica", 7.5)
            c.drawCentredString(150, 355, f"CÉD. PROF. {evol1.get('cedula', '')}")
        if evol1.get('mip'):
            c.setFont("Helvetica-Bold", 8)
            c.drawCentredString(400, 365, str(evol1.get('mip', '')).upper())
            
        # Dibujar texto SOAP 1 en su Frame (y: 380 a 580)
        frame1 = Frame(20, 375, 535, 205, topPadding=0, bottomPadding=0, leftPadding=0, rightPadding=0, id='F1')
        story1 = get_soap_story(evol1)
        frame1.addFromList(story1, c)
        
    # --- EVOLUCIÓN 2 ---
    if evol2 and (evol2.get('subjetivo') or evol2.get('fecha')):
        c.setFont("Helvetica-Bold", 8.5)
        c.drawString(225, 331, str(evol2.get('fecha', '')))
        c.drawString(335, 331, str(evol2.get('hora', '')))
        
        t2 = str(evol2.get('turno', '')).upper()
        if 'MAT' in t2: c.drawString(427, 331, "X")
        elif 'VESP' in t2: c.drawString(482, 331, "X")
        elif 'NOCT' in t2: c.drawString(540, 331, "X")
        
        c.setFont("Helvetica-Bold", 8)
        c.drawString(100, 298, str(evol2.get('vitals_ta', '--')))
        c.drawString(160, 298, str(evol2.get('vitals_fc', '--')))
        c.drawString(220, 298, str(evol2.get('vitals_fr', '--')))
        c.drawString(295, 298, str(evol2.get('vitals_sato2', '--')))
        c.drawString(380, 298, str(evol2.get('vitals_peso', '--')))
        c.drawString(460, 298, str(evol2.get('vitals_talla', '--')))
        
        if evol2.get('medico'):
            c.drawCentredString(150, 68, str(evol2.get('medico', '')).upper())
            c.setFont("Helvetica", 7.5)
            c.drawCentredString(150, 58, f"CÉD. PROF. {evol2.get('cedula', '')}")
        if evol2.get('mip'):
            c.setFont("Helvetica-Bold", 8)
            c.drawCentredString(400, 68, str(evol2.get('mip', '')).upper())
            
        # Dibujar texto SOAP 2 en su Frame (y: 80 a 285)
        frame2 = Frame(20, 80, 535, 205, topPadding=0, bottomPadding=0, leftPadding=0, rightPadding=0, id='F2')
        story2 = get_soap_story(evol2)
        frame2.addFromList(story2, c)
        
    c.save()
    packet.seek(0)
    return pypdf.PdfReader(packet).pages[0]

def render_page2_overlay(evol3):
    packet = io.BytesIO()
    c = canvas.Canvas(packet, pagesize=letter)
    
    # --- EVOLUCIÓN 3 ---
    if evol3 and (evol3.get('subjetivo') or evol3.get('fecha')):
        c.setFont("Helvetica-Bold", 8.5)
        c.drawString(225, 681, str(evol3.get('fecha', '')))
        c.drawString(335, 681, str(evol3.get('hora', '')))
        
        t3 = str(evol3.get('turno', '')).upper()
        if 'MAT' in t3: c.drawString(427, 681, "X")
        elif 'VESP' in t3: c.drawString(482, 681, "X")
        elif 'NOCT' in t3: c.drawString(540, 681, "X")
        
        c.setFont("Helvetica-Bold", 8)
        c.drawString(100, 648, str(evol3.get('vitals_ta', '--')))
        c.drawString(160, 648, str(evol3.get('vitals_fc', '--')))
        c.drawString(220, 648, str(evol3.get('vitals_fr', '--')))
        c.drawString(295, 648, str(evol3.get('vitals_sato2', '--')))
        c.drawString(380, 648, str(evol3.get('vitals_peso', '--')))
        c.drawString(460, 648, str(evol3.get('vitals_talla', '--')))
        
        if evol3.get('medico'):
            c.drawCentredString(150, 365, str(evol3.get('medico', '')).upper())
            c.setFont("Helvetica", 7.5)
            c.drawCentredString(150, 355, f"CÉD. PROF. {evol3.get('cedula', '')}")
        if evol3.get('mip'):
            c.setFont("Helvetica-Bold", 8)
            c.drawCentredString(400, 365, str(evol3.get('mip', '')).upper())
            
        # Dibujar texto SOAP 3 en su Frame (y: 380 a 635)
        frame3 = Frame(20, 375, 535, 260, topPadding=0, bottomPadding=0, leftPadding=0, rightPadding=0, id='F3')
        story3 = get_soap_story(evol3)
        frame3.addFromList(story3, c)
        
    c.save()
    packet.seek(0)
    return pypdf.PdfReader(packet).pages[0]

def generate_official_nota_urgencias_pdf_3_evols(pt_data, evol1, evol2, evol3, output_pdf_path):
    template_reader = pypdf.PdfReader(TEMPLATE_PDF_PATH)
    page1_template = template_reader.pages[0]
    page2_template = template_reader.pages[1]
    
    page1_overlay = render_page1_overlay(pt_data, evol1, evol2)
    page2_overlay = render_page2_overlay(evol3)
    
    writer = pypdf.PdfWriter()
    
    # Página 1
    p1 = pypdf.PageObject.create_blank_page(width=letter[0], height=letter[1])
    p1.merge_page(page1_template)
    p1.merge_page(page1_overlay)
    writer.add_page(p1)
    
    # Página 2 (se agrega si existe Evolución 3 o si siempre se entrega el formato de 2 hojas)
    p2 = pypdf.PageObject.create_blank_page(width=letter[0], height=letter[1])
    p2.merge_page(page2_template)
    p2.merge_page(page2_overlay)
    writer.add_page(p2)
    
    with open(output_pdf_path, "wb") as f_out:
        writer.write(f_out)
        
    return output_pdf_path

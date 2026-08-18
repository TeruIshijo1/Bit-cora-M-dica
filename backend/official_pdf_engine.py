import os
import io
import pypdf
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, Frame, SimpleDocTemplate, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# Ruta del formato original oficial (Vectorial de Illustrator)
TEMPLATE_PDF_PATH = os.path.abspath(r'd:\Escritorio\Bitacora_HES\Formatos VERTICAL\87_01_NOTA DE EVOLUCION DE URGENCIAS.pdf')

def create_page1_overlay(pt_data, nota_data):
    """Crea una capa transparente con los datos demográficos y signos vitales en las coordenadas exactas."""
    packet = io.BytesIO()
    c = canvas.Canvas(packet, pagesize=letter)
    
    # 1. Fecha y Hora de Ingreso (Top Right)
    c.setFont("Helvetica-Bold", 8.5)
    c.drawString(410, 714, str(pt_data.get('fecha_ingreso', '')))
    c.drawString(515, 714, str(pt_data.get('hora_ingreso', '')))
    
    # 2. Nombre del Paciente y Fecha de Nacimiento
    c.setFont("Helvetica-Bold", 9)
    c.drawString(110, 688, str(pt_data.get('nombre', '')).upper())
    c.drawString(485, 688, str(pt_data.get('dob', '')))
    
    # 3. Expediente, Cama, Edad, Sexo, Grupo y RH, Alergias
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
    
    # Alergias en rojo institucional
    c.setFillColor(colors.HexColor('#d93025'))
    c.setFont("Helvetica-Bold", 8)
    c.drawString(460, 674, str(pt_data.get('alergias', ''))[:35].upper())
    c.setFillColor(colors.black)
    
    # 4. Diagnóstico(s)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(85, 658, str(nota_data.get('diagnostico', ''))[:110].upper())
    
    # 5. Destino, Fecha de egreso, Hora de egreso
    c.setFont("Helvetica-Bold", 8)
    c.drawString(60, 643, str(nota_data.get('destino', ''))[:40].upper())
    c.drawString(340, 643, str(nota_data.get('fecha_egreso', '___/___/___')))
    c.drawString(470, 643, str(nota_data.get('hora_egreso', '__:__')))
    
    # 6. Fecha de Nota, Hora, Turno
    c.setFont("Helvetica-Bold", 8.5)
    c.drawString(225, 626, str(nota_data.get('fecha', '')))
    c.drawString(335, 626, str(nota_data.get('hora', '')))
    
    turno = str(nota_data.get('turno', 'Matutino')).upper()
    if 'MAT' in turno:
        c.drawString(427, 626, "X")
    elif 'VESP' in turno:
        c.drawString(482, 626, "X")
    elif 'NOCT' in turno:
        c.drawString(540, 626, "X")
        
    # 7. Signos Vitales
    c.setFont("Helvetica-Bold", 8)
    c.drawString(100, 594, str(nota_data.get('vitals_ta', '--')))
    c.drawString(160, 594, str(nota_data.get('vitals_fc', '--')))
    c.drawString(220, 594, str(nota_data.get('vitals_fr', '--')))
    c.drawString(295, 594, str(nota_data.get('vitals_sato2', '--')))
    c.drawString(380, 594, str(nota_data.get('vitals_peso', '--')))
    c.drawString(460, 594, str(nota_data.get('vitals_talla', '--')))
    
    # 8. Médico y MIP (Firmas inferiores de la primera nota)
    c.setFont("Helvetica-Bold", 8)
    medico_name = str(nota_data.get('medico', ''))
    c.drawCentredString(150, 370, medico_name.upper())
    c.setFont("Helvetica", 7.5)
    c.drawCentredString(150, 360, f"CÉD. PROF. {nota_data.get('cedula', 'N/D')}")
    
    c.save()
    packet.seek(0)
    return pypdf.PdfReader(packet).pages[0]

def create_flowable_soap_pages(nota_data):
    """Genera las páginas con el texto SOAP que fluye dentro del área clínica del formato."""
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'SoapTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=10,
        textColor=colors.HexColor('#003366'),
        spaceAfter=1
    )
    
    body_style = ParagraphStyle(
        'SoapBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=9.5,
        textColor=colors.HexColor('#111111'),
        spaceAfter=5,
        alignment=4 # Justified
    )
    
    story = []
    
    # (S) Subjetivo
    story.append(Paragraph("<b>(S) Subjetivo:</b>", title_style))
    story.append(Paragraph(nota_data.get('subjetivo', '').replace('\n', '<br/>'), body_style))
    story.append(Spacer(1, 2))
    
    # (O) Objetivo
    story.append(Paragraph("<b>(O) Objetivo:</b>", title_style))
    story.append(Paragraph(nota_data.get('objetivo', '').replace('\n', '<br/>'), body_style))
    story.append(Spacer(1, 2))
    
    # (A) Análisis
    story.append(Paragraph("<b>(A) Análisis:</b>", title_style))
    story.append(Paragraph(nota_data.get('analisis', '').replace('\n', '<br/>'), body_style))
    story.append(Spacer(1, 2))
    
    # (P) Plan
    story.append(Paragraph("<b>(P) Plan (laboratorios solicitados y tratamientos a establecer):</b>", title_style))
    story.append(Paragraph(nota_data.get('plan', '').replace('\n', '<br/>'), body_style))
    
    packet = io.BytesIO()
    doc = SimpleDocTemplate(
        packet,
        pagesize=letter,
        leftMargin=20,
        rightMargin=55,
        topMargin=215, # Deja libre el encabezado y datos del paciente
        bottomMargin=70  # Deja libre las firmas y el pie
    )
    
    doc.build(story)
    packet.seek(0)
    return pypdf.PdfReader(packet).pages

def generate_official_nota_urgencias_pdf(nota_data, pt_data, output_pdf_path):
    """
    Combina el PDF oficial de Adobe Illustrator (fondo idéntico al 100%)
    con los datos del paciente y el texto SOAP dinámico.
    """
    template_reader = pypdf.PdfReader(TEMPLATE_PDF_PATH)
    page1_template = template_reader.pages[0]
    page2_template = template_reader.pages[1] if len(template_reader.pages) > 1 else page1_template
    
    # Generar capa de datos demográficos para página 1
    page1_data_overlay = create_page1_overlay(pt_data, nota_data)
    
    # Generar páginas de texto SOAP fluido
    soap_pages = create_flowable_soap_pages(nota_data)
    
    writer = pypdf.PdfWriter()
    
    # Página 1: Fondo oficial de Illustrator + datos + texto SOAP (página 1)
    p1 = pypdf.PageObject.create_blank_page(width=letter[0], height=letter[1])
    p1.merge_page(page1_template)
    p1.merge_page(page1_data_overlay)
    if len(soap_pages) > 0:
        p1.merge_page(soap_pages[0])
    writer.add_page(p1)
    
    # Si el texto SOAP es muy extenso y generó página 2, 3, etc.
    for i in range(1, len(soap_pages)):
        p_extra = pypdf.PageObject.create_blank_page(width=letter[0], height=letter[1])
        p_extra.merge_page(page2_template)
        p_extra.merge_page(soap_pages[i])
        writer.add_page(p_extra)
        
    with open(output_pdf_path, "wb") as f_out:
        writer.write(f_out)
        
    return output_pdf_path

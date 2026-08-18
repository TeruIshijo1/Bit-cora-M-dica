import os
import qrcode
from xhtml2pdf import pisa
from jinja2 import Environment, FileSystemLoader

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")
if not os.path.exists(TEMPLATE_DIR):
    os.makedirs(TEMPLATE_DIR)

# HTML Template
html_template = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Comprobante de Atención - {{ folio }}</title>
    <style>
        body { font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; margin: 0; padding: 20px; color: #333; }
        .header-table { width: 100%; border-bottom: 4px solid #1a56db; padding-bottom: 10px; margin-bottom: 20px; }
        .logo { width: 250px; }
        .folio-container { text-align: right; }
        .folio-title { color: #d93025; font-weight: bold; font-size: 14px; margin: 0; }
        .folio-number { font-size: 24px; font-weight: bold; margin: 5px 0 0 0; }
        .title-bar { background-color: #1a56db; color: white; padding: 10px 20px; font-weight: bold; font-size: 18px; margin-bottom: 20px; }
        .section-title { color: #1e40af; font-size: 14px; font-weight: bold; border-bottom: 1px solid #e2e8f0; padding-bottom: 5px; margin-bottom: 15px; margin-top: 30px; }
        .grid { display: table; width: 100%; margin-bottom: 10px; }
        .row { display: table-row; }
        .label { display: table-cell; font-weight: bold; font-size: 12px; color: #64748b; padding: 8px 0; width: 30%; }
        .value { display: table-cell; font-size: 14px; padding: 8px 0; font-weight: bold; }
        .notes-box { border: 1px solid #cbd5e1; border-radius: 8px; padding: 15px; font-size: 13px; font-style: italic; min-height: 80px; margin-bottom: 40px; }
        .signatures { display: table; width: 100%; margin-top: 60px; text-align: center; font-size: 12px; }
        .sig-col { display: table-cell; width: 50%; padding: 0 20px; }
        .line { border-top: 1px solid #94a3b8; margin-bottom: 5px; }
        .auth-box { text-align: center; color: #64748b; font-size: 10px; font-family: monospace; margin-bottom: 40px; }
        .qr-code { width: 80px; }
        .footer { text-align: center; font-size: 10px; color: #94a3b8; margin-top: 50px; border-top: 1px dashed #cbd5e1; padding-top: 20px; }
    </style>
</head>
<body>
    <table class="header-table">
        <tr>
            <td style="width: 33%; vertical-align: middle;">
                <h1 style="color:#1a56db; margin:0;">Hospital<span style="color:#4ade80;">Escandón</span></h1>
                <p style="color:#64748b; font-style:italic; margin:0; font-size:12px;">calidad médica a tu alcance</p>
            </td>
            <td style="width: 34%; text-align: center; vertical-align: middle;">
                <img src="{{ qr_img_path }}" class="qr-code" />
            </td>
            <td style="width: 33%; text-align: right; vertical-align: middle;">
                <p class="folio-title">COMPROBANTE DE ATENCIÓN</p>
                <p class="folio-number">{{ folio }}</p>
            </td>
        </tr>
    </table>

    <div class="title-bar">
        REGISTRO OFICIAL DE PROCEDIMIENTO Y ATENCIÓN MÉDICA
    </div>

    <div class="section-title">1. INFORMACIÓN DEL PERSONAL MÉDICO</div>
    <div class="grid">
        <div class="row"><div class="label">MÉDICO ESPECIALISTA:</div><div class="value">{{ medico_nombre }}</div></div>
        <div class="row"><div class="label">ESPECIALIDAD:</div><div class="value">{{ medico_especialidad }}</div></div>
        <div class="row"><div class="label">CÉDULA PROFESIONAL:</div><div class="value">{{ medico_cedula }}</div></div>
    </div>

    <div class="section-title">2. DETALLES DE LA ATENCIÓN Y PACIENTE</div>
    <div class="grid">
        <div class="row"><div class="label">PACIENTE:</div><div class="value">{{ paciente_nombre }}</div></div>
        <div class="row"><div class="label">HABITACIÓN (MANUAL):</div><div class="value">{{ habitacion }}</div></div>
        <div class="row">
            <div class="label">TIPO DE SERVICIO:</div>
            <div class="value"><span style="background:#e0f2fe; color:#0369a1; padding:4px 8px; border-radius:4px; font-size:12px;">{{ tipo_servicio }}</span></div>
        </div>
        <div class="row"><div class="label">FECHA / HORA ATENCIÓN:</div><div class="value">{{ fecha_realizacion }}</div></div>
        <div class="row"><div class="label">FECHA / HORA REGISTRO:</div><div class="value">{{ fecha_registro }} <span style="color:#94a3b8;font-weight:normal;font-size:10px;">(Captura en Tiempo y Forma)</span></div></div>
    </div>

    <div class="section-title">3. PROCEDIMIENTO REALIZADO Y NOTAS CLÍNICAS</div>
    <div class="notes-box">
        {{ notas }}
    </div>

    <div class="auth-box">
        <p style="font-weight:bold; margin-bottom:2px;">[ AUTENTICADO BIOMÉTRICAMENTE ]</p>
        <p style="margin:0;">SHA256:</p>
        <p style="margin:0;">{{ hash_seguridad }}</p>
    </div>

    <div class="signatures">
        <div class="sig-col">
            <div class="line"></div>
            <p style="font-weight:bold; margin:0;">{{ medico_nombre }}</p>
            <p style="color:#64748b; margin:0;">Firma Digital del Médico (Huella)</p>
        </div>
        <div class="sig-col">
            <div class="line"></div>
            <p style="font-weight:bold; margin:0;">RECURSOS HUMANOS / PAGOS</p>
            <p style="color:#64748b; margin:0;">Validación Administrativa Interna</p>
        </div>
    </div>

    <div class="footer">
        Este documento es un comprobante interno de control operacional para el Hospital Escandón.<br>
        Su alteración o mal uso invalida el proceso de distribución de honorarios correspondiente.
    </div>
</body>
</html>
"""

template_path = os.path.join(TEMPLATE_DIR, "comprobante.html")
with open(template_path, "w", encoding="utf-8") as f:
    f.write(html_template)

env = FileSystemLoader(TEMPLATE_DIR)
template_env = Environment(loader=env)

def generate_pdf(atencion, medico, paciente):
    # Generar QR
    qr = qrcode.make(atencion.folio)
    qr_dir = os.path.join(os.path.dirname(__file__), "static", "qr")
    if not os.path.exists(qr_dir):
        os.makedirs(qr_dir)
    
    qr_img_path = os.path.join(qr_dir, f"{atencion.folio}.png")
    qr.save(qr_img_path)
    
    # Preparar datos
    tipos = {"CON": "CONSULTA MÉDICA", "JOR": "JORNADA", "INT": "INTERCONSULTA MÉDICA"}
    
    # Convertir QR a base64 para embeber directamente en el HTML y evitar problemas de rutas en xhtml2pdf
    import base64
    with open(qr_img_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
    qr_b64 = f"data:image/png;base64,{encoded_string}"
    
    context = {
        "folio": atencion.folio,
        "medico_nombre": medico.nombre_completo,
        "medico_especialidad": medico.especialidad,
        "medico_cedula": medico.cedula,
        "paciente_nombre": paciente.nombre_completo,
        "habitacion": atencion.habitacion_capturada,
        "tipo_servicio": tipos.get(atencion.tipo_atencion, atencion.tipo_atencion),
        "fecha_realizacion": atencion.fecha_realizacion.strftime("%Y-%m-%d %H:%M hrs"),
        "fecha_registro": atencion.fecha_registro.strftime("%Y-%m-%d %H:%M hrs"),
        "notas": atencion.procedimiento_detalle,
        "hash_seguridad": atencion.hash_seguridad,
        "qr_img_path": qr_b64
    }
    
    template = template_env.get_template("comprobante.html")
    html_out = template.render(context)
    
    pdf_dir = os.path.join(os.path.dirname(__file__), "static", "pdfs")
    if not os.path.exists(pdf_dir):
        os.makedirs(pdf_dir)
        
    pdf_path = os.path.join(pdf_dir, f"{atencion.folio}.pdf")
    
    with open(pdf_path, "w+b") as result_file:
        pisa_status = pisa.CreatePDF(html_out, dest=result_file)
    
    return f"/static/pdfs/{atencion.folio}.pdf"

import subprocess
import base64

CHROME_PATHS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]

def get_browser_executable():
    for p in CHROME_PATHS:
        if os.path.exists(p):
            return p
    return None

def render_html_to_pdf_chrome(html_content, output_pdf_path):
    browser = get_browser_executable()
    if not browser:
        # Fallback to pisa if browser not found
        with open(output_pdf_path, "w+b") as result_file:
            pisa.CreatePDF(html_content, dest=result_file)
        return output_pdf_path

    temp_html = output_pdf_path.replace(".pdf", "_render_temp.html")
    with open(temp_html, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    cmd = [
        browser,
        "--headless",
        "--disable-gpu",
        "--no-pdf-header-footer",
        "--allow-file-access-from-files",
        f"--print-to-pdf={output_pdf_path}",
        temp_html
    ]
    
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
    
    if os.path.exists(temp_html):
        try:
            os.remove(temp_html)
        except:
            pass
            
    if res.returncode != 0 and not os.path.exists(output_pdf_path):
        raise RuntimeError(f"Chromium PDF Generation failed: {res.stderr}")
        
    return output_pdf_path

def generate_nota_urgencias_pdf(nota_data, pt_data, pdf_filename):
    logo_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "static", "logo.png"))
    logo_b64 = ""
    if os.path.exists(logo_file):
        with open(logo_file, "rb") as lf:
            logo_b64 = f"data:image/png;base64,{base64.b64encode(lf.read()).decode('utf-8')}"
            
    context = {
        "paciente": pt_data,
        "nota": nota_data,
        "medico": {
            "nombre": nota_data.get('medico', 'N/D'),
            "cedula": nota_data.get('cedula', 'N/D')
        },
        "logo_path": logo_b64
    }
    
    template = template_env.get_template("nota_urgencias.html")
    html_out = template.render(context)
    
    pdf_dir = os.path.join(os.path.dirname(__file__), "static", "pdfs")
    if not os.path.exists(pdf_dir):
        os.makedirs(pdf_dir)
        
    pdf_path = os.path.join(pdf_dir, pdf_filename)
    render_html_to_pdf_chrome(html_out, pdf_path)
    
    return f"/static/pdfs/{pdf_filename}"

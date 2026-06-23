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
        .header { display: flex; justify-content: space-between; align-items: center; border-bottom: 4px solid #1a56db; padding-bottom: 10px; margin-bottom: 20px; }
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
        .qr-code { position: absolute; top: 20px; left: 50%; transform: translateX(-50%); width: 80px; }
        .footer { text-align: center; font-size: 10px; color: #94a3b8; margin-top: 50px; border-top: 1px dashed #cbd5e1; padding-top: 20px; }
    </style>
</head>
<body>
    <div class="header">
        <div>
            <!-- We assume the logo is available or we use a text placeholder if not -->
            <h1 style="color:#1a56db; margin:0;">Hospital<span style="color:#4ade80;">Escandón</span></h1>
            <p style="color:#64748b; font-style:italic; margin:0; font-size:12px;">calidad médica a tu alcance</p>
        </div>
        <img src="{{ qr_img_path }}" class="qr-code" />
        <div class="folio-container">
            <p class="folio-title">COMPROBANTE DE ATENCIÓN</p>
            <p class="folio-number">{{ folio }}</p>
        </div>
    </div>

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
    
    context = {
        "folio": atencion.folio,
        "medico_nombre": medico.nombre_completo if medico else "Sin asignar",
        "medico_especialidad": medico.especialidad if medico else "",
        "medico_cedula": medico.cedula if medico else "",
        "paciente_nombre": paciente.nombre_completo if paciente else "Desconocido",
        "habitacion": atencion.habitacion_capturada,
        "tipo_servicio": tipos.get(atencion.tipo_atencion, atencion.tipo_atencion),
        "fecha_realizacion": atencion.fecha_realizacion.strftime("%Y-%m-%d %H:%M hrs"),
        "fecha_registro": atencion.fecha_registro.strftime("%Y-%m-%d %H:%M hrs"),
        "notas": atencion.procedimiento_detalle,
        "hash_seguridad": atencion.hash_seguridad,
        "qr_img_path": f"file://{os.path.abspath(qr_img_path)}"
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

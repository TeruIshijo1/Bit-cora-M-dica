from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
import datetime
import hashlib
import uuid
from PIL import Image
import io
import os
import shutil
import csv
from fastapi.responses import StreamingResponse

from database import engine, get_db, Base
from pydantic import BaseModel
from typing import List, Optional
import shutil
from database import SessionLocal, engine
import models
import schemas
from seed import get_password_hash, pwd_context
from jose import JWTError, jwt
from pdf_generator import generate_pdf

from docxtpl import DocxTemplate
from docx2pdf import convert as docx2pdf_convert
import pythoncom
from openpyxl import Workbook
from openpyxl.styles import PatternFill, Font, Alignment
from openpyxl.drawing.image import Image as ExcelImage
from fastapi.responses import FileResponse

# Config
SECRET_KEY = "hospital_escandon_super_secret"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 12
UPLOADS_DIR = "static/uploads"
GENERADOS_DIR = "generados"
PLANTILLAS_DIR = "plantillas"
os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(GENERADOS_DIR, exist_ok=True)
os.makedirs(PLANTILLAS_DIR, exist_ok=True)

app = FastAPI(title="MediReg API - Hospital Escandón")

# Servir estaticos para fotos de medicos
app.mount("/static", StaticFiles(directory="static"), name="static")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

from fastapi.security import OAuth2PasswordBearer
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login/admin")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        rol: str = payload.get("rol")
        if username is None or rol is None:
            raise HTTPException(status_code=401, detail="Credenciales invalidas")
        
        if rol == "medico":
            user = db.query(models.Medico).filter(models.Medico.cedula == username).first()
            if user:
                # Add a temporary attribute so require_role works
                setattr(user, "rol", "medico")
        else:
            user = db.query(models.Usuario).filter(models.Usuario.username == username).first()
            
        if not user:
            raise HTTPException(status_code=401, detail="Usuario no existe")
            
        return user
    except JWTError:
        raise HTTPException(status_code=401, detail="Credenciales invalidas")

def require_role(allowed_roles: List[str]):
    def role_checker(current_user = Depends(get_current_user)):
        rol = getattr(current_user, "rol", "medico")
        if "admin" not in allowed_roles and rol not in allowed_roles and rol != "admin":
            raise HTTPException(status_code=403, detail="No tienes permisos para esta acción")
        return current_user
    return role_checker

import requests

@app.post("/api/auth/login/admin", response_model=schemas.Token)
def login_admin(req: schemas.LoginAdminRequest, db: Session = Depends(get_db)):
    print(f"Intento de login para usuario: '{req.username}'")
    user = db.query(models.Usuario).filter(models.Usuario.username == req.username).first()
    if not user:
        print("Error: Usuario no encontrado en DB.")
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")
        
    try:
        if not pwd_context.verify(req.password, user.password_hash):
            print(f"Error: Contraseña incorrecta para el usuario '{req.username}'.")
            raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")
    except Exception as e:
        print(f"Error verificando hash (posible contraseña en texto plano en DB): {e}")
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")
    
    print("Login exitoso.")
    access_token = create_access_token(data={"sub": user.username, "rol": user.rol})
    return {"access_token": access_token, "token_type": "bearer", "rol": user.rol}

@app.post("/api/auth/login/biometric", response_model=schemas.Token)
def login_biometric(req: schemas.LoginBiometricRequest, db: Session = Depends(get_db)):
    if not req.fmd_template:
        raise HTTPException(status_code=400, detail="No se recibió la huella biométrica (FMD).")
    
    medicos = db.query(models.Medico).filter(models.Medico.activo_status == True, models.Medico.fmd_template.isnot(None)).all()
    if not medicos:
        raise HTTPException(status_code=401, detail="No hay médicos registrados con huella.")
    
    match_found = None
    medicos_data = [{"id": m.id, "fmd_template": m.fmd_template} for m in medicos]
    try:
        response = requests.post("http://localhost:8082/match-bulk", json={
            "fmd1": req.fmd_template,
            "medicos": medicos_data
        }, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success") and data.get("isMatch"):
                match_id = data.get("match_id")
                match_found = next((m for m in medicos if m.id == match_id), None)
        else:
            print(f"Error del motor biométrico: {response.text}")
            raise HTTPException(status_code=500, detail="Error de procesamiento biométrico.")
    except Exception as e:
        print(f"Error conectando al microservicio: {e}")
        raise HTTPException(status_code=500, detail="Error de conexión con motor biométrico.")
            
    if not match_found:
        raise HTTPException(status_code=401, detail="Huella no reconocida.")
    
    access_token = create_access_token(data={"sub": match_found.cedula, "rol": "medico"})
    return {
        "access_token": access_token, 
        "token_type": "bearer", 
        "rol": "medico",
        "medico_id": match_found.id,
        "nombre_completo": match_found.nombre_completo,
        "especialidad": match_found.especialidad,
        "cedula": match_found.cedula,
        "foto_url": match_found.foto_url
    }

@app.post("/api/auth/impersonate")
def impersonate(req: schemas.ImpersonateRequest, db: Session = Depends(get_db), current_user: models.Usuario = Depends(require_role(["admin", "sistemas"]))):
    # This allows admin to get a token for any username or medico
    if req.rol == "medico":
        medico = db.query(models.Medico).filter(models.Medico.id == req.target_id).first()
        if not medico:
            raise HTTPException(status_code=404, detail="Médico no encontrado")
        access_token = create_access_token(data={"sub": medico.cedula, "rol": "medico"})
        return {
            "access_token": access_token, 
            "token_type": "bearer", 
            "rol": "medico",
            "medico_id": medico.id,
            "nombre_completo": medico.nombre_completo,
            "especialidad": medico.especialidad,
            "cedula": medico.cedula,
            "foto_url": medico.foto_url
        }
    else:
        user = db.query(models.Usuario).filter(models.Usuario.id == req.target_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        access_token = create_access_token(data={"sub": user.username, "rol": user.rol})
        return {
            "access_token": access_token, 
            "token_type": "bearer", 
            "rol": user.rol
        }

# --- Catálogos ---
@app.get("/api/catalogos/areas", response_model=List[schemas.CatalogoResponse])
def get_areas(db: Session = Depends(get_db)):
    return db.query(models.CatalogoArea).filter(models.CatalogoArea.activo == True).all()

@app.post("/api/catalogos/areas", response_model=schemas.CatalogoResponse)
def create_area(area: schemas.CatalogoBase, db: Session = Depends(get_db), current_user: models.Usuario = Depends(require_role(["admin", "rh"]))):
    nueva_area = models.CatalogoArea(nombre=area.nombre, activo=area.activo)
    db.add(nueva_area)
    db.commit()
    db.refresh(nueva_area)
    return nueva_area

@app.get("/api/catalogos/tipos", response_model=List[schemas.CatalogoResponse])
def get_tipos(db: Session = Depends(get_db)):
    return db.query(models.CatalogoTipoAtencion).filter(models.CatalogoTipoAtencion.activo == True).all()

@app.post("/api/catalogos/tipos", response_model=schemas.CatalogoResponse)
def create_tipo(tipo: schemas.CatalogoBase, db: Session = Depends(get_db), current_user: models.Usuario = Depends(require_role(["admin", "rh"]))):
    nuevo_tipo = models.CatalogoTipoAtencion(nombre=tipo.nombre, activo=tipo.activo)
    db.add(nuevo_tipo)
    db.commit()
    db.refresh(nuevo_tipo)
    return nuevo_tipo

# --- Pacientes ---
@app.get("/api/pacientes", response_model=List[schemas.PacienteResponse])
def get_pacientes(db: Session = Depends(get_db)):
    return db.query(models.Paciente).filter(models.Paciente.status_ingreso == "Ingresado").all()

@app.post("/api/pacientes", response_model=schemas.PacienteResponse)
def create_paciente(paciente: schemas.PacienteCreate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(get_current_user)):
    nuevo_paciente = models.Paciente(
        nombre_completo=paciente.nombre_completo,
        num_habitacion=paciente.num_habitacion,
        area_hospitalaria=paciente.area_hospitalaria,
        status_ingreso="Ingresado",
        creado_por_id=current_user.id
    )
    db.add(nuevo_paciente)
    db.commit()
    db.refresh(nuevo_paciente)
    return nuevo_paciente

@app.put("/api/pacientes/{paciente_id}", response_model=schemas.PacienteResponse)
def update_paciente(paciente_id: int, req: schemas.PacienteUpdate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(get_current_user)):
    paciente = db.query(models.Paciente).filter(models.Paciente.id == paciente_id).first()
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    paciente.nombre_completo = req.nombre_completo
    paciente.num_habitacion = req.num_habitacion
    if req.area_hospitalaria is not None:
        paciente.area_hospitalaria = req.area_hospitalaria
    db.commit()
    db.refresh(paciente)
    return paciente

@app.put("/api/pacientes/{paciente_id}/alta")
def alta_paciente(paciente_id: int, db: Session = Depends(get_db), current_user: models.Usuario = Depends(get_current_user)):
    paciente = db.query(models.Paciente).filter(models.Paciente.id == paciente_id).first()
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    paciente.status_ingreso = "Alta"
    db.commit()
    return {"message": "Paciente dado de alta"}

# --- Médicos ---
@app.get("/api/medicos", response_model=List[schemas.MedicoResponse])
def get_medicos(db: Session = Depends(get_db)):
    return db.query(models.Medico).filter(models.Medico.activo_status == True).all()

@app.post("/api/medicos", response_model=schemas.MedicoResponse)
async def create_medico(
    numero_empleado: str = Form(...),
    nombre_completo: str = Form(...),
    especialidad: str = Form(...),
    cedula: str = Form(...),
    fmd_template: str = Form(...),
    foto: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    # Ya no se genera numero empleado automáticamente
    
    huella_token_unique = str(uuid.uuid4())
    
    foto_url = None
    if foto:
        ext = os.path.splitext(foto.filename)[1]
        filename = f"{numero_empleado}{ext}"
        filepath = os.path.join(UPLOADS_DIR, filename)
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(foto.file, buffer)
        foto_url = f"/static/uploads/{filename}"

    nuevo_medico = models.Medico(
        numero_empleado=numero_empleado,
        nombre_completo=nombre_completo,
        especialidad=especialidad,
        cedula=cedula,
        huella_token=huella_token_unique,
        fmd_template=fmd_template,
        foto_url=foto_url
    )
    db.add(nuevo_medico)
    db.commit()
    db.refresh(nuevo_medico)
    return nuevo_medico

# --- Atenciones ---
@app.post("/api/atenciones/pre-captura", response_model=schemas.AtencionResponse)
def pre_captura(req: schemas.PreCapturaRequest, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    hoy = datetime.date.today()
    
    exact_match = db.query(models.AtencionMedica).filter(
        models.AtencionMedica.paciente_id == req.paciente_id,
        models.AtencionMedica.medico_id == req.medico_id,
        models.AtencionMedica.tipo_atencion == req.tipo_atencion,
        models.AtencionMedica.nombre_procedimiento == req.nombre_procedimiento,
        func.date(models.AtencionMedica.fecha_realizacion) == hoy
    ).first()
    
    if exact_match:
        raise HTTPException(status_code=400, detail=f"Ya existe un registro exacto hoy con folio: {exact_match.folio}")
    
    count = db.query(models.AtencionMedica).count() + 1
    year = datetime.date.today().year
    folio = f"HES-{year}-{count:05d}"
    
    is_medico = getattr(current_user, "rol", "") == "medico"
    
    paciente_db = db.query(models.Paciente).filter(models.Paciente.id == req.paciente_id).first()
    area_hosp = req.area_hospitalaria or (paciente_db.area_hospitalaria if paciente_db else "No asignada")
    
    nueva_atencion = models.AtencionMedica(
        folio=folio,
        fecha_realizacion=req.fecha_realizacion,
        medico_id=req.medico_id,
        paciente_id=req.paciente_id,
        area_hospitalaria=area_hosp,
        tipo_atencion=req.tipo_atencion,
        nombre_procedimiento=req.nombre_procedimiento,
        habitacion_capturada=req.habitacion_capturada,
        procedimiento_detalle=req.procedimiento_detalle,
        creado_por_id=None if is_medico else current_user.id,
        estatus_pago="Pendiente de Firma"
    )
    
    db.add(nueva_atencion)
    db.commit()
    db.refresh(nueva_atencion)
    return nueva_atencion

@app.get("/api/atenciones/pendientes/{medico_id}", response_model=List[schemas.AtencionResponse])
def pendientes_medico(medico_id: int, db: Session = Depends(get_db)):
    return db.query(models.AtencionMedica).filter(
        models.AtencionMedica.medico_id == medico_id,
        models.AtencionMedica.estatus_pago == "Pendiente de Firma"
    ).all()

@app.get("/api/atenciones/historial/{medico_id}", response_model=List[schemas.AtencionResponse])
def historial_medico(medico_id: int, db: Session = Depends(get_db)):
    return db.query(models.AtencionMedica).filter(
        models.AtencionMedica.medico_id == medico_id,
        models.AtencionMedica.estatus_pago != "Pendiente de Firma"
    ).order_by(models.AtencionMedica.fecha_firma.desc()).all()

@app.get("/api/atenciones/mis-registros", response_model=List[schemas.AtencionResponse])
def mis_registros(db: Session = Depends(get_db), current_user: models.Usuario = Depends(get_current_user)):
    hoy = datetime.date.today()
    return db.query(models.AtencionMedica).filter(
        models.AtencionMedica.creado_por_id == current_user.id,
        func.date(models.AtencionMedica.fecha_registro) == hoy
    ).order_by(models.AtencionMedica.fecha_registro.desc()).all()

@app.get("/api/atenciones/todas", response_model=List[schemas.AtencionResponse])
def get_todas_atenciones(db: Session = Depends(get_db), current_user: models.Usuario = Depends(require_role(["admin", "rh", "sistemas"]))):
    return db.query(models.AtencionMedica).order_by(models.AtencionMedica.fecha_realizacion.desc()).all()

@app.get("/api/atenciones/exportar")
def exportar_atenciones(db: Session = Depends(get_db), current_user: models.Usuario = Depends(require_role(["admin", "rh", "sistemas"]))):
    atenciones = db.query(models.AtencionMedica).order_by(models.AtencionMedica.fecha_realizacion.desc()).all()
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Atenciones"
    
    # Insertar Logo
    logo_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend", "public", "logo.png")
    if os.path.exists(logo_path):
        img = ExcelImage(logo_path)
        img.width = 100
        img.height = 35
        ws.add_image(img, "A1")
        
    # Metadata Header
    ws.merge_cells("C1:G1")
    ws["C1"] = "HOSPITAL ESCANDÓN - REPORTE DE ATENCIONES MÉDICAS"
    ws["C1"].font = Font(bold=True, size=14, color="003870")
    ws["C1"].alignment = Alignment(horizontal="center", vertical="center")
    
    ws["I1"] = "Generado por:"
    ws["I1"].font = Font(bold=True)
    ws["J1"] = current_user.username
    ws["I2"] = "Fecha:"
    ws["I2"].font = Font(bold=True)
    ws["J2"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Headers
    headers = ["Folio", "Fecha Realización", "Médico", "Especialidad", "Paciente", "Habitación", "Área Hospitalaria", "Tipo Atención", "Procedimiento", "Estatus Pago", "Fecha Firma", "Hash"]
    header_fill = PatternFill(start_color="003870", end_color="003870", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True)
    
    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=4, column=col_num, value=header)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center")
        
    row_idx = 5
    for a in atenciones:
        medico_nombre = a.medico.nombre_completo if a.medico else "N/A"
        medico_esp = a.medico.especialidad if a.medico else "N/A"
        paciente_nombre = a.paciente.nombre_completo if a.paciente else "N/A"
        f_firma = a.fecha_firma.strftime("%Y-%m-%d %H:%M:%S") if a.fecha_firma else ""
        
        ws.cell(row=row_idx, column=1, value=a.folio)
        ws.cell(row=row_idx, column=2, value=a.fecha_realizacion.strftime("%Y-%m-%d %H:%M:%S") if a.fecha_realizacion else "")
        ws.cell(row=row_idx, column=3, value=medico_nombre)
        ws.cell(row=row_idx, column=4, value=medico_esp)
        ws.cell(row=row_idx, column=5, value=paciente_nombre)
        ws.cell(row=row_idx, column=6, value=a.habitacion_capturada)
        ws.cell(row=row_idx, column=7, value=a.area_hospitalaria)
        ws.cell(row=row_idx, column=8, value=a.tipo_atencion)
        ws.cell(row=row_idx, column=9, value=a.nombre_procedimiento)
        ws.cell(row=row_idx, column=10, value=a.estatus_pago)
        ws.cell(row=row_idx, column=11, value=f_firma)
        ws.cell(row=row_idx, column=12, value=a.hash_seguridad or "")
        row_idx += 1
        
    from openpyxl.utils import get_column_letter
    for col_idx in range(1, ws.max_column + 1):
        column = get_column_letter(col_idx)
        max_length = 0
        for cell in ws[column]:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = (max_length + 2)
        ws.column_dimensions[column].width = adjusted_width if adjusted_width < 50 else 50
        
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    response = StreamingResponse(iter([output.getvalue()]), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response.headers["Content-Disposition"] = "attachment; filename=atenciones_export.xlsx"
    return response

@app.post("/api/atenciones/firmar-lote")
def firmar_lote(req: schemas.FirmaLoteRequest, db: Session = Depends(get_db)):
    if not req.fmd_template:
        raise HTTPException(status_code=400, detail="No huella recibida.")

    medicos = db.query(models.Medico).filter(models.Medico.activo_status == True, models.Medico.fmd_template.isnot(None)).all()
    if not medicos:
        raise HTTPException(status_code=401, detail="No hay médicos registrados")
    
    match_found = None
    medicos_data = [{"id": m.id, "fmd_template": m.fmd_template} for m in medicos]
    
    try:
        response = requests.post("http://localhost:8082/match-bulk", json={
            "fmd1": req.fmd_template,
            "medicos": medicos_data
        }, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success") and data.get("isMatch"):
                match_id = data.get("match_id")
                match_found = next((m for m in medicos if m.id == match_id), None)
    except Exception as e:
        print(f"Error conectando al microservicio en firma: {e}")
            
    if not match_found:
        raise HTTPException(status_code=401, detail="Huella no reconocida.")
    
    firmados = []
    ahora = datetime.datetime.utcnow()
    
    for folio in req.folios:
        atencion = db.query(models.AtencionMedica).filter(
            models.AtencionMedica.folio == folio,
            models.AtencionMedica.medico_id == match_found.id
        ).first()
        
        if atencion:
            paciente = db.query(models.Paciente).filter(models.Paciente.id == atencion.paciente_id).first()
            raw_text = f"{atencion.folio}{atencion.fecha_realizacion.isoformat()}{match_found.nombre_completo}{paciente.nombre_completo}{atencion.habitacion_capturada}"
            hash_str = hashlib.sha256(raw_text.encode('utf-8')).hexdigest()
            
            atencion.hash_seguridad = hash_str
            atencion.estatus_pago = "Validado para Pago"
            atencion.fecha_firma = ahora
            
            # Generar PDF
            try:
                pdf_path = generate_pdf(atencion, match_found, paciente)
                atencion.ruta_archivo_firmado = pdf_path
            except Exception as e:
                print("Error al generar PDF:", e)
                
            firmados.append(folio)
            
    db.commit()
    return {"message": f"{len(firmados)} atenciones firmadas", "firmados": firmados}

@app.put("/api/atenciones/{folio}")
def update_atencion(folio: str, tipo_atencion: str, db: Session = Depends(get_db)):
    atencion = db.query(models.AtencionMedica).filter(models.AtencionMedica.folio == folio).first()
    if not atencion:
        raise HTTPException(status_code=404, detail="Atención no encontrada")
    atencion.tipo_atencion = tipo_atencion
    db.commit()
    return {"message": "Actualizado"}

@app.get("/api/atenciones/{folio}/pdf")
def generar_comprobante_pdf(folio: str, db: Session = Depends(get_db)):
    atencion = db.query(models.AtencionMedica).filter(models.AtencionMedica.folio == folio).first()
    if not atencion:
        raise HTTPException(status_code=404, detail="Atención no encontrada")
        
    template_path = os.path.join(PLANTILLAS_DIR, "comprobante_base.docx")
    if not os.path.exists(template_path):
        raise HTTPException(status_code=500, detail="Plantilla no encontrada")
        
    doc = DocxTemplate(template_path)
    
    context = {
        "folio": atencion.folio,
        "medico_nombre": atencion.medico.nombre_completo if atencion.medico else "",
        "medico_especialidad": atencion.medico.especialidad if atencion.medico else "",
        "medico_cedula": atencion.medico.cedula if atencion.medico else "",
        "medico_num_empleado": atencion.medico.numero_empleado if atencion.medico else "",
        "paciente_nombre": atencion.paciente.nombre_completo if atencion.paciente else "",
        "paciente_habitacion": atencion.habitacion_capturada or (atencion.paciente.num_habitacion if atencion.paciente else ""),
        "tipo_servicio": atencion.tipo_atencion,
        "fecha_atencion": atencion.fecha_realizacion.strftime("%Y-%m-%d %H:%M") if atencion.fecha_realizacion else "",
        "fecha_registro": (atencion.fecha_firma or atencion.fecha_realizacion or datetime.datetime.now()).strftime("%Y-%m-%d %H:%M"),
        "procedimiento": atencion.nombre_procedimiento,
        "detalle": atencion.procedimiento_detalle or "Sin notas clínicas",
        "hash_seguridad": atencion.hash_seguridad or "Pendiente"
    }
    
    doc.render(context)
    
    temp_docx = os.path.join(GENERADOS_DIR, f"{folio}.docx")
    temp_pdf = os.path.join(GENERADOS_DIR, f"{folio}.pdf")
    
    doc.save(temp_docx)
    
    pythoncom.CoInitialize()
    try:
        docx2pdf_convert(os.path.abspath(temp_docx), os.path.abspath(temp_pdf))
    except Exception as e:
        print(f"Error docx2pdf: {e}")
        raise HTTPException(status_code=500, detail="Error generando PDF")
    finally:
        pythoncom.CoUninitialize()
        
    if not os.path.exists(temp_pdf):
        raise HTTPException(status_code=500, detail="PDF no se pudo generar")
        
    return FileResponse(temp_pdf, media_type="application/pdf", filename=f"Comprobante_{folio}.pdf")

# === ENDPOINTS RH ===
@app.get("/api/usuarios", response_model=List[schemas.UsuarioResponse])
def get_usuarios(db: Session = Depends(get_db), current_user: models.Usuario = Depends(require_role(["admin", "rh", "sistemas"]))):
    return db.query(models.Usuario).all()

@app.post("/api/usuarios", response_model=schemas.UsuarioResponse)
def create_usuario(usuario: schemas.UsuarioCreate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(require_role(["admin", "rh", "sistemas"]))):
    existing = db.query(models.Usuario).filter(models.Usuario.username == usuario.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Usuario ya existe")
    nuevo_usuario = models.Usuario(
        username=usuario.username,
        password_hash=pwd_context.hash(usuario.password),
        rol=usuario.rol
    )
    db.add(nuevo_usuario)
    db.commit()
    db.refresh(nuevo_usuario)
    return nuevo_usuario

@app.put("/api/usuarios/{usuario_id}/password")
def update_usuario_password(usuario_id: int, payload: schemas.UsuarioPasswordUpdate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(require_role(["admin", "sistemas"]))):
    usuario = db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
    usuario.password_hash = pwd_context.hash(payload.new_password)
    db.commit()
    return {"message": "Contraseña actualizada exitosamente"}

@app.delete("/api/usuarios/{usuario_id}")
def delete_usuario(usuario_id: int, db: Session = Depends(get_db), current_user: models.Usuario = Depends(require_role(["sistemas"]))):
    usuario = db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if usuario.username == current_user.username:
        raise HTTPException(status_code=400, detail="No te puedes eliminar a ti mismo")
    db.delete(usuario)
    db.commit()
    return {"message": "Usuario eliminado"}

@app.put("/api/medicos/{medico_id}")
def update_medico(medico_id: int, activo: bool, db: Session = Depends(get_db), current_user: models.Usuario = Depends(require_role(["admin", "rh", "sistemas"]))):
    medico = db.query(models.Medico).filter(models.Medico.id == medico_id).first()
    medico.activo_status = activo
    db.commit()
    return {"message": "Actualizado"}

@app.put("/api/medicos/{medico_id}/datos", response_model=schemas.MedicoResponse)
async def update_medico_datos(
    medico_id: int,
    numero_empleado: str = Form(...),
    nombre_completo: str = Form(...),
    especialidad: str = Form(...),
    cedula: str = Form(...),
    foto: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_role(["admin", "rh", "sistemas"]))
):
    medico = db.query(models.Medico).filter(models.Medico.id == medico_id).first()
    if not medico:
        raise HTTPException(status_code=404, detail="Médico no encontrado")
        
    medico.numero_empleado = numero_empleado
    medico.nombre_completo = nombre_completo
    medico.especialidad = especialidad
    medico.cedula = cedula
    
    if foto:
        ext = foto.filename.split(".")[-1]
        filename = f"{medico_id}_{numero_empleado}.{ext}"
        filepath = os.path.join(UPLOADS_DIR, filename)
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(foto.file, buffer)
        medico.foto_url = f"/static/uploads/{filename}"
        
    db.commit()
    db.refresh(medico)
    return medico

# === ESCANEOS RH ===
ESCANEOS_DIR = "static/escaneos_rh"
os.makedirs(ESCANEOS_DIR, exist_ok=True)

@app.get("/api/escaneos", response_model=List[schemas.EscaneoRHResponse])
def get_escaneos(db: Session = Depends(get_db), current_user: models.Usuario = Depends(require_role(["admin", "rh", "sistemas"]))):
    return db.query(models.EscaneoRH).order_by(models.EscaneoRH.fecha_subida.desc()).all()

@app.post("/api/escaneos", response_model=schemas.EscaneoRHResponse)
async def upload_escaneo(
    titulo: str = Form(...),
    archivo: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_role(["admin", "rh"]))
):
    # Enforce 5MB limit
    contents = await archivo.read()
    if len(contents) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="El archivo excede el tamaño máximo permitido de 5MB.")
    
    ext = os.path.splitext(archivo.filename)[1]
    unique_filename = f"{uuid.uuid4()}{ext}"
    filepath = os.path.join(ESCANEOS_DIR, unique_filename)
    
    with open(filepath, "wb") as buffer:
        buffer.write(contents)
        
    ruta_archivo = f"/static/escaneos_rh/{unique_filename}"
    
    nuevo_escaneo = models.EscaneoRH(
        titulo=titulo,
        nombre_archivo=archivo.filename,
        ruta_archivo=ruta_archivo,
        subido_por_id=current_user.id
    )
    db.add(nuevo_escaneo)
    db.commit()
    db.refresh(nuevo_escaneo)
    return nuevo_escaneo

@app.put("/api/escaneos/{escaneo_id}", response_model=schemas.EscaneoRHResponse)
def rename_escaneo(escaneo_id: int, req: schemas.EscaneoRHUpdate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(require_role(["admin", "rh"]))):
    escaneo = db.query(models.EscaneoRH).filter(models.EscaneoRH.id == escaneo_id).first()
    if not escaneo:
        raise HTTPException(status_code=404, detail="Escaneo no encontrado")
    escaneo.titulo = req.titulo
    db.commit()
    db.refresh(escaneo)
    return escaneo

@app.delete("/api/escaneos/{escaneo_id}")
def delete_escaneo(escaneo_id: int, db: Session = Depends(get_db), current_user: models.Usuario = Depends(require_role(["admin", "rh"]))):
    escaneo = db.query(models.EscaneoRH).filter(models.EscaneoRH.id == escaneo_id).first()
    if not escaneo:
        raise HTTPException(status_code=404, detail="Escaneo no encontrado")
    
    # Try to delete the physical file
    try:
        filename = os.path.basename(escaneo.ruta_archivo)
        filepath = os.path.join(ESCANEOS_DIR, filename)
        if os.path.exists(filepath):
            os.remove(filepath)
    except Exception as e:
        print(f"Error al eliminar el archivo fisico: {e}")
        
    db.delete(escaneo)
    db.commit()
    return {"message": "Escaneo eliminado correctamente"}

# === DASHBOARD & STATS ===
@app.get("/api/stats")
def get_stats(db: Session = Depends(get_db), current_user: models.Usuario = Depends(require_role(["admin", "sistemas", "rh"]))):
    # Total atenciones este mes
    hoy = datetime.date.today()
    primer_dia_mes = datetime.date(hoy.year, hoy.month, 1)
    total_mes = db.query(models.AtencionMedica).filter(func.date(models.AtencionMedica.fecha_realizacion) >= primer_dia_mes).count()
    
    # Pendientes de firma totales
    pendientes = db.query(models.AtencionMedica).filter(models.AtencionMedica.estatus_pago == "Pendiente de Firma").count()
    
    # Top procedimientos
    top_proc = db.query(
        models.AtencionMedica.nombre_procedimiento, func.count(models.AtencionMedica.folio).label('total')
    ).group_by(models.AtencionMedica.nombre_procedimiento).order_by(func.count(models.AtencionMedica.folio).desc()).limit(5).all()
    
    # Top medicos
    top_meds = db.query(
        models.Medico.nombre_completo, func.count(models.AtencionMedica.folio).label('total')
    ).join(models.AtencionMedica, models.Medico.id == models.AtencionMedica.medico_id).group_by(models.Medico.nombre_completo).order_by(func.count(models.AtencionMedica.folio).desc()).limit(5).all()
    
    return {
        "total_mes": total_mes,
        "pendientes_firma": pendientes,
        "top_procedimientos": [{"nombre": p[0], "total": p[1]} for p in top_proc],
        "top_medicos": [{"nombre": m[0], "total": m[1]} for m in top_meds]
    }

# === BACKUP ===
# === BACKUP ===
from fastapi.responses import FileResponse
@app.get("/api/backup")
def get_backup(current_user: models.Usuario = Depends(require_role(["admin", "sistemas"]))):
    db_path = "hospital_escandon.db"
    if not os.path.exists(db_path):
        raise HTTPException(status_code=404, detail="Base de datos no encontrada")
    hoy = datetime.date.today().strftime("%Y%m%d")
    return FileResponse(path=db_path, filename=f"backup_hes_{hoy}.db", media_type="application/octet-stream")

# === FRONTEND (PRODUCCION) ===
frontend_dist = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
if os.path.exists(frontend_dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="assets")
    
    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        # Ignorar si es una ruta de backend o estática principal
        if full_path.startswith("api/") or full_path.startswith("static/") or full_path.startswith("generados/"):
            raise HTTPException(status_code=404, detail="Not found")
            
        # Si el archivo existe físicamente en dist/, servirlo (ej. logo.png, websdk.client.min.js)
        file_path = os.path.join(frontend_dist, full_path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        
        # De lo contrario, devolver index.html para el React Router
        index_path = os.path.join(frontend_dist, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        return {"message": "Frontend no construido. Por favor corre 'npm run build' en la carpeta frontend."}

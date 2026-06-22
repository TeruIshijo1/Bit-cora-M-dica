from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# --- Catálogos ---
class CatalogoBase(BaseModel):
    nombre: str
    activo: Optional[bool] = True

class CatalogoResponse(CatalogoBase):
    id: int
    class Config:
        from_attributes = True

# --- Auth ---
class LoginAdminRequest(BaseModel):
    username: str
    password: str

class LoginBiometricRequest(BaseModel):
    huella_token: str
    fmd_template: Optional[str] = None

class ImpersonateRequest(BaseModel):
    rol: str
    target_id: int
    fmd_template: Optional[str] = None

class Token(BaseModel):
    access_token: str
    token_type: str
    rol: Optional[str] = None
    medico_id: Optional[int] = None
    nombre_completo: Optional[str] = None
    especialidad: Optional[str] = None
    cedula: Optional[str] = None
    foto_url: Optional[str] = None

# --- Usuarios ---
class UsuarioCreate(BaseModel):
    username: str
    password: str
    rol: str

class UsuarioResponse(BaseModel):
    id: int
    username: str
    rol: str
    activo: bool
    class Config:
        from_attributes = True

class PacienteCreate(BaseModel):
    nombre_completo: str
    num_habitacion: str
    area_hospitalaria: Optional[str] = None

class PacienteUpdate(BaseModel):
    nombre_completo: str
    num_habitacion: str
    area_hospitalaria: Optional[str] = None

class PacienteResponse(BaseModel):
    id: int
    nombre_completo: str
    num_habitacion: str
    area_hospitalaria: Optional[str] = None
    status_ingreso: str
    fecha_registro: Optional[datetime] = None
    creador: Optional[UsuarioResponse] = None
    class Config:
        from_attributes = True

# --- Médicos ---
class MedicoCreate(BaseModel):
    nombre_completo: str
    especialidad: str
    cedula: str
    huella_token: str
    fmd_template: Optional[str] = None

class MedicoResponse(BaseModel):
    id: int
    numero_empleado: str
    nombre_completo: str
    especialidad: str
    cedula: str
    foto_url: Optional[str] = None
    activo_status: bool
    class Config:
        from_attributes = True

# --- Atenciones ---
class PreCapturaRequest(BaseModel):
    medico_id: int
    paciente_id: int
    habitacion_capturada: str
    area_hospitalaria: Optional[str] = None
    tipo_atencion: str
    nombre_procedimiento: str
    fecha_realizacion: datetime
    procedimiento_detalle: str

class AtencionResponse(BaseModel):
    folio: str
    fecha_registro: datetime
    fecha_realizacion: Optional[datetime] = None
    fecha_firma: Optional[datetime] = None
    hash_seguridad: Optional[str] = None
    medico_id: int
    paciente_id: int
    creado_por_id: Optional[int] = None
    
    area_hospitalaria: Optional[str] = None
    tipo_atencion: Optional[str] = None
    nombre_procedimiento: Optional[str] = None
    habitacion_capturada: Optional[str] = None
    procedimiento_detalle: Optional[str] = None
    estatus_pago: Optional[str] = None
    
    paciente: Optional[PacienteResponse] = None
    medico: Optional[MedicoResponse] = None
    creador: Optional[UsuarioResponse] = None
    class Config:
        from_attributes = True

class FirmaLoteRequest(BaseModel):
    huella_token: str
    fmd_template: Optional[str] = None
    folios: List[str]

# --- Escaneos RH ---
class EscaneoRHResponse(BaseModel):
    id: int
    titulo: str
    nombre_archivo: str
    ruta_archivo: str
    fecha_subida: datetime
    subido_por: Optional[UsuarioResponse] = None
    class Config:
        from_attributes = True

class EscaneoRHUpdate(BaseModel):
    titulo: str

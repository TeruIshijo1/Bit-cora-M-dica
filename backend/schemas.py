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
    nombre_completo: Optional[str] = None

class UsuarioPasswordUpdate(BaseModel):
    new_password: str

class UsuarioResponse(BaseModel):
    id: int
    username: str
    nombre_completo: Optional[str] = None
    rol: str
    activo: bool
    class Config:
        from_attributes = True

class PacienteBase(BaseModel):
    nombre_completo: str
    num_habitacion: str
    area_hospitalaria: Optional[str] = None

class PacienteCreate(PacienteBase):
    pass

class PacienteUpdate(PacienteBase):
    pass

class PacienteResponse(PacienteBase):
    id: int
    status_ingreso: str
    fecha_registro: Optional[datetime] = None
    creador: Optional[UsuarioResponse] = None
    dado_de_alta_por: Optional[UsuarioResponse] = None
    fecha_alta: Optional[datetime] = None
    registrado_por_nombre: Optional[str] = None
    class Config:
        from_attributes = True

# --- Médicos ---
class MedicoCreate(BaseModel):
    nombre_completo: str
    especialidad: str
    cedula: str
    huella_token: str
    fmd_template: Optional[str] = None
    bajo_contrato: bool = False
    horario_laboral: Optional[str] = None
    es_ayudante: bool = False
    medico_asignado_id: Optional[int] = None

class MedicoResponse(BaseModel):
    id: int
    numero_empleado: str
    nombre_completo: str
    especialidad: str
    cedula: str
    foto_url: Optional[str] = None
    activo_status: bool
    bajo_contrato: bool
    tiene_huella: bool
    horario_laboral: Optional[str] = None
    es_ayudante: bool
    medico_asignado_id: Optional[int] = None
    class Config:
        from_attributes = True

# --- Notas ---
class NotaCreate(BaseModel):
    nota: str

class NotaResponse(BaseModel):
    id: int
    nota: str
    fecha_creacion: datetime
    creador: Optional[UsuarioResponse] = None
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
    fecha_realizacion: Optional[datetime] = None
    procedimiento_detalle: Optional[str] = None

class AtencionResponse(BaseModel):
    folio: str
    fecha_registro: datetime
    fecha_realizacion: Optional[datetime] = None
    area_hospitalaria: str
    tipo_atencion: str
    nombre_procedimiento: str
    habitacion_capturada: str
    procedimiento_detalle: Optional[str] = None
    estatus_pago: str
    fecha_firma: Optional[datetime] = None
    reaperturado: bool
    is_caducado: Optional[bool] = False
    registrado_por_nombre: Optional[str] = None
    
    medico: Optional[MedicoResponse] = None
    paciente: Optional[PacienteResponse] = None
    creador: Optional[UsuarioResponse] = None
    notas: List[NotaResponse] = []
    
    class Config:
        from_attributes = True

class FirmaExpressRequest(BaseModel):
    folio: str
    huella_token: str

class FirmaResponse(BaseModel):
    folio: str
    mensaje: str
    hash_seguridad: str
    fecha_firma: datetime

class FirmaLoteRequest(BaseModel):
    huella_token: str
    fmd_template: Optional[str] = None
    folios: List[str]

# --- Archivos RH ---
class EscaneoRHCreate(BaseModel):
    titulo: str

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

# --- Auditoría y Trazabilidad ---
class TrasladoPacienteResponse(BaseModel):
    id: int
    paciente_id: int
    origen_area: Optional[str] = None
    origen_habitacion: Optional[str] = None
    destino_area: Optional[str] = None
    destino_habitacion: Optional[str] = None
    fecha_traslado: datetime
    usuario: Optional[UsuarioResponse] = None
    class Config:
        from_attributes = True

class AuditoriaLogResponse(BaseModel):
    id: int
    accion: str
    detalles_json: Optional[str] = None
    fecha_hora: datetime
    ip_origen: Optional[str] = None
    usuario: Optional[UsuarioResponse] = None
    class Config:
        from_attributes = True

# --- Analíticas ---
class AreaStat(BaseModel):
    area: str
    cantidad: int

class SLAStat(BaseModel):
    medico: str
    tiempo_promedio_minutos: float
    total_atenciones: int

class ActivityStat(BaseModel):
    fecha: str
    cantidad: int

class AnalyticsDashboardResponse(BaseModel):
    visitas_por_area: List[AreaStat]
    sla_por_medico: List[SLAStat]
    actividad_reciente: List[ActivityStat]
    total_pacientes_activos: int
    total_atenciones_mes: int

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

class CatalogoTipoAtencionResponse(BaseModel):
    id: int
    nombre: str
    
    class Config:
        from_attributes = True

class CatalogoFormatoCreate(BaseModel):
    codigo: str
    nombre: str
    activo: Optional[bool] = True

class CatalogoFormatoResponse(BaseModel):
    id: int
    codigo: str
    nombre: str
    activo: bool

    class Config:
        from_attributes = True

# --- Auth ---
class BiometricChallengeResponse(BaseModel):
    challenge_id: str
    capture_authorization: str
    expires_in: int = 120
    expires_at: datetime

class BiometricChallengeRequest(BaseModel):
    action: str
    session_id: str
    expected_medico_id: Optional[int] = None
    expected_identity_ref: Optional[str] = None
    patient_ref: Optional[str] = None
    document_code: Optional[str] = None
    document_ref: Optional[str] = None

class LoginAdminRequest(BaseModel):
    username: str
    password: str

class LoginBiometricRequest(BaseModel):
    fmd_template: str
    medico_id: Optional[int] = None
    challenge_id: str
    session_id: str

class ImpersonateRequest(BaseModel):
    rol: str
    target_id: int
    motivo: str

class Token(BaseModel):
    access_token: str
    token_type: str
    rol: Optional[str] = None
    medico_id: Optional[int] = None
    nombre_completo: Optional[str] = None
    especialidad: Optional[str] = None
    cedula: Optional[str] = None
    foto_url: Optional[str] = None
    permisos_modulos: Optional[str] = None
    formatos_permitidos: Optional[str] = None
    must_change_password: bool = False

# --- Usuarios ---
class UsuarioCreate(BaseModel):
    username: str
    password: str
    rol: str
    nombre_completo: Optional[str] = None
    permisos_modulos: Optional[str] = None
    formatos_permitidos: Optional[str] = None
    formatos_firma_permitidos: Optional[str] = None

class UsuarioPasswordUpdate(BaseModel):
    new_password: str


class UsuarioSelfPasswordChange(BaseModel):
    current_password: str
    new_password: str

class UsuarioUpdate(BaseModel):
    rol: Optional[str] = None
    nombre_completo: Optional[str] = None
    permisos_modulos: Optional[str] = None
    formatos_permitidos: Optional[str] = None
    formatos_firma_permitidos: Optional[str] = None

class UsuarioResponse(BaseModel):
    id: int
    username: str
    nombre_completo: Optional[str] = None
    rol: str
    activo: bool
    must_change_password: bool = False
    permisos_modulos: Optional[str] = None
    formatos_permitidos: Optional[str] = None
    formatos_firma_permitidos: Optional[str] = None
    biometric_status: str = "SIN_BIOMETRIA"
    tiene_huella: bool = False
    class Config:
        from_attributes = True

class PacienteBase(BaseModel):
    nombre_completo: str
    num_habitacion: str
    area_hospitalaria: Optional[str] = None
    codigo_barras: Optional[str] = None

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

# --- Camas ---
class CamaResponse(BaseModel):
    id: int
    numero_cama: str
    area: str
    estado: str
    activo: bool
    class Config:
        from_attributes = True

class OcupacionArea(BaseModel):
    area: str
    total_camas: int
    camas_ocupadas: int
    camas_disponibles: int
    camas_mantenimiento: int
    porcentaje_ocupacion: float

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
    formatos_permitidos: Optional[str] = None

class MedicoUpdatePermisos(BaseModel):
    formatos_permitidos: Optional[str] = None

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
    formatos_permitidos: Optional[str] = None
    biometric_status: str = "SIN_BIOMETRIA"
    requiere_reenrolamiento: bool = False
    requiere_actualizacion_fea: bool = False
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
    huella_token: Optional[str] = None
    fmd_template: Optional[str] = None
    medico_id: Optional[int] = None
    challenge_id: str
    session_id: str

class FirmaResponse(BaseModel):
    folio: str
    mensaje: str
    hash_seguridad: str
    fecha_firma: datetime

class FirmaLoteRequest(BaseModel):
    huella_token: Optional[str] = None
    fmd_template: Optional[str] = None
    folios: List[str]
    medico_id: Optional[int] = None
    challenge_id: str
    session_id: str

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
    request_id: str
    operation_id: Optional[str] = None
    actor_real: str
    actor_effective: str
    motivo_impersonacion: Optional[str] = None
    resultado: str
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

class CleanRecordsRequest(BaseModel):
    clean_atenciones: bool = False
    clean_notas: bool = False
    clean_traslados: bool = False
    clean_pacientes: bool = False

class AutorizarRequest(BaseModel):
    aceptado: bool

# --- Biometría Dactilar de Firmantes por Episodio (Pacientes, Familiares y Testigos) ---
class FirmanteBiometricoBase(BaseModel):
    tipo_firmante: str = "PACIENTE" # PACIENTE, REPRESENTANTE_LEGAL, TESTIGO_1, TESTIGO_2
    nombre_completo: str
    parentesco: Optional[str] = "Titular"
    identificacion_oficial: Optional[str] = None
    domicilio: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[str] = None

class FirmanteBiometricoCreate(FirmanteBiometricoBase):
    pass

class FirmanteBiometricoUpdate(BaseModel):
    nombre_completo: Optional[str] = None
    parentesco: Optional[str] = None
    tipo_firmante: Optional[str] = None
    identificacion_oficial: Optional[str] = None
    domicilio: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[str] = None

class FirmanteBiometricoResponse(FirmanteBiometricoBase):
    id: int
    paciente_id: int
    pt_num: Optional[str] = None
    huella_token: Optional[str] = None
    tiene_huella: bool
    estado: str # ACTIVO, INACTIVO_POR_ALTA, REVOCADO
    fecha_registro: datetime
    fecha_inactivacion: Optional[datetime] = None
    sincronizado_vertical: Optional[bool] = True
    biometric_status: str = "SIN_BIOMETRIA"
    requiere_reenrolamiento: bool = False

    class Config:
        from_attributes = True

class VerificarHuellaFirmanteRequest(BaseModel):
    fmd_template: str
    firmante_id: int
    tipo_firmante: Optional[str] = None # Filtro opcional (ej. "PACIENTE", "TESTIGO_1")
    challenge_id: str
    session_id: str

class VerificarHuellaFirmanteResponse(BaseModel):
    is_match: bool
    firmante: Optional[FirmanteBiometricoResponse] = None
    sello_biometrico: Optional[str] = None
    fecha_hora_verificacion: str

class FirmaBiometricaFirmanteInputSchema(BaseModel):
    fmd_template: str
    firmante_id: int
    rol_firmante: Optional[str] = None # Papel elegido para este documento; no modifica el perfil enrolado
    codigo_formato: str
    tipo_documento: str
    evolution_slot: Optional[int] = 0
    challenge_id: str
    session_id: str
    motivo_representacion: Optional[str] = None

class BiometricEnrollmentRequest(BaseModel):
    fmd_template: str
    challenge_id: str
    session_id: str
    motivo: Optional[str] = None


class FirmaBiometricaEspecialInputSchema(BaseModel):
    fmd_template: str
    usuario_firmante_id: int
    rol_firmante: Optional[str] = None
    codigo_formato: str
    tipo_documento: str
    evolution_slot: int = 0
    challenge_id: str
    session_id: str


# Compatibilidad para clientes antiguos; el endpoint genérico usa el esquema nuevo.
FirmaBiometricaBancoSangreInputSchema = FirmaBiometricaEspecialInputSchema


class FEAKeyRotationRequest(BaseModel):
    fmd_template: str
    challenge_id: str
    session_id: str
    motivo: str

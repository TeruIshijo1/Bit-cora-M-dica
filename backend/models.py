from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    ForeignKey,
    Integer,
    String,
    DateTime,
    Text,
    Index,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
import datetime
import uuid

from database import Base

class CatalogoArea(Base):
    __tablename__ = "catalogo_areas"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, unique=True, index=True)
    activo = Column(Boolean, default=True)

class CatalogoTipoAtencion(Base):
    __tablename__ = "catalogo_tipos_atencion"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, unique=True, index=True)
    activo = Column(Boolean, default=True)

class Cama(Base):
    __tablename__ = "camas"
    id = Column(Integer, primary_key=True, index=True)
    numero_cama = Column(String, unique=True, index=True)
    area = Column(String, index=True)
    estado = Column(String, default="DISPONIBLE") # OCUPADA, DISPONIBLE, MANTENIMIENTO, BLOQUEADA
    estado_limpieza = Column(String, default="Limpia")
    notas_limpieza = Column(String, nullable=True)
    activo = Column(Boolean, default=True)

class CatalogoFormato(Base):
    __tablename__ = "catalogo_formatos"

    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String, index=True, nullable=False)
    nombre = Column(String, nullable=False)
    activo = Column(Boolean, default=True)

class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    nombre_completo = Column(String, nullable=True)
    password_hash = Column(String)
    rol = Column(String, default="enfermeria") # enfermeria, admin, rh, sistemas, trabajo_social
    activo = Column(Boolean, default=True)
    must_change_password = Column(Boolean, default=False, nullable=False)
    permisos_modulos = Column(Text, nullable=True) # JSON object (ej. {"camas": "escritura", "agenda": "lectura"})
    formatos_permitidos = Column(Text, nullable=True) # JSON list (ej. ["HE-DIRMED-SINPRO-PLT-87/01"])
    
    atenciones_creadas = relationship("AtencionMedica", back_populates="creador")

class Medico(Base):
    __tablename__ = "medicos"

    id = Column(Integer, primary_key=True, index=True)
    numero_empleado = Column(String, unique=True, index=True)
    nombre_completo = Column(String, index=True)
    especialidad = Column(String)
    cedula = Column(String)
    huella_token = Column(String, unique=True, index=True)
    fmd_template = Column(Text, nullable=True) # Sólo plantilla FMD; nunca imagen RAW
    biometric_status = Column(String(32), default="SIN_BIOMETRIA", nullable=False, index=True)
    template_format = Column(String(32), nullable=True)
    template_version = Column(Integer, nullable=True)
    fecha_enrolamiento = Column(DateTime, nullable=True)
    requiere_reenrolamiento = Column(Boolean, default=False, nullable=False)
    requiere_actualizacion_fea = Column(Boolean, default=False, nullable=False)
    biometric_reenrolled_by_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    biometric_reenrolled_at = Column(DateTime, nullable=True)
    foto_url = Column(String, nullable=True) # Foto perfil estetica
    activo_status = Column(Boolean, default=True)
    bajo_contrato = Column(Boolean, default=False)
    horario_laboral = Column(String, nullable=True) # JSON string
    es_ayudante = Column(Boolean, default=False)
    medico_asignado_id = Column(Integer, ForeignKey("medicos.id"), nullable=True)
    
    # Asymmetric Keys (FEA - NOM-004)
    public_key_pem = Column(Text, nullable=True) # ECDSA Public Key (SECP256R1)
    private_key_enc = Column(Text, nullable=True) # ECDSA Private Key (Encrypted with Fernet KEK)
    private_key_cipher_version = Column(String(64), nullable=True)
    
    formatos_permitidos = Column(Text, nullable=True) # JSON list of formats allowed to fill
    
    medico_asignado = relationship("Medico", remote_side=[id])
    
    @property
    def tiene_huella(self) -> bool:
        return bool(self.fmd_template and self.biometric_status == "FMD_VALIDO")
    
    atenciones = relationship("AtencionMedica", back_populates="medico")
    historial_llaves = relationship("HistorialLlaveFEA", back_populates="medico", order_by="HistorialLlaveFEA.fecha_creacion.desc()")

class HistorialLlaveFEA(Base):
    __tablename__ = "historial_llaves_fea"

    id = Column(Integer, primary_key=True, index=True)
    key_id = Column(String(64), unique=True, index=True, nullable=False)
    medico_id = Column(Integer, ForeignKey("medicos.id"), index=True, nullable=False)
    public_key_pem = Column(Text, nullable=False)
    fecha_creacion = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    fecha_inactivacion = Column(DateTime, nullable=True)
    activo = Column(Boolean, default=True)
    estado = Column(String(32), default="ACTIVA", nullable=False)

    medico = relationship("Medico", back_populates="historial_llaves")

    __table_args__ = (
        Index(
            "uq_historial_llaves_fea_unica_activa",
            "medico_id",
            unique=True,
            postgresql_where=text("activo IS TRUE"),
        ),
    )

class Paciente(Base):
    __tablename__ = "pacientes"

    id = Column(Integer, primary_key=True, index=True)
    nombre_completo = Column(String, index=True)
    num_habitacion = Column(String, index=True)
    area_hospitalaria = Column(String, nullable=True)
    codigo_barras = Column(String, index=True, nullable=True)
    status_ingreso = Column(String, default="Ingresado")
    fecha_registro = Column(DateTime, default=datetime.datetime.utcnow)
    creado_por_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    dado_de_alta_por_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    fecha_alta = Column(DateTime, nullable=True)
    registrado_por_nombre = Column(String, nullable=True)
    
    creador = relationship("Usuario", foreign_keys=[creado_por_id])
    dado_de_alta_por = relationship("Usuario", foreign_keys=[dado_de_alta_por_id])
    atenciones = relationship("AtencionMedica", back_populates="paciente")
    firmantes_biometricos = relationship("BiometriaFirmanteEpisodio", back_populates="paciente", cascade="all, delete-orphan")

class BiometriaFirmanteEpisodio(Base):
    """
    Registro biométrico dactilar temporal de pacientes, familiares/representantes legales y testigos.
    Aislado del catálogo de médicos. Se destruye/inactiva automáticamente al alta del paciente (LFPDPPP).
    """
    __tablename__ = "biometria_firmantes_episodio"

    id = Column(Integer, primary_key=True, index=True)
    paciente_id = Column(Integer, ForeignKey("pacientes.id"), index=True, nullable=False)
    pt_num = Column(String(50), index=True, nullable=True) # Folio / MRN / Expediente
    tipo_firmante = Column(String(50), default="PACIENTE", index=True) # PACIENTE, REPRESENTANTE_LEGAL, TESTIGO_1, TESTIGO_2
    nombre_completo = Column(String(255), index=True, nullable=False)
    parentesco = Column(String(100), default="Titular") # Titular, Hijo(a), Padre/Madre, Cónyuge, Familiar, etc.
    identificacion_oficial = Column(String(100), nullable=True) # INE, Pasaporte, Cédula
    domicilio = Column(Text, nullable=True) # Requisito formal NOM-004 para testigos
    telefono = Column(String(50), nullable=True)
    email = Column(String(100), nullable=True)
    
    # Material biométrico temporal
    fmd_template = Column(Text, nullable=True) # Sólo plantilla ANSI 378; se purga a NULL al alta
    huella_token = Column(String(100), unique=True, index=True, nullable=True)
    biometric_status = Column(String(32), default="SIN_BIOMETRIA", nullable=False, index=True)
    template_format = Column(String(32), nullable=True)
    template_version = Column(Integer, nullable=True)
    fecha_enrolamiento = Column(DateTime, nullable=True)
    requiere_reenrolamiento = Column(Boolean, default=False, nullable=False)
    
    # Ciclo de vida y auditoría
    estado = Column(String(50), default="ACTIVO", index=True) # ACTIVO, INACTIVO_POR_ALTA, REVOCADO
    fecha_registro = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    fecha_inactivacion = Column(DateTime, nullable=True)
    inactivado_por_usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)

    paciente = relationship("Paciente", back_populates="firmantes_biometricos")
    inactivado_por = relationship("Usuario", foreign_keys=[inactivado_por_usuario_id])

    @property
    def tiene_huella(self) -> bool:
        return bool(
            self.fmd_template
            and self.estado == "ACTIVO"
            and self.biometric_status == "FMD_VALIDO"
        )


class BiometricChallenge(Base):
    """Challenge biométrico compartido entre workers y consumido atómicamente."""

    __tablename__ = "biometric_challenges"

    id = Column(Integer, primary_key=True, index=True)
    token_hash = Column(String(64), unique=True, nullable=False)
    action = Column(String(64), nullable=False, index=True)
    session_id = Column(String(128), nullable=False, index=True)
    subject_ref = Column(String(128), nullable=True, index=True)
    expected_identity_ref = Column(String(128), nullable=True, index=True)
    patient_ref = Column(String(128), nullable=True, index=True)
    document_code = Column(String(128), nullable=True)
    document_ref = Column(String(128), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False, index=True)
    consumed_at = Column(DateTime, nullable=True, index=True)
    acquisition_id = Column(String(128), nullable=True, unique=True, index=True)

class AtencionMedica(Base):
    __tablename__ = "atenciones_medicas"

    folio = Column(String, primary_key=True, index=True)
    fecha_registro = Column(DateTime, default=datetime.datetime.utcnow)
    fecha_realizacion = Column(DateTime)
    
    creado_por_id = Column(Integer, ForeignKey("usuarios.id"))
    medico_id = Column(Integer, ForeignKey("medicos.id"))
    paciente_id = Column(Integer, ForeignKey("pacientes.id"))
    
    area_hospitalaria = Column(String) 
    tipo_atencion = Column(String) 
    nombre_procedimiento = Column(String)
    habitacion_capturada = Column(String)
    procedimiento_detalle = Column(Text)
    
    fecha_firma = Column(DateTime, nullable=True)
    hash_seguridad = Column(String, nullable=True)
    ruta_archivo_firmado = Column(String, nullable=True)
    estatus_pago = Column(String, default="Pendiente de Firma") # Pendiente de Firma, Validado para Pago, Resguardado
    reaperturado = Column(Boolean, default=False)
    registrado_por_nombre = Column(String, nullable=True)

    @property
    def is_caducado(self):
        if self.reaperturado:
            return False
        hoy = datetime.date.today()
        # Si la fecha de realizacion o registro es anterior a hoy, caduca.
        fecha_eval = self.fecha_realizacion.date() if self.fecha_realizacion else self.fecha_registro.date()
        return fecha_eval < hoy

    creador = relationship("Usuario", back_populates="atenciones_creadas", foreign_keys=[creado_por_id])
    medico = relationship("Medico", back_populates="atenciones")
    paciente = relationship("Paciente", back_populates="atenciones")
    notas = relationship("NotaEnfermeria", back_populates="atencion", cascade="all, delete")

    __table_args__ = (
        Index("idx_atenciones_med_fecha_pago", "medico_id", "fecha_realizacion", "estatus_pago"),
    )

class NotaEnfermeria(Base):
    __tablename__ = "notas_enfermeria"

    id = Column(Integer, primary_key=True, index=True)
    atencion_folio = Column(String, ForeignKey("atenciones_medicas.folio"))
    nota = Column(Text)
    creada_por_id = Column(Integer, ForeignKey("usuarios.id"))
    fecha_creacion = Column(DateTime, default=datetime.datetime.utcnow)

    atencion = relationship("AtencionMedica", back_populates="notas")
    creador = relationship("Usuario")

class EscaneoRH(Base):
    __tablename__ = "escaneos_rh"

    id = Column(Integer, primary_key=True, index=True)
    titulo = Column(String, index=True)
    nombre_archivo = Column(String)
    ruta_archivo = Column(String)
    fecha_subida = Column(DateTime, default=datetime.datetime.utcnow)
    subido_por_id = Column(Integer, ForeignKey("usuarios.id"))
    
    subido_por = relationship("Usuario")

class TrasladoPaciente(Base):
    __tablename__ = "traslados_pacientes"

    id = Column(Integer, primary_key=True, index=True)
    paciente_id = Column(Integer, ForeignKey("pacientes.id"))
    origen_area = Column(String, nullable=True)
    origen_habitacion = Column(String, nullable=True)
    destino_area = Column(String, nullable=True)
    destino_habitacion = Column(String, nullable=True)
    fecha_traslado = Column(DateTime, default=datetime.datetime.utcnow)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))

    paciente = relationship("Paciente")
    usuario = relationship("Usuario")

class AuditoriaLog(Base):
    __tablename__ = "auditoria_logs"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    accion = Column(String, nullable=False)
    detalles_json = Column(Text, nullable=True)
    fecha_hora = Column(DateTime, default=datetime.datetime.utcnow)
    ip_origen = Column(String, nullable=True)
    request_id = Column(String(128), nullable=False, index=True)
    operation_id = Column(String(128), nullable=True, index=True)
    actor_real = Column(String(255), nullable=False)
    actor_effective = Column(String(255), nullable=False)
    motivo_impersonacion = Column(String(500), nullable=True)
    resultado = Column(String(32), nullable=False, default="EXITO")

    usuario = relationship("Usuario")


class RevokedToken(Base):
    __tablename__ = "revoked_tokens"

    jti = Column(String(64), primary_key=True)
    subject = Column(String(255), nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    revoked_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.datetime.now(datetime.timezone.utc))
    reason = Column(String(255), nullable=False, default="LOGOUT")
    revoked_by = Column(String(255), nullable=True)

class ProcedimientoFrecuente(Base):
    __tablename__ = "procedimientos_frecuentes"

    id = Column(Integer, primary_key=True, index=True)
    medico_id = Column(Integer, ForeignKey("medicos.id"), index=True)
    nombre_procedimiento = Column(String)
    frecuencia = Column(Integer, default=1)

    medico = relationship("Medico")

class CitaMedica(Base):
    __tablename__ = "citas_medicas"

    id = Column(Integer, primary_key=True, index=True)
    medico_id = Column(Integer, ForeignKey("medicos.id"), index=True, nullable=True)
    paciente_id = Column(Integer, ForeignKey("pacientes.id"), index=True, nullable=True)
    nombre_paciente_manual = Column(String, nullable=True)
    fecha_hora = Column(DateTime, index=True)
    motivo = Column(String)
    lugar = Column(String, default="Consultorio - Consulta Externa")
    estatus = Column(String, default="Programada") # Programada, Completada, Cancelada
    notas = Column(Text, nullable=True)
    fecha_creacion = Column(DateTime, default=datetime.datetime.utcnow)

    medico = relationship("Medico")
    paciente = relationship("Paciente")

class FirmaDocumentoClinico(Base):
    __tablename__ = "firmas_documentos_clinicos"

    id = Column(Integer, primary_key=True, index=True)
    tipo_documento = Column(String, index=True) # "Nota de Evolución de Urgencias (87/01)", "Consentimiento Informado", etc.
    codigo_formato = Column(String, index=True) # "HE-DIRMED-SINPRO-PLT-87/01"
    pt_num = Column(String, index=True)
    expediente = Column(String, index=True)
    evolution_slot = Column(Integer, nullable=True) # 1, 2, 3 o None
    rol_firmante = Column(String, default="MEDICO", index=True) # "MEDICO", "PACIENTE", "REPRESENTANTE_LEGAL", "TESTIGO_1", "TESTIGO_2"
    firmante_id = Column(Integer, ForeignKey("biometria_firmantes_episodio.id"), nullable=True)
    medico_id = Column(Integer, ForeignKey("medicos.id"), index=True, nullable=True)
    nombre_medico = Column(String)
    cedula_profesional = Column(String)
    fecha_hora_firma = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    metodo_autenticacion = Column(String, default="Biometría Dactilar DigitalPersona (NOM-004/NOM-024-SSA3)")
    hash_sha256 = Column(String)
    sello_digital = Column(Text)
    cadena_original = Column(Text)
    ip_origen = Column(String, nullable=True)
    tsa_token = Column(Text, nullable=True) # Token RFC 3161 de Autoridad de Sellado de Tiempo (base64)
    key_id = Column(String(64), ForeignKey("historial_llaves_fea.key_id"), nullable=True, index=True)
    signature_schema_version = Column(String(32), default="LEGACY_V1", nullable=False, index=True)
    canonical_payload = Column(Text, nullable=True)
    payload_hash = Column(String(64), nullable=True)
    document_version = Column(String(128), nullable=True)
    pdf_hash = Column(String(64), nullable=True)
    pdf_identifier = Column(String(255), nullable=True)
    tsa_status = Column(String(32), default="SIN_TSA", nullable=False, index=True)
    tsa_nonce = Column(String(128), nullable=True)
    tsa_attempts = Column(Integer, default=0, nullable=False)
    tsa_last_error = Column(Text, nullable=True)
    tsa_verified_at = Column(DateTime, nullable=True)
    clinical_sync_operation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("clinical_sync_operations.operation_id"),
        nullable=True,
        unique=True,
        index=True,
    )
    
    # AUDITORÍA FORENSE Y NO-ELIMINACIÓN (NOM-024-SSA3-2012)
    estado = Column(String, default="ACTIVA", index=True) # ACTIVA, REVOCADA, HISTORICA
    fecha_revocacion = Column(DateTime, nullable=True)
    motivo_revocacion = Column(String, nullable=True)
    version = Column(Integer, default=1)

    medico = relationship("Medico")

    __table_args__ = (
        Index("idx_firmas_pt_formato_slot_estado", "pt_num", "codigo_formato", "evolution_slot", "estado"),
        Index(
            "uq_firma_documento_activa_logica",
            text("COALESCE(pt_num, '')"),
            text("COALESCE(codigo_formato, '')"),
            text("COALESCE(evolution_slot, -1)"),
            text("COALESCE(rol_firmante, 'MEDICO')"),
            text("COALESCE(document_version, '')"),
            unique=True,
            postgresql_where=text("estado = 'ACTIVA'"),
        ),
    )

class HistoricoNotaClinica(Base):
    """
    Registro inmutable de versiones de notas clínicas (Append-Only Ledger) conforme a la NOM-024.
    Ningún registro clínico se destruye; toda edición o cancelación genera una nueva versión auditable.
    """
    __tablename__ = "historico_notas_clinicas"

    id = Column(Integer, primary_key=True, index=True)
    codigo_formato = Column(String, index=True)
    tipo_documento = Column(String)
    pt_num = Column(String, index=True)
    expediente = Column(String, index=True)
    evolution_slot = Column(Integer, nullable=True)
    medico_id = Column(Integer, ForeignKey("medicos.id"), nullable=True)
    nombre_medico = Column(String)
    cedula_profesional = Column(String)
    contenido_soap_json = Column(Text) # Respaldo completo de S, O, A, P, Signos Vitales
    accion = Column(String, default="EDICION") # CREACION, EDICION, REVOCACION
    motivo = Column(String, nullable=True)
    fecha_registro = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    ip_origen = Column(String, nullable=True)
    version = Column(Integer, default=1)
    clinical_sync_operation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("clinical_sync_operations.operation_id"),
        nullable=True,
        unique=True,
        index=True,
    )

    medico = relationship("Medico")

    __table_args__ = (
        Index("idx_historico_pt_formato_fecha", "pt_num", "codigo_formato", "fecha_registro"),
    )


class DietaCuidadosPrescripcion(Base):
    """
    Registro clínico enriquecido de régimen dietético y plan de cuidados de enfermería (Bitácora HES / PostgreSQL).
    """
    __tablename__ = "dieta_cuidados_prescripciones"

    id = Column(Integer, primary_key=True, index=True)
    pt_num = Column(String(50), index=True, nullable=False)
    expediente = Column(String(50), nullable=True)
    tipo_dieta = Column(String(100), nullable=False)
    horario = Column(String(50), nullable=True, default="Continuo")
    fase_clinica = Column(String(255), nullable=True)
    indicaciones_nutricionales = Column(Text, nullable=True)
    inicio_ayuno_dieta = Column(String(100), nullable=True)
    nutriologo_responsable = Column(String(255), nullable=True)
    alergias_alimentarias = Column(String(255), nullable=True)
    tolerancia_via_oral = Column(String(255), nullable=True)
    cuidados_enfermeria_json = Column(Text, nullable=True) # JSON array de cuidados
    medico_id = Column(Integer, ForeignKey("medicos.id"), nullable=True)
    medico_nombre = Column(String(255), nullable=True)
    medico_cedula = Column(String(100), nullable=True)
    hash_sha256 = Column(String(64), nullable=True)
    sello_digital = Column(Text, nullable=True)
    cadena_original = Column(Text, nullable=True)
    fecha_hora_prescripcion = Column(DateTime, default=datetime.datetime.now, index=True)
    activo = Column(Boolean, default=True)
    clinical_sync_operation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("clinical_sync_operations.operation_id"),
        nullable=True,
        unique=True,
        index=True,
    )

    medico = relationship("Medico")


class ClinicalSyncOperation(Base):
    """Durable intent for one PostgreSQL -> SQL Server/Vertical clinical write."""

    __tablename__ = "clinical_sync_operations"

    operation_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    idempotency_key = Column(String(255), nullable=False, unique=True)
    operation_type = Column(String(80), nullable=False, index=True)
    aggregate_type = Column(String(80), nullable=False)
    aggregate_id = Column(String(255), nullable=False, index=True)
    patient_ref = Column(String(80), nullable=True, index=True)
    payload = Column(JSONB, nullable=False, default=dict)
    request_fingerprint = Column(String(64), nullable=False)
    state = Column(String(32), nullable=False, default="PENDING", index=True)
    attempts = Column(Integer, nullable=False, default=0)
    max_attempts = Column(Integer, nullable=False, default=5)
    last_error = Column(Text, nullable=True)
    local_applied_at = Column(DateTime(timezone=True), nullable=True)
    external_applied_at = Column(DateTime(timezone=True), nullable=True)
    next_attempt_at = Column(DateTime(timezone=True), nullable=True, index=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        onupdate=lambda: datetime.datetime.now(datetime.timezone.utc),
    )
    completed_at = Column(DateTime(timezone=True), nullable=True)

    attempts_log = relationship(
        "ClinicalSyncAttempt",
        back_populates="operation",
        cascade="all, delete-orphan",
        order_by="ClinicalSyncAttempt.attempt_number",
    )

    __table_args__ = (
        CheckConstraint(
            "state IN ('PENDING','PROCESSING','SYNCED','RETRYABLE_ERROR','FAILED','REQUIRES_RECONCILIATION')",
            name="ck_clinical_sync_operation_state",
        ),
        Index(
            "idx_clinical_sync_reconciliation",
            "state",
            "next_attempt_at",
            "created_at",
        ),
    )


class ClinicalSyncAttempt(Base):
    """Append-only evidence for every delivery/reconciliation attempt."""

    __tablename__ = "clinical_sync_attempts"

    id = Column(Integer, primary_key=True)
    operation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("clinical_sync_operations.operation_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    attempt_number = Column(Integer, nullable=False)
    outcome = Column(String(32), nullable=False)
    error_class = Column(String(120), nullable=True)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=False)
    finished_at = Column(DateTime(timezone=True), nullable=False)

    operation = relationship("ClinicalSyncOperation", back_populates="attempts_log")

    __table_args__ = (
        UniqueConstraint(
            "operation_id",
            "attempt_number",
            name="uq_clinical_sync_attempt_number",
        ),
    )


class DocumentoVerificacionQR(Base):
    """
    Registro universal de documentos generados para verificación y apertura directa por QR (NOM-024-SSA3-2012).
    Permite abrir exactamente el archivo generado sin depender de heurísticas o búsquedas de texto.
    """
    __tablename__ = "documentos_verificacion_qr"

    id = Column(Integer, primary_key=True, index=True)
    doc_uuid = Column(String(128), unique=True, index=True, nullable=False) # Identificador único del documento
    pt_num = Column(String(50), index=True, nullable=False)
    expediente = Column(String(50), nullable=True)
    codigo_formato = Column(String(100), index=True, nullable=False)
    tipo_documento = Column(String(255), nullable=True)
    slot = Column(Integer, nullable=True, default=1)
    pdf_path = Column(Text, nullable=False) # Ruta física absoluta en disco del PDF generado
    pdf_filename = Column(String(255), nullable=True)
    hash_sha256 = Column(String(64), nullable=True)
    fecha_generacion = Column(DateTime, default=datetime.datetime.now, index=True)
    medico_nombre = Column(String(255), nullable=True)
    medico_cedula = Column(String(100), nullable=True)
    activo = Column(Boolean, default=True)

    __table_args__ = (
        Index("idx_doc_qr_pt_formato_slot", "pt_num", "codigo_formato", "slot"),
    )

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, DateTime, Text
from sqlalchemy.orm import relationship
import datetime

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

class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)
    rol = Column(String, default="enfermeria") # enfermeria, admin, rh
    activo = Column(Boolean, default=True)
    
    atenciones_creadas = relationship("AtencionMedica", back_populates="creador")

class Medico(Base):
    __tablename__ = "medicos"

    id = Column(Integer, primary_key=True, index=True)
    numero_empleado = Column(String, unique=True, index=True)
    nombre_completo = Column(String, index=True)
    especialidad = Column(String)
    cedula = Column(String)
    huella_token = Column(String, unique=True, index=True)
    fmd_template = Column(String) # Store FMD Base64 string for DigitalPersona
    foto_url = Column(String, nullable=True) # Foto perfil estetica
    activo_status = Column(Boolean, default=True)
    
    atenciones = relationship("AtencionMedica", back_populates="medico")

class Paciente(Base):
    __tablename__ = "pacientes"

    id = Column(Integer, primary_key=True, index=True)
    nombre_completo = Column(String, index=True)
    num_habitacion = Column(String, index=True)
    area_hospitalaria = Column(String, nullable=True)
    status_ingreso = Column(String, default="Ingresado")
    fecha_registro = Column(DateTime, default=datetime.datetime.utcnow)
    creado_por_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    
    creador = relationship("Usuario")
    atenciones = relationship("AtencionMedica", back_populates="paciente")

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

    creador = relationship("Usuario", back_populates="atenciones_creadas")
    medico = relationship("Medico", back_populates="atenciones")
    paciente = relationship("Paciente", back_populates="atenciones")

class EscaneoRH(Base):
    __tablename__ = "escaneos_rh"

    id = Column(Integer, primary_key=True, index=True)
    titulo = Column(String, index=True)
    nombre_archivo = Column(String)
    ruta_archivo = Column(String)
    fecha_subida = Column(DateTime, default=datetime.datetime.utcnow)
    subido_por_id = Column(Integer, ForeignKey("usuarios.id"))
    
    subido_por = relationship("Usuario")

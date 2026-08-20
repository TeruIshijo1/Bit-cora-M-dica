from sqlalchemy.orm import Session
from database import SessionLocal, engine, Base
import models
from passlib.context import CryptContext
import datetime

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password):
    return pwd_context.hash(password)

def seed_database():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # 1. Usuarios Base
        usuarios_data = [
            ("amendoza", "Alberto García Mendoza", "Teru1823-", "admin"),
            ("rh_user", "Recursos Humanos 1", "rh123", "rh"),
            ("enfermera1", "Enfermera Principal", "enf123", "enfermeria"),
            ("jose_prueba", "JOSE JOSE PRUEBA ENRIQUEZ", "password123", "medico")
        ]
        for uname, nombre, pwd, rol in usuarios_data:
            user = db.query(models.Usuario).filter(models.Usuario.username == uname).first()
            if not user:
                db.add(models.Usuario(username=uname, nombre_completo=nombre, password_hash=get_password_hash(pwd), rol=rol))
            else:
                if not user.nombre_completo:
                    user.nombre_completo = nombre
                if not user.password_hash.startswith("$2b$"):
                    user.password_hash = get_password_hash(pwd)
        
        # 2. Médicos (incluyendo JOSE JOSE PRUEBA ENRIQUEZ)
        medico_prueba = db.query(models.Medico).filter(models.Medico.nombre_completo.ilike("%JOSE JOSE PRUEBA%")).first()
        if not medico_prueba:
            medico_prueba = models.Medico(
                numero_empleado="MED-PRUEBA-01",
                nombre_completo="JOSE JOSE PRUEBA ENRIQUEZ",
                especialidad="Medicina de Urgencias / Cirugía General",
                cedula="PRUEBA-99281",
                huella_token=None,
                fmd_template=None,
                activo_status=True,
                bajo_contrato=True,
                horario_laboral="Lunes a Viernes 08:00 - 16:00"
            )
            db.add(medico_prueba)
            db.flush()

        # Medico Dr. Alejandro Mendoza si no existe
        medico_mendoza = db.query(models.Medico).filter(models.Medico.nombre_completo.ilike("%ALEJANDRO MENDOZA%")).first()
        if not medico_mendoza:
            medico_mendoza = models.Medico(
                numero_empleado="MED-00124",
                nombre_completo="DR. ALEJANDRO MENDOZA RIVERA",
                especialidad="Medicina de Urgencias",
                cedula="12345678",
                huella_token="TOKEN-MENDOZA-12345",
                fmd_template="MOCK_FMD_MENDOZA",
                activo_status=True,
                bajo_contrato=True
            )
            db.add(medico_mendoza)
            db.flush()

        # 3. Camas (incluyendo Cama Virtual para COMODIN COMODIN COMODIN)
        cama_virtual = db.query(models.Cama).filter(models.Cama.numero_cama == "CAMA URGENCIAS 1 (VIRTUAL)").first()
        if not cama_virtual:
            db.add(models.Cama(
                numero_cama="CAMA URGENCIAS 1 (VIRTUAL)",
                area="Urgencias",
                estado="OCUPADA",
                estado_limpieza="Limpia",
                activo=True
            ))

        # 4. Pacientes base
        p_comodin = db.query(models.Paciente).filter(models.Paciente.nombre_completo.ilike("%COMODIN%")).first()
        if not p_comodin:
            p_comodin = models.Paciente(
                id=5704,
                nombre_completo="COMODIN COMODIN COMODIN",
                num_habitacion="CAMA URGENCIAS 1 (VIRTUAL)",
                area_hospitalaria="Urgencias",
                codigo_barras="PT-5704",
                status_ingreso="Ingresado",
                fecha_registro=datetime.datetime.now()
            )
            db.add(p_comodin)
            db.flush()

        # 5. Citas de prueba para la agenda
        if db.query(models.CitaMedica).count() == 0:
            ahora = datetime.datetime.now()
            db.add_all([
                models.CitaMedica(
                    medico_id=medico_prueba.id if medico_prueba else None,
                    paciente_id=p_comodin.id if p_comodin else None,
                    nombre_paciente_manual="COMODIN COMODIN COMODIN (PT-5704)",
                    fecha_hora=ahora + datetime.timedelta(days=1, hours=2),
                    motivo="Revaloración Clínica y Seguimiento en Urgencias",
                    lugar="Consultorio 12 - Consulta Externa",
                    estatus="Programada",
                    notas="Verificar resultados de USG abdominal y tolerancia a vía oral."
                ),
                models.CitaMedica(
                    medico_id=medico_prueba.id if medico_prueba else None,
                    paciente_id=None,
                    nombre_paciente_manual="GABRIELA HERNÁNDEZ SOTO",
                    fecha_hora=ahora + datetime.timedelta(days=1, hours=4),
                    motivo="Consulta de Primera Vez - Valoración Quirúrgica",
                    lugar="Consultorio 12 - Consulta Externa",
                    estatus="Programada",
                    notas="Paciente enviada de Triage para valoración de colecistectomía."
                ),
                models.CitaMedica(
                    medico_id=medico_prueba.id if medico_prueba else None,
                    paciente_id=None,
                    nombre_paciente_manual="ROBERTO VALENCIA RUIZ",
                    fecha_hora=ahora + datetime.timedelta(days=2, hours=1),
                    motivo="Control Postoperatorio Semana 2",
                    lugar="Consultorio 12 - Consulta Externa",
                    estatus="Programada",
                    notas="Retiro de puntos y alta definitiva."
                )
            ])

        # 6. Catalogos Area
        if db.query(models.CatalogoArea).count() == 0:
            areas = ["Hospitalización", "Privados Planta Alta (PPA)", "Privados Planta Baja (PPB)", "Terapia Intensiva", "Urgencias", "Quirófano", "Cuneros", "UCI"]
            for a in areas:
                db.add(models.CatalogoArea(nombre=a))

        # 7. Catalogos Tipo Atencion
        if db.query(models.CatalogoTipoAtencion).count() == 0:
            tipos = [
                "Visita Médica Quirúrgica (Interconsulta)", 
                "Visita Médica Clínica (Jornada)", 
                "Visita Médica Urgencias (Interconsulta)", 
                "Servicio de Anestésia", 
                "Cirugia", 
                "Estudio", 
                "Procedimiento"
            ]
            for t in tipos:
                db.add(models.CatalogoTipoAtencion(nombre=t))

        db.commit()
        print("Datos base y Medico de Pruebas sembrados con éxito.")
        
    except Exception as e:
        print(f"Error seeding data: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()

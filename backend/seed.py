from sqlalchemy.orm import Session
from database import SessionLocal, engine, Base
import models
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password):
    return pwd_context.hash(password)

def seed_database():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # Check and insert Usuarios
        usuarios_data = [
            ("amendoza", "Teru1823-", "admin"),
            ("rh_user", "rh123", "rh"),
            ("enfermera1", "enf123", "enfermeria")
        ]
        for uname, pwd, rol in usuarios_data:
            user = db.query(models.Usuario).filter(models.Usuario.username == uname).first()
            if not user:
                db.add(models.Usuario(username=uname, password_hash=get_password_hash(pwd), rol=rol))
            else:
                # Si el password_hash no parece bcrypt, lo corregimos
                if not user.password_hash.startswith("$2b$"):
                    user.password_hash = get_password_hash(pwd)
        
        # Pacientes base si no hay ninguno
        if db.query(models.Paciente).count() == 0:
            db.add_all([
                models.Paciente(nombre_completo="Carlos Sánchez", num_habitacion="101A", status_ingreso="Ingresado"),
                models.Paciente(nombre_completo="María López", num_habitacion="203B", status_ingreso="Ingresado"),
                models.Paciente(nombre_completo="Juan Pérez", num_habitacion="Urgencias", status_ingreso="Alta")
            ])

        # Catalogos Area si no hay
        if db.query(models.CatalogoArea).count() == 0:
            areas = ["Hospitalización", "Privados Planta Alta (PPA)", "Privados Planta Baja (PPB)", "Terapia Intensiva", "Urgencias", "Quirófano", "Cuneros", "UCI"]
            for a in areas:
                db.add(models.CatalogoArea(nombre=a))

        # Catalogos Tipo Atencion si no hay
        if db.query(models.CatalogoTipoAtencion).count() == 0:
            tipos = ["Consulta Médica", "Jornada", "Interconsulta", "Servicio de Anestesia"]
            for t in tipos:
                db.add(models.CatalogoTipoAtencion(nombre=t))

        db.commit()
        print("Datos base verificados/insertados con éxito.")
        
    except Exception as e:
        print(f"Error seeding data: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()

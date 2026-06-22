from sqlalchemy.orm import Session
from database import SessionLocal, engine, Base
import models
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password):
    return pwd_context.hash(password)

def seed_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # Usuarios
        usuarios = [
            models.Usuario(username="amendoza", password_hash=get_password_hash("Teru1823-"), rol="admin"),
            models.Usuario(username="rh_user", password_hash=get_password_hash("rh123"), rol="rh"),
            models.Usuario(username="enfermera1", password_hash=get_password_hash("enf123"), rol="enfermeria")
        ]
        db.add_all(usuarios)
        
        # Pacientes
        pacientes = [
            models.Paciente(nombre_completo="Carlos Sánchez", num_habitacion="101A", status_ingreso="Ingresado"),
            models.Paciente(nombre_completo="María López", num_habitacion="203B", status_ingreso="Ingresado"),
            models.Paciente(nombre_completo="Juan Pérez", num_habitacion="Urgencias", status_ingreso="Alta")
        ]
        db.add_all(pacientes)

        # Catalogos
        areas = [
            models.CatalogoArea(nombre="Hospitalización"),
            models.CatalogoArea(nombre="Privados Planta Alta (PPA)"),
            models.CatalogoArea(nombre="Privados Planta Baja (PPB)"),
            models.CatalogoArea(nombre="Terapia Intensiva"),
            models.CatalogoArea(nombre="Urgencias"),
            models.CatalogoArea(nombre="Quirófano"),
            models.CatalogoArea(nombre="Cuneros"),
            models.CatalogoArea(nombre="UCI")
        ]
        db.add_all(areas)

        tipos = [
            models.CatalogoTipoAtencion(nombre="Consulta Médica"),
            models.CatalogoTipoAtencion(nombre="Jornada"),
            models.CatalogoTipoAtencion(nombre="Interconsulta"),
            models.CatalogoTipoAtencion(nombre="Servicio de Anestesia")
        ]
        db.add_all(tipos)

        db.commit()
        print("Base de datos limpia generada con éxito.")
        
    except Exception as e:
        print(f"Error seeding data: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()

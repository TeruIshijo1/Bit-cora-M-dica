import sys
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext

import models
from database import engine, SessionLocal

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def run():
    db = SessionLocal()
    
    # Create RH User
    existing_rh = db.query(models.Usuario).filter(models.Usuario.username == "rh_user").first()
    if not existing_rh:
        rh_user = models.Usuario(
            username="rh_user",
            password_hash=pwd_context.hash("rh123"),
            rol="rh"
        )
        db.add(rh_user)
        
    # Create Nurse User
    existing_enf = db.query(models.Usuario).filter(models.Usuario.username == "enfermera1").first()
    if not existing_enf:
        enf_user = models.Usuario(
            username="enfermera1",
            password_hash=pwd_context.hash("enf123"),
            rol="enfermeria"
        )
        db.add(enf_user)

    db.commit()
    db.close()
    print("Usuarios 'rh_user' (rh123) y 'enfermera1' (enf123) creados exitosamente.")

if __name__ == "__main__":
    run()

from database import get_db, SessionLocal
from models import Usuario
from schemas import PacienteCreate
from main import create_paciente

db = SessionLocal()
user = db.query(Usuario).first()
if user:
    try:
        req = PacienteCreate(
            nombre_completo="Paciente Test",
            num_habitacion="101",
            area_hospitalaria="Hospitalización"
        )
        res = create_paciente(req, db, user)
        print("Success:", res.id)
    except Exception as e:
        print("Error:", repr(e))
else:
    print("No user found")
db.close()

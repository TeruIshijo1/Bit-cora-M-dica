import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))
from backend.database import SessionLocal
from backend.models import Medico

db = SessionLocal()
medicos = db.query(Medico).filter(Medico.bajo_contrato == True).all()

unique_horarios = set()
for m in medicos:
    if m.horario_laboral and not m.horario_laboral.startswith('{'):
        unique_horarios.add(m.horario_laboral)

for h in unique_horarios:
    print(repr(h))

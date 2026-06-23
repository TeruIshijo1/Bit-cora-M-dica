import sys
sys.path.append('.')
from database import SessionLocal
from models import AtencionMedica
from pdf_generator import generate_pdf
import traceback

try:
    db = SessionLocal()
    atenciones = db.query(AtencionMedica).all()
    for atencion in atenciones:
        print("Folio:", atencion.folio)
        print(generate_pdf(atencion, atencion.medico, atencion.paciente))
except Exception as e:
    traceback.print_exc()

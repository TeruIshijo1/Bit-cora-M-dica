import sys
import os

sys.path.append(r"d:\Escritorio\Bitácora HES\backend")
import main
from database import SessionLocal
import models
import datetime

db = SessionLocal()
try:
    # Dummy user
    admin_user = db.query(models.Usuario).filter_by(rol='admin').first() or db.query(models.Usuario).first()
    if not admin_user:
        admin_user = models.Usuario(username="test", rol="admin")

    res = main.exportar_atenciones(db=db, current_user=admin_user)
    print("Success:", res)
except Exception as e:
    import traceback
    traceback.print_exc()
finally:
    db.close()

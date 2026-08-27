from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

import models
import schemas
from database import get_db
from security import require_role

router = APIRouter(prefix="/api/catalogos", tags=["Catálogos"])

@router.get("/areas", response_model=List[schemas.CatalogoResponse])
def get_areas(db: Session = Depends(get_db)):
    return db.query(models.CatalogoArea).filter(models.CatalogoArea.activo == True).all()

@router.post("/areas", response_model=schemas.CatalogoResponse)
def create_area(
    area: schemas.CatalogoBase,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_role(["admin", "rh", "sistemas"]))
):
    nueva_area = models.CatalogoArea(nombre=area.nombre, activo=area.activo)
    db.add(nueva_area)
    db.commit()
    db.refresh(nueva_area)
    return nueva_area

@router.delete("/areas/{id}")
def delete_area(
    id: int,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_role(["admin", "sistemas"]))
):
    area = db.query(models.CatalogoArea).filter(models.CatalogoArea.id == id).first()
    if not area:
        raise HTTPException(status_code=404, detail="Area no encontrada")
    area.activo = False
    db.commit()
    return {"status": "ok", "message": "Area desactivada"}

@router.get("/tipos", response_model=List[schemas.CatalogoResponse])
def get_tipos(db: Session = Depends(get_db)):
    return db.query(models.CatalogoTipoAtencion).filter(models.CatalogoTipoAtencion.activo == True).all()

@router.post("/tipos", response_model=schemas.CatalogoResponse)
def create_tipo(
    tipo: schemas.CatalogoBase,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_role(["admin", "rh", "sistemas"]))
):
    nuevo_tipo = models.CatalogoTipoAtencion(nombre=tipo.nombre, activo=tipo.activo)
    db.add(nuevo_tipo)
    db.commit()
    db.refresh(nuevo_tipo)
    return nuevo_tipo

@router.delete("/tipos/{id}")
def delete_tipo(
    id: int,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_role(["admin", "sistemas"]))
):
    tipo = db.query(models.CatalogoTipoAtencion).filter(models.CatalogoTipoAtencion.id == id).first()
    if not tipo:
        raise HTTPException(status_code=404, detail="Tipo de Atención no encontrado")
    tipo.activo = False
    db.commit()
    return {"status": "ok", "message": "Tipo de atención desactivado"}

@router.get("/formatos", response_model=List[schemas.CatalogoFormatoResponse])
def get_formatos(db: Session = Depends(get_db)):
    return db.query(models.CatalogoFormato).filter(models.CatalogoFormato.activo == True).order_by(models.CatalogoFormato.nombre).all()

@router.post("/formatos", response_model=schemas.CatalogoFormatoResponse)
def create_formato(req: schemas.CatalogoFormatoCreate, db: Session = Depends(get_db)):
    nuevo = models.CatalogoFormato(nombre=req.nombre, codigo=req.codigo, activo=req.activo)
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo

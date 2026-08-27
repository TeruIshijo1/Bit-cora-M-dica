import os
import datetime
from typing import Optional, List
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from dotenv import load_dotenv

import models
from database import get_db

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))
load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("Falta SECRET_KEY en el archivo .env. El sistema no puede iniciar de forma segura.")

ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login/admin")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[datetime.timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.datetime.utcnow() + expires_delta
    else:
        expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        rol: str = payload.get("rol")
        if username is None or rol is None:
            raise HTTPException(status_code=401, detail="Credenciales invalidas")
        
        if rol in ["medico", "ayudante"]:
            user = db.query(models.Medico).filter(models.Medico.cedula == username).first()
            if user:
                setattr(user, "rol", rol)
        else:
            user = db.query(models.Usuario).filter(models.Usuario.username == username).first()
            
        if not user:
            raise HTTPException(status_code=401, detail="Usuario no existe")
            
        return user
    except JWTError:
        raise HTTPException(status_code=401, detail="Credenciales invalidas")

def require_role(allowed_roles: List[str]):
    def role_checker(current_user = Depends(get_current_user)):
        rol = getattr(current_user, "rol", "medico")
        if "admin" not in allowed_roles and rol not in allowed_roles and rol != "admin":
            raise HTTPException(status_code=403, detail="No tienes permisos para esta acción")
        return current_user
    return role_checker

def log_auditoria(db: Session, usuario_id: Optional[int], accion: str, detalles_json: Optional[str] = None):
    try:
        log = models.AuditoriaLog(
            usuario_id=usuario_id,
            accion=accion,
            detalles_json=detalles_json,
            ip_origen=None
        )
        db.add(log)
        db.commit()
    except Exception as e:
        print(f"Error guardando auditoria: {e}")

import os
import datetime
import time
import uuid
from typing import Optional, List
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from dotenv import load_dotenv

import models
from database import get_db
from app_config import load_settings

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))
load_dotenv()

SETTINGS = load_settings()
SECRET_KEY = SETTINGS.secret_key
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = SETTINGS.access_token_minutes
SESSION_IDLE_TIMEOUT_MINUTES = 20

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login/admin")

ROLE_ALIASES = {
    "mantenimiento/limpieza": "limpieza",
}


def normalize_role(role: Optional[str]) -> str:
    """Return the canonical role value used by authorization checks."""
    if not isinstance(role, str):
        return ""
    normalized = role.strip().lower()
    return ROLE_ALIASES.get(normalized, normalized)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[datetime.timedelta] = None) -> str:
    to_encode = data.copy()
    now = datetime.datetime.now(datetime.timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({
        "exp": expire,
        "iat": now,
        "jti": str(uuid.uuid4()),
        "iss": SETTINGS.jwt_issuer,
        "aud": SETTINGS.jwt_audience,
    })
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def authenticate_token(token: str, db: Session):
    """Decode a JWT and revalidate the current identity and active state in DB."""
    try:
        decode_kwargs = {
            "algorithms": [ALGORITHM],
            "audience": SETTINGS.jwt_audience,
            "issuer": SETTINGS.jwt_issuer,
            "options": {
                "require_exp": True,
                "require_sub": True,
                "require_jti": SETTINGS.production,
                "verify_aud": SETTINGS.production or bool(jwt.get_unverified_claims(token).get("aud")),
                "verify_iss": SETTINGS.production or bool(jwt.get_unverified_claims(token).get("iss")),
            },
        }
        payload = jwt.decode(token, SECRET_KEY, **decode_kwargs)
        last_activity = payload.get("last_activity", payload.get("iat", int(time.time())))
        try:
            last_activity = int(last_activity)
        except (TypeError, ValueError):
            raise HTTPException(status_code=401, detail="Sesión expirada por inactividad")
        if time.time() - last_activity >= SESSION_IDLE_TIMEOUT_MINUTES * 60:
            raise HTTPException(status_code=401, detail="Sesión expirada por inactividad")
        username: str = payload.get("sub")
        token_role = normalize_role(payload.get("rol"))
        if not username or not token_role:
            raise HTTPException(status_code=401, detail="Credenciales invalidas")

        if token_role in {"medico", "ayudante"}:
            user = db.query(models.Medico).filter(models.Medico.cedula == username).first()
            if not user:
                raise HTTPException(status_code=401, detail="Usuario no existe")
            if not bool(getattr(user, "activo_status", False)):
                raise HTTPException(status_code=403, detail="Usuario inactivo")
            effective_role = "ayudante" if bool(getattr(user, "es_ayudante", False)) else "medico"
        else:
            user = db.query(models.Usuario).filter(models.Usuario.username == username).first()
            if not user:
                raise HTTPException(status_code=401, detail="Usuario no existe")
            if not bool(getattr(user, "activo", False)):
                raise HTTPException(status_code=403, detail="Usuario inactivo")
            effective_role = normalize_role(getattr(user, "rol", None))

        jti = payload.get("jti")
        if jti and db.query(models.RevokedToken).filter(models.RevokedToken.jti == jti).first():
            raise HTTPException(status_code=401, detail="Sesión revocada")

        # Authorization always uses the live database role, never a stale JWT claim.
        setattr(user, "rol", effective_role)
        setattr(user, "_auth_claims", payload)
        return user
    except JWTError:
        raise HTTPException(status_code=401, detail="Credenciales invalidas")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    return authenticate_token(token, db)

def require_role(allowed_roles: List[str]):
    normalized_allowed = frozenset(normalize_role(role) for role in allowed_roles if normalize_role(role))

    def role_checker(current_user = Depends(get_current_user), request: Request = None):
        if request is not None and getattr(request.state, "permission_authorized", False):
            return current_user
        rol = normalize_role(getattr(current_user, "rol", None))
        if not normalized_allowed or (rol != "admin" and rol not in normalized_allowed):
            raise HTTPException(status_code=403, detail="No tienes permisos para esta acción")
        return current_user
    return role_checker

def log_auditoria(db: Session, usuario_id: Optional[int], accion: str, detalles_json: Optional[str] = None):
    log = models.AuditoriaLog(
        usuario_id=usuario_id,
        accion=accion,
        detalles_json=detalles_json,
        ip_origen=None,
    )
    db.add(log)
    db.flush()

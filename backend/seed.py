"""Explicit development-only seed without embedded credentials or biometrics."""

from __future__ import annotations

from password_policy import valid_password

import argparse
import os

from passlib.context import CryptContext


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def seed_development_catalogs(*, create_admin: bool = False) -> None:
    if os.getenv("APP_ENV", "").strip().lower() != "development":
        raise RuntimeError("El seed sólo puede ejecutarse con APP_ENV=development.")

    from database import SessionLocal
    import models

    with SessionLocal() as db:
        if create_admin:
            username = os.getenv("DEV_SEED_USERNAME", "").strip()
            password = os.getenv("DEV_SEED_PASSWORD", "")
            if not username or not valid_password(password):
                raise RuntimeError("DEV_SEED_USERNAME y DEV_SEED_PASSWORD (mínimo 8 caracteres, mayúscula, minúscula, número y símbolo) son obligatorios.")
            if not db.query(models.Usuario).filter(models.Usuario.username == username).first():
                db.add(models.Usuario(
                    username=username,
                    nombre_completo="Administrador de desarrollo",
                    password_hash=get_password_hash(password),
                    rol="admin",
                    activo=True,
                    must_change_password=True,
                ))

        if db.query(models.CatalogoArea).count() == 0:
            for name in ("Hospitalización", "Urgencias", "Quirófano", "Terapia Intensiva"):
                db.add(models.CatalogoArea(nombre=name))
        if db.query(models.CatalogoTipoAtencion).count() == 0:
            for name in ("Visita médica", "Cirugía", "Estudio", "Procedimiento"):
                db.add(models.CatalogoTipoAtencion(nombre=name))
        db.commit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed explícito y exclusivo de desarrollo")
    parser.add_argument("--confirm-development", action="store_true", required=True)
    parser.add_argument("--create-admin", action="store_true")
    args = parser.parse_args()
    seed_development_catalogs(create_admin=args.create_admin)
    print("Seed de desarrollo completado sin biometría ni credenciales embebidas.")

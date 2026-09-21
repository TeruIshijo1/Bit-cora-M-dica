"""One-time initial administrator bootstrap for a migrated empty database."""

from __future__ import annotations

import argparse
import getpass
import json
import os
import secrets
import string
import uuid


def _generated_password(length: int = 24) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*-_=+"
    while True:
        value = "".join(secrets.choice(alphabet) for _ in range(length))
        if all((any(c.islower() for c in value), any(c.isupper() for c in value), any(c.isdigit() for c in value), any(not c.isalnum() for c in value))):
            return value


def main() -> None:
    parser = argparse.ArgumentParser(description="Bootstrap inicial HES (una sola ejecución)")
    parser.add_argument("--username", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--prompt-password", action="store_true")
    parser.add_argument("--acknowledge-one-time", action="store_true", required=True)
    args = parser.parse_args()

    if os.getenv("APP_ENV", "").strip().lower() != "production":
        raise SystemExit("Bootstrap rechazado: APP_ENV debe ser production.")

    from database import SessionLocal
    from seed import get_password_hash
    import models

    password = getpass.getpass("Contraseña temporal segura: ") if args.prompt_password else _generated_password()
    if len(password) < 14:
        raise SystemExit("La contraseña temporal debe tener al menos 14 caracteres.")

    with SessionLocal() as db:
        if db.query(models.Usuario).count() != 0:
            raise SystemExit("Bootstrap rechazado: la base ya contiene usuarios.")
        user = models.Usuario(
            username=args.username.strip(), nombre_completo=args.name.strip(),
            password_hash=get_password_hash(password), rol="admin", activo=True,
            must_change_password=True,
        )
        db.add(user)
        db.flush()
        db.add(models.AuditoriaLog(
            usuario_id=user.id,
            accion="BOOTSTRAP_ADMIN_INICIAL",
            detalles_json=json.dumps({"username": user.username, "must_change_password": True}),
            request_id=f"bootstrap-{uuid.uuid4()}",
            actor_real="bootstrap:local-console",
            actor_effective=f"admin:{user.id}",
            resultado="EXITO",
        ))
        db.commit()

    print("Administrador inicial creado. La contraseña temporal se mostrará una sola vez:")
    print(password)
    print("El usuario deberá cambiarla antes de usar funciones clínicas.")


if __name__ == "__main__":
    main()

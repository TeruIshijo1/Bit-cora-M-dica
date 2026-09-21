"""Environment-aware configuration validation for the HES API.

Production must fail before the application starts accepting traffic.  Test and
development retain explicit, local defaults so the existing developer workflow
does not become a production deployment by accident.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import urlparse


class ConfigurationError(RuntimeError):
    pass


PLACEHOLDER_FRAGMENTS = (
    "clave_secreta",
    "password",
    "changeme",
    "replace_me",
    "super_segura",
    "synthetic-test",
)


def _csv(name: str, default: str = "") -> tuple[str, ...]:
    return tuple(value.strip() for value in os.getenv(name, default).split(",") if value.strip())


def _secret(name: str, *, production: bool) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ConfigurationError(f"{name} es obligatorio.")
    if production and (len(value) < 32 or any(fragment in value.lower() for fragment in PLACEHOLDER_FRAGMENTS)):
        raise ConfigurationError(f"{name} debe ser aleatorio, no predecible y tener al menos 32 caracteres.")
    return value


@dataclass(frozen=True)
class AppSettings:
    environment: str
    production: bool
    secret_key: str
    jwt_issuer: str
    jwt_audience: str
    access_token_minutes: int
    allowed_origins: tuple[str, ...]
    allowed_hosts: tuple[str, ...]
    proxy_https_enabled: bool
    private_storage_root: str


def load_settings() -> AppSettings:
    environment = os.getenv("APP_ENV", "development").strip().lower()
    if environment not in {"development", "test", "production"}:
        raise ConfigurationError("APP_ENV debe ser development, test o production.")
    production = environment == "production"

    secret_key = _secret("SECRET_KEY", production=production)
    access_token_minutes = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15" if production else "480"))
    if access_token_minutes < 1 or (production and access_token_minutes > 30):
        raise ConfigurationError("ACCESS_TOKEN_EXPIRE_MINUTES debe estar entre 1 y 30 en producción.")

    origins = _csv(
        "ALLOWED_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173" if not production else "",
    )
    hosts = _csv("ALLOWED_HOSTS", "localhost,127.0.0.1,testserver" if not production else "")
    proxy_https_enabled = os.getenv("PROXY_HTTPS_ENABLED", "false").strip().lower() == "true"

    if production:
        for required_secret in ("HES_HMAC_SECRET", "BIOMETRIC_ATTESTATION_SECRET"):
            _secret(required_secret, production=True)
        database_url = os.getenv("DATABASE_URL", "")
        if not database_url.startswith(("postgresql://", "postgresql+psycopg2://")):
            raise ConfigurationError("DATABASE_URL de producción debe apuntar explícitamente a PostgreSQL.")
        if not origins or "*" in origins or any(urlparse(origin).scheme != "https" for origin in origins):
            raise ConfigurationError("ALLOWED_ORIGINS debe contener sólo orígenes HTTPS explícitos en producción.")
        if not hosts or "*" in hosts:
            raise ConfigurationError("ALLOWED_HOSTS debe ser una allowlist explícita sin '*'.")
        if not proxy_https_enabled:
            raise ConfigurationError("PROXY_HTTPS_ENABLED=true es obligatorio detrás del proxy TLS de producción.")
        tsa_url = os.getenv("TSA_URL", "").strip()
        if tsa_url and not os.getenv("TSA_TRUST_STORE", "").strip():
            raise ConfigurationError("TSA_TRUST_STORE es obligatorio cuando TSA_URL está configurada.")

    storage_root = os.getenv(
        "PRIVATE_STORAGE_ROOT",
        os.path.join(os.path.dirname(__file__), "private_storage"),
    )
    return AppSettings(
        environment=environment,
        production=production,
        secret_key=secret_key,
        jwt_issuer=os.getenv("JWT_ISSUER", "hes-api").strip() or "hes-api",
        jwt_audience=os.getenv("JWT_AUDIENCE", "hes-clinical-clients").strip() or "hes-clinical-clients",
        access_token_minutes=access_token_minutes,
        allowed_origins=origins,
        allowed_hosts=hosts,
        proxy_https_enabled=proxy_https_enabled,
        private_storage_root=os.path.realpath(storage_root),
    )

"""Request-scoped QR metadata shared by every ReportLab PDF engine.

The engines intentionally know nothing about FastAPI, database sessions or
patient routing.  An explicit PDF preparation endpoint sets this context;
the common institutional canvas then paints the same opaque verification URL
for every format that uses it.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Iterator, Optional
from urllib.parse import urlsplit, urlunsplit


_CURRENT_QR: ContextVar[Optional[dict]] = ContextVar("hes_pdf_qr", default=None)


def document_uuid(pt_num: str, codigo_formato: str, slot: int = 1) -> str:
    """Return a high-entropy opaque id stable for a patient/document slot."""
    secret = os.getenv("HES_HMAC_SECRET", "").strip() or os.getenv("SECRET_KEY", "hes-development")
    material = f"hes-pdf-qr-v1:{pt_num}:{codigo_formato}:{int(slot or 1)}"
    digest = hmac.new(secret.encode("utf-8"), material.encode("utf-8"), hashlib.sha256).digest()
    token = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return f"v1_{token}"


@contextmanager
def qr_render_context(
    *,
    doc_uuid: str,
    verification_url: str,
    pt_num: str,
    codigo_formato: str,
    slot: int,
    persist: bool = False,
) -> Iterator[dict]:
    value = {
        "doc_uuid": doc_uuid,
        "verification_url": verification_url,
        "pt_num": str(pt_num),
        "codigo_formato": str(codigo_formato),
        "slot": int(slot or 1),
        "persist": bool(persist),
    }
    token = _CURRENT_QR.set(value)
    try:
        yield value
    finally:
        _CURRENT_QR.reset(token)


def current_qr_context() -> Optional[dict]:
    return _CURRENT_QR.get()


def qr_payload(doc_info: Optional[dict] = None) -> tuple[Optional[str], bool]:
    """Return (payload, from_explicit_preparation_context)."""
    info = doc_info or {}
    explicit = info.get("qr_data") or info.get("qr_url")
    if explicit:
        value = str(explicit)
        parsed = urlsplit(value)
        # Todas las lecturas públicas pasan por la pantalla institucional de
        # cotejo. Si un motor histórico trae el endpoint PDF como destino,
        # conserva su id y normaliza únicamente ese path conocido.
        if parsed.path.rstrip("/").endswith("/verificar/pdf/documento"):
            parsed = parsed._replace(path=parsed.path.rstrip("/")[:-len("/pdf/documento")])
            value = urlunsplit(parsed)
        return value, False
    context = current_qr_context()
    if context and context.get("verification_url"):
        return str(context["verification_url"]), True
    return None, False

"""RFC 3161 client with full CMS, certificate-chain, EKU and nonce validation."""

from __future__ import annotations

import asyncio
import base64
import datetime
import hashlib
import logging
import os
import secrets
import urllib.request
from pathlib import Path
from typing import Iterable, Optional

from asn1crypto import cms, tsp, x509 as asn1_x509
from cryptography import x509 as crypto_x509
from cryptography.hazmat.primitives import serialization
from pyhanko.sign.validation.generic_cms import validate_tst_signed_data
from pyhanko.sign.validation.status import TimestampSignatureStatus
from pyhanko_certvalidator import ValidationContext


logger = logging.getLogger("hes.tsa")
TSA_STATUS_GRANTED = 0
TSA_STATUS_GRANTED_WITH_MODS = 1
SIN_TSA = "SIN_TSA"
TSA_PENDIENTE = "TSA_PENDIENTE"
TSA_VERIFICADO = "TSA_VERIFICADO"
TSA_FALLIDO = "TSA_FALLIDO"


def get_tsa_url() -> str:
    return os.getenv("TSA_URL", "https://freetsa.org/tsr")


def _load_trust_roots(path: Optional[str] = None) -> list[asn1_x509.Certificate]:
    trust_path = path or os.getenv("TSA_TRUST_STORE")
    if not trust_path:
        raise RuntimeError("TSA_TRUST_STORE no está configurado; no se puede afirmar confianza TSA")
    pem_bytes = Path(trust_path).read_bytes()
    certs = crypto_x509.load_pem_x509_certificates(pem_bytes)
    if not certs:
        raise RuntimeError("El trust store TSA no contiene certificados PEM")
    return [asn1_x509.Certificate.load(cert.public_bytes(serialization.Encoding.DER)) for cert in certs]


def _extract_tst_info(token: cms.ContentInfo) -> tuple[cms.SignedData, tsp.TSTInfo]:
    if token["content_type"].native != "signed_data":
        raise ValueError("El TimeStampToken no contiene CMS SignedData")
    signed_data = token["content"]
    encap = signed_data["encap_content_info"]
    if encap["content_type"].native != "tst_info":
        raise ValueError("El eContentType CMS no es id-ct-TSTInfo")
    content = encap["content"]
    parsed = content.parsed if hasattr(content, "parsed") else tsp.TSTInfo.load(bytes(content))
    if not isinstance(parsed, tsp.TSTInfo):
        parsed = tsp.TSTInfo.load(bytes(content))
    return signed_data, parsed


def _run_validation(coro):
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    raise RuntimeError("La verificación TSA síncrona no puede ejecutarse dentro de un event loop activo")


def verify_timestamp(
    token_b64: str,
    expected_hash_sha256_hex: str,
    *,
    expected_nonce: Optional[int | str] = None,
    trust_roots: Optional[Iterable[asn1_x509.Certificate]] = None,
    trust_store_path: Optional[str] = None,
    expected_subject: Optional[str] = None,
    expected_cert_sha256: Optional[str] = None,
) -> dict:
    result = {
        "disponible": False,
        "verificado": False,
        "status": TSA_FALLIDO if token_b64 else SIN_TSA,
        "gen_time": None,
        "serial": None,
        "autoridad": None,
        "algoritmo": None,
        "nonce": None,
        "error": None,
    }
    if not token_b64:
        return result
    try:
        expected_hash = bytes.fromhex(expected_hash_sha256_hex)
        if len(expected_hash) != 32:
            raise ValueError("El hash esperado no es SHA-256")
        token = cms.ContentInfo.load(base64.b64decode(token_b64, validate=True))
        signed_data, tst_info = _extract_tst_info(token)
        result["disponible"] = True
        algorithm = tst_info["message_imprint"]["hash_algorithm"]["algorithm"].native
        result["algoritmo"] = algorithm
        if algorithm != "sha256":
            raise ValueError(f"Algoritmo messageImprint no permitido: {algorithm}")
        imprint = tst_info["message_imprint"]["hashed_message"].native
        if imprint != expected_hash:
            raise ValueError("El messageImprint TSA no corresponde al payload firmado")

        nonce_value = tst_info["nonce"].native
        result["nonce"] = str(nonce_value) if nonce_value is not None else None
        if expected_nonce is not None and nonce_value != int(expected_nonce):
            raise ValueError("El nonce TSA no coincide con la solicitud")

        gen_time = tst_info["gen_time"].native
        roots = list(trust_roots) if trust_roots is not None else _load_trust_roots(trust_store_path)
        context = ValidationContext(
            trust_roots=roots,
            other_certs=[choice.chosen for choice in signed_data["certificates"] if choice.name == "certificate"],
            moment=gen_time,
            allow_fetching=False,
            revocation_mode="soft-fail",
        )
        status_kwargs = _run_validation(
            validate_tst_signed_data(
                signed_data,
                validation_context=context,
                expected_tst_imprint=lambda algo: expected_hash if algo == "sha256" else b"",
            )
        )
        status = TimestampSignatureStatus(**status_kwargs)
        if not (status.valid and status.intact and status.trusted):
            raise ValueError("Firma CMS TSA inválida o certificado no confiable")

        signer = status.signing_cert
        subject = signer.subject.human_friendly
        fingerprint = hashlib.sha256(signer.dump()).hexdigest()
        required_subject = expected_subject if expected_subject is not None else os.getenv("TSA_EXPECTED_SUBJECT")
        required_fingerprint = (
            expected_cert_sha256 if expected_cert_sha256 is not None else os.getenv("TSA_EXPECTED_CERT_SHA256")
        )
        if required_subject and required_subject.casefold() not in subject.casefold():
            raise ValueError("La identidad del certificado firmante no coincide con la TSA configurada")
        if required_fingerprint and fingerprint.casefold() != required_fingerprint.replace(":", "").casefold():
            raise ValueError("El certificado TSA no coincide con el pin SHA-256 configurado")

        result.update(
            {
                "verificado": True,
                "status": TSA_VERIFICADO,
                "gen_time": gen_time.isoformat(),
                "serial": format(tst_info["serial_number"].native, "x"),
                "autoridad": subject,
                "cert_sha256": fingerprint,
                "error": None,
            }
        )
    except Exception as exc:
        logger.warning("Verificación TSA rechazada: %s", exc)
        result["error"] = str(exc)
    return result


def get_timestamp(hash_sha256_hex: str, *, nonce: Optional[int] = None) -> dict:
    """Request and verify an RFC 3161 token; network failures remain pending."""
    request_nonce = nonce if nonce is not None else secrets.randbits(128) or 1
    try:
        digest = bytes.fromhex(hash_sha256_hex)
        if len(digest) != 32:
            raise ValueError("El hash para TSA debe ser SHA-256")
        request_obj = tsp.TimeStampReq(
            {
                "version": 1,
                "message_imprint": {
                    "hash_algorithm": {"algorithm": "sha256"},
                    "hashed_message": digest,
                },
                "nonce": request_nonce,
                "cert_req": True,
            }
        )
        http_request = urllib.request.Request(
            get_tsa_url(),
            data=request_obj.dump(),
            headers={"Content-Type": "application/timestamp-query"},
            method="POST",
        )
        with urllib.request.urlopen(
            http_request, timeout=float(os.getenv("TSA_TIMEOUT", "3"))
        ) as response:
            body = response.read()
        tsr = tsp.TimeStampResp.load(body)
        native_status = tsr["status"]["status"].native
        successful_statuses = {
            TSA_STATUS_GRANTED,
            TSA_STATUS_GRANTED_WITH_MODS,
            "granted",
            "granted_with_mods",
        }
        if native_status not in successful_statuses:
            raise ValueError(f"La TSA rechazó la solicitud con estado {native_status}")
        token = tsr["time_stamp_token"]
        if token.native is None:
            raise ValueError("La TSA respondió granted sin TimeStampToken")
        token_b64 = base64.b64encode(token.dump()).decode("ascii")
        verification = verify_timestamp(
            token_b64,
            hash_sha256_hex,
            expected_nonce=request_nonce,
        )
        return {
            **verification,
            "token_b64": token_b64,
            "nonce": str(request_nonce),
        }
    except (OSError, TimeoutError) as exc:
        logger.warning("TSA no disponible: firma conservada con estado pendiente (%s)", exc)
        return {
            "status": TSA_PENDIENTE,
            "verificado": False,
            "disponible": False,
            "token_b64": None,
            "nonce": str(request_nonce),
            "error": str(exc),
        }
    except Exception as exc:
        logger.warning("Respuesta TSA rechazada: %s", exc)
        return {
            "status": TSA_FALLIDO,
            "verificado": False,
            "disponible": True,
            "token_b64": None,
            "nonce": str(request_nonce),
            "error": str(exc),
        }

"""Private, content-validated upload storage."""

from __future__ import annotations

import io
import os
import tempfile
import uuid
import zipfile
from dataclasses import dataclass
from pathlib import Path

from fastapi import HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError


PHOTO_LIMIT = 5 * 1024 * 1024
DOCUMENT_LIMIT = 10 * 1024 * 1024


@dataclass(frozen=True)
class ValidatedUpload:
    data: bytes
    extension: str
    media_type: str


async def read_limited(upload: UploadFile, limit: int) -> bytes:
    data = await upload.read(limit + 1)
    if len(data) > limit:
        raise HTTPException(status_code=413, detail=f"El archivo excede el máximo de {limit // (1024 * 1024)} MB.")
    if not data:
        raise HTTPException(status_code=422, detail="El archivo está vacío.")
    return data


def validate_photo(data: bytes) -> ValidatedUpload:
    try:
        with Image.open(io.BytesIO(data)) as image:
            image.verify()
            fmt = (image.format or "").upper()
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="La foto no contiene una imagen válida.") from exc
    if fmt == "JPEG":
        return ValidatedUpload(data, ".jpg", "image/jpeg")
    if fmt == "PNG":
        return ValidatedUpload(data, ".png", "image/png")
    raise HTTPException(status_code=422, detail="Sólo se permiten fotos JPEG o PNG.")


def validate_document(data: bytes) -> ValidatedUpload:
    if data.startswith(b"%PDF-") and b"%%EOF" in data[-2048:]:
        return ValidatedUpload(data, ".pdf", "application/pdf")
    try:
        photo = validate_photo(data)
        return photo
    except HTTPException:
        pass
    if data.startswith(b"PK\x03\x04"):
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                names = set(archive.namelist())
                if "[Content_Types].xml" in names and "xl/workbook.xml" in names:
                    return ValidatedUpload(data, ".xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        except (zipfile.BadZipFile, OSError):
            pass
    raise HTTPException(status_code=422, detail="Contenido no permitido. Use PDF, JPEG, PNG o XLSX válidos.")


def store_private(root: str, category: str, validated: ValidatedUpload) -> tuple[str, str]:
    category_root = os.path.realpath(os.path.join(root, category))
    if os.path.commonpath([os.path.realpath(root), category_root]) != os.path.realpath(root):
        raise RuntimeError("Categoría de almacenamiento inválida")
    os.makedirs(category_root, exist_ok=True)
    stored_name = f"{uuid.uuid4().hex}{validated.extension}"
    final_path = os.path.join(category_root, stored_name)
    fd, temporary = tempfile.mkstemp(prefix=".upload-", dir=category_root)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(validated.data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, final_path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return stored_name, final_path


def resolve_private(root: str, category: str, stored_name: str) -> str:
    safe_name = os.path.basename(stored_name or "")
    category_root = os.path.realpath(os.path.join(root, category))
    path = os.path.realpath(os.path.join(category_root, safe_name))
    if not safe_name or os.path.commonpath([category_root, path]) != category_root:
        raise HTTPException(status_code=400, detail="Ruta de archivo inválida.")
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Archivo no encontrado.")
    return path

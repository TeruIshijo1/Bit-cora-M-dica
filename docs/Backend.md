# Backend

El Backend es el motor lógico del proyecto, encargado de procesar las peticiones del [[Frontend]], aplicar las reglas de negocio médico, gestionar la seguridad criptográfica y generar los documentos oficiales.

## Tecnologías Principales
- **Framework:** FastAPI (Python 3.10+) con servidor asíncrono Uvicorn.
- **Seguridad y Roles:** `security.py` con tokens JWT (HS256) y decoradores `require_role`.
- **Criptografía FEA (NOM-024 / NOM-004):** `crypto_fea.py` utilizando curvas elípticas ECDSA P-256 (SECP256R1), derivación de llaves KEK vía HKDF-SHA256 con cifrado Fernet y sellado de tiempo RFC 3161 (`tsa_client.py`).
- **Motor de PDFs Multiplataforma:** `pdf_engine_v2.py` (ReportLab Platypus) y `pdf_generator.py` (xhtml2pdf), sin ninguna dependencia de Windows COM ni Microsoft Word.
- **Gestión de Dependencias:** `requirements.txt` (limpio y portable para Linux / Docker).

## Arquitectura Modular de Routers y Servicios
- `routers/catalogos.py`: Catálogos de áreas, tipos de atención y formatos autorizados.
- `services/pdf_service.py`: Servicio unificado de generación de notas de urgencias, consentimientos informados y comprobantes de atención.
- `kh_database.py`: Conector de solo lectura hacia el ERP central SQL Server (`KH_HE`).

## Relaciones en el Proyecto
- Provee los endpoints REST protegidos por autenticación global (`GlobalAuthMiddleware`), CORS estricto y `TrustedHostMiddleware` consumidos por el [[Frontend]].
- Interactúa estrechamente con la [[Database]] para gestionar y persistir los datos clínicos y el historial de llaves asimétricas.
- Su despliegue y scripts de arranque se asocian a la etapa de [[Pase_a_Produccion]].

---
aliases: [Backend FastAPI, API HES]
tags: [hes/backend, hes/arquitectura, hes/seguridad]
tipo: modulo
modulo: backend
codigo_fuente:
  - backend/main.py
  - backend/security.py
  - backend/crypto_fea.py
  - backend/clinical_signing.py
  - backend/tsa_client.py
  - backend/routers/catalogos.py
  - backend/services/pdf_service.py
  - backend/kh_database.py
  - backend/requirements.txt
actualizado: 2026-09-17
relacionados:
  - "[[00_Inicio]]"
  - "[[Mapa_Proyecto]]"
  - "[[Arquitectura]]"
  - "[[API-Endpoints]]"
  - "[[Seguridad-FEA]]"
  - "[[Formatos-PDF]]"
  - "[[Database]]"
  - "[[Pase_a_Produccion]]"
---

# Backend

El Backend es el motor lógico del proyecto, encargado de procesar las peticiones del [[Frontend]], aplicar las reglas de negocio médico, gestionar la seguridad criptográfica y generar los documentos oficiales.

## Tecnologías Principales
- **Framework:** FastAPI (Python 3.10+) con servidor asíncrono Uvicorn.
- **Seguridad y Roles:** `security.py` con tokens JWT (HS256) y decoradores `require_role`. Ver [[Seguridad-FEA]] y [[API-Endpoints]].
- **Criptografía FEA (NOM-024 / NOM-004):** `clinical_signing.py` produce snapshots `CANONICAL_V2`; `crypto_fea.py` firma con ECDSA P-256 y `key_id` exacta, custodia privada `FERNET_HKDF_SHA256_V1`; `tsa_client.py` valida íntegramente CMS/RFC 3161 con trust store y nonce.
- **Motor de PDFs Multiplataforma:** `pdf_engine_v2.py` (ReportLab Platypus) y `pdf_generator.py` (xhtml2pdf), sin ninguna dependencia de Windows COM ni Microsoft Word. Ver [[Formatos-PDF]] y [[decisiones/ADR-0001-reportlab-sin-word]].
- **Gestión de Dependencias:** `requirements.txt` (limpio y portable para Linux / Docker).

## Arquitectura Modular de Routers y Servicios
- `routers/catalogos.py`: Catálogos de áreas, tipos de atención y formatos autorizados.
- `services/pdf_service.py`: Servicio unificado de generación de notas de urgencias, consentimientos informados y comprobantes de atención.
- `clinical_signing.py`: carga autoritativa del acto clínico, serialización determinista y verificación de snapshot/PDF/identidad/llave.
- `kh_database.py`: adaptador explícito hacia SQL Server (`KH_HE`). Las lecturas
  permanecen directas; toda mutación falla explícitamente, acepta correlación
  por `operation_id` y participa en la máquina durable de sincronización de
  `clinical_sync.py`.
- `clinical_sync.py` + `clinical_sync_adapters.py`: intención PostgreSQL previa,
  idempotencia, estados `PENDING/PROCESSING/SYNCED/RETRYABLE_ERROR/FAILED/
  REQUIRES_RECONCILIATION`, backoff e intentos auditables. Cubre medicamentos,
  dietas, notas, signos vitales, alergias, consentimientos, formatos universales,
  contactos PTCN, altas/reingresos y firma Vertical. Un `INSERT` universal sin
  GUID descubrible se bloquea antes del write. No implementa 2PC.
- Orquestador: `main.py` (~12k líneas, middlewares GlobalAuth + CORS + TrustedHost + RateLimit). `GlobalAuthMiddleware` usa la allowlist exacta y la matriz deny-by-default de `route_policy.py`. Detalle en [[API-Endpoints]].

## Perfil productivo

- `backend/app_config.py` separa development, test y production. Producción
  exige secretos fuertes, PostgreSQL, issuer/audience, hosts/origins HTTPS,
  proxy HTTPS y trust store TSA cuando se configura el servicio.
- `backend/bootstrap_admin.py` es el único bootstrap: explícito, sólo sobre base
  vacía, secreto aleatorio o interactivo, cambio obligatorio y evento auditado.
- `deploy/systemd/hes-api.service` ejecuta dos workers sin `--reload`, bind local,
  reinicio, parada limpia y logs de journal. Nginx termina TLS.
- JWT usa expiración corta, `jti`, issuer/audience, revocación y consulta del
  estado actual del usuario. Auditoría y logs correlacionan `request_id` y
  `operation_id` con redacción de secretos y biometría.

## Relaciones en el Proyecto
- Provee los endpoints REST protegidos por autenticación global (`GlobalAuthMiddleware`), CORS estricto y `TrustedHostMiddleware` consumidos por el [[Frontend]].
- Interactúa estrechamente con la [[Database]] para gestionar y persistir los datos clínicos y el historial de llaves asimétricas.
- Su despliegue y scripts de arranque se asocian a la etapa de [[Pase_a_Produccion]].

---
> 🤖 *Contexto IA: antes de tocar `backend/`, leer [[Guia-Desarrollo-IA]] (reglas `.env`, FEA, ReportLab) y [[API-Endpoints]]. Código fuente: `backend/main.py`, `backend/security.py`, `backend/crypto_fea.py`.*

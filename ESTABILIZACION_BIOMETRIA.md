# Estabilización de seguridad biométrica — Bloque A

**Fecha:** 2026-09-17  
**Alcance:** P0-02, P0-03, P0-04 y parte biométrica de P0-06.  
**Fuera de alcance respetado:** rediseño ECDSA, cadena original, TSA, atomicidad PostgreSQL/SQL Server y refactors generales.

## Dictamen

| Hallazgo | Estado | Evidencia negativa asociada |
|---|---|---|
| P0-02 | **RESUELTO** | `test_fingerprint_b_against_a_is_rejected_without_mutation`, fallos/timeout/respuesta inválida y rol/paciente ajenos rechazan sin mutar biometría ni crear firmas. |
| P0-03 | **RESUELTO** | ausencia, inexistencia, expiración, reutilización, acción/paciente/documento distintos, captura stale y carrera concurrente cubiertos en `test_biometric_security.py`; exactamente uno de 20 consumidores gana. |
| P0-04 | **RESUELTO** | enrolamiento sintético persiste sólo envelope ANSI 378 canónico; RAW se rechaza como `LEGACY_RAW` y existe únicamente en memoria hasta `/extract-fmd`. |
| P0-06 (biometría) | **BLOQUEADO_SEGURO** | reenrolamiento médico es explícito, RBAC, motivo y auditoría; activa `requiere_actualizacion_fea=true` y toda firma criptográfica devuelve 423 hasta el Bloque B. No se rediseñaron llaves. |

## Protocolo final

1. La SPA solicita challenge contextual antes de iniciar el lector.
2. PostgreSQL guarda sólo SHA-256 del nonce con acción, sesión, sujeto autenticado, identidad biométrica esperada, paciente, documento, creación, expiración y consumo.
3. El lector produce RAW temporal. La SPA lo entrega exclusivamente al servicio loopback confiable.
4. `/extract-fmd` convierte RAW a ANSI 378, lo descarta y devuelve un envelope atestado por HMAC para challenge+sesión+instante.
5. FastAPI consume el challenge con un `UPDATE` condicional atómico, valida contexto/attestation y envía al matcher únicamente FMD.
6. Match exacto continúa. No-match, timeout, caída, HTTP inválido, JSON inválido o excepción fallan cerrados.
7. Verificación/firma nunca enrola, reenrola ni reasigna identidad. `firmante_id` es obligatorio y el rol persistido es autoritativo.

## Enrolamiento y legacy

- Enrolamiento y reenrolamiento tienen rutas separadas para médicos y firmantes de episodio.
- El reenrolamiento requiere motivo y genera `AuditoriaLog` sin almacenar FMD/RAW en el evento.
- Estados: `SIN_BIOMETRIA`, `LEGACY_RAW`, `FMD_VALIDO`.
- La migración nueva marca todo valor histórico no vacío como `LEGACY_RAW` y no lo transforma, borra ni reconstruye.
- Sólo fixtures FMD sintéticos se usaron en pruebas.

## Migración

- Nueva: `backend/migrations/versions/4b7e2a91c6d0_biometric_security_stabilization.py`.
- Base `9024a9c93603_initial_postgresql_schema.py`: sin modificación.
- Agrega `biometric_challenges`, metadatos mínimos de plantilla/estado y `requiere_actualizacion_fea`.

## Pruebas antes/después

Antes del cambio, las cuatro regresiones iniciales terminaron **4 failed** sobre PostgreSQL TEST: challenge ausente, no-match, matcher caído y `firmante_id` ausente eran aceptados.

Después:

```text
backend/tests/test_biometric_security.py
25 passed, 133 warnings in 9.57s

suite completa pytest
63 passed, 134 warnings, 10 subtests passed in 22.71s

Alembic upgrade de PostgreSQL TEST limpio
9024a9c93603 -> 4b7e2a91c6d0: OK

alembic check
No new upgrade operations detected.

compileall backend
OK

frontend npm run build
✓ built in 539ms

node --check del servicio DigitalPersona
OK
```

Las advertencias son deprecaciones preexistentes de Pydantic/SQLAlchemy/Starlette y no fallos de la estabilización.

## Archivos del bloque

- Backend: `backend/main.py`, `backend/models.py`, `backend/schemas.py`, `backend/biometric_security.py`, `backend/route_policy.py`, `backend/.env.example`.
- Migración: `backend/migrations/versions/4b7e2a91c6d0_biometric_security_stabilization.py`.
- Pruebas: `backend/tests/test_biometric_security.py`.
- Frontend: `frontend/src/hooks/useDigitalPersona.js`, `frontend/src/pages/LoginDual.jsx`, `frontend/src/pages/PatientDashboard.jsx`, `frontend/src/pages/FirmaExpress.jsx`, `frontend/src/features/biometrics/BiometricSignModal.jsx`, `BiometricPatientSignModal.jsx`, `FirmantesEpisodioModal.jsx`.
- Servicio: `biometric-service/server.js` (copia versionada) y `D:/Escritorio/Teru/Bio-security/server.js` (servicio instalado, hashes SHA-256 iguales al validar).
- Documentación: `docs/Biometria-DigitalPersona.md`, `docs/API-Endpoints.md`, `docs/Database.md`, `docs/Frontend.md`.

## Riesgos restantes estrictamente relacionados

- Todos los registros históricos clasificados `LEGACY_RAW` quedan bloqueados hasta reenrolamiento presencial controlado; no hay conversión automática segura posible.
- Tras reenrolar un médico, la FEA queda bloqueada de forma deliberada hasta que el Bloque B defina la transición/rotación criptográfica. Las llaves existentes no se modificaron.
- La extracción/matching fue validada por contrato, sintaxis y fixtures sintéticos; falta la prueba operativa con lector físico y SDK nativo en el puesto clínico antes de producción.

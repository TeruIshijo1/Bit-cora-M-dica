# Preparación técnica final de preproducción

Fecha: 2026-09-17  
Alcance: Bloque D — seguridad, estabilidad, despliegue y continuidad.  
Dictamen: **preparada técnicamente para validación final de preproducción; no
autorizada aún para go-live**.

## Cierre P0/P1 de la auditoría inicial

| Hallazgo | Estado | Prueba / límite real |
|---|---|---|
| P0-01 — bypass y exposición de expediente/PDF | `MITIGADO_Y_BLOQUEADO` | Allowlist exacta, auth global, archivos privados y matriz automatizada; no hay webroot clínico. Falta aprobación funcional de autorización horizontal y alcance del portal QR público. |
| P0-02 — huella incorrecta sustituye identidad | `RESUELTO` | Mismatch, servicio caído y datos inválidos fallan sin mutación ni firma. |
| P0-03 — challenge opcional/replay | `RESUELTO` | Challenge contextual obligatorio, 120 s, persistido y consumo atómico; prueba de 20 consumidores deja un ganador. |
| P0-04 — persistencia RAW | `RESUELTO` | Nuevos enrolamientos sólo guardan FMD ANSI 378 canónico; RAW se procesa temporalmente en loopback. Histórico no conforme queda `LEGACY_RAW` y exige reenrolamiento. |
| P0-05 — ECDSA no vinculada al documento | `RESUELTO` | CANONICAL_V2, hash completo, `key_id` exacta y PDF cuando aplica; mutaciones y marcadores Vertical fallan. |
| P0-06 — sustitución de huella conserva llave | `RESUELTO` | Reenrolamiento bloquea firma 423 y exige actualización FEA explícita, match/challenge, motivo, rotación e historia. |
| P0-07 — arranque inseguro | `RESUELTO` | Seed explícito sólo DEV, bootstrap único sin contraseña literal, cambio obligatorio, auditoría; `systemd` sin reload y proxy TLS. |
| P0-08 — dual-write no recuperable | `RESUELTO` | Intención PostgreSQL previa, idempotencia, estados durables e intentos; ningún timeout se reporta `SYNCED`. |
| P0-09 — JWT permite escrituras amplias | `MITIGADO_Y_BLOQUEADO` | Usuario/rol/activo se revalidan, escrituras fail-closed y 231 rutas inventariadas. Falta decisión hospitalaria de relación profesional-paciente y cuatro permisos funcionales; esas rutas permanecen 403. |
| P1-01 — custodia/rotación/key-id | `RESUELTO` | Una llave activa, historia append-only, `key_id` exacta, descifrado fail-closed y rotación explícita. No se declara HSM. |
| P1-02 — TSA sin verificación criptográfica | `RESUELTO` | CMS/RFC3161, trust store, EKU, vigencia, identidad, nonce e imprint; caída produce `TSA_PENDIENTE`. |
| P1-03 — auditoría mutable/impersonación | `RESUELTO` | Trigger PostgreSQL bloquea update/delete; actor real/efectivo, motivo, resultado, request/operation id; logout/fin trazable. |
| P1-04 — doble submit/firma | `RESUELTO` | Idempotency key, unicidad PostgreSQL y prueba de 50 solicitudes: un `operation_id`, una creación. |
| P1-05 — uploads públicos/arbitrarios | `RESUELTO` | Validación de contenido/tamaño, allowlist, nombre UUID, path contenido, escritura atómica privada y controlador autorizado. |
| P1-06 — sesión larga/HTTP/perímetro | `RESUELTO` | JWT 15 min con `jti`, issuer/audience y revocación; secretos fuertes, HTTPS/proxy, hosts/origins explícitos, HSTS y headers. Activación TLS real es gate de entorno. |
| P1-07 — contrato móvil roto | `RESUELTO` | `habitacion_capturada` y nombres médicos alineados; `tsc --noEmit` pasa. |
| P1-08 — `no-undef` en verificación/consentimientos | `RESUELTO` | `docCode`, variables fuera de scope y `cleaningStatus` corregidos; lint runtime pasa. |
| P1-09 — sin red de pruebas | `RESUELTO` | 139 pruebas + 10 subpruebas sobre PostgreSQL TEST; gates de migración, frontend, móvil, biometría, seguridad y fallas. |
| P1-10 — continuidad sin probar | `GATE_EXTERNO_PENDIENTE` | Backup/restore real sintético y runbook listos. Falta programar, cifrar/custodiar y evidenciar copia fuera del host en infraestructura hospitalaria. |
| P1-11 — GET con escrituras / SQL Server contradictorio | `RESUELTO` | GET sin mutaciones, writes declarados y frontera durable cubierta por pruebas estructurales. |
| P1-12 — vulnerabilidades/build no reproducible | `MITIGADO_Y_BLOQUEADO` | Lockfiles presentes; 0 HIGH/CRITICAL runtime. Quedan 14 moderadas Expo y CVE-2024-23342 sin parche en ruta ECDSA no utilizada; ver `DEPENDENCY_INVENTORY.md`. |

No hay P0/P1 marcado `NO_RESUELTO`. Los puntos mitigados no pueden declararse
cerrados hasta completar decisiones o evidencia externa indicadas.

## Evidencia ejecutada

- PostgreSQL TEST completo: **139 passed, 172 warnings, 10 subtests passed** en
  61.45 s. Conserva y amplía las 129 pruebas previas.
- Alembic desde esquema limpio: `upgrade head` PASS; `alembic check`: **No new
  upgrade operations detected**.
- Consistencia, biometría, FEA/TSA, autorización, uploads y failure injection:
  incluidas en la misma regresión. Matriz: `FAILURE_INJECTION_PREPRODUCCION.md`.
- Concurrencia: **20** consumos simultáneos de challenge, un ganador; **50**
  solicitudes simultáneas con la misma idempotency key, una creación.
- Frontend: build PASS (721 módulos) y lint runtime `no-undef` PASS. La alerta de
  chunks grandes es de rendimiento, no un fallo runtime.
- Móvil: `npx tsc --noEmit` PASS.
- Servicio biométrico: `node --check server.js` PASS y lockfile generado.
- Python: `compileall` PASS.
- Secret scan: **253 archivos de texto, 0 hallazgos de alta confianza**.
- Inventario de autorización: **231 rutas** — 30 públicas, 60 autenticadas y
  141 con rol específico; ninguna escritura sin política/bloqueo.
- Dependencias: frontend 0 vulnerabilidades runtime; biometría 0; móvil 14
  moderadas/0 high/0 critical; Python un advisory único sin fix y ruta mitigada.

## Restore medido

Restore real sobre base PostgreSQL TEST vacía con datos exclusivamente
sintéticos:

- backup: **0.241 s**;
- restore: **0.354 s**;
- dump: **112,937 bytes**;
- SHA-256: `3a84268bd572d7eea5c744f10a3cb4a0df511d6f384a60fd02d3d880a5cf3a53`;
- `pg_restore --list`: PASS;
- 24 tablas esperadas: PASS;
- firma CANONICAL_V2: PASS;
- llave pública histórica: PASS;
- estado `clinical_sync_operations`: PASS.

El artefacto del simulacro está ignorado; no contiene datos clínicos reales.

## Configuración productiva obligatoria

Antes de iniciar `hes-api.service` deben establecerse y validarse:

- `APP_ENV=production`;
- `DATABASE_URL` PostgreSQL productiva y pool/conexión;
- `SECRET_KEY`, `HES_HMAC_SECRET` y `BIOMETRIC_ATTESTATION_SECRET` aleatorios,
  independientes y de al menos 32 caracteres;
- `ACCESS_TOKEN_EXPIRE_MINUTES` (máximo validado: 30; plantilla: 15),
  `JWT_ISSUER` y `JWT_AUDIENCE`;
- `ALLOWED_ORIGINS` HTTPS y `ALLOWED_HOSTS` explícitos, nunca `*`;
- `PROXY_HTTPS_ENABLED=true`, certificado TLS y proxy confiable;
- `PRIVATE_STORAGE_ROOT` privado y `MIN_FREE_DISK_BYTES`;
- `TSA_URL` y `TSA_TRUST_STORE` privado cuando TSA esté habilitado;
- credenciales SQL Server/Vertical mediante archivo de entorno protegido, nunca
  incluidas en el paquete;
- bootstrap inicial explícito sólo si la tabla de usuarios está vacía.

El paquete se genera con `python preparar_produccion.py`, que falla si los gates
técnicos no pasan y produce `MANIFEST.sha256.json` sin `.env`, datos, reload o
servidor de desarrollo.

## GO_LIVE_GATES

- [PASS] PostgreSQL TEST, migraciones y `alembic check`
- [PASS] autorización fail-closed e inventario de rutas
- [PASS] biometría sintética, anti-replay y concurrencia multiworker
- [PASS] FEA CANONICAL_V2, rotación histórica y TSA criptográfica
- [PASS] idempotencia/consistencia y failure injection simulada
- [PASS] build/lint frontend y typecheck móvil
- [PASS] backup/restore TEST sintético medido
- [PASS] 0 vulnerabilidades HIGH/CRITICAL de runtime
- [PENDING] `GATE_PENDIENTE_SQLSERVER_STAGING`: smoke real de medicación,
  suspensión, dieta, nota, signos, consentimiento, alta/reingreso,
  reconciliación e idempotencia. **Nunca usar KH_HE productivo para este gate.**
- [PENDING] lector DigitalPersona físico + SDK en puesto clínico
- [PENDING] matriz funcional/horizontal y cuatro rutas bloqueadas aprobadas por
  responsables hospitalarios
- [PENDING] TLS/hosts/origins/secrets/TSA trust store instalados y readiness del
  entorno productivo
- [PENDING] backup cifrado programado, custodia y copia fuera del host verificada
- [PENDING] validación jurídica NOM/FEA/privacidad y procedimientos hospitalarios

## Riesgos residuales reales

1. No existe SQL Server TEST/STAGING accesible; los adaptadores se validaron con
   PostgreSQL real y dobles/fallas simuladas, no contra el esquema externo real.
2. No se probó lector físico; calidad, drivers, FAR y ciclo operativo requieren
   evidencia en el puesto clínico.
3. La relación profesional-paciente y cuatro decisiones de rol siguen cerradas
   por 403, por lo que esos flujos no deben habilitarse por excepción manual.
4. El backup fuera del host y TLS dependen de infraestructura/operación real; el
   repositorio sólo puede aportar controles y scripts verificables.
5. Permanecen advisories moderados Expo y CVE-2024-23342 mitigado; no hay
   HIGH/CRITICAL aceptadas.
6. La conformidad NOM y validez jurídica no se infieren de controles técnicos.

No se conectó a KH_HE productivo, no se usaron datos clínicos reales y no se
declara cumplimiento normativo.

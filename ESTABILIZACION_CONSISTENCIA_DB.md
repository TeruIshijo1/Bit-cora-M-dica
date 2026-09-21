# Bloque C — Estabilización de consistencia PostgreSQL ↔ SQL Server

**Fecha:** 2026-09-17  
**Alcance:** exclusivamente P0-08 y la parte GET/sincronización de P1-11.  
**PostgreSQL de pruebas:** `hospital_escandon_test` (PostgreSQL 17 real).  
**SQL Server:** adaptador controlado/fault injection; no se usó `KH_HE` productivo.

## Dictamen

- **P0-08: PARCIAL.** Quedaron implementados y probados el modelo durable,
  idempotencia, reconciliación y los flujos de mayor riesgo: medicación,
  suspensión, dieta/cuidados, firma médica Vertical y alta/reingreso. Todos los
  mutadores de `kh_database.py` fallan ahora explícitamente. Las notas,
  consentimientos/formato universal heredados ya no pueden ocultar un error de
  SQL Server, pero aún no todos crean una intención durable antes de su write;
  por eso no se declara P0-08 completamente resuelto.
- **P1-11 (GET/sincronización): RESUELTO.** Los GET declarados en `main.py` no
  llaman `db.add/delete/flush/commit`. El censo se sincroniza mediante
  `POST /api/pacientes/sincronizar-kh`; `GET /api/pacientes`, dashboard,
  firmantes y verificación documental son de solo lectura.

No se implementó 2PC/XA ni compensación clínica destructiva.

## Inventario de dual-writes encontrado

| Flujo / endpoint | PostgreSQL | SQL Server / Vertical | Orden anterior / fallo | Estado de Bloque C |
|---|---|---|---|---|
| Alta y reingreso (`PUT .../alta`, `.../reingresar`) | paciente, cama, biometría temporal, auditoría | `PC` | commits internos de auditoría; error SQL oculto y respuesta exitosa | intención → cambio PG → write idempotente `PC` → estado; 202 si queda pendiente |
| Medicación (`POST .../medicamentos/prescribir-biometrico`) | firma/evidencia y auditoría | `PTDG INSERT` | SQL primero, PG después; reintento duplicable | durable, evidencia enlazada, GUID SQL determinista por `operation_id` |
| Suspensión (`POST .../discontinuar-biometrico`) | auditoría | `PTDG UPDATE` | SQL primero | durable; update sólo si aún no está `DC`, reintento seguro |
| Dieta/cuidados (`POST .../dieta-cuidados/prescribir-biometrico`) | `dieta_cuidados_prescripciones` + auditoría | `MR_SOL_DIET INSERT` | error SQL impreso e ignorado; devolvía éxito | durable; nunca devuelve éxito confirmado si SQL falla; GUID determinista |
| Firma clínica (`POST .../firmar-biometrico`) | `firmas_documentos_clinicos` | API/estado de firma Vertical | PG confirmado antes; excepción Vertical ignorada | durable; firma PG enlazada; Vertical debe confirmar o devuelve 202/502 |
| Notas urgencias/hospitalización | histórico, revocación de firma, auditoría | `MR_NE_URG`, `MR_24_HOJA_EVOL`, `PTVS` | SQL primero; PG después | error SQL explícito; **pendiente integrar intención durable en cada endpoint** |
| Signos vitales | auditoría | `PTVS` y, según caso, nota | SQL primero | error SQL explícito; **pendiente durable** |
| Alergias | auditoría | `PTAL`, texto en notas/dieta | SQL primero | error SQL explícito; **pendiente durable** |
| Consentimientos 32/01, EED, 25, 34/01, 12, 04, 15, 02, 08, 43, 11, 19, 15-EV, 06, 07 | histórico y revocación de firmas | tablas `MR_*` | SQL primero; algunos errores PG se imprimían | error SQL explícito; **pendiente durable** |
| Formato universal crear/guardar | histórico | INSERT/UPDATE dinámico `MR_*` | SQL primero; PG después | inventariado; **pendiente durable e idempotencia por tabla/PK** |
| Contactos/firmantes | firmante del episodio | `PTCN` | sincronización mezclada con lecturas | GET ya no escribe; mutadores PTCN fallan explícitamente; durable pendiente |

## Modelo durable implementado

La migración nueva `8f3c2d1a7b90` crea:

- `clinical_sync_operations`: UUID `operation_id`, `idempotency_key` único,
  tipo/aggregate/paciente, payload mínimo JSONB, estado, intentos, error
  sanitizado, timestamps local/externo, backoff y terminación.
- `clinical_sync_attempts`: evidencia append-only de cada intento, con unicidad
  `(operation_id, attempt_number)`.
- FK única `clinical_sync_operation_id` en firmas, histórico de notas y dietas.

Estados efectivos: `PENDING`, `PROCESSING`, `SYNCED`, `RETRYABLE_ERROR`,
`FAILED` y `REQUIRES_RECONCILIATION`.

El payload elimina FMD, challenge, sesión, JWT, autorización, contraseñas,
tokens y privadas. `last_error` elimina URLs de conexión y valores sensibles.

## Idempotencia y fronteras de fallo

- El cliente puede enviar `Idempotency-Key`; la UI lo envía para medicación,
  suspensión, dieta, firma y alta.
- PostgreSQL impone unicidad. Dos requests concurrentes obtienen la misma
  operación y sólo una puede pasar a `PROCESSING`.
- Medicación/dieta derivan el GUID de Vertical de `operation_id` y consultan el
  GUID antes de insertar. Suspensión, alta/reingreso y estado firmado son
  updates repetibles sin segundo efecto clínico.
- Timeout/red/deadlock → `RETRYABLE_ERROR`, respuesta 202 y backoff exponencial
  acotado.
- Error permanente/constraint → `FAILED`, respuesta 502 sanitizada.
- Éxito externo + fallo al confirmar PG → intento de marcar
  `REQUIRES_RECONCILIATION`; nunca se ejecuta compensación destructiva.
- Un helper de auditoría sólo hace `flush`; el commit pertenece al servicio o
  endpoint.

## Reconciliación

- Comando: `python backend/scripts/reconcile_clinical_sync.py --limit 50`.
- API protegida: `POST /api/clinical-sync/reconcile?limit=50` para
  `admin/sistemas`.
- Estado: `GET /api/clinical-sync/operations/{operation_id}`.
- Procesa sólo `PENDING`, `RETRYABLE_ERROR` y
  `REQUIRES_RECONCILIATION`, respeta backoff/límite, registra cada intento y no
  elimina operaciones.

## Contrato HTTP/UI

- `SYNCED`: 200 con `operation_id` y `state=SYNCED`.
- Pendiente/estado incierto: 202, `success=false`, `operation_id` y estado.
- Permanente: 502 genérico; el detalle técnico sólo queda sanitizado en PG.
- La UI muestra separadamente “sincronización pendiente” y conserva el
  identificador; no presenta el 202 como guardado sincronizado.

## Migración y endpoints modificados

- Migración nueva: `backend/migrations/versions/8f3c2d1a7b90_clinical_sync_operations.py`.
- Flujos modificados: alta, reingreso, prescripción/suspensión de medicamento,
  dieta/cuidados, firma médica Vertical.
- Nuevos endpoints: sincronización explícita de pacientes, consulta de estado
  y reconciliación.
- `vertical_signer.sign_in_vertical_api` ya no devuelve `True` ante excepción o
  respuesta rechazada.
- Todos los mutadores identificados de `kh_database.py` están envueltos por
  `explicit_kh_mutation` y aceptan correlación `operation_id`.

## Pruebas y regresión

Antes de Bloque C: **93 passed**.  
Pruebas dirigidas nuevas: **20 passed** en PostgreSQL real.  
Suite completa tras los cambios: **113 passed**, 153 warnings y 10 subtests.

Las 20 pruebas nuevas cubren éxito, timeout, error permanente, resultado legacy
oculto, confirmación PG fallida tras éxito externo, retry, idempotency key,
concurrencia, reinicio antes del write, retry de operación ya sincronizada,
evidencia por intento, sanitización, payload mínimo, auditoría sin commit y
ausencia estática de writes en GET.

Validaciones finales:

| Validación | Resultado |
|---|---|
| Alembic desde PostgreSQL TEST limpio | OK |
| `alembic check` | OK — `No new upgrade operations detected` |
| `python -m compileall -q backend` | OK |
| `npm run build` | OK (advertencia heredada de chunks >500 kB) |
| `node --check biometric-service/server.js` | OK |

## Riesgos restantes estrictamente de consistencia

1. Los endpoints heredados de notas, alergias, signos, consentimientos y formato
   universal todavía necesitan adoptar la intención durable antes del write
   externo y enlazar su histórico local antes de poder declarar P0-08 resuelto.
2. SQL Server no dispone de una columna de idempotencia uniforme en todas las
   tablas `MR_*`; cada adaptador restante debe usar su PK/regla natural sin
   inventar compensaciones.
3. No se ejecutó una prueba contra SQL Server TEST/STAGING real; las fronteras
   se probaron con adaptador controlado, como permite el bloque.

No se abren iniciativas fuera del Bloque C ni se avanza al Bloque D.

# BLOQUE C — Cierre definitivo de consistencia PostgreSQL ↔ SQL Server

**Fecha:** 2026-09-17  
**Alcance:** cierre de P0-08 y conservación del cierre P1-11.  
**Referencia:** `ESTABILIZACION_CONSISTENCIA_DB.md`.

## Resultado ejecutivo

- **P0-08: RESUELTO.** Todos los dual-writes clínicos conocidos del inventario
  están integrados en `clinical_sync_operations` / `clinical_sync_attempts` o
  se bloquean antes del write cuando no existe una idempotencia segura.
- **P1-11: RESUELTO.** Los `GET` clínicos permanecen sin efectos de escritura.
  Se retiró además el almacenamiento de PDF en `MR_CI_ETE_CARD` que ocurría
  durante el `GET` de PDF 32/01.
- No se creó otra arquitectura, otro reconciliador ni una migración adicional.
  La revisión `8f3c2d1a7b90` ya soporta todos los tipos nuevos.

## Frontera transaccional aplicada

Todos los endpoints cubiertos ejecutan:

`VALIDACIÓN → INTENCIÓN DURABLE PG → CAMBIO LOCAL PG → WRITE SQL SERVER → CONFIRMACIÓN PG → SYNCED`

Un timeout o error nunca produce éxito confirmado. El estado persistido queda
en `RETRYABLE_ERROR`, `FAILED` o `REQUIRES_RECONCILIATION` y la respuesta
recuperable incluye `operation_id`.

El reconciliador existente fue extendido, no duplicado:

- sólo entrega operaciones con `local_applied_at` confirmado;
- respeta backoff y registra cada intento;
- no procesa `REQUIRES_RECONCILIATION` de forma desatendida;
- conserva las operaciones `retry_policy=manual` aun si se solicitan
  explícitamente;
- marca `SYNCED` únicamente después de confirmar el estado en PostgreSQL.

`log_auditoria` continúa haciendo `flush`, sin `commit` interno.

## Idempotencia externa

- Los `INSERT` en tablas con GUID existente usan UUID v5 determinista derivado
  de `operation_id` y nombre del mutador. Antes de insertar se consulta ese GUID.
- Los `UPDATE` por PK o clave natural son repetibles y verificables.
- PTCN usa la clave natural `PTID + ContactName`: sincronización es upsert y la
  revocación repetida converge al mismo estado.
- `MR_NE_URG` puede reutilizar slots dentro de una fila. Si un timeout deja
  ambiguo un cambio de slot sin GUID propio, se marca
  `REQUIRES_RECONCILIATION` y no se reejecuta automáticamente.
- El formato universal descubre el GUID real de la tabla. Si no existe, el
  `INSERT` se bloquea antes de ejecutarse y queda en
  `REQUIRES_RECONCILIATION`. No se añadieron columnas a SQL Server.

## Cobertura final

| Flujo | Intención durable | Idempotencia | Reconciliación | Test | Estado |
|---|---|---|---|---|---|
| Nota de urgencias `MR_NE_URG` | Sí, antes de histórico/revocación | GUID en fila nueva; slot ambiguo se bloquea manualmente | Automática sólo cuando es segura; ambigüedad permanece en `REQUIRES_RECONCILIATION` | éxito, timeout ambiguo, no redelivery | RESUELTO |
| Nota hospitalización `MR_24_HOJA_EVOL` | Sí | GUID determinista en INSERT; UPDATE por MRNum | Automática con backoff | retry sin segundo efecto | RESUELTO |
| Signos vitales `PTVS` + actualización `MR_NE_URG` | Sí | `PTVSID` determinista; una transacción SQL Server | Automática con backoff | retry sin segundo signo | RESUELTO |
| Alta de alergia `PTAL` | Sí | `PTALID` determinista | Automática con backoff | retry sin segunda alergia | RESUELTO |
| Inactivar alergia / texto consolidado | Sí | UPDATE repetible por PK/paciente | Automática con backoff | fault injection y registro de intento | RESUELTO |
| Consentimiento 32/01 `MR_CI_ETE_CARD` | Sí | GUID determinista o UPDATE repetible | Automática; error nunca devuelve éxito | timeout y retry | RESUELTO |
| EED `MR_CI_EED` | Sí | GUID determinista o UPDATE repetible | Automática | inventario estructural | RESUELTO |
| 25 `MR_CI_RGO_CE` | Sí | GUID determinista o UPDATE repetible | Automática | timeout y retry de un efecto | RESUELTO |
| 34/01 `MR_CI_EMI` | Sí | GUID determinista o UPDATE repetible | Automática | inventario estructural | RESUELTO |
| 12 `MR_CI_RGO_HU` | Sí | GUID determinista o UPDATE repetible | Automática | inventario estructural | RESUELTO |
| 04 `MR_CI_CC` | Sí | GUID determinista o UPDATE repetible | Automática | inventario estructural | RESUELTO |
| 15 `MR_CI_CES` | Sí | GUID determinista o UPDATE repetible | Automática | inventario estructural | RESUELTO |
| 02 `MR_02_CI_TRATAMIENTO_QUIRURGICO` | Sí | GUID determinista o UPDATE repetible | Automática | inventario estructural | RESUELTO |
| 07 `MR_CI_PQ` | Sí | GUID determinista o UPDATE repetible | Automática | inventario estructural | RESUELTO |
| 08 `MR_08_CI_DIAGNOSTICO_ADMISION_CONTI` | Sí | GUID determinista o UPDATE repetible | Automática | inventario estructural | RESUELTO |
| 43 `MR_CI_OI` | Sí | GUID determinista o UPDATE repetible | Automática | inventario estructural | RESUELTO |
| 11 `MR_CI_NO_REANIMACION` | Sí | GUID determinista o UPDATE repetible | Automática | inventario estructural | RESUELTO |
| 19 `MR_CI_HISTERECTOMIA` | Sí | GUID determinista o UPDATE repetible | Automática | inventario estructural | RESUELTO |
| Egreso voluntario 15 `MR_EV_HOSP` | Sí | GUID determinista o UPDATE repetible | Automática | inventario estructural | RESUELTO |
| 06 `MR_CI_APA` | Sí | GUID determinista o UPDATE repetible | Automática | inventario estructural | RESUELTO |
| Formato universal INSERT | Sí | GUID descubierto + UUID determinista; sin GUID se bloquea antes del INSERT | Automática si es segura; manual si no hay GUID | retry seguro y bloqueo manual | RESUELTO |
| Formato universal UPDATE | Sí | PK + paciente; UPDATE repetible y verificación de existencia | Automática con backoff | retry seguro | RESUELTO |
| Contactos/firmantes `PTCN` | Sí | `PTID + ContactName`, upsert/delete convergentes | Automática con backoff | retry sin duplicado | RESUELTO |
| Medicación `PTDG` | Sí | GUID determinista / UPDATE repetible | Automática con backoff | regresión existente | RESUELTO |
| Dieta `MR_SOL_DIET` | Sí | GUID determinista | Automática con backoff | regresión existente | RESUELTO |
| Alta/reingreso | Sí | UPDATE convergente | Automática con backoff | regresión existente | RESUELTO |
| Firma Vertical | Sí | `operation_id` verificado por adaptador | Automática con backoff | regresión existente | RESUELTO |

## Prueba estructural

`backend/tests/test_clinical_sync_consistency.py` compara automáticamente:

1. todos los mutadores decorados con `explicit_kh_mutation`;
2. la allowlist del reconciliador;
3. `MUTATOR_STRATEGIES`;
4. llamadas clínicas directas desde endpoints;
5. entrada durable de los endpoints universales;
6. ausencia de escrituras PostgreSQL/SQL Server en `GET`.

La prueba falla si se agrega un mutador conocido sin estrategia durable.

## Evidencia de validación

- PostgreSQL TEST real: `hospital_escandon_test`.
- Suite completa: **129 passed, 153 warnings, 10 subtests passed**.
- Suite de consistencia: **36 passed**.
- Alembic sobre PostgreSQL TEST limpio: `upgrade head` correcto.
- `alembic check`: **No new upgrade operations detected**.
- `python -m compileall -q backend`: correcto.
- `frontend npm run build`: correcto.
- `node --check biometric-service/server.js`: correcto.
- `git diff --check`: sólo reporta whitespace preexistente en el worktree; no
  detectó errores de parche.

## SQL Server TEST/STAGING

No hay una instancia SQL Server TEST/STAGING configurada en este entorno. No se
conectó ni se intentó conectar a `KH_HE` productivo. Las pruebas SQL Server se
ejecutaron con fault injection y adaptadores simulados. El smoke test sobre una
instancia SQL Server dedicada queda registrado como gate del Bloque D antes de
producción; este cierre no inició ni ejecutó el Bloque D.

## Cierre

**P0-08: RESUELTO.**  
**P1-11: RESUELTO.**


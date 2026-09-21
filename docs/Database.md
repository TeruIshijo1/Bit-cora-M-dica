---
aliases: [Base de datos, PostgreSQL HES, DB]
tags: [hes/database, hes/seguridad, hes/operaciones]
tipo: modulo
modulo: database
codigo_fuente:
  - backend/models.py
  - backend/schemas.py
  - backend/database.py
  - backend/seed.py
  - scripts/backup_postgres.ps1
  - backend/scripts/backup_restore_drill.py
actualizado: 2026-09-21
relacionados:
  - "[[00_Inicio]]"
  - "[[Backend]]"
  - "[[Seguridad-FEA]]"
  - "[[Normativa-NOM]]"
  - "[[Pase_a_Produccion]]"
---

# Database

Este componente gestiona la persistencia de datos de toda la aplicación, estructurando la información clínica y garantizando el no repudio y la custodia legal.

## Tecnologías y Modelos Clave
- **Motor Principal:** PostgreSQL (`hospital_escandon_db`).
- **ORM:** SQLAlchemy + Pydantic v2.
- **Historial de Llaves FEA:** Tabla `historial_llaves_fea` para preservar todas las llaves públicas históricas de los médicos y validar firmas antiguas ante rotaciones biométricas. Ver [[Seguridad-FEA]] y [[decisiones/ADR-0002-fea-historial-llaves]].
- **Auditoría y Trazabilidad:** Tabla `auditoria_logs` para registro inmutable de acciones operativas.
- **Modelos Principales:** `Usuario`, `Medico`, `Paciente`, `AtencionMedica`, `FormatoClinico`, `NotaEnfermeria`, `HistorialLlaveFEA`. Fuente: `backend/models.py`.

## Estrategia de Respaldos
- `scripts/backup_postgres.ps1` ejecuta `pg_dump --format=custom`, valida el
  catálogo con `pg_restore --list`, calcula SHA-256, exige cifrado `age` en
  producción, verifica la copia fuera del host y aplica retención configurable.
- `backend/scripts/backup_restore_drill.py` sólo acepta bases locales terminadas
  en `_test`; crea evidencia sintética, restaura realmente sobre una base TEST
  vacía y verifica tablas, firma CANONICAL_V2, llave pública histórica y estado
  `clinical_sync_operations`.
- La programación, custodia de la clave, destino externo, retención autorizada y
  simulacro periódico requieren procedimiento hospitalario. Detalle: [[Pase_a_Produccion]].

## Relaciones en el Proyecto
- Es consumida, leída y modificada exclusivamente por el [[Backend]].
- En [[Pase_a_Produccion]], es de suma importancia verificar las credenciales en `.env` y asegurar la ejecución periódica de los scripts de respaldo.

## Pruebas de integración PostgreSQL

- Las suites críticas de `backend/tests/` usan PostgreSQL real; SQLite queda
  fuera de autenticación, autorización, RBAC, transacciones, concurrencia,
  firmas, biometría e integridad clínica.
- Prioridad: PostgreSQL 17 efímero con Testcontainers. Fallback: base dedicada
  cuyo nombre termina en `_test`.
- La suite aborta salvo que `APP_ENV=test`, la URL sea PostgreSQL y la base sea
  explícitamente de pruebas.
- El esquema fresco se crea mediante Alembic (`backend/alembic.ini` y
  `backend/migrations/`), no mediante `Base.metadata.create_all()`.
- La revisión incremental `4b7e2a91c6d0` agrega `biometric_challenges` y metadatos mínimos de plantilla/estado a médicos y firmantes. `9024a9c93603` permanece intacta.
- La revisión `c31f4a7d9e20` agrega `key_id`, snapshot/payload canónico, hashes de payload/PDF, versión de documento/esquema y estados TSA. También impone una sola llave FEA activa y protege el historial con trigger append-only.
- `biometric_challenges` es el almacén multi-worker: guarda hash del nonce, acción, sesión, sujeto, identidad esperada, paciente/documento, expiración y consumo. El `UPDATE ... WHERE consumed_at IS NULL` hace atómico el uso único.
- Valores biométricos históricos no vacíos quedan marcados `LEGACY_RAW` y `requiere_reenrolamiento=true`; la migración no toca el contenido de `fmd_template`.
- Cada prueba se aísla con truncado controlado; cada sesión resetea el esquema
  antes y después.
- La revisión `8f3c2d1a7b90` agrega `clinical_sync_operations` y
  `clinical_sync_attempts`. `idempotency_key` es único; el payload excluye FMD,
  challenges, tokens y secretos. Firmas, históricos y dietas pueden enlazar una
  sola evidencia local a `clinical_sync_operation_id`.
- PostgreSQL registra la intención antes del write externo. SQL Server no forma
  parte de la transacción PostgreSQL: una caída queda durablemente pendiente,
  fallida o en `REQUIRES_RECONCILIATION`, nunca simulada como atomicidad 2PC.
- Los `INSERT` de tablas clínicas con GUID usan un UUID determinista derivado de
  `operation_id` y lo consultan antes de reintentar. Los `UPDATE` por PK/clave
  natural son repetibles. Si un formato universal no expone GUID seguro, queda
  en `REQUIRES_RECONCILIATION` sin ejecutar el `INSERT`. Ese estado no participa
  en reintentos desatendidos; sólo puede revisarse de forma controlada.
- SQL Server productivo `KH_HE` se rechaza en modo test. La futura integración
  STAGING/TEST vive separada en `backend/tests/sqlserver_staging/`.
- La revisión `d4f5a6b7c8d9` agrega revocación JWT, cambio obligatorio de
  contraseña inicial y evidencia completa de auditoría. PostgreSQL bloquea
  `UPDATE` y `DELETE` de `auditoria_logs`; los eventos son append-only.
- La revisión `f7a9c2d4e6b1` liga cada operación durable a
  `request_fingerprint`, agrega evidencia del actor/fecha de reenrolamiento y
  `acquisition_id` biométrico único, normaliza duplicados activos históricos e
  impone una única firma activa por documento lógico. También protege por
  trigger el snapshot CANONICAL_V2 completado contra mutación o borrado.
- La revisión idempotente `9e2c4b6d8f10` converge instalaciones heredadas que
  conservaban tablas biométricas anteriores: agrega sólo los metadatos ausentes
  de médicos/firmantes y `expected_identity_ref`/`acquisition_id` en challenges.
  Las plantillas históricas no vacías quedan `LEGACY_RAW` y requieren
  reenrolamiento; no se convierten ni se borran.
- La revisión `b2d4f6a8c0e1` incorpora instalaciones PostgreSQL heredadas sin
  `alembic_version`. Converge columnas/tablas/índices y triggers de seguridad
  ausentes sin eliminar usuarios, plantillas, firmas ni auditorías. Antes de
  estampar `9e2c4b6d8f10` y subir a esta revisión debe existir un dump validado y
  debe ensayarse la restauración en una base separada. No aplica a SQL Server
  `KH_HE` ni abre una conexión hacia él.

Runbook y resultados: `INFRAESTRUCTURA_TEST_POSTGRES.md`.

## Evidencia FEA CANONICAL_V2

`firmas_documentos_clinicos` conserva `canonical_payload`, `payload_hash`, `key_id`, `signature_schema_version`, `document_version`, `pdf_hash`, `pdf_identifier`, `tsa_status`, `tsa_nonce`, intentos y último error. Las filas anteriores conservan `LEGACY_V1`; la migración no inventa cobertura criptográfica retroactiva.

`historial_llaves_fea.key_id` es único. `firmas_documentos_clinicos.key_id` referencia esa fila exacta. La pública histórica nunca se borra; una rotación sólo inactiva la fila vigente e inserta la nueva.

Los `GET` de lectura clínica usan `allow_create=False`: consultar pacientes,
firmas o PDFs no inserta/actualiza pacientes ERP ni registros QR. Los PDFs
generados por GET son artefactos transitorios eliminados al finalizar la
respuesta; la preparación/persistencia pertenece a un flujo mutante explícito.

---
> 🤖 *Contexto IA: nunca borrar/sobrescribir `historial_llaves_fea`; al rotar marcar `activo=False`. Ver [[Guia-Desarrollo-IA]] regla 2.*

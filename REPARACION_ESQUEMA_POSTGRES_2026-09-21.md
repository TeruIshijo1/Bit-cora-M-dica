# Reparación de esquema PostgreSQL — 2026-09-21

## Resultado

Se reparó exclusivamente `hospital_escandon_db` en PostgreSQL local. No se abrió
ninguna conexión a SQL Server `KH_HE` y no se ejecutaron operaciones sobre sus
tablas, cadenas o QR.

El error de acceso de `amendoza` era un desfase entre el código y la tabla
`usuarios`: faltaba `must_change_password`. La cuenta existía, estaba activa y
con rol `admin`; la petición fallaba antes de comprobar la contraseña.

## Resguardo y procedimiento

- Dump previo: `D:\HES_Backups\hospital_escandon_db_pre_schema_repair_20260921_092619.dump`.
- Tamaño: 5,491,899 bytes.
- SHA-256: `093e65bebee2777dc00d8e52846216c29ffe7495be1ee8af1a31bf16958d4d2e`.
- `pg_restore --list` aceptó el catálogo.
- Se restauró una copia separada y se probó primero la convergencia.
- Se añadió la revisión idempotente `b2d4f6a8c0e1`; la base heredada se estampó
  en `9e2c4b6d8f10` y se actualizó transaccionalmente hasta esa nueva cabeza.
- `alembic check` terminó sin operaciones pendientes tanto en la copia como en
  la base activa.

La restauración reveló referencias históricas huérfanas preexistentes: 9 eventos
de auditoría apuntan a usuarios ausentes y 14 traslados a pacientes ausentes.
No se borraron ni reescribieron. Las restricciones activas de la base original
se conservaron; en una restauración nueva deben incorporarse `NOT VALID` para
preservar estas filas y hacer cumplir integridad en escrituras futuras, hasta que
el hospital decida su reconciliación documental.

## Evidencia de preservación

Antes y después de la migración:

| Evidencia | Antes | Después |
|---|---:|---:|
| Usuarios | 16 | 16 |
| Médicos | 243 | 243 |
| Plantillas médicas no vacías | 37 | 37 |
| Digest agregado de plantillas | `de98c9f9c04981c0707cd0e6a9d0386c` | idéntico |
| Firmas clínicas | 67 | 67 |
| Eventos de auditoría | 473 | 473 |

Las 37 plantillas permanecen clasificadas como `LEGACY_RAW`; no son elegibles
para login hasta un reenrolamiento controlado bajo el protocolo actual. Las otras
206 cuentas médicas permanecen `SIN_BIOMETRIA`.

## Comprobación de acceso

Después del reinicio, `/health` respondió `alive`. Una solicitud de diagnóstico
para `amendoza` con contraseña deliberadamente incorrecta devolvió 401, no 500:
la consulta de la cuenta y la validación de credenciales vuelven a ejecutarse.
No se leyó, cambió ni registró la contraseña real.

La regresión PostgreSQL completa terminó con 198 pruebas y 10 subpruebas
aprobadas (332 advertencias). Tras la migración y el reinicio, la API central
respondió `alive` y el agente biométrico respondió `alive`, protocolo 2.

# FASE 3A.0 — Infraestructura PostgreSQL de pruebas

Fecha de validación: 2026-09-17.

## Estrategia elegida

Las pruebas bajo `backend/tests/` se ejecutan exclusivamente contra PostgreSQL.
La primera opción es un contenedor efímero `postgres:17-alpine` administrado por
Testcontainers. Cuando Docker no está disponible se exige
`TEST_DATABASE_URL` hacia una base dedicada cuyo nombre termine en `_test`.

En este equipo Docker no está instalado. La validación se hizo contra el
PostgreSQL 17 local usando únicamente `hospital_escandon_test`. No se abrió ni
se modificó la base de desarrollo/producción.

## Protecciones anti-producción

Antes de crear el engine o limpiar el esquema se valida todo lo siguiente:

1. `APP_ENV` es exactamente `test`.
2. La URL usa el dialecto PostgreSQL; `sqlite:///` se rechaza.
3. El nombre de base termina en `_test` (se permiten sufijos de worker como
   `_test_gw0`).

El control está en `backend/testing/database_guards.py`, se invoca desde
`backend/tests/conftest.py` y también desde `backend/database.py` cuando
`APP_ENV=test`. La limpieza vuelve a validar el destino inmediatamente antes de
ejecutar `DROP SCHEMA public CASCADE`.

La prueba automática `backend/tests/test_test_database_guards.py` cubre entorno
incorrecto, SQLite, bases operativas, PostgreSQL de test válido y rechazo de
`KH_HE`. Además se ejecutó pytest con `APP_ENV=production`: terminó con código
1 y el mensaje `Suite abortada: APP_ENV debe ser "test" antes de preparar
PostgreSQL.` antes de tocar el esquema.

## Creación, migración y limpieza

Flujo de cada sesión:

1. Testcontainers crea `hospital_escandon_test`; o el operador proporciona una
   base dedicada mediante `TEST_DATABASE_URL`.
2. Se resetea únicamente el esquema `public` del destino ya validado.
3. Alembic ejecuta `upgrade head` usando
   `backend/migrations/versions/9024a9c93603_initial_postgresql_schema.py`.
4. Cada prueba empieza y termina con `TRUNCATE ... RESTART IDENTITY CASCADE` de
   las tablas de aplicación. Los fixtures son completamente sintéticos.
5. Al finalizar se elimina el esquema de pruebas. Testcontainers también
   destruye el contenedor.

`Base.metadata.create_all()` ya no se usa en la suite crítica. En
`APP_ENV=test` tampoco se ejecuta la auto-alteración heredada de `database.py`:
Alembic es la única fuente del esquema.

La revisión inicial es una línea base para bases nuevas. No debe ejecutarse con
`upgrade` sobre una base operativa que ya contenga las tablas; su adopción en
una instalación existente requiere primero verificar paridad y hacer un
`alembic stamp` controlado. Ese pase productivo queda expresamente fuera de esta
fase y no se realizó.

Para el fallback local, `backend/scripts/create_test_database.py` crea la base
sólo después de validar el sufijo `_test`; requiere una URL administrativa
explícita y nunca elimina bases.

## Pruebas migradas y añadidas

- `backend/tests/test_p0_authorization.py`: conserva sus 16 casos de
  autenticación, autorización, RBAC y bloqueo de efectos clínicos, ahora sobre
  PostgreSQL y sin SQLite ni `create_all()`.
- `backend/tests/test_postgresql_semantics.py`: añade 9 pruebas de dialecto,
  índice único, NOT NULL, clave foránea, rollback, aislamiento entre conexiones,
  lock de fila y dos transacciones concurrentes.
- `backend/tests/test_test_database_guards.py`: añade 5 funciones de prueba
  parametrizadas para los controles PostgreSQL/SQL Server.

No se cambió la lógica de biometría, ECDSA, TSA ni la lógica clínica.

El workflow `.github/workflows/integration-postgres.yml` levanta PostgreSQL 17
con credenciales y datos sintéticos, ejecuta pytest y después `compileall`. No
contiene ni carga PHI.

## SQL Server

No se conecta automáticamente a SQL Server. Los tests existentes mantienen
mocks. El directorio `backend/tests/sqlserver_staging/` reserva una capa futura
de integración y su fixture exige `APP_ENV=test` y una base con sufijo `_test`.
`kh_database.get_kh_connection()` valida ese destino en modo test y rechaza
explícitamente `KH_HE` antes de abrir una conexión.

## Resultados antes/después

Antes: `test_p0_authorization.py` contenía 16 casos, pero reemplazaba PostgreSQL
por un archivo SQLite temporal y construía el esquema con
`Base.metadata.create_all()`. No existían pruebas de semántica PostgreSQL. No se
re-ejecutó esa variante SQLite durante esta fase.

Después, sobre PostgreSQL 17 real de pruebas:

```text
38 passed, 17 warnings, 10 subtests passed in 14.40s
```

La suite migrada aislada informó:

```text
16 passed, 16 warnings, 10 subtests passed in 6.32s
```

La comprobación `alembic check` informó:

```text
No new upgrade operations detected.
```

La compilación informó:

```text
compileall: OK
```

Las 17 advertencias son deprecaciones existentes de SQLAlchemy, Starlette,
Pydantic y SlowAPI; no son fallos de prueba.

## Comandos

Instalación:

```powershell
cd D:\Escritorio\Bitacora_HES
.\backend\venv\Scripts\python.exe -m pip install -r backend\requirements-test.txt
```

Con Docker/Testcontainers:

```powershell
$env:APP_ENV = "test"
Remove-Item Env:TEST_DATABASE_URL -ErrorAction SilentlyContinue
.\backend\venv\Scripts\python.exe -m pytest -q
```

Con PostgreSQL dedicado (sin Docker):

```powershell
$env:APP_ENV = "test"
$env:TEST_DATABASE_URL = "postgresql://usuario_test:password@localhost:5432/hospital_escandon_test"
$env:TEST_DATABASE_ADMIN_URL = "postgresql://administrador:password@localhost:5432/postgres"
.\backend\venv\Scripts\python.exe backend\scripts\create_test_database.py
.\backend\venv\Scripts\python.exe -m pytest -q
```

Validaciones adicionales:

```powershell
$env:DATABASE_URL = $env:TEST_DATABASE_URL
.\backend\venv\Scripts\python.exe -m alembic -c backend\alembic.ini upgrade head
.\backend\venv\Scripts\python.exe -m alembic -c backend\alembic.ini check
.\backend\venv\Scripts\python.exe -m compileall -q backend
```

## Archivos de esta fase

- `backend/alembic.ini`
- `.github/workflows/integration-postgres.yml`
- `backend/migrations/env.py`
- `backend/migrations/script.py.mako`
- `backend/migrations/versions/9024a9c93603_initial_postgresql_schema.py`
- `backend/testing/database_guards.py`
- `backend/tests/conftest.py`
- `backend/tests/test_p0_authorization.py`
- `backend/tests/test_postgresql_semantics.py`
- `backend/tests/test_test_database_guards.py`
- `backend/tests/sqlserver_staging/conftest.py`
- `backend/tests/sqlserver_staging/README.md`
- `backend/scripts/create_test_database.py`
- `backend/database.py`
- `backend/kh_database.py`
- `backend/requirements.txt`
- `backend/requirements-test.txt`
- `backend/.env.example`
- `pytest.ini`
- `docs/Database.md`

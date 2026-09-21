# Corrección P0 de autenticación y autorización — Fase 3A

**Fecha:** 2026-09-17  
**Alcance:** frontera JWT/roles, bypass de rutas, archivos clínicos y contención de escrituras.  
**Fuera de alcance respetado:** P0-03, P0-04, P0-05, P1-01, P1-02, algoritmo biométrico, RAW/FMD, challenge, ECDSA, cadena original, TSA, llaves y arquitectura PostgreSQL/SQL Server.

## Resultado ejecutivo

- Se corrigió el bypass lógico de `require_role()` y ahora los roles se comparan de forma canónica con denegación por defecto.
- Cada JWT se decodifica y su identidad, rol vigente y estado activo se revalidan contra PostgreSQL antes de ejecutar el endpoint.
- Se eliminó la regla pública por `startswith`, por ruta fuera de `/api` y por subcadenas `pdf`/`pdf-`.
- La exposición pública de todo `backend/static/` fue retirada. PDFs y escaneos RH ya no son resolubles por nombre bajo `/static`.
- Los 39 endpoints declarados de PDF clínico tienen una política explícita de lectura clínica.
- Las escrituras tienen una matriz central exacta por método+plantilla. Una escritura nueva o no clasificada devuelve 403.
- Se generó el inventario automático de **214 rutas**: **28 PUBLICA**, **58 AUTENTICADA**, **128 ROL_ESPECIFICO**.
- Resultado final: **16 pruebas, 16 pasan**; build frontend correcto.

No se marca P0-01 ni P0-09 como completamente resuelto en producción. Existe prueba automatizada del cierre de los bypass aquí corregidos, pero siguen pendientes la autorización horizontal paciente-profesional, la decisión funcional de cuatro rutas y pruebas de staging con PostgreSQL/SQL Server reales.

## Defectos reproducidos antes del cambio

La primera ejecución válida contra el código vulnerable fue:

```text
python -m unittest backend.tests.test_p0_authorization -v
Ran 8 tests
FAILED (failures=8)
```

Fallos reproducidos:

1. `require_role(["admin"])` permitía `enfermeria`, `usuario` y un rol inexistente (`fantasma`): los tres obtenían 200.
2. Un usuario `activo=False` conservaba acceso con un JWT no vencido.
3. El alias `/ehr/...` pasaba sin token mientras `/api/...` exigía autenticación.
4. Una ruta `/api/...` con texto `pdf` pasaba sin token y ejecutaba el handler.
5. Una escritura bajo `/ehr` sin token ejecutaba el handler y sus side effects simulados.
6. Un PDF clínico conocido bajo `/static/pdfs/...` devolvía 200 sin token.

La primera invocación con el Python global no llegó a ejecutar la suite porque no tenía FastAPI; se usó `backend/venv`. FastAPI/Starlette 0.141.1/1.6.0 requirió además `httpx2`, que quedó declarado en `backend/requirements.txt`.

## Cambios realizados

### Identidad y roles

- `backend/security.py`
  - `normalize_role()` unifica mayúsculas/espacios y el alias `Mantenimiento/Limpieza`.
  - `authenticate_token()` valida firma/expiración, resuelve la identidad vigente en BD, rechaza usuario/médico inactivo y usa el rol actual de BD, no un rol obsoleto del JWT.
  - `require_role()` ahora aplica `rol in allowed_roles` con override administrativo explícito; una lista vacía o rol desconocido falla con 403.
- `backend/main.py`
  - Eliminó la implementación duplicada vulnerable y usa las funciones de `security.py`.
  - El login por contraseña rechaza cuentas inactivas.

### Frontera de rutas

- `backend/route_policy.py`
  - Allowlist pública exacta por método+plantilla.
  - Lista exacta de shells/assets frontend que no contienen datos clínicos.
  - `READ_ROLE_POLICIES` para los 39 endpoints de PDF clínico.
  - `WRITE_ROLE_POLICIES` para todas las escrituras con permiso deducible.
  - `REQUIRES_FUNCTIONAL_DECISION` para escrituras cuyo permiso no puede deducirse con certeza.
- `GlobalAuthMiddleware`
  - No concede acceso por prefijos ni subcadenas.
  - Protege de igual forma rutas `/api`, `/ehr`, `/pacientes`, `/kh` y cualquier alias no público.
  - Resuelve la plantilla FastAPI declarada y aplica su política antes del parseo del body y antes de side effects.

### Archivos clínicos

- Se retiró `app.mount("/static", ...)`.
- Sólo `/static/logo.png` queda público mediante ruta exacta.
- `/static/pdfs/*` y `/static/escaneos_rh/*` devuelven 401 sin token y 404 incluso con token; el árbol privado no se sirve directamente.
- Se añadió `GET /api/escaneos/{escaneo_id}/archivo`, restringido a `admin`, `rh` y `sistemas`, con basename y comprobación de contención del path.
- `AdminDashboard.jsx` abre escaneos mediante Axios autenticado y un blob temporal, no mediante URL física pública.

### Inventario automático

`backend/scripts/audit_route_authorization.py` analiza el AST de `main.py` y `routers/catalogos.py`, combina las políticas centrales y falla si encuentra una escritura sin política ni bloqueo funcional explícito.

Resultado completo: [INVENTARIO_RUTAS_AUTORIZACION.md](INVENTARIO_RUTAS_AUTORIZACION.md).

## Matriz de escrituras y permisos

La matriz completa está en `INVENTARIO_RUTAS_AUTORIZACION.md`, con estas columnas:

- endpoint;
- acción;
- roles actuales/locales;
- roles esperados según código/documentación;
- PUBLICA / AUTENTICADA / ROL_ESPECIFICO;
- protección existente o faltante;
- archivo y línea.

Las políticas clínicas deducibles usan los gates existentes del frontend y dependencias backend:

- `MEDICAL_STAFF`: `admin`, `medico`, `ayudante` para prescripción, discontinuación, dieta y firma médica.
- `CLINICAL_STAFF`: `admin`, `sistemas`, `medico`, `ayudante`, `enfermeria` para operaciones de PatientDashboard cuyo reparto más granular no está documentado.
- administración/RH/sistemas conserva las listas ya declaradas por cada handler.

Esto es contención de rol, no el RBAC clínico final.

## Endpoints con permiso indeterminado

Quedan cerrados por defecto con 403 para todos los roles, incluido `sistemas`, hasta contar con decisión funcional:

| Endpoint | Estado |
|---|---|
| `PUT /api/atenciones/{folio}` | REQUIERE_DECISION_FUNCIONAL |
| `POST /api/ehr/paciente/{pt_num}/formato-crear-registro` | REQUIERE_DECISION_FUNCIONAL |
| `POST /api/ehr/paciente/{pt_num}/formato-guardar-registro` | REQUIERE_DECISION_FUNCIONAL |
| `POST /ehr/paciente/{pt_num}/formato-guardar-registro` | REQUIERE_DECISION_FUNCIONAL |

## Evidencia de no side effects al rechazar

`test_clinical_write_denies_wrong_role_before_all_side_effects` demuestra para una escritura clínica rechazada:

- snapshot de todas las tablas SQLite sin cambios (sustituto aislado de PostgreSQL en la suite);
- mock de escritura SQL Server no invocado;
- generador PDF no invocado;
- firma ECDSA no invocada.

Además, los probes `/ehr` y `pdf` demuestran que el handler ni siquiera se ejecuta sin token. No se conectó a PostgreSQL ni SQL Server reales durante las pruebas.

## Pruebas que pasan después

Comando final:

```text
backend\venv\Scripts\python.exe -m unittest discover -s backend\tests -v
Ran 16 tests in 0.181s
OK
```

Casos cubiertos:

1. admin → endpoint admin permitido;
2. rh → endpoint rh permitido;
3. sistemas → endpoint sistemas permitido;
4. enfermería/básico/rol inexistente → endpoint admin 403;
5. petición sin token 401;
6. JWT inválido 401;
7. JWT expirado 401;
8. usuario desactivado 401/403 antes del endpoint;
9. alias `/ehr` con la misma autenticación que `/api`;
10. texto `pdf` no evita autenticación;
11. allowlist no acepta variantes por prefijo;
12. PDFs y escaneos clínicos no se sirven desde `/static`;
13. endpoint PDF exige rol clínico;
14. controlador RH exige rol apropiado;
15. rol incorrecto en escritura no produce side effects;
16. rutas indeterminadas fallan cerradas y toda escritura declarada está clasificada.

Otras verificaciones:

```text
backend\venv\Scripts\python.exe backend\scripts\audit_route_authorization.py
Inventario generado
Total=214 PUBLICA=28 AUTENTICADA=58 ROL_ESPECIFICO=128
```

```text
backend\venv\Scripts\python.exe -m compileall -q backend
exit 0
```

```text
cd frontend; npm run build
721 modules transformed
✓ built in 543ms
exit 0
```

Vite conserva la advertencia preexistente de chunks mayores de 500 kB. `git diff --check` no queda limpio por whitespace preexistente en numerosos archivos ya modificados antes de esta fase; no se hizo una limpieza cosmética masiva.

## Archivos de esta fase

- `backend/main.py`
- `backend/security.py`
- `backend/route_policy.py` (nuevo)
- `backend/scripts/audit_route_authorization.py` (nuevo)
- `backend/tests/test_p0_authorization.py` (nuevo)
- `backend/requirements.txt`
- `.gitignore` (excepción limitada para versionar `backend/tests/test_*.py`)
- `frontend/src/pages/AdminDashboard.jsx`
- `docs/API-Endpoints.md`
- `docs/Backend.md`
- `docs/Formatos-PDF.md`
- `INVENTARIO_RUTAS_AUTORIZACION.md` (generado)
- `CORRECCION_P0_AUTORIZACION.md`

## Riesgos abiertos

1. **Autorización horizontal:** aún no se valida relación médico/paciente, equipo tratante, episodio o servicio. Por ello P0-09 queda contenido por rol, no cerrado funcionalmente.
2. **Roles clínicos amplios:** `CLINICAL_STAFF` replica el gate actual de PatientDashboard. Enfermería/sistemas requieren una decisión funcional por acción para reducir privilegios.
3. **Portal QR público:** el HTML de verificación permanece en allowlist por contrato actual. Debe migrarse a referencias opacas no enumerables y revisar qué metadatos del paciente puede mostrar.
4. **Descargas en pestaña nueva:** enlaces frontend antiguos que dependan de navegación directa a PDF ya no llevarán Bearer y recibirán 401. Deben migrarse progresivamente al patrón Axios+blob; el flujo RH ya fue migrado.
5. **Fotos de perfil:** las URLs históricas `/static/uploads/...` ya no se sirven desde el webroot; el frontend puede mostrar imágenes rotas hasta migrarlas a un controlador autenticado o declarar formalmente ese recurso como público.
6. **Validación de infraestructura:** falta ejecutar la matriz contra staging con PostgreSQL y SQL Server instrumentados. La suite actual usa SQLite temporal y mocks para garantizar aislamiento.
7. **Override admin:** se conserva la semántica histórica de que `admin` puede satisfacer cualquier `require_role`; requiere confirmación funcional para separación de funciones clínicas.
8. Los demás P0/P1 de biometría, criptografía, TSA y atomicidad permanecen abiertos y no fueron modificados.

## `git diff --stat`

El árbol ya estaba ampliamente modificado antes de esta fase. La salida global exacta al cierre (no atribuye todos esos cambios a esta corrección y omite archivos untracked) es:

```text
81 files changed, 28694 insertions(+), 8641 deletions(-)
```

Para los dos archivos tracked que estaban limpios al inicio y que esta fase modificó de forma exclusiva:

```text
 backend/requirements.txt |  1 +
 backend/security.py      | 51 +++++++++++++++++++++++++++++++++++++-----------
 2 files changed, 41 insertions(+), 11 deletions(-)
```

Los archivos nuevos no aparecen en `git diff --stat` hasta añadirse al índice: `route_policy.py` (194 líneas), `audit_route_authorization.py` (228), `test_p0_authorization.py` (305) e `INVENTARIO_RUTAS_AUTORIZACION.md` (227). No se hizo commit, push ni force-push.

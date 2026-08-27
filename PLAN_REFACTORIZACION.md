# 🏗️ PLAN MAESTRO DE REFACTORIZACIÓN: DESCOMPOSICIÓN DEL MONOLITO
## Plataforma Bitácora Médica HE - Hospital Escandón

---

### 📋 1. Diagnóstico y Objetivo Pragmático

#### Estado Actual
* **Archivo central:** `backend/main.py` con **+5,800 líneas de código**.
* **Problema:** En un solo archivo coexisten configuración HTTP, middlewares, modelos Pydantic, generación de PDFs en ReportLab, criptografía FEA (NOM-024), conexiones a dos bases de datos (PostgreSQL y SQL Server), algoritmos de búsqueda y más de 45 endpoints.
* **Meta:** Reestructurar el backend en módulos cohesivos (`routers/` y `services/`) sin alterar contratos de API ni romper la compatibilidad con el frontend React, permitiendo mantenimiento ágil y seguro por desarrolladores e IA.

---

### 📂 2. Arquitectura Modular Propuesta

```text
backend/
├── core/                       # Núcleo de configuración y seguridad
│   ├── __init__.py
│   ├── config.py               # Variables de entorno y constantes globales
│   ├── security.py             # Helpers de JWT y get_current_user / require_role
│   └── middlewares.py          # GlobalAuthMiddleware y SecurityHeadersMiddleware
│
├── services/                   # Capa de Lógica de Negocio y Operaciones Pesadas
│   ├── __init__.py
│   ├── auth_service.py         # Login admin, autenticación biométrica y switch de roles
│   ├── fea_service.py          # Criptografía NOM-024, firma digital y sellado TSA
│   ├── pdf_service.py          # Motores de renderizado ReportLab (87/01, 32/01, EED, Bitácora)
│   ├── ehr_service.py          # Orquestación de expediente clínico y conciliación
│   └── export_service.py       # Generación de reportes analíticos y libros Excel
│
├── routers/                    # Controladores HTTP (FastAPI APIRouters)
│   ├── __init__.py
│   ├── auth.py                 # /api/auth/*
│   ├── catalogos.py            # /api/catalogos/*
│   ├── camas.py                # /api/camas/*
│   ├── pacientes.py            # /api/pacientes/*
│   ├── medicos.py              # /api/medicos/*
│   ├── atenciones.py           # /api/atenciones/*
│   ├── agenda.py               # /api/agenda/*
│   ├── ehr.py                  # /api/ehr/* (Clínica, Notas, Prescripciones, Alergias)
│   ├── escaneos.py             # /api/escaneos/*
│   └── admin.py                # /api/usuarios, /api/analytics, /api/auditoria, /api/backup
│
├── database.py                 # Conexión SQLAlchemy PostgreSQL
├── kh_database.py              # Conexión y consultas SQL Server (KH_HE)
├── models.py                   # Modelos ORM SQLAlchemy
├── schemas.py                  # Esquemas Pydantic v2
└── main.py                     # Entrypoint ligero (~120 líneas) con app.include_router()
```

---

### 🔌 3. Detalle de Controladores (`routers/`)

| Archivo Router | Prefijo / Tags | Endpoints Principales Migrados |
|---|---|---|
| `routers/auth.py` | `/api/auth` | `/login/admin`, `/login/biometric`, `/impersonate` |
| `routers/catalogos.py` | `/api/catalogos` | `/areas`, `/tipos`, `/formatos` (CRUD) |
| `routers/camas.py` | `/api/camas` | `/`, `/ocupacion`, `/paciente/{pt_num}`, `/{id}/limpieza` |
| `routers/pacientes.py` | `/api/pacientes` | `/`, `/{id}`, `/{id}/alta`, `/altas`, `/{id}/traslados`, `/{id}/journey` |
| `routers/medicos.py` | `/api/medicos` | `/`, `/{id}`, `/list`, `/{id}/huella`, `/{id}/datos`, `/{id}/permisos`, `/{id}/procedimientos_frecuentes` |
| `routers/atenciones.py` | `/api/atenciones` | `/pre-captura`, `/pendientes/{id}`, `/historial/{id}`, `/mis-registros`, `/global`, `/todas`, `/exportar`, `/firmar-lote`, `/{folio}`, `/{folio}/pdf`, `/{folio}/reaperturar`, `/{folio}/autorizar` |
| `routers/agenda.py` | `/api/agenda` | `/citas`, `/citas/{id}`, `/citas/paciente/{id}` |
| `routers/ehr.py` | `/api/ehr` | `/paciente/{pt_num}`, `/pacientes/buscar`, `/signos-vitales`, `/medicamentos`, `/dieta-cuidados`, `/alergias`, `/nota-urgencias`, `/consentimiento-32-01`, `/consentimiento-eed`, `/pdf-*`, `/firmas`, `/historial-auditoria` |
| `routers/escaneos.py` | `/api/escaneos` | CRUD de expedientes escaneados de Recursos Humanos y firmas de contrato |
| `routers/admin.py` | `/api` | `/usuarios` (CRUD), `/analytics`, `/auditoria`, `/backup` |

---

### 🧠 4. Capa de Servicios de Negocio (`services/`)

1. **`services/auth_service.py`**:
   * Valida credenciales contra `models.Usuario` con bcrypt.
   * Invoca el microservicio biométrico DigitalPersona para cotejo 1:N de huellas `FMD`.
   * Emite tokens JWT con claims de roles y permisos granulares.

2. **`services/fea_service.py`**:
   * Encapsula la generación de pares de llaves elípticas SECP256k1 para nuevos médicos.
   * Cifra llaves privadas con KEK derivada vía HKDF con huella dactilar.
   * Genera firmas digitales ECDSA-SHA256 y tramita sellos de tiempo RFC 3161 (TSA).

3. **`services/pdf_service.py`**:
   * Contiene los motores ReportLab para:
     * Nota de Urgencias (Formato 87/01 con hasta 3 notas consecutivas).
     * Consentimiento Informado ETE (Formato 32/01).
     * Consentimiento y Monitoreo EED (Ecocardiograma de Estrés con Dobutamina).
     * Hoja de Atención Médica General.
   * Incrusta cadenas originales, hashes SHA-256, sellos digitales y códigos QR forenses.

4. **`services/ehr_service.py`**:
   * Orquesta la conciliación transaccional híbrida (escritura en SQL Server `KH_HE` y registro inmutable en PostgreSQL `firmas_documentos_clinicos` e `historico_notas_clinicas`).

---

### 🛡️ 5. Secuencia y Orden Seguro de Extracción

Para evitar romper la plataforma en producción, la refactorización se ejecutará en **5 pasos ordenados por riesgo creciente**:

1. **Paso 1: Extracción del Núcleo (`core/`) y Schemas**
   * **Qué mover:**
     * `core/config.py` (variables de entorno, constantes de algoritmos).
     * `core/security.py` (`get_current_user`, `require_role`, `create_access_token`).
     * `core/middlewares.py` (`GlobalAuthMiddleware`, `SecurityHeadersMiddleware`).
     * Consolidar todos los esquemas Pydantic inline en `schemas.py`.
   * **Impacto:** Cero cambio funcional en las rutas; todas las dependencias de seguridad se vuelven accesibles limpiamente.
   * **Riesgo:** Bajo. Importaciones circulares prevenidas desde la raíz.

2. **Paso 2: Routers de Catálogos, Configuración y Soporte**
   * **Qué mover:** `routers/catalogos.py`, `routers/escaneos.py`, `routers/agenda.py`, `routers/camas.py`.
   * **Impacto:** Rutas de lectura y CRUD estándar aisladas de `main.py`.
   * **Riesgo:** Bajo. Fácilmente validables con pruebas unitarias.

3. **Paso 3: Extracción de Servicios Complejos (`services/`)**
   * **Qué mover:** Extraer funciones de generación de PDF ReportLab (~1,500 líneas) a `services/pdf_service.py` y criptografía a `services/fea_service.py`.
   * **Impacto:** Reduce `main.py` a casi la mitad sin tocar los endpoints HTTP.
   * **Riesgo:** Medio. Verificar rutas de fuentes tipográficas y logos estáticos.

4. **Paso 4: Routers Clínicos y Transaccionales**
   * **Qué mover:** `routers/auth.py`, `routers/pacientes.py`, `routers/medicos.py`, `routers/atenciones.py`, `routers/admin.py`, `routers/ehr.py`.
   * **Impacto:** Controladores limpios de 50 a 150 líneas cada uno que delegan a `services/` y `kh_database.py`.
   * **Riesgo:** Medio-Alto si no se inyectan correctamente `Depends(get_db)` y `Depends(get_current_user)`.

5. **Paso 5: Adelgazamiento Final de `main.py`**
   * **Qué queda en `main.py`:**
     * Instanciación de `FastAPI()`.
     * Registro de Middlewares (`GlobalAuthMiddleware`, `CORSMiddleware`, `SecurityHeadersMiddleware`).
     * Montaje de archivos estáticos (`/static`).
     * Registro limpio de routers vía `app.include_router(...)`.
     * Montaje del SPA de frontend (`serve_frontend`).
   * **Resultado:** `main.py` pasa de **5,800 líneas** a menos de **150 líneas legibles**.

---

### ⚠️ 6. Matriz de Riesgos Principales y Mitigaciones Técnicas

| Módulo a Extraer | Riesgo Principal | Mitigación Técnica Obligatoria |
|---|---|---|
| **`core/security.py`** | Importaciones circulares entre `models`, `database` y `security`. | `security.py` solo importa `models` y `schemas`; nunca importa routers ni `main.py`. |
| **`GlobalAuthMiddleware`** | Que el middleware intercepte o bloquee erróneamente rutas al montar routers. | Mantener la lista blanca de rutas públicas (`/docs`, `/openapi.json`, `/api/auth/login`) centralizada en `core/config.py`. |
| **`services/pdf_service.py`** | Rutas relativas rotas hacia logos (`static/uploads/`, `logo.png`). | Usar rutas absolutas normalizadas con `os.path.abspath(os.path.join(os.path.dirname(__file__), "../static"))`. |
| **`routers/ehr.py`** | Pérdida de transaccionalidad al guardar en SQL Server + PostgreSQL simultáneamente. | Mantener bloques `try/except` con `db.rollback()` local si la llamada a `kh_database` falla con `HTTPException(503)`. |
| **Pydantic Validation Schemas** | Schemas definidos inline en `main.py` que no se encuentren en `schemas.py`. | Mover todos los modelos (`SignosVitalesInputSchema`, `PrescribirMedicamentoInputSchema`, etc.) a `schemas.py` antes de mover las rutas. |

---

### 🧪 7. Protocolo de Validación por Módulo (Smoke Tests)

A cada extracción de router se ejecutará de forma inmediata:
1. `python -m py_compile backend/routers/{nuevo_router}.py` (Sintaxis y tipado).
2. Verificación de carga en FastAPI `TestClient` comprobando que los endpoints responden con su status code esperado.
3. Validación de preflight CORS `OPTIONS` y autorización JWT `Bearer <token>` no interrumpidas.

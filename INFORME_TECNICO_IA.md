# 🏥 INFORME TÉCNICO DE AUDITORÍA INTEGRAL: BITÁCORA MÉDICA HES (MediReg HES)

**Fecha de Auditoría:** 27 de Agosto de 2026  
**Auditor Senior:** Antigravity AI Code Auditor (Especialista en HealthTech, Red Team, Interoperabilidad Clínica y Arquitectura de Datos)  
**Proyecto Evaluado:** Bitácora Médica HES (Hospital Escandón)  
**Marco Normativo de Referencia:** NOM-004-SSA3-2012 (Expediente Clínico), NOM-024-SSA3-2012 (Sistemas de Información de Registro Electrónico para la Salud), RFC 3161 (Time-Stamp Protocol), OWASP Top 10 API Security.

---

## 📋 1. RESUMEN EJECUTIVO Y MAPEO DE ARQUITECTURA

### 1.1 Arquitectura General del Sistema
La aplicación **Bitácora Médica HES** es una solución hospitalaria híbrida diseñada para digitalizar la captura de atenciones médicas, notas SOAP de evolución de urgencias, consentimientos informados (32/01 y EED), régimen dietético y prescripciones de fármacos en el **Hospital Escandón**.

* **Frontend:** SPA en React 18 + Vite + Tailwind CSS. Maneja la interfaz de usuario de EHR (`PatientDashboard`, `CamasDashboard`, `CapturaEnfermeria`, `AdminDashboard`, `FirmaExpress`).
* **Backend API:** FastAPI (Python 3.10+) estructurado casi en su totalidad dentro de un único archivo monolítico (`backend/main.py` de más de 5,700 líneas).
* **Bases de Datos Híbridas:**
  1. **PostgreSQL Local (`hospital_escandon_db`):** Almacena usuarios, catálogos, registros de atenciones locales, historial inmutable de notas (`historico_notas_clinicas`), firmas biométricas con llaves asimétricas (`firmas_documentos_clinicos`), citas y auditoría.
  2. **SQL Server Central (`KH_HE`):** Sistema hospitalario maestro (ERP Vertical) que almacena el censo hospitalario, signos vitales (`PTVS`), medicamentos (`PTDG`), notas de urgencia (`MR_NE_URG`) y consentimientos informados (`MR_CI_*`).
* **Mecanismo Criptográfico:** Implementa Firma Electrónica Avanzada (FEA) basada en curvas elípticas ECDSA (SECP256R1) y cifrado simétrico Fernet para las llaves privadas de los médicos, complementado con sellado de tiempo RFC 3161.

---

## 🎯 2. LOS 10 ARCHIVOS MÁS CRÍTICOS DEL PROYECTO

| # | Archivo | Justificación Técnica de Criticidad |
|---|---|---|
| 1 | `backend/main.py` | **Monolito de >5,700 líneas.** Concentra fallos críticos de Broken Access Control (IDOR), endpoints sin autenticación JWT, lógica de negocio mezclada con ruteo y hardcoded secrets. |
| 2 | `backend/kh_database.py` | **Acceso directo a Base de Datos Hospitalaria Central.** Ejecuta consultas SQL crudas con pyodbc, interpolación de límites en f-strings, fallbacks con datos mockeados y falta de transaccionalidad distribuida. |
| 3 | `backend/crypto_fea.py` | **Módulo de Firma Electrónica Avanzada (NOM-004/NOM-024).** Maneja generación y descifrado de llaves ECDSA. Presenta un mecanismo de auto-regeneración que destruye la validez forense de firmas pasadas y fallback a cédula pública para derivar la KEK. |
| 4 | `backend/vertical_signer.py` | **Integración externa con ERP Vertical.** Contiene cookies de sesión de producción hardcodeadas, código de autorización fijo (`123456`) y deshabilita la verificación de certificados SSL (`verify=False`). |
| 5 | `backend/models.py` | **Definición de Esquemas Relacionales.** Falta de índices compuestos en tablas de alto volumen (`atenciones_medicas`, `firmas_documentos_clinicos`), riesgo de registros huérfanos y campos JSON sin tipado ni esquema estricto. |
| 6 | `backend/database.py` | **Gestor de Conexiones SQLAlchemy.** Ejecuta sentencias DDL directas (`ALTER TABLE`) sin control de versiones ni transacciones de migración (Alembic ausente), mezclando lógica SQLite y PostgreSQL en runtime. |
| 7 | `backend/seed.py` | **Poblador Inicial de Datos.** Almacena contraseñas administrativas y de personal médico en texto plano dentro del código fuente con ejecución automática. |
| 8 | `backend/pdf_engine_v2.py` | **Motor de Renderizado Clínico Oficial.** Manipula directamente buffers y archivos en disco local sin validación de colisiones ni sanitización de rutas para concurrencia masiva. |
| 9 | `backend/tsa_client.py` | **Cliente Sellado de Tiempo RFC 3161.** Realiza peticiones HTTP bloqueantes a servidores públicos externos (`freetsa.org`) dentro del hilo de procesamiento. |
| 10 | `frontend/src/api.js` | **Cliente HTTP Frontend.** No implementa interceptor global de token ni manejo automático de expiración (401 Refresh), dejando la seguridad delegada manualmente en cada componente. |

---

## 🚨 3. AUDITORÍA DE SEGURIDAD (RED TEAM REVIEW)

### 3.1 Matriz de Vulnerabilidades Encontradas

| Vulnerabilidad | Archivo | Línea Aprox. | Nivel de Riesgo | Solución Propuesta |
|---|---|---|---|---|
| **Broken Access Control (IDOR Extremo):** Rutas de expediente EHR, notas, signos vitales y PDFs no exigen autenticación ni verifican que el usuario sea el médico asignado o paciente correspondiente. | `backend/main.py` | `2859`, `2903`, `3083`, `3611`, `3731`, `4087`, `5011`, `5061`, `5623` | **CRÍTICO** | Implementar un middleware de autenticación global obligatorio en `/api/*` y validar autorización basada en contexto (ABAC/RBAC) verificando si el usuario tiene relación terapéutica con el paciente. |
| **Bypass de Modificación de Atenciones (IDOR):** Endpoint `PUT /api/atenciones/{folio}` permite a cualquier actor anónimo alterar el tipo de atención médica sin token. | `backend/main.py` | `1795-1810` | **CRÍTICO** | Agregar `Depends(get_current_user)` y verificar que el `folio` pertenezca al usuario solicitante o rol supervisor autorizado. |
| **Exposición Pública de Historiales de Médicos:** Endpoints `/api/atenciones/pendientes/{medico_id}` e `/historial/{medico_id}` no tienen autenticación. | `backend/main.py` | `1431-1456` | **ALTO** | Proteger con `get_current_user` y validar que `current_user.id == medico_id` o `current_user.rol == 'admin'`. |
| **JWT Secret Hardcodeado y Duración Excesiva:** Se utiliza `"hospital_escandon_super_secret"` quemado en código con expiración de 12 horas (720 min). | `backend/main.py` | `85-89` | **CRÍTICO** | Forzar lectura de `SECRET_KEY` criptográficamente seguro desde variables de entorno con fallo al inicio si no existe. Reducir vida útil a 15-30 min con Refresh Tokens. |
| **Credenciales de Producción y Desactivación de SSL:** En `vertical_signer.py` se tienen cookies `.ASPXAUTH` quemadas y `verify=False` en peticiones HTTPS. | `backend/vertical_signer.py` | `8-9`, `88` | **CRÍTICO** | Extraer credenciales a bóveda de secretos (`.env`) y activar estrictamente la validación de certificados TLS/CA institucionales (`verify=True`). |
| **Inyección SQL Potencial en Limit Clause:** Inserción de variable `{limit}` mediante f-string en consulta T-SQL. | `backend/kh_database.py` | `2169` | **MEDIO** | Validar que `limit` sea un entero positivo y forzar casteo explícito `SELECT TOP (?)` o sanitización paramétrica. |
| **Destrucción Masiva de Registros Médicos:** Endpoint `/api/clean-records` permite borrar atenciones, notas y eliminar archivos PDF físicos con `os.remove()`. | `backend/main.py` | `2693-2772` | **CRÍTICO (LEGAL)** | **Eliminar por completo este endpoint.** La NOM-004-SSA3-2012 prohíbe la destrucción de expedientes clínicos. |
| **Fuga de Credenciales en Código Fuente:** Passwords de administrador, RH, médicos y enfermería en texto plano en el seeder. | `backend/seed.py` | `18-22`, `38-62` | **ALTO** | Eliminar contraseñas predeterminadas del repositorio; requerir creación del primer superusuario mediante CLI en el despliegue inicial. |
| **Degradación de Seguridad Criptográfica FEA:** Si el médico no tiene huella, la KEK de Fernet se deriva de la Cédula Profesional (dato público). | `backend/crypto_fea.py` | `63-65`, `87-88`, `148` | **ALTO** | Prohibir derivación criptográfica a partir de datos públicos; requerir obligatoriamente factor biométrico o certificado X.509 (.cer/.key PKCS#8) con frase de paso. |

---

## 🩺 4. AUDITORÍA DE REGLAS DE NEGOCIO MÉDICO

### 4.1 Integridad de Datos en Prescripción y Farmacoterapia
* **Ausencia de Validación Farmacológica:** En `prescribir_medicamento_biometrico` (`backend/main.py:3741`), los campos de dosis (`amount`), unidad de medida (`uom`) y frecuencia son cadenas de texto abiertas sin validación contra catálogo de fármacos autorizados (COFEPRIS/Vademécum). No existen alertas de sobredosificación ni verificación cruzada contra las alergias activas del paciente registradas en la tabla `PTAL`.
* **Riesgo Clínico:** Un médico podría prescribir accidentalmente un fármaco contraindicado para una alergia existente (ej. Penicilina) sin que el backend genere un bloqueo o advertencia de seguridad clínica.

### 4.2 Ciclo de Vida y Estados de Documentos Clínicos
* **Edición Directa en Base de Datos Central:** Si bien en PostgreSQL se creó la tabla inmutable `HistoricoNotaClinica` (NOM-024), en SQL Server (`backend/kh_database.py:1440-1480`) la nota médica original en `MR_NE_URG` se sobrescribe mediante `UPDATE` directo (`UPDATE MR_NE_URG SET S_SUBJETIVO1 = ? ... WHERE PTNum = ?`).
* **Inexistencia de Máquina de Estados Médica Formal:** Los documentos no manejan estados médicos tradicionales (`BORRADOR` ➔ `FIRMADO_TITULAR` ➔ `CO_FIRMADO_MIP` ➔ `CERRADO_NO_MODIFICABLE`). La reapertura y modificación de atenciones se permite sin un flujo de validación médica por parte del Comité Hospitalario.

### 4.3 Trazabilidad y Logs de Auditoría
* **Logs Desconectados del Contexto de Usuario:** En las prescripciones de medicamentos y dietas (`main.py:3889`, `main.py:4389`), el `usuario_id` en `AuditoriaLog` se almacena como `None`, delegando la autoría únicamente al match biométrico en memoria sin registrar la identidad de la sesión HTTP web que envió la transacción.
* **IPs Desactualizadas:** Múltiples inserciones en `AuditoriaLog` registran `ip_origen=None` o `"127.0.0.1"` al no inyectar el objeto `Request` de FastAPI.

---

## 🏗️ 5. VIDA ÚTIL, DEUDA TÉCNICA Y PATRONES DE DISEÑO

### 5.1 Fat Controllers y Acoplamiento Extremo
El archivo `backend/main.py` aglutina todas las capas de la aplicación (presentación, negocio, datos y generación binaria).

#### ❌ Las 5 Peores Funciones / Bombas de Tiempo del Proyecto:

1. **`get_pacientes()` (`backend/main.py:601-843`):**
   * Endpoint GET que realiza sincronización masiva HTTP/ODBC y escrituras en base de datos en cada petición. Si 20 usuarios abren la vista, el backend colapsa la BD central.
2. **`generar_comprobante_pdf()` (`backend/main.py:1813-1910`):**
   * Invocación sincrónica de Microsoft Word vía OLE/COM en Windows (`docx2pdf_convert`). Incompatible con Linux/Docker y propenso a congelar el proceso ante concurrencia.
3. **`firmar_documento()` - Regeneración Destructiva de Llaves (`backend/crypto_fea.py:91-106`):**
   * Si la llave KEK cambia (por ejemplo al actualizar huella), se genera un nuevo par de llaves ECDSA y se sobreescribe el anterior, invalidando permanentemente todas las firmas históricas del médico.
4. **`clean_records()` (`backend/main.py:2693-2772`):**
   * Borrado masivo físico de expedientes clínicos y PDFs de disco con `os.remove()`, violando la NOM-004-SSA3-2012.
5. **`check_and_add_columns()` (`backend/database.py:34-85`):**
   * Migraciones empíricas en tiempo de arranque con captura silenciosa de excepciones (`except: pass`), ocultando fallos de esquema.

---

## 🗄️ 6. AUDITORÍA DE BASE DE DATOS (DBA REVIEW)

### 6.1 Problema de Consultas N+1 (Lazy Loading)
* **Iteraciones en Exportación:** En `backend/main.py:1591-1600`, la función `exportar_atenciones` ejecuta una consulta base `db.query(models.AtencionMedica)` y luego itera sobre cada registro llamando a `a.medico.nombre_completo` y `a.paciente.nombre_completo`. Con miles de registros se disparan miles de consultas adicionales.
  * **Solución:** Utilizar `joinedload` de SQLAlchemy:
    ```python
    query = db.query(models.AtencionMedica).options(
        joinedload(models.AtencionMedica.medico),
        joinedload(models.AtencionMedica.paciente)
    )
    ```

### 6.2 Falta de Índices Compuestos Críticos
En `backend/models.py` faltan índices en columnas sometidas a filtros constantes:
1. `atenciones_medicas`: Crear índice compuesto `(medico_id, fecha_realizacion, estatus_pago)` para acelerar consultas de pendientes e historial.
2. `firmas_documentos_clinicos`: Crear índice compuesto `(pt_num, codigo_formato, evolution_slot, estado)` para consultas instantáneas en el renderizador PDF.
3. `historico_notas_clinicas`: Crear índice en `(pt_num, codigo_formato, fecha_registro)`.
4. `medicos.medico_asignado_id`: Agregar `index=True` para acelerar relaciones jerárquicas entre médicos titulares y ayudantes.

### 6.3 Riesgo Crítico de Transacciones Distribuidas (Two-Phase Commit / Atómica)
* **Problema:** El sistema realiza escrituras secuenciales no atómicas en dos motores de bases de datos distintos (SQL Server y PostgreSQL).
* **Escenario de Fallo:** Si PostgreSQL se cae o lanza un error de restricción después de escribir en SQL Server, el medicamento/nota queda guardado en el hospital pero sin firma ni registro de auditoría en la Bitácora local.
* **Solución:** Implementar Outbox Pattern o lógica de compensación inmediata para revertir cambios en SQL Server si el commit local en PostgreSQL falla.

---

## 🛠️ 7. PLAN DE ACCIÓN Y RECOMENDACIONES PRIORITARIAS

1. **Inmediato (P0 - Seguridad & Legal):**
   - Instalar un Middleware global de autenticación JWT en FastAPI para proteger el 100% de los endpoints bajo `/api/ehr/*`, `/api/pacientes/*`, `/api/camas/*` y `/api/atenciones/*`.
   - Eliminar el endpoint `/api/clean-records` y remover credenciales quemadas en `seed.py` y `vertical_signer.py`.
   - Configurar `SECRET_KEY` y `HES_HMAC_SECRET` obligatorios desde el `.env`.
2. **Corto Plazo (P1 - Integridad & Arquitectura):**
   - Migrar la generación de comprobantes Word/COM (`docx2pdf`) a motores nativos multiplataforma en Python (ReportLab / WeasyPrint).
   - Separar el monolito `main.py` en una arquitectura por capas: `routers/`, `services/`, `repositories/` y `schemas/`.
   - Implementar Alembic para migraciones formales de base de datos.
3. **Mediano Plazo (P2 - Calidad Clínica & DB):**
   - Incorporar catálogo de fármacos y validación de dosis / interacciones alérgicas en las prescripciones.
   - Optimizar consultas con `joinedload` e indexar llaves foráneas e historiales clínicos.
   - Implementar versionado de llaves públicas FEA para no invalidar firmas históricas ante rotaciones.
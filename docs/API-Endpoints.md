---
aliases: [API REST, Endpoints, Contrato API]
tags: [hes/backend, hes/frontend, hes/arquitectura]
tipo: modulo
modulo: api
codigo_fuente:
  - backend/main.py
  - backend/security.py
  - backend/routers/catalogos.py
  - frontend/src/api.js
  - frontend/src/hooks/useQueries.js
actualizado: 2026-09-21
relacionados:
  - "[[Backend]]"
  - "[[Frontend]]"
  - "[[Seguridad-FEA]]"
  - "[[Database]]"
---

# API-Endpoints

Contrato REST entre [[Frontend]] y [[Backend]]. Auth global JWT Bearer + roles.

## Base
- `main.py` (~12k líneas): orquestador + middlewares (`TrustedHostMiddleware`, CORS estricto, `GlobalAuthMiddleware`, `slowapi` rate-limit) + **muchos endpoints inline** + routers modulares.
- `routers/catalogos.py`: áreas, tipos de atención, formatos autorizados.
- `frontend/src/api.js`: cliente Axios. `useQueries.js`: caché TanStack.

## Auth y roles
- JWT HS256 (`security.py`), `require_role("admin" | "enfermeria" | "rh" | "sistemas" | "trabajo_social" | "medico")`. La identidad, el rol vigente y el estado activo se revalidan contra PostgreSQL en cada petición.
- `AuthContext.jsx`: sesión global, permisos por módulo (`permisos_modulos` JSON), formatos permitidos por usuario/médico.
- Rutas públicas: allowlist exacta por método+plantilla en `backend/route_policy.py` (login, challenge, portal HTML de verificación, documentación y assets frontend concretos). No existen excepciones por prefijo ni por texto `pdf`; todo lo demás exige Bearer.
- Toda escritura `POST`/`PUT`/`PATCH`/`DELETE` requiere una entrada explícita en `WRITE_ROLE_POLICIES`; una ruta nueva o indeterminada falla cerrada con 403.
- `static/` no está montado como webroot. PDFs clínicos y escaneos RH sólo se entregan por controladores autorizados; `/api/escaneos/{id}/archivo` exige `admin`, `rh` o `sistemas`.

## Dominios (verificar en `main.py` con `@app.api_route`)
- `POST /api/auth/login` · `GET /api/auth/me`
- `/api/catalogos/*` — áreas, tipos atención, formatos (`routers/catalogos.py`)
- `/api/pacientes/*` — CRUD + búsqueda (consumido por `PatientSearchModal`)
- `/api/atenciones/*` — episodios, notas, evolución
- `/api/ehr/*` — expediente: alergias (`DIS_AL`), dietas, medicamentos, timeline
- `/api/biometria/*` — challenge, enrol, match, firma FEA
- `/api/formatos/*` — generación PDF vía `pdf_service` → [[Formatos-PDF]]
- `/api/farmacia/*`, `/api/camas/*`, `/api/agenda/*` — operación
- `/api/admin/*` — usuarios, roles, `auditoria_logs`
- `GET /health` — liveness del proceso, sin dependencias ni secretos.
- `GET /readiness` — PostgreSQL obligatorio; reporta por separado SQL Server,
  biometría, TSA y capacidad. TSA pendiente no derriba por sí sola el proceso.
- `GET /api/operational/metrics` — instrumentación mínima protegida: HTTP 5xx,
  fallos DB/biometría, estados clinical sync, TSA y disco.
- `POST /api/auth/logout` — revoca inmediatamente el `jti` del token activo.
- `POST /api/auth/change-password` — cambio propio; obligatorio tras bootstrap o
  reset administrativo antes de usar otras rutas.
- `POST /api/pacientes/sincronizar-kh` — sincronización explícita del censo;
  `GET /api/pacientes` es estrictamente de solo lectura.
- `GET /api/clinical-sync/operations/{operation_id}` — estado durable sin
  exponer payload clínico ni errores internos.
- `POST /api/clinical-sync/reconcile` — reintento acotado para admin/sistemas.
- Portal HTML, estado y descarga `/verificar*` — verificación QR pública sólo
  mediante `id`/`doc_uuid` opaco `v1_*` de alta entropía y coincidencia exacta.
  Folio, paciente, formato o slot no sirven como identificadores públicos y la
  respuesta pública no expone nombre, edad ni expediente.

## Convenciones
- Errores centralizados en frontend: `useApiError.js`.
- Paginación/filtros por query params; respuestas Pydantic v2 (`schemas.py`).
- Escrituras duales aceptan `Idempotency-Key`. `SYNCED` responde 200/201;
  pendiente recuperable o incierta responde 202 con `operation_id`; fallo
  permanente responde 5xx sanitizado y conserva evidencia.
- Cada `Idempotency-Key` queda ligada a la huella SHA-256 de operación,
  agregado, paciente y payload canónico mínimo. Reutilizarla con otra solicitud
  devuelve `409 IDEMPOTENCY_KEY_CONFLICT` sin mutar datos.
- Las notas, signos vitales, alergias, consentimientos, formatos universales y
  contactos/firmantes PTCN siguen la misma frontera durable. Los `GET` no
  almacenan PDFs ni producen mutaciones en PostgreSQL o SQL Server.
- OpenAPI viva en `/docs` (Swagger) cuando el backend corre.

## Contrato biométrico fail-closed

AF-02 usa evidencia V2 de adquisición física local. El backend entrega
`capture_authorization` firmada en la respuesta del challenge. El agente de la
estación expone `/begin-capture`, `/capture-result` y `/cancel-capture` solamente
en loopback; `/extract-fmd` está retirado (410). Las referencias de matching
viajan cifradas para el agente y FastAPI valida el resultado firmado contra
la plantilla vigente, sin llamar a `localhost:8082` del servidor.
Ver [[Biometria-DigitalPersona]].

- `POST /api/biometrics/challenge` exige `action` y `session_id`; acepta el contexto específico de paciente, documento e identidad esperada. Para acciones distintas de `LOGIN` exige Bearer válido. Las acciones `FIRMA_MEDICA`/`FIRMA_FIRMANTE` exigen paciente/formato resolubles e incluyen `document_digest` autoritativo firmado; cambios de contenido durante captura se rechazan con 409.
- Todo endpoint autorizado por huella exige `fmd_template`, `challenge_id` y `session_id`. La attestation incluye además `acquisition_id`, inicio y fin de captura; challenge/adquisición ausentes, expirados, consumidos o de otro contexto fallan sin efectos.
- Una huella que no coincide durante una operación clínica autenticada responde 403 y no invalida el JWT de la sesión; el frontend conserva la pantalla y permite reintentar. El mismatch de `LOGIN`, donde aún no existe sesión, responde 401.
- Enrolamiento y reenrolamiento son explícitos: `/api/medicos/{id}/biometria/{enrolar|reenrolar}` y `/api/pacientes/{paciente}/firmantes-biometricos/{firmante}/{enrolar|reenrolar}`.
- `firmante_id` es obligatorio al verificar o firmar. El rol persistido del firmante manda; un `rol_firmante` contradictorio se rechaza. PACIENTE, TUTOR, REPRESENTANTE_LEGAL, FAMILIAR, TESTIGO_1 y TESTIGO_2 mantienen su rol; CONTACTO no autoriza por sí mismo.
- `GET /api/ehr/paciente/{pt_num}/firmas-documento` devuelve `requiere_testigos` y `listo_para_cierre_medico`. Consentimientos reconocidos/egreso voluntario exigen autorizador y dos testigos distintos; notas no exigen ese circuito. Los indicadores corresponden al contenido vigente de la ranura exacta, incluso 0. `/firmas` filtra evidencia vigente; `/historial-auditoria` conserva histórica.
- `PUT /api/medicos/{id}/huella` está retirado (410) para impedir sustituciones no auditadas.
- `POST /api/medicos/{id}/fea/completar-actualizacion` completa explícitamente la rotación posterior al reenrolamiento: challenge `ACTUALIZACION_FEA`, match 1:1, motivo y auditoría. Exige un segundo actor administrativo distinto del que reenroló; hasta completar el bloque B, firma y login biométrico responden 423.
- `POST /api/ehr/paciente/{pt_num}/firmar-biometrico` ya no acepta `contenido_resumen`; obtiene el documento completo en backend y persiste `CANONICAL_V2` + `key_id`.
- `POST /api/firmas/{firma_id}/tsa/reintentar` reintenta idempotentemente el RFC 3161 sin regenerar ni modificar la ECDSA médica.
- La verificación distingue `VERIFICACIÓN_CRIPTOGRÁFICA_COMPLETA`, `FIRMA_LEGACY_NO_CUBRE_DOCUMENTO_COMPLETO` y metadata Vertical no criptográfica. `ESignature`, `SignedBy` o `FIRMADO_BIOMETRICAMENTE` nunca bastan para marcar identidad/integridad/autenticidad.

---
> 🤖 *Contexto IA: antes de crear un endpoint, buscar si ya existe en `main.py` (grep `@app.`). Nuevo dominio = nuevo router + registro en `main.py` + hook en `useQueries.js`.*

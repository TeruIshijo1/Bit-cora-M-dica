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
actualizado: 2026-09-29
relacionados:
  - "[[Backend]]"
  - "[[Frontend]]"
  - "[[Seguridad-FEA]]"
  - "[[Database]]"
---

# API-Endpoints

## Firmas del área

- `GET /api/firmas-area?estado=pendientes|historial&cursor=...`: bandeja compartida
  según rol y `formatos_firma_permitidos`. Devuelve `items`, `next_cursor`, área y
  rol. Páginas de hasta 25 resultados; una exploración acotada de 200 registros
  puede devolver una página vacía con continuación. La UI conserva Cargar más.
- `GET /api/firmas-area/documento?pt_num=...&codigo_formato=...&slot=...`: resumen
  clínico, PDF exacto e historial con usuario, nombre, fecha y vigencia. `slot > 0`.
- Las rutas existentes de firmantes, estado del documento y firma especial
  admiten `firmas_area` sólo para documentos permitidos. En sesión del área el
  roster se limita al usuario propio y challenge/guardado rechazan otra identidad.
  Los operadores clínicos conservan la selección de personal de otras áreas.
- La firma especial responde 409 si el área ya firmó; el estado se comprueba bajo
  bloqueo transaccional por fuente documental y rol. Las firmas no se duplican por
  aliases de código ni ranuras heredadas. No cambia el contrato biométrico ni FEA.
- `auth/me` incluye ID de la cuenta y `formatos_firma_permitidos`. La consulta de
  PDF por área exige `mrnum` explícito del formato asignado; no habilita PDF integral.

Contrato REST entre [[Frontend]] y [[Backend]]. Auth global JWT Bearer + roles.

## Permisos por área y usuario

Ver [[Permisos-Acceso]]: catálogo compartido, selección explícita por usuario,
RH limitado a cinco áreas, formatos activos integrados al selector y validación
en API/SPA. El mínimo de contraseña es 8 caracteres con mayúscula, minúscula,
número y símbolo. Las cuentas existentes conservan sus datos.

## Base
- `main.py` (~12k líneas): orquestador + middlewares (`TrustedHostMiddleware`, CORS estricto, `GlobalAuthMiddleware`, `slowapi` rate-limit) + **muchos endpoints inline** + routers modulares.
- `routers/catalogos.py`: áreas, tipos de atención, formatos autorizados.
- `frontend/src/api.js`: cliente Axios. `useQueries.js`: caché TanStack.

## Auth y roles
- JWT HS256 (`security.py`), `require_role("admin" | "enfermeria" | "rh" | "sistemas" | "trabajo_social" | "medico")`. La identidad, el rol vigente y el estado activo se revalidan contra PostgreSQL en cada petición.
- `AuthContext.jsx`: sesión global, permisos por módulo (`permisos_modulos` JSON), formatos permitidos por usuario/médico.
- Rutas públicas: allowlist exacta por método+plantilla en `backend/route_policy.py` (login, challenge, portal HTML de verificación, documentación y assets frontend concretos). No existen excepciones por prefijo ni por texto `pdf`; todo lo demás exige Bearer.
- Toda escritura `POST`/`PUT`/`PATCH`/`DELETE` requiere una entrada explícita en `WRITE_ROLE_POLICIES`; una ruta nueva o indeterminada falla cerrada con 403.
- `static/` no está montado como webroot. PDFs clínicos y escaneos RH sólo se entregan por controladores autorizados; `/api/escaneos/{id}/archivo` exige el permiso `escaneos`.

## Dominios (verificar en `main.py` con `@app.api_route`)
- `POST /api/auth/login` · `GET /api/auth/me`
- `/api/catalogos/*` — áreas, tipos atención, formatos (`routers/catalogos.py`)
- `/api/pacientes/*` — CRUD + búsqueda (consumido por `PatientSearchModal`)
- `/api/atenciones/*` — episodios, notas, evolución
- `/api/ehr/*` — expediente: alergias (`DIS_AL`), dietas, medicamentos, timeline
- `/api/biometria/*` — challenge, enrol, match, firma FEA
- `/api/formatos/*` — generación PDF vía `pdf_service` → [[Formatos-PDF]]
- `/api/farmacia/*`, `/api/camas/*`, `/api/agenda/*` — operación. En agenda,
  las sesiones de médico/ayudante sólo reciben, consultan y pueden crear citas
  para su propio `medico_id`; administración puede operar la agenda global.
- `/api/admin/*` — usuarios, roles, `auditoria_logs`
- `GET /health` — liveness del proceso, sin dependencias ni secretos.
- `GET /readiness` — PostgreSQL obligatorio; reporta por separado SQL Server,
  biometría, TSA y capacidad. TSA pendiente no derriba por sí sola el proceso.
- `GET /api/operational/metrics` — instrumentación mínima protegida: HTTP 5xx,
  fallos DB/biometría, estados clinical sync, TSA y disco.
- `POST /api/auth/logout` — revoca inmediatamente el `jti` del token activo.
- `GET /api/auth/session` — heartbeat autenticado para una sesión con actividad
  reciente. El frontend envía la antigüedad, en segundos, de la última actividad
  real mediante `X-Session-Activity`; el middleware responde
  `X-Session-Token` con un JWT renovado. Las respuestas de rutas autenticadas marcan
  `X-Session-Authenticated`, incluso ante errores de negocio, para que fallos de
  firma no se confundan con expiración del JWT. JWT y UI aplican 20 minutos de
  inactividad; consultas en segundo plano no renuevan por sí solas la sesión.
- `POST /api/auth/change-password` — cambio propio; obligatorio tras bootstrap o
  reset administrativo antes de usar otras rutas.
- `GET /api/ehr/pacientes/buscar?q=...` — búsqueda explícita por nombre, folio o
  CURP. Una consulta vacía devuelve `[]`; el acceso inicial a expedientes se
  resuelve desde `GET /api/camas`, que entrega el censo físico y no incluye
  camas virtuales.
- `POST /api/pacientes/sincronizar-kh` — sincronización explícita del censo;
  `GET /api/pacientes` es estrictamente de solo lectura.
- `GET /api/clinical-sync/operations/{operation_id}` — estado durable sin
  exponer payload clínico ni errores internos.
- `POST /api/clinical-sync/reconcile` — reintento acotado para admin/sistemas. Con `operation_id` exacto admite sólo una firma médica `REQUIRES_RECONCILIATION` cuyo `SignRecord` fue reconocido por Vertical o cuya respuesta HTTP quedó incierta; la conciliación consulta la fila nativa y nunca vuelve a enviar ese comando.
- Portal HTML, estado y descarga `/verificar*` — verificación QR pública sólo
  mediante `id`/`doc_uuid` opaco `v1_*` de alta entropía y coincidencia exacta.
  Folio, paciente, formato o slot no sirven como identificadores públicos.
  Quien posea el QR puede ver nombre, folio, edad y abrir el PDF exacto; no hay
  búsqueda pública por esos datos. La identidad se consulta por el paciente
  vinculado al QR en `V_MRPT` (con respaldo local por código de barras exacto).
  El estado `COPIA_INTEGRA_VERIFICADA` del expediente compilado acredita sólo
  coincidencia SHA-256 con la copia resguardada, no una firma FEA de la compilación.
  Para formatos individuales con firma verificada, la pantalla usa el
  booleano `valido` como fuente de verdad para mostrar “firmado”; estados como
  `FIRMA_ECDSA_VALIDA_TSA_PENDIENTE` significan que la firma sí fue verificada
  y sólo queda pendiente el sellado TSA, no que el documento esté sin firmar.
- `GET /api/ehr/paciente/{pt_num}/pdf-consentimiento-02` — representación de
  solo lectura; no crea evidencia QR. Si ya existe el PDF verificable de la
  firma activa, entrega exactamente ese archivo.
- `GET /api/ehr/paciente/{pt_num}/pdf-expediente-completo` — representación
  autenticada del expediente integral. Compila formatos con evidencia vigente,
  todos los laboratorios e imagenología y sus reportes PDF disponibles; cuando
  existe `PUBLIC_VERIFICATION_BASE_URL` HTTPS, conserva una copia exacta y
  genera un QR opaco que abre el cotejo público del expediente completo. Expone
  `X-HES-Signature-Report` para notificar faltantes de médico, paciente o
  testigos. Si una firma HES activa no puede vincularse a la versión actual,
  responde `409` con `code=EXPEDIENTE_REQUIERE_REVISION_DE_FIRMAS`, la lista de
  formatos afectados y la acción `REVISAR_Y_REFIRMAR`; la interfaz ofrece ir
  directamente a cada formato. La compilación se detiene para evitar entregar
  un PDF aparentemente sin firma y no se borra la evidencia anterior.
- `GET /api/kh/estudios/{ptmt_num}/pdf` — entrega el PDF original de laboratorio
  o imagenología desde Vertical. El `Content-Disposition` normaliza nombres
  vacíos o UUID a `Resultado_Estudio_PTMT_{ptmt_num}.pdf`; el dashboard usa
  además el tipo y la descripción del estudio en su enlace de descarga.
- `POST /api/ehr/paciente/{pt_num}/pdf-preparar?source=...` — prepara
  `pdf-consentimiento-09?mrnum=N` de la misma persona. La ruta no admite URLs
  arbitrarias. Emite un QR con identificador opaco y guarda la copia exacta
  en almacenamiento privado. El GET autenticado del 09 también conserva ese
  QR estable para que la vista directa no lo pierda. Todos los QR apuntan a la
  pantalla institucional diseñada en `/verificar?id=...`, que muestra el
  cotejo y conserva el botón al PDF oficial completo. Ambos exigen
  `PUBLIC_VERIFICATION_BASE_URL` público HTTPS (o la variable histórica
  `VERIFICATION_BASE_URL`). Los demás PDF se consultan por GET autenticado
  hasta que cada motor se incorpore explícitamente a la preparación.

## Convenciones
- Errores centralizados en frontend: `useApiError.js`.
- Paginación/filtros por query params; respuestas Pydantic v2 (`schemas.py`).
- Escrituras duales aceptan `Idempotency-Key`. `SYNCED` responde 200/201;
  pendiente recuperable o incierta responde 202 con `operation_id`; fallo
  permanente responde 5xx sanitizado y conserva evidencia. Cuando el cambio
  local ya existe, la respuesta incluye `local_applied=true`; la interfaz debe
  impedir una segunda captura y mostrar el estado real de Vertical.
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

- `POST /api/biometrics/challenge` exige `action` y `session_id`; acepta el contexto específico de paciente, documento e identidad esperada. Para acciones distintas de `LOGIN` exige Bearer válido. `FIRMA_MEDICA`, `FIRMA_FIRMANTE` y `FIRMA_BANCO_SANGRE` exigen paciente/formato resolubles e incluyen `document_digest` autoritativo firmado; cambios de contenido durante captura se rechazan con 409.
- Todo endpoint autorizado por huella exige `fmd_template`, `challenge_id` y `session_id`. La attestation incluye además `acquisition_id`, inicio y fin de captura; challenge/adquisición ausentes, expirados, consumidos o de otro contexto fallan sin efectos.
- Una huella que no coincide durante una operación clínica autenticada responde 403 y no invalida el JWT de la sesión; el frontend conserva la pantalla y permite reintentar. El mismatch de `LOGIN`, donde aún no existe sesión, responde 401.
- Enrolamiento y reenrolamiento son explícitos: `/api/medicos/{id}/biometria/{enrolar|reenrolar}` y `/api/pacientes/{paciente}/firmantes-biometricos/{firmante}/{enrolar|reenrolar}`. El enrolamiento médico inicial valida un médico único ya existente en `KH_HE.dbo.PR`; si su autorización está vacía genera un código aleatorio de seis dígitos exclusivo para él. Nunca crea profesionales ni sobrescribe códigos existentes, y el código no se devuelve ni se persiste en HES.
- `firmante_id` es obligatorio al verificar o firmar. `tipo_firmante` conserva el
  perfil enrolado de la persona; `rol_firmante` indica el papel elegido para ese
  documento y queda ligado criptográficamente al challenge. Un TUTOR,
  REPRESENTANTE_LEGAL o FAMILIAR puede ocupar TESTIGO_1/TESTIGO_2 cuando el
  paciente autoriza por sí mismo. El perfil no se modifica, PACIENTE no puede
  convertirse en testigo y CONTACTO no autoriza ni testimonia por sí mismo.
  Una misma persona no puede ocupar dos lugares en el mismo documento vigente.
- `GET /api/ehr/paciente/{pt_num}/firmas-documento` devuelve `requiere_autorizacion`, `requiere_testigos`, `testigos_esperados`, `testigos_requeridos`, `testigos_firmados` y `listo_para_cierre_medico`. `testigos_esperados` son los lugares del formato (0, 1 o 2), que permanecen disponibles; `testigos_requeridos` es el mínimo para cierre operativo tras identificar a quien autoriza: uno si firma el paciente en un formato con testigos, cero si firma tutor/familiar/representante. `testigos_firmados` cuenta identidades distintas, excluyendo al autorizante. Cada testigo firmado debe tener identidad propia; una persona no puede ocupar dos lugares. Un formato sin testigos aún puede requerir autorización del paciente; las notas médicas no la requieren. El cierre operativo con menos firmas que lugares del formato no declara cumplimiento NOM. Los indicadores corresponden al contenido vigente de la ranura exacta, incluso 0. Cada nueva fuente clínica debe declarar su política de firmas: una fuente registrada sin ella responde 409 al intentar firmar, en vez de asumir que no requiere autorizador. `/firmas` filtra evidencia vigente y señala `politica_firma_pendiente` en registros antiguos sin política; `/historial-auditoria` conserva evidencia histórica.
- Un documento vigente admite un solo autorizante (PACIENTE o TUTOR/FAMILIAR/REPRESENTANTE_LEGAL) y una firma por cada lugar TESTIGO_1/TESTIGO_2. Otra persona no puede sustituir un lugar ocupado mediante una nueva captura; el intento responde 409 sin crear evidencia. `GET /firmas-documento` expone además `testigos_formato_completos` y `cierre_excepcional_por_testigos` para distinguir la finalización operativa de los lugares previstos en el formato.
- Cuando el médico cierra un consentimiento, la misma transacción de la firma médica inserta `CIERRE_MEDICO_CONSENTIMIENTO` en `auditoria_logs`. Su `detalles_json` fija paciente, código, ranura, digest de la versión, médico, ID/rol del autorizante, IDs de los dos lugares de testigo, `testigos_esperados`, `testigos_firmados`, `testigos_minimos_cierre`, `cierre_excepcional_por_testigos` y `firma_id`; `operation_id` se registra en la columna de auditoría. La instantánea permite comprobar cuántos testigos habían firmado *en el momento del cierre*, aunque alguien firme después. `cierre_excepcional_por_testigos=true` no constituye declaración de cumplimiento NOM.
- La firma médica vigente del documento exacto añade `medico_sync_operation_id` y `medico_sync_state` a `/firmas-documento`. Una firma HES pendiente de confirmación en Vertical no se reemplaza por una segunda captura médica de la misma versión. Si la fuente clínica Vertical no puede cargarse, la respuesta conserva esos campos para cualquier firma médica local activa del formato y ranura, incluso `SYNCED`, y añade `medico_sync_unverified=true`; `medico_firmado` permanece falso hasta verificar la versión.
- `GET /api/ehr/paciente/{pt_num}/firmas` devuelve sólo firmas vigentes de la versión clínica exacta y, para cada firma médica, su `medico_sync_state` y `medico_sync_operation_id`. Así la tarjeta puede mostrar por separado la firma HES y la entrega a Vertical sin inferir éxito a partir de un sello local; los estados se consultan en una sola lectura por lote.
- La capacidad para autorizar se toma sólo del campo `paciente_capaz` cuando está expresamente presente en el snapshot clínico autoritativo; la ausencia de ese dato no se sustituye por edad, tipo de interrogatorio o una selección temporal del modal. Los formatos nuevos deben guardar la decisión con su documento y ranura para permitir validación automática completa.
- `PUT /api/medicos/{id}/huella` está retirado (410) para impedir sustituciones no auditadas.
- `POST /api/medicos/{id}/fea/completar-actualizacion` completa explícitamente la rotación posterior al reenrolamiento: challenge `ACTUALIZACION_FEA`, match 1:1, motivo y auditoría. Exige un segundo actor administrativo distinto del que reenroló; hasta completar el bloque B, firma y login biométrico responden 423.
- `POST /api/ehr/paciente/{pt_num}/firmar-biometrico` ya no acepta `contenido_resumen`; obtiene el documento completo en backend y persiste `CANONICAL_V2` + `key_id`. Antes de crear la evidencia consulta en modo lectura `KH_HE.dbo.V_MRPR`: resuelve primero por cédula y, sólo si no existe, por nombre exacto único. `PRNum` y `MedicalRecordAuthorizationCode` se envían en memoria a `SignRecord`; el código no se persiste ni se registra en HES.
- La confirmación de entrega a Vertical exige `MR_ST=SG`, `SignedOn`, cadena `ESignature` nativa y vínculo del médico mediante el campo clínico (`N_MEDICO` o equivalente) o `PRNum`. Excepción acotada: `MR_NE_URG` puede conservar `MR_ST=RG` tras un `SignRecord` reconocido explícitamente; sólo se admite si la fila exacta muestra una fecha y cadena nuevas, posteriores a la operación y con el médico correcto. La conciliación de ese caso exige el reconocimiento previo y es sólo de lectura; una respuesta HTTP incierta no habilita esta excepción. `SignedBy` identifica al usuario técnico autenticado de Vertical y no se compara con el nombre del médico. La lectura posterior espera unos segundos de propagación y nunca sustituye la cadena nativa. Si Vertical reconoció `SignRecord` pero la fila exacta aún no confirma, el intento registra un motivo acotado (`NATIVE_*`).
- `POST /api/firmas/{firma_id}/tsa/reintentar` reintenta idempotentemente el RFC 3161 sin regenerar ni modificar la ECDSA médica.
- La verificación distingue `VERIFICACIÓN_CRIPTOGRÁFICA_COMPLETA`, `FIRMA_LEGACY_NO_CUBRE_DOCUMENTO_COMPLETO` y metadata Vertical no criptográfica. `ESignature`, `SignedBy` o `FIRMADO_BIOMETRICAMENTE` nunca bastan para marcar identidad/integridad/autenticidad.
- Administración/Sistemas registra o actualiza la huella de una cuenta con `POST /api/usuarios/{usuario_id}/biometria/enrolar` y `/reenrolar` (motivo obligatorio). El roster `GET /api/ehr/firmantes-especiales?codigo_formato=...&rol_firmante=...` sólo devuelve cuentas activas, enroladas y autorizadas; nunca expone FMD.
- `POST /api/ehr/paciente/{pt_num}/firmar-biometrico-especial` recibe cuenta, rol especial, formato, ranura y challenge. El servidor exige que el formato declare ese rol, que la cuenta tenga ese rol y el formato en `formatos_firma_permitidos`, y liga la captura al digest clínico exacto. `/firmas-documento` entrega `firmas_especiales_requeridas`, `firmas_especiales_estado`, `firmas_especiales_pendientes`, `firmas_especiales_completas` y `documento_operativamente_completo`. La firma especial no sustituye la autorización de paciente/testigos ni la FEA médica.
- El requisito se declara por formato en `backend/format_catalog.py`. Hoy sólo `HE-DIRMED-CONSUL-PLT-09` requiere `BANCO_SANGRE`; agregar roles a la metadata de un formato futuro lo incorpora al editor, prompt secuencial, validación, estado electrónico y representación PDF. La ruta antigua específica de Banco de Sangre permanece como alias compatible.

---
> 🤖 *Contexto IA: antes de crear un endpoint, buscar si ya existe en `main.py` (grep `@app.`). Nuevo dominio = nuevo router + registro en `main.py` + hook en `useQueries.js`.*

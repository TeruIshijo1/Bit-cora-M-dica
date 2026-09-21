# Auditoría preproducción — Bitácora Médica HES

**Fecha de corte:** 2026-09-17  
**Alcance:** `backend/`, `frontend/`, `mobile_app/`, microservicio DigitalPersona, scripts de despliegue/backup, documentación y controles NOM-004-SSA3-2012 / NOM-024-SSA3-2012.  
**Dictamen:** **NO GO PARA PRODUCCIÓN**.  
**Naturaleza de la revisión:** análisis estático exhaustivo, compilación, lint/typecheck, inventario de rutas y dependencias. No se ejecutaron ataques contra datos reales, pruebas destructivas, cambios de código ni migraciones.

## 1. Resumen ejecutivo

Se identificaron **9 hallazgos P0, 12 P1, 4 P2 y 1 P3**. Los bloqueadores principales son:

1. Existen rutas clínicas y PDFs accesibles sin autenticación por reglas demasiado amplias del middleware, alias `/ehr` fuera de `/api` y el montaje público de `static/`.
2. La firma de pacientes/tutores puede aceptar una huella no coincidente, reemplazar la plantilla almacenada y continuar como firma válida.
3. El challenge biométrico es opcional y los principales flujos de frontend no lo envían; un FMD capturado puede reutilizarse.
4. Lo denominado FMD es en realidad una captura `SampleFormat.Raw`, que se persiste y transmite como JSON/base64.
5. La ECDSA firma un resumen suministrado por el cliente, no el documento clínico ni el PDF. La verificación posterior relee la misma cadena almacenada y puede declarar íntegro un documento modificado.
6. Un rol administrativo/RH puede sustituir la huella de un médico conservando su llave privada y firmar posteriormente como él.
7. El arranque “productivo” ejecuta un seed con credenciales conocidas y biometría simulada, usa HTTP y `--reload`.
8. PostgreSQL y SQL Server se confirman en momentos distintos; ya existe al menos un camino que reporta éxito y modifica PostgreSQL aun cuando falla SQL Server.
9. Numerosas escrituras clínicas aceptan cualquier JWT válido sin autorización por rol o relación médico-paciente.

Hasta que todos los P0 y P1 cuenten con pruebas automatizadas de regresión, no debe desplegarse este estado en una red clínica ni cargarse información real.

## 2. Metodología, evidencia y límites

### Acciones realizadas

- Lectura de la bóveda `docs/` indicada por `AGENTS.md`, incluidos arquitectura, backend, frontend, biometría, FEA, PDFs, base de datos, producción, normativa y ADR.
- Revisión de modelos, esquemas, middleware, rutas, flujos PostgreSQL/SQL Server, firma ECDSA, TSA, PDFs, frontend, móvil y servicio DigitalPersona.
- Parseo AST correcto de los 33 archivos Python del backend.
- `npm run build` del frontend: termina, pero genera artefactos grandes (JS principal ~1.58 MB; worker PDF ~1.26 MB).
- `npm run lint` del frontend: **311 problemas** (286 errores, 25 advertencias), incluidos identificadores no definidos y problemas de hooks.
- `npx tsc --noEmit` de móvil: falla con múltiples errores de tipos.
- `npm audit --omit=dev`: frontend **7 vulnerabilidades** (5 altas, 2 moderadas); móvil **26** (10 altas, 16 moderadas), según el registro consultado en la fecha de corte.
- No hay suite automatizada activa de unidad, integración, seguridad, biometría, concurrencia o E2E. En el estado de trabajo aparecen eliminados `backend/test_crypto_fea.py` y `backend/test_tsa_client.py`.

### Límites

- No se abrió ni modificó `.env`; no se validaron valores productivos de secretos, TLS, CORS, TSA o conexiones.
- No se conectó a bases productivas, Vertical, lector físico ni TSA. Los escenarios destructivos se diseñan en la sección 6 para un ambiente aislado.
- No se afirma cumplimiento jurídico. La matriz normativa es una evaluación de evidencia técnica y requiere revisión jurídica/operativa y, para NOM-024, el procedimiento de evaluación aplicable.
- El repositorio ya contenía cambios sin confirmar. Esta auditoría no los alteró y evalúa el árbol de trabajo observado.

## 3. Hallazgos P0 — críticos

### P0-01 — Bypass global de autenticación y exposición de expediente/PDF

**Archivo/líneas:** `backend/main.py:167-185`, `backend/main.py:247-263`, `backend/main.py:3894`, `backend/main.py:4325`, `backend/main.py:5945-5948`, `backend/main.py:6319-6333`, `backend/main.py:6449-6455`, `backend/main.py:7609-7836`, `backend/main.py:9001-12109`.  
**Descripción:** el middleware deja pasar todo path que no empiece por `/api`, y también cualquier ruta cuyo texto contenga `/pdf` o `/pdf-`. Hay numerosos alias `/ehr/...` de lectura y escritura, incluso firmas y consentimientos. Además, `static/` se monta completo sin control. El endpoint de PDF público acepta folios/códigos enumerables y puede buscar o regenerar documentos clínicos completos.  
**Cómo reproducir:** en staging, sin cabecera `Authorization`, solicitar un alias `/ehr/paciente/{folio}/...`, una ruta `/api/.../pdf-...`, `/api/verificar/pdf?pt_num=...` y un nombre conocido bajo `/static/pdfs/` o `/static/escaneos_rh/`. Repetir con folios adyacentes.  
**Impacto:** divulgación masiva de datos clínicos, acceso a firmas/sellos, modificación no autorizada de consentimientos y violación de confidencialidad.  
**Probabilidad:** alta; no requiere cuenta y los identificadores son predecibles.  
**Solución recomendada:** lista cerrada de rutas públicas exactas; retirar alias no autenticados; autenticar/autorización por paciente/rol; entregar archivos mediante controlador seguro y referencias opacas de un solo uso; separar almacenamiento privado del webroot.  
**Prueba de corrección:** matriz automatizada que recorra todas las rutas y verifique 401/403 sin token o con rol incorrecto; prueba de enumeración; prueba que confirme que ningún archivo clínico es resoluble directamente desde `/static`.

### P0-02 — La verificación de firmante acepta huella incorrecta y la convierte en la nueva identidad

**Archivo/líneas:** `backend/main.py:363-464`, `backend/main.py:5945-6021`; `backend/models.py:115-148`; `frontend/src/components/BiometricPatientSignModal.jsx:220-249`.  
**Descripción:** si el firmante no tiene plantilla, se enrola durante la firma; si la comparación falla o el microservicio da error, el código reemplaza la plantilla por la huella suministrada y devuelve éxito. Sin ID explícito, puede elegir al primer firmante y sobrescribirlo. El endpoint también tiene alias público `/ehr`.  
**Cómo reproducir:** en staging, crear un firmante A con huella A; firmar el documento de A enviando huella B. Observar que la operación termina y `fmd_template` queda reemplazada por B. Repetir con microservicio detenido y sin `firmante_id`.  
**Impacto:** suplantación de paciente/tutor, consentimientos inválidos, pérdida de la biometría original y falsa evidencia de no repudio.  
**Probabilidad:** alta; es comportamiento explícito de fallback.  
**Solución recomendada:** separar enrolamiento de firma; una discordancia siempre debe fallar cerrado; re-enrolamiento con flujo autorizado, doble control y auditoría; hacer obligatorio el ID ligado al episodio; nunca mutar biometría desde un verificador.  
**Prueba de corrección:** huella B contra A retorna 401/422 y no cambia ninguna fila; microservicio caído retorna 503 y no firma; concurrencia de 20 intentos no enrola ni sustituye plantillas.

### P0-03 — Challenge biométrico opcional: replay en login y firma médica

**Archivo/líneas:** `backend/main.py:270-297`, `backend/main.py:301-340`, `backend/main.py:644-655`, `backend/main.py:5750-5778`; `frontend/src/pages/LoginDual.jsx:91`; `frontend/src/pages/PatientDashboard.jsx:1491-1502`, `1544-1560`, `1593-1602`, `1629-1644`; `frontend/src/components/BiometricSignModal.jsx:35-60`.  
**Descripción:** `validate_and_consume_challenge()` devuelve verdadero si no recibe challenge. Los contratos lo hacen opcional y los flujos principales no lo envían. Un modal intenta obtenerlo, pero continúa si falla y la captura puede adelantarse a la respuesta. El nonce tampoco está ligado criptográficamente a la captura, usuario, acción y hash de documento.  
**Cómo reproducir:** capturar una petición válida, retirar `challenge_id` y reenviar el mismo `fmd_template` para login o firma; repetir varias veces y en paralelo.  
**Impacto:** replay de biometría, acceso como médico y firma repetida/suplantada usando una muestra interceptada o extraída de BD.  
**Probabilidad:** alta dado que la omisión es el camino normal del frontend.  
**Solución recomendada:** challenge obligatorio, aleatorio, de un uso, persistido de forma atómica, ligado a usuario/acción/documento/sesión y consumido aun en fallo; limitar intentos y rate-limit; exigir captura posterior al challenge.  
**Prueba de corrección:** ausencia, expiración, reutilización, acción/usuario/documento distintos y dos consumos simultáneos deben fallar; sólo un primer consumo correcto puede producir efecto.

### P0-04 — Se almacena una muestra dactilar RAW, no una plantilla irreversible

**Archivo/líneas:** `frontend/src/hooks/useDigitalPersona.js:77-108`, `frontend/src/hooks/useDigitalPersona.js:238`; `backend/models.py:51-81`, `115-148`; `backend/main.py:317-338`, `411-464`; `../Teru/Bio-security/server.js:26-49`, `72-97`.  
**Descripción:** el lector usa `SampleFormat.Raw`, empaqueta base64, dimensiones y resolución y lo denomina `fmd_template`. Ese objeto se guarda en PostgreSQL y se reenvía al microservicio, que recién allí lo convierte temporalmente a ANSI FMD. La documentación afirma que se almacena una plantilla irreversible, lo que contradice la implementación.  
**Cómo reproducir:** enrolar en staging, inspeccionar el valor guardado y comprobar campos de imagen RAW/dimensiones; reconstruir visualmente la matriz de píxeles en un entorno controlado.  
**Impacto:** una brecha de BD expone material biométrico permanente potencialmente reconstruible; no puede “cambiarse” como una contraseña.  
**Probabilidad:** alta; ocurre en cada captura/enrolamiento.  
**Solución recomendada:** convertir en el dispositivo o componente confiable a formato de plantilla apropiado; cifrado por registro con KMS/HSM y control de acceso; minimizar retención y 1:N; plan de respuesta/consentimiento y migración segura de muestras existentes.  
**Prueba de corrección:** inspección automatizada confirma que nunca se persisten campos/píxeles RAW; pruebas de logs/tráfico/backup; descifrado sólo por servicio autorizado; evaluación biométrica y de privacidad independiente.

### P0-05 — La firma ECDSA no está vinculada al documento real y la verificación puede declarar integridad falsa

**Archivo/líneas:** `backend/main.py:5750-5942`, especialmente `5789-5799`; `backend/main.py:6449-6766`; `backend/main.py:6775-7100`; `backend/vertical_signer.py:393-395`.  
**Descripción:** la cadena firmada incorpora metadatos y los primeros 100 caracteres de `contenido_resumen` enviados por el cliente. No contiene hash canónico de la fila clínica actual ni hash del PDF. La verificación recalcula sobre la cadena almacenada, no sobre el documento vigente. Si sólo encuentra `ESignature`/`SignedBy` de Vertical, llega a marcar identidad, integridad y autenticidad verdaderas; Vertical puede guardar el literal `FIRMADO_BIOMETRICAMENTE`. La firma de paciente es un SHA-256 truncado sin clave, no una firma autenticada.  
**Cómo reproducir:** firmar documento D, alterar su contenido en Vertical o regenerar un PDF distinto conservando la fila de firma; invocar verificación. Probar también una fila Vertical con el marcador textual.  
**Impacto:** evidencia clínica y jurídica falsa; cambios posteriores indetectables; documento A puede aparentar la firma de B.  
**Probabilidad:** alta porque es el diseño actual, no una condición excepcional.  
**Solución recomendada:** esquema de documento canónico/versionado; hash SHA-256 de bytes o representación canónica completa; firma sobre hash + identidad + propósito + versión + key-id; guardar snapshot inmutable; verificar contra contenido actual y cadena de confianza; eliminar resultados “válidos” por marcadores.  
**Prueba de corrección:** cambiar un bit del contenido, PDF, firmante, slot, propósito o llave debe invalidar; golden vectors ECDSA; verificación histórica después de rotación; prueba negativa del marcador Vertical.

### P0-06 — Sustitución administrativa de huella permite firmar con la llave privada de otro médico

**Archivo/líneas:** `backend/main.py:2762-2791`; `backend/crypto_fea.py:22-48`, `102-167`; `backend/models.py:51-93`.  
**Descripción:** admin/RH/sistemas pueden reemplazar `medico.fmd_template` sin reautenticación del médico, comparación anterior, doble aprobación ni rotación de llave. La llave privada existente permanece cifrada con un token UUID almacenado en la misma fila, no con un secreto derivado de biometría. Tras sustituir la huella, el operador puede superar el matching y usar la misma llave del médico.  
**Cómo reproducir:** en staging, como RH sustituir la huella de M por la del operador; después firmar como M con esa captura y verificar que la llave pública/privada no cambió.  
**Impacto:** suplantación completa del profesional y ruptura del control exclusivo exigido para FEA/no repudio.  
**Probabilidad:** media-alta; requiere rol interno, pero el proceso está permitido.  
**Solución recomendada:** ceremonia de enrolamiento/re-enrolamiento con presencia y autenticación fuerte del titular, aprobación dual, motivo, revocación/rotación vinculada y auditoría inmutable; custodia de llave en HSM/keystore o factor que permanezca bajo control del médico.  
**Prueba de corrección:** un administrador solo no puede sustituir/firmar; toda rotación conserva verificación histórica y genera eventos inmutables; prueba de separación de funciones.

### P0-07 — Arranque productivo crea cuentas con contraseñas conocidas y biometría simulada

**Archivo/líneas:** `backend/seed.py:17-21`, `backend/seed.py:50-60`; `iniciar.bat:7-13`.  
**Descripción:** cada arranque ejecuta `seed.py`, que contiene contraseñas literales para admin, RH, enfermería y prueba, además de una muestra biométrica simulada. El servidor se expone en `0.0.0.0`, HTTP y modo `--reload`.  
**Cómo reproducir:** ejecutar el script en una BD vacía o donde falten usuarios y comprobar las cuentas creadas; iniciar con el BAT y observar reload/HTTP. No probar estas credenciales en producción.  
**Impacto:** toma inmediata del sistema, escalamiento a roles privilegiados, modificación de expedientes y firma fraudulenta.  
**Probabilidad:** alta si el paquete se instala como documentado.  
**Solución recomendada:** excluir seeds de producción; bootstrap único con secreto temporal aleatorio y cambio obligatorio; detección de cuentas demo; servidor productivo sin reload detrás de TLS/proxy y supervisor. Rotar cualquier credencial que haya podido desplegarse.  
**Prueba de corrección:** instalación limpia no crea cuentas conocidas/demo; scanner de secretos; intento con todos los valores históricos falla; proceso no usa reload y no atiende HTTP directo.

### P0-08 — Operaciones clínicas no atómicas entre PostgreSQL y SQL Server

**Archivo/líneas:** `backend/main.py:536-558`, `1215-1280`, `5041-5148`, `5182-5227`, `5396-5545`, `5759-5927`, `12081-12100`, `12258-12278`; `backend/kh_database.py` (operaciones INSERT/UPDATE/DELETE).  
**Descripción:** los sistemas se confirman por separado y `log_auditoria` hace commits propios. Alta, medicación, suspensión, dieta, firma y formatos universales pueden quedar parcialmente aplicados. En dieta, el error de SQL Server sólo se imprime y PostgreSQL continúa hasta devolver éxito. En firma, PostgreSQL confirma antes de actualizar Vertical y el error posterior se ignora.  
**Cómo reproducir:** en staging, cortar SQL Server justo antes de su write y ejecutar dieta/firma; luego invertir el fallo, dejando caer PostgreSQL después del write Vertical. Comparar ambos estados y la respuesta HTTP.  
**Impacto:** indicaciones divergentes, medicación/dieta no reflejada en el sistema operativo, alta inconsistente y riesgo directo al paciente.  
**Probabilidad:** media-alta en fallas de red ordinarias.  
**Solución recomendada:** definir sistema de registro y máquina de estados transaccional; outbox/inbox e idempotencia; estados `PENDIENTE/SINCRONIZADO/FALLIDO`, reintentos y conciliación; no reportar éxito hasta estado seguro; no hacer commit dentro del logger.  
**Prueba de corrección:** inyección de fallos en cada frontera de commit demuestra estado consistente o recuperable/auditable, reintento idempotente y conciliación automática.

### P0-09 — Cualquier portador de JWT puede ejecutar numerosas escrituras clínicas

**Archivo/líneas:** `backend/main.py:151-243`, `backend/main.py:2480-2668`, `backend/main.py:4585-5702`, `backend/main.py:8000-12278`; `backend/security.py:43-63`.  
**Descripción:** el middleware sólo valida el JWT. Muchas rutas de notas, signos, alergias, medicación, dieta, consentimientos y formatos no usan `require_role` ni verifican asignación del médico al paciente. El rol procede del token y no se revalida el estado activo del usuario.  
**Cómo reproducir:** crear un token de enfermería/usuario básico legítimo y llamar rutas de escritura médica con un paciente no asignado; desactivar ese usuario y repetir antes del vencimiento.  
**Impacto:** escalamiento horizontal/vertical, alteración de expediente, prescripción y falsificación de acciones clínicas.  
**Probabilidad:** alta para un usuario interno o token robado.  
**Solución recomendada:** política deny-by-default por ruta, roles/capacidades centralizados, relación episodio-profesional, revalidación de usuario activo y pruebas de autorización completas.  
**Prueba de corrección:** matriz rol × endpoint × relación con paciente; todo caso no permitido devuelve 403 sin side effects; token de usuario desactivado se rechaza inmediatamente.

## 4. Hallazgos P1 — resolver antes de producción

### P1-01 — Custodia/rotación de claves no garantiza control exclusivo ni historia confiable

**Archivo/líneas:** `backend/crypto_fea.py:16-48`, `60-91`, `102-167`, `180-239`; `backend/models.py:83-93`.  
**Descripción:** la KEK se deriva de `huella_token` (UUID guardado junto al ciphertext) más un secreto global. Una copia de BD y `HES_HMAC_SECRET` compromete todas las llaves. Cualquier excepción de descifrado activa rotación automática; si insertar historia falla, el error se ignora. La verificación acepta cualquier llave histórica del médico sin key-id ni asociación temporal y la BD no impone append-only/un único activo.  
**Cómo reproducir:** en staging, corromper el ciphertext o provocar error transitorio; observar rotación. Alterar/insertar una llave histórica y verificar una firma correspondiente.  
**Impacto:** pérdida de verificabilidad histórica, sustitución de clave y firma no atribuible inequívocamente.  
**Probabilidad:** media.  
**Solución recomendada:** HSM/KMS, key-id y vigencia firmada por cada firma; rotación explícita, transaccional y aprobada; historial append-only con controles DB; backups/recuperación de claves.  
**Prueba necesaria:** fault injection de descifrado no rota; DB impide update/delete de historia; firmas antiguas verifican sólo con su key-id y fallan ante sustitución.

### P1-02 — El TSA RFC 3161 se analiza, pero no se verifica criptográficamente

**Archivo/líneas:** `backend/tsa_client.py:51-122`, `153-175`; `backend/main.py:5803-5805`, `6766`.  
**Descripción:** la solicitud omite nonce. La respuesta se parsea y compara el imprint, pero no se valida firma CMS, certificado, cadena, EKU, vigencia, revocación ni identidad de TSA. El resultado se etiqueta como verificado; una falla TSA es no bloqueante y no deja una política clara de validez temporal.  
**Cómo reproducir:** alimentar un token ASN.1 sintácticamente válido con imprint esperado pero firma/certificado no confiable; observar aceptación. Probar replay de respuesta al no haber nonce.  
**Impacto:** sello de tiempo falsificable y falsa certeza probatoria.  
**Probabilidad:** media; aumenta con compromiso/intermediario o datos manipulados.  
**Solución recomendada:** librería/verificador RFC 3161 completo, trust store pinneado, nonce, política y estados explícitos; cola de reintento o bloqueo según política clínica/jurídica.  
**Prueba necesaria:** vectores válidos e inválidos (firma, cadena, EKU, fecha, nonce, imprint, revocación); TSA caído deja estado inequívoco y recuperable.

### P1-03 — Auditoría mutable, incompleta y con fallos silenciosos; impersonación sin trazabilidad suficiente

**Archivo/líneas:** `backend/models.py:231-241`; `backend/main.py:536-558`, `687-735`; `backend/security.py:73-84`.  
**Descripción:** `auditoria_logs` es una tabla ordinaria sin append-only, hash encadenado ni almacenamiento externo. El helper confirma su propia transacción y traga excepciones. La función de impersonación permite a admin/sistemas emitir token de otra identidad sin motivo, aprobación ni evento robusto; muchas llamadas registran IP nula.  
**Cómo reproducir:** negar INSERT al logger y ejecutar una acción; ésta continúa. Actualizar/borrar un log con credenciales de aplicación. Impersonar y comparar evidencia disponible.  
**Impacto:** no se puede reconstruir fielmente el expediente ni atribuir cambios; afecta investigación y no repudio.  
**Probabilidad:** alta ante errores de BD y media para abuso interno.  
**Solución recomendada:** auditoría transaccional/outbox, append-only con controles DB/WORM y hash encadenado, actor real + actor efectivo + motivo + IP/request-id; alertas cuando no pueda auditarse.  
**Prueba necesaria:** DB rechaza UPDATE/DELETE; toda mutación tiene evento; fallo de auditoría bloquea o deja outbox durable; impersonación queda atribuida extremo a extremo.

### P1-04 — Doble submit/doble firma sin idempotencia ni restricción única

**Archivo/líneas:** `frontend/src/pages/PatientDashboard.jsx:1491-1674`; `frontend/src/components/BiometricSignModal.jsx:65-101`; `frontend/src/components/BiometricPatientSignModal.jsx:220-249`; `backend/models.py:270-302`; `backend/main.py:5855-5891`, `5986-6021`.  
**Descripción:** efectos React dependen de un FMD global y usan estado asíncrono como candado. Dos eventos/renders pueden iniciar dos POST antes de que `submitting` cambie. Backend no recibe idempotency-key ni tiene una restricción única de firma activa/versionada; revoca e inserta con carreras.  
**Cómo reproducir:** emitir dos eventos de captura o dos POST simultáneos idénticos; verificar firmas duplicadas, dos writes Vertical o estados activo/revocado inconsistentes.  
**Impacto:** doble prescripción/firma, evidencia ambigua y conflictos clínicos.  
**Probabilidad:** media-alta con sensores/eventos y red lenta.  
**Solución recomendada:** lock sincrónico por `useRef`, desuscripción/cancelación, idempotency-key ligada a challenge/acción, restricción única y transacción con bloqueo/versión.  
**Prueba necesaria:** 20/50 solicitudes concurrentes producen exactamente un efecto y respuestas repetibles; doble clic y doble evento no duplican.

### P1-05 — Uploads arbitrarios quedan públicamente servidos desde el mismo origen

**Archivo/líneas:** `backend/main.py:1810-1860`, `2730-2754`, `2797-2869`, `247-249`.  
**Descripción:** fotos y escaneos conservan extensiones suministradas, con validación insuficiente de tipo/contenido, y se almacenan bajo `static/`. Los escaneos RH aceptan múltiples contenidos y se devuelven como URL pública.  
**Cómo reproducir:** subir SVG/HTML o archivo con MIME/extensión engañosos y abrir su URL directa sin token; probar malware/EICAR sólo en laboratorio.  
**Impacto:** exposición de documentos RH, distribución de malware y posible contenido activo/stored-XSS en el origen confiable.  
**Probabilidad:** media-alta.  
**Solución recomendada:** almacenamiento privado, allowlist y detección por contenido, renombrado sin extensión controlada, AV/sandbox, descarga con `Content-Disposition`, autorización y límites.  
**Prueba necesaria:** corpus malicioso rechazado; URL directa 404/401; sólo rol autorizado descarga; headers impiden ejecución inline.

### P1-06 — Sesiones largas, HTTP permitido y configuración perimetral insegura

**Archivo/líneas:** `backend/main.py:87-96`, `90`, `251-263`, `472-500`; `backend/security.py:22-63`; `frontend/src/services/api.js:12-18`; `mobile_app/src/app/server-setup.tsx:18-25`; `mobile_app/src/api.js:13-32`.  
**Descripción:** JWT HS256 dura 480 minutos, sin `jti`, issuer/audience, revocación ni comprobación de usuario activo en middleware. Web guarda token en `localStorage`; móvil permite cualquier HTTP/HTTPS y envía token al host configurado. CORS y TrustedHost incluyen `*`; no se fuerza HTTPS/HSTS.  
**Cómo reproducir:** capturar un token, desactivar usuario y reutilizarlo; configurar móvil a HTTP/host controlado en laboratorio; inspeccionar token en localStorage; enviar Host arbitrario.  
**Impacto:** robo/reutilización de sesión y credenciales clínicas, exposición en red y mayor radio de ataque.  
**Probabilidad:** alta en LAN/Wi-Fi si se despliega como el BAT.  
**Solución recomendada:** TLS obligatorio, hosts/orígenes cerrados, access token corto + refresh rotado/revocable, revalidar estado, cookie HttpOnly o mitigación XSS, allowlist/pinning móvil y rate limiting de login/biometría.  
**Prueba necesaria:** HTTP falla/redirige sin credenciales; usuario desactivado se corta; refresh replay falla; Host/CORS no autorizados se rechazan; rate-limit bajo fuerza bruta.

### P1-07 — La captura móvil de enfermería no puede guardarse con el contrato actual

**Archivo/líneas:** `mobile_app/src/app/captura-enfermeria.tsx:31-47`, `64-95`, `145-147`; `backend/schemas.py:183-203`; `backend/main.py:2070-2086`.  
**Descripción:** el móvil omite `habitacion_capturada`, campo obligatorio del request, por lo que el backend responde 422. Además muestra `m.nombres/m.apellidos`, mientras el API entrega `nombre_completo`, dejando médicos sin etiqueta. El typecheck móvil ya falla.  
**Cómo reproducir:** completar una captura desde la app; observar 422. Abrir el selector de médicos y comprobar etiquetas indefinidas.  
**Impacto:** flujo operativo de enfermería bloqueado y posible abandono de registro clínico.  
**Probabilidad:** alta; ocurre en el camino normal.  
**Solución recomendada:** contrato OpenAPI tipado compartido, enviar la habitación validada y mapear campos correctos; manejo específico de 422/401 y pruebas de contrato.  
**Prueba necesaria:** E2E móvil registra y recupera captura; contrato generado compila; pruebas con cama/medico faltante y sesión expirada.

### P1-08 — Errores de ejecución confirmados en verificación pública y consentimientos

**Archivo/líneas:** `frontend/src/pages/VerificarDocumento.jsx:10-53`, `172`; `frontend/src/pages/PatientDashboard.jsx:2583-2584`, `2700-2701`.  
**Descripción:** `docCode` se usa sin declararse, por lo que la pantalla de verificación lanza `ReferenceError`. Dos guardados de consentimiento usan `p` fuera de alcance. Vite compila porque no hace typecheck semántico completo; ESLint sí los detecta.  
**Cómo reproducir:** abrir ruta de verificación o ejecutar guardado de consentimientos 15/02; observar excepción en consola y operación interrumpida.  
**Impacto:** imposibilidad de validar evidencia y pérdida/no registro de consentimientos.  
**Probabilidad:** alta en esos flujos.  
**Solución recomendada:** corregir origen de parámetros/folio y bloquear CI ante `no-undef`; error boundary y mensajes recuperables.  
**Prueba necesaria:** E2E de QR/verificación y de cada consentimiento; CI debe fallar ante cualquier identificador no definido.

### P1-09 — No existe red de seguridad automatizada para flujos clínicos críticos

**Archivo/líneas:** `frontend/package.json`; `mobile_app/package.json`; estado Git de `backend/test_crypto_fea.py` y `backend/test_tsa_client.py`.  
**Descripción:** no se encontró suite activa. Frontend lint tiene 286 errores y móvil no typecheckea. No hay pruebas de autorización, firma, biometría, concurrencia, compatibilidad SQL Server, PDF o recuperación.  
**Cómo reproducir:** inventariar scripts/test files; ejecutar lint/typecheck.  
**Impacto:** cambios aparentemente correctos pueden reabrir bypasses o romper atención clínica sin detección.  
**Probabilidad:** alta en cada entrega.  
**Solución recomendada:** pipeline obligatorio descrito en sección 7, fixtures sin PHI y ambientes efímeros; ninguna corrección se cierra sin prueba negativa asociada.  
**Prueba necesaria:** CI reproducible con cobertura por riesgo y gates de lint/type/build/security/integration/E2E.

### P1-10 — Continuidad operativa no definida ni probada

**Archivo/líneas:** `iniciar.bat:7-13`; `scripts/backup_db.bat:33-44`; `scripts/backup_db.sh:28-34`; `preparar_produccion.py:16-94`.  
**Descripción:** proceso único con reload, sin health/readiness, supervisor, monitoreo o restart documentado. Backups son dumps locales, sin cifrado, copia externa, verificación ni restore drill. No hay RTO/RPO, runbook de desastre, modo clínico degradado ni control de disco lleno.  
**Cómo reproducir:** terminar backend/Node, llenar volumen en laboratorio, corromper backup y observar ausencia de detección/recuperación automática.  
**Impacto:** interrupción hospitalaria y pérdida no detectada de expedientes/evidencia.  
**Probabilidad:** media-alta a lo largo de la operación.  
**Solución recomendada:** arquitectura operativa supervisada, probes y alertas, backups 3-2-1 cifrados/inmutables, restauraciones periódicas, RTO/RPO aprobados, capacidad/retención y procedimiento offline/degradado.  
**Prueba necesaria:** game day documentado: caída de cada servicio, restore completo y point-in-time, disco lleno y conmutación; medir RTO/RPO reales.

### P1-11 — “SQL Server sólo lectura” contradice escrituras reales y un GET produce cambios

**Archivo/líneas:** `docs/00_Inicio.md`, `docs/Arquitectura.md`, `docs/Database.md`; `backend/kh_database.py` (múltiples INSERT/UPDATE/DELETE); `backend/main.py:743-965`.  
**Descripción:** documentación/AGENTS declara KH_HE sólo lectura, pero la aplicación prescribe, suspende, firma y actualiza SQL Server. Además, `GET /api/pacientes` sincroniza, inserta y da altas automáticamente, con commits durante una lectura. Esto rompe semántica, permite efectos por refresh/caché y complica carreras.  
**Cómo reproducir:** snapshot de ambas BD; invocar GET concurrentemente o con cambios Vertical; comparar altas/inserts. Auditar permisos efectivos de la cuenta KH.  
**Impacto:** modificaciones inesperadas, duplicados, altas erróneas y controles de despliegue basados en una premisa falsa.  
**Probabilidad:** alta; el GET es frecuente.  
**Solución recomendada:** corregir arquitectura/documentación; separar sincronización en job/command idempotente y transaccional; mínimo privilegio con cuenta de escritura explícita y reconciliación.  
**Prueba necesaria:** GET es side-effect free; sync concurrente no duplica ni da alta incorrecta; auditoría DB confirma permisos mínimos.

### P1-12 — Dependencias con vulnerabilidades conocidas y builds no reproducibles

**Archivo/líneas:** `frontend/package-lock.json`; `mobile_app/package-lock.json`; `backend/requirements.txt`.  
**Descripción:** `npm audit --omit=dev` reportó 5 altas/2 moderadas en frontend (incluye React Router, PostCSS, nanoid, browserslist) y 10 altas/16 moderadas en móvil (incluye xmldom, Metro, image-size, js-yaml). Python usa mayormente rangos/no pinning y no pudo auditarse porque `pip-audit` no está instalado.  
**Cómo reproducir:** ejecutar audits contra lockfiles y un scanner Python/SBOM en CI.  
**Impacto:** DoS, traversal/divulgación en tooling y superficie móvil/web; artefactos diferentes entre instalaciones. La explotabilidad exacta debe evaluarse por ruta de uso.  
**Probabilidad:** media.  
**Solución recomendada:** actualizar lockfiles con pruebas, pinning/hash de Python, SBOM y escaneo continuo; separar dependencias de build/runtime y definir SLA por severidad.  
**Prueba necesaria:** audits sin altas/critical aceptadas o excepción documentada; rebuild hermético y smoke/E2E tras upgrades.

## 5. Hallazgos P2/P3

### P2-01 — Ciclo de vida del lector y microservicio biométrico no son controlables ni reproducibles

**Archivo/líneas:** `frontend/src/hooks/useDigitalPersona.js:10-30`, `119-150`, `187-215`; `frontend/src/hooks/useFingerprint.js:1-90`; `../Teru/Bio-security/server.js:1-115`; `preparar_produccion.py:58-66`.  
**Descripción:** hay dos stacks biométricos (puertos 8082/8081). El singleton deja un listener anónimo de fallo sin remover y reintenta; componentes sólo quitan suscriptores, no garantizan detener captura. El servicio vive fuera del repositorio y el empaquetador copia un directorio hermano. FAR `10000` está hardcodeado, sin calibración ni pruebas.  
**Cómo reproducir:** abrir/cerrar modales repetidamente, desconectar/reconectar sensor y contar listeners/peticiones; construir desde un checkout limpio sin `../Teru`.  
**Impacto:** eventos duplicados, capturas en pantalla equivocada, fuga de recursos y build no reproducible.  
**Probabilidad:** media.  
**Solución recomendada:** un único adaptador con máquina de estados, cleanup/retry acotado y ownership de captura; versionar servicio/lockfile; configurar y validar umbral con estudio biométrico.  
**Prueba necesaria:** 100 ciclos mount/unmount mantienen un listener; desconexión no produce loop; build limpio incluye versión/hash exactos; pruebas FAR/FRR aprobadas.

### P2-02 — Gestión de conexiones y migraciones de arranque frágiles

**Archivo/líneas:** `backend/database.py:12-86`; `backend/kh_database.py:24-107`.  
**Descripción:** el engine PostgreSQL carece de `pool_pre_ping`, límites/recycle/timeouts explícitos; import ejecuta ALTER TABLE ad hoc y traga fallos. SQL Server tiene precheck/connect timeout, pero no se observa timeout de consulta uniforme.  
**Cómo reproducir:** matar conexiones o bloquear una consulta; reiniciar dos instancias simultáneas durante ALTER; medir recuperación.  
**Impacto:** workers bloqueados, arranque parcialmente migrado y caída prolongada.  
**Probabilidad:** media.  
**Solución recomendada:** migraciones versionadas fuera del arranque, pool/statement timeouts y circuit breaker; readiness dependiente del estado mínimo.  
**Prueba necesaria:** conexión stale se recupera; query bloqueada corta dentro del SLO; dos despliegues no compiten; migración fallida impide servir tráfico.

### P2-03 — Frontend monolítico, estado obsoleto y carga excesiva

**Archivo/líneas:** `frontend/src/pages/PatientDashboard.jsx` (~12 mil líneas); `frontend/src/hooks/useQueries.js`; múltiples usos directos de `api.get/post`; `frontend/src/components/ClinicalPdfViewer.jsx:12`, `321`.  
**Descripción:** gran parte de las llamadas evita TanStack Query y usa efectos/caché manual; lint reporta dependencias incompletas de hooks. El bundle principal es grande y el visor puede descargar worker desde `unpkg.com`, dependencia externa no controlada.  
**Cómo reproducir:** throttling/red intermitente, navegar rápido entre pacientes y comparar respuestas tardías; bloquear CDN y abrir PDF; medir memoria/bundle.  
**Impacto:** datos del paciente previo, requests duplicados, pantalla lenta o visor indisponible.  
**Probabilidad:** media.  
**Solución recomendada:** migración incremental por flujo a queries/mutations cancelables con keys por paciente, code splitting y worker local versionado; no refactor masivo antes de tests.  
**Prueba necesaria:** pruebas de cambio rápido de paciente y respuesta fuera de orden; presupuesto de bundle; PDF funciona sin Internet.

### P2-04 — Fechas naive y mezcla de UTC/local pueden distorsionar evidencia

**Archivo/líneas:** `backend/security.py:38`; `backend/main.py` (usos de `datetime.utcnow()`/`datetime.now()` y cadenas ISO); `mobile_app/src/app/captura-enfermeria.tsx:72-84`.  
**Descripción:** se mezclan datetimes sin zona, hora local del dispositivo y UTC; algunas salidas pueden añadir semántica UTC a valores naive. Cambios DST/configuración del host y relojes móviles afectan orden y expiración.  
**Cómo reproducir:** ejecutar con zonas/relojes distintos y en cambio de horario; comparar fecha clínica, JWT, challenge y TSA.  
**Impacto:** orden cronológico ambiguo, challenges mal expirados y evidencia temporal inconsistente.  
**Probabilidad:** media.  
**Solución recomendada:** instantes UTC timezone-aware, zona clínica explícita sólo para presentación, reloj servidor para actos y sincronización NTP monitoreada.  
**Prueba necesaria:** casos multi-zona/DST y reloj cliente incorrecto; round-trip conserva instante y representación esperada.

### P3-01 — Observabilidad y mensajes de error no permiten diagnóstico operacional seguro

**Archivo/líneas:** `backend/main.py` y `backend/kh_database.py` (numerosos `print`/`except Exception`); `mobile_app/src/app/captura-enfermeria.tsx:49-53`, `89-93`.  
**Descripción:** logs no estructurados, errores tragados y mensajes genéricos impiden correlacionar una operación entre frontend, backend y Vertical. No hay request-id, métricas, SLO ni alertas; tampoco política de redacción central.  
**Cómo reproducir:** provocar timeout de cada dependencia y tratar de reconstruir una operación sólo con logs.  
**Impacto:** MTTR alto y riesgo de loguear datos clínicos al añadir diagnóstico improvisado.  
**Probabilidad:** alta durante incidentes.  
**Solución recomendada:** logging estructurado con correlation-id, códigos de error seguros, métricas/alertas y redacción explícita de PHI/FMD/token.  
**Prueba necesaria:** ejercicio de incidente reconstruye el flujo por ID sin exponer biometría, JWT ni contenido clínico.

## 6. Plan de pruebas de fallos (ambiente aislado)

| Escenario | Estado observado/inferencia actual | Criterio seguro exigido |
|---|---|---|
| PostgreSQL caído | Login/estado local y la mayoría de rutas fallan; no hay modo degradado | 503 rápido, ninguna escritura Vertical huérfana, alerta y recuperación documentada |
| SQL Server caído | Algunos flujos fallan; dieta y otros pueden continuar/confirmar parcial | Nunca éxito falso; estado pendiente durable y conciliable |
| Microservicio biométrico caído | Médico suele fallar; firmante puede caer en reemplazo inseguro | 503/fallo cerrado, cero firma y cero cambio biométrico |
| Sensor desconectado antes/durante captura | Reintentos/listeners sin garantía de cleanup | Cancelación visible, timeout acotado, captura detenida y sin submit |
| Timeout/respuesta biométrica corrupta | Excepciones heterogéneas; fallback de firmante inseguro | Fallo cerrado, auditado y sin side effects |
| Doble clic/doble evento/doble firma | Sin idempotencia/unique; carrera probable | Exactamente un efecto; misma respuesta para reintentos |
| 20 y 50 usuarios simultáneos | No hay prueba; matching 1:N serial y backend único | Latencia/SLO definidos, sin pool starvation, duplicados ni mezcla de pacientes |
| Sesión expirada durante operación | Respuestas genéricas; móvil sin manejo global de 401 | Operación no parcial; reautenticación segura y reintento idempotente |
| JWT inválido/desactivado | Inválido se rechaza; desactivado puede seguir hasta 8 h | Ambos rechazados antes de side effects |
| Reinicio backend entre writes | No hay saga/outbox general | Recuperación automática o cola auditable; nunca estado final falso |
| Pérdida momentánea de red | Frontend puede reintentar/doblar manualmente | Estado incierto explícito, consulta de resultado por idempotency-key |
| TSA caído/corrupto | Firma continúa y verificación TSA es insuficiente | Política explícita; pendiente/reintento o bloqueo, sin “verificado” falso |
| PDF no generable | Hay rutas que tragan error y conservan éxito/firma | Firma/documento con estado claro; regeneración idempotente y alerta |
| Disco lleno | No hay preflight/alerta | Falla atómica, rollback/cola y umbral de capacidad alertado |
| Vertical devuelve null/tipos/texto inesperado | Mucho parsing tolerante y excepciones amplias | Validación de contrato, cuarentena y ningún cambio destructivo |
| Backup corrupto | No hay verificación/restore drill | Restauración automatizada verificada y medición RPO/RTO |

**Ejecución propuesta:** usar PostgreSQL/SQL Server efímeros o dobles controlados, Toxiproxy para red/latencia, filesystem con cuota, mocks TSA/DigitalPersona y barreras para detener cada operación antes/después de commit. Cada caso debe comparar respuesta, ambas bases, auditoría, PDFs y posibilidad de reintento.

## 7. Estrategia de pruebas automatizadas y gates

### Cobertura mínima por nivel

1. **Unitarias:** canonicalización/hash/firma/verificación; challenges; autorización; estado de sagas; fechas; validadores de archivos y contratos.
2. **Integración:** PostgreSQL real; doble SQL Server; microservicio biométrico; TSA válido/inválido; generación/verificación de PDF.
3. **Seguridad:** inventario de rutas deny-by-default, IDOR, roles, replay, JWT revocado, uploads, path traversal, rate limit y secretos.
4. **Biometría:** 1:1/1:N, no-match, baja calidad, duplicado, timeout, reconexión, FAR/FRR y ausencia de RAW/logs.
5. **Concurrencia:** 20/50 actores, doble firma, doble prescripción, dos rotaciones, dos consumos de nonce, sync simultáneo.
6. **Failure injection:** todos los casos de sección 6 en cada frontera de commit.
7. **E2E:** login, asignación, nota, medicación, consentimiento, firma médico/paciente, QR/verificación, alta/reingreso y captura móvil.

### Gates obligatorios sugeridos

- Backend: lint/typecheck, unit/integration, migración desde copia representativa y scanner de dependencias/secretos.
- Frontend/móvil: lint sin errores, typecheck, tests de componentes, build reproducible, audit sin vulnerabilidades altas no aceptadas.
- Seguridad: matriz de rutas generada desde OpenAPI; toda ruta nueva debe declarar política.
- Release: smoke en artefacto final, firma/SBOM, restauración de backup, prueba de rollback y aprobación clínica/seguridad.
- Un hallazgo sólo cambia a **RESUELTO** cuando su prueba negativa reproduce primero el defecto y pasa después de la corrección.

## 8. Matriz NOM-004-SSA3-2012 / NOM-024-SSA3-2012

Referencias primarias consultadas: [NOM-004-SSA3-2012, DOF](https://www.dof.gob.mx/nota_detalle.php?codigo=5272787&fecha=15/10/2012) y [NOM-024-SSA3-2012, DOF](https://dof.gob.mx/normasOficiales/4956/SALUD1/SALUD1.html). NOM-024 6.6 exige confidencialidad, integridad, disponibilidad, trazabilidad y no repudio, documentos electrónicos inalterables, autenticación y autorización por roles. Esta tabla **no es certificación ni dictamen jurídico**.

| Requisito | Clasificación | Evidencia en código | Evidencia faltante | Riesgo | Acción necesaria |
|---|---|---|---|---|---|
| NOM-004: integración, uso, manejo, archivo, conservación y confidencialidad | PARCIALMENTE IMPLEMENTADO | Expediente, PDFs, BD y roles existen | Política aprobada, custodia, retención, acceso y destrucción; rutas públicas contradicen confidencialidad | Divulgación/pérdida | Cerrar P0-01/P1-05 y validar proceso documental |
| NOM-004: conservación mínima aplicable desde último acto médico | NO DEMOSTRABLE SOLO MEDIANTE CÓDIGO | Hay almacenamiento persistente/backups básicos | Política de retención, capacidad, backup/restore y evidencia de ejecución | Pérdida histórica | Definir retención, legal hold y pruebas de restauración |
| NOM-004: notas con fecha, hora, nombre y firma de quien las elabora | PARCIALMENTE IMPLEMENTADO | Modelos/PDF incluyen metadatos y firmas en varios formatos | Cobertura de todos los formatos, identidad real, zona horaria y firma ligada al contenido | Nota no atribuible | Inventario de formatos + tests de campos y FEA |
| NOM-004: notas legibles, sin alteraciones indebidas | PARCIALMENTE IMPLEMENTADO | PDFs y versiones parciales | Inmutabilidad; hoy se puede cambiar documento sin invalidar firma | Evidencia alterable | Snapshot/versionado y firma sobre documento real |
| NOM-004: cartas de consentimiento con datos/firmas requeridos | PARCIALMENTE IMPLEMENTADO | Formatos 02/04/06/07/08/11/15/19/43 | Validación clínica/jurídica de cada plantilla; flujos tienen bypass/bugs | Consentimiento inválido | Revisión jurídica por formato y E2E completo |
| NOM-004: confidencialidad y entrega a terceros autorizados | PARCIALMENTE IMPLEMENTADO | JWT y algunas rutas con roles | PDFs/static y alias públicos; no hay prueba de autorización por titular | Brecha de PHI | Autorización deny-by-default y trazabilidad de entrega |
| NOM-024 5.3/5.9: confidencialidad, integridad, confiabilidad, datos completos e inalterados | PARCIALMENTE IMPLEMENTADO | Cifrado parcial, hashes, ECDSA, BD | Hash no cubre documento; commits parciales; archivos públicos | Integridad falsa | Cerrar P0-01/P0-05/P0-08 |
| NOM-024 5.6: conservación y disponibilidad a través del tiempo | NO DEMOSTRABLE SOLO MEDIANTE CÓDIGO | Scripts de dump local | HA, DR, restore probado, RTO/RPO, capacidad | Interrupción/pérdida | Programa de continuidad y evidencia periódica |
| NOM-024 5.8 y 3.54: trazabilidad inequívoca | PARCIALMENTE IMPLEMENTADO | `auditoria_logs`, historial de llaves | Logs mutables/fallables; actor efectivo/real incompleto | No reconstrucción | Auditoría append-only y pruebas de completitud |
| NOM-024 6.6.1: SGSI que cubra CIA, trazabilidad y no repudio | REQUIERE VALIDACIÓN JURÍDICA/OPERATIVA | Algunos controles técnicos | SGSI, análisis de riesgo, responsables, políticas, monitoreo y revisiones | No conformidad sistémica | Implantar/validar SGSI con evidencia |
| NOM-024 6.6.2: documentos estructurados e inalterables y capacidad de FEA | PARCIALMENTE IMPLEMENTADO | ECDSA P-256 y tablas de firma | Control exclusivo, vínculo a datos, detección de modificación y TSA confiable | FEA no demostrable | Rediseño acotado de evidencia + peritaje jurídico/cripto |
| NOM-024 6.6.3: autenticación de usuarios, organizaciones y dispositivos | PARCIALMENTE IMPLEMENTADO | Usuario/contraseña/JWT y biometría | Rutas públicas; dispositivo/sensor/servicios no autenticados; replay | Acceso ilegítimo | Autenticación extremo a extremo y challenge obligatorio |
| NOM-024 6.6.4: autorización basada en roles | PARCIALMENTE IMPLEMENTADO | `require_role` en algunas rutas | Muchas mutaciones sólo requieren cualquier JWT | Escalamiento | Política central y matriz automatizada |
| NOM-024 6.6.5: autenticación, cifrado y FEA en intercambio | PARCIALMENTE IMPLEMENTADO | JWT/ECDSA/TSA parcial | HTTP permitido, firma no vinculada, trust TSA incompleto | Intercepción/falsedad | TLS, identidad de servicios y verificación completa |
| NOM-024: guías, formatos, catálogos e interoperabilidad aplicables | REQUIERE VALIDACIÓN JURÍDICA/OPERATIVA | Uso de datos Vertical y formatos internos | Mapeo a guías/catálogos DGIS vigentes, pruebas semánticas y alcance | Intercambio no conforme | Gap assessment especializado |
| NOM-024 7: evaluación de conformidad/certificación cuando aplique | REQUIERE VALIDACIÓN JURÍDICA/OPERATIVA | No se encontró certificado/dictamen | Alcance legal, unidad verificadora, dictamen y certificado | Afirmación de cumplimiento infundada | Consulta jurídica y procedimiento formal |

## 9. Contradicciones documentación–implementación

| Afirmación documental | Implementación observada | Consecuencia |
|---|---|---|
| SQL Server `KH_HE` es “sólo lectura” | `kh_database.py` contiene INSERT/UPDATE/DELETE para medicación, dieta, firma y formatos | Arquitectura, permisos y análisis de riesgo incorrectos |
| Se almacena FMD/plantilla irreversible | Frontend captura `SampleFormat.Raw` y lo persiste antes de convertir en el microservicio | Riesgo biométrico subestimado |
| Challenge de 120 s previene replay | Backend acepta challenge ausente y la mayoría de flujos no lo envía | Control documentado no efectivo |
| FEA protege integridad/no repudio del documento | Se firma resumen controlado por cliente y se verifica cadena almacenada | La evidencia no cubre el acto clínico real |
| Inicio/paquete de producción | Arranca seeds, HTTP, `--reload` y copia microservicio desde directorio hermano | Despliegue inseguro/no reproducible |
| Auditoría permite reconstrucción | Logs son mutables, su commit puede fallar silenciosamente | Trazabilidad no demostrable |

La regla del proyecto indica que, cuando código y documentación se contradicen, manda el código y debe actualizarse la nota. Esa actualización deberá hacerse en la fase de corrección, no en esta auditoría.

## 10. Disponibilidad y puntos únicos de falla

| Componente | Qué detiene | Recuperación observada | Prioridad |
|---|---|---|---|
| Backend FastAPI único | Toda UI/API/expediente | BAT manual; sin supervisor/probes | P0 operacional |
| PostgreSQL | Auth local, pacientes, biometría, firmas/auditoría | Dump local; restore no probado | P0 operacional |
| SQL Server KH/Vertical | La mayoría del expediente y actos clínicos | Sin cola/saga general; estados parciales | P0 clínico |
| Node DigitalPersona 8082 | Login/firma biométrica | Sin supervisor/health; fallback inseguro de firmante | P0 seguridad |
| Lector/servicio DigitalPersona cliente | Firmas y login biométrico del puesto | Reintentos UI; sin procedimiento alterno aprobado | P1 |
| Disco local `static/`/PDF/backup | PDFs, uploads y potencialmente backup | Sin cuota/alerta/replicación | P1 |
| Secreto global HES/JWT | Todas las sesiones/llaves derivadas | Rotación y recuperación no demostradas | P0 seguridad |
| TSA externo | Sellado temporal | Se degrada sin política; verificación insuficiente | P1 probatorio |
| CDN del worker PDF | Visor clínico | Fallback externo no controlado | P2 |
| Red LAN/host único | Operación completa | Sin modo offline/degradado documentado | P0 operacional |

## 11. Orden recomendado para la siguiente fase

1. Contención inmediata: impedir despliegue, rotar credenciales conocidas, cerrar rutas/archivos públicos y deshabilitar fallbacks biométricos.
2. Congelar contratos de evidencia: definir documento canónico, idempotencia, estados transaccionales y política TSA/llaves con responsables clínicos, seguridad y jurídico.
3. Crear primero las pruebas negativas de P0; luego aplicar correcciones pequeñas y verificables.
4. Resolver P1 funcionales/operativos, restaurar gates de CI y ejecutar failure/concurrency tests.
5. Realizar piloto sin PHI, evaluación biométrica, restore drill, pentest independiente y validación NOM/jurídica antes de cualquier go-live.

**Fin de la primera fase. No se implementaron correcciones.**

# Auditoría final independiente de preproducción — Bitácora Médica HES

**Fecha:** 2026-09-17.  
**Resultado:** **NO LISTO para piloto/preproducción; NO LISTO para go-live.**  
**Árbol auditado:** workspace `D:/Escritorio/Bitacora_HES`, con modificaciones previas sin confirmar. HEAD de referencia: `787027e2902e466f586f6bc5041600edb98a1648`; ese commit por sí solo no representa el código auditado.

La suite existente pasa, pero varias afirmaciones de cierre no sobreviven a pruebas independientes. Se clasifican los **21 originales: 12 REABIERTO, 6 CONFIRMADO_CERRADO, 2 GATE_EXTERNO_PENDIENTE y 1 MITIGADO_Y_BLOQUEADO_SEGURO**. Los defectos reproducidos son de confidencialidad, identidad, evidencia de firma, consistencia o éxito falso; no dependen de que falten SQL Server STAGING, TLS productivo o lector físico.

No se editó código, configuración ni informes anteriores. No se ejecutó el empaquetador de producción. Sólo se genera este informe como entregable. Las contradicciones documentales se registran aquí, respetando la instrucción de no modificar el proyecto.

## Alcance y método

Se contrastaron las once referencias solicitadas: `AUDITORIA_PREPRODUCCION.md`, `REVISION_BIOMETRIA_CRIPTO_ASTRA.md`, `CORRECCION_P0_AUTORIZACION.md`, `INFRAESTRUCTURA_TEST_POSTGRES.md`, `ESTABILIZACION_BIOMETRIA.md`, `ESTABILIZACION_FEA_CRIPTO.md`, `ESTABILIZACION_CONSISTENCIA_DB_FINAL.md`, `PREPRODUCCION_TECNICA_FINAL.md`, `FAILURE_INJECTION_PREPRODUCCION.md`, `CONTINGENCIA_OPERATIVA.md` y `DEPENDENCY_INVENTORY.md`, todas en la raíz del workspace. Se consultó la bóveda obligatoria y las notas técnicas correspondientes.

La evidencia combina lectura del código actual, suite PostgreSQL real, migraciones desde esquema vacío, HTTP mediante TestClient y sondas adversariales ejecutadas en memoria. **No se conectó a KH_HE, Vertical, TSA ni infraestructura productivos.** Las sondas adicionales fijaron SQL Server a TEST/loopback y reemplazaron sus conexiones y respuestas de red por datos sintéticos. Los secretos utilizados por las sondas fueron sintéticos; el helper local de pruebas cargó configuración para derivar exclusivamente la base local terminada en `_test`, sin mostrar credenciales ni utilizar la base operativa.

Los dobles se limitaron a las fronteras externas indicadas en cada hallazgo. No se sustituyeron middleware, autorización, consumo de challenges, persistencia PostgreSQL, firma ECDSA o verificadores para obtener los resultados adversariales. La prueba de carreras añadió únicamente una barrera antes del commit para forzar un intercalado posible. Las sondas no quedaron incorporadas al código ni a la suite.

## Clasificación de todos los P0/P1 originales

“Bloquea preproducción” se refiere al piloto solicitado como estado listo para validación operativa, no a la posibilidad de seguir ejecutando pruebas aisladas de desarrollo. Los gates exclusivamente productivos no bloquean por sí solos el uso de datos sintéticos.

| HALLAZGO ORIGINAL | ESTADO FINAL | EVIDENCIA | GATE PENDIENTE | BLOQUEA PREPRODUCCIÓN (SI/NO) |
|---|---|---|---|---|
| P0-01 — Bypass global y exposición clínica/PDF | **REABIERTO** | Auth global y archivos privados funcionan; AF-01 reproduce portal público enumerable y lectura de expediente/cadena clínica con rol limpieza. | Cierre AF-01; aprobación del alcance público y horizontal. | SI |
| P0-02 — Mismatch sustituye la identidad | **CONFIRMADO_CERRADO** | Verificador de firmante exige ID, episodio y rol persistido; mismatch, caída, timeout y respuesta inválida rechazan sin cambiar plantilla ni firmar. Suite biométrica ejecutada. | Lector físico para validación operativa, no para corregir este fallback. | NO |
| P0-03 — Challenge opcional/replay | **REABIERTO** | Challenge obligatorio, contextual y atómico confirmado; AF-02 permite volver a atestar RAW previo con un challenge nuevo. | Cierre AF-02 y prueba del componente de captura en puesto. | SI |
| P0-04 — Persistencia de RAW nuevo | **CONFIRMADO_CERRADO** | Altas rechazan FMD embebido; enrolamiento guarda sólo envelope FMD canónico. Migración marca histórico `LEGACY_RAW`; matching lo excluye. | Tratamiento operativo del histórico y reenrolamiento físico. | NO |
| P0-05 — Firma no vinculada al documento real | **REABIERTO** | ECDSA cubre bytes CANONICAL_V2, pero AF-04 valida un slot distinto, no coteja contenido vigente y demuestra snapshot modificable en DB. | Cierre AF-04; repetir verificación negativa por documento solicitado. | SI |
| P0-06 — Sustitución administrativa de identidad FEA | **REABIERTO** | El uso inmediato de la llave anterior sí queda bloqueado; AF-03 demuestra sustitución, rotación y login como médico por el mismo RH. | Cierre AF-03; acreditar control del titular en la transición. | SI |
| P0-07 — Seed/cuentas conocidas/arranque inseguro | **CONFIRMADO_CERRADO** | Seed sólo DEV explícito; BAT rechaza production; bootstrap sin credenciales literales y con cambio obligatorio; systemd sin reload y bind local. | Instalación y credenciales productivas; no se probaron en host real. | NO |
| P0-08 — Dual-write y éxito falso | **REABIERTO** | Intenciones durables presentes, pero AF-06 confirma `SYNCED` tras HTTP 200 vacío de Vertical; AF-07 presenta 202 como éxito; AF-08 reutiliza resultado ajeno. | Cierre AF-06/07/08 y smoke SQL Server STAGING. | SI |
| P0-09 — Autorización insuficiente con JWT | **REABIERTO** | Writes sin política y cuatro rutas indecisas dan 403. AF-01 demuestra que la lectura clínica general sigue permitiendo cualquier identidad activa; no existe bloqueo horizontal general. | Cierre AF-01 y matriz institucional; la decisión funcional no se clasifica como bug. | SI |
| P1-01 — Custodia/rotación/control exclusivo/historia | **REABIERTO** | Key-id exacta, historial protegido, llave activa única y descifrado fail-closed pasan. El control exclusivo de la identidad sigue roto por AF-03; no se reabre por ausencia de HSM. | Cierre AF-03 y custodia operativa del secreto externo a DB. | SI |
| P1-02 — TSA sin garantía criptográfica completa | **REABIERTO** | El verificador CMS sí rechaza vectores inválidos, pero AF-10 prueba que el cliente rechaza una respuesta RFC3161 válida; el estado resumido omite TSA pendiente. | Cierre AF-10; trust store y servicio TSA del entorno. | SI |
| P1-03 — Auditoría incompleta/impersonación | **REABIERTO** | Trigger append-only e inicio/fin de impersonación existen. AF-11 demuestra cambios de rol sin evento y detecta logs clínicos que se hacen flush después del commit y se pierden al cerrar. | Cierre AF-11. | SI |
| P1-04 — Doble submit/firma concurrente | **REABIERTO** | 50 llamadas con la misma clave producen una intención; AF-05 reproduce dos POST reales, dos 200 y dos firmas ACTIVA del mismo documento/slot con claves distintas. | Cierre AF-05 y AF-08. | SI |
| P1-05 — Uploads públicos/arbitrarios | **CONFIRMADO_CERRADO** | Almacenamiento privado, nombre UUID, límites, allowlist, rechazo HTML/SVG, contención de path y descarga RH como attachment. Sin montaje público de static. | Ninguno para la exposición original. No se afirma disponer de antivirus ni análisis profundo de PDF/XLSX. | NO |
| P1-06 — Sesiones/HTTP/perímetro | **GATE_EXTERNO_PENDIENTE** | JWT con jti/issuer/audience, expiración acotada en producción, revocación y revalidación de activo/rol; configuración rechaza wildcard y ausencia de proxy HTTPS. | Activación TLS/proxy/hosts/origins/secrets y validación del cliente en entorno productivo. | NO |
| P1-07 — Contrato móvil de captura | **CONFIRMADO_CERRADO** | Móvil envía `habitacion_capturada`, muestra `nombre_completo`; typecheck ejecutado sin errores. | Smoke operativo móvil; no se afirma E2E físico ejecutado. | NO |
| P1-08 — Identificadores indefinidos en frontend | **CONFIRMADO_CERRADO** | Lint runtime y build pasan; corregidos los identificadores originales. Los éxitos falsos de sincronización se registran en AF-07, no se ocultan tras el build. | Ninguno para los ReferenceError originales. | NO |
| P1-09 — Red de seguridad insuficiente | **REABIERTO** | Existen 139 pruebas y 10 subpruebas; los falsos positivos relevantes de cierre se identifican abajo y fueron atravesados por sondas independientes. | Regresiones que alcancen los caminos AF-01 a AF-11. | SI |
| P1-10 — Continuidad operativa | **GATE_EXTERNO_PENDIENTE** | Supervisor, probes, runbook, script de backup cifrado/copia verificada y restore sintético existen. Restore previo no se vuelve a presentar como ejecución de esta auditoría. | Programación, custodia, off-host y simulacro operativo institucional. | NO |
| P1-11 — GET con efectos/SQL Server supuestamente read-only | **REABIERTO** | AF-09 reproduce INSERT PostgreSQL desde GET y constata escritura de PDF/registro QR desde GET. Mutadores SQL Server están declarados, con los límites indicados abajo. | Cierre AF-09; integración STAGING. | SI |
| P1-12 — Dependencias vulnerables/builds | **MITIGADO_Y_BLOQUEADO_SEGURO** | Audits actuales: web/biometría 0; móvil 14 moderadas, 0 altas/críticas. Advisory Python persiste en ruta de firma no usada por HES; FEA usa cryptography. | Reevaluación prevista en inventario. Python no tiene lock completo: no se certifica reconstrucción hermética. | NO |

## NUEVOS_BLOQUEADORES

Se encontraron las siguientes manifestaciones no contenidas por los cierres anteriores. Reabren los originales indicados; no constituyen iniciativas nuevas ni recomendaciones generales de arquitectura. Cada una bloquea el dictamen de preproducción. Las clasificaciones de severidad utilizadas son exclusivamente **BLOCKER** y **HIGH**.

### AF-01 — BLOCKER — Exposición clínica pública y a roles no clínicos

**Originales afectados:** P0-01, P0-09.

- [route_policy.py:8](D:/Escritorio/Bitacora_HES/backend/route_policy.py:8) mantiene públicos `/verificar*` y `/api/verificar*` seleccionados. [main.py:8419](D:/Escritorio/Bitacora_HES/backend/main.py:8419) llama directamente al motor de estado; no se limita a entregar un shell HTML. [main.py:8207](D:/Escritorio/Bitacora_HES/backend/main.py:8207) consulta nombre, expediente y edad a partir del folio proporcionado, incluso sin firma o UUID válido.
- [main.py:262](D:/Escritorio/Bitacora_HES/backend/main.py:262) sólo impone roles de lectura a las rutas incluidas en READ_ROLE_POLICIES. El expediente general y [main.py:7282](D:/Escritorio/Bitacora_HES/backend/main.py:7282) quedan fuera; este último devuelve `cadena_original`, que ahora contiene el contenido clínico completo.

**Reproducción ejecutada:** GET anónimo `/verificar?pt=7777&doc=PLT-11` devolvió 200 y el nombre sintético proveniente de la consulta. Con JWT legítimo `limpieza`, GET `/api/ehr/paciente/7777` devolvió 200 con datos clínicos; GET `/api/ehr/paciente/FEA-PT-1/firmas` devolvió el marcador clínico `BYTE-101-MUST-BE-SIGNED` del snapshot firmado real en PostgreSQL TEST.

Se sustituyó sólo la lectura ERP por datos sintéticos. Middleware, política, JWT y serialización fueron reales. La ausencia de una decisión funcional horizontal no es el hallazgo: **la afirmación de bloqueo seguro es falsa porque esas lecturas están abiertas**. Los PDFs y escaneos físicos sí mantienen la protección comprobada por la suite.

### AF-02 — HIGH — El servicio vuelve a atestar RAW anterior con un challenge nuevo

**Original afectado:** P0-03.

[server.js:85](D:/Escritorio/Bitacora_HES/biometric-service/server.js:85) acepta RAW aportado por el llamador, extrae FMD y construye `captured_at` con la hora de procesamiento. Sólo exige que challenge y sesión sean strings no vacíos. No obtiene por sí mismo una adquisición del lector asociada al nonce. [biometric_security.py:102](D:/Escritorio/Bitacora_HES/backend/biometric_security.py:102) valida HMAC/contexto, pero no establece que el RAW se haya capturado después del challenge.

**Reproducción ejecutada:** se ejecutó el handler JavaScript original en VM con transporte Express en memoria y extractor nativo sustituido por una transformación determinista sintética. Dos envíos del mismo RAW archivado con challenges diferentes produjeron el mismo FMD y dos attestations HMAC válidas:

```text
same_archived_raw=true
same_fmd=true
new_challenges=true
both_valid_attestations=true
physical_device_used=false
```

La prueba demuestra el defecto del protocolo de attestación, no el rendimiento o la tasa de aceptación del lector. Requiere disponer de una captura anterior válida y acceso al servicio loopback; no demuestra acceso remoto directo a ese puerto. El consumo de **un mismo nonce** sí está corregido: los 20 consumidores PostgreSQL dejan un ganador. Eso no impide renovar la attestación de material antiguo a través de la interfaz actual.

### AF-03 — BLOCKER — Un mismo RH sustituye identidad, rota FEA y entra como el médico

**Originales afectados:** P0-06, P1-01.

[main.py:3679](D:/Escritorio/Bitacora_HES/backend/main.py:3679) permite al operador autorizado sustituir la plantilla sin comprobar la identidad biométrica anterior. [main.py:3779](D:/Escritorio/Bitacora_HES/backend/main.py:3779) permite al mismo rol completar la actualización FEA comprobando únicamente la plantilla recién sustituida.

**Reproducción HTTP ejecutada:** un único usuario `rh`, sin intervención del médico original, obtuvo challenges y realizó:

1. Reenrolamiento con muestra sintética B: 200.
2. Actualización FEA con esa misma B y otro challenge: 200.
3. Verificación en PostgreSQL: nueva `key_id`, `requiere_actualizacion_fea=false`.
4. Login biométrico con B: 200, identidad del médico objetivo.

El doble del matcher comparó igualdad entre la muestra y la plantilla que recibió; no devolvió incondicionalmente la identidad elegida. Persistencia, challenges, autorización HTTP, rotación y JWT fueron reales.

**Límite preciso:** la llave anterior no se reutilizó silenciosamente y su pública histórica se conservó. Lo que sigue permitido es la suplantación con una llave nueva atribuida al mismo médico. Por ello el bloqueo 423 intermedio no basta para cerrar el hallazgo original de identidad/control exclusivo.

### AF-04 — BLOCKER — Se declara válido otro slot y la evidencia no es inmutable en DB

**Original afectado:** P0-05.

[main.py:8237](D:/Escritorio/Bitacora_HES/backend/main.py:8237) sólo aplica el filtro de slot si encuentra resultados. Si no encuentra el slot solicitado, conserva las firmas de otros slots; después [main.py:8379](D:/Escritorio/Bitacora_HES/backend/main.py:8379) responde `valido=true` indicando el slot solicitado.

**Reproducción HTTP ejecutada:** con una firma ECDSA CANONICAL_V2 real para slot 1, solicitar el estado del mismo formato/paciente con `slot=999` devolvió:

```text
HTTP 200
valido=true
slot=999
slot realmente firmado=1
```

También [main.py:7715](D:/Escritorio/Bitacora_HES/backend/main.py:7715) selecciona por `firma_id` sin ligarlo al paciente/código/slot de la solicitud; sus fallbacks pueden elegir otra firma activa. Este segundo camino se constató estáticamente, sin atribuirle una reproducción HTTP adicional.

[clinical_signing.py:196](D:/Escritorio/Bitacora_HES/backend/clinical_signing.py:196) verifica correctamente el snapshot frente a las columnas de su propia fila y su llave, pero no vuelve a cargar el contenido vigente. Esto permite verificar historia; **no acredita por sí solo el documento operativo que se está consultando**. Las pruebas existentes cambian el snapshot o sus columnas, no el registro fuente posterior a la firma.

Finalmente, el esquema no protege `canonical_payload` con un trigger de inmutabilidad. Una sonda sobre PostgreSQL migrado modificó y confirmó el snapshot sintético; el UPDATE fue aceptado. ECDSA detectaría la alteración al verificar, pero el snapshot original ya se habría perdido. El trigger de protección existente corresponde al historial de llaves, no a esta tabla.

**Controles que sí pasan:** bytes UTF-8 canónicos completos, cambios después del carácter 100, key-id exacta, historia tras rotación, descifrado fail-closed y rechazo de marcadores Vertical como evidencia ECDSA. Los PDFs secundarios no tienen hash firmado; `verify_pdf_hash` no los declara protegidos. Eso no corrige la selección equivocada del documento ni impone inmutabilidad del snapshot.

### AF-05 — HIGH — Dos firmas activas del mismo documento bajo concurrencia

**Original afectado:** P1-04.

[main.py:7008](D:/Escritorio/Bitacora_HES/backend/main.py:7008) revoca firmas mediante lectura y posterior INSERT, sin exclusión por documento/slot. [models.py:398](D:/Escritorio/Bitacora_HES/backend/models.py:398) define un índice **no único** por paciente/formato/slot/estado. La unicidad de `clinical_sync_operation_id` sólo evita duplicar la misma operación.

**Reproducción ejecutada:** dos POST concurrentes al endpoint real `firmar-biometrico`, mismo médico/paciente/formato/slot, challenges válidos diferentes y `Idempotency-Key` diferentes. Una barrera antes de `mark_local_applied` hizo que ambas consultas de firmas previas ocurrieran antes de los commits. Resultado: **[200, 200], dos filas ACTIVA, ambas slot 1**.

Se usaron PostgreSQL y ECDSA reales. La lectura del documento ERP y entrega externa fueron sintéticas. La barrera sólo fuerza una planificación concurrente posible; no elimina controles. La prueba de 50 intenciones con una clave igual no verifica este caso.

### AF-06 — BLOCKER — Vertical HTTP 200 vacío provoca SQL de firma y SYNCED

**Original afectado:** P0-08.

[vertical_signer.py:428](D:/Escritorio/Bitacora_HES/backend/vertical_signer.py:428) acepta éxito si no encuentra `d.Errors`. La respuesta `{}` satisface esa condición. Acto seguido escribe `SignedBy`, `MR_ST='SG'` y, cuando existe la columna, el literal `FIRMADO_BIOMETRICAMENTE`; confirma SQL y retorna True.

**Reproducción ejecutada:** dispatcher y adaptador Vertical originales, intención PostgreSQL durable real, conexiones SQL sintéticas y respuesta HTTP `200 / {}`. Resultado:

```text
state=SYNCED
sql_updates=1
marker_written=true
```

No se invocó Vertical real. El fallo está en la interpretación de respuesta del adaptador, antes de cualquier incertidumbre del esquema STAGING. `ensure_external_success` recibe True y ya no puede advertir que nunca hubo confirmación explícita de firma.

### AF-07 — HIGH — El frontend anuncia guardado SQL Server tras 202 pendiente

**Original afectado:** P0-08.

[PatientDashboard.jsx:3480](D:/Escritorio/Bitacora_HES/frontend/src/pages/PatientDashboard.jsx:3480), handler `handleSaveModal15EV`, considera éxito `!res.data?.error`. El cuerpo 202 de [main.py:788](D:/Escritorio/Bitacora_HES/backend/main.py:788) incluye `success:false` y estado pendiente, pero no `error`; Axios lo resuelve normalmente.

**Reproducción ejecutada:** extracción y ejecución del handler JavaScript original en VM, con API simulada devolviendo `202`, `success:false`, `state:'RETRYABLE_ERROR'`. El handler cerró su camino como éxito y emitió exactamente:

> ¡Formato 15 (Egreso Voluntario) guardado exitosamente en SQL Server y expediente clínico!

La API externa fue el único dato inyectado; se ejercitó la condición y alerta reales. El tratamiento correcto de 202 en algunos flujos de medicación/dieta no cubre todos los consentimientos.

### AF-08 — HIGH — Reutilizar clave idempotente con otra solicitud devuelve éxito ajeno

**Originales afectados:** P0-08, P1-04.

[clinical_sync.py:116](D:/Escritorio/Bitacora_HES/backend/clinical_sync.py:116) construye la clave suministrada como `operation_type:clave`; [clinical_sync.py:149](D:/Escritorio/Bitacora_HES/backend/clinical_sync.py:149) devuelve la fila existente sin cotejar paciente, agregado ni payload.

**Reproducción PostgreSQL ejecutada:** sincronizar intención A y después crear intención B, con otro paciente y otro payload, conservando tipo y clave. Resultado: `created=false`, paciente retornado A aunque se solicitó B; `_existing_sync_response` emitió **HTTP 200 / success:true**. B no fue aplicado.

Se probaron funciones reales de intención, transición y respuesta; sólo el efecto externo inicial fue un callback sintético. La unicidad de la clave funciona, pero no impide confirmar falsamente una solicitud distinta.

### AF-09 — HIGH — GET sigue creando pacientes y escribiendo evidencia PDF/QR

**Original afectado:** P1-11.

[main.py:1827](D:/Escritorio/Bitacora_HES/backend/main.py:1827) declara `allow_create`, pero no lo utiliza para impedir INSERT/UPDATE/commit. [main.py:7282](D:/Escritorio/Bitacora_HES/backend/main.py:7282) lo invoca desde GET; el dashboard incluso pasa `allow_create=False`, sin que esa bandera bloquee el efecto.

**Reproducción HTTP/PostgreSQL ejecutada:** GET `/api/ehr/paciente/99991/firmas`, con un registro ERP sintético que aún no existía localmente. Respuesta 200; conteo PostgreSQL de pacientes **1 → 2**. No se simuló la persistencia.

Además, GET de PDFs llama generadores con rutas de salida y [main.py:4928](D:/Escritorio/Bitacora_HES/backend/main.py:4928) registra/actualiza `DocumentoVerificacionQR`, hash, ruta y fecha, con commit propio. Por ejemplo, [main.py:9701](D:/Escritorio/Bitacora_HES/backend/main.py:9701). Esto contradice la afirmación “GET no almacena PDFs ni produce mutaciones”. La prueba estructural no recorre esos helpers.

### AF-10 — HIGH — Cliente TSA rechaza respuestas válidas; estado resumido oculta TSA pendiente

**Original afectado:** P1-02.

[tsa_client.py:191](D:/Escritorio/Bitacora_HES/backend/tsa_client.py:191) ejecuta `int(tsr['status']['status'].native)`. Para la respuesta válida construida con asn1crypto, `native` es el string **`'granted'`**, no 0.

**Reproducción ejecutada:** certificado raíz/firmante TSA sintéticos, CMS firmado real, nonce coincidente y trust root de prueba. El mismo token validó directamente con `verify_timestamp`, pero envuelto en `TimeStampResp` y entregado al cliente real mediante transporte HTTP sintético produjo:

```text
direct_valid_cms=True
native_pki_status='granted'
client_status='TSA_FALLIDO'
client_error="invalid literal for int() with base 10: 'granted'"
```

No se sustituyó el verificador criptográfico. Es un defecto local del cliente, no una TSA externa pendiente de configurar.

El estado detallado sí conserva `sellado_tiempo.verificado=false` al quedar pendiente. Sin embargo, [clinical_signing.py:279](D:/Escritorio/Bitacora_HES/backend/clinical_signing.py:279) calcula `complete` sin TSA, y el endpoint resumido retorna `VERIFICACIÓN_CRIPTOGRÁFICA_COMPLETA` sin incluir el estado TSA. La sonda de estado empleó una firma `TSA_PENDIENTE` y recibió `valido=true`, sin campo TSA. La integridad ECDSA puede ser válida sin TSA; lo que falta es que esa distinción llegue inequívocamente a todos los consumidores.

La validación existente de CMS/cadena/EKU/imprint/nonce aporta evidencia útil. Su revocación permanece `soft-fail` sin fetching, límite documentado previamente; no se presenta como verificación online completa de revocación ni como un nuevo requisito de esta auditoría.

### AF-11 — HIGH — Auditoría protegida pero no completa ni siempre confirmada

**Original afectado:** P1-03.

[main.py:3436](D:/Escritorio/Bitacora_HES/backend/main.py:3436) modifica privilegios y confirma sin insertar evento de auditoría. **Reproducción HTTP ejecutada:** cambio `limpieza → enfermeria` por admin, respuesta 200; conteo de `auditoria_logs` **0 → 0**.

Existe además una regresión transaccional: [main.py:1724](D:/Escritorio/Bitacora_HES/backend/main.py:1724) confirma el ingreso del paciente y posteriormente llama `log_auditoria`. El helper [main.py:732](D:/Escritorio/Bitacora_HES/backend/main.py:732) sólo hace flush; no hay otro commit antes del retorno. El cierre de sesión de DB revierte ese evento. El mismo patrón aparece en actualización de cama, [main.py:4411](D:/Escritorio/Bitacora_HES/backend/main.py:4411). Este segundo caso se comprobó por flujo transaccional estático, no se cuenta como otra reproducción HTTP.

El trigger append-only sí bloquea UPDATE/DELETE de eventos existentes, y la impersonación guarda motivo y actor real/efectivo en su inicio/fin. Estos controles no crean los eventos omitidos ni hacen durable un flush posterior al commit clínico. Los logs HTTP registran ruta/status, pero no sustituyen un evento transaccional con atribución y detalle del cambio de privilegio.

## Verificación específica de biometría y criptografía

| Control pedido | Resultado directo |
|---|---|
| No persistir RAW nuevo | Confirmado en caminos de alta/enrolamiento y prueba de contenido persistido. RAW temporal existe en navegador y extracción loopback. No se afirma que se haya purgado RAW histórico. |
| Mismatch nunca reenrola | Confirmado para verificación/firma; rechazado sin cambio de plantilla. |
| Matcher caído falla cerrado | Confirmado ante error de transporte, timeout, HTTP/JSON inválido y no-match. |
| Firmante ID obligatorio | Confirmado en esquemas y helper; episodio y rol persistido se cotejan. |
| Challenge obligatorio/contextual/120 segundos | Confirmado por código y negativos de la suite. La frescura del material de captura sigue abierta en AF-02. |
| Consumo concurrente único | Confirmado: 20 consumidores, un ganador en PostgreSQL real. |
| Reenrolamiento bloquea FEA anterior | Confirmado, pero el desbloqueo por el mismo operador permite AF-03. |
| LEGACY_RAW bloqueado | Confirmado; requiere flujo explícito de reenrolamiento. |
| Bytes CANONICAL_V2 y contenido no truncado | Confirmado en serialización y ECDSA; el loader se ejecuta en backend. No equivale a prueba de paridad completa con cada esquema ERP real. |
| Snapshot inmutable | No confirmado: UPDATE sintético persistido en DB; AF-04. |
| Key-id exacta/historia/rotación/descifrado | Confirmados los mecanismos criptográficos y las restricciones de historial; identidad del titular reabierta por AF-03. |
| Marcador Vertical no implica ECDSA válida | Confirmado en el verificador. El adaptador aún fabrica éxito operativo ante respuesta vacía: AF-06. |
| PDF declarado protegido sólo con hash ligado | Confirmado en el helper de verificación. Los PDFs actuales son secundarios; no se certifica integridad de su archivo generado. |
| TSA CMS/RFC3161 end-to-end | Verificador de token funciona; cliente de respuesta falla con granted: AF-10. |
| TSA_PENDIENTE no confundido con completo | Correcto en detalle TSA, incompleto en respuesta resumida: AF-10. |

## Inventario de mutaciones SQL Server y límites de consistencia

Se revisaron llamadas SQL directas, strings SQL, funciones decoradas, dispatcher, rutas y helpers; no se tomó el inventario de decoradores como prueba suficiente por sí solo.

- Los mutadores de notas, signos, alergias, consentimientos y contactos de `kh_database.py` están referenciados por `_KH_MUTATORS`/`MUTATOR_STRATEGIES` y por las rutas durables. El helper no decorado `_sync_allergies_to_notes` se ejecuta dentro de mutadores de alergias cubiertos; no se identificó como ruta externa independiente.
- Medicación/dieta usan GUID determinista; alta/reingreso, formatos universales y firma Vertical tienen dispatcher explícito. El INSERT universal sin GUID descubrible se bloquea antes de escribir. Los cuatro endpoints de decisión funcional permanecen 403.
- No se encontró otro write SQL Server clínico independiente del conjunto revisado que justificara inventar un hallazgo adicional de “mutador fuera del registro”. Esto no certifica la semántica de todos los UPDATE/INSERT contra un esquema SQL Server real ausente.
- La pertenencia de `VERTICAL_SIGN` al registro **no hace seguro su resultado**: AF-06 ejercita el adaptador real y lo lleva a SYNCED sin confirmación.
- Los tests que sustituyen el adaptador por un set de `operation_id` prueban la máquina de estados, no la idempotencia del SQL real. No hay demostración end-to-end SQL Server STAGING. La validación de ese esquema sigue siendo gate externo, independiente de AF-06/07/08.
- Un GET sí tiene efectos PostgreSQL y PDF/QR, aunque no se haya encontrado un write SQL Server directo en su propio cuerpo; AF-09.

## APP_ENV=production y gates externos

Se revisaron [app_config.py](D:/Escritorio/Bitacora_HES/backend/app_config.py), [seed.py](D:/Escritorio/Bitacora_HES/backend/seed.py), [bootstrap_admin.py](D:/Escritorio/Bitacora_HES/backend/bootstrap_admin.py), [hes-api.service](D:/Escritorio/Bitacora_HES/deploy/systemd/hes-api.service) y [hes.conf.example](D:/Escritorio/Bitacora_HES/deploy/nginx/hes.conf.example).

| Condición | Evidencia/límite |
|---|---|
| Sin seed ni demo automáticos | Seed rechaza entorno distinto de development; bootstrap es explícito, con tabla de usuarios vacía y contraseña aleatoria/interactiva. No se ejecutó bootstrap en producción. |
| Sin reload | Servicio systemd usa dos workers, bind 127.0.0.1 y Restart=on-failure. El BAT con reload está limitado a desarrollo. |
| Secrets obligatorios | Validación previa a construir engine: SECRET_KEY y secretos FEA/attestation, longitud y placeholders. No se verificaron valores del host ni su entropía/custodia reales. |
| CORS/hosts/TLS | Orígenes HTTPS y hosts explícitos; proxy HTTPS obligatorio; plantilla Nginx TLS y HSTS. Falta instalación real. No hay promesa de TLS por ejecutar sólo el BAT. |
| Almacenamiento privado | Uploads fuera de webroot; rutas protegidas. Los PDFs generados en carpetas históricas tampoco tienen montaje static público. |
| Health/readiness | Liveness y readiness presentes. PostgreSQL y disco determinan readiness; SQL Server/biometría/TSA se reportan aparte. Readiness=200 no certifica que esos tres servicios estén operativos. |
| Fallo de dependencia | Matcher caído bloquea; writes externos quedan pendientes salvo el éxito falso ya reproducido; TSA pendiente/fallido no destruye ECDSA. No existe un bloqueo universal de go-live condicionado a un acta de gates externos. |
| Continuidad | Runbook, script de cifrado/copia y restore drill sintético disponibles; programación y off-host no verificados en infraestructura real. |

La falta de SQL Server TEST/STAGING, lector físico probado, TLS instalado, copia off-host programada, decisión funcional de roles o validación jurídica **no se registra como bug del software**. Se mantienen como gates externos. El informe tampoco afirma que estén cerrados o que una readiness saludable los sustituya.

## Calidad de pruebas: falsos positivos relevantes

| Evidencia anterior | Qué sí prueba | Qué no alcanzaba y se reprodujo ahora |
|---|---|---|
| Probes P0 y matriz de rutas | Middleware real, JWT, roles locales, ausencia de auth y archivos no públicos. | No cubre la información real del portal público ni la cadena clínica en `/firmas`: AF-01. |
| Mismatch/caída de matcher | Ejecuta el verificador real ante respuestas adversas; es una prueba negativa útil. | No acredita frescura del RAW que el servicio vuelve a atestar: AF-02. |
| Bloqueo 423 y completar actualización FEA | El flag detiene la firma; la función de rotación cambia llave. | La prueba de desbloqueo sustituye `verificar_huella_medico` por un médico fijo y no encadena reenrolamiento por el mismo operador: AF-03. |
| Mutar byte/slot/versión de la fila firmada | Detecta corrupción de los bytes y discordancia interna contra su propio snapshot. | No valida selección de la fila frente al slot solicitado ni inmutabilidad en DB: AF-04. |
| 50 intenciones concurrentes | Restricción única de una misma idempotency key. | No cubre firma del mismo documento con claves/challenges distintos, ni una clave con payload diferente: AF-05/08. |
| `test_unexpected_vertical_response_never_reports_success` | El coordinador rechaza un dict sin confirmación entregado directamente por el callback. | No atraviesa `sign_in_vertical_api`, que transforma `{}` HTTP en True: AF-06. |
| Retry sin duplicado por adaptador simulado | Reintentos/estados del coordinador PostgreSQL. | El set del fake implementa precisamente la propiedad de idempotencia que se quiere comprobar; no prueba el SQL de cada adaptador. |
| Inyección de errores del backend | Cuerpos/estados pendientes de la API. | No prueba la interpretación por cada handler React; AF-07 procesa 202 como éxito. |
| `test_all_get_endpoints_are_free_of_session_writes` | Búsqueda AST de nombres de llamadas directas y SQL literal. | No sigue helpers ni escrituras de archivos; no ve `get_or_create`/registro QR: AF-09. |
| CMS válido y reintento TSA | Verificación de un token aislado; preservación de ECDSA al mockear `get_timestamp`. | Omite la respuesta TimeStampResp válida y el parseo de granted: AF-10. |
| UPDATE/DELETE de auditoría rechazados | El trigger protege eventos ya persistidos. | No verifica que cada mutación produzca evento ni que éste tenga commit: AF-11. |

Los mocks no invalidan toda la suite: los controles de PostgreSQL, challenge, cryptography, FK, historial y varios rechazos HTTP son reales. Lo inválido es extrapolar sus resultados a los caminos anteriores que no ejercitan.

## Comprobaciones ejecutadas en esta auditoría

| Comprobación | Resultado observado |
|---|---|
| `backend/venv/Scripts/python.exe backend/scripts/run_local_postgres_tests.py` | **139 passed, 172 warnings, 10 subtests passed, 67.29 s**. PostgreSQL TEST real; migraciones Alembic. |
| `backend/venv/Scripts/python.exe backend/scripts/run_local_alembic_check.py` | Upgrade desde esquema vacío y **No new upgrade operations detected**. |
| Frontend `npm run lint:runtime` | Exit 0. |
| Frontend `npm run build` | Exit 0; 721 módulos. |
| Móvil `tsc --noEmit` local | Exit 0. |
| `node --check biometric-service/server.js` | Exit 0. |
| Parseo AST Python, excluyendo venv | **66 archivos**, sin errores de sintaxis. No se presenta como prueba de comportamiento. |
| Inventario de rutas, calculado sin reescribir el archivo existente | **231**, 30 públicas, 60 autenticadas, 141 con rol; cero writes sin política/bloqueo conocido. |
| Scanner de secretos existente | **253 archivos**, cero patrones de alta confianza. No demuestra ausencia universal de secretos ni inspecciona `.env` ignorado. |
| `npm audit --omit=dev`, frontend | 0 vulnerabilidades. |
| `npm audit --omit=dev`, biometría | 0 vulnerabilidades. |
| `npm audit --omit=dev`, móvil | 14 moderadas; 0 altas/críticas. |
| `pip-audit -r backend/requirements.txt` | Exit 1: reporta dos entradas de vulnerabilidad en un paquete `ecdsa`; no es un audit limpio. |
| Sondas independientes | Reproducciones descritas AF-01 a AF-11; los límites de simulación y verificaciones estáticas están identificados en cada una. |
| Restore/lector/SQL Server/TLS productivos | No ejecutados. No se reutilizan los tiempos del informe anterior como medición nueva. |

El advisory de `python-ecdsa` afecta firma/generación/ECDH y no su verificación; el proveedor no anuncia parche. La ruta FEA de este árbol usa `cryptography` y los JWT configurados para las pruebas usan HS256. Por ello se conserva la mitigación documentada, sin declarar que desapareció el advisory. Fuente primaria consultada: [GHSA-wj6h-64fc-37mp](https://github.com/tlsfuzzer/python-ecdsa/security/advisories/GHSA-wj6h-64fc-37mp). Los requirements Python mantienen rangos y paquetes sin fijar; los resultados corresponden al entorno/resolución auditados, no a todas las instalaciones futuras.

## Identificación del código auditado

SHA-256 de archivos clave; permiten distinguir este árbol modificado del HEAD de referencia:

| Archivo | SHA-256 |
|---|---|
| backend/main.py | `f3dd5c349a5203a06743d02d51daa06a4997abf0c7761da12d979e66d65cace5` |
| backend/clinical_signing.py | `ee2ee3493a084935c183197eda1bf28281309fcd9d08bc670f5b1f4c56a30665` |
| backend/crypto_fea.py | `dcef70d7953f842679f2e34749883ce52df4c974af7500bf75c81e93b152fb37` |
| backend/tsa_client.py | `5b291db87624c9b38c0de40f8ea16f0d280bd1fc6a496bc6963a113bd531c68f` |
| backend/clinical_sync.py | `4e24937ea1645376c7963fe901a043cef5d09521eb3231b9f138a912f2abf39a` |
| backend/vertical_signer.py | `53f51faf856ccf619cc81c471954083e687e1b18cd96d457c55440b69091eddf` |
| biometric-service/server.js | `9fbce2965b1d4be9f45f7163221caa5431a1e281f4d87236aaff861aae11f192` |
| frontend/src/pages/PatientDashboard.jsx | `5fe4d9f0b905d5d4f24499706c2c50a4c0c036e6dae9a1a932ab638fb1924772` |

## A) PILOTO / PREPRODUCCIÓN CON DATOS SINTÉTICOS

**NO LISTO.**

AF-01 a AF-11 invalidan cierres de seguridad, firma y consistencia aun en un laboratorio sin dependencias productivas. Los datos sintéticos permiten reproducirlos de forma segura, pero no convierten el resultado en una plataforma lista para piloto. La ausencia de SQL Server STAGING o lector físico, por sí sola, no motivó este dictamen.

## B) GO-LIVE CON DATOS REALES

**NO LISTO.** Gates restantes:

1. **GATE_SOFTWARE_CONFIDENCIALIDAD:** cerrar AF-01 y verificar lecturas clínicas/portal público con la política aprobada.
2. **GATE_SOFTWARE_IDENTIDAD_BIOMETRICA_FEA:** cerrar AF-02 y AF-03, demostrando frescura de captura y control del titular en reenrolamiento/rotación.
3. **GATE_SOFTWARE_EVIDENCIA_FIRMA:** cerrar AF-04 y AF-05; documento solicitado, conservación de snapshot y concurrencia de firmas.
4. **GATE_SOFTWARE_CONSISTENCIA:** cerrar AF-06, AF-07 y AF-08; respuesta Vertical, presentación 202 e identidad de solicitud idempotente.
5. **GATE_SOFTWARE_LECTURAS_Y_AUDITORIA:** cerrar AF-09 y AF-11; GET sin mutación y eventos transaccionales completos.
6. **GATE_SOFTWARE_TSA:** cerrar AF-10; respuesta RFC3161 válida end-to-end y estado pendiente inequívoco.
7. **GATE_REGRESION_INDEPENDIENTE:** ejecutar negativos que atraviesen esos caminos, además de la suite existente.
8. **GATE_EXTERNO_SQLSERVER_STAGING:** smoke de mutadores, idempotencia, fallos y reconciliación contra instancia dedicada; nunca KH_HE productivo para esta validación.
9. **GATE_EXTERNO_LECTOR:** lector DigitalPersona/SDK y ciclo de captura real en el puesto clínico con la configuración final.
10. **GATE_EXTERNO_ROLES:** aprobación institucional de alcance horizontal y permisos; las cuatro rutas indecisas deben continuar bloqueadas hasta su decisión.
11. **GATE_EXTERNO_DESPLIEGUE:** migración del entorno, TLS/proxy, hosts/origins, secretos, almacenamiento, supervisor y trust store TSA instalados y verificados.
12. **GATE_EXTERNO_CONTINUIDAD:** backup cifrado programado, custodia, copia fuera del host y restore/procedimiento operativo acreditados.
13. **GATE_EXTERNO_JURIDICO_OPERATIVO:** validación NOM/FEA/privacidad y procedimientos hospitalarios correspondientes.

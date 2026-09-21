---
aliases: [Biometría, DigitalPersona, Huellas]
tags: [hes/seguridad, hes/frontend, hes/backend]
tipo: modulo
modulo: biometria
codigo_fuente:
  - frontend/src/hooks/useDigitalPersona.js
  - frontend/src/hooks/useFingerprint.js
  - frontend/src/features/biometrics/BiometricSignModal.jsx
  - frontend/src/features/biometrics/BiometricPatientSignModal.jsx
  - frontend/src/utils/medicalBiometricEnrollment.js
  - frontend/src/mockWebSdk.js
actualizado: 2026-09-21
relacionados:
  - "[[Frontend]]"
  - "[[Backend]]"
  - "[[Seguridad-FEA]]"
  - "[[Guia-Desarrollo-IA]]"
---

# Biometria-DigitalPersona

AF-02 implementa adquisición directa con DigitalPersona 4500 y DPUruNet real.
La prueba física de desarrollo pasó: captura, ANSI FMD, attestation, comparación
SDK consigo misma y reapertura del lector tras cleanup. Detalle en
`CIERRE_AF02_ADQUISICION_CONFIABLE.md`.

## Arquitectura

- Servidor central hospital: FastAPI, PostgreSQL, frontend e integraciones por HTTPS/LAN.
- Cada estación médica Windows: navegador → `127.0.0.1:8082` HES Biometric Agent →
  bridge .NET Framework x64 → SDK DigitalPersona → USB 4500.
- La exclusividad del lector es local a cada estación: una captura en una computadora
  no bloquea los lectores de las otras estaciones. El agente elimina el estado
  `busy` al vencer el ticket aunque el bridge nativo no confirme su salida, evitando
  que una captura interrumpida deje esa computadora bloqueada indefinidamente.
- El servidor no abre USB ni llama a su propio localhost para comparar huellas.
- La PC actual sólo desarrolla/prueba; no es el servidor de producción.
- Instalador por estación/usuario: `biometric-service/install-client.ps1`.
  SDK, rutas, secreto DPAPI, inicio al logon y origen HTTPS en `biometric-service/README.md`.
- Kit offline listo para copiar: `Instalacion_Enfermeria/LEEME_PRIMERO.md`.
  Incluye Node firmado, dependencias, bridge compilado y RTE x64 existente.
  Destino: `https://192.168.254.249:8000`; requiere certificado institucional con
  SAN IP confiado en los clientes. El instalador no configura producción.
  SHA-256, diagnóstico y registro de aceptación para 50 estaciones acompañan el kit.
- El supervisor por usuario evita duplicados, reinicia el proceso tras una caída
  y permite parada explícita. El agente serializa probes de varias pestañas y
  espera a que termine el probe antes de abrir captura; rechaza origen/Host ajenos.
- FastAPI publica una CSP con `connect-src` limitado al propio origen y a
  `http://127.0.0.1:8082`/`http://localhost:8082`. La SPA marca cada `fetch` con
  `targetAddressSpace: loopback`; Chrome pide al usuario permiso para acceder a
  dispositivos locales cuando corresponde. En una intranet HTTP sin contexto
  seguro no se inicia adquisición. Sin el permiso requerido el navegador bloquea antes de llegar
  al agente, aunque `/health` y `/devices` respondan desde Windows.

## Flujo V2

1. Backend persiste hash de challenge contextual de 120 s y entrega
   `capture_authorization` firmada: acción, sesión, identidad, paciente/documento,
   tiempos y trabajo de comparación cifrado AES-256-GCM.
2. SPA envía exclusivamente esa autorización a `/begin-capture`.
3. Agente valida autorización/TTL, crea acquisition_id aleatorio, abre el lector
   exclusivo e inicia Reader.Capture después del challenge.
4. DPUruNet recibe el evento físico, genera ANSI 378 mediante
   FeatureExtraction.CreateFmdFromFid, limpia buffers y libera el dispositivo.
   RAW no llega al navegador, HTTP, PostgreSQL, logs ni archivos.
5. El agente compara ANSI con Importer.ImportFmd + Comparison.Compare cuando
   la acción requiere verificar identidad. Las referencias cifradas sólo las
   descifra el agente; el backend revalida su hash contra la plantilla vigente.
6. HMAC V2 compromete autorización contextual, acquisition_id, inicio/fin,
   dispositivo, hash FMD y resultado de comparación. `/capture-result` entrega
   el FMD atestado una sola vez. El backend valida HMAC/contexto/tiempos y consume
   challenge/adquisición de forma atómica con unicidad PostgreSQL.
7. Cancelar/cerrar/reintentar purga estado y llama `/cancel-capture`. Cada
   reintento usa challenge nuevo. Un solo controlador SPA y lector exclusivo.

## Experiencia de captura

- Abrir un modal de firma o enrolamiento no activa el lector. El usuario inicia la
  lectura con “Leer huella”, de modo que la acción sea predecible y deliberada.
- Las acciones están separadas por identidad: “Paciente / familiar” abre únicamente
  firmantes del episodio, mientras “Firmar como médico” abre exclusivamente la
  verificación del perfil médico autenticado. El botón médico nunca redirige al flujo
  del paciente; los requisitos pendientes se validan sin mezclar identidades.
- La pantalla presenta un paso a la vez y oculta challenge, FMD, HMAC, PTCN y códigos
  criptográficos del flujo cotidiano. Esos valores se conservan en payloads y auditoría.
- Los rechazos de identidad en operaciones protegidas se muestran dentro del modal y
  permiten reintentar sin cerrar la sesión. El rechazo del login conserva su semántica
  propia y no concede acceso.
- Al actualizar una huella se solicita un motivo visible; para médicos se conserva la
  ceremonia de segundo actor requerida para activar o actualizar FEA.

`/extract-fmd` y `/acquisitions/start` están retirados (410). No existe endpoint
que acepte RAW/FMD del cliente para atestarlo como una captura nueva.
SDK ausente, timeout, lector desconectado/cambiado, extracción o comparación
fallida no producen attestation. Respuestas 408/503 incluyen código recuperable;
reuso/contexto de adquisición ajeno devuelve 409.

## Confianza y almacenamiento

La confianza incluye estación, SDK/agente y secreto HMAC; no es attestation
hardware contra un administrador local malicioso. Aprovisionar secreto fuera de
la SPA/Git y sincronizar relojes con el servidor. CORS autoriza sólo el origen
configurado; loopback nunca se publica a LAN.

- SIN_BIOMETRIA: sin plantilla.
- LEGACY_RAW: preservado, bloqueado; exige reenrolamiento controlado.
- FMD_VALIDO: sólo envelope canónico ANSI 378 versión 1 persiste en PostgreSQL.
  El protocolo de transporte/attestation es V2; no cambia el formato almacenado.
- Matching nunca sustituye la plantilla enrolada; umbral SDK conservado: 10000.
- NUNCA registrar samples, FMD, autorización, tokens ni binarios.

## Componentes

`native/CaptureBridge.cs` controla hardware; `native-device.js` usa pipes privados;
`server.js` administra adquisición y firma; `capture-protocol.js` aplica HMAC/AES;
`trustedCapture.js` y `useDigitalPersona.js` coordinan SPA y purga;
`backend/biometric_security.py` valida y consume evidencia.
Adaptadores TEST sólo por inyección de código en pruebas, sin bypass HTTP.

## Firma contextual e individual (2026-09-19)

- Cada médico conserva su perfil, FMD, `medico_id` y llave propia. La identidad
  solicitada debe coincidir con la sesión médica; se compara contra esa plantilla.
  El enrolamiento sigue siendo controlado por los roles autorizados, no un alta
  de identidad sin supervisión. Reenrolar no elimina llaves históricas.
- El médico puede operar el lector para un paciente/responsable: `subject_ref`
  identifica al operador; `expected_identity_ref=firmante:<id>` al titular que
  pone el dedo. No sustituir esta última por la identidad del operador.
- `FIRMA_MEDICA` y `FIRMA_FIRMANTE` comprometen también `document_digest` del
  contenido autoritativo en la autorización HMAC. Un cambio durante la captura
  exige leer nuevamente el documento y obtener otro challenge (TTL 120 s).
- SPA procesa sólo capturas de la acción, paciente, formato, ranura y firmante
  seleccionados. Cambiar/cerrar cancela captura; respuestas tardías no actualizan
  otro modal. El rol persistido no cambia al seleccionar tutor, familiar o testigo.
- Pruebas nuevas: `backend/tests/test_signature_workflow.py` y
  `frontend/test/biometricSigners.test.js`. No reemplazan pruebas con personas,
  lector físico y estación hospitalaria; ver informe de corrección en la raíz.

## Enrolamiento médico desde administración (2026-09-21)

- El perfil del médico se crea primero sin biometría. El enrolamiento se inicia
  después desde el directorio, cuando ya existe un `medico_id` al cual ligar el
  challenge `ENROLAMIENTO_MEDICO`.
- Una plantilla `LEGACY_RAW` no se borra ni se sobrescribe por la ruta antigua:
  exige `REENROLAMIENTO_MEDICO`, motivo, challenge y auditoría.
- Después del reenrolamiento la interfaz identifica `requiere_actualizacion_fea`
  y ofrece el Bloque B con `ACTUALIZACION_FEA`. Debe aprobarlo otro actor
  Admin/RH/Sistemas; hasta terminarlo, login biométrico y firma permanecen
  bloqueados. Las llaves y firmas históricas siguen intactas.
- La SPA sólo habilita el guardado cuando acción, `medico_id`, referencia de
  documento, challenge y sesión pertenecen al médico visible en el modal.
- Un mismatch de huella durante una operación clínica autenticada responde 403:
  se rechaza la firma y se muestra el error, pero el JWT válido y el trabajo de
  la pantalla permanecen. Sólo el mismatch de `LOGIN` responde 401.

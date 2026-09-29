---
aliases: [Frontend React, SPA HES]
tags: [hes/frontend, hes/arquitectura]
tipo: modulo
modulo: frontend
codigo_fuente:
  - frontend/src/main.jsx
  - frontend/src/App.jsx
  - frontend/src/context/AuthContext.jsx
  - frontend/src/hooks/useQueries.js
  - frontend/src/hooks/useDigitalPersona.js
  - frontend/src/features/ehr/modals/AllergiesModal.jsx
  - frontend/src/features/admin/AuditLogsTab.jsx
  - frontend/src/features/biometrics/BiometricSignModal.jsx
  - frontend/src/features/biometrics/BiometricBancoSangreSignModal.jsx
actualizado: 2026-09-29
relacionados:
  - "[[00_Inicio]]"
  - "[[Mapa_Proyecto]]"
  - "[[Arquitectura]]"
  - "[[Backend]]"
  - "[[API-Endpoints]]"
  - "[[Biometria-DigitalPersona]]"
  - "[[Pase_a_Produccion]]"
---

# Frontend

## Firmas del área

`FirmasArea.jsx` ofrece pendientes compartidos e historial con firmante y fecha.
`useAreaSignaturesQuery` pagina registros existentes y actualiza cada 20 segundos;
`useAreaSignatureDocumentQuery` verifica el documento exacto antes de mostrar la
acción de firma. La vista incluye resumen clínico, PDF oficial y firmas anteriores.
Un error de consulta no se presenta como bandeja vacía ni permite iniciar la firma.

`SpecialSignerBiometricSignModal` conserva dos entradas: desde EHR permite al
operador elegir personal autorizado; desde la bandeja fija `selfSignerId` a la
cuenta autenticada. El servidor comprueba esa misma restricción. Después de guardar
o recibir 409 se refrescan documento, firmas y bandeja. Una firma hecha por otro
usuario se muestra en el historial compartido, sin cerrar la sesión del médico.

El Frontend del proyecto es responsable de la interfaz gráfica hospitalaria, la interacción en tiempo real y la captura biométrica fluida.

El botón de expediente completo incorpora los pendientes de la cabecera
`X-HES-Signature-Report` a la misma bandeja de revisión de firmas, incluso cuando
el PDF se generó correctamente pero algún formato nunca se firmó. Cada
pendiente se identifica por código **y ranura** para que completar una evolución
no oculte las demás. Para la nota 24 el formulario de firma envía
`MRNum_24_HOJA_EVOL`, aunque la tarjeta siga mostrando el ordinal de evolución.

## Permisos por área y usuario

Ver [[Permisos-Acceso]]: catálogo compartido, selección explícita por usuario,
RH limitado a cinco áreas, formatos activos integrados al selector y validación
en API/SPA. El mínimo de contraseña es 8 caracteres con mayúscula, minúscula,
número y símbolo. Las cuentas existentes conservan sus datos.

## Tecnologías Principales
- **Framework:** React 18 (instalado React 19 en `package.json`, verificar compatibilidad).
- **Empaquetador:** Vite (con Rolldown engine).
- **Caché y Estado Asíncrono:** `@tanstack/react-query` (TanStack Query) con políticas *stale-while-revalidate* para transiciones instantáneas de pantalla (`useQueries.js`). Ver [[decisiones/ADR-0003-tanstack-query]].
- **Estado Global:** `AuthContext.jsx` con persistencia de sesión JWT, detección de rol y permisos por módulo.
- **Estilos y UI Kit:** Tailwind CSS con componentes atómicos (`Button.jsx` con estados de carga y `AlertBanner.jsx` para caídas de servicio).
- **Biometría:** `@digitalpersona/devices` (`useDigitalPersona.js`) comunicándose por loopback local con el lector USB. Ver [[Biometria-DigitalPersona]].

## Arquitectura por Features
- `src/features/ehr/modals/`: Subcomponentes modulares de expediente clínico (ej. `AllergiesModal.jsx`).
- `src/features/admin/`: Paneles administrativos de trazabilidad (`AuditLogsTab.jsx`) y gestión de usuarios (`UsersManagerTab.jsx`).
- `src/features/biometrics/`: Modales aislados de firma biométrica (`BiometricSignModal.jsx`).
- `src/pages/`: `PatientDashboard`, `CapturaEnfermeria`, `CamasDashboard`, `AgendaMedica`, `AdminDashboard`, `FirmaExpress`, `VerificarDocumento`, `LoginDual`.
- `src/hooks/`: `useQueries`, `useApiError`, `useDigitalPersona`, `useFingerprint`, `useAutoLogout`, `useEscapeKey`.

## Acceso a expedientes y relación con camas

La ruta `/ehr` funciona como selector de pacientes y nunca abre un expediente
implícito. Su vista inicial usa el censo de `/camas` y sólo muestra pacientes
ocupando camas físicas; las camas virtuales quedan fuera del acceso rápido.
El buscador de la pantalla y el atajo global `Ctrl/Cmd+K` activan una búsqueda
explícita por nombre, folio o CURP y sí permiten localizar pacientes de cama
virtual o históricos. `PatientDirectory`, `PatientSearchModal` y la agenda
comparten el mismo contrato de búsqueda, por lo que los accesos desde camas,
agenda y expediente llegan siempre a `/ehr/{pt_num}`.

La acción superior de nueva evolución usa `patient.evolution_context`, calculado
por KH_HE. Si el episodio `PC` es `ER`, abre `HE-DIRMED-SINPRO-PLT-87/01`
(urgencias); si es `IP`, abre `HE-DIRMED-CONSUL-PLT-24` (hospitalización).
Las habitaciones virtuales y el historial de `MR_24_HOJA_EVOL` sólo sirven como
respaldo cuando KH_HE no informa `PCType`.

## Expediente: navegación y detalle bajo demanda

`PatientRecordChrome.jsx` y `styles/patient-record.css` organizan el expediente
con navegación lateral, una cabecera compacta y un catálogo en lista. En móvil,
la navegación se abre desde el botón de la sección activa. Se conservan los
formularios, acciones, permisos y flujos de firma existentes.
Los bordes exteriores usan `--record-outline` y los separadores internos
`--record-line`, con contraste mayor para distinguir los bloques sin añadir
recuadros a cada campo ni aumentar el grosor de las líneas.

Datos ampliados, signos vitales y solicitudes/cargos se muestran en bloques
plegables: sólo uno permanece abierto a la vez. Los signos vitales aparecen
abiertos al entrar al expediente, volver a Historial o al catálogo. Seleccionar
cualquier formato (también desde historial o revisión de firmas), o abrir un
editor para crear o modificar una nota, consentimiento o formato universal,
cierra los bloques automáticamente, incluidos los accesos directos de la cabecera.
Después pueden volver a abrirse manualmente. Cambiar de paciente reinicia la vista
en Historial con los signos abiertos. El plegado no desmonta el área del formato
ni borra sus campos. Las alergias se
mantienen completas y visibles; las lecturas que ya activaban una alerta se
resumen junto a la fecha de toma aun con los signos plegados. `vitalAlerts.js`
comparte los mismos umbrales anteriores entre resumen y detalle, sin cambiar
criterios clínicos. Las acciones de nueva toma y gestión de alergias siguen
inaccesibles para episodios de alta.

`ClinicalFormatHeader.jsx` separa las acciones de editar, PDF y nuevo formato
de las opciones de firma en las 16 cabeceras específicas de consentimientos y
formatos. El estado de cada firmante permanece visible; el botón «Firmas»
despliega las acciones de paciente, médico y áreas responsables. La auditoría
conserva su acceso desde el estado de firma médica, presentado como botón con
borde, fondo verde suave y estados visibles de hover y foco. Las opciones se pliegan al
cambiar de formato y no se ofrece un desplegable vacío si no hay acciones.

`ClinicalFormatEditor.jsx` unifica la presentación de los 19 editores de notas,
consentimientos, egresos y formatos universales. Mantiene visibles el nombre del
paciente, la cabecera y las acciones de guardar/cancelar mientras se desplazan
los campos. Los controles, validaciones, avisos de integridad, permisos y
funciones de guardado permanecen en `PatientDashboard`. El diálogo contiene la
navegación por teclado, cierra con Escape y devuelve el foco al botón de origen.
`styles/clinical-formats.css` limita estos estilos al expediente y sus editores:
etiquetas legibles, secciones con separadores y un solo acento para la acción
principal, con adaptación a pantallas pequeñas.

## Lenguaje y experiencia de uso

- La interfaz operativa usa instrucciones breves y palabras cotidianas: “Firmar ahora”,
  “Leer huella”,
  “Registrar huella”, “Firma guardada” y “Intentar de nuevo”. Los nombres de protocolos,
  algoritmos, tablas y sellos no se muestran en el flujo normal; permanecen disponibles
  en auditoría y trazabilidad.
- `utils/userMessages.js` traduce fallos de lector, sesión y challenge a acciones que el
  personal puede realizar sin exponer detalles internos.
- En la firma de documentos, seleccionar a la persona y pulsar “Firmar ahora” inicia
  directamente la lectura de huella; ya no se exige un segundo clic en “Leer huella”.
  El botón secundario queda disponible para reintentar. El enrolamiento de una huella
  sigue separado y requiere su acción explícita.
- La firma médica de la nota 87/01 abre el modal con su código de formato
  explícito; si falta el código no se abre una consulta deshabilitada que parezca
  estar cargando. La consulta de firmas termina en 15 s si el servidor no
  responde y deja disponible un reintento sin repetir una huella.
- Al registrar por primera vez la huella de un médico, la interfaz informa que
  éste debe existir previamente en Vertical. La preparación del código interno
  es automática y no agrega campos técnicos al flujo de enrolamiento.
- Un tutor, responsable o familiar registrado aparece también entre los posibles
  testigos cuando el paciente firma por sí mismo. La selección sólo cambia su función
  en ese documento; no altera su perfil ni permite que la misma persona cubra dos lugares.
  El modal consulta `testigos_esperados` para mostrar los espacios disponibles y
  `testigos_requeridos` para indicar el mínimo de cierre. En formatos con dos
  espacios, el paciente que autoriza necesita al menos un testigo; si autoriza
  un representante, los dos espacios siguen disponibles pero son opcionales.
  `listo_para_cierre_medico` del servidor decide si puede continuar el médico.
  La capacidad para autorizar se toma del documento guardado y admite booleanos
  o textos como `false`/`0` sin invertir su significado.
- La firma de paciente, familiar, testigos o médico no cierra el modal automáticamente.
  Después de una lectura válida se muestra una confirmación única: “Aceptar y aplicar
  firma(s)”, que refresca el documento y cierra la ventana; las tarjetas de firmas
  ya se actualizan al guardar cada firma. El contador de
  testigos muestra el total realmente registrado, no la posición del último testigo.
- Si la huella médica fue aceptada y el registro local ya existe, una sincronización
  pendiente o fallida con Vertical bloquea una segunda lectura: muestra el estado real
  y permite “Aceptar” o “Actualizar estado”. Al reabrir, el estado del documento
  recupera la firma médica vigente y su operación de sincronización. Se consulta
  el estado inmediatamente antes de encender el lector para reducir duplicados
  entre estaciones. La vigencia clínica y la sincronización se consultan por
  separado; después de guardar se
  refrescan el estado exacto, las tarjetas, el expediente y la bandeja de
  firmas incluso si la entrega a Vertical queda pendiente. Una tarjeta ya
  firmada ofrece “Ver firma”, no otra captura. La nota 87/01 conserva su firma
  vigente aunque Vertical añada metadatos nativos al mismo registro. Si Vertical
  no responde y el servidor reporta
  `medico_sync_unverified`, el modal y la tarjeta universal muestran la firma
  local como pendiente de revisión y bloquean otra lectura, aunque
  `medico_firmado` sea falso porque la versión actual no pudo comprobarse.
- Si Vertical no permite verificar las firmas de paciente, familiar o testigo,
  `detalles.source_unverified` bloquea la captura y el cierre médico en el modal.
  En vez de mostrar ausencias de firmas como definitivas, ofrece actualizar el
  estado y pide no repetir la huella hasta poder comprobar la versión.
- El consentimiento de transfusión PLT-09 muestra “Ver firmas registradas”
  cuando sólo hay evidencias biométricas de paciente, familiar o testigo, con
  identidad, papel, fecha e identificador del registro. No las presenta como
  FEA médica. Cuando existe una firma médica HES vigente de esa ranura,
  “Ver auditoría de firma” abre la misma verificación de integridad usada por
  los demás consentimientos; un marcador firmado sólo en Vertical no se
  etiqueta como sello FEA de HES.
- La captura de enfermería usa verbos de tarea (“Registrar atención”, “Actualizar camas”,
  “Guardar atención”) y evita términos internos como “pre-captura” o “sincronizar”.
- Los encabezados, la navegación y las acciones principales conservan los colores
  institucionales: azul `#004687`, azul claro `#0088C9` y verde `#00974A`.
  La capa de confort de `styles/he-premium.css` suaviza únicamente fondos, bordes,
  sombras y estados secundarios, además de reducir el movimiento.
- Los estados técnicos continúan en el backend y en los registros de auditoría; cambiar
  la presentación no modifica permisos, validaciones biométricas ni sincronización clínica.

## Captura biométrica

`useDigitalPersona` usa un controlador singleton (`utils/trustedCapture.js`).
Solicita challenge/autorización al backend, inicia `/begin-capture` en el agente
local de la estación y consulta `/capture-result`. El SDK nativo controla el USB;
la SPA no recibe RAW ni descifra plantillas de referencia. Conserva únicamente
FMD atestado/challenge/sesión hasta enviarlos y los purga al cerrar/reintentar.
La cancelación invalida respuestas tardías y llama `/cancel-capture`; los fallos
permiten reintentar con challenge nuevo. Un monitor singleton vuelve a probar el
agente cada 800 ms y no abre probes mientras existe una captura física activa.
Si `/devices` informa `busy`, conserva el inventario pero aclara que la lectura
está en curso en ese equipo; no autoemite challenges hasta que la captura de la
otra pestaña termine. El estado es exclusivo del agente loopback de cada estación,
no un bloqueo compartido entre las aproximadamente 50 computadoras.
Los errores de challenge/captura se conservan hasta un reintento explícito; el
inventario periódico sólo limpia errores de conectividad del agente. Los
endpoints públicos de login nunca reciben un JWT residual. La aplicación sólo
cierra la sesión ante respuestas 401 que confirman un problema de autenticación
(token ausente, inválido o revocado); un reto biométrico fallido o vencido conserva
la sesión y permite reintentar. Un rechazo de login público permanece visible y
no cancela el controlador desde el interceptor.
Captura local/challenge tienen timeout de 15 s por petición. HTTP de intranet
se rechaza con un mensaje de HTTPS antes de usar `crypto.randomUUID`.
Un login fallido exige reintento explícito; no hay temporizador que reactive el
lector al cambiar a Personal. Respuestas tardías tras cambiar de pestaña o
desmontar la pantalla no establecen una sesión ni navegan.
FastAPI también ignora cualquier `Bearer` residual cuando `action=LOGIN`; los
otros tipos de challenge continúan exigiendo y validando autenticación.
Un detalle de respuesta que indique que la huella no coincide nunca dispara el
cierre global de sesión, incluso si una ruta antigua lo devuelve como 401; el
modal muestra un error recuperable y mantiene el formulario visible.
La sesión del usuario cierra tras 20 minutos sin actividad real. El temporizador
se inicia al autenticarse, sincroniza la actividad entre pestañas y consulta un
heartbeat cada cinco minutos sólo mientras hay actividad reciente. Las respuestas
Las respuestas autenticadas pueden renovar el JWT mediante `X-Session-Token` sólo en
el heartbeat periódico; la marca `X-Session-Authenticated` distingue un error de
firma recuperable de un token inválido. Consultas de datos en segundo plano no
prolongan por sí solas el plazo. La sesión también se valida en backend por
inactividad, no sólo en la UI.
`iniciar.bat` ejecuta primero `scripts/reset_hes_development_listeners.ps1`:
si 8000/8082 pertenecen a una instancia HES saludable anterior, la reemplaza
antes de generar la nueva credencial compartida. Si identifica otro proceso,
falla sin cerrarlo.
Las peticiones declaran `targetAddressSpace: loopback`. La CSP servida por
FastAPI autoriza únicamente `127.0.0.1:8082`/`localhost:8082` además del propio
origen y `blob:` para que el visor PDF lea el archivo temporal dentro del
navegador. El portal público de cotejo también necesita estilos en línea e imágenes
`data:` para conservar su diseño institucional al abrirse desde un QR; la CSP
los permite de forma explícita, sin habilitar marcos ni objetos. Chrome solicita
el permiso de acceso a dispositivos locales; si está
pendiente o denegado, el login muestra cómo concederlo y permite reintentar.
Ver [[Biometria-DigitalPersona]].
`utils/biometricLifecycle.js` registra la purga sin importar el hook desde
`api.js`; así evita un ciclo de inicialización `api` ↔ `useDigitalPersona` que
dejaría indefinida la instancia Axios al solicitar el primer challenge.

`ErrorBoundary` reconoce fallos de imports dinámicos cuando una pestaña conserva
el hash de una compilación anterior. Recarga una sola vez por asset mediante
`sessionStorage`; si el mismo chunk continúa ausente, muestra la pantalla de error
sin crear un ciclo de recargas.

`ClinicalPdfViewer` recibe los bytes obtenidos por Axios con JWT o una URL
`blob:` local y los entrega a PDF.js. El worker se
sirve siempre desde los assets locales: no hay fallback a CDN. Si su hash desaparece
durante una recompilación, la SPA recarga una sola vez. El fallback por `iframe` no
se usa porque la CSP clínica mantiene `object-src 'none'`; descargar y abrir fuera
continúan disponibles.
`AuthenticatedPdfButton` obtiene el PDF con el interceptor JWT y lo abre en
`/ehr/visor-pdf`, una vista protegida que renderiza con PDF.js y descarga con el
nombre clínico del `Content-Disposition`. Los estudios de laboratorio e
imagenología usan esa misma vista al abrirse en otra pestaña. La URL `blob:`
temporal no se muestra como página del navegador porque al descargar desde su
visor nativo Chrome le asigna el UUID de la URL como nombre. El botón de
descarga y Ctrl+S en la vista usan el nombre clínico; el JWT nunca entra en la
URL. La impresión conserva el PDF original.
Para una versión guardada del consentimiento 09 (`mrnum` exacto), el botón usa
`POST /pdf-preparar` y recibe la copia con QR resguardada; las vistas previas y
los otros motores usan GET autenticado hasta tener un preparador propio.

## Flujo biométrico contextual (2026-09-19)

`useBiometricSignersQuery`, `useDocumentSignaturesQuery` y
`useReadDocumentSignatures` centralizan las consultas de firmantes/estado.
El botón médico consulta la política actual del servidor: no impone testigos
a todas las notas ni permite cerrar consentimientos incompletos.
`biometricSigners.js` conserva el rol persistido (incluido FAMILIAR/TUTOR),
deduplica por ID y asigna T1/T2 por rol, no por posición en una lista.
`trustedCapture` publica contexto no biométrico junto al resultado y lo purga
al cancelar/fallar. Los modales verifican dicho contexto y descartan respuestas
tardías; no muestran firma completa sólo porque el paciente ya firmó.
`useSpecialSignatureSignersQuery` alimenta el modal común de áreas firmantes.
`UsersManagerTab` separa los formatos de consulta (`formatos_permitidos`) de
los formatos donde la cuenta puede firmar (`formatos_firma_permitidos`). La
lista de firma se deriva de los requisitos que declara cada formato e indica
“requiere firma de: …”; una cuenta de Banco de Sangre no recibe permisos para
leer pacientes o expediente. Administración/Sistemas registra su huella desde
Usuarios y permisos. Tras la firma médica, la pantalla abre cada área pendiente
en secuencia; cerrar el modal deja visible el paso pendiente en el formato.

## Relaciones en el Proyecto
- Consume exclusivamente los endpoints autenticados provistos por el [[Backend]]. Contrato en [[API-Endpoints]].
- Empaqueta sus assets de producción en `dist/` para ser distribuidos en la fase de [[Pase_a_Produccion]].
- Medicación, suspensión, dieta, firma y alta envían `Idempotency-Key` y
  distinguen visualmente éxito confirmado de `202` pendiente; un cambio local
  pendiente nunca se presenta como sincronizado con Vertical.
- `src/utils/clinicalSyncResult.js` centraliza esa regla: sólo HTTP 200/201 con
  `success=true` y `state=SYNCED` produce mensaje de éxito. HTTP 202,
  `success=false` o estados pendientes muestran “SINCRONIZACIÓN PENDIENTE” y
  conservan el `operation_id` para reconciliación.

---
> 🤖 *Contexto IA: para nuevas pantallas extender `useQueries.js`, no usar `useEffect + api.get` suelto. No loguear huellas/FMD. Ver [[Guia-Desarrollo-IA]].*

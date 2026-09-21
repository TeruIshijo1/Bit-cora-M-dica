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
actualizado: 2026-09-21
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

El Frontend del proyecto es responsable de la interfaz gráfica hospitalaria, la interacción en tiempo real y la captura biométrica fluida.

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

## Lenguaje y experiencia de uso

- La interfaz operativa usa instrucciones breves y palabras cotidianas: “Leer huella”,
  “Registrar huella”, “Firma guardada” y “Intentar de nuevo”. Los nombres de protocolos,
  algoritmos, tablas y sellos no se muestran en el flujo normal; permanecen disponibles
  en auditoría y trazabilidad.
- `utils/userMessages.js` traduce fallos de lector, sesión y challenge a acciones que el
  personal puede realizar sin exponer detalles internos.
- Los flujos de firmantes separan dos pasos visibles: guardar los datos de la persona y
  registrar su huella. La lectura nunca comienza al abrir el modal; requiere pulsar el
  botón correspondiente.
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
endpoints públicos de login nunca reciben un JWT residual. Un 401 en una ruta
protegida elimina autenticación y purga biometría; un rechazo de login público
permanece visible para reintentar y no cancela el controlador desde el interceptor.
Captura local/challenge tienen timeout de 15 s por petición. HTTP de intranet
se rechaza con un mensaje de HTTPS antes de usar `crypto.randomUUID`.
Un login fallido exige reintento explícito; no hay temporizador que reactive el
lector al cambiar a Personal. Respuestas tardías tras cambiar de pestaña o
desmontar la pantalla no establecen una sesión ni navegan.
FastAPI también ignora cualquier `Bearer` residual cuando `action=LOGIN`; los
otros tipos de challenge continúan exigiendo y validando autenticación.
`iniciar.bat` ejecuta primero `scripts/reset_hes_development_listeners.ps1`:
si 8000/8082 pertenecen a una instancia HES saludable anterior, la reemplaza
antes de generar la nueva credencial compartida. Si identifica otro proceso,
falla sin cerrarlo.
Las peticiones declaran `targetAddressSpace: loopback`. La CSP servida por
FastAPI autoriza únicamente `127.0.0.1:8082`/`localhost:8082` además del propio
origen. Chrome solicita el permiso de acceso a dispositivos locales; si está
pendiente o denegado, el login muestra cómo concederlo y permite reintentar.
Ver [[Biometria-DigitalPersona]].
`utils/biometricLifecycle.js` registra la purga sin importar el hook desde
`api.js`; así evita un ciclo de inicialización `api` ↔ `useDigitalPersona` que
dejaría indefinida la instancia Axios al solicitar el primer challenge.

`ErrorBoundary` reconoce fallos de imports dinámicos cuando una pestaña conserva
el hash de una compilación anterior. Recarga una sola vez por asset mediante
`sessionStorage`; si el mismo chunk continúa ausente, muestra la pantalla de error
sin crear un ciclo de recargas.

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

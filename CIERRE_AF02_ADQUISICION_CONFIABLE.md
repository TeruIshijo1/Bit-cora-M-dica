# CIERRE AF-02 — ADQUISICIÓN CONFIABLE DIGITALPERSONA

Fecha: 2026-09-18. Estado final: **AF-02 CERRADO**.

Referencia: `VERIFICACION_Y_REMEDIACION_FINAL_ASTRA.md`. Este documento sustituye
exclusivamente el estado AF-02 de esa verificación histórica. AF-01 y AF-03..AF-11
conservan su cierre, con regresión comprobada. No se hicieron push, despliegues,
operaciones en producción ni conexiones a KH_HE. Los cambios y el paquete de
entrega permanecen en el workspace local. PostgreSQL usado: base local TEST
separada, con guardas de entorno y migraciones; ERP simulado en las pruebas.

## Resultado y SDK real

Se reemplazó el bloqueo de software por una ruta de adquisición física que no
acepta imágenes ni FMD del navegador para convertirlos en capturas recientes.

Inspección previa a implementar:

| Componente | Evidencia local |
|---|---|
| Lector | U.are.U 4500 Fingerprint Reader HID Global, PnP OK, USB local |
| Runtime | DigitalPersona U.are.U RTE 3.2.0.89 |
| Managed SDK | `C:\Program Files\DigitalPersona\U.are.U RTE\Windows\Lib\DotNET\DPUruNet.dll`, con documentación XML |
| Bibliotecas nativas | `C:\Windows\System32\dpfpdd.dll` y `dpfj.dll`, versión 3.2.0.89; también instalación x86 en SysWOW64 |
| Servicios/componentes | DpHost / DpHostW.exe, DPAgent.exe; drivers DigitalPersona/HID presentes |
| Compilación | .NET Framework 4.x, csc x64; compilación y apertura exclusiva verificadas |
| Binding anterior | uareu-biometric 1.0.2 tenía stubs de captura; eliminado como dependencia del agente |
| Bio-security anterior | Revisado sólo en lectura; el flujo RAW anterior no ofrece adquisición física confiable |

APIs verificadas con XML/reflexión y ejecutadas con el SDK instalado:
`ReaderCollection.GetReaders`, `Reader.Open(DP_PRIORITY_EXCLUSIVE)`, `GetStatus`,
`Reader.Capture(ANSI, DP_IMG_PROC_DEFAULT, timeout, resolution)`, `CancelCapture`,
`FeatureExtraction.CreateFmdFromFid`, `Importer.ImportFmd`, `Comparison.Compare`.
No se inventaron APIs ni se sustituyó el driver por una simulación en producción.

## Arquitectura final

```text
SERVIDOR CENTRAL HOSPITAL
FastAPI + PostgreSQL + frontend + integraciones
             ↕ HTTPS / LAN
PC CLIENTE DEL MÉDICO
Navegador → 127.0.0.1:8082 HES Biometric Agent
           → bridge .NET Framework x64
           → SDK DigitalPersona → lector 4500 USB
```

Captura y matching ANSI ocurren en cada estación biométrica. El servidor central
no necesita lector USB, SDK Windows ni acceso al localhost de la estación.
También se eliminó su anterior llamada a `127.0.0.1:8082/match-bulk`; ahora valida
el resultado firmado por el agente. Readiness central informa que la biometría
es una capacidad de la estación cliente, no un servicio USB central.
La PC actual es exclusivamente de desarrollo y prueba.

El instalador `biometric-service/install-client.ps1` compila el bridge contra el
SDK real instalado y prepara Node/dependencias en una carpeta por usuario.
Configura origen HTTPS exacto, escucha exclusivamente loopback, cifra el secreto
con DPAPI CurrentUser y restringe el archivo al usuario/SYSTEM. Puede registrar
inicio al logon; no abre puertos LAN. `start-client.ps1` inicia el agente oculto.
Instrucciones completas en `biometric-service/README.md`.

Se probó una instalación dentro de `scratch/af02_capture/installed-client`, con
secreto sintético y `-NoStartup`. Pasaron compilación, npm ci, escritura DPAPI y
comprobación de ausencia del secreto en texto claro. No se modificó el inicio
Windows ni se instaló fuera del workspace. El paquete fuente listo para instalar
es `scratch/af02_capture/HES-Biometric-Agent-client.zip`; no contiene secretos,
biometría, node_modules ni DLL propietarias. Cada estación debe tener el runtime
real, Node/npm y .NET Framework; el instalador acepta la ruta del SDK.

## Protocolo y demostración de freshness

1. FastAPI crea challenge aleatorio, guarda su hash en PostgreSQL y fija TTL
   de 120 s. Devuelve autorización V2 firmada con challenge, sesión, acción,
   actor, identidad esperada, paciente/documento e inicio/vencimiento.
2. Si requiere comparación, incluye las referencias ANSI cifradas AES-256-GCM.
   El challenge es AAD; la clave se deriva por HMAC con dominio separado. El
   navegador transporta el trabajo cifrado sin recibir referencias en claro.
3. `/begin-capture` sólo admite la autorización. Verifica HMAC/TTL antes de
   crear acquisition_id aleatorio de 256 bits y abrir el dispositivo exclusivo.
   Rechaza campos RAW, data, FMD, acquisition_id o captured_at aportados por cliente.
4. El proceso nativo inicia Reader.Capture después del challenge y adquiere la
   muestra directamente del USB. Valida resultado/calidad/dispositivo, extrae
   ANSI 378, limpia buffers en finally y libera el SDK/lector antes de responder
   por pipes privados. No genera archivos de imagen.
5. El agente valida orden temporal y dispositivo, ejecuta matching local cuando
   corresponde y firma evidencia V2: hash SHA-256 del FMD, challenge/sesión,
   acquisition_id, inicio de adquisición/captura, captured_at, dispositivo,
   autorización contextual completa y resultado/identidad/hash de referencia.
   HMAC-SHA256 usa dominios diferentes para autorización y attestation.
6. `/capture-result` devuelve 202 mientras espera y entrega el FMD atestado una
   sola vez; reuso o contexto ajeno falla. Cancelación/TTL eliminan el resultado
   y abortan captura. Capturas simultáneas no generan dos resultados válidos.
7. FastAPI verifica firmas, hash FMD, orden temporal, contexto y challenge.
   PostgreSQL consume el challenge atómicamente y exige acquisition_id único.
   Matching firmado se contrasta con identidad y plantilla enrolada vigentes;
   cambios de plantilla posteriores a emitir la autorización invalidan el match.

`/extract-fmd` y `/acquisitions/start` responden 410: no hay puente RAW/FMD cliente
→ attestation. `/match-bulk` sólo compara ANSI y nunca produce attestation.
La SPA ya no usa WebSDK para adquirir RAW. Un controlador singleton gestiona
challenge, begin, polling y cancelación; invalida respuestas tardías, purga FMD
al cerrar/reintentar y muestra errores recuperables. El login permite reintentar
incluso tras error del lector; los modales cancelan al cerrarse.
El monitor trata `busy=true` como no disponible para una captura nueva, evitando
que pestañas concurrentes emitan challenges repetidos mientras otra usa el lector.
También distingue errores del agente de errores de challenge: el polling sólo
recupera conectividad y no borra un 401 para volver a solicitar challenges en
bucle. Los endpoints públicos de login omiten JWT residuales y limpian cualquier
sesión almacenada al recibir 401.
El backend aplica la misma defensa: `action=LOGIN` ignora un `Bearer` residual,
mientras cualquier otra acción biométrica conserva autenticación obligatoria.
El arranque de desarrollo también es reiniciable: valida los listeners 8000/8082,
cierra sólo una instancia HES reconocible y después genera una única credencial
para la API y el agente nuevos. Un proceso ajeno nunca se termina automáticamente.

La comunicación navegador-agente quedó validada también bajo Chrome moderno:
la CSP central permite `connect-src` exclusivamente al propio origen y al agente
loopback en 8082; cada petición declara `targetAddressSpace: loopback`. Chrome
puede solicitar permiso de acceso a dispositivos locales en la primera visita.
El diagnóstico comprobó que el bloqueo previo ocurría en CSP antes de alcanzar
al agente; no era una falla del SDK, del lector ni del servicio local.
Al habilitar la conexión también se corrigió el ciclo de módulos entre `api.js`
y `useDigitalPersona`: `biometricLifecycle.js` registra la purga por JWT
expirado sin que Axios importe el hook, por lo que la primera solicitud de
challenge siempre recibe la instancia Axios.
La migración idempotente `9e2c4b6d8f10` repara esquemas heredados incompletos;
agrega sólo columnas/índices AF-02 ausentes en challenges, médicos y firmantes.
Preserva filas y marca biometría histórica no vacía `LEGACY_RAW` para
reenrolamiento, sin intentar convertirla.

PostgreSQL mantiene exclusivamente el envelope FMD ANSI canónico versión 1;
V2 es la versión del protocolo de adquisición, no una conversión del dato
almacenado. LEGACY_RAW continúa bloqueado y exige reenrolamiento. Matching no
sobrescribe plantillas, y las reglas FEA/segundo actor siguen vigentes.

La confianza incluye el agente, su SDK, la cuenta Windows y el secreto HMAC
aprovisionado. No se afirma hardware attestation frente a una estación tomada
por un administrador/atacante con ese secreto. DPAPI protege el secreto en disco
frente a otras cuentas; el navegador nunca lo recibe. Sincronizar los relojes y
aprovisionar sólo el origen HTTPS real al instalar cada estación.

## Prueba física ejecutada

Con el operador presente, se ejecutó `node biometric-service/scripts/smoke-native.js`
contra el lector USB conectado. Terminó con código 0:

| Comprobación | Resultado |
|---|---|
| Detección y apertura del 4500 | PASS |
| Espera de dedo y captura física posterior al challenge | PASS |
| Extracción FMD ANSI mediante DPUruNet | PASS |
| Attestation emitida por el servicio y HMAC verificado | PASS |
| Importación/comparación nativa de la muestra consigo misma | PASS |
| Reapertura del lector tras cleanup | PASS |
| Identidad clínica utilizada | Ninguna |
| Persistencia de RAW o FMD del smoke | Ninguna |

La comparación consigo misma comprueba integración real del matcher; no pretende
estimar FAR/FRR ni certificar identificación clínica. La aceptación backend del
protocolo completo se comprobó por separado con adaptador TEST y PostgreSQL.
Registro sanitizado: `scratch/af02_capture/physical-smoke-result.json`.
No queda GATE_FISICO_PENDIENTE para este smoke de desarrollo. La instalación y
validación HTTPS/loopback de cada futura estación corresponde al despliegue;
no se ejecutó despliegue ni se afirma haber probado la LAN de producción.

## Pruebas y regresión

| Verificación | Resultado |
|---|---|
| Suite PostgreSQL completa | 170 PASS + 10 subpruebas PASS |
| AF-01..AF-11 y reproducción dirigida anterior, adaptada a V2 | 26 PASS (18 de regresión + 8 dirigidas) |
| biometric-service, adaptador TEST en la misma interfaz del driver | 24 PASS |
| Frontend pruebas de protocolo/cancelación, reintento, JWT residual y utilidades | 13 PASS |
| Chrome 153 real: CSP → challenge HTTP 200 → agente → espera física del 4500 | PASS |
| Frontend lint:runtime | PASS |
| Frontend build | PASS; aviso de tamaño de bundle preexistente |
| Mobile TypeScript --noEmit | PASS |
| Python compileall backend, excluyendo venv/cache | PASS |
| Node syntax server/native-device/capture-protocol | PASS |
| Alembic upgrade/check PostgreSQL TEST | PASS; sin operaciones nuevas |
| Compilación nativa + instalador local | PASS |
| Sintaxis PowerShell de instalador, launcher y build | PASS |
| Scanner de secretos | PASS; 0 hallazgos de alta confianza |

Cobertura AF-02: RAW archivado y FMD arbitrario rechazados antes de activar el
lector; evento de dispositivo → attestation válida; adquisición anterior al
challenge rechazada; adquisición reutilizada rechazada; challenge/sesión/acción/
paciente/documento alterados rechazados; TTL y muestras antiguas rechazados;
lector desconectado, SDK ausente, timeout, extracción fallida o dispositivo
cambiado sin attestation; concurrencia con un ganador; cancelación sin resultado;
backend acepta evidencia Node legítima y rechaza HMAC/datos falsificados;
ninguna prueba persiste RAW. Las nueve pruebas nuevas de backend ejecutan el
servicio Node por HTTP con inyección TEST y validan AES/HMAC reales entre lenguajes.
Los cinco casos anteriores de errores del matcher se adaptaron a resultados
atestados inválidos; los fallos de dispositivo/transporte local se cubren en Node.

Comandos principales reproducibles desde la raíz (PowerShell):

```powershell
backend/venv/Scripts/python.exe backend/scripts/run_local_postgres_tests.py
backend/venv/Scripts/python.exe backend/scripts/run_local_postgres_tests.py backend/tests/test_af_remediation_regressions.py scratch/af02_capture/verification_backend.py
node --test biometric-service/test/acquisition-freshness.test.js
node --test frontend/test/*.test.js
npm --prefix frontend run lint:runtime
npm --prefix frontend run build
# Desde mobile_app: .\node_modules\.bin\tsc.cmd --noEmit
backend/venv/Scripts/python.exe -m compileall -q -x 'venv|__pycache__' backend
backend/venv/Scripts/python.exe backend/scripts/run_local_alembic_check.py
```

Logs sanitizados por comando en `scratch/af02_capture/`: backend-full.log,
af-directed.log, biometric-tests.log, frontend-tests.log, frontend-lint.log,
frontend-build.log, mobile-typecheck.log, compileall.log, alembic-check.log,
installer.log, secret-scan.log. No incluyen RAW/FMD del smoke físico.

## Código modificado en este cierre

- `biometric-service/native/CaptureBridge.cs`, `native/build.ps1`, `native/.gitignore`:
  captura, cancelación, extracción y comparación reales; binarios locales ignorados.
- `biometric-service/native-device.js`, `capture-protocol.js`, `server.js`:
  interfaz nativa, protocolo, cifrado, estado de adquisición y errores cerrados.
- `biometric-service/install-client.ps1`, `start-client.ps1`, `.gitignore`, README:
  instalación por estación y configuración protegida.
- `biometric-service/package.json`, `package-lock.json`: retiro del binding stub.
- `biometric-service/test/acquisition-freshness.test.js`, `testing/capture-fixture.cjs`,
  `scripts/smoke-native.js`: pruebas sin hardware, puente entre lenguajes y smoke físico.
- `backend/biometric_security.py`, `main.py`, `schemas.py`, `.env.example`:
  autorización V2, validación, match local firmado y readiness según arquitectura.
- `backend/tests/test_biometric_security.py`, `test_af02_native_protocol.py`:
  fixtures V2 y regresiones criptográficas/PostgreSQL.
- `frontend/src/utils/trustedCapture.js`, `hooks/useDigitalPersona.js`,
  `pages/LoginDual.jsx`, los tres modales de `features/biometrics/`,
  `frontend/test/trustedCapture.test.js`: protocolo nuevo, purga, cancelación y reintento.
- Notas `docs/Biometria-DigitalPersona.md`, `Frontend.md`, `API-Endpoints.md`,
  `Seguridad-FEA.md`, `Arquitectura.md`, `Pase_a_Produccion.md`: contrato vigente.

Se preservaron los cambios previos del workspace. Durante la corrección posterior
del arranque se agregó la migración idempotente `9e2c4b6d8f10` y se reparó el
esquema de la base local de desarrollo (campos biométricos faltantes). La
regresión usa una base TEST separada; esto no significa que la reparación local
se limitara a TEST. No se migró producción ni se contactó SQL Server.
No se creó commit ni se hizo push. Trabajo terminado en local.

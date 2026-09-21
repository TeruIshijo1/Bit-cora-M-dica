# HES Biometric Agent — estación cliente Windows x64

El hospital ejecuta FastAPI/PostgreSQL/frontend centralmente por HTTPS. Cada PC
con lector USB ejecuta este agente en **127.0.0.1:8082**. El servidor central no
abre USB, no necesita DigitalPersona y no llama al localhost de una estación.
La PC de desarrollo no es el servidor de producción.

## Instalación por estación/usuario

Para distribuir a 50 puestos usar el kit offline `Instalacion_Enfermeria/`:
`Instalar_Enfermeria.bat`, diagnóstico y guía de aceptación. Se genera con
`scripts/build_station_kit.ps1` y apunta a `https://192.168.254.249:8000`.
Incluye Node y módulos, por lo que ese kit no requiere instalar npm ni Internet
en cada estación. El procedimiento fuente siguiente es para desarrollo.
El arranque instalado supervisa el proceso con reinicio gradual (5 a 60 s),
excluye duplicados y admite `stop-client.ps1`. No registra biometría.

Requisitos verificados en desarrollo: U.are.U RTE 3.2.0.89, lector DigitalPersona
4500, driver HID/DigitalPersona y .NET Framework 4.x x64. El SDK real está en
`C:\Program Files\DigitalPersona\U.are.U RTE\Windows\Lib\DotNET\DPUruNet.dll`;
el runtime nativo proporciona `dpfpdd.dll` y `dpfj.dll` en Windows System32.
Instalar el runtime del fabricante en cada estación, además de Node.js y npm.
El SDK/runtime propietario no se guarda en Git. El instalador compila contra la
copia instalada; admite `-SdkDirectory` para otra ruta real.

Copiar esta carpeta fuente (sin node_modules) a la estación y ejecutar:

```powershell
.\install-client.ps1 -AppOrigin https://bitacora.hospital.example
```

Sustituir el origen por el real, sin rutas. El instalador pide en entrada oculta
el `BIOMETRIC_ATTESTATION_SECRET` aprovisionado por Sistemas e idéntico al del
backend. Nunca colocarlo en el frontend, argumentos, repositorio o tickets.
Se instala en `%LOCALAPPDATA%\HESBiometricAgent`; cifra configuración con DPAPI
CurrentUser y restringe el archivo al usuario/SYSTEM. Registra inicio al logon
para ese usuario; `-NoStartup` omite ese registro. Iniciar con
`& "$env:LOCALAPPDATA\HESBiometricAgent\start-client.ps1"` o volver a iniciar sesión.
No requiere abrir firewall ni publicar 8082 en LAN. No instala nada en el
servidor central. Para otro usuario Windows, repetir el aprovisionamiento.
Sincronizar relojes de estaciones y servidor. Configurar HTTPS válido y permitir
al navegador del hospital el acceso a loopback/red local cuando lo solicite.

La confianza abarca el agente, su runtime y la cuenta Windows de la estación:
quien controle esa cuenta o el secreto HMAC puede suplantar al agente. DPAPI
protege el secreto en disco frente a otras cuentas; no es hardware attestation.
La protección de AF-02 impide que el navegador convierta material archivado en
una nueva captura; no pretende resistir una estación comprometida.

## Protocolo V2

Backend emite challenge de 120 s + autorización firmada con acción/sesión y
contexto paciente/documento/identidad. Las referencias ANSI viajan cifradas con
AES-256-GCM en esa autorización. El navegador no las descifra.
`POST /begin-capture {authorization}` abre físicamente el lector mediante
`native/CaptureBridge.exe`. `POST /capture-result {authorization,acquisition_id}`
responde 202 mientras espera y entrega una sola vez el FMD atestado. Cancelar
con `/cancel-capture` y los mismos campos. Ante error/reintento solicitar un
challenge nuevo. `/devices` prueba apertura del lector; `/health` es liveness.

El bridge usa DPUruNet Reader.Capture → FeatureExtraction.CreateFmdFromFid;
matching usa Importer.ImportFmd + Comparison.Compare (umbral existente 10000).
Limpia buffers RAW/FMD en finally y libera el lector antes de devolver el
resultado privado al agente. El agente firma hash FMD, tiempos, dispositivo,
adquisición, autorización contextual y resultado de comparación. FastAPI
verifica HMAC, contexto, frescura, plantilla vigente y consumo único en PostgreSQL.
No hay RAW en navegador, HTTP, DB ni archivos. `/extract-fmd` y
`/acquisitions/start` están retirados (410). `/match-bulk` compara ANSI, pero
jamás emite attestation ni autoriza por sí solo una operación clínica.

## Desarrollo y pruebas

```powershell
npm ci --ignore-scripts
.\native\build.ps1
npm test
node .\scripts\smoke-native.js
```

El smoke solicita un dedo durante 60 segundos. Sólo imprime indicadores;
comprueba detección, captura, ANSI FMD, HMAC, comparación de la muestra consigo
misma y reapertura tras cleanup. No usa identidad clínica ni persiste biometría.
Esta comparación comprueba integración del SDK, no estima FAR/FRR clínicos.
El adaptador TEST sólo se inyecta en pruebas por código: no hay interruptor HTTP
ni variable de producción que sustituya el dispositivo físico.

# Estaciones Bitácora HES — médicos y enfermería

Destino previsto: **https://192.168.254.249:8000/login**. Paquete para Windows x64;
cada estación tiene su propio lector USB y agente en **127.0.0.1:8082**.
El servidor central no necesita lector, DigitalPersona ni este instalador.

## Antes de distribuir a las 50 computadoras

Sistemas debe configurar TLS del servidor con certificado cuyo SAN incluya
`IP:192.168.254.249`, emitido por la CA institucional confiada en las estaciones.
Distribuir la CA mediante el mecanismo institucional; no instalar certificados
desconocidos ni omitir advertencias del navegador. No se incluyen certificados,
claves privadas ni secretos en este paquete. Ver `SERVIDOR_Y_LIBERACION.md`.
El acceso HTTP por IP no cumple los requisitos de contexto seguro del navegador.
No usar flags que desactiven seguridad como solución permanente.

## Instalación en cada estación

1. Copiar **la carpeta completa** `Instalacion_Enfermeria` al disco local o USB.
   Conectar un único DigitalPersona 4500. Usar Windows x64, .NET Framework 4.x
   y Edge/Chrome mantenidos por Sistemas. No se admite Windows x86.
2. Iniciar Windows con la cuenta que utilizará Bitácora. Ejecutar
   `Instalar_Enfermeria.bat`. **No ejecutar toda la instalación como otra cuenta**:
   el secreto queda cifrado para el usuario actual. Sólo el asistente del
   fabricante puede solicitar elevación administrativa para instalar drivers.
3. El programa comprueba SHA-256 de los archivos e instala, si falta, el runtime
   U.are.U RTE 3.2.0.89 incluido. Si pide reinicio, reiniciar y repetir el paso 2.
   El nombre histórico `DigitalPersona_Web_Client` contiene el RTE real; no es
   necesario instalar otro WebSDK para la captura HES V2.
4. Sistemas introduce, en entrada oculta, el **secreto estable del servidor**
   `BIOMETRIC_ATTESTATION_SECRET`, de al menos 32 caracteres aleatorios.
   Debe coincidir exactamente en servidor y estaciones. La clave temporal de
   `iniciar.bat` sólo sirve para desarrollo. No copiarla al kit ni a un ticket.
5. Se instala Node portable con dependencias ya incluidas y el agente en
   `%LOCALAPPDATA%\HESBiometricAgent`. No requiere npm ni Internet en cada PC.
   La configuración usa DPAPI CurrentUser; no copiar `client-config.json`
   entre PCs o usuarios. Otro usuario Windows requiere aprovisionamiento propio.
6. Se crea acceso directo a Bitácora y arranque automático al iniciar sesión.
   El supervisor reinicia el agente ante salida inesperada, con espera gradual.
   Un agente por estación: cerrar sesión de otros usuarios que mantengan 8082
   ocupado. No abrir 8082 en el firewall ni publicarlo en la red.
7. Ejecutar `Diagnosticar_Estacion.bat`: comprueba agente, lector, origen, HTTPS
   y reloj. Este diagnóstico no usa expedientes ni captura huellas. Después
   abrir Bitácora y autorizar acceso a dispositivos locales si el navegador
   lo pide. La prueba PowerShell no sustituye el permiso del navegador.

## Prueba de aceptación por puesto

Registrar en `CONTROL_50_ESTACIONES.csv` (sin biometría, contraseñas ni datos de
pacientes): identificador del puesto, usuario Windows y técnico responsable.
Usar exclusivamente un entorno/identidades de prueba para validar:

- Detección, captura y login de médico enrolado; rechazo de identidad incorrecta.
- Cancelar, cambiar a Personal y volver: sin capturas tardías ni solicitudes repetidas.
- Desconectar/reconectar lector; cerrar/abrir navegador; reiniciar Windows y verificar arranque.
- Dos pestañas: una captura activa, la otra informa ocupado; no cruza huellas.
- Firma de documento de prueba con paciente/documento correctos; sin reutilizar challenge.
- Caducidad de sesión, pérdida de red y recuperación sin duplicar escrituras.

Registrar APROBADO sólo con evidencia de todos los pasos. Hacer primero un
piloto; luego grupos de estaciones, conservando contingencia del hospital.
Ninguna prueba local garantiza disponibilidad absoluta de 50 PCs ni autoriza
por sí sola el uso clínico como expediente electrónico.

## Soporte / actualización

- `Iniciar_Agente.bat`: iniciar manualmente (el supervisor evita duplicados).
- `Detener_Agente.bat`: cerrar primero capturas; solicita parada sólo al agente
  instalado para este usuario. Esperar unos segundos antes de reinstalar.
- Puerto ocupado: cerrar sesión del otro usuario o revisar con Sistemas;
  no matar procesos desconocidos ni reinstalar indefinidamente.
- Runtime/lector no disponible: revisar USB, driver en Administrador de
  dispositivos y runtime. Un servicio HTTP vivo no demuestra que el SDK funcione.
- Autorización inválida: verificar secreto estable y reloj con Sistemas.
- HTTPS/certificado/permisos: corregir infraestructura y permiso del navegador.
- `agent-status.txt` en la carpeta instalada contiene sólo estado operativo.
- Integridad SHA-256 detecta copia incompleta; distribuir desde un medio de
  confianza, pues el manifiesto no es una firma digital del paquete.

El secreto HMAC es compartido: una estación comprometida puede suplantar al
agente. DPAPI protege el archivo entre cuentas, no frente al dueño de la cuenta
o un administrador local. Sistemas debe controlar acceso, distribución y rotación
coordinada del secreto en todas las estaciones y el servidor.

Fuente del requisito del navegador:
[Chrome — Local Network Access](https://developer.chrome.com/blog/local-network-access).

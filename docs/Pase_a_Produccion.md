# Pase a Producción

Esta sección cubre todos los pasos, scripts y configuraciones necesarios para poner el proyecto en marcha y desplegarlo en un entorno productivo real.

## Elementos y Herramientas
- Scripts de preparación y migración: `preparar_produccion.py`.
- Scripts batch para facilitar el despliegue en servidores Windows: `iniciar.bat`, `instalar.bat`, `instalar server.bat`.
- Uso de Ngrok (`ngrok.exe`) para exponer los puertos locales temporalmente durante pruebas o integraciones iniciales.
- Directorio de `pase_a_produccion/` con configuraciones específicas.

## Relaciones en el Proyecto
- Encargado de tomar el código fuente del [[Frontend]] y compilarlo en archivos estáticos (`dist`).
- Configura e inicializa los servicios del [[Backend]] asegurándose de que estén listos para recibir tráfico.
- Verifica la integridad y aplica los últimos cambios a la [[Database]] antes del arranque de los servicios en vivo.

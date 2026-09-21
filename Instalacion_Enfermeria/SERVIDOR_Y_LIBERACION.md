# Configuración prevista del servidor central

Esta guía no ejecuta cambios. El servidor productivo no se contactó desde el
workspace. El sistema operativo del servidor todavía debe confirmarse.

## IP y puerto solicitados

Los usuarios abrirán **https://192.168.254.249:8000**. TLS ocupa el puerto 8000
de LAN; FastAPI queda privado en `127.0.0.1:8001`, sin `--reload`.
Ejemplo de proxy: `deploy/nginx/hes-intranet-8000.conf.example` en el proyecto.
En Linux adaptar la unidad existente cambiando su puerto interno de 8000 a
8001. En Windows usar el supervisor institucional de servicios y el proxy TLS
autorizado; no ejecutar `iniciar.bat` como servicio productivo.
No iniciar proxy y Uvicorn sobre el mismo puerto/dirección.

Variables no secretas que Sistemas debe integrar en la configuración existente:

```text
APP_ENV=production
ALLOWED_HOSTS=192.168.254.249
ALLOWED_ORIGINS=https://192.168.254.249:8000
PROXY_HTTPS_ENABLED=true
```

El agente en cada estación recibe `BIOMETRIC_ALLOWED_ORIGINS` de su instalador;
no se instala ni publica 8082 en el servidor. Conservar claves FEA, JWT, BD,
TSA y demás secretos existentes; no sustituir el `.env` por esta guía. Generar y
aprovisionar la clave estable biométrica antes del piloto. El servidor debe
aceptar cabeceras de proxy sólo desde el proxy confiable, conservar IP de cada
cliente y no agrupar las 50 estaciones bajo la IP del proxy para rate limiting.

## Liberación operativa pendiente

1. Certificado válido con SAN IP y cadena CA confiada en cada estación; permisos
   de acceso local en Chrome/Edge; relojes sincronizados.
2. Migraciones revisadas y aplicadas sobre respaldo validado; la base anterior
   de desarrollo tenía deriva de esquema, no usar `create_all` para migrar.
3. Recursos/capacidad del servidor y PostgreSQL medidos con 50 sesiones reales
   representativas. `DB_POOL_SIZE=10`, `DB_MAX_OVERFLOW=10` son **por worker**:
   dos workers pueden usar 40 conexiones; reservar conexiones para operación.
   La regresión de 50 challenges en TEST no mide PDF, firmas/TSA ni ERP.
4. Pruebas de las rutas clínicas, roles, concurrencia e idempotencia con datos
   sintéticos en STAGING; integración externa real pendiente sin tocar KH_HE.
5. Backup cifrado programado fuera del servidor, prueba de restauración,
   monitoreo y procedimiento de contingencia aprobado por el hospital.
6. Validación clínica, normativa y de responsables antes del uso como EME.

No se declara “cero fallas” ni pase a producción por haber compilado o instalado
un agente. Completar el piloto y acta de aceptación de los 50 puestos.

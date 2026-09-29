---
aliases: [Deploy, Pase a producción, Release HES]
tags: [hes/operaciones, tipo/runbook]
tipo: operacion
modulo: devops
codigo_fuente:
  - preparar_produccion.py
  - deploy/systemd/hes-api.service
  - deploy/nginx/hes.conf.example
  - backend/requirements.txt
  - frontend/package.json
  - scripts/backup_postgres.ps1
actualizado: 2026-09-18
relacionados:
  - "[[00_Inicio]]"
  - "[[Arquitectura]]"
  - "[[Backend]]"
  - "[[Frontend]]"
  - "[[Database]]"
  - "[[Guia-Desarrollo-IA]]"
---

# Pase a Producción

Plan de 50 estaciones: `Instalacion_Enfermeria/LEEME_PRIMERO.md` y
`SERVIDOR_Y_LIBERACION.md`. El kit se genera localmente con
`scripts/build_station_kit.ps1`. La dirección interna de las estaciones puede
seguir siendo `https://192.168.254.249:8000`, pero no debe usarse en los QR:
`PUBLIC_VERIFICATION_BASE_URL` debe apuntar a un dominio HTTPS público que
resuelva desde Internet y desde la casa del paciente. La instalación actual
conserva `VERIFICATION_BASE_URL` como alias compatible mientras se migra al
nombre nuevo.
La plantilla `deploy/nginx/hes-intranet-8000.conf.example` termina TLS en 8000
y usa FastAPI privado en 8001; es alternativa al ejemplo 443/8000 existente.
No se desplegó ni se contactó el servidor; aceptación de estaciones pendiente.

Protocolo oficial de despliegue y empaquetado seguro para el Hospital Escandón.

## Reglas de Oro
1. **El archivo `.env` es Sagrado:** Nunca se sobrescribe en el servidor ni se incluye en el control de versiones.
2. **Sin compilación en el servidor:** El código visual se compila en el entorno de desarrollo (`npm run build`) y se envía como assets estáticos empaquetados.
3. **Multiplataforma Linux / Docker:** El backend no contiene librerías dependientes de Windows COM ni Microsoft Word.
4. **Sin servidor de desarrollo:** `iniciar.bat` es sólo DEV. Producción usa `systemd`, Uvicorn sin `--reload`, dos workers validados y Nginx/TLS.
5. **Fallo cerrado:** `APP_ENV=production` valida secretos, PostgreSQL, origins/hosts HTTPS, proxy HTTPS y confianza TSA antes de servir tráfico.

## Proceso Automatizado
Ejecutar el script en la raíz del proyecto:
```powershell
python preparar_produccion.py
```

### Lo que hace el script:
1. Ejecuta la regresión PostgreSQL, compileall, scanner de secretos e inventario de autorización.
2. Ejecuta lint runtime/build/audit HIGH+ del frontend, typecheck/audit HIGH+ móvil y `node --check` biométrico.
3. Sólo si todos los gates pasan, empaqueta frontend, backend, servicio biométrico, supervisor, proxy, scripts y formatos, excluyendo secretos/datos/runtime.
4. Genera `MANIFEST.sha256.json`. No incluye `.env`, `iniciar.bat`, seeds automáticos ni `--reload`.

## Agente por estación biométrica

`biometric-service/` es software cliente Windows, aunque viaje en el paquete.
No levantarlo en el servidor central. Instalar runtime DigitalPersona y ejecutar
`install-client.ps1 -AppOrigin https://ORIGEN-REAL` en cada estación/usuario con
USB 4500. El instalador aprovisiona secreto DPAPI y arranque al logon; ver
`biometric-service/README.md`. El smoke físico de desarrollo no reemplaza la
verificación de instalación, reloj, origen HTTPS y permisos de acceso loopback
del navegador de cada estación. No se ha desplegado producción en este cierre.

## Checklist pre-pase
- [ ] `APP_ENV=production` y `.env` del servidor intacto (comparar con `backend/.env.example`)
- [ ] `npm run build` verde, `dist/` generado
- [ ] Motores PDF verificados: [[Formatos-PDF]]
- [ ] `systemd` y Nginx/TLS instalados con hosts/origins reales
- [ ] Backup PostgreSQL cifrado, verificado y copiado fuera del host (`scripts/backup_postgres.ps1`)
- [ ] Restore periódico sobre TEST con comprobación de firmas y estados
- [ ] TSA y relojes sincronizados (ver [[Seguridad-FEA]])
- [ ] Acta / validación normativa vigente (ver [[Normativa-NOM]])
- [ ] Gate SQL Server STAGING y lector físico completados

El procedimiento de fallas está en `CONTINGENCIA_OPERATIVA.md`. El estado
binario de liberación está en `PREPRODUCCION_TECNICA_FINAL.md`.

---
> 🤖 *Contexto IA: `pase_a_produccion/` y `backend/generados/` están en `.gitignore`. Nunca commitear `.env`, `*.db`, PDFs generados.*

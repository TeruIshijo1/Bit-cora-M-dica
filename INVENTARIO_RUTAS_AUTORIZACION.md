# Inventario de rutas y autorización

Generado automáticamente por `backend/scripts/audit_route_authorization.py`.

- Total: **231**
- PUBLICA: **37**
- AUTENTICADA: **10**
- ROL_ESPECIFICO: **184**

La columna “roles actuales/locales” refleja dependencias declaradas en cada handler; el middleware global se aplica además a toda ruta no pública.

| Endpoint | Acción | Roles actuales/locales | Roles esperados | Clase | Protección existente/faltante | Fuente |
|---|---|---|---|---|---|---|
| GET `/` | lectura | middleware global | — | PUBLICA | allowlist exacta método+ruta | `route_policy.py:0` |
| GET `/admin` | lectura | middleware global | — | PUBLICA | allowlist exacta método+ruta | `route_policy.py:0` |
| GET `/agenda` | lectura | middleware global | — | PUBLICA | allowlist exacta método+ruta | `route_policy.py:0` |
| GET `/api/agenda/citas` | lectura | middleware global | cualquier identidad activa | AUTENTICADA | middleware global | `backend/main.py:9355` |
| POST `/api/agenda/citas` | creación/acción | middleware global | admin, ayudante, enfermeria, medico, sistemas | ROL_ESPECIFICO | middleware global + política de escritura | `backend/main.py:9424` |
| GET `/api/analytics` | lectura | admin, director, rh, sistemas | admin, director, rh, sistemas | ROL_ESPECIFICO | middleware global + dependencia local | `backend/main.py:4086` |
| GET `/api/api/kh/estudios/{ptmt_num}/pdf` | lectura | middleware global | ayudante, enfermeria, medico | ROL_ESPECIFICO | middleware global + política de lectura clínica | `backend/main.py:4999` |
| GET `/api/atenciones/exportar` | lectura | admin, rh, sistemas | ayudante, enfermeria, medico | ROL_ESPECIFICO | middleware global + política de lectura clínica | `backend/main.py:3111` |
| POST `/api/atenciones/firmar-lote` | creación/acción | middleware global | admin, ayudante, medico | ROL_ESPECIFICO | middleware global + política de escritura | `backend/main.py:3300` |
| GET `/api/atenciones/global` | lectura | JWT autenticado (sin rol local) | ayudante, enfermeria, medico | ROL_ESPECIFICO | middleware global + política de lectura clínica | `backend/main.py:3095` |
| GET `/api/atenciones/historial/{medico_id}` | lectura | middleware global | ayudante, enfermeria, medico | ROL_ESPECIFICO | middleware global + política de lectura clínica | `backend/main.py:3073` |
| GET `/api/atenciones/mis-registros` | lectura | JWT autenticado (sin rol local) | ayudante, enfermeria, medico | ROL_ESPECIFICO | middleware global + política de lectura clínica | `backend/main.py:3087` |
| GET `/api/atenciones/pendientes/{medico_id}` | lectura | middleware global | ayudante, enfermeria, medico | ROL_ESPECIFICO | middleware global + política de lectura clínica | `backend/main.py:3059` |
| POST `/api/atenciones/pre-captura` | creación/acción | JWT autenticado (sin rol local) | admin, enfermeria, sistemas | ROL_ESPECIFICO | middleware global + política de escritura | `backend/main.py:2777` |
| GET `/api/atenciones/todas` | lectura | admin, rh, sistemas | ayudante, enfermeria, medico | ROL_ESPECIFICO | middleware global + política de lectura clínica | `backend/main.py:3103` |
| PUT `/api/atenciones/{folio}` | actualización | middleware global | REQUIERE_DECISION_FUNCIONAL | ROL_ESPECIFICO | bloqueada por defecto (403) | `backend/main.py:3382` |
| PUT `/api/atenciones/{folio}/autorizar` | actualización | sistemas | sistemas | ROL_ESPECIFICO | middleware global + política de escritura | `backend/main.py:4404` |
| POST `/api/atenciones/{folio}/notas` | creación/acción | JWT autenticado (sin rol local) | admin, ayudante, enfermeria, medico, sistemas | ROL_ESPECIFICO | middleware global + política de escritura | `backend/main.py:4346` |
| GET `/api/atenciones/{folio}/pdf` | lectura | middleware global | ayudante, enfermeria, medico | ROL_ESPECIFICO | middleware global + política de lectura clínica | `backend/main.py:3399` |
| PUT `/api/atenciones/{folio}/reaperturar` | actualización | sistemas | sistemas | ROL_ESPECIFICO | middleware global + política de escritura | `backend/main.py:4386` |
| GET `/api/auditoria` | lectura | admin, sistemas | admin, sistemas | ROL_ESPECIFICO | middleware global + dependencia local | `backend/main.py:4192` |
| POST `/api/auth/change-password` | creación/acción | JWT autenticado (sin rol local) | admin, enfermeria, limpieza, rh, sistemas, trabajo_social | ROL_ESPECIFICO | middleware global + política de escritura | `backend/main.py:3553` |
| POST `/api/auth/impersonate` | creación/acción | admin, sistemas | admin, sistemas | ROL_ESPECIFICO | middleware global + política de escritura | `backend/main.py:1318` |
| POST `/api/auth/login/admin` | creación/acción | middleware global | — | PUBLICA | allowlist exacta método+ruta | `backend/main.py:1219` |
| POST `/api/auth/login/biometric` | creación/acción | middleware global | — | PUBLICA | allowlist exacta método+ruta | `backend/main.py:1271` |
| POST `/api/auth/logout` | creación/acción | JWT autenticado (sin rol local) | admin, ayudante, enfermeria, limpieza, medico, rh, sistemas, trabajo_social | ROL_ESPECIFICO | middleware global + política de escritura | `backend/main.py:1426` |
| GET `/api/backup` | lectura | admin, sistemas | admin, sistemas | ROL_ESPECIFICO | middleware global + dependencia local | `backend/main.py:4330` |
| POST `/api/biometrics/challenge` | creación/acción | middleware global | — | PUBLICA | allowlist exacta método+ruta | `backend/main.py:440` |
| GET `/api/camas` | lectura | middleware global | ayudante, enfermeria, medico | ROL_ESPECIFICO | middleware global + política de lectura clínica | `backend/main.py:4445` |
| GET `/api/camas/ocupacion` | lectura | middleware global | ayudante, enfermeria, medico | ROL_ESPECIFICO | middleware global + política de lectura clínica | `backend/main.py:9245` |
| GET `/api/camas/paciente/{pt_num}` | lectura | middleware global | ayudante, enfermeria, medico | ROL_ESPECIFICO | middleware global + política de lectura clínica | `backend/main.py:4514` |
| PUT `/api/camas/{numero_cama}/limpieza` | actualización | Mantenimiento/Limpieza, admin, limpieza, sistemas | admin, limpieza, sistemas | ROL_ESPECIFICO | middleware global + política de escritura | `backend/main.py:4487` |
| GET `/api/catalogos/areas` | lectura | middleware global | cualquier identidad activa | AUTENTICADA | middleware global | `backend/routers/catalogos.py:13` |
| POST `/api/catalogos/areas` | creación/acción | admin, rh, sistemas | admin, rh, sistemas | ROL_ESPECIFICO | middleware global + política de escritura | `backend/routers/catalogos.py:17` |
| DELETE `/api/catalogos/areas/{id}` | eliminación lógica/física | admin, sistemas | admin, sistemas | ROL_ESPECIFICO | middleware global + política de escritura | `backend/routers/catalogos.py:29` |
| GET `/api/catalogos/formatos` | lectura | middleware global | cualquier identidad activa | AUTENTICADA | middleware global | `backend/routers/catalogos.py:71` |
| POST `/api/catalogos/formatos` | creación/acción | middleware global | admin, sistemas | ROL_ESPECIFICO | middleware global + política de escritura | `backend/routers/catalogos.py:75` |
| GET `/api/catalogos/tipos` | lectura | middleware global | cualquier identidad activa | AUTENTICADA | middleware global | `backend/routers/catalogos.py:42` |
| POST `/api/catalogos/tipos` | creación/acción | admin, rh, sistemas | admin, rh, sistemas | ROL_ESPECIFICO | middleware global + política de escritura | `backend/routers/catalogos.py:46` |
| DELETE `/api/catalogos/tipos/{id}` | eliminación lógica/física | admin, sistemas | admin, sistemas | ROL_ESPECIFICO | middleware global + política de escritura | `backend/routers/catalogos.py:58` |
| GET `/api/clinical-sync/operations/{operation_id}` | lectura | middleware global | cualquier identidad activa | AUTENTICADA | middleware global | `backend/main.py:1166` |
| POST `/api/clinical-sync/reconcile` | creación/acción | admin, sistemas | admin, sistemas | ROL_ESPECIFICO | middleware global + política de escritura | `backend/main.py:1190` |
| GET `/api/ehr/alergias/catalogo` | lectura | middleware global | ayudante, enfermeria, medico | ROL_ESPECIFICO | middleware global + política de lectura clínica | `backend/main.py:6774` |
| PUT `/api/ehr/paciente/{paciente_id}/alta` | actualización | JWT autenticado (sin rol local) | admin, enfermeria, sistemas | ROL_ESPECIFICO | middleware global + política de escritura | `backend/main.py:1945` |
| GET `/api/ehr/paciente/{paciente_id}/firmantes-biometricos` | lectura | middleware global | ayudante, enfermeria, medico | ROL_ESPECIFICO | middleware global + política de lectura clínica | `backend/main.py:2510` |
| POST `/api/ehr/paciente/{paciente_id}/firmantes-biometricos` | creación/acción | JWT autenticado (sin rol local) | admin, ayudante, enfermeria, medico, sistemas | ROL_ESPECIFICO | middleware global + política de escritura | `backend/main.py:2173` |
| POST `/api/ehr/paciente/{paciente_id}/firmantes-biometricos/verificar` | creación/acción | middleware global | admin, ayudante, enfermeria, medico, sistemas | ROL_ESPECIFICO | middleware global + política de escritura | `backend/main.py:2548` |
| DELETE `/api/ehr/paciente/{paciente_id}/firmantes-biometricos/{firmante_id}` | eliminación lógica/física | JWT autenticado (sin rol local) | admin, ayudante, enfermeria, medico, sistemas | ROL_ESPECIFICO | middleware global + política de escritura | `backend/main.py:2590` |
| PUT `/api/ehr/paciente/{paciente_id}/firmantes-biometricos/{firmante_id}` | actualización | JWT autenticado (sin rol local) | admin, ayudante, enfermeria, medico, sistemas | ROL_ESPECIFICO | middleware global + política de escritura | `backend/main.py:2276` |
| POST `/api/ehr/paciente/{paciente_id}/firmantes-biometricos/{firmante_id}/enrolar` | creación/acción | JWT autenticado (sin rol local) | admin, ayudante, enfermeria, medico, sistemas | ROL_ESPECIFICO | middleware global + política de escritura | `backend/main.py:2462` |
| POST `/api/ehr/paciente/{paciente_id}/firmantes-biometricos/{firmante_id}/reenrolar` | creación/acción | JWT autenticado (sin rol local) | admin, ayudante, enfermeria, medico, sistemas | ROL_ESPECIFICO | middleware global + política de escritura | `backend/main.py:2489` |
| PUT `/api/ehr/paciente/{paciente_id}/reingresar` | actualización | JWT autenticado (sin rol local) | admin, enfermeria, sistemas | ROL_ESPECIFICO | middleware global + política de escritura | `backend/main.py:2104` |
| GET `/api/ehr/paciente/{pt_num}` | lectura | middleware global | ayudante, enfermeria, medico | ROL_ESPECIFICO | middleware global + política de lectura clínica | `backend/main.py:4523` |
| GET `/api/ehr/paciente/{pt_num}/alergias` | lectura | middleware global | ayudante, enfermeria, medico | ROL_ESPECIFICO | middleware global + política de lectura clínica | `backend/main.py:6788` |
| POST `/api/ehr/paciente/{pt_num}/alergias/actualizar-texto` | creación/acción | middleware global | admin, ayudante, enfermeria, medico, sistemas | ROL_ESPECIFICO | middleware global + política de escritura | `backend/main.py:6909` |
| POST `/api/ehr/paciente/{pt_num}/alergias/inactivar` | creación/acción | middleware global | admin, ayudante, enfermeria, medico, sistemas | ROL_ESPECIFICO | middleware global + política de escritura | `backend/main.py:6861` |
| POST `/api/ehr/paciente/{pt_num}/alergias/registrar` | creación/acción | middleware global | admin, ayudante, enfermeria, medico, sistemas | ROL_ESPECIFICO | middleware global + política de escritura | `backend/main.py:6801` |
| GET `/api/ehr/paciente/{pt_num}/consentimiento-02` | lectura | middleware global | ayudante, enfermeria, medico | ROL_ESPECIFICO | middleware global + política de lectura clínica | `backend/main.py:10936` |
| POST `/api/ehr/paciente/{pt_num}/consentimiento-02` | creación/acción | middleware global | admin, ayudante, enfermeria, medico, sistemas | ROL_ESPECIFICO | middleware global + política de escritura | `backend/main.py:11186` |
| GET `/api/ehr/paciente/{pt_num}/consentimiento-04` | lectura | middleware global | ayudante, enfermeria, medico | ROL_ESPECIFICO | middleware global + política de lectura clínica | `backend/main.py:10389` |
| POST `/api/ehr/paciente/{pt_num}/consentimiento-04` | creación/acción | middleware global | admin, ayudante, enfermeria, medico, sistemas | ROL_ESPECIFICO | middleware global + política de escritura | `backend/main.py:10585` |
| GET `/api/ehr/paciente/{pt_num}/consentimiento-06` | lectura | middleware global | ayudante, enfermeria, medico | ROL_ESPECIFICO | middleware global + política de lectura clínica | `backend/main.py:12999` |
| POST `/api/ehr/paciente/{pt_num}/consentimiento-06` | creación/acción | middleware global | admin, ayudante, enfermeria, medico, sistemas | ROL_ESPECIFICO | middleware global + política de escritura | `backend/main.py:13235` |
| GET `/api/ehr/paciente/{pt_num}/consentimiento-07` | lectura | middleware global | ayudante, enfermeria, medico | ROL_ESPECIFICO | middleware global + política de lectura clínica | `backend/main.py:11245` |
| POST `/api/ehr/paciente/{pt_num}/consentimiento-07` | creación/acción | middleware global | admin, ayudante, enfermeria, medico, sistemas | ROL_ESPECIFICO | middleware global + política de escritura | `backend/main.py:11489` |
| GET `/api/ehr/paciente/{pt_num}/consentimiento-08` | lectura | middleware global | ayudante, enfermeria, medico | ROL_ESPECIFICO | middleware global + política de lectura clínica | `backend/main.py:11543` |
| POST `/api/ehr/paciente/{pt_num}/consentimiento-08` | creación/acción | middleware global | admin, ayudante, enfermeria, medico, sistemas | ROL_ESPECIFICO | middleware global + política de escritura | `backend/main.py:11792` |
| GET `/api/ehr/paciente/{pt_num}/consentimiento-11` | lectura | middleware global | ayudante, enfermeria, medico | ROL_ESPECIFICO | middleware global + política de lectura clínica | `backend/main.py:12144` |
| POST `/api/ehr/paciente/{pt_num}/consentimiento-11` | creación/acción | middleware global | admin, ayudante, enfermeria, medico, sistemas | ROL_ESPECIFICO | middleware global + política de escritura | `backend/main.py:12372` |
| GET `/api/ehr/paciente/{pt_num}/consentimiento-12` | lectura | middleware global | ayudante, enfermeria, medico | ROL_ESPECIFICO | middleware global + política de lectura clínica | `backend/main.py:10147` |
| POST `/api/ehr/paciente/{pt_num}/consentimiento-12` | creación/acción | middleware global | admin, ayudante, enfermeria, medico, sistemas | ROL_ESPECIFICO | middleware global + política de escritura | `backend/main.py:10332` |
| GET `/api/ehr/paciente/{pt_num}/consentimiento-15` | lectura | middleware global | ayudante, enfermeria, medico | ROL_ESPECIFICO | middleware global + política de lectura clínica | `backend/main.py:10642` |
| POST `/api/ehr/paciente/{pt_num}/consentimiento-15` | creación/acción | middleware global | admin, ayudante, enfermeria, medico, sistemas | ROL_ESPECIFICO | middleware global + política de escritura | `backend/main.py:10878` |
| GET `/api/ehr/paciente/{pt_num}/consentimiento-15-ev` | lectura | middleware global | ayudante, enfermeria, medico | ROL_ESPECIFICO | middleware global + política de lectura clínica | `backend/main.py:12712` |
| POST `/api/ehr/paciente/{pt_num}/consentimiento-15-ev` | creación/acción | middleware global | admin, ayudante, enfermeria, medico, sistemas | ROL_ESPECIFICO | middleware global + política de escritura | `backend/main.py:12945` |
| GET `/api/ehr/paciente/{pt_num}/consentimiento-19` | lectura | middleware global | ayudante, enfermeria, medico | ROL_ESPECIFICO | middleware global + política de lectura clínica | `backend/main.py:12426` |
| POST `/api/ehr/paciente/{pt_num}/consentimiento-19` | creación/acción | middleware global | admin, ayudante, enfermeria, medico, sistemas | ROL_ESPECIFICO | middleware global + política de escritura | `backend/main.py:12656` |
| GET `/api/ehr/paciente/{pt_num}/consentimiento-25` | lectura | middleware global | ayudante, enfermeria, medico | ROL_ESPECIFICO | middleware global + política de lectura clínica | `backend/main.py:9653` |
| POST `/api/ehr/paciente/{pt_num}/consentimiento-25` | creación/acción | middleware global | admin, ayudante, enfermeria, medico, sistemas | ROL_ESPECIFICO | middleware global + política de escritura | `backend/main.py:9841` |
| POST `/api/ehr/paciente/{pt_num}/consentimiento-32-01` | creación/acción | middleware global | admin, ayudante, enfermeria, medico, sistemas | ROL_ESPECIFICO | middleware global + política de escritura | `backend/main.py:5763` |
| GET `/api/ehr/paciente/{pt_num}/consentimiento-34-01` | lectura | middleware global | ayudante, enfermeria, medico | ROL_ESPECIFICO | middleware global + política de lectura clínica | `backend/main.py:9898` |
| POST `/api/ehr/paciente/{pt_num}/consentimiento-34-01` | creación/acción | middleware global | admin, ayudante, enfermeria, medico, sistemas | ROL_ESPECIFICO | middleware global + política de escritura | `backend/main.py:10090` |
| GET `/api/ehr/paciente/{pt_num}/consentimiento-43` | lectura | middleware global | ayudante, enfermeria, medico | ROL_ESPECIFICO | middleware global + política de lectura clínica | `backend/main.py:11850` |
| POST `/api/ehr/paciente/{pt_num}/consentimiento-43` | creación/acción | middleware global | admin, ayudante, enfermeria, medico, sistemas | ROL_ESPECIFICO | middleware global + política de escritura | `backend/main.py:12085` |
| POST `/api/ehr/paciente/{pt_num}/consentimiento-eed` | creación/acción | middleware global | admin, ayudante, enfermeria, medico, sistemas | ROL_ESPECIFICO | middleware global + política de escritura | `backend/main.py:9600` |
| GET `/api/ehr/paciente/{pt_num}/dieta-cuidados` | lectura | middleware global | ayudante, enfermeria, medico | ROL_ESPECIFICO | middleware global + política de lectura clínica | `backend/main.py:6424` |
| POST `/api/ehr/paciente/{pt_num}/dieta-cuidados/prescribir-biometrico` | creación/acción | middleware global | admin, ayudante, medico | ROL_ESPECIFICO | middleware global + política de escritura | `backend/main.py:6547` |
| GET `/api/ehr/paciente/{pt_num}/egreso-voluntario-15` | lectura | middleware global | ayudante, enfermeria, medico | ROL_ESPECIFICO | middleware global + política de lectura clínica | `backend/main.py:12712` |
| POST `/api/ehr/paciente/{pt_num}/egreso-voluntario-15` | creación/acción | middleware global | admin, ayudante, enfermeria, medico, sistemas | ROL_ESPECIFICO | middleware global + política de escritura | `backend/main.py:12945` |
| GET `/api/ehr/paciente/{pt_num}/evoluciones-hospitalizacion` | lectura | middleware global | ayudante, enfermeria, medico | ROL_ESPECIFICO | middleware global + política de lectura clínica | `backend/main.py:5461` |
| POST `/api/ehr/paciente/{pt_num}/firmar-biometrico` | creación/acción | middleware global | admin, ayudante, medico | ROL_ESPECIFICO | middleware global + política de escritura | `backend/main.py:6965` |
| POST `/api/ehr/paciente/{pt_num}/firmar-biometrico-firmante` | creación/acción | middleware global | admin, ayudante, enfermeria, medico, sistemas | ROL_ESPECIFICO | middleware global + política de escritura | `backend/main.py:7261` |
| GET `/api/ehr/paciente/{pt_num}/firmas` | lectura | middleware global | ayudante, enfermeria, medico | ROL_ESPECIFICO | middleware global + política de lectura clínica | `backend/main.py:7414` |
| GET `/api/ehr/paciente/{pt_num}/firmas-documento` | lectura | middleware global | ayudante, enfermeria, medico | ROL_ESPECIFICO | middleware global + política de lectura clínica | `backend/main.py:7701` |
| POST `/api/ehr/paciente/{pt_num}/formato-crear-registro` | creación/acción | middleware global | REQUIERE_DECISION_FUNCIONAL | ROL_ESPECIFICO | bloqueada por defecto (403) | `backend/main.py:13370` |
| POST `/api/ehr/paciente/{pt_num}/formato-guardar-registro` | creación/acción | middleware global | REQUIERE_DECISION_FUNCIONAL | ROL_ESPECIFICO | bloqueada por defecto (403) | `backend/main.py:13391` |
| GET `/api/ehr/paciente/{pt_num}/formato-historial` | lectura | middleware global | ayudante, enfermeria, medico | ROL_ESPECIFICO | middleware global + política de lectura clínica | `backend/main.py:13285` |
| GET `/api/ehr/paciente/{pt_num}/historial-auditoria` | lectura | middleware global | ayudante, enfermeria, medico | ROL_ESPECIFICO | middleware global + política de lectura clínica | `backend/main.py:7719` |
| GET `/api/ehr/paciente/{pt_num}/historial-signos-vitales` | lectura | middleware global | ayudante, enfermeria, medico | ROL_ESPECIFICO | middleware global + política de lectura clínica | `backend/main.py:6013` |
| GET `/api/ehr/paciente/{pt_num}/medicamentos` | lectura | middleware global | ayudante, enfermeria, medico | ROL_ESPECIFICO | middleware global + política de lectura clínica | `backend/main.py:6150` |
| POST `/api/ehr/paciente/{pt_num}/medicamentos/discontinuar-biometrico` | creación/acción | middleware global | admin, ayudante, medico | ROL_ESPECIFICO | middleware global + política de escritura | `backend/main.py:6319` |
| POST `/api/ehr/paciente/{pt_num}/medicamentos/prescribir-biometrico` | creación/acción | middleware global | admin, ayudante, medico | ROL_ESPECIFICO | middleware global + política de escritura | `backend/main.py:6159` |
| POST `/api/ehr/paciente/{pt_num}/nota-hospitalizacion` | creación/acción | middleware global | admin, ayudante, enfermeria, medico, sistemas | ROL_ESPECIFICO | middleware global + política de escritura | `backend/main.py:5596` |
| POST `/api/ehr/paciente/{pt_num}/nota-urgencias` | creación/acción | middleware global | admin, ayudante, enfermeria, medico, sistemas | ROL_ESPECIFICO | middleware global + política de escritura | `backend/main.py:5830` |
| GET `/api/ehr/paciente/{pt_num}/pdf-consentimiento-02` | lectura | middleware global | ayudante, enfermeria, medico | ROL_ESPECIFICO | middleware global + política de lectura clínica | `backend/main.py:10993` |
| GET `/api/ehr/paciente/{pt_num}/pdf-consentimiento-04` | lectura | middleware global | ayudante, enfermeria, medico | ROL_ESPECIFICO | middleware global + política de lectura clínica | `backend/main.py:10409` |
| GET `/api/ehr/paciente/{pt_num}/pdf-consentimiento-06` | lectura | middleware global | ayudante, enfermeria, medico | ROL_ESPECIFICO | middleware global + política de lectura clínica | `backend/main.py:13046` |
| GET `/api/ehr/paciente/{pt_num}/pdf-consentimiento-07` | lectura | middleware global | ayudante, enfermeria, medico | ROL_ESPECIFICO | middleware global + política de lectura clínica | `backend/main.py:11301` |
| GET `/api/ehr/paciente/{pt_num}/pdf-consentimiento-08` | lectura | middleware global | ayudante, enfermeria, medico | ROL_ESPECIFICO | middleware global + política de lectura clínica | `backend/main.py:11600` |
| GET `/api/ehr/paciente/{pt_num}/pdf-consentimiento-11` | lectura | middleware global | ayudante, enfermeria, medico | ROL_ESPECIFICO | middleware global + política de lectura clínica | `backend/main.py:12191` |
| GET `/api/ehr/paciente/{pt_num}/pdf-consentimiento-12` | lectura | middleware global | ayudante, enfermeria, medico | ROL_ESPECIFICO | middleware global + política de lectura clínica | `backend/main.py:10166` |
| GET `/api/ehr/paciente/{pt_num}/pdf-consentimiento-15` | lectura | middleware global | ayudante, enfermeria, medico | ROL_ESPECIFICO | middleware global + política de lectura clínica | `backend/main.py:10699` |
| GET `/api/ehr/paciente/{pt_num}/pdf-consentimiento-19` | lectura | middleware global | ayudante, enfermeria, medico | ROL_ESPECIFICO | middleware global + política de lectura clínica | `backend/main.py:12473` |
| GET `/api/ehr/paciente/{pt_num}/pdf-consentimiento-25` | lectura | middleware global | ayudante, enfermeria, medico | ROL_ESPECIFICO | middleware global + política de lectura clínica | `backend/main.py:9673` |
| GET `/api/ehr/paciente/{pt_num}/pdf-consentimiento-32-01` | lectura | middleware global | ayudante, enfermeria, medico | ROL_ESPECIFICO | middleware global + política de lectura clínica | `backend/main.py:5130` |
| GET `/api/ehr/paciente/{pt_num}/pdf-consentimiento-34-01` | lectura | middleware global | ayudante, enfermeria, medico | ROL_ESPECIFICO | middleware global + política de lectura clínica | `backend/main.py:9917` |
| GET `/api/ehr/paciente/{pt_num}/pdf-consentimiento-43` | lectura | middleware global | ayudante, enfermeria, medico | ROL_ESPECIFICO | middleware global + política de lectura clínica | `backend/main.py:11905` |
| GET `/api/ehr/paciente/{pt_num}/pdf-consentimiento-eed` | lectura | middleware global | ayudante, enfermeria, medico | ROL_ESPECIFICO | middleware global + política de lectura clínica | `backend/main.py:9499` |
| GET `/api/ehr/paciente/{pt_num}/pdf-egreso-voluntario-15` | lectura | middleware global | ayudante, enfermeria, medico | ROL_ESPECIFICO | middleware global + política de lectura clínica | `backend/main.py:12759` |
| GET `/api/ehr/paciente/{pt_num}/pdf-expediente-completo` | lectura | middleware global | ayudante, enfermeria, medico | ROL_ESPECIFICO | middleware global + política de lectura clínica | `backend/main.py:5408` |
| GET `/api/ehr/paciente/{pt_num}/pdf-nota-hospitalizacion` | lectura | middleware global | ayudante, enfermeria, medico | ROL_ESPECIFICO | middleware global + política de lectura clínica | `backend/main.py:5469` |
| GET `/api/ehr/paciente/{pt_num}/pdf-nota-urgencias` | lectura | middleware global | ayudante, enfermeria, medico | ROL_ESPECIFICO | middleware global + política de lectura clínica | `backend/main.py:5238` |
| GET `/api/ehr/paciente/{pt_num}/signos-vitales` | lectura | middleware global | ayudante, enfermeria, medico | ROL_ESPECIFICO | middleware global + política de lectura clínica | `backend/main.py:6007` |
| POST `/api/ehr/paciente/{pt_num}/signos-vitales` | creación/acción | middleware global | admin, ayudante, enfermeria, medico, sistemas | ROL_ESPECIFICO | middleware global + política de escritura | `backend/main.py:6020` |
| GET `/api/ehr/paciente/{pt_num}/verificar-documento-estado` | lectura | middleware global | ayudante, enfermeria, medico | ROL_ESPECIFICO | middleware global + política de lectura clínica | `backend/main.py:8262` |
| POST `/api/ehr/paciente/{pt_num}/verificar-integridad` | creación/acción | middleware global | admin, ayudante, enfermeria, medico, sistemas | ROL_ESPECIFICO | middleware global + política de escritura | `backend/main.py:7834` |
| GET `/api/ehr/pacientes/buscar` | lectura | middleware global | ayudante, enfermeria, medico | ROL_ESPECIFICO | middleware global + política de lectura clínica | `backend/main.py:6730` |
| GET `/api/escaneos` | lectura | admin, rh, sistemas | admin, rh, sistemas | ROL_ESPECIFICO | middleware global + dependencia local | `backend/main.py:3934` |
| POST `/api/escaneos` | creación/acción | admin, rh | admin, rh | ROL_ESPECIFICO | middleware global + política de escritura | `backend/main.py:3974` |
| DELETE `/api/escaneos/{escaneo_id}` | eliminación lógica/física | admin, rh | admin, rh | ROL_ESPECIFICO | middleware global + política de escritura | `backend/main.py:4046` |
| PUT `/api/escaneos/{escaneo_id}` | actualización | admin, rh | admin, rh | ROL_ESPECIFICO | middleware global + política de escritura | `backend/main.py:4026` |
| GET `/api/escaneos/{escaneo_id}/archivo` | lectura | admin, rh, sistemas | admin, rh, sistemas | ROL_ESPECIFICO | middleware global + dependencia local | `backend/main.py:3943` |
| GET `/api/files/photos/{filename}` | lectura | JWT autenticado (sin rol local) | cualquier identidad activa | AUTENTICADA | middleware global | `backend/main.py:4017` |
| POST `/api/firmas/{firma_id}/tsa/reintentar` | creación/acción | admin, ayudante, medico | admin, ayudante, medico | ROL_ESPECIFICO | middleware global + política de escritura | `backend/main.py:7215` |
| GET `/api/kh/estudios/{ptmt_num}/pdf` | lectura | middleware global | ayudante, enfermeria, medico | ROL_ESPECIFICO | middleware global + política de lectura clínica | `backend/main.py:4999` |
| GET `/api/medicos` | lectura | middleware global | cualquier identidad activa | AUTENTICADA | middleware global | `backend/main.py:2662` |
| POST `/api/medicos` | creación/acción | admin, rh, sistemas | admin, rh, sistemas | ROL_ESPECIFICO | middleware global + política de escritura | `backend/main.py:2670` |
| GET `/api/medicos/list` | lectura | middleware global | cualquier identidad activa | AUTENTICADA | middleware global | `backend/main.py:9339` |
| PUT `/api/medicos/{medico_id}` | actualización | admin, rh, sistemas | admin, rh, sistemas | ROL_ESPECIFICO | middleware global + política de escritura | `backend/main.py:3610` |
| POST `/api/medicos/{medico_id}/biometria/enrolar` | creación/acción | admin, rh, sistemas | admin, rh, sistemas | ROL_ESPECIFICO | middleware global + política de escritura | `backend/main.py:3823` |
| POST `/api/medicos/{medico_id}/biometria/reenrolar` | creación/acción | admin, rh, sistemas | admin, rh, sistemas | ROL_ESPECIFICO | middleware global + política de escritura | `backend/main.py:3841` |
| PUT `/api/medicos/{medico_id}/datos` | actualización | admin, rh, sistemas | admin, rh, sistemas | ROL_ESPECIFICO | middleware global + política de escritura | `backend/main.py:3657` |
| POST `/api/medicos/{medico_id}/fea/completar-actualizacion` | creación/acción | admin, rh, sistemas | admin, rh, sistemas | ROL_ESPECIFICO | middleware global + política de escritura | `backend/main.py:3859` |
| PUT `/api/medicos/{medico_id}/huella` | actualización | admin, rh, sistemas | admin, rh, sistemas | ROL_ESPECIFICO | middleware global + política de escritura | `backend/main.py:3738` |
| PUT `/api/medicos/{medico_id}/permisos` | actualización | admin, sistemas | admin, sistemas | ROL_ESPECIFICO | middleware global + política de escritura | `backend/main.py:3629` |
| GET `/api/medicos/{medico_id}/procedimientos_frecuentes` | lectura | middleware global | cualquier identidad activa | AUTENTICADA | middleware global | `backend/main.py:3041` |
| GET `/api/operational/metrics` | lectura | admin, sistemas | admin, sistemas | ROL_ESPECIFICO | middleware global + dependencia local | `backend/main.py:423` |
| GET `/api/pacientes` | lectura | middleware global | ayudante, enfermeria, medico | ROL_ESPECIFICO | middleware global + política de lectura clínica | `backend/main.py:1685` |
| POST `/api/pacientes` | creación/acción | JWT autenticado (sin rol local) | admin, enfermeria, sistemas | ROL_ESPECIFICO | middleware global + política de escritura | `backend/main.py:1696` |
| GET `/api/pacientes/altas` | lectura | JWT autenticado (sin rol local) | ayudante, enfermeria, medico | ROL_ESPECIFICO | middleware global + política de lectura clínica | `backend/main.py:4434` |
| POST `/api/pacientes/sincronizar-kh` | creación/acción | admin, enfermeria, sistemas | admin, enfermeria, sistemas | ROL_ESPECIFICO | middleware global + política de escritura | `backend/main.py:1458` |
| PUT `/api/pacientes/{paciente_id}` | actualización | JWT autenticado (sin rol local) | admin, enfermeria, sistemas | ROL_ESPECIFICO | middleware global + política de escritura | `backend/main.py:1758` |
| PUT `/api/pacientes/{paciente_id}/alta` | actualización | JWT autenticado (sin rol local) | admin, enfermeria, sistemas | ROL_ESPECIFICO | middleware global + política de escritura | `backend/main.py:1945` |
| GET `/api/pacientes/{paciente_id}/firmantes-biometricos` | lectura | middleware global | ayudante, enfermeria, medico | ROL_ESPECIFICO | middleware global + política de lectura clínica | `backend/main.py:2510` |
| POST `/api/pacientes/{paciente_id}/firmantes-biometricos` | creación/acción | JWT autenticado (sin rol local) | admin, ayudante, enfermeria, medico, sistemas | ROL_ESPECIFICO | middleware global + política de escritura | `backend/main.py:2173` |
| POST `/api/pacientes/{paciente_id}/firmantes-biometricos/verificar` | creación/acción | middleware global | admin, ayudante, enfermeria, medico, sistemas | ROL_ESPECIFICO | middleware global + política de escritura | `backend/main.py:2548` |
| DELETE `/api/pacientes/{paciente_id}/firmantes-biometricos/{firmante_id}` | eliminación lógica/física | JWT autenticado (sin rol local) | admin, ayudante, enfermeria, medico, sistemas | ROL_ESPECIFICO | middleware global + política de escritura | `backend/main.py:2590` |
| PUT `/api/pacientes/{paciente_id}/firmantes-biometricos/{firmante_id}` | actualización | JWT autenticado (sin rol local) | admin, ayudante, enfermeria, medico, sistemas | ROL_ESPECIFICO | middleware global + política de escritura | `backend/main.py:2276` |
| POST `/api/pacientes/{paciente_id}/firmantes-biometricos/{firmante_id}/enrolar` | creación/acción | JWT autenticado (sin rol local) | admin, ayudante, enfermeria, medico, sistemas | ROL_ESPECIFICO | middleware global + política de escritura | `backend/main.py:2462` |
| POST `/api/pacientes/{paciente_id}/firmantes-biometricos/{firmante_id}/reenrolar` | creación/acción | JWT autenticado (sin rol local) | admin, ayudante, enfermeria, medico, sistemas | ROL_ESPECIFICO | middleware global + política de escritura | `backend/main.py:2489` |
| GET `/api/pacientes/{paciente_id}/journey` | lectura | JWT autenticado (sin rol local) | ayudante, enfermeria, medico | ROL_ESPECIFICO | middleware global + política de lectura clínica | `backend/main.py:4208` |
| PUT `/api/pacientes/{paciente_id}/reingresar` | actualización | JWT autenticado (sin rol local) | admin, enfermeria, sistemas | ROL_ESPECIFICO | middleware global + política de escritura | `backend/main.py:2104` |
| GET `/api/pacientes/{paciente_id}/traslados` | lectura | JWT autenticado (sin rol local) | ayudante, enfermeria, medico | ROL_ESPECIFICO | middleware global + política de lectura clínica | `backend/main.py:4200` |
| POST `/api/pacientes/{pt_num}/firmar-biometrico-firmante` | creación/acción | middleware global | admin, ayudante, enfermeria, medico, sistemas | ROL_ESPECIFICO | middleware global + política de escritura | `backend/main.py:7261` |
| GET `/api/pacientes/{pt_num}/firmas` | lectura | middleware global | ayudante, enfermeria, medico | ROL_ESPECIFICO | middleware global + política de lectura clínica | `backend/main.py:7414` |
| GET `/api/usuarios` | lectura | admin, rh, sistemas | admin, rh, sistemas | ROL_ESPECIFICO | middleware global + dependencia local | `backend/main.py:3418` |
| POST `/api/usuarios` | creación/acción | admin, rh, sistemas | admin, rh, sistemas | ROL_ESPECIFICO | middleware global + política de escritura | `backend/main.py:3426` |
| DELETE `/api/usuarios/{usuario_id}` | eliminación lógica/física | sistemas | sistemas | ROL_ESPECIFICO | middleware global + política de escritura | `backend/main.py:3582` |
| PUT `/api/usuarios/{usuario_id}` | actualización | admin, sistemas | admin, sistemas | ROL_ESPECIFICO | middleware global + política de escritura | `backend/main.py:3468` |
| PUT `/api/usuarios/{usuario_id}/password` | actualización | admin, sistemas | admin, sistemas | ROL_ESPECIFICO | middleware global + política de escritura | `backend/main.py:3524` |
| GET `/api/verificar` | lectura | middleware global | — | PUBLICA | allowlist exacta método+ruta | `backend/main.py:8549` |
| GET `/api/verificar/documento` | lectura | middleware global | — | PUBLICA | allowlist exacta método+ruta | `backend/main.py:8549` |
| GET `/api/verificar/documento-estado` | lectura | middleware global | — | PUBLICA | allowlist exacta método+ruta | `backend/main.py:8262` |
| GET `/api/verificar/expediente` | lectura | middleware global | — | PUBLICA | allowlist exacta método+ruta | `backend/main.py:8549` |
| GET `/api/verificar/expediente/{pt_num}` | lectura | middleware global | — | PUBLICA | allowlist exacta método+ruta | `backend/main.py:8549` |
| GET `/api/verificar/pdf` | lectura | middleware global | — | PUBLICA | allowlist exacta método+ruta | `backend/main.py:9050` |
| GET `/api/verificar/pdf/documento` | lectura | middleware global | — | PUBLICA | allowlist exacta método+ruta | `backend/main.py:9050` |
| GET `/api/verificar/pdf/{pt_num}` | lectura | middleware global | — | PUBLICA | allowlist exacta método+ruta | `backend/main.py:9050` |
| GET `/assets` | lectura | middleware global | — | PUBLICA | allowlist exacta método+ruta | `route_policy.py:0` |
| GET `/camas` | lectura | middleware global | — | PUBLICA | allowlist exacta método+ruta | `route_policy.py:0` |
| GET `/captura` | lectura | middleware global | — | PUBLICA | allowlist exacta método+ruta | `route_policy.py:0` |
| GET `/docs` | lectura | middleware global | — | PUBLICA | allowlist exacta método+ruta | `route_policy.py:0` |
| GET `/docs/oauth2-redirect` | lectura | middleware global | — | PUBLICA | allowlist exacta método+ruta | `route_policy.py:0` |
| GET `/ehr` | lectura | middleware global | — | PUBLICA | allowlist exacta método+ruta | `route_policy.py:0` |
| GET `/ehr/paciente/{pt_num}/consentimiento-06` | lectura | middleware global | ayudante, enfermeria, medico | ROL_ESPECIFICO | middleware global + política de lectura clínica | `backend/main.py:12999` |
| POST `/ehr/paciente/{pt_num}/consentimiento-06` | creación/acción | middleware global | admin, ayudante, enfermeria, medico, sistemas | ROL_ESPECIFICO | middleware global + política de escritura | `backend/main.py:13235` |
| GET `/ehr/paciente/{pt_num}/consentimiento-07` | lectura | middleware global | ayudante, enfermeria, medico | ROL_ESPECIFICO | middleware global + política de lectura clínica | `backend/main.py:11245` |
| POST `/ehr/paciente/{pt_num}/consentimiento-07` | creación/acción | middleware global | admin, ayudante, enfermeria, medico, sistemas | ROL_ESPECIFICO | middleware global + política de escritura | `backend/main.py:11489` |
| GET `/ehr/paciente/{pt_num}/consentimiento-11` | lectura | middleware global | ayudante, enfermeria, medico | ROL_ESPECIFICO | middleware global + política de lectura clínica | `backend/main.py:12144` |
| POST `/ehr/paciente/{pt_num}/consentimiento-11` | creación/acción | middleware global | admin, ayudante, enfermeria, medico, sistemas | ROL_ESPECIFICO | middleware global + política de escritura | `backend/main.py:12372` |
| GET `/ehr/paciente/{pt_num}/consentimiento-15-ev` | lectura | middleware global | ayudante, enfermeria, medico | ROL_ESPECIFICO | middleware global + política de lectura clínica | `backend/main.py:12712` |
| POST `/ehr/paciente/{pt_num}/consentimiento-15-ev` | creación/acción | middleware global | admin, ayudante, enfermeria, medico, sistemas | ROL_ESPECIFICO | middleware global + política de escritura | `backend/main.py:12945` |
| GET `/ehr/paciente/{pt_num}/consentimiento-19` | lectura | middleware global | ayudante, enfermeria, medico | ROL_ESPECIFICO | middleware global + política de lectura clínica | `backend/main.py:12426` |
| POST `/ehr/paciente/{pt_num}/consentimiento-19` | creación/acción | middleware global | admin, ayudante, enfermeria, medico, sistemas | ROL_ESPECIFICO | middleware global + política de escritura | `backend/main.py:12656` |
| GET `/ehr/paciente/{pt_num}/egreso-voluntario-15` | lectura | middleware global | ayudante, enfermeria, medico | ROL_ESPECIFICO | middleware global + política de lectura clínica | `backend/main.py:12712` |
| POST `/ehr/paciente/{pt_num}/egreso-voluntario-15` | creación/acción | middleware global | admin, ayudante, enfermeria, medico, sistemas | ROL_ESPECIFICO | middleware global + política de escritura | `backend/main.py:12945` |
| POST `/ehr/paciente/{pt_num}/firmar-biometrico-firmante` | creación/acción | middleware global | admin, ayudante, enfermeria, medico, sistemas | ROL_ESPECIFICO | middleware global + política de escritura | `backend/main.py:7261` |
| GET `/ehr/paciente/{pt_num}/firmas-documento` | lectura | middleware global | ayudante, enfermeria, medico | ROL_ESPECIFICO | middleware global + política de lectura clínica | `backend/main.py:7701` |
| POST `/ehr/paciente/{pt_num}/formato-guardar-registro` | creación/acción | middleware global | REQUIERE_DECISION_FUNCIONAL | ROL_ESPECIFICO | bloqueada por defecto (403) | `backend/main.py:13391` |
| GET `/ehr/paciente/{pt_num}/pdf-consentimiento-02` | lectura | middleware global | ayudante, enfermeria, medico | ROL_ESPECIFICO | middleware global + política de lectura clínica | `backend/main.py:10993` |
| GET `/ehr/paciente/{pt_num}/pdf-consentimiento-04` | lectura | middleware global | ayudante, enfermeria, medico | ROL_ESPECIFICO | middleware global + política de lectura clínica | `backend/main.py:10409` |
| GET `/ehr/paciente/{pt_num}/pdf-consentimiento-06` | lectura | middleware global | ayudante, enfermeria, medico | ROL_ESPECIFICO | middleware global + política de lectura clínica | `backend/main.py:13046` |
| GET `/ehr/paciente/{pt_num}/pdf-consentimiento-07` | lectura | middleware global | ayudante, enfermeria, medico | ROL_ESPECIFICO | middleware global + política de lectura clínica | `backend/main.py:11301` |
| GET `/ehr/paciente/{pt_num}/pdf-consentimiento-08` | lectura | middleware global | ayudante, enfermeria, medico | ROL_ESPECIFICO | middleware global + política de lectura clínica | `backend/main.py:11600` |
| GET `/ehr/paciente/{pt_num}/pdf-consentimiento-11` | lectura | middleware global | ayudante, enfermeria, medico | ROL_ESPECIFICO | middleware global + política de lectura clínica | `backend/main.py:12191` |
| GET `/ehr/paciente/{pt_num}/pdf-consentimiento-15` | lectura | middleware global | ayudante, enfermeria, medico | ROL_ESPECIFICO | middleware global + política de lectura clínica | `backend/main.py:10699` |
| GET `/ehr/paciente/{pt_num}/pdf-consentimiento-19` | lectura | middleware global | ayudante, enfermeria, medico | ROL_ESPECIFICO | middleware global + política de lectura clínica | `backend/main.py:12473` |
| GET `/ehr/paciente/{pt_num}/pdf-consentimiento-43` | lectura | middleware global | ayudante, enfermeria, medico | ROL_ESPECIFICO | middleware global + política de lectura clínica | `backend/main.py:11905` |
| GET `/ehr/paciente/{pt_num}/pdf-egreso-voluntario-15` | lectura | middleware global | ayudante, enfermeria, medico | ROL_ESPECIFICO | middleware global + política de lectura clínica | `backend/main.py:12759` |
| GET `/ehr/paciente/{pt_num}/pdf-expediente-completo` | lectura | middleware global | ayudante, enfermeria, medico | ROL_ESPECIFICO | middleware global + política de lectura clínica | `backend/main.py:5408` |
| POST `/ehr/paciente/{pt_num}/verificar-integridad` | creación/acción | middleware global | admin, ayudante, enfermeria, medico, sistemas | ROL_ESPECIFICO | middleware global + política de escritura | `backend/main.py:7834` |
| GET `/firma-express` | lectura | middleware global | — | PUBLICA | allowlist exacta método+ruta | `route_policy.py:0` |
| GET `/health` | lectura | middleware global | — | PUBLICA | allowlist exacta método+ruta | `backend/main.py:367` |
| GET `/kh/estudios/{ptmt_num}/pdf` | lectura | middleware global | ayudante, enfermeria, medico | ROL_ESPECIFICO | middleware global + política de lectura clínica | `backend/main.py:4999` |
| GET `/login` | lectura | middleware global | — | PUBLICA | allowlist exacta método+ruta | `route_policy.py:0` |
| GET `/logo.png` | lectura | middleware global | — | PUBLICA | allowlist exacta método+ruta | `route_policy.py:0` |
| GET `/openapi.json` | lectura | middleware global | — | PUBLICA | allowlist exacta método+ruta | `route_policy.py:0` |
| POST `/pacientes/{pt_num}/firmar-biometrico-firmante` | creación/acción | middleware global | admin, ayudante, enfermeria, medico, sistemas | ROL_ESPECIFICO | middleware global + política de escritura | `backend/main.py:7261` |
| GET `/readiness` | lectura | middleware global | — | PUBLICA | allowlist exacta método+ruta | `backend/main.py:372` |
| GET `/redoc` | lectura | middleware global | — | PUBLICA | allowlist exacta método+ruta | `route_policy.py:0` |
| GET `/rh` | lectura | middleware global | — | PUBLICA | allowlist exacta método+ruta | `route_policy.py:0` |
| GET `/static/logo.png` | lectura | middleware global | — | PUBLICA | allowlist exacta método+ruta | `backend/main.py:294` |
| GET `/verificar` | lectura | middleware global | — | PUBLICA | allowlist exacta método+ruta | `backend/main.py:8549` |
| GET `/verificar/documento` | lectura | middleware global | — | PUBLICA | allowlist exacta método+ruta | `backend/main.py:8549` |
| GET `/verificar/expediente` | lectura | middleware global | — | PUBLICA | allowlist exacta método+ruta | `backend/main.py:8549` |
| GET `/verificar/expediente/{pt_num}` | lectura | middleware global | — | PUBLICA | allowlist exacta método+ruta | `backend/main.py:8549` |
| GET `/verificar/pdf` | lectura | middleware global | — | PUBLICA | allowlist exacta método+ruta | `backend/main.py:9050` |
| GET `/verificar/pdf/documento` | lectura | middleware global | — | PUBLICA | allowlist exacta método+ruta | `backend/main.py:9050` |
| GET `/verificar/pdf/{pt_num}` | lectura | middleware global | — | PUBLICA | allowlist exacta método+ruta | `backend/main.py:9050` |
| GET `/websdk.client.min.js` | lectura | middleware global | — | PUBLICA | allowlist exacta método+ruta | `route_policy.py:0` |
| GET `/{full_path:path}` | lectura | middleware global | cualquier identidad activa | AUTENTICADA | middleware global | `backend/main.py:13440` |

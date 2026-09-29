---
tags: [hes/seguridad, hes/backend, hes/frontend, tipo/modulo]
tipo: modulo
modulo: permisos
actualizado: 2026-09-29
relacionados:
  - "[[API-Endpoints]]"
  - "[[Frontend]]"
  - "[[Database]]"
---

# Permisos de acceso por usuario

`backend/access_catalog.json` es el registro compartido de roles y áreas. Lo
consumen el backend, la navegación, las pestañas y el editor de usuarios.
Incluye Dashboard, Historial Global, Pacientes, Alta de Médicos, Directorio,
Escaneos Diarios, Catálogos, Auditoría, Usuarios y permisos, Respaldos, Agenda,
Censo de Camas, Expediente Clínico, Captura de Enfermería, Firmas pendientes y Firmas del área.

RH tiene un límite de cinco áreas: Dashboard, Historial Global, Alta de Médicos,
Directorio y Escaneos Diarios. Es posible desmarcarlas individualmente. RH no
administra usuarios, asigna formatos ni entra en módulos clínicos. El rol de
Sistemas se ofrece separado de Administrador; también aparecen Dirección,
Trabajo Social, Enfermería, Nutrición, Limpieza, Laboratorio y Banco de Sangre.

## Asignación y compatibilidad

- `usuarios.permisos_modulos` conserva JSON. `null` usa los valores sugeridos
  del rol para cuentas anteriores; un objeto explícito es una lista completa:
  ausente/false significa denegado, incluso para admin. No se fusiona con los
  valores del rol. Las claves históricas `admin` y `rh` se expanden a sus áreas,
  siempre respetando los límites del rol y una denegación explícita por área.
- El editor permite crear y editar usuarios, marcar/quitar áreas y formatos,
  buscar formatos y aplicar sugerencias del rol. Usuarios/Respaldos requieren
  admin o sistemas; las firmas médicas siguen requiriendo identidad médica.
- `formatos_permitidos=[]` significa ningún formato; `null` conserva la
  compatibilidad de cuentas anteriores. Al crear usuarios se guarda una lista
  explícita. Al editar una cuenta histórica se muestran los formatos actuales
  seleccionados; guardar fija esa selección.
- `formatos_firma_permitidos` es otra lista explícita. Sólo acepta formatos que
  declaran la firma especial del área del usuario. La pantalla muestra su área
  como “(requiere firma de: …)” y agrega formatos nuevos cuando se incorporan al
  catálogo. Concede consulta y firma de esos documentos en `firmas_area`, sin
  abrir el expediente completo. Banco de Sangre sólo tiene disponible ese módulo.
  La asignación de firma existente habilita su bandeja si la clave del módulo
  aún no existe; una denegación explícita `firmas_area:false` prevalece.
  Esta excepción de compatibilidad no asigna otros módulos ni formatos.
  La cuenta también puede firmar desde la sesión clínica del operador.
- `GET /api/auth/me` publica los permisos efectivos actuales. AuthContext los
  consulta con TanStack Query al ingresar y cada minuto. La API revalida la BD
  en cada solicitud: quitar un permiso bloquea inmediatamente nuevas consultas.
- No se agregan columnas ni se modifica automáticamente ningún usuario real.

## Bandeja compartida por área

`/firmas-area` consulta registros existentes de Vertical mediante el catálogo,
incluidos los creados antes de habilitar la bandeja. Todos los usuarios con rol
y permiso para el formato ven el mismo pendiente. No se asignan copias personales.
Una firma vigente lo retira de pendientes y conserva firmante/fecha en el
historial del área; una modificación clínica vuelve a requerir firma y mantiene
la anterior. Se comprueban snapshot, versión y registro de origen.

Desde la bandeja sólo se permite firmar con la cuenta propia. Desde EHR, un
operador clínico autorizado puede seleccionar a otro firmante enrolado; su huella
identifica a ese firmante sin cerrar la sesión del operador. El bloqueo transaccional
por documento y área vuelve a comprobar el estado: dos capturas concurrentes no
pueden registrar dos firmas vigentes, incluso usando aliases o la ranura heredada 0.

La bandeja se pagina y actualiza cada 20 segundos. Una caída de Vertical se muestra
como error, nunca como lista vacía confirmada. Cada API revalida permisos y el
PDF se limita al formato autorizado y un `mrnum` positivo explícito.

Validación 2026-09-29: 25 pruebas de `test_area_signatures.py` aprobadas en
PostgreSQL efímero dedicado, además de las suites de permisos, biometría y
autorización P0. Incluyen sesión médica conservada, usuario distinto del slot,
dos firmas simultáneas (una se guarda y la otra recibe 409), aliases, registros
repetidos, paginación, revocación e historial por versión. Frontend: permisos,
lint y build aprobados; navegador con datos sintéticos en escritorio/móvil,
actualización por firma de otro usuario y error de origen. La lectura física del
dispositivo no se simula como verificación real; queda por probar en la estación.

## Frontera de autorización

`GlobalAuthMiddleware` resuelve la ruta exacta, incluidos routers FastAPI
incluidos y aliases `/ehr`, consulta `access_control.route_modules` y aplica
permisos vigentes. Rutas nuevas sin política fallan con 403. Toda escritura
también necesita su entrada en `WRITE_ROLE_POLICIES`. Las restricciones de
identidad médica, impersonación y reapertura/autorización permanecen vigentes.
`require_role` sólo acepta el permiso de área después de la comprobación global;
su invocación fuera de ese contexto conserva la comprobación de rol.

Los permisos de formatos se verifican en lectura, PDF, edición universal,
firmas y emisión de challenge. Sus aliases se normalizan al mismo controlador
clínico. El dashboard compuesto elimina cuerpos/historiales de formatos no
permitidos; las listas de firmas y auditoría clínica también se filtran.
El PDF integral exige acceso a todos los formatos activos, además del compilado.
El cotejo público por QR opaco conserva su contrato de verificación pública.
Los campos `consentimiento_*` e `historial_*` se resuelven contra el mismo
catálogo; un campo nuevo sin formato registrado se excluye de cuentas con
selección explícita, hasta completar su registro.

## Incorporación de áreas y formatos

1. Área nueva: registrar una entrada en `access_catalog.json`, asociar sus
   endpoints en `route_modules` y conectar su pantalla. El selector de permisos
   y sus grupos se actualizan desde ese mismo registro. No crear otra lista de
   permisos en un formulario. Las cuentas con selección explícita no reciben
   áreas nuevas automáticamente.
2. Formato nuevo: registrar su definición activa en
   `backend/format_catalog.py` (catálogo compartido por EHR y permisos). Su
   `url_pdf` también determina las rutas de lectura/escritura del formato.
   Los formatos activos de `catalogo_formatos` se integran al selector mediante
   `routers.catalogos.available_formats`, sin repetir opciones en React.
   Deben existir sus motores/controladores y las políticas de escritura/firma
   correspondientes antes de activar un formato; descubrirlo no concede acceso.
3. Para rutas de documento con nombres no derivados de `url_pdf`, registrar el
   alias en `format_for_route`. Conservar controles de formato cuando una ruta
   devuelve varios documentos juntos.

## Contraseñas y verificación

`password_policy.py` exige al menos 8 caracteres, mayúscula, minúscula, número
y símbolo (un espacio no cuenta como símbolo). Se usa en alta, reset, cambio
propio, bootstrap y seed. El cambio obligatorio tras reset se conserva.

Pruebas: `backend/tests/test_user_permissions.py` (PostgreSQL TEST) y
`frontend/test/permissions.test.js`. La suite cubre los cinco accesos de RH,
rechazos directos, revocación con JWT vigente, permisos vacíos/malformados,
catálogo dinámico, contraseñas de ocho caracteres y formatos por alias.

Validación local del 2026-09-28: 104 pruebas de permisos, autorización P0,
biometría y seguridad de preproducción aprobadas (más 10 subtests); 48 pruebas
de frontend, `npm run lint:runtime` y `npm run build` aprobados. La revisión
adicional de `test_signature_workflow.py` detectó ocho fallos en sus pruebas
existentes de perfiles de firmantes: siete esperan `firma.perfil_firmante` y
uno espera `main.resolve_document_signer_role`, contratos que no están
implementados en el flujo actual. No se modificó esa política clínica como
parte de la asignación de accesos. Verificación visual con datos ficticios,
sin modificar cuentas ni datos clínicos reales.

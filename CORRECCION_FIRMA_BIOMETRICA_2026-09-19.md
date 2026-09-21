# Corrección dirigida del circuito de firma biométrica

Fecha: 2026-09-19, hora local. Continuación autorizada de
`REVISION_FIRMA_Y_EXTENSIBILIDAD_2026-09-19.md`.

## Resultado y alcance

Se reforzó el circuito existente, sin sustituir DigitalPersona, ECDSA médica,
la caché de sesión Vertical ni su operación nativa `SignRecord`. No se conectó
esta ejecución a KH_HE para escribir/probar; ERP, SDK y TSA se sustituyeron por
adaptadores sintéticos. No se borraron expedientes, huellas ni llaves históricas.
No hay migración nueva, despliegue, commit ni push. Se preservaron los cambios
preexistentes del árbol de trabajo.

Cada médico conserva su identidad, huella y llave propias. Al firmar, la
identidad solicitada debe coincidir con la sesión médica, el resultado biométrico
y el autor asignado al documento. El payload incorpora ID, nombre, cédula y
`key_id` del médico verificado, no datos de identidad elegidos por el navegador.
El alta/enrolamiento médico sigue siendo un procedimiento controlado por los
roles autorizados; no se habilitó autorregistro sin verificación de identidad.

## Correcciones verificadas

| Hallazgo | Reproducción previa | Corrección | Regresión permanente | Resultado técnico |
|---|---|---|---|---|
| RF-01: sellos de otra ranura/versión | Confirmada; tests negativos fallaron antes de corregir | Ranura exacta, incluido 0; cotejo de snapshot, versión, origen y evidencia vigente para indicadores/PDF | `test_slot_zero_cannot_borrow_slot_seven`, `test_changed_content_invalidates_current_patient_signature` | Corregido en pruebas |
| RF-02: firmar la última fila Vertical en vez de la seleccionada | Confirmada; test negativo falló antes de corregir | Destino derivado del snapshot ya validado; urgencias conserva fila y subranura elegidas | `test_urgent_sync_uses_selected_row_not_latest`, `test_legacy_sync_without_exact_row_requires_reconciliation` | Corregido en pruebas |
| RF-03: cierre de consentimiento con sólo paciente | Confirmada; test negativo falló antes de corregir | Autorizador más dos testigos registrados distintos; backend e interfaz controlan cierre. Notas médicas no heredan ese requisito | `test_consent_needs_both_witnesses_for_closure`, `test_two_witness_roles_cannot_be_the_same_registered_person`, `test_medical_note_does_not_require_patient_and_witnesses` | Corregido en pruebas |
| RF-04: cambiar automáticamente tutor a representante/testigo | Confirmada mediante selector anterior | Rol persistido, selección por ID, T1/T2 por rol y sin elegir paciente incapacitado por ausencia de representante | `frontend/test/biometricSigners.test.js` | Corregido en pruebas |
| RF-05: formato desconocido convertido en nota de urgencias | Confirmada; test negativo falló antes de corregir | Alias conocidos o nombre exacto de tabla descubierta; código desconocido se rechaza | `test_unknown_format_must_not_become_an_urgent_note` | Corregido en pruebas |

Los tests backend de esta tabla viven en
`backend/tests/test_signature_workflow.py`. Las sondas diagnósticas de la revisión
anterior esperaban el comportamiento defectuoso y no deben usarse como aceptación.

Otras correcciones dentro del mismo circuito:

- Una sesión médica puede operar el lector para paciente/tutor/familiar/testigo
  sin que su propia identidad reemplace al firmante esperado. La auditoría
  identifica al operador médico sin usar su ID como FK de la tabla Usuarios.
- Challenge de 120 segundos vinculado también al hash del contenido autoritativo.
  Cambiar documento durante la captura o antes de reintentar Vertical se rechaza;
  no se vuelve a usar la captura para otro acto. Se conserva bloqueo anti-replay.
- Los modales filtran por acción, paciente, documento, ranura e identidad; cancelar,
  cambiar selección o cerrar invalida respuestas tardías. Las consultas de estado
  se centralizan en TanStack Query y los familiares conservan su rol registrado.
- Firma del paciente usa el bloqueo transaccional por documento/rol y las
  restricciones existentes de unicidad. CONTACTO no autoriza consentimientos,
  tampoco por una evidencia histórica previa.
- Vertical exige médico inequívoco (cédula, o nombre exacto cuando no hay cédula)
  y código de autorización real. Se eliminaron médico/PIN por defecto y coincidencia
  parcial. Si falta correspondencia, debe corregirse el perfil; no se firma a
  nombre de un tercero.
- Se conserva la llamada nativa SignRecord. Tras su confirmación positiva se
  comprueba `SignedBy`, estado SG y `ESignature` real en la fila/paciente exactos.
  No se fabrica cadena `FIRMADO_BIOMETRICAMENTE`, ni se hace UPDATE manual para
  simular el éxito. Presencia de cadena significa persistencia nativa, no una
  verificación criptográfica independiente del algoritmo propietario de Vertical.
- La proyección clínica de filas Vertical generales excluye estado/cadena de
  firma y `ModifiedOn`/`ModifiedBy`; la versión es su hash. Un cambio administrativo
  al firmar no invalida firmas previas; un cambio de contenido sí. Los snapshots
  antiguos no se migran ni reescriben: si no corresponden, se conservan históricos.

## Evidencia de ejecución

| Comprobación | Resultado |
|---|---|
| Suite completa PostgreSQL TEST, incluidas AF-01..AF-11 | 197 passed, 10 subtests passed; 329 warnings; 96.11 s |
| Última regresión CONTACTO y repetición del circuito completo específico | 25 passed, 62 warnings; 12.38 s |
| Agente biométrico `npm test` | 26 passed, adaptador físico sintético |
| Frontend `node --test frontend/test/*.test.js` | 19 passed |
| Frontend `npm run lint:runtime` y `npm run build` | Exit 0; 725 módulos; advertencia por tamaño de chunks |
| Python compileall / node --check del agente / TypeScript móvil local | Exit 0 |
| Alembic upgrade limpio y check en PostgreSQL TEST | PASS; sin operaciones nuevas de migración detectadas |
| Secret scan existente | 300 archivos; 0 hallazgos de alta confianza; no es análisis exhaustivo de secretos |
| npm audit producción web/agente | 0 vulnerabilidades reportadas |
| npm audit producción móvil | 14 moderadas; 0 altas/críticas; sin cambios de dependencias |
| pip-audit requisitos backend | `ecdsa 0.19.2`, PYSEC-2026-1325, reportado dos veces; sin versión corregida indicada; aviso ya documentado |

La última regresión CONTACTO se añadió después de la suite global de 197; se
reporta su ejecución por separado para no atribuirle una pasada global inexistente.
La suite aislada recrea únicamente PostgreSQL local con sufijo `_test` y elimina
sus datos sintéticos al terminar. El build regeneró `frontend/dist/`.
`git diff --check` señala espacios finales en el diff acumulado del árbol;
no se aplicó una limpieza cosmética masiva a cambios anteriores.

## Incorporación de nuevos módulos y formatos

La firma común se puede reutilizar; **no se declara que farmacia, laboratorio,
imagenología o los más de 100 formatos pendientes ya estén implementados**.
Cada incorporación necesita código/alias y fuente/PK inequívocos, cargador del
contenido completo, política de firmantes por acto, representación PDF y pruebas
del circuito. El descubrimiento de una tabla no aprueba por sí solo su política
clínica. La regla actual distingue los consentimientos reconocidos/egreso voluntario
de las notas; actos nuevos y personal no médico requieren su política explícita.
No deben reutilizar identidad, huella o llave de un médico para enfermería u otros
profesionales.

## Validaciones pendientes antes de liberar

1. Prueba controlada con dos perfiles médicos reales: enrolamiento supervisado,
   firma correcta con cada uno y rechazo de la huella ajena; verificar nombre,
   cédula, llave y atribución correspondiente en ambos sistemas.
2. Prueba física paciente, tutor/representante/familiar y dos testigos; huella
   incorrecta, lector desconectado, cancelación, expiración y cambio de documento.
   Confirmar identidad y facultad de representación, no sólo lectura del dedo.
3. Con responsable de Vertical, confirmar columnas PR/credenciales, respuesta
   real SignRecord y cadena/QR de cada familia de formatos, incluida urgencias
   con varios médicos/subranuras por fila. Comprobar reintento tras caída de red
   sin sobrescribir la atribución de otro médico. No se ejecutó este gate externo.
4. Revisar correspondencia de formatos actuales individualmente y resolver
   operaciones históricas pendientes sin PK/digest antes de automatizar reintentos.
5. Validación institucional/jurídica de firma, privacidad, conservación,
   representación y contingencias. La evidencia del paciente/responsable sigue
   siendo `BIOMETRIC_EVIDENCE_V1`: no se creó una FEA personal para cada paciente.
   Tampoco se certifica ECE/NOM por tener pruebas verdes.

Referencias oficiales consultadas en la revisión:
[NOM-004, numerales 5.10, 10.1.1.10 y 10.2.3.8](https://dof.gob.mx/nota_detalle_popup.php?codigo=5272787)
y [NOM-024, seguridad y evaluación de conformidad](https://dof.gob.mx/nota_detalle_popup.php?codigo=5280847).
La corrección técnica no constituye liberación clínica ni dictamen normativo.

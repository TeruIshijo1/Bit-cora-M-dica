# Revisión de firma biométrica y extensibilidad

Fecha: 2026-09-19. Alcance: solicitud de revisar firmas de médicos, pacientes,
familiares/responsables y capacidad de incorporar nuevos formatos/módulos.

## Dictamen

**No es posible afirmar que todo está funcional ni que cumple integralmente la
NOM. Hay defectos reproducidos posteriores a la captura biométrica.** El cierre
de adquisición AF-02 no demuestra por sí solo la corrección del acto de firma,
del documento mostrado, del cierre del consentimiento o de la sincronización.

Esta pasada es una revisión: no modifica lógica de aplicación, políticas de
firma ni migraciones. No hace push, despliegues ni conexiones a KH_HE operativo.
Las pruebas usan PostgreSQL local TEST y sustitutos sintéticos del ERP/lector.
No se repitió una ceremonia física de firma con médico, paciente y testigos.

## Hallazgos reproducidos

Todos permanecen **NO RESUELTOS** en esta pasada.

| ID / prioridad | Evidencia | Consecuencia y corrección requerida |
|---|---|---|
| RF-01 / Alta — documento y versión | `backend/main.py:7411`: el selector de firmas sólo filtra ranura si es mayor que cero. Prueba: existe únicamente firma de paciente en ranura 7; consultar ranura 0 responde `paciente_firmado=true`. En ranura exacta tampoco llama a la carga de contenido vigente ni verifica versión. | El resumen y los consumidores PDF de este helper pueden reutilizar firmas de otro registro o contenido antiguo. Exigir documento/ranura exactos, incluso cero, versión y hash comunes; separar histórico de vigente. La verificación pública más estricta no corrige este otro camino. |
| RF-02 / Alta — destino de firma médica | `backend/clinical_signing.py:404` carga la evolución seleccionada; `backend/main.py:1084` resuelve `MR_NE_URG` consultando siempre la última fila. Prueba con ERP simulado: snapshot `MR_NE_URG:11:1`, destino de sincronización `MR_NE_URG:99`. | Al firmar una evolución anterior, la ECDSA puede cubrir una fila y la confirmación Vertical otra. Resolver una sola referencia autoritativa y usarla en snapshot, validación de autoría y operación durable. La prueba ejercita ambos resolutores reales, no un write externo real. |
| RF-03 / Alta — cierre sin testigos | `backend/main.py:7651` calcula `listo_para_cierre_medico` sólo con el sello del paciente. Prueba de consentimiento 02: ambos testigos ausentes, listo=true. `BiometricPatientSignModal.jsx:179,490,498` los llama opcionales; `FirmantesEpisodioModal.jsx:524` llama opcional al segundo. | No representa los requisitos del consentimiento informado. Política por clase de documento, con comprobación backend; no imponer los mismos firmantes a toda nota médica. Las excepciones de urgencia necesitan procedimiento explícito, no omisión silenciosa. |
| RF-04 / Media — rol automático contradictorio | Ejecución del selector real de `BiometricPatientSignModal.jsx:98,105`: TUTOR se envía como REPRESENTANTE_LEGAL; después de autorización un representante puede seleccionarse como TESTIGO_1. `backend/main.py:666` rechaza roles distintos al persistido con 409. | Una huella correcta puede fallar por la interfaz, no por el lector. Conservar identidad/rol persistidos en todas las selecciones automáticas; seleccionar testigos reales por rol, no por posición. Revisar además familiares/contactos: el selector de representantes sólo permite TUTOR/REPRESENTANTE_LEGAL, aunque otros caminos aceptan FAMILIAR/CONTACTO. Un contacto no debe adquirir representación legal automáticamente. |
| RF-05 / Alta — formato desconocido | `backend/vertical_signer.py:261`: fallback a `MR_NE_URG`. Prueba: `FUTURO-LAB-9999` se resuelve como una nota de urgencias, en lugar de rechazarse. El cargador de documentos utiliza ese resolver. | No es seguro incorporar más de cien formatos confiando en inferencias. Registro explícito de códigos/alias, almacenamiento, PK y versión; formato no registrado debe quedar bloqueado. |

### Brechas adicionales identificadas en código

1. **Huella y firma electrónica no son sinónimos.** El médico tiene snapshot
   `CANONICAL_V2` y ECDSA. Pacientes/tutores/testigos tienen
   `BIOMETRIC_EVIDENCE_V1`, snapshot y hash, pero el campo `sello_digital` es un
   identificador aleatorio `EVIDENCIA_BIOMETRICA_NO_FEA:<uuid>`
   (`backend/main.py:7265`), no una firma asimétrica personal. La base sí protege
   el snapshot contra UPDATE/DELETE; no se afirma que carezca de evidencia.
   Falta acordar el modelo probatorio aplicable y cómo se acredita intención,
   identidad, representación y aceptación del contenido. No se debe cambiar la
   etiqueta a FEA para aparentar equivalencia, ni asumir que toda firma
   electrónica de paciente necesariamente debe ser FEA. Tampoco una ECDSA
   médica aislada demuestra todos los requisitos jurídicos de FEA.
2. **La autorización de captura no fija el contenido mostrado.**
   `backend/biometric_security.py:313` liga acción, paciente, código y ranura,
   pero no versión/hash del documento. Los endpoints cargan el contenido al
   firmar. Una actualización entre visualización/captura y firma no tiene una
   precondición de versión revisada por el firmante. Es una brecha de diseño
   observada, no un ataque concurrente end-to-end ejecutado en esta revisión.
   Se requiere preparación de un snapshot, aceptación explícita y rechazo de
   cambios antes del cierre, también para la sincronización diferida.

La leyenda `Validez legal NOM-004-SSA3-2012` de la pantalla no debe utilizarse
como prueba de conformidad. Ninguno de estos hallazgos exige debilitar matching,
aceptar RAW del navegador o eliminar controles anti-replay.

## Contraste normativo

La NOM-004, numeral 5.10, admite firmas electrónicas/digitales sujetas a las
disposiciones jurídicas aplicables; no convierte una lectura dactilar aislada
en una firma válida. Los numerales 10.1.1.8–10 exigen los firmantes del
consentimiento, incluidos dos testigos; 10.2.3.8 también contempla dos en egreso
voluntario. El numeral 9.2.8 es relevante para firma del personal que informa
estudios de laboratorio/imagenología. Fuente: [NOM-004, DOF](https://dof.gob.mx/nota_detalle_popup.php?codigo=5272787).

La NOM-024, apartados 6.6 y 7, trata seguridad, documentos inalterables,
autenticación/autorización y evaluación de conformidad. Pasar pruebas unitarias
no acredita ese proceso. Fuente: [NOM-024, DOF](https://dof.gob.mx/nota_detalle_popup.php?codigo=5280847).

Ambas aparecen vigentes en el catálogo oficial consultado:
[NOM-004](https://platiica.economia.gob.mx/normalizacion/nom-004-ssa3-2012/) y
[NOM-024](https://platiica.economia.gob.mx/normalizacion/nom-024-ssa3-2012/).
Este contraste técnico no sustituye revisión jurídica/institucional del modelo
de firma, contingencias, privacidad y representación.

## Pruebas ejecutadas

| Comprobación | Resultado de esta pasada |
|---|---|
| Suite PostgreSQL existente | 173 passed, 10 subtests passed, 286 warnings; 82.36 s |
| Agente biométrico `npm test` | 26 aprobadas; adaptador de lector sintético |
| Frontend `node --test test/*.test.js` | 15 aprobadas |
| `npm run lint:runtime` | exit 0 |
| `npm run build` | exit 0, 724 módulos; advertencia de tamaño de chunks |
| Reproducciones backend adicionales | 5 comportamientos defectuosos confirmados + 1 regresión existente = 6 passed; 4.20 s |
| Reproducciones frontend adicionales | 2 selecciones de rol contradictorias confirmadas ejecutando el selector extraído mediante AST |

**Los “passed” de las sondas diagnósticas confirman que el defecto existe; no
son pruebas de aceptación de una corrección.** La suite verde existente no
cubre estas combinaciones.

Reproducciones locales en `scratch/revision_firma_20260919/` (ignorado por Git):

```powershell
.\backend\venv\Scripts\python.exe backend/scripts/run_local_postgres_tests.py -- backend/tests/test_af_remediation_regressions.py::test_af01_public_verification_rejects_enumerable_patient_folio scratch/revision_firma_20260919/probe_backend.py -s --disable-warnings
node scratch/revision_firma_20260919/probe_frontend.mjs
```

El helper de PostgreSQL valida host local y nombre `_test`; recrea el esquema
de esa base dedicada antes/después. Se eliminaron únicamente datos sintéticos
de pruebas mediante el aislamiento estándar. No se modificaron expedientes
operativos. El build regeneró `frontend/dist/`.

## Base necesaria para los nuevos módulos y formatos

No se recomienda duplicar estos flujos para cada formato. Primero corregir
RF-01 a RF-05 y convertir las reproducciones en regresiones permanentes con
expectativas seguras. Después incorporar un contrato común, sin reescritura
general del proyecto:

| Pieza | Condición de incorporación |
|---|---|
| Registro explícito de documentos | Código/alias, módulo, versión de esquema, fuente/PK, cargador autoritativo y renderizador. Sin fallback semántico. |
| Política de firma por acto | Roles y número de firmantes, capacidades/representación, propósito y reglas de sustitución/contingencia. Incluir profesionales no médicos cuando corresponda. |
| Documento preparado para firma | ID estable + versión + hash del contenido aceptado; todas las firmas de un acto deben referirse a ese mismo contenido. |
| Evidencia y verificación | Snapshot inmutable, prueba de autenticación vinculada al acto, custodia de llaves según modalidad, auditoría y estados separados: firmado, completo, TSA y sincronizado. |
| Adaptador de módulo | Farmacia, laboratorio e imagenología aportan sus propios datos y reglas; no se hacen pasar por una nota `MR_NE_URG`. TanStack Query y componentes compartidos en frontend. |
| Pruebas contractuales | Documento equivocado, cambio de versión, doble firma, roles, representación, testigos, reintentos, caída del lector/ERP/TSA y consulta histórica. Ejecutarlas para cada alta de formato. |

No se validaron individualmente todos los formatos actuales ni los futuros aún
no implementados. Para liberar la operación real faltan, además de corregir
estos defectos, las pruebas físicas de aceptación por rol y estación y la
validación institucional correspondiente. No se declara listo para liberación
el circuito completo solicitado.

# VERIFICACIÓN Y REMEDIACIÓN FINAL DIRIGIDA — AF-01 A AF-11

Fecha: 2026-09-17. Referencias: `AUDITORIA_FINAL_PREPRODUCCION_ASTRA.md` y `REMEDIACION_FINAL_AF01_AF11.md`.

**Resultado: 10 CERRADO; AF-02 REABIERTO, con el ataque bloqueado de forma segura. Piloto: NO LISTO. Paso a gates externos de go-live: NO.**

La remediación anterior no acredita frescura biométrica: una imagen archivada que la instancia del servicio no había procesado obtuvo una attestation HMAC válida bajo un challenge y una adquisición nuevos. Se corrigió la frontera insegura para que no emita attestations de RAW aportado por el cliente. Esto bloquea también la captura legítima actual; falta implementar una adquisición de origen confiable. No se declara cerrado AF-02 por una denegación general.

El alcance fue exclusivamente AF-01..AF-11. No se hizo auditoría general, refactor cosmético, cambio de dependencias, commit, push ni despliegue. Se conservaron los cambios previos del usuario. El código de aplicación editado en esta pasada es únicamente `biometric-service/server.js`; se ajustaron su regresión y cuatro notas para documentar la limitación real.

## Método y límites de la evidencia

- PostgreSQL local dedicado TEST, protegido por nombre `_test` y `APP_ENV=test`. Cada sesión de pytest recreó el esquema con Alembic; no se utilizó la base operativa ni SQL Server productivo.
- Las fronteras ERP/Vertical/TSA/lector usaron datos o respuestas sintéticos. HTTP, JWT, roles, HMAC, consumo de challenges, PostgreSQL, ECDSA y verificación CMS se ejecutaron realmente donde se indican. Los fixtures HMAC utilizados para ejercitar AF-03/05 son exclusivos de TEST y no representan una captura física disponible en el producto.
- Se ejecutó la suite inicial antes de editar: **161 passed, 193 warnings, 10 subtests passed**. Las tres pruebas iniciales del servicio también pasaban. Eso no detectaba el caso AF-02 de RAW antiguo nunca visto por el proceso.
- Para AF ya cerrados se ejecutaron pruebas existentes y sondas en `scratch/af_final_verification/`; no se modificó su implementación ni sus pruebas permanentes.
- Los 21 handlers de frontend se extrajeron del AST de `PatientDashboard.jsx` y se ejecutaron en VM con estado React y transporte simulados. Se comprobó que cada uno alcanzara su solicitud y su rama de respuesta 202; no es una prueba visual de navegador.

## Tabla de verificación final

| AF | REPRODUCCIÓN ORIGINAL | RESULTADO ANTES DE ESTA PASADA | ¿SE MODIFICÓ CÓDIGO? | CAMBIO REALIZADO | PRUEBA FINAL | ESTADO |
|---|---|---|---|---|---|---|
| AF-01 | Anónimo por folio enumerable; `limpieza` leyendo expediente y firmas. | Folio: 404 sin PHI; expediente/firmas: 403. El portal exige identificador opaco registrado. | NO | Ninguno. | Regresiones AF-01; un `v1_*` registrado llega al estado público en la sonda AF-04 y un folio no lo sustituye. | **CERRADO** |
| AF-02 | RAW archivado + challenge nuevo + sesión + adquisición nueva; comprobar uso único y orden temporal. | **HTTP 200, attestation emitida, HMAC válida, ningún lector utilizado** cuando el RAW no estaba en la memoria de digests. | SÍ | `/extract-fmd` consume la adquisición contextual válida y responde **503 TRUSTED_CAPTURE_UNAVAILABLE**, sin extracción ni HMAC; retira atestación y memoria de digests inseguras. | Mismo ataque: 503, sin attestation. Nueva prueba permanente falla antes y pasa después. Sin adquisición: 422; reuso: 409. Backend rechaza adquisición anterior al challenge (401) y reutilización en otro challenge (unicidad PostgreSQL). Falta captura confiable operativa. | **REABIERTO** |
| AF-03 | Un único RH: reenrolamiento → rotación FEA → login médico. | La cadena se corta por separación de actores. | NO | Ninguno. | HTTP real con HMAC/challenges reales y matcher por igualdad: reenrolar 200 → rotar con el mismo RH 403 → login 423; llave original conservada. Regresión existente cubre segundo actor. | **CERRADO** |
| AF-04 | Firma ECDSA slot 1; consultar 999; `firma_id` ajeno; UPDATE canónico; contenido operativo posterior distinto. | Selección exacta, trigger e identificación histórica funcionan. | NO | Ninguno. | Firma ECDSA real: slot 999 devuelve `SIN_FIRMA`/`valido=false`; ID ajeno 409; UPDATE rechazado y bytes originales conservados; consulta del contenido cambiado indica histórico y `documento_vigente=false`. | **CERRADO** |
| AF-05 | Dos POST simultáneos, mismo paciente/formato/slot/documento, challenges e idempotency keys diferentes. | Una sola firma ACTIVA. | NO | Ninguno. | Sonda HTTP con barrera, HMAC y dos challenges consumidos realmente: **[200, 200], ACTIVA=1**. La segunda firma serializada reemplaza la vigencia anterior; se conserva evidencia histórica. Unicidad también pasa bajo INSERT concurrente. | **CERRADO** |
| AF-06 | Dispatcher durable + Vertical `HTTP 200 / {}`. | El adaptador rechaza confirmación vacía. | NO | Ninguno. | Se alcanzó la respuesta HTTP sintética a través del dispatcher/adaptador reales: cero UPDATE de firma y estado PostgreSQL **FAILED**, nunca `SYNCED`. | **CERRADO** |
| AF-07 | Formato 15 EV: 202, `success=false`, `state=RETRYABLE_ERROR`; handlers del helper común. | Respuesta tratada como pendiente. | NO | Ninguno. | **21 handlers reales ejecutados**, incluido `handleSaveModal15EV`: todos alcanzan una solicitud, muestran sincronización pendiente, sin `successMsg` ni texto de guardado exitoso en SQL Server. También pasan los 2 tests permanentes del helper. | **CERRADO** |
| AF-08 | Misma Idempotency-Key: paciente/payload A y luego B. | Conflicto detectado; no reutiliza resultado ajeno. | NO | Ninguno. | Endpoint real de egreso voluntario: A=200; B=**409 IDEMPOTENCY_KEY_CONFLICT**; sólo A alcanza el adaptador externo. Regresiones de fingerprint también pasan. | **CERRADO** |
| AF-09 | GET firmas de paciente inexistente en PostgreSQL y GET PDF; comparar persistencia. | No crea paciente ni QR ni deja PDF. | NO | Ninguno. | Ambos GET=200; **conteos de todas las tablas PostgreSQL y hashes de archivos persistentes** en generados/static/private_storage iguales antes/después. PDF sintético realmente servido; sus bytes y QR no quedan persistidos. | **CERRADO** |
| AF-10 | TimeStampResp/CMS/root TEST/EKU/nonce/imprint válidos, PKIStatus granted; luego TSA pendiente. | TSA válida reconocida y pendiente visible. | NO | Ninguno. | `test_af10_complete_timestamp_response_with_granted_status_is_verified`: **TSA_VERIFICADO** con CMS/trust reales TEST. `test_af10_summary_exposes_pending_tsa_without_claiming_complete`: `tsa_status=TSA_PENDIENTE`, nunca verificación completa. También pasan vectores TSA negativos. | **CERRADO** |
| AF-11 | Cambio de rol, ingreso, cambio de cama; cerrar sesión, consultar y atacar auditoría. | Eventos durables. | NO | Ninguno. | HTTP: cambio de rol, ingreso y **traslado real BED-A→BED-B**, logout, cierre y reapertura de sesión DB. Tres eventos, actor real/efectivo `admin:<id>` y `usuario_id` correctos, acciones exactas. UPDATE/DELETE rechazados por PostgreSQL. La regresión original de limpieza de cama también pasa. | **CERRADO** |

## AF-02: evidencia y trabajo que sigue pendiente

La sonda `af02-original-attack.cjs` ejecuta el mismo cuerpo de ataque sobre la copia inicial de `server.js` y sobre el archivo corregido. Sólo se sustituye el extractor nativo por uno determinista sintético, como en la auditoría original; Express, adquisiciones y emisión/verificación HMAC son reales.

Antes:

```json
{"http_status":200,"attestation_issued":true,"valid_hmac":true,"reader_used":false}
```

Después:

```json
{"http_status":503,"attestation_issued":false,"valid_hmac":false,"reader_used":false}
```

No basta almacenar más digests, hacerlos persistentes o añadir otro nonce: una imagen antigua no observada previamente sigue careciendo de prueba de origen/instante. Por ello se retiró su capacidad de generar una nueva attestation. Los tokens de adquisición siguen teniendo contexto, TTL y consumo único, pero su creación no acredita una lectura física.

El paquete instalado `uareu-biometric@1.0.2`, `dist/modules/index.js`, contiene `dpfpddCapture`/`dpfpddCaptureAsync` (aprox. 318/321) y `dpfjCreateFmdFromRaw` (aprox. 418) como funciones que lanzan `Method not yet implemented in modern version`. No se modificó `node_modules` ni se sustituyó por una implementación física especulativa. **Queda pendiente software de adquisición confiable ligado al challenge**, no sólo conectar o validar un lector físico. El bloqueo afecta enrolamiento, login y actos biométricos que necesitan una nueva captura; el frontend recibe su error existente. No se añadió bypass ni éxito sintético a la aplicación.

## CAMBIOS_REALIZADOS_POR_ASTRA

Líneas aproximadas referidas al archivo final; cuando se elimina una función se señala su ubicación inicial. Todos estos cambios pertenecen a **AF-02**.

| Archivo / función / líneas | Comportamiento antes | Comportamiento después y razón | Test / resultado antes → después |
|---|---|---|---|
| `biometric-service/server.js`, handler `POST /extract-fmd`, final 89–112; anterior aprox. 142–203 | Convertía RAW aportado por el cliente, fechaba al procesar y firmaba HMAC si el digest no estaba en memoria. | Valida contexto; elimina RAW del request; consume adquisición válida y devuelve 503 sin FMD/attestation. Evita convertir material archivado en evidencia reciente. Contexto ausente=422, inválido/usado=409. | Nueva regresión `unseen archived RAW...`: **FAIL (200)** → **PASS (503, cero extracción, cero attestation)**. Sonda original antes/después también ejecutada. |
| `biometric-service/server.js`, `parseRaw`, `attest`, `rawReplayDigest`, `rememberCaptureDigest`, variables de digests, anteriores aprox. 31–123; `clearAcquisitionsForTest`, final 162–166 | Helpers implementaban y retenían la vía de atestación de RAW no confiable. | Se eliminó exclusivamente esa vía y su caché; helper TEST limpia las adquisiciones restantes. Matching de FMD almacenado y contratos backend no se modificaron. | Suite del servicio: 3 pruebas iniciales → 4 finales, todas pasan con expectativas seguras. |
| `biometric-service/test/acquisition-freshness.test.js`, nuevo test aprox. 32–57 | No cubría RAW archivado nunca visto por el proceso. | Añade adquisición nueva + imagen archivada con extractor disponible; exige ausencia de respuesta 200/FMD y contador de extracción=0. | Test añadido antes de corregir: FAIL; después: PASS. |
| Mismo archivo, pruebas existentes de uso único y adquisición fresca, aprox. 70–147 | Esperaban que el primer RAW del navegador obtuviera 200; luego comprobaban replay. | Primer intento=503 explícito; el mismo acquisition_id sigue dando 409; otra adquisición tampoco permite emitir HMAC (503). | Las dos expectativas de primer 200 eran inseguras y se cambiaron deliberadamente. La prueba sin adquisición permanece en 422. **Ninguno de los 161 tests Python cambió.** |
| `docs/Biometria-DigitalPersona.md`, sección Flujo, aprox. 43–62 | Describía digests + acquisition_id como captura fresca suficiente. | Declara AF-02 reabierto, estados 422/409/503, bloqueo funcional, stubs SDK y adquisición confiable pendiente. | Contraste con ataque antes/después y código final; documentación no tiene test propio. |
| `docs/Frontend.md`, Captura biométrica, aprox. 43–49 | Describía flujo de captura sin advertir que el servicio no puede acreditar origen. | Expone el error 503 y el bloqueo actual de captura; remite a la nota biométrica. | Coherente con respuesta 503 reproducida; no se editó React. |
| `docs/API-Endpoints.md`, Contrato biométrico, aprox. 85–93 | Contrato sin reflejar denegación del loopback. | Registra `TRUSTED_CAPTURE_UNAVAILABLE` y distingue fixtures TEST del flujo operativo pendiente. | Coherente con regresión AF-02 y backend de challenges ejecutado. |
| `docs/Seguridad-FEA.md`, Diseño/Anti-replay, aprox. 33 | Asociaba adquisición única con protección sin explicitar ausencia de prueba de origen. | Explica que el ID no prueba frescura y que captura queda bloqueada. | Coherente con sonda AF-02; sin cambio criptográfico backend. |
| `VERIFICACION_Y_REMEDIACION_FINAL_ASTRA.md` | No existía. | Entregable de esta pasada: evidencia, limitación, archivos, regresión y dictamen. | Revisión contra salidas reales y hashes iniciales. |

Lista completa de archivos del proyecto editados o creados por esta pasada:

1. `biometric-service/server.js`
2. `biometric-service/test/acquisition-freshness.test.js`
3. `docs/API-Endpoints.md`
4. `docs/Biometria-DigitalPersona.md`
5. `docs/Frontend.md`
6. `docs/Seguridad-FEA.md`
7. `VERIFICACION_Y_REMEDIACION_FINAL_ASTRA.md`

Se preservó el formato de fin de línea original. El registro inicial SHA-256 de 378 archivos permite distinguir estos cambios de la remediación anterior aún sin commit. El diff exclusivo de los seis archivos existentes suma **84 inserciones, 119 eliminaciones**; el informe nuevo se cuenta aparte.

### Auxiliares y evidencia local

Se creó `scratch/af_final_verification/`, ignorado por Git. Contiene:

- `baseline_hashes.json`: hashes iniciales, sin contenido de `.env`.
- `baseline/` y `final/`: copias de los seis archivos editados para comparar exactamente esta pasada; las tres notas no copiadas al inicio se reconstruyeron revirtiendo sólo las adiciones documentales y se verificaron contra su SHA-256 inicial.
- `this-pass.patch`, `this-pass-stat.txt`: diff de esta pasada, incluido el código inicialmente no trackeado.
- `git-diff-stat.txt`: salida global requerida del árbol con cambios previos.
- `af02-original-attack.cjs`, `af02-before.log`, `af02-after.log`: reproducción sobre copia inicial y archivo corregido.
- `af07-handlers.mjs`, `af07-handlers.log`: ejecución y resultados de los 21 handlers.
- `verification_backend.py`, `directed-backend.log`: ocho sondas adicionales para AF-02/03/04/05/06/08/09/11, ejecutadas junto a las 18 regresiones dirigidas existentes.
- `full-postgres-final.log`, `alembic-final.log`: regresión PostgreSQL completa y migraciones/check finales.

Las primeras ejecuciones del arnés adicional encontraron dos errores **del fixture**, corregidos sin editar aplicación: médico sintético sin la especialidad obligatoria del esquema de respuesta y expectativa de nombre de usuario en auditoría, cuyo contrato real es `rol:id`. El arnés JS también necesitó sus globals de navegador/JavaScript (`Boolean`, `localStorage`) para alcanzar las solicitudes. La corrida final verifica el contrato real; estos ajustes no cambian expectativas de seguridad.

Los comandos de build y compileall regeneraron sus artefactos habituales `frontend/dist/` y cachés Python. Pytest utilizó su scratch temporal. Alembic final dejó migrado el esquema TEST vacío. No hubo migraciones, cambios de datos ni archivos de pacientes operativos.

## Regresión final ejecutada

| Comprobación | Comando real / resultado |
|---|---|
| PostgreSQL TEST completo | `backend/venv/Scripts/python.exe backend/scripts/run_local_postgres_tests.py` — **161 passed, 193 warnings, 10 subtests passed**, 69.47 s. Ninguna prueba Python alterada. |
| AF-01..AF-11 | Suite completa incluye AF-02/TSA en sus archivos específicos. Regresión dirigida: helper anterior con `backend/tests/test_af_remediation_regressions.py scratch/af_final_verification/verification_backend.py` — **26 passed**, 62 warnings (18 existentes + 8 sondas). |
| Alembic desde cero y check | `backend/venv/Scripts/python.exe backend/scripts/run_local_alembic_check.py`, ejecutado tras el reset final de pytest: revisiones desde base hasta `f7a9c2d4e6b1`; **No new upgrade operations detected**. |
| compileall | `backend/venv/Scripts/python.exe -m compileall -q backend` — exit 0. |
| Frontend lint:runtime | `npm run lint:runtime`, en frontend — exit 0. |
| Frontend tests | `node --test test/*.test.js`, en frontend — **2 pass**; adicionalmente 21 handlers ejecutados con 202, todos pendientes. |
| Frontend build | `npm run build`, en frontend — exit 0, **722 módulos**. Advertencia existente de chunks mayores de 500 kB, sin cambio de alcance. |
| Mobile typecheck | `node_modules/.bin/tsc.cmd --noEmit`, en mobile_app — exit 0; binario local, sin instalación. |
| Biometric service tests | `npm --prefix biometric-service test` — **4 pass**. |
| Biometric service sintaxis | `node --check biometric-service/server.js` — exit 0. |

Los warnings Python son deprecaciones ya presentes; no se trataron como defectos nuevos ni se modificó código para silenciarlos. Las regresiones técnicas verdes no equivalen a captura biométrica operativa.

## git diff --stat

Salida global del árbol contra Git: incluye **cambios previos**, no atribuibles a esta pasada. El servicio, sus tests y varias notas estaban inicialmente sin seguimiento, por lo que este comando no los incluye; el diff contra la copia inicial, listado arriba, cubre esa limitación.

```text
 .gitignore                                         |    13 +-
 Formatos VERTICAL/README_FORMATOS.md               |   154 +-
 README.md                                          |     8 +-
 README_FORMATOS.md                                 |   117 +-
 backend/.env.example                               |    37 +-
 backend/add_missing_indexes.py                     |    59 -
 backend/alter_formatos.py                          |    46 -
 backend/alter_postgres.py                          |    38 -
 backend/check_mr_ne_urg.py                         |    34 -
 backend/clear_all_evolutions.py                    |    22 -
 backend/clear_evol_3.py                            |    39 -
 backend/crypto_fea.py                              |   489 +-
 backend/database.py                                |    22 +-
 backend/find_vertical_schema.py                    |    44 -
 backend/fix_controller_key.py                      |    35 -
 backend/fix_sequences.py                           |    27 -
 backend/generados/HES-2026-00001.docx              |   Bin 81034 -> 0 bytes
 backend/generados/HES-2026-00001.pdf               |   Bin 94871 -> 0 bytes
 backend/generados/HES-2026-00005.docx              |   Bin 80996 -> 0 bytes
 backend/generados/HES-2026-00005.pdf               |   Bin 94958 -> 0 bytes
 backend/generados/HES-2026-00007.docx              |   Bin 81145 -> 0 bytes
 backend/generados/HES-2026-00007.pdf               |   Bin 96114 -> 0 bytes
 backend/generados/HES-2026-00008.docx              |   Bin 81018 -> 0 bytes
 backend/generados/HES-2026-00008.pdf               |   Bin 94963 -> 0 bytes
 backend/generados/HES-2026-00009.docx              |   Bin 81006 -> 0 bytes
 backend/generados/HES-2026-00009.pdf               |   Bin 94054 -> 0 bytes
 backend/generados/HES-2026-00010.docx              |   Bin 81072 -> 0 bytes
 backend/generados/HES-2026-00010.pdf               |   Bin 95306 -> 0 bytes
 backend/inspect_exact_keys.py                      |    27 -
 backend/inspect_pdf.py                             |    19 -
 backend/inspect_vertical_link.py                   |    50 -
 backend/kh_database.py                             |  4377 ++++-
 backend/main.py                                    |  9817 ++++++++--
 backend/migrate_to_postgres.py                     |    75 -
 backend/models.py                                  |   282 +-
 backend/official_pdf_engine.py                     |   217 -
 backend/pdf_engine_04.py                           |   241 +-
 backend/pdf_engine_12.py                           |   247 +-
 backend/pdf_engine_25.py                           |   257 +-
 backend/pdf_engine_32_01.py                        |   289 +-
 backend/pdf_engine_34_01.py                        |   390 +-
 backend/pdf_engine_eed.py                          |   110 +-
 backend/pdf_engine_v2.py                           |   429 +-
 backend/requirements.txt                           |     4 +
 backend/schemas.py                                 |   116 +-
 backend/scripts/extract_form_assets.py             |   107 -
 backend/scripts/inject_test_patient_sql.py         |    93 -
 backend/security.py                                |   113 +-
 backend/seed.py                                    |   188 +-
 backend/services/pdf_service.py                    |  1157 +-
 backend/test_chrome_render.py                      |    65 -
 backend/test_crypto_fea.py                         |   120 -
 backend/test_fetch_3_evols.py                      |    71 -
 backend/test_inject_3_evols.py                     |    66 -
 backend/test_post.py                               |    21 -
 backend/test_tsa_client.py                         |    53 -
 backend/tmp_fix_seq.py                             |    15 -
 backend/tsa_client.py                              |   374 +-
 backend/update_test_doctor.py                      |    29 -
 backend/vertical_signer.py                         |   338 +-
 docs/Backend.md                                    |    64 +-
 docs/Database.md                                   |    94 +-
 docs/Frontend.md                                   |    56 +-
 docs/Mapa_Proyecto.md                              |    30 +-
 docs/Pase_a_Produccion.md                          |    51 +-
 frontend/package-lock.json                         |   358 +-
 frontend/package.json                              |     2 +
 frontend/src/App.jsx                               |     8 +-
 frontend/src/api.js                                |     8 +
 frontend/src/components/Layout.jsx                 |    51 +-
 frontend/src/components/PatientSearchModal.jsx     |     2 +-
 frontend/src/context/AuthContext.jsx               |    33 +-
 .../src/features/biometrics/BiometricSignModal.jsx |    36 +-
 .../src/features/ehr/modals/AllergiesModal.jsx     |    88 +-
 frontend/src/hooks/useAutoLogout.js                |     9 +-
 frontend/src/hooks/useDigitalPersona.js            |   497 +-
 frontend/src/index.css                             |     1 +
 frontend/src/pages/AdminDashboard.jsx              |    46 +-
 frontend/src/pages/AgendaMedica.jsx                |   242 +-
 frontend/src/pages/CamasDashboard.jsx              |   229 +-
 frontend/src/pages/CapturaEnfermeria.jsx           |     9 +-
 frontend/src/pages/FirmaExpress.jsx                |    94 +-
 frontend/src/pages/LoginDual.jsx                   |   231 +-
 frontend/src/pages/PatientDashboard.jsx            | 18508 ++++++++++++++-----
 frontend/vite.config.js                            |     9 +-
 iniciar.bat                                        |    24 +-
 mobile_app/package-lock.json                       |  1162 +-
 mobile_app/package.json                            |     3 +
 mobile_app/src/app/camas.tsx                       |    26 +-
 mobile_app/src/app/captura-enfermeria.tsx          |    26 +-
 mobile_app/src/app/dashboard.tsx                   |    12 +-
 mobile_app/src/app/index.tsx                       |     4 +-
 mobile_app/src/app/login.tsx                       |    12 +-
 mobile_app/src/app/server-setup.tsx                |    19 +-
 mobile_app/src/contexts/ServerContext.tsx          |    16 +-
 preparar_produccion.py                             |   211 +-
 96 files changed, 32758 insertions(+), 10454 deletions(-)
```

## NUEVO_BLOCKER_INTRODUCIDO_POR_REMEDIACION:

**NINGUNO.** La insuficiencia de frescura y su bloqueo funcional se mantienen dentro de **AF-02**, expresamente reabierto. No se inventa un hallazgo nuevo ni se oculta que la contención impide emitir nuevas capturas.

## Dictamen

**A) PILOTO/PREPRODUCCIÓN CON DATOS SINTÉTICOS: NO LISTO.**

**B) SOFTWARE LISTO PARA PASAR A GATES EXTERNOS DE GO-LIVE: NO.**

Razón interna: AF-02 requiere una implementación operativa de adquisición confiable y su verificación. El ataque ya se rechaza, pero el producto no dispone actualmente de un camino legítimo seguro de captura.

SQL Server STAGING, lector físico, TLS del host, backup off-host, decisión institucional de roles y validación jurídica NOM permanecen como **gates externos**. No se clasifican como bugs pendientes ni causan por sí solos este dictamen negativo.

No se hizo push. Trabajo detenido al entregar este informe.

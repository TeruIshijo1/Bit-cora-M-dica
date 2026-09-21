# Remediación final dirigida — AF-01 a AF-11

Fecha de ejecución: 2026-09-17  
Referencia autoritativa: `AUDITORIA_FINAL_PREPRODUCCION_ASTRA.md`  
Alcance: exclusivamente AF-01 a AF-11. No se hizo push.

## Resultado ejecutivo

Los once caminos adversariales descritos por Astra quedaron cerrados y cuentan
con regresión permanente. La corrida final sobre PostgreSQL TEST, creado desde
cero por Alembic, terminó con **161 passed, 10 subtests passed**.

Antes de corregir se ejecutó el arnés inicial de reproducción: sus 10 escenarios
backend fallaron por las vías esperadas (portal/lectura, actor RH único, selección
de firma, mutabilidad, duplicado activo, Vertical vacío, colisión idempotente,
GET mutante y auditoría perdida). Los vectores específicos JavaScript y TSA de
la referencia autoritativa se conservaron como pruebas ejecutables en sus
respectivas suites.

| AF | REPRODUCIDO ANTES | CAMBIO | TEST DE REGRESIÓN | RESULTADO | ESTADO |
|---|---|---|---|---|---|
| AF-01 | Sí. Folio público devolvía datos sintéticos y `limpieza` obtenía expediente/firmas. | Allowlist pública exacta; estado/HTML/PDF público exige `v1_*` opaco exacto. Se eliminó búsqueda por folio/paciente/formato, se redactaron identidad, expediente y ruta física. Las lecturas clínicas tienen política explícita y excluyen roles no clínicos. La creación QR desde GET queda bloqueada por defecto. | `test_af01_public_verification_rejects_enumerable_patient_folio`; `test_af01_non_clinical_role_cannot_read_ehr_or_signatures`; suite de política de rutas. | Anónimo por folio: 404. `limpieza`: 403 en expediente y firmas. Sólo un identificador opaco registrado puede verificar/descargar. | **RESUELTO** |
| AF-02 | Sí. El mismo RAW podía producir otra attestation con challenge nuevo. | Flujo challenge → adquisición loopback de 120 s → captura → FMD. `acquisition_id` aleatorio, contextual y de un solo uso se incluye en HMAC; backend exige que la adquisición sea posterior al challenge y la consume atómicamente. El servicio rechaza RAW ya procesado con otra adquisición. | `biometric-service/test/acquisition-freshness.test.js` (3 casos); `test_af02_legacy_attestation_without_service_acquisition_is_rejected`. | RAW + strings challenge/sesión sin adquisición: 422. Reuso de adquisición: 409. Mismo RAW con challenge/adquisición nuevos: 409. | **RESUELTO** |
| AF-03 | Sí. Un único RH podía representar reenrolamiento y completar rotación. | Se persiste actor/fecha del reenrolamiento. La rotación FEA exige otro actor administrativo; mientras está pendiente, firma y login biométrico responden 423. Al completar por segundo actor se limpia la ceremonia y se conserva historial append-only. | `test_af03_same_administrative_actor_cannot_reenrol_and_rotate_fea`; `test_af03_reenrol_rotation_and_login_require_two_administrative_actors`; regresión FEA 17. | Mismo RH: 403 en rotación y 423 en login. Segundo actor: rotación controlada y login posterior válido. | **RESUELTO** |
| AF-04 | Sí. Slot inexistente hacía fallback; `firma_id` ajeno era aceptable; PostgreSQL permitía cambiar `canonical_payload`. | Selección exacta por paciente+código+slot+tipo+versión; `firma_id` debe pertenecer al documento. Histórico sólo mediante opción explícita. Se coteja snapshot contra contenido operativo vigente. Trigger PostgreSQL bloquea UPDATE de payload/hash/sello/llave/binding y DELETE de firma completada. | `test_af04_public_slot_999_never_falls_back_to_slot_1`; `test_af04_firma_id_must_belong_to_requested_document`; `test_af04_completed_signature_snapshot_is_database_immutable`; `test_af04_current_operational_content_cannot_be_presented_as_signed_version`. | Slot 999: `SIN_FIRMA`. ID ajeno: 404/409. UPDATE canónico: rechazado por DB. Contenido vigente distinto: histórico, no vigente. | **RESUELTO** |
| AF-05 | Sí. Dos solicitudes concurrentes dejaban dos filas `ACTIVA`. | Índice único parcial PostgreSQL por paciente+código+slot normalizado+rol+versión y advisory transaction lock por documento lógico. Duplicados históricos se normalizan sin borrar evidencia. Conflicto final devuelve 409. | `test_af05_database_allows_only_one_active_signature_per_logical_document`; `test_af05_two_concurrent_signatures_yield_one_active_record`; `test_af05_two_concurrent_http_signatures_with_distinct_keys_leave_one_active`. | Dos POST concurrentes, challenges e idempotency keys distintos: exactamente una firma activa. | **RESUELTO** |
| AF-06 | Sí. `HTTP 200 / {}` se convertía en `True`, escribía marcador y podía llegar a `SYNCED`. | El adaptador sólo acepta la confirmación contractual explícita `Document has been signed`. Respuesta vacía, esquema desconocido o confirmación ausente lanza error y no ejecuta UPDATE SQL. | `test_af06_http_200_empty_json_never_confirms_vertical` y regresiones de clinical-sync. | `200 / {}`: excepción, cero UPDATE, nunca `SYNCED`. | **RESUELTO** |
| AF-07 | Sí. Formato 15 EV trataba 202 sin `error` como éxito SQL Server. | Helper común `clinicalSyncResult.js`: éxito únicamente con HTTP 200/201 + `success=true` + `state=SYNCED`. 202, `success=false` y estados pendientes muestran “SINCRONIZACIÓN PENDIENTE”. Se aplicó a los handlers durable-sync de `PatientDashboard`. | `frontend/test/clinicalSyncResult.test.js` (Formato 15 EV y matriz de estados); lint runtime y build. | 202/`RETRYABLE_ERROR` no cierra como éxito ni afirma guardado en SQL Server. | **RESUELTO** |
| AF-08 | Sí. Misma clave/tipo con paciente y payload distintos devolvía el acto A. | `clinical_sync_operations.request_fingerprint` SHA-256 estable sobre operación, agregado, paciente y payload mínimo canónico. Coincidencia reutiliza; diferencia lanza `IDEMPOTENCY_KEY_CONFLICT`, también en carrera de INSERT. | `test_af08_same_idempotency_key_with_different_request_is_conflict`; `test_af08_http_layer_returns_409_for_different_request_same_key`. | Solicitud B con clave de A: HTTP 409, sin éxito ajeno. | **RESUELTO** |
| AF-09 | Sí. `allow_create=False` insertaba/actualizaba paciente; GET PDF persistía QR/archivo. | `allow_create=False` retorna antes de consultar/escribir ERP local. Los GET de firmas/EHR usan ese modo. Registro QR requiere `persist=True` desde un flujo mutante explícito; los GET no lo usan. PDFs GET se sirven como scratch transitorio y se eliminan al completar la respuesta; no se genera QR enumerable implícito. | `test_af09_allow_create_false_prevents_insert_and_update`; `test_af09_get_signatures_does_not_create_erp_patient`; `test_af09_get_pdf_does_not_persist_qr_or_generated_file`. | Conteos de pacientes y `DocumentoVerificacionQR` no cambian; el archivo generado no queda persistido. | **RESUELTO** |
| AF-10 | Sí. `native='granted'` provocaba `int('granted')` y TSA fallida; resumen omitía TSA pendiente. | Parseo robusto de estados RFC 3161 `0/1`, `granted` y `granted_with_mods`; se conserva verificación CMS, cadena, EKU, imprint y nonce. Todos los resúmenes exponen `tsa_status`; sólo TSA verificada permite “VERIFICACIÓN_CRIPTOGRÁFICA_COMPLETA”. | Vector completo `test_af10_complete_timestamp_response_with_granted_status_is_verified`; `test_af10_summary_exposes_pending_tsa_without_claiming_complete`; suite TSA negativa. | TimeStampResp/CMS/nonce/root válidos: `TSA_VERIFICADO`. TSA pendiente: ECDSA válida con estado explícito, nunca completa. | **RESUELTO** |
| AF-11 | Sí. Cambio de rol no creaba evento; ingreso y cama podían perder el log tras cerrar sesión. | Eventos de usuario, rol/permisos, contraseña, médico, biometría, rotación, ingreso y cama se agregan antes del commit de la misma transacción. Se conserva trigger append-only. | `test_af11_role_change_persists_exactly_one_audit_event`; `test_af11_patient_admission_and_bed_events_survive_session_close`; suite de auditoría append-only. | Cambio de rol: exactamente un evento. Ingreso y cama: eventos visibles después de cerrar/reabrir sesión. | **RESUELTO** |

## Migración

Se agregó únicamente la revisión `f7a9c2d4e6b1` sobre
`d4f5a6b7c8d9`. Incluye:

- `clinical_sync_operations.request_fingerprint`, con backfill estable de filas existentes;
- actor/fecha de reenrolamiento médico;
- `biometric_challenges.acquisition_id` único;
- índice único parcial `uq_firma_documento_activa_logica`;
- triggers de inmutabilidad y no eliminación de evidencia de firma completada.

No se modificó ninguna migración histórica.

## Regresión final ejecutada

| Comprobación | Resultado |
|---|---|
| PostgreSQL TEST completo: `backend/scripts/run_local_postgres_tests.py` | **PASS — 161 passed, 193 warnings, 10 subtests passed** |
| Regresiones dirigidas AF: `test_af_remediation_regressions.py` | **PASS — 18 passed** |
| Alembic upgrade sobre DB limpia + `alembic check` | **PASS — No new upgrade operations detected** |
| `python -m compileall -q backend` | **PASS** |
| Frontend `npm run lint:runtime` | **PASS** |
| Frontend `node --test test/clinicalSyncResult.test.js` | **PASS — 2 passed** |
| Frontend `npm run build` | **PASS — 722 módulos**; advertencia no bloqueante por tamaño de chunks |
| Mobile `npx tsc --noEmit` | **PASS** |
| Biometric service `node --check server.js` | **PASS** |
| Biometric service `npm test` | **PASS — 3 passed** |
| Secret scan existente | **PASS — 259 archivos, 0 hallazgos de alta confianza** |
| `npm audit --omit=dev` frontend | **PASS — 0 vulnerabilidades** |
| `npm audit --omit=dev` biometric-service | **PASS — 0 vulnerabilidades** |
| `npm audit --omit=dev` móvil | **14 moderadas, 0 altas/críticas**; fixes propuestos por npm son cambios mayores de Expo y permanecen en el gate de dependencias ya documentado |
| `pip-audit -r backend/requirements.txt` | **2 reportes del mismo advisory en `ecdsa 0.19.2`**, sin versión corregida publicada; FEA usa `cryptography` y JWT usa HS256, conforme al límite ya documentado por Astra |

El gate solicitado fue `lint:runtime` y quedó verde. También se ejecutó el lint
general de forma informativa: sigue reportando deuda preexistente (incluido el
WebSDK minificado de tercero); no se modificó porque queda fuera de AF-01..AF-11
y el build de producción sí pasa.

## Gates deliberadamente no reclamados

Este informe cierra técnicamente AF-01..AF-11. No sustituye los gates externos
ya identificados por Astra: SQL Server STAGING, lector físico en puesto, matriz
institucional de acceso horizontal, TLS/secrets/trust store del host, continuidad
operativa y validación jurídico-operativa. La preparación/persistencia de un QR
nuevo permanece cerrada por defecto hasta invocarse desde una operación mutante
explícita; un GET nunca la crea.

No se hizo push.

# Estabilización FEA, llaves y TSA — Bloque B

**Fecha:** 2026-09-17  
**Alcance cerrado:** P0-05, parte criptográfica restante de P0-06, P1-01 y P1-02.  
**Ambiente de validación:** PostgreSQL 17 local `hospital_escandon_test`; certificados, llaves, biometría y datos exclusivamente sintéticos. No se usó PostgreSQL productivo, `KH_HE` productivo ni TSA productiva.

## Dictamen

| Hallazgo | Estado | Evidencia principal |
|---|---|---|
| P0-05 — firma no vinculada al documento real | **RESUELTO** | Snapshot completo `CANONICAL_V2`, SHA-256 y ECDSA sobre bytes canónicos; verificación de snapshot, identidad, documento, versión, slot, `key_id` y PDF cuando aplica. |
| P0-06 — transición criptográfica posterior al reenrolamiento | **RESUELTO** | Bloqueo 423, challenge/match 1:1 y operación explícita auditada de rotación; la pública anterior permanece histórica. |
| P1-01 — custodia/rotación/key-id | **RESUELTO** para el alcance mínimo definido | `key_id` exacta, una llave activa por médico, historial protegido en PostgreSQL, descifrado fail-closed, rotación explícita y custodia versionada. No se declara HSM. |
| P1-02 — TSA analizado sin verificación criptográfica | **RESUELTO** | Validación RFC 3161/CMS con pyHanko, trust store pinneado, EKU, vigencia, identidad, nonce, eContent/messageDigest e imprint. |

## Diseño final del payload firmado

El frontend sólo indica qué documento desea firmar mediante `codigo_formato` y `evolution_slot`. `contenido_resumen` fue eliminado del esquema y de los dos clientes React. El backend carga el contenido autoritativo completo desde Vertical/PostgreSQL y falla cerrado con 409 si no puede obtenerlo.

`CANONICAL_V2` incluye:

- `schema_version`, `tipo_documento`, `codigo_formato`;
- `paciente`, `pt_num`, `expediente`;
- `evolution_slot`, `version_documento`, `source_identifier`;
- `contenido_clinico` completo;
- `firmante.medico_id`, nombre y cédula;
- `proposito_firma`, fecha/hora ISO-8601 con zona `America/Mexico_City`;
- `key_id`;
- rol, identificador y SHA-256 del PDF cuando el PDF es evidencia primaria.

Serialización: JSON RFC 8259 en UTF-8, claves ordenadas, separadores fijos `,` y `:`, booleanos/null JSON normales, sin NaN/infinitos y normalización determinista de fechas, decimales y bytes.

### Bytes exactos protegidos

1. Se serializa el objeto completo con `canonical_json_bytes()`.
2. `payload_hash = SHA-256(bytes_utf8_CANONICAL_V2)`.
3. ECDSA P-256 con SHA-256 firma exactamente `bytes_utf8_CANONICAL_V2`.
4. Se persisten el snapshot completo, su hash, la firma y la `key_id`.
5. RFC 3161 sella `payload_hash`; no regenera la ECDSA.

No hay truncamiento de caracteres ni dependencia del orden de diccionarios del frontend.

## Snapshot y verificación histórica

`firmas_documentos_clinicos.canonical_payload` conserva el snapshot inmutable necesario para reproducir los bytes firmados aunque el documento operativo evolucione. La verificación:

1. recalcula SHA-256 sobre los bytes almacenados del snapshot;
2. exige que el JSON vuelva a serializar exactamente a la misma secuencia canónica;
3. coteja paciente/expediente, tipo/código, versión, slot, identidad y `key_id` contra las columnas de la firma;
4. selecciona exclusivamente la pública de `medico_id + key_id`;
5. verifica ECDSA;
6. verifica PDF cuando el payload declara `pdf.sha256`;
7. verifica TSA sólo cuando el estado persistido es `TSA_VERIFICADO`.

Modificar un byte del snapshot o PDF invalida el control correspondiente. Un marcador Vertical (`ESignature`, `SignedBy`, `FIRMADO_BIOMETRICAMENTE`) se devuelve sólo como metadata y nunca produce `integridad`, `identidad` o `autenticidad = true`.

## Modelo de key_id y rotación

`historial_llaves_fea` ahora tiene `key_id` único y estado. PostgreSQL impone un índice único parcial para una sola llave activa por médico. Un trigger bloquea `DELETE`, cambios de pública/key-id/médico/fecha y reactivaciones; sólo permite la transición unidireccional `ACTIVA → INACTIVA` con `fecha_inactivacion`.

Cada firma nueva guarda `key_id` como FK. La verificación no itera llaves históricas.

Rotación posterior a reenrolamiento:

1. Bloque A marca `requiere_actualizacion_fea = true`.
2. Todo intento de firma médica falla con HTTP 423.
3. `POST /api/medicos/{id}/fea/completar-actualizacion` exige rol autorizado existente, challenge `ACTUALIZACION_FEA`, match biométrico 1:1 y motivo.
4. En una transacción se bloquea el médico, se inactiva la llave vigente, se crea un nuevo par/key-id, se cifra la privada y se audita el evento.
5. Sólo al completar se limpia `requiere_actualizacion_fea`.
6. Firmas anteriores continúan verificando mediante su `key_id` histórica.

Un error de Fernet/HKDF lanza `PrivateKeyDecryptionError`; no rota, no reemplaza la pública y no crea otra identidad.

## Custodia real de la privada

El mecanismo actual se identifica como `FERNET_HKDF_SHA256_V1`. La KEK usa HKDF-SHA256 sobre `huella_token + HES_HMAC_SECRET`; `huella_token` es un UUID de custodia almacenado en BD, no material derivado de la huella. `HES_HMAC_SECRET` permanece fuera de BD y la privada nunca se devuelve ni registra.

`PrivateKeyCustodian` establece la interfaz sustituible para KMS/HSM. No se implementó ni se afirmó disponer de HSM en esta fase.

## PDF

El payload admite `pdf_identifier` y SHA-256 de los bytes PDF reales antes de firmar. La prueba modifica un byte y obtiene fallo.

En los flujos actuales el PDF se genera después de la firma y funciona como representación secundaria del snapshot clínico primario. Por ello queda explícitamente rotulado `REPRESENTACION_SECUNDARIA_NO_FIRMADA`; la API no declara integridad PDF. Sólo un flujo que entregue los bytes antes de firmar puede usar `EVIDENCIA_PRIMARIA` y obtener `PDF_VERIFICADO`.

## TSA RFC 3161

Se sustituyó el parser parcial por `asn1crypto` + validación CMS/PKIX de pyHanko. Se comprueba:

- `SignedData`, `SignerInfo`, firma CMS y atributo `messageDigest`;
- eContent `id-ct-TSTInfo`;
- `messageImprint` y algoritmo SHA-256;
- certificado firmante, cadena hasta `TSA_TRUST_STORE` y vigencia al `genTime`;
- EKU crítica `timeStamping`;
- identidad/pin opcional `TSA_EXPECTED_SUBJECT` / `TSA_EXPECTED_CERT_SHA256`;
- nonce de 128 bits y correspondencia con la solicitud;
- correspondencia con `payload_hash`.

Estados: `SIN_TSA`, `TSA_PENDIENTE`, `TSA_VERIFICADO`, `TSA_FALLIDO`; los tokens históricos quedan `TSA_LEGACY_NO_VERIFICADO`. Caída de red deja `TSA_PENDIENTE`, nunca verificado. `POST /api/firmas/{id}/tsa/reintentar` es idempotente para estados ya verificados y no modifica la ECDSA original.

## Paciente, tutor y testigo

Se eliminó la presentación del SHA-256 truncado `BIO-HES` como firma criptográfica. Estas actuaciones persisten snapshot completo, identidad, rol, resultado de match, timestamp, hash y auditoría bajo `BIOMETRIC_EVIDENCE_V1`, descrito como `AUTENTICACION_BIOMETRICA_Y_EVIDENCIA_DE_ACTO_NO_FEA_PERSONAL`. No se inventa una clave privada del paciente.

## Migración

Nueva revisión: `backend/migrations/versions/c31f4a7d9e20_fea_canonical_keys_tsa.py`.

Agrega:

- `historial_llaves_fea.key_id`, `estado`, índice único activo y trigger protector;
- `medicos.private_key_cipher_version`;
- `firmas_documentos_clinicos.key_id`, `signature_schema_version`, `canonical_payload`, `payload_hash`, `document_version`, `pdf_hash`, `pdf_identifier`, `tsa_status`, `tsa_nonce`, `tsa_attempts`, `tsa_last_error`, `tsa_verified_at` y FK de key-id.

No se modificaron `9024a9c93603_initial_postgresql_schema.py` ni `4b7e2a91c6d0_biometric_security_stabilization.py`.

## Compatibilidad histórica

- Filas existentes: `LEGACY_V1`; visibles pero `FIRMA_LEGACY_NO_CUBRE_DOCUMENTO_COMPLETO`.
- Tokens TSA históricos: `TSA_LEGACY_NO_VERIFICADO`.
- No se reescribieron snapshots, firmas ni tokens antiguos como si fueran V2.
- Las llaves históricas existentes reciben identificadores `legacy-{id}` sin alterar su pública.

## Pruebas antes/después

Primero se añadieron cuatro regresiones negativas y se ejecutaron contra el defecto original:

```text
4 failed
- contenido posterior al carácter 100 no estaba firmado
- ciphertext corrupto rotaba automáticamente
- se aceptaba cualquier llave histórica
- marcador Vertical se reportaba íntegro/auténtico
```

Después se implementaron 30 pruebas nuevas en `backend/tests/test_fea_crypto_stabilization.py`, incluidos los 25 escenarios obligatorios: contenido completo, todas las mutaciones de binding, PDF, Vertical, llave equivocada/histórica, rotación, 423/actualización FEA, cinco vectores TSA, caída/reintento y controles adicionales de legacy/append-only/contrato cliente.

Resultado final PostgreSQL TEST:

```text
93 passed, 153 warnings, 10 subtests passed in 35.91s
```

Las 63 pruebas preexistentes continúan pasando; las 30 nuevas también pasan. Las advertencias son deprecaciones ya visibles de SQLAlchemy, Starlette, Pydantic, SlowAPI y uso heredado de `utcnow`; no hubo fallos.

## Regresión global

| Comprobación | Resultado |
|---|---|
| Suite completa pytest sobre PostgreSQL TEST | **OK — 93 passed** |
| Alembic desde esquema limpio hasta `c31f4a7d9e20` | **OK** |
| `alembic check` | **OK — No new upgrade operations detected** |
| `python -m compileall -q backend` | **OK** |
| `frontend npm run build` | **OK**; sólo advertencia de chunks grandes existente |
| `node --check biometric-service/server.js` | **OK** |

## Riesgos restantes de este bloque

1. La custodia V1 sigue dependiendo de la separación operativa entre la copia de BD y `HES_HMAC_SECRET`; una exposición conjunta comprometería privadas. La interfaz está preparada para KMS/HSM, pero esa infraestructura no existe en esta fase.
2. Producción debe aprovisionar y custodiar `TSA_TRUST_STORE`; sin él ningún token puede quedar `TSA_VERIFICADO`. Los pins de sujeto/fingerprint son recomendables.
3. La validación PKIX no hace fetching de red y usa revocación `soft-fail`; el trust store y material de revocación deben mantenerse por procedimiento operativo de TSA.
4. Los PDFs actuales son secundarios y no tienen integridad propia declarada. Convertir un formato concreto a PDF primario requiere generar sus bytes antes de la ECDSA e incluir su hash, sin alterar el diseño canónico.

No se abordaron atomicidad PostgreSQL/SQL Server, disponibilidad, backups, refactors generales ni RBAC adicional. No se abrió Bloque C.

---
aliases: [FEA, Firma Electrónica Avanzada, Criptografía HES]
tags: [hes/seguridad, hes/normativa, hes/backend]
tipo: modulo
modulo: seguridad
codigo_fuente:
  - backend/clinical_signing.py
  - backend/crypto_fea.py
  - backend/tsa_client.py
  - backend/security.py
  - backend/models.py
actualizado: 2026-09-19
relacionados:
  - "[[Backend]]"
  - "[[Database]]"
  - "[[Biometria-DigitalPersona]]"
  - "[[Normativa-NOM]]"
  - "[[Guia-Desarrollo-IA]]"
  - "[[decisiones/ADR-0002-fea-historial-llaves]]"
---

# Seguridad-FEA

Motor de Firma Electrónica Avanzada (NOM-024): ECDSA P-256 + HKDF-SHA256 + Fernet + TSA RFC 3161.

## Diseño
- El navegador sólo selecciona `codigo_formato` y `evolution_slot`. El backend obtiene el acto clínico completo desde Vertical/PostgreSQL; `contenido_resumen`, texto o hash del cliente no forman parte del contrato.
- `clinical_signing.py` construye `CANONICAL_V2`: JSON UTF-8, claves ordenadas, separadores `,`/`:`, sin NaN y con fecha zonificada `America/Mexico_City`. Incluye paciente, expediente, tipo/código, slot, versión, contenido clínico completo, identidad/cédula, propósito y `key_id`.
- El snapshot canónico completo es inmutable; se persisten sus bytes UTF-8 y SHA-256. ECDSA P-256/SHA-256 firma exactamente esos bytes. Un trigger PostgreSQL bloquea `UPDATE` de payload/hash/sello/vínculos y `DELETE` de evidencia CANONICAL_V2 completada.
- Cada firma ECDSA persiste `key_id`. La verificación selecciona sólo `medico_id + key_id`; nunca prueba indiscriminadamente todas las llaves históricas.
- La privada se cifra con `FERNET_HKDF_SHA256_V1`: KEK HKDF-SHA256 sobre `huella_token` + `HES_HMAC_SECRET`. El token no deriva de la huella; es un UUID de custodia almacenado en BD. El secreto global vive fuera de BD.
- Un error de descifrado falla cerrado y nunca genera otra identidad. `PrivateKeyCustodian` es la frontera sustituible por KMS/HSM futuro.
- Sellado RFC 3161 usa nonce y verificación CMS completa con pyHanko: `messageDigest`, eContent/TSTInfo, imprint/algoritmo, firma, cadena, vigencia, EKU `timeStamping`, identidad configurada y nonce.
- Anti-replay: challenge/adquisición de un solo uso y 120 s. El agente local controla captura física después del challenge. HMAC V2 cubre autorización contextual, dispositivo, tiempos, hash FMD y matching local. FastAPI revalida contexto/plantilla vigente y consume acquisition_id único en PostgreSQL; ver [[Biometria-DigitalPersona]].
- Auditoría: todo acto en `auditoria_logs` (fecha, hora, IP, usuario).

## Estados y compatibilidad

- `CANONICAL_V2`: elegible para `VERIFICACIÓN_CRIPTOGRÁFICA_COMPLETA`.
- `LEGACY_V1`: evidencia histórica visible, siempre rotulada `FIRMA_LEGACY_NO_CUBRE_DOCUMENTO_COMPLETO`; no se reescribe ni asciende a V2.
- `BIOMETRIC_EVIDENCE_V1`: paciente/tutor/testigo = autenticación biométrica + evidencia del acto; no es FEA personal ni firma asimétrica del firmante.
- TSA: `SIN_TSA`, `TSA_PENDIENTE`, `TSA_VERIFICADO`, `TSA_FALLIDO` y `TSA_LEGACY_NO_VERIFICADO`. Sólo `TSA_VERIFICADO` implica validación criptográfica completa.
- La respuesta RFC 3161 acepta los estados PKI nativos `granted` y
  `granted_with_mods` (además de sus valores enteros) y mantiene obligatoria la
  validación CMS completa. Un resumen con TSA pendiente nunca se rotula como
  `VERIFICACIÓN_CRIPTOGRÁFICA_COMPLETA`.

## Regla de oro — historial de llaves
Tabla `historial_llaves_fea`: **append-only**. Al rotar (re-enrolamiento):
1. `UPDATE historial_llaves_fea SET activo=False WHERE medico_id=X AND activo=True`
2. `INSERT` nueva llave con `activo=True`.
3. Conservar `medicos.public_key_pem` anterior en historial para verificar firmas viejas.
4. **NUNCA `DELETE` ni `UPDATE` destructivo.** Violarlo anula validez legal retroactiva.

PostgreSQL impone una sola llave activa por médico y una sola firma `ACTIVA` por documento lógico (paciente, código, slot, rol y versión). Un trigger bloquea `DELETE`/mutación del material histórico de llaves; sólo permite la transición unidireccional `ACTIVA → INACTIVA` con fecha. La actualización posterior a reenrolamiento se completa en `POST /api/medicos/{id}/fea/completar-actualizacion`, exige biometría vigente, challenge, autorización, motivo auditado y un segundo actor administrativo distinto del reenrolador.

Ver [[decisiones/ADR-0002-fea-historial-llaves]].

## Vinculación operativa de firmas (2026-09-19)

Los indicadores y sellos PDF se seleccionan por paciente/código/ranura exactos
(incluido 0), comparando snapshot, versión y origen actuales. La evidencia
histórica se conserva; no se estampa en una versión nueva como vigente.
Los consentimientos reconocidos y el egreso voluntario requieren autorizador
y dos testigos con IDs distintos antes del cierre médico; una nota clínica
no hereda esos requisitos. Un CONTACTO no se convierte en representante/testigo.

La captura compromete el hash de la versión que se cargó al emitir el challenge.
Las filas Vertical generales se versionan por hash de su proyección clínica,
excluyendo `ESignature`, `SignedBy`, `SignedOn`, `MR_ST`, `ModifiedOn` y
`ModifiedBy`: el cambio administrativo de SignRecord no altera el acto clínico.
No se reescriben snapshots antiguos; una evidencia incompatible queda histórica.

SignRecord conserva el protocolo nativo y la caché de sesión de Vertical.
Se exige médico PR inequívoco y autorización real, fila/paciente exactos,
respuesta positiva y cadena nativa persistida. No hay PR/PIN por defecto,
UPDATE manual de firma ni cadena sintética. Su presencia confirma persistencia
en Vertical, **no** verifica criptográficamente la cadena opaca del proveedor.
Reintentar una operación nueva comprueba el digest; una operación histórica
sin fila exacta requiere reconciliación, nunca selecciona el último documento.

El registro del paciente/responsable sigue siendo `BIOMETRIC_EVIDENCE_V1`,
no ECDSA personal. No equipararlo a la llave médica ni declarar por ello FEA
o cumplimiento NOM. Ver [[Normativa-NOM]].

## Archivos
| Archivo | Rol |
|---|---|
| `backend/crypto_fea.py` | Generación, cifrado KEK, firma, verificación |
| `backend/clinical_signing.py` | Snapshot canónico, serialización y verificación integral |
| `backend/tsa_client.py` | Sellado RFC 3161 |
| `backend/security.py` | JWT HS256 + `require_role` |
| `backend/models.py` | `Medico`, `HistorialLlaveFEA`, `AuditoriaLog` |

## Verificación

`backend/tests/test_fea_crypto_stabilization.py` y `test_af_remediation_regressions.py` contienen los vectores negativos y TSA de TEST. La selección de verificación es exacta por paciente, código, slot, tipo, versión y `firma_id`; no existe fallback a otra firma activa. Alterar snapshot, paciente, formato, versión, slot, firmante, `key_id` o PDF primario invalida la verificación correspondiente.

Los PDFs actuales son representaciones secundarias del snapshot clínico primario. No se declara su integridad criptográfica salvo que una integración entregue sus bytes antes de firmar y persista `pdf_hash` + `pdf_identifier` dentro de `CANONICAL_V2`.

---
> 🤖 *Contexto IA: no inventar esquemas RSA ni guardar privadas en claro. Leer `crypto_fea.py` antes de tocar firma.*

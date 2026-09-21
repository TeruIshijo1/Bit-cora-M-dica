# Segunda revisión independiente y adversarial — biometría y criptografía

**Fecha de revisión:** 2026-09-17  
**Alcance exclusivo:** P0-02, P0-03, P0-04, P0-05, P0-06, P1-01, P1-02 y P1-04 de `AUDITORIA_PREPRODUCCION.md`.  
**Árbol revisado:** rama `main`, `HEAD 787027e2902e466f586f6bc5041600edb98a1648`, sobre el estado de trabajo local no limpio existente al iniciar esta revisión.  
**Naturaleza de la revisión:** análisis estático de extremo a extremo y contraste con el SDK instalado y documentación oficial de HID. No se conectó un lector, una base productiva, Vertical ni una TSA real. No se modificó código.

## 1. Conclusión ejecutiva

La revisión independiente no refuta ninguno de los ocho riesgos centrales. Seis quedan **CONFIRMADOS** y dos **CONFIRMADOS PARCIALMENTE** porque la debilidad de backend está demostrada, pero una parte de la reproducibilidad o de la redacción original requiere prueba concurrente o debe acotarse.

Los hechos de mayor impacto son:

1. `SampleFormat.Raw` entrega una imagen dactilar, no un FMD. El navegador extrae sus bytes y metadatos, y PostgreSQL conserva esa representación RAW bajo el nombre engañoso `fmd_template`. La conversión a ANSI 378 sólo ocurre temporalmente en el microservicio de matching.
2. El challenge es opcional en todos los verificadores. Cuando se usa, sí tiene TTL y consumo único dentro de un proceso, pero no está asociado a usuario, acción, documento, sesión ni captura.
3. La discordancia biométrica de un firmante de episodio no falla cerrado: reemplaza la muestra enrolada y devuelve éxito. El fallo del microservicio produce el mismo resultado.
4. La ECDSA médica firma una cadena de metadatos y como máximo 100 caracteres suministrados por el cliente. No firma el contenido clínico canónico, su versión ni el PDF. Los verificadores vuelven a comprobar la cadena almacenada, no el documento vigente.
5. Un reenrolamiento administrativo conserva `huella_token` y la clave privada cifrada. Después del reemplazo, la nueva huella puede desbloquear el uso de la misma clave del médico. Además, el defecto de `require_role()` amplía la operación a cualquier principal autenticado cuando `admin` aparece en la lista permitida.
6. El token RFC 3161 se parsea y se coteja por imprint, pero no se valida su firma CMS ni la confianza del certificado TSA.

## 2. Recorrido técnico reconstruido

### 2.1 Captura en navegador

- `frontend/src/hooks/useDigitalPersona.js:217-242`, función `startCapture()`, llama `FingerprintReader.startAcquisition(SampleFormat.Raw)`.
- En la versión instalada `@digitalpersona/devices 0.2.6`, `frontend/node_modules/@digitalpersona/devices/src/devices/fingerprints/sample.ts:4-14` define `Raw = 1` como **“A raw fingerprint image (bitmap)”**. `frontend/node_modules/@digitalpersona/core/src/biometrics/factor.ts:53-60` diferencia explícitamente `Raw` (imagen), `Intermediate` (feature set) y `Processed` (template).
- `frontend/src/hooks/useDigitalPersona.js:77-108`, `onSamplesAcquired()`, toma `sample.Data`, decodifica el wrapper JSON, extrae `parsed.Data` y `parsed.Format`, y construye:

  ```text
  {"base64":"<bytes de imagen>","metadata":{"width":W,"height":H,"resolution":DPI}}
  ```

- La documentación oficial de HID confirma que una muestra RAW de huella es una imagen, con datos Base64url y metadatos de ancho, alto, DPI, bits por píxel, polaridad y compresión: [HID biometric sample format](https://hidglobal.github.io/digitalpersona-access-management-services/was-cred-format.html). El repositorio oficial del paquete coincide con el código instalado: [HID DigitalPersona devices](https://github.com/hidglobal/digitalpersona-devices/blob/master/src/devices/fingerprints/sample.ts).

### 2.2 API y persistencia

- Ese JSON se envía como `fmd_template` en login, enrolamiento, verificación y firma.
- `backend/models.py:51-70` persiste la muestra médica en `medicos.fmd_template`; `backend/models.py:115-148` hace lo mismo para firmantes de episodio en `biometria_firmantes_episodio.fmd_template`.
- No hay cifrado por registro en estas columnas. La denominación y los comentarios dicen FMD/ANSI, pero el valor real es el JSON RAW producido por el navegador.

### 2.3 Servicio biométrico

- `backend/main.py:334-358` y `backend/main.py:423-456` reenvían la captura y las muestras almacenadas a `http://127.0.0.1:8082/match-bulk`.
- `D:\Escritorio\Teru\Bio-security\server.js:26-49`, `getAnsiFeatureSet()`, parsea el JSON RAW, decodifica `base64` y ejecuta `dpfjCreateFmdFromRaw(..., ANSI_378_2004)`.
- `D:\Escritorio\Teru\Bio-security\server.js:52-108`, `/match-bulk`, convierte a ANSI tanto la muestra entrante como cada muestra almacenada y compara los FMD temporales con `dpfjCompareFeatureSets()`.
- Por tanto, el ANSI FMD existe sólo en memoria del proceso Node durante el match. Lo almacenado y lo transportado por la aplicación es la imagen RAW.

### 2.4 Criptografía médica

- `backend/crypto_fea.py:33-48` genera ECDSA P-256.
- `backend/crypto_fea.py:22-31` deriva una KEK Fernet con HKDF-SHA256 a partir de `huella_token || HES_HMAC_SECRET`, sal e `info` constantes.
- `backend/crypto_fea.py:101-181` descifra la privada y firma `cadena_original.encode('utf-8')` con ECDSA/SHA-256.

### 2.5 Verificación posterior

- `backend/main.py:6449-6766`, `/verificar-integridad`, usa `firma.cadena_original` almacenada siempre que exista.
- `backend/main.py:6775-7107`, `/verificar/documento-estado`, recalcula el hash de esa misma cadena almacenada y verifica la ECDSA contra ella.
- Ninguno vuelve a construir una representación canónica del documento clínico actual ni calcula el PDF actual antes de declarar integridad.

## 3. Hallazgos

## P0-02 — La verificación de firmante acepta huella incorrecta y la convierte en la nueva identidad

**Veredicto: CONFIRMADO**  
**Severidad real: CRÍTICA**

### Flujo completo

1. El frontend selecciona un firmante y captura RAW. `BiometricPatientSignModal.jsx:220-249`, `ejecutarFirma()`, normalmente envía `firmante_id`, `rol_firmante`, formato, slot y muestra.
2. El endpoint `backend/main.py:5945-5972`, `firmar_documento_biometrico_firmante()`, resuelve al paciente, verifica que no esté dado de alta y llama `verificar_huella_firmante_episodio()`.
3. `backend/main.py:387-402` limita candidatos a firmantes `ACTIVO` asociados al paciente/folio y, si existe, al ID o tipo solicitado.
4. Si el firmante no tiene muestra, `backend/main.py:411-418` lo enrola durante la propia firma y devuelve éxito.
5. Si ya tiene muestra, `backend/main.py:420-429` intenta `/match-bulk`. Si coincide, devuelve el firmante.
6. Si no coincide, el servicio responde error, devuelve no-match o no está disponible, `backend/main.py:430-438` sustituye `fmd_template`, cambia `huella_token`, confirma la transacción y devuelve éxito.
7. Sin ID y sin match, `backend/main.py:440-464` toma `firmantes[0]`, sobrescribe su muestra y también devuelve éxito.
8. `backend/main.py:5978-6021` genera un sello `BIO-HES` y registra la firma como activa.

### Validaciones reales que sí existen

- El paciente debe existir y no estar dado de alta (`main.py:5959-5962`).
- El firmante debe estar activo y asociado por `paciente_id` o variantes del folio (`main.py:381-402`).
- Con `firmante_id`, el frontend normal sí hace selección explícita (`BiometricPatientSignModal.jsx:240-247`).
- Hay un intento real de match ANSI si existe muestra previa (`main.py:420-429`).

Estas validaciones no mitigan el defecto central porque todo resultado distinto de match termina en reenrolamiento y éxito.

### Defectos adicionales omitidos por la auditoría anterior

- Cuando se suministra `firmante_id`, `tipo_firmante` no filtra la consulta por el uso de `elif` (`main.py:394-397`). Después, `rol_desc` se toma del rol enviado por el cliente (`main.py:5978-5982`). Es posible etiquetar al mismo registro como paciente, representante o testigo.
- La asociación por episodio usa varias condiciones unidas por `OR`; existe incluso un fallback de actualización por ID global que reasocia un firmante a otro paciente (`main.py:1525-1539`). No es el camino de firma directo, pero debilita la custodia del registro enrolado.
- El sello presencial no es una firma autenticada. Es SHA-256 truncado de datos almacenados y fecha (`main.py:5982`), sin secreto ni clave privada. La verificación pública sólo coteja el hash de la cadena (`main.py:7004-7010`), no recomputa ni autentica `sello_biometrico`.

### Condiciones necesarias para explotar

- Conocer un paciente activo y un firmante, o invocar el camino sin ID.
- Poder llamar al endpoint y suministrar una captura RAW válida de cualquier dedo. Mediante la ruta `/api`, basta un JWT aceptado por el middleware; los alias sin `/api` interactúan con P0-01 y no se reevalúan aquí.
- No se necesita que el microservicio funcione: su caída facilita el fallback.

### Prueba concluyente recomendada

En staging, guardar hash de la fila de A, firmar con B y repetir con el puerto 8082 cerrado. En ambos casos comprobar: HTTP 200, nueva firma activa, `fmd_template` modificado y posterior match de B contra A. La prueba debe ejecutarse también sin `firmante_id` y con dos firmantes activos.

---

## P0-03 — Challenge biométrico opcional y replay

**Veredicto: CONFIRMADO**  
**Severidad real: CRÍTICA**

### Flujo y comprobaciones existentes

- `backend/main.py:270-297` genera un nonce aleatorio de 32 bytes URL-safe, lo guarda en memoria con TTL de 120 segundos y lo elimina al consumirlo.
- Si se presenta un challenge, `backend/main.py:314-315` y `378-379` rechazan expiración o reutilización. El `pop()` ocurre antes del match, por lo que un intento biométrico fallido también consume el nonce.
- Login tiene rate limit de 15/minuto (`main.py:644-646`). El frontend purga memoria y descarta capturas anteriores al montaje (`LoginDual.jsx:44-58`, `127-144`).

### Por qué continúa siendo opcional

- Los esquemas lo declaran `Optional`: `backend/schemas.py:45-49`, `231-236`, `345-364`, y `backend/main.py:5750-5757`.
- Los verificadores sólo llaman a `validate_and_consume_challenge()` si `challenge_id` es truthy (`main.py:314`, `378`). Su ausencia no se rechaza. Además, `validate_and_consume_challenge(None)` retorna `True` (`main.py:284-291`).
- El login real no solicita ni envía challenge: `frontend/src/pages/LoginDual.jsx:73-92`.
- La firma médica principal no lo envía: `frontend/src/pages/PatientDashboard.jsx:1491-1502`.
- Prescripción, suspensión y dieta tampoco lo envían: `PatientDashboard.jsx:1543-1674`.
- La firma de paciente/tutor/testigo no lo envía: `BiometricPatientSignModal.jsx:227-249`.
- Firma Express tampoco lo envía: `frontend/src/pages/FirmaExpress.jsx:134-143`.
- `BiometricSignModal.jsx:37-80` sí intenta obtenerlo, pero inicia la captura en paralelo, permite continuar si la solicitud falla y puede enviar `challenge_id: null`. No es el componente usado por el flujo médico principal de `PatientDashboard`.

### Ausencia de ligaduras

El almacén es `Dict[str, float]`: sólo nonce y expiración. No contiene usuario, médico, sesión, acción, paciente, formato, slot, hash de documento ni compromiso de la captura (`main.py:270-291`). Tampoco se persiste el challenge en `FirmaDocumentoClinico` (`models.py:270-302`). La muestra RAW no incorpora el nonce antes de la extracción del FMD.

El control es además local a un proceso Python. En un despliegue con varios workers no existe almacén común ni consumo atómico distribuido. Esto puede provocar rechazos legítimos si emisión y consumo caen en workers distintos; la omisión del nonce sigue evitando cualquier rechazo.

### Reutilización de captura

Una captura interceptada o extraída de `medicos.fmd_template` puede reenviarse sin modificación. El microservicio convierte de nuevo tanto la captura reenviada como la copia almacenada; una comparación de la muestra consigo misma debería producir el mejor score. En login, el resultado entrega un JWT del médico (`main.py:644-683`). En firma, el mismo RAW vuelve a autorizar el acceso a la clave privada.

### Condiciones necesarias para explotar

- Obtener una captura RAW válida: lectura de PostgreSQL/backup, intercepción del payload, XSS o acceso equivalente.
- Para login no se requiere sesión previa. Para rutas `/api` de firma se requiere cualquier JWT aceptado, pero el firmante biométrico no se liga al sujeto JWT.
- Omitir `challenge_id`; no es necesario robar ni reutilizar un nonce.

### Prueba concluyente recomendada

Reenviar exactamente el mismo payload RAW, sin `challenge_id`, primero a login y después dos veces a firma. Luego probar un challenge válido con usuario, acción, paciente y formato distintos: actualmente todos son aceptados mientras el nonce no se haya consumido.

---

## P0-04 — Se almacena una muestra dactilar RAW, no una plantilla irreversible

**Veredicto: CONFIRMADO**  
**Severidad real: ALTA**

### Qué entrega realmente DigitalPersona

`SampleFormat.Raw` es una imagen bitmap, no una plantilla ni un feature set. Esto está definido tanto en el paquete instalado (`sample.ts:4-14`) como en la documentación oficial de HID. `SamplesAcquired` parsea el payload del WebSDK como `BioSample[]` (`frontend/node_modules/@digitalpersona/devices/src/devices/fingerprints/events.ts:6-23`), donde `BioSample.Data` es Base64url (`@digitalpersona/core/src/biometrics/factor.ts:107-120`).

### Qué llega al navegador y qué se almacena

- El navegador recibe un `BioSample` RAW. Su `Data` envuelve una estructura de imagen que contiene bytes y `Format`.
- `useDigitalPersona.js:83-108` extrae los bytes y conserva ancho, alto y DPI.
- Ese JSON completo llega a FastAPI como texto `fmd_template`.
- PostgreSQL lo almacena sin conversión ni cifrado en `medicos.fmd_template` (`models.py:59-60`) y `biometria_firmantes_episodio.fmd_template` (`models.py:133-135`).

### Dónde se crea el FMD

La única conversión observada está fuera del repositorio principal, en `D:\Escritorio\Teru\Bio-security\server.js:26-49`. `dpfjCreateFmdFromRaw()` crea un FMD ANSI 378 temporal para cada comparación. El servidor no devuelve ese FMD a FastAPI ni lo persiste.

### Reconstrucción biométrica

Sí puede reconstruirse una representación visual de la impresión capturada: la columna conserva bytes de imagen y las dimensiones/resolución necesarias. La aplicación descarta algunos metadatos del wrapper (BPP, padding, polaridad y compresión), pero el camino productivo entrega esos bytes a `dpfjCreateFmdFromRaw()` como buffer RAW; para las muestras que comparan correctamente, ancho, alto y resolución bastan para rearmar la matriz de píxeles con la convención esperada por el lector. Esto no equivale a reconstruir físicamente el dedo, pero sí expone una imagen biométrica reutilizable y visualizable.

### Controles intermedios existentes

- El lector se comunica mediante el agente local y el matcher escucha en `127.0.0.1` (`server.js:111-115`).
- El hook detiene adquisición y purga estado global (`useDigitalPersona.js:47-60`, `108-116`).
- Las muestras de firmantes de episodio se ponen en `NULL` al alta o revocación (`main.py:3434-3447`, `1745-1747`).

No hay purga equivalente para la muestra médica, ni cifrado de columna, ni minimización a FMD. La purga de memoria del navegador no elimina la copia persistida.

### Condiciones necesarias para explotar

Acceso de lectura a la tabla, un backup, un volcado o un payload de red/memoria. No se necesita `HES_HMAC_SECRET` para recuperar la imagen.

### Prueba concluyente recomendada

Sobre datos sintéticos de staging, decodificar `fmd_template.base64`, renderizar con `width × height` y validar visualmente las crestas. Verificar también backups, réplicas y retención después del alta. No usar huellas reales para esta prueba.

---

## P0-05 — La ECDSA no está vinculada al documento clínico completo y la verificación puede declarar integridad falsa

**Veredicto: CONFIRMADO**  
**Severidad real: CRÍTICA**

### Bytes exactos firmados

`backend/main.py:5781-5799` construye la cadena y `backend/crypto_fea.py:174-181` firma exactamente sus bytes UTF-8:

```text
cadena_original =
  "||" + pt_num +
  "|PT-" + pt_num +
  "|" + req.codigo_formato +
  "|" + (req.evolution_slot o "GRAL") +
  "|" + datetime.now().isoformat() +
  "|" + match_found.id +
  "|" + match_found.cedula +
  "|" + req.contenido_resumen[0:100] +
  "||"

mensaje_firmado = UTF8(cadena_original)
firma = ECDSA(secp256r1, SHA256(mensaje_firmado))
hash_sha256_almacenado = hex(SHA256(mensaje_firmado))
```

El corte es de 100 caracteres Unicode antes de codificar a UTF-8. `contenido_resumen` proviene del cliente (`PatientDashboard.jsx:1496-1502`); no se consulta la fila clínica antes de firmar y no existe serialización canónica.

### Ligadura efectiva

| Elemento | ¿Ligado por ECDSA? | Resultado |
|---|---:|---|
| Contenido clínico completo | No | Sólo hasta 100 caracteres enviados por el cliente. |
| Versión del documento | No | `FirmaDocumentoClinico.version` existe (`models.py:296`) pero no entra a la cadena. |
| Paciente | Parcial | Entra el texto `pt_num`, pero no datos canónicos del paciente ni la fila clínica, y después no se contrasta la cadena con los campos de la fila. |
| Médico | Parcial-fuerte | Entran `medico.id` y cédula, y la firma usa su clave; no entra `key-id` ni nombre. |
| Fecha/acto | Parcial | Entra una fecha local ingenua, formato y slot. No entra zona horaria ni propósito estructurado. |
| Tipo de documento | No | `req.tipo_documento` se almacena aparte, pero no se firma. |
| PDF | No | Ningún byte ni hash de PDF entra a la cadena. |

El TSA recibe `hash_sha256` de esta cadena (`main.py:5803-5805`), no el hash del PDF ni de una versión clínica completa.

### Validaciones intermedias existentes

- Se bloquea firma de pacientes dados de alta (`main.py:5766`).
- Se realiza match biométrico real del médico (`main.py:5771-5777`).
- Se intenta comparar el médico asignado en Vertical con el médico biométrico (`main.py:5811-5853`). La comprobación falla abierto ante errores de SQL/estructura, aunque propaga un 403 por discrepancia explícita.
- ECDSA P-256/SHA-256 está implementada correctamente sobre la cadena que recibe (`crypto_fea.py:174-190`).
- Existe `DocumentoVerificacionQR.hash_sha256` (`models.py:364-388`) y `registrar_documento_para_qr()` calcula SHA-256 del PDF (`main.py:3914-3968`). Ésta es una validación omitida por la auditoría anterior.

El último control no corrige el hallazgo: el registro QR puede sobrescribirse al regenerar el mismo `doc_uuid` (`main.py:3942-3950`), el hash no está firmado y las rutas de verificación/descarga no lo recalculan ni comparan antes de declarar/servir (`main.py:6775-7107`, `7609-7723`).

### Qué comprueba realmente la verificación

1. `/verificar-integridad`: si existe `firma.cadena_original`, usa esa copia (`main.py:6570-6573`), calcula su hash y verifica ECDSA (`main.py:6589-6617`). Sólo consulta un fragmento clínico vivo cuando la cadena almacenada falta (`main.py:6574-6585`).
2. `/verificar/documento-estado`: recalcula hash y ECDSA sobre la cadena almacenada (`main.py:6988-7002`). No lee el contenido clínico vigente ni el PDF.
3. Si se pasa `firma_id`, `/verificar-integridad` selecciona la fila por ID sin verificar que pertenezca al `pt_num` de la URL (`main.py:6466-6470`).
4. Ningún verificador analiza la cadena para comprobar que sus campos coincidan con `firma.pt_num`, `codigo_formato`, slot, tipo o versión. Una reasignación de metadatos de la fila puede conservar una ECDSA válida.
5. Cuando no existe firma local, cualquier `ESignature` o `SignedBy` de Vertical produce identidad, integridad, autenticidad y tiempo marcados como verdaderos (`main.py:6497-6564`). `vertical_signer.py:385-395` puede escribir el literal `FIRMADO_BIOMETRICAMENTE` como `ESignature`; el hash mostrado entonces es sólo SHA-256 de ese texto.
6. Para pacientes/tutores/testigos, el verificador público sólo comprueba el hash de la cadena y nunca autentica `BIO-HES` (`main.py:7004-7010`).

### Efecto de una alteración posterior

- **Sí falla:** modificación de `cadena_original`, `hash_sha256` o la firma ECDSA sin producir una firma nueva válida; eliminación de todas las claves públicas capaces de verificarla.
- **No falla:** modificación del contenido clínico en Vertical/PostgreSQL fuera de esa cadena, cambios después del carácter 100, cambio/regeneración del PDF, cambio del tipo textual, cambio de `version`, y diversas reasignaciones de metadatos conservando la cadena.

### Condiciones necesarias para explotar

Editar el documento clínico o reemplazar/regenerar el PDF después de la firma sin alterar la fila `firmas_documentos_clinicos`. No es necesario romper ECDSA. Para la variante Vertical basta una fila con `SignedBy`/`ESignature` no vacío y ausencia de firma local.

### Prueba concluyente recomendada

Firmar D, guardar la respuesta de ambos verificadores, modificar un campo clínico después del carácter 100 y regenerar un PDF diferente. Ambos verificadores deben seguir devolviendo válido en el estado actual. Repetir cambiando un byte de `cadena_original`; ese caso sí debe fallar y sirve como control positivo del test.

---

## P0-06 — Sustitución administrativa de huella permite firmar con la clave de otro médico

**Veredicto: CONFIRMADO**  
**Severidad real: CRÍTICA**

### Flujo completo

1. El panel captura la huella del operador y la envía al médico seleccionado (`frontend/src/pages/AdminDashboard.jsx:544-580`).
2. `PUT /api/medicos/{id}/huella` sustituye directamente `medico.fmd_template` (`backend/main.py:2762-2791`). Sólo crea `huella_token` si estaba vacío; normalmente lo conserva.
3. No se solicita huella anterior, reautenticación del titular, motivo, segunda aprobación ni rotación de claves.
4. Login biométrico o firma envía la huella del operador. El matcher la compara con la nueva muestra del médico y devuelve ese `medico.id` (`main.py:317-350`).
5. `firmar_documento()` deriva la misma KEK porque `huella_token` no cambió, descifra el mismo `private_key_enc` y firma con la clave histórica del médico (`crypto_fea.py:101-181`).

### Hallazgo adicional: el rol está menos restringido de lo que parece

El endpoint declara `require_role(["admin", "rh", "sistemas"])` (`main.py:2770-2773`), pero `require_role()` sólo rechaza si `"admin" not in allowed_roles` (`main.py:562-570`). Como `admin` sí está en esa lista, la condición completa siempre es falsa. En la implementación actual, **cualquier usuario autenticado que resuelva en `get_current_user()` puede invocar el reemplazo**, no sólo admin/RH/sistemas.

La ruta de firma médica tampoco tiene dependencia de rol o ligadura entre el sujeto JWT y `match_found` (`main.py:5759-5777`). Mediante `/api`, cualquier JWT aceptado puede iniciar el acto; la identidad final se toma del match. Tras reemplazar la muestra, el operador también puede usar el login biométrico público para obtener directamente un JWT del médico (`main.py:644-683`).

### Reenrolamiento y claves

- Si el médico ya tenía claves, el reenrolamiento conserva la privada y pública.
- Si no las tenía, el primer acto posterior genera el par a nombre del médico (`crypto_fea.py:50-99`), ya bajo la biometría sustituida.
- La huella no deriva la KEK. Sólo autoriza lógicamente el camino que usa el UUID `huella_token` almacenado.

### Condiciones necesarias para explotar

Un JWT válido de cualquier cuenta, conocer el ID del médico y tener acceso físico a un lector para capturar la huella del operador. No se requiere conocer `HES_HMAC_SECRET`, extraer la privada ni presentar al médico.

### Prueba concluyente recomendada

En staging, registrar hashes de `public_key_pem`, `private_key_enc` y `huella_token`; reemplazar la muestra con una cuenta de rol mínimo; hacer login con la nueva huella y firmar. Los tres valores criptográficos deben permanecer iguales y la firma verificar con la clave pública anterior.

---

## P1-01 — Custodia y rotación de claves

**Veredicto: CONFIRMADO PARCIALMENTE**  
**Severidad real: ALTA**

### Cifrado y secreto de recuperación

- La privada se genera como PKCS#8 PEM sin cifrado interno (`crypto_fea.py:33-41`).
- Después se cifra con Fernet (`crypto_fea.py:71-75`).
- La clave Fernet se deriva por HKDF-SHA256 de `huella_token || HES_HMAC_SECRET`, con sal e `info` constantes (`crypto_fea.py:16-31`).
- `huella_token` es un UUID aleatorio guardado junto al ciphertext en `medicos` (`models.py:59-70`; creación en `main.py:1818-1852`). No es un secreto derivado de la huella.

Una copia de PostgreSQL por sí sola no basta; una copia de PostgreSQL **más** `HES_HMAC_SECRET` permite derivar todas las KEK y descifrar todas las privadas. Puede recuperarlas cualquier proceso u operador con ambos accesos. Un usuario de UI no obtiene la privada directamente, pero P0-06 le permite provocar su uso sin conocerla.

### Reenrolamiento

`update_medico_huella()` cambia sólo `fmd_template`; conserva token, clave privada y pública (`main.py:2784-2787`). Por tanto, el reenrolamiento no rota la clave aunque la documentación diga lo contrario.

### Rotación real

No existe ceremonia o endpoint explícito de rotación. En `crypto_fea.py:118-167`, cualquier excepción durante el descifrado —incluido ciphertext vacío/corrupto, secreto cambiado u otro error— entra al mismo `except`, inactiva claves marcadas activas, genera un nuevo par, lo guarda y confirma.

Matiz frente a la auditoría anterior: errores al importar/crear/agregar el registro histórico pueden ser tragados (`crypto_fea.py:126-164`), pero un fallo de base durante `commit()` no está capturado en esa sección y normalmente abortará la solicitud. Por eso el enunciado “si insertar historia falla, el error siempre se ignora” es demasiado amplio.

### Verificación histórica

- Primero se prueba la clave pública actual y después todas las filas históricas del médico, sin filtrar `activo`, fecha o vigencia (`crypto_fea.py:195-239`).
- `FirmaDocumentoClinico` no guarda `key-id` (`models.py:270-302`). La clave que verificó no queda identificada inequívocamente.
- `HistorialLlaveFEA` no tiene unicidad de clave activa, restricción append-only ni evidencia de trigger en el código (`models.py:83-93`).
- Si el historial persistido contiene la clave antigua, las firmas antiguas siguen verificando. Si falta y la clave corriente ya rotó, `_historical_keys` es sólo una ayuda en memoria (`crypto_fea.py:147-151`, `233-237`) y no garantiza verificación tras reinicio.
- La documentación exige verificación por médico + fecha y auditoría de toda rotación (`docs/decisiones/ADR-0002-fea-historial-llaves.md`), pero el código no usa fecha ni registra un `AuditoriaLog` de rotación.

### Parte confirmada y parte pendiente

Está confirmado el modelo de custodia centralizada, la recuperación con BD + secreto global, la rotación automática por error, la ausencia de key-id y la búsqueda indiscriminada por todas las claves. Requiere inspección dinámica del esquema productivo confirmar si existen triggers, permisos o controles externos no declarados que impidan `UPDATE/DELETE` y múltiples claves activas.

### Prueba concluyente recomendada

En una copia de staging: descifrar una clave con token + secreto; corromper un byte de Fernet y comprobar la rotación; reiniciar el proceso y verificar una firma anterior; consultar `pg_trigger`, constraints y grants de `historial_llaves_fea`; insertar dos claves activas y medir el resultado.

---

## P1-02 — TSA RFC 3161 parseado pero no verificado criptográficamente

**Veredicto: CONFIRMADO**  
**Severidad real: ALTA**

### Qué sí se valida

- La solicitud declara SHA-256, solicita certificado y se envía por HTTPS usando la validación TLS predeterminada de `urllib` (`backend/tsa_client.py:96-123`).
- Se valida el `PKIStatus` y que exista token (`tsa_client.py:125-136`).
- Se parsean `ContentInfo`, `SignedData` y `TSTInfo`, y se compara `messageImprint.hashedMessage` con el hash esperado (`tsa_client.py:80-93`, `136-147`).
- En verificación posterior se repite el parseo y el cotejo del imprint (`tsa_client.py:153-175`).

### Qué no se valida

- Firma CMS de `SignerInfo`.
- `messageDigest` de atributos firmados y correspondencia con `eContent`.
- Certificado firmante, cadena de confianza, ancla/pinning, identidad de la TSA.
- EKU `timeStamping`, uso de clave, vigencia, política, revocación OCSP/CRL.
- Algoritmo del `messageImprint` recibido; sólo se comparan los bytes.
- Coherencia criptográfica de `genTime`, serial y policy con un firmante confiable.
- Nonce. La clase lo soporta (`tsa_client.py:46-54`), pero la petición lo omite deliberadamente (`tsa_client.py:102-113`).

`verify_timestamp()` marca `verificado=True` únicamente por `imprint_ok` (`tsa_client.py:160-171`). El campo `autoridad` es la URL configurada, no la identidad extraída y autenticada del certificado.

### Matiz sobre replay

La ausencia de nonce no permite reutilizar un token para un hash diferente: el cotejo de imprint lo impide salvo colisión SHA-256. Sí permite reutilizar una respuesta para el mismo hash y elimina la prueba de frescura solicitud-respuesta. El riesgo principal no es ese replay cruzado, sino aceptar como “verificado” un CMS sintácticamente válido con firma o certificado no confiable.

La política no bloqueante está explícita (`tsa_client.py:1-7`, `148-150`): una firma puede quedar sin TSA. Sin embargo, no existe en el modelo un estado de cola o “pendiente de countersign”; sólo `tsa_token = NULL` (`models.py:290`).

### Condiciones necesarias para explotar

Poder sustituir/inocular el token almacenado, comprometer la TSA/transporte o proporcionar una respuesta manipulada al cliente. El atacante debe conservar el imprint esperado, pero no necesita una firma CMS válida frente al verificador actual.

### Prueba concluyente recomendada

Generar un `TimeStampToken` ASN.1/CMS con el imprint correcto y una firma aleatoria o certificado autofirmado no confiable. `verify_timestamp()` debe marcarlo actualmente como verificado si el contenido es parseable. Repetir con algoritmo de imprint distinto, EKU ausente, certificado expirado y nonce incorrecto.

---

## P1-04 — Doble submit/doble firma sin idempotencia ni unicidad

**Veredicto: CONFIRMADO PARCIALMENTE**  
**Severidad real: ALTA**

### Backend confirmado

- `FirmaDocumentoClinico` sólo tiene un índice no único sobre paciente/formato/slot/estado (`backend/models.py:270-302`).
- Los endpoints no aceptan `Idempotency-Key`, request ID ni versión esperada.
- La firma médica consulta activas, las marca revocadas y luego inserta una nueva (`main.py:5855-5891`) sin `SELECT ... FOR UPDATE`, bloqueo por documento ni restricción única parcial.
- La firma de firmante hace lo mismo (`main.py:5986-6021`).

Dos transacciones concurrentes pueden leer el mismo estado previo, revocar las mismas filas y confirmar cada una una nueva fila `ACTIVA`. Si no había firma previa, ambas insertan directamente. Las cadenas serán distintas porque cada solicitud toma su propio `datetime.now()`, de modo que no existe deduplicación natural.

### Mitigaciones frontend que la auditoría anterior subestimó

- El manejador global detiene adquisición después de la primera muestra (`useDigitalPersona.js:108-111`).
- Los modales comprueban `submitting`, y Firma Express deshabilita el botón mientras procesa (`BiometricSignModal.jsx:63-68`; `BiometricPatientSignModal.jsx:220-236`; `FirmaExpress.jsx:134-143`, `390-395`).
- Los efectos dependen principalmente del cambio de `dpFmd`; una notificación con exactamente el mismo string no necesariamente vuelve a ejecutar el efecto.

Estas medidas reducen la probabilidad de doble POST causado por un solo gesto normal, por lo que esa parte no queda plenamente reproducida mediante inspección estática. No protegen contra dos eventos RAW distintos antes de consolidar estado, doble clic en otra ruta, reintento de red, dos pestañas ni solicitudes concurrentes directas.

### Condiciones necesarias para explotar

Dos peticiones válidas concurrentes con el mismo paciente, formato, slot y rol. Para firma médica, cada una debe superar el match; P0-03 permite reutilizar el mismo RAW sin challenge. Se requiere una intercalación en la que ambas consultas de activas ocurran antes del primer commit o, si no había firma, simplemente dos commits exitosos.

### Prueba necesaria

Prueba dinámica con barrera de concurrencia y 20 solicitudes idénticas contra PostgreSQL real. Debe medirse número de filas activas, revocadas, writes a Vertical y respuestas. También debe instrumentarse el navegador/lector para determinar si dos `SamplesAcquired` producen dos POST en el flujo real. Hasta esa prueba, queda confirmada la condición de carrera de backend, no la frecuencia exacta del disparador React.

## 4. Tabla final

| HALLAZGO | VEREDICTO TÉCNICO | SEVERIDAD REAL | EVIDENCIA | PRUEBA NECESARIA | CAMBIO MÍNIMO RECOMENDADO |
|---|---|---|---|---|---|
| P0-02 | **CONFIRMADO** | **CRÍTICA** | `main.py:363-464` reemplaza muestra en mismatch/error y retorna éxito; `main.py:5945-6021` firma después. | Huella B contra A, servicio 8082 caído y caso sin ID; comprobar mutación de fila y firma activa. | Separar enrolamiento de verificación; mismatch/error siempre falla cerrado; ID de firmante obligatorio y ligado a episodio/rol. |
| P0-03 | **CONFIRMADO** | **CRÍTICA** | `main.py:270-315`, `378-379`; parámetros opcionales en esquemas; login y flujos principales no envían challenge. | Replay exacto sin nonce en login/firma; cruce de nonce entre usuario/acción/documento; prueba multiworker. | Challenge obligatorio, persistido y consumido atómicamente, ligado a sesión, usuario, acción, paciente, documento y captura posterior. |
| P0-04 | **CONFIRMADO** | **ALTA** | `useDigitalPersona.js:77-108`, `217-242`; SDK `SampleFormat.Raw`; `models.py:59-60`, `133-135`; conversión sólo en `server.js:26-49`. | Decodificar una muestra sintética almacenada y renderizar la matriz; revisar backups y retención. | Persistir sólo plantilla adecuada o referencia a vault biométrico; cifrado por registro y migración/purga controlada del RAW. |
| P0-05 | **CONFIRMADO** | **CRÍTICA** | Cadena en `main.py:5789`; ECDSA en `crypto_fea.py:174-190`; verificación de cadena almacenada en `main.py:6570-6617`, `6988-7002`; fallback Vertical `6497-6564`. | Alterar contenido/PDF después de firmar y comparar ambos verificadores; control cambiando un byte de la cadena. | Firma sobre representación canónica/versionada completa y/o hash del PDF, con propósito y key-id; verificación contra contenido vigente/snapshot inmutable. |
| P0-06 | **CONFIRMADO** | **CRÍTICA** | Reemplazo en `main.py:2762-2791`; bug de roles `562-570`; token/clave conservados; descifrado en `crypto_fea.py:101-181`. | Reemplazo con rol mínimo, login como médico y firma conservando hashes de token/clave. | Reenrolamiento con presencia del titular, control dual y rotación explícita; corregir autorización y ligar firmante JWT con identidad biométrica. |
| P1-01 | **CONFIRMADO PARCIALMENTE** | **ALTA** | HKDF/Fernet `crypto_fea.py:16-31`, `71-75`; rotación por excepción `118-167`; verificación con cualquier histórica `195-239`; sin key-id en `models.py:270-302`. | Fault injection, reinicio, verificación histórica y consulta de triggers/grants/constraints productivos. | Key-id por firma; rotación explícita/transaccional; historia protegida en DB; custodia KMS/HSM o factor realmente bajo control del médico. |
| P1-02 | **CONFIRMADO** | **ALTA** | `_parse_token()` sólo parsea/imprint (`tsa_client.py:80-93`); `verify_timestamp()` usa `imprint_ok` (`153-175`); sin nonce `102-113`. | Tokens con firma CMS inválida, certificado no confiable/expirado, EKU ausente, algoritmo/nonce incorrectos. | Verificador RFC 3161/CMS completo con trust store/pinning, nonce y estado explícito de sellado pendiente/fallido. |
| P1-04 | **CONFIRMADO PARCIALMENTE** | **ALTA** | Índice no único `models.py:300-302`; revoca+inserta sin lock `main.py:5855-5891`, `5986-6021`; existen guardas UI parciales. | Barrera concurrente con 20 POST y lector instrumentado; contar activas, revocadas y writes Vertical. | Idempotency key y restricción única de firma activa/versionada, más transacción/bloqueo por documento. |


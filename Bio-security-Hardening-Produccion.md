# Bio-security — Plan de Hardening y Puesta en Producción

## Sistema biométrico y de firma electrónica para entorno hospitalario

**Repositorio:** `TeruIshijo1/Bio-security`  
**Fecha:** 31 de agosto de 2026  
**Objetivo:** llevar la implementación actual a un nivel adecuado para producción hospitalaria, sujeto a validación legal, institucional y de seguridad.

---

# 1. Resumen ejecutivo

El proyecto `Bio-security` implementa:

- Captura biométrica mediante DigitalPersona.
- Conversión/matching basado en ANSI 378.
- Generación de claves ECDSA P-256.
- SHA-256 para firmas.
- Cifrado de claves privadas.
- Derivación mediante HKDF-SHA256.
- Sellado de tiempo mediante RFC 3161.
- Verificación de firmas con comportamiento `fail-closed`.

La arquitectura es una buena base, pero **no debe considerarse lista para producción hospitalaria todavía**.

Las prioridades son:

1. Eliminar el fallback criptográfico hacia la cédula.
2. Versionar las claves ECDSA.
3. Mantener verificables las firmas históricas después de cambiar la huella.
4. Aislar el microservicio biométrico.
5. Eliminar CORS abierto.
6. Implementar autenticación entre servicios.
7. Implementar challenge/nonce anti-replay.
8. Proteger los templates biométricos.
9. Fortalecer la gestión de secretos.
10. Validar completamente los tokens RFC 3161.
11. Implementar auditoría de seguridad.
12. Medir FAR/FRR antes de fijar definitivamente el threshold.
13. Realizar pruebas de penetración antes del Go-Live.

> **Regla de Go-Live:** no poner el sistema en producción mientras exista algún riesgo ALTO o CRÍTICO sin mitigar o aceptar formalmente por el responsable de seguridad institucional.

---

# 2. Arquitectura actual

El microservicio biométrico actual expone:

```http
POST /match-bulk
```

y recibe una huella junto con templates de médicos para realizar matching.

Actualmente el servicio utiliza:

```javascript
const falseAcceptRate = 10000;
```

y:

```javascript
if (score <= falseAcceptRate)
```

También se observa:

```javascript
app.use(cors());
```

y:

```javascript
const PORT = 8082;
app.listen(PORT, ...);
```

El código biométrico convierte la muestra a ANSI 378 y utiliza DigitalPersona/U.are.U para realizar la comparación.

---

# 3. Arquitectura criptográfica actual

La implementación actual genera:

```text
ECDSA
  └── SECP256R1 / P-256
       └── SHA-256
```

La clave privada se serializa como PKCS#8 y se cifra antes de almacenarse.

La KEK se deriva actualmente mediante:

```text
HKDF-SHA256(
    huella_token + HES_HMAC_SECRET
)
```

La firma tiene la forma:

```text
ECDSA:<base64(signature)>
```

El sistema también incorpora cliente RFC 3161 para obtener un `TimeStampToken`.

---

# 4. Lo que está bien

## 4.1 Separación biometría / firma

La huella no se utiliza directamente como firma digital.

El modelo correcto es:

```text
Huella
  ↓
Autenticación
  ↓
Autorización
  ↓
Uso controlado de clave privada
  ↓
ECDSA
```

Esto debe conservarse.

La biometría **autentica al usuario**; ECDSA **firma criptográficamente el contenido**.

---

## 4.2 ECDSA P-256

El uso de:

```text
ECDSA + SECP256R1 + SHA-256
```

es una elección razonable para el mecanismo de firma.

---

## 4.3 Clave privada cifrada

No se almacena la clave privada ECDSA directamente en texto claro.

La implementación actual cifra la clave privada y almacena `private_key_enc`.

Esto es correcto como principio, aunque el mecanismo de gestión de claves debe endurecerse para producción.

---

## 4.4 HKDF

El uso de HKDF-SHA256 como KDF es apropiado como primitiva criptográfica.

El problema no es HKDF en sí, sino **qué material secreto se introduce en ella y cómo se gestiona ese material**.

---

## 4.5 Fail-closed

Cuando una firma ECDSA no puede verificarse correctamente:

```python
return False
```

Esto es correcto.

En seguridad:

```text
error → rechazar
```

es preferible a:

```text
error → permitir
```

---

## 4.6 RFC 3161

La arquitectura:

```text
Documento
   ↓
SHA-256
   ↓
TSA RFC 3161
   ↓
TimeStampToken
```

es adecuada para proporcionar evidencia temporal independiente.

Sin embargo, la validación del token debe ser más completa antes de producción.

---

# 5. Hallazgos de seguridad

---

## H-01 — Fallback criptográfico hacia la cédula

### Severidad: ALTA

La implementación actual utiliza:

```python
token = medico.huella_token or medico.cedula
```

Esto es incorrecto para material criptográfico.

La cédula es un identificador, no un secreto.

### Riesgo

Si no existe `huella_token`, la clave criptográfica termina dependiendo de:

```text
cédula + secreto del servidor
```

La cédula puede ser conocida o deducida.

### Corrección obligatoria

Eliminar completamente:

```python
or medico.cedula
```

y utilizar:

```python
token = medico.huella_token

if not token:
    raise SecurityError(
        "No existe material biométrico criptográfico"
    )
```

El comportamiento debe ser:

```text
sin material biométrico
        ↓
NO FIRMA
```

Nunca:

```text
sin huella
   ↓
cédula
   ↓
firma
```

---

# 6. H-02 — Rotación destructiva de claves

### Severidad: ALTA

Actualmente, cuando la clave privada no puede descifrarse con la KEK actual, se genera un nuevo par ECDSA.

Esto significa que:

```text
ECDSA Key #1
   ↓
firmas históricas
   ↓
cambio/re-registro biométrico
   ↓
ECDSA Key #2
```

y la clave pública actual puede dejar de corresponder con las firmas históricas.

Esto es inaceptable para una bitácora médica.

## Corrección obligatoria

Implementar versionado de claves.

Modelo recomendado:

```text
medical_signing_keys

id
medico_id
key_version
algorithm
curve
public_key_pem
private_key_enc
status
created_at
activated_at
retired_at
revoked_at
revocation_reason
```

Estados:

```text
ACTIVE
RETIRED
REVOKED
```

Cada firma debe guardar:

```text
signature_id
medico_id
key_id
algorithm
document_hash
signature
signed_at
tsa_token
```

La verificación debe utilizar:

```text
signature.key_id
        ↓
clave pública histórica
        ↓
verificación
```

y no simplemente:

```text
médico → clave actualmente activa
```

### Resultado deseado

Si el médico cambia su huella:

```text
Key v1 → RETIRED
Key v2 → ACTIVE
```

Las firmas hechas con `Key v1` deben continuar siendo verificables.

---

# 7. H-03 — Exposición del microservicio biométrico

### Severidad: ALTA

El servicio actual escucha en:

```text
8082
```

y no se observa autenticación propia del endpoint.

## Riesgo

Un atacante con acceso al puerto podría intentar interactuar directamente con el motor biométrico.

## Arquitectura recomendada

Si el backend y servicio biométrico están en el mismo servidor:

```text
127.0.0.1:8082
```

El navegador nunca debe acceder directamente.

Arquitectura:

```text
Browser
   │
   │ HTTPS
   ▼
Backend
   │
   │ local / IPC
   ▼
Biometric Service
   │
   ▼
DigitalPersona
```

Si el servicio está en otro servidor:

```text
Backend
   │
   │ mTLS
   ▼
Biometric Service
```

---

# 8. H-04 — CORS abierto

### Severidad: ALTA

Actualmente:

```javascript
app.use(cors());
```

Esto debe eliminarse.

La arquitectura preferida es:

```text
Browser
   X
Biometric Service
```

El navegador debe hablar únicamente con el backend.

Si CORS es absolutamente necesario, usar una allowlist explícita:

```javascript
app.use(cors({
    origin: [
        'https://dominio-hospitalario'
    ],
    methods: ['POST'],
    credentials: true
}));
```

Nunca usar:

```javascript
cors()
```

sin restricciones en producción.

---

# 9. H-05 — Protección contra replay

### Severidad: ALTA

No debe aceptarse una autenticación biométrica como una petición reutilizable.

Implementar challenge/nonce.

## Flujo

```text
1. Backend genera nonce.
2. Nonce tiene expiración corta.
3. Usuario realiza autenticación.
4. Servicio biométrico valida huella.
5. Backend consume nonce.
6. Nonce no puede reutilizarse.
```

Generación:

```python
nonce = secrets.token_bytes(32)
```

El challenge debe tener al menos 128 bits de entropía.

Modelo:

```text
challenge_id
nonce_hash
session_id
created_at
expires_at
used_at
```

Condición de éxito:

```text
nonce válido
AND
nonce no utilizado
AND
huella válida
AND
usuario autorizado
```

---

# 10. H-06 — Protección de templates biométricos

### Severidad: ALTA

Los templates biométricos deben considerarse información extremadamente sensible.

Evitar almacenar innecesariamente:

- imágenes de huellas;
- fotografías;
- RAW;
- información biométrica adicional.

Conservar únicamente el material necesario para el matching.

## Protección

```text
Template
   ↓
Cifrado en reposo
   ↓
Acceso exclusivo del servicio biométrico
```

Además:

- auditoría de cada lectura;
- permisos mínimos;
- protección de backups;
- eliminación conforme a política institucional;
- prohibición de acceso desde frontend.

> Una contraseña puede cambiarse. Una huella comprometida no puede sustituirse de la misma manera.

---

# 11. H-07 — Threshold biométrico

### Severidad: MEDIA/ALTA

Actualmente:

```text
falseAcceptRate = 10000
```

No debe asumirse que ese número representa automáticamente un FAR específico.

Debe medirse.

## FAR

```text
FAR =
falsos positivos /
intentos impostores
```

## FRR

```text
FRR =
falsos negativos /
intentos genuinos
```

Realizar pruebas con:

- múltiples usuarios;
- múltiples dedos;
- múltiples capturas;
- diferentes condiciones;
- intentos genuinos;
- intentos impostores.

El threshold definitivo debe basarse en resultados medidos.

---

# 12. H-08 — Validación completa de RFC 3161

### Severidad: MEDIA/ALTA

Actualmente se verifica que el imprint del token coincida con el hash esperado.

Eso es necesario, pero no suficiente para una validación completa.

Debe validarse también:

- estructura CMS;
- firma del TSA;
- certificado del TSA;
- cadena de confianza;
- periodo de validez;
- EKU apropiado;
- política TSA;
- revocación cuando aplique;
- algoritmo;
- integridad completa del token.

No considerar:

```text
ASN.1 válido
+
imprint correcto
=
TSA completamente confiable
```

La validación debe comprobar la confianza criptográfica del emisor.

---

# 13. H-09 — Gestión de secretos

### Severidad: ALTA

Actualmente:

```text
HES_HMAC_SECRET
```

se obtiene del entorno.

Esto es mejor que hardcodearlo, pero en producción hospitalaria se recomienda un sistema dedicado:

- Vault;
- KMS;
- Secret Manager;
- HSM.

Los secretos nunca deben estar:

- en Git;
- en el frontend;
- en logs;
- en respuestas HTTP;
- dentro del código;
- dentro de imágenes Docker;
- en backups sin protección.

---

# 14. Diseño criptográfico objetivo

La arquitectura objetivo debe separar:

## Autenticación

```text
Huella
   ↓
Matching
   ↓
Identidad autenticada
```

## Autorización

```text
Identidad
   +
Sesión
   +
Rol
   +
Operación
   ↓
Autorizado
```

## Firma

```text
Documento
   ↓
SHA-256
   ↓
ECDSA P-256
   ↓
Firma
```

## Evidencia temporal

```text
Hash
   ↓
TSA RFC 3161
   ↓
TimeStampToken
```

---

# 15. No convertir la huella directamente en una clave

No utilizar:

```text
huella
  ↓
SHA-256
  ↓
clave privada
```

ni:

```text
huella
  ↓
hash
  ↓
firma
```

La biometría debe ser un mecanismo de autenticación.

La criptografía debe manejar las claves criptográficas.

---

# 16. Protección de claves privadas

Para una arquitectura nueva puede evaluarse:

```text
AES-256-GCM
```

como AEAD.

Cada registro debería incluir:

```text
crypto_version
kek_id
algorithm
nonce
ciphertext
tag
created_at
```

Nunca reutilizar un nonce con la misma clave.

Para un nivel superior:

```text
HSM/KMS
   ↓
clave criptográfica
```

Idealmente la clave privada de firma no debería salir del módulo criptográfico cuando la infraestructura disponible lo permita.

---

# 17. Key Management

Cada clave debe tener:

```text
key_id
version
status
created_at
activated_at
retired_at
revoked_at
revocation_reason
```

Estados:

```text
GENERATED
ACTIVE
RETIRED
ARCHIVED
REVOKED
```

Una clave comprometida:

```text
ACTIVE → REVOKED
```

Una clave reemplazada:

```text
ACTIVE → RETIRED
```

No eliminar automáticamente claves necesarias para verificar firmas históricas.

---

# 18. Autorización

La huella válida no debe significar:

```text
puede hacer cualquier cosa
```

La decisión debe ser:

```text
huella válida
AND
sesión válida
AND
rol válido
AND
operación permitida
AND
recurso permitido
```

Ejemplo:

```text
Puede firmar este expediente
```

no:

```text
Puede firmar cualquier expediente
```

---

# 19. Rate limiting

El servicio biométrico debe limitar intentos.

Ejemplo inicial para evaluar:

```text
10 intentos/minuto/dispositivo
30 intentos/5 minutos/identidad
```

Los valores definitivos deben determinarse mediante pruebas.

Después de fallos repetidos:

```text
fallo
 ↓
delay progresivo
 ↓
bloqueo temporal
 ↓
alerta
```

Evitar bloqueos permanentes únicamente por fallos biométricos para no facilitar DoS contra médicos.

---

# 20. Evitar un oráculo biométrico

No permitir arbitrariamente:

```text
huella A
   ↓
score contra médico X
```

El backend debe controlar:

- identidad;
- contexto;
- operación;
- sesión;
- médico objetivo.

Cuando sea posible, preferir:

```text
1:1 matching
```

sobre:

```text
1:N matching
```

porque reduce la superficie de ataque.

---

# 21. No devolver información biométrica innecesaria

El frontend preferentemente debe recibir:

```json
{
    "authenticated": true,
    "subject_id": "...",
    "challenge_id": "..."
}
```

y no:

```json
{
    "score": 7321,
    "template": "...",
    "raw": "..."
}
```

El score debe mantenerse interno salvo que exista una razón operacional justificada.

---

# 22. Endpoint recomendado

Conceptualmente:

```http
POST /internal/biometric/verify
Authorization: Bearer <short-lived-token>
X-Request-ID: <uuid>
```

Payload:

```json
{
    "challenge_id": "...",
    "biometric_sample": "...",
    "device_id": "..."
}
```

Respuesta:

```json
{
    "authenticated": true,
    "subject_id": "...",
    "challenge_id": "..."
}
```

---

# 23. Flujo de firma definitivo

```text
Usuario
   ↓
Sesión autenticada
   ↓
Solicita firma
   ↓
Backend verifica autorización
   ↓
Backend genera challenge
   ↓
Usuario coloca dedo
   ↓
Servicio biométrico realiza matching
   ↓
Challenge se consume
   ↓
Identidad autenticada
   ↓
Backend obtiene clave versionada
   ↓
Hash SHA-256 del documento
   ↓
Firma ECDSA P-256
   ↓
Solicitud TSA RFC 3161
   ↓
Validación del token
   ↓
Persistencia
   ↓
Auditoría
```

---

# 24. Registro de una firma

Guardar como mínimo:

```text
signature_id
document_id
document_hash
medico_id
key_id
algorithm
signature
signed_at
tsa_token
tsa_gen_time
tsa_serial
created_at
```

El hash debe representar exactamente el documento que fue firmado.

Si el documento cambia:

```text
SHA256(documento_original)
    !=
SHA256(documento_modificado)
```

y la verificación debe fallar.

---

# 25. Auditoría

Eventos mínimos:

| Evento | Información |
|---|---|
| Intento biométrico | fecha, dispositivo, resultado, request_id |
| Match exitoso | identidad, dispositivo, request_id |
| Match fallido | fecha, dispositivo, motivo general |
| Firma | médico, documento, key_id, hash |
| Verificación | documento, key_id, resultado |
| Rotación | key anterior, key nueva |
| Revocación | key_id, motivo, operador |
| TSA | serial, genTime, autoridad |
| Cambio administrativo | usuario, acción, fecha |

Nunca registrar:

- templates biométricos;
- imágenes de huella;
- claves privadas;
- secretos;
- tokens de sesión;
- credenciales.

---

# 26. Integridad de auditoría

Para eventos críticos puede implementarse una cadena de hashes:

```text
H_n = SHA256(H_(n-1) || Evento_n)
```

Resultado:

```text
H0 → H1 → H2 → H3 → ...
```

Además, enviar logs críticos a un sistema externo/SIEM.

Esto dificulta que un atacante con acceso a la aplicación pueda modificar silenciosamente toda la evidencia.

---

# 27. TLS

Todo tráfico remoto debe utilizar:

```text
HTTPS/TLS
```

y para comunicación backend → servicio biométrico remoto:

```text
mTLS
```

Evitar:

- HTTP;
- TLS obsoleto;
- certificados sin control;
- configuraciones criptográficas débiles.

---

# 28. Base de datos

Separar usuarios de BD:

```text
app_runtime
migration_user
audit_user
admin_user
```

La aplicación no debe conectarse como:

```text
sa
root
postgres
admin
```

El usuario de runtime debe tener solamente los permisos necesarios.

---

# 29. Backups

Los backups deben:

- estar cifrados;
- tener control de acceso;
- tener política de retención;
- tener protección contra borrado accidental;
- tener pruebas periódicas de restauración.

Proceso:

```text
Backup
  ↓
Restore
  ↓
Validación
```

Las claves de cifrado no deben almacenarse junto con los backups.

---

# 30. Hardening del servidor

Producción debe utilizar:

- usuario sin privilegios;
- firewall;
- puertos mínimos;
- actualizaciones de seguridad;
- EDR/antimalware institucional;
- servicios innecesarios deshabilitados;
- logs;
- NTP;
- backups;
- monitoreo.

El puerto biométrico `8082` no debe estar abierto a toda la red.

---

# 31. Contenedores

Si se utiliza Docker:

- usuario no root;
- imágenes mínimas;
- filesystem read-only cuando sea posible;
- secrets externos;
- límites de CPU;
- límites de memoria;
- health checks;
- redes internas;
- sin capacidades Linux innecesarias.

Nunca:

```dockerfile
COPY .env .
```

---

# 32. Dependencias

Antes de producción:

```bash
npm audit
```

y ejecutar herramientas equivalentes para Python.

También:

- revisar dependencias transitorias;
- bloquear versiones;
- mantener actualizaciones;
- generar SBOM;
- revisar vulnerabilidades;
- establecer proceso de actualización.

---

# 33. DLL biométricas

El repositorio contiene DLL nativas del stack DigitalPersona.

Estas DLL deben:

1. proceder de una fuente confiable;
2. tener versión conocida;
3. tener hash registrado;
4. tener firma digital validada cuando corresponda;
5. no poder ser reemplazadas por usuarios sin privilegios.

Debe evitarse que un atacante pueda sustituir:

```text
dpfj.dll
dpfpdd.dll
```

por una DLL maliciosa.

---

# 34. Pruebas funcionales

## Autenticación

- huella correcta;
- huella incorrecta;
- dedo diferente;
- usuario inexistente;
- dispositivo no autorizado;
- sesión expirada;
- challenge expirado;
- challenge reutilizado;
- múltiples intentos.

## Criptografía

- firma válida;
- documento modificado;
- firma modificada;
- clave incorrecta;
- clave revocada;
- clave retirada;
- rotación;
- verificación histórica.

## TSA

- token válido;
- token corrupto;
- hash incorrecto;
- certificado inválido;
- certificado expirado;
- TSA indisponible;
- TSA rechazando petición.

---

# 35. Pruebas de ataque

Realizar pruebas controladas de:

- replay;
- replay de firma;
- manipulación del documento;
- manipulación del score;
- acceso directo al puerto 8082;
- enumeración de médicos;
- modificación de templates;
- extracción de secretos;
- sustitución de DLL;
- SQL injection;
- path traversal;
- SSRF;
- abuso de CORS;
- brute force;
- DoS;
- robo de sesión;
- escalamiento de privilegios.

Estas pruebas deben realizarse con autorización institucional.

---

# 36. Matriz de riesgos

| ID | Riesgo | Severidad | Mitigación |
|---|---|---|---|
| H-01 | Fallback hacia cédula | ALTA | Eliminar fallback |
| H-02 | Rotación destructiva ECDSA | ALTA | Versionar claves |
| H-03 | Servicio biométrico expuesto | ALTA | Aislamiento/mTLS |
| H-04 | CORS abierto | ALTA | Eliminar o allowlist |
| H-05 | Replay | ALTA | Challenge de un solo uso |
| H-06 | Compromiso de template | ALTA | Cifrado y aislamiento |
| H-07 | Threshold sin validación estadística | MEDIA/ALTA | FAR/FRR |
| H-08 | Validación TSA incompleta | MEDIA/ALTA | Validación CMS/certificados |
| H-09 | Gestión de secretos | ALTA | Vault/KMS/HSM |
| H-10 | Auditoría insuficiente | MEDIA | Audit trail robusto |

---

# 37. Checklist de Go-Live

## Seguridad criptográfica

- [ ] El fallback a cédula fue eliminado.
- [ ] ECDSA P-256 está implementado correctamente.
- [ ] SHA-256 está implementado correctamente.
- [ ] Las claves privadas están cifradas.
- [ ] Las claves tienen `key_id`.
- [ ] Las claves están versionadas.
- [ ] Existe revocación.
- [ ] Las firmas históricas siguen siendo verificables.
- [ ] Existe estrategia de gestión de secretos.

## Biometría

- [ ] Templates protegidos.
- [ ] No se almacenan imágenes innecesarias.
- [ ] Matching validado.
- [ ] FAR medido.
- [ ] FRR medido.
- [ ] Threshold validado.
- [ ] Existe protección contra replay.
- [ ] Existe rate limiting.
- [ ] Existe protección contra enumeración/oráculo.

## API

- [ ] CORS abierto eliminado.
- [ ] Servicio biométrico aislado.
- [ ] Backend autenticado ante servicio biométrico.
- [ ] TLS/mTLS configurado.
- [ ] Rate limiting.
- [ ] Validación de payloads.
- [ ] Límites de tamaño.
- [ ] Timeouts.
- [ ] Logs de seguridad.

## TSA

- [ ] Imprint verificado.
- [ ] Firma CMS verificada.
- [ ] Certificado TSA validado.
- [ ] Cadena de confianza validada.
- [ ] Política TSA validada.
- [ ] Revocación evaluada.
- [ ] Token almacenado.
- [ ] GenTime almacenado.
- [ ] Serial almacenado.

## Infraestructura

- [ ] Firewall configurado.
- [ ] Puerto 8082 no expuesto públicamente.
- [ ] Usuario de servicio sin privilegios.
- [ ] Dependencias auditadas.
- [ ] DLL verificadas.
- [ ] Backups cifrados.
- [ ] Restauración probada.
- [ ] Monitoreo habilitado.
- [ ] SIEM/log centralizado.

## Seguridad operacional

- [ ] Procedimiento de revocación.
- [ ] Procedimiento de alta biométrica.
- [ ] Procedimiento de baja.
- [ ] Procedimiento de incidente.
- [ ] Procedimiento de recuperación.
- [ ] Penetration test.
- [ ] Pruebas de carga.
- [ ] Pruebas de recuperación.
- [ ] Aprobación institucional.

---

# 38. Criterios de NO-GO

El sistema **NO debe entrar en producción** si:

- una persona puede firmar sin autenticación válida;
- una autenticación puede reutilizarse;
- el servicio biométrico está expuesto directamente;
- una clave privada está en texto claro;
- un secreto está en Git;
- las firmas históricas dejan de verificarse tras una rotación;
- el documento puede modificarse sin invalidar la firma;
- un template puede modificarse sin auditoría;
- no existe revocación;
- no existe backup funcional;
- no existe monitoreo;
- no se han probado los mecanismos de recuperación;
- el threshold biométrico no ha sido validado;
- no se ha realizado una evaluación de seguridad antes del Go-Live.

---

# 39. Plan de implementación

## Fase 1 — Correcciones críticas

1. Eliminar fallback a cédula.
2. Implementar versionado de claves.
3. Mantener claves históricas.
4. Implementar challenge anti-replay.
5. Aislar servicio biométrico.
6. Eliminar CORS abierto.
7. Implementar autenticación entre servicios.

## Fase 2 — Criptografía

1. Revisar diseño de KEK.
2. Implementar `key_id`.
3. Implementar `crypto_version`.
4. Evaluar AES-256-GCM.
5. Implementar KMS/Vault/HSM.
6. Implementar revocación.

## Fase 3 — Auditoría

1. Audit trail.
2. Correlación de eventos.
3. Logs centralizados.
4. SIEM.
5. Alertas.

## Fase 4 — Validación

1. FAR/FRR.
2. Penetration testing.
3. Pruebas de carga.
4. Pruebas de recuperación.
5. Pruebas de corrupción.
6. Pruebas de rotación.
7. Pruebas TSA.

## Fase 5 — Producción controlada

1. Despliegue en ambiente controlado.
2. Activación de monitoreo.
3. Validación de logs.
4. Piloto.
5. Revisión de incidentes.
6. Aprobación de Go-Live.

---

# 40. Arquitectura final

```text
                    ┌─────────────────┐
                    │     Usuario     │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │    Frontend     │
                    └────────┬────────┘
                             │ HTTPS
                             ▼
                    ┌─────────────────┐
                    │     Backend     │
                    └───────┬─┬───────┘
                            │ │
             Challenge ────┘ │
                              │
                              ▼
                    ┌─────────────────┐
                    │ Servicio        │
                    │ Biométrico      │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ DigitalPersona  │
                    └─────────────────┘

Backend
   │
   ├──► Autorización
   │
   ├──► Hash SHA-256
   │
   ├──► Clave ECDSA versionada
   │
   ├──► Firma ECDSA
   │
   ├──► TSA RFC 3161
   │
   ├──► Base de datos
   │
   └──► Auditoría / SIEM
```

---

# 41. Flujo de seguridad final

```text
Sesión
  ↓
Challenge único
  ↓
Huella
  ↓
Matching
  ↓
Identidad
  ↓
Autorización
  ↓
Clave ECDSA versionada
  ↓
SHA-256
  ↓
Firma ECDSA
  ↓
TSA RFC 3161
  ↓
Persistencia
  ↓
Auditoría
```

La propiedad fundamental es:

```text
AUTENTICACIÓN
      ≠
FIRMA
```

pero:

```text
AUTENTICACIÓN
      ↓
AUTORIZACIÓN
      ↓
USO CONTROLADO DE LA CLAVE
      ↓
FIRMA
```

---

# 42. Nivel objetivo

El sistema debe evaluarse formalmente utilizando OWASP ASVS como referencia de verificación.

La meta no debe ser simplemente:

> "La aplicación funciona."

Debe ser:

> "La aplicación funciona y sus controles de seguridad han sido verificados contra un modelo de amenazas y criterios de aceptación definidos."

Para un entorno hospitalario también deben revisarse las obligaciones institucionales y legales aplicables al tratamiento de datos personales sensibles, información clínica y mecanismos de firma.

---

# 43. Conclusión

`Bio-security` tiene una base técnica sólida.

La combinación:

```text
DigitalPersona
      +
ANSI 378
      +
ECDSA P-256
      +
SHA-256
      +
HKDF
      +
RFC 3161
```

es una arquitectura válida para construir un sistema robusto de autenticación biométrica y firma.

Sin embargo, los algoritmos criptográficos no son suficientes.

Las prioridades absolutas antes de producción son:

1. **Eliminar la cédula como fallback criptográfico.**
2. **Versionar las claves ECDSA.**
3. **Nunca perder verificabilidad histórica.**
4. **Aislar el servicio biométrico.**
5. **Eliminar CORS abierto.**
6. **Implementar challenge anti-replay.**
7. **Proteger templates biométricos.**
8. **Fortalecer gestión de secretos.**
9. **Validar completamente RFC 3161.**
10. **Implementar auditoría.**
11. **Validar FAR/FRR.**
12. **Realizar penetration testing.**

La condición final es:

```text
NO GO-LIVE
       ↓
si existe algún riesgo ALTO/CRÍTICO
sin mitigación o aceptación formal
```

---

# 44. Referencias

- OWASP Application Security Verification Standard (ASVS):
  https://owasp.org/www-project-application-security-verification-standard/

- OWASP ASVS 5.0:
  https://github.com/OWASP/ASVS/tree/master/5.0

- RFC 3161 — Time-Stamp Protocol:
  https://www.rfc-editor.org/rfc/rfc3161

- Repositorio del proyecto:
  https://github.com/TeruIshijo1/Bio-security

---

## Nota de alcance

Este documento es una revisión técnica de arquitectura y código, no una certificación de seguridad ni una certificación legal de firma electrónica.

Antes del uso clínico en producción se requiere una revisión independiente de seguridad, infraestructura, privacidad/protección de datos y cumplimiento normativo aplicable.

# Bitácora Médica HES — Seguridad, Biometría y Expediente Clínico Electrónico

## Documento Informativo y Ejecutivo para Órganos Directivos
**Hospital Escandón**  
*Dirección General • Dirección Médica • Comité de Expediente Clínico • Dirección Jurídica y TI*  
**Fecha:** Septiembre 2026  
**Marco Normativo:** NOM-004-SSA3-2012 (Expediente Clínico) • NOM-024-SSA3-2012 (Sistemas de Información de Registro Electrónico para la Salud) • Código de Comercio (Firma Electrónica Avanzada)

---

## 1. Resumen Ejecutivo

La **Bitácora Médica del Hospital Escandón** es la plataforma institucional diseñada para la gestión, captura, validación clínica y firma electrónica de los actos médicos que integran el **Expediente Clínico Electrónico (ECE)**.

### Objetivos Principales:
1. **Autenticación Biométrica y Atribución Presencial:** La firma requiere autenticación biométrica presencial del médico y no contempla un bypass mediante contraseña. El mecanismo está diseñado para fortalecer la atribución de la firma y la trazabilidad de las acciones clínicas, sujeto a la validación jurídica y normativa correspondiente.
2. **Integridad Documental Criptográfica:** Integridad criptográfica verificable; cualquier intento de modificar una nota médica ya firmada invalida la firma y alerta de alteración.
3. **Eficiencia y Cero Papel:** Emisión instantánea de formatos oficiales vectoriales de alta calidad (Notas de Evolución, Consentimientos Informados, Recetas y Dietas) con sello digital y código QR de validación.

```mermaid
flowchart LR
    A[Médico Tratante] -->|Coloca Huella Dactilar| B(Lector DigitalPersona)
    B -->|Identidad Acreditada| C{Bitácora Médica HES}
    C -->|Firma Criptográfica FEA| D[Expediente Clínico Inalterable]
    D -->|Genera| E[PDF Oficial con Sello QR y Sellado de Tiempo]
```

---

## 2. ¿Cómo Funciona la Bitácora en el Flujo Hospitalario?

La Bitácora digitaliza de forma integral los procesos clínicos en Urgencias, Hospitalización, Quirófano y Consulta Externa:

```
┌─────────────────────────┐     ┌─────────────────────────┐     ┌─────────────────────────┐
│   1. Registro Clínico   │ ──► │  2. Firma Biométrica    │ ──► │  3. Expediente Oficial  │
│ Captura de nota médica, │     │ El médico valida con su │     │ Generación de PDF con   │
│ fármacos, consentimientos│    │ huella en el lector USB │     │ sellos y código QR      │
└─────────────────────────┘     └─────────────────────────┘     └─────────────────────────┘
```

1. **Ingreso y Consulta:** Enfermería y médicos acceden a la información del paciente en tiempo real (procedimientos, diagnósticos CIE-10/CIE-11, cama asignada).
2. **Acto Médico:** El médico redacta la evolución del paciente, prescribe medicamentos en la orden médica o formaliza un consentimiento informado.
3. **Estampado de Firma:** Al terminar, el médico coloca su dedo en el lector biométrico. El sistema valida su identidad en menos de 1 segundo y estampa su **Firma Electrónica Avanzada (FEA)**.
4. **Resguardo y Validación:** El documento queda blindado en la base de datos y se genera el archivo PDF con membrete oficial del Hospital Escandón listo para impresión o consulta en peritaje.

---

## 3. Biometría Dactilar DigitalPersona: ¿Cómo opera y por qué es segura?

### A. No se almacenan imágenes de huellas (Privacidad y Protección de Datos)
Por estricto apego a la **Ley Federal de Protección de Datos Personales (LFPDPPP)** y las mejores prácticas internacionales:
* El sistema **NUNCA guarda fotos, imágenes ni escaneos de las huellas** de los médicos.
* Lo que se procesa es una **plantilla matemática abstracta (FMD bajo norma ANSI/NIST 378)** compuesta por coordenadas de minucias dactilares.
* A partir de esa plantilla matemática es **imposible reconstruir la imagen del dedo**, protegiendo la privacidad del personal de salud ante cualquier eventualidad.

### B. Autenticación Biométrica Presencial y Atribución Clínica (Sin bypass de contraseña)
* **¿Por qué la firma exige huella obligatoria?**  
  En muchos entornos hospitalarios, los esquemas que permiten firmar con *usuario y contraseña* conllevan el riesgo operativo de que las credenciales sean compartidas con terceros (enfermería, médicos internos o asistentes) por practicidad, debilitando la trazabilidad de la autoría.
* **El Enfoque Técnico de la Bitácora HES:**  
  La firma requiere autenticación biométrica presencial del médico y no contempla un bypass mediante contraseña. El mecanismo está diseñado para fortalecer la atribución de la firma y la trazabilidad de las acciones clínicas, respaldando que el médico adscrito estuvo presente al autorizar la nota, sujeto a la validación jurídica y normativa correspondiente.

### C. Auto-Refresco y Continuidad Operativa
Para evitar que problemas comunes (sensor con gel antibacterial, dedo colocado con poca presión) frenen la atención médica:
* El sistema cuenta con **auto-refresco inteligente**: si la lectura no es clara, el lector se reinicia automáticamente en **800 milisegundos**, permitiendo al médico volver a colocar el dedo de inmediato sin congelar pantallas, sin bloquear su usuario y sin requerir recargar la página (`F5`).

---

## 4. Firma Electrónica Avanzada (FEA) e Integridad Documental

La Bitácora Médica implementa los mismos estándares criptográficos utilizados por el **SAT y el Sistema Financiero Nacional**, adaptados al expediente clínico:

```
                  ┌──────────────────────────────────────────────┐
                  │          Contenido de la Nota Médica         │
                  │ (Paciente, Diagnóstico, Indicaciones, Fecha) │
                  └──────────────────────┬───────────────────────┘
                                         │
                                         ▼ Función Hash SHA-256
                  ┌──────────────────────────────────────────────┐
                  │       Huella Digital del Documento (Hash)    │
                  │   e3b0c44298fc1c149afbf4c8996fb92427ae41...  │
                  └──────────────────────┬───────────────────────┘
                                         │ + Clave Privada ECDSA (Médico)
                                         ▼
                  ┌──────────────────────────────────────────────┐
                  │        SELLO DIGITAL FEA INALTERABLE         │
                  │ ECDSA:MEQCID7x8k1m...9Zb2qK4x1Lw50pQvNx      │
                  └──────────────────────────────────────────────┘
```

### 1. Claves Criptográficas Asimétricas (ECDSA P-256)
* Cada médico registrado posee un par de llaves criptográficas únicas (Curva Elíptica P-256 / SHA-256).
* Su clave privada de firma se encuentra **cifrada en la base de datos**. Solo se desbloquea en memoria RAM durante los milisegundos en que el médico coloca su huella válida.

### 2. Detección Instantánea de Manipulación (Integridad)
* Cada documento genera un código resumen único (**Hash SHA-256**).
* **Si una persona intentara alterar el texto en la base de datos** (por ejemplo, cambiar la dosis de un fármaco o la hora de una cirugía), el Hash cambiará por completo y el Sello Digital quedará roto. La Bitácora alertará de inmediato: **`INTEGRIDAD_COMPROMETIDA`**, impidiendo falsificaciones o alteraciones extemporáneas.

### 3. Sellado de Tiempo y Fecha Local Exacta (NOM-004)
* Cada acto firmado registra la fecha y hora exacta del servidor hospitalario sincronizado, impidiendo el "antidatado" (firmar con fecha del día anterior) y aportando validez pericial ante auditorías.

---

## 5. Formatos Oficiales y Expediente Físico/Digital

La Bitácora genera documentos médicos en formato **PDF vectorial de alta definición (600 DPI)** con el membrete institucional oficial del Hospital Escandón:

| Código de Formato | Nombre del Documento | Área Hospitalaria |
| :--- | :--- | :--- |
| **HE-DIRMED-SINPRO-PLT-87/01** | Nota de Evolución Médica de Urgencias | Urgencias / Choque |
| **HE-DIRMED-SINPRO-PLT-04** | Consentimiento para Colocación de Catéter | Terapia / Hospitalización |
| **HE-DIRMED-SINPRO-PLT-12** | Consentimiento Gineco-Obstétrico Urgencias | Tococirugía / Urgencias |
| **HE-DIRMED-SINPRO-PLT-25** | Consentimiento Gineco-Obstetricia y Consulta Ext. | Consulta / Hospitalización |
| **HE-DIRMED-SINPRO-PLT-34/01** | Consentimiento para Prueba de Mesa Inclinada | Cardiología / Fisiología |
| **RECETA-PTDG** | Prescripción Farmacológica Hospitalaria | Farmacia / Piso |
| **DIETA-MR_SOL_DIET** | Régimen Dietético y Cuidados de Enfermería | Nutrición / Enfermería |

### Elementos de Seguridad Impresos en Cada Hoja:
1. **Cadena Original de Firma:** Contiene los identificadores del paciente, médico, cédula profesional y resumen clínico.
2. **Sello Digital FEA:** Código criptográfico único de autenticidad.
3. **Código QR Institucional:** Permite escanear el documento con un celular o tablet para verificar en el sistema si la hoja impresa coincide 1:1 con el expediente electrónico original.

---

## 6. Seguridad de la Infraestructura y Red Hospitalaria

Para proteger la información confidencial de los pacientes:
* **Operación en Red Local (Intranet):** El microservicio de matching biométrico y las bases de datos operan de forma aislada dentro de la infraestructura del hospital (`127.0.0.1` / Red HES), sin exponer puertos al internet público.
* **Protección Anti-Replay (Challenge de 120 segundos):** Cada intento de firma genera un token de un solo uso que expira en 2 minutos. Si alguien interceptara el tráfico de red, el token ya no podrá ser reutilizado para firmar otros documentos.
* **Trazabilidad y Auditoría Continua:** Todas las operaciones (creación de pacientes, firmas, prescripciones, cambios de estatus) quedan registradas en una bitácora de auditoría inmutable con fecha, hora, IP de la terminal y usuario responsable.

---

## 7. Ruta de Implementación Jurídica para Validez Legal Plena (Blindaje Institucional)

Para que la tecnología biométrica y la Firma Electrónica Avanzada alcancen **plena eficacia jurídica y valor probatorio indiscutible** ante juzgados, aseguradoras, CONAMED y COFEPRIS, la infraestructura de software debe complementarse con la **Trilogía Jurídica y Documental** del hospital:

```
                          ┌────────────────────────────────────────────────────────┐
                          │    TRILOGÍA DE GOBERNANZA Y VALIDEZ JURÍDICA HES       │
                          └──────────────────────────┬─────────────────────────────┘
                                                     │
         ┌───────────────────────────────────────────┼───────────────────────────────────────────┐
         ▼                                           ▼                                           ▼
┌─────────────────────────────────┐ ┌─────────────────────────────────┐ ┌─────────────────────────────────┐
│   1. CONVENIO CON EL MÉDICO     │ │   2. CONSENTIMIENTO PACIENTE    │ │   3. AVAL COMITÉ EXPEDIENTE     │
│ Acuerdo de Aceptación de Firma  │ │ Aviso de Privacidad Integral    │ │ Acta del Comité de Calidad y    │
│ Electrónica y Atribución        │ │ y Consentimiento para Datos     │ │ Expediente Clínico avalando     │
│ Biométrica (Código de Comercio) │ │ Sensibles Biométricos (LFPDPPP) │ │ la Bitácora HES (NOM-004-SSA3)  │
└─────────────────────────────────┘ └─────────────────────────────────┘ └─────────────────────────────────┘
```

---

### A. Convenio de Uso de Medios Electrónicos y Firma Digital (Médico – Hospital)
* **Fundamento Legal:** Código de Comercio (Artículos 89, 90, 97 y 100), Código Civil Federal (Art. 1803) y NOM-024-SSA3-2012.
* **Mecanismo:** Cada médico adscrito o con prerrogativas firma un convenio (o adenda a su contrato de prestación de servicios) al momento de registrar su huella dactilar por primera vez.
* **Cláusulas Esenciales que Debe Contener:**
  1. **Reconocimiento de Validez:** El médico acepta formalmente que el uso de su huella dactilar capturada en los lectores institucionales del Hospital Escandón para estampar la Firma Electrónica Avanzada (ECDSA P-256) en la Bitácora HES surte los **mismos efectos jurídicos que su firma autógrafa**.
  2. **Atribución Exclusiva y Personalísima:** El médico reconoce que el material biométrico y su llave privada asociada son de su estricto control exclusivo, asumiendo la autoría y responsabilidad clínica de cualquier acto firmado bajo este método.
  3. **Prohibición de Delegación:** Compromiso expreso de no permitir que terceras personas coloquen el dedo o utilicen sus accesos.
  4. **Procedimiento de Incidencia:** Obligación de notificar a Sistemas en caso de lesiones que impidan la lectura de su huella o solicitud de baja/revocación de llave.

---

### B. Aviso de Privacidad y Consentimiento de Datos Biométricos (Paciente – Hospital)
* **Fundamento Legal:** Ley Federal de Protección de Datos Personales en Posesión de los Particulares (**LFPDPPP**, Arts. 8, 9, 15 y 16) y su Reglamento.
* **Mecanismo:** En la **Hoja de Ingreso Hospitalario / Carta de Consentimiento de Servicios**, el paciente o su representante legal firma la autorización correspondiente.
* **Cláusula Tipo a Incorporar en el Ingreso:**
  > *"El Titular consiente expresamente el tratamiento de sus **Datos Personales Sensibles** (estado de salud, antecedentes médicos y, en su caso, registros o cotejos biométricos de autenticación), para la integración, consulta, resguardo y firma de su **Expediente Clínico Electrónico** en la Bitácora Médica del Hospital Escandón, conforme a la NOM-004-SSA3-2012 y la Ley Federal de Protección de Datos Personales."*

---

### C. Formalización por el Comité de Expediente Clínico (Hospital Escandón)
* **Fundamento Legal:** NOM-004-SSA3-2012 (Numerales 5.3 y 5.4) y Ley General de Salud.
* **Mecanismo:** El **Comité de Calidad y Expediente Clínico** emite un **Acta de Sesión Ordinaria** donde:
  1. Se aprueba formalmente la plataforma **Bitácora Médica HES** como el sistema oficial y exclusivo para la elaboración de notas de evolución, consentimientos, recetas y órdenes médicas electrónicas.
  2. Se establece la política institucional de conservación de los expedientes electrónicos por un **periodo mínimo de 5 años** a partir de la última fecha de atención.
  3. Se autoriza la emisión de copias certificadas impresas en los formatos vectoriales institucionales con código QR y cadena original para peritajes judiciales o requerimientos sanitarios.

---

## 8. Matriz de Cumplimiento Normativo y Autoridades

| Autoridad / Entorno | Marco Jurídico | ¿Cómo lo Cumple la Bitácora Médica HES? |
| :--- | :--- | :--- |
| **SSA / COFEPRIS** | **NOM-004-SSA3-2012** (Expediente Clínico) | Estructura de notas conforme a norma (subjetivo, objetivo, análisis, plan), fecha/hora exacta y archivo clínico estructurado. |
| **DGIRE / SSA** | **NOM-024-SSA3-2012** (Sistemas ECE) | Autenticación biométrica de usuarios, integridad de datos, pistas de auditoría inmutables y catálogos estandarizados. |
| **Poder Judicial / Juzgados** | **Código de Comercio** (Arts. 89-114) | Firma electrónica avanzada con criptografía asimétrica ECDSA P-256, hash SHA-256 y sellado de tiempo para plena validez probatoria. |
| **INAI** | **LFPDPPP** (Datos Personales Sensibles) | No se almacenan fotos de huellas (solo vectores matemáticos ANSI 378 cifrados); base de datos aislada en intranet local. |
| **CONAMED / Aseguradoras** | **Ley General de Salud** | Trazabilidad médica transparente, formatos oficiales de consentimientos informados y verificación instantánea mediante código QR. |

---

## 9. Beneficios para el Hospital Escandón

```
┌────────────────────────────────────────────────────────────────────────────┐
│                    BENEFICIOS CLAVE PARA LA INSTITUCIÓN                    │
├─────────────────────────┬──────────────────────────┬───────────────────────┤
│    RESPALDO NORMATIVO   │    EFICIENCIA CLÍNICA    │    CONTROL Y COBRO    │
│                         │                          │                       │
│ • Alineación técnica a  │ • Eliminación de notas   │ • Conciliación de     │
│   NOM-004 y NOM-024.    │   ilegibles a mano.      │   honorarios médicos  │
│ • Atribución biométrica │ • Consulta inmediata del │   solo sobre notas    │
│   presencial robusta.   │   historial en cualquier │   debidamente         │
│ • Evidencia documental │   piso del hospital.     │   firmadas con FEA.   │
│   estructurada para     │ • Ahorro del 100% en     │ • Cero pérdidas de    │
│   auditorías y peritajes│   papelería extraviada.  │   formatos físicos.   │
└─────────────────────────┴──────────────────────────┴───────────────────────┘
```

---

## 10. Conclusión y Recomendación para la Dirección General

La arquitectura tecnológica de la **Bitácora Médica HES** proporciona una base de alta seguridad mediante **autenticación biométrica dactilar presencial, criptografía de curva elíptica P-256 y formatos normativos oficiales**.

Para consolidar el **blindaje jurídico total** ante directivos, se recomienda formalizar de inmediato la ruta legal de tres pasos:
1. **Recabar la firma del Convenio de Uso de Firma Digital** con cada médico adscrito al enrolar su huella.
2. **Actualizar el formato de Ingreso Hospitalario** con la cláusula de consentimiento de datos sensibles.
3. **Emitir el Acta del Comité de Expediente Clínico** aprobando la Bitácora Médica como software oficial del Hospital Escandón.

Con esta convergencia técnica y jurídica, el hospital asegura la máxima protección de la información clínica, garantiza la trazabilidad de sus médicos y respalda legalmente todas las actuaciones institucionales.

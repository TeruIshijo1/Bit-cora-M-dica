# 🏥 Guía Maestra de Formatos Clínicos Oficiales (Hospital Escandón)

Esta guía documenta la metodología oficial, dimensiones y pasos técnicos automatizados para crear e integrar **nuevos formatos hospitalarios** (notas de evolución, consentimientos informados, hojas de enfermería, valoraciones preoperatorias, etc.) con fidelidad institucional del 100%, idéntica a los reportes autorizados por el área de Calidad.

---

## 📐 1. Geometría Estándar RDLC (Calibración Física Universal)

Todos los formatos verticales del hospital deben regirse estrictamente por la **cuadrícula estándar RDLC**:

| Parámetro | Valor RDLC | Valor en Python ReportLab | Descripción |
|---|---|---|---|
| **Hoja (Carta)** | `21.59 cm × 27.94 cm` | `612.0 pt × 792.0 pt` | Tamaño estándar Letter |
| **Márgenes del Reporte** | `0.7 cm, 0.7 cm, 0.8 cm, 0.8 cm` | Izq/Der: `19.84 pt`, Sup/Inf: `22.68 pt` | Márgenes base del informe |
| **Ancho de Cuerpo (Body)** | `20.19 cm` | `572.31 pt` | Área imprimible máxima |
| **Contenedor Principal** | `20.10 cm × 25.50 cm` | `569.76 pt × 722.84 pt` | Tamaño del marco institucional |
| **Origen X (`FRAME_X`)** | `0.745 cm` (`0.7 + 0.045`) | **`21.12 pt`** | Posición horizontal exacta |
| **Origen Y (`FRAME_Y`)** | `1.49 cm` | **`42.24 pt`** | Posición vertical exacta RDLC |
| **Ancho Marco (`FRAME_W`)** | `20.10 cm` | **`569.76 pt`** | Ancho del marco perimetral |
| **Alto Marco (`FRAME_H`)** | `25.50 cm` | **`722.84 pt`** | Alto del marco perimetral |
| **Borde Perimetral** | `MidnightBlue`, `1.25 pt` | `#191970`, `1.25 pt` | Trazo perimetral del formato |
| **Ancho Contenido Texto** | `19.36 cm` | **`548.76 pt`** | Espacio interior libre para tablas y texto |

### 📏 Regla Global de Distribución Vertical y Aprovechamiento de Hoja (Anti-Amontonamiento):
1. **Aprovechamiento Integral de la Hoja**: Todo formato de 1 página debe distribuir armónicamente su contenido a lo largo de la altura útil del marco (~620 pt), abarcando desde la base del encabezado (58 pt) hasta la barra del pie de página (38 pt), evitando dejar vacíos en la parte inferior.
2. **Separación Armónica entre Secciones**: No compactar el contenido en el tercio superior. Aplicar espaciadores calibrados (`Spacer(1, 6.0)` a `Spacer(1, 10.0)`) y padding vertical en celdas (`3.8 pt` a `4.5 pt`) entre bloques de datos, autorizaciones, descripciones clínicas y marco legal.
3. **Tipografía Institucional Cómoda**: Utilizar fuentes legibles de `7.8 pt` con interlineado de `10.0 - 10.8 pt` para el cuerpo clínico, y de `6.8 pt` con leading `8.8 pt` para el articulado legal y leyendas de excepción.
4. **Posicionamiento Inferior de Firmas**: Las firmas y sellos biométricos deben situarse en la parte baja de la hoja, próximos al pie de página, garantizando una holgura generosa (`14 - 16 pt`) entre la primera y segunda fila de firmantes.

---

## 🚀 2. Flujo de Creación de un Nuevo Formato (Paso a Paso)

Solo necesitas tener el **PDF muestra autorizado por Calidad** (ejemplo: `88_01_NOTA_DE_INGRESO.pdf`).

### Paso 1: Colocar el PDF Muestra
Guarda el archivo PDF oficial dentro de la carpeta:
```text
Bitacora_HES/
└── Formatos VERTICAL/
    └── 88_01_NOTA_DE_INGRESO.pdf
```

---

### Paso 2: Ejecutar el Extractor Automatizado de Assets
Ejecuta el script utilitario que recorta a 600 DPI el encabezado, limpia las firmas de diseñadores externos en el pie y engrosa el membrete lateral:

```powershell
python backend/scripts/extract_form_assets.py "Formatos VERTICAL/88_01_NOTA_DE_INGRESO.pdf"
```

El script creará automáticamente en `Formatos VERTICAL/Encabezado, pie, lateral/`:
1. `header_completo_oficial.png` (Encabezado con marca de agua, cruz y código de calidad).
2. `pie_hes_sin_disenador.png` (Pie institucional limpio, sin marcas externas y listo para folio dinámico).
3. `lateral_hes_oficial_bold.png` (Membrete vertical de Fundación optimizado para no salir deslavado).
4. `logo_hes_oficial.png` (Logotipo institucional para páginas subsecuentes).

---

### Paso 3: Estructurar el Generador en Python

Copia la estructura base del motor `backend/pdf_engine_v2.py` o crea tu función especializada. 

#### Plantilla Estándar del Canvas (`RDLCCanvas`):
```python
from reportlab.pdfgen import canvas
from reportlab.lib import colors
import os

MIDNIGHT_BLUE = colors.HexColor('#191970')
BLUE_BAR_COLOR = colors.HexColor('#005FA8')
PRIMARY_BLUE = colors.HexColor('#0056b3')

FRAME_X = 21.12
FRAME_W = 569.76
FRAME_H = 722.84
FRAME_Y = 42.24

class RDLCCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []
        self.fecha_ingreso = ""
        self.hora_ingreso = ""

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_letterhead(num_pages)
            super().showPage()
        super().save()

    def draw_letterhead(self, total_pages):
        self.saveState()

        # 1. Marco perimetral institucional
        self.setStrokeColor(MIDNIGHT_BLUE)
        self.setLineWidth(1.25)
        self.rect(FRAME_X, FRAME_Y, FRAME_W, FRAME_H, fill=False, stroke=True)

        # 2. Encabezado (75 pt de alto)
        head_h = 75.0
        head_y = (FRAME_Y + FRAME_H) - head_h
        if self._pageNumber == 1:
            self.drawImage("header_completo_oficial.png", FRAME_X, head_y, width=FRAME_W, height=head_h, mask='auto')
        else:
            # Encabezado compacto página 2+
            self.drawImage("logo_hes_oficial.png", FRAME_X + FRAME_W - 139, FRAME_Y + FRAME_H - 32, width=135, height=27, mask='auto')

        # 3. Membrete lateral vertical de Fundación
        self.drawImage("lateral_hes_oficial_bold.png", FRAME_X + FRAME_W - 14.5, FRAME_Y + 42.0, width=12.0, height=560.0, mask='auto')

        # 4. Pie de página con numeración dinámica "Página X de Y"
        foot_h = 38.0
        foot_y = FRAME_Y + 0.5
        self.drawImage("pie_hes_sin_disenador.png", FRAME_X, foot_y, width=FRAME_W, height=foot_h, mask='auto')
        self.setFillColor(BLUE_BAR_COLOR)
        self.rect(FRAME_X, foot_y + foot_h - 4.5, FRAME_W, 4.5, fill=True, stroke=False)
        
        self.setFont("Helvetica-Bold", 7.5)
        self.setFillColor(PRIMARY_BLUE)
        self.drawRightString(FRAME_X + FRAME_W - 6, foot_y + 8, f"Página {self._pageNumber} de {total_pages}")

        self.restoreState()
```

---

## 🩺 3. Reglas de Oro de Calidad Médica (NOM-004-SSA3-2012)

1. **Datos Demográficos Completos**:
   - Nombre completo en mayúsculas, expediente (`PT-XXXX`), cama, edad con sufijo `años`, fecha de nacimiento y género (`M [X] F [ ]`).
   - Alergias resaltadas en color rojo institucional `#d93025`.

2. **Signos Vitales y Diagnósticos**:
   - Deben incluirse TA, FC, FR, SatO2, Temperatura, Peso y Talla.
   - El diagnóstico principal debe estar en negritas y mayúsculas.

3. **Anclaje de Firmas Autógrafas**:
   - Las firmas de médico tratante y médico interno (MIP) deben estar agrupadas con `KeepTogether([t_sig])` y un `Spacer(1, 18)` para que descansen **justo sobre la barra superior del pie de página**.

4. **Compatibilidad Total de Impresión (Carta y A4)**:
   - El margen inferior `FRAME_Y = 47.91 pt` asegura que ningún rodillo mecánico de ninguna impresora institucional corte el texto ni los datos de contacto de la Fundación.

---

## 🧠 5. Regla de Oro de Inteligencia Demográfica y Legal: Otorgante del Consentimiento (Mayor vs Menor de Edad)

En **todos los formatos clínicos y consentimientos informados habidos y por haber**:

1. **Pacientes Mayores de Edad (`Edad >= 18 años`)**:
   - Por defecto, el sistema activa la casilla inteligente: `¿El paciente puede otorgar consentimiento y firmar por sí mismo? (Mayor de edad)`.
   - **Si está marcada (`paciente_capaz = true`)**:
     - Se asigna automáticamente el **nombre completo del paciente** en la firma legal de consentimiento.
     - El campo de *Familiar / Tutor / Representante Legal* queda deshabilitado / no requerido.
   - **Si el médico desmarca la casilla (`paciente_capaz = false`)**:
     - (Por incapacidad física/mental, inconsciencia, sedación o estado crítico).
     - Se habilita de forma obligatoria el campo de captura del **Familiar, Tutor o Representante Legal**, asignando dicho nombre en la firma.

2. **Pacientes Menores de Edad (`Edad < 18 años`)**:
   - Por estricta disposición jurídica de la **NOM-004-SSA3-2012** y el Reglamento de la Ley General de Salud, un menor de edad no puede consentir por sí mismo.
   - El sistema **bloquea la opción de autofirma** y muestra la alerta institucional:
     `⚠️ Paciente menor de edad (${edad} años) — Requiere padre, madre, tutor o representante legal.`
   - El campo para ingresar el nombre completo del **Padre, Madre, Tutor o Representante Legal** se vuelve **estrictamente obligatorio** para guardar o firmar el formato.

3. **Supresión Dinámica de Casillas Vacías de Tutor (Estética y Precisión Jurídica)**:
   - Si el paciente es mayor de edad y capaz (`paciente_capaz = true`), la casilla, línea azul y texto de tutor **NO debe dibujarse en blanco ni quedar huérfana**.
   - El motor PDF reconfigura dinámicamente el bloque de firmas en disposición triangular/piramidal armónica (Paciente y Testigo arriba; Médico Tratante centrado abajo).
   - La casilla del tutor únicamente se dibuja en cuadrícula 2x2 cuando realmente existe un tutor asignado (menor de edad o paciente incapacitado).

4. **Lógica Dual Dinámica: Autorizo vs No Autorizo / Disentimiento (Formato 15 y equivalentes)**:
   - Los consentimientos quirúrgicos que contemplan disentimiento disponen de un selector de decisión:
     - **🟢 SÍ Autorizo (Consentimiento Informado - Hoja 1)**: Genera el formato clínico con los 7 puntos médicos, justificación, riesgos obstétricos/quirúrgicos, alternativas y firmas con distribución piramidal inteligente.
     - **🔴 NO Autorizo (Disentimiento Informado - Hoja 2)**: Genera el formato de revocación/negativa informada con motivo de no aceptación, cláusula de deslinde de responsabilidad (NOM-004-SSA3-2012), datos de testigo/parentesco y sello biométrico de constancia médica.

---

## ✍️ 6. Regla de Oro Universal para el Bloque de Firmas (Todos los Formatos Habidos y por Haber)

Queda estrictamente establecido como **estándar corporativo obligatorio** para todos los formatos actuales y futuros:

1. **Sobre la Línea Azul (`PRIMARY_BLUE`)**:
   - **Paciente, Familiares y Testigos**: Se deja el espacio superior en blanco (`Paragraph("&nbsp;", style_sig_space)`) para que se estampe la firma autógrafa física o digital.
   - **Médico Tratante / Autorizado**: Se posiciona directamente sobre la línea azul el **Sello Biométrico Digital NOM-004 / NOM-024 (DigitalPersona)** si el documento ya fue firmado biométricamente, o el espacio libre en blanco si está pendiente de firma.

2. **Bajo la Línea Azul (Sustitución Total de Etiquetas Genéricas)**:
   - **NUNCA** deben mostrarse textos genéricos de captura como *"Nombre completo y firma del paciente"*, *"Nombre completo y firma del testigo"* o *"Nombre completo, cédulas y firma del médico tratante"*.
   - **Paciente**: Se imprime su **Nombre Completo** en negrita: `<b>{paciente_nombre}</b>`.
   - **Tutor / Representante**: Se imprime su **Nombre Completo** en negrita: `<b>{pariente}</b>` (únicamente si existe tutor activo).
   - **Testigos**: Se imprime el **Nombre Completo del Testigo** en negrita: `<b>{testigo}</b>`.
   - **Médico Tratante**:
     - **Renglón 1**: Nombre completo del médico en negritas (`<b>{medico}</b>`).
     - **Renglón 2**: Cédula profesional en **cursiva y negrita**: `<font size='6.4' color='#334155'><i><b>CÉD. PROF. {cedula}</b></i></font>`.
   - **Médico Interno (MIP)**: Nombre en negrita (`<b>{mip_nombre}</b>`) y debajo en cursiva negrita `<i><b>MÉDICO INTERNO DE PREGRADO</b></i>`.

---

## 📋 7. Catálogo de Formatos Activos Implementados

| Código Formato | Nombre Oficial | Servicio | Tabla SQL Server | PK | Motor PDF |
|---|---|---|---|---|---|
| `HE-DIRMED-SINPRO-PLT-87/01` | Nota de Evolución (Hasta 3 notas) | Urgencias | `MR_NE_URG` | `MRNum_NE_URG` | `pdf_engine_v2.py` |
| `HE-DIRMED-CONSUL-PLT-34/01` | Consentimiento Mesa Inclinada (Tilt Test) | Cardiología | `MR_CI_EMI` | `MRNum_CI_EMI` | `pdf_engine_34_01.py` |
| `HE-DIRMED-CONSUL-PLT-32/01` | Consentimiento Ecocardiograma Transesofágico | Cardiología | `MR_CI_ETE_CARD` | `MRNum_CI_ETE_CARD` | `pdf_engine_32_01.py` |
| `HE-DIRMED-CONSUL-PLT-EED` | Consentimiento Endoscopia Esofagogastroduodenal | Gastroenterología | `MR_CI_EED` | `MRNum_CI_EED` | `pdf_engine_eed.py` |
| `HE-DIRMED-CONSUL-PLT-25` | Consentimiento Gineco y Obstetricia (CE) | Consulta Externa | `MR_CI_RGO_CE` | `MRNum_CI_RGO_CE` | `pdf_engine_25.py` |
| `HE-DIRMED-CONSUL-PLT-12` | Consentimiento Gineco y Obstetricia (Hosp/Urg) | Hosp. y Urgencias | `MR_CI_RGO_HU` | `MRNum_CI_RGO_HU` | `pdf_engine_12.py` |
| `HE-DIRMED-CONSUL-PLT-04` | Consentimiento Colocación de Catéter Venoso Central | Procedimientos / Cirugía | `MR_CI_CC` | `MRNum_CI_CC` | `pdf_engine_04.py` |
| `HE-DIRMED-CONSUL-PLT-15` | Consentimiento Informado para Cesárea / Disentimiento | Ginecología y Obstetricia | `MR_CI_CES` | `MRNum_CI_CES` | `pdf_engine_15.py` |
| `HE-DIRMED-CONSUL-PLT-08` | Consentimiento Tratamiento y Diagnóstico en Admisión Continua | Admisión Continua / Urgencias | `MR_08_CI_DIAGNOSTICO_ADMISION_CONTI` | `MRNum_08_CI_DIAGNOSTICO_ADMISION_CONTI` | `pdf_engine_08.py` |
| `HE-DIRMED-CONSUL-PLT-02` | Consentimiento Informado Tratamiento Quirúrgico / Disentimiento | Cirugía y Quirófano | `MR_02_CI_TRATAMIENTO_QUIRURGICO` | `MRNum_02_CI_TRATAMIENTO_QUIRURGICO` | `pdf_engine_02.py` |
| `HE-DIRMED-SINPRO-PLT-43` | Consentimiento Informado para Intubación Endotraqueal | Urgencias / Terapia Intensiva | `MR_ORD_INTUB_END` | `MRNum_ORD_INTUB_END` | `pdf_engine_43.py` |
| `HE-DIRMED-CONSUL-PLT-06` | Consentimiento Informado para Procedimientos Anestésicos | Anestesiología / Quirófano | `MR_CI_PA` | `MRNum_CI_PA` | `pdf_engine_06.py` |
| `HE-DIRMED-CONSUL-PLT-07` | Consentimiento Informado para Procedimientos Quirúrgicos | Cirugía y Quirófano | `MR_CI_PQ` | `MRNum_CI_PQ` | `pdf_engine_07.py` |
| `HE-DIRMED-CONSUL-PLT-09` | Consentimiento Informado para Transfusión de Hemocomponentes | Medicina Transfusional / Hospital | `MR_CI_AUT_TRANS_HEMO` | `MRNum_CI_AUT_TRANS_HEMO` | `pdf_engine_09.py` |
| `HE-DIRMED-CONSUL-PLT-11` | Consentimiento de No Reanimación Cardiopulmonar | Urgencias / Terapia / Bioética | `MR_CI_NRC` | `MRNum_CI_NRC` | `pdf_engine_11.py` |
| `HE-DIRMED-CONSUL-PLT-19` | Consentimiento Informado para Histerectomía | Ginecología y Obstetricia | `MR_CI_HA` | `MRNum_CI_HA` | `pdf_engine_19.py` |

---

## 📱 8. Estándar Universal de Código QR y Cotejo ECE en Tiempo Real (NOM-004-SSA3-2012 / NOM-024-SSA3-2012)

Para **todos los formatos y consentimientos informados habidos y por haber**:

1. **Inclusión Automática en el Canvas Base (`RDLCCanvas` / `CleanConsentCanvas`)**:
   - Todo motor de PDF que herede de `RDLCCanvas` o `CleanConsentCanvas` (`backend/pdf_engine_v2.py`) dibuja automáticamente el código QR de cotejo en la esquina inferior derecha del pie de página sin requerir archivos pregenerados en disco.
   - El código QR se genera en memoria (`io.BytesIO`) y se renderiza con `ImageReader` directamente sobre el pie de página institucional.

2. **Calibración y Dimensiones Físicas del QR**:
   - **Tamaño:** `25.5 pt × 25.5 pt` (`qr_sz = 25.5`).
   - **Posición X:** `FRAME_X + FRAME_W - qr_sz - 6.0 pt`.
   - **Posición Y:** `foot_y + 3.5 pt` (encajado perfectamente dentro del pie de página, sin tocar la barra azul superior).
   - **Marco Contenedor:** Fondo blanco puro (`colors.white`) con bordes redondeados de `0.5 pt` y radio `1.2 pt` (`roundRect`) que garantiza legibilidad 100% ante cualquier cámara de smartphone.
   - **Metadatos a la Izquierda del QR:**
     - `Página X de Y` (Helvetica-Bold 6.2 pt, Azul Institucional `#0056b3`).
     - `VERIFICACIÓN ECE` (Helvetica-Bold 4.8 pt, Azul Marino `#002855`).
     - `Cotejo NOM-004-SSA3` (Helvetica 4.2 pt, Gris `#64748b`).

3. **Estructura de la URL de Cotejo**:
   ```text
   https://TU-DOMINIO-PUBLICO/verificar?id=v1_{identificador_opaco}
   ```
   - `PUBLIC_VERIFICATION_BASE_URL` define el dominio HTTPS público (por ejemplo,
     el Funnel institucional); `VERIFICATION_BASE_URL` se conserva como alias
     histórico. El identificador no contiene paciente, formato ni folio.

4. **Portal Institucional de Verificación (`/verificar`)**:
   - Al escanear el QR desde cualquier smartphone, el servidor responde con la pantalla institucional oficial:
     - **Encabezado:** Logo oficial de Hospital Escandón (`logo_hes_oficial.png` en base64) y acreditación NOM-004-SSA3 / NOM-024-SSA3.
     - **Distintivo:** `Expediente Electrónico Válido e Íntegro`.
     - **Datos del Paciente:** Nombre completo del paciente consultado en tiempo real desde el ECE, número de expediente y edad.
     - **Acto Médico:** Nombre del formato normado y estado `AUTORIZADO Y FIRMADO`.
     - **Atribución y Firma:** Nombre del médico tratante, cédula profesional, fecha/hora de firma, método biométrico DigitalPersona y sellos digitales criptográficos (SHA-256 y FEA).
     - **Botón de Descarga:** Acceso directo para abrir y descargar el PDF original (`/api/ehr/paciente/{pt_num}/pdf-consentimiento-04`).
     - **Redes y Canales Oficiales:** Enlaces directos a Facebook, Instagram, TikTok, X, YouTube y Sitio Web de Hospital Escandón.
     - **Firma de Autoría:** Crédito sutil con enlace interactivo a GitHub (`Autor: Ing. Alberto García M.`).

---

## ⚡ 9. Motor Universal de Resolución, Firma y Sincronización Automática con Vertical (Para los 100+ Formatos)

Para garantizar que **cualquiera de los 100+ formatos clínicos institucionales** (actuales y futuros) funcione de forma automática y transparente sin requerir código manual en cada uno:

1. **Resolución Inteligente de Controladores (`vertical_signer.resolve_vertical_controller_and_pk`)**:
   - **Caché en Memoria de Esquema SQL Server:** Inspecciona automáticamente todas las tablas clínicas (`MR_%`) de `KH_HE`.
   - **Inferencia Numérica Multinivel:** Detecta códigos numéricos en el identificador (ej. `02`, `08`, `15`, `24`, `26`, `32`, `34`, `79`, `87`, `88`, etc.) y los vincula automáticamente con su tabla correspondiente (`MR_02_...`, `MR_08_...`, `MR_24_...`, `MR_26_...`).
   - **Puntuación Semántica de Tokens Clínicos:** Normaliza y compara palabras clave clínicas (`HISTERECTOMIA`, `NO_REANIMACION`, `REANIMACION`, `TINA`, `TERM_EMB`, `AUT_TRANS_HEMO`, `SOL_OP`, `SOL_DIET`, `LV_SPI`, `RTOE_PACE`, `RPS_FQ`, `VRA_HOS`, `ERC_HOS`, `HC_HOS`, `HC_URG`, etc.) asignando la tabla correspondiente con 100% de precisión.
   - **Regla Estándar de Primary Key:** Resuelve dinámicamente la columna PK como `MRNum_{tabla.replace('MR_', '')}` (estándar homogéneo en el 100% de las 37 tablas clínicas de Vertical).

2. **Firma Nativa Transparente en Vertical (`vertical_signer.sign_in_vertical_api`)**:
   - Actualiza de forma inmediata en SQL Server:
     ```sql
     UPDATE {controller_name} 
     SET SignedBy = ?, SignedOn = GETDATE(), MR_ST = 'SG', ESignature = COALESCE(ESignature, 'FIRMADO_BIOMETRICAMENTE') 
     WHERE {pk_field} = ?
     ```
   - Invoca la API nativa de Vertical (`_invoke/Execute -> SignRecord`) con credenciales del sistema, generando el token interno y el sello digital nativo.
   - Auto-relogin transparente en caso de expiración de sesión.

3. **Tarjeta Universal de Expediente en Frontend (`PatientDashboard.jsx`)**:
   - Cualquier formato del catálogo que se seleccione muestra en tiempo real su historial de folios (`Doc #1`, `Doc #2`), su estado de firma (`FIRMADO` vs `PENDIENTE DE FIRMA`) y botón para **Firmar con Huella** dactilar DigitalPersona.
   - Si un paciente no tiene registros previos en Vertical para ese formato, ofrece el botón **Crear Registro Inicial en Vertical**, inicializando la fila en SQL Server y habilitando la firma inmediata.

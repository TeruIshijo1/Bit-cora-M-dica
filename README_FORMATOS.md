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

## ⚡ 4. Comandos Rápidos de Verificación

Para compilar y abrir el PDF resultante en pantalla en 1 solo comando:

```powershell
python backend/pdf_engine_v2.py
Start-Process "backend/static/pdfs/TEST_nota_urgencias_final.pdf"
```

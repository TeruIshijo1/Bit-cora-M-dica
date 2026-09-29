---
aliases: [PDFs clínicos, Motor PDF, Formatos oficiales]
tags: [hes/backend, hes/operaciones]
tipo: modulo
modulo: formatos
codigo_fuente:
  - backend/pdf_engine_v2.py
  - backend/pdf_generator.py
  - backend/services/pdf_service.py
  - backend/pdf_engine_02.py
  - backend/pdf_engine_04.py
  - backend/pdf_engine_09.py
  - backend/pdf_engine_15.py
actualizado: 2026-09-28
relacionados:
  - "[[Backend]]"
  - "[[Seguridad-FEA]]"
  - "[[Pase_a_Produccion]]"
  - "[[decisiones/ADR-0001-reportlab-sin-word]]"
---

# Formatos-PDF

Generación 100% Python puro (ReportLab Platypus / xhtml2pdf), 600 DPI, sin Word ni COM. Ver [[decisiones/ADR-0001-reportlab-sin-word]].

## Catálogo oficial
| Código | Documento | Área |
|---|---|---|
| HE-DIRMED-SINPRO-PLT-87/01 | Nota de Evolución Médica de Urgencias | Urgencias / Choque |
| HE-DIRMED-SINPRO-PLT-04 | Consentimiento Colocación de Catéter | Terapia / Hospitalización |
| HE-DIRMED-CONSUL-PLT-09 | Consentimiento Informado para Transfusión de Hemocomponentes | Medicina / Banco de Sangre |
| HE-DIRMED-SINPRO-PLT-12 | Consentimiento Gineco-Obstétrico Urgencias | Tococirugía / Urgencias |
| HE-DIRMED-SINPRO-PLT-25 | Consentimiento Gineco-Obstetricia y Cons. Ext. | Consulta / Hospitalización |
| HE-DIRMED-SINPRO-PLT-34/01 | Consentimiento Prueba de Mesa Inclinada | Cardiología / Fisiología |
| RECETA-PTDG | Prescripción Farmacológica | Farmacia / Piso |
| DIETA-MR_SOL_DIET | Régimen Dietético / Enfermería | Nutrición / Enfermería |

## Mapeo código → motor
| Motor | Formato |
|---|---|
| `pdf_engine_v2.py` | Base + 87/01 |
| `pdf_engine_02.py` | 02 |
| `pdf_engine_04.py` | 04 |
| `pdf_engine_09.py` | 09 |
| `pdf_engine_06.py`, `07`, `08`, `11` | 06, 07, 08, 11 |
| `pdf_engine_12.py` | 12 |
| `pdf_engine_15.py`, `pdf_engine_15_ev.py` | 15 (+ evolución) |
| `pdf_engine_19.py` | 19 |
| `pdf_engine_24.py`, `25` | 24, 25 |
| `pdf_engine_32_01.py`, `34_01.py`, `43` | 32/01, 34/01, 43 |
| `pdf_engine_eed.py`, `pdf_engine_expediente.py` | EED / expediente |
| `pdf_generator.py` | Comprobantes con QR |
| `services/pdf_service.py` | Fachada unificada |

## Elementos impresos
1. Cadena original del documento cuando el formato la requiere.
2. Sello digital FEA sólo cuando existe firma médica verificable de ese formato.
3. QR institucional verificable, únicamente cuando se ha resguardado la copia exacta → [[API-Endpoints]].
4. El Formato 09 reserva en su verificación transfusional campos impresos para el nombre,
   la matrícula y la firma autógrafa del personal de Banco de Sangre, que se completan
   al momento de la transfusión y no representan una firma biométrica HES ni una FEA.

## Reglas
- Calibración RDLC exacta; no mover coordenadas sin verificar contra `test_*.pdf` de referencia.
- El membrete lateral derecho es una zona reservada: todos los motores deben calcular el ancho de contenido con `letterhead_content_width()` de `backend/pdf_engine_v2.py`, conservando la separación institucional antes de `LATERAL_X`. Ningún texto clínico, tabla o firma puede ocupar esa franja.
- Los PDF clínicos generados (expediente, notas, consentimientos) y de estudios entregados por la API incorporan metadatos internos `/Title` oficiales, cabecera `Content-Disposition` expuesta en CORS y nombres de archivo estandarizados (`Expediente_Completo_PT_{pt_num}.pdf`, `Nota_Urgencias_{pt_num}.pdf`, `Resultado_Estudio_PTMT_{ptmt_num}.pdf`, etc.). Esto evita que el navegador descargue o guarde los archivos con UUIDs aleatorios de los Blob URLs locales (`c32edfa1-...pdf`).
- Salida privada a `backend/generados/` y `backend/static/pdfs/` (gitignored). Esos directorios no se montan como webroot; los documentos se entregan únicamente por endpoints autenticados/autorizados.
- La preparación explícita `POST /pdf-preparar` está implementada para el
  consentimiento 09 guardado (`mrnum` exacto). Cada emisión recibe un
  identificador opaco `v1_*` y guarda el PDF exacto bajo
  `PRIVATE_STORAGE_ROOT/verified_pdfs`; el QR codifica únicamente
  `PUBLIC_VERIFICATION_BASE_URL/verificar?id=...` (se acepta la variable
  histórica `VERIFICATION_BASE_URL`). Así todos los QR abren la pantalla
  institucional diseñada para el cotejo público: cualquier persona con el QR
  ve nombre, folio, edad, estado y el botón al PDF oficial completo. Nunca
  incluye paciente, expediente,
  formato o ranura en la URL pública. La descarga pública vuelve a calcular
  SHA-256 y rechaza la copia si difiere del archivo registrado. Los demás
  motores aún requieren incorporar su preparación explícita; sus vistas GET
  autenticadas no deben anunciarse como copias QR resguardadas.
- Los nombres y sellos de paciente, representante y testigos se imprimen desde
  evidencia de firma vigente del código y la ranura exactos, verificada contra
  la versión clínica actual. No se rellenan espacios de
  testigos ni del representante desde el directorio de contactos por el solo
  hecho de estar registrados. Si queda un segundo lugar de testigo sin firma,
  aparece en blanco; el cierre operativo puede estar permitido sin que ello
  declare cumplimiento del número de testigos previsto por NOM-004.
- Los PDF especializados consultan el `mrnum` de la fila Vertical seleccionada
  antes de superponer su historial HES: una ranura no toma datos de otra, y los
  campos `pt_num`, `mrnum` y `slot` del historial no sustituyen la identidad de
  la versión seleccionada. `SignedBy` de Vertical identifica al usuario técnico
  que efectuó la operación nativa; no es nombre del médico ni sello FEA HES.
  Como identidad de la firma nativa, sólo `medico_tratante`/`n_medico` del
 registro Vertical pueden atribuirse al profesional cuando falta evidencia
 HES vigente; un nombre de censo mostrado en otros campos no prueba autoría.
- Las respuestas binarias capturadas manualmente se imprimen como una sola
  respuesta legible (por ejemplo, `SÍ` o `NO`) con color discreto; no se
  muestran casillas ASCII vacías como `[ ] SÍ [X] NO`.
- La descarga pública de un PDF ya resguardado es de solo lectura. El GET
  autenticado del consentimiento 09 conserva el QR estable de su paciente y
  ranura, actualiza la copia privada verificable y entrega una vista temporal;
  el POST de preparación usa el mismo flujo cuando se solicita desde el botón
  de impresión.
- El expediente clínico completo se compila con la evidencia vigente de cada
  formato registrado, conserva la ranura exacta, incluye todos los resultados
  de laboratorio e imagenología y anexa el PDF original del estudio cuando
  Vertical lo conserva. Si existe `PUBLIC_VERIFICATION_BASE_URL` público HTTPS,
  su carátula lleva un QR opaco que abre el cotejo y el PDF exacto de ese
  expediente compilado. El cotejo del compilado confirma integridad de la copia
  por SHA-256; no declara una firma FEA global ni atribuye la generación al
  último firmante de uno de sus formatos. Las firmas individuales permanecen
  en los documentos incluidos.
- Las notas 87/01 y 24 muestran el bloque de firma junto a **cada** evolución,
  tanto en el PDF individual como en el expediente completo; nunca se aplica la
  firma de la última evolución a todas las anteriores. En 87/01 la ranura de
  firma es el ordinal `num`; en 24 es `MRNum_24_HOJA_EVOL`, no el ordinal que
  se muestra en pantalla. El nombre de un MIP es atribución de colaboración,
  no evidencia de su firma biométrica.
- El consentimiento 32/01 incluye en el bloque del médico el registro nativo
  `SignedBy`/`SignedOn` de Vertical cuando existe; se etiqueta como usuario
  técnico y nunca se presenta como huella HES del médico o del paciente.
- En los formatos especializados y en el renderer universal con registros Vertical, la compilación lee
  primero el registro clínico más reciente y usa **su** `mrnum` para consultar
  las firmas; la fecha de la última huella no decide qué versión se imprime.
- Antes de entregar el expediente completo se ejecuta un preflight de firmas por
  formato y por evolución. La respuesta PDF expone `X-HES-Signature-Report` para que la interfaz
  avise si falta médico, paciente/representante o algún testigo. Si existe una
  firma HES activa que no puede vincularse a la versión clínica actual, la
  compilación se detiene y responde una acción `REVISAR_Y_REFIRMAR`: la interfaz
  pregunta si se desea revisar la versión vigente, lista los formatos afectados
  y abre directamente el primero para completar la nueva firma. Nunca se
  entrega una representación que aparente estar sin firma por una falla de
  lectura o sincronización. Una firma nativa de Vertical se conserva como
  evidencia nativa y no se promociona indebidamente a FEA HES.
- En desarrollo, si `PUBLIC_VERIFICATION_BASE_URL` no está configurada y la
  solicitud llega por `localhost` o una IP privada, la preparación se detiene
  con un mensaje de configuración: no se genera un QR que falle fuera del
  hospital. Producción debe configurar una dirección HTTPS con DNS público,
  proxy y certificado válidos para acceso desde la casa del paciente. Los PDF
  impresos antes de configurar esa dirección deben reimprimirse, porque el QR
  forma parte de sus bytes y no se puede cambiar sin generar una nueva copia.
- Los formatos que ya tienen motor especializado conservan su plantilla RDLC;
  cualquier otro formato activo del catálogo que tenga registros reales para
  el paciente entra automáticamente por `generate_formato_universal`, que
  imprime todos los campos devueltos por Vertical y su trazabilidad de firmas.
  Un formato sin registro para ese paciente no se agrega sólo por existir en el
  catálogo. Si una firma HES existe pero el controlador no puede resolverse, la
  compilación se bloquea para no ocultar evidencia.
- `preparar_produccion.py` verifica plantillas antes del pase.
- Evidencia actual: el snapshot clínico `CANONICAL_V2` es la evidencia primaria; el PDF generado después es una representación secundaria y la API no declara su hash como verificado. Cuando un flujo genere el PDF antes de firmar, debe incluir SHA-256 de sus bytes reales e identificador en el payload; cambiar un byte invalida `pdf.verificado`.
- Cada formato puede declarar `firmas_especiales_requeridas` con uno o varios roles. El PDF incorpora sólo esas áreas y muestra estado pendiente o nombre/fecha de la evidencia biométrica vigente, marcada como no FEA. PLT-09 coloca Banco de Sangre dentro del bloque de verificación transfusional de la primera hoja. El renderer universal usa la misma metadata para formatos futuros.

---
> 🤖 *Contexto IA: un formato nuevo requiere registrarse en `catalogo_formatos` y existir en el esquema Vertical. No necesita cambios en la compilación ni en la lógica de firmas: se integrará por el renderer universal hasta que se le agregue una plantilla especializada.*

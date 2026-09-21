---
aliases: [Normativa, NOM-004, NOM-024, Cumplimiento]
tags: [hes/normativa, hes/seguridad]
tipo: norma
modulo: transversal
actualizado: 2026-09-19
relacionados:
  - "[[00_Inicio]]"
  - "[[Seguridad-FEA]]"
  - "[[Biometria-DigitalPersona]]"
  - "[[Database]]"
---

# Normativa-NOM

Matriz de evidencia técnica; **no constituye una declaración de cumplimiento
normativo ni asesoría jurídica**. El cumplimiento sólo puede determinarse con
evidencia operativa, políticas institucionales y validación jurídica.

## Advertencia de revisión 2026-09-19

Los componentes criptográficos implementados no acreditan un circuito completo
de consentimiento correcto. La revisión
`../REVISION_FIRMA_Y_EXTENSIBILIDAD_2026-09-19.md` reproduce selección de firmas
sin ranura/versión exactas, destino Vertical distinto del documento firmado,
roles automáticos contradictorios y cierre marcado listo sin dos testigos.
También identifica un fallback inseguro para formatos nuevos. Esa pasada fue
diagnóstica; la corrección posterior y sus regresiones constan en
`../CORRECCION_FIRMA_BIOMETRICA_2026-09-19.md`. No confundir corrección técnica
con aceptación operativa ni validación institucional.

Para consentimientos, la [NOM-004, 10.1.1.10](https://dof.gob.mx/nota_detalle_popup.php?codigo=5272787)
contempla dos testigos; el flujo corregido los exige para los consentimientos
reconocidos y elimina la leyenda genérica de opcionalidad. La evidencia
biométrica del paciente no es la ECDSA médica ni
una FEA personal. Se requieren reglas por documento y validación institucional
del modelo de firma; la leyenda de la interfaz no certifica conformidad.

| Marco / tema | Clasificación | Evidencia o pendiente |
|---|---|---|
| Integridad de notas y firmas | `IMPLEMENTADO_TECNICAMENTE` | Payload CANONICAL_V2, SHA-256, ECDSA P-256, llave histórica exacta y verificación; ver [[Seguridad-FEA]]. |
| Sellado de tiempo | `IMPLEMENTADO_TECNICAMENTE` | Validación CMS, cadena de confianza, EKU, nonce e imprint; indisponibilidad queda `TSA_PENDIENTE`, no verificada. |
| Trazabilidad de acceso/operación | `IMPLEMENTADO_TECNICAMENTE` | Auditoría append-only con actor real/efectivo, acción, resultado, `request_id` y `operation_id`; logging redactado. |
| Confidencialidad técnica | `IMPLEMENTADO_TECNICAMENTE` | Rutas autenticadas, RBAC fail-closed, archivos privados, TLS exigido en producción y biometría FMD sin RAW nuevo. |
| Conservación, retención, destrucción y acceso | `REQUIERE_PROCEDIMIENTO_HOSPITAL` | Definir responsables, plazos, archivo, acceso de emergencia, baja y evidencia de ejecución. |
| Backup externo y restauración periódica | `EVIDENCIA_OPERATIVA_PENDIENTE` | Existe backup cifrable y restore sintético probado; falta evidencia periódica del entorno hospitalario y custodia fuera del host. |
| Roles funcionales y asignación médico-paciente | `REQUIERE_PROCEDIMIENTO_HOSPITAL` | Las rutas sin decisión están bloqueadas; Dirección debe aprobar la matriz funcional final. |
| Uso de firma electrónica y atribución biométrica | `REQUIERE_VALIDACION_JURIDICA` | Validar alcance de FEA, consentimiento, aviso de privacidad, conservación probatoria y relación con TSA. |
| NOM-004-SSA3-2012 / expediente clínico | `REQUIERE_VALIDACION_JURIDICA` | Correlacionar formatos, contenido, conservación y operación institucional con la norma aplicable. |
| NOM-024-SSA3-2012 / sistema ECE | `REQUIERE_VALIDACION_JURIDICA` | Evaluar interoperabilidad, catálogos, seguridad, evidencia y proceso de certificación aplicable. |

## Instrumentos institucionales pendientes

1. Convenio médico de aceptación y atribución de firma electrónica.
2. Consentimiento/aviso de tratamiento de datos personales sensibles.
3. Acta del Comité de Expediente Clínico y procedimiento de contingencia.

Los tres puntos son `REQUIERE_VALIDACION_JURIDICA` y
`REQUIERE_PROCEDIMIENTO_HOSPITAL`.

---
> 🤖 *Contexto IA: no dar asesoría legal; solo implementar controles técnicos aquí descritos. Cambios normativos → actualizar esta nota y [[Seguridad-FEA]].*

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
  - backend/pdf_engine_15.py
actualizado: 2026-09-17
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
| `pdf_engine_06.py`, `07`, `08`, `11` | 06, 07, 08, 11 |
| `pdf_engine_12.py` | 12 |
| `pdf_engine_15.py`, `pdf_engine_15_ev.py` | 15 (+ evolución) |
| `pdf_engine_19.py` | 19 |
| `pdf_engine_24.py`, `25` | 24, 25 |
| `pdf_engine_32_01.py`, `34_01.py`, `43` | 32/01, 34/01, 43 |
| `pdf_engine_eed.py`, `pdf_engine_expediente.py` | EED / expediente |
| `pdf_generator.py` | Comprobantes con QR |
| `services/pdf_service.py` | Fachada unificada |

## Elementos impresos (todos)
1. Cadena original (paciente, médico, cédula, resumen).
2. Sello digital FEA.
3. QR institucional verificable en `VerificarDocumento.jsx` → [[API-Endpoints]].

## Reglas
- Calibración RDLC exacta; no mover coordenadas sin verificar contra `test_*.pdf` de referencia.
- Salida privada a `backend/generados/` y `backend/static/pdfs/` (gitignored). Esos directorios no se montan como webroot; los documentos se entregan únicamente por endpoints autenticados/autorizados.
- `preparar_produccion.py` verifica plantillas antes del pase.
- Evidencia actual: el snapshot clínico `CANONICAL_V2` es la evidencia primaria; el PDF generado después es una representación secundaria y la API no declara su hash como verificado. Cuando un flujo genere el PDF antes de firmar, debe incluir SHA-256 de sus bytes reales e identificador en el payload; cambiar un byte invalida `pdf.verificado`.

---
> 🤖 *Contexto IA: nuevo formato = nuevo `pdf_engine_XX.py` + registro en `pdf_service.py` + entrada en `catalogo_formatos` + fila en esta tabla.*

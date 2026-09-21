---
aliases: [ADR-0001]
tags: [hes/arquitectura, hes/backend, tipo/adr]
tipo: adr
estado: aceptado
fecha: 2026-09-17
relacionados:
  - "[[Formatos-PDF]]"
  - "[[Pase_a_Produccion]]"
  - "[[Guia-Desarrollo-IA]]"
---

# ADR-0001: PDFs solo con ReportLab / xhtml2pdf (sin Word ni COM)

## Estado
Aceptado.

## Contexto
Se requiere generar formatos clínicos oficiales en Windows y Linux/Docker sin licencias Office.

## Decisión
Solo `reportlab (Platypus)` y `xhtml2pdf`. Prohibido `docx2pdf`, `pywin32`, `pythoncom`.

## Consecuencias
- 600 DPI vectorial portable; calibración RDLC manual en `pdf_engine_*.py`.
- `preparar_produccion.py` verifica plantillas; salida en `backend/generados/` (gitignored).

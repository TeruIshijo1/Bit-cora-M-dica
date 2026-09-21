---
aliases: [Glosario HES, Ubiquitous Language]
tags: [hes/arquitectura, tipo/moc]
tipo: moc
modulo: transversal
actualizado: 2026-09-17
relacionados:
  - "[[00_Inicio]]"
  - "[[Arquitectura]]"
---

# Glosario

| Término | Significado | Ver |
|---|---|---|
| FEA | Firma Electrónica Avanzada (ECDSA P-256 + TSA) | [[Seguridad-FEA]] |
| FMD | Finger Minutiae Data, plantilla ANSI/NIST 378 (no imagen) | [[Biometria-DigitalPersona]] |
| TSA | Time Stamping Authority, sellado RFC 3161 | [[Seguridad-FEA]] |
| KEK / HKDF | Llave de cifrado derivada vía HKDF-SHA256 (protege privada) | [[Seguridad-FEA]] |
| EHR / ECE | Expediente clínico electrónico | [[Backend]], [[Database]] |
| RDLC | Especificación de layout institucional para PDFs | [[Formatos-PDF]] |
| KH_HE | ERP SQL Server central, solo lectura vía `kh_database.py` | [[Backend]] |
| DIS_AL | Catálogo de alergias | [[Frontend]] (`AllergiesModal`) |
| Challenge 120s | Token de un solo uso anti-replay para firma | [[Seguridad-FEA]] |
| `historial_llaves_fea` | Tabla append-only de llaves públicas | [[Database]] |
| `pase_a_produccion/` | Paquete deploy (gitignored) | [[Pase_a_Produccion]] |
| MOC | Map of Content (índice Obsidian) | [[00_Inicio]] |
| ADR | Architecture Decision Record | `decisiones/` |

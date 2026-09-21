---
aliases: [ADR-0002]
tags: [hes/seguridad, hes/normativa, tipo/adr]
tipo: adr
estado: aceptado
fecha: 2026-09-17
relacionados:
  - "[[Seguridad-FEA]]"
  - "[[Database]]"
  - "[[Normativa-NOM]]"
---

# ADR-0002: Historial de llaves FEA append-only

## Estado
Aceptado (exigencia NOM-024 / no repudio).

## Contexto
Los médicos rotan credenciales biométricas; las firmas antiguas deben seguir verificables.

## Decisión
Tabla `historial_llaves_fea` append-only. Rotación = `activo=False` + `INSERT` nueva. Nunca `DELETE`/`UPDATE` destructivo.

## Consecuencias
- Verificación histórica por `medico_id + fecha_firma`.
- Toda rotación queda en `auditoria_logs`.

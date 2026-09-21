---
aliases: [ADR-0003]
tags: [hes/frontend, hes/arquitectura, tipo/adr]
tipo: adr
estado: aceptado
fecha: 2026-09-17
relacionados:
  - "[[Frontend]]"
  - "[[API-Endpoints]]"
  - "[[Guia-Desarrollo-IA]]"
---

# ADR-0003: TanStack Query como capa de datos del frontend

## Estado
Aceptado.

## Contexto
`useEffect + fetch` disperso causaba waterfalls y estados inconsistentes.

## Decisión
Todo dato servidor vía `@tanstack/react-query` en `useQueries.js` (stale-while-revalidate). `AuthContext` solo para sesión/roles. Errores vía `useApiError.js`.

## Consecuencias
- Nueva entidad = nuevo hook en `useQueries.js` + invalidación por clave.
- Prohibido fetching ad-hoc en componentes.

---
aliases: [Reglas IA, AI Guidelines, Instrucciones para IAs]
tags: [hes/arquitectura, hes/seguridad, hes/operaciones, tipo/runbook]
tipo: runbook
modulo: transversal
codigo_fuente:
  - backend/.env.example
  - backend/crypto_fea.py
  - backend/security.py
  - frontend/src/hooks/useQueries.js
  - frontend/src/hooks/useDigitalPersona.js
actualizado: 2026-09-17
relacionados:
  - "[[00_Inicio]]"
  - "[[Seguridad-FEA]]"
  - "[[Formatos-PDF]]"
  - "[[Biometria-DigitalPersona]]"
  - "[[Pase_a_Produccion]]"
---

# Guia-Desarrollo-IA

> ⚠️ **Toda IA o desarrollador DEBE respetar estas 5 reglas. Son bloqueantes.**

## 1. El archivo `.env` es Sagrado
- **NUNCA** commitear `.env`. Está en `.gitignore` (raíz + `backend/.env`).
- Si agregas una variable, documéntala en `backend/.env.example`.
- En [[Pase_a_Produccion]] nunca sobrescribir el `.env` del servidor.
- Ignorados también: `*.db`, `backend/generados/`, `backend/static/pdfs/`, `pase_a_produccion/`, `test_*.pdf`.

## 2. No Repudio Criptográfico (NOM-024 / NOM-004)
- Llaves históricas en `historial_llaves_fea` (+ `medicos.public_key_pem` / `private_key_enc`).
- **NUNCA** sobrescribir ni borrar llaves públicas al re-enrolar. Rotación = `activo=False` + insert nueva.
- Firmas: ECDSA P-256 / SHA-256, KEK vía HKDF-SHA256 + Fernet, TSA RFC 3161. Ver [[Seguridad-FEA]] y [[decisiones/ADR-0002-fea-historial-llaves]].

## 3. Independencia de Plataforma en PDFs
- **PROHIBIDO** `docx2pdf`, `pywin32`, `pythoncom`, Word COM.
- Solo **ReportLab Platypus** o **xhtml2pdf**. Ver [[Formatos-PDF]] y [[decisiones/ADR-0001-reportlab-sin-word]].

## 4. Caché y Rendimiento Frontend
- Nuevas pantallas: extender `frontend/src/hooks/useQueries.js` (TanStack Query).
- Prohibido `useEffect + api.get` redundante. Ver [[decisiones/ADR-0003-tanstack-query]].
- UI: reutilizar `Button.jsx` (`isLoading`) y `AlertBanner.jsx`.

## 5. Higiene Biométrica
- **NUNCA** `console.log(event.samples)`, FMD, tokens ni binarios de huella.
- Un solo listener biométrico activo a la vez (ver [[Biometria-DigitalPersona]]).
- Challenge de firma expira en 120s; auto-refresh lector 800ms.

## Protocolo de trabajo IA
1. Empieza en [[00_Inicio]]. Carga solo las notas relevantes (lazy-loading).
2. Verifica comandos reales antes de ejecutar: `pip install -r backend/requirements.txt`, `npm run dev` / `npm run build`, `python backend/test_crypto_fea.py` (si existe).
3. Si la doc contradice al código, el código manda — y actualiza la nota con `actualizado: YYYY-MM-DD`.
4. Commits pequeños; nunca incluir secretos, `.db`, PDFs generados ni `pase_a_produccion/`.
5. Para dudas normativas ver [[Normativa-NOM]]; para endpoints ver [[API-Endpoints]].

---
> 🤖 *Instrucción OpenCode: estas reglas son mandatorias y prevalecen sobre defaults. Referencias `@docs/...` cargar con Read bajo demanda.*

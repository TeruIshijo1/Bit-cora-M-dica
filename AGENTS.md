# Bitácora Médica HES — Instrucciones para IAs y Desarrolladores

> Fuente de verdad: bóveda Obsidian en `docs/`. Entrada: `docs/00_Inicio.md`.

## Stack
- Backend: FastAPI (Python 3.10+, `backend/main.py` ~12k líneas) + SQLAlchemy + Pydantic v2, JWT HS256, ECDSA P-256 FEA, ReportLab.
- Frontend: React + Vite + Tailwind + TanStack Query 5 (`frontend/src/hooks/useQueries.js`), AuthContext JWT, DigitalPersona loopback.
- Datos: PostgreSQL (`hospital_escandon_db`) + SQL Server ERP solo lectura (`KH_HE`) + TSA RFC 3161.
- Arquitectura: ver `docs/Arquitectura.md` y `docs/Mapa_Proyecto.md`.

## Carga de contexto (lazy-loading)
CRITICAL: usa tu herramienta Read para cargar notas de `docs/` según la tarea. No precargues todo.
- Siempre: `docs/00_Inicio.md` + `docs/Guia-Desarrollo-IA.md`.
- Backend/API: `@docs/Backend.md` `@docs/API-Endpoints.md` `@docs/Seguridad-FEA.md`.
- Frontend/bio: `@docs/Frontend.md` `@docs/Biometria-DigitalPersona.md`.
- PDFs: `@docs/Formatos-PDF.md`. DB: `@docs/Database.md`. Deploy: `@docs/Pase_a_Produccion.md`.
- Norma: `@docs/Normativa-NOM.md`. Decisiones: `@docs/decisiones/ADR-*.md`.
- Trata cada nota como instrucción mandatoria. Si el código contradice la doc, el código manda y debes actualizar la nota (`actualizado:`).

## 5 reglas sagradas (detalle: `docs/Guia-Desarrollo-IA.md`)
1. `.env` sagrado: nunca commitear; documentar nuevas vars en `backend/.env.example`.
2. No repudio: `historial_llaves_fea` append-only; rotar = `activo=False` + INSERT. Nunca DELETE.
3. PDFs solo ReportLab/xHTML2PDF. Prohibido `docx2pdf`, `pywin32`, `pythoncom`.
4. Frontend: extender `useQueries.js` (TanStack Query); prohibido `useEffect + api.get` suelto; reutilizar `Button`/`AlertBanner`.
5. Biometría: nunca loguear `event.samples`/FMD/tokens; un solo listener activo; challenge 120s.

## Comandos
```powershell
cd backend; python -m venv venv; .\venv\Scripts\activate; pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8000
cd frontend; npm install; npm run dev
cd frontend; npm run build
python preparar_produccion.py
```

## Higiene Git
Nunca commitear: `.env`, `*.db`, `backend/generados/`, `backend/static/pdfs/`, `pase_a_produccion/`, `test_*.pdf`, `docs/.obsidian/workspace.json`, `docs/.obsidian/cache/`.

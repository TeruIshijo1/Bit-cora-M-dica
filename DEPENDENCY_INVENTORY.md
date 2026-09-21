# Inventario de dependencias y vulnerabilidades

Fecha de corte: 2026-09-17. Los inventarios transitivos reproducibles son
`frontend/package-lock.json`, `mobile_app/package-lock.json` y
`biometric-service/package-lock.json`; Python se define en
`backend/requirements.txt` y se escanea con `pip-audit`.

| Componente | Inventario runtime | Scanner | Resultado |
|---|---:|---|---|
| Frontend web | 138 paquetes de producción | `npm audit --omit=dev` | 0 vulnerabilidades |
| Servicio biométrico | 73 paquetes de producción | `npm audit --omit=dev` | 0 vulnerabilidades |
| Aplicación móvil | 669 paquetes de producción | `npm audit --omit=dev` | 14 moderadas; 0 high; 0 critical |
| Backend Python | 26 requisitos directos; árbol resuelto por `pip-audit` | `pip-audit -r backend/requirements.txt` | 1 advisory único, reportado dos veces; sin versión corregida |

## Dependencias directas

- Backend: FastAPI, Uvicorn, SQLAlchemy, Pydantic, psycopg2, pyodbc,
  python-jose, cryptography, ReportLab, xhtml2pdf, pypdf, pyHanko, Pillow,
  requests, Alembic y utilitarios declarados en `requirements.txt`.
- Frontend: React 19, Vite 8, TanStack Query 5, Axios, DigitalPersona,
  pdfjs/jsPDF, Tailwind y Recharts.
- Móvil: Expo SDK 57, React Native 0.86, Expo Router 57, Axios y SecureStore.
- Biometría: Express 5, CORS y `uareu-biometric`.

## Riesgos restantes y tratamiento

### `ecdsa==0.19.2` — CVE-2024-23342 / GHSA-wj6h-64fc-37mp

- Estado: sin release corregido; `pip-audit` lo identifica como
  `PYSEC-2026-1325` (duplicado en la salida, un solo advisory).
- Ruta: dependencia transitiva de `python-jose`.
- Explotación relevante: ataque de temporización Minerva al firmar ECDSA P-256
  con `python-ecdsa`.
- Mitigación aplicada: HES fija los JWT a HS256; no invoca firma ECDSA de
  `python-jose`. La FEA P-256 usa `cryptography`, que no depende de esa ruta. La
  API no expone una primitiva de firma `python-ecdsa`.
- Fecha objetivo: 2026-10-15, retirar la dependencia transitiva o reevaluar una
  versión corregida manteniendo la batería criptográfica completa.

### Expo — 14 advisories moderados

- Paquetes: toolchain Expo/config/Metro/Xcode y cadenas `query-string` /
  `decode-uri-component` / `uuid`.
- No quedan HIGH ni CRITICAL. La corrección automática propuesta por npm
  degrada componentes mayores (incluido Expo 46/Router 5) y rompe el contrato
  validado de SDK 57, por lo que no se aplicó.
- Mitigación: aplicación móvil nativa, servidor configurado sólo por HTTPS fuera
  de desarrollo, sin exposición del toolchain de compilación como servicio.
  Persiste riesgo moderado de entradas URI malformadas; se prueba typecheck y se
  conserva lockfile.
- Fecha objetivo: 2026-10-15, reevaluar releases compatibles de Expo 57 y repetir
  typecheck/pruebas antes de cambiar el lockfile.

No hay vulnerabilidades HIGH/CRITICAL de runtime aceptadas en este corte.

# 🏥 Bitácora Médica HES (MediReg HES)

Sistema integral de gestión clínica, control de atenciones médicas, expediente electrónico (EHR), auditoría biométrica y generación de formatos clínicos oficiales para el **Hospital Escandón**.

---

## 📌 Resumen Ejecutivo

**Bitácora Médica HES** es una plataforma hospitalaria moderna diseñada para optimizar los flujos de trabajo médicos, administrativos y de enfermería, asegurando la integridad, trazabilidad y cumplimiento normativo (**NOM-004-SSA3-2012**) de cada registro clínico.

### ✨ Capacidades Principales:
- 🩺 **Expediente Clínico Electrónico (EHR Dashboard):** Vista integral del paciente con datos demográficos, signos vitales en tiempo real, alergias destacadas, medicamentos activos y línea de tiempo interactiva de notas médicas y eventos.
- 📄 **Motor Oficial de Formatos Clínicos PDF (ReportLab V2):** Generador dinámico de notas médicas con diseño institucional de alta fidelidad (100% idéntico a especificaciones RDLC e Illustrator), membretes a 600 DPI, maquetación SOAP fluida y paginación automática.
- 🔒 **Autenticación Biométrica Criptográfica:** Integración con lectores de huellas dactilares **DigitalPersona (U.are.U SDK)** para firma y sellado SHA-256 de notas y procedimientos con generación de comprobantes con código QR.
- 🛏️ **Censo y Ocupación de Camas:** Monitoreo en tiempo real de la ocupación hospitalaria por área sincronizado directamente con la base de datos central.
- 👨‍⚕️ **Control de Procedimientos y Honorarios:** Registro auditable de consultas, interconsultas y jornadas por médico especialista con validación administrativa.

---

## 🏗️ Arquitectura y Stack Tecnológico

```mermaid
graph TD
    Client["💻 Frontend React + Vite + Tailwind"] -->|"REST API :8000"| Backend["🐍 Backend FastAPI / Python"]
    Client -->|"Biometría (Firma)"| BiometricSvc["📦 Repo: Bio-security Node.js"]
    Backend -->|"Lectura / Escritura"| Postgres["🐘 PostgreSQL Principal"]
    Backend -->|"Solo Lectura"| SQLServer["🏥 SQL Server KH_HE"]
    Backend -->|"ReportLab V2 Engine"| PDFGen["📄 Generador PDF Formatos"]
    Backend -->|"Motor FEA"| Crypto["🔐 Criptografía ECDSA P-256 + HKDF"]
    Crypto -->|"Sello de Tiempo RFC 3161"| TSA["⏱️ Time Stamping Authority"]
```

### 1. **Frontend (`/frontend`)**
- **Framework:** React 18 con Vite.
- **Estilos:** Tailwind CSS con paleta institucional Hospital Escandón (`hes-blue-main`, `hes-blue-light`, `hes-emerald`).
- **Iconografía:** Lucide React & React Icons.
- **Cliente HTTP:** Axios configurado con interceptores de autenticación.

### 2. **Backend API (`/backend`)**
- **Framework:** FastAPI (Python 3.x) con Uvicorn.
- **ORM:** SQLAlchemy + Pydantic v2.
- **Generación de Reportes:** ReportLab Platypus (`pdf_engine_v2.py`) calibrado exactamente según especificaciones de reportes RDLC y `xhtml2pdf` para comprobantes QR.
- **Conectividad Externa:** `pyodbc` para enlace seguro de solo lectura con SQL Server.

### 3. **Microservicio Biométrico (`/backend_node` y `Bio-security`)**
- **Servidor:** Node.js (Express) en el puerto `8082`.
- **Hardware:** SDK nativo DigitalPersona U.are.U para captura y verificación 1:1 / 1:N de huellas dactilares.
- **Repositorio Independiente:** El componente completo de biometría e integración de huella dactilar utiliza su propio repositorio dedicado: **[Bio-security](../Bio-security)**.

### 4. **Bases de Datos**
- **PostgreSQL (`hospital_escandon_db`):** Base de datos transaccional principal del sistema (usuarios, sesiones, roles, firmas biométricas, registros de atenciones y auditoría).
- **SQL Server (`KH_HE`):** Sistema hospitalario central. La conexión es de **estricta solo lectura** mediante variables de entorno `KH_*` para alimentar el censo de pacientes, camas, signos vitales y notas de evolución.

---

## 📂 Estructura del Proyecto

```text
Bitacora_HES/
├── backend/                        # API REST en FastAPI (Python)
│   ├── main.py                     # Endpoints REST y ruteo principal
│   ├── kh_database.py              # Conexión y consultas a SQL Server (KH_HE)
│   ├── pdf_engine_v2.py            # Motor PDF ReportLab V2 (Alta fidelidad RDLC)
│   ├── pdf_generator.py            # Generador de comprobantes de atención con QR
│   ├── models.py / schemas.py      # Modelos SQLAlchemy y esquemas Pydantic
│   ├── requirements.txt            # Dependencias de Python
│   ├── scripts/                    # Scripts utilitarios (ej. extracción de assets)
│   ├── static/                     # Assets estáticos (logos, firmas, membretes)
│   └── templates/                  # Plantillas HTML para reportes
├── backend_node/                   # Microservicio biométrico en Node.js
│   ├── server.js                   # Endpoints biométricos (Express)
│   └── package.json                # Dependencias de Node
├── frontend/                       # Aplicación Web SPA (React + Vite)
│   ├── src/
│   │   ├── pages/                  # Vistas (PatientDashboard, Expediente, etc.)
│   │   ├── components/             # Componentes UI reutilizables
│   │   └── api/                    # Configuración de clientes Axios
│   ├── package.json
│   └── vite.config.js
├── Formatos VERTICAL/              # Documentación y assets fuente de formatos clínicos
│   ├── Encabezado, pie, lateral/   # Elementos gráficos institucionales a 600 DPI
│   ├── 87_01_NOTA DE EVOLUCION...  # Formato muestra oficial autorizado por Calidad
│   └── README_FORMATOS.md          # Guía técnica para crear nuevos formatos clínicos
├── iniciar.bat                     # Script para levantar los servicios locales
├── instalar server.bat             # Script para instalar dependencias completas
├── preparar_produccion.py          # Script de empaquetado seguro para despliegue
├── README.md                       # Documentación principal del repositorio
├── README_FORMATOS.md              # Documentación de diseño y geometría de formatos
└── README_PRUEBAS_SQL.md           # Guía de pruebas e inyección de datos en SQL Server (Vertical)
```

---

## 📐 Motor de Formatos Clínicos Oficiales

El sistema cuenta con un motor de renderizado de alta fidelidad que reproduce los formatos aprobados por la Dirección Médica y Calidad del Hospital Escandón:

* **Especificaciones Geométricas RDLC:**
  * **Página:** Tamaño Carta (`21.59 cm × 27.94 cm` / `612 × 792 pt`).
  * **Contenedor Principal:** `20.10 cm × 25.50 cm` con borde perimetral `MidnightBlue` (`#191970`).
  * **Margen Inferior:** `47.91 pt` para total compatibilidad con impresoras láser y rodillos sin cortes.
  * **Estructura Clínica SOAP:** Secciones `(S) Subjetivo`, `(O) Objetivo`, `(A) Análisis` y `(P) Plan` con auto-paginación y preservación de firmas de médico tratante y MIP.

> Para más detalles sobre cómo agregar o adaptar nuevos formatos hospitalarios, consulta la [Guía Maestra de Formatos](Formatos%20VERTICAL/README_FORMATOS.md).

---

## 🚀 Puesta en Marcha (Desarrollo Local)

### Requisitos Previos
* **Python 3.10+**
* **Node.js 18+** y `npm`
* **PostgreSQL** instalado y configurado
* Driver ODBC `{SQL Server}` de Windows
* Lector biométrico DigitalPersona (opcional para pruebas sin hardware)

### 1. Instalación Rápida
Ejecuta el script automatizado en la raíz:
```cmd
"instalar server.bat"
```
O de forma manual:
```powershell
# 1. Backend Python
cd backend
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt

# 2. Microservicio Biométrico
cd ..\backend_node
npm install

# 3. Frontend React
cd ..\frontend
npm install
```

### 2. Configuración de Variables de Entorno (`backend/.env`)
Crea o verifica el archivo `.env` dentro de `backend/`:
```env
# Base de Datos Local PostgreSQL
DATABASE_URL=postgresql://usuario:password@localhost:5432/hospital_escandon_db

# Base de Datos Hospitalaria Externa (SQL Server KH_HE vía Tailscale Mesh VPN)
KH_SERVER=127.0.0.1,1433
KH_DATABASE=KH_HE
KH_USERNAME=escandon_bi_user
KH_PASSWORD=tu_password_sql

# Para más información de la conexión de red, consulta:
# GUIA_CONEXION_PRODUCCION_TAILSCALE.md

# Seguridad JWT
SECRET_KEY=clave_secreta_super_segura
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=480
```

### 3. Iniciar el Entorno
Ejecuta el script de inicio simultáneo:
```cmd
iniciar.bat
```
* **Frontend:** `http://localhost:5173`
* **Backend API (Swagger Docs):** `http://localhost:8000/docs`
* **Microservicio Biométrico:** `http://localhost:8082`

---

## 🚢 Despliegue a Producción (CI / CD Seguro)

El proyecto implementa una estricta política de separación entre entornos: **nunca se edita código directamente en el servidor de producción**.

Para empaquetar una versión lista para producción:
```powershell
python preparar_produccion.py
```

Este script automatizado realiza:
1. Compilación optimizada del Frontend React (`npm run build` ➔ `dist/`).
2. Empaquetado limpio del backend Python y microservicio Node en la carpeta `pase_a_produccion/`.
3. **Exclusión estricta y segura** de credenciales (`.env`), entornos virtuales (`venv/`), `node_modules/` y bases de datos locales para proteger la integridad del servidor.
4. El contenido de `pase_a_produccion/` se copia directamente al servidor de producción sin riesgo de sobrescribir contraseñas ni configuración local.

---

## 📄 Licencia y Confidencialidad

Propiedad exclusiva del **Ing. Alberto García Mendoza**.  
Todos los derechos reservados. El uso, copia o distribución no autorizada de este código o sus especificaciones clínicas está estrictamente prohibido.

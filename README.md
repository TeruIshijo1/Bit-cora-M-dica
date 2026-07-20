# Bitácora Médica HES (MediReg HES)

El sistema **Bitácora Médica HES** es una plataforma interna desarrollada para el Hospital Escandón, diseñada para llevar un registro seguro y auditable de las actividades médicas y de enfermería. 

Su principal propósito es garantizar la integridad y trazabilidad de los registros hospitalarios mediante:
- **Autenticación Biométrica:** Integración con lectores de huellas dactilares (DigitalPersona) para asegurar que cada acción esté firmada criptográficamente o respaldada por el personal correcto.
- **Gestión de Registros Médicos:** Captura ágil de datos de los pacientes y procedimientos desde las estaciones de enfermería.
- **Trazabilidad:** Monitoreo en tiempo real para administradores y responsables médicos.

---

## 🤖 Contexto para Agentes de Inteligencia Artificial
*(Si eres una IA leyendo esto, asume este contexto antes de hacer cualquier modificación en el código)*

### 1. Arquitectura y Stack Tecnológico
- **Frontend:** React + Vite. El código fuente está en la carpeta `frontend/`.
- **Backend:** FastAPI (Python). El código está en la carpeta `backend/` usando un entorno virtual (`venv`).
- **Microservicio Biométrico:** Node.js (Express) corriendo en el puerto 8082, ubicado en `backend_node/`. Usa el SDK U.are.U para lectura de huellas digitales.

### 2. Bases de Datos (¡MUY IMPORTANTE!)
- **Base de Datos Principal:** La aplicación usa **PostgreSQL** (`hospital_escandon_db`). Se conecta usando variables de entorno cargadas desde un archivo `.env` mediante SQLAlchemy. *(Nota: Inicialmente usaba SQLite, pero ya fue migrada a Postgres. NO uses SQLite).*
- **Base de Datos Hospitalaria Externa (`KH_HE`):** El sistema se conecta en modo de **solo lectura** a una base de datos externa de SQL Server del hospital a través de `pyodbc` (usando el driver clásico `{SQL Server}`). Esta conexión se maneja en el archivo `backend/kh_database.py` usando variables con prefijo `KH_` (ej. `KH_SERVER`, `KH_USERNAME`) para evitar colisiones con variables globales de Windows.
- Existe una tarea de sincronización que trae el estado en tiempo real de las **Camas y Pacientes** desde `KH_HE` hacia la base de datos de PostgreSQL para visualizarlas en el frontend.

### 3. Flujo de Despliegue a Producción (CI/CD)
- **Regla de oro:** Desarrollamos y probamos TODO en la computadora local. **Nunca modificamos código directamente en el servidor de producción.**
- Para pasar a producción, ejecutamos el script local **`preparar_produccion.py`**. Este script automatiza:
  1. Compilación del frontend de React (`npm run build`).
  2. Empaquetado de todo el proyecto en una carpeta limpia llamada `pase_a_produccion`.
  3. Exclusión intencional del archivo `.env`, carpetas `venv`, `node_modules` y cualquier base de datos `.db` o `.sqlite` local.
- **Despliegue final:** Se copia el contenido de `pase_a_produccion` manualmente al servidor. Al no incluir el archivo `.env`, se garantiza que las credenciales y la base de datos del servidor de producción jamás se sobrescriban.

---

## Requisitos Previos (Desarrollo Local)
- Python 3.x
- Node.js
- (Opcional) Hardware de lector de huellas DigitalPersona para las funcionalidades de biometría.

## Cómo ejecutar localmente
Existen scripts `.bat` en la raíz para facilitar la ejecución y configuración del entorno en Windows:
- `instalar server.bat`: Para instalar dependencias tanto de Python como de Node.js.
- `iniciar.bat`: Para levantar los servicios locales (inicia el frontend, el backend de FastAPI y el microservicio de Node.js simultáneamente).

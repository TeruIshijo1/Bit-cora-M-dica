# Mapa del Proyecto

Visión general y diagrama de interconexión entre todos los módulos del sistema hospitalario HES.

```mermaid
graph LR
    subgraph Cliente ["Interfaz de Usuario"]
        F["[[Frontend]] (React + TanStack Query)"]
    end

    subgraph Servidor ["Lógica de Negocio"]
        B["[[Backend]] (FastAPI + Routers + Services)"]
    end

    subgraph Persistencia ["Almacenamiento"]
        D["[[Database]] (PostgreSQL + Backups)"]
        SQL["SQL Server ERP (KH_HE)"]
    end

    subgraph Despliegue ["Operaciones"]
        P["[[Pase_a_Produccion]] (Empaquetado Seguro)"]
    end

    F -->|REST API JWT| B
    B -->|SQLAlchemy| D
    B -->|pyodbc| SQL
    B -.-> P
    F -.-> P
```

## Resumen de Módulos
- **[[Frontend]]:** SPA React 18 con Vite, UI Kit atómico, TanStack Query y captura de huellas DigitalPersona.
- **[[Backend]]:** FastAPI modular con routers (`catalogos.py`), servicios (`pdf_service.py`) y motor criptográfico asimétrico FEA.
- **[[Database]]:** PostgreSQL con modelos clínicos, logs inmutables y tabla `historial_llaves_fea`.
- **[[Pase_a_Produccion]]:** Protocolo de empaquetado seguro excluyendo credenciales sensibles.

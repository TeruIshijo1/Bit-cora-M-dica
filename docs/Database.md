# Database

Este componente gestiona la persistencia de datos de toda la aplicación, estructurando la información que maneja el proyecto.

## Tecnologías y Archivos Clave
- Actualmente configurada en SQLite (`hospital_escandon.db`), cuenta con respaldos automáticos (`hospital_escandon_backup.db`).
- Existen scripts de migración para escalar hacia PostgreSQL (`migrate_to_postgres.py`).
- `database.py`: Configuración de la conexión y sesión con la base de datos.
- `models.py`: Definición de los modelos ORM (mapeo objeto-relacional).
- `schemas.py`: Validación de la estructura de datos entrante y saliente.

## Relaciones en el Proyecto
- Es consumida, leída y modificada exclusivamente por el [[Backend]].
- Durante el ciclo de [[Pase_a_Produccion]], es de suma importancia asegurar los respaldos de este componente y aplicar las migraciones necesarias al esquema.

# Database

Este componente gestiona la persistencia de datos de toda la aplicación, estructurando la información clínica y garantizando el no repudio y la custodia legal.

## Tecnologías y Modelos Clave
- **Motor Principal:** PostgreSQL (`hospital_escandon_db`).
- **ORM:** SQLAlchemy + Pydantic v2.
- **Historial de Llaves FEA:** Tabla `historial_llaves_fea` para preservar todas las llaves públicas históricas de los médicos y validar firmas antiguas ante rotaciones biométricas.
- **Auditoría y Trazabilidad:** Tabla `auditoria_logs` para registro inmutable de acciones operativas.
- **Modelos Principales:** `Usuario`, `Medico`, `Paciente`, `AtencionMedica`, `FormatoClinico`, `NotaEnfermeria`, `HistorialLlaveFEA`.

## Estrategia de Respaldos
- **Windows:** `scripts/backup_db.bat` ejecuta `pg_dump` con rotación automática de 14 días.
- **Linux / Docker:** `scripts/backup_db.sh` genera volcados comprimidos con `gzip` (`hes_backup_*.sql.gz`) configurado para `crontab`.

## Relaciones en el Proyecto
- Es consumida, leída y modificada exclusivamente por el [[Backend]].
- En [[Pase_a_Produccion]], es de suma importancia verificar las credenciales en `.env` y asegurar la ejecución periódica de los scripts de respaldo.

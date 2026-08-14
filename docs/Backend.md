# Backend

El Backend es el motor lógico del proyecto, encargado de procesar las peticiones del [[Frontend]] y aplicar las reglas de negocio.

## Tecnologías Principales
- Python (usando frameworks modernos, posiblemente FastAPI).
- Entornos virtuales para manejo de dependencias (`venv`, `requirements.txt`).
- También existe una variante o servicio en Node (`backend_node`).

## Archivos y Módulos Clave
- `main.py`: Punto de entrada principal de la API.
- `pdf_generator.py`: Encargado de la generación dinámica de reportes en PDF.
- `seed.py`: Poblamiento inicial de datos.

## Relaciones en el Proyecto
- Provee los endpoints REST/GraphQL que son consumidos directamente por el [[Frontend]].
- Interactúa estrechamente con la [[Database]] para gestionar y persistir los datos (utilizando `models.py` y `schemas.py`).
- Su despliegue y scripts de arranque (ej. `iniciar.bat`, `instalar server.bat`) se asocian a la etapa de [[Pase_a_Produccion]].

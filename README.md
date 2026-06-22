# Bitácora Médica HES

Sistema de bitácora médica para el Hospital Escandón.

## Estructura del Proyecto

El proyecto está compuesto por los siguientes módulos principales:

- **frontend/**: Aplicación frontend construida con React y Vite.
- **backend/**: API principal del sistema (Python/FastAPI).
- **backend_node/**: Servicios secundarios en Node.js (probablemente utilizados para la integración con lectores biométricos).
- **Instalacion_Enfermeria/**: Archivos y scripts para la instalación de los clientes o componentes en las estaciones de enfermería (incluye integración con DigitalPersona).

## Requisitos Previos

- Python 3.x
- Node.js
- (Opcional) Hardware de lector de huellas DigitalPersona para las funcionalidades de biometría.

## Cómo ejecutar localmente

Existen scripts `.bat` en la raíz para facilitar la ejecución y configuración del entorno en Windows:

- `instalar.bat`: Para instalar dependencias.
- `iniciar.bat`: Para levantar los servicios locales.

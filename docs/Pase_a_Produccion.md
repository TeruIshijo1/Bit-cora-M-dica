# Pase a Producción

Protocolo oficial de despliegue y empaquetado seguro para el Hospital Escandón.

## Reglas de Oro
1. **El archivo `.env` es Sagrado:** Nunca se sobrescribe en el servidor ni se incluye en el control de versiones.
2. **Sin compilación en el servidor:** El código visual se compila en el entorno de desarrollo (`npm run build`) y se envía como assets estáticos empaquetados.
3. **Multiplataforma Linux / Docker:** El backend no contiene librerías dependientes de Windows COM ni Microsoft Word.

## Proceso Automatizado
Ejecutar el script en la raíz del proyecto:
```powershell
python preparar_produccion.py
```

### Lo que hace el script:
1. Compila el [[Frontend]] con Vite hacia `dist/`.
2. Empaqueta el [[Backend]] en `pase_a_produccion/` excluyendo `venv/`, `.env` y archivos temporales.
3. Verifica la integridad de las plantillas y motores PDF.
4. Genera el directorio listo para ser sincronizado con el servidor de producción.

@echo off
echo ===================================================
echo   Iniciando MediReg HES - Entorno Productivo
echo ===================================================
echo ===================================================
echo Para usar el sistema, abre tu navegador en:
echo - http://localhost:8000  (Si estas en esta misma PC)
echo - http://192.168.254.249:8000 (Desde cualquier otra PC en la red)
echo ===================================================

echo Iniciando el servidor principal de Python y el servicio Biometrico...
npx concurrently -n "PYTHON,BIOMETRICO" -c "bgBlue.bold,bgMagenta.bold" "cd backend && call venv\Scripts\activate && python seed.py && uvicorn main:app --host 0.0.0.0 --port 8000" "cd backend_node && node server.js"

:: El script termina aquí.
exit

@echo off
echo ===================================================
echo   Iniciando MediReg HES - Entorno Productivo
echo ===================================================
echo ===================================================
echo Para usar el sistema, abre tu navegador en:
echo - http://localhost:8000  (Si estas en esta misma PC)
echo - http://192.168.254.150:8000 (Desde cualquier otra PC o Tablet en la red)
echo ===================================================

echo ===================================================
echo Iniciando el servidor principal de Python, el servicio Biometrico y Ngrok...
npx concurrently -n "PYTHON,BIOMETRICO,NGROK" -c "bgBlue.bold,bgMagenta.bold,bgGreen.bold" "cd backend && (if exist venv\Scripts\activate.bat call venv\Scripts\activate.bat) && python seed.py && python -m uvicorn main:app --host 0.0.0.0 --port 8000" "cd backend_node && node server.js" "ngrok http 8000 --log=stdout"

:: El script termina aquí.
exit

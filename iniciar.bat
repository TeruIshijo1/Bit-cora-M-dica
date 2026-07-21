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
echo Abriendo tunel seguro con Ngrok para las tablets...
start "Ngrok Tunnel" "D:\Escritorio\escandon-bi\ngrok.exe" http 8000
echo Copia el enlace HTTPS que aparezca en la ventana negra de Ngrok.
echo ===================================================

echo Iniciando el servidor principal de Python y el servicio Biometrico...
npx concurrently -n "PYTHON,BIOMETRICO" -c "bgBlue.bold,bgMagenta.bold" "cd backend && python seed.py && python -m uvicorn main:app --host 0.0.0.0 --port 8000" "cd backend_node && node server.js"

:: El script termina aquí.
exit

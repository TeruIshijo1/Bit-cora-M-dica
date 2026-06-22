@echo off
echo ===================================================
echo   Iniciando MVP Bitacora-HES - Hospital Escandon
echo ===================================================

echo Iniciando todos los servicios en esta unica ventana...
npx concurrently -n "PYTHON,REACT,BIOMETRICO" -c "bgBlue.bold,bgGreen.bold,bgMagenta.bold" "cd backend && call venv\Scripts\activate && uvicorn main:app --host 0.0.0.0 --port 8000" "cd frontend && npm run dev -- --host 0.0.0.0 --port 5173" "cd backend_node && node server.js"

:: El script termina aquí.
exit

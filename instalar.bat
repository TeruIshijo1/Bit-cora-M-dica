@echo off
echo ===================================================
echo   Instalando Dependencias Bitacora-HES
echo ===================================================

echo.
echo [1/3] Instalando dependencias del Backend (Python)...
cd backend
call venv\Scripts\activate
pip install -r requirements.txt
pip install requests
cd ..

echo.
echo [2/3] Instalando dependencias del Frontend (React)...
cd frontend
call npm install
cd ..

echo.
echo [3/3] Instalando dependencias del Microservicio (Node.js)...
cd backend_node
call npm install
cd ..

echo.
echo ===================================================
echo Instalacion completada!
echo Ahora puedes ejecutar iniciar.bat
echo ===================================================
pause

@echo off
echo ===================================================
echo   Instalando Dependencias Bitacora-HES
echo ===================================================

echo.
echo [1/3] Instalando dependencias del Backend (Python)...
cd backend
echo Configurando entorno virtual de Python (esto puede tardar un poco)...
if exist venv rmdir /s /q venv
python -m venv venv
call venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cd ..

echo.
echo [2/3] Instalando dependencias del Frontend (React)...
cd frontend
call npm install
call npm run build
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

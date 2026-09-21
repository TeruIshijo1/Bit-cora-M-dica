@echo off
setlocal
cd /d "%~dp0"
echo INSTALACION DE ESTACION HES - MEDICOS / ENFERMERIA
echo Ejecute con la cuenta Windows que usara Bitacora.
echo El runtime puede solicitar elevacion; el agente se instala por usuario.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Instalar_Estacion.ps1"
set "HES_INSTALL_EXIT=%ERRORLEVEL%"
if "%HES_INSTALL_EXIT%"=="0" goto done
echo INSTALACION PENDIENTE O FALLIDA. Revise el mensaje anterior.
:done
pause
exit /b %HES_INSTALL_EXIT%

@echo off
setlocal enabledelayedexpansion
color 0b
cd /d "%~dp0"
echo ====================================================
echo   INSTALADOR DE ENFERMERIA - HOSPITAL ESCANDON
echo ====================================================
echo.
echo Este instalador preparara esta computadora para que las
echo enfermeras puedan utilizar la Bitacora HES con el lector
echo de huellas.
echo.
echo Instrucciones: Por favor, espera y NO CIERRES esta ventana.
echo.

:: 1. Instalar el Componente WebSDK (DigitalPersona Lite Client)
echo.
echo [1/1] Instalando Controlador DigitalPersona (WebSDK)...
if exist "DigitalPersona_Web_Client\x64\setup.exe" (
    echo.
    echo ==========================================================
    echo ATENCION: Se abrira el instalador de huellas DigitalPersona.
    echo.
    echo IMPORTANTE: Si al finalizar te pide REINICIAR LA PC, 
    echo puedes aceptar sin problema. LA INSTALACION YA TERMINO.
    echo ==========================================================
    echo.
    start /wait "" "DigitalPersona_Web_Client\x64\setup.exe"
    echo Controlador instalado.
) else (
    echo [ADVERTENCIA] No se encontro 'DigitalPersona_Web_Client\x64\setup.exe'.
    echo El lector de huellas podria no funcionar correctamente sin esto.
)

:fin
echo.
echo ====================================================
echo   INSTALACION COMPLETADA CON EXITO
echo ====================================================
echo Ya puedes desconectar la memoria USB.
echo.
pause

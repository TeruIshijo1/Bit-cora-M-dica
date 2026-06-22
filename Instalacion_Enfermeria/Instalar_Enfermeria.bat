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
echo de huellas y creara un icono en el escritorio.
echo.
echo Instrucciones: Por favor, espera y NO CIERRES esta ventana.
echo.

:: 1. Copiar icono
echo [1/3] Copiando el icono de la aplicacion...
if exist "hes_logo.ico" (
    copy /y "hes_logo.ico" "%PUBLIC%\hes_logo.ico" >nul
)

:: 2. Crear Acceso Directo de Internet
echo.
echo [2/3] Configurando Acceso Directo al Sistema...
echo.

set /p ServerIP="Ingresa la Direccion IP del SERVIDOR PRINCIPAL (ej. 192.168.1.50): "

set TargetURL=http://%ServerIP%:5173/

if exist "%PUBLIC%\hes_logo.ico" (
    set "IconStr=%PUBLIC%\hes_logo.ico"
) else (
    set "IconStr=C:\Windows\System32\shell32.dll"
)

:: Usar VBScript para encontrar el escritorio correcto (Desktop, Escritorio, OneDrive) y crear el acceso
set SCRIPT="%TEMP%\CrearAcceso.vbs"
echo Set oWS = WScript.CreateObject("WScript.Shell") > %SCRIPT%
echo sLinkFile = oWS.SpecialFolders("Desktop") ^& "\Bitacora HES.url" >> %SCRIPT%
echo Set FSO = CreateObject("Scripting.FileSystemObject") >> %SCRIPT%
echo Set oFile = FSO.CreateTextFile(sLinkFile, True) >> %SCRIPT%
echo oFile.WriteLine("[InternetShortcut]") >> %SCRIPT%
echo oFile.WriteLine("URL=%TargetURL%") >> %SCRIPT%
echo oFile.WriteLine("IconIndex=0") >> %SCRIPT%
echo oFile.WriteLine("IconFile=%IconStr%") >> %SCRIPT%
echo oFile.Close >> %SCRIPT%

cscript /nologo %SCRIPT%
del %SCRIPT%

echo.
echo ¡Acceso directo "Bitacora HES" creado en tu Escritorio!

:: 3. Instalar el Componente WebSDK (DigitalPersona Lite Client)
echo.
echo [3/3] Instalando Controlador DigitalPersona (WebSDK)...
if exist "DigitalPersona_Web_Client\x64\setup.exe" (
    echo.
    echo ==========================================================
    echo ATENCION: Se abrira el instalador de huellas DigitalPersona.
    echo.
    echo IMPORTANTE: Si al finalizar te pide REINICIAR LA PC, 
    echo puedes aceptar sin problema. LA INSTALACION YA TERMINO
    echo y el icono en el escritorio ya esta creado.
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

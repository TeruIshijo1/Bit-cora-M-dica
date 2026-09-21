@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Diagnosticar_Estacion.ps1" -IncludeServer
if errorlevel 1 echo DIAGNOSTICO NO APROBADO. Revise el mensaje anterior.
pause

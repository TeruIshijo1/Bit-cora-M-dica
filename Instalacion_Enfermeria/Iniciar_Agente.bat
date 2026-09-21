@echo off
start "HES Biometric Agent" /b powershell.exe -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "%LOCALAPPDATA%\HESBiometricAgent\start-client.ps1"

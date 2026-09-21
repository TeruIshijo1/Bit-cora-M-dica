@echo off
setlocal
pushd "%~dp0"
if /I "%APP_ENV%"=="production" (
  echo ERROR: iniciar.bat es exclusivamente para desarrollo.
  popd
  exit /b 1
)
set APP_ENV=development
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\reset_hes_development_listeners.ps1"
if errorlevel 1 (
  echo ERROR: No fue posible preparar los puertos locales de HES.
  popd
  exit /b 1
)
if not defined BIOMETRIC_ATTESTATION_SECRET (
  for /f "usebackq delims=" %%S in (`powershell.exe -NoProfile -Command "$afBytes = New-Object byte[] 32; $afGenerator = [Security.Cryptography.RandomNumberGenerator]::Create(); try { $afGenerator.GetBytes($afBytes); [Convert]::ToBase64String($afBytes) } finally { $afGenerator.Dispose(); [Array]::Clear($afBytes, 0, $afBytes.Length) }"`) do set "BIOMETRIC_ATTESTATION_SECRET=%%S"
)
if not defined BIOMETRIC_ATTESTATION_SECRET (
  echo ERROR: No fue posible preparar el secreto biometrico temporal de desarrollo.
  popd
  exit /b 1
)
echo Iniciando HES en DESARROLLO. No se ejecuta seed automaticamente.
echo Se preparo una credencial biometrica temporal solo para estos procesos.
npx concurrently -n "API,BIOMETRIA" -c "bgBlue.bold,bgMagenta.bold" "cd backend && python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload" "cd biometric-service && node server.js"
popd
endlocal

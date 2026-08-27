@echo off
REM ============================================================================
REM SCRIPT DE RESPALDO AUTOMÁTICO POSTGRESQL - HOSPITAL ESCANDÓN (HES)
REM Cumplimiento NOM-024-SSA3-2012 / NOM-004-SSA3-2012 (Custodia y Auditoría)
REM ============================================================================

setlocal enabledelayedexpansion

REM Configuración de Base de Datos (Personalizable por .env)
set DB_HOST=localhost
set DB_PORT=5432
set DB_NAME=hospital_escandon_db
set DB_USER=postgres

REM Directorio de Respaldos
set BACKUP_DIR=%~dp0..\backups
if not exist "%BACKUP_DIR%" (
    mkdir "%BACKUP_DIR%"
)

REM Formato de Fecha/Hora AAAAMMDD_HHMMSS
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set datetime=%%I
set TIMESTAMP=%datetime:~0,8%_%datetime:~8,6%
set BACKUP_FILE=%BACKUP_DIR%\hes_backup_%TIMESTAMP%.sql

echo =======================================================
echo [HES BACKUP ENGINE] Iniciando respaldo de base de datos...
echo Base de Datos: %DB_NAME%
echo Servidor:      %DB_HOST%:%DB_PORT%
echo Destino:       %BACKUP_FILE%
echo =======================================================

REM Ejecución de pg_dump
pg_dump -h %DB_HOST% -p %DB_PORT% -U %DB_USER% -d %DB_NAME% -F p -b -v -f "%BACKUP_FILE%"

if %ERRORLEVEL% EQU 0 (
    echo [EXITO] Respaldo completado exitosamente: %BACKUP_FILE%
    REM Rotación: Mantener últimos 14 respaldos
    for /f "skip=14 delims=" %%F in ('dir /b /o-d /tc "%BACKUP_DIR%\hes_backup_*.sql"') do (
        echo [ROTACION] Eliminando respaldo antiguo: %%F
        del "%BACKUP_DIR%\%%F"
    )
) else (
    echo [ERROR CRITICO] Fallo la ejecucion de pg_dump. Verifique credenciales o servicio PostgreSQL.
    exit /b 1
)

endlocal

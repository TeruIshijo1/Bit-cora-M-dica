param(
    [string]$AppOrigin = 'https://192.168.254.249:8000',
    [switch]$CheckOnly
)
$ErrorActionPreference = 'Stop'
if (![Environment]::Is64BitProcess) { throw 'Ejecute PowerShell x64. No se admite Windows de 32 bits.' }
$stationUri = [Uri]$AppOrigin
if (!$stationUri.IsAbsoluteUri -or $stationUri.Scheme -ne 'https' -or $stationUri.AbsolutePath -ne '/' -or $stationUri.Query -or $stationUri.Fragment -or $stationUri.UserInfo) { throw 'Indique el origen HTTPS exacto, sin ruta ni credenciales.' }
& (Join-Path $PSScriptRoot 'Verificar_Paquete.ps1')
$stationSdk = 'C:\Program Files\DigitalPersona\U.are.U RTE\Windows\Lib\DotNET'
$stationPrerequisites = @((Join-Path $stationSdk 'DPUruNet.dll'), (Join-Path $env:WINDIR 'System32\dpfpdd.dll'), (Join-Path $env:WINDIR 'System32\dpfj.dll'))
$stationMissing = @($stationPrerequisites | Where-Object { !(Test-Path -LiteralPath $_) })
if ($CheckOnly) {
    Write-Output ('Paquete integro. Componentes de runtime faltantes: ' + $stationMissing.Count)
    Write-Output ('Origen previsto: ' + $AppOrigin + '. No se contacto al servidor ni se modifico la estacion.')
    exit 0
}
if ($stationMissing.Count) {
    Write-Output 'Instale el runtime DigitalPersona en el asistente. Puede solicitar privilegios de administrador.'
    $stationSetup = Start-Process -FilePath (Join-Path $PSScriptRoot 'DigitalPersona_Web_Client\x64\setup.exe') -Wait -PassThru
    if ($stationSetup.ExitCode -in @(3010,1641)) { Write-Output 'Reinicie Windows y vuelva a ejecutar Instalar_Enfermeria.bat. Configuracion pendiente.'; exit 3010 }
    if ($stationSetup.ExitCode -ne 0) { throw ('Instalador DigitalPersona no completado. Codigo: ' + $stationSetup.ExitCode) }
    foreach ($stationFile in $stationPrerequisites) { if (!(Test-Path -LiteralPath $stationFile)) { throw 'Runtime incompleto. Reinicie si el fabricante lo indica y repita; no se declara instalada la estacion.' } }
}
Write-Output 'Aprovisionamiento por Sistemas: use el mismo secreto estable configurado en el servidor. No genere uno diferente para cada PC.'
& (Join-Path $PSScriptRoot 'HES-Agent\install-client.ps1') -AppOrigin $AppOrigin -SdkDirectory $stationSdk
$stationShortcut = Join-Path ([Environment]::GetFolderPath('Desktop')) 'Bitacora HES.url'
@('[InternetShortcut]', ('URL=' + $stationUri.GetLeftPart([UriPartial]::Authority) + '/login')) | Set-Content -LiteralPath $stationShortcut -Encoding ASCII
Write-Output 'Agente instalado para este usuario Windows. Verificando disponibilidad local...'
for ($stationTry=0; $stationTry -lt 10; $stationTry++) {
    try {
        $stationHealth = Invoke-RestMethod 'http://127.0.0.1:8082/health' -TimeoutSec 2
        if ($stationHealth.protocol_version -eq 2) { break }
    } catch { }
    Start-Sleep -Seconds 1
}
& (Join-Path $PSScriptRoot 'Diagnosticar_Estacion.ps1') -AppOrigin $AppOrigin
Write-Output 'Instalacion local comprobada. Falta validar HTTPS, permisos del navegador y una captura real antes de liberar este puesto.'

$ErrorActionPreference = 'Stop'
$stationRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$stationTest = [IO.Path]::GetFullPath((Join-Path $stationRoot ('scratch\station-kit-test-' + [Guid]::NewGuid().ToString('N'))))
if (!$stationTest.StartsWith(($stationRoot.TrimEnd('\') + '\scratch\'), [StringComparison]::OrdinalIgnoreCase)) { throw 'Destino TEST fuera del workspace.' }
if (Get-NetTCPConnection -State Listen -LocalPort 8082 -ErrorAction SilentlyContinue) { throw '8082 ocupado. No se interrumpe el agente existente para esta prueba.' }
$stationSupervisor = $null
function Wait-StationHealth {
    for ($stationAttempt=0; $stationAttempt -lt 25; $stationAttempt++) {
        try { if ((Invoke-RestMethod 'http://127.0.0.1:8082/health' -TimeoutSec 1).protocol_version -eq 2) { return } } catch { }
        Start-Sleep -Seconds 1
    }
    throw 'El supervisor no inicio/recupero el agente a tiempo.'
}
try {
    $stationSecret = ConvertTo-SecureString 'synthetic-offline-kit-test-secret-32-characters' -AsPlainText -Force
    & (Join-Path $stationRoot 'Instalacion_Enfermeria\HES-Agent\install-client.ps1') -AppOrigin 'https://192.168.254.249:8000' -InstallDirectory $stationTest -AttestationSecret $stationSecret -NoStartup -NoLaunch
    $stationConfig = Get-Content (Join-Path $stationTest 'client-config.json') -Raw | ConvertFrom-Json
    if ($stationConfig.secret -eq 'synthetic-offline-kit-test-secret-32-characters') { throw 'Secreto sin DPAPI.' }
    $stationDecoded = ConvertTo-SecureString $stationConfig.secret
    if ($stationDecoded.Length -ne $stationSecret.Length) { throw 'DPAPI no recuperable por el usuario.' }
    $stationDecoded.Dispose(); $stationSecret.Dispose()
    $stationArgs = '-NoProfile -ExecutionPolicy Bypass -File "' + (Join-Path $stationTest 'start-client.ps1') + '"'
    $stationSupervisor = Start-Process powershell.exe -ArgumentList $stationArgs -WindowStyle Hidden -PassThru
    Wait-StationHealth
    & (Join-Path $stationRoot 'Instalacion_Enfermeria\Diagnosticar_Estacion.ps1')
    $stationFirstPid = (Get-NetTCPConnection -State Listen -LocalPort 8082).OwningProcess | Select-Object -Unique
    $stationDuplicate = Start-Process powershell.exe -ArgumentList $stationArgs -WindowStyle Hidden -PassThru
    if (!$stationDuplicate.WaitForExit(10000) -or $stationDuplicate.ExitCode -ne 0) { throw 'El segundo supervisor no se cerro limpiamente.' }
    $stationChild = Get-CimInstance Win32_Process -Filter "ProcessId = $stationFirstPid"
    if ($stationChild.ExecutablePath -ne (Join-Path $stationTest 'runtime\node.exe')) { throw 'Listener ajeno; no se detiene.' }
    Stop-Process -Id $stationFirstPid -Force
    Wait-StationHealth
    $stationNextPid = (Get-NetTCPConnection -State Listen -LocalPort 8082).OwningProcess | Select-Object -Unique
    if ($stationNextPid -eq $stationFirstPid) { throw 'No se verifico reinicio del proceso.' }
    & (Join-Path $stationTest 'stop-client.ps1')
    if (!$stationSupervisor.WaitForExit(15000)) { throw 'El supervisor no atendio la parada.' }
    if (Get-NetTCPConnection -State Listen -LocalPort 8082 -ErrorAction SilentlyContinue) { throw 'La parada no libero 8082.' }
    Write-Output 'PASS: instalacion offline aislada, DPAPI, lector, instancia unica, recuperacion de caida y parada. Sin servidor remoto ni captura de dedo.'
} finally {
    if (Test-Path -LiteralPath $stationTest) {
        Set-Content (Join-Path $stationTest 'stop.request') 'stop'
        if ($stationSupervisor -and !$stationSupervisor.HasExited) { [void]$stationSupervisor.WaitForExit(15000) }
        if (!$stationSupervisor -or $stationSupervisor.HasExited) { Remove-Item -LiteralPath $stationTest -Recurse -Force }
    }
}

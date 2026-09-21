param([string]$AppOrigin = 'https://192.168.254.249:8000', [switch]$IncludeServer)
$ErrorActionPreference = 'Stop'
# No FMD, passwords, ticket, device identifier or medical record is printed.
$stationHealth = Invoke-RestMethod 'http://127.0.0.1:8082/health' -TimeoutSec 5
if ($stationHealth.status -ne 'alive' -or $stationHealth.protocol_version -ne 2) { throw 'El servicio local no es HES Biometric Agent V2.' }
$stationDevices = Invoke-RestMethod 'http://127.0.0.1:8082/devices' -Headers @{Origin=$AppOrigin} -TimeoutSec 15
if ($stationDevices.busy) { throw 'Lector ocupado. Cierre otras pestanas de captura y repita el diagnostico.' }
if (@($stationDevices.devices).Count -ne 1) { throw 'Debe haber exactamente un lector conectado.' }
Write-Output 'OK: agente V2, origen permitido y un lector disponible en esta PC.'
if ($IncludeServer) {
    if (([Uri]$AppOrigin).Scheme -ne 'https') { throw 'Se requiere HTTPS.' }
    # Only liveness; readiness may consult hospital integrations and is not used.
    $stationResponse = Invoke-WebRequest ($AppOrigin.TrimEnd('/') + '/health') -UseBasicParsing -TimeoutSec 10
    if (($stationResponse.Content | ConvertFrom-Json).status -ne 'alive') { throw 'El servidor no devolvio la salud esperada.' }
    Write-Output 'OK: servidor HES accesible con TLS validado por Windows.'
    if ($stationResponse.Headers.Date) {
        $stationRemoteTime = [DateTimeOffset]::Parse([string]$stationResponse.Headers.Date)
        $stationClockDelta = [Math]::Abs(([DateTimeOffset]::UtcNow - $stationRemoteTime).TotalSeconds)
        if ($stationClockDelta -gt 30) { throw 'Diferencia de reloj mayor a 30 segundos; sincronice Windows con la hora del hospital.' }
        Write-Output 'OK: diferencia de reloj menor a 30 segundos.'
    }
}
Write-Output 'El diagnostico no captura huellas ni demuestra login/firma. Complete la prueba funcional de la guia.'

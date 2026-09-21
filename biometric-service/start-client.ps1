$ErrorActionPreference = 'Stop'
$afMutex = New-Object Threading.Mutex($false, 'Local\HES.BiometricAgent.Supervisor')
$afOwns = $false
try {
    try { $afOwns = $afMutex.WaitOne(0) } catch [Threading.AbandonedMutexException] { $afOwns = $true }
    if (!$afOwns) { exit 0 }
    $afStop = Join-Path $PSScriptRoot 'stop.request'
    Remove-Item -LiteralPath $afStop -Force -ErrorAction SilentlyContinue
    $afDelay = 5
    while (!(Test-Path -LiteralPath $afStop)) {
        if (Get-NetTCPConnection -State Listen -LocalPort 8082 -ErrorAction SilentlyContinue) {
            'Puerto 8082 ocupado. No se inicia una segunda instancia.' | Set-Content (Join-Path $PSScriptRoot 'agent-status.txt')
            break
        }
        $afConfig = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'client-config.json') -Raw | ConvertFrom-Json
        $afSecret = ConvertTo-SecureString $afConfig.secret
        $afPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($afSecret)
        try {
            $env:BIOMETRIC_ATTESTATION_SECRET = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($afPointer)
            $env:BIOMETRIC_ALLOWED_ORIGINS = $afConfig.origin
            $env:BIOMETRIC_PORT = '8082'
            $afProcess = Start-Process -FilePath $afConfig.node -ArgumentList ('"' + (Join-Path $PSScriptRoot 'server.js') + '"') -WorkingDirectory $PSScriptRoot -WindowStyle Hidden -PassThru
            $afStarted = Get-Date
        } finally {
            [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($afPointer)
            Remove-Item Env:BIOMETRIC_ATTESTATION_SECRET -ErrorAction SilentlyContinue
            $afSecret.Dispose()
        }
        'Agente iniciado; use Diagnosticar_Estacion para comprobar lector y servidor.' | Set-Content (Join-Path $PSScriptRoot 'agent-status.txt')
        while (!$afProcess.WaitForExit(1000)) {
            if (Test-Path -LiteralPath $afStop) {
                # Only children of this supervisor are stopped, never unknown listeners.
                Get-CimInstance Win32_Process -Filter "ParentProcessId = $($afProcess.Id)" | Where-Object Name -eq 'CaptureBridge.exe' | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
                Stop-Process -Id $afProcess.Id -Force -ErrorAction SilentlyContinue
                break
            }
        }
        if (Test-Path -LiteralPath $afStop) { break }
        if (((Get-Date) - $afStarted).TotalSeconds -gt 120) { $afDelay = 5 }
        'Agente interrumpido; reinicio automático pendiente.' | Set-Content (Join-Path $PSScriptRoot 'agent-status.txt')
        for ($afSecond = 0; $afSecond -lt $afDelay -and !(Test-Path -LiteralPath $afStop); $afSecond++) { Start-Sleep -Seconds 1 }
        $afDelay = [Math]::Min(60, $afDelay * 2)
    }
} catch {
    'No se pudo iniciar el agente. Reaprovisione con el usuario Windows que lo utiliza; consulte a Sistemas.' | Set-Content (Join-Path $PSScriptRoot 'agent-status.txt')
    exit 1
} finally {
    if ($afOwns) { $afMutex.ReleaseMutex() }
    $afMutex.Dispose()
}

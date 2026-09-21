[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$ports = @(8000, 8082)

function Get-ProcessTreePostOrder {
    param([int]$ParentId)
    $children = @(Get-CimInstance Win32_Process -Filter "ParentProcessId=$ParentId")
    foreach ($child in $children) {
        Get-ProcessTreePostOrder -ParentId $child.ProcessId
    }
    $ParentId
}

function Test-HesListener {
    param(
        [int]$Port,
        [object]$Process
    )

    try {
        $health = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/health" -TimeoutSec 2
    }
    catch {
        return $false
    }

    if ($Port -eq 8000) {
        return $health.status -eq 'alive' -and
            $Process.Name -match '^python(.exe)?$' -and
            $Process.CommandLine -match 'uvicorn\s+main:app' -and
            $Process.CommandLine -match '--port\s+8000'
    }

    return $health.status -eq 'alive' -and
        $health.protocol_version -eq 2 -and
        $Process.Name -match '^node(.exe)?$' -and
        $Process.CommandLine -match 'server\.js'
}

$stopped = @()
foreach ($port in $ports) {
    $listeners = @(
        Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue |
            Select-Object -ExpandProperty OwningProcess -Unique
    )
    foreach ($processId in $listeners) {
        $process = Get-CimInstance Win32_Process -Filter "ProcessId=$processId"
        if (-not $process -or -not (Test-HesListener -Port $port -Process $process)) {
            throw "El puerto $port esta ocupado por un proceso que no se pudo identificar como HES. No se cerro ningun proceso ajeno."
        }
        foreach ($treeProcessId in @(Get-ProcessTreePostOrder -ParentId $processId)) {
            Stop-Process -Id $treeProcessId -Force -ErrorAction SilentlyContinue
        }
        $stopped += $port
    }
}

$deadline = (Get-Date).AddSeconds(8)
do {
    $occupied = @(
        Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue |
            Where-Object LocalPort -in $ports
    )
    if (-not $occupied) { break }
    Start-Sleep -Milliseconds 200
} while ((Get-Date) -lt $deadline)

if ($occupied) {
    throw "No fue posible liberar los puertos HES 8000/8082."
}
if ($stopped.Count) {
    Write-Host "Se cerro la instancia HES de desarrollo anterior para iniciar una nueva."
}

$ErrorActionPreference = 'Stop'
$stationRoot = [IO.Path]::GetFullPath($PSScriptRoot).TrimEnd('\') + '\'
$stationManifest = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'MANIFEST.sha256.json') -Raw | ConvertFrom-Json
if (!$stationManifest.files -or $stationManifest.files.Count -lt 10) { throw 'Manifiesto incompleto. Solicite nuevamente el paquete a Sistemas.' }
foreach ($stationEntry in $stationManifest.files) {
    $stationPath = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot $stationEntry.path))
    if (!$stationPath.StartsWith($stationRoot, [StringComparison]::OrdinalIgnoreCase)) { throw 'Ruta fuera del paquete.' }
    if (!(Test-Path -LiteralPath $stationPath -PathType Leaf)) { throw ('Falta archivo del paquete: ' + $stationEntry.path) }
    if ((Get-FileHash -LiteralPath $stationPath -Algorithm SHA256).Hash -ne $stationEntry.sha256) { throw ('Archivo alterado/incompleto: ' + $stationEntry.path) }
}
Write-Output 'Integridad SHA-256 del paquete verificada.'

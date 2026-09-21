param([switch]$Apply)
$ErrorActionPreference = 'Stop'
$cleanupRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..')).TrimEnd('\')
$cleanupCandidates = @(Get-ChildItem -LiteralPath $cleanupRoot -File | Where-Object {
    $_.Name -match '^(test_.*\.(pdf|png)|dummy_.*\.pdf)$'
} | Select-Object -ExpandProperty FullName)
# Only the reproducible old release, identified by its build manifest.
$cleanupRelease = Join-Path $cleanupRoot 'pase_a_produccion'
if (Test-Path -LiteralPath (Join-Path $cleanupRelease 'MANIFEST.sha256.json')) {
    $cleanupPrivate = @(Get-ChildItem -LiteralPath $cleanupRelease -Recurse -File -Force | Where-Object {
        ($_.Name -like '.env*' -and $_.Name -ne '.env.example') -or $_.Name -eq 'client-config.json' -or $_.Extension -in @('.db','.sqlite','.backup','.dump')
    })
    if (!$cleanupPrivate.Count) { $cleanupCandidates += $cleanupRelease }
}
$cleanupRows = @()
foreach ($cleanupCandidate in $cleanupCandidates) {
    $cleanupPath = [IO.Path]::GetFullPath($cleanupCandidate)
    if (!$cleanupPath.StartsWith(($cleanupRoot + '\'), [StringComparison]::OrdinalIgnoreCase)) { throw 'Destino fuera del workspace.' }
    $cleanupItem = Get-Item -LiteralPath $cleanupPath -Force
    if ($cleanupItem.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'No se limpia una ruta enlazada.' }
    if ($cleanupItem.PSIsContainer) {
        $cleanupChildren = @(Get-ChildItem -LiteralPath $cleanupPath -Recurse -Force)
        if (@($cleanupChildren | Where-Object { $_.Attributes -band [IO.FileAttributes]::ReparsePoint }).Count) { throw 'El directorio contiene enlaces; se conserva.' }
        $cleanupFiles = @($cleanupChildren | Where-Object { !$_.PSIsContainer })
    } else { $cleanupFiles = @($cleanupItem) }
    $cleanupRows += [pscustomobject]@{ path=$cleanupPath.Substring($cleanupRoot.Length+1); files=$cleanupFiles.Count; bytes=($cleanupFiles | Measure-Object -Property Length -Sum).Sum; reason='Salida de prueba o paquete regenerable obsoleto' }
}
if ($Apply) {
    # Persist the exact inventory before deleting; never touch .env, clinical data,
    # source, templates, audit evidence, installed dependencies or personal notes.
    $cleanupRows | ConvertTo-Json -Depth 3 | Set-Content -LiteralPath (Join-Path $cleanupRoot 'docs\LIMPIEZA_GENERADOS_2026-09-18.json') -Encoding UTF8
    foreach ($cleanupCandidate in $cleanupCandidates) { Remove-Item -LiteralPath $cleanupCandidate -Recurse -Force }
}
$cleanupRows | Format-Table -AutoSize
Write-Output ('Apply=' + $Apply + '; archivos=' + (($cleanupRows | Measure-Object -Property files -Sum).Sum) + '; bytes=' + (($cleanupRows | Measure-Object -Property bytes -Sum).Sum))

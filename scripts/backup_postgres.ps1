param(
    [Parameter(Mandatory=$true)][string]$BackupDirectory,
    [Parameter(Mandatory=$true)][string]$OffsiteDirectory,
    [string]$AgeRecipient = $env:BACKUP_AGE_RECIPIENT,
    [int]$RetentionDays = 14
)

$ErrorActionPreference = 'Stop'
if ($env:APP_ENV -notin @('production', 'test')) { throw 'APP_ENV debe ser production o test.' }
if (-not $env:PGDATABASE) { throw 'PGDATABASE es obligatorio.' }
if ($env:APP_ENV -eq 'production' -and -not $AgeRecipient) { throw 'BACKUP_AGE_RECIPIENT es obligatorio en production.' }

$pgRoot = if ($env:POSTGRES_BIN) { $env:POSTGRES_BIN } else { 'C:\Program Files\PostgreSQL\17\bin' }
$pgDump = Join-Path $pgRoot 'pg_dump.exe'
$pgRestore = Join-Path $pgRoot 'pg_restore.exe'
if (-not (Test-Path -LiteralPath $pgDump) -or -not (Test-Path -LiteralPath $pgRestore)) { throw 'No se localizaron pg_dump/pg_restore.' }

$backupRoot = [IO.Path]::GetFullPath($BackupDirectory)
$offsiteRoot = [IO.Path]::GetFullPath($OffsiteDirectory)
New-Item -ItemType Directory -Force -Path $backupRoot, $offsiteRoot | Out-Null
$timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$plain = Join-Path $backupRoot "hes_$($env:PGDATABASE)_$timestamp.dump"

$started = Get-Date
& $pgDump --format=custom --compress=9 --no-owner --no-acl --file=$plain
if ($LASTEXITCODE -ne 0) { throw 'pg_dump falló.' }
& $pgRestore --list $plain | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'pg_restore --list rechazó el archivo.' }
$hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $plain).Hash

if ($AgeRecipient) {
    $age = Get-Command age -ErrorAction Stop
    $encrypted = "$plain.age"
    & $age.Source -r $AgeRecipient -o $encrypted $plain
    if ($LASTEXITCODE -ne 0) { throw 'El cifrado age falló.' }
    Remove-Item -LiteralPath $plain -Force
    $artifact = $encrypted
} else {
    $artifact = $plain
}

$offsiteArtifact = Join-Path $offsiteRoot ([IO.Path]::GetFileName($artifact))
Copy-Item -LiteralPath $artifact -Destination $offsiteArtifact -Force
if ((Get-FileHash -Algorithm SHA256 -LiteralPath $artifact).Hash -ne (Get-FileHash -Algorithm SHA256 -LiteralPath $offsiteArtifact).Hash) {
    throw 'La copia externa no coincide con el origen.'
}

$cutoff = (Get-Date).AddDays(-$RetentionDays)
Get-ChildItem -LiteralPath $backupRoot -File | Where-Object LastWriteTime -lt $cutoff | Remove-Item -Force
$elapsed = [math]::Round(((Get-Date) - $started).TotalSeconds, 3)
[pscustomobject]@{ artifact=$artifact; offsite=$offsiteArtifact; source_sha256=$hash; duration_seconds=$elapsed; verified=$true } | ConvertTo-Json -Compress

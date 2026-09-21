param([string]$NodePath = (Get-Command node.exe -ErrorAction Stop).Source)
$ErrorActionPreference = 'Stop'
$kitRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$kitSource = Join-Path $kitRoot 'biometric-service'
$kitTarget = Join-Path $kitRoot 'Instalacion_Enfermeria\HES-Agent'
if ((Get-AuthenticodeSignature -LiteralPath $NodePath).Status -ne 'Valid') { throw 'El ejecutable Node debe tener firma Authenticode valida.' }
& (Join-Path $kitSource 'native\build.ps1')
New-Item -ItemType Directory -Path $kitTarget,(Join-Path $kitTarget 'native\bin'),(Join-Path $kitTarget 'runtime') -Force | Out-Null
foreach ($kitFile in @('server.js','native-device.js','capture-protocol.js','package.json','package-lock.json','install-client.ps1','start-client.ps1','stop-client.ps1','README.md')) {
    Copy-Item -LiteralPath (Join-Path $kitSource $kitFile) -Destination $kitTarget -Force
}
Copy-Item -LiteralPath (Join-Path $kitSource 'native\bin\CaptureBridge.exe') -Destination (Join-Path $kitTarget 'native\bin') -Force
Copy-Item -LiteralPath $NodePath -Destination (Join-Path $kitTarget 'runtime\node.exe') -Force
$kitNodeVersion = & $NodePath --version
if ($LASTEXITCODE -ne 0 -or $kitNodeVersion -notmatch '^v\d+\.\d+\.\d+$') { throw 'Version Node no valida.' }
Invoke-WebRequest -Uri ('https://raw.githubusercontent.com/nodejs/node/' + $kitNodeVersion + '/LICENSE') -UseBasicParsing -OutFile (Join-Path $kitTarget 'runtime\LICENSE-Node.txt')
if ((Get-Item (Join-Path $kitTarget 'runtime\LICENSE-Node.txt')).Length -lt 100) { throw 'Licencia Node incompleta.' }
Push-Location $kitTarget
try { & npm.cmd ci --omit=dev --ignore-scripts --no-audit; if ($LASTEXITCODE -ne 0) { throw 'No se pudieron empaquetar dependencias.' } } finally { Pop-Location }
$kitPackage = Join-Path $kitRoot 'Instalacion_Enfermeria'
$kitFiles = @(Get-ChildItem -LiteralPath $kitPackage -Recurse -File | Where-Object { $_.Name -notin @('MANIFEST.sha256.json','CONTROL_50_ESTACIONES.csv') } | ForEach-Object {
    if ($_.Name -eq 'client-config.json' -or $_.Name -like '.env*') { throw 'Se detecto configuracion privada en el paquete.' }
    @{ path=$_.FullName.Substring($kitPackage.Length+1).Replace('\','/'); sha256=(Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash }
})
@{ generated_at=[DateTime]::UtcNow.ToString('o'); origin='https://192.168.254.249:8000'; node=(& $NodePath --version); files=$kitFiles } | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $kitPackage 'MANIFEST.sha256.json') -Encoding UTF8
Write-Output ('Paquete offline generado: ' + $kitFiles.Count + ' archivos. No contiene secretos del servidor.')

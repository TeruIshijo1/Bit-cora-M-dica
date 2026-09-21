param(
    [Parameter(Mandatory=$true)][string]$AppOrigin,
    [string]$InstallDirectory = (Join-Path $env:LOCALAPPDATA 'HESBiometricAgent'),
    [string]$SdkDirectory = 'C:\Program Files\DigitalPersona\U.are.U RTE\Windows\Lib\DotNET',
    [Security.SecureString]$AttestationSecret,
    [switch]$NoStartup,
    [switch]$NoLaunch
)
$ErrorActionPreference = 'Stop'
$afOrigin = [Uri]$AppOrigin
if (!$afOrigin.IsAbsoluteUri -or $afOrigin.AbsolutePath -ne '/' -or $afOrigin.Query -or $afOrigin.Fragment -or $afOrigin.UserInfo -or ($afOrigin.Scheme -ne 'https' -and !($afOrigin.Scheme -eq 'http' -and $afOrigin.IsLoopback))) {
    throw 'AppOrigin debe ser el origen HTTPS exacto del hospital; HTTP sólo se permite para desarrollo localhost.'
}
if (![Environment]::Is64BitOperatingSystem -or ![Environment]::Is64BitProcess) { throw 'Use Windows x64 y PowerShell de 64 bits.' }
$afBundled = Test-Path -LiteralPath (Join-Path $PSScriptRoot 'runtime\node.exe')
if (!$afBundled) {
    $afNode = (Get-Command node.exe -ErrorAction Stop).Source
    $afNpm = (Get-Command npm.cmd -ErrorAction Stop).Source
    & (Join-Path $PSScriptRoot 'native\build.ps1') -SdkDirectory $SdkDirectory
}
foreach ($afPrerequisite in @((Join-Path $SdkDirectory 'DPUruNet.dll'), (Join-Path $env:WINDIR 'System32\dpfpdd.dll'), (Join-Path $env:WINDIR 'System32\dpfj.dll'))) {
    if (!(Test-Path -LiteralPath $afPrerequisite)) { throw 'Falta el runtime U.are.U x64. Ejecute primero el instalador DigitalPersona incluido.' }
}
$afDestination = [IO.Path]::GetFullPath($InstallDirectory)
if ($afDestination.TrimEnd('\') -eq $PSScriptRoot.TrimEnd('\')) { throw 'Use un destino de instalación distinto del código fuente.' }
if (Get-NetTCPConnection -State Listen -LocalPort 8082 -ErrorAction SilentlyContinue) { throw 'El puerto 8082 está en uso. Cierre las capturas y detenga el agente con Detener_Agente.bat antes de instalar/actualizar.' }
if (!$AttestationSecret) { $AttestationSecret = Read-Host 'Secreto BIOMETRIC_ATTESTATION_SECRET del servidor (entrada oculta)' -AsSecureString }
if ($AttestationSecret.Length -lt 32) { throw 'El secreto requiere al menos 32 caracteres.' }
New-Item -ItemType Directory -Path $afDestination -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $afDestination 'native\bin') -Force | Out-Null
foreach ($afFile in @('server.js','capture-protocol.js','native-device.js','package.json','package-lock.json','start-client.ps1','stop-client.ps1')) {
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot $afFile) -Destination $afDestination -Force
}
foreach ($afFile in @('CaptureBridge.exe')) {
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot ('native\bin\' + $afFile)) -Destination (Join-Path $afDestination 'native\bin') -Force
}
Copy-Item -LiteralPath (Join-Path $SdkDirectory 'DPUruNet.dll') -Destination (Join-Path $afDestination 'native\bin') -Force
if ($afBundled) {
    foreach ($afFolder in @('runtime','node_modules')) { Copy-Item -LiteralPath (Join-Path $PSScriptRoot $afFolder) -Destination $afDestination -Recurse -Force }
    $afNode = Join-Path $afDestination 'runtime\node.exe'
} else {
    Push-Location $afDestination
    try { & $afNpm ci --omit=dev --ignore-scripts; if ($LASTEXITCODE -ne 0) { throw 'Falló npm ci.' } } finally { Pop-Location }
}
# DPAPI CurrentUser: no plaintext credential on disk or command line.
$afConfiguration = @{ origin=$afOrigin.GetLeftPart([UriPartial]::Authority); node=$afNode; secret=($AttestationSecret | ConvertFrom-SecureString) }
$afConfigPath = Join-Path $afDestination 'client-config.json'
$afConfiguration | ConvertTo-Json | Set-Content -LiteralPath $afConfigPath -Encoding UTF8
$afAcl = New-Object Security.AccessControl.FileSecurity
$afAcl.SetAccessRuleProtection($true,$false)
$afIdentity = [Security.Principal.WindowsIdentity]::GetCurrent().Name
$afAcl.AddAccessRule((New-Object Security.AccessControl.FileSystemAccessRule($afIdentity,'FullControl','Allow')))
$afAcl.AddAccessRule((New-Object Security.AccessControl.FileSystemAccessRule('SYSTEM','FullControl','Allow')))
Set-Acl -LiteralPath $afConfigPath -AclObject $afAcl
if (!$NoStartup) {
    $afPowerShell = Join-Path $env:WINDIR 'System32\WindowsPowerShell\v1.0\powershell.exe'
    $afLauncher = Join-Path $afDestination 'start-client.ps1'
    $afRun = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run'
    New-Item -Path $afRun -Force | Out-Null
    Set-ItemProperty -LiteralPath $afRun -Name 'HES Biometric Agent' -Value ('"' + $afPowerShell + '" -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "' + $afLauncher + '"')
}
Write-Output ('Agente instalado para este usuario en ' + $afDestination + '. Ejecute start-client.ps1 o vuelva a iniciar sesión. Escucha exclusivamente 127.0.0.1:8082.')
if (!$NoLaunch) {
    Start-Process -FilePath (Join-Path $env:WINDIR 'System32\WindowsPowerShell\v1.0\powershell.exe') -ArgumentList ('-NoProfile -ExecutionPolicy Bypass -File "' + (Join-Path $afDestination 'start-client.ps1') + '"') -WindowStyle Hidden
}

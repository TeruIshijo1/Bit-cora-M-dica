param([string]$SdkDirectory = 'C:\Program Files\DigitalPersona\U.are.U RTE\Windows\Lib\DotNET')
$ErrorActionPreference = 'Stop'
$afAssembly = Join-Path $SdkDirectory 'DPUruNet.dll'
$afCompiler = Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319\csc.exe'
if (!(Test-Path -LiteralPath $afAssembly)) { throw 'DPUruNet.dll no está instalado en el directorio indicado.' }
if (!(Test-Path -LiteralPath $afCompiler)) { throw 'Falta el compilador de .NET Framework 4.x.' }
$afOutput = Join-Path $PSScriptRoot 'bin'
New-Item -ItemType Directory -Path $afOutput -Force | Out-Null
& $afCompiler /nologo /target:exe /platform:x64 /optimize+ "/reference:$afAssembly" /reference:System.Web.Extensions.dll "/out:$afOutput\CaptureBridge.exe" "$PSScriptRoot\CaptureBridge.cs"
if ($LASTEXITCODE -ne 0) { throw 'Falló la compilación del adaptador DigitalPersona.' }
Copy-Item -LiteralPath $afAssembly -Destination $afOutput -Force
Write-Output 'CaptureBridge compilado; runtime nativo requerido en Windows System32.'

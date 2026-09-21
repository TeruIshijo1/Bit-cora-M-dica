$ErrorActionPreference = 'Stop'
Set-Content -LiteralPath (Join-Path $PSScriptRoot 'stop.request') -Value 'stop'
Write-Output 'Parada solicitada al agente de este usuario. Espere a que 8082 quede libre antes de actualizar.'

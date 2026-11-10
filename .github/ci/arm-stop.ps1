# On an ARM PC the bootstrap must stop in the first minute with one plain sentence, before any download.
$ErrorActionPreference = 'Continue'
$env:Path = 'C:\Windows\system32;C:\Windows;C:\Windows\System32\Wbem;C:\Windows\System32\WindowsPowerShell\v1.0'
$out = (& powershell -NoProfile -ExecutionPolicy Bypass -File "$env:GITHUB_WORKSPACE\bootstrap.ps1" 2>&1 | Out-String)
$code = $LASTEXITCODE
Write-Host $out
Write-Host "bootstrap exit $code; PROCESSOR_ARCHITECTURE $env:PROCESSOR_ARCHITECTURE"
if ($code -eq 1 -and $out -match 'ARM chip' -and -not (Test-Path "$env:GITHUB_WORKSPACE\runtime\bin\uv.exe")) { Write-Host 'OK: the plain ARM stop, nothing downloaded'; exit 0 }
Write-Host 'expected the plain ARM stop with nothing downloaded'; exit 1

# Windows PowerShell 5.1, PATH scrubbed down to Windows itself: every setup step through avs.cmd, then the checkup.
$ErrorActionPreference = 'Continue'
$env:Path = 'C:\Windows\system32;C:\Windows;C:\Windows\System32\Wbem;C:\Windows\System32\WindowsPowerShell\v1.0'
$A = Join-Path $env:RUNNER_TEMP 'Jane Doe\AVS'
& powershell -NoProfile -ExecutionPolicy Bypass -File "$A\bootstrap.ps1"
if ($LASTEXITCODE -ne 0) { exit 1 }
& "$A\avs.cmd" install --all --accent '#2E7D5B' --sans inter --serif fraunces --name 'Test Practice' --handle '@avs_test'
$installed = $LASTEXITCODE
& "$A\avs.cmd" doctor | Tee-Object -FilePath (Join-Path $env:RUNNER_TEMP 'doctor.txt')
$doc = $LASTEXITCODE
& "$A\avs.cmd" report
Get-ChildItem -LiteralPath ([Environment]::GetFolderPath('Desktop')) -Filter 'AVS-report-*.txt' | Copy-Item -Destination "$A\runtime\logs\" -ErrorAction SilentlyContinue
Write-Host "install exit $installed, doctor exit $doc"
if ($installed -ne 0 -or $doc -ne 0) { exit 1 }

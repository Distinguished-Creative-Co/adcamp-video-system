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
$smoke = 0
if ($installed -eq 0 -and $doc -eq 0) {
  & "$A\avs.cmd" smoke 2>&1 | Tee-Object -FilePath (Join-Path $env:RUNNER_TEMP 'smoke.txt')
  $smoke = $LASTEXITCODE
  $o = "$A\engine\out"
  if (Test-Path -LiteralPath "$o\sample.mp4") { & "$A\runtime\bin\ffmpeg.exe" -v error -y -i "$o\sample.mp4" -vf scale=720:1280 -c:v libx264 -crf 24 -c:a aac -b:a 128k -movflags +faststart "$o\sample-phone.mp4" }
}
& "$A\avs.cmd" report
Get-ChildItem -LiteralPath ([Environment]::GetFolderPath('Desktop')) -Filter 'AVS-report-*.txt' | Copy-Item -Destination "$A\runtime\logs\" -ErrorAction SilentlyContinue
Write-Host "install exit $installed, doctor exit $doc, smoke exit $smoke"
if ($installed -ne 0 -or $doc -ne 0 -or $smoke -ne 0) { exit 1 }

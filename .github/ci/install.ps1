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
# the update check reads the live windows-preview line, never main: a fresh install of this version hears there is nothing newer
$uc = (& "$A\avs.cmd" update --check 2>&1 | Out-String).Trim()
Write-Host "update check: $uc"
$upd = 1
if ($uc -match '^UPDATE NONE') { $upd = 0 }
$smoke = 0
if ($installed -eq 0 -and $doc -eq 0) {
  & "$A\avs.cmd" smoke 2>&1 | Tee-Object -FilePath (Join-Path $env:RUNNER_TEMP 'smoke.txt')
  $smoke = $LASTEXITCODE
  # the result is kept: after a pass the checkup says so (a failed test video can never read All set)
  $after = (& "$A\avs.cmd" doctor 2>&1 | Out-String)
  if ($smoke -eq 0 -and ($after -notmatch 'OK\s+test video\s+passed' -or $after -notmatch 'All set')) { Write-Host $after; Write-Host 'the passed test video is not on the checkup'; $smoke = 1 }
  $o = "$A\engine\out"
  if (Test-Path -LiteralPath "$o\sample.mp4") { & "$A\runtime\bin\ffmpeg.exe" -v error -y -i "$o\sample.mp4" -vf scale=720:1280 -c:v libx264 -crf 24 -c:a aac -b:a 128k -movflags +faststart "$o\sample-phone.mp4" }
}
$sz = (Get-ChildItem -LiteralPath $A -Recurse -Force -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
"AVS folder after setup and the test video: {0:N1} GB" -f ($sz / 1GB) | Tee-Object -FilePath (Join-Path $env:RUNNER_TEMP 'size.txt')
& "$A\avs.cmd" report
Get-ChildItem -LiteralPath ([Environment]::GetFolderPath('Desktop')) -Filter 'AVS-report-*.txt' | Copy-Item -Destination "$A\runtime\logs\" -ErrorAction SilentlyContinue
$lint = 1
if ($installed -eq 0 -and $doc -eq 0) { & powershell -NoProfile -ExecutionPolicy Bypass -File "$env:GITHUB_WORKSPACE\.github\ci\skill-lint.ps1"; $lint = $LASTEXITCODE }
Write-Host "install exit $installed, doctor exit $doc, update check $upd, smoke exit $smoke, skill lint exit $lint"
if ($installed -ne 0 -or $doc -ne 0 -or $upd -ne 0 -or $smoke -ne 0 -or $lint -ne 0) { exit 1 }

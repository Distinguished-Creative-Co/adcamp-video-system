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
  # running it again after a run that stopped in step 4: plant what that run leaves behind (the sample's three covers
  # with C picked, cleared only at the end of step 4), then the test must pass again and keep the first run's log
  if ($smoke -eq 0) {
    & "$A\avs.cmd" run cover_options.py sample --options qa/sample/covers-given.json | Out-Null
    & "$A\avs.cmd" run cover_options.py sample --pick c | Out-Null
    if (-not (Test-Path -LiteralPath "$A\engine\qa\sample\covers.json")) { Write-Host 'the planted cover pick is missing'; $smoke = 1 }
    else {
      & "$A\avs.cmd" smoke 2>&1 | Tee-Object -FilePath (Join-Path $env:RUNNER_TEMP 'smoke-again.txt')
      if ($LASTEXITCODE -ne 0) { Write-Host 'the test failed when run again after a stopped run'; $smoke = 1 }
      elseif (-not (Test-Path -LiteralPath "$A\runtime\logs\test-video-previous.log")) { Write-Host 'the first run log was not kept'; $smoke = 1 }
      else { Write-Host 'run again after a stopped run: passed, first run log kept' }
    }
  }
  # a home folder with a dot in its name (C:\Users\first.last): the renderer reads everything after the last dot in a
  # path as a file extension, and once refused the carousel's slides folder there. The same AVS, reached through a
  # junction named first.last: the control proves the renderer sees a dot in that path, then a carousel must render.
  if ($smoke -eq 0) {
    $J = Join-Path $env:RUNNER_TEMP 'first.last'
    & cmd /c mklink /J "$J" "$A" | Out-Null
    Push-Location "$J\engine"
    $ext = (& "$A\runtime\node\node.exe" -e "const {RenderInternals}=require('@remotion/renderer');console.log(RenderInternals.getExtensionOfFilename(process.argv[1])||'')" "$J\engine\carousels\dotcheck\slides" 2>&1 | Out-String).Trim()
    Pop-Location
    if ($ext -eq '') { Write-Host 'control failed: the renderer saw no dot in the first.last path'; $smoke = 1 }
    else {
      & "$J\avs.cmd" run carousel.py new dotcheck | Out-Null
      $fill = Join-Path $env:RUNNER_TEMP 'dotcheck-fill.py'
      Set-Content -LiteralPath $fill -Encoding ASCII -Value @'
import json, sys
p = sys.argv[1]
d = json.load(open(p))
d['slides'] = [{'layout': 'hook', 'headline': 'A dotted ==folder=='}, {'layout': 'statement', 'headline': 'Still ==renders=='},
               {'layout': 'cta', 'headline': 'All ==set==', 'keyword': 'OK'}]
d['approved'] = True
json.dump(d, open(p, 'w'), indent=1)
'@
      & "$A\runtime\base\Scripts\python.exe" $fill "$J\engine\carousels\dotcheck\carousel.json"
      & "$J\avs.cmd" run carousel.py render dotcheck --no-open 2>&1 | Tee-Object -FilePath (Join-Path $env:RUNNER_TEMP 'dotcheck.txt')
      $rc = $LASTEXITCODE
      $n = @(Get-ChildItem -LiteralPath "$J\engine\carousels\dotcheck\slides" -Filter '*.png' -ErrorAction SilentlyContinue).Count
      if ($rc -ne 0 -or $n -ne 3) { Write-Host "carousel under a first.last folder: FAILED (exit $rc, $n slides; the renderer read '$ext' as an extension)"; $smoke = 1 }
      else { Write-Host "carousel under a first.last folder: passed, 3 slides (control: the renderer reads '$ext' as an extension)" }
    }
    Remove-Item -LiteralPath "$A\engine\carousels\dotcheck" -Recurse -Force -ErrorAction SilentlyContinue
    & cmd /c rmdir "$J"   # rmdir without /s removes the junction itself, never the AVS folder it points at
  }
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

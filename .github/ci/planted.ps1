# A failing step must fail the run: exit codes from avs.cmd reach Windows PowerShell 5.1 (the shell Claude uses).
# PowerShell names ignore case: $A (the folder) and the results must never share a letter-for-letter name.
$ErrorActionPreference = 'Continue'
$env:Path = 'C:\Windows\system32;C:\Windows;C:\Windows\System32\Wbem;C:\Windows\System32\WindowsPowerShell\v1.0'
$A = Join-Path $env:RUNNER_TEMP 'Plant\AVS'
& powershell -NoProfile -ExecutionPolicy Bypass -File "$A\bootstrap.ps1"
if ($LASTEXITCODE -ne 0) { Write-Host 'bootstrap failed'; exit 1 }
& "$A\avs.cmd" install --step nope; $r1 = $LASTEXITCODE
& "$A\avs.cmd" doctor; $r2 = $LASTEXITCODE
& "$A\avs.cmd" reel "$A\engine\samples\no-such.mp4" x; $r3 = $LASTEXITCODE
& "$A\avs.cmd" run no_such_script.py; $r4 = $LASTEXITCODE
Write-Host "bad step $r1 (want 2), doctor before install $r2 (want 1), missing video $r3 (want 1), missing script $r4 (want 2)"
if ($r1 -eq 2 -and $r2 -eq 1 -and $r3 -eq 1 -and $r4 -eq 2) { Write-Host 'OK: every planted failure came back as a failure'; exit 0 }
exit 1

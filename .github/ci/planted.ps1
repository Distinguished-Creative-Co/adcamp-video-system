# A failing step must fail the run: exit codes from avs.cmd reach Windows PowerShell 5.1 (the shell Claude uses).
$ErrorActionPreference = 'Continue'
$env:Path = 'C:\Windows\system32;C:\Windows;C:\Windows\System32\Wbem;C:\Windows\System32\WindowsPowerShell\v1.0'
$A = Join-Path $env:RUNNER_TEMP 'Plant\AVS'
& powershell -NoProfile -ExecutionPolicy Bypass -File "$A\bootstrap.ps1"
if ($LASTEXITCODE -ne 0) { Write-Host 'bootstrap failed'; exit 1 }
& "$A\avs.cmd" install --step nope; $a = $LASTEXITCODE
& "$A\avs.cmd" doctor; $b = $LASTEXITCODE
& "$A\avs.cmd" reel "$A\engine\samples\no-such.mp4" x; $c = $LASTEXITCODE
& "$A\avs.cmd" run no_such_script.py; $d = $LASTEXITCODE
Write-Host "bad step $a (want 2), doctor before install $b (want 1), missing video $c (want 1), missing script $d (want 2)"
if ($a -eq 2 -and $b -eq 1 -and $c -eq 1 -and $d -eq 2) { Write-Host 'OK: every planted failure came back as a failure'; exit 0 }
exit 1

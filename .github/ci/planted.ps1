# A failing step must fail the run: exit codes from avs.cmd reach Windows PowerShell 5.1 (the shell Claude uses).
# PowerShell names ignore case: $A (the folder) and the results must never share a letter-for-letter name.
$ErrorActionPreference = 'Continue'
$env:Path = 'C:\Windows\system32;C:\Windows;C:\Windows\System32\Wbem;C:\Windows\System32\WindowsPowerShell\v1.0'
$A = Join-Path $env:RUNNER_TEMP 'Plant\AVS'
# a PC with 4 GB of memory: the bootstrap stops in the first minute with one plain line, before any download
$env:AVS_TEST_RAM_GB = '4'
$lowOut = (& powershell -NoProfile -ExecutionPolicy Bypass -File "$A\bootstrap.ps1" 2>&1 | Out-String); $r5 = $LASTEXITCODE
Remove-Item Env:AVS_TEST_RAM_GB
Write-Host $lowOut
$lowBoot = ($r5 -eq 1 -and $lowOut -match '4 GB of memory' -and $lowOut -match 'at least 8 GB' -and -not (Test-Path -LiteralPath "$A\runtime\bin\uv.exe"))
& powershell -NoProfile -ExecutionPolicy Bypass -File "$A\bootstrap.ps1"
if ($LASTEXITCODE -ne 0) { Write-Host 'bootstrap failed'; exit 1 }
# the same PC at the PC check, which runs again when setup resumes
$env:AVS_TEST_RAM_GB = '4'
$chkOut = (& "$A\avs.cmd" install --step check 2>&1 | Out-String); $r6 = $LASTEXITCODE
Remove-Item Env:AVS_TEST_RAM_GB
Write-Host $chkOut
$lowCheck = ($r6 -eq 1 -and $chkOut -match 'at least 8 GB')
& "$A\avs.cmd" install --step nope; $r1 = $LASTEXITCODE
& "$A\avs.cmd" doctor; $r2 = $LASTEXITCODE
# a test video that fails keeps its result and output: the checkup says so and the report carries the log
& "$A\avs.cmd" smoke; $r7 = $LASTEXITCODE
$doc2 = (& "$A\avs.cmd" doctor 2>&1 | Out-String)
Write-Host $doc2
& "$A\avs.cmd" report | Out-Null
$rep = Get-ChildItem -LiteralPath ([Environment]::GetFolderPath('Desktop')) -Filter 'AVS-report-*.txt' | Sort-Object LastWriteTime | Select-Object -Last 1
$repText = ''
if ($rep) { $repText = Get-Content -Raw -LiteralPath $rep.FullName }
$kept = ($r7 -eq 1 -and $doc2 -match 'FAILED\s+test video' -and $doc2 -match 'AVS is not installed' -and $doc2 -notmatch 'All set' -and
         $repText -match 'runtime/logs/test-video.log' -and $repText -match 'AVS is not installed')
& "$A\avs.cmd" reel "$A\engine\samples\no-such.mp4" x; $r3 = $LASTEXITCODE
& "$A\avs.cmd" run no_such_script.py; $r4 = $LASTEXITCODE
Write-Host "bad step $r1 (want 2), doctor before install $r2 (want 1), missing video $r3 (want 1), missing script $r4 (want 2)"
Write-Host "4 GB stops the bootstrap with nothing downloaded: $lowBoot. 4 GB stops the PC check: $lowCheck. A failed test video is kept for the checkup and the report: $kept"
if ($r1 -eq 2 -and $r2 -eq 1 -and $r3 -eq 1 -and $r4 -eq 2 -and $lowBoot -and $lowCheck -and $kept) { Write-Host 'OK: every planted failure came back as a failure'; exit 0 }
exit 1

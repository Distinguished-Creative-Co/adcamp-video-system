# Every command the Windows skill names, run with --help from Windows PowerShell 5.1, and the launcher from Git Bash.
# A command a stock PC cannot run fails here, not in a member's chat.
$ErrorActionPreference = 'Continue'
$A = Join-Path $env:RUNNER_TEMP 'Jane Doe\AVS'
$skill = Get-Content -LiteralPath "$A\skills\avs\SKILL.md" -Raw
$bad = @()
$scripts = [regex]::Matches($skill, 'avs run ([a-z_]+\.(?:py|mjs))') | ForEach-Object { $_.Groups[1].Value } | Sort-Object -Unique
foreach ($s in $scripts) {
  $null = & "$A\avs.cmd" run $s --help 2>&1; $rc = $LASTEXITCODE
  if ($rc -ne 0) { $bad += "avs run $s --help: exit $rc" }
}
$verbs = [regex]::Matches($skill, '`avs ([a-z][a-z-]+)') | ForEach-Object { $_.Groups[1].Value } | Where-Object { $_ -ne 'run' } | Sort-Object -Unique
foreach ($v in $verbs) {
  $null = & "$A\avs.cmd" $v --help 2>&1; $rc = $LASTEXITCODE
  if ($rc -ne 0) { $bad += "avs $v --help: exit $rc" }
}
$gb = 'C:\Program Files\Git\bin\bash.exe'
$u = ($A -replace '\\', '/')
$out = (& $gb --noprofile --norc -c "`"$u/avs.cmd`" doctor" 2>&1 | Out-String); $rc = $LASTEXITCODE
if ($rc -ne 0 -or $out -notmatch 'All set') { $bad += "Git Bash: avs.cmd doctor exit $rc" }
Write-Host ("skill lint: {0} scripts and {1} verbs from the skill, each run with --help in Windows PowerShell 5.1, plus the launcher from Git Bash" -f $scripts.Count, $verbs.Count)
if ($bad.Count) { $bad | ForEach-Object { Write-Host "  FAILED $_" }; exit 1 }
Write-Host '  OK every command the skill names runs on this PC'
exit 0

. "$PSScriptRoot\prelude.ps1"
$t = if (Test-Path -LiteralPath "$R\results.md") { Get-Content -LiteralPath "$R\results.md" -Raw } else { "no results file`n" }
[IO.File]::AppendAllText($env:GITHUB_STEP_SUMMARY, "## AVS for Windows, Phase 0 spike`n`n$t`n")
Write-Host $t

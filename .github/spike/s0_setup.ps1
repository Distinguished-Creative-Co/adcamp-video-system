. "$PSScriptRoot\prelude.ps1"
[IO.File]::WriteAllText("$R\results.md", "| # | Works | What happened |`n|---|---|---|`n")
Write-Host "AVS folder: $R"

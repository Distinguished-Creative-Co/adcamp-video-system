. "$PSScriptRoot\prelude.ps1"
$t0 = Get-Date
$out = (& $PY "$PSScriptRoot\models_test.py" 2>&1 | Out-String); $ok = $LASTEXITCODE -eq 0
$min = [math]::Round(((Get-Date) - $t0).TotalMinutes, 1)
[IO.File]::WriteAllText("$R\logs\models.txt", $out)
$gb = [math]::Round(((Get-ChildItem -LiteralPath "$R\models" -Recurse -File -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum) / 1GB, 2)
$tail = (($out -split "`r?`n") | Where-Object { $_ -match 'ready|Error|error' } | Select-Object -Last 5) -join ' / '
Row '4 speech and alignment models' $ok "$min min, $gb GB in the models folder; $tail"

. "$PSScriptRoot\prelude.ps1"
$t0 = Get-Date
& uv pip install --python $PY -r "$ENG\scripts\requirements-apple.txt" *> "$R\logs\pip-whisperx.txt"; $pipok = $LASTEXITCODE -eq 0
$min = [math]::Round(((Get-Date) - $t0).TotalMinutes, 1)
$imp = (& $PY -c "import whisperx, torch, faster_whisper; print('whisperx ok, torch', torch.__version__)" 2>&1 | Out-String).Trim()
$impok = $LASTEXITCODE -eq 0
$gb = [math]::Round(((Get-ChildItem -LiteralPath "$R\whisperx" -Recurse -File -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum) / 1GB, 2)
$fail = if (-not $pipok) { ' / pip tail: ' + ((Get-Content -LiteralPath "$R\logs\pip-whisperx.txt" -Tail 6) -join ' ') } else { '' }
Row '3 speech libraries (requirements-apple.txt) and the import line' ($pipok -and $impok) "pip $pipok in $min min, venv $gb GB; import: $($imp.Substring(0, [math]::Min(300, $imp.Length)))$fail"

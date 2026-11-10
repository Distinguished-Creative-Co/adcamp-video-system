. "$PSScriptRoot\prelude.ps1"
Push-Location -LiteralPath $ENG
$t0 = Get-Date
& $PY scripts\word_align_x.py samples\sample.mp4 --fast --model base *> "$R\logs\words.txt"; $ok = $LASTEXITCODE -eq 0
$sec = [math]::Round(((Get-Date) - $t0).TotalSeconds)
$j = 'script\word-timings\sample-wx.json'
$n = if (Test-Path -LiteralPath $j) { (Get-Content -LiteralPath $j -Raw | ConvertFrom-Json).Count } else { 0 }
if (Test-Path -LiteralPath $j) { Copy-Item -LiteralPath $j "$R\out\sample-wx.json" }
Pop-Location
Row '8 word_align_x.py --fast on the sample, unchanged' ($ok -and $n -gt 50) "$sec s, $n words; $(((Get-Content -LiteralPath "$R\logs\words.txt" -Tail 2) -join ' '))"

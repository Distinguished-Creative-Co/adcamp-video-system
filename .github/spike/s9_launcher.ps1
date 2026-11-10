. "$PSScriptRoot\prelude.ps1"
$E = "$PSScriptRoot\echo_args.py"
$res = [ordered]@{}
# 1. Windows PowerShell 5.1, the shell a member's Claude is likely to get
$res['PowerShell 5.1'] = (& $PY $E "C:\Users\Jane Doe\AVS\inbox\Mike's video & more.mp4" '{"text": "it''s here", "n": 2}' 2>&1 | Out-String).Trim()
# 2. PowerShell 7
[IO.File]::WriteAllText("$R\call.ps1", "& '$PY' '$E' 'C:\Users\Jane Doe\AVS\inbox\Mike''s video & more.mp4' '{`"text`": `"it''s here`", `"n`": 2}'`n")
$pw = 'C:\Program Files\PowerShell\7\pwsh.exe'
$res['PowerShell 7'] = if (Test-Path $pw) { (& $pw -NoProfile -File "$R\call.ps1" 2>&1 | Out-String).Trim() } else { 'not on this machine' }
# 3. cmd
[IO.File]::WriteAllText("$env:RUNNER_TEMP\call.cmd", "@`"$PY`" `"$E`" `"C:\Users\Jane Doe\AVS\inbox\Mike's video & more.mp4`" `"{\`"text\`": \`"it's here\`", \`"n\`": 2}`"`r`n")
# the batch file itself sits at a path with no space, so only what it passes is under test
$res['cmd'] = (& cmd.exe /d /c "$env:RUNNER_TEMP\call.cmd" 2>&1 | Out-String).Trim()
# 4. Git Bash
$u = { param($p) $p -replace '\\', '/' }
[IO.File]::WriteAllText("$R\call.sh", "`"$(& $u $PY)`" `"$(& $u $E)`" 'C:\Users\Jane Doe\AVS\inbox\Mike'`"'`"'s video & more.mp4' '{`"text`": `"it'`"'`"'s here`", `"n`": 2}'`n")
$gb = 'C:\Program Files\Git\bin\bash.exe'
$res['Git Bash'] = if (Test-Path $gb) { (& $gb --noprofile --norc (& $u "$R\call.sh") 2>&1 | Out-String).Trim() } else { 'not on this machine' }
# 5. the file route the plan prefers: the text goes in a file, only a plain path is passed
[IO.File]::WriteAllText("$R\args one.json", '{"text": "it''s here", "n": 2}')
$res['PS 5.1, JSON in a file'] = (& $PY "$PSScriptRoot\check_json.py" "$R\args one.json" 2>&1 | Out-String).Trim()
$note = ($res.GetEnumerator() | ForEach-Object { "$($_.Key): $($_.Value)" }) -join ' / '
Row '9 passing a path and quoted text to Python' (($res.Values | Where-Object { $_ -eq 'MATCH' }).Count -ge 1) $note

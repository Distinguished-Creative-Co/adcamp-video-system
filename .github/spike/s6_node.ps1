. "$PSScriptRoot\prelude.ps1"
$n = "node-v$env:NODE_VERSION-win-x64"; $z = "$n.zip"; $base = "https://nodejs.org/dist/v$env:NODE_VERSION"
$got = (Fetch "$base/$z" "$R\dl\$z") -and (Fetch "$base/SHASUMS256.txt" "$R\dl\node-SHASUMS256.txt")
$want = if ($got) { ((Get-Content -LiteralPath "$R\dl\node-SHASUMS256.txt" | Where-Object { $_ -match " $([regex]::Escape($z))$" }) -split '\s+')[0] } else { '' }
$hashok = $got -and ((Sha "$R\dl\$z") -eq $want)
& tar.exe -xf "$R\dl\$z" -C "$R\dl"
if (Test-Path -LiteralPath "$R\dl\$n") { Move-Item -LiteralPath "$R\dl\$n" -Destination "$R\node" -Force }
$nv = (& node -v) -join ''
Push-Location -LiteralPath $ENG
$t0 = Get-Date
& npm ci --no-audit --no-fund --loglevel=error *> "$R\logs\npm.txt"; $npmok = $LASTEXITCODE -eq 0
$npmMin = [math]::Round(((Get-Date) - $t0).TotalMinutes, 1)
& npx remotion browser ensure *> "$R\logs\browser.txt"; $brok = $LASTEXITCODE -eq 0
& npx remotion still src/methodology/index.ts FontSheet "$R\out\font sheet.png" --log=error *> "$R\logs\still.txt"; $stillok = ($LASTEXITCODE -eq 0) -and (Test-Path -LiteralPath "$R\out\font sheet.png")
Pop-Location
Row '6 Node, npm ci, renderer browser, one still' ($hashok -and $npmok -and $brok -and $stillok) "node $nv, checksum $hashok; npm ci $npmok ($npmMin min); browser $brok; FontSheet still to a path with a space $stillok"

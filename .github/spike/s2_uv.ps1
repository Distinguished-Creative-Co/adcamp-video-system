. "$PSScriptRoot\prelude.ps1"
$z = 'uv-x86_64-pc-windows-msvc.zip'; $base = "https://github.com/astral-sh/uv/releases/download/$env:UV_VERSION"
$got = (Fetch "$base/$z" "$R\dl\$z") -and (Fetch "$base/$z.sha256" "$R\dl\$z.sha256")
$want = if ($got) { ((Get-Content -LiteralPath "$R\dl\$z.sha256" -Raw).Trim() -split '\s+')[0].ToLower() } else { '' }
$hashok = $got -and ((Sha "$R\dl\$z") -eq $want)
New-Item -ItemType Directory -Force -Path "$R\dl\uv" | Out-Null
& tar.exe -xf "$R\dl\$z" -C "$R\dl\uv"
Get-ChildItem -LiteralPath "$R\dl\uv" -Recurse -Filter 'uv*.exe' | ForEach-Object { Copy-Item -LiteralPath $_.FullName -Destination "$R\bin" -Force }
$uvv = (& uv --version) -join ' '
& uv python install $env:PY_VERSION --no-bin; $pyok = $LASTEXITCODE -eq 0
& uv venv "$R\whisperx" --python $env:PY_VERSION; $venvok = ($LASTEXITCODE -eq 0) -and (Test-Path -LiteralPath $PY)
$layout = (Get-ChildItem -LiteralPath "$R\whisperx" | ForEach-Object { $_.Name }) -join ','
Row '2 uv, Python 3.12, a venv' ($hashok -and $pyok -and $venvok) "$uvv; checksum $hashok; python install $pyok; venv folders: $layout; Scripts\python.exe $venvok"

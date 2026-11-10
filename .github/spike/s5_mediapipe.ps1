. "$PSScriptRoot\prelude.ps1"
& uv venv "$R\matte" --python $env:PY_VERSION *> "$R\logs\matte-venv.txt"
& uv pip install --python $MPY 'mediapipe==0.10.21' *> "$R\logs\pip-matte.txt"; $pipok = $LASTEXITCODE -eq 0
& $MPY -c "import mediapipe" 2>&1 | Out-Null; $impok = $LASTEXITCODE -eq 0
$md = "$R\models\media pipe"; New-Item -ItemType Directory -Force -Path $md | Out-Null
$m = "$md\selfie_multiclass_256x256.tflite"
$got = Fetch 'https://storage.googleapis.com/mediapipe-models/image_segmenter/selfie_multiclass_256x256/float32/latest/selfie_multiclass_256x256.tflite' $m
$hashok = $got -and ((Sha $m) -eq 'c6748b1253a99067ef71f7e26ca71096cd449baefa8f101900ea23016507e0e0')
& ffmpeg -v error -y -ss 2 -i "$ENG\samples\sample.mp4" -frames:v 1 "$R\frame one.png"
$res = (& $MPY "$PSScriptRoot\mp_test.py" $m "$R\frame one.png" 2>&1 | Out-String).Trim()
$fullok = $res -match 'full path with a space: ok'; $bytesok = $res -match 'bytes: ok'
Row '5 MediaPipe cutout' ($pipok -and $impok -and $hashok -and ($fullok -or $bytesok)) "install $pipok, import $impok, model checksum $hashok; $(($res -split "`r?`n" | Where-Object { $_ -match 'ok|FAILED' }) -join ' / ')"

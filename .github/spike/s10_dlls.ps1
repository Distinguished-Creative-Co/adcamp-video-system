. "$PSScriptRoot\prelude.ps1"
$a = (& $PY "$PSScriptRoot\dlls.py" torch ctranslate2 onnxruntime faster_whisper whisperx 2>&1 | Select-Object -Last 1 | Out-String).Trim()
$b = (& $MPY "$PSScriptRoot\dlls.py" mediapipe cv2 2>&1 | Select-Object -Last 1 | Out-String).Trim()
Row '10 which Microsoft C++ runtime files the libraries load' $true "speech: $a / cutout: $b"

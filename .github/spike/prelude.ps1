# Shared by every Phase 0 step. Windows PowerShell 5.1, PATH scrubbed down to Windows itself plus AVS's own tools,
# so nothing the runner preinstalled (its Python, Node, Git, ffmpeg) can help. The AVS folder has a space on purpose.
$ErrorActionPreference = 'Continue'
$R = Join-Path $env:RUNNER_TEMP 'AVS spike'
$ENG = Join-Path $env:GITHUB_WORKSPACE 'engine'
$env:Path = "$R\bin;$R\node;$R\ffmpeg\bin;C:\Windows\system32;C:\Windows;C:\Windows\System32\Wbem;C:\Windows\System32\WindowsPowerShell\v1.0"
$env:UV_PYTHON_INSTALL_DIR = "$R\python"; $env:UV_CACHE_DIR = "$R\uv-cache"
$env:HF_HOME = "$R\models\hf"; $env:TORCH_HOME = "$R\models\torch"
$env:PYTHONUTF8 = '1'; $env:HF_HUB_DISABLE_TELEMETRY = '1'; $env:PYANNOTE_METRICS_ENABLED = '0'; $env:DO_NOT_TRACK = '1'
$PY = "$R\whisperx\Scripts\python.exe"; $MPY = "$R\matte\Scripts\python.exe"
foreach ($d in "$R", "$R\dl", "$R\bin", "$R\out", "$R\logs", "$R\models") { New-Item -ItemType Directory -Force -Path $d | Out-Null }
function Row([string]$n, [bool]$ok, [string]$note) {
  $flag = if ($ok) { 'yes' } else { 'NO' }
  $line = "| $n | $flag | $(($note -replace '\|', '/') -replace "`r?`n", ' ') |`n"
  [IO.File]::AppendAllText("$R\results.md", $line)
  Write-Host "ROW $line"
}
function Fetch([string]$url, [string]$out) { & curl.exe -fsSL --retry 3 -o $out $url; return ($LASTEXITCODE -eq 0) }
function Sha([string]$p) { if (Test-Path -LiteralPath $p) { (Get-FileHash -Algorithm SHA256 -LiteralPath $p).Hash.ToLower() } else { 'missing' } }

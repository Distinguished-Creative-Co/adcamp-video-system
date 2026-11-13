# AdCamp Video System for Windows: the one PowerShell step. It checks the chip, fetches uv (checksum checked),
# installs AVS's own Python 3.12 into runtime\python and makes runtime\base, the Python the launcher runs on.
# Everything after this goes through avs.cmd in this folder.
#   powershell -NoProfile -ExecutionPolicy Bypass -File bootstrap.ps1 [-FromPlugin]
param([switch]$FromPlugin)   # from the Plugins panel: copy AVS into the home folder first, then set it up there
$ErrorActionPreference = 'Continue'
$AVS = $PSScriptRoot
if ($FromPlugin) {
  $dst = Join-Path $HOME 'AVS'
  if (Test-Path -LiteralPath (Join-Path $dst 'runtime\base\Scripts\python.exe')) { Write-Host "  OK AVS is already set up in $dst. To bring it to this version: avs.cmd update `"$AVS`""; exit 0 }
  if ((Test-Path -LiteralPath $dst) -and -not (Test-Path -LiteralPath (Join-Path $dst 'engine'))) { Write-Host "  FAILED $dst exists but is not AVS. Move or rename it, then run this again."; exit 1 }
  & robocopy $AVS $dst /E /XD .git .claude-plugin /NFL /NDL /NJH /NJS /NP | Out-Null
  if ($LASTEXITCODE -ge 8) { Write-Host '  FAILED AVS could not be copied into your home folder. Run this again.'; exit 1 }
  New-Item -ItemType Directory -Force -Path (Join-Path $dst 'runtime') | Out-Null
  [IO.File]::WriteAllText((Join-Path $dst 'runtime\.via-plugin'), $AVS)
  Write-Host "  OK AVS copied to $dst (the skill comes from the plugin)"
  & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $dst 'bootstrap.ps1')
  exit $LASTEXITCODE
}
$RT = Join-Path $AVS 'runtime'
$UV_VERSION = '0.12.22'
$UV_SHA = 'ea1397797a0ca15f63516dd0f49c2dde9776db9be5861cab152ebe8ad199894d'
function Stop-Avs([string]$m) { Write-Host "  FAILED $m"; exit 1 }
Write-Host ''
Write-Host "== bootstrap: AVS's own Python, which runs the setup steps"
$arch = if ($env:PROCESSOR_ARCHITEW6432) { $env:PROCESSOR_ARCHITEW6432 } else { $env:PROCESSOR_ARCHITECTURE }
$osArch = try { [string][System.Runtime.InteropServices.RuntimeInformation]::OSArchitecture } catch { '' }   # also right when this shell runs emulated
if ($arch -match 'ARM' -or $osArch -match 'Arm') { Stop-Avs 'this PC has an ARM chip (like a Snapdragon laptop). AVS for Windows needs an Intel or AMD PC for now.' }
$ramGb = 0   # the memory installed, as Windows Settings shows it (AVS_TEST_RAM_GB stands in for it in the tests)
if ($env:AVS_TEST_RAM_GB) { $ramGb = [double]$env:AVS_TEST_RAM_GB } else {
  try { $ramGb = [double]((Get-CimInstance Win32_PhysicalMemory -ErrorAction Stop | Measure-Object -Property Capacity -Sum).Sum) / 1GB } catch { }
  if (-not $ramGb) { try { $ramGb = [double](Get-CimInstance Win32_ComputerSystem -ErrorAction Stop).TotalPhysicalMemory / 1GB } catch { } }
}
if ($ramGb -gt 0 -and $ramGb -lt 7.5) {
  Stop-Avs ('this PC has {0:N0} GB of memory. AVS needs at least 8 GB (16 recommended), because making a video runs the renderer and the speech tools at the same time. Nothing was downloaded.' -f $ramGb)
}
if (-not (Get-Command curl.exe -ErrorAction SilentlyContinue) -or -not (Get-Command tar.exe -ErrorAction SilentlyContinue)) {
  Stop-Avs 'this Windows is missing curl.exe or tar.exe. AVS needs Windows 10 version 1803 or newer.'
}
foreach ($d in $RT, "$RT\bin", "$RT\dl") { New-Item -ItemType Directory -Force -Path $d | Out-Null }
$env:UV_PYTHON_INSTALL_DIR = "$RT\python"; $env:UV_CACHE_DIR = "$RT\uv-cache"
$uv = "$RT\bin\uv.exe"
if (-not (Test-Path -LiteralPath $uv)) {
  $z = "$RT\dl\uv.zip"
  & curl.exe -fL --retry 3 -sS -o $z "https://github.com/astral-sh/uv/releases/download/$UV_VERSION/uv-x86_64-pc-windows-msvc.zip"
  if ($LASTEXITCODE -ne 0) { Stop-Avs 'the uv download failed. Check the internet connection and run this again.' }
  if ((Get-FileHash -Algorithm SHA256 -LiteralPath $z).Hash.ToLower() -ne $UV_SHA) {
    Remove-Item -LiteralPath $z -Force; Stop-Avs 'the uv download did not match its checksum, so it was not used. Run this again.'
  }
  New-Item -ItemType Directory -Force -Path "$RT\dl\uv" | Out-Null
  & tar.exe -xf $z -C "$RT\dl\uv"
  Get-ChildItem -LiteralPath "$RT\dl\uv" -Recurse | Where-Object { $_.Name -in 'uv.exe', 'uvx.exe' } | ForEach-Object { Copy-Item -LiteralPath $_.FullName -Destination "$RT\bin" -Force }
  Remove-Item -LiteralPath "$RT\dl\uv" -Recurse -Force; Remove-Item -LiteralPath $z -Force
  if (-not (Test-Path -LiteralPath $uv)) { Stop-Avs 'uv did not unpack. Run this again.' }
}
& $uv python install 3.12 --no-bin
if ($LASTEXITCODE -ne 0) { Stop-Avs 'Python 3.12 did not install. Run this again.' }
if (-not (Test-Path -LiteralPath "$RT\base\Scripts\python.exe")) {
  & $uv venv "$RT\base" --python 3.12 --managed-python
  if ($LASTEXITCODE -ne 0) { Stop-Avs 'the launcher Python could not be made. Run this again.' }
}
Write-Host "  OK uv and Python 3.12 are in $RT. Next: avs.cmd install --step check"
exit 0

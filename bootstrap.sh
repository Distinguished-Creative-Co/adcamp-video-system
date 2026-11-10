#!/bin/sh
# AdCamp Video System: the launcher's bootstrap on a Mac. It fetches uv (checksum checked), installs AVS's own
# Python 3.12 into runtime/python and makes runtime/base, the Python the launcher runs on. Then: ./avs install --all
set -eu
AVS="$(cd "$(dirname "$0")" && pwd)"; RT="$AVS/runtime"; V=0.12.22
if [ "$(sysctl -n hw.optional.arm64 2>/dev/null || echo 0)" = 1 ]; then A=aarch64; S=5d714de09501a59393ceca78f4bc232a50478729640d251907160299b2a93ddd
else A=x86_64; S=1b8a5b316883df2daf20fb9a446e5b230e01d947d57aba2694977c5ac5a7e98c; fi
echo; echo "== bootstrap: AVS's own Python, which runs the setup steps"
mkdir -p "$RT/bin" "$RT/dl"
export UV_PYTHON_INSTALL_DIR="$RT/python" UV_CACHE_DIR="$RT/uv-cache"
if [ ! -x "$RT/bin/uv" ]; then
  T="$RT/dl/uv.tar.gz"
  curl -fL --retry 3 -sS -o "$T" "https://github.com/astral-sh/uv/releases/download/$V/uv-$A-apple-darwin.tar.gz" || { echo "  FAILED the uv download failed. Check the internet connection and run this again."; exit 1; }
  [ "$(shasum -a 256 "$T" | cut -c1-64)" = "$S" ] || { rm -f "$T"; echo "  FAILED the uv download did not match its checksum, so it was not used. Run this again."; exit 1; }
  tar -xzf "$T" -C "$RT/dl" && cp "$RT/dl/uv-$A-apple-darwin/uv" "$RT/dl/uv-$A-apple-darwin/uvx" "$RT/bin/"
  rm -rf "$T" "$RT/dl/uv-$A-apple-darwin"
fi
"$RT/bin/uv" python install 3.12 --no-bin
[ -x "$RT/base/bin/python" ] || "$RT/bin/uv" venv "$RT/base" --python 3.12 --managed-python
chmod +x "$AVS/avs"
echo "  OK uv and Python 3.12 are in $RT. Next: ./avs install --step check"

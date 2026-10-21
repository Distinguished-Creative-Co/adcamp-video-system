#!/bin/bash
# Distinguished Vertical Editor checkup: what is installed, what is missing. Changes nothing.
#   ~/DVE/tools/doctor.sh
RE="$(cd "$(dirname "$0")/.." && pwd)"
RT="$RE/runtime"
[ -f "$RT/env.sh" ] && . "$RT/env.sh"
export PATH="$RT/node/bin:$RT/bin:$PATH"
miss=0
row(){ if [ "$2" = ok ]; then printf '  \033[32mOK\033[0m       %-22s %s\n' "$1" "$3"; else printf '  \033[31mMISSING\033[0m  %-22s %s\n' "$1" "$3"; miss=1; fi; }
v(){ "$@" 2>/dev/null | head -1; }

echo "DVE $(cat "$RE/VERSION" 2>/dev/null) on $(uname -m), macOS $(sw_vers -productVersion)"
free_gb=$(df -g "$RE" | awk 'NR==2{print $4}')
[ "$free_gb" -ge 5 ] && row "disk" ok "${free_gb} GB free" || row "disk" no "${free_gb} GB free (keep 5+ GB for renders)"
command -v node >/dev/null && row "node" ok "$(node -v)" || row "node" no "run: ./install.sh --step node"
if command -v ffmpeg >/dev/null && ffmpeg -hide_banner -encoders 2>/dev/null | grep -q libvpx-vp9; then row "ffmpeg" ok "$(v ffmpeg -version | cut -c1-30)"; else row "ffmpeg" no "run: ./install.sh --step ffmpeg"; fi
command -v uv >/dev/null && row "uv" ok "$(v uv --version)" || row "uv" no "run: ./install.sh --step uv"
[ -x "$RT/bin/python3" ] && row "python" ok "$(v "$RT/bin/python3" --version)" || row "python" no "run: ./install.sh --step python"
if [ -x "$RT/whisperx/bin/python" ] && "$RT/whisperx/bin/python" -c "import whisperx, torch" 2>/dev/null; then
  row "speech libraries" ok "torch $("$RT/whisperx/bin/python" -c 'import torch; print(torch.__version__)')"
else row "speech libraries" no "run: ./install.sh --step venv"; fi
[ -d "$RE/engine/node_modules/remotion" ] && row "renderer" ok "Remotion $(node -p "require('$RE/engine/node_modules/remotion/package.json').version" 2>/dev/null)" || row "renderer" no "run: ./install.sh --step npm"
ls "$RT/models/hf/hub" 2>/dev/null | grep -q faster-whisper-small && row "speech models" ok "faster-whisper base + small" || row "speech models" no "run: ./install.sh --step models"
if [ -x "$RT/matte/bin/python" ] && "$RT/matte/bin/python" -c "import mediapipe" 2>/dev/null && [ -f "$RT/models/mediapipe/selfie_multiclass_256x256.tflite" ]; then row "cutout" ok "MediaPipe segmenter + model"; else row "cutout" no "run: ./install.sh --step cutout"; fi
[ -f "$RT/env.sh" ] && row "env" ok "runtime/env.sh" || row "env" no "run: ./install.sh --step env"
[ -f "$HOME/.claude/skills/dve/SKILL.md" ] && row "skill" ok "~/.claude/skills/dve" || row "skill" no "run: ./install.sh --step skill"
python3 -c "import json;b=json.load(open('$RE/engine/src/brand.json'));print('  brand: accent %s, sans %s, serif %s' % (b['accent'],b['sans'],b['serif']))" 2>/dev/null
echo
[ "$miss" -eq 0 ] && echo "All set. In Claude Code: \"make a reel\" (drop your video and script in ~/DVE/inbox)." || echo "Something is missing: run the step shown, or ./install.sh --all"
exit $miss

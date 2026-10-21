#!/bin/bash
# Distinguished Vertical Editor installer (macOS, Apple Silicon or Intel). No sudo, no Homebrew needed.
#
#   ./install.sh --step <name> [options]     run ONE step (Claude Code runs them in order, narrating each)
#   ./install.sh --all [options]             run every step in order
#   ./install.sh --list                      print the steps with their download sizes
#
# Steps (each is safe to re-run; a finished step is skipped):
#   check    disk space, chip, macOS                                       (no download)
#   node     Node.js 22 into runtime/node, unless Node 20+ is already there (~50 MB)
#   ffmpeg   static ffmpeg + ffprobe into runtime/bin, unless a capable one is there (~80 MB)
#   uv       the uv Python manager into runtime/bin, unless already there   (~15 MB)
#   python   Python 3.12 into runtime/python                                (~30 MB)
#   venv     speech libraries into runtime/whisperx                          (~1.3 GB, 3-8 min)
#   npm      the video renderer's packages into engine/node_modules          (~450 MB, 1-3 min)
#   models   speech models into runtime/models                               (~1 GB)
#   cutout   the person-cutout library (MediaPipe) + model into runtime/matte (~70 MB)
#   browser  the headless Chrome the renderer draws with                     (~175 MB)
#   brand    write engine/src/brand.json        --accent '#RRGGBB' --sans <name> --serif <name> [--handle @you --name 'Your Name' --avatar photo.jpg]
#   env      write runtime/env.sh (the paths every script loads)
#   skill    install the Claude Code skill "dve"   [--skill-dir DIR, default ~/.claude/skills]
#
# Everything lives in this folder (~/DVE). tools/uninstall.sh removes it.
set -euo pipefail

RE="$(cd "$(dirname "$0")" && pwd)"
RT="$RE/runtime"
ENG="$RE/engine"
ARCH="$(uname -m)"                      # arm64 | x86_64
NODE_VERSION="22.23.3"
UV_VERSION="0.12.22"
PY_VERSION="3.12"
SKILL_DIR="$HOME/.claude/skills"
ACCENT=""; SANS=""; SERIF=""; HANDLE=""; NAME=""; AVATAR=""; STEP=""; ALL=0

while [ $# -gt 0 ]; do
  case "$1" in
    --step) STEP="$2"; shift 2;;
    --all) ALL=1; shift;;
    --list) sed -n '/^# Steps/,/^# Everything/p' "$0" | sed 's/^# \{0,1\}//'; exit 0;;
    --accent) ACCENT="$2"; shift 2;;
    --sans) SANS="$2"; shift 2;;
    --serif) SERIF="$2"; shift 2;;
    --handle) HANDLE="$2"; shift 2;;
    --name) NAME="$2"; shift 2;;
    --avatar) AVATAR="$2"; shift 2;;
    --skill-dir) SKILL_DIR="$2"; shift 2;;
    *) echo "unknown option: $1 (see ./install.sh --list)"; exit 2;;
  esac
done

mkdir -p "$RT/bin" "$RT/dl" "$RT/models"
export PATH="$RT/node/bin:$RT/bin:$PATH"
export UV_PYTHON_INSTALL_DIR="$RT/python" UV_CACHE_DIR="$RT/uv-cache"
export HF_HOME="$RT/models/hf" TORCH_HOME="$RT/models/torch"
case "$ARCH" in
  arm64) NODE_ARCH=arm64; FF_ARCH=arm64; UV_ARCH=aarch64; REQ=requirements-apple.txt;;
  x86_64) NODE_ARCH=x64; FF_ARCH=amd64; UV_ARCH=x86_64; REQ=requirements-intel.txt;;
  *) echo "error: unsupported chip $ARCH"; exit 1;;
esac

ok(){ printf '\033[1;32m  OK\033[0m %s\n' "$*"; }
say(){ printf '\n\033[1;33m▸ %s\033[0m\n' "$*"; }
die(){ printf '\033[1;31m  FAILED\033[0m %s\n' "$*"; exit 1; }
fetch(){ curl -fL --retry 3 --progress-bar -o "$2" "$1" || die "download failed: $1"; }

node_ok(){ command -v node >/dev/null 2>&1 && [ "$(node -p 'process.versions.node.split(".")[0]' 2>/dev/null || echo 0)" -ge 20 ]; }
ffmpeg_ok(){ command -v ffmpeg >/dev/null 2>&1 && command -v ffprobe >/dev/null 2>&1 \
  && ffmpeg -hide_banner -encoders 2>/dev/null | grep -q libvpx-vp9 && ffmpeg -hide_banner -encoders 2>/dev/null | grep -q libx264; }

step_check(){
  say "check: this Mac"
  ok "chip: $ARCH ($([ "$ARCH" = arm64 ] && echo 'Apple Silicon' || echo 'Intel: slower, uses the Intel library set'))"
  ok "macOS $(sw_vers -productVersion)"
  local free_gb; free_gb=$(df -g "$RE" | awk 'NR==2{print $4}')
  [ "$free_gb" -ge 12 ] || die "only ${free_gb} GB free. DVE needs about 12 GB (3 GB of downloads plus working space)."
  ok "free disk: ${free_gb} GB"
  command -v curl >/dev/null || die "curl missing"
}

step_node(){
  say "node: Node.js (runs the video renderer)"
  if node_ok; then ok "Node $(node -v) already installed at $(command -v node)"; return; fi
  local tgz="node-v${NODE_VERSION}-darwin-${NODE_ARCH}.tar.gz"
  fetch "https://nodejs.org/dist/v${NODE_VERSION}/${tgz}" "$RT/dl/$tgz"
  fetch "https://nodejs.org/dist/v${NODE_VERSION}/SHASUMS256.txt" "$RT/dl/node-SHASUMS256.txt"
  ( cd "$RT/dl" && grep " ${tgz}\$" node-SHASUMS256.txt | shasum -a 256 -c - >/dev/null ) || die "Node download failed its checksum"
  rm -rf "$RT/node" && mkdir -p "$RT/node" && tar -xzf "$RT/dl/$tgz" -C "$RT/node" --strip-components 1
  node_ok || die "Node did not start"
  rm -f "$RT/dl/$tgz" "$RT/dl/node-SHASUMS256.txt"
  ok "Node $(node -v) installed in runtime/node (checksum verified)"
}

step_ffmpeg(){
  say "ffmpeg: video and audio processing"
  if ffmpeg_ok; then ok "ffmpeg already installed at $(command -v ffmpeg)"; return; fi
  for t in ffmpeg ffprobe; do
    fetch "https://ffmpeg.martin-riedl.de/redirect/latest/macos/${FF_ARCH}/release/${t}.zip" "$RT/dl/${t}.zip"
    unzip -o -q "$RT/dl/${t}.zip" -d "$RT/bin"
    chmod +x "$RT/bin/$t"
  done
  rm -f "$RT/dl/ffmpeg.zip" "$RT/dl/ffprobe.zip"
  ffmpeg_ok || die "ffmpeg is missing the VP9 or H.264 encoder"
  ok "$(ffmpeg -version | head -1 | cut -c1-40) installed in runtime/bin"
}

step_uv(){
  say "uv: installs Python and its libraries without touching your system"
  if command -v uv >/dev/null 2>&1; then ok "uv already installed ($(uv --version))"; return; fi
  local tgz="uv-${UV_ARCH}-apple-darwin.tar.gz"
  fetch "https://github.com/astral-sh/uv/releases/download/${UV_VERSION}/${tgz}" "$RT/dl/$tgz"
  fetch "https://github.com/astral-sh/uv/releases/download/${UV_VERSION}/${tgz}.sha256" "$RT/dl/$tgz.sha256"
  ( cd "$RT/dl" && shasum -a 256 -c "$tgz.sha256" >/dev/null ) || die "uv download failed its checksum"
  tar -xzf "$RT/dl/$tgz" -C "$RT/dl" && cp "$RT/dl/uv-${UV_ARCH}-apple-darwin/uv" "$RT/dl/uv-${UV_ARCH}-apple-darwin/uvx" "$RT/bin/"
  rm -rf "$RT/dl/$tgz" "$RT/dl/$tgz.sha256" "$RT/dl/uv-${UV_ARCH}-apple-darwin"
  ok "uv $(uv --version | awk '{print $2}') installed in runtime/bin (checksum verified)"
}

step_python(){
  say "python: Python ${PY_VERSION} (private to DVE)"
  uv python install "$PY_VERSION" --no-bin >/dev/null   # no shortcut in ~/.local/bin: everything stays in this folder
  local py; py="$(uv python find "$PY_VERSION")"
  ln -sf "$py" "$RT/bin/python3"
  ok "$("$RT/bin/python3" --version) at runtime/bin/python3"
}

step_venv(){
  say "venv: speech-to-text and word alignment libraries ($REQ)"
  [ -x "$RT/whisperx/bin/python" ] || uv venv "$RT/whisperx" --python "$PY_VERSION" >/dev/null
  uv pip install --python "$RT/whisperx/bin/python" -r "$ENG/scripts/$REQ"
  "$RT/whisperx/bin/python" -c "import whisperx, torch, faster_whisper; print('whisperx ok, torch', torch.__version__)" \
    || die "the speech libraries did not import"
  uv cache clean >/dev/null 2>&1 || true   # the download cache is ~1 GB and never needed again
  ok "speech libraries installed in runtime/whisperx"
}

step_npm(){
  say "npm: the video renderer (Remotion) and its packages"
  node_ok || die "run the node step first"
  ( cd "$ENG" && npm ci --no-audit --no-fund --loglevel=error )
  ok "renderer packages installed in engine/node_modules"
}

step_models(){
  say "models: speech (faster-whisper base + small) and word alignment (wav2vec2)"
  [ -x "$RT/whisperx/bin/python" ] || die "run the venv step first"
  "$RT/whisperx/bin/python" - <<'PY'
import torch
from faster_whisper import WhisperModel
for m in ('base', 'small'):
    WhisperModel(m, device='cpu', compute_type='int8'); print('  speech model', m, 'ready')
import whisperx
whisperx.load_align_model(language_code='en', device='cpu'); print('  word-alignment model ready')
whisperx.load_model('base', 'cpu', compute_type='int8'); print('  voice-activity model ready')
PY
  ok "models cached in runtime/models"
}

step_cutout(){
  say "cutout: MediaPipe (cuts you out of the frame for the words-behind-you effect, Apache-2.0)"
  [ -x "$RT/matte/bin/python" ] || uv venv "$RT/matte" --python "$PY_VERSION" >/dev/null   # its own venv: it wants numpy 1.x
  uv pip install --python "$RT/matte/bin/python" "mediapipe==0.10.21"
  "$RT/matte/bin/python" -c "import mediapipe" || die "MediaPipe did not import"
  local m="$RT/models/mediapipe/selfie_multiclass_256x256.tflite"
  mkdir -p "$RT/models/mediapipe"
  if [ ! -f "$m" ] || [ "$(shasum -a 256 "$m" | cut -c1-64)" != "c6748b1253a99067ef71f7e26ca71096cd449baefa8f101900ea23016507e0e0" ]; then
    fetch "https://storage.googleapis.com/mediapipe-models/image_segmenter/selfie_multiclass_256x256/float32/latest/selfie_multiclass_256x256.tflite" "$m"
    [ "$(shasum -a 256 "$m" | cut -c1-64)" = "c6748b1253a99067ef71f7e26ca71096cd449baefa8f101900ea23016507e0e0" ] || die "the cutout model failed its checksum"
  fi
  uv cache clean >/dev/null 2>&1 || true
  ok "cutout library in runtime/matte, model in runtime/models/mediapipe (checksum verified)"
}

step_browser(){
  say "browser: the headless Chrome the renderer draws frames with"
  ( cd "$ENG" && npx remotion browser ensure >/dev/null )
  ok "renderer browser ready"
}

step_brand(){
  say "brand: your accent color, fonts, and the follow card's name, handle and photo"
  if [ -n "$AVATAR" ]; then
    [ -f "$AVATAR" ] || die "no such photo: $AVATAR"
    mkdir -p "$ENG/public/inserts"
    "$RT/bin/python3" - "$AVATAR" "$ENG/public/inserts/avatar.png" <<'PY'
import subprocess, sys
src, dst = sys.argv[1:3]
# square crop from the middle, 400 px, PNG (the card draws it in a circle)
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', src, '-vf', "crop='min(iw,ih)':'min(iw,ih)',scale=400:400", '-frames:v', '1', dst], check=True)
print('  photo saved as public/inserts/avatar.png')
PY
  fi
  "$RT/bin/python3" - "$ENG/src/brand.json" "$ACCENT" "$SANS" "$SERIF" "$HANDLE" "$NAME" "$AVATAR" <<'PY'
import json, re, sys
p, accent, sans, serif, handle, name = sys.argv[1:7]   # argv[7]: a photo was given
b = json.load(open(p))
if handle:
    b['handle'] = handle if handle.startswith('@') else '@' + handle
if name:
    b['name'] = name
if len(sys.argv) > 7 and sys.argv[7]:
    b['avatar'] = 'inserts/avatar.png'
if accent:
    if not re.fullmatch(r'#?[0-9A-Fa-f]{6}', accent): sys.exit('  accent must be a hex color like #F7C715')
    b['accent'] = '#' + accent.lstrip('#').upper()
if sans:
    if sans not in ('hanken', 'inter', 'montserrat', 'dmsans', 'poppins'): sys.exit('  sans must be hanken, inter, montserrat, dmsans or poppins')
    b['sans'] = sans
if serif:
    if serif not in ('playfair', 'instrument', 'dmserif', 'fraunces'): sys.exit('  serif must be playfair, instrument, dmserif or fraunces')
    b['serif'] = serif
json.dump(b, open(p, 'w'), indent=2)
print('  accent %s, sans %s, serif %s, follow card: %s %s' % (b['accent'], b['sans'], b['serif'], b.get('name') or '(no name yet)', b.get('handle') or ''))
PY
  ok "engine/src/brand.json written (change it any time, then re-render)"
}

step_env(){
  say "env: runtime/env.sh"
  local nodedir; nodedir="$(dirname "$(command -v node)")"
  cat > "$RT/env.sh" <<EOF
# written by install.sh: every DVE script loads this
export DVE_HOME="$RE"
export PATH="$nodedir:$RT/bin:\$PATH"
export DVE_PYTHON="$RT/whisperx/bin/python"
export DVE_MATTE_PYTHON="$RT/matte/bin/python"
export DVE_MODELS="$RT/models/mediapipe"
export HF_HOME="$RT/models/hf"
export TORCH_HOME="$RT/models/torch"
export UV_PYTHON_INSTALL_DIR="$RT/python"
EOF
  ok "runtime/env.sh written"
}

step_skill(){
  say "skill: Claude Code skill \"dve\" -> $SKILL_DIR/dve"
  mkdir -p "$SKILL_DIR/dve"
  sed "s|{{DVE_HOME}}|$RE|g" "$RE/skill/dve/SKILL.md" > "$SKILL_DIR/dve/SKILL.md"
  ok "skill installed. In a NEW Claude Code session, say: make a reel"
  # DVE's own cue sounds arrived in an update: switch on any role that is empty, once. A role you turn
  # off afterwards (null) stays off, because "_sfx_offered" remembers this already happened.
  "$RT/bin/python3" - "$ENG/sounds.json" <<'PY' || true
import json, os, sys
p = sys.argv[1]
d = json.load(open(p))
ALL = (('transition_whoosh', 'whoosh'), ('element_land', 'land'), ('state_change', 'click'), ('back_text_hit', 'impact'),
       ('insert_pop', 'pop'), ('cta_ding', 'ding'), ('cta_riser', 'riser'))
offered = d.get('_sfx_offered')
offered = set(offered) if isinstance(offered, list) else ({'transition_whoosh', 'element_land', 'state_change'} if offered else set())
on = []
for role, f in ALL:
    rel = 'sounds/sfx/%s.wav' % f
    if role not in offered and not d.get(role) and os.path.exists(os.path.join(os.path.dirname(p), rel)):
        d[role] = rel
        on.append(f)
    offered.add(role)
d['_sfx_offered'] = sorted(offered)
json.dump(d, open(p, 'w'), indent=2)
if on:
    print('Sound effects switched on: %s (DVE\'s own sounds). Set a role to null in engine/sounds.json to turn one off.' % ', '.join(on))
PY
}

STEPS="check node ffmpeg uv python venv npm models cutout browser brand env skill"
if [ "$ALL" -eq 1 ]; then
  for s in $STEPS; do "step_$s"; done
elif [ -n "$STEP" ]; then
  case " $STEPS " in *" $STEP "*) "step_$STEP";; *) die "no step '$STEP' (see ./install.sh --list)";; esac
else
  sed -n '2,6p' "$0" | sed 's/^# \{0,1\}//'
fi

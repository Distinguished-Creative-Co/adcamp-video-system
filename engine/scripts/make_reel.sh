#!/usr/bin/env bash
# make_reel.sh — raw vertical recording + writer's script -> reviewed 1080x1920 short.
#
#   scripts/make_reel.sh <raw.MOV|mp4> <name> [--face X,Y] [--regen] [--preview] [--unmirror]   builds everything, STOPS at the scene map
#       [--keep-take N | --drop-take N | --trim A-B]   a different take, or a fumble cut out (raw seconds): forces a fresh cut
#     --trim repeats, one per fumble. Picks and trims are saved (script/word-timings/<name>-takepicks.json, -trims.json),
#       and a change to either file, by hand too, re-cuts on the next run
#     --unmirror: flip iPhone front-camera footage saved mirrored (text on screen reads backwards)
#     --reframe Z: crop to 1/Z from the full-res source, bottom-anchored (removes dead space above the subject)
#     --paid: first generation makes a paid Meta ad config (Click Learn More, destination link, ad kit)
#     --outdoor: street or camera audio where noise fills the pauses: precise word timing on the raw,
#       pauses found from the gaps between words (last_take.py --word-gaps)
#   scripts/make_reel.sh <raw.MOV|mp4> <name> --draft      a half-size review draft with sound, badged DRAFT, into out/drafts/
#     (not the deliverable, so it needs no approval: the creator watches the edit in motion before approving)
#     refuses while the config's frames do not match the cut (a re-cut keeps the old config: frozen tail or lost words)
#   scripts/make_reel.sh <raw.MOV|mp4> <name> --render       renders ONLY with a current human approval
#
# Needs script/<name>.txt (blank-line paragraphs = spoken beats). Steps are skipped when
# their output is newer than their inputs. The laws: the spoken script is the timeline;
# cuts only between sentences, in silence; captions show the script on spoken timing; the
# avatar is always on screen; render only after a human approved the scene map.
case "${1:-}" in -h|--help) sed -n '2,/^[^#]/p' "$0" | sed -n 's/^# \{0,1\}//p'; exit 0;; esac   # --help: the usage, nothing else
set -euo pipefail

RAW="${1:?usage: make_reel.sh <raw> <name> [--face X,Y] [--regen] [--preview] [--render]}"
NAME="${2:?usage: make_reel.sh <raw> <name> ...}"
shift 2
FACE=""; REGEN=""; RENDER=0; DRAFT=0; PREVIEW=0; UNMIRROR=""; REFRAME=""; PAID=""; OUTDOOR=""; TAKES=""; ENGINE="remotion"
while [ $# -gt 0 ]; do
  case "$1" in
    --face) FACE="$2"; shift 2;;
    --regen) REGEN="--regen"; shift;;
    --render) RENDER=1; shift;;
    --draft) DRAFT=1; shift;;
    --preview) PREVIEW=1; shift;;
    --unmirror) UNMIRROR="--unmirror"; shift;;
    --reframe) REFRAME="--reframe $2"; shift 2;;
    --paid) PAID="--paid"; shift;;
    --outdoor) OUTDOOR="--word-gaps"; shift;;
    --keep-take|--drop-take|--trim) TAKES="$TAKES $1 $2"; shift 2;;   # take picks and fumble trims: forces a fresh cut
    *) echo "unknown option $1"; exit 2;;
  esac
done

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
# the installer writes runtime/env.sh: node, ffmpeg, python3, the whisperX venv, model caches
RUNTIME="$(cd "$ROOT/.." && pwd)/runtime"
[ -f "$RUNTIME/env.sh" ] || { echo "error: AVS is not installed (no $RUNTIME/env.sh). Run ~/AVS/install.sh"; exit 1; }
. "$RUNTIME/env.sh"
WHISPERX="$AVS_PYTHON"
MATTE_PY="$AVS_MATTE_PYTHON"
SRC="inputs/${NAME}.mp4"
WX="script/word-timings/${NAME}-wx.json"
CUT="public/host/${NAME}-cut.mp4"
CUTWX="script/word-timings/${NAME}-cut-wx.json"
CFG="src/methodology/reels/${NAME}.config.ts"
MAP="script/${NAME}-scene-map.md"
OUT="out/${NAME}.mp4"
say(){ printf '\n\033[1;33m▸ %s\033[0m\n' "$*"; }
newer(){ [ -f "$1" ] && [ "$1" -nt "$2" ]; }   # newer <output> <input>

# the writer's script is needed to BUILD a cut; a render (or a variant reusing another cut) does not
[ "$RENDER" -eq 1 ] || [ "$DRAFT" -eq 1 ] || [ -f "script/${NAME}.txt" ] || { echo "error: script/${NAME}.txt is missing (the writer's script is the timeline)"; exit 1; }
[ -x "$WHISPERX" ] || { echo "error: whisperX not found. Run: ~/AVS/tools/doctor.sh"; exit 1; }
[ -x "$MATTE_PY" ] || { echo "error: the cutout environment is missing. Run: ~/AVS/tools/doctor.sh"; exit 1; }
command -v ffmpeg >/dev/null || { echo "error: ffmpeg not on PATH"; exit 1; }

# The files one reel's render reads, staged into a temp public dir ($PUB). "hi" adds the full-resolution
# host twin (sharp zooms); a draft leaves it out, so it draws from the 1080 cut and renders faster.
stage_public(){   # exactly the files the render loads: reelFiles() in ReelConfig.ts, the list the components draw from
  PUB="$(mktemp -d)"
  FILES="$(node scripts/reel_files.mjs "$NAME")" || { rm -rf "$PUB"; echo "error: could not read the files ${NAME} uses (its config failed to load)"; exit 1; }
  MISSING=""
  while read -r kind rest; do
    [ -n "$kind" ] || continue
    f="$rest"; case "$rest" in "hi "*) f="${rest#hi }"; [ "${1:-}" = hi ] || continue;; esac   # full-resolution files: the real render only
    if [ -f "public/$f" ]; then mkdir -p "$PUB/$(dirname "$f")"; cp "public/$f" "$PUB/$f"
    elif [ "$kind" = need ]; then MISSING="$MISSING public/$f"; fi
  done <<< "$FILES"
  if [ -n "$MISSING" ]; then
    rm -rf "$PUB"
    echo "error: ${NAME} uses files that are not there:${MISSING}"
    echo "  A cutout (-fg-, -thumb-) is made by: $MATTE_PY scripts/matte_reel.py ${NAME}. A screenshot or clip goes back under public/ with that name, or out of the config."
    exit 1
  fi
  return 0
}

# A render that could not load a file draws a hole or a broken image and still finishes, so its log is read:
# any failed load of a file the reel needs stops the build. The optional files (the full-resolution and graded
# copies, the sidecar) are looked for and may be missing, so those misses are fine.
render_checked(){   # <log> <remotion render args...>
  local log="$1"; shift
  set +e
  npx remotion render "$@" 2>&1 | tee "$log"; local rc=${PIPESTATUS[0]}
  local fails maybe bad=""
  fails="$(grep -E 'Failed to load resource|status of 404' "$log")"
  maybe="$(printf '%s\n' "$FILES" | sed -nE 's/^maybe (hi )?//p')"
  while IFS= read -r line; do
    [ -n "$line" ] || continue
    u="$(printf '%s' "$line" | grep -oE 'https?://[^] ]+' | head -1)"
    case "$u" in *'/proxy?src='*) u="$(printf '%s' "$u" | sed -E 's#^.*/proxy[?]src=##; s#&.*$##; s#%3A#:#g; s#%2F#/#g')";; esac   # a video frame read through the renderer's proxy
    u="$(printf '%s' "$u" | sed -E 's#^https?://[^/]+/(public/)?##; s#[?].*$##')"
    if [ -z "$u" ]; then bad="$bad a file (see $log)"
    elif ! printf '%s\n' "$maybe" | grep -qxF "$u"; then case " $bad " in *" $u "*) ;; *) bad="$bad $u";; esac; fi
  done <<< "$fails"
  if [ "$rc" -ne 0 ]; then   # the renderer stopped: name the reel's own file it choked on (a damaged cutout, a broken clip)
    local f u
    while read -r k f; do
      [ "$k" = need ] || continue   # the optional copies are looked for and may be missing
      grep -qF "$f" "$log" && grep -F "$f" "$log" | grep -qiE 'error|fail|could not|cannot|unable|decode|invalid' && { case " $bad " in *" $f "*) ;; *) bad="$bad $f";; esac; }
    done <<< "$FILES"
  fi
  set -e
  if [ -n "$bad" ]; then
    rm -f "$3"; rm -rf "$PUB"
    echo "error: the render of ${NAME} could not load:${bad} (missing or damaged). Its picture would show a hole or a broken image, so it stops here."
    echo "  A cutout (-fg-, -thumb-): move it out of public/host (and its .src file beside it), then run the same command again, it is cut again. A screenshot or clip: put a good copy back under public/ with that name. Then render again."
    exit 1
  fi
  if [ "$rc" -ne 0 ]; then
    rm -f "$3"; rm -rf "$PUB"
    echo "error: the render of ${NAME} stopped: $(grep -iE 'error' "$log" | grep -v '^ *at ' | tail -1 | cut -c1-200). The full log is $log."
    exit "$rc"
  fi
}

if [ "$DRAFT" -eq 1 ]; then
  # A review copy, not the deliverable: half size, same edit and sound, badged so nobody posts it.
  # It binds nothing and approves nothing; the real render still needs a current approval.
  python3 -c "import sys; sys.path.insert(0,'scripts'); import reel_config, scene_map; c=reel_config.load('$NAME'); e=scene_map.cut_length_error('$NAME', c['frames'], scene_map.cut_frames(c)); sys.exit('error: no draft of ${NAME}. ' + e if e else 0)"   # the scene map's length check
  DD="out/drafts"; DRAFT_OUT="$DD/${NAME}-DRAFT.mp4"; mkdir -p "$DD" "qa/${NAME}"
  say "draft: the edit at half size with sound, to watch before approving -> $DRAFT_OUT"
  python3 scripts/color_lut.py "$NAME"; "$MATTE_PY" scripts/matte_reel.py "$NAME"
  stage_public
  render_checked "qa/${NAME}/draft-render.log" src/methodology/index.ts "$NAME" "$DD/${NAME}-picture.mp4" --muted --scale=0.5 --crf=28 --public-dir="$PUB" --timeout=180000
  rm -rf "$PUB"
  MIX_QA_SUB=draft python3 scripts/mix_master.py "$NAME" "$DD/${NAME}-picture.mp4" "$DD/${NAME}-mix.mp4"   # records go to qa/<name>/draft, the render's stay
  "$MATTE_PY" scripts/draft_badge.py "$DD/${NAME}-badge.png" 540
  ffmpeg -v error -y -i "$DD/${NAME}-mix.mp4" -i "$DD/${NAME}-badge.png" \
    -filter_complex "[0:v][1:v]overlay=(W-w)/2:20" -c:v libx264 -crf 28 -preset veryfast -pix_fmt yuv420p \
    -c:a aac -b:a 96k -movflags +faststart "$DRAFT_OUT"
  rm -f "$DD/${NAME}-picture.mp4" "$DD/${NAME}-mix.mp4" "$DD/${NAME}-badge.png"
  printf '\n\033[1;32mdraft %s\033[0m (%s)  Show it to the creator, then ask for approval of the real render.\n' \
    "$DRAFT_OUT" "$(du -h "$DRAFT_OUT" | cut -f1)"
  exit 0
fi

if [ "$RENDER" -eq 1 ]; then
  say "render gate: a current human approval is required"
  python3 scripts/approve_reel.py "$NAME" --check
  if [ -n "${AVS_HOME:-}" ] && [ -f "$OUT" ]; then   # a member's re-render lands next to the one before it (v2, v3), never over it
    n=2; while [ -f "out/${NAME}-v${n}.mp4" ]; do n=$((n+1)); done; OUT="out/${NAME}-v${n}.mp4"
  fi
  say "6/7  render ($ENGINE) -> $OUT"
  python3 scripts/color_lut.py "$NAME"; "$MATTE_PY" scripts/matte_reel.py "$NAME"   # back-text cutouts (reused when the cut is unchanged)
    stage_public hi
    render_checked "qa/${NAME}/render.log" src/methodology/index.ts "$NAME" "out/${NAME}-picture.mp4" --muted --crf=18 --public-dir="$PUB" --timeout=180000
    rm -rf "$PUB"
  say "     mix + master: narration from the cut, your sounds.json effects, -14 LUFS, true peak <= -1 dBTP"
  python3 scripts/mix_master.py "$NAME" "out/${NAME}-picture.mp4" "$OUT"
  mv "out/${NAME}-picture.mp4" "qa/${NAME}/picture.mp4"
  say "7/7  verify the render"
  if ! "$MATTE_PY" scripts/verify_reel.py "$NAME" "$OUT"; then   # its own venv has numpy, for the audio drift check
    if [ -n "${AVS_HOME:-}" ]; then   # a member's failed render steps aside, so the render after the fix takes the same name
      mv "$OUT" "qa/${NAME}/failed-$(basename "$OUT")"
      echo "RENDER FAILED CHECKS: fix what the FAIL lines name, then render again (the failed file is qa/${NAME}/failed-$(basename "$OUT"))"
    fi
    exit 1
  fi
  python3 scripts/verify_brightness.py "$OUT" || true
  say "     cut sheets: the frames around every visual change, checked for flashes and wrong frames"
  python3 scripts/verify_cuts.py "$NAME" "$OUT" || echo "  cut sheets FAILED: read qa/${NAME}/cuts/ before delivering"
  python3 scripts/extract_reel_stills.py "$NAME" "$OUT"
  OUTSTEM=$(basename "$OUT" .mp4)
  say "     companion pack: covers + static ads from the same config -> out/${OUTSTEM}-companions/"
  python3 scripts/companions.py "$NAME" "$OUTSTEM"   # a re-render keeps the first version's pack too
  echo "RENDERED $OUT"
  printf '\n\033[1;32mrendered %s\033[0m  The gates are not the edit: look at qa/%s/stills/sheet.png and watch it once, sound on.\n' "$OUT" "$NAME"
  exit 0
fi

# a DIFFERENT raw can be older than the cached input (camera clips keep their shoot date), so
# freshness alone is not enough: the input remembers which raw it came from
# the video given must be the recording, never AVS's own normalized copy of it: the checks below would delete that copy
if [ -f "$SRC" ] && [ "$(cd "$(dirname "$RAW")" && pwd -P)/$(basename "$RAW")" = "$(cd "$(dirname "$SRC")" && pwd -P)/$(basename "$SRC")" ]; then
  echo "error: ${SRC} is AVS's own copy of the video, not the recording. Give the original video (the one in the inbox, or inbox/done/${NAME}/). Nothing was changed."; exit 1
fi
STAMP="inputs/${NAME}.source"
RAWID="$(cd "$(dirname "$RAW")" && pwd)/$(basename "$RAW")|$(stat -f %z "$RAW")"
OLDID="$(cat "$STAMP" 2>/dev/null || true)"   # same file name and size = the same raw, even moved (inbox -> inbox/done)
if [ -f "$SRC" ] && [ -f "$STAMP" ] && [ "${OLDID##*/}" != "${RAWID##*/}" ]; then say "new raw for ${NAME}: discarding the cached input"; rm -f "$SRC"; fi
if [ -n "$UNMIRROR" ] && [ -f "$SRC" ] && [ -f "qa/${NAME}/source.json" ]; then   # --unmirror asked after the first build: flip it now
  WAS=$(python3 -c "import json; print('yes' if json.load(open('qa/${NAME}/source.json')).get('unmirrored') else 'no')")
  [ "$WAS" = no ] && { say "flipping ${NAME} (text in the shot read backwards): rebuilding the input"; rm -f "$SRC"; }
fi
if [ -f "$SRC" ] && [ -f "$STAMP" ] && [ "$OLDID" != "$RAWID" ] && [ "${OLDID##*/}" = "${RAWID##*/}" ]; then
  # the same recording, moved (inbox -> inbox/done): point the records at its new place so the full-resolution twin keeps working
  echo "$RAWID" > "$STAMP"
  [ -f "qa/${NAME}/source.json" ] && python3 -c "import json,sys; p='qa/${NAME}/source.json'; d=json.load(open(p)); d['raw']=sys.argv[1]; json.dump(d,open(p,'w'),indent=1)" "$(cd "$(dirname "$RAW")" && pwd)/$(basename "$RAW")"
fi
[ -f "$SRC" ] && [ ! -f "$STAMP" ] && echo "$RAWID" > "$STAMP"   # reels built before the stamp adopt their raw
newer "$SRC" "$RAW" || { say "0/5  normalize -> $SRC (1080x1920, 30 fps CFR, one AAC track)"; python3 scripts/normalize_source.py "$RAW" "$SRC" $UNMIRROR $REFRAME && echo "$RAWID" > "$STAMP"; }
if [ -n "$OUTDOOR" ]; then FASTFLAG=""; else FASTFLAG="--fast"; fi   # outdoor needs precise word edges on the raw
PRECISE="script/word-timings/${NAME}-wx.precise"   # marks a transcript made by the precise (outdoor) pass
if [ -n "$OUTDOOR" ] && [ -f "$WX" ] && [ ! -f "$PRECISE" ]; then   # --outdoor after a quick transcript: the precise pass has to run
  say "--outdoor: the transcript on disk is the quick one, making the precise one"; rm -f "$WX"
fi
newer "$WX" "$SRC" || { say "1/5  transcribe ${FASTFLAG:-(precise, outdoor)}"; rm -f "$PRECISE"; "$WHISPERX" scripts/word_align_x.py "$SRC" $FASTFLAG && { [ -n "$FASTFLAG" ] || touch "$PRECISE"; }; }
TRIMS="script/word-timings/${NAME}-trims.json"; PICKS="script/word-timings/${NAME}-takepicks.json"   # newer() is true while one is absent
if [ -n "$TAKES" ] || ! newer "$CUT" "$WX" || ! newer "$CUT" "script/${NAME}.txt" || ! newer "$CUT" "$TRIMS" || ! newer "$CUT" "$PICKS"; then
  say "2/5  last take: keep the last clean take of each sentence, cut in silence -> $CUT"
  python3 scripts/last_take.py "$SRC" --words "$WX" --script "script/${NAME}.txt" --out "$CUT" \
    --report "script/${NAME}-takes.md" --json "script/word-timings/${NAME}-takes.json" $OUTDOOR $TAKES
fi
if ! newer "$CUTWX" "$CUT"; then
  say "3/5  whisperX align the cut, tighten loose joins, re-align (10-20ms word times)"
  "$WHISPERX" scripts/word_align_x.py "$CUT"
  REFINE=$(python3 scripts/last_take.py "$SRC" --words "$WX" --script "script/${NAME}.txt" --out "$CUT" \
    --report "script/${NAME}-takes.md" --json "script/word-timings/${NAME}-takes.json" $OUTDOOR $TAKES --refine "$CUTWX")
  echo "$REFINE"
  case "$REFINE" in *"no re-cut"*) ;; *) "$WHISPERX" scripts/word_align_x.py "$CUT";; esac
fi
say "     full-resolution cut from the original recording, so punch-ins and zooms stay sharp"
python3 scripts/hires_cut.py "$NAME" || echo "  hi-res cut unavailable: the render uses the 1080p cut"
say "     seam check: stray sound or dead air at cut joins, head and tail"
python3 scripts/verify_seams.py "$NAME" || echo "  seam check FAILED: see qa/${NAME}/seams.json (the scene map will say NOT READY)"
say "4/5  config -> $CFG"
if [ -n "$FACE" ]; then python3 scripts/gen_reel_config.py "$NAME" --face "$FACE" $REGEN $PAID; else python3 scripts/gen_reel_config.py "$NAME" $REGEN $PAID; fi
say "5/5  scene map -> $MAP"
python3 scripts/scene_map.py "$NAME" || true   # also checks the keyword and writes script/${NAME}-post.md
node scripts/test_layout.mjs "$NAME" || true
if [ "$PREVIEW" -eq 1 ]; then python3 scripts/color_lut.py "$NAME"; "$MATTE_PY" scripts/matte_reel.py "$NAME"; python3 scripts/extract_reel_stills.py "$NAME" --preview; python3 scripts/storyboard.py "$NAME"; fi
printf '\n\033[1;36mSTOPPED before render, by design.\033[0m Read %s.\n' "$MAP"
printf 'Edit only scenes / swaps / big flags / copy in %s, then re-run this command (the config is kept).\n' "$CFG"
printf 'When the human approves:  python3 scripts/approve_reel.py %s --by "<name>"  then  scripts/make_reel.sh %s %s --render\n' "$NAME" "$RAW" "$NAME"

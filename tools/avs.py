#!/usr/bin/env python3
"""AdCamp Video System launcher, for a Mac and a Windows PC. Standard library only, run by AVS's own Python
through the avs (Mac) or avs.cmd (Windows) file in the AVS folder.

    avs install --step <name> [options]   run ONE setup step (each is safe to re-run, a finished one is skipped)
    avs install --all [options]           every step, in order
    avs install --list                    the steps and their download sizes
    avs preflight                         can this computer run AVS? (no download)
    avs doctor                            what is installed and what is missing (changes nothing)
    avs report                            a plain-text report for support, saved on the Desktop
    avs reel <video> <name> [options]     cut, preview, draft or render a video (avs reel --help)
    avs run <script> [args]               an engine script with the Python or Node it needs
    avs open inbox | out | coach          the folder in Finder (Mac) or File Explorer (PC), or a file or page
    avs flag installed|local-pages [--off]   setup finished / pages in the browser instead of beside the chat
    avs backup-config <name>              save a video's config inside the install before a fix
    avs words <transcript json>           what was said, as plain text
    avs inbox-done <name> <file> [...]    move a finished video's files into inbox/done/<name>/
    avs clean <name>                      free a finished video's working files (they rebuild if needed)
    avs phone-copy out/<file>.mp4         a small copy for watching in the chat
    avs ffprobe <args> / avs ffmpeg <args>   AVS's own ffprobe and ffmpeg
  avs run takes @file=<path> as one argument holding that file's text (JSON, quoted words).
    avs smoke                             the install test: the sample video, then every tool
    avs update --check | --latest | <zip or folder>    a newer AVS, keeping your reels, brand and music
    avs uninstall [--yes] [--delete-videos]           remove AVS, your finished videos copied out first

Options for install: --accent '#RRGGBB' --sans <name> --serif <name> --handle @you --name 'Your Name'
  --avatar <photo> --skill-dir <folder> (default ~/.claude/skills)
On Windows never pass text with quotes in it on the command line (Windows PowerShell 5.1 splits it): put it in a file.
"""
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import time
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import avs_platform as P  # noqa: E402

AVS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RT = os.path.join(AVS, 'runtime')
ENG = os.path.join(AVS, 'engine')
BIN = os.path.join(RT, 'bin')
LOGS = os.path.join(RT, 'logs')
UVX = os.path.join(BIN, 'uv' + P.EXE)
WHISPERX, MATTE, YTDLP_VENV = os.path.join(RT, 'whisperx'), os.path.join(RT, 'matte'), os.path.join(RT, 'ytdlp')
MODELS = os.path.join(RT, 'models')
REMOTION = os.path.join(ENG, 'node_modules', '@remotion', 'cli', 'remotion-cli.js')
FONTS_SANS = ('hanken', 'inter', 'montserrat', 'dmsans', 'poppins')
FONTS_SERIF = ('playfair', 'instrument', 'dmserif', 'fraunces')

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')


class Fail(Exception):
    """A step that could not finish: the message is what the person is told."""


def say(s):
    print('\n== ' + s, flush=True)


def ok(s):
    print('  OK ' + s, flush=True)


def note(s):
    print('  note: ' + s, flush=True)


def env():
    """The environment every AVS program runs with: its own tools first on PATH, the model folders, no usage pings."""
    e = dict(os.environ)
    nodedir = os.path.dirname(P.node_exe(RT))
    first = [nodedir, BIN, P.venv_bin(YTDLP_VENV)] if P.WIN else [nodedir, BIN]
    rest = [x for x in e.get('PATH', '').split(os.pathsep) if x and x not in first]
    e['PATH'] = os.pathsep.join(first + rest)
    e.update({'AVS_HOME': AVS, 'AVS_PYTHON': P.venv_python(WHISPERX), 'AVS_MATTE_PYTHON': P.venv_python(MATTE),
              'AVS_MODELS': os.path.join(MODELS, 'mediapipe'), 'HF_HOME': os.path.join(MODELS, 'hf'),
              'TORCH_HOME': os.path.join(MODELS, 'torch'), 'UV_PYTHON_INSTALL_DIR': os.path.join(RT, 'python'),
              'UV_CACHE_DIR': os.path.join(RT, 'uv-cache'), 'npm_config_cache': os.path.join(RT, 'npm-cache'), 'PYTHONUTF8': '1', 'PYANNOTE_METRICS_ENABLED': '0',
              'HF_HUB_DISABLE_TELEMETRY': '1'})
    return e


def run(cmd, step, cwd=None, check=True):
    """Run a program with the AVS environment, its output kept in runtime/logs/<step>.log. On failure: the last lines."""
    os.makedirs(LOGS, exist_ok=True)
    log = os.path.join(LOGS, step + '.log')
    with open(log, 'a', encoding='utf-8', errors='replace') as f:
        f.write('\n$ %s\n' % ' '.join(cmd))
        f.flush()
        p = subprocess.run(cmd, cwd=cwd, env=env(), stdout=f, stderr=subprocess.STDOUT)
    if check and p.returncode != 0:
        tail = open(log, encoding='utf-8', errors='replace').read().strip().splitlines()[-8:]
        raise Fail('%s stopped (code %d). Last lines of runtime/logs/%s.log:\n    %s' % (os.path.basename(cmd[0]), p.returncode, step, '\n    '.join(tail)))
    return p.returncode


def output(cmd, cwd=None):
    try:
        return subprocess.run(cmd, cwd=cwd, env=env(), capture_output=True, text=True, encoding='utf-8', errors='replace').stdout.strip()
    except OSError:
        return ''


def sha256(path):
    import hashlib
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def fetch(url, dst, sha=None, step='download'):
    """Download with curl (on Windows since 10 1803, on every Mac), retried, then the checksum. A bad file is removed."""
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if sha and os.path.exists(dst) and sha256(dst) == sha:
        return dst
    if run([P.curl(), '-fL', '--retry', '3', '--retry-delay', '3', '-sS', '-o', dst, url], step, check=False) != 0:
        raise Fail('the download failed: %s. Check the internet connection and run this step again.' % url)
    if sha and sha256(dst) != sha:
        os.remove(dst)
        raise Fail('the download of %s did not match its checksum, so it was not used. Run this step again.' % os.path.basename(dst))
    return dst


def unpack(archive, into):
    os.makedirs(into, exist_ok=True)
    if archive.endswith('.zip'):
        with zipfile.ZipFile(archive) as z:
            z.extractall(into)
    else:
        with tarfile.open(archive) as t:
            t.extractall(into, filter='data')


def uv(*a, step):
    return run([UVX] + list(a), step)


# ---- steps ----------------------------------------------------------------------------------------------------

def step_check(a):
    say('check: this computer')
    name, ver, words = P.system()
    chip = P.native_machine()
    if P.WIN:
        if chip == 'arm64':
            raise Fail('this PC has an ARM chip (like a Snapdragon laptop). AVS for Windows needs an Intel or AMD PC for now.')
        if ver[2] < 17763:
            raise Fail('%s is too old. AVS needs Windows 10 version 1809 or newer.' % words)
        ok('%s, %s chip' % (words, 'Intel or AMD'))
        missing = P.cpp_runtime_missing()
        if missing:
            raise Fail('this PC is missing Microsoft\'s free Visual C++ runtime (%s), which the speech and cutout libraries need. '
                       'Install it once from %s (it asks for an administrator), then run this step again.' % (', '.join(missing), P.CPP_RUNTIME_URL))
        ok('Microsoft C++ runtime present')
        for t in ('curl.exe', 'tar.exe'):
            if not shutil.which(t):
                raise Fail('%s is missing from Windows. AVS needs Windows 10 version 1803 or newer with its built-in tools.' % t)
    elif P.MAC:
        if ver[0] < 12:
            raise Fail('%s is too old. AVS needs macOS 12 (Monterey) or newer.' % words)
        ok('%s, %s' % (words, 'Apple chip' if chip == 'arm64' else 'Intel chip: slower, uses the Intel library set'))
    else:
        raise Fail('AVS runs on a Mac or a Windows PC, not on %s.' % name)
    need = 6 if os.path.isdir(os.path.join(RT, 'python')) else 12   # a stopped install already took its downloads' space
    free = P.free_gb(AVS)
    if free < need:
        raise Fail('only %.0f GB free. AVS needs about %d GB free here (downloads plus working space).' % (free, need))
    ok('free disk: %.0f GB' % free)
    ram = P.ram_gb()
    ok('memory: %.0f GB' % ram)
    if 0 < ram < 15:
        note('under 16 GB of memory: renders take longer.')
    if any(ord(c) > 127 for c in AVS):
        note('the AVS folder path has a letter outside plain English (%s). If a step fails over it, tell Chris.' % AVS)
    return '%s, %s, %.0f GB free, %.0f GB memory' % (words, chip, free, ram)


def step_uv(a):
    say('uv: the Python manager')
    if os.path.exists(UVX):
        ok(output([UVX, '--version']) + ' already in runtime/bin')
        return 'present'
    url, sha = P.UV[P.key()]
    arc = fetch(url, os.path.join(RT, 'dl', os.path.basename(url)), sha, 'uv')
    tmp = os.path.join(RT, 'dl', 'uv-unpack')
    unpack(arc, tmp)
    os.makedirs(BIN, exist_ok=True)
    for dp, _, fs in os.walk(tmp):
        for f in fs:
            if f in ('uv' + P.EXE, 'uvx' + P.EXE):
                shutil.copy2(os.path.join(dp, f), os.path.join(BIN, f))
    shutil.rmtree(tmp, ignore_errors=True)
    os.remove(arc)
    ok(output([UVX, '--version']) + ' in runtime/bin')
    return 'installed'


def step_python(a):
    say('python: Python %s (private to AVS)' % P.PY_VERSION)
    uv('python', 'install', P.PY_VERSION, '--no-bin', step='python')
    py = output([UVX, 'python', 'find', P.PY_VERSION, '--managed-python'])   # AVS's own, never one the computer had
    if not py:
        raise Fail('Python %s did not install. Run this step again.' % P.PY_VERSION)
    ok('%s at %s' % (output([py, '--version']), os.path.relpath(py, AVS)))
    return py


def node_ok():
    n = P.node_exe(RT)
    return os.path.exists(n) and output([n, '-p', 'process.versions.node.split(".")[0]']).isdigit()


def step_node(a):
    say('node: Node.js (runs the video renderer)')
    if node_ok():
        ok('Node %s already in runtime/node' % output([P.node_exe(RT), '-v']))
        return 'present'
    url, sha = P.NODE[P.key()]
    arc = fetch(url, os.path.join(RT, 'dl', os.path.basename(url)), sha, 'node')
    tmp = os.path.join(RT, 'dl', 'node-unpack')
    shutil.rmtree(tmp, ignore_errors=True)
    unpack(arc, tmp)
    top = os.path.join(tmp, os.listdir(tmp)[0])
    shutil.rmtree(os.path.join(RT, 'node'), ignore_errors=True)
    shutil.move(top, os.path.join(RT, 'node'))
    shutil.rmtree(tmp, ignore_errors=True)
    os.remove(arc)
    if not node_ok():
        raise Fail('Node did not start after install. Run this step again.')
    ok('Node %s in runtime/node' % output([P.node_exe(RT), '-v']))
    return 'installed'


def ffmpeg_ok():
    ff = os.path.join(BIN, 'ffmpeg' + P.EXE)
    if not (os.path.exists(ff) and os.path.exists(os.path.join(BIN, 'ffprobe' + P.EXE))):
        if P.WIN or not (shutil.which('ffmpeg') and shutil.which('ffprobe')):
            return False
        ff = shutil.which('ffmpeg')   # a Mac may already have a capable one, as install.sh allowed
    enc = output([ff, '-hide_banner', '-encoders'])
    return 'libx264' in enc and 'libvpx-vp9' in enc


def step_ffmpeg(a):
    say('ffmpeg: video and audio tools')
    if ffmpeg_ok():
        ok('a capable ffmpeg is already there')
        return 'present'
    os.makedirs(BIN, exist_ok=True)
    if P.WIN:
        url, sha = P.FFMPEG['win-x64']
        arc = fetch(url, os.path.join(RT, 'dl', os.path.basename(url)), sha, 'ffmpeg')
        tmp = os.path.join(RT, 'dl', 'ffmpeg-unpack')
        unpack(arc, tmp)
        for dp, _, fs in os.walk(tmp):
            for f in ('ffmpeg.exe', 'ffprobe.exe'):
                if f in fs:
                    shutil.copy2(os.path.join(dp, f), os.path.join(BIN, f))
        shutil.rmtree(tmp, ignore_errors=True)
        os.remove(arc)
    else:
        arch = 'arm64' if P.native_machine() == 'arm64' else 'amd64'
        for t in ('ffmpeg', 'ffprobe'):
            z = fetch('https://ffmpeg.martin-riedl.de/redirect/latest/macos/%s/release/%s.zip' % (arch, t), os.path.join(RT, 'dl', t + '.zip'), None, 'ffmpeg')
            unpack(z, BIN)
            os.chmod(os.path.join(BIN, t), 0o755)
            os.remove(z)
    if not ffmpeg_ok():
        raise Fail('ffmpeg installed but is missing an encoder AVS needs. Run this step again.')
    ok(output([os.path.join(BIN, 'ffmpeg' + P.EXE), '-hide_banner', '-version']).splitlines()[0][:60])
    return 'installed'


def step_npm(a):
    say('npm: the video renderer (Remotion) and its packages')
    if not node_ok():
        raise Fail('run the node step first.')
    lock, mark = os.path.join(ENG, 'package-lock.json'), os.path.join(ENG, 'node_modules', '.avs-lock')
    if os.path.isdir(os.path.join(ENG, 'node_modules', 'remotion')) and os.path.exists(mark) and open(lock, 'rb').read() == open(mark, 'rb').read():
        ok('renderer packages already installed')
        return 'present'
    run([P.node_exe(RT), P.npm_cli(RT), 'ci', '--no-audit', '--no-fund', '--loglevel=error'], 'npm', cwd=ENG)
    shutil.copy2(lock, mark)
    shutil.rmtree(os.path.join(RT, 'npm-cache'), ignore_errors=True)   # npm's download cache, never needed again
    ok('renderer packages installed in engine/node_modules')
    return 'installed'


def step_browser(a):
    say('browser: the headless Chrome the renderer draws frames with')
    run([P.node_exe(RT), REMOTION, 'browser', 'ensure'], 'browser', cwd=ENG)
    ok('renderer browser ready')
    return 'ready'


def step_still(a):
    say('still: one test image from the renderer, before the big downloads')
    out = os.path.join(ENG, 'out', 'setup-check.png')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    run([P.node_exe(RT), REMOTION, 'still', 'src/methodology/index.ts', 'FontSheet', out, '--log=error'], 'still', cwd=ENG)
    if not os.path.exists(out) or os.path.getsize(out) < 10000:
        raise Fail('the renderer ran but drew no image. Run this step again, and if it fails twice tell Chris.')
    ok('the renderer drew engine/out/setup-check.png')
    return 'drawn'


def requirements():
    if P.MAC and P.native_machine() != 'arm64':
        return os.path.join(ENG, 'scripts', 'requirements-intel.txt')
    return os.path.join(ENG, 'scripts', 'requirements-apple.txt')   # the pinned set; Windows Phase 0 ran it as is


def step_venv(a):
    say('venv: speech-to-text and word alignment libraries')
    py = P.venv_python(WHISPERX)
    if not os.path.exists(py):
        uv('venv', WHISPERX, '--python', P.PY_VERSION, '--managed-python', step='venv')
    uv('pip', 'install', '--python', py, '-r', requirements(), step='venv')
    if run([py, '-c', "import whisperx, torch, faster_whisper; print('whisperx ok, torch', torch.__version__)"], 'venv', check=False):
        raise Fail('the speech libraries did not import. Run this step again.')
    run([UVX, 'cache', 'clean'], 'venv', check=False)   # the download cache is about 1 GB and never needed again
    ok('speech libraries installed in runtime/whisperx')
    return 'installed'


MODELS_PY = '''
from faster_whisper import WhisperModel
for m in ('base', 'small'):
    WhisperModel(m, device='cpu', compute_type='int8'); print('  speech model', m, 'ready')
import whisperx
whisperx.load_align_model(language_code='en', device='cpu'); print('  word-alignment model ready')
whisperx.load_model('base', 'cpu', compute_type='int8'); print('  voice-activity model ready')
'''


def step_models(a):
    say('models: speech (faster-whisper base and small) and word alignment (wav2vec2)')
    py = P.venv_python(WHISPERX)
    if not os.path.exists(py):
        raise Fail('run the venv step first.')
    for attempt in (1, 2):   # shared download hosts sometimes refuse a burst: one retry
        if run([py, '-c', MODELS_PY], 'models', check=False) == 0:
            break
        if attempt == 2:
            raise Fail('a speech model did not download. Check the internet connection and run this step again.')
        time.sleep(20)
    ok('models cached in runtime/models')
    return 'cached'


def step_cutout(a):
    say('cutout: the person-cutout library (MediaPipe) and its model')
    py = P.venv_python(MATTE)
    if not os.path.exists(py):
        uv('venv', MATTE, '--python', P.PY_VERSION, '--managed-python', step='cutout')
    uv('pip', 'install', '--python', py, 'mediapipe==' + P.MEDIAPIPE, step='cutout')
    if run([py, '-c', 'import mediapipe'], 'cutout', check=False):
        raise Fail('MediaPipe did not import. Run this step again.')
    url, sha = P.CUTOUT_MODEL
    fetch(url, os.path.join(MODELS, 'mediapipe', 'selfie_multiclass_256x256.tflite'), sha, 'cutout')
    ok('cutout library in runtime/matte, model in runtime/models/mediapipe (checksum verified)')
    return 'installed'


def step_ytdlp(a):
    say('ytdlp: the downloader that brings in reels you like, to build a style from them')
    if P.WIN:   # a Python package, not the packed yt-dlp.exe that antivirus often flags
        exe = os.path.join(P.venv_bin(YTDLP_VENV), 'yt-dlp.exe')
        if not os.path.exists(exe):
            uv('venv', YTDLP_VENV, '--python', P.PY_VERSION, '--managed-python', step='ytdlp')
            uv('pip', 'install', '--python', P.venv_python(YTDLP_VENV), 'yt-dlp==' + P.YTDLP, step='ytdlp')
    else:
        exe = os.path.join(BIN, 'yt-dlp')
        if not os.path.exists(exe):
            url, sha = P.YTDLP_MAC
            fetch(url, exe, sha, 'ytdlp')
            os.chmod(exe, 0o755)
    v = output([exe, '--version'])
    if not v:
        raise Fail('the reel downloader did not start. It is optional: AVS works without it, you can drop video files in instead.')
    ok('yt-dlp %s' % v)
    return v


def step_brand(a):
    say('brand: your accent color, fonts, and the follow card\'s name, handle and photo')
    p = os.path.join(ENG, 'src', 'brand.json')
    b = json.load(open(p, encoding='utf-8'))
    if a.avatar:
        if not os.path.isfile(a.avatar):
            raise Fail('no such photo: %s' % a.avatar)
        src = a.avatar
        if src.lower().endswith(('.heic', '.heif')) and P.MAC:   # iPhone photos: the Mac's own sips makes a plain image first
            import tempfile
            tmp = os.path.join(tempfile.mkdtemp(), 'photo.png')
            run(['sips', '-s', 'format', 'png', src, '--out', tmp], 'brand')
            src = tmp
        dst = os.path.join(ENG, 'public', 'inserts', 'avatar.png')
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if run([os.path.join(BIN, 'ffmpeg' + P.EXE) if os.path.exists(os.path.join(BIN, 'ffmpeg' + P.EXE)) else 'ffmpeg', '-y', '-loglevel', 'error',
                '-i', src, '-vf', "crop='min(iw,ih)':'min(iw,ih)',scale=400:400", '-frames:v', '1', dst], 'brand', check=False):
            raise Fail('that photo could not be read%s. Send a JPG or PNG instead.' % (' (an iPhone HEIC file)' if src.lower().endswith(('.heic', '.heif')) else ''))
        b['avatar'] = 'inserts/avatar.png'
        ok('photo saved as public/inserts/avatar.png')
    if a.handle:
        b['handle'] = a.handle if a.handle.startswith('@') else '@' + a.handle
    if a.name:
        b['name'] = a.name
    if a.accent:
        if not re.fullmatch(r'#?[0-9A-Fa-f]{6}', a.accent):
            raise Fail('the accent must be a hex color like #F7C715.')
        b['accent'] = '#' + a.accent.lstrip('#').upper()
        rgb = [int(b['accent'][i:i + 2], 16) / 255 for i in (1, 3, 5)]
        lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
        if 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2] < 0.15:
            note('a dark color. Words and graphics over your video and photos use a lighter shade of it so they stay readable. Light slides keep it exactly.')
    if a.sans:
        if a.sans not in FONTS_SANS:
            raise Fail('sans must be one of: %s.' % ', '.join(FONTS_SANS))
        b['sans'] = a.sans
    if a.serif:
        if a.serif not in FONTS_SERIF:
            raise Fail('serif must be one of: %s.' % ', '.join(FONTS_SERIF))
        b['serif'] = a.serif
    json.dump(b, open(p, 'w', encoding='utf-8'), indent=2)
    ok('accent %s, sans %s, serif %s, follow card: %s %s' % (b['accent'], b['sans'], b['serif'], b.get('name') or '(no name yet)', b.get('handle') or ''))
    return b['accent']


def step_env(a):
    say('env: the paths every AVS program uses')
    keep = ('AVS_HOME', 'AVS_PYTHON', 'AVS_MATTE_PYTHON', 'AVS_MODELS', 'HF_HOME', 'TORCH_HOME', 'UV_PYTHON_INSTALL_DIR',
            'PYANNOTE_METRICS_ENABLED', 'HF_HUB_DISABLE_TELEMETRY', 'PYTHONUTF8')
    e = env()
    d = {k: e[k] for k in keep}
    d['PATH_FIRST'] = e['PATH'].split(os.pathsep)[:3]
    json.dump(d, open(os.path.join(RT, 'env.json'), 'w', encoding='utf-8'), indent=1)
    if P.MAC:   # the Mac engine scripts and skill still load env.sh until the two lines merge
        lines = ['# written by the AVS launcher: every AVS script loads this',
                 'export PATH="%s:%s:$PATH"' % (os.path.dirname(P.node_exe(RT)) if node_ok() else os.path.dirname(shutil.which('node') or ''), BIN)]
        lines += ['export %s="%s"' % (k, d[k]) for k in keep if k != 'PYTHONUTF8']
        open(os.path.join(RT, 'env.sh'), 'w').write('\n'.join(lines) + '\n')
    ok('runtime/env.json written' + (' (and runtime/env.sh)' if P.MAC else ''))
    return 'written'


def step_skill(a):
    sd = a.skill_dir or os.path.join(os.path.expanduser('~'), '.claude', 'skills')
    if os.path.exists(os.path.join(RT, '.via-plugin')):
        say('skill: comes from the AVS plugin')
        old = os.path.join(sd, 'avs', 'SKILL.md')
        if os.path.exists(old) and 'AdCamp Video System' in open(old, encoding='utf-8', errors='replace').read():
            shutil.rmtree(os.path.dirname(old), ignore_errors=True)   # an older copy would answer "make a reel" twice
        ok('the plugin provides the skill. In a NEW Claude Code session, say: make a reel')
    else:
        say('skill: Claude Code skill "avs" -> %s' % os.path.join(sd, 'avs'))
        os.makedirs(os.path.join(sd, 'avs'), exist_ok=True)
        shutil.copy2(os.path.join(AVS, 'skills', 'avs', 'SKILL.md'), os.path.join(sd, 'avs', 'SKILL.md'))
        ok('skill installed. In a NEW Claude Code session, say: make a reel')
    # AVS's own cue sounds: switch on any empty role, once (a role turned off afterwards stays off)
    p = os.path.join(ENG, 'sounds.json')
    try:
        d = json.load(open(p, encoding='utf-8'))
        roles = (('transition_whoosh', 'whoosh'), ('element_land', 'land'), ('state_change', 'click'), ('back_text_hit', 'impact'),
                 ('insert_pop', 'pop'), ('cta_ding', 'ding'), ('cta_riser', 'riser'))
        offered = d.get('_sfx_offered')
        offered = set(offered) if isinstance(offered, list) else ({'transition_whoosh', 'element_land', 'state_change'} if offered else set())
        on = []
        for role, f in roles:
            rel = 'sounds/sfx/%s.wav' % f
            if role not in offered and not d.get(role) and os.path.exists(os.path.join(ENG, rel)):
                d[role] = rel
                on.append(f)
            offered.add(role)
        d['_sfx_offered'] = sorted(offered)
        json.dump(d, open(p, 'w', encoding='utf-8'), indent=2)
        if on:
            print("Sound effects switched on: %s (AVS's own sounds). Set a role to null in engine/sounds.json to turn one off." % ', '.join(on))
    except (OSError, ValueError):
        pass
    return 'installed'


STEPS = [   # name, what, size. Cheap and likely-to-fail first, so a problem shows in minutes, not after an hour
    ('check', 'this computer: chip, system, disk, memory (on a PC: the Microsoft C++ runtime)', 'no download'),
    ('uv', 'the uv Python manager into runtime/bin', '~20 MB'),
    ('python', 'Python 3.12 into runtime/python', '~30 MB'),
    ('node', 'Node.js 22 into runtime/node', '~30 MB'),
    ('ffmpeg', 'ffmpeg and ffprobe into runtime/bin', '~110 MB'),
    ('npm', 'the video renderer\'s packages into engine/node_modules', '~450 MB'),
    ('browser', 'the headless Chrome the renderer draws with', '~175 MB'),
    ('still', 'one test image from the renderer', 'no download'),
    ('venv', 'speech libraries into runtime/whisperx', '~1.8 GB, 3-10 min'),
    ('models', 'speech models into runtime/models', '~1 GB'),
    ('cutout', 'the person-cutout library and model into runtime/matte', '~200 MB'),
    ('ytdlp', 'the reel downloader (optional)', '~5-40 MB'),
    ('brand', 'engine/src/brand.json: --accent --sans --serif [--handle --name --avatar]', 'no download'),
    ('env', 'runtime/env.json, the paths every AVS program uses', 'no download'),
    ('skill', 'the Claude Code skill "avs"', 'no download'),
]


def log_step(name, good, secs, text):
    os.makedirs(RT, exist_ok=True)
    with open(os.path.join(RT, 'steps.log'), 'a', encoding='utf-8') as f:
        f.write(json.dumps({'time': datetime.datetime.now().isoformat(timespec='seconds'), 'step': name, 'ok': good,
                            'seconds': round(secs), 'note': str(text)[:500]}) + '\n')


def do_step(name, a):
    t0 = time.time()
    try:
        r = globals()['step_' + name](a)
        log_step(name, True, time.time() - t0, r)
        return True
    except Fail as e:
        log_step(name, False, time.time() - t0, e)
        print('  FAILED %s' % e, flush=True)
        return False


def install(a):
    names = [s[0] for s in STEPS]
    if a.list:
        for n, what, size in STEPS:
            print('  %-8s %s (%s)' % (n, what, size))
        return 0
    if a.step:
        if a.step not in names:
            print('no step "%s". The steps: %s' % (a.step, ', '.join(names)))
            return 2
        return 0 if do_step(a.step, a) else 1
    if a.all:
        for n in names:
            if not do_step(n, a):
                print('\nSetup stopped at "%s". Fix what it says, then run: install --step %s, and carry on from there.' % (n, n))
                return 1
        print('\nSetup finished. Next: the test video.')
        return 0
    print(__doc__)
    return 2


def rows():
    """(name, good, detail) for the checkup."""
    r = []
    free = P.free_gb(AVS)
    r.append(('disk', free >= 5, '%.0f GB free%s' % (free, '' if free >= 5 else ' (keep 5+ GB for renders)')))
    if P.WIN:
        m = P.cpp_runtime_missing()
        r.append(('C++ runtime', not m, 'present' if not m else 'missing %s: install %s' % (', '.join(m), P.CPP_RUNTIME_URL)))
    r.append(('node', node_ok(), output([P.node_exe(RT), '-v']) if node_ok() else 'run: install --step node'))
    r.append(('ffmpeg', ffmpeg_ok(), 'libx264, libvpx-vp9' if ffmpeg_ok() else 'run: install --step ffmpeg'))
    r.append(('uv', os.path.exists(UVX), output([UVX, '--version']) if os.path.exists(UVX) else 'run: install --step uv'))
    py = output([UVX, 'python', 'find', P.PY_VERSION, '--managed-python']) if os.path.exists(UVX) else ''
    r.append(('python', bool(py), output([py, '--version']) if py else 'run: install --step python'))
    sp = P.venv_python(WHISPERX)
    t = output([sp, '-c', 'import whisperx, torch; print(torch.__version__)']) if os.path.exists(sp) else ''
    r.append(('speech libraries', bool(t), 'torch ' + t.splitlines()[-1] if t else 'run: install --step venv'))
    rem = os.path.join(ENG, 'node_modules', 'remotion', 'package.json')
    r.append(('renderer', os.path.exists(rem), 'Remotion ' + json.load(open(rem))['version'] if os.path.exists(rem) else 'run: install --step npm'))
    hub = os.path.join(MODELS, 'hf', 'hub')
    sm = os.path.isdir(hub) and any('faster-whisper-small' in d for d in os.listdir(hub))
    r.append(('speech models', sm, 'faster-whisper base + small' if sm else 'run: install --step models'))
    mp = P.venv_python(MATTE)
    cut = os.path.exists(mp) and output([mp, '-c', 'import mediapipe; print(1)']) == '1' and \
        os.path.exists(os.path.join(MODELS, 'mediapipe', 'selfie_multiclass_256x256.tflite'))
    r.append(('cutout', cut, 'MediaPipe segmenter + model' if cut else 'run: install --step cutout'))
    r.append(('env', os.path.exists(os.path.join(RT, 'env.json')), 'runtime/env.json' if os.path.exists(os.path.join(RT, 'env.json')) else 'run: install --step env'))
    yd = os.path.join(P.venv_bin(YTDLP_VENV), 'yt-dlp.exe') if P.WIN else os.path.join(BIN, 'yt-dlp')
    yv = output([yd, '--version']) if os.path.exists(yd) else ''
    r.append(('reel downloader', bool(yv), 'yt-dlp ' + yv if yv else 'optional, run: install --step ytdlp'))
    if os.path.exists(os.path.join(RT, '.via-plugin')):
        r.append(('skill', True, 'from the AVS plugin'))
    else:
        s = os.path.join(os.path.expanduser('~'), '.claude', 'skills', 'avs', 'SKILL.md')
        r.append(('skill', os.path.exists(s), '~/.claude/skills/avs' if os.path.exists(s) else 'run: install --step skill'))
    return r


def doctor(a):
    name, ver, words = P.system()
    print('AVS %s on %s, %s' % (open(os.path.join(AVS, 'VERSION')).read().strip() if os.path.exists(os.path.join(AVS, 'VERSION')) else '?', words, P.native_machine()))
    bad = 0
    for n, good, d in rows():
        print('  %-8s %-18s %s' % ('OK' if good else 'MISSING', n, d))
        bad += 0 if good or n == 'reel downloader' else 1
    try:
        b = json.load(open(os.path.join(ENG, 'src', 'brand.json'), encoding='utf-8'))
        print('  brand: accent %s, sans %s, serif %s' % (b['accent'], b['sans'], b['serif']))
    except (OSError, ValueError, KeyError):
        pass
    print('\nAll set. In Claude Code: "make a reel".' if not bad else '\nSomething is missing: run the step shown.')
    return 1 if bad else 0


def preflight(a):
    return 0 if do_step('check', a) else 1


def report(a):
    """Everything support needs, with no videos and no personal details: saved on the Desktop. The home folder becomes ~."""
    import io
    import contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        print('AVS report, %s' % datetime.datetime.now().strftime('%Y-%m-%d %H:%M'))
        print('folder: %s' % AVS)
        print('python: %s' % sys.version.split()[0])
        doctor(a)
        print('\nsteps.log (last 40):')
        sl = os.path.join(RT, 'steps.log')
        print(''.join(open(sl, encoding='utf-8').readlines()[-40:]) if os.path.exists(sl) else '  none yet')
        for e in (json.loads(l) for l in (open(sl, encoding='utf-8').readlines() if os.path.exists(sl) else [])):
            if not e.get('ok'):
                lg = os.path.join(LOGS, e['step'] + '.log')
                if os.path.exists(lg):
                    print('\n--- runtime/logs/%s.log (last 30) ---' % e['step'])
                    print(''.join(open(lg, encoding='utf-8', errors='replace').readlines()[-30:]))
    out = os.path.join(P.desktop(), 'AVS-report-%s.txt' % datetime.datetime.now().strftime('%Y%m%d-%H%M'))
    text = buf.getvalue()
    home = os.path.expanduser('~')
    win = home.replace('/', '\\')
    for h in (win.replace('\\', '\\\\'), win, home.replace('\\', '/')):   # their name never leaves the PC in a path, JSON-escaped ones included
        text = text.replace(h, '~')
    open(out, 'w', encoding='utf-8').write(text)
    print('Report saved: %s' % out)
    return 0


WX_SCRIPTS = ('word_align_x.py',)   # need the speech libraries
MATTE_SCRIPTS = ('matte_reel.py', 'verify_reel.py', 'draft_badge.py', 'study_example.py', 'gen_host_cutout.py')   # need numpy / MediaPipe


PLACES = {'inbox': os.path.join(AVS, 'inbox'), 'out': os.path.join(ENG, 'out'), 'coach': os.path.join(AVS, 'coach'), 'avs': AVS}
FLAGS = {'installed': '.installed', 'local-pages': '.local-pages'}


def small(verb, argv):
    """The one-liners the skill used to write in shell, as launcher verbs that run the same on a Mac and a PC."""
    import glob
    if argv and argv[0] in ('-h', '--help'):
        print([l.strip() for l in __doc__.splitlines() if l.strip().startswith('avs %s' % verb)][0] if any(
            l.strip().startswith('avs %s' % verb) for l in __doc__.splitlines()) else 'avs %s' % verb)
        return 0
    if verb == 'flag':   # avs flag installed | local-pages [--off]
        if not argv or argv[0] not in FLAGS:
            print('usage: avs flag installed | local-pages [--off]'); return 2
        f = os.path.join(RT, FLAGS[argv[0]])
        if '--off' in argv:
            if os.path.exists(f):
                os.remove(f)
            print('%s off' % argv[0])
        else:
            os.makedirs(RT, exist_ok=True); open(f, 'a').close(); print('%s on' % argv[0])
        return 0
    if verb == 'backup-config':   # avs backup-config <name>: the config saved inside the install before a fix
        if not argv:
            print('usage: avs backup-config <name>'); return 2
        src = os.path.join(ENG, 'src', 'methodology', 'reels', argv[0] + '.config.ts')
        if not os.path.exists(src):
            print('no config for %s' % argv[0]); return 1
        dst = os.path.join(ENG, 'qa', argv[0], 'before-fix-%s.config.ts' % datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))
        os.makedirs(os.path.dirname(dst), exist_ok=True); shutil.copy2(src, dst)
        print('SAVED %s' % os.path.relpath(dst, ENG).replace(os.sep, '/')); return 0
    if verb == 'words':   # avs words <transcript json>: what was said, as plain text
        if not argv:
            print('usage: avs words <script/word-timings/<file>-wx.json>'); return 2
        p = argv[0] if os.path.isabs(argv[0]) else os.path.join(ENG, argv[0])
        if not os.path.isfile(p):
            print('no transcript at %s' % argv[0]); return 1
        w = json.load(open(p, encoding='utf-8'))
        w = w['words'] if isinstance(w, dict) else w
        print(' '.join(x['word'] for x in w)); return 0
    if verb == 'inbox-done':   # avs inbox-done <name> <file> [<file> ...]: into inbox/done/<name>/, never over a file
        if len(argv) < 2:
            print('usage: avs inbox-done <name> <file in the inbox> [...]'); return 2
        d = os.path.join(AVS, 'inbox', 'done', argv[0]); os.makedirs(d, exist_ok=True)
        for f in argv[1:]:
            src = f if os.path.isabs(f) else os.path.join(AVS, 'inbox', f)
            dst = os.path.join(d, os.path.basename(src))
            if not os.path.exists(src):
                print('not in the inbox: %s' % f)
            elif os.path.exists(dst):
                print('kept where it is (done/%s/%s already exists): %s' % (argv[0], os.path.basename(src), f))
            else:
                shutil.move(src, dst); print('moved %s' % os.path.basename(src))
        return 0
    if verb == 'clean':   # avs clean <name>: the working files any later preview or render rebuilds (about 250 MB a video)
        if not argv:
            print('usage: avs clean <name>'); return 2
        n = argv[0]
        gone = 0
        for rel in ('qa/%s/picture.mp4', 'qa/%s/mix.wav', 'qa/%s/draft', 'qa/%s/preview', 'qa/%s/stills', 'out/drafts/%s-DRAFT.mp4',
                    'public/host/%s-cut-c.mp4', 'public/host/%s-cut-c.mp4.json', 'public/host/%s-cut-hi-c.mp4', 'public/host/%s-cut-hi-c.mp4.json',
                    'qa/%s/storyboard/covers/.measure'):
            p = os.path.join(ENG, rel % n)
            if os.path.isdir(p):
                shutil.rmtree(p, ignore_errors=True); gone += 1
            elif os.path.exists(p):
                os.remove(p); gone += 1
        for pat in ('out/drafts/%s-b??-?.mp4', 'public/host/%s-thumb-*', 'public/host/%s-fg-*'):   # exact names: another video's never match
            for p in glob.glob(os.path.join(ENG, pat % glob.escape(n))):
                os.remove(p); gone += 1
        print('freed %d working files of %s' % (gone, n)); return 0
    if verb == 'phone-copy':   # avs phone-copy out/<file>.mp4: a small copy for watching in the chat
        if not argv:
            print('usage: avs phone-copy out/<file>.mp4'); return 2
        src = argv[0] if os.path.isabs(argv[0]) else os.path.join(ENG, argv[0])
        dst = os.path.splitext(src)[0] + '-phone.mp4'
        rc = subprocess.run([os.path.join(BIN, 'ffmpeg' + P.EXE) if os.path.exists(os.path.join(BIN, 'ffmpeg' + P.EXE)) else 'ffmpeg', '-v', 'error', '-y',
                             '-i', src, '-vf', 'scale=540:960', '-crf', '30', '-c:a', 'aac', '-b:a', '96k', dst], env=env()).returncode
        if rc == 0:
            print('PHONE COPY %s' % os.path.relpath(dst, ENG).replace(os.sep, '/'))
        return rc
    return 2


def open_place(argv):
    """avs open inbox | out | coach | avs | <a file or folder inside AVS>: Finder on a Mac, File Explorer on a PC."""
    if not argv or argv[0] in ('-h', '--help'):
        print('usage: avs open inbox | out | coach | avs | <file, folder or http page>')
        return 0 if argv else 2
    if argv[0].startswith(('http://', 'https://')):   # a page a local server prints
        P.open_path(argv[0]); print('opened %s' % argv[0]); return 0
    p = PLACES.get(argv[0]) or os.path.abspath(os.path.join(ENG, argv[0]) if not os.path.isabs(argv[0]) else argv[0])
    if not os.path.exists(p):
        print('nothing at %s' % p)
        return 1
    P.open_path(p)
    print('opened %s' % p)
    return 0


def run_script(argv):
    """avs run <script> [args]: an engine script from the engine folder, with the Python (or Node) it needs."""
    if not argv or argv[0] in ('-h', '--help'):
        print('usage: avs run <script in engine/scripts> [args]   e.g. avs run approve_reel.py my-reel --by "Name"')
        return 0 if argv else 2
    s, rest = os.path.basename(argv[0]), argv[1:]
    # @file=<path>: that file's text as ONE argument, so JSON and quoted words never cross a Windows shell's quoting
    rest = [open(x[6:], encoding='utf-8').read().strip() if x.startswith('@file=') and os.path.isfile(x[6:]) else x for x in rest]
    path = os.path.join('scripts', s)
    if not os.path.exists(os.path.join(ENG, path)):
        print('no script %s in engine/scripts' % s)
        return 2
    if s.endswith('.mjs'):
        cmd = [P.node_exe(RT), path]
    elif s in WX_SCRIPTS:
        cmd = [P.venv_python(WHISPERX), path]
    elif s in MATTE_SCRIPTS:
        cmd = [P.venv_python(MATTE), path]
    else:
        cmd = [sys.executable, path]
    return subprocess.run(cmd + rest, cwd=ENG, env=env()).returncode


def expand_home(a):
    """~/... in an argument is the home folder, from any shell (PowerShell passes ~ to a program as it is)."""
    if a.startswith('@file=~'):
        return '@file=' + os.path.expanduser(a[6:])
    return os.path.expanduser(a) if a == '~' or a.startswith(('~/', '~\\')) else a


def main(argv):
    argv = [expand_home(a) for a in argv]
    if argv and argv[0] in ('ffprobe', 'ffmpeg'):   # AVS's own ffmpeg and ffprobe, which are on no PATH but the launcher's
        if argv[1:2] in (['-h'], ['--help']) and len(argv) == 2:
            print('usage: avs %s <its usual arguments>   (AVS\'s own %s)' % (argv[0], argv[0])); return 0
        exe = os.path.join(BIN, argv[0] + P.EXE)
        return subprocess.run([exe if os.path.exists(exe) else argv[0]] + argv[1:], env=env()).returncode
    # verbs with their own options take the rest of the line as it is
    if argv and argv[0] in ('flag', 'backup-config', 'words', 'inbox-done', 'clean', 'phone-copy'):
        os.environ.update(env())
        return small(argv[0], argv[1:])
    if argv and argv[0] in ('reel', 'run', 'smoke', 'update', 'uninstall', 'open'):
        os.environ.update(env())
        if argv[0] == 'run':
            return run_script(argv[1:])
        if argv[0] == 'open':
            return open_place(argv[1:])
        if argv[0] == 'reel':
            import avs_reel
            return avs_reel.main(argv[1:])
        if argv[0] == 'smoke':
            import avs_smoke
            return avs_smoke.main(argv[1:])
        import avs_manage
        return avs_manage.main(argv)
    import argparse
    ap = argparse.ArgumentParser(prog='avs', add_help=False)
    ap.add_argument('verb', nargs='?')
    ap.add_argument('--step'); ap.add_argument('--all', action='store_true'); ap.add_argument('--list', action='store_true')
    for o in ('--accent', '--sans', '--serif', '--handle', '--name', '--avatar', '--skill-dir'):
        ap.add_argument(o)
    ap.add_argument('-h', '--help', action='store_true')
    a = ap.parse_args(argv)
    if a.help or not a.verb:
        print(__doc__.strip())
        return 0
    verbs = {'install': install, 'preflight': preflight, 'doctor': doctor, 'report': report}
    if a.verb not in verbs:
        print('unknown command "%s". Commands: %s' % (a.verb, ', '.join(verbs)))
        return 2
    os.environ.update(env())   # on Windows a program is found on THIS process's PATH, not the one handed to the child
    return verbs[a.verb](a)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))

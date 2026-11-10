"""avs reel: make_reel.sh's chain in Python, for a Mac and a Windows PC (same flags, same steps, same messages).

    avs reel <raw.MOV|mp4> <name> [--face X,Y] [--regen] [--preview] [--unmirror]   builds everything, STOPS at the scene map
        [--keep-take N | --drop-take N | --trim A-B]   a different take, or a fumble cut out (raw seconds): forces a fresh cut
      --trim repeats, one per fumble. Picks and trims are saved (script/word-timings/<name>-takepicks.json, -trims.json),
        and a change to either file, by hand too, re-cuts on the next run
      --unmirror: flip iPhone front-camera footage saved mirrored (text on screen reads backwards)
      --reframe Z: crop to 1/Z from the full-res source, bottom-anchored (removes dead space above the subject)
      --paid: first generation makes a paid Meta ad config (Click Learn More, destination link, ad kit)
      --outdoor: street or camera audio where noise fills the pauses: precise word timing on the raw
    avs reel <raw> <name> --draft      a half-size review draft with sound, badged DRAFT, into out/drafts/ (needs no approval)
    avs reel <raw> <name> --render     renders ONLY with a current human approval

Needs script/<name>.txt (blank-line paragraphs = spoken beats). Steps are skipped when their output is newer than their
inputs. The laws: the spoken script is the timeline; cuts only between sentences, in silence; captions show the script on
spoken timing; the avatar is always on screen; render only after a human approved the scene map.
"""
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import avs as A  # noqa: E402
import avs_platform as P  # noqa: E402

ENG = A.ENG
PY = sys.executable                        # AVS's own Python: what `python3` is in make_reel.sh
WX = P.venv_python(A.WHISPERX)             # the speech libraries
MPY = P.venv_python(A.MATTE)               # the cutout library (and numpy, for verify_reel)
NODE = P.node_exe(A.RT)
REMOTION = A.REMOTION


class Stop(Exception):
    """make_reel.sh's `exit`: the message is printed, the code returned."""
    def __init__(self, msg, code=1):
        super().__init__(msg)
        self.code = code


def say(s):
    print('\n== ' + s, flush=True)


def sh(cmd, check=True, extra_env=None):
    """Run in the engine folder with the AVS environment, output straight to the console (as the bash script did)."""
    e = A.env()
    if extra_env:
        e.update(extra_env)
    p = subprocess.run(cmd, cwd=ENG, env=e)
    if check and p.returncode != 0:
        raise Stop('', p.returncode)   # the program already said what went wrong
    return p.returncode


def out(cmd):
    return subprocess.run(cmd, cwd=ENG, env=A.env(), capture_output=True, text=True, encoding='utf-8', errors='replace')


def py(script, *a, check=True, extra_env=None):
    return sh([PY, os.path.join('scripts', script)] + list(a), check, extra_env)


def newer(a, b, root=None):
    """bash's [ a -nt b ]: a exists and is newer than b, or a exists and b does not."""
    a, b = os.path.join(root or ENG, a), os.path.join(root or ENG, b)
    return os.path.exists(a) and (not os.path.exists(b) or os.path.getmtime(a) > os.path.getmtime(b))


def needs_cut(name, takes=False, root=None):
    """Step 2's condition, the one test_cutter checks: take picks or trims asked for, or the cut older than the transcript,
    the script, the trims file or the picks file (each absent file counts as old)."""
    cut, wx = 'public/host/%s-cut.mp4' % name, 'script/word-timings/%s-wx.json' % name
    n = lambda x: newer(cut, x, root)  # noqa: E731
    return bool(takes) or not n(wx) or not n('script/%s.txt' % name) or \
        not n('script/word-timings/%s-trims.json' % name) or not n('script/word-timings/%s-takepicks.json' % name)


def tail_id(rid):
    """The part of a source stamp that survives a move (inbox -> inbox/done): file name and size."""
    return re.split(r'[\\/]', rid)[-1]


def stage_public(name, hi=False):
    """Exactly the files the render loads (reel_files.mjs), copied into a temp public folder. Returns (folder, lines)."""
    p = out([NODE, os.path.join('scripts', 'reel_files.mjs'), name])
    if p.returncode != 0:
        raise Stop('error: could not read the files %s uses (its config failed to load)' % name)
    pub = tempfile.mkdtemp(prefix='avs-pub-')
    missing = []
    for line in p.stdout.splitlines():
        kind, _, rest = line.partition(' ')
        if not kind:
            continue
        f = rest
        if rest.startswith('hi '):
            f = rest[3:]
            if not hi:
                continue   # full-resolution files: the real render only
        src = os.path.join(ENG, 'public', f)
        if os.path.isfile(src):
            os.makedirs(os.path.dirname(os.path.join(pub, f)), exist_ok=True)
            shutil.copy2(src, os.path.join(pub, f))
        elif kind == 'need':
            missing.append('public/' + f)
    if missing:
        shutil.rmtree(pub, ignore_errors=True)
        raise Stop('error: %s uses files that are not there: %s\n  A cutout (-fg-, -thumb-) is made by the cutout step '
                   '(matte_reel.py %s). A screenshot or clip goes back under public/ with that name, or out of the config.' % (name, ' '.join(missing), name))
    return pub, p.stdout.splitlines()


def render_checked(name, log, args, dst, pub, files):
    """Render, with the log read afterwards: a failed load of a file the reel needs stops the build (a hole or a broken
    image would otherwise finish quietly)."""
    os.makedirs(os.path.dirname(os.path.join(ENG, log)), exist_ok=True)
    with open(os.path.join(ENG, log), 'w', encoding='utf-8', errors='replace') as lf:
        p = subprocess.Popen([NODE, REMOTION, 'render'] + args, cwd=ENG, env=A.env(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             text=True, encoding='utf-8', errors='replace')
        for line in p.stdout:
            sys.stdout.write(line)
            lf.write(line)
        rc = p.wait()
    text = open(os.path.join(ENG, log), encoding='utf-8', errors='replace').read()
    maybe = {re.sub(r'^maybe (hi )?', '', l) for l in files if l.startswith('maybe ')}
    bad = []
    for line in text.splitlines():
        if not re.search(r'Failed to load resource|status of 404', line):
            continue
        m = re.search(r'https?://[^\] ]+', line)
        u = m.group(0) if m else ''
        if '/proxy?src=' in u:   # a video frame read through the renderer's proxy
            u = urllib.parse.unquote(u.split('/proxy?src=', 1)[1].split('&', 1)[0])
        u = re.sub(r'[?].*$', '', re.sub(r'^https?://[^/]+/(public/)?', '', u))
        if not u:
            bad.append('a file (see %s)' % log)
        elif u not in maybe and u not in bad:
            bad.append(u)
    if rc != 0:   # the renderer stopped: name the reel's own file it choked on (a damaged cutout, a broken clip)
        for l in files:
            k, _, f = l.partition(' ')
            if k == 'need' and f in text and any(re.search(r'error|fail|could not|cannot|unable|decode|invalid', x, re.I) for x in text.splitlines() if f in x):
                if f not in bad:
                    bad.append(f)
    if bad:
        if os.path.exists(os.path.join(ENG, dst)):
            os.remove(os.path.join(ENG, dst))
        shutil.rmtree(pub, ignore_errors=True)
        raise Stop('error: the render of %s could not load: %s (missing or damaged). Its picture would show a hole or a broken image, so it stops here.\n'
                   '  A cutout (-fg-, -thumb-): move it out of public/host (and its .src file beside it), then run the same command again, it is cut again. '
                   'A screenshot or clip: put a good copy back under public/ with that name. Then render again.' % (name, ' '.join(bad)))
    if rc != 0:
        if os.path.exists(os.path.join(ENG, dst)):
            os.remove(os.path.join(ENG, dst))
        shutil.rmtree(pub, ignore_errors=True)
        last = [x for x in text.splitlines() if re.search('error', x, re.I) and not x.lstrip().startswith('at ')]
        raise Stop('error: the render of %s stopped: %s. The full log is %s.' % (name, (last[-1] if last else 'no message')[:200], log), rc)


def draft(name):
    code = ('import sys; sys.path.insert(0,"scripts"); import reel_config, scene_map; c=reel_config.load(sys.argv[1]); '
            'e=scene_map.cut_length_error(sys.argv[1], c["frames"], scene_map.cut_frames(c)); sys.exit("error: no draft of " + sys.argv[1] + ". " + e if e else 0)')
    sh([PY, '-c', code, name])   # the scene map's length check
    dd = os.path.join('out', 'drafts')
    draft_out = os.path.join(dd, '%s-DRAFT.mp4' % name)
    os.makedirs(os.path.join(ENG, dd), exist_ok=True)
    os.makedirs(os.path.join(ENG, 'qa', name), exist_ok=True)
    say('draft: the edit at half size with sound, to watch before approving -> %s' % draft_out)
    py('color_lut.py', name)
    sh([MPY, os.path.join('scripts', 'matte_reel.py'), name])
    pub, files = stage_public(name)
    pic, mix, badge = (os.path.join(dd, '%s-%s' % (name, x)) for x in ('picture.mp4', 'mix.mp4', 'badge.png'))
    render_checked(name, 'qa/%s/draft-render.log' % name, ['src/methodology/index.ts', name, pic, '--muted', '--scale=0.5', '--crf=28',
                                                           '--public-dir=' + pub, '--timeout=180000'], pic, pub, files)
    shutil.rmtree(pub, ignore_errors=True)
    py('mix_master.py', name, pic, mix, extra_env={'MIX_QA_SUB': 'draft'})   # records go to qa/<name>/draft, the render's stay
    sh([MPY, os.path.join('scripts', 'draft_badge.py'), badge, '540'])
    sh(['ffmpeg', '-v', 'error', '-y', '-i', mix, '-i', badge, '-filter_complex', '[0:v][1:v]overlay=(W-w)/2:20', '-c:v', 'libx264', '-crf', '28',
        '-preset', 'veryfast', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '96k', '-movflags', '+faststart', draft_out])
    for f in (pic, mix, badge):
        if os.path.exists(os.path.join(ENG, f)):
            os.remove(os.path.join(ENG, f))
    print('\ndraft %s (%.1f MB)  Show it to the creator, then ask for approval of the real render.' % (draft_out, os.path.getsize(os.path.join(ENG, draft_out)) / 1e6))
    return 0


def render(name):
    say('render gate: a current human approval is required')
    py('approve_reel.py', name, '--check')
    o = os.path.join('out', '%s.mp4' % name)
    if os.environ.get('AVS_HOME') and os.path.exists(os.path.join(ENG, o)):   # a member's re-render lands next to the one before it (v2, v3)
        n = 2
        while os.path.exists(os.path.join(ENG, 'out', '%s-v%d.mp4' % (name, n))):
            n += 1
        o = os.path.join('out', '%s-v%d.mp4' % (name, n))
    say('6/7  render (remotion) -> %s' % o)
    py('color_lut.py', name)
    sh([MPY, os.path.join('scripts', 'matte_reel.py'), name])   # back-text cutouts (reused when the cut is unchanged)
    pub, files = stage_public(name, hi=True)
    pic = os.path.join('out', '%s-picture.mp4' % name)
    render_checked(name, 'qa/%s/render.log' % name, ['src/methodology/index.ts', name, pic, '--muted', '--crf=18', '--public-dir=' + pub, '--timeout=180000'], pic, pub, files)
    shutil.rmtree(pub, ignore_errors=True)
    say('     mix + master: narration from the cut, your sounds.json effects, -14 LUFS, true peak <= -1 dBTP')
    py('mix_master.py', name, pic, o)
    os.replace(os.path.join(ENG, pic), os.path.join(ENG, 'qa', name, 'picture.mp4'))
    say('7/7  verify the render')
    if sh([MPY, os.path.join('scripts', 'verify_reel.py'), name, o], check=False) != 0:   # its own venv has numpy, for the audio drift check
        if os.environ.get('AVS_HOME'):   # a member's failed render steps aside, so the render after the fix takes the same name
            failed = os.path.join('qa', name, 'failed-' + os.path.basename(o))
            os.replace(os.path.join(ENG, o), os.path.join(ENG, failed))
            print('RENDER FAILED CHECKS: fix what the FAIL lines name, then render again (the failed file is %s)' % failed)
        return 1
    py('verify_brightness.py', o, check=False)
    say('     cut sheets: the frames around every visual change, checked for flashes and wrong frames')
    if py('verify_cuts.py', name, o, check=False):
        print('  cut sheets FAILED: read qa/%s/cuts/ before delivering' % name)
    py('extract_reel_stills.py', name, o)
    stem = os.path.splitext(os.path.basename(o))[0]
    say('     companion pack: covers + static ads from the same config -> out/%s-companions/' % stem)
    py('companions.py', name, stem)   # a re-render keeps the first version's pack too
    print('RENDERED %s' % o)
    print('\nrendered %s  The gates are not the edit: look at qa/%s/stills/sheet.png and watch it once, sound on.' % (o, name))
    return 0


def build(raw, name, a):
    src, wx = os.path.join('inputs', name + '.mp4'), 'script/word-timings/%s-wx.json' % name
    cut, cutwx = 'public/host/%s-cut.mp4' % name, 'script/word-timings/%s-cut-wx.json' % name
    cfg, mp = 'src/methodology/reels/%s.config.ts' % name, 'script/%s-scene-map.md' % name
    SRC = os.path.join(ENG, src)
    raw_abs = os.path.abspath(raw)
    if not os.path.isfile(raw_abs):
        raise Stop('error: no such video: %s' % raw)
    # the video given must be the recording, never AVS's own normalized copy of it: the checks below would delete that copy
    if os.path.exists(SRC) and os.path.realpath(raw_abs) == os.path.realpath(SRC):
        raise Stop('error: %s is AVS\'s own copy of the video, not the recording. Give the original video (the one in the inbox, or inbox/done/%s/). Nothing was changed.' % (src, name))
    stamp = os.path.join(ENG, 'inputs', name + '.source')
    rawid = '%s|%d' % (raw_abs, os.path.getsize(raw_abs))
    oldid = open(stamp, encoding='utf-8').read().strip() if os.path.exists(stamp) else ''
    if os.path.exists(SRC) and os.path.exists(stamp) and tail_id(oldid) != tail_id(rawid):
        say('new raw for %s: discarding the cached input' % name)
        os.remove(SRC)
    sj = os.path.join(ENG, 'qa', name, 'source.json')
    if a.unmirror and os.path.exists(SRC) and os.path.exists(sj) and not json.load(open(sj)).get('unmirrored'):   # --unmirror asked after the first build
        say('flipping %s (text in the shot read backwards): rebuilding the input' % name)
        os.remove(SRC)
    if os.path.exists(SRC) and os.path.exists(stamp) and oldid != rawid and tail_id(oldid) == tail_id(rawid):
        # the same recording, moved (inbox -> inbox/done): point the records at its new place
        open(stamp, 'w', encoding='utf-8').write(rawid + '\n')
        if os.path.exists(sj):
            d = json.load(open(sj))
            d['raw'] = raw_abs
            json.dump(d, open(sj, 'w'), indent=1)
    if os.path.exists(SRC) and not os.path.exists(stamp):
        open(stamp, 'w', encoding='utf-8').write(rawid + '\n')   # reels built before the stamp adopt their raw
    if not (os.path.exists(SRC) and os.path.getmtime(SRC) > os.path.getmtime(raw_abs)):
        say('0/5  normalize -> %s (1080x1920, 30 fps CFR, one AAC track)' % src)
        extra = (['--unmirror'] if a.unmirror else []) + (['--reframe', a.reframe] if a.reframe else [])
        py('normalize_source.py', raw_abs, src, *extra)
        open(stamp, 'w', encoding='utf-8').write(rawid + '\n')
    fast = [] if a.outdoor else ['--fast']   # outdoor needs precise word edges on the raw
    precise = os.path.join(ENG, 'script', 'word-timings', name + '-wx.precise')
    if a.outdoor and os.path.exists(os.path.join(ENG, wx)) and not os.path.exists(precise):
        say('--outdoor: the transcript on disk is the quick one, making the precise one')
        os.remove(os.path.join(ENG, wx))
    if not newer(wx, src):
        say('1/5  transcribe %s' % (fast[0] if fast else '(precise, outdoor)'))
        if os.path.exists(precise):
            os.remove(precise)
        sh([WX, os.path.join('scripts', 'word_align_x.py'), src] + fast)
        if not fast:
            open(precise, 'w').close()
    takes = sum(a.takes, [])
    outdoor = ['--word-gaps'] if a.outdoor else []
    lt = [PY, os.path.join('scripts', 'last_take.py'), src, '--words', wx, '--script', 'script/%s.txt' % name, '--out', cut,
          '--report', 'script/%s-takes.md' % name, '--json', 'script/word-timings/%s-takes.json' % name] + outdoor + takes
    if needs_cut(name, takes):
        say('2/5  last take: keep the last clean take of each sentence, cut in silence -> %s' % cut)
        sh(lt)
    if not newer(cutwx, cut):
        say('3/5  whisperX align the cut, tighten loose joins, re-align (10-20ms word times)')
        sh([WX, os.path.join('scripts', 'word_align_x.py'), cut])
        r = out(lt + ['--refine', cutwx])
        print(r.stdout.rstrip())
        if r.returncode:
            sys.stdout.write(r.stderr)
            raise Stop('', r.returncode)
        if 'no re-cut' not in r.stdout:
            sh([WX, os.path.join('scripts', 'word_align_x.py'), cut])
    say('     full-resolution cut from the original recording, so punch-ins and zooms stay sharp')
    if py('hires_cut.py', name, check=False):
        print('  hi-res cut unavailable: the render uses the 1080p cut')
    say('     seam check: stray sound or dead air at cut joins, head and tail')
    if py('verify_seams.py', name, check=False):
        print('  seam check FAILED: see qa/%s/seams.json (the scene map will say NOT READY)' % name)
    say('4/5  config -> %s' % cfg)
    py('gen_reel_config.py', name, *((['--face', a.face] if a.face else []) + (['--regen'] if a.regen else []) + (['--paid'] if a.paid else [])))
    say('5/5  scene map -> %s' % mp)
    py('scene_map.py', name, check=False)   # also checks the keyword and writes script/<name>-post.md
    sh([NODE, os.path.join('scripts', 'test_layout.mjs'), name], check=False)
    if a.preview:
        py('color_lut.py', name)
        sh([MPY, os.path.join('scripts', 'matte_reel.py'), name])
        py('extract_reel_stills.py', name, '--preview')
        py('storyboard.py', name)
    launcher = 'avs.cmd' if P.WIN else './avs'
    print('\nSTOPPED before render, by design. Read %s.' % mp)
    print('Edit only scenes / swaps / big flags / copy in %s, then re-run this command (the config is kept).' % cfg)
    print('When the human approves:  avs run approve_reel.py %s --by "<name>"  then  %s reel %s %s --render' % (name, launcher, raw, name))
    return 0


def main(argv):
    if not argv or argv[0] in ('-h', '--help'):
        print(__doc__.strip())
        return 0
    if len(argv) < 2:
        print('usage: avs reel <raw> <name> [--face X,Y] [--regen] [--preview] [--render]')
        return 2
    raw, name, rest = argv[0], argv[1], argv[2:]

    class O:
        face = reframe = None
        regen = render = draft = preview = unmirror = paid = outdoor = False
        takes = []
    a = O()
    a.takes = []
    i = 0
    while i < len(rest):
        x = rest[i]
        if x in ('--face', '--reframe'):
            setattr(a, x[2:], rest[i + 1]); i += 2
        elif x in ('--regen', '--render', '--draft', '--preview', '--unmirror', '--paid', '--outdoor'):
            setattr(a, x[2:], True); i += 1
        elif x in ('--keep-take', '--drop-take', '--trim'):
            a.takes.append([x, rest[i + 1]]); i += 2   # take picks and fumble trims: forces a fresh cut
        else:
            print('unknown option %s' % x)
            return 2
    os.environ.update(A.env())
    try:
        if not (a.render or a.draft) and not os.path.exists(os.path.join(ENG, 'script', name + '.txt')):
            raise Stop('error: script/%s.txt is missing (the writer\'s script is the timeline)' % name)
        if not os.path.exists(WX):
            raise Stop('error: the speech libraries are missing. Run: avs doctor')
        if not os.path.exists(MPY):
            raise Stop('error: the cutout environment is missing. Run: avs doctor')
        if not shutil.which('ffmpeg'):
            raise Stop('error: ffmpeg not found. Run: avs doctor')
        if a.draft:
            return draft(name)
        if a.render:
            return render(name)
        return build(raw, name, a)
    except Stop as s:
        if str(s):
            print(str(s))
        return s.code

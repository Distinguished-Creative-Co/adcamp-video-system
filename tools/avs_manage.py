"""avs update and avs uninstall (update.sh and uninstall.sh in Python, for a Mac and a Windows PC).

    avs update --latest                       the newest version, straight from GitHub
    avs update <AVS-x.y.z.zip>                a version you downloaded
    avs update <folder>                       an AVS folder (the plugin's, after a plugin update)
    avs update --check [--plugin <folder>]    is there a newer version? One line, no changes:
        UPDATE NONE | UPDATE SKIPPED <why> | UPDATE SYNC <folder> | UPDATE AVAILABLE <old> -> <new>: <what's new>
      GitHub is asked at most once a day (runtime/update-check.json). A Windows PC reads the windows-preview line.
    avs uninstall [--yes] [--delete-videos]   remove the AVS folder and the skill. Finished videos, caption drafts and
      carousel slides are copied to AVS-videos on the Desktop first, unless --delete-videos.
"""
import datetime
import filecmp
import glob
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import avs as A  # noqa: E402
import avs_platform as P  # noqa: E402

AVS, RT, ENG = A.AVS, A.RT, A.ENG
BRANCH = 'windows-preview' if P.WIN else 'main'   # the Windows line lives on its own branch until the two meet
REPO = os.environ.get('AVS_REPO', 'https://github.com/Distinguished-Creative-Co/adcamp-video-system')
RAW = os.environ.get('AVS_REPO_RAW', 'https://raw.githubusercontent.com/Distinguished-Creative-Co/adcamp-video-system/' + BRANCH)
TARBALL = os.environ.get('AVS_REPO_TARBALL', REPO + '/archive/refs/heads/%s.tar.gz' % BRANCH)
TEST_REELS = ('sample', 'sample-big-energy', 'sample-soft-story', 'sample-install-check', 'sample-paid-check')   # every reel the install test makes


def vt(v):
    try:
        return tuple(int(x) for x in v.strip().split('.'))
    except ValueError:
        return (0,)


def version(folder):
    p = os.path.join(folder, 'VERSION')
    return open(p).read().strip() if os.path.exists(p) else '0.0.0'


def get(url):
    r = subprocess.run([P.curl(), '-fsSL', '--max-time', '8', url], capture_output=True)
    return r.stdout.decode('utf-8', 'replace') if r.returncode == 0 else ''


def check(argv):
    old = version(AVS)
    plugin = argv[argv.index('--plugin') + 1] if '--plugin' in argv and argv.index('--plugin') + 1 < len(argv) else ''
    if plugin and vt(version(plugin)) > vt(old):
        print('UPDATE SYNC %s' % plugin)
        return 0
    cache, today = os.path.join(RT, 'update-check.json'), datetime.date.today().isoformat()
    c = json.load(open(cache)) if os.path.exists(cache) else {}
    if c.get('checked') == today:
        new, note = c.get('newest', ''), c.get('note', '')
    else:
        new = get(RAW + '/VERSION').strip()
        if not new:
            print('UPDATE SKIPPED (could not reach GitHub)')
            return 0
        try:
            note = json.loads(get(RAW + '/whats-new.json') or '{}').get(new) or 'fixes and improvements'
        except ValueError:
            note = 'fixes and improvements'
        os.makedirs(RT, exist_ok=True)
        json.dump({'checked': today, 'newest': new, 'note': note}, open(cache, 'w'))
    print('UPDATE AVAILABLE %s -> %s: %s' % (old, new, note) if vt(new) > vt(old) else 'UPDATE NONE (%s is the newest)' % old)
    return 0


def copy_in(src, dst):
    """Code and docs only, by content: reels, inputs, renders, qa, styles, picks and runtime are never in the package."""
    n = 0
    for dp, dns, fns in os.walk(src):
        rel = os.path.relpath(dp, src)
        dns[:] = [d for d in dns if d not in ('.git', '.claude-plugin') and os.path.join(rel, d).replace(os.sep, '/') != 'engine/src/methodology/reels']
        for f in fns:
            s, d = os.path.join(dp, f), os.path.join(dst, rel, f)
            if os.path.exists(d) and filecmp.cmp(s, d, shallow=False):
                continue
            os.makedirs(os.path.dirname(d), exist_ok=True)
            for attempt in range(5):   # Windows will not replace a file another program holds: wait a moment and retry
                try:
                    shutil.copy2(s, d)
                    break
                except PermissionError:
                    if attempt == 4:
                        raise
                    time.sleep(2)
            n += 1
    return n


def update(argv):
    if not argv or argv[0] in ('-h', '--help'):
        print(__doc__.strip())
        return 0 if argv else 2
    if argv[0] == '--check':
        return check(argv[1:])
    src = argv[0]
    if src != '--latest' and not os.path.exists(src):
        print('no such file or folder: %s' % src)
        return 1
    old = version(AVS)
    bk = tempfile.mkdtemp(prefix='avs-settings-')
    print('Backing up your settings to %s' % bk)
    for f in (os.path.join(ENG, 'src', 'brand.json'), os.path.join(ENG, 'sounds.json')):
        if os.path.exists(f):
            shutil.copy2(f, bk)
    if os.path.isdir(os.path.join(ENG, 'sounds', 'music')):
        shutil.copytree(os.path.join(ENG, 'sounds', 'music'), os.path.join(bk, 'music'))
    tmp = tempfile.mkdtemp(prefix='avs-update-')
    pkg = os.path.join(tmp, 'AVS')
    try:
        if src == '--latest':
            print('Downloading the newest AVS from GitHub (about 60 MB)')
            tgz = os.path.join(tmp, 'avs.tar.gz')
            if subprocess.run([P.curl(), '-fsSL', '-o', tgz, TARBALL]).returncode != 0:
                print('download failed: check your internet connection')
                return 1
            with tarfile.open(tgz) as t:
                for m in t.getmembers():   # strip the archive's top folder
                    m.name = m.name.split('/', 1)[1] if '/' in m.name else ''
                t.extractall(pkg, members=[m for m in t.getmembers() if m.name], filter='data')
        elif os.path.isdir(src):
            shutil.copytree(src, pkg, ignore=shutil.ignore_patterns('.git'))
        else:
            with zipfile.ZipFile(src) as z:
                z.extractall(tmp)
        if not os.path.isdir(os.path.join(pkg, 'engine')):
            print('that is not an AVS package')
            return 1
        new = version(pkg)
        copy_in(pkg, AVS)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)   # the unpacked package copy never stays behind
    for f, d in (('brand.json', os.path.join(ENG, 'src')), ('sounds.json', ENG)):
        if os.path.exists(os.path.join(bk, f)):
            shutil.copy2(os.path.join(bk, f), os.path.join(d, f))
    if os.path.isdir(os.path.join(bk, 'music')):
        shutil.copytree(os.path.join(bk, 'music'), os.path.join(ENG, 'sounds', 'music'), dirs_exist_ok=True)
    for f in ('update-check.json',):
        if os.path.exists(os.path.join(RT, f)):
            os.remove(os.path.join(RT, f))
    if os.path.isdir(src) and os.path.exists(os.path.join(RT, '.via-plugin')):   # the plugin moved to its new version folder
        open(os.path.join(RT, '.via-plugin'), 'w').write(os.path.abspath(src))
    reg = 'import sys; sys.path.insert(0, "scripts"); import gen_reel_config as g; g.register(sys.argv[1], False)'
    for c in glob.glob(os.path.join(ENG, 'src', 'methodology', 'reels', '*.config.ts')):
        subprocess.run([sys.executable, '-c', reg, os.path.basename(c)[:-len('.config.ts')]], cwd=ENG, env=A.env(), capture_output=True)
    new_launcher = os.path.join(AVS, 'tools', 'avs.py')   # the new version's own steps
    for step in ('npm', 'cutout', 'ytdlp', 'skill'):
        subprocess.run([sys.executable, new_launcher, 'install', '--step', step], env=A.env())
    if os.path.exists(os.path.join(RT, '.via-plugin')) and src == '--latest':
        print('One more step for the plugin: open Plugins, then Manage plugins, and update AVS.')
    open(os.path.join(RT, '.installed'), 'a').close()   # an install that updates is a finished install
    shutil.rmtree(bk, ignore_errors=True)   # the settings backup is only needed if the update stops partway
    print('Updated AVS %s -> %s. Your reels, brand, music and styles are kept.' % (old, new))
    return 0


def size_text(folder):
    total = 0
    for dp, _, fs in os.walk(folder):
        for f in fs:
            try:
                total += os.path.getsize(os.path.join(dp, f))
            except OSError:
                pass
    return '%.1f GB' % (total / 1e9)


def uninstall(argv):
    if argv and argv[0] in ('-h', '--help'):
        print(__doc__.strip())
        return 0
    yes, keep = '--yes' in argv, '--delete-videos' not in argv
    desk = os.path.join(P.desktop(), 'AVS-videos')
    skill = os.path.join(os.path.expanduser('~'), '.claude', 'skills', 'avs')
    print('This removes %s (%s) and %s.' % (AVS, size_text(AVS), skill))
    if keep:
        print('Your inbox footage, scripts and saved styles go with it. Finished videos, caption drafts and carousel slides are copied to %s first.' % desk)
    if not yes and input('Type REMOVE to continue: ').strip() != 'REMOVE':
        print('Cancelled.')
        return 1
    if keep:
        out = os.path.join(ENG, 'out')
        skip_dirs, skip_files = {'drafts', 'sample-companions'}, {'sample.mp4', 'sample-phone.mp4', 'font-sheet.png', 'setup-check.png'}
        if glob.glob(os.path.join(out, '*.mp4')):   # their finished videos: never the drafts or the install test's
            for dp, dns, fns in os.walk(out):
                dns[:] = [d for d in dns if d not in skip_dirs and not d.startswith('.')]
                for f in fns:
                    if f.startswith('.') or (dp == out and f in skip_files):
                        continue
                    d = os.path.join(desk, os.path.relpath(dp, out), f)
                    os.makedirs(os.path.dirname(d), exist_ok=True)
                    shutil.copy2(os.path.join(dp, f), d)
        for f in sum((glob.glob(os.path.join(ENG, 'script', p)) for p in ('*-post.md', '*-ad.md', '*-post-mine.md', '*-ad-mine.md')), []):
            b = os.path.basename(f)
            reel = b
            for suf in ('-post-mine.md', '-ad-mine.md', '-post.md', '-ad.md'):
                if reel.endswith(suf):
                    reel = reel[:-len(suf)]
                    break
            if reel in TEST_REELS:
                continue   # the install test's own drafts
            os.makedirs(os.path.join(desk, 'captions'), exist_ok=True)
            shutil.copy2(f, os.path.join(desk, 'captions'))
        for d in glob.glob(os.path.join(ENG, 'carousels', '*', '')):
            sl = os.path.join(d, 'slides')
            if not glob.glob(os.path.join(sl, '*.png')):
                continue
            to = os.path.join(desk, 'carousels', os.path.basename(os.path.dirname(d)))
            shutil.copytree(sl, to, dirs_exist_ok=True)
            cj = os.path.join(d, 'carousel.json')
            if os.path.exists(cj):
                try:
                    open(os.path.join(to, 'caption.txt'), 'w', encoding='utf-8').write(json.load(open(cj, encoding='utf-8')).get('caption') or '')
                except (OSError, ValueError):
                    pass
        if os.path.isdir(desk) and os.listdir(desk):
            print('Videos, caption drafts and slides copied to %s' % desk)
        else:
            shutil.rmtree(desk, ignore_errors=True)
            print('No finished videos or caption drafts of yours to copy.')
    shutil.rmtree(skill, ignore_errors=True)
    if P.WIN:   # this launcher runs from inside the folder, and Windows will not delete a running program: a helper does it after we exit
        helper = os.path.join(tempfile.gettempdir(), 'avs-remove-%d.cmd' % os.getpid())
        open(helper, 'w', newline='\r\n').write('@echo off\nping -n 4 127.0.0.1 >nul\nrmdir /s /q "%s"\ndel "%%~f0"\n' % AVS)
        subprocess.Popen(['cmd.exe', '/d', '/c', helper], creationflags=0x00000008 | 0x00000200, close_fds=True)   # DETACHED_PROCESS, NEW_PROCESS_GROUP
        print('AVS is being removed (the folder goes a few seconds after this). If you installed it from the Plugins panel, remove AdCamp Video System there too.')
    else:
        shutil.rmtree(AVS, ignore_errors=True)
        print('AVS removed. If you installed it from the Plugins panel, remove AdCamp Video System there too.')
    return 0


def main(argv):
    return update(argv[1:]) if argv[0] == 'update' else uninstall(argv[1:])

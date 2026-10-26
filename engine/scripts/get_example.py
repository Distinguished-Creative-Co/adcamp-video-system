#!/usr/bin/env python3
"""Bring the reels a member likes onto this Mac so they can be studied: a post link or a file.

    python3 scripts/get_example.py "<link or file>" ["<another>" ...] [--browser chrome|safari|firefox|edge]

  a link      fetched with yt-dlp (Instagram, TikTok, YouTube Shorts, Pinterest, X and most others). One video
              per link. Nothing is posted, liked or followed: it is a plain download for study.
  a file      copied in as it is (a reel they saved, a screen recording of one)
  --browser   ONLY after the member said yes in chat: some posts (often Instagram) only show to a logged-in
              visitor, and this lets yt-dlp read that browser's login for this one download. Nothing is stored.

Each lands in styles/_examples/ and prints one line:
  EXAMPLE READY <file>          next: scripts/study_example.py <file>
  EXAMPLE FAILED LOGIN <link>   ask the member: use their browser's login for it, or have them save the video and drop the file in
  EXAMPLE FAILED <link>: <why>  ask for another link or the file
The study copies are for looking at only: never put an example's footage, music, words, handle or name in a reel.
"""
import hashlib
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, 'styles', '_examples')
MEDIA = ('.mp4', '.mov', '.m4v', '.webm', '.mkv', '.jpg', '.jpeg', '.png', '.webp')
LOGIN_HINTS = ('login', 'log in', 'sign in', 'cookies', 'rate-limit', 'rate limit', 'private', 'not available', 'empty media')


def ytdlp():
    for c in (shutil.which('yt-dlp'), os.path.join(ROOT, '..', 'runtime', 'bin', 'yt-dlp'), os.path.expanduser('~/.local/bin/yt-dlp')):
        if c and os.path.isfile(c) and os.access(c, os.X_OK):
            return c
    return None


def fetch(link, browser):
    tool = ytdlp()
    if not tool:
        return 'EXAMPLE FAILED %s: the downloader is not installed. In AVS run: ~/AVS/install.sh --step ytdlp' % link
    key = hashlib.sha1(link.encode()).hexdigest()[:10]
    dst = os.path.join(OUT, 'ex-%s.mp4' % key)
    if os.path.exists(dst):
        return 'EXAMPLE READY %s' % dst
    cmd = [tool, '--no-playlist', '--no-progress', '--quiet', '--no-warnings', '--max-filesize', '600M',
           '-f', 'bv*[ext=mp4][height<=1920]+ba[ext=m4a]/b[ext=mp4]/bv*+ba/b', '--merge-output-format', 'mp4',
           '-o', os.path.join(OUT, 'ex-%s.%%(ext)s' % key), link]
    if browser:
        cmd[1:1] = ['--cookies-from-browser', browser]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if p.returncode != 0 and not any(h in (p.stderr or '').lower() for h in LOGIN_HINTS):
        # sites change and an old downloader breaks first: update it once, then try again
        if subprocess.run([tool, '-U'], capture_output=True, text=True, timeout=180).returncode == 0:
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    got = [f for f in os.listdir(OUT) if f.startswith('ex-%s.' % key) and f.endswith(MEDIA)]
    if p.returncode == 0 and got:
        src = os.path.join(OUT, got[0])
        if src != dst and src.endswith('.mp4'):
            os.replace(src, dst)
            src = dst
        return 'EXAMPLE READY %s' % src
    why = (p.stderr or p.stdout or 'no video in that post').strip().splitlines()[-1][:200]
    if not browser and any(h in why.lower() for h in LOGIN_HINTS):
        return 'EXAMPLE FAILED LOGIN %s' % link
    return 'EXAMPLE FAILED %s: %s' % (link, why)


def main():
    a = sys.argv[1:]
    browser = a[a.index('--browser') + 1] if '--browser' in a else None
    items = [x for i, x in enumerate(a) if not x.startswith('--') and (i == 0 or a[i - 1] != '--browser')]
    if not items:
        sys.exit(__doc__)
    if browser not in (None, 'chrome', 'safari', 'firefox', 'edge', 'brave', 'arc'):
        sys.exit('get_example: --browser must be chrome, safari, firefox, edge, brave or arc')
    os.makedirs(OUT, exist_ok=True)
    for it in items:
        path = os.path.expanduser(it)
        if os.path.isfile(path):
            if not path.lower().endswith(MEDIA):
                print('EXAMPLE FAILED %s: not a video or picture file' % it)
                continue
            key = hashlib.sha1(os.path.abspath(path).encode()).hexdigest()[:10]
            dst = os.path.join(OUT, 'ex-%s%s' % (key, os.path.splitext(path)[1].lower()))
            shutil.copy2(path, dst)
            print('EXAMPLE READY %s' % dst)
        elif it.startswith(('http://', 'https://')):
            print(fetch(it, browser), flush=True)
        else:
            print('EXAMPLE FAILED %s: not a link or a file on this Mac' % it)


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Free music by vibe, from Openverse (openverse.org). Only licenses that allow any use, ads included:
CC0 and public domain (no credit needed) and CC BY (a one-line credit in the caption, written for you).

    python3 scripts/find_music.py "<vibe words>" [--n 3]        search, keep the ones that play, cut a 20 s snippet of each
    python3 scripts/find_music.py --pick <id> [--reel <name>]   keep that one: into sounds/music, LICENSES.md and
                                                                credits.json, and pinned on the reel (with musicStart)
    python3 scripts/find_music.py --use <sounds/music/file> --reel <name> [--credit "<line>"]   pin a kept track, or
                                                                their own licensed file, on a reel (same as last time).
                                                                --credit: the credit their own track's license asks for

A track plays only on a reel it is pinned to (never added to music_beds, so no reel gets music nobody picked).

Search prints one block per candidate (number, title, creator, license, length, snippet path, id) and writes
sounds/music/candidates/candidates.json. Put the snippets in the chat and let them choose. Nothing is kept until
--pick. Openverse needs no account; anonymous searches are rate-limited, so if it says to wait, wait a minute.
"""
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import reel_config  # noqa: E402
import styles_lib as L  # noqa: E402

API = 'https://api.openverse.org/v1/audio/'
UA = 'AdCamp-Video-System/2.0 (music by vibe; +https://github.com/Distinguished-Creative-Co/adcamp-video-system)'
MUSIC = os.path.join(ROOT, 'sounds', 'music')
CAND = os.path.join(MUSIC, 'candidates')
CREDITS = os.path.join(MUSIC, 'credits.json')
LABEL = {'cc0': 'CC0 (no credit needed)', 'pdm': 'Public domain (no credit needed)', 'by': 'CC BY (credit in the caption)'}
MIN_S, MAX_S = 30, 300


def get(url, timeout=30):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    try:
        return urllib.request.urlopen(req, timeout=timeout)
    except urllib.error.HTTPError as e:
        if e.code == 429:
            sys.exit('find_music: Openverse says too many searches for now. Try again in a minute.')
        raise


def search(vibe, category):
    q = {'q': vibe, 'license': 'cc0,by,pdm', 'page_size': 20, 'mature': 'false'}
    if category:
        q['category'] = 'music'
    for attempt in (1, 2):   # the first search of a phrase can be slow on Openverse's side
        try:
            data = json.load(get(API + '?' + urllib.parse.urlencode(q), timeout=45))
            break
        except (OSError, ValueError):
            if attempt == 2:
                sys.exit('find_music: Openverse did not answer. Check the internet connection and try again in a minute.')
    out = []
    for r in data.get('results', []):
        secs = (r.get('duration') or 0) / 1000
        named = (r.get('creator') or '').strip().lower() not in ('', 'unknown', 'anonymous')
        if r.get('license') in LABEL and MIN_S <= secs <= MAX_S and r.get('url') and (named or r['license'] != 'by'):   # CC BY needs a name to credit
            out.append(r)
    return out


def real_ext(path):
    """The extension of what the file actually is (Openverse labels some mp3s "mp32")."""
    p = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=format_name', '-of', 'csv=p=0', path], capture_output=True, text=True)
    fmt = p.stdout.strip().split(',')[0]
    return {'mp3': 'mp3', 'ogg': 'ogg', 'flac': 'flac', 'wav': 'wav', 'mov': 'm4a', 'aiff': 'aiff'}.get(fmt, 'mp3')


def seconds(path):
    p = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', path], capture_output=True, text=True)
    try:
        return float(p.stdout.strip())
    except ValueError:
        return 0.0


def first_loud(path):
    """Seconds until the track gets going (first 0.5 s window within 12 dB of its loudest), so a quiet intro is skipped."""
    p = subprocess.run(['ffmpeg', '-hide_banner', '-t', '40', '-i', path, '-vn', '-af',
                        'aresample=16000,asetnsamples=8000,astats=metadata=1:reset=1,ametadata=print:key=lavfi.astats.Overall.RMS_level',
                        '-f', 'null', '-'], capture_output=True, text=True)
    lv = [float(x) if x not in ('-inf', 'inf') else -120.0 for x in re.findall(r'RMS_level=(-?[\d.]+|-?inf)', p.stderr)]
    if not lv:
        return 0.0
    top = max(lv)
    return next((i * 0.5 for i, v in enumerate(lv) if v >= top - 12), 0.0)


def slug(t):
    return re.sub(r'[^a-z0-9]+', '-', t.lower()).strip('-')[:40] or 'track'


def credit_line(c):
    """CC BY asks for title, creator, source, license (with its link) and a note of changes."""
    if c['license'] != 'by':
        return ''
    return 'Music: "%s" by %s (%s), %s %s, edited for this video' % (
        c['title'], c['creator'], c['source_url'], c['license_name'], c['license_url'] or 'https://creativecommons.org/licenses/')


def do_search(vibe, n):
    if os.path.isdir(CAND):
        shutil.rmtree(CAND)   # the last search's leftovers (never a kept track: those live in sounds/music)
    os.makedirs(CAND)
    # Openverse matches every word, so a long vibe finds little: relax from the whole phrase to fewer words
    words = [w for w in re.findall(r"[a-z0-9']+", vibe.lower()) if w not in ('and', 'a', 'the', 'with', 'music', 'song', 'track')]
    queries = [vibe] + [' '.join(words[:i] + words[i + 1:]) for i in range(len(words))] * (len(words) > 2) + sorted(words, key=len, reverse=True)
    seen, pool = set(), []
    for q in dict.fromkeys(x for x in queries if x.strip()):
        for r in search(q, True):   # music only: without the category, results are field recordings and sound effects
            if r['id'] not in seen:
                seen.add(r['id'])
                pool.append(r)
        if len(pool) >= n * 3:
            break
    kept = []
    for r in pool:
        if len(kept) >= n:
            break
        short = r['id'][:8]
        full = os.path.join(CAND, '%s.download' % short)
        try:
            with get(r['url'], timeout=60) as resp, open(full, 'wb') as f:
                shutil.copyfileobj(resp, f)
        except Exception:
            continue
        dur = seconds(full)
        if dur < MIN_S:   # did not download whole, or does not play
            os.remove(full)
            continue
        named = os.path.join(CAND, '%s.%s' % (short, real_ext(full)))
        os.rename(full, named)
        full = named
        start = min(max(first_loud(full), 0.0), max(0.0, dur - 20))
        snip = os.path.join(CAND, '%s-snippet.m4a' % short)
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', '%.2f' % start, '-t', '20', '-i', full, '-vn', '-af', 'afade=t=in:d=0.5,afade=t=out:st=18.5:d=1.5',
                        '-c:a', 'aac', '-b:a', '128k', snip], check=True)
        ver = r.get('license_version') or ''
        title = re.sub(r'\.(wav|mp3|flac|ogg|aiff?|m4a)$', '', (r.get('title') or '').strip(), flags=re.I).strip() or 'Untitled'
        kept.append({'id': short, 'title': title, 'creator': (r.get('creator') or 'unknown').strip(),
                     'license': r['license'], 'license_name': ('CC BY %s' % ver).strip() if r['license'] == 'by' else ('CC0' if r['license'] == 'cc0' else 'Public Domain Mark'),
                     'license_url': r.get('license_url') or '', 'source_url': r.get('foreign_landing_url') or r['url'], 'provider': r.get('source') or '',
                     'file': os.path.relpath(full, ROOT), 'snippet': os.path.relpath(snip, ROOT), 'seconds': round(dur, 1),
                     'music_start': round(start, 1), 'vibe': vibe})
    json.dump(kept, open(os.path.join(CAND, 'candidates.json'), 'w'), indent=1)
    if not kept:
        print('NO MUSIC for "%s": try other words (a mood, an instrument, a genre), or no music.' % vibe)
        return
    for i, c in enumerate(kept, 1):
        print('%d. "%s" by %s | %s | %d:%02d | snippet %s | id %s' % (
            i, c['title'], c['creator'], LABEL[c['license']], c['seconds'] // 60, c['seconds'] % 60, c['snippet'], c['id']))


def pin(reel, rel, start):
    path = reel_config.config_path(reel)
    src = open(path).read()
    src = L.set_key(src, 'music', rel, 'the picked bed')
    src = L.set_key(src, 'musicStart', start, 'skips the quiet intro')
    open(path, 'w').write(src)
    print('find_music: %s plays under %s (from %.1f s in). Approval is stale: show the new draft.' % (rel, reel, start))
    # the caption draft carries the CC BY credit: rebuild it now, so it always names the track that plays
    subprocess.run([sys.executable, os.path.join(HERE, 'post_kit.py'), reel], cwd=ROOT, capture_output=True)


def do_pick(pid, reel):
    cp = os.path.join(CAND, 'candidates.json')
    cands = json.load(open(cp)) if os.path.exists(cp) else []
    c = next((x for x in cands if x['id'] == pid), None)
    if not c:
        sys.exit('find_music: no candidate %s. Search again first.' % pid)
    ext = os.path.splitext(c['file'])[1]
    rel = 'sounds/music/%s-%s%s' % (slug(c['title']), c['id'], ext)
    shutil.move(os.path.join(ROOT, c['file']), os.path.join(ROOT, rel))
    lic = os.path.join(MUSIC, 'LICENSES.md')
    with open(lic, 'a') as f:
        f.write('| %s | "%s" by %s, %s (found with AVS music search) | %s %s | %s |\n' % (
            os.path.basename(rel), c['title'].replace('|', '/'), c['creator'].replace('|', '/'), c['source_url'],
            c['license_name'], c['license_url'], datetime.date.today().isoformat()))
    credits = json.load(open(CREDITS)) if os.path.exists(CREDITS) else {}
    credits[rel] = {k: c[k] for k in ('title', 'creator', 'license', 'license_name', 'license_url', 'source_url', 'vibe', 'music_start')}
    credits[rel]['line'] = credit_line(c)
    json.dump(credits, open(CREDITS, 'w'), indent=1)
    print('find_music: kept "%s" by %s (%s) as %s. Source: %s' % (c['title'], c['creator'], c['license_name'], rel, c['source_url']))
    if credits[rel]['line']:
        print('find_music: the caption draft will end with: %s' % credits[rel]['line'])
    if reel:
        pin(reel, rel, c['music_start'])
    shutil.rmtree(CAND, ignore_errors=True)


def main():
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    reel = a[a.index('--reel') + 1] if '--reel' in a else None
    if a[0] == '--pick':
        return do_pick(a[1], reel)
    if a[0] == '--use':
        rel = a[1]
        if not reel or not os.path.isfile(os.path.join(ROOT, rel)):
            sys.exit('find_music: --use needs a kept track (sounds/music/...) and --reel <name>')
        credits = json.load(open(CREDITS)) if os.path.exists(CREDITS) else {}
        if '--credit' in a:   # their own track: the caption draft carries its credit like any CC BY pick
            credits.setdefault(rel, {})['line'] = a[a.index('--credit') + 1].strip()
            json.dump(credits, open(CREDITS, 'w'), indent=1)
        start = (credits.get(rel) or {}).get('music_start')
        return pin(reel, rel, first_loud(os.path.join(ROOT, rel)) if start is None else start)
    n = int(a[a.index('--n') + 1]) if '--n' in a else 3
    do_search(a[0], n)


if __name__ == '__main__':
    main()

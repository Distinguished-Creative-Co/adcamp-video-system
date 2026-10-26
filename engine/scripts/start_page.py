#!/usr/bin/env python3
"""The start page: every video begins here, beside the chat, before anything is cut. The member picks a caption style
(8, each playing), 2 to 4 effects (21, each playing, grouped by what they're for), pastes a script or lets Claude
write it from what they said, and sets regular post or paid ad and a music vibe. Prefilled from last time, so a
video like the last one is one press of Start.

    python3 scripts/start_page.py build [--video <file>] [--script <file>] [--look <look>]   writes qa/start/ (pane.html, index.html)
    python3 scripts/start_page.py serve [--video <file>] [--script <file>]   the same page in a browser tab, waits for Start
    python3 scripts/start_page.py read '<the start/current document as JSON>'   checks the picks, keeps them for this video
    python3 scripts/start_page.py read --file <file>   the same, from the document saved to a file (use this one)
    python3 scripts/start_page.py read --last [--look <look>] [--script <file>]   "same as last time" or "just go"
    python3 scripts/start_page.py remember --reel <name> --color <key> | --captions <key>
                                                  a change after Start: kept for that video and next time's prefill
    python3 scripts/start_page.py use <name>      after naming the video: qa/<name>/start.json, script/<name>.txt
    python3 scripts/start_page.py apply <name>    after the first build in their look: their caption style, and the
                                                  effects to place (printed for the effects pass)

Publish qa/start/pane.html with files-map.json and capabilities {"db": {}, "user": {}, "comments": {}}. Start writes the
picks into the page's own store (collection "start", doc "current": read it with ArtifactData) and sends one comment to
Claude ("Start my video: ..."), which wakes the session. Prints START SAVED with the picks in plain words.
"""
import datetime
import http.server
import json
import os
import socket
import subprocess
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import adcamp_page  # noqa: E402
import styles_lib as L  # noqa: E402

PAGE = os.path.join(ROOT, 'picker')
OUT = os.path.join(ROOT, 'qa', 'start')
LAST = os.path.join(ROOT, 'styles', 'start-last.json')
PICKED = os.path.join(OUT, 'picked.json')
MAX_FX = 4
GROUPS = [
    ('For your words', ['word-stamp', 'giant-captions', 'snap-zoom', 'glass-word', 'quote-card', 'intertitle', 'arrow-note', 'icon-strike']),
    ('For numbers', ['counter', 'pie']),
    ('For lists and steps', ['giant-number', 'list-tracker', 'receipt', 'note-wall']),
    ('For the open and the ask', ['cover-story', 'pinned-line', 'keycaps', 'comment-box']),
    ('For your screenshots', ['page-scroll', 'live-markup', 'highlighter']),
]
ORGANIC_ONLY = {'comment-box'}   # a paid ad sends people to the link, not the comments
NEEDS_SHOT = ('page-scroll', 'live-markup', 'highlighter')   # these need a real screenshot from them (public/proof/)


def catalog():
    return json.load(open(os.path.join(PAGE, 'catalog.json')))


def say(line):
    print(line, flush=True)


def look_in_force(look=None):
    """The look this video is made in: the one asked for ("make it in Big Energy"), else their default, else Clean Talk."""
    asked = L.find(look) if look else None
    if asked and asked.get('hidden') and not asked.get('aliases') and os.environ.get('AVS_HOME'):
        asked = None   # an engine base is not a member's look (make_style.py refuses it too): their own look instead
    return asked or L.by_slug(L.default_slug() or '') or L.by_slug('clean-talk') or {}


def last_picks():
    """styles/start-last.json: the caption style and effects last picked in each look (a one-off "make it in Big
    Energy" never replaces what they tuned for their own look), and the post type, music and color last picked."""
    d = json.load(open(LAST)) if os.path.exists(LAST) else {}
    looks = d.get('looks') or {}
    if not looks and d.get('look'):   # the older shape held one look's picks
        looks = {d['look']: {'captionStyle': d.get('captionStyle'), 'effects': d.get('effects') or []}}
    d = {k: v for k, v in d.items() if k not in ('captionStyle', 'effects', 'look')}
    d['looks'] = looks
    return d


def prefill(look=None):
    """The picks last made in this look, else the look's own: its caption style and up to three of its effects. Post
    type, music and color carry over from last time either way."""
    cat = catalog()
    fx_keys = {e['key'] for e in cat['effects']}
    st = look_in_force(look)
    last = last_picks()
    fx = [k for k in st.get('effects_allowed') or [] if k in fx_keys and k not in ('page-scroll', 'live-markup', 'highlighter')][:3]
    p = {'captionStyle': st.get('captionStyle') or 'lines', 'effects': fx, 'look': st.get('slug'),   # no caption style of its own (cards and panels): the build's own, lines
         'placement': last.get('placement', 'organic'), 'music': last.get('music', 'none'), 'color': last.get('color', 'natural')}
    mine = last['looks'].get(st.get('slug')) or {}
    if mine.get('captionStyle'):
        p['captionStyle'] = mine['captionStyle']
        p['effects'] = [k for k in mine.get('effects') or [] if k in fx_keys][:MAX_FX]
    return p


def colors(video_jpg):
    """The color looks, each shown on a frame of this video (or of the sample when there's no video yet)."""
    idx = json.load(open(os.path.join(ROOT, 'luts', 'luts.json')))
    src = video_jpg if video_jpg and os.path.exists(video_jpg) else os.path.join(PAGE, 'previews', 'styles', 'clean-talk.jpg')
    out = []
    for c in idx:
        jpg = os.path.join(OUT, 'color-%s.jpg' % c['key'])
        vf = 'scale=270:-2' + ('' if c['key'] == 'natural' else ',lut3d=%s' % os.path.join(ROOT, 'luts', c['key'] + '.cube'))
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', src, '-vf', vf, '-q:v', '4', jpg], check=False)
        if os.path.exists(jpg):
            out.append(dict(c, poster='color-%s.jpg' % c['key']))
    return out


def state(video=None, script=None, look=None):
    cat = catalog()
    by = {e['key']: e for e in cat['effects']}
    groups = [{'name': g, 'items': [by[k] for k in keys if k in by]} for g, keys in GROUPS]
    seen = {k for _, keys in GROUPS for k in keys}
    rest = [e for e in cat['effects'] if e['key'] not in seen]
    if rest:
        groups.append({'name': 'More', 'items': rest})
    st = look_in_force(look)
    name = st.get('aliases', [st.get('name')])[0] if st.get('hidden') else st.get('name')
    return {'captions': cat['captions'], 'groups': groups, 'max': MAX_FX, 'picks': prefill(look), 'look': name or 'Clean Talk',
            'colors': colors(os.path.join(OUT, 'this-video.jpg') if video else None),
            'video': os.path.basename(video) if video else None, 'thumb': 'this-video.jpg' if video else None,
            'script': script or ''}


def page(st):
    body = open(os.path.join(PAGE, 'start.html')).read()
    body = body.replace('__TOP__', adcamp_page.top('Video System', 'New video'))
    body = body.replace('__STATE__', json.dumps(st).replace('</', '<\\/'))
    css = open(os.path.join(PAGE, 'picker.css')).read() + open(os.path.join(PAGE, 'start.css')).read()
    return body, css


def build(a, serve_mode=False):
    video = a[a.index('--video') + 1] if '--video' in a else None
    look = a[a.index('--look') + 1] if '--look' in a else None
    script_file = a[a.index('--script') + 1] if '--script' in a else None
    script = open(script_file).read().strip() if script_file and os.path.exists(script_file) else None
    os.makedirs(OUT, exist_ok=True)
    if video and os.path.exists(video):
        import normalize_source   # iPhone HDR footage gets the same tone-map as the cut, so the frame and colors look true
        try:
            trc = next(x.get('color_transfer') for x in normalize_source.probe(video)['streams'] if x.get('codec_type') == 'video')
        except (subprocess.CalledProcessError, StopIteration, ValueError, KeyError):
            trc = None
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', '2', '-i', video, '-frames:v', '1',
                        '-vf', normalize_source.tonemap_vf(trc) + 'scale=360:-2', '-q:v', '4', os.path.join(OUT, 'this-video.jpg')], check=False)
    for f in os.listdir(OUT) if os.path.isdir(OUT) else []:
        if f.startswith('color-') and f.endswith('.jpg'):
            os.remove(os.path.join(OUT, f))
    st = state(video if video and os.path.exists(os.path.join(OUT, 'this-video.jpg')) else None, script, look)
    json.dump({'video': os.path.basename(video) if video else None, 'built': datetime.datetime.now().astimezone().isoformat(timespec='seconds')},
              open(os.path.join(OUT, 'page.json'), 'w'))
    body, css = page(st)
    adcamp_page.write(OUT, 'New Video', body, extra_css=css)
    files = {}
    for it in st['captions'] + [e for g in st['groups'] for e in g['items']]:
        for k in ('preview', 'poster'):
            if it.get(k) and os.path.exists(os.path.join(PAGE, it[k])):
                files[it[k]] = os.path.join(PAGE, it[k])
    if st['thumb']:
        files['this-video.jpg'] = os.path.join(OUT, 'this-video.jpg')
    for c in st['colors']:
        files[c['poster']] = os.path.join(OUT, c['poster'])
    json.dump(['pane.html'] + sorted(files), open(os.path.join(OUT, 'files.json'), 'w'), indent=1)
    json.dump(files, open(os.path.join(OUT, 'files-map.json'), 'w'), indent=1)
    if not serve_mode:
        say('START PAGE READY qa/start/pane.html (%d files, files-map.json is the Artifact tool\'s files)' % len(files))
    return st


def clean(p):
    """The picks the page sent, checked. Raises ValueError with a plain reason."""
    cat = catalog()
    caps = {c['key'] for c in cat['captions']}
    fxs = {e['key'] for e in cat['effects']}
    if p.get('captionStyle') not in caps:
        raise ValueError('pick a caption style')
    placement = 'paid' if p.get('placement') == 'paid' else 'organic'
    fx = [k for k in p.get('effects') or [] if k in fxs]
    ticked = fx[:MAX_FX]   # what they ticked, kept for next time even when this ad leaves one out
    dropped = [k for k in ticked if placement == 'paid' and k in ORGANIC_ONLY]
    fx = [k for k in ticked if k not in dropped]
    music = str(p.get('music') or 'none').strip()[:80] or 'none'
    script = str(p.get('script') or '').strip()[:20000]
    lut = p.get('color') or 'natural'
    if lut not in {c['key'] for c in json.load(open(os.path.join(ROOT, 'luts', 'luts.json')))}:
        raise ValueError('pick one of the color looks')
    look = p.get('look') if L.by_slug(p.get('look') or '') else None
    return {'captionStyle': p['captionStyle'], 'effects': fx, 'placement': placement, 'music': music, 'color': lut, 'look': look,
            'script': script if not p.get('noScript') else '', 'dropped': dropped, 'ticked': ticked,
            'at': datetime.datetime.now().astimezone().isoformat(timespec='seconds')}


def names():
    cat = catalog()
    return {c['key']: c['name'] for c in cat['captions']}, {e['key']: e['name'] for e in cat['effects']}


def saved_line(p):
    cn, fn = names()
    return 'START SAVED captions=%s (%s) effects=%s (%s) color=%s placement=%s music=%s script=%s%s' % (
        p['captionStyle'], cn.get(p['captionStyle']), ','.join(p['effects']) or 'none', ', '.join(fn.get(k, k) for k in p['effects']) or 'none',
        p.get('color', 'natural'), p['placement'], p['music'], ('%d words, first line: %s' % (len(p['script'].split()), p['script'].splitlines()[0][:80])) if p['script'] else 'none',
        (', dropped for a paid ad: %s' % ', '.join(fn.get(k, k) for k in p['dropped'])) if p['dropped'] else '') + (
        ', needs a screenshot from them: %s' % ', '.join(fn.get(k, k) for k in p['effects'] if k in NEEDS_SHOT) if any(k in NEEDS_SHOT for k in p['effects']) else '')


def keep(p):
    os.makedirs(OUT, exist_ok=True)
    json.dump(p, open(PICKED, 'w'), indent=1)
    os.makedirs(os.path.dirname(LAST), exist_ok=True)
    last = last_picks()   # next time's prefill: this look's picks, and the post type, music and color
    last['looks'][p.get('look') or look_in_force().get('slug') or 'clean-talk'] = {'captionStyle': p['captionStyle'], 'effects': p.get('ticked', p['effects'])}
    last.update({k: p.get(k) for k in ('placement', 'music', 'color')})
    json.dump(last, open(LAST, 'w'), indent=1)
    say(saved_line(p))


def read(raw):
    try:
        doc = json.loads(raw)
        page = json.load(open(os.path.join(OUT, 'page.json'))) if os.path.exists(os.path.join(OUT, 'page.json')) else {}
        if page.get('video') and doc.get('video') and doc['video'] != page['video']:
            sys.exit('START STALE: those picks are for %s, the page is for %s. Ask them to press Start on the page.' % (doc['video'], page['video']))
        if page.get('built') and doc.get('at') and str(doc['at'])[:19] < datetime.datetime.fromisoformat(page['built']).astimezone(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%S'):
            sys.exit('START STALE: those picks were saved before this video\'s page was opened. Ask them to press Start on the page.')
        keep(clean(doc))
    except (ValueError, TypeError) as e:
        sys.exit('start_page: that start is not usable (%s)' % e)


def remember(key, value, reel=None):
    """A change made after the start ("make it moodier", other captions) kept for this video, so a later restyle puts it
    back on instead of the start page's pick (qa/<reel>/start.json), and carried into next time's prefill."""
    sp = os.path.join(ROOT, 'qa', reel, 'start.json') if reel else None
    picks = json.load(open(sp)) if sp and os.path.exists(sp) else None
    if picks is not None:
        picks[key] = value
        json.dump(picks, open(sp, 'w'), indent=1)
    if reel and key == 'color':
        import reel_config
        if os.path.exists(reel_config.config_path(reel)):
            set_color(reel, value)   # on the video too, with its grade trimmed to match
    p = last_picks()
    if key == 'captionStyle':
        look = (picks or {}).get('look') or look_in_force().get('slug') or 'clean-talk'
        p['looks'].setdefault(look, {'effects': (picks or {}).get('ticked') or (picks or {}).get('effects') or []})['captionStyle'] = value
    else:
        p[key] = value
    os.makedirs(os.path.dirname(LAST), exist_ok=True)
    json.dump(p, open(LAST, 'w'), indent=1)
    say('remembered %s=%s %s' % (key, value, 'for %s and the next start page' % reel if picks is not None else 'for the next start page'))


def use(name):
    if not os.path.exists(PICKED):
        sys.exit('start_page: nothing picked yet (the start page saves it)')
    p = json.load(open(PICKED))
    os.makedirs(os.path.join(ROOT, 'qa', name), exist_ok=True)
    json.dump(p, open(os.path.join(ROOT, 'qa', name, 'start.json'), 'w'), indent=1)
    sp = os.path.join(ROOT, 'script', name + '.txt')
    if p.get('script'):
        os.makedirs(os.path.dirname(sp), exist_ok=True)
        open(sp, 'w').write(p['script'].strip() + '\n')
        say('SCRIPT WRITTEN script/%s.txt (%d words). Check it matches what was said before the cut.' % (name, len(p['script'].split())))
    else:
        say('NO SCRIPT: write script/%s.txt from what was said (the skill\'s step 1).' % name)
    say('placement=%s music=%s' % (p['placement'], p['music']))


def set_color(name, lut):
    """The color look on a video's config. A color look replaces the grade's color (the vignette and grain stay), and
    back to natural brings the look's own grade back."""
    import reel_config
    path = reel_config.config_path(name)
    cfg = reel_config.load(name)
    if (cfg.get('color') or 'natural') == lut:
        return
    s = L.set_key(open(path).read(), 'color', lut, 'the color look (scripts/color_lut.py grades the footage)')
    g = {k: v for k, v in (cfg.get('grade') or {}).items() if k in ('vignette', 'film')}
    look = L.by_slug((cfg.get('meta') or {}).get('look') or '') or {}
    if lut != 'natural':
        s = L.set_key(s, 'grade', g, 'only the vignette and grain: the color look sets the color') if g else L.remove_key(s, 'grade')
    elif look.get('grade'):
        s = L.set_key(s, 'grade', look['grade'], 'the look\'s own grade (no color look)')
    open(path, 'w').write(s)


def apply(name):
    """Their caption style on the video (after the first build and its look), and the effects to place."""
    import reel_config
    sp = os.path.join(ROOT, 'qa', name, 'start.json')
    if not os.path.exists(sp):
        sys.exit('start_page: %s has no start picks (start_page.py use %s first)' % (name, name))
    p = json.load(open(sp))
    path = reel_config.config_path(name)
    cfg = reel_config.load(name)
    s = open(path).read()
    cn, fn = names()
    if (cfg.get('captionStyle') or 'lines') != p['captionStyle']:
        s = L.set_key(s, 'captionStyle', p['captionStyle'], 'picked on the start page')
        look = dict(cfg.get('look') or {})
        caps = look.pop('captions', None)
        if caps is not None:   # the look's type was tuned for its own caption style
            if caps.get('money'):   # money green is a color choice, not the type: it stays with any caption style
                look['captions'] = {'money': caps['money']}
            s = L.set_key(s, 'look', look, 'the look without its caption type: the picked caption style uses its own') if look else L.remove_key(s, 'look')
        open(path, 'w').write(s)
        say('captions: %s (picked), in your brand fonts and color' % cn.get(p['captionStyle']))
    else:
        say('captions: %s (as in the look)' % cn.get(p['captionStyle']))
    lut = p.get('color') or 'natural'
    set_color(name, lut)
    say('color: %s' % lut)
    say('PLACE %s' % (', '.join('%s (%s)' % (k, fn.get(k, k)) for k in p['effects']) or 'none: captions only'))


def serve(a):
    """The page in a browser tab: Start posts the picks here, then this stops (START SAVED is the cue)."""
    body, css = page(build(a, serve_mode=True))
    doc = adcamp_page.document('New Video', body, extra_css=css).encode()
    stop = threading.Event()

    class H(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *x, **kw):
            super().__init__(*x, directory=PAGE, **kw)

        def log_message(self, *x):
            pass

        def do_GET(self):
            if not adcamp_page.local_host_ok(self):
                return self.send_error(403)
            path = self.path.split('?')[0]
            if path in ('/', '/index.html'):
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Content-Length', str(len(doc)))
                self.end_headers()
                self.wfile.write(doc)
                return
            if path == '/this-video.jpg' or (path.startswith('/color-') and path.endswith('.jpg') and '/' not in path[1:]):
                self.directory = OUT
            elif not path.startswith('/previews/') or '..' in path:
                return self.send_error(404)
            rng = self.headers.get('Range')
            if rng and path.endswith('.mp4'):   # Safari plays video only through byte ranges
                fp = self.translate_path(path)
                return adcamp_page.send_range(self, fp, rng) if os.path.isfile(fp) else self.send_error(404)
            return super().do_GET()

        def do_POST(self):
            if self.path != '/api/start':
                return self.send_error(404)
            if not adcamp_page.local_post_ok(self):   # only the page itself, never another website in the same browser
                return self.send_error(403)
            n = int(self.headers.get('Content-Length') or 0)
            try:
                keep(clean(json.loads(self.rfile.read(min(n, 65536)))))
            except (ValueError, TypeError) as e:
                body = json.dumps({'error': str(e)}).encode()
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(body)
                return
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"ok": true}')
            threading.Timer(1.5, stop.set).start()

    port = 8781
    for p in range(8781, 8801):
        with socket.socket() as sk:
            try:
                sk.bind(('127.0.0.1', p))
                port = p
                break
            except OSError:
                continue
    srv = http.server.ThreadingHTTPServer(('127.0.0.1', port), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    say('START PAGE http://127.0.0.1:%d/' % port)
    if '--no-open' not in a:
        subprocess.run(['open', 'http://127.0.0.1:%d/' % port], check=False)
    t0 = time.time()
    while not stop.wait(5):
        if time.time() - t0 > 3600:
            say('START PAGE CLOSED (no start for an hour)')
            break
    srv.shutdown()


def main():
    a = sys.argv[1:]
    if not a or a[0] not in ('build', 'serve', 'read', 'use', 'apply', 'remember'):
        sys.exit(__doc__)
    if a[0] == 'build':
        build(a)
    elif a[0] == 'serve':
        serve(a)
    elif a[0] == 'read' and len(a) > 1:
        if a[1] == '--last':   # "same as last time" or "just go": the page's own prefill, plus the inbox script if any
            look = a[a.index('--look') + 1] if '--look' in a else None
            p = prefill(look)
            sf = a[a.index('--script') + 1] if '--script' in a else None
            p['script'] = open(sf).read() if sf and os.path.exists(sf) else ''
            keep(clean(p))
        elif a[1] == '--file':   # the start/current document saved to a file (a script's apostrophes never meet the shell)
            read(open(a[2]).read())
        else:
            read(a[1])
    elif a[0] == 'remember' and ('--color' in a or '--captions' in a):
        reel = a[a.index('--reel') + 1] if '--reel' in a and a.index('--reel') + 1 < len(a) else None
        if '--color' in a:
            key = a[a.index('--color') + 1] if a.index('--color') + 1 < len(a) else ''
            if key not in {c['key'] for c in json.load(open(os.path.join(ROOT, 'luts', 'luts.json')))}:
                sys.exit('start_page: "%s" is not one of the color looks' % key)
            remember('color', key, reel)
        if '--captions' in a:
            key = a[a.index('--captions') + 1] if a.index('--captions') + 1 < len(a) else ''
            if key not in {c['key'] for c in catalog()['captions']}:
                sys.exit('start_page: "%s" is not one of the caption styles' % key)
            remember('captionStyle', key, reel)
    elif a[0] in ('use', 'apply') and len(a) > 1:
        (use if a[0] == 'use' else apply)(a[1])
    else:
        sys.exit(__doc__)


if __name__ == '__main__':
    main()

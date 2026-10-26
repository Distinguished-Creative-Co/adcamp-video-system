#!/usr/bin/env python3
"""The Picker: a page on this Mac to choose a look by watching it. Pick a ready style, or mix your own
caption style, effects and transitions, and optionally a font pair, then Save. Standard library only.

    python3 scripts/picker.py [--port 8771] [--no-open] [--until-saved]
    python3 scripts/picker.py --pane      the same page for the Claude app's pane: writes qa/picker/ and stops
    python3 scripts/picker.py --from-store '<the picks/current document as JSON>'   a pane pick into styles/picks.json

--pane writes qa/picker/pane.html with the catalog inside the page, and files.json (the page plus every preview clip
under the path the page uses). Publish pane.html with those files and capabilities {"db": {}, "user": {}}. Save my pick
then writes one document, picks/current, into the page's own store (read it with ArtifactData: collection "picks",
doc "current") in the same shape as styles/picks.json below; write it there before my_styles.py save --from-picks.

Prints one line per event, for Claude to read:
    PICKER READY http://127.0.0.1:8771/
    PICKS SAVED styles/picks.json mode=mix captions=pill effects=keycaps,counter transitions=flash parts=off fonts=pair-3
    PICKER CLOSED
--until-saved stops it right after a save (and after 30 minutes without a visit either way). It answers only
on 127.0.0.1, only to requests addressed to this computer, and serves only the picker's own files.

styles/picks.json:
    {"mode": "style" | "mix", "style": "<slug>" | null, "captionStyle": "<key>" | null,
     "effects": ["<key>", ...], "parts": null | {"<effect key>": ["hook", "middle", "end"]},
     "transitions": ["<key>", ...], "fonts": null | {"key": "pair-N", "sans": "<sans>", "serif": "<serif>"},
     "updated": "<ISO time>"}
A "style" pick names a ready style (built in or saved). A "mix" pick is turned into a saved style with
scripts/my_styles.py save "<name>" --from-picks. A font pick (either mode) goes into src/brand.json, so every
video, card and carousel uses it.
"""
import datetime
import http.server
import json
import os
import re
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
PICKS = os.path.join(ROOT, 'styles', 'picks.json')
PARTS = ('hook', 'middle', 'end')
IDLE = 1800


def say(line):
    print(line, flush=True)


def catalog():
    return json.load(open(os.path.join(PAGE, 'catalog.json')))


def state():
    cat = catalog()
    mine = [{'key': s['slug'], 'name': s['name'], 'line': (s.get('summary') or 'Your saved style, built %s.' % s.get('created', '')).strip(),
             'preview': None, 'poster': None, 'mine': True} for s in L.all_styles() if not s.get('builtin')]
    for s in mine:
        for f, k in (('sample.mp4', 'preview'), ('sample.jpg', 'poster')):
            if os.path.exists(os.path.join(L.style_dir(s['key']), f)):
                s[k] = 'styles/%s/%s' % (s['key'], f)
    brand = {}
    try:
        brand = json.load(open(os.path.join(ROOT, 'src', 'brand.json')))
    except (OSError, ValueError):
        pass
    picks = json.load(open(PICKS)) if os.path.exists(PICKS) else None
    return {'catalog': cat, 'mine': mine, 'default': L.default_slug(), 'accent': brand.get('accent', '#F7C715'), 'picks': picks,
            'fonts': {'sans': brand.get('sans'), 'serif': brand.get('serif')}}


def clean(p):
    """The picks the page sent, checked against the catalog. Raises ValueError with a plain reason."""
    cat = catalog()
    keys = {g: {i['key'] for i in cat[g]} for g in cat}
    styles = keys['styles'] | {s['slug'] for s in L.all_styles()}
    mode = p.get('mode')
    if mode not in ('style', 'mix'):
        raise ValueError('mode must be style or mix')
    out = {'mode': mode, 'style': None, 'captionStyle': None, 'effects': [], 'parts': None, 'transitions': [], 'fonts': None}
    if p.get('fonts'):
        pair = next((f for f in cat.get('fonts', []) if f['key'] == p['fonts']), None)
        if not pair:
            raise ValueError('pick one of the font pairs')
        out['fonts'] = {'key': pair['key'], 'sans': pair['sans'], 'serif': pair['serif']}
    if mode == 'style':
        if p.get('style') not in styles:
            raise ValueError('pick one style')
        out['style'] = p['style']
    else:
        if p.get('captionStyle') not in keys['captions']:
            raise ValueError('pick a caption style')
        out['captionStyle'] = p['captionStyle']
        out['effects'] = [k for k in p.get('effects') or [] if k in keys['effects']]
        out['transitions'] = [k for k in p.get('transitions') or [] if k in keys['transitions']]
        parts = p.get('parts')
        if isinstance(parts, dict):
            out['parts'] = {k: [x for x in v if x in PARTS] for k, v in parts.items() if k in out['effects'] and isinstance(v, list) and v}
            out['parts'] = out['parts'] or None
    out['updated'] = datetime.datetime.now().astimezone().isoformat(timespec='seconds')
    return out


def free_port(start):
    for port in range(start, start + 20):
        with socket.socket() as s:
            try:
                s.bind(('127.0.0.1', port))
                return port
            except OSError:
                continue
    sys.exit('picker: no free port near %d' % start)


def page(embedded=None):
    """The Picker page from picker/page.html on the AdCamp kit. embedded: the state, for the pane build."""
    body = open(os.path.join(PAGE, 'page.html')).read()
    body = body.replace('__TOP__', adcamp_page.top('Video System', 'The Picker'))
    body = body.replace('__STATE__', json.dumps(embedded).replace('</', '<\\/') if embedded is not None else '')
    return body, open(os.path.join(PAGE, 'picker.css')).read()


def pane():
    out = os.path.join(ROOT, 'qa', 'picker')
    st = state()
    body, css = page(st)
    adcamp_page.write(out, 'The Picker', body, extra_css=css)
    files = {}
    for group in ('styles', 'captions', 'effects', 'transitions', 'fonts'):
        for it in st['catalog'].get(group, []):
            for k in ('preview', 'poster'):
                if it.get(k):
                    files[it[k]] = os.path.relpath(os.path.join(PAGE, it[k]), ROOT)
    for it in st['mine']:
        for k in ('preview', 'poster'):
            if it.get(k):
                files[it[k]] = it[k]
    files = {k: os.path.join(ROOT, v) for k, v in files.items() if os.path.exists(os.path.join(ROOT, v))}
    json.dump(['pane.html'] + sorted(files), open(os.path.join(out, 'files.json'), 'w'), indent=1)
    json.dump(files, open(os.path.join(out, 'files-map.json'), 'w'), indent=1)
    json.dump({'built': datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')},
              open(os.path.join(out, 'page.json'), 'w'))   # a pick saved before this opening is last time's
    size = sum(os.path.getsize(v) for v in files.values())
    say('PANE READY qa/picker/pane.html (%d files, %.1f MB, qa/picker/files-map.json maps each published path to its file)'
        % (len(files), size / 1e6))


def from_store(raw):
    """A pick saved in the pane (the picks/current document, as JSON) into styles/picks.json, checked like a local Save."""
    try:
        doc = json.loads(raw)
        built = os.path.join(ROOT, 'qa', 'picker', 'page.json')
        if doc.get('updated') and os.path.exists(built):
            saved = datetime.datetime.fromisoformat(str(doc['updated']).replace('Z', '+00:00'))
            opened = datetime.datetime.fromisoformat(json.load(open(built))['built'])
            if saved < opened - datetime.timedelta(minutes=2):   # a little slack for a phone's clock
                sys.exit('PICKS STALE: that pick was saved before this Picker opened. Ask them to press Save my pick on the page.')
        picks = clean(doc)
    except (ValueError, TypeError, KeyError) as e:
        sys.exit('picker: that pick is not usable (%s)' % e)
    os.makedirs(os.path.dirname(PICKS), exist_ok=True)
    json.dump(picks, open(PICKS, 'w'), indent=1)
    say(saved_line(picks))


def saved_line(picks):
    parts = 'off' if not picks['parts'] else ','.join('%s:%s' % (k, '+'.join(v)) for k, v in picks['parts'].items())
    fonts = picks['fonts']['key'] if picks['fonts'] else 'none'
    if picks['mode'] == 'style':
        return 'PICKS SAVED %s mode=style style=%s fonts=%s' % (os.path.relpath(PICKS, ROOT), picks['style'], fonts)
    return 'PICKS SAVED %s mode=mix captions=%s effects=%s transitions=%s parts=%s fonts=%s' % (
        os.path.relpath(PICKS, ROOT), picks['captionStyle'], ','.join(picks['effects']) or 'none',
        ','.join(picks['transitions']) or 'none', parts, fonts)


def main():
    a = sys.argv[1:]
    if '--pane' in a:
        return pane()
    if '--from-store' in a:
        return from_store(a[a.index('--from-store') + 1])
    port = free_port(int(a[a.index('--port') + 1]) if '--port' in a else 8771)
    until_saved = '--until-saved' in a
    last = {'t': time.time()}
    stop = threading.Event()

    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *x, **kw):
            super().__init__(*x, directory=ROOT, **kw)

        def log_message(self, *x):
            pass

        def local(self):
            host = (self.headers.get('Host') or '').split(':')[0]
            return host in ('127.0.0.1', 'localhost')

        def send_json(self, code, obj):
            body = json.dumps(obj).encode()
            self.send_response(code)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            last['t'] = time.time()
            if not self.local():
                return self.send_error(403)
            path = self.path.split('?')[0]
            if path in ('/', '/index.html'):
                body, css = page()
                doc = adcamp_page.document('The Picker', body, extra_css=css).encode()
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Content-Length', str(len(doc)))
                self.send_header('Cache-Control', 'no-store')
                self.end_headers()
                self.wfile.write(doc)
                return
            elif path == '/api/state':
                return self.send_json(200, state())
            elif path.startswith('/previews/'):
                self.path = '/picker' + path
            elif path.startswith('/styles/') and path.endswith(('/sample.mp4', '/sample.jpg')) and '..' not in path:
                pass
            else:
                return self.send_error(404)
            rng = self.headers.get('Range')
            if rng and self.path.endswith('.mp4'):   # Safari plays video only through byte ranges
                return self.send_range(rng)
            return super().do_GET()

        def send_range(self, rng):
            fp = self.translate_path(self.path.split('?')[0])
            if not os.path.isfile(fp):
                return self.send_error(404)
            size = os.path.getsize(fp)
            m = re.match(r'bytes=(\d*)-(\d*)', rng)
            if not m:
                return self.send_error(416)
            a = int(m.group(1)) if m.group(1) else max(0, size - int(m.group(2) or 0))
            b = int(m.group(2)) if m.group(1) and m.group(2) else size - 1
            b = min(b, size - 1)
            if a > b:
                return self.send_error(416)
            self.send_response(206)
            self.send_header('Content-Type', 'video/mp4')
            self.send_header('Accept-Ranges', 'bytes')
            self.send_header('Content-Range', 'bytes %d-%d/%d' % (a, b, size))
            self.send_header('Content-Length', str(b - a + 1))
            self.end_headers()
            with open(fp, 'rb') as f:
                f.seek(a)
                self.wfile.write(f.read(b - a + 1))

        def do_POST(self):
            last['t'] = time.time()
            if not adcamp_page.local_post_ok(self) or self.path != '/api/picks':   # only the page itself
                return self.send_error(403)
            n = int(self.headers.get('Content-Length') or 0)
            if n <= 0 or n > 32768:
                return self.send_json(400, {'error': 'empty or too large'})
            try:
                picks = clean(json.loads(self.rfile.read(n)))
            except (ValueError, TypeError) as e:
                return self.send_json(400, {'error': str(e)})
            os.makedirs(os.path.dirname(PICKS), exist_ok=True)
            json.dump(picks, open(PICKS, 'w'), indent=1)
            say(saved_line(picks))
            self.send_json(200, {'ok': True})
            if until_saved:
                threading.Timer(1.5, stop.set).start()

    srv = http.server.ThreadingHTTPServer(('127.0.0.1', port), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = 'http://127.0.0.1:%d/' % port
    say('PICKER READY %s' % url)
    if '--no-open' not in a:
        subprocess.run(['open', url], check=False)
    try:
        while not stop.wait(5):
            if time.time() - last['t'] > IDLE:
                break
    except KeyboardInterrupt:
        pass
    srv.shutdown()
    say('PICKER CLOSED')


if __name__ == '__main__':
    main()

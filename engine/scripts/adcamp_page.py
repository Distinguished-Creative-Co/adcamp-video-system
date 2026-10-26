#!/usr/bin/env python3
"""The AdCamp look for every page AVS shows a member: the storyboard, the style board, the Picker and carousel
slides. Same tokens as joinadcamp.com (near black, one yellow, Anton for display, Archivo for reading).

Each page is written twice from one body:
  - pane.html   for the Claude app's pane beside the chat (the Artifact tool adds the doctype, head and body)
  - index.html  a whole document for a local browser tab (the fallback when the session has no Artifact tool)

    import adcamp_page as A
    A.write(folder, title, body, extra_css='', fonts=())
"""
import os

FONTS = ('Anton', 'Archivo:wght@400;500;600;700;800')

CSS = r'''
/* AdCamp: one dark world, one yellow. Display in Anton capitals, reading in Archivo. */
:root {
  color-scheme: dark;
  --ink: #0B0B0B; --card: #141414; --inner: #181818; --panel: #101010;
  --line: #2A2A2A; --line-2: #3A3A3A; --hair: #1F1F1F;
  --yellow: #FFD000; --yellow-hover: #FFE45C; --yellow-wash: rgba(255,208,0,0.08); --yellow-edge: rgba(255,208,0,0.35);
  --t-white: #FFFFFF; --t-body: #CFCFCF; --t-sub: #A8A8A8; --t-foot: #8A8A8A;
  --f-display: 'Anton', Impact, 'Arial Narrow', sans-serif;
  --f-body: 'Archivo', 'Helvetica Neue', Arial, sans-serif;
  --r-pill: 999px; --r-card: 16px; --r-inner: 14px;
}
*, *::before, *::after { box-sizing: border-box; }
body { margin: 0; background: var(--ink); color: var(--t-white); font: 400 15px/1.55 var(--f-body); -webkit-font-smoothing: antialiased; }
img, video { max-width: 100%; display: block; }
[hidden] { display: none !important; }
a { color: var(--yellow); }
:focus-visible { outline: 3px solid var(--yellow); outline-offset: 3px; }
::selection { background: var(--yellow); color: var(--ink); }
.page { max-width: 1080px; margin: 0 auto; padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); padding-block: 20px 72px; display: grid; gap: 22px; }
.page > * { min-width: 0; }

/* Top bar: wordmark left, a status pill right */
.top { display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap; }
.mark { font-family: var(--f-display); font-size: 24px; letter-spacing: 0.01em; line-height: 1; text-transform: uppercase; }
.mark b { font-weight: 400; color: var(--yellow); }
.mark small { font-family: var(--f-body); font-size: 11px; font-weight: 800; letter-spacing: 0.18em; color: var(--t-sub); margin-left: 10px; vertical-align: 3px; }
.pill { display: inline-flex; align-items: center; gap: 8px; font-size: 12px; font-weight: 700; letter-spacing: 0.16em; text-transform: uppercase; border: 1px solid var(--line-2); background: rgba(20,20,20,0.7); padding: 8px 14px; border-radius: var(--r-pill); color: #D6D6D6; font-variant-numeric: tabular-nums; }
.dot { width: 8px; height: 8px; border-radius: 50%; background: var(--yellow); display: inline-block; }

/* Hero: dot grid and a yellow glow from above */
.hero { position: relative; overflow: hidden; border-radius: 20px; padding: 40px 28px 34px; background: var(--panel); border: 1px solid var(--hair); display: grid; gap: 14px; justify-items: start; }
.hero::before { content: ""; position: absolute; inset: 0; background-image: radial-gradient(rgba(255,255,255,0.12) 1px, transparent 1px); background-size: 22px 22px; -webkit-mask-image: radial-gradient(ellipse 80% 90% at 30% 0%, #000 25%, transparent 75%); mask-image: radial-gradient(ellipse 80% 90% at 30% 0%, #000 25%, transparent 75%); pointer-events: none; }
.hero::after { content: ""; position: absolute; width: 760px; height: 760px; left: 20%; top: -520px; background: radial-gradient(circle, rgba(255,208,0,0.24), rgba(255,208,0,0) 62%); pointer-events: none; }
.hero > * { position: relative; z-index: 1; }
.eyebrow-pill { display: inline-flex; align-items: center; gap: 10px; font-size: 12px; font-weight: 800; letter-spacing: 0.18em; text-transform: uppercase; color: var(--yellow); border: 1px solid var(--yellow-edge); background: var(--yellow-wash); padding: 7px 14px; border-radius: var(--r-pill); }
h1, h2, .display { font-family: var(--f-display); font-weight: 400; text-transform: uppercase; letter-spacing: 0.005em; text-wrap: balance; margin: 0; }
h1 { font-size: clamp(40px, 8vw, 76px); line-height: 0.95; }
h1 .y, h2 .y { color: var(--yellow); text-shadow: 0 0 36px rgba(255,208,0,0.45); }
h2 { font-size: clamp(26px, 4.4vw, 38px); line-height: 1; }
.lede { margin: 0; max-width: 62ch; font-size: 17px; line-height: 1.55; color: var(--t-body); }
.eyebrow { font-size: 12px; font-weight: 800; letter-spacing: 0.18em; text-transform: uppercase; color: var(--yellow); }
.label { font-size: 11px; font-weight: 800; letter-spacing: 0.16em; text-transform: uppercase; color: var(--t-sub); margin: 0 0 6px; }

/* Cards */
.card { background: var(--card); border: 1px solid var(--line); border-radius: var(--r-card); padding: 20px; display: grid; gap: 12px; }
.card.lift { transition: border-color .2s ease, box-shadow .2s ease, transform .2s ease; }
.card.lift:hover { border-color: rgba(255,208,0,0.7); box-shadow: 0 0 0 1px rgba(255,208,0,0.25), 0 18px 50px rgba(255,208,0,0.12); }
.card.need { background: radial-gradient(ellipse 80% 120% at 0% 0%, rgba(255,208,0,0.12), rgba(255,208,0,0) 55%), var(--panel); border-color: var(--yellow-edge); }
.inner { background: var(--inner); border: 1px solid #2E2E2E; border-radius: var(--r-inner); padding: 14px 16px; }
.chip { display: inline-flex; align-items: center; font-size: 12px; font-weight: 800; letter-spacing: 0.14em; text-transform: uppercase; padding: 5px 10px; border-radius: 6px; background: var(--yellow); color: var(--ink); font-variant-numeric: tabular-nums; }
.muted { color: var(--t-sub); }
.foot { color: var(--t-foot); font-size: 13px; }
ul.list { margin: 0; padding-left: 18px; color: var(--t-body); }
ul.list li + li { margin-top: 2px; }

/* Buttons */
.btn { display: inline-flex; align-items: center; justify-content: center; gap: 8px; min-height: 44px; padding: 0 22px; border-radius: var(--r-pill); font: 800 14px/1 var(--f-body); letter-spacing: 0.06em; text-transform: uppercase; cursor: pointer; border: 0; text-decoration: none; transition: transform .15s ease, box-shadow .15s ease; }
.btn-y { background: var(--yellow); color: var(--ink); }
.btn-y:hover { transform: translateY(-2px); box-shadow: 0 0 0 4px rgba(255,208,0,0.25), 0 12px 40px rgba(255,208,0,0.4); }
.btn-ghost { background: rgba(20,20,20,0.6); color: var(--t-white); border: 1px solid var(--line-2); }
.btn-ghost:hover { transform: translateY(-2px); box-shadow: 0 0 0 4px rgba(255,255,255,0.12); }
.btn[disabled] { opacity: .5; cursor: default; transform: none; box-shadow: none; }
textarea, input[type=text] { width: 100%; font: inherit; color: var(--t-white); background: var(--inner); border: 1px solid #2E2E2E; border-radius: 12px; padding: 10px 12px; resize: vertical; }
textarea::placeholder { color: var(--t-foot); }

@media (max-width: 640px) { .hero { padding: 28px 18px 24px; } .card { padding: 16px; } }
@media (prefers-reduced-motion: reduce) { .card.lift, .btn { transition: none; } .btn:hover, .card.lift:hover { transform: none; } }
'''


def font_link(fonts=()):
    fams = list(FONTS) + [f for f in fonts if f]
    q = '&'.join('family=' + f.replace(' ', '+') for f in dict.fromkeys(fams))
    return ('<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
            '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?%s&display=swap">' % q)


def fragment(title, body, extra_css='', fonts=()):
    """The page as the pane takes it: title and style first, no doctype, head or body tags."""
    return ('<title>%s</title>\n<meta name="claude:viewport-fit-sides" content="cover">\n%s\n<style>%s%s</style>\n%s\n'
            % (title, font_link(fonts), CSS, extra_css, body))


def document(title, body, extra_css='', fonts=()):
    """The same page as a whole document, for a local browser tab."""
    return ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n%s</head>\n<body>\n%s</body>\n</html>\n'
            % (fragment(title, '', extra_css, fonts), body))


def write(folder, title, body, extra_css='', fonts=(), pane_body=None):
    """Write pane.html and index.html into folder. pane_body: a different body for the pane (no local-only controls)."""
    os.makedirs(folder, exist_ok=True)
    open(os.path.join(folder, 'pane.html'), 'w').write(fragment(title, pane_body if pane_body is not None else body, extra_css, fonts))
    open(os.path.join(folder, 'index.html'), 'w').write(document(title, body, extra_css, fonts))


def top(label, status):
    """The AdCamp wordmark and a status pill, the top of every page."""
    return ('<div class="top"><div class="mark">Ad<b>Camp</b><small>Video System</small></div>'
            '<span class="pill"><span class="dot" aria-hidden="true"></span>%s</span></div>' % status) if label is None else \
           ('<div class="top"><div class="mark">Ad<b>Camp</b><small>%s</small></div>'
            '<span class="pill"><span class="dot" aria-hidden="true"></span>%s</span></div>' % (label, status))


def files_map(folder, published):
    """files.json (what the page publishes) and files-map.json ({published path: absolute source}): the map is the
    Artifact tool's `files` argument as it is. published: paths relative to folder, the page first."""
    import json
    json.dump(['pane.html'] + list(published), open(os.path.join(folder, 'files.json'), 'w'), indent=1)
    json.dump({p: os.path.abspath(os.path.join(folder, p)) for p in published}, open(os.path.join(folder, 'files-map.json'), 'w'), indent=1)


def local_host_ok(handler):
    """A request to a local page's server names this Mac as its host (a page elsewhere that points a name at this Mac
    gets nothing: the start page holds their script)."""
    return (handler.headers.get('Host') or '').split(':')[0] in ('127.0.0.1', 'localhost')


def local_post_ok(handler):
    """A POST to one of the local pages' servers is theirs only when it comes from that page: the Host is this Mac, the
    body is JSON (another website can't send JSON here without the browser asking first, and nothing here says yes),
    and any Origin is this same local address. Keeps a site open in the same browser from writing their picks or notes."""
    host = handler.headers.get('Host') or ''
    if not local_host_ok(handler):
        return False
    if not (handler.headers.get('Content-Type') or '').lower().startswith('application/json'):
        return False
    origin = handler.headers.get('Origin')
    if origin:   # a browser always names where a POST comes from
        port = host.split(':')[1] if ':' in host else '80'
        return origin in ('http://127.0.0.1:%s' % port, 'http://localhost:%s' % port)
    return handler.headers.get('Sec-Fetch-Site', 'same-origin') in ('same-origin', 'none')


def send_range(handler, fp, rng):
    """Answer a byte-range request for a video file (Safari plays video only through ranges)."""
    import re
    size = os.path.getsize(fp)
    m = re.match(r'bytes=(\d*)-(\d*)', rng or '')
    if not m:
        return handler.send_error(416)
    a = int(m.group(1)) if m.group(1) else max(0, size - int(m.group(2) or 0))
    b = min(int(m.group(2)) if m.group(1) and m.group(2) else size - 1, size - 1)
    if a > b:
        return handler.send_error(416)
    handler.send_response(206)
    handler.send_header('Content-Type', 'video/mp4')
    handler.send_header('Accept-Ranges', 'bytes')
    handler.send_header('Content-Range', 'bytes %d-%d/%d' % (a, b, size))
    handler.send_header('Content-Length', str(b - a + 1))
    handler.end_headers()
    with open(fp, 'rb') as f:
        f.seek(a)
        handler.wfile.write(f.read(b - a + 1))


def stage(folder, dest):
    """Copy a page and every file it shows into dest under their published paths, for a session whose working folder
    doesn't hold ~/AVS (the Artifact tool takes files only from the working folder or the scratchpad). Writes
    dest/files-map.json and returns the path of the copied pane.html."""
    import json
    import shutil
    m = json.load(open(os.path.join(folder, 'files-map.json')))
    os.makedirs(dest, exist_ok=True)
    shutil.copyfile(os.path.join(folder, 'pane.html'), os.path.join(dest, 'pane.html'))
    out = {}
    for pub, src in m.items():
        d = os.path.join(dest, pub)
        os.makedirs(os.path.dirname(d), exist_ok=True)
        shutil.copyfile(src, d)
        out[pub] = os.path.abspath(d)
    json.dump(out, open(os.path.join(dest, 'files-map.json'), 'w'), indent=1)
    return os.path.join(dest, 'pane.html')


if __name__ == '__main__':
    import sys
    if len(sys.argv) == 4 and sys.argv[1] == 'stage':   # python3 scripts/adcamp_page.py stage <page folder> <scratch folder>
        print('STAGED %s (files-map.json beside it)' % stage(sys.argv[2], sys.argv[3]))
    else:
        sys.exit('usage: python3 scripts/adcamp_page.py stage <page folder> <scratch folder>')

#!/usr/bin/env python3
"""The storyboard: the preview as a page the person reads and leaves notes on, before anything renders.

    python3 scripts/storyboard.py <name>        after the preview stills exist (make_reel.sh --preview)

One row per beat (each scene of the reel): its time, real preview stills, the words said, what moves
on screen (panels, words behind the host, inserts), what you hear, and a box for a note. On top, what
the edit still needs from the person ("needs" in the config), if anything. Colours and font come from
src/brand.json, so the page looks like their reels.

Writes qa/<name>/storyboard/index.html with its stills beside it. Two ways to review it:
  - Claude artifacts: publish index.html with the frames/ folder and comments turned on; each comment
    names its beat in the text ("b03: ...")
  - anywhere: python3 scripts/review_server.py <name>, open the address it prints, leave notes, press
    "Looks good, render it". Notes land in qa/<name>/storyboard/notes.json.
"""
import html
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import reel_config  # noqa: E402

FPS = 30
SOUND_WORDS = {'transition_whoosh': 'whoosh', 'element_land': 'soft land', 'state_change': 'click', 'back_text_hit': 'impact',
               'insert_pop': 'pop', 'cta_ding': 'ding', 'cta_riser': 'riser'}


def tc(f):
    s = f / FPS
    return '%d:%04.1f' % (s // 60, s % 60)


def beats(cfg):
    sc = sorted(cfg['scenes'], key=lambda s: s['from'])
    out = []
    for i, s in enumerate(sc):
        a = s['from']
        b = sc[i + 1]['from'] if i + 1 < len(sc) else cfg['frames']
        out.append({'id': 'b%02d' % (i + 1), 'from': a, 'to': b, 'mode': s['mode'], 'tone': s.get('tone')})
    return out


def overlaps(x, a, b):
    return x['in'] < b and a < x['out']


def what_moves(cfg, bt):
    a, b = bt['from'], bt['to']
    out = []
    if bt['mode'] == 'full':
        out.append('You full screen' + (', punched in at the open' if a == 0 and (cfg.get('open') or {}).get('scale', 1) > 1 else ''))
    else:
        out.append('You in the glass card on a %s stage, captions above' % (bt.get('tone') or 'dark'))
    for t in cfg.get('backText') or []:
        if overlaps(t, a, b):
            out.append('Big words behind you: %s' % t['text'])
    for s in cfg.get('swaps') or []:
        if overlaps(s, a, b):
            k = s['content']['kind']
            label = {'cta': 'Call-to-action card', 'stat': 'Stat panel', 'shot': 'Proof screenshot', 'checklist': 'Checklist',
                     'funnel': 'Funnel', 'decision': 'Decision'}.get(k, k)
            extra = s['content'].get('title') or s['content'].get('value') or s.get('kicker') or ''
            out.append('%s slides in at %s%s' % (label, tc(s['in']), (': ' + extra) if extra else ''))
    for n in cfg.get('inserts') or []:
        if overlaps(n, a, b):
            out.append('Follow card' if n['kind'] == 'follow' else 'Your clip %s%s' % (n['src'], (' ("%s")' % n['label']) if n.get('label') else ''))
    for e in cfg.get('effects') or []:
        if e['kind'] == 'transition':
            if a <= e['at'] < b:
                out.append('%s transition at %s' % (e['style'].capitalize(), tc(e['at'])))
        elif overlaps(e, a, b):
            detail = e.get('word') or e.get('label') or e.get('keys') or e.get('text') or e.get('value') or ''
            out.append('Effect: %s%s at %s' % (e['kind'].replace('-', ' '), (' (%s)' % detail) if detail else '', tc(e['in'])))
    for z in cfg.get('zooms') or []:
        if a <= z.get('at', -1) < b:
            out.append('Zoom to %.2fx at %s' % (z.get('scale', 1), tc(z['at'])))
    if a == 0 and cfg.get('cover'):
        out.append('Cover title on frame 0: "%s"' % cfg['cover']['title'])
    return out


def sounds(cfg, bt):
    try:
        sys.path.insert(0, HERE)
        import mix_master
        cues = mix_master.derive_cues(cfg)
    except Exception:
        return []
    roles = json.load(open(os.path.join(ROOT, 'sounds.json')))
    out = []
    for c in cues:
        if bt['from'] <= c['frame'] < bt['to']:
            on = bool(roles.get(c['role']))
            out.append('%s at %s%s' % (SOUND_WORDS.get(c['role'], c['role']), tc(c['frame']), '' if on else ' (no sound file set)'))
    return out


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    name = sys.argv[1]
    cfg = reel_config.load(name)
    prev = os.path.join(ROOT, 'qa', name, 'preview')
    stills = sorted(int(f[1:5]) for f in os.listdir(prev) if f.startswith('f') and f.endswith('.png')) if os.path.isdir(prev) else []
    if not stills:
        sys.exit('storyboard: no preview stills yet. Run make_reel.sh <video> %s --preview first.' % name)
    out_dir = os.path.join(ROOT, 'qa', name, 'storyboard')
    fr_dir = os.path.join(out_dir, 'frames')
    if os.path.isdir(fr_dir):
        shutil.rmtree(fr_dir)
    os.makedirs(fr_dir)
    brand = json.load(open(os.path.join(ROOT, 'src', 'brand.json')))
    accent = brand.get('accent', '#F7C715')
    font = {'hanken': 'Hanken Grotesk', 'inter': 'Inter', 'montserrat': 'Montserrat', 'dmsans': 'DM Sans', 'poppins': 'Poppins'}.get(brand.get('sans'), 'Hanken Grotesk')
    words = cfg['words']

    def said(a, b):
        return ' '.join(w['t'] for w in words if w['t'] and a / FPS <= w['s'] < b / FPS)

    rows = []
    for bt in beats(cfg):
        pick = [f for f in stills if bt['from'] <= f < bt['to']]
        if len(pick) > 3:
            pick = [pick[0], pick[len(pick) // 2], pick[-1]]
        imgs = []
        for f in pick:
            jpg = 'f%04d.jpg' % f
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', os.path.join(prev, 'f%04d.png' % f), '-vf', 'scale=324:-2', '-q:v', '4',
                            os.path.join(fr_dir, jpg)], check=True)
            imgs.append('<figure><img src="frames/%s" alt="Frame %d" loading="lazy" width="162" height="288"><figcaption>%s</figcaption></figure>' % (jpg, f, tc(f)))
        moves = ''.join('<li>%s</li>' % html.escape(m) for m in what_moves(cfg, bt))
        hear = sounds(cfg, bt)
        hear_html = ''.join('<li>%s</li>' % html.escape(h) for h in hear) or '<li>Your voice only</li>'
        rows.append('''
<section class="beat" id="{id}">
  <div class="frames">{imgs}</div>
  <div class="body">
    <p class="meta"><span class="id">{id}</span> {a} to {b}</p>
    <p class="line">{line}</p>
    <div class="cols"><div><h3>On screen</h3><ul>{moves}</ul></div><div><h3>You hear</h3><ul>{hear}</ul></div></div>
    <label class="note"><span>Note for {id}</span><textarea data-beat="{id}" rows="2" placeholder="Anything to change here? Leave it blank if it looks good."></textarea></label>
  </div>
</section>'''.format(id=bt['id'], imgs=''.join(imgs) or '<p class="none">No still in this beat</p>', a=tc(bt['from']), b=tc(bt['to']),
                     line=html.escape(said(bt['from'], bt['to'])) or '<em>(no words in this beat)</em>', moves=moves, hear=hear_html))
    needs = cfg.get('needs') or []
    if needs:
        need_html = '<section class="needs"><h2>What I need from you</h2><ol>%s</ol><p>Each one has a placeholder in the preview, so you can still review everything now.</p></section>' % ''.join(
            '<li><a href="#%s">%s</a> %s</li>' % (html.escape(n['beat']), html.escape(n['beat']), html.escape(n['what'])) for n in needs)
    else:
        need_html = '<section class="needs none"><h2>What I need from you</h2><p>Nothing. Everything this edit uses is already in hand.</p></section>'
    page = TEMPLATE.replace('__TITLE__', html.escape((cfg.get('cover') or {}).get('title') or name)).replace('__NAME__', html.escape(name)) \
        .replace('__ACCENT__', accent).replace('__FONT__', font).replace('__FONTQ__', font.replace(' ', '+')) \
        .replace('__NEEDS__', need_html).replace('__ROWS__', ''.join(rows)).replace('__LEN__', tc(cfg['frames']))
    open(os.path.join(out_dir, 'index.html'), 'w').write(page)
    files = ['index.html'] + ['frames/' + f for f in sorted(os.listdir(fr_dir))]
    json.dump(files, open(os.path.join(out_dir, 'files.json'), 'w'), indent=1)
    print('storyboard: qa/%s/storyboard/index.html (%d beats, %d stills%s). Review it: python3 scripts/review_server.py %s'
          % (name, len(rows), len(files) - 1, ', %d needs' % len(needs) if needs else '', name))


TEMPLATE = '''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__ storyboard</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=__FONTQ__:wght@400;600;800&display=swap" rel="stylesheet">
<style>
:root { --accent: __ACCENT__; --ink: #1b1c20; --muted: #5d5f68; --paper: #f6f4ef; --sheet: #ffffff; --hair: rgba(0,0,0,.1); }
@media (prefers-color-scheme: dark) { :root { --ink: #ece9e2; --muted: #a3a29c; --paper: #131419; --sheet: #1b1d23; --hair: rgba(255,255,255,.1); } }
* { box-sizing: border-box; }
body { margin: 0; background: var(--paper); color: var(--ink); font: 400 15px/1.55 "__FONT__", system-ui, sans-serif; padding: 28px 16px 96px; }
.wrap { max-width: 1040px; margin: 0 auto; display: grid; gap: 22px; }
.eyebrow { font-size: 12px; letter-spacing: .14em; text-transform: uppercase; color: var(--muted); font-weight: 600; }
h1 { margin: 4px 0 0; font-size: clamp(30px, 6vw, 48px); line-height: 1.05; font-weight: 800; }
.how { margin: 0; color: var(--muted); max-width: 64ch; }
.needs { border: 2px solid var(--accent); border-radius: 10px; padding: 14px 16px; background: var(--sheet); }
.needs.none { border-color: var(--hair); }
.needs h2 { margin: 0 0 6px; font-size: 13px; letter-spacing: .12em; text-transform: uppercase; }
.needs ol { margin: 0 0 6px; padding-left: 20px; } .needs p { margin: 0; color: var(--muted); }
.needs a { color: inherit; font-weight: 700; }
.beat { display: grid; grid-template-columns: auto minmax(0, 1fr); gap: 20px; background: var(--sheet); border: 1px solid var(--hair); border-radius: 10px; padding: 16px; scroll-margin-top: 12px; }
.beat:target { border-color: var(--accent); }
.frames { display: flex; gap: 8px; align-self: start; }
figure { margin: 0; display: grid; gap: 4px; }
figure img { display: block; width: 108px; height: auto; aspect-ratio: 9 / 16; object-fit: cover; border-radius: 6px; border: 1px solid var(--hair); }
figcaption { font-size: 11px; color: var(--muted); font-variant-numeric: tabular-nums; }
.meta { margin: 0; font-size: 12px; color: var(--muted); font-variant-numeric: tabular-nums; }
.id { display: inline-block; background: var(--accent); color: #111; font-weight: 800; border-radius: 4px; padding: 1px 7px; margin-right: 6px; }
.line { margin: 6px 0 10px; font-size: 18px; font-weight: 600; line-height: 1.35; }
.cols { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
h3 { margin: 0 0 4px; font-size: 11px; letter-spacing: .12em; text-transform: uppercase; color: var(--muted); }
ul { margin: 0; padding-left: 18px; }
.note { display: grid; gap: 4px; margin-top: 12px; }
.note span { font-size: 12px; color: var(--muted); }
textarea { width: 100%; font: inherit; color: inherit; background: var(--paper); border: 1px solid var(--hair); border-radius: 8px; padding: 8px 10px; resize: vertical; }
textarea:focus-visible, button:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.bar { position: fixed; left: 0; right: 0; bottom: 0; display: flex; gap: 10px; justify-content: center; align-items: center; flex-wrap: wrap; padding: 12px 16px; background: var(--sheet); border-top: 1px solid var(--hair); }
button { font: 700 15px/1 "__FONT__", system-ui, sans-serif; border-radius: 999px; padding: 12px 20px; border: 1px solid var(--hair); background: var(--paper); color: var(--ink); cursor: pointer; }
button.go { background: var(--accent); color: #111; border-color: transparent; }
#status { font-size: 13px; color: var(--muted); min-width: 12ch; }
@media (max-width: 680px) { .beat { grid-template-columns: 1fr; } .cols { grid-template-columns: 1fr; } figure img { width: 92px; } }
@media (prefers-reduced-motion: reduce) { * { scroll-behavior: auto; } }
</style>
</head>
<body>
<main class="wrap">
  <header>
    <div class="eyebrow">Storyboard: __NAME__ (__LEN__)</div>
    <h1>__TITLE__</h1>
    <p class="how">Read it top to bottom. Leave a note on any beat you want changed, then press <b>Save notes</b>. When it all looks right, press <b>Looks good, render it</b>. Nothing renders until you do.</p>
  </header>
  __NEEDS__
  __ROWS__
</main>
<div class="bar"><span id="status"></span><button type="button" id="save">Save notes</button><button type="button" class="go" id="go">Looks good, render it</button></div>
<script>
(function () {
  var status = document.getElementById('status');
  function collect() {
    return Array.prototype.map.call(document.querySelectorAll('textarea[data-beat]'), function (t) { return { beat: t.dataset.beat, text: t.value.trim() }; })
      .filter(function (n) { return n.text; });
  }
  function send(notes, done) {
    fetch('notes', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(notes) })
      .then(function (r) { if (!r.ok) throw new Error(r.status); status.textContent = done; })
      .catch(function () { status.textContent = 'Could not save. Copy your notes into the chat instead.'; });
  }
  document.getElementById('save').addEventListener('click', function () {
    var n = collect(); send(n, n.length ? 'Saved ' + n.length + ' note' + (n.length > 1 ? 's' : '') + '.' : 'No notes to save.');
  });
  document.getElementById('go').addEventListener('click', function () {
    var n = collect(); n.push({ beat: 'all', text: 'go' }); send(n, 'Saved. Tell Claude it can render.');
  });
})();
</script>
</body>
</html>
'''

if __name__ == '__main__':
    main()

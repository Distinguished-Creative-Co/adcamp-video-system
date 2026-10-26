#!/usr/bin/env python3
"""The storyboard: the preview as a page the person reads and leaves notes on, before anything renders.

    python3 scripts/storyboard.py <name>        after the preview stills exist (make_reel.sh --preview)

One row per part of the reel (each scene, long ones split at sentence ends): its time, real preview stills, the
words said, what moves on screen, what you hear. On top, what the edit still needs from the person ("needs" in the
config), if anything. The page wears the AdCamp look (scripts/adcamp_page.py).

Writes qa/<name>/storyboard/ with its stills in frames/, two ways to review:
  - pane.html, published in the Claude app's pane with every frame (files.json) and
    capabilities {"comments": {"composer_only": true}}: a Comment button per part opens the app's own comment box,
    and the comment goes to Claude (read it with ArtifactComments; the thread sits on the part, #b03).
  - index.html, the fallback in a browser tab: python3 scripts/review_server.py <name> --until-done, a note box per
    part, Save notes and Done. Notes land in qa/<name>/storyboard/notes.json.
"""
import html
import datetime
import json
import re
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import adcamp_page  # noqa: E402
import reel_config  # noqa: E402

FPS = 30
SOUND_WORDS = {'transition_whoosh': 'a whoosh', 'element_land': 'a soft tap', 'state_change': 'a click', 'back_text_hit': 'a hit',
               'insert_pop': 'a pop', 'cta_ding': 'a ding', 'cta_riser': 'a rising swell'}


def fx_names():
    """Effect names as the member saw them in the Picker (picker/catalog.json)."""
    try:
        cat = json.load(open(os.path.join(ROOT, 'picker', 'catalog.json')))
        return {e['key']: e['name'] for e in cat.get('effects', [])}
    except (OSError, ValueError):
        return {}


FX = fx_names()


def tc(f):
    s = f / FPS
    return '%d:%04.1f' % (s // 60, s % 60)


def beats(cfg):
    """Storyboard beats: the scenes, with any scene longer than about 7 s split at sentence ends into beats of
    about 5 s, so a full-screen style is several beats a person can point at, not one long one."""
    sc = sorted(cfg['scenes'], key=lambda s: s['from'])
    fps = cfg.get('fps', 30)
    ends = []   # frames where a new sentence starts
    ws = [w for w in cfg['words'] if w.get('t')]
    for w, nxt in zip(ws, ws[1:]):
        if re.search(r'[.?!]["\u201d]?$', w['t']):
            ends.append(round(nxt['s'] * fps) - 3)
    spans = []
    for i, s in enumerate(sc):
        a = s['from']
        b = sc[i + 1]['from'] if i + 1 < len(sc) else cfg['frames']
        while b - a > 7 * fps:
            ok = [e for e in ends if e >= a + 2 * fps and b - e >= 2 * fps]
            near = [e for e in ok if e <= a + 7 * fps]
            if not ok:
                break
            c = min(near, key=lambda e: abs(e - (a + 5 * fps))) if near else ok[0]   # a long sentence: its own beat
            spans.append((a, c, s))
            a = c
        spans.append((a, b, s))
    return [{'id': 'b%02d' % (i + 1), 'from': a, 'to': b, 'mode': s['mode'], 'tone': s.get('tone')} for i, (a, b, s) in enumerate(spans)]


def overlaps(x, a, b):
    return x['in'] < b and a < x['out']


def what_moves(cfg, bt):
    a, b = bt['from'], bt['to']
    out = []
    if bt['mode'] == 'full':
        out.append('You full screen' + (', punched in at the open' if a == 0 and (cfg.get('open') or {}).get('scale', 1) > 1 else ''))
    else:
        out.append('You in the glass card on a %s stage, captions above' % (bt.get('tone') or 'dark'))
    over = ((cfg.get('look') or {}).get('backText') or {}).get('over')   # a hook title drawn in front, over their head
    for t in cfg.get('backText') or []:
        if overlaps(t, a, b):
            out.append(('Hook title over you: %s' if over or t.get('over') else 'Big words behind you: %s') % t['text'])
    for s in cfg.get('swaps') or []:
        if overlaps(s, a, b):
            k = s['content']['kind']
            label = {'cta': 'Call-to-action card', 'stat': 'Stat panel', 'shot': 'Proof screenshot', 'checklist': 'Checklist',
                     'funnel': 'Funnel', 'decision': 'Decision'}.get(k, k)
            extra = s['content'].get('title') or s['content'].get('value') or s.get('kicker') or ''
            out.append('%s slides in at %s%s' % (label, tc(s['in']), (': ' + extra) if extra else ''))
    for n in cfg.get('inserts') or []:
        if overlaps(n, a, b):
            out.append('Follow card' if n['kind'] == 'follow' else 'Your clip%s' % ((' ("%s")' % n['label']) if n.get('label') else ''))
    for e in cfg.get('effects') or []:
        if e['kind'] == 'transition':
            if a <= e['at'] < b:
                out.append('%s transition at %s' % (e['style'].capitalize(), tc(e['at'])))
        elif overlaps(e, a, b):
            detail = e.get('word') or e.get('label') or e.get('keys') or e.get('text') or e.get('value') or ''
            label = 'A slide over the picture' if e['kind'] == 'card' else FX.get(e['kind'], e['kind'].replace('-', ' ').capitalize())
            out.append('%s%s at %s' % (label, (' (%s)' % detail) if detail else '', tc(e['in'])))
    for z in cfg.get('zooms') or []:
        if a <= z.get('at', -1) < b:
            out.append('%s at %s' % ('Camera pushes in' if z.get('scale', 1) > 1 else 'Camera eases back out', tc(z['at'])))
    if a == 0 and cfg.get('cover'):
        out.append('Cover title (what shows before it plays): "%s"' % cfg['cover']['title'])
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
    notes = os.path.join(out_dir, 'notes.json')
    if os.path.exists(notes):   # last round's notes were applied: keep them, but never let them count again
        os.rename(notes, os.path.join(out_dir, 'notes-applied-%s.json' % datetime.datetime.now().strftime('%Y%m%d-%H%M%S')))
    fr_dir = os.path.join(out_dir, 'frames')
    if os.path.isdir(fr_dir):
        shutil.rmtree(fr_dir)
    os.makedirs(fr_dir)
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
            imgs.append('<figure><img src="frames/%s" alt="Frame at %s" loading="lazy" width="162" height="288"><figcaption>%s</figcaption></figure>'
                        % (jpg, tc(f), tc(f)))
        moves = ''.join('<li>%s</li>' % html.escape(m) for m in what_moves(cfg, bt))
        hear = ''.join('<li>%s</li>' % html.escape(h) for h in sounds(cfg, bt)) or '<li>Your voice only</li>'
        line = html.escape(said(bt['from'], bt['to']))
        rows.append({'id': bt['id'], 'n': int(bt['id'][1:]), 'a': tc(bt['from']), 'b': tc(bt['to']),
                     'imgs': ''.join(imgs) or '<p class="foot">No still in this part</p>',
                     'line': ('&ldquo;%s&rdquo;' % line) if line else '<span class="muted">(no words in this part)</span>',
                     'moves': moves, 'hear': hear})
    needs = cfg.get('needs') or []
    title = (cfg.get('cover') or {}).get('title') or name.replace('-', ' ')
    pane, local = page_bodies(title, tc(cfg['frames']), rows, needs)
    adcamp_page.write(out_dir, html.escape(title), local, extra_css=STORYBOARD_CSS, pane_body=pane)
    files = ['pane.html'] + ['frames/' + f for f in sorted(os.listdir(fr_dir))]
    adcamp_page.files_map(out_dir, files[1:])
    print('storyboard: qa/%s/storyboard/pane.html (%d parts, %d stills%s). In the Claude app publish pane.html with its frames '
          '(files.json). Elsewhere: python3 scripts/review_server.py %s --until-done'
          % (name, len(rows), len(files) - 1, ', %d needs' % len(needs) if needs else '', name))


def page_bodies(title, length, rows, needs):
    """The storyboard's body twice: for the pane (a comment button per part, the Claude app's own comment loop) and
    for a local tab (a note box per part, Save notes and Done)."""
    words = html.escape(title).split(' ')
    head = ' '.join(words[:-1]) + (' ' if len(words) > 1 else '') + '<span class="y">%s</span>' % words[-1]
    if needs:
        need = ('<section class="card need" id="needs" data-comment-target><p class="eyebrow">What I need from you</p><ol class="needs">%s</ol>'
                '<p class="foot">Each one has a stand-in in the preview, so you can review everything now.</p></section>'
                % ''.join('<li><a href="#%s">Part %s</a>: %s</li>' % (html.escape(str(n['beat'])), str(n['beat']).lstrip('b'), html.escape(n['what']))
                          for n in needs))
    else:
        need = ('<section class="inner none" id="needs"><span class="eyebrow">What I need from you</span>'
                '<span class="muted">Nothing. Everything this edit uses is already in hand.</span></section>')

    def row(r, note):
        return ('<section class="card lift beat" id="{id}" data-comment-target>'
                '<div class="beat-head"><span class="chip">Part {n:02d}</span><span class="time">{a} to {b}</span></div>'
                '<div class="beat-grid"><div class="frames">{imgs}</div><div class="beat-body"><p class="line">{line}</p>'
                '<div class="cols"><div><p class="label">On screen</p><ul class="list">{moves}</ul></div>'
                '<div><p class="label">You hear</p><ul class="list">{hear}</ul></div></div>{note}</div></div></section>').format(note=note, **r)

    hero = ('{top}<header class="hero"><span class="eyebrow-pill">Nothing renders until you say go</span><h1>{head}</h1>'
            '<p class="lede">{how}</p></header>{need}')
    pane_how = ('Every part of your video, before a single frame renders. To change a part, press <b>Comment on this part</b>, '
                'say what you want, and send it to Claude. When it all looks right, tell Claude to render it.')
    local_how = ('Every part of your video, before a single frame renders. Leave a note on any part you want changed. '
                 '<b>Save notes</b> keeps them as you go. Press <b>Done</b> when you have finished, and Claude takes it from there.')
    top = adcamp_page.top('Video System', 'Storyboard &middot; %s' % length)
    btn = '<div class="beat-act"><button type="button" class="btn btn-ghost" data-comment hidden>Comment on this part</button></div>'
    pane = ('<main class="page">' + hero.format(top=top, head=head, how=pane_how, need=need)
            + ''.join(row(r, btn) for r in rows)
            + '<p class="foot end">Looks right? Tell Claude to render it. Want a change after that? Comment on the part here, '
              'and the new version lands next to the first.</p></main>' + PANE_JS)
    note = ('<label class="note"><span class="label">Note for part {n:02d}</span><textarea data-beat="{id}" rows="2" '
            'placeholder="Anything to change here? Leave it blank if it looks good."></textarea></label>')
    local = ('<main class="page">' + hero.format(top=top, head=head, how=local_how, need=need)
             + ''.join(row(r, note.format(**r)) for r in rows) + '</main>'
             + '<div class="bar"><span id="status" aria-live="polite"></span><button type="button" class="btn btn-ghost" id="save">Save notes</button>'
               '<button type="button" class="btn btn-y" id="go">Done</button></div>' + LOCAL_JS)
    return pane, local


STORYBOARD_CSS = """
.beat { scroll-margin-top: 16px; }
.beat:target { border-color: var(--yellow); }
.beat-head { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.time { font-size: 13px; color: var(--t-sub); font-variant-numeric: tabular-nums; letter-spacing: 0.02em; }
.beat-grid { display: grid; grid-template-columns: auto minmax(0, 1fr); gap: 20px; }
.beat-grid > * { min-width: 0; }
.frames { display: flex; gap: 8px; align-self: start; }
figure { margin: 0; display: grid; gap: 4px; }
figure img { width: 104px; height: auto; aspect-ratio: 9 / 16; object-fit: cover; border-radius: 10px; border: 1px solid var(--line); background: var(--inner); }
figcaption { font-size: 11px; color: var(--t-foot); font-variant-numeric: tabular-nums; }
.beat-body { display: grid; gap: 14px; align-content: start; }
.line { margin: 0; font-size: 19px; font-weight: 600; line-height: 1.4; max-width: 60ch; }
.cols { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.cols > * { min-width: 0; }
.beat-act { display: flex; }
ol.needs { margin: 0; padding-left: 20px; color: var(--t-body); display: grid; gap: 4px; }
ol.needs a { color: var(--yellow); font-weight: 700; }
.none { display: flex; gap: 12px; align-items: baseline; flex-wrap: wrap; }
.end { text-align: center; max-width: 60ch; justify-self: center; margin: 6px 0 0; }
.note { display: grid; gap: 6px; }
.bar { position: fixed; left: 0; right: 0; bottom: 0; display: flex; gap: 10px; justify-content: center; align-items: center; flex-wrap: wrap;
  padding: 12px max(16px, env(safe-area-inset-right, 0px)) calc(12px + env(safe-area-inset-bottom, 0px)) max(16px, env(safe-area-inset-left, 0px));
  background: rgba(11,11,11,0.92); border-top: 1px solid var(--line); }
#status { font-size: 13px; color: var(--t-sub); }
@media (max-width: 700px) { .beat-grid { grid-template-columns: minmax(0, 1fr); } .cols { grid-template-columns: minmax(0, 1fr); } figure img { width: 92px; } }
"""

PANE_JS = """<script>
// Each part's button opens the Claude app's own comment box on that part. The comment goes to Claude from there.
(function () {
  var tries = 0;
  function start() {
    if (!(window.claude && window.claude.use)) { if (++tries < 20) setTimeout(start, 250); return; }
    window.claude.use('comments').then(function (c) {
      if (!c) return;
      document.querySelectorAll('[data-comment]').forEach(function (b) {
        b.hidden = false;
        b.addEventListener('click', function () {
          c.openComposer({ element: b.closest('section') }).catch(function (e) {
            if (e && (e.code === 'unavailable' || e.code === 'not_granted')) {
              document.querySelectorAll('[data-comment]').forEach(function (x) { x.hidden = true; });
            }
          });
        });
      });
    }).catch(function () {});
  }
  start();
})();
</script>"""

LOCAL_JS = """<script>
(function () {
  var status = document.getElementById('status');
  function collect() {
    // every box goes, empty ones too: an empty box clears that part's saved note
    return Array.prototype.map.call(document.querySelectorAll('textarea[data-beat]'), function (t) { return { beat: t.dataset.beat, text: t.value.trim() }; });
  }
  function count(notes) { return notes.filter(function (n) { return n.text; }).length; }
  // a reopened page shows the notes already saved, so a Save never clears them by accident
  fetch('notes.json', { cache: 'no-store' }).then(function (r) { return r.ok ? r.json() : []; }).then(function (kept) {
    kept.forEach(function (n) { var t = document.querySelector('textarea[data-beat="' + n.beat + '"]'); if (t && !t.value) t.value = n.text; });
  }).catch(function () {});
  function send(notes, done) {
    fetch('notes', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(notes) })
      .then(function (r) { if (!r.ok) throw new Error(r.status); status.textContent = done; })
      .catch(function () { status.textContent = 'Could not save. Copy your notes into the chat instead.'; });
  }
  document.getElementById('save').addEventListener('click', function () {
    var n = collect(), c = count(n); send(n, c ? 'Saved ' + c + ' note' + (c > 1 ? 's' : '') + '. Press Done when you are finished.' : 'Saved. No notes.');
  });
  document.getElementById('go').addEventListener('click', function () {
    var n = collect(), c = count(n); n.push({ beat: 'all', text: 'go' });
    send(n, c ? 'Sent ' + c + ' note' + (c > 1 ? 's' : '') + ' to Claude. A new draft comes next.' : 'Done. Tell Claude in the chat to render it, and it makes the final video.');
  });
})();
</script>"""


if __name__ == '__main__':
    main()

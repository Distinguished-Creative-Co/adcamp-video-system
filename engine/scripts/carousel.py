#!/usr/bin/env python3
"""Carousels in the member's look, from a reel or a topic. Copy first, then slides.

    python3 scripts/carousel.py new "<title>" [--from-reel <reel>] [--style <style>] [--size 4:5|1:1]
    python3 scripts/carousel.py frames <reel> --at 3.2,7.5 --out <carousel folder>      stills from the reel's cut
    python3 scripts/carousel.py check <carousel folder>                                  every word on every slide
    python3 scripts/carousel.py render <carousel folder> [--pane]                        slides/*.png, pane.html, preview.html
    python3 scripts/carousel.py open <carousel folder>                                   the swipe preview again

A carousel is a folder carousels/<slug>/ holding carousel.json (the words for every slide and the post caption,
written by Claude and approved by the member BEFORE any render), assets/ (pictures), slides/ and preview.html.
The look comes from a saved style (its caption face and key color) and brand.json (handle, photo, accent).
Slide fields: src/components/slides/Slide.tsx. Nothing is posted.
"""
import datetime
import glob
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import reel_config  # noqa: E402
import styles_lib as L  # noqa: E402

DIR = os.path.join(ROOT, 'carousels')
LAYOUTS = ('hook', 'statement', 'content', 'cta')


def folder(arg):
    p = arg if os.path.isabs(arg) else os.path.join(DIR, arg) if not os.path.exists(arg) else arg
    if not os.path.exists(os.path.join(p, 'carousel.json')):
        sys.exit('carousel: no carousel.json in %s' % p)
    return os.path.abspath(p)


def brand():
    try:
        return json.load(open(os.path.join(ROOT, 'src', 'brand.json')))
    except (OSError, ValueError):
        return {}


def look_from(style_name):
    b = brand()
    look = {'theme': 'paper', 'accent': b.get('accent', '#F7C715')}
    st = L.find(style_name) if style_name else L.by_slug(L.default_slug())
    if st and not st.get('hidden'):   # a starter look or their own: its type and color carry into the carousel
        cap = (st.get('look') or {}).get('captions') or {}
        if cap.get('font'):
            look['font'] = cap['font']
        if cap.get('keyColor') and cap['keyColor'] != 'accent':   # "accent" is the brand accent, already set
            look['accent'] = cap['keyColor']
        if cap.get('case') == 'upper':
            look['case'] = 'upper'
    return look, ((st.get('aliases') or ['your usual look'])[0] if st.get('hidden') else st['name']) if st else None   # never an engine base's name


def words_of(reel):
    """The reel's spoken sentences with their times, from its config (what was actually said and kept)."""
    cfg = reel_config.load(reel)
    out, cur = [], []
    for w in cfg['words']:
        if not w.get('t'):
            continue
        cur.append(w)
        if re.search(r'[.?!]["”]?$', w['t']):
            out.append((cur[0]['s'], ' '.join(x['t'] for x in cur)))
            cur = []
    if cur:
        out.append((cur[0]['s'], ' '.join(x['t'] for x in cur)))
    return out


def cmd_new(a):
    title = a[1]
    slug = L.slugify(title)[:48]
    d = os.path.join(DIR, slug)
    if os.path.exists(d):
        sys.exit('carousel: %s exists. Pick another title, or work in that folder.' % os.path.relpath(d, ROOT))
    size = a[a.index('--size') + 1] if '--size' in a else '4:5'
    if size not in ('4:5', '1:1'):
        sys.exit('carousel: --size is 4:5 or 1:1')
    look, sname = look_from(a[a.index('--style') + 1] if '--style' in a else None)
    os.makedirs(os.path.join(d, 'assets'))
    b = brand()
    who = {'handle': b.get('handle') or '', 'name': b.get('name') or ''}
    av = os.path.join(ROOT, 'public', b.get('avatar') or 'inserts/avatar.png')
    if b.get('avatar') and os.path.exists(av):
        shutil.copy2(av, os.path.join(d, 'assets', 'avatar' + os.path.splitext(av)[1]))
        who['avatar'] = 'assets/avatar' + os.path.splitext(av)[1]
    doc = {'title': title, 'slug': slug, 'size': size, 'look': look, 'who': who, 'created': datetime.date.today().isoformat(),
           'approved': False, 'slides': [], 'caption': ''}
    if '--from-reel' in a:
        reel = a[a.index('--from-reel') + 1]
        doc['source'] = reel
        with open(os.path.join(d, 'transcript.txt'), 'w') as f:
            for t, s in words_of(reel):
                f.write('[%5.1fs] %s\n' % (t, s))
    json.dump(doc, open(os.path.join(d, 'carousel.json'), 'w'), indent=1)
    print('carousel: made %s (%s, look: %s%s)' % (os.path.relpath(d, ROOT), size, sname or 'brand colors',
                                                    ', transcript.txt from %s' % doc['source'] if doc.get('source') else ''))
    print('next: write the slides and the caption into carousel.json, show the member the words, get a yes, then render')


def cmd_frames(a):
    reel = a[1]
    ats = [float(x) for x in a[a.index('--at') + 1].split(',')]
    out = folder(a[a.index('--out') + 1])
    cfg = reel_config.load(reel)
    src = os.path.join(ROOT, 'public', cfg['src'])
    hi = src.replace('-cut.mp4', '-cut-hi.mp4')
    if os.path.exists(hi):
        src = hi
    lut = cfg.get('color') or 'natural'   # the reel's color look on the stills too (the graded copies may be cleaned up)
    vf = ('lut3d=%s:interp=tetrahedral,' % os.path.join(ROOT, 'luts', lut + '.cube') if lut != 'natural' else '') + 'scale=1080:-2'
    for t in ats:
        dst = os.path.join(out, 'assets', 'f%05.1f.jpg' % t)
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', '%.2f' % t, '-i', src, '-frames:v', '1', '-vf', vf, '-q:v', '2', dst], check=True)
        print('carousel: %s' % os.path.relpath(dst, out))


def problems(doc, d):
    errs, notes = [], []
    n = len(doc.get('slides') or [])
    if not 3 <= n <= 10:
        errs.append('a carousel is 3 to 10 slides (this has %d)' % n)
    for i, s in enumerate(doc.get('slides') or [], 1):
        if s.get('layout') not in LAYOUTS:
            errs.append('slide %d: layout must be one of %s' % (i, ', '.join(LAYOUTS)))
        hl = (s.get('headline') or '').replace('==', '')
        if not hl.strip():
            errs.append('slide %d: no headline' % i)
        if any(len(line) > 26 for line in hl.split('\n')):
            notes.append('slide %d: a headline line runs past 26 characters, it will be set small' % i)
        if len(s.get('items') or []) > 5:
            errs.append('slide %d: at most 5 list items' % i)
        if s.get('photo') and not os.path.exists(os.path.join(d, s['photo'])):
            errs.append('slide %d: photo %s is not in the folder' % (i, s['photo']))
    if n and doc['slides'][0].get('layout') != 'hook':
        notes.append('slide 1 is usually the hook')
    return errs, notes, []


def cmd_check(a):
    d = folder(a[1])
    doc = json.load(open(os.path.join(d, 'carousel.json')))
    errs, notes, nums = problems(doc, d)
    for i, s in enumerate(doc['slides'], 1):
        line = ' / '.join(x for x in [s.get('label'), s.get('headline', '').replace('\n', ' '), s.get('sub'),
                                      ' / '.join(it['t'] for it in s.get('items') or []), s.get('callout'),
                                      ' '.join(x for x in [s.get('keywordLead'), s.get('keyword')] if x), s.get('keywordNote')] if x)   # every word on the slide
        print('%d. [%s] %s' % (i, s['layout'], line.replace('==', '')))   # the words as they read, highlight marks left out
    print('caption: %d characters' % len(doc.get('caption') or ''))
    for e in errs:
        print('PROBLEM: ' + e)
    for n in notes:
        print('note: ' + n)
    sys.exit(1 if errs else 0)


def write_pages(d, doc, names):
    """The swipe preview on the AdCamp kit: pane.html for the Claude app's pane (a comment button on the slide in view;
    publish it with every file in files.json and capabilities {"comments": {"composer_only": true}}) and preview.html
    for a browser tab."""
    import adcamp_page
    title = html.escape(doc['title'])
    n = len(names)
    slides = ''.join('<section class="slide" id="s%02d" data-comment-target aria-label="Slide %d of %d"><img src="slides/%s" alt="Slide %d of %d" '
                     'width="1080" height="%d"></section>' % (i, i, n, f, i, n, 1350 if doc.get('size', '4:5') == '4:5' else 1080)
                     for i, f in enumerate(names, 1))
    dots = ''.join('<i%s></i>' % (' class="on"' if i == 0 else '') for i in range(n))
    cap = html.escape(doc.get('caption') or '')

    def body(pane):
        how = ('Swipe through. To change a slide, press <b>Comment on this slide</b> and send it to Claude. When it is right, '
               'the slides are ready in your carousel folder.' if pane else
               'Swipe through, or use the arrows. Tell Claude in the chat what to change on any slide.')
        btn = ('<button type="button" class="btn btn-ghost" id="cm" hidden>Comment on this slide</button>' if pane else '')
        return ('<main class="page narrow">' + adcamp_page.top('Video System', 'Carousel &middot; %d slides' % n) +
                '<header class="hero"><span class="eyebrow-pill">%s</span><h1>%s</h1><p class="lede">%s</p></header>'
                % ('Draft, words not approved yet' if not doc.get('approved') else 'Nothing is posted', title, how) +
                '<div class="phone"><div class="track" id="t" tabindex="0" aria-label="Slides">%s</div></div>' % slides +
                '<div class="nav"><button type="button" class="round" id="p" aria-label="Previous slide">&#8592;</button>'
                '<div class="dots" id="d">%s</div><button type="button" class="round" id="x" aria-label="Next slide">&#8594;</button></div>' % dots +
                '<div class="act">%s</div>' % btn +
                '<section class="card"><p class="eyebrow">Your caption</p><p class="cap" id="cap">%s</p>'
                '<div><button type="button" class="btn btn-ghost" id="copy">Copy caption</button> <span class="foot" id="cs" aria-live="polite"></span></div></section>'
                % (cap or '<span class="muted">No caption yet.</span>') + '</main>' + CAR_JS)
    adcamp_page.write(d, title, body(False), extra_css=CAR_CSS, pane_body=body(True))
    os.replace(os.path.join(d, 'index.html'), os.path.join(d, 'preview.html'))
    adcamp_page.files_map(d, ['slides/' + f for f in names])


CAR_CSS = """
.narrow { max-width: 560px; }
.hero h1 { font-size: clamp(34px, 7vw, 56px); }
.phone { border: 1px solid var(--line); border-radius: 20px; overflow: hidden; background: #000; }
.track { display: flex; overflow-x: auto; scroll-snap-type: x mandatory; scrollbar-width: none; }
.track::-webkit-scrollbar { display: none; }
.slide { flex: 0 0 100%; scroll-snap-align: center; }
.slide img { width: 100%; height: auto; }
.nav { display: flex; align-items: center; justify-content: space-between; }
.round { width: 44px; height: 44px; border-radius: 50%; border: 1px solid var(--line-2); background: var(--card); color: var(--t-white); font-size: 18px; cursor: pointer; }
.dots { display: flex; gap: 6px; flex-wrap: wrap; justify-content: center; }
.dots i { width: 8px; height: 8px; border-radius: 50%; background: var(--line-2); }
.dots i.on { background: var(--yellow); }
.act { display: flex; justify-content: center; }
.cap { margin: 0; white-space: pre-wrap; color: var(--t-body); }
@media (prefers-reduced-motion: reduce) { .track { scroll-behavior: auto; } }
"""

CAR_JS = """<script>
(function () {
  var t = document.getElementById('t'), d = document.querySelectorAll('#d i');
  var still = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  function at() { return Math.round(t.scrollLeft / t.clientWidth); }
  function go(n) { t.scrollTo({ left: n * t.clientWidth, behavior: still ? 'auto' : 'smooth' }); }
  t.addEventListener('scroll', function () { var k = at(); d.forEach(function (e, j) { e.className = j === k ? 'on' : ''; }); });
  document.getElementById('p').onclick = function () { go(Math.max(0, at() - 1)); };
  document.getElementById('x').onclick = function () { go(Math.min(d.length - 1, at() + 1)); };
  t.addEventListener('keydown', function (e) { if (e.key === 'ArrowRight') go(Math.min(d.length - 1, at() + 1)); if (e.key === 'ArrowLeft') go(Math.max(0, at() - 1)); });
  document.getElementById('copy').onclick = function () {
    var s = document.getElementById('cs'), txt = document.getElementById('cap').textContent;
    navigator.clipboard.writeText(txt).then(function () { s.textContent = 'Copied.'; }, function () {
      var r = document.createRange(); r.selectNodeContents(document.getElementById('cap'));
      var sel = window.getSelection(); sel.removeAllRanges(); sel.addRange(r); s.textContent = 'Selected. Press Command C to copy.';
    });
  };
  // in the Claude app's pane: comment on the slide in view, through the app's own comment box
  var cm = document.getElementById('cm'), tries = 0;
  function start() {
    if (!cm) return;
    if (!(window.claude && window.claude.use)) { if (++tries < 20) setTimeout(start, 250); return; }
    window.claude.use('comments').then(function (c) {
      if (!c) return;
      cm.hidden = false;
      cm.onclick = function () {
        var el = t.children[at()];
        c.openComposer({ element: el }).catch(function (e) { if (e && (e.code === 'unavailable' || e.code === 'not_granted')) cm.hidden = true; });
      };
    }).catch(function () {});
  }
  start();
})();
</script>"""


def cmd_render(a):
    d = folder(a[1])
    doc = json.load(open(os.path.join(d, 'carousel.json')))
    errs, notes, nums = problems(doc, d)
    if errs:
        sys.exit('carousel: not rendered:\n  ' + '\n  '.join(errs))
    if not doc.get('approved') and '--draft' not in a:
        sys.exit('carousel: the words are not approved yet. Show the member the copy (carousel.py check), and after a clear yes '
                 'set "approved": true in carousel.json. (--draft renders anyway, marked as a draft in the preview.)')
    out = os.path.join(d, 'slides')
    for f in glob.glob(os.path.join(out, '*.png')):
        os.remove(f)
    os.makedirs(out, exist_ok=True)
    props = tempfile.NamedTemporaryFile('w', suffix='.json', delete=False)
    json.dump({'doc': doc}, props)
    props.close()
    cmd = ['npx', 'remotion', 'render', 'src/methodology/index.ts', 'Carousel', out, '--sequence', '--image-format=png',
           '--props=' + props.name, '--public-dir=' + d, '--log=error']
    p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    os.remove(props.name)
    if p.returncode != 0:
        sys.exit('carousel: render failed: ' + (p.stderr or p.stdout)[-600:])
    frames = sorted(glob.glob(os.path.join(out, '*.png')))
    names = []
    for i, f in enumerate(frames, 1):
        dst = os.path.join(out, '%s-%02d.png' % (doc['slug'], i))
        os.replace(f, dst)
        names.append(os.path.basename(dst))
    write_pages(d, doc, names)
    print('carousel: %d slides in %s. In the Claude app publish %s with its slides (files.json). Elsewhere the preview is %s'
          % (len(names), os.path.relpath(out, ROOT), os.path.relpath(os.path.join(d, 'pane.html'), ROOT),
             os.path.relpath(os.path.join(d, 'preview.html'), ROOT)))
    for n in notes:
        print('note: ' + n)
    if '--no-open' not in a and '--pane' not in a:
        subprocess.run(['open', os.path.join(d, 'preview.html')], check=False)


def main():
    a = sys.argv[1:]
    if not a or a[0] not in ('new', 'frames', 'check', 'render', 'open') or len(a) < 2:
        sys.exit(__doc__)
    if a[0] == 'open':
        subprocess.run(['open', os.path.join(folder(a[1]), 'preview.html')], check=False)
        return
    {'new': cmd_new, 'frames': cmd_frames, 'check': cmd_check, 'render': cmd_render}[a[0]](a)


if __name__ == '__main__':
    main()

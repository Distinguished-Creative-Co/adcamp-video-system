#!/usr/bin/env python3
"""The style board: the member's look on one page, in the AdCamp frame. Their type, their colors and what each one
is for, their look playing, and the other starter looks playing beside it.

    python3 scripts/style_board.py [<reel>]
    python3 scripts/style_board.py --keep-clip "<their look>" <a video in it>   that look plays on the board from now on

"Your look" plays a few seconds of <reel>'s finished video (out/<reel>.mp4) when it was made in their default look:
`sample` (the install test's video, in their brand) at setup, their own video after their first one. Otherwise, and
for the other looks, it plays the Picker's preview clip of that look (picker/previews/styles/), made on the sample in
the default colors. Nothing renders: it takes a few seconds.

Writes qa/style-board/: pane.html for the Claude app's pane (publish it with every file in files.json and
capabilities {"comments": {"composer_only": true}}, then a comment on a look or a swatch goes to Claude), index.html
for a browser tab, clips/. Prints BOARD READY when done.
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
import adcamp_page  # noqa: E402
import reel_config  # noqa: E402
import styles_lib as L  # noqa: E402

OUT = os.path.join(ROOT, 'qa', 'style-board')
SANS = {'hanken': 'Hanken Grotesk', 'inter': 'Inter', 'montserrat': 'Montserrat', 'dmsans': 'DM Sans', 'poppins': 'Poppins'}
SERIF = {'playfair': ('Playfair Display', 800), 'instrument': ('Instrument Serif', 400), 'dmserif': ('DM Serif Display', 400),
         'fraunces': ('Fraunces', 800)}


def lum(hex_):
    rgb = [int(hex_.lstrip('#')[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def lifted(hex_):
    """The shade words take over footage: a dark brand color lifted toward white until it reads (as the engine does)."""
    if lum(hex_) >= 0.15:
        return hex_.upper()
    base = [int(hex_.lstrip('#')[i:i + 2], 16) for i in (0, 2, 4)]
    for k in range(21):
        t = k * 0.05
        c = '#' + ''.join('%02X' % round(v + (255 - v) * t) for v in base)
        if lum(c) >= 0.5:
            return c
    return '#FFFFFF'


def ink_on(hex_):
    return '#FFFFFF' if lum(hex_) < 0.35 else '#141414'


def lead_look():
    """Their look: the default (a starter, their own tweak, a Picker mix or a look from reels), else Clean Talk."""
    return L.by_slug(L.default_slug() or '') or L.by_slug('clean-talk')


def clips(reel):
    """{slug: (clip, poster, own)}: the Picker's clip for every starter, a saved look's own sample clip when it has one,
    and the member's own video for their look when that video was made in it."""
    os.makedirs(os.path.join(OUT, 'clips'), exist_ok=True)
    cat = json.load(open(os.path.join(ROOT, 'picker', 'catalog.json')))
    out = {}
    for st in cat.get('styles', []):
        for k, dst in (('preview', st['key'] + '.mp4'), ('poster', st['key'] + '.jpg')):
            shutil.copyfile(os.path.join(ROOT, 'picker', st[k]), os.path.join(OUT, 'clips', dst))
        out[st['key']] = ('clips/%s.mp4' % st['key'], 'clips/%s.jpg' % st['key'], False)
    renders = [os.path.join(ROOT, 'out', reel + '.mp4')] + [os.path.join(ROOT, 'out', '%s-v%d.mp4' % (reel, n)) for n in range(2, 100)]
    renders = [r for r in renders if os.path.exists(r)]
    render = renders[-1] if renders else os.path.join(ROOT, 'out', reel + '.mp4')   # the newest version
    lead = lead_look()
    if not lead.get('builtin') and os.path.exists(os.path.join(L.style_dir(lead['slug']), 'sample.mp4')):
        for f in ('sample.mp4', 'sample.jpg'):
            src = os.path.join(L.style_dir(lead['slug']), f)
            if os.path.exists(src):
                shutil.copyfile(src, os.path.join(OUT, 'clips', 'look-' + f))
        out[lead['slug']] = ('clips/look-sample.mp4', 'clips/look-sample.jpg', False)
    look = (reel_config.load(reel).get('meta') or {}).get('look') if os.path.exists(reel_config.config_path(reel)) else None
    if look and look == lead['slug'] and os.path.exists(render):   # their own video, only under their own look
        mp4, jpg = os.path.join(OUT, 'clips', 'yours.mp4'), os.path.join(OUT, 'clips', 'yours.jpg')
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', '0.3', '-t', '5', '-i', render, '-an', '-vf', 'scale=360:-2,fps=30',
                        '-c:v', 'libx264', '-crf', '28', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', mp4], check=True)
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', '1.6', '-i', render, '-frames:v', '1', '-vf', 'scale=360:-2', '-q:v', '4', jpg],
                       check=True)
        out[look] = ('clips/yours.mp4', 'clips/yours.jpg', True)
    return out


def page(brand, media, sample):
    accent = brand.get('accent', '#F7C715').upper()
    sans = SANS.get(brand.get('sans'), 'Hanken Grotesk')
    serif, sw = SERIF.get(brand.get('serif'), SERIF['playfair'])
    starters = [s for s in L.all_styles() if s.get('starter')]
    dflt = L.default_slug()
    lead = lead_look()
    others = [s for s in starters if s['slug'] != lead['slug']]
    over = lifted(accent)
    who = html.escape(brand.get('name') or '')

    def shown(st):   # an engine base is never named: "cards and panels"
        return ((st.get('aliases') or ['your usual look'])[0].capitalize() if st.get('hidden') else st['name'])

    def look_card(st, big=False):
        m = media.get(st['slug'])
        pic = ('<video src="%s" poster="%s" muted loop playsinline autoplay preload="metadata" width="270" height="480" '
               'aria-label="%s look, playing"></video>' % (m[0], m[1], html.escape(shown(st)))) if m else '<div class="nopic">Plays here after your first video in it</div>'
        tag = '<span class="chip">Your look</span>' if st['slug'] == dflt else ('<span class="chip">Where you start</span>' if big else '')
        return ('<section class="card lift look%s" id="look-%s" data-comment-target><div class="shot">%s</div><div class="look-body">%s'
                '<h2>%s</h2><p class="muted">%s</p><div class="act"><button type="button" class="btn btn-ghost" data-comment hidden>'
                'Comment on this look</button></div></div></section>'
                % (' big' if big else '', st['slug'], pic, tag, html.escape(shown(st)), html.escape(st.get('feel') or 'Your own look.')))

    swatches = [('Your color', accent, 'Key words, hook titles, numbers and buttons. Slides and carousels use it exactly.')]
    if over != accent:
        swatches.append(('Over your video', over, 'A lighter shade of your color, so words over your video stay readable.'))
    swatches.append(('Text on your color', ink_on(accent), 'The words on a button or a highlight in your color.'))
    sw_html = ''.join('<div class="sw" data-comment-target id="sw-%d"><span class="chipcolor" style="background:%s"></span><div><p class="label">%s</p>'
                      '<p class="hex">%s</p><p class="muted">%s</p><button type="button" class="btn btn-ghost btn-sm" data-comment hidden>Comment on this color</button></div></div>' % (i, c, html.escape(n), c, html.escape(d))
                      for i, (n, c, d) in enumerate(swatches))
    own = any(m[2] for m in media.values())
    note = ('Your look plays %s in your colors and fonts. The other looks play on the sample in the default colors, and yours '
            'would use your color and fonts.' % ('the sample video' if sample else 'your own video')) if own else (
            'The looks play on the sample in the default colors. Yours use your color and fonts.')
    body = (
        '<main class="page">' + adcamp_page.top('Video System', 'Your style') +
        '<header class="hero"><span class="eyebrow-pill">Set once, used on every video</span><h1>Your <span class="y">look</span></h1>'
        '<p class="lede">__HOW__</p></header>'
        + look_card(lead, big=True) +
        '<section class="card" id="type" data-comment-target><p class="eyebrow">Your type</p><div class="type">'
        '<div><p class="label">Main font: %s</p><p class="spec-sans">Same four things</p><p class="spec-small">Captions, slides and your follow card.</p></div>'
        '<div><p class="label">Second font: %s</p><p class="spec-serif">every one of them</p><p class="spec-small">Key words in Soft Story and some looks.</p></div>'
        '</div><div class="act"><button type="button" class="btn btn-ghost" data-comment hidden>Comment on the type</button></div></section>'
        % (html.escape(sans), html.escape(serif)) +
        '<section class="card" id="colors"><p class="eyebrow">Your colors</p><div class="sws">%s</div></section>' % sw_html +
        '<div class="others"><p class="eyebrow">The other looks</p><div class="grid">%s</div></div>' % ''.join(look_card(s) for s in others) +
        '<section class="inner more"><p class="label">Other ways to pick</p><p class="muted">Ask Claude to open the Picker to mix your own '
        'captions and effects, or send two or three reels you love and Claude builds a look from them.</p></section>'
        '<p class="foot">%s%s</p></main>' % (note, (' Brand: %s.' % who) if who else '') + PANE_JS)
    css = BOARD_CSS.replace('__SANS__', sans).replace('__SERIF__', serif).replace('__SW__', str(sw)).replace('__ACCENT__', over)   # the board is near black: a dark brand color shows in its lifted shade
    fonts = ('%s:wght@500;800' % sans, '%s:ital,wght@1,%d' % (serif, sw) if sw != 400 else '%s:ital@1' % serif)
    pane_how = ('Every video comes out like this. Comment on anything you would change, a look, a color, the type, and send it '
                'to Claude. It redraws the board. When it looks right, say so in the chat.')
    local_how = ('Every video comes out like this. Tell Claude in the chat what you would change, a look, a color, the type, '
                 'and it redraws the board. When it looks right, say so.')
    return body.replace('__HOW__', pane_how), body.replace('__HOW__', local_how), css, fonts


BOARD_CSS = """
.look { grid-template-columns: auto minmax(0, 1fr); align-items: center; gap: 20px; }
.look.big { grid-template-columns: minmax(0, 260px) minmax(0, 1fr); }
.look h2 { font-size: clamp(28px, 4vw, 40px); }
.look-body { display: grid; gap: 10px; justify-items: start; align-content: center; }
.look-body .muted { margin: 0; max-width: 46ch; }
.shot video { width: 150px; aspect-ratio: 9 / 16; height: auto; object-fit: cover; border-radius: 12px; border: 1px solid var(--line); }
.look.big .shot video { width: 100%; max-width: 260px; }
.nopic { width: 150px; aspect-ratio: 9 / 16; border-radius: 12px; border: 1px dashed var(--line-2); display: grid; place-items: center; color: var(--t-foot); font-size: 12px; }
.type { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
.type > * { min-width: 0; }
.spec-sans { margin: 0; font-family: '__SANS__', var(--f-body); font-weight: 800; font-size: clamp(30px, 5vw, 44px); line-height: 1.05; color: var(--t-white); }
.spec-serif { margin: 0; font-family: '__SERIF__', Georgia, serif; font-style: italic; font-weight: __SW__; font-size: clamp(30px, 5vw, 44px); line-height: 1.05; color: __ACCENT__; }
.spec-small { margin: 6px 0 0; color: var(--t-foot); font-size: 13px; }
.sws { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 14px; }
.sw { display: flex; gap: 12px; align-items: flex-start; }
.sw > div { min-width: 0; }
.sw .muted { margin: 0; font-size: 13px; }
.chipcolor { flex: none; width: 52px; height: 52px; border-radius: 12px; border: 1px solid var(--line-2); }
.hex { margin: 0 0 2px; font-weight: 700; font-variant-numeric: tabular-nums; letter-spacing: 0.04em; }
.others { display: grid; gap: 12px; }
.grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; }
.grid .look { grid-template-columns: minmax(0, 1fr); align-items: start; }
.grid .shot video { width: 100%; }
.grid .look h2 { font-size: 26px; }
.act { display: flex; }
.btn-sm { min-height: 34px; padding: 0 14px; font-size: 12px; margin-top: 8px; }
.more .muted { margin: 0; }
@media (max-width: 760px) { .grid, .sws { grid-template-columns: minmax(0, 1fr); } .type { grid-template-columns: minmax(0, 1fr); }
  .look, .look.big { grid-template-columns: minmax(0, 1fr); } .grid .shot video, .shot video { width: 160px; } }
"""

PANE_JS = """<script>
// Each button opens the Claude app's own comment box on that look or section. The comment goes to Claude from there.
(function () {
  var tries = 0;
  function start() {
    if (!(window.claude && window.claude.use)) { if (++tries < 20) setTimeout(start, 250); return; }
    window.claude.use('comments').then(function (c) {
      if (!c) return;
      document.querySelectorAll('[data-comment]').forEach(function (b) {
        b.hidden = false;
        b.addEventListener('click', function () {
          c.openComposer({ element: b.closest('[data-comment-target]') }).catch(function (e) {
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


def keep_clip(style, video):
    """A few seconds of a video made in their own look (its sample draft), kept in the look's folder so the board
    plays it: styles/<slug>/sample.mp4 and sample.jpg."""
    st = L.find(style)
    if not st or st.get('builtin'):
        sys.exit('style_board: %s is not one of their own looks' % style)
    d = L.style_dir(st['slug'])
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', '0.3', '-t', '5', '-i', video, '-an', '-vf', 'scale=360:-2,fps=30', '-c:v', 'libx264',
                    '-crf', '28', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', os.path.join(d, 'sample.mp4')], check=True)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', '1.6', '-i', video, '-frames:v', '1', '-vf', 'scale=360:-2', '-q:v', '4',
                    os.path.join(d, 'sample.jpg')], check=True)
    print('CLIP KEPT for %s (the board plays it)' % st['name'])


def main():
    if len(sys.argv) == 4 and sys.argv[1] == '--keep-clip':
        return keep_clip(sys.argv[2], sys.argv[3])
    a = [x for x in sys.argv[1:] if not x.startswith('--')]
    reel = a[0] if a else 'sample'
    shutil.rmtree(os.path.join(OUT, 'clips'), ignore_errors=True)
    media = clips(reel)
    brand = json.load(open(os.path.join(ROOT, 'src', 'brand.json')))
    pane, local, css, fonts = page(brand, media, reel == 'sample')
    adcamp_page.write(OUT, 'Your Look', local, extra_css=css, fonts=fonts, pane_body=pane)
    adcamp_page.files_map(OUT, sorted('clips/' + f for f in os.listdir(os.path.join(OUT, 'clips'))))
    print('BOARD READY qa/style-board/pane.html (%s)' % ('your look plays %s' % reel if any(m[2] for m in media.values())
                                                       else 'the preview clips: %s has no finished video in their look yet' % reel))


if __name__ == '__main__':
    main()

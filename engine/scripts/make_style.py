#!/usr/bin/env python3
"""Build a reel in a named style: a starter look, a saved style, or the cards and panels build.

    python3 scripts/make_style.py <base> <style> [--force]           a second version: <base>-<slug>
    python3 scripts/make_style.py <name> <style> --in-place [--force] the reel itself becomes the style

<style> is a slug or (part of) a style's name. A version is written to src/methodology/reels/<base>-<slug>.config.ts
from the base reel's config (same cut, words, grade, music, post, claims), reshaped to the style's base build
(cards and panels keeps the reel's panel layout, every other look makes it full screen), then the style's own choices on top
(captions, type and color, grade, framing, transitions, back text, sounds, the hook title: scripts/styles_lib.py).
--in-place does the same to the reel's own config: the member's default look, right after the first build, so every
later step (fixes, retime, draft, approval, render) works on the one reel. Registers it in Root.tsx, and marks key
words and zoom punches when the style asks (scripts/dynamic_keys.py). Then run the preview steps and get the draft
approved before rendering. Nothing that may hold approved edits is overwritten without --force.
"""
import datetime
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import reel_config  # noqa: E402
import styles_lib  # noqa: E402


def build(base, st, vid):
    """The config text of <base> in style st, with id vid. Returns (text, notes, zoom mode)."""
    style = st['base']          # the structure: studio keeps the reel's, minimal and hype reshape it
    bc = reel_config.load(base)
    s = open(reel_config.config_path(base)).read()
    if vid != base:
        s = s.replace('"id": "%s"' % base, '"id": "%s"' % vid, 1)
    styled = bool((bc.get('meta') or {}).get('look')) or bool(re.search(r'^  "captionStyle": [^\n]*// [^\n]*style', s, re.M))   # already in a look (meta.look, or an older restyle's own tag)
    if style != 'studio':
        s = reshape(s, style)
    s, bc, strip_notes = strip_look(s, bc, st, styled, start_picks(base).get('effects') or [] if vid == base else [])
    s, notes = styles_lib.apply_overlay(s, st, bc)
    notes = strip_notes + notes
    if style == 'minimal' and ((bc.get('cover') or {}).get('title') or bc.get('inserts') or bc.get('backText')):
        notes.append('%s is captions only: the cover title, words behind you and the follow card or clips are not in it' % st['name'])
    if st.get('zooms') == 'none':
        s = styles_lib.remove_key(s, 'zooms')
    if bc.get('placement') == 'paid' and style != 'studio' and not any(e.get('kind') == 'pinned-line' for e in bc.get('effects', [])):
        # a paid ad says "Click Learn More" on screen; full frame has no CTA panel, so it rides as a pinned line
        f_out = bc['frames']
        s = styles_lib.add_effects(s, [{'kind': 'pinned-line', 'in': max(0, f_out - 150), 'out': f_out, 'text': 'Click Learn More'}],
                                   'paid ad: the call to action on screen')
    if style == 'studio' and not any(sc['mode'] == 'window' for sc in bc['scenes']):
        notes.append('%s has cards and panels, and this reel is already full frame: build a fresh copy of the video under a '
                     'new name (make_reel.sh <video> <new name> --preview), then put that one in %s' % (st['name'], st['name']))
    if style != 'studio' and styled and (bc.get('swaps') or bc.get('thumbnail')):   # never about a first build's own panels
        dropped = (['%d panel%s' % (len(bc['swaps']), '' if len(bc['swaps']) == 1 else 's')] if bc.get('swaps') else []) + \
                  (['the custom cover image'] if bc.get('thumbnail') else [])
        notes.append('%s is full frame: %s from the earlier build %s not in it' % (st['name'], ' and '.join(dropped),
                     'are' if len(dropped) > 1 or bc.get('swaps') and len(bc['swaps']) > 1 else 'is'))
    s = styles_lib.mark_look(s, st['slug'])
    if st.get('hook_title') and not bc.get('backText') and style != 'studio':
        ht = styles_lib.hook_title(bc)
        if ht:
            s = styles_lib.set_key(s, 'backText', [ht], '%s style: hook title from the opening line (reword it if it reads oddly)' % st['name'])
    zooms = st.get('zooms') or ('keys' if style == 'hype' else 'keep')
    return s, notes, zooms


def start_picks(name):
    """What the member picked on the start page for this video (qa/<name>/start.json), or {} for an older video."""
    try:
        return json.load(open(os.path.join(ROOT, 'qa', name, 'start.json')))
    except (OSError, ValueError):
        return {}


def strip_look(s, bc, st, styled, picked=()):
    """What the reel's current look added and the new look decides: its type and color, its transitions, its hook title
    and effects the new look doesn't use. The reel's content (cover, words, cards with their own words, music, post)
    stays, and so do the effects they picked on the start page for this video. Returns the text, the config as it now
    stands (for the overlay's transitions and the hook title) and plain notes naming what it removed, by the names they
    saw in the Picker."""
    s = styles_lib.remove_key(s, 'look')
    removed = []
    if styled:   # what the old look decided goes, the new look sets its own (or none)
        for k in ('grade', 'framing'):
            if k not in st:
                s = styles_lib.remove_key(s, k)
                bc = {x: v for x, v in bc.items() if x != k}
    effects = bc.get('effects', [])
    allowed = st.get('effects_allowed')
    keep = []
    for e in effects:
        k = e.get('kind')
        if k == 'transition' and (st.get('transitions') or styled):
            continue   # the new look places its own
        if allowed is not None and k not in allowed and k not in ('transition', 'card', 'pinned-line') and k not in picked:
            removed.append(fx_name(k))
            continue   # a card carries their words, a pinned line their call to action: both stay
        keep.append(e)
    if keep != effects:
        s = styles_lib.remove_key(s, 'effects')
        s = styles_lib.add_effects(s, keep, 'kept from the reel')
    drop_bt = st.get('hook_title') is False or (styled and not st.get('hook_title') and st.get('backText') != 'keep')
    if drop_bt and bc.get('backText'):
        s = styles_lib.remove_key(s, 'backText')
        prev = styles_lib.by_slug((bc.get('meta') or {}).get('look')) or {}   # the look it had: a hook title there is what they saw
        removed.append('%s (%s)' % ('the hook title' if prev.get('hook_title') else 'the words behind you',
                                    ', '.join('"%s"' % b['text'] for b in bc['backText'])))
    bc = dict(bc, effects=keep)
    if drop_bt:
        bc.pop('backText', None)
    names = list(dict.fromkeys(removed))
    notes = ['%s does not use %s: taken out (the version before is saved)' % (st['name'], ', '.join(names))] if names else []
    return s, bc, notes


def fx_name(kind):
    """The name a member saw in the Picker for an effect kind (picker/catalog.json), else the kind in plain words."""
    try:
        cat = json.load(open(os.path.join(ROOT, 'picker', 'catalog.json')))
        return next(e['name'] for e in cat['effects'] if e['key'] == kind)
    except (OSError, ValueError, StopIteration, KeyError):
        return kind.replace('-', ' ')


def main():
    a = [x for x in sys.argv[1:] if not x.startswith('--')]
    if len(a) != 2:
        sys.exit(__doc__)
    base, want = a
    in_place = '--in-place' in sys.argv
    st = styles_lib.find(want)
    if st and st.get('hidden') and not st.get('aliases') and os.environ.get('AVS_HOME'):   # a member's install
        sys.exit('make_style: "%s" is an engine base, not a look. Use a starter look (Big Energy for punchy, Clean Talk '
                 'for captions-first) or one of theirs.' % want)
    if st and st['slug'] == 'studio' and not in_place:
        sys.exit('make_style: cards and panels is the full build itself, not a version of a reel in another look. '
                 'Build the reel with it from the start (make_reel.sh, then skip --in-place).')
    if not st:
        sys.exit('make_style: no style "%s". Styles: %s'
                 % (want, ', '.join(x['name'] for x in styles_lib.all_styles())))
    errs = styles_lib.check(st)
    if errs:
        sys.exit('make_style: %s style.json: %s' % (st['name'], '; '.join(errs)))
    vid = base if in_place else '%s-%s' % (base, st['slug'])
    out = reel_config.config_path(vid)
    if in_place:
        if st['slug'] == 'studio':
            if any(sc['mode'] == 'window' for sc in reel_config.load(base)['scenes']):
                print('make_style: %s is the full build (cards and panels) already: nothing to change' % base)
            else:
                print('make_style: %s is full frame. Cards and panels need a fresh build: make_reel.sh <video> <new name> '
                      '--preview, then fill it without a restyle' % base)
            return
        cur = open(out).read()
        if ((reel_config.load(base).get('meta') or {}).get('look') or re.search(r'^  "captionStyle": [^\n]*// [^\n]*style', cur, re.M)) \
                and '--force' not in sys.argv:
            sys.exit('make_style: %s is already styled (use --force to restyle it, which redoes its look choices)' % os.path.relpath(out, ROOT))
    elif os.path.exists(out) and '--force' not in sys.argv:
        sys.exit('make_style: %s exists (use --force to rebuild it from %s)' % (os.path.relpath(out, ROOT), base))
    bc = reel_config.load(base)
    beds = json.load(open(os.path.join(ROOT, 'sounds.json'))).get('music_beds') or []
    if (bc.get('music') or beds) and bc.get('musicStart') is None and st.get('music') is not False:
        # the house bed has a quiet 10s intro: without musicStart the music takes 11s to arrive
        # (caught twice, Chris 2026-10-02). Set it on the BASE so every variant inherits it.
        print('make_style: WARNING %s has no "musicStart" (the bed will take ~11s to come in). '
              'Add "musicStart": 11 to the base config first, then re-run.' % base)
    s, notes, zooms = build(base, st, vid)
    if os.path.exists(out):   # a restyle or a rebuilt version replaces work: keep every version before it
        bdir = os.path.join(ROOT, 'qa', base)
        os.makedirs(bdir, exist_ok=True)
        stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
        with open(os.path.join(bdir, 'before-restyle-%s.config.ts' % stamp), 'w') as f:
            f.write(open(out).read())
    open(out, 'w').write(s)
    if not in_place:
        root = os.path.join(ROOT, 'src', 'methodology', 'Root.tsx')
        r = open(root).read()
        line = "    <Reel id=\"%s\" load={() => import('./reels/%s.config')} />" % (vid, vid)
        if line not in r:
            r = r.replace('    <Reel id="%s" load' % base, line + '\n    <Reel id="%s" load' % base, 1)
            open(root, 'w').write(r)
    if zooms == 'keys' or (st['base'] == 'hype' and zooms != 'none'):
        s = styles_lib.remove_key(s, 'zooms')   # a fresh block (a retimed config may hold it on one line)
        s = s.replace('  "placement":', '  "zooms": [  // generated by scripts/dynamic_keys.py\n  ],\n  "placement":', 1)
        open(out, 'w').write(s)
        subprocess.run([sys.executable, os.path.join(HERE, 'dynamic_keys.py'), vid], check=True)
    elif st['base'] != 'studio':   # no zoom punches, but the key words are marked for looks that color them
        subprocess.run([sys.executable, os.path.join(HERE, 'dynamic_keys.py'), vid, '--keys-only'], check=True)
    for n in notes:
        print('make_style: note: ' + n)
    picks = start_picks(base) if in_place else {}
    if picks:   # a video begun on the start page: their caption style, color and effects go back on (start_page.py apply)
        def caps(look):   # money green is a color choice, not the caption type
            c = dict((look.get('look') or {}).get('captions') or {})
            c.pop('money', None)
            return look.get('captionStyle'), c
        old = styles_lib.by_slug((bc.get('meta') or {}).get('look') or '') or {}
        if old and caps(old) != caps(st) and st.get('captionStyle'):   # a look change about the captions: the new look's win
            picks['captionStyle'] = st['captionStyle']
            json.dump(picks, open(os.path.join(ROOT, 'qa', base, 'start.json'), 'w'), indent=1)
        subprocess.run([sys.executable, os.path.join(HERE, 'start_page.py'), 'apply', base], check=True)
    print('make_style: wrote %s in %s%s. Next: matte_reel.py, scene_map.py, test_layout.mjs, extract_reel_stills.py --preview, then approval.'
          % (os.path.relpath(out, ROOT), st['name'], '' if in_place else ' and registered it'))


def reshape(s, style):
    """The minimal and hype base builds: full screen throughout, no panels, their own captions."""
    L = styles_lib
    sp = L._span(s, 'scenes')
    s = s[:sp[0]] + '  "scenes": [\n    {"from": 0, "mode": "full"}  // %s style: full screen throughout\n  ],\n' % style + s[sp[1]:]
    sp = L._span(s, 'swaps')
    s = s[:sp[0]] + '  "swaps": [\n  ],\n' + s[sp[1]:]
    for k in ('thumbnail', 'zooms', 'captionAccent', 'captionStyle'):
        s = L.remove_key(s, k)
    if style == 'minimal':
        s = L.remove_key(s, 'backText')
        s = L.remove_key(s, 'inserts')
        # Minimal is captions only: of the effects it keeps the camera transitions (moves, not overlays)
        cfg_fx = re.findall(r'\{[^{}\n]*"kind": "transition"[^{}\n]*\}', s[L._span(s, 'effects')[0]:L._span(s, 'effects')[1]]) if L._span(s, 'effects') else []
        keep = [json.loads(x) for x in cfg_fx if re.search(r'"style": "(whip|zoom|spin|flash)"', x)]
        s = L.remove_key(s, 'effects')
        s = L.add_effects(s, keep, 'minimal style: camera transitions only')
        s = L.set_key(s, 'cover', None, 'minimal style: no overlays outside captions')
        cap = '  "captionStyle": "punch",  // minimal style\n'
    else:
        cap = ('  "captionStyle": "dynamic",  // hype style: two-font stacked captions in the brand fonts\n'
               '  "zooms": [  // generated by scripts/dynamic_keys.py\n  ],\n')
    return s.replace('  "placement":', cap + '  "placement":', 1)

if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""The member's saved styles (styles/<slug>/: style.json for the build, style.md in plain words).

    python3 scripts/my_styles.py list
    python3 scripts/my_styles.py show <style>
    python3 scripts/my_styles.py new "<name>" [--base "cards and panels"]   a blank style on the full-screen build (or that one)
    python3 scripts/my_styles.py new "<name>" --like <style>        their own copy of a starter look (or any style) to tweak
    python3 scripts/my_styles.py save <style> --from-reel <reel>     the reel's dialed-in look becomes the style's
    python3 scripts/my_styles.py save "<name>" --from-picks           the Picker's mix (styles/picks.json) as a style
    python3 scripts/my_styles.py default <style>                     plain "make a reel" uses it
    python3 scripts/my_styles.py rename <style> "<new name>"
    python3 scripts/my_styles.py retire <style>                      hidden from the list, kept on disk
    python3 scripts/my_styles.py last                                what the last finished video used (or "LAST none")
    python3 scripts/my_styles.py last --save <reel> --style <style> [--music sounds/music/<file>|none]   after a hand-over

<style> is a slug or (part of) a name. Built-in styles (the starter looks, and the cards and panels build) can be
used and set as the default, never changed: tweak a starter by making their own copy (--like). A reel is put in a style with scripts/make_style.py <reel> <style>.
"""
import datetime
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import reel_config  # noqa: E402
import styles_lib as L  # noqa: E402

MD = '''# {name}

Made: {date}. Edit this file in plain words. style.json is what the build reads. Keep both in step.

## Made from
- (each example: the link or file, and what was taken from it)

## Type
## Color
## Captions
## Caption motion
## Pace
## Framing
## Graphic elements
## Sound

## Standing notes
- (rules from their notes that hold for every reel in this style)

## Could not be matched
- (what the examples do that AVS can't, said plainly)
'''

# what a dialed-in reel hands back to its style
FROM_REEL = ('captionStyle', 'look', 'grade', 'framing', 'sfx')   # music is picked per video, never part of a style


def need(name):
    st = L.find(name)
    if not st:
        sys.exit('my_styles: no style matches "%s". Saved styles: %s' % (name, ', '.join(s['name'] for s in L.all_styles())))
    return st


def write(st):
    json.dump(st, open(os.path.join(L.style_dir(st['slug']), 'style.json'), 'w'), indent=1)


def clear_retired(slug):
    """A style they retired keeps its folder: set it aside under a dated name, so the name can be used again."""
    d = L.style_dir(slug)
    p = os.path.join(d, 'style.json')
    if os.path.isdir(d) and os.path.exists(p) and json.load(open(p)).get('retired'):
        os.rename(d, '%s-retired-%s' % (d, datetime.datetime.now().strftime('%Y%m%d-%H%M%S')))


def from_picks(name, dflt):
    p = os.path.join(L.STYLES, 'picks.json')
    if not os.path.exists(p):
        sys.exit('my_styles: no picks saved yet. Open the Picker: python3 scripts/picker.py')
    pk = json.load(open(p))
    if pk.get('fonts'):   # a font pick is theirs everywhere: captions, cards, carousels
        bp = os.path.join(L.ROOT, 'src', 'brand.json')
        brand = json.load(open(bp))
        brand.update(sans=pk['fonts']['sans'], serif=pk['fonts']['serif'])
        json.dump(brand, open(bp, 'w'), indent=2)
        print('my_styles: fonts set in src/brand.json: %s with %s for key words' % (pk['fonts']['sans'], pk['fonts']['serif']))
    if pk.get('mode') == 'style':
        st = need(pk['style'])
        json.dump({'default': st['slug']}, open(L.defaults_path(), 'w'))
        print('my_styles: they picked the ready style "%s": it is the default now (no new style needed)' % st['name'])
        return
    slug = L.member_slug(name)
    clear_retired(slug)
    st = L.by_slug(slug) if os.path.exists(L.style_dir(slug)) else None
    if st and st.get('builtin'):
        sys.exit('my_styles: %s is one of the starter looks. Pick another name.' % st['name'])
    if st and '--replace' not in sys.argv:   # never write a mix over one of their styles without asking
        sys.exit('my_styles: they already have a style called "%s". Ask: replace it, or pick another name? '
                 '(Replace: run again with --replace.)' % st['name'])
    if st:   # a real replace: nothing of the old style survives but its name and folder
        st = {'name': st['name'], 'slug': st['slug'], 'created': st.get('created', datetime.date.today().isoformat()), 'sources': []}
        open(os.path.join(L.style_dir(slug), 'style.md'), 'w').write(MD.format(name=st['name'], date=st['created']).replace(
            '- (each example: the link or file, and what was taken from it)', '- Picked in the Picker on %s.' % datetime.date.today().isoformat()))
    else:
        os.makedirs(os.path.join(L.style_dir(slug), 'sources'))
        st = {'name': name, 'slug': slug, 'created': datetime.date.today().isoformat(), 'sources': []}
        open(os.path.join(L.style_dir(slug), 'style.md'), 'w').write(MD.format(name=name, date=st['created']).replace(
            '- (each example: the link or file, and what was taken from it)', '- Picked in the Picker on %s.' % st['created']))
    # full screen with words behind them, so any picked effect has room (studio's windows would hide most of them)
    st.update({'base': 'hype', 'captionStyle': pk['captionStyle'], 'zooms': 'none',
               'effects_allowed': pk.get('effects') or [], 'effect_parts': pk.get('parts'),
               'transitions_allowed': pk.get('transitions') or []})
    if st['transitions_allowed']:
        st['transitions'] = {'first_join': st['transitions_allowed'][0]}
    # one plain line for "what styles do I have", in the names they saw in the Picker
    try:
        cat = json.load(open(os.path.join(L.ROOT, 'picker', 'catalog.json')))
    except (OSError, ValueError):
        cat = {}
    nm = lambda group, k: next((x['name'] for x in cat.get(group, []) if x.get('key') == k), k.replace('-', ' '))  # noqa: E731
    fx = [nm('effects', k) for k in st['effects_allowed']]
    st['feel'] = 'Your mix from the Picker: %s captions%s.' % (nm('captions', st['captionStyle']), ' with ' + ', '.join(fx) if fx else '')
    md = os.path.join(L.style_dir(slug), 'style.md')
    if os.path.exists(md):
        txt = open(md).read()
        txt = txt.replace('## Captions\n', '## Captions\n- %s, picked in the Picker.\n' % nm('captions', st['captionStyle']), 1)
        txt = txt.replace('## Graphic elements\n', '## Graphic elements\n- %s\n' % (', '.join(fx) or 'None picked.'), 1)
        open(md, 'w').write(txt)
    st['updated'] = datetime.date.today().isoformat()
    errs = L.check(st)
    if errs:
        sys.exit('my_styles: not saved: ' + '; '.join(errs))
    write(st)
    if not dflt:
        json.dump({'default': st['slug']}, open(L.defaults_path(), 'w'))
    print('my_styles: saved the Picker mix as "%s": %s captions, effects %s, transitions %s%s' % (
        name, st['captionStyle'], ', '.join(st['effects_allowed']) or 'none', ', '.join(st['transitions_allowed']) or 'none',
        ' (now the default)' if not dflt else ''))


def safe_name(st):
    """The name a member may hear: an engine base (hidden) is never named, its alias or "your usual look" instead."""
    if not st.get('hidden'):
        return st['name']
    return (st.get('aliases') or ['your usual look'])[0]


def last(a):
    """styles/last.json: the style, placement and music of the last finished video (the start page prefills from
    styles/start-last.json; this one keeps the music file, so "same track as last time" can be offered)."""
    p = os.path.join(L.STYLES, 'last.json')
    if '--save' not in a:
        if not L.default_slug():
            print('LAST none (no look set yet: run the look step first)')
            return
        if not os.path.exists(p):
            print('LAST none')
            return
        lt = json.load(open(p))
        st = L.by_slug(L.default_slug())   # "same" builds in their default look, so name that one
        if not st or st.get('retired'):
            print('LAST none (the style it used is gone)')
            return
        music, f = None, lt.get('music')
        if f and os.path.isfile(os.path.join(L.ROOT, f)):   # a kept track: its title for them, the file for Claude
            cp = os.path.join(L.ROOT, 'sounds', 'music', 'credits.json')
            c = (json.load(open(cp)).get(f) if os.path.exists(cp) else None) or {}
            music = '"%s"' % c['title'] if c.get('title') else 'the same track'
        shown = safe_name(st)
        print('LAST %s | %s | music: %s' % (shown, 'paid ad' if lt.get('placement') == 'paid' else 'regular post', music or 'none'))
        if music:
            print('LAST FILE %s   (for find_music.py --use, never say it to them)' % f)
        return
    if '--style' not in a:
        sys.exit(__doc__)
    cfg = reel_config.load(a[a.index('--save') + 1])
    st = need(a[a.index('--style') + 1])
    music = a[a.index('--music') + 1].strip() if '--music' in a else 'none'
    lt = {'style': st['slug'], 'placement': cfg.get('placement', 'organic'), 'music': None if music.lower() == 'none' else music,
          'reel': cfg['id'], 'saved': datetime.date.today().isoformat()}
    os.makedirs(L.STYLES, exist_ok=True)
    json.dump(lt, open(p, 'w'), indent=1)
    print('my_styles: saved for next time (%s, %s, %s)' % (
        safe_name(st), 'paid ad' if lt['placement'] == 'paid' else 'regular post', 'the same track on offer' if lt['music'] else 'no music'))


def main():
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    cmd = a[0]
    dflt = L.default_slug()
    if cmd == 'list':
        for st in L.all_styles():
            kind = 'starter look' if st.get('starter') else ('built in' if st.get('builtin') else 'yours, saved %s' % st.get('created', ''))
            print('%-18s %-22s %s%s' % (st['name'], kind, st.get('feel', ''), '   (default)' if st['slug'] == dflt else ''))
        if not dflt:
            print('No default yet: the next video starts by picking one (Clean Talk if they have no preference).')
        elif L.by_slug(dflt) and L.by_slug(dflt).get('hidden'):
            print('Default: %s' % safe_name(L.by_slug(dflt)))
        return
    if cmd == 'new':
        if len(a) < 2:
            sys.exit(__doc__)
        name = a[1].strip()
        like = L.find(a[a.index('--like') + 1]) if '--like' in a else None
        if '--like' in a and not like:
            sys.exit('my_styles: no style "%s" to start from' % a[a.index('--like') + 1])
        base = like['base'] if like else 'hype'   # full frame, like every starter look
        if '--base' in a and not like:
            want = a[a.index('--base') + 1]
            hit = L.find(want)
            base = want if want in L.BASES else (hit['slug'] if hit and hit['slug'] in L.BASES else None)
            if not base:
                sys.exit('my_styles: --base takes "cards and panels", or leave it out for the full-screen build')
        slug = L.member_slug(name)
        clear_retired(slug)
        if os.path.exists(L.style_dir(slug)):
            sys.exit('my_styles: a style called "%s" already exists. Pick another name.' % name)
        os.makedirs(os.path.join(L.style_dir(slug), 'sources'))
        st = {'name': name, 'slug': slug, 'created': datetime.date.today().isoformat(), 'base': base, 'sources': []}
        if like:   # everything the look decides, none of what makes it a shipped starter
            st.update({k: v for k, v in like.items() if k not in ('name', 'slug', 'builtin', 'starter', 'order', 'hidden', 'aliases', 'created', 'sources')})
            st['started_from'] = like['name']
        write(st)
        md = MD.format(name=name, date=st['created'])
        if like:   # start their notes from the starter's own plain-words description
            src = os.path.join(L.style_dir(like['slug']), 'style.md')
            body = open(src).read().split('\n', 1)[1] if os.path.exists(src) else ''
            md = '# %s\n\nMade: %s, started from the %s starter look. Edit this file in plain words. style.json is what the build reads.\n%s' % (
                name, st['created'], like['name'], body)
        open(os.path.join(L.style_dir(slug), 'style.md'), 'w').write(md)
        print('my_styles: made "%s" in %s (style.json, style.md, sources/)' % (name, os.path.relpath(L.style_dir(slug), L.ROOT)))
        return
    if cmd == 'last':
        return last(a)
    if len(a) < 2:
        sys.exit(__doc__)
    if cmd == 'save' and '--from-picks' in a:
        return from_picks(a[1].strip(), dflt)
    st = need(a[1])
    if cmd == 'show':
        d = L.style_dir(st['slug'])
        print('%s: %s' % (st['name'], d))
        md = os.path.join(d, 'style.md')
        if os.path.exists(md):
            print(open(md).read())
        print(json.dumps({k: v for k, v in st.items() if k not in ('name', 'slug')}, indent=1))
        return
    if cmd == 'default':
        if st.get('hidden') and not st.get('aliases'):
            sys.exit('my_styles: that is an engine base, not a look. Pick a starter look or one of theirs.')
        json.dump(dict({'default': st['slug']}, **({'by_name': True} if st.get('hidden') else {})), open(L.defaults_path(), 'w'))
        print('my_styles: "%s" is the default now' % safe_name(st))
        return
    if st.get('builtin'):
        sys.exit('my_styles: %s is built in and stays as it is. Make your own: my_styles.py new "<name>"' % safe_name(st))
    if cmd == 'save':
        if '--from-reel' not in a:
            sys.exit(__doc__)
        cfg = reel_config.load(a[a.index('--from-reel') + 1])
        took = []
        for k in FROM_REEL:
            if k == 'grade' and (cfg.get('color') or 'natural') != 'natural':
                continue   # a color look trimmed the reel's grade for this video: the style keeps its own
            if k in cfg and cfg[k] is not None:
                st[k] = cfg[k]
                took.append(k)
            elif k in ('framing', 'grade') and k in st:   # a note took it off the reel ("one framing", "no film look"): off the style too
                del st[k]
                took.append('no ' + k)
        errs = L.check(st)
        if errs:
            sys.exit('my_styles: not saved: ' + '; '.join(errs))
        st['saved_from'] = cfg['id']
        st['updated'] = datetime.date.today().isoformat()
        write(st)
        if not dflt:
            json.dump({'default': st['slug']}, open(L.defaults_path(), 'w'))
        print('my_styles: saved %s into "%s"%s' % (', '.join(took), st['name'], ' (now the default)' if not dflt else ''))
        return
    if cmd == 'rename':
        if len(a) < 3:
            sys.exit(__doc__)
        st['name'] = a[2].strip()
        write(st)
        print('my_styles: renamed to "%s" (the folder keeps its name, %s)' % (st['name'], st['slug']))
        return
    if cmd == 'retire':
        st['retired'] = True
        write(st)
        if dflt == st['slug']:
            os.remove(L.defaults_path())
        print('my_styles: "%s" is hidden from the list and kept on disk in %s' % (st['name'], os.path.relpath(L.style_dir(st['slug']), L.ROOT)))
        return
    sys.exit(__doc__)


if __name__ == '__main__':
    main()

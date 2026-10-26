"""Saved styles: folders under styles/<slug>/ (style.json for the build, style.md in plain words).

A style is a BASE (studio, minimal or hype: the structure of the build) plus an OVERLAY of choices the
member's examples or words decided. make_style.py applies both to a reel's config; my_styles.py makes,
lists and saves them. Built-in styles carry only their base. Overlay fields, all optional:

  captionStyle   "lines" | "punch" | "dynamic" | "word" | "bigword" | "pill" | "editorial" | "steps"
  look           {"captions": {...CaptionLook}, "backText": {"font", "color", "outline"}}   (ReelConfig.ts)
  grade          a Grade object, or null for the footage as filmed
  framing        {"tight": 1.05-1.5}: every other take drawn tighter, or null for one framing
  zooms          "keys" (punch-ins on key words, scripts/dynamic_keys.py) | "none" | "keep"
  backText       "keep" | "drop"
  cover          "keep" | "drop"
  transitions    {"first_join": <style>, "every_join": <style>}: flash, whip, zoom, spin, iris or bars
  music          false for no bed (else the reel's own choice)
  sfx            false for no cue sounds
  effects_allowed, effect_parts, transitions_allowed   what the Picker mix allows: Claude places effects only from
                 effects_allowed (and only in their parts: hook, middle, end), transitions from transitions_allowed
  hook_title     true: make_style.py writes a 2-3 word hook title over the head at the open when the reel has none
  open           {"scale": 1.0-1.6}: the punch-in on the first words (1.0 for none)

Style folders also carry: builtin (shipped, never edited), starter (one of the starter looks members choose from),
feel (one plain line for lists and the Picker), hidden (a base kept for the engine, in no list or menu: still found
by name, so "cards and panels" reaches Studio).
"""
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
STYLES = os.path.join(ROOT, 'styles')
BASES = ('studio', 'minimal', 'hype')
TRANSITIONS = ('flash', 'whip', 'zoom', 'spin', 'iris', 'bars')
CAPTION_STYLES = ('lines', 'punch', 'dynamic', 'word', 'bigword', 'pill', 'editorial', 'steps')
FPS = 30


def slugify(name):
    s = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
    return s or 'style'


def member_slug(name):
    """The folder for a style the member names. The engine bases keep their folders, so a style they call "Hype" lives
    in hype-look and is still found by its name."""
    s = slugify(name)
    return s + '-look' if s in BASES else s


def by_slug(slug):
    """A style by its exact folder name (hidden ones too), or None."""
    return next((st for st in all_styles(include_hidden=True) if st['slug'] == slug), None) if slug else None


def style_dir(slug):
    return os.path.join(STYLES, slug)


def all_styles(include_hidden=False):
    """Starters first (in their shipped order), then the member's own. Retired never, hidden only when asked."""
    out = []
    if os.path.isdir(STYLES):
        for d in sorted(os.listdir(STYLES)):
            p = os.path.join(STYLES, d, 'style.json')
            if os.path.isfile(p):
                st = json.load(open(p))
                if not st.get('retired') and (include_hidden or not st.get('hidden')):
                    out.append(st)
    return sorted(out, key=lambda st: (0 if st.get('starter') else 1, st.get('order', 99), st['name'].lower()))


def find(name):
    """A style by slug or by (part of) its name, case-insensitive. None when nothing or several match."""
    want = name.strip().lower()
    styles = all_styles(include_hidden=True)
    # their own and the starters first, so a style they named "Hype" wins over the engine base of that name
    seen, hidden = [st for st in styles if not st.get('hidden')], [st for st in styles if st.get('hidden')]
    for st in seen + hidden:
        if want in (st['slug'], st['name'].lower()) or want in [x.lower() for x in st.get('aliases', [])]:
            return st
    for group in (seen, hidden):
        hits = [st for st in group if want in st['name'].lower() or want in st['slug']]
        if hits:
            return hits[0] if len(hits) == 1 else None
    return None


def defaults_path():
    return os.path.join(STYLES, 'default.json')


def default_slug():
    """Their default look, or None. A default that is gone, retired, or an engine base nobody may name (minimal, hype)
    counts as none, so the look step runs. "cards and panels" (studio, which has an alias) is a real choice."""
    p = defaults_path()
    d = json.load(open(p)) if os.path.exists(p) else {}
    slug = d.get('default')
    st = by_slug(slug)
    if not st or (st.get('hidden') and not st.get('aliases')):
        return None
    if st.get('hidden') and not d.get('by_name'):   # a Studio default from before looks existed: they never chose it
        return None
    return slug


# ---------------------------------------------------------------- config text editing
# Reel configs are commented JSON inside a .ts file, one top-level key per line at two spaces. These
# edit that text in place so comments elsewhere survive.

def _span(s, key):
    """(start, end) of a top-level key's line(s), or None."""
    m = re.search(r'^  "%s": ' % re.escape(key), s, re.M)
    if not m:
        return None
    line_end = s.index('\n', m.start()) + 1
    first = s[m.start():line_end]
    value = first[m.end() - m.start():].split('//')[0].strip()
    if value.endswith(('[', '{')):
        close = re.compile(r'^  [\]\}],?[^\n]*\n', re.M).search(s, line_end)
        return m.start(), close.end()
    return m.start(), line_end


def remove_key(s, key):
    sp = _span(s, key)
    return s if sp is None else s[:sp[0]] + s[sp[1]:]


def set_key(s, key, value, note):
    """Set a top-level key to a JSON value on one line, right before "placement"."""
    s = remove_key(s, key)
    line = '  "%s": %s,  // %s\n' % (key, json.dumps(value, separators=(', ', ': ')), note)
    if '\n  "placement":' not in s:
        raise ValueError('config has no "placement" line to anchor on')
    return s.replace('\n  "placement":', '\n' + line.rstrip('\n') + '\n  "placement":', 1)


def add_effects(s, entries, note):
    if not entries:
        return s
    body = ',\n'.join('    %s' % json.dumps(e, separators=(', ', ': ')) for e in entries)
    sp = _span(s, 'effects')
    if sp and s[sp[0]:sp[1]].count('\n') == 1:   # held on one line (a retimed config): open it back up with what it holds
        old = json.loads(s[sp[0]:sp[1]].split(': ', 1)[1].split('//')[0].strip().rstrip(','))
        s = remove_key(s, 'effects')
        return add_effects(s, old + list(entries), note)
    if sp is None:
        return s.replace('\n  "placement":', '\n  "effects": [  // %s\n%s\n  ],\n  "placement":' % (note, body), 1)
    block = s[sp[0]:sp[1]]
    inner = block[block.index('\n') + 1:block.rindex('\n  ]')]
    sep = ',\n' if inner.strip() else ''
    new = block[:block.index('\n') + 1] + (inner.rstrip().rstrip(',') + sep if inner.strip() else '') + body + '\n' + block[block.rindex('  ]'):]
    return s[:sp[0]] + new + s[sp[1]:]


def video_joins(cfg):
    """Picture joins on the cut, in frames, from the cut's sidecar (written by last_take.py)."""
    p = os.path.join(ROOT, 'public', os.path.splitext(cfg['src'])[0] + '.json')
    if not os.path.exists(p):
        return []
    return [round(t * FPS) for t in json.load(open(p)).get('videoJoins', [])]


def mark_look(s, slug):
    """Record the look a reel is built in, inside meta (kept by retime_reel.py), so a later restyle knows."""
    m = re.search(r'^  "meta": (\{.*\})\s*$', s, re.M)
    if not m:
        return s
    meta = json.loads(m.group(1))
    meta['look'] = slug
    return s[:m.start(1)] + json.dumps(meta, separators=(', ', ': ')) + s[m.end(1):]


def apply_overlay(s, st, cfg):
    """The style's choices on top of the base build. Returns (config text, notes for the person)."""
    notes = []
    tag = '%s style' % st['name']
    if 'captionStyle' in st:
        s = remove_key(s, 'captionAccent') if st['captionStyle'] != 'dynamic' else s
        s = set_key(s, 'captionStyle', st['captionStyle'], tag)
    if st.get('look'):
        s = set_key(s, 'look', st['look'], tag + ': type and color')
    if 'grade' in st:
        g = st['grade']
        if g and (cfg.get('color') or 'natural') != 'natural':   # a color look sets the color: the look keeps only vignette and grain
            g = {k: v for k, v in g.items() if k in ('vignette', 'film')}
        s = set_key(s, 'grade', g, tag) if g else remove_key(s, 'grade')
    if 'framing' in st:
        s = set_key(s, 'framing', st['framing'], tag + ': every other take tighter') if st['framing'] else remove_key(s, 'framing')
    if st.get('open') is not None and re.search(r'^  "open": \{', s, re.M):   # the punch-in at the start (scale 1.0: none)
        m = re.search(r'^  "open": (\{[^\n]*?\}),', s, re.M)
        cur = json.loads(m.group(1))
        cur.update(st['open'])
        s = s[:m.start(1)] + json.dumps(cur, separators=(', ', ': ')) + s[m.end(1):]
    if st.get('backText') == 'drop':
        s = remove_key(s, 'backText')
    if st.get('cover') == 'drop':
        s = set_key(s, 'cover', None, tag + ': no cover title')
    if st.get('music') is False and not isinstance(cfg.get('music'), str):   # a track picked for this reel wins
        s = set_key(s, 'music', False, tag + ': no music')
    if st.get('sfx') is False:
        s = set_key(s, 'sfx', False, tag + ': no cue sounds')
    tr = st.get('transitions') or {}
    joins = video_joins(cfg)
    have = {e.get('at') for e in cfg.get('effects', []) if e.get('kind') == 'transition'}
    add = []
    every = tr.get('every_join')
    first = tr.get('first_join')
    for i, at in enumerate(j for j in joins if j > 45 and j < cfg['frames'] - 15):
        kind = first if i == 0 and first else every
        if kind and at not in have:
            add.append({'kind': 'transition', 'at': at, 'style': kind})
    if (first or every) and not joins:
        notes.append('no picture joins in this cut, so the %s transitions have nowhere to go' % tag)
    s = add_effects(s, add, tag + ': transitions on picture joins')
    return s, notes


def check(st):
    """Problems with a style.json, in plain words (empty = fine)."""
    errs = []
    if st.get('base') not in BASES:
        errs.append('base must be one of %s' % ', '.join(BASES))
    if st.get('captionStyle') not in (None,) + CAPTION_STYLES:
        errs.append('captionStyle must be one of %s' % ', '.join(CAPTION_STYLES))
    for k in ('first_join', 'every_join'):
        v = (st.get('transitions') or {}).get(k)
        if v is not None and v not in TRANSITIONS:
            errs.append('transitions.%s must be one of %s' % (k, ', '.join(TRANSITIONS)))
    if st.get('zooms') not in (None, 'keys', 'none', 'keep'):
        errs.append('zooms must be keys, none or keep')
    for k in ('backText', 'cover'):
        if st.get(k) not in (None, 'keep', 'drop'):
            errs.append('%s must be keep or drop' % k)
    t = (st.get('framing') or {}).get('tight')
    if t is not None and not 1.05 <= t <= 1.5:
        errs.append('framing.tight must be 1.05-1.5 (or no framing at all)')
    if st.get('hook_title') not in (None, True, False):
        errs.append('hook_title must be true or false')
    return errs


FILLER = {'so', 'okay', 'ok', 'um', 'uh', 'hey', 'well', 'alright', 'and', 'but', 'now', 'look', 'listen', 'i', "i've",
          "i'm", 'the', 'a', 'an', 'to', 'of', 'with', 'about', 'over', 'that', 'this', 'it', 'is', 'was', 'had', 'have',
          'my', 'your', 'you', 'we', 'our', 'for', 'in', 'on', 'at', 'be', 'are', 'just', 'really', 'very', 'so',
          'when', 'if', 'what', 'how', 'why', 'who', 'there', 'here', 'they', 'them', 'he', 'she', 'his', 'her', 'its'}


def hook_title(cfg):
    """A 2-3 word hook title from the reel's own opening, shown over the head while the first line is said. The cover
    title when it is written, else the first content words of the first sentence. Claude may reword it."""
    words = [w for w in cfg['words'] if w['t']]
    if not words:
        return None
    norm = lambda t: re.sub(r"[^a-z0-9']", '', t.lower())  # noqa: E731
    spoken = {norm(w['t']) for w in words}
    title = ((cfg.get('cover') or {}).get('title') or '').strip()
    if not title or 'TODO' in title or any(norm(x) not in spoken for x in title.split()):   # back text must be said aloud
        first = [norm(w['t']) for w in words if w['sent'] == words[0]['sent'] and norm(w['t'])]
        runs, cur = [], []   # stretches of the line without filler words: "same conversation", "four different chiropractors"
        for t in first:
            if t in FILLER:
                runs, cur = runs + ([cur] if cur else []), []
            else:
                cur.append(t)
        runs += [cur] if cur else []
        pick = next((r for r in runs if len(r) >= 2), runs[0] if runs else first[:3])
        title = ' '.join(pick[:3])
    parts = title.split()[:3]
    while len(parts) > 1 and len(' '.join(parts)) > 18:   # the engine's limit: 1-3 words, 18 characters
        parts = parts[:-1]
    title = ' '.join(parts)[:18]
    f_in = max(0, round(words[0]['s'] * FPS))
    first_end = max(w['e'] for w in words if w['sent'] == words[0]['sent'])
    f_out = max(f_in + 45, min(round(first_end * FPS), f_in + 90))
    return {'text': title, 'in': f_in, 'out': min(f_out, cfg['frames'] - 1)}

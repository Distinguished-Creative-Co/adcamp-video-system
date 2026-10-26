#!/usr/bin/env python3
"""Step 4 — build src/methodology/reels/<name>.config.ts from the pipeline outputs.

    python3 scripts/gen_reel_config.py <name> [--face X,Y] [--regen] [--no-register]

Reads script/<name>.txt and script/word-timings/<name>-cut-wx.json. The writer's
spelling goes onto whisperX timing through script_phrases.phrases(), then words are chunked into short caption lines. Default direction is
structural and deterministic (no API key anywhere):

  scenes  beat 1 full (the hook, with the open punch-in), then alternate window / full
          by beat, ending in a window so the close can carry the CTA panel
  swaps   one STAT panel on the sentence with the most numerals, if it sits in a window
          beat; one CTA panel on the last beat, held to the end

Stat labels and CTA copy are left as TODO for the operator to write in the config. The
scene map refuses to call a config ready while a TODO remains. An existing config is
never overwritten without --regen. Registers one <Reel .../> line in Root.tsx.
"""
import datetime
import json
import math
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import script_phrases  # noqa: E402
from reel_config import config_path  # noqa: E402

FPS = 30
GLIDE_F, SWAP_F = 20, 18
LINE_CHARS, LINE_WORDS = 22, 5
PAUSE_BREAK = 0.5
OPEN = {'scale': 1.4, 'frames': 26}


def probe(path):
    p = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
                        'stream=width,height:format=duration', '-of', 'json', path],
                       capture_output=True, text=True, check=True)
    d = json.loads(p.stdout)
    return int(d['streams'][0]['width']), int(d['streams'][0]['height']), float(d['format']['duration'])


def sentence_paragraphs(text):
    """Paragraph index of each script sentence, split exactly as script_phrases splits."""
    paras = [p.strip() for p in re.split(r'\n\s*\n', text.strip()) if p.strip()]
    out = []
    for pi, p in enumerate(paras):
        for s in re.split(r'(?<=[.?!])\s+', p):
            if s.strip():
                out.append(pi)
    return out


def is_strong(tok, first_in_sentence):
    bare = tok.strip('.,?!:;"“”')
    if not bare:
        return False
    if re.match(r'^\d', bare) or tok.startswith(('"', '“')):
        return True
    return (not first_in_sentence) and bare[0].isupper() and bare not in ('I', "I'll", "I'm", "I've")


def main():
    args = sys.argv[1:]
    if not args:
        sys.exit('usage: gen_reel_config.py <name> [--face X,Y] [--paid] [--regen] [--no-register]')
    name = args[0]
    regen = '--regen' in args
    face = None
    if '--face' in args:
        fx, fy = args[args.index('--face') + 1].split(',')
        face = (int(float(fx)), int(float(fy)))
    out_path = config_path(name)
    if os.path.exists(out_path) and not regen:
        print('config exists, left untouched (use --regen to discard edits): %s' % out_path)
        register(name, '--no-register' in args)
        return

    script_txt = os.path.join(ROOT, 'script', '%s.txt' % name)
    cut_wx = os.path.join(ROOT, 'script', 'word-timings', '%s-cut-wx.json' % name)
    cut_mp4 = os.path.join(ROOT, 'public', 'host', '%s-cut.mp4' % name)
    text = open(script_txt).read()
    words = json.load(open(cut_wx))
    sw, sh, dur = probe(cut_mp4)
    if sh <= sw:
        sys.exit('gen_reel_config: %s is not vertical' % cut_mp4)
    if face is None:
        face = (sw // 2, int(sh * 0.48))
    para_of_sent = sentence_paragraphs(text)

    ph = script_phrases.phrases(words, text)
    # 1. flatten: script spelling on cut timing, sentence index, and forced break points
    rw, sent = [], 0
    for p in ph:
        for w in p['words']:
            rw.append({'t': w['t'], 's': w['s'], 'e': max(w['e'], w['s'] + 0.01), 'sent': sent})
        if p['ends_sentence']:
            sent += 1
    sent_texts = [st.strip() for st in re.split(r'(?<=[.?!])\s+', ' '.join(text.split())) if st.strip()]
    for si in set(w['sent'] for w in rw):
        mine = [w for w in rw if w['sent'] == si and w['t']]
        if not mine or si >= len(sent_texts):
            continue
        st = sent_texts[si]
        # script_phrases writes every sentence end as '.', so restore the writer's own ? and !
        end = st.rstrip('"\u201d')[-1:]
        if end in '?!' and mine[-1]['t'].endswith('.'):
            mine[-1]['t'] = mine[-1]['t'][:-1] + end
        # ...and it drops quote marks: put them back on quoted words ('Comment "check"')
        for q in re.findall(r'["\u201c]([^"\u201d]+)["\u201d]', st):
            qw = q.split()
            for k in range(len(mine) - len(qw) + 1):
                if [re.sub(r'[^A-Za-z0-9]', '', x['t']).lower() for x in mine[k:k + len(qw)]] == \
                   [re.sub(r'[^A-Za-z0-9]', '', x).lower() for x in qw]:
                    mine[k]['t'] = '"' + mine[k]['t']
                    last = mine[k + len(qw) - 1]
                    m = re.match(r'^(.*?)([.,?!]*)$', last['t'])
                    last['t'] = m.group(1) + '"' + m.group(2)
                    break

    # 2. segments between forced breaks: sentence end, a comma after 2+ words, a pause > 0.5s
    segs, cur, prev_e = [], [], None
    for i, w in enumerate(rw):
        if not w['t']:
            cur.append(i)
            continue
        if cur and prev_e is not None and (w['s'] - prev_e > PAUSE_BREAK or rw[cur[-1]]['sent'] != w['sent']):
            if any(rw[j]['t'] for j in cur):
                segs.append(cur)
                cur = []
        cur.append(i)
        prev_e = w['e']
        spoken = [j for j in cur if rw[j]['t']]
        if w['t'].rstrip('"\u201d').endswith(('.', '?', '!')) or (w['t'].endswith(',') and len(spoken) >= 2):
            segs.append(cur)
            cur = []
    if cur:
        segs.append(cur)

    # 3. balanced lines inside each segment: fewest lines that fit, then even lengths
    #    (no one-word orphans like "solve." hanging on their own line)
    def split_even(idx):
        toks = [j for j in idx if rw[j]['t']]
        chars = lambda js: sum(len(rw[j]['t']) for j in js) + max(len(js) - 1, 0)  # noqa: E731
        k = 1
        while True:
            target = chars(toks) / float(k)
            lines, curl = [], []
            for j in toks:
                if curl and (chars(curl + [j]) > LINE_CHARS + 4 or len(curl) >= LINE_WORDS + 1 or
                             (chars(curl) >= target and len(lines) < k - 1)):
                    lines.append(curl)
                    curl = []
                curl.append(j)
            lines.append(curl)
            if len(lines) <= k and all(chars(l) <= LINE_CHARS + 4 and len(l) <= LINE_WORDS + 1 for l in lines):
                return lines
            k += 1

    line = 0
    for seg in segs:
        lines = split_even(seg)
        owner = {}
        for li, l in enumerate(lines):
            for j in l:
                owner[j] = li
        last_li = 0
        for j in seg:
            if j in owner:
                last_li = owner[j]
            rw[j]['line'] = line + last_li      # absorbed tokens ride the line before them
        line += len(lines)

    # 4. one emphasis per line: a numeral, else a quoted word, else a proper noun
    def rank(w, first):
        bare = w['t'].strip('.,?!:;"\u201c\u201d')
        if not bare:
            return 0
        if re.match(r'^\d', bare):
            return 3
        if w['t'].startswith(('"', '\u201c')):
            return 2
        return 1 if is_strong(w['t'], first) else 0
    first_seen, best = set(), {}
    for w in rw:
        if not w['t']:
            continue
        first = w['sent'] not in first_seen
        first_seen.add(w['sent'])
        r = rank(w, first)
        if r and (w['line'] not in best or r > best[w['line']][0]):
            best[w['line']] = (r, id(w))
    for w in rw:
        if w['t'] and w['line'] in best and best[w['line']][1] == id(w):
            w['big'] = True

    frames = int(math.ceil(dur * FPS))
    para_of = lambda w: para_of_sent[min(w['sent'], len(para_of_sent) - 1)]  # noqa: E731
    npara = max(para_of_sent) + 1

    def gap_frame(i_first):
        """A move starts the moment the boundary word ENDS (the first frame after the previous
        spoken word), never on the next sentence's start. A method learned from the AI Video Editor course (see CREDITS)."""
        w = rw[i_first]
        prev = [x for x in rw[:i_first] if x['t']]
        lo = prev[-1]['e'] + 0.02 if prev else 0.0
        t = lo
        f = int(math.ceil(t * FPS))
        if f / FPS < lo:
            f = int(math.ceil(lo * FPS))
        if f / FPS > w['s']:
            f = int(math.floor(w['s'] * FPS))
        return f

    def snap_to_gap(f):
        """Latest frame <= f that is not inside a spoken word."""
        while f > 0 and any(x['s'] < f / FPS - 1e-6 and x['e'] > f / FPS + 1e-6 for x in rw if x['t']):
            f -= 1
        return f

    def first_word_idx(pred):
        for i, w in enumerate(rw):
            if w['t'] and pred(w):
                return i
        return None

    # scenes: beat 1 full, then alternate by beat, and the last beat must be a window
    starts = []
    for pi in range(npara):
        i = first_word_idx(lambda w, pi=pi: para_of(w) == pi)
        if i is not None:
            starts.append((pi, i))
    modes = ['full'] + [('window' if k % 2 == 1 else 'full') for k in range(1, len(starts))]
    if len(modes) > 1 and modes[-1] == 'full':
        modes[-1] = 'window'
        if modes[-2] == 'window':
            modes.pop(-1)
            starts.pop(-1)
    scenes = []
    # tone runs (Shortify): middle window scenes read as a light "paper" chapter; the hook and
    # the ending stay dark
    for k, (pi, i) in enumerate(starts):
        if k == 0:
            scenes.append({'from': 0, 'mode': 'full', 'note': 'beat 1: ' + ' '.join(x['t'] for x in rw[i:i + 6] if x['t'])})
            continue
        if modes[k] == scenes[-1]['mode']:
            continue
        scenes.append({'from': gap_frame(i), 'mode': modes[k], 'note': 'beat %d: %s' % (pi + 1, ' '.join(x['t'] for x in rw[i:i + 6] if x['t']))})

    def scene_at(f):
        sc = [s for s in scenes if s['from'] <= f]
        return sc[-1] if sc else scenes[0]

    def next_scene_from(f):
        nx = [s['from'] for s in scenes if s['from'] > f]
        return nx[0] if nx else frames

    swaps = []
    # STAT: the sentence with the most numerals
    by_sent = {}
    for w in rw:
        if w['t'] and re.match(r'^\d', w['t'].strip('"')):
            by_sent.setdefault(w['sent'], []).append(w)
    if by_sent:
        s_idx = max(by_sent, key=lambda k: (len(by_sent[k]), -k))
        i0 = first_word_idx(lambda w: w['sent'] == s_idx)
        last = [w for w in rw if w['sent'] == s_idx and w['t']][-1]
        f_in = gap_frame(i0)
        sc = scene_at(f_in)
        # slide back right after the sentence, or earlier if the next scene change needs room
        target = min(int(math.ceil((last['e'] + 0.02) * FPS)), next_scene_from(f_in) - SWAP_F - 2)
        f_out = snap_to_gap(target)
        if sc['mode'] == 'window' and f_in >= sc['from'] + GLIDE_F and f_out + SWAP_F <= next_scene_from(f_in) and f_out - f_in >= 60:
            nums = [w['t'].strip('.,?!"') for w in by_sent[s_idx]]
            value = ('%s of %s' % (nums[0], nums[1])) if len(nums) >= 2 else nums[0]
            swaps.append({'in': f_in, 'out': f_out, 'kicker': 'TODO kicker',
                          'content': {'kind': 'stat', 'value': value, 'label': 'TODO label',
                                      'at': max(f_in + SWAP_F, int(round(by_sent[s_idx][0]['s'] * FPS)))},
                          'note': 'stat on: ' + ' '.join(w['t'] for w in rw if w['sent'] == s_idx and w['t'])})
    # CTA: the last beat, held to the end
    li = first_word_idx(lambda w: para_of(w) == npara - 1)
    if li is not None:
        f_in = gap_frame(li)
        sc = scene_at(f_in)
        if f_in == sc['from']:
            f_in = sc['from'] + GLIDE_F + 6
            # never inside a word: move forward to the first frame that is between words
            while f_in < frames and any(x['s'] < f_in / FPS - 1e-6 and x['e'] > f_in / FPS + 1e-6 for x in rw if x['t']):
                f_in += 1
        if sc['mode'] == 'window' and f_in >= sc['from'] + GLIDE_F:
            swaps.append({'in': f_in, 'out': frames, 'kicker': 'TODO kicker',
                          'content': {'kind': 'cta', 'title': 'TODO title',
                                      'button': 'Click Learn More' if '--paid' in args else 'TODO button', 'sub': 'TODO sub'},
                          'note': 'cta on: ' + ' '.join(w['t'] for w in rw if para_of(w) == npara - 1 and w['t'])})

    wins = [sc for sc in scenes if sc['mode'] == 'window']
    for sc in wins[:-1]:
        sc['tone'] = 'light'
    for sc in scenes:
        if sc['mode'] == 'window' and 'tone' not in sc:
            sc['tone'] = 'dark'
    cfg = {
        'id': name, 'src': 'host/%s-cut.mp4' % name, 'source': {'w': sw, 'h': sh},
        'faceX': face[0], 'faceY': face[1], 'fps': FPS, 'frames': frames, 'open': OPEN,
        'words': rw, 'scenes': scenes, 'swaps': swaps,
        # frame-0 cover: pick a frame with eyes open from the preview stills, write 2-4 words
        'cover': {'frame': min(frames - 1, 45), 'title': 'TODO cover title'},
        'framing': {'tight': 1.2},
        'captionStyle': 'lines',
        'placement': 'paid' if '--paid' in args else 'organic',
        'post': ({'keyword': '', 'gets': '', 'link': ''} if '--paid' in args else
                 {'keyword': '', 'gets': '', 'link': ''}),
        'meta': {'raw': 'inputs/%s.mp4' % name, 'script': 'script/%s.txt' % name,
                 'cutWx': 'script/word-timings/%s-cut-wx.json' % name,
                 'generated': datetime.date.today().isoformat()},
    }
    write_config(cfg, out_path, rw)
    print('wrote %s: %d frames, %d words, %d lines, %d scenes, %d swaps' % (
        out_path, frames, len(rw), rw[-1]['line'] + 1 if rw else 0, len(scenes), len(swaps)))
    register(name, '--no-register' in args)


def write_config(cfg, path, rw):
    legal = []
    for i, w in enumerate(rw):
        if w['t'].rstrip('"”').endswith(('.', '?', '!')):
            nxt = next((x for x in rw[i + 1:] if x['t']), None)
            if nxt:
                legal.append('%d-%d after "%s"' % (int(math.ceil((w['e'] + 0.02) * FPS)), int(math.floor(nxt['s'] * FPS)), w['t']))
    j = lambda v: json.dumps(v, ensure_ascii=False)  # noqa: E731
    L = ["import type { ReelConfig } from '../ReelConfig';",
         '// GENERATED by scripts/gen_reel_config.py on %s from %s + %s' % (cfg['meta']['generated'], cfg['meta']['script'], cfg['meta']['cutWx']),
         '// Edit ONLY scenes / swaps / big flags / open.scale. The body must stay JSON (trailing // comments allowed, never // inside a string).',
         '// Frames are at 30 fps. Scene changes must sit in a gap after a sentence end. Gaps (frame ranges):',
         ]
    for k in range(0, len(legal), 3):
        L.append('//   ' + ' | '.join(legal[k:k + 3]))
    L.append('const cfg = {')
    for key in ('id', 'src', 'source', 'faceX', 'faceY', 'fps', 'frames', 'open'):
        L.append('  %s: %s,' % (j(key), j(cfg[key])))
    L.append('  "scenes": [')
    for i, s in enumerate(cfg['scenes']):
        note = s.pop('note', '')
        L.append('    %s%s  // %.2fs %s' % (j(s), ',' if i < len(cfg['scenes']) - 1 else '', s['from'] / FPS, note))
    L.append('  ],')
    L.append('  "cover": %s,  // frame-0 cover: a clean frame of the host + a 2-4 word title (null to skip)' % j(cfg['cover']))
    L.append('  "framing": %s,  // second framing: every other take is drawn this much tighter on full-screen shots, so joins read as a camera change (remove for one framing)' % j(cfg['framing']))
    L.append('  "captionStyle": %s,  // "lines" (short lines) or "punch" (1-2 words at a time, bigger)' % j(cfg['captionStyle']))
    L.append('  "placement": %s,  // "organic" (caption drafts) or "paid" (Click Learn More + ad copy draft)' % j(cfg['placement']))
    L.append('  "post": %s,  // link: where the ad or post sends people (optional, the ad destination is set in Ads Manager)' % j(cfg['post']))
    L.append('  "swaps": [')
    for i, s in enumerate(cfg['swaps']):
        note = s.pop('note', '')
        L.append('    %s%s  // %s' % (j(s), ',' if i < len(cfg['swaps']) - 1 else '', note))
    L.append('  ],')
    L.append('  "words": [')
    for i, w in enumerate(cfg['words']):
        L.append('    %s%s' % (j(w), ',' if i < len(cfg['words']) - 1 else ''))
    L.append('  ],')
    L.append('  "meta": %s' % j(cfg['meta']))
    L.append('} satisfies ReelConfig;')
    L.append('export default cfg;')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, 'w').write('\n'.join(L) + '\n')


def register(name, skip):
    if skip:
        return
    root = os.path.join(ROOT, 'src', 'methodology', 'Root.tsx')
    src = open(root).read()
    line = "    <Reel id=\"%s\" load={() => import('./reels/%s.config')} />" % (name, name)
    if 'id="%s"' % name in src:
        print('Root.tsx already registers %s' % name)
        return
    marker = '{/* REELS (one line each; scripts/gen_reel_config.py appends here) */}'
    if marker not in src:
        sys.exit('Root.tsx: registration marker missing, add the line by hand:\n' + line)
    src = src.replace(marker, marker + '\n' + line, 1)
    open(root, 'w').write(src)
    print('registered %s in Root.tsx (one line)' % name)


if __name__ == '__main__':
    main()

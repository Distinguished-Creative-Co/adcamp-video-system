#!/usr/bin/env python3
"""Put the writer's script on the spoken timing, split into phrases.

    python3 scripts/script_phrases.py <words.json> <script.txt>     (prints the phrase table)

The script is the display truth (its spelling and punctuation go on screen). The aligner's
word times are the timing truth. phrases() lines the two up word by word and breaks the
result at the writer's commas and sentence ends, folding phrases too short to read.
Library use: gen_reel_config.py and the beat-map scripts call phrases(words, text).
"""
import difflib
import json
import re
import sys

MIN_PHRASE_S = 1.0

# a comma-grouped number ("4,000") is one token; then a word; then a punctuation run
_TOKEN = re.compile(r"\d{1,3}(?:,\d{3})+(?!\d)|[A-Za-z0-9][A-Za-z0-9'\-]*|[,.?!]+")


def _clean(text):
    return re.sub(r'[^a-z0-9]', '', text.lower())


def _script_tokens(script_text):
    """[{'clean', 'mark', 'sent', 'raw'}] for every word of the script."""
    toks = []
    sentences = [s.strip() for s in re.split(r'(?<=[.?!])\s+', script_text.strip()) if s.strip()]
    for si, sentence in enumerate(sentences):
        if not sentence.endswith(('.', '?', '!')):
            sentence += '.'
        for m in _TOKEN.finditer(sentence):
            piece = m.group(0)
            if piece[0] in ',.?!':
                if toks:
                    toks[-1]['mark'] = '.' if any(c in '.?!' for c in piece) else ','
                continue
            toks.append({'clean': _clean(piece), 'mark': None, 'sent': si, 'raw': piece})
    return [t for t in toks if t['clean']]


def _normalise(words):
    out = []
    for w in words:
        text = w.get('word', w.get('t', ''))
        start = w.get('start', w.get('s'))
        end = w.get('end', w.get('e'))
        out.append({'t': str(text).strip(), 's': round(float(start), 2), 'e': round(float(end), 2)})
    return out


def _with_mark(tok):
    return tok['raw'] + (tok['mark'] or '')


def _fill_sentences(sent, disp):
    """Ad-libbed runs (no script match) join the sentence they most likely belong to."""
    n = len(sent)
    i = 0
    while i < n:
        if sent[i] is not None:
            i += 1
            continue
        j = i
        while j + 1 < n and sent[j + 1] is None:
            j += 1
        prev = sent[i - 1] if i > 0 else None
        nxt = sent[j + 1] if j + 1 < n else None
        if prev is None and nxt is None:
            pick = 0
        elif prev is None:
            pick = nxt
        elif nxt is None:
            pick = prev
        elif nxt > prev and disp[j].endswith(('.', '?', '!')):
            pick = prev          # a tag on the end of the previous sentence
        else:
            pick = nxt if nxt > prev else prev
        for k in range(i, j + 1):
            sent[k] = pick
        i = j + 1


def _merge(a, b):
    return {'words': a['words'] + b['words'], 's': a['s'], 'e': b['e'],
            'ends_sentence': a['ends_sentence'] or b['ends_sentence']}


def _fold(raw, min_phrase_s):
    out = []
    carry = None
    for idx, p in enumerate(raw):
        if carry is not None:
            p = _merge(carry, p)
            carry = None
        tiny = (p['e'] - p['s']) < min_phrase_s and len(p['words']) <= 3
        if tiny and not p['ends_sentence'] and idx + 1 < len(raw):
            carry = p
            continue
        if tiny and out and not out[-1]['ends_sentence']:
            out[-1] = _merge(out[-1], p)
            continue
        out.append(p)
    return out


def phrases(words, script_text, min_phrase_s=MIN_PHRASE_S):
    spoken = _normalise(words)
    toks = _script_tokens(script_text)
    a = [t['clean'] for t in toks]
    b = [_clean(w['t']) for w in spoken]
    n = len(spoken)
    sent = [None] * n
    mark = [None] * n
    disp = [w['t'] for w in spoken]

    sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
    for i0, j0, size in sm.get_matching_blocks():
        for k in range(size):
            sent[j0 + k] = toks[i0 + k]['sent']
            mark[j0 + k] = toks[i0 + k]['mark']

    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == 'equal':
            for k in range(i2 - i1):
                disp[j1 + k] = _with_mark(toks[i1 + k])
        elif op == 'replace':
            m, cnt = i2 - i1, j2 - j1
            used = set()
            for k in range(cnt):
                ti = i1 + (k * m) // cnt
                disp[j1 + k] = '' if ti in used else _with_mark(toks[ti])
                used.add(ti)
            if m > cnt > 0:
                extra = [toks[i1 + x]['raw'] for x in range((cnt - 1) * m // cnt + 1, m)]
                if extra:
                    last = disp[j2 - 1].rstrip('.,')
                    disp[j2 - 1] = ' '.join([last] + extra) + (toks[i2 - 1]['mark'] or '')
        # insert: an ad-lib keeps its spoken text; delete: unspoken script shows nothing

    _fill_sentences(sent, disp)
    for k in range(n):
        if mark[k] != '.' and mark[k] is None and disp[k].endswith((',', ';', ':')):
            mark[k] = ','

    raw_phrases, cur = [], []
    for k in range(n):
        cur.append({'t': disp[k], 's': spoken[k]['s'], 'e': spoken[k]['e']})
        ends = k == n - 1 or sent[k + 1] != sent[k]
        if ends or mark[k]:
            raw_phrases.append({'words': cur, 's': cur[0]['s'], 'e': cur[-1]['e'], 'ends_sentence': ends})
            cur = []
    return _fold(raw_phrases, min_phrase_s)


def main():
    if len(sys.argv) != 3:
        sys.exit('usage: script_phrases.py <words.json> <script.txt>')
    with open(sys.argv[1]) as f:
        words = json.load(f)
    if isinstance(words, dict):
        words = words.get('words', [])
    with open(sys.argv[2]) as f:
        text = f.read()
    for i, p in enumerate(phrases(words, text)):
        line = ' '.join(w['t'] for w in p['words'] if w['t'])
        print('%3d  %7.2f  %7.2f  %5.2f  %s  %s' % (i, p['s'], p['e'], p['e'] - p['s'],
                                                  '.' if p['ends_sentence'] else ' ', line))


if __name__ == '__main__':
    main()

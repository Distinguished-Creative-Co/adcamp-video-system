#!/usr/bin/env python3
"""Fill the sample reel's copy (tools/smoke_test.sh runs this after the first preview).

    python3 samples/fill_sample.py

The sample is a real reel: the cover title, the words behind the host, the thumbnail and the
call-to-action card are the ones its owner approved. Frames are found from the spoken words in
the generated config, so they follow this Mac's own word timings. Safe to run twice.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
import reel_config  # noqa: E402

NAME = 'sample'


def word_index(words, seq, start=0):
    """First index where the spoken words match seq (case and punctuation ignored)."""
    norm = lambda t: ''.join(c for c in t.lower() if c.isalnum() or c == "'")
    seq = [norm(x) for x in seq]
    for i in range(start, len(words) - len(seq) + 1):
        if [norm(w['t']) for w in words[i:i + len(seq)]] == seq:
            return i
    sys.exit('fill_sample: could not find "%s" in the sample words' % ' '.join(seq))


def back_text(cfg, text, seq):
    """Show `text` from the frame its first word is spoken to the end of that (full-screen) scene."""
    fps, words = cfg['fps'], cfg['words']
    f_in = round(words[word_index(words, seq)]['s'] * fps)
    starts = sorted(s['from'] for s in cfg['scenes'])
    scene = max(s for s in starts if s <= f_in)
    mode = next(s['mode'] for s in cfg['scenes'] if s['from'] == scene)
    if mode != 'full':
        sys.exit('fill_sample: "%s" lands in a %s scene, back text needs a full-screen scene' % (text, mode))
    nxt = [s for s in starts if s > f_in]
    f_out = (nxt[0] if nxt else cfg['frames']) - 1
    return {'text': text, 'in': f_in, 'out': f_out}


def sub(src, old, new):
    if old not in src:
        sys.exit('fill_sample: expected text not found in the config:\n  %s' % old[:100])
    return src.replace(old, new, 1)


def main():
    path = reel_config.config_path(NAME)
    cfg = reel_config.load(NAME)
    src = open(path).read()
    if 'TODO' not in src:
        print('fill_sample: %s is already filled' % os.path.relpath(path, ROOT))
    else:
        bt = [back_text(cfg, "GOOGLE'S AI", ["Google's", 'AI']),
              back_text(cfg, '10 OF 15', ['10', 'out', 'of', '15']),
              back_text(cfg, 'NEXT PATIENT', ['next', 'patient'])]
        src = sub(src, '"cover": {"frame": 45, "title": "TODO cover title"},',
                  '"cover": {"frame": 45, "title": "AI recommended him", "accent": "AI"},')
        block = ('  "grade": {"exposure": 0.9, "contrast": 1.15, "saturation": 0.88, "vignette": 0.55, "film": 1},  // the cinematic look\n'
                 '  "backText": [  // big words behind the host, full-screen shots only\n'
                 + ',\n'.join('    ' + json.dumps(b) for b in bt) + '\n  ],\n'
                 '  "thumbnail": {"frame": 45, "back": "Google\'s AI recommended him", "front": "Named 10 of 15 times. Not a single ad."},\n')
        src = sub(src, '  "captionStyle":', block + '  "captionStyle":')
        src = sub(src, '"kicker": "TODO kicker", "content": {"kind": "cta", "title": "TODO title", "button": "TODO button", "sub": "TODO sub"}',
                  '"kicker": "Chiropractors", "content": {"kind": "cta", "title": "Is AI recommending you?", "button": "Comment SITE", '
                  '"sub": "I\'ll show you what AI is saying about your practice."}')
        open(path, 'w').write(src)
        print('fill_sample: filled cover, grade, back text, thumbnail and the call-to-action card')

    # The pause after "a single ad." ends in a breath that sits too close to the next word to cut
    # (cuts need 0.15s of real silence). It plays as a natural beat: record it as reviewed.
    cut_wx = os.path.join(ROOT, 'script', 'word-timings', '%s-cut-wx.json' % NAME)
    wx = json.load(open(cut_wx))
    wx = wx['words'] if isinstance(wx, dict) else wx
    norm = lambda t: ''.join(c for c in t.lower() if c.isalnum())
    i = next((k for k in range(len(wx) - 1) if norm(wx[k]['word']) == 'ad' and norm(wx[k + 1]['word']) == 'that'), None)
    rev = os.path.join(ROOT, 'script', 'word-timings', '%s-seams-reviewed.json' % NAME)
    if i is not None and wx[i + 1]['start'] - wx[i]['end'] > 0.3:
        json.dump([{'a': round(wx[i]['end'] - 0.05, 2), 'b': round(wx[i + 1]['start'] + 0.05, 2),
                    'why': 'Sample clip: sentence-end beat after "a single ad." The breath before "That matters" '
                           'leaves no 0.15s silence to cut in, so the pause stays. Reviewed: reads as natural.'}],
                  open(rev, 'w'), indent=1)
        print('fill_sample: recorded the reviewed pause after "a single ad."')


if __name__ == '__main__':
    main()

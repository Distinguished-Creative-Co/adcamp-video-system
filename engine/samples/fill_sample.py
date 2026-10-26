#!/usr/bin/env python3
"""Fill the sample reel's copy (tools/smoke_test.sh runs this after the first preview).

    python3 samples/fill_sample.py [name]          name defaults to "sample"

The sample is a real reel, the copy its owner approved: the cover title, the hook title, the post keyword and the
One Fee card all come from what he said. In a full-frame look (the starters) the One Fee card is a slide over the
picture; in the cards-and-panels build it is a checklist panel, with the thumbnail and the call-to-action card. Frames are found from the spoken words
in the generated config, so they follow this Mac's own word timings. A few joins between takes keep a
breath or the end of a word: they are recorded as reviewed, the way an editor would sign them off.
Safe to run twice.
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
import reel_config  # noqa: E402
import styles_lib  # noqa: E402

NAME = sys.argv[1] if len(sys.argv) > 1 else 'sample'
norm = lambda t: ''.join(c for c in t.lower() if c.isalnum() or c == "'")


def word_index(words, seq, start=0):
    """First index where the spoken words match seq (case and punctuation ignored)."""
    seq = [norm(x) for x in seq]
    for i in range(start, len(words) - len(seq) + 1):
        if [norm(w['t']) for w in words[i:i + len(seq)]] == seq:
            return i
    sys.exit('fill_sample: could not find "%s" in the sample words' % ' '.join(seq))


def back_text(cfg, text, seq, hold=2.4):
    """Show `text` from the frame its first word is spoken, for `hold` seconds inside that full-screen scene."""
    fps, words = cfg['fps'], [w for w in cfg['words'] if w['t']]
    f_in = round(words[word_index(words, seq)]['s'] * fps)
    starts = sorted(s['from'] for s in cfg['scenes'])
    scene = max(s for s in starts if s <= f_in)
    if next(s['mode'] for s in cfg['scenes'] if s['from'] == scene) != 'full':
        sys.exit('fill_sample: "%s" lands in a window scene, back text needs a full-screen scene' % text)
    nxt = [s for s in starts if s > f_in]
    f_out = min((nxt[0] if nxt else cfg['frames']) - 1, f_in + round(hold * fps))
    return {'text': text, 'in': f_in, 'out': f_out}


def sub(src, old, new):
    if old not in src:
        sys.exit('fill_sample: expected text not found in the config:\n  %s' % old[:100])
    return src.replace(old, new, 1)


def one_fee_card(cfg, src):
    """The checklist card on "One fee ... you own the domain ... all the files": one window scene from "Here's what I do
    instead" to "Four conversations", each item ticking in on its word."""
    fps, words = cfg['fps'], [w for w in cfg['words'] if w['t']]
    at = lambda seq: round(words[word_index(words, seq)]['s'] * fps)
    f_start, f_end = at(["here's", 'what', 'i', 'do', 'instead']), at(['four', 'conversations'])
    scenes = sorted(cfg['scenes'], key=lambda x: x['from'])
    win = max(x['from'] for x in scenes if x['from'] <= f_start)
    end = max(x['from'] for x in scenes if x['from'] <= f_end)   # the full-screen scene at "Four conversations"
    if next(x['mode'] for x in scenes if x['from'] == win) != 'window':
        sys.exit('fill_sample: "Here\'s what I do instead" is not in a window scene')
    for f in [x['from'] for x in scenes if win < x['from'] < end]:   # one window through to "Four conversations"
        src, n = re.subn(r'\n    \{"from": %d, [^\n]*' % f, '', src, count=1)
        if not n:
            sys.exit('fill_sample: scene at frame %d not found' % f)
    items = [{'t': 'One fee', 'at': at(['fee', 'and', 'all'])}, {'t': 'All edits, first year', 'at': at(['all', 'the', 'edits'])},
             {'t': 'You own the domain', 'at': at(['the', 'domain'])}, {'t': 'The website and files', 'at': at(['all', 'the', 'files'])}]
    quiet = lambda f: not any(w['s'] - 0.03 <= f / fps <= w['e'] + 0.03 for w in words)   # card edges sit between words
    f_in = next(f for f in range(win + 20, items[0]['at']) if quiet(f))
    f_out = next(f for f in range(end - 18, items[-1]['at'], -1) if quiet(f))
    card = {'in': f_in, 'out': f_out, 'kicker': 'What I do instead', 'content': {'kind': 'checklist', 'items': items}}
    return sub(src, '  "swaps": [\n', '  "swaps": [\n    %s,\n' % json.dumps(card))


def one_fee_slide(cfg, src):
    """In a full-frame look: the One Fee card as a slide over the picture, each line ticking in on its word."""
    fps, words = cfg['fps'], [w for w in cfg['words'] if w['t']]
    at = lambda seq: round(words[word_index(words, seq)]['s'] * fps)
    items = [{'t': 'All edits, first year', 'at': at(['all', 'the', 'edits'])}, {'t': 'You own the domain', 'at': at(['the', 'domain'])},
             {'t': 'The website and files', 'at': at(['all', 'the', 'files'])}]
    f_in = at(['fee', 'and', 'all']) - 6
    f_out = min(f_in + 290, round(max(w['e'] for w in words if norm(w['t']) == 'files') * fps) + 24)
    card = {'kind': 'card', 'in': f_in, 'out': f_out, 'layout': 'content', 'label': 'What I do instead',
            'headline': '==One fee.==', 'items': items}
    return styles_lib.add_effects(src, [card], 'the One Fee card')


def main():
    path = reel_config.config_path(NAME)
    cfg = reel_config.load(NAME)
    src = open(path).read()
    if 'TODO' not in src and 'SAME CONVERSATION' in src:
        print('fill_sample: %s is already filled' % os.path.relpath(path, ROOT))
    else:
        panels = any(sc['mode'] == 'window' for sc in cfg['scenes'])   # the cards-and-panels build, or a full-frame look
        bt = [back_text(cfg, 'SAME CONVERSATION', ['same', 'conversation'])]
        src = sub(src, '"cover": {"frame": 45, "title": "TODO cover title"},', '"cover": {"frame": 45, "title": "Same four things", "accent": "four"},')
        # the post line ships blank in the package and with TODOs in a fresh generator run: replace whichever is there
        post = '"post": {"keyword": "SITE", "gets": "a new way to run your practice\'s website", "link": ""}'
        src, n = re.subn(r'"post": \{[^\n]*?\}(?=,)', post, src, count=1)
        if not n:
            sys.exit('fill_sample: no "post" line in the config')
        src = styles_lib.set_key(src, 'backText', bt, 'the hook title, from the first spoken words')   # replaces an automatic one
        if panels:
            src = styles_lib.set_key(src, 'thumbnail', {"frame": 45, "back": "Same four things", "front": "What four chiropractors told me"}, 'custom cover')
            src = one_fee_card(cfg, src)
            src = sub(src, '"kicker": "TODO kicker", "content": {"kind": "cta", "title": "TODO title", "button": "TODO button", "sub": "TODO sub"}',
                      '"kicker": "Chiropractors", "content": {"kind": "cta", "title": "DM me the word SITE", "button": "DM SITE", '
                      '"sub": "A new way to run your practice\'s website."}')
        else:
            src = one_fee_slide(cfg, src)
        open(path, 'w').write(src)
        print('fill_sample: filled the cover, the hook title, the post keyword and the One Fee card%s'
              % (', the thumbnail and the call-to-action card' if panels else ''))

    # A few joins keep a breath or the tail of a word (no 0.15 s of true silence to cut in). They read as natural
    # beats: record them as reviewed. Found from the words, so they follow this Mac's timings.
    wx = json.load(open(os.path.join(ROOT, 'script', 'word-timings', '%s-cut-wx.json' % NAME)))
    wx = wx['words'] if isinstance(wx, dict) else wx
    rev = []
    for before, after, why in (('back', 'four', 'the beat before "Four, all of them"'), ('it', 'four', 'the beat before "Four conversations"'),
                               ('scratch', 'and', 'the "ch" of "scratch." running into the pause'),
                               ('with', 'and', 'the end of "with." and a breath before "And no one\'s"')):
        for k in range(len(wx) - 1):
            if norm(wx[k]['word']) == before and norm(wx[k + 1]['word']) in (after, '4'):
                rev.append({'a': round(wx[k]['end'] - 0.05, 2), 'b': round(wx[k + 1]['start'] + 0.05, 2),
                            'why': 'Sample clip: %s, no 0.15 s silence to cut in. Reviewed: reads as a natural pause.' % why})
                break
    json.dump(rev, open(os.path.join(ROOT, 'script', 'word-timings', '%s-seams-reviewed.json' % NAME), 'w'), indent=1)
    print('fill_sample: recorded %d reviewed pauses' % len(rev))


if __name__ == '__main__':
    main()

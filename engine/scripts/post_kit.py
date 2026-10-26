#!/usr/bin/env python3
"""The post kit for one reel: a caption or ad copy DRAFT built from the reel's own script.

    python3 scripts/post_kit.py <name>            write script/<name>-post.md (organic) or -ad.md (paid)
    python3 scripts/post_kit.py <name> --check    always passes (kept so scene_map.py can call it)

ORGANIC: one caption, the script as short one-line blocks (hook and closer on their own lines),
no hashtags, plus a link line if the config has one.
PAID (Meta): primary text from the script, a headline slot, a short description slot, the
"Learn More" button, and the destination (set in Ads Manager, never invented).

CC BY MUSIC: when the reel's music bed came from scripts/find_music.py under CC BY, its credit line (in
sounds/music/credits.json) is added at the end. The license asks for it wherever the video is posted.

Everything here is a DRAFT to trim, and nothing is posted or spent from here.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import reel_config  # noqa: E402


def script_blocks(name):
    meta = reel_config.load(name).get('meta', {})
    text = open(os.path.join(ROOT, meta.get('script') or os.path.join('script', '%s.txt' % name))).read()
    paras = [' '.join(p.split()) for p in re.split(r'\n\s*\n', text.strip()) if p.strip()]
    blocks = []
    for p in paras:
        blocks += [s.strip() for s in re.split(r'(?<=[.?!])["”]?\s+', p) if s.strip()]
    return blocks


def music_credit(name, cfg):
    """The credit line a CC BY music bed needs, or '' (CC0, public domain, their own licensed file, no music)."""
    if cfg.get('music') is False:
        return ''
    bed = cfg.get('music')
    if not bed:   # rotated: the bed this reel last mixed with
        lp = os.path.join(ROOT, 'qa', 'music-log.json')
        bed = next((e['bed'] for e in reversed(json.load(open(lp))) if e['reel'] == name), None) if os.path.exists(lp) else None
    cp = os.path.join(ROOT, 'sounds', 'music', 'credits.json')
    if not bed or not os.path.exists(cp):
        return ''
    return (json.load(open(cp)).get(bed) or {}).get('line', '')


KEEP = 'Keep the Music line at the end in every place you post this video (its license asks for the credit).'


def main():
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    name = a[0]
    if '--check' in a:
        print('post kit: PASS (drafts are optional)')
        return
    cfg = reel_config.load(name)
    post = cfg.get('post') or {}
    link = (post.get('link') or '').strip()
    if 'TODO' in link:
        link = ''
    blocks = script_blocks(name)
    credit = music_credit(name, cfg)
    if credit:
        blocks.append(credit)
    if cfg.get('placement') == 'paid':
        L = ['# Ad copy draft (paid): %s' % name, '',
             'DRAFT. Trim it, then paste it into Ads Manager.' + (' ' + KEEP if credit else ''), '',
             '## Primary text', '', '```', '\n\n'.join(blocks), '```', '',
             '## Headline', '', 'Write 3-5 short options (under 40 characters) and test them. The strongest is usually the problem your customer has, in their words.', '',
             '## Description', '', '```', 'One plain line: who it is for and what they get.', '```', '',
             '## Call to action button', '', 'Learn More (the video says "Click Learn More").', '',
             '## Destination', '', link or 'Set in Ads Manager: the page people land on after they click.', '',
             '## Before it runs', '',
             '- The destination is live and matches what the ad promises.',
             '- Check the placement previews in Ads Manager (Feed, Stories, Reels) for crop and safe zones.']
        out = os.path.join(ROOT, 'script', '%s-ad.md' % name)
    else:
        L = ['# Caption draft (organic): %s' % name, '',
             'DRAFT. It is the full script: trim it to the strongest lines, end on a question or a clear next step.' + (' ' + KEEP if credit else ''), '',
             '```', '\n\n'.join(blocks[:-1] if credit else blocks) + ('\n\n' + link if link else '') + ('\n\n' + credit if credit else ''), '```']
        out = os.path.join(ROOT, 'script', '%s-post.md' % name)
    open(out, 'w').write('\n'.join(L) + '\n')
    print('post kit: PASS, wrote %s%s' % (os.path.relpath(out, ROOT), ' (with the music credit line)' if credit else ''))


if __name__ == '__main__':
    main()

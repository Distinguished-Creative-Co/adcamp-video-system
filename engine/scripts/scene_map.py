#!/usr/bin/env python3
"""Step 5 — THE REVIEW ARTIFACT: script/<name>-scene-map.md. Nothing renders until a human
has read it and approved (scripts/approve_reel.py).

    python3 scripts/scene_map.py <name>

Every row says what is SAID, what is SHOWN, and what MOVES. It also accounts for all the
audio the take step removed, flags repeated phrases left in the cut, runs both validators,
refuses to call a config ready while any TODO copy remains, and writes a face-check still.
Python 3.9 compatible.
"""
import hashlib
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import reel_config  # noqa: E402
import verify_clean_read  # noqa: E402  (copied, unchanged: find_repeats / norm)

FPS = 30
GLIDE_F, SWAP_F = 20, 18


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()[:12]


def face_check(cfg, name):
    """A still of the cut with the face anchor and the card's crop drawn on it."""
    out = os.path.join(ROOT, 'qa', name, 'face-check.png')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    src = os.path.join(ROOT, 'public', cfg['src'])
    fx, fy = cfg['faceX'], cfg['faceY']
    # card crop at rest: cover scale for 600x760 over the source, face at 48% of the card height
    sw, sh = cfg['source']['w'], cfg['source']['h']
    s = max(600.0 / sw, 760.0 / sh)
    band_h = 760 / s
    band_w = 600 / s
    y0 = min(max(fy - 0.48 * band_h, 0), sh - band_h)
    x0 = min(max(fx - 0.5 * band_w, 0), sw - band_w)
    vf = ('drawbox=x=%d:y=%d:w=%d:h=%d:color=yellow@0.9:t=6,'
          'drawbox=x=%d:y=0:w=4:h=ih:color=red@0.8:t=fill,drawbox=x=0:y=%d:w=iw:h=4:color=red@0.8:t=fill,'
          'scale=540:960') % (x0, y0, band_w, band_h, fx - 2, fy - 2)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', '2', '-i', src, '-frames:v', '1', '-vf', vf, out], check=True)
    return os.path.relpath(out, ROOT)


def main():
    if len(sys.argv) != 2:
        sys.exit('usage: scene_map.py <name>')
    name = sys.argv[1]
    cfg = reel_config.load(name)
    words = cfg['words']
    frames = cfg['frames']
    takes_p = os.path.join(ROOT, 'script', 'word-timings', '%s-takes.json' % reel_config.stem(cfg))
    takes = json.load(open(takes_p)) if os.path.exists(takes_p) else None
    cut_wx = json.load(open(os.path.join(ROOT, cfg['meta']['cutWx'])))
    cfg_path = reel_config.config_path(name)
    cut_mp4 = os.path.join(ROOT, 'public', cfg['src'])

    ok_ts, ts_msg = reel_config.ts_validate(name)
    sp = subprocess.run([sys.executable, os.path.join(HERE, 'verify_seams.py'), name], capture_output=True, text=True)
    seams_ok = sp.returncode == 0
    seams_lines = [ln.strip() for ln in sp.stdout.splitlines() if ln.strip()]
    roles = json.load(open(os.path.join(ROOT, 'sounds.json')))
    roles = {k: v for k, v in roles.items() if not k.startswith('_')}
    role_names = {k: v for k, v in roles.items() if k != 'music_beds'}
    law = reel_config.timeline_errors(cfg)
    todo = [ln.strip() for ln in open(cfg_path) if 'TODO' in ln.split('//')[0]]
    toks = [(verify_clean_read.norm(w['word']), float(w['start']), w['word'].strip())
            for w in cut_wx if verify_clean_read.norm(w['word'])]
    repeats = verify_clean_read.find_repeats(toks)
    fc = face_check(cfg, name)

    lines = {}
    for w in words:
        if w['t']:
            lines.setdefault(w['line'], []).append(w)

    def said(f0, f1):
        return ' '.join(w['t'] for w in words if w['t'] and f0 / FPS <= w['s'] < f1 / FPS)

    def caption_rows(f0, f1):
        out = []
        for ln, ws in sorted(lines.items()):
            if f0 / FPS <= ws[0]['s'] < f1 / FPS:
                out.append(' '.join(('**%s**' % w['t']) if w.get('big') else w['t'] for w in ws))
        return ' / '.join(out)

    L = ['# Scene map: %s' % name, '',
         'Config `%s` (%s), cut `%s` (%s). %d frames = %.1fs at 30 fps, 1080x1920.'
         % (os.path.relpath(cfg_path, ROOT), sha(cfg_path), cfg['src'], sha(cut_mp4), frames, frames / FPS), '']
    pk = subprocess.run([sys.executable, os.path.join(HERE, 'post_kit.py'), name], capture_output=True, text=True)
    post_ok = pk.returncode == 0
    post_line = (pk.stdout.strip().splitlines() or ['post kit: no output'])[0]
    inserts = cfg.get('inserts') or []
    brand = json.load(open(os.path.join(ROOT, 'src', 'brand.json')))
    ins_errs = []
    if inserts:
        for k in ('handle', 'name'):
            if not (brand.get(k) or '').strip() and not all((b.get(k) or '').strip() for b in inserts if b.get('kind') == 'follow'):
                ins_errs.append('the follow card needs "%s" in src/brand.json (or on each insert)' % k)
        av = (brand.get('avatar') or '').strip()
        if av and not os.path.exists(os.path.join(ROOT, 'public', av)) and any(b.get('kind') == 'follow' for b in inserts):
            ins_errs.append('avatar %s is missing under public/ (initials would show instead)' % av)
        for b in inserts:
            if b.get('kind') != 'clip':
                continue
            cp = os.path.join(ROOT, 'public', b.get('src') or '')
            if not os.path.exists(cp):
                ins_errs.append('clip %s is missing under public/ (prepare it with scripts/prep_insert.py)' % b.get('src'))
                continue
            pr = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', cp], capture_output=True, text=True).stdout.strip()
            need = float(b.get('start') or 0) + (b['out'] - b['in']) / FPS
            if pr and float(pr) + 0.05 < need:
                ins_errs.append('clip %s runs %.1fs, the insert needs %.1fs (start %.1fs + %d frames)' % (b['src'], float(pr), need, float(b.get('start') or 0), b['out'] - b['in']))
    ready = ok_ts and not law and not todo and seams_ok and post_ok and not ins_errs
    L += ['**Status: %s**' % ('READY FOR REVIEW' if ready else 'NOT READY (fix the items under Checks)'), '']

    if takes:
        L += ['## 1. Takes (what the cut kept from the raw recording)', '',
              'Room tone %.1f dB, silence thresholds %s / %s dB. Raw %.1fs, cut %.1fs. HARD RULE gate: %s.'
              % (takes['floor_db'], takes['loose_db'], takes['strict_db'], takes['duration'],
                 takes['cut_duration'], takes['gate']), '',
              '| raw time | kept / dropped | why | said (transcript) |', '|---|---|---|---|']
        lab = takes['labels']
        i = 0
        while i < len(lab):
            j = i
            while j + 1 < len(lab) and (lab[j + 1]['label'], lab[j + 1]['why']) == (lab[i]['label'], lab[i]['why']):
                j += 1
            L.append('| %.2f-%.2f | %s | %s | %s |' % (lab[i]['start'], lab[j]['end'], lab[i]['label'],
                                                      lab[i]['why'], ' '.join(x['word'] for x in lab[i:j + 1])))
            i = j + 1
        L += ['', 'Full detail and override commands: `script/%s-takes.md`.' % name, '']

    L += ['## 2. Face anchor', '',
          'faceX %d, faceY %d (source px). Red cross = anchor, yellow box = what the glass card shows at rest: `%s`. '
          'Check the whole head sits inside the yellow box.' % (cfg['faceX'], cfg['faceY'], fc), '']

    cv = cfg.get('cover')
    L += ['## 2b. Cover (frame 0)', '',
          ('Frame %d of the host with the title "%s"%s. Instagram shows frame 0 as the default cover. '
           'Check the preview still `f0000.png`: eyes open, title clear of the face.'
           % (cv['frame'], cv['title'], (', accent word "%s"' % cv['accent']) if cv.get('accent') else ''))
          if cv else 'None (frame 0 is the first frame of the open).', '']
    L += ['## 3. Scenes (cut timeline)', '',
          '| # | time | frame | mode | motion | said | captions as displayed (**emphasis**) |', '|---|---|---|---|---|---|---|']
    for i, sc in enumerate(cfg['scenes']):
        f0 = sc['from']
        f1 = cfg['scenes'][i + 1]['from'] if i + 1 < len(cfg['scenes']) else frames
        if i == 0:
            motion = 'OPEN punched in %.2fx, zooms out to 1.0 over %.2fs on the first words, then a slow push in' % (
                cfg['open']['scale'], cfg['open']['frames'] / FPS)
        elif sc['mode'] == 'window':
            motion = 'GLIDE DOWN %.2fs: the full frame shrinks into the glass card, captions move to the stage above' % (GLIDE_F / FPS)
        else:
            motion = 'GLIDE UP %.2fs: the card grows back to full frame, captions to the lower-middle band' % (GLIDE_F / FPS)
        where = 'full frame, captions lower-middle' if sc['mode'] == 'full' else 'card + %s stage, captions on stage' % sc.get('tone', 'dark')
        L.append('| %d | %.2f-%.2fs | %d | %s (%s) | %s | %s | %s |' % (
            i + 1, f0 / FPS, f1 / FPS, f0, sc['mode'], where, motion, said(f0, f1), caption_rows(f0, f1)))
    L += ['']

    L += ['## 4. Panel swaps', '']
    if not cfg['swaps']:
        L += ['None.', '']
    for i, s in enumerate(cfg['swaps']):
        k = s['content']
        out_desc = 'held to the end' if s['out'] >= frames else 'slides back %.2f-%.2fs, card returns from the left' % (
            s['out'] / FPS, (s['out'] + SWAP_F) / FPS)
        if k['kind'] == 'stat':
            body = 'STAT **%s**, label "%s"' % (k['value'], k['label'])
        elif k['kind'] == 'cta':
            body = 'CTA title "%s", sub "%s", button "%s"' % (k['title'], k.get('sub', ''), k['button'])
        elif k['kind'] == 'checklist':
            body = 'CHECKLIST: ' + ' / '.join('"%s" ticks @%.2fs' % (x['t'], x['at'] / FPS) for x in k['items'])
        elif k['kind'] == 'funnel':
            body = 'FUNNEL: ' + ' > '.join('"%s"%s @%.2fs' % (x['t'], (' ' + x['value']) if x.get('value') else '', x['at'] / FPS) for x in k['stages'])
        elif k['kind'] == 'decision':
            body = 'DECISION "%s": %s, picks "%s" @%.2fs' % (k.get('question', ''), ' / '.join('"%s"' % x['t'] for x in k['options']),
                                                           k['options'][k['pick']]['t'], k['pickAt'] / FPS)
        elif k['kind'] == 'shot':
            body = 'PROOF SHOT `%s` (%dx%d): shown whole, punches in on (%d,%d %dx%d) @%.2fs, source line "%s"' % (
                k['src'], k['w'], k['h'], k['focus']['x'], k['focus']['y'], k['focus']['w'], k['focus']['h'], k['at'] / FPS, k['source'])
        else:
            body = 'the spoken lines, large'
        L += ['**Swap %d**: %.2fs to %s. Kicker "%s". %s.' % (i + 1, s['in'] / FPS, out_desc, s.get('kicker', ''), body),
              '', 'Motion: the card slides off LEFT while the frosted panel slides in from the RIGHT (%.2fs). '
              'The host rides the panel as an inset (bottom left), so the avatar is always on screen. '
              'Captions continue on the panel.' % (SWAP_F / FPS), '',
              'Said during the swap: %s' % said(s['in'], s['out'] if s['out'] < frames else frames), '']

    bts = cfg.get('backText') or []
    gr = cfg.get('grade')
    L += ['## 4b. Look: grade, back text and inserts', '',
          'Grade on the host footage: %s.' % (', '.join('%s %s' % kv for kv in gr.items()) if gr else 'none'), '']
    if bts:
        L += ['Back text (huge words behind the host, cutouts matted by `scripts/matte_reel.py`):', '',
              '| frames | time | text | said there |', '|---|---|---|---|']
        for b in bts:
            L.append('| %d-%d | %.2f-%.2fs | **%s** | %s |' % (b['in'], b['out'], b['in'] / FPS, b['out'] / FPS, b['text'], said(b['in'], b['out'])))
        L.append('')
    fx = cfg.get('effects') or []
    if fx:
        L += ['Effects (motion graphics and transitions):', '', '| frames | time | effect | said there |', '|---|---|---|---|']
        for e in fx:
            a, b = (e['at'] - 6, e['at'] + 6) if e['kind'] == 'transition' else (e['in'], e['out'])
            what = e['kind'] + (' ' + e.get('style', '') if e['kind'] == 'transition' else '')
            detail = e.get('word') or e.get('label') or e.get('keys') or e.get('text') or e.get('value') or e.get('source') or ''
            L.append('| %d-%d | %.2f-%.2fs | %s%s | %s |' % (a, b, a / FPS, b / FPS, what, (': ' + detail) if detail else '', said(a, b)))
        L.append('')
    if inserts:
        L += ['Inserts (floating cards over the host, top band):', '', '| frames | time | card | said there |', '|---|---|---|---|']
        for b in inserts:
            if b.get('kind') == 'clip':
                card = 'cutaway clip %s%s' % (b.get('src'), (', label "%s"' % b['label']) if b.get('label') else '')
            else:
                who = '%s %s' % (b.get('name') or brand.get('name', ''), b.get('handle') or brand.get('handle', ''))
                card = 'follow card: %s' % who.strip()
            L.append('| %d-%d | %.2f-%.2fs | %s | %s |' % (b['in'], b['out'], b['in'] / FPS, b['out'] / FPS, card, said(b['in'], b['out'])))
        L.append('')
    if cfg.get('needs'):
        L += ['## 4c. What the edit needs from the person', '', 'Shown on top of the storyboard (`qa/%s/storyboard/index.html`). Placeholders stand in until they arrive.' % name, '']
        L += ['- %s: %s' % (n['beat'], n['what']) for n in cfg['needs']] + ['']
    L += ['## 5. Checks', '',
          '- Structure (validateReel): %s' % ('PASS' if ok_ts else 'FAIL: ' + ts_msg),
          '- Inserts (follow card identity in src/brand.json, cutaway clips present and long enough): %s' % ('none' if not inserts else ('PASS' if not ins_errs else 'FAIL: ' + '; '.join(ins_errs))),
          '- Timeline law (scene changes and swap edges in real gaps, scene changes after sentence ends): %s'
          % ('PASS' if not law else 'FAIL'),
          ] + ['  - ' + e for e in law] + [
          '- Seam check (stray sound or dead air at cut joins, head, tail): %s' % ('PASS' if seams_ok else 'FAIL'),
          ] + ['  - ' + x for x in seams_lines if x.startswith(('FAIL', 'warn', 'seams'))] + [
          '- Numbers on screen that were never spoken: %s' % ('none' if not any('never spoken' in e for e in law) else 'SEE ABOVE'),
          '- Sound effects: %s. Cues go on every move and panel element; null roles are skipped.' % (
              ', '.join('%s %s' % (k, 'set' if v else 'none') for k, v in role_names.items())),
          '- Audio delivery: narration mixed from the cut, mastered to -14 LUFS, true peak <= -1 dBTP (checked after render). '
          'Music: %s.' % (cfg.get('music') or ('least recently used of %d beds' % len(roles.get('music_beds', [])) if roles.get('music_beds') else 'none supplied')),
          '- Captions style: %s. Tone runs: %s.' % (cfg.get('captionStyle', 'lines'), ' / '.join(
              '%s %s' % (sc['mode'], sc.get('tone', 'dark')) for sc in cfg['scenes'])),
          '- Caption / ad copy draft (`script/%s-post.md` or `-ad.md`): %s' % (name, 'written' if post_ok else 'FAIL'),
          '  - ' + post_line,
          '- Copy TODOs left in the config: %s' % ('none' if not todo else len(todo)),
          ] + ['  - `%s`' % t[:120] for t in todo] + [
          '- Repeated phrases in the cut audio (possible uncut flub): %s' % ('none' if not repeats else len(repeats)),
          ] + ['  - "%s" at %.1fs and again at %.1fs' % (r['phrase'], r['t1'], r['t2']) for r in repeats] + [
          '- Safe zones: captions, card, panel text and CTA stay inside x < 960 and y < 1600 by engine construction '
          '(checked frame by frame in `node scripts/test_layout.mjs %s`).' % name, '']

    L += ['## 6. Approve, then render', '',
          'Rendering is blocked until a human approves this exact map, config and cut:', '',
          '```', 'python3 scripts/approve_reel.py %s --by "<your name>"' % name,
          'scripts/make_reel.sh <raw> %s --render' % name, '```', '',
          'Editing the config, the cut, or the engine after approval invalidates it.']
    out = os.path.join(ROOT, 'script', '%s-scene-map.md' % name)
    open(out, 'w').write('\n'.join(L) + '\n')
    print('wrote %s  [%s]' % (os.path.relpath(out, ROOT), 'READY' if ready else 'NOT READY'))
    sys.exit(0 if ready else 1)


if __name__ == '__main__':
    main()

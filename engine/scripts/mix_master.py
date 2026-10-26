#!/usr/bin/env python3
"""Mix and master the delivered audio, then mux it onto the muted picture render.

    python3 scripts/mix_master.py <name> out/<name>-picture.mp4 out/<name>.mp4

One audio path (a method learned from the AI Video Editor course, see CREDITS): narration comes straight
from the approved cut, never through the browser, so it cannot drift or double. Sound
effects come only from sounds.json roles the creator supplied; null roles are recorded as
unassigned and skipped. Cues are derived from the config, one per real event:

  transition_whoosh  every scene change and every panel swap in/out (one per movement)
  element_land       every panel element as it settles (stat, CTA, checklist item, funnel stage, option)
  state_change       a decision's pick

Effects start about 8 dB under the dialogue mean (cluster-compensated). The mix is mastered
with two-pass loudnorm to -14 LUFS, true peak -1.5 dBTP, then verified: the file is refused
if its true peak is above -1 dBTP. Writes qa/<name>/sound-cues.json and loudness.json.
"""
import json
import math
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import reel_config  # noqa: E402

FPS = 30
SWAP_F, ENTER_F, SETTLE_F = 18, 12, 30
ROLES = ('transition_whoosh', 'element_land', 'state_change', 'back_text_hit', 'insert_pop', 'cta_ding', 'cta_riser')   # plus music_beds, handled separately


def mean_db(path):
    t = subprocess.run(['ffmpeg', '-hide_banner', '-i', path, '-af', 'volumedetect', '-f', 'null', '-'],
                       capture_output=True, text=True).stderr
    m = re.search(r'mean_volume: ([\-\d.]+)', t)
    if not m:
        sys.exit('mix_master: could not measure %s' % path)
    return float(m.group(1))


def loud(path):
    t = subprocess.run(['ffmpeg', '-hide_banner', '-i', path, '-af',
                        'loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json', '-f', 'null', '-'],
                       capture_output=True, text=True).stderr
    return json.loads(re.search(r'\{\s*"input_i".*?\}', t, re.S).group())


DUCK = 'sidechaincompress=threshold=0.05:ratio=4:attack=25:release=400'


def lufs(path):
    t = subprocess.run(['ffmpeg', '-hide_banner', '-i', path, '-af', 'ebur128', '-f', 'null', '-'],
                       capture_output=True, text=True).stderr
    return float(re.findall(r'I:\s+(-?[\d.]+) LUFS', t)[-1])


def bed_gain(voice, bed, start, duration, under):
    """Gain that puts the DUCKED bed `under` LU below the voice, measured on the real stems
    (two correction passes: the ducking compressor is not linear in gain)."""
    import tempfile
    tmp = tempfile.mkdtemp()
    vstem, bstem = os.path.join(tmp, 'v.wav'), os.path.join(tmp, 'b.wav')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', voice, '-vn', '-ac', '2', '-ar', '48000', vstem], check=True)
    v = lufs(vstem)
    gain_db = (v - under) - (mean_db(bed) + 3)          # first guess
    measured = None
    for _ in range(3):
        g = 10 ** (gain_db / 20)
        fg = ('[0:a]aresample=48000,aformat=channel_layouts=stereo[k];'
              '[1:a]aresample=48000,aformat=channel_layouts=stereo,volume=%.6f,atrim=duration=%.3f[b];[b][k]%s[o]'
              % (g, duration, DUCK))
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', vstem, '-stream_loop', '-1']
                       + (['-ss', '%.3f' % start] if start > 0 else []) + ['-i', bed, '-filter_complex', fg,
                       '-map', '[o]', '-t', '%.3f' % duration, bstem], check=True)
        measured = v - lufs(bstem)
        if abs(measured - under) < 0.5:
            break
        gain_db += measured - under
    return 10 ** (gain_db / 20), measured


def settled(cues, swap_in, out, frames):
    """Mirror of layout.completionTimes: the engine draws cues shifted to settle before out."""
    if not cues or out >= frames:
        return cues
    adv = max(0, cues[-1] + ENTER_F - (out - SETTLE_F))
    return [c - adv for c in cues]


def derive_cues(cfg):
    frames = cfg['frames']
    cues = []
    for sc in cfg['scenes'][1:]:
        cues.append({'role': 'transition_whoosh', 'frame': sc['from'], 'why': 'scene -> %s' % sc['mode']})
    for i, s in enumerate(cfg['swaps']):
        cues.append({'role': 'transition_whoosh', 'frame': s['in'], 'why': 'swap %d in' % (i + 1)})
        if s['content']['kind'] == 'cta':
            cues.append({'role': 'cta_riser', 'frame': s['in'], 'why': 'swap %d: lift into the call to action' % (i + 1)})
        if s['out'] < frames:
            cues.append({'role': 'transition_whoosh', 'frame': s['out'], 'why': 'swap %d out' % (i + 1)})
        k = s['content']
        default = s['in'] + SWAP_F
        if k['kind'] in ('stat', 'cta'):
            raw = [k.get('at', default)]
        elif k['kind'] == 'checklist':
            raw = [x['at'] for x in k['items']]
        elif k['kind'] == 'funnel':
            raw = [x['at'] for x in k['stages']]
        elif k['kind'] == 'decision':
            raw = [x['at'] for x in k['options']] + [k['pickAt']]
        else:
            raw = []
        drawn = settled(raw, s['in'], s['out'], frames)
        for j, f in enumerate(drawn):
            is_pick = k['kind'] == 'decision' and j == len(drawn) - 1
            # felt landing of an eased entrance ~58% through it
            land = f - 5 + int(round(ENTER_F * 0.58))
            role = 'state_change' if is_pick else ('cta_ding' if k['kind'] == 'cta' else 'element_land')
            cues.append({'role': role, 'frame': land, 'why': 'swap %d %s element %d' % (i + 1, k['kind'], j + 1)})
    for b in cfg.get('backText') or []:
        cues.append({'role': 'back_text_hit', 'frame': b['in'] + 8, 'why': 'back text lands: %s' % b['text']})
    for n in cfg.get('inserts') or []:
        cues.append({'role': 'insert_pop', 'frame': n['in'] + 6, 'why': '%s card appears' % n['kind']})
        if n['kind'] == 'follow':
            cues.append({'role': 'state_change', 'frame': n['in'] + 26, 'why': 'follow card: Follow tapped'})
    for e in cfg.get('effects') or []:
        for c in effect_cues(e):
            cues.append(c)
    return sorted(cues, key=lambda c: c['frame'])


def effect_cues(e):
    """Sounds for the effects (src/components/vertical/effects): each kind knows its own beats."""
    k, a = e['kind'], e.get('in', e.get('at', 0))
    if k in ('word-stamp', 'icon-strike'):
        return [{'role': 'back_text_hit', 'frame': a + 6, 'why': '%s lands' % k}]
    if k in ('keycaps',):
        return [{'role': 'state_change', 'frame': a + 4 + 5 * i, 'why': 'key %d' % (i + 1)} for i in range(len(e.get('keys') or []))]
    if k in ('receipt',):
        return [{'role': 'insert_pop', 'frame': f, 'why': 'receipt line'} for f in (e.get('lineAt') or [])]
    if k in ('page-scroll', 'live-markup', 'intertitle', 'counter', 'pie'):
        return [{'role': 'transition_whoosh' if k in ('page-scroll', 'intertitle') else 'insert_pop', 'frame': a, 'why': '%s in' % k}]
    if k in ('list-tracker', 'note-wall'):
        return [{'role': 'element_land', 'frame': it['at'], 'why': '%s item' % k} for it in (e.get('items') or e.get('notes') or [])]
    if k == 'snap-zoom':
        return [{'role': 'back_text_hit', 'frame': e['at'], 'why': 'snap zoom'}]
    if k == 'giant-number':
        return [{'role': 'back_text_hit', 'frame': a + 4, 'why': 'giant number %s slams in' % e.get('value', '')}]
    if k in ('quote-card', 'pinned-line', 'highlighter', 'arrow-note'):
        return [{'role': 'insert_pop', 'frame': a, 'why': '%s in' % k}]
    if k == 'cover-story':
        return [{'role': 'back_text_hit', 'frame': a + 6, 'why': 'cover story'}]
    if k == 'comment-box':
        kw = e.get('keyword') or ''
        return ([{'role': 'state_change', 'frame': a + 10 + 4 * i, 'why': 'key %d' % (i + 1)} for i in range(len(kw))]
                + [{'role': 'cta_ding', 'frame': a + 14 + 4 * len(kw), 'why': 'comment sent'}])
    if k == 'card':
        return ([{'role': 'transition_whoosh', 'frame': a, 'why': 'card in'}]
                + [{'role': 'element_land', 'frame': it['at'], 'why': 'card item'} for it in e.get('items') or [] if it.get('at') is not None])
    if k in ('transition',):
        return [{'role': 'transition_whoosh', 'frame': a, 'why': 'transition: %s' % e.get('style', '')}]
    return []


def main():
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    name, picture, final = sys.argv[1:]
    cfg = reel_config.load(name)
    voice = os.path.join(ROOT, 'public', cfg['src'])
    duration = cfg['frames'] / float(FPS)
    roles = json.load(open(os.path.join(ROOT, 'sounds.json')))
    target = mean_db(voice) - 8
    inputs = ['ffmpeg', '-y', '-v', 'error', '-i', voice]
    filters = ['[0:a]aresample=48000,aformat=channel_layouts=stereo[v]']
    labels = ['[v]']
    resolved = []
    cues = derive_cues(cfg) if cfg.get('sfx') is not False else []   # a style can ask for no cue sounds
    means = {}
    # peaks.json (scripts/make_sounds.py): when a sound is loudest. It starts that much early so its
    # loudest moment lands on the frame of the event, not its first sample. Your own files: add them there
    pk_p = os.path.join(ROOT, 'sounds', 'sfx', 'peaks.json')
    peaks = json.load(open(pk_p)) if os.path.exists(pk_p) else {}
    for c in cues:
        path = roles.get(c['role'])
        at = c['frame'] / float(FPS)
        if not path:
            resolved.append(dict(c, at=round(at, 3), status='unassigned'))
            continue
        clip = os.path.join(ROOT, path)
        if not os.path.isfile(clip):
            sys.exit('mix_master: sounds.json %s points at a missing file: %s' % (c['role'], path))
        if clip not in means:
            means[clip] = mean_db(clip)
        i = len(labels)
        inputs += ['-i', clip]
        same = sum(1 for x in cues if x['role'] == c['role'] and abs(x['frame'] - c['frame']) <= 3)
        gain = 10 ** ((target - 10 * math.log10(max(same, 1)) - means[clip]) / 20)
        start = max(0.0, at - float(peaks.get(path, 0.0)))
        filters.append('[%d:a]aresample=48000,aformat=channel_layouts=stereo,volume=%.8f,adelay=%dS:all=1[s%d]'
                       % (i, gain, round(start * 48000), i))
        labels.append('[s%d]' % i)
        resolved.append(dict(c, at=round(at, 3), starts=round(start, 3), status='assigned', file=path, gain=round(gain, 5)))
    # MUSIC BED (Shortify): one bed under the voice, ducked when you speak, rotated so two
    # reels in a row never share a bed. Only beds the creator supplied in sounds.json.
    beds = [b for b in roles.get('music_beds', []) if b]
    log_p = os.path.join(ROOT, 'qa', 'music-log.json')
    log = json.load(open(log_p)) if os.path.exists(log_p) else []
    bed = cfg.get('music')
    if bed is None and beds:
        prev = [e['bed'] for e in log if e['reel'] != name]
        last_other = prev[-1] if prev else None
        used = {b: max([i for i, e in enumerate(log) if e['bed'] == b] or [-1]) for b in beds}
        order = sorted(beds, key=lambda b: used[b])
        # rotation is a preference: with one bed (or none unused) the least recently used still plays, never silence
        bed = next((b for b in order if b != last_other), order[0] if order else None)
    music_note = 'none (no music_beds in sounds.json)' if not beds and not bed else 'none'
    if bed:
        bp = os.path.join(ROOT, bed)
        if not os.path.isfile(bp):
            sys.exit('mix_master: music bed missing: %s' % bed)
        i = len(labels)
        start = float(cfg.get('musicStart') or 0)
        inputs += ['-stream_loop', '-1'] + (['-ss', '%.3f' % start] if start > 0 else []) + ['-i', bp]
        under = float(cfg.get('musicUnderLu') or roles.get('music_under_voice_lu', 16))   # per-reel override
        g, measured = bed_gain(voice, bp, start, duration, under)   # measured, not guessed
        music_note_level = 'ducked bed %.1f LU under the voice (target %.0f)' % (measured, under)
        filters[0] = '[0:a]aresample=48000,aformat=channel_layouts=stereo,asplit=2[v][vkey]'
        filters.append('[%d:a]aresample=48000,aformat=channel_layouts=stereo,volume=%.6f,atrim=duration=%.3f,'
                       'afade=t=in:d=%.2f,afade=t=out:st=%.3f:d=1.2[bedraw]' % (i, g, duration, 0.3 if start > 0 else 0.6, max(0, duration - 1.2)))
        filters.append('[bedraw][vkey]%s[bed]' % DUCK)
        labels.append('[bed]')
        music_note = '%s, %s' % (bed, music_note_level)
        if not log or log[-1].get('reel') != name or log[-1].get('bed') != bed:
            log.append({'reel': name, 'bed': bed})
            json.dump(log, open(log_p, 'w'), indent=1)
    filters.append('%samix=inputs=%d:normalize=0:dropout_transition=0,atrim=duration=%.3f[mix]'
                   % (''.join(labels), len(labels), duration))
    qa = os.path.join(ROOT, 'qa', name, os.environ.get('MIX_QA_SUB', ''))   # a review draft keeps its records apart
    os.makedirs(qa, exist_ok=True)
    mix = os.path.join(qa, 'mix.wav')
    subprocess.run(inputs + ['-filter_complex', ';'.join(filters), '-map', '[mix]', '-c:a', 'pcm_s24le', mix], check=True)
    json.dump(resolved, open(os.path.join(qa, 'sound-cues.json'), 'w'), indent=1)

    m = loud(mix)
    af = ('loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={input_i}:measured_TP={input_tp}:measured_LRA={input_lra}:'
          'measured_thresh={input_thresh}:offset={target_offset}:linear=true').format(**m)
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', picture, '-i', mix, '-map', '0:v:0', '-map', '1:a:0',
                    '-af', af, '-c:v', 'copy', '-c:a', 'aac', '-b:a', '256k', '-ar', '48000',
                    '-movflags', '+faststart', final], check=True)
    chk = loud(final)
    json.dump({'before': m, 'final': chk}, open(os.path.join(qa, 'loudness.json'), 'w'), indent=1)
    n_on = sum(1 for r in resolved if r['status'] == 'assigned')
    print('mixed %s: %d cues (%d assigned, %d unassigned), music %s, integrated %.1f LUFS, true peak %.1f dBTP'
          % (final, len(resolved), n_on, len(resolved) - n_on, music_note, float(chk['input_i']), float(chk['input_tp'])))
    if float(chk['input_tp']) > -1.0:
        sys.exit('mix_master: true peak %.2f dBTP is above -1. Lower the mix and re-run.' % float(chk['input_tp']))


if __name__ == '__main__':
    main()

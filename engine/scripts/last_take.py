#!/usr/bin/env python3
"""Step 2 — LAST TAKE: pick the last complete take of every script sentence, cut the rest.

    python3 scripts/last_take.py inputs/<name>.mp4 --words script/word-timings/<name>-wx.json \
        --script script/<name>.txt --out public/host/<name>-cut.mp4 \
        --report script/<name>-takes.md --json script/word-timings/<name>-takes.json \
        [--noise-db N --strict-db N] [--drop-take N,..] [--keep-take N,..] [--allow-missing] [--plan-only]

Why this exists: a creator re-reads lines without saying "reset, reset". The copied
cutter (hostcut_plan.py) only removes marked flubs and dead air, so every retake would
ship. This step matches the transcript against the writer's script, keeps the LAST
complete take of each script sentence, drops false starts / partial and earlier takes,
and tightens sentence-boundary pauses. It is built on the copied hostcut.py primitives,
unchanged: one silence map, the HARD RULE gate, and forbidden spans. Every dropped take
is a forbidden span, so render_cut structurally refuses a keep list that leaks one.

Rule: the LAST complete take of each sentence that can be CUT OUT cleanly (silence at both
edges, or a neighboring kept sentence running straight on), unless an earlier complete take
covers the script at least NEAR_BEST better (a later stumble loses to a clean earlier read).

Units are SENTENCES (the writer's . ? !), grouped into paragraphs (spoken beats) for
the scene map. A sentence-level choice lets a clean earlier read of sentence A pair
with a later read of sentence B.

Cuts land only in real silence (>= 0.15s) and only between sentences. Pauses inside a
sentence are never touched. Python 3.9 compatible.
"""
import argparse
import difflib
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hostcut  # noqa: E402  (copied, unchanged)

MIN_JOIN = 0.15      # a cut may land only in a silence at least this long
LEAD = 0.12          # silence kept before a kept take's first word
END_BREATH = 0.30   # silence after the very last word: end on the high point, no padded tail (seam rule: tail <= 0.35s)
TAIL = 0.18          # silence kept after a kept take's last word (LEAD + TAIL = a natural sentence pause)
TIGHT_MIN = 0.35     # sentence-boundary pauses at least this long get tightened
FLOOR_MED = 0.28     # ...to this much silence
FLOOR_LONG = 0.22    # ...or this, for dead air >= 2s
COMPLETE = 0.80      # script-token coverage for a take to count as complete
PARTIAL = 0.35       # below this a match is noise, not a take
NEAR_BEST = 0.10     # a later take within this much coverage of the best one still wins

NUMWORDS = {'zero': '0', 'one': '1', 'two': '2', 'three': '3', 'four': '4', 'five': '5', 'six': '6',
            'seven': '7', 'eight': '8', 'nine': '9', 'ten': '10', 'eleven': '11', 'twelve': '12',
            'thirteen': '13', 'fourteen': '14', 'fifteen': '15', 'sixteen': '16', 'seventeen': '17',
            'eighteen': '18', 'nineteen': '19', 'twenty': '20', 'thirty': '30', 'forty': '40',
            'fifty': '50', 'hundred': '100'}
# whisper's recurring mishearings of brand words; extend as they show up in take reports
ALIASES = {'chatgbt': 'chatgpt', 'chatgtp': 'chatgpt', 'chatgbd': 'chatgpt', 'chatgpd': 'chatgpt',
           'chatbt': 'chatgpt', 'proplexity': 'perplexity', 'perplexy': 'perplexity',
           'saddick': 'sciatica', 'sciadica': 'sciatica', 'siatica': 'sciatica', 'sciatic': 'sciatica',
           'chirpactors': 'chiropractors', 'chiroactors': 'chiropractors'}


def norm(tok):
    t = re.sub(r'[^a-z0-9]', '', tok.lower())
    t = NUMWORDS.get(t, t)
    return ALIASES.get(t, t)


def sim(a, b):
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    if len(a) >= 4 and len(b) >= 3:
        r = difflib.SequenceMatcher(None, a, b).ratio()
        if r >= 0.72:
            return r
    return 0.0


# ── calibration + the one silence map ──────────────────────────────────────────────────
def rms_floor(src):
    """p10 of 100ms RMS windows (dB). The recording's own room tone."""
    p = subprocess.run(
        ['ffmpeg', '-nostdin', '-i', src, '-vn', '-ac', '1', '-ar', '48000', '-af',
         'asetnsamples=4800,astats=metadata=1:reset=1,ametadata=print:key=lavfi.astats.Overall.RMS_level:file=-',
         '-f', 'null', '-'], capture_output=True, text=True)
    vals = []
    for line in p.stdout.splitlines():
        if 'RMS_level=' in line:
            v = line.split('=', 1)[1].strip()
            try:
                f = float(v)
            except ValueError:
                continue
            if f > -120:
                vals.append(f)
    if not vals:
        raise RuntimeError('could not measure audio levels in %s' % src)
    vals.sort()
    return vals[len(vals) // 10]


# ── script units ───────────────────────────────────────────────────────────────────────
def script_units(text):
    """[{id, para, text, toks}] — one per writer's sentence, paragraph = spoken beat."""
    units = []
    paras = [p.strip() for p in re.split(r'\n\s*\n', text.strip()) if p.strip()]
    for pi, p in enumerate(paras):
        for s in re.split(r'(?<=[.?!])["”]?\s+', ' '.join(p.split())):
            s = s.strip()
            if not s:
                continue
            toks = [norm(t) for t in re.findall(r"[A-Za-z0-9][A-Za-z0-9'\-]*", s)]
            toks = [t for t in toks if t]
            if toks:
                units.append({'id': len(units), 'para': pi, 'text': s, 'toks': toks})
    return units


# ── semi-global alignment of one sentence against the whole transcript ──────────────────
MATCH_BAD, DEL, INS = -1.5, -1.0, -0.6


def align(P, T):
    """Script tokens P (fully aligned) vs transcript tokens T (free ends).
    Returns H[m] row and a traceback function end_j -> (j0, matched_idx_set)."""
    m, n = len(P), len(T)
    NEG = -1e9
    H = [[0.0] * (n + 1)] + [[NEG] * (n + 1) for _ in range(m)]
    B = [[None] * (n + 1) for _ in range(m + 1)]
    for i in range(1, m + 1):
        H[i][0] = H[i - 1][0] + DEL
        B[i][0] = ('D',)
        for j in range(1, n + 1):
            best, bp = NEG, None
            s1 = sim(P[i - 1], T[j - 1])
            v = H[i - 1][j - 1] + ((2 * s1 - 1) if s1 > 0 else MATCH_BAD)
            if v > best:
                best, bp = v, ('M' if s1 > 0 else 'X',)
            v = H[i - 1][j] + DEL
            if v > best:
                best, bp = v, ('D',)
            v = H[i][j - 1] + INS
            if v > best:
                best, bp = v, ('I',)
            # two ASR tokens = one script token ('chat' + 'gbt' = 'ChatGPT'), only when
            # neither half matches alone, and always worth LESS than a clean 1:1 match
            if j >= 2 and s1 == 0 and sim(P[i - 1], T[j - 2]) == 0:
                joined = ALIASES.get(T[j - 2] + T[j - 1], T[j - 2] + T[j - 1])
                s2 = sim(P[i - 1], joined)
                if s2 > 0:
                    v = H[i - 1][j - 2] + (2 * s2 - 1) - 0.3
                    if v > best:
                        best, bp = v, ('J',)
            H[i][j], B[i][j] = best, bp

    def trace(j_end):
        i, j = m, j_end
        matched, jfirst = set(), None
        while i > 0:
            op = B[i][j][0]
            if op in ('M', 'X'):
                if op == 'M':
                    matched.add(i - 1)
                    jfirst = j - 1
                i, j = i - 1, j - 1
            elif op == 'J':
                matched.add(i - 1)
                jfirst = j - 2
                i, j = i - 1, j - 2
            elif op == 'D':
                i -= 1
            else:
                j -= 1
        return jfirst, matched

    return H[m], trace


def candidates_for(unit, T, words):
    P = unit['toks']
    m = len(P)
    row, trace = align(P, T)
    seen, out = set(), []
    for j in range(1, len(T) + 1):
        if row[j] <= -1e8:
            continue
        # local maximum of the end score (a take's natural end)
        if (j < len(T) and row[j + 1] > row[j]) or row[j - 1] > row[j]:
            continue
        if row[j] < 0.2 * m:
            continue
        j0, matched = trace(j)
        if j0 is None:
            continue
        cov = len(matched) / float(m)
        if cov < PARTIAL:
            continue
        span = (j0, j - 1)
        dur = words[span[1]]['end'] - words[span[0]]['start']
        if dur > max(4.0, 0.7 * m + 3.0):
            continue                                   # alignment wandered across takes
        if span in seen:
            continue
        seen.add(span)
        ends_ok = (m - 1 in matched or m - 2 in matched) and (0 in matched or 1 in matched)
        out.append({'unit': unit['id'], 'i0': span[0], 'i1': span[1], 'score': round(row[j], 2),
                    'coverage': round(cov, 2), 'complete': cov >= COMPLETE and ends_ok})
    # overlapping candidates of the same unit: keep the better score
    out.sort(key=lambda c: -c['score'])
    kept = []
    for c in out:
        if any(not (c['i1'] < k['i0'] or c['i0'] > k['i1']) for k in kept):
            continue
        kept.append(c)
    kept.sort(key=lambda c: c['i0'])
    return kept


# ── boundaries in silence ──────────────────────────────────────────────────────────────
def silence_before(S, prev_end, first_start):
    c = [(s, e) for s, e in S if e - s >= MIN_JOIN and e > prev_end - 0.15 and s < first_start + 0.08]
    if not c:
        return None
    s, e = max(c, key=lambda p: p[0])
    return round(min(max(first_start - LEAD, s + 0.02), e - 0.02), 3)


def silence_after(S, last_end, next_start):
    c = [(s, e) for s, e in S if e - s >= MIN_JOIN and s < next_start + 0.08 and e > last_end - 0.08]
    if not c:
        return None
    s, e = min(c, key=lambda p: p[0])
    return round(min(max(last_end + TAIL, s + 0.02), e - 0.02), 3)


JOIN_TARGET_TAIL, JOIN_TARGET_LEAD = 0.16, 0.12   # speech-to-cut and cut-to-speech after refining


def render(a, rec, keep, S, dur, forbidden):
    """Render the cut: snap boundaries onto cuts already in the source, then J-cut every join
    (scripts/picture_plan.py). Records the picture plan in the takes record."""
    import picture_plan as PP
    cuts = PP.source_cuts(a.src)
    keep, snaps = PP.snap_to_source_cuts([tuple(k) for k in keep], S, cuts, MIN_JOIN, dur)
    hostcut.assert_cuts_in_silence(keep, S, dur, min_join_silence=MIN_JOIN, forbidden_spans=forbidden)
    lead = 0.0 if getattr(a, 'no_jcut', False) else PP.LEAD
    L = PP.leads(keep, S, cuts, lead)
    pics = PP.picture_spans(keep, L)
    hostcut.render_cut(a.src, keep, a.out, silences=S, duration=dur, forbidden_spans=forbidden,
                       min_join_silence=MIN_JOIN, crf=18, picture=pics)
    rec['keep'] = [list(k) for k in keep]
    rec['cut_duration'] = round(sum(e0 - s0 for s0, e0 in keep), 3)
    rec['source_cuts'] = cuts
    rec['snaps'] = snaps
    rec['leads'] = L
    rec['picture'] = [list(p) for p in pics]
    rec['video_joins'] = PP.video_joins(keep, L)
    # sidecar next to the cut: the renderer reads where the PICTURE changes (second framing, cut sheets)
    side = os.path.splitext(a.out)[0] + '.json'
    json.dump({'videoJoins': rec['video_joins'], 'leads': L, 'sourceCuts': len(cuts)}, open(side, 'w'))
    if snaps:
        print('source cuts: %d boundaries moved onto cuts already in the clip' % sum(1 for n in snaps if '->' in n))
    print('j-cuts: %d of %d joins lead with the next voice (%.2fs)' % (sum(1 for x in L if x > 0), len(L), lead))
    return keep


def refine(a):
    """Second pass, after whisperX has aligned the CUT (accurate word edges). The first pass
    placed joins from fast-whisper times, which run loose, so a join can leave 0.6-1s of air.
    Measure each join in the cut, move its boundaries toward the speech, keep them inside the
    same silence (the HARD RULE), and re-render. Never touches a pause without a cut in it."""
    rec = json.load(open(a.json))
    keep = [list(k) for k in rec['keep']]
    S = [tuple(x) for x in rec['silences']]
    cutw = [w for w in json.load(open(a.refine)) if w.get('word', '').strip()]
    dur = rec['duration']
    acc, joins = 0.0, []
    for i, (s0, e0) in enumerate(keep):
        if i:
            joins.append((i, acc))
        acc += e0 - s0
    moved = []
    for i, jt in joins:
        before = [w for w in cutw if w['end'] <= jt + 0.05]
        after = [w for w in cutw if w['start'] >= jt - 0.05]
        if not before or not after:
            continue
        left = jt - before[-1]['end'] - JOIN_TARGET_TAIL      # extra air before the join (cut time)
        right = after[0]['start'] - jt - JOIN_TARGET_LEAD      # extra air after the join
        pe, ns = keep[i - 1][1], keep[i][0]
        sil_e = next(((s0, e0) for s0, e0 in S if s0 - 0.006 <= pe <= e0 + 0.006 and e0 - s0 >= MIN_JOIN), None)
        sil_s = next(((s0, e0) for s0, e0 in S if s0 - 0.006 <= ns <= e0 + 0.006 and e0 - s0 >= MIN_JOIN), None)
        new_pe, new_ns = pe, ns
        if left > 0.02 and sil_e:
            new_pe = round(min(pe, max(pe - left, sil_e[0] + 0.03)), 3)   # only ever tighten
        if right > 0.02 and sil_s:
            new_ns = round(max(ns, min(ns + right, sil_s[1] - 0.03)), 3)
        if (new_pe, new_ns) != (pe, ns):
            keep[i - 1][1], keep[i][0] = new_pe, new_ns
            moved.append('join %d: -%.2fs before, -%.2fs after' % (i, pe - new_pe, new_ns - ns))
    if not moved:
        print('refine: joins already tight, no re-cut')
        return
    forbidden = [tuple(f) for f in rec['forbidden']]
    hostcut.assert_cuts_in_silence([tuple(k) for k in keep], S, dur, min_join_silence=MIN_JOIN, forbidden_spans=forbidden)
    render(a, rec, keep, S, dur, forbidden)
    rec['refined'] = moved
    json.dump(rec, open(a.json, 'w'), indent=1)
    with open(a.report, 'a') as f:
        f.write('\n## Joins refined after alignment (HARD RULE re-checked: PASS)\n\n' + '\n'.join('- ' + m for m in moved) + '\n')
    print('refine: %d joins tightened, cut now %.1fs -> %s' % (len(moved), rec['cut_duration'], a.out))
    print('\n'.join('  ' + m for m in moved))


def trims_path(a):
    return re.sub(r'-takes\.json$', '-trims.json', a.json)


def apply_trims(keep, trims):
    """Remove raw ranges from the keep list (a fumble inside a kept take). The HARD RULE gate
    checks every new boundary afterwards, so a trim edge must sit in a real silence."""
    out = []
    for s0, e0 in keep:
        segs = [(s0, e0)]
        for ta, tb in trims:
            nxt = []
            for x0, x1 in segs:
                if tb <= x0 or ta >= x1:
                    nxt.append((x0, x1))
                    continue
                if ta > x0:
                    nxt.append((x0, ta))
                if tb < x1:
                    nxt.append((tb, x1))
            segs = nxt
        out += [(round(x0, 3), round(x1, 3)) for x0, x1 in segs if x1 - x0 > 0.05]
    return out


def trim(a):
    """Cut a raw range out of the current cut (e.g. Chris: "at 24s there is a fumble"). Saved to
    <name>-trims.json so every later re-run keeps it."""
    ta, tb = [float(x) for x in a.trim.split('-')]
    rec = json.load(open(a.json))
    S = [tuple(x) for x in rec['silences']]
    keep = apply_trims([tuple(k) for k in rec['keep']], [(ta, tb)])
    forbidden = [tuple(f) for f in rec['forbidden']]
    hostcut.assert_cuts_in_silence(keep, S, rec['duration'], min_join_silence=MIN_JOIN, forbidden_spans=forbidden)
    keep = render(a, rec, keep, S, rec['duration'], forbidden)
    tp = trims_path(a)
    trims = json.load(open(tp)) if os.path.exists(tp) else []
    trims.append({'raw': [ta, tb], 'why': 'manual trim (fumble kept by the selector)'})
    json.dump(trims, open(tp, 'w'), indent=1)
    rec.setdefault('trims', []).append([ta, tb])
    json.dump(rec, open(a.json, 'w'), indent=1)
    with open(a.report, 'a') as f:
        f.write('\n## Manual trim (HARD RULE re-checked: PASS)\n\n- removed raw %.2f-%.2f\n' % (ta, tb))
    print('trim: removed raw %.2f-%.2f, cut now %.1fs -> %s (saved to %s)' % (ta, tb, rec['cut_duration'], a.out, os.path.basename(tp)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src')
    ap.add_argument('--words', required=True)
    ap.add_argument('--script', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--report', required=True)
    ap.add_argument('--json', required=True)
    ap.add_argument('--noise-db', type=float, default=None)
    ap.add_argument('--strict-db', type=float, default=None)
    ap.add_argument('--word-gaps', action='store_true',
                    help='outdoor shoots: pauses are the gaps between aligned words (needs precise word times), not quiet audio')
    ap.add_argument('--denoise-detect', action='store_true',
                    help='find silences on a traffic-filtered copy of the audio (outdoor shoots); the cut still uses the original')
    ap.add_argument('--drop-take', default='')
    ap.add_argument('--keep-take', default='')
    ap.add_argument('--allow-missing', action='store_true')
    ap.add_argument('--plan-only', action='store_true')
    ap.add_argument('--no-jcut', action='store_true', help='picture and sound cut at the same moment (no J-cuts)')
    ap.add_argument('--refine', default=None, help='cut-wx.json of the current cut: tighten loose joins, re-cut')
    ap.add_argument('--trim', default=None, help='RAW_A-RAW_B seconds of the raw take to remove (a fumble the selector kept); saved to <name>-trims.json')
    a = ap.parse_args()
    if a.refine:
        return refine(a)
    if a.trim:
        return trim(a)

    words = json.load(open(a.words))
    words = [w for w in words if w.get('word', '').strip()]
    T = [norm(w['word']) for w in words]
    units = script_units(open(a.script).read())
    dur = hostcut.probe_duration(a.src)

    det = a.src
    if a.denoise_detect:
        # OUTDOOR SHOOTS: street sound in the pauses peaks near -20 dB and hides them. Detect on a
        # copy with the rumble and hiss filtered and the steady noise tracked out; voice is untouched
        # in the cut itself. Only WHERE the pauses are comes from this copy.
        det = os.path.splitext(a.json)[0] + '-detect.wav'
        subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-i', a.src, '-vn', '-ac', '1', '-ar', '48000', '-af',
                        'highpass=f=150,lowpass=f=6000,afftdn=nr=24:nf=-28:tn=1', det], check=True)
    floor = rms_floor(det)
    strict = a.strict_db if a.strict_db is not None else float(min(max(round(floor + 16), -45), -28))
    loose = a.noise_db if a.noise_db is not None else strict + 4
    S = hostcut.detect_silences(det, noise_db=loose, min_d=0.06, duration=dur, strict_db=strict)
    if a.word_gaps:
        # OUTDOOR SHOOTS: traffic fills the pauses, so loudness cannot find them. A pause is any gap
        # of 0.25s+ between aligned words (precise whisperX times), kept 0.06s clear of each word.
        # The HARD RULE still holds: no cut can land on a word. Run word_align_x.py WITHOUT --fast first.
        G = []
        prev = 0.0
        for w in words:
            a0, b0 = prev + 0.06, w['start'] - 0.06
            if b0 - a0 >= 0.25 - 0.12:
                G.append((round(a0, 3), round(b0, 3)))
            prev = max(prev, w['end'])
        if dur - prev > 0.2:
            G.append((round(prev + 0.06, 3), round(dur, 3)))
        # union with the true-quiet map: the aligner sometimes smears a word over a real pause
        # (measured: "tomorrow" stretched 2.5s over silence), and quiet that deep is never speech
        S = sorted(G + [tuple(x) for x in S])
        M = []
        for x0, x1 in S:
            if M and x0 <= M[-1][1]:
                M[-1] = (M[-1][0], max(M[-1][1], x1))
            else:
                M.append((x0, x1))
        S = M

    # candidates, numbered in transcript order for the report and the overrides
    cands = []
    for u in units:
        cands += candidates_for(u, T, words)
    cands.sort(key=lambda c: (c['i0'], c['unit']))
    for k, c in enumerate(cands, 1):
        c['n'] = k
    drop = {int(x) for x in a.drop_take.split(',') if x.strip()}
    force = {int(x) for x in a.keep_take.split(',') if x.strip()}

    # CUTTABLE EDGES: a take can only be kept if it can be cut out. Its start needs a real
    # silence before it (or the previous sentence's take ending right against it), and its end
    # a silence after it (or the next chosen sentence starting right against it). Back-to-back
    # retakes with no pause between them otherwise force a cut through speech.
    def start_ok(c):
        if c['i0'] == 0:
            return True
        if silence_before(S, words[c['i0'] - 1]['end'], words[c['i0']]['start']) is not None:
            return True
        return any(o['unit'] == c['unit'] - 1 and o['i1'] == c['i0'] - 1 and o['complete'] for o in cands)

    def end_ok(c, nxt):
        if c['i1'] == len(words) - 1:
            return True
        if nxt is not None and nxt['i0'] == c['i1'] + 1:
            return True
        return silence_after(S, words[c['i1']]['end'], words[c['i1'] + 1]['start']) is not None

    # backward pass: latest complete take of each sentence, monotonic in the transcript
    chosen, missing = {}, []
    limit = len(words)
    nxt_pick = None
    for u in reversed(units):
        mine = [c for c in cands if c['unit'] == u['id'] and c['n'] not in drop and c['i1'] < limit]
        # if the take after this one cannot start on its own, keep the take that runs into it
        if nxt_pick is not None and not (nxt_pick['i0'] == 0 or silence_before(S, words[nxt_pick['i0'] - 1]['end'], words[nxt_pick['i0']]['start']) is not None):
            glued = [c for c in mine if c['i1'] == nxt_pick['i0'] - 1 and c['complete']]
            if glued:
                mine = glued
        cuttable = [c for c in mine if start_ok(c) and end_ok(c, nxt_pick)]
        if any(c['complete'] for c in cuttable):
            mine = cuttable
        forced = [c for c in mine if c['n'] in force]
        # the LAST complete take, unless an earlier complete take reads the script clearly
        # better (a later take that stumbles loses to a clean earlier one)
        done = [c for c in mine if c['complete']]
        best_cov = max([c['coverage'] for c in done] or [0])
        pick = forced[-1] if forced else next((c for c in reversed(done) if c['coverage'] >= best_cov - NEAR_BEST), None)
        if pick is None:
            missing.append(u['id'])
            continue
        chosen[u['id']] = pick
        limit = pick['i0']
        nxt_pick = pick
    if missing and not a.allow_missing:
        pass  # reported below, then exit non-zero

    # label every transcript word
    label = [None] * len(words)
    for uid, c in chosen.items():
        for i in range(c['i0'], c['i1'] + 1):
            label[i] = ('KEPT', 'S%d' % (uid + 1))
    chosen_ns = {c['n'] for c in chosen.values()}
    for c in cands:
        if c['n'] in chosen_ns:
            continue
        win = chosen.get(c['unit'])
        if not c['complete']:
            why = 'partial retake / false start'
        elif win is not None and c['i0'] > win['i0']:
            why = 'later take, reads the script less cleanly'
        else:
            why = 'earlier take'
        why += ' of S%d' % (c['unit'] + 1)
        if c['n'] in drop:
            why = 'dropped by --drop-take, S%d' % (c['unit'] + 1)
        for i in range(c['i0'], c['i1'] + 1):
            if label[i] is None:
                label[i] = ('DROPPED', why + ' (take #%d)' % c['n'])
    for i in range(len(words)):
        if label[i] is None:
            label[i] = ('DROPPED', 'unmatched speech')

    # kept groups: consecutive chosen sentences with nothing dropped between them
    order = [chosen[u['id']] for u in units if u['id'] in chosen]
    groups = []
    for c in order:
        if groups and c['i0'] == groups[-1]['i1'] + 1:
            groups[-1]['i1'] = c['i1']
            groups[-1]['units'].append(c['unit'])
        else:
            groups.append({'i0': c['i0'], 'i1': c['i1'], 'units': [c['unit']]})

    errors, keep = [], []
    for g in groups:
        first, last = words[g['i0']], words[g['i1']]
        if g['i0'] == 0 and first['start'] < 0.5:
            # fast-whisper clamps the first word to 0.0; trust the silence map for the head
            head = [(s, e) for s, e in S if s <= 0.05 and e - s >= MIN_JOIN]
            cs = round(max(0.0, head[0][1] - LEAD), 3) if head and head[0][1] - LEAD > head[0][0] + 0.02 else 0.0
        else:
            prev_end = words[g['i0'] - 1]['end'] if g['i0'] > 0 else 0.0
            cs = silence_before(S, prev_end, first['start'])
            if cs is None and g['i0'] == 0:
                cs = 0.0   # the source's own first frame: not a cut, the HARD RULE exempts it (room sound before the first word)
        if g['i1'] == len(words) - 1:
            # the close keeps a short breath after the last word, then ends in silence
            end_t = last['end'] + END_BREATH
            inside = [(s, e) for s, e in S if s <= end_t <= e and e - s >= MIN_JOIN]
            ce = round(dur, 3) if (end_t >= dur - 0.05 or not inside) else round(min(end_t, inside[0][1] - 0.02), 3)
        else:
            nxt = words[g['i1'] + 1]['start'] if g['i1'] + 1 < len(words) else dur
            ce = silence_after(S, last['end'], nxt)
        if cs is None or ce is None:
            errors.append('no silence >= %.2fs at the %s of kept text "%s ... %s" (%.2f-%.2fs)'
                          % (MIN_JOIN, 'start' if cs is None else 'end', first['word'], last['word'],
                             first['start'], last['end']))
            continue
        # sentence-boundary tightening inside the group (never inside a sentence)
        unit_last_idx = {chosen[uid]['i1'] for uid in g['units']}
        segs, cur = [], cs
        for s, e in S:
            if s <= first['start'] or e >= last['end'] or e - s < TIGHT_MIN:
                continue
            before = [i for i in range(g['i0'], g['i1'] + 1) if words[i]['end'] <= s + 0.08]
            if not before:
                continue
            bi = before[-1]
            at_sentence_end = bi in unit_last_idx or words[bi]['word'].rstrip().endswith(('.', '?', '!'))
            if not at_sentence_end:
                continue
            fl = FLOOR_LONG if e - s >= 2.0 else FLOOR_MED
            a_pt, b_pt = round(s + fl / 2, 3), round(e - fl / 2, 3)
            if b_pt - a_pt < 0.05:
                continue
            segs.append((cur, a_pt))
            cur = b_pt
        segs.append((cur, ce))
        keep += segs

    tp = trims_path(a)
    if os.path.exists(tp):
        keep = apply_trims(keep, [tuple(t['raw']) for t in json.load(open(tp))])
    forbidden = []
    for r in hostcut.detect_reset_spans(words, S):
        forbidden.append(r['forbid'])
    run = None
    for i, (lab, _) in enumerate(label):
        if lab == 'DROPPED':
            run = [i, i] if run is None else [run[0], i]
        if (lab != 'DROPPED' or i == len(words) - 1) and run is not None:
            fs, fe = words[run[0]]['start'] + 0.05, words[run[1]]['end'] - 0.05
            # fast-whisper word edges run loose: where a dropped run's edge sits inside a measured
            # silence, the audio is the truth, so the forbidden span stops at that silence
            for s0, e0 in S:
                if s0 <= fe <= e0:
                    fe = s0
                if s0 <= fs <= e0:
                    fs = e0
            if fe > fs:
                forbidden.append((round(fs, 3), round(fe, 3)))
            run = None

    gate = 'not run'
    if keep and not errors:
        try:
            hostcut.assert_cuts_in_silence(keep, S, dur, min_join_silence=MIN_JOIN, forbidden_spans=forbidden)
            gate = 'PASS'
        except Exception as ex:  # noqa: BLE001  (reported, then exit non-zero)
            gate = 'FAIL: %s' % ex
            errors.append(gate)

    # raw -> cut time (QA only; the whisperX align of the cut is the timing truth)
    def to_cut(t):
        acc = 0.0
        for s, e in keep:
            if t < s:
                return None
            if t <= e:
                return round(acc + t - s, 3)
            acc += e - s
        return None

    cut_len = round(sum(e - s for s, e in keep), 3)
    rec = {'src': a.src, 'script': a.script, 'words': a.words, 'duration': dur,
           'floor_db': round(floor, 1), 'loose_db': loose, 'strict_db': strict,
           'silences': [[round(s, 3), round(e, 3)] for s, e in S],
           'units': [{'id': u['id'], 'para': u['para'], 'text': u['text']} for u in units],
           'candidates': cands, 'chosen': {str(k): v['n'] for k, v in chosen.items()},
           'missing': missing, 'keep': keep, 'forbidden': forbidden, 'gate': gate, 'errors': errors,
           'cut_duration': cut_len,
           'labels': [{'i': i, 'word': w['word'], 'start': w['start'], 'end': w['end'],
                       'label': label[i][0], 'why': label[i][1], 'cut_t': to_cut(w['start'])}
                      for i, w in enumerate(words)]}
    os.makedirs(os.path.dirname(a.json) or '.', exist_ok=True)
    json.dump(rec, open(a.json, 'w'), indent=1)

    # human report
    L = ['# Takes: %s' % os.path.basename(a.src), '',
         'Room tone %.1f dB, silence thresholds loose %.0f / strict %.0f dB, %d silences >= %.2fs.'
         % (floor, loose, strict, sum(1 for s, e in S if e - s >= MIN_JOIN), MIN_JOIN),
         'Raw %.1fs, cut %.1fs, %d keep segments. HARD RULE gate: %s.' % (dur, cut_len, len(keep), gate), '',
         '## Sentences and the take kept', '',
         '| S | beat | kept take | raw time | coverage | script sentence |', '|---|---|---|---|---|---|']
    for u in units:
        c = chosen.get(u['id'])
        if c:
            L.append('| S%d | %d | #%d | %.2f-%.2f | %.0f%% | %s |' % (
                u['id'] + 1, u['para'] + 1, c['n'], words[c['i0']]['start'], words[c['i1']]['end'],
                100 * c['coverage'], u['text']))
        else:
            L.append('| S%d | %d | **MISSING** | | | %s |' % (u['id'] + 1, u['para'] + 1, u['text']))
    L += ['', '## Every stretch of audio, in order', '',
          '| raw time | kept / dropped | why | said (transcript) |', '|---|---|---|---|']
    i = 0
    while i < len(words):
        j = i
        while j + 1 < len(words) and label[j + 1] == label[i]:
            j += 1
        L.append('| %.2f-%.2f | %s | %s | %s |' % (words[i]['start'], words[j]['end'], label[i][0],
                                                  label[i][1], ' '.join(w['word'] for w in words[i:j + 1])))
        i = j + 1
    L += ['', '## Keep segments (raw seconds)', '']
    L += ['- %.3f to %.3f (%.2fs)' % (s, e, e - s) for s, e in keep]
    L += ['', 'Override a pick with `--drop-take N` or `--keep-take N` (take numbers from the candidates in the JSON twin).']
    if errors:
        L += ['', '## ERRORS', ''] + ['- ' + x for x in errors]
    if missing:
        L += ['', '## MISSING', ''] + ['- S%d has no complete take: %s' % (m + 1, units[m]['text']) for m in missing]
    open(a.report, 'w').write('\n'.join(L) + '\n')
    print('\n'.join(L[:5]))

    if errors or (missing and not a.allow_missing):
        sys.exit('last_take: stopped (see %s)' % a.report)
    if a.plan_only:
        print('plan only: no render')
        return
    keep = render(a, rec, keep, S, dur, forbidden)
    json.dump(rec, open(a.json, 'w'), indent=1)
    print('wrote %s (%.1fs)' % (a.out, hostcut.probe_duration(a.out)))


if __name__ == '__main__':
    main()

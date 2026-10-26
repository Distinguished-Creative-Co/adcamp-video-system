#!/usr/bin/env python3
"""AVS's own sound effects, synthesized here from noise, tones and envelopes.

    "$AVS_PYTHON" scripts/make_sounds.py          write sounds/sfx/*.wav and sounds/sfx/peaks.json
    "$AVS_PYTHON" scripts/make_sounds.py --wire   also point the three cue roles in sounds.json at them

Nothing is sampled or downloaded: every sound is built from scratch with numpy and scipy, with a
fixed random seed, so a run always writes the same files and the sounds belong to whoever runs it.
48 kHz, 16-bit stereo WAV, peak -3 dBFS, short fades at both ends.

The roles mix_master.py places:
  whoosh  transition_whoosh: a scene change or a panel swapping in or out
  land    element_land: a stat, checklist item or CTA settling into place
  click   state_change: a decision's pick, the follow card's tap
  impact  back_text_hit: big words landing behind the host, an effect's stamp
  pop     insert_pop: a follow card or clip card appearing, an effect's item landing
  ding    cta_ding: the call-to-action button landing
  riser   cta_riser: the second before the call-to-action card slides in (loudest at its end)
peaks.json records, per file, the time of its loudest 10 ms. mix_master.py starts each sound that
much early, so the loudest moment lands on the frame of the event instead of the file's first sample.
"""
import json
import os
import sys
import wave

import numpy as np
from scipy.signal import butter, sosfilt

SR = 48000
PEAK_DB = -3.0
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, 'sounds', 'sfx')
rng = np.random.default_rng(20261019)


def secs(d):
    return np.arange(int(round(d * SR))) / SR


def band(x, lo, hi, order=2):
    return sosfilt(butter(order, [lo, hi], btype='bandpass', fs=SR, output='sos'), x)


def swept_band(noise, centres, q=1.6, block=256):
    """Noise through a band-pass whose centre follows `centres` (one value per sample). Filtered in
    short blocks with overlapping raised-cosine windows so the sweep has no steps."""
    n = len(noise)
    out = np.zeros(n)
    hop = block // 2
    win = np.hanning(block)
    for start in range(0, n - block, hop):
        c = float(centres[start + hop])
        lo, hi = c / (1 + 1 / q), c * (1 + 1 / q)
        seg = noise[max(0, start - block):start + block]
        y = band(seg, max(lo, 30), min(hi, SR / 2 - 100))[-block:]
        out[start:start + block] += y * win
    return out


def shape(n, attack, release, curve=2.0):
    """0 -> 1 over `attack` samples, hold, 1 -> 0 over the last `release` samples (power curves)."""
    env = np.ones(n)
    a, r = max(1, attack), max(1, release)
    env[:a] = (np.arange(a) / a) ** curve
    env[n - r:] = (1 - np.arange(r) / r) ** curve
    return env


def whoosh():
    """Air passing the listener: band-limited noise whose centre climbs and falls, swelling to a peak
    at about 40 percent of the way through, panned from left to right as it passes."""
    t = secs(0.75)
    n = len(t)
    u = t / t[-1]
    bell = np.exp(-((u - 0.42) / 0.2) ** 2)
    centres = 350 + 2600 * np.exp(-((u - 0.45) / 0.24) ** 2)
    air = swept_band(rng.standard_normal(n + 512), np.pad(centres, (0, 512), mode='edge'))[:n]
    body = band(rng.standard_normal(n), 80, 260) * 0.6
    mono = (air + body) * bell
    pan = np.clip(u * 1.2 - 0.1, 0, 1)
    left, right = mono * np.cos(pan * np.pi / 2), mono * np.sin(pan * np.pi / 2)
    return np.stack([left, right], 1)


def land():
    """A soft wooden thock: a low tone that drops in pitch and dies fast, a little knock of filtered
    noise on the front, and a short tail as if in a small room."""
    t = secs(0.22)
    f = 210 * np.exp(-t * 9) + 120
    phase = 2 * np.pi * np.cumsum(f) / SR
    tone = np.sin(phase) * np.exp(-t * 32)
    knock = band(rng.standard_normal(len(t)), 900, 3200) * np.exp(-t * 180) * 0.5
    room = band(rng.standard_normal(len(t)), 300, 1500) * np.exp(-t * 26) * 0.06
    mono = tone + knock + room
    return np.stack([mono, mono * 0.96], 1)


def click():
    """A crisp interface click: a short bright ping with a noise edge, then a quieter second tap
    45 ms later, like a switch that settles."""
    t = secs(0.14)

    def tap(at, level):
        tt = np.clip(t - at, 0, None)
        on = (t >= at).astype(float)
        ping = np.sin(2 * np.pi * 2300 * tt) * np.exp(-tt * 160)
        edge = band(rng.standard_normal(len(t)), 2500, 9000) * np.exp(-tt * 420)
        return (ping + 0.7 * edge) * on * level
    mono = tap(0.0015, 1.0) + tap(0.047, 0.45)
    return np.stack([mono * 0.97, mono], 1)


def impact():
    """A low body hit: a sine that drops from 150 Hz toward 45 Hz under a fast decay, a short
    filtered knock on the attack, and a little low room."""
    t = secs(0.7)
    f = 105 * np.exp(-t * 14) + 45
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 7.5)
    knock = band(rng.standard_normal(len(t)), 200, 1400) * np.exp(-t * 90) * 0.55
    room = band(rng.standard_normal(len(t)), 60, 300) * np.exp(-t * 9) * 0.08
    mono = tone + knock + room
    return np.stack([mono, mono], 1)


def pop():
    """A short round pop: a tone that flicks up in pitch over 25 ms and is gone, with a breath of air."""
    t = secs(0.16)
    f = 420 + 700 * (1 - np.exp(-t * 120))
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 55)
    air = band(rng.standard_normal(len(t)), 1500, 6000) * np.exp(-t * 200) * 0.25
    mono = tone + air
    return np.stack([mono * 0.98, mono], 1)


def ding():
    """A clean bell: a fundamental near 1.6 kHz with two inharmonic partials, each ringing out at
    its own rate over about a second."""
    t = secs(1.3)
    mono = (np.sin(2 * np.pi * 1600 * t) * np.exp(-t * 4.5)
            + 0.45 * np.sin(2 * np.pi * 1600 * 2.76 * t) * np.exp(-t * 9)
            + 0.25 * np.sin(2 * np.pi * 1600 * 5.40 * t) * np.exp(-t * 16))
    mono *= shape(len(t), int(0.002 * SR), 1, 1.0)
    return np.stack([mono, mono * 0.97], 1)


def riser():
    """A one-second lift into a moment: noise whose band climbs, a tone gliding up an octave and
    a half, both swelling to the top and stopping there (its loudest moment is the very end)."""
    t = secs(1.0)
    n = len(t)
    u = t / t[-1]
    centres = 300 + 4200 * u ** 2
    air = swept_band(rng.standard_normal(n + 512), np.pad(centres, (0, 512), mode='edge'))[:n]
    f = 220 * 2 ** (1.5 * u)
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.35
    mono = (air + tone) * u ** 2.2
    mono[-int(0.004 * SR):] *= np.linspace(1, 0, int(0.004 * SR))
    return np.stack([mono * (1 - 0.3 * u), mono * (0.7 + 0.3 * u)], 1)


SOUNDS = {'whoosh': whoosh, 'land': land, 'click': click, 'impact': impact, 'pop': pop, 'ding': ding, 'riser': riser}
ROLES = {'transition_whoosh': 'whoosh', 'element_land': 'land', 'state_change': 'click',
         'back_text_hit': 'impact', 'insert_pop': 'pop', 'cta_ding': 'ding', 'cta_riser': 'riser'}


def finish(x):
    n = len(x)
    x = x - x.mean(axis=0)
    fade_in, fade_out = int(0.002 * SR), int(0.02 * SR)
    env = shape(n, fade_in, fade_out, curve=1.0)
    x = x * env[:, None]
    return x / (np.abs(x).max() + 1e-12) * 10 ** (PEAK_DB / 20)


def loudest(x, window=0.010):
    """Start of the loudest 10 ms window, in seconds (energy across both channels)."""
    e = (x ** 2).sum(axis=1)
    w = int(window * SR)
    c = np.convolve(e, np.ones(w), mode='valid')
    return round(int(np.argmax(c)) / SR, 4)


def write(path, x):
    pcm = (np.clip(x, -1, 1) * 32767).astype('<i2')
    with wave.open(path, 'wb') as f:
        f.setnchannels(2)
        f.setsampwidth(2)
        f.setframerate(SR)
        f.writeframes(pcm.tobytes())


def main():
    os.makedirs(OUT, exist_ok=True)
    peaks = {}
    for name, make in SOUNDS.items():
        x = finish(make())
        rel = 'sounds/sfx/%s.wav' % name
        write(os.path.join(ROOT, rel), x)
        peaks[rel] = loudest(x)
        print('make_sounds: %-28s %.2fs, loudest at %.3fs' % (rel, len(x) / SR, peaks[rel]))
    json.dump(peaks, open(os.path.join(OUT, 'peaks.json'), 'w'), indent=1)
    if '--wire' in sys.argv:
        p = os.path.join(ROOT, 'sounds.json')
        roles = json.load(open(p))
        for role, name in ROLES.items():
            roles[role] = 'sounds/sfx/%s.wav' % name
        json.dump(roles, open(p, 'w'), indent=2)
        print('make_sounds: sounds.json now places whoosh, land and click on every reel')


if __name__ == '__main__':
    main()

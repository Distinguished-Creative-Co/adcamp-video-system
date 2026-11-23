#!/usr/bin/env python3
"""A clip whose FIRST audio track can't be decoded must still build (newer iPhones, spatial audio).

    python3 scripts/test_audio_tracks.py

Newer iPhones record spatial audio (APAC, 5 channels, no ffmpeg decoder) as the first audio track and a plain stereo
AAC copy after it. Taking the first track, or ffmpeg's own pick (the most channels), stopped AVS at its first step:
"Decoding requested, but no decoder found for: apple_apac".

Builds small clips in a temp folder, no footage needed. The spatial-audio one is a two-track MOV whose first track's
sample entry is rewritten to 'apac', so ffmpeg reads it exactly as it reads an iPhone's (apple_apac, no decoder).
Checks: normalize_source.audio_stream() picks the AAC track (and AAC over a decodable PCM track before it), the
normalize step runs on the spatial clip and writes one AAC track with sound in it, a clip with ONLY the undecodable
track is refused with a plain message, and the transcriber's speech_input() hands the speech libraries a one-track
WAV of the AAC track.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import normalize_source  # noqa: E402
import word_align_x  # noqa: E402  (the speech libraries load only when a transcript is made)

FAILS = []


def check(ok, what):
    print('%s  %s' % ('ok  ' if ok else 'FAIL', what))
    if not ok:
        FAILS.append(what)


def ff(*args):
    subprocess.run(['ffmpeg', '-v', 'error', '-nostdin', '-y'] + list(args), check=True)


def streams(path):
    return normalize_source.probe(path)['streams']


def loudness(path):
    t = subprocess.run(['ffmpeg', '-hide_banner', '-nostdin', '-i', path, '-map', '0:a:0', '-af', 'volumedetect', '-f', 'null', '-'],
                       capture_output=True, text=True).stderr
    m = re.search(r'mean_volume: (-?[\d.]+) dB', t)
    return float(m.group(1)) if m else -99.0


def make(tmp):
    """two.mov: video, PCM (first audio), AAC stereo (second). apac.mov: the same with the PCM entry renamed to apac.
    only-apac.mov: video plus the undecodable track alone."""
    v = ['-f', 'lavfi', '-i', 'color=c=gray:s=360x640:r=30:d=3']
    a1 = ['-f', 'lavfi', '-i', 'sine=f=440:d=3:r=48000']
    a2 = ['-f', 'lavfi', '-i', 'sine=f=880:d=3:r=48000']
    two = os.path.join(tmp, 'two.mov')
    ff(*(v + a1 + a2 + ['-map', '0:v', '-map', '1:a', '-map', '2:a', '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
                        '-c:a:0', 'pcm_s16le', '-c:a:1', 'aac', '-ac', '2', two]))
    one = os.path.join(tmp, 'one.mov')
    ff(*(v + a1 + ['-map', '0:v', '-map', '1:a', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'pcm_s16le', '-ac', '2', one]))
    out = {'two': two}
    for name, src in (('apac', two), ('only-apac', one)):
        d = open(src, 'rb').read()
        if d.count(b'sowt') != 1:   # the PCM track's sample entry: exactly one, or the rewrite would be a guess
            sys.exit('test_audio_tracks: this ffmpeg wrote %d sowt entries in %s, expected 1' % (d.count(b'sowt'), src))
        out[name] = os.path.join(tmp, name + '.mov')
        open(out[name], 'wb').write(d.replace(b'sowt', b'apac'))
    return out


def main():
    tmp = tempfile.mkdtemp(prefix='avs-audio-')
    try:
        clips = make(tmp)
        sp = streams(clips['apac'])
        first = next(s for s in sp if s.get('codec_type') == 'audio')
        print('spatial-audio stand-in: ' + ', '.join('%d %s/%s' % (s['index'], s.get('codec_type'), s.get('codec_name')) for s in sp))
        check(first.get('codec_tag_string') == 'apac' and not normalize_source._decodes(clips['apac'], first['index']),
              'the stand-in clip\'s first audio track is apac and ffmpeg cannot decode it (as on an iPhone)')

        check(normalize_source.audio_stream(clips['apac']) == 2, 'audio_stream picks the AAC track (2) past the apac one')
        check(normalize_source.audio_stream(clips['two']) == 2, 'audio_stream prefers AAC (2) over a decodable PCM track before it')
        check(normalize_source.audio_stream(clips['only-apac']) is None, 'audio_stream finds nothing in a clip with only apac')

        out = os.path.join(tmp, 'norm.mp4')
        p = subprocess.run([sys.executable, os.path.join(HERE, 'normalize_source.py'), clips['apac'], out, '--no-record'],
                           capture_output=True, text=True)
        check(p.returncode == 0, 'normalize runs on the spatial-audio clip%s' % ('' if p.returncode == 0 else ': ' + (p.stderr or p.stdout)[-300:]))
        if p.returncode == 0:
            auds = [s for s in streams(out) if s.get('codec_type') == 'audio']
            check(len(auds) == 1 and auds[0].get('codec_name') == 'aac' and auds[0].get('channels') == 2,
                  'the normalized file has one stereo AAC track (%s)' % json.dumps([(s.get('codec_name'), s.get('channels')) for s in auds]))
            lv = loudness(out)
            check(lv > -40, 'the normalized track has sound in it (mean %.1f dB)' % lv)

        p = subprocess.run([sys.executable, os.path.join(HERE, 'normalize_source.py'), clips['only-apac'], os.path.join(tmp, 'none.mp4'), '--no-record'],
                           capture_output=True, text=True)
        check(p.returncode != 0 and 'no usable audio stream' in (p.stderr + p.stdout) and 'Traceback' not in p.stderr,
              'a clip with only the undecodable track is refused with a plain message')

        wav, wtmp = word_align_x.speech_input(clips['apac'])
        try:
            ws = streams(wav)
            check(wtmp is not None and len(ws) == 1 and ws[0].get('codec_type') == 'audio' and ws[0].get('sample_rate') == '16000'
                  and ws[0].get('channels') == 1, 'the transcriber reads a one-track 16 kHz mono WAV of the spatial clip')
            check(loudness(wav) > -40, 'that WAV has the AAC track\'s sound in it')
        finally:
            if wtmp:
                shutil.rmtree(wtmp, ignore_errors=True)
        same, none = word_align_x.speech_input(out) if os.path.exists(out) else (None, 'x')
        check(same == out and none is None, 'a one-track file goes to the transcriber as is (no extra copy)')
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    if FAILS:
        print('FAIL: %d check%s failed' % (len(FAILS), '' if len(FAILS) == 1 else 's'))
        sys.exit(1)
    print('PASS: a clip whose first audio track cannot be decoded builds from its AAC track')


if __name__ == '__main__':
    if '--help' in sys.argv[1:] or sys.argv[1:2] == ['-h']:
        print(__doc__.strip())
        sys.exit(0)
    main()

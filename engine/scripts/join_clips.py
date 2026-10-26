#!/usr/bin/env python3
"""Several clips in, one recording out: for members who film a video as a few separate clips.

    python3 scripts/join_clips.py <files or a folder> --list [--gap 600]
    python3 scripts/join_clips.py <files or a folder> --out <joined.mp4> [--video 1] [--gap 600] [--unmirror]

--list prints the clips in the order they were recorded, as a table: when, how long, and which video each one
belongs to. A gap of more than --gap seconds (10 minutes) between one clip ending and the next starting means a
new video, so a batch from two filming sessions splits by itself. Show the table and confirm before cutting.
--out joins one video's clips (--video N, default 1): each normalized like a single recording (1080x1920,
30 fps, one audio track), with 0.6 s of held picture and silence between clips so every join is a clean pause
the cutter can use. Then make the reel from the joined file. Landscape clips are refused, as everywhere.
Writes <joined>.clips.json (each clip's file and where it starts in the joined file).
"""
import datetime
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
VIDEO = ('.mov', '.mp4', '.m4v')
PAD = 0.6


def probe(path):
    d = json.loads(subprocess.run(['ffprobe', '-v', 'error', '-print_format', 'json', '-show_streams', '-show_format', path],
                                  capture_output=True, text=True).stdout or '{}')
    v = next((s for s in d.get('streams', []) if s.get('codec_type') == 'video'), None)
    if not v:
        return None
    w, h = v.get('width', 0), v.get('height', 0)
    rot = 0
    for sd in v.get('side_data_list') or []:
        rot = int(sd.get('rotation', 0) or 0)
    rot = int((v.get('tags') or {}).get('rotate', rot) or 0)
    if abs(rot) % 180 == 90:
        w, h = h, w
    tags = dict((d.get('format') or {}).get('tags') or {}, **(v.get('tags') or {}))
    when = tags.get('com.apple.quicktime.creationdate') or tags.get('creation_time')
    try:
        t = datetime.datetime.fromisoformat(when.replace('Z', '+00:00')).timestamp() if when else None
    except ValueError:
        t = None
    dur = float((d.get('format') or {}).get('duration') or 0)
    if t is None:   # no recorded time in the file: the file's own time, which is when it finished saving
        t = os.path.getmtime(path) - dur
    return {'file': path, 'start': t, 'length': dur, 'vertical': h > w, 'size': '%dx%d' % (w, h)}


def gather(items):
    files = []
    for it in items:
        it = os.path.expanduser(it)
        if os.path.isdir(it):
            files += [os.path.join(it, f) for f in sorted(os.listdir(it)) if f.lower().endswith(VIDEO) and 'joined' not in f.lower()]
        elif it.lower().endswith(VIDEO):
            files.append(it)
    clips = [c for c in (probe(f) for f in files) if c]
    clips.sort(key=lambda c: c['start'])
    return clips


def group(clips, gap):
    n, prev_end = 0, None
    for c in clips:
        if prev_end is None or c['start'] - prev_end > gap:
            n += 1
        c['video'] = n
        prev_end = c['start'] + c['length']
    return clips


def main():
    a = sys.argv[1:]
    flags = ('--gap', '--out', '--video')
    items = [x for i, x in enumerate(a) if not x.startswith('--') and (i == 0 or a[i - 1] not in flags)]
    if not items or ('--list' not in a and '--out' not in a):
        sys.exit(__doc__)
    gap = float(a[a.index('--gap') + 1]) if '--gap' in a else 600
    clips = group(gather(items), gap)
    if not clips:
        sys.exit('join_clips: no video files found')
    if '--list' in a:
        print('| # | clip | recorded | length | video | note |')
        print('|---|---|---|---|---|---|')
        for i, c in enumerate(clips, 1):
            print('| %d | %s | %s | %.1fs | %d | %s |' % (i, os.path.basename(c['file']), datetime.datetime.fromtimestamp(c['start']).strftime('%b %d %-I:%M:%S %p'),
                                                     c['length'], c['video'], '' if c['vertical'] else 'LANDSCAPE: not usable, film vertical'))
        n = max(c['video'] for c in clips)
        print('%d clip%s, %d video%s (a new video after a gap of more than %d minutes).' % (len(clips), '' if len(clips) == 1 else 's', n, '' if n == 1 else 's', gap // 60))
        return
    want = int(a[a.index('--video') + 1]) if '--video' in a else 1
    use = [c for c in clips if c['video'] == want]
    if not use:
        sys.exit('join_clips: there is no video %d' % want)
    bad = [os.path.basename(c['file']) for c in use if not c['vertical']]
    if bad:
        sys.exit('join_clips: landscape clips are not supported: %s' % ', '.join(bad))
    out = os.path.abspath(a[a.index('--out') + 1])
    tmp = tempfile.mkdtemp()
    try:
        norm = []
        for i, c in enumerate(use):
            dst = os.path.join(tmp, 'c%02d.mp4' % i)
            cmd = [sys.executable, os.path.join(HERE, 'normalize_source.py'), c['file'], dst, '--no-record'] + (['--unmirror'] if '--unmirror' in a else [])
            p = subprocess.run(cmd, capture_output=True, text=True)
            if p.returncode != 0:
                sys.exit('join_clips: could not prepare %s: %s' % (os.path.basename(c['file']), (p.stderr or p.stdout)[-300:]))
            norm.append(dst)
        ins, parts = [], []
        for i, f in enumerate(norm):
            ins += ['-i', f]
            last = i == len(norm) - 1
            v = '[%d:v]tpad=stop_mode=clone:stop_duration=%.2f[v%d]' % (i, 0 if last else PAD, i)
            au = '[%d:a]apad=pad_dur=%.2f[a%d]' % (i, 0 if last else PAD, i)
            parts += [v, au]
        graph = ';'.join(parts) + ';' + ''.join('[v%d][a%d]' % (i, i) for i in range(len(norm))) + 'concat=n=%d:v=1:a=1[v][a]' % len(norm)
        subprocess.run(['ffmpeg', '-v', 'error', '-y'] + ins + ['-filter_complex', graph, '-map', '[v]', '-map', '[a]', '-r', '30',
                        '-c:v', 'libx264', '-crf', '16', '-preset', 'medium', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k',
                        '-movflags', '+faststart', out], check=True)
        at, rec = 0.0, []
        for c, f in zip(use, norm):
            dur = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', f], capture_output=True, text=True).stdout)
            rec.append({'clip': c['file'], 'starts_at': round(at, 3), 'length': round(dur, 3)})
            at += dur + PAD
        json.dump(rec, open(out + '.clips.json', 'w'), indent=1)
        print('join_clips: %d clips -> %s (%.1fs)' % (len(use), out, at - PAD))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == '__main__':
    main()

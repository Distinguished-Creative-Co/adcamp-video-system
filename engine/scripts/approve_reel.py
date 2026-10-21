#!/usr/bin/env python3
"""Record a HUMAN's approval of a scene map. The render refuses without a fresh one.

    python3 scripts/approve_reel.py <name> --by "<reviewer>"
    python3 scripts/approve_reel.py <name> --check        (exit 0 only if approval is current)

The approval binds the exact config, scene map, cut, and engine files by hash, so any
later edit to one of them invalidates it. An operating agent NEVER runs this on the
human's behalf: it is the human's signature that they read the map.
"""
import datetime
import glob
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import reel_config  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def bound_files(name):
    files = [os.path.join('src', 'methodology', 'reels', '%s.config.ts' % name),
             os.path.join('script', '%s-scene-map.md' % name),
             os.path.join('public', reel_config.load(name)['src'])]
    files.append('sounds.json')
    files += sorted(glob.glob(os.path.join('src', 'methodology', '*.ts*')))
    files += sorted(glob.glob(os.path.join('src', 'components', '**', '*.ts*'), recursive=True))
    return [f for f in files if '/reels/' not in f or f.endswith('%s.config.ts' % name)]


def digest(name):
    out = {}
    for rel in bound_files(name):
        p = os.path.join(ROOT, rel)
        h = hashlib.sha256()
        if rel.endswith('Root.tsx'):
            # other reels' one-line registrations must not stale this reel's approval
            data = b''.join(l for l in open(p, 'rb').read().splitlines(True)
                            if b'<Reel id=' not in l or ('<Reel id="%s"' % name).encode() in l)
            h.update(data)
        else:
            with open(p, 'rb') as f:
                for chunk in iter(lambda: f.read(1 << 20), b''):
                    h.update(chunk)
        out[rel] = h.hexdigest()
    return out


def main():
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    name = a[0]
    path = os.path.join(ROOT, 'script', '%s.approved' % name)
    if '--check' in a:
        if not os.path.exists(path):
            sys.exit('NOT APPROVED: %s has no approval. Read script/%s-scene-map.md, then run approve_reel.py.' % (name, name))
        rec = json.load(open(path))
        now = digest(name)
        changed = sorted(k for k in set(now) | set(rec['files']) if now.get(k) != rec['files'].get(k))
        if changed:
            sys.exit('APPROVAL STALE for %s: changed since approval: %s' % (name, ', '.join(changed)))
        print('approval current: %s, by %s at %s' % (name, rec['by'], rec['at']))
        return
    if '--by' not in a:
        sys.exit('approve_reel.py <name> --by "<reviewer>"')
    by = a[a.index('--by') + 1].strip()
    if not by:
        sys.exit('--by needs the reviewer\'s name')
    rec = {'name': name, 'by': by, 'at': datetime.datetime.now().isoformat(timespec='seconds'), 'files': digest(name)}
    json.dump(rec, open(path, 'w'), indent=1)
    print('approved %s by %s (%d files bound)' % (name, by, len(rec['files'])))


if __name__ == '__main__':
    main()

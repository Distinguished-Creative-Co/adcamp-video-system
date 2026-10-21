#!/usr/bin/env python3
"""Serve a reel's storyboard on this computer and save the notes left on it.

    python3 scripts/review_server.py <name> [--port 8770]

Open the address it prints. Notes from the page land in qa/<name>/storyboard/notes.json as a list of
{"beat": "b03" or "all", "text": ..., "at": time}; "all" + "go" means the person pressed "Looks good,
render it". Each save replaces the previous notes for the same beats and keeps the rest. Standard
library only. Ctrl+C stops it.
"""
import datetime
import http.server
import json
import os
import sys
import threading

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    skip = {i + 1 for i, a in enumerate(sys.argv) if a == '--port'}
    args = [a for i, a in enumerate(sys.argv) if i and i not in skip and not a.startswith('--')]
    if len(args) != 1:
        sys.exit(__doc__)
    folder = os.path.join(ROOT, 'qa', args[0], 'storyboard')
    if not os.path.exists(os.path.join(folder, 'index.html')):
        sys.exit('review_server: no storyboard yet. Run python3 scripts/storyboard.py %s first.' % args[0])
    port = int(sys.argv[sys.argv.index('--port') + 1]) if '--port' in sys.argv else 8770
    notes_path = os.path.join(folder, 'notes.json')
    lock = threading.Lock()

    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=folder, **kw)

        def log_message(self, *a):
            pass

        def do_POST(self):
            if self.path.rstrip('/') != '/notes':
                self.send_error(404)
                return
            try:
                incoming = json.loads(self.rfile.read(int(self.headers.get('Content-Length', 0))) or b'[]')
                assert isinstance(incoming, list)
            except (ValueError, AssertionError):
                self.send_error(400)
                return
            now = datetime.datetime.now().isoformat(timespec='seconds')
            with lock:
                try:
                    kept = json.load(open(notes_path))
                except (OSError, ValueError):
                    kept = []
                beats = {str(n.get('beat')) for n in incoming}
                kept = [n for n in kept if n.get('beat') not in beats]
                kept += [{'beat': str(n.get('beat'))[:8], 'text': str(n.get('text'))[:2000], 'at': now} for n in incoming if n.get('text')]
                json.dump(kept, open(notes_path, 'w'), indent=1)
            for n in incoming:
                print('note %s: %s' % (n.get('beat'), n.get('text')), flush=True)
            self.send_response(204)
            self.end_headers()

    srv = http.server.ThreadingHTTPServer(('127.0.0.1', port), Handler)
    print('storyboard for %s: http://127.0.0.1:%d  (notes -> %s, Ctrl+C to stop)' % (args[0], port, os.path.relpath(notes_path, ROOT)), flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()

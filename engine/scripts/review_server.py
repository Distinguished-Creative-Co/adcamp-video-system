#!/usr/bin/env python3
"""Serve a reel's storyboard on this computer and save the notes left on it.

    python3 scripts/review_server.py <name> [--port 8770] [--until-done]

Open the address it prints. Notes from the page land in qa/<name>/storyboard/notes.json as a list of
{"beat": "b03" or "all", "text": ..., "at": time}; "all" + "go" means the person pressed "Done".
Each save replaces the notes for the beats it sends (an empty text clears one) and keeps the rest. Standard
library only. Ctrl+C stops it. --until-done prints "STORYBOARD DONE <n> notes" and stops once they press Done
(or after an hour without a visit: "STORYBOARD CLOSED"), so Claude, running it in the background, hears when
they have finished.
"""
import datetime
import http.server
import json
import os
import socket
import sys
import threading
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import adcamp_page  # noqa: E402


def main():
    skip = {i + 1 for i, a in enumerate(sys.argv) if a == '--port'}
    args = [a for i, a in enumerate(sys.argv) if i and i not in skip and not a.startswith('--')]
    if len(args) != 1:
        sys.exit(__doc__)
    folder = os.path.join(ROOT, 'qa', args[0], 'storyboard')
    if not os.path.exists(os.path.join(folder, 'index.html')):
        sys.exit('review_server: no storyboard yet. Run python3 scripts/storyboard.py %s first.' % args[0])
    port = int(sys.argv[sys.argv.index('--port') + 1]) if '--port' in sys.argv else 8770
    for p in range(port, port + 20):   # another storyboard (or anything) on the port: take the next free one
        with socket.socket() as sk:
            try:
                sk.bind(('127.0.0.1', p))
                port = p
                break
            except OSError:
                continue
    notes_path = os.path.join(folder, 'notes.json')
    lock = threading.Lock()
    until_done = '--until-done' in sys.argv
    stop, last = threading.Event(), {'t': time.time()}

    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=folder, **kw)

        def log_message(self, *a):
            pass

        def do_GET(self):
            if not adcamp_page.local_host_ok(self):
                self.send_error(403)
                return
            last['t'] = time.time()
            super().do_GET()

        def do_POST(self):
            if self.path.rstrip('/') != '/notes':
                self.send_error(404)
                return
            if not adcamp_page.local_post_ok(self):   # only the storyboard itself, never another website in the same browser
                self.send_error(403)
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
                had = {n.get('beat') for n in kept}
                kept = [n for n in kept if n.get('beat') not in beats]
                # an empty box clears that beat's note
                kept += [{'beat': str(n.get('beat'))[:8], 'text': str(n.get('text'))[:2000], 'at': now} for n in incoming if n.get('text')]
                json.dump(kept, open(notes_path, 'w'), indent=1)
            last['t'] = time.time()
            for n in incoming:
                if n.get('text'):
                    print('note %s: %s' % (n.get('beat'), n.get('text')), flush=True)
                elif str(n.get('beat')) in had:
                    print('note %s: cleared' % n.get('beat'), flush=True)
            self.send_response(204)
            self.end_headers()
            if until_done and any(str(n.get('beat')) == 'all' and n.get('text') == 'go' for n in incoming):
                print('STORYBOARD DONE %d notes' % sum(1 for n in kept if n.get('beat') != 'all'), flush=True)
                threading.Timer(1.5, stop.set).start()

    srv = http.server.ThreadingHTTPServer(('127.0.0.1', port), Handler)
    print('storyboard for %s: http://127.0.0.1:%d  (notes -> %s, Ctrl+C to stop)' % (args[0], port, os.path.relpath(notes_path, ROOT)), flush=True)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        while not stop.wait(5):
            if until_done and time.time() - last['t'] > 3600:
                print('STORYBOARD CLOSED (no visit for an hour)', flush=True)
                break
    except KeyboardInterrupt:
        pass
    srv.shutdown()


if __name__ == '__main__':
    main()

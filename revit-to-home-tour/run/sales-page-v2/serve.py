"""Serve this folder on http://localhost:8137 for a local preview.

Python's built-in server cannot answer byte-range requests, and browsers need
those to loop and scrub video. This adds just that.

    python serve.py
"""
import os
import re
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler
from socketserver import ThreadingMixIn

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8137
RANGE = re.compile(r'bytes=(\d*)-(\d*)$')


class Handler(SimpleHTTPRequestHandler):
    def send_head(self):
        match = RANGE.match(self.headers.get('Range', ''))
        path = self.translate_path(self.path)
        if not match or not os.path.isfile(path):
            return SimpleHTTPRequestHandler.send_head(self)
        size = os.path.getsize(path)
        first, last = match.groups()
        if first == '':
            start, end = max(0, size - int(last or 0)), size - 1
        else:
            start, end = int(first), min(int(last), size - 1) if last else size - 1
        if start > end or start >= size:
            self.send_error(416, 'Requested range not satisfiable')
            return None
        handle = open(path, 'rb')
        handle.seek(start)
        self.range_left = end - start + 1
        self.send_response(206)
        self.send_header('Content-Type', self.guess_type(path))
        self.send_header('Content-Range', 'bytes %d-%d/%d' % (start, end, size))
        self.send_header('Content-Length', str(self.range_left))
        self.end_headers()
        return handle

    def end_headers(self):
        self.send_header('Accept-Ranges', 'bytes')
        SimpleHTTPRequestHandler.end_headers(self)

    def copyfile(self, source, outputfile):
        left = getattr(self, 'range_left', None)
        if left is None:
            return SimpleHTTPRequestHandler.copyfile(self, source, outputfile)
        self.range_left = None
        while left > 0:
            chunk = source.read(min(65536, left))
            if not chunk:
                break
            outputfile.write(chunk)
            left -= len(chunk)

    def log_message(self, *args):
        pass


class Server(ThreadingMixIn, HTTPServer):
    daemon_threads = True


if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    print('Snowdon Towers tour: http://localhost:%d  (Ctrl+C to stop)' % PORT)
    try:
        Server(('127.0.0.1', PORT), Handler).serve_forever()
    except KeyboardInterrupt:
        pass

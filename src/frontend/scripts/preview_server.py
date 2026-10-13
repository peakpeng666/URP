"""Local-only reference console; independent from the product frontend's stack."""
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit, unquote
import argparse

ROOT = Path(__file__).resolve().parents[1]

class Handler(SimpleHTTPRequestHandler):
    def translate_path(self, path):
        route = unquote(urlsplit(path).path)
        if route.startswith('/data/'):
            base, relative = ROOT / 'public/data', route[6:]
        elif route.startswith('/core/'):
            base, relative = ROOT / 'core', route[6:]
        else:
            base, relative = ROOT / 'preview', route.lstrip('/') or 'index.html'
        resolved = (base / relative).resolve()
        if resolved != base.resolve() and base.resolve() not in resolved.parents:
            return str(base / '_forbidden_')
        return str(resolved)

    def end_headers(self):
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('X-Content-Type-Options', 'nosniff')
        super().end_headers()

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--port', type=int, default=4174)
    args = p.parse_args()
    print(f'BPP reference console http://localhost:{args.port}', flush=True)
    ThreadingHTTPServer(('127.0.0.1', args.port), Handler).serve_forever()

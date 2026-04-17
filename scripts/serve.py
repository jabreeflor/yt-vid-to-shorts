#!/usr/bin/env python3
"""Serve the rendered gallery over localhost and open it in the default browser.

Using http:// instead of file:// avoids Chrome's stricter local-file policies,
which in practice break <video> playback (silent audio, frozen frame, weird
layout) when gallery.html is opened by double-clicking.

Usage:
    python serve.py <workdir> [--port 8723] [--no-open]
"""
import argparse
import http.server
import socketserver
import sys
import webbrowser
from pathlib import Path


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("workdir")
    parser.add_argument("--port", type=int, default=8723)
    parser.add_argument("--no-open", action="store_true")
    args = parser.parse_args()

    workdir = Path(args.workdir).resolve()
    gallery = workdir / "gallery.html"
    if not gallery.exists():
        print(f"serve: {gallery} not found. Run render_gallery.py first.", file=sys.stderr)
        sys.exit(1)

    handler = lambda *a, **kw: QuietHandler(*a, directory=str(workdir), **kw)

    with socketserver.TCPServer(("127.0.0.1", args.port), handler) as httpd:
        url = f"http://127.0.0.1:{args.port}/gallery.html"
        print(f"[serve] {url}")
        print("[serve] Ctrl+C to stop")
        if not args.no_open:
            webbrowser.open(url)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n[serve] stopped")


if __name__ == "__main__":
    main()

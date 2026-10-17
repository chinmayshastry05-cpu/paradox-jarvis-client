"""Capture REAL screenshots of the built UI in headless Chromium.

Serves the Vite build output (frontend/dist) on a local port, loads the
app in headless Chromium, and screenshots three views: chat ("/"),
system control ("/system-control"), and settings ("/settings").

Usage:
  python3 screenshot.py <dist-dir> <out-dir>

Requires: a Chromium/Chrome binary on PATH (chromium, chromium-browser,
google-chrome) and Python 3. No screenshots are fabricated — if the
server or browser fails, the script exits non-zero.
"""
import http.server
import os
import shutil
import socketserver
import subprocess
import sys
import threading
import time
import urllib.request

VIEWS = [
    ("chat", "/"),
    ("system-control", "/system-control"),
    ("settings", "/settings"),
]


def find_chromium():
    for name in ("chromium", "chromium-browser", "google-chrome", "google-chrome-stable"):
        path = shutil.which(name)
        if path:
            return path
    # Playwright's Chrome for Testing (writes --screenshot files; the
    # meta-chromium binary does not).
    import glob as _glob

    for path in sorted(_glob.glob(
        os.path.expanduser("~/.cache/ms-playwright/chromium-*/chrome-linux64/chrome")
    )):
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path
    for path in ("/opt/meta-chromium/chrome",):
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path
    return None


def wait_for_server(port, timeout=30):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=3) as r:
                if r.status == 200:
                    return True
        except Exception:
            time.sleep(0.5)
    return False


def main():
    dist_dir = sys.argv[1]
    out_dir = sys.argv[2]
    if not os.path.isdir(dist_dir):
        print(f"dist/ not found at {dist_dir}; run npm run build first", file=sys.stderr)
        raise SystemExit(1)
    chromium = find_chromium()
    if not chromium:
        print("no Chromium/Chrome binary found on PATH", file=sys.stderr)
        raise SystemExit(1)
    os.makedirs(out_dir, exist_ok=True)

    # Serve dist/ (SPA fallback to index.html).
    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=dist_dir, **kw)

        def do_GET(self):
            if not os.path.exists(os.path.join(dist_dir, self.path.lstrip("/").split("?")[0])):
                self.path = "/index.html"
            super().do_GET()

        def log_message(self, *a):
            pass

    httpd = socketserver.TCPServer(("127.0.0.1", 0), Handler)
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        if not wait_for_server(port):
            print("dev server did not come up", file=sys.stderr)
            raise SystemExit(1)
        for name, route in VIEWS:
            out = os.path.join(out_dir, f"ui-{name}.png")
            # --virtual-time-budget lets the SPA render + settle before capture.
            cmd = [
                chromium,
                "--headless=new",
                "--disable-gpu",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--hide-scrollbars",
                "--window-size=1440,900",
                "--virtual-time-budget=5000",
                f"--screenshot={out}",
                f"http://127.0.0.1:{port}{route}",
            ]
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=240)
            if r.returncode != 0 or not os.path.exists(out):
                print(f"screenshot failed for {route}: {r.stderr[:500]}", file=sys.stderr)
                raise SystemExit(1)
            print(f"wrote {out} ({os.path.getsize(out)} bytes)")
    finally:
        httpd.shutdown()


if __name__ == "__main__":
    main()

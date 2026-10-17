"""Capture REAL screenshots of the built UI via Playwright (reliable lifecycle).

Serves the Vite build output (src/openjarvis/server/static) on a local
port, loads the app in headless Chromium, and screenshots three views:
chat ("/"), system control ("/system-control"), settings ("/settings").

Usage:
  python3 screenshot_pw.py <dist-dir> <out-dir>

Requires: playwright + its bundled Chromium. No screenshots are
fabricated — if the server or browser fails, the script exits non-zero.
"""
import http.server
import os
import socketserver
import sys
import threading
import time
import urllib.request

from playwright.sync_api import sync_playwright

VIEWS = [
    ("chat", "/"),
    ("system-control", "/system-control"),
    ("settings", "/settings"),
]


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
    if not os.path.isfile(os.path.join(dist_dir, "index.html")):
        print(f"index.html not found in {dist_dir}; run npm run build first", file=sys.stderr)
        raise SystemExit(1)
    os.makedirs(out_dir, exist_ok=True)

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
        with sync_playwright() as p:
            browser = p.chromium.launch(args=["--no-sandbox", "--disable-dev-shm-usage"])
            try:
                # Pre-seed localStorage so the first-run analytics opt-in
                # modal never appears (clicking it cannot dismiss it when
                # the backend is down — the save fails and it stays open).
                context = browser.new_context(viewport={"width": 1440, "height": 900})
                context.add_init_script(
                    "localStorage.setItem('openjarvis-optin-seen', 'true');"
                    "localStorage.setItem('openjarvis-analytics-choice-seen', 'true');"
                )
                page = context.new_page()
                try:
                    for name, route in VIEWS:
                        page.goto(f"http://127.0.0.1:{port}{route}",
                                  wait_until="networkidle", timeout=30000)
                        page.wait_for_timeout(1500)
                        out = os.path.join(out_dir, f"ui-{name}.png")
                        page.screenshot(path=out)
                        print(f"wrote {out} ({os.path.getsize(out)} bytes)")
                finally:
                    page.close()
            finally:
                browser.close()
    finally:
        httpd.shutdown()


if __name__ == "__main__":
    main()

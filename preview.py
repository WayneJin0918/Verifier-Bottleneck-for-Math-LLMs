#!/usr/bin/env python3
"""Rebuild the note when a source file changes, and serve it.

Edit src/stu.md or css/blog.css, then refresh. This server reloads the
page on its own. The injected reload script is not written into index.html.
"""

from __future__ import annotations

import subprocess
import threading
import time
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PORT = 8891
WATCH = (
    ROOT / "src" / "stu.md",
    ROOT / "css" / "blog.css",
    ROOT / "js" / "math.js",
    ROOT / "js" / "ui.js",
    ROOT / "build_site.py",
)
RELOAD = """
<script>
(function () {
  var seen = "";
  function tick() {
    fetch("/__stamp", { cache: "no-store" })
      .then(function (response) { return response.text(); })
      .then(function (stamp) {
        if (seen && stamp !== seen) location.reload();
        seen = stamp;
      })
      .catch(function () {});
  }
  setInterval(tick, 700);
})();
</script>
"""


def build() -> None:
    subprocess.run(["python3", str(ROOT / "build_site.py")], cwd=ROOT, check=False)


def watch() -> None:
    seen = {path: path.stat().st_mtime if path.exists() else 0 for path in WATCH}
    while True:
        time.sleep(0.4)
        changed = False
        for path in WATCH:
            stamp = path.stat().st_mtime if path.exists() else 0
            if stamp != seen[path]:
                seen[path] = stamp
                changed = True
        if changed:
            build()


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_GET(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0]
        if path == "/__stamp":
            index = ROOT / "index.html"
            body = str(index.stat().st_mtime if index.exists() else 0).encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if path in ("/", "/index.html"):
            page = (ROOT / "index.html").read_text(encoding="utf-8")
            page = page.replace("</body>", RELOAD + "</body>", 1)
            data = page.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        super().do_GET()


def main() -> None:
    build()
    threading.Thread(target=watch, daemon=True).start()
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"http://127.0.0.1:{PORT}/", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()

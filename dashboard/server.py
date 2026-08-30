"""
UpLift dashboard backend — zero external dependencies.
Serves the reports/ JSON and a static HTML dashboard on http://localhost:7890
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent   # repo root
REPORTS = ROOT / "reports"
STATIC = Path(__file__).resolve().parent        # dashboard/


def _json(path: Path) -> object:
    with open(path) as f:
        return json.load(f)


def _run_tests() -> dict:
    """Run pytest and return a result dict (non-blocking, max 30 s)."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "--tb=no", "-q"],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
            timeout=30,
        )
        last_line = result.stdout.strip().splitlines()[-1] if result.stdout.strip() else ""
        return {
            "returncode": result.returncode,
            "summary": last_line,
            "passed": result.returncode == 0,
        }
    except Exception as exc:  # noqa: BLE001
        return {"returncode": -1, "summary": str(exc), "passed": False}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args: object) -> None:  # silence default log
        print(f"  {self.address_string()} {fmt % args}")

    def _send(self, status: int, content_type: str, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json_response(self, data: object, status: int = 200) -> None:
        body = json.dumps(data, indent=2).encode()
        self._send(status, "application/json", body)

    def do_GET(self) -> None:
        path = self.path.split("?")[0]

        if path in ("/", "/index.html"):
            html_file = STATIC / "index.html"
            self._send(200, "text/html; charset=utf-8", html_file.read_bytes())

        elif path == "/api/upgrade-report":
            self._json_response(_json(REPORTS / "upgrade-report.json"))

        elif path == "/api/breaking-changes":
            self._json_response(_json(REPORTS / "breaking-changes.json"))

        elif path == "/api/usage-map":
            self._json_response(_json(REPORTS / "usage-map.json"))

        elif path == "/api/upgrade-report-md":
            md = (ROOT / "UPGRADE_REPORT.md").read_text()
            self._json_response({"markdown": md})

        elif path == "/api/run-tests":
            self._json_response(_run_tests())

        else:
            self._json_response({"error": "not found"}, 404)


def main() -> None:
    port = int(os.environ.get("UPLIFT_DASHBOARD_PORT", 7890))
    server = HTTPServer(("localhost", port), Handler)
    print(f"\n  UpLift Dashboard  →  http://localhost:{port}\n  Ctrl-C to stop.\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Stopped.")


if __name__ == "__main__":
    main()

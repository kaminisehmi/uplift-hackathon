"""
UpLift dashboard backend — zero external dependencies.
Serves the reports/ JSON and a static HTML dashboard on http://localhost:7890
"""
from __future__ import annotations

import json
import re
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent   # repo root
REPORTS = ROOT / "reports"
STATIC = Path(__file__).resolve().parent        # dashboard/

# ── concurrency guard for /api/run-migration ──────────────────────────────
_migration_lock = threading.Lock()
_migration_running = False


def _json(path: Path) -> object:
    with open(path) as f:
        return json.load(f)


_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]")


def _run_tests() -> dict:
    """Run pytest and return a result dict (non-blocking, max 30 s)."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "--tb=no", "-q", "--color=no"],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
            timeout=30,
        )
        # Strip any ANSI colour codes so the dashboard shows plain text.
        clean = _ANSI_RE.sub("", result.stdout).strip()
        last_line = clean.splitlines()[-1] if clean else ""
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

        if path == "/cards.html":
            self._send(200, "text/html; charset=utf-8",
                       (STATIC / "cards.html").read_bytes())
            return

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
            report_md = ROOT / "UPGRADE_REPORT.md"
            md = report_md.read_text() if report_md.exists() else ""
            self._json_response({"markdown": md})

        elif path == "/api/run-tests":
            self._json_response(_run_tests())

        else:
            self._json_response({"error": "not found"}, 404)

    def do_POST(self) -> None:
        path = self.path.split("?")[0]

        if path == "/api/run-migration":
            self._handle_run_migration()
        else:
            self._json_response({"error": "not found"}, 404)

    def _handle_run_migration(self) -> None:
        """Stream `uplift upgrade pydantic --force` stdout to the client.

        Uses chunked transfer encoding so the browser receives each output line
        as it is emitted.  Guards against concurrent runs with a 409 response.
        """
        global _migration_running

        with _migration_lock:
            if _migration_running:
                self._json_response(
                    {"error": "A migration is already running. Please wait."},
                    status=409,
                )
                return
            _migration_running = True

        try:
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Transfer-Encoding", "chunked")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()

            cmd = [sys.executable, "-m", "uplift", "upgrade", "pydantic", "--force"]
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                cwd=str(ROOT),
                text=True,
                bufsize=1,
            )

            assert proc.stdout is not None  # always set when stdout=PIPE
            for line in proc.stdout:
                chunk = line.encode("utf-8")
                # chunked encoding: <hex-size>\r\n<data>\r\n
                self.wfile.write(f"{len(chunk):x}\r\n".encode())
                self.wfile.write(chunk)
                self.wfile.write(b"\r\n")
                self.wfile.flush()

            proc.wait()
            rc_line = f"[uplift] exit code {proc.returncode}\n".encode("utf-8")
            self.wfile.write(f"{len(rc_line):x}\r\n".encode())
            self.wfile.write(rc_line)
            self.wfile.write(b"\r\n")
            # chunked terminator
            self.wfile.write(b"0\r\n\r\n")
            self.wfile.flush()
        except Exception as exc:  # noqa: BLE001
            # Best-effort: if headers not yet sent this will fail silently
            try:
                err = f"[error] {exc}\n".encode("utf-8")
                self.wfile.write(f"{len(err):x}\r\n".encode())
                self.wfile.write(err)
                self.wfile.write(b"\r\n0\r\n\r\n")
                self.wfile.flush()
            except Exception:  # noqa: BLE001
                pass
        finally:
            with _migration_lock:
                _migration_running = False


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

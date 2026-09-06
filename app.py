"""Local server for the Career Evidence Compiler MVP."""

from __future__ import annotations

import json
import mimetypes
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from document_ingest import extract_base64_document, fetch_job_url
from engine import analyze_application, generate_package


ROOT = Path(__file__).resolve().parent
WEB = ROOT / "web"


class Handler(BaseHTTPRequestHandler):
    server_version = "CareerEvidenceCompiler/0.1"

    def do_GET(self) -> None:  # noqa: N802 - stdlib handler API
        path = urlparse(self.path).path
        if path == "/api/health":
            self._json({"ok": True, "name": "career-evidence-compiler"})
            return
        if path == "/" or path == "/index.html":
            self._file(WEB / "index.html")
            return
        if path.startswith("/web/"):
            self._file(WEB / path.removeprefix("/web/"))
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def do_POST(self) -> None:  # noqa: N802 - stdlib handler API
        path = urlparse(self.path).path
        if path not in {"/api/analyze", "/api/generate", "/api/fetch-job", "/api/parse-document"}:
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length) or b"{}")
            if path == "/api/fetch-job":
                result = fetch_job_url(payload.get("url", ""))
            elif path == "/api/parse-document":
                result = extract_base64_document(payload.get("filename", ""), payload.get("data", ""))
            elif path == "/api/analyze":
                result = analyze_application(
                    payload.get("profile", {}),
                    payload.get("narrative", ""),
                    payload.get("job_description", ""),
                    payload.get("resume_text", ""),
                )
            else:
                result = generate_package(
                    payload.get("profile", {}),
                    payload.get("narrative", ""),
                    payload.get("job_description", ""),
                    payload.get("analysis", {}),
                    payload.get("decisions", {}),
                )
            self._json(result)
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            self._json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
        except Exception as exc:  # keep local UI errors visible without a traceback page
            self._json({"error": f"Unexpected local error: {exc}"}, HTTPStatus.INTERNAL_SERVER_ERROR)

    def _file(self, path: Path) -> None:
        if not path.is_file() or path.parent.resolve() != WEB.resolve():
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        data = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _json(self, value: object, status: HTTPStatus = HTTPStatus.OK) -> None:
        data = json.dumps(value, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt: str, *args: object) -> None:
        print(f"[{self.log_date_time_string()}] {fmt % args}")


if __name__ == "__main__":
    address = ("127.0.0.1", int(os.environ.get("CEC_PORT", "8765")))
    print(f"Career Evidence Compiler listening at http://{address[0]}:{address[1]}")
    ThreadingHTTPServer(address, Handler).serve_forever()

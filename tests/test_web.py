"""Tests for the safe URL fetcher (a real local HTTP server is used, no internet needed)."""
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from agent import web
from agent.web import FetchError, safe_fetch


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/ok":
            body = json.dumps({"value": 42}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/redirect":
            self.send_response(302)
            self.send_header("Location", "http://example.com/")
            self.end_headers()
        elif self.path == "/slow":
            import time
            time.sleep(2)
            self.send_response(200)
            self.end_headers()
        else:
            self.send_response(503)
            self.end_headers()

    def log_message(self, *args):
        pass


@pytest.fixture()
def server(monkeypatch):
    srv = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    monkeypatch.setattr(web, "_check_url", lambda url: None)  # allow localhost only inside this test
    yield f"http://127.0.0.1:{srv.server_port}"
    srv.shutdown()


def test_fetch_ok(server):
    status, ctype, body = safe_fetch(server + "/ok")
    assert status == 200 and "json" in ctype
    assert json.loads(body) == {"value": 42}


def test_http_error_becomes_fetch_error(server):
    with pytest.raises(FetchError, match="503"):
        safe_fetch(server + "/boom")


def test_redirect_is_reported_not_followed(server):
    with pytest.raises(FetchError, match="redirected"):
        safe_fetch(server + "/redirect")


def test_timeout_is_reported(server):
    with pytest.raises(FetchError, match="timed out"):
        safe_fetch(server + "/slow", timeout=1)


@pytest.mark.parametrize("url", [
    "http://127.0.0.1/", "http://localhost:8000/", "http://10.0.0.5/", "http://192.168.1.1/",
    "http://169.254.169.254/latest/meta-data/", "file:///etc/passwd", "ftp://example.com/",
])
def test_non_public_or_non_http_urls_are_blocked(url):
    with pytest.raises(FetchError):
        safe_fetch(url)

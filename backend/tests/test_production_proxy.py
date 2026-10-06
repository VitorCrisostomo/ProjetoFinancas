"""Valida o proxy real com frontend e API fictícios, sem carregar dados da aplicação."""

import json
import os
import socket
import subprocess
import threading
import time
import unittest
from contextlib import closing
from http.client import HTTPConnection
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory


class ProbeHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = json.dumps(
            {
                "path": self.path,
                "headers": {
                    name: self.headers.get(name)
                    for name in (
                        "X-Forwarded-For",
                        "X-Forwarded-Host",
                        "X-Forwarded-Proto",
                        "Forwarded",
                        "X-Forwarded-Prefix",
                    )
                },
            }
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args):
        pass


@unittest.skipUnless(os.getenv("FINANCEHUB_TEST_CADDY"), "Defina FINANCEHUB_TEST_CADDY.")
class ProductionProxyTests(unittest.TestCase):
    hostname = "fixture.tailtest.ts.net"
    html = b"<!doctype html><title>production proxy fixture</title>"

    @classmethod
    def setUpClass(cls):
        temporary = TemporaryDirectory()
        cls.addClassCleanup(temporary.cleanup)
        root = Path(temporary.name)
        frontend = root / "frontend with spaces"
        (frontend / "assets").mkdir(parents=True)
        (frontend / "index.html").write_bytes(cls.html)
        (frontend / "assets/app-fixture.js").write_bytes(b"console.log('fixture');")
        backend = ThreadingHTTPServer(("127.0.0.1", 0), ProbeHandler)
        cls.addClassCleanup(backend.server_close)
        threading.Thread(target=backend.serve_forever, daemon=True).start()
        cls.addClassCleanup(backend.shutdown)
        with closing(socket.socket()) as listener:
            listener.bind(("127.0.0.1", 0))
            cls.port = listener.getsockname()[1]
        source = Path(__file__).resolve().parents[2] / "deploy/Caddyfile"
        configuration = source.read_text(encoding="utf-8").replace(":8080", f":{cls.port}")
        configuration = configuration.replace("127.0.0.1:8000", f"127.0.0.1:{backend.server_port}")
        config_path = root / "Caddyfile"
        config_path.write_text(configuration, encoding="utf-8")
        log = (root / "caddy.log").open("w", encoding="utf-8")
        cls.addClassCleanup(log.close)
        cls.process = subprocess.Popen(
            [os.environ["FINANCEHUB_TEST_CADDY"], "run", "--config", str(config_path)],
            env={**os.environ, "APP_HOST": cls.hostname, "FRONTEND_ROOT": frontend.as_posix()},
            stdout=log,
            stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        cls.addClassCleanup(cls.stop_proxy)
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if cls.process.poll() is not None:
                raise RuntimeError("Caddy encerrou antes de iniciar o proxy de teste.")
            try:
                if cls.request("/")[2] == cls.html:
                    return
            except OSError:
                pass
            time.sleep(0.05)
        raise RuntimeError("O proxy de teste não iniciou dentro do prazo.")

    @classmethod
    def stop_proxy(cls):
        cls.process.terminate()
        try:
            cls.process.wait(timeout=5)
        finally:
            if cls.process.poll() is None:
                cls.process.kill()
                cls.process.wait(timeout=5)

    @classmethod
    def request(cls, path, hostname=None, headers=None):
        with closing(HTTPConnection("127.0.0.1", cls.port, timeout=2)) as connection:
            connection.request(
                "GET", path, headers={"Host": hostname or cls.hostname, **(headers or {})}
            )
            response = connection.getresponse()
            return (
                response.status,
                {key.lower(): value for key, value in response.getheaders()},
                response.read(),
            )

    def test_untrusted_host_is_rejected_before_frontend_and_api(self):
        for path in ("/", "/transactions/2026/10", "/api/probe"):
            with self.subTest(path=path):
                status, _, body = self.request(path, hostname="untrusted.invalid")
                self.assertEqual(status, 421)
                self.assertNotEqual(body, self.html)

    def test_spa_reload_and_static_caching_preserve_security_headers(self):
        for path in ("/", "/transactions/2026/10"):
            with self.subTest(path=path):
                status, headers, body = self.request(path)
                self.assertEqual((status, body), (200, self.html))
                self.assertEqual(headers["cache-control"], "no-cache")
                self.assertEqual(headers["x-content-type-options"], "nosniff")
                self.assertEqual(headers["x-frame-options"], "DENY")
                self.assertEqual(headers["referrer-policy"], "no-referrer")
                self.assertIn("max-age=", headers["strict-transport-security"])
                self.assertNotIn("server", headers)
        status, headers, body = self.request("/assets/app-fixture.js")
        self.assertEqual(status, 200)
        self.assertEqual(body, b"console.log('fixture');")
        self.assertIn("immutable", headers["cache-control"])
        self.assertIn("max-age=31536000", headers["cache-control"])
        self.assertEqual(self.request("/api")[0], 404)

    def test_api_prefix_and_forwarded_headers_follow_the_trusted_proxy(self):
        status, _, body = self.request(
            "/api/probe?fixture=1",
            headers={
                "X-Forwarded-For": "198.51.100.77, 127.0.0.1",
                "X-Forwarded-Host": "untrusted.invalid",
                "X-Forwarded-Proto": "http",
                "Forwarded": "for=198.51.100.77;proto=http;host=untrusted.invalid",
                "X-Forwarded-Prefix": "/untrusted",
            },
        )
        self.assertEqual(status, 200)
        probe = json.loads(body)
        self.assertEqual(probe["path"], "/probe?fixture=1")
        headers = probe["headers"]
        self.assertEqual(headers["X-Forwarded-For"], "198.51.100.77")
        self.assertEqual(headers["X-Forwarded-Host"], self.hostname)
        self.assertEqual(headers["X-Forwarded-Proto"], "https")
        self.assertIsNone(headers["Forwarded"])
        self.assertIsNone(headers["X-Forwarded-Prefix"])

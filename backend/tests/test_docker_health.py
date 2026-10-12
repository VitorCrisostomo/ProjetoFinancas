"""Healthcheck lê somente configuração sintética e sinaliza falhas sem expor conteúdo."""

import importlib.util
import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

path = Path(__file__).resolve().parents[2] / "deploy/docker/check_api_health.py"
spec = importlib.util.spec_from_file_location("docker_api_health", path)
health = importlib.util.module_from_spec(spec)
spec.loader.exec_module(health)


class DockerHealthTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.configuration = Path(temporary.name) / "app.env"
        self.configuration.write_text(
            "AUTH_ALLOWED_ORIGINS='https://fixture.ts.net'\n", encoding="utf-8"
        )
        self.environment = patch.dict(os.environ, {"FINANCEHUB_ENV_FILE": str(self.configuration)})
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def test_generated_origin_and_dotenv_last_definition_are_respected(self):
        self.assertEqual(health.configured_host(), "fixture.ts.net")
        self.configuration.write_text(
            "AUTH_ALLOWED_ORIGINS='https://old.ts.net'\n"
            'AUTH_ALLOWED_ORIGINS="https://fixture.ts.net" # Current origin\n',
            encoding="utf-8",
        )
        self.assertEqual(health.configured_host(), "fixture.ts.net")

    def test_malformed_origin_never_probes_the_service(self):
        for origin in (
            "http://fixture.ts.net",
            "https://user:pw@fixture.ts.net",
            "https://fixture.ts.net/path",
        ):
            self.configuration.write_text(f"AUTH_ALLOWED_ORIGINS='{origin}'\n", encoding="utf-8")
            with patch.object(health.http.client, "HTTPConnection") as connection:
                self.assertEqual(health.main(), 1)
                if connection.called:
                    connection.return_value.request.assert_not_called()

    def test_availability_response_is_required_and_connection_is_closed(self):
        for status, content, expected in (
            (200, b'{"status":"ok"}', 0),
            (503, b'{"status":"unavailable"}', 1),
            (200, b"invalid-json", 1),
            (200, b'[{"status":"ok"}]', 1),
        ):
            with self.subTest(status=status, content=content):
                connection = Mock()
                connection.getresponse.return_value.status = status
                connection.getresponse.return_value.read.return_value = content
                with patch.object(health.http.client, "HTTPConnection", return_value=connection):
                    self.assertEqual(health.main(), expected)
                connection.request.assert_called_once_with(
                    "GET", "/healthz", headers={"Host": "fixture.ts.net"}
                )
                connection.close.assert_called_once_with()

    def test_failed_connection_returns_failure_without_raising(self):
        connection = Mock()
        connection.request.side_effect = OSError("synthetic connection failure")
        with patch.object(health.http.client, "HTTPConnection", return_value=connection):
            self.assertEqual(health.main(), 1)
        connection.close.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()

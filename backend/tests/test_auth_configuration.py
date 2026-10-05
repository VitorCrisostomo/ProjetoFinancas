"""Valida a configuração real sem carregar o .env ou abrir o banco financeiro."""

import importlib.util
import os
import unittest
from pathlib import Path
from unittest.mock import patch


class AuthConfigurationTests(unittest.TestCase):
    def load_config(self, overrides=None):
        environment = {
            "JWT_SECRET_KEY": "configuration-test-secret-at-least-32-characters",
            "DATABASE_URI": "sqlite:///:memory:",
            **(overrides or {}),
        }
        path = Path(__file__).resolve().parents[1] / "config.py"
        spec = importlib.util.spec_from_file_location("isolated_auth_config", path)
        module = importlib.util.module_from_spec(spec)
        with patch.dict(os.environ, environment, clear=True), patch("dotenv.load_dotenv"):
            spec.loader.exec_module(module)
        return module

    def test_secure_cookie_is_default_and_cors_only_allows_explicit_origins(self):
        config = self.load_config()
        self.assertTrue(config.app.config["JWT_COOKIE_SECURE"])
        self.assertTrue(config.app.config["JWT_COOKIE_CSRF_PROTECT"])
        self.assertEqual(config.app.config["JWT_TOKEN_LOCATION"], ["cookies"])

        @config.app.route("/probe")
        def probe():
            return {}

        client = config.app.test_client()
        response = client.get("/probe", headers={"Origin": "http://localhost:5173"})
        self.assertEqual(response.headers["Access-Control-Allow-Origin"], "http://localhost:5173")
        self.assertEqual(response.headers["Access-Control-Allow-Credentials"], "true")
        response = client.get("/probe", headers={"Origin": "https://untrusted.example"})
        self.assertNotIn("Access-Control-Allow-Origin", response.headers)

    def test_weak_secret_and_invalid_secure_setting_fail_closed(self):
        for overrides in (
            {"JWT_SECRET_KEY": ""},
            {"JWT_SECRET_KEY": "short"},
            {"AUTH_COOKIE_SECURE": "typo"},
        ):
            with self.subTest(overrides=overrides), self.assertRaises(RuntimeError):
                self.load_config(overrides)

    def test_local_http_requires_explicit_setting(self):
        config = self.load_config(
            {
                "AUTH_COOKIE_SECURE": "false",
                "AUTH_ALLOWED_ORIGINS": "https://finance.example",
            }
        )
        self.assertFalse(config.app.config["JWT_COOKIE_SECURE"])
        self.assertEqual(config.app.config["AUTH_ALLOWED_ORIGINS"], ["https://finance.example"])


if __name__ == "__main__":
    unittest.main()

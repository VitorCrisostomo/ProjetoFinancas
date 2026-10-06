"""Valida a configuração real sem carregar o .env ou abrir o banco financeiro."""

import importlib.util
import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from dotenv import load_dotenv

from services.data_encryption import DataCipher, generate_key_file


class AuthConfigurationTests(unittest.TestCase):
    def load_config(self, overrides=None, relative_key=False, file_contents=None):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        key_path = root / "keys.json"
        environment_path = root / "app.env"
        environment_path.write_text(
            file_contents or "# configuração fictícia de teste\n", encoding="utf-8"
        )
        generate_key_file(key_path)
        production = (overrides or {}).get("APP_ENV") == "production"
        environment = {
            "JWT_SECRET_KEY": "configuration-test-secret-at-least-32-characters",
            "DATABASE_URI": f"sqlite:///{(root / 'financehub.db').as_posix()}"
            if production
            else "sqlite:///:memory:",
            "DATA_ENCRYPTION_KEY_FILE": os.path.relpath(key_path)
            if relative_key
            else str(key_path),
            "FINANCEHUB_ENV_FILE": str(environment_path),
            "BACKUP_DIRECTORY": str(root / "backups"),
        }
        if production:
            environment["AUTH_ALLOWED_ORIGINS"] = "https://finance.test.ts.net"
        for name, value in (overrides or {}).items():
            if value is None:
                environment.pop(name, None)
            else:
                environment[name] = value
        path = Path(__file__).resolve().parents[1] / "config.py"
        spec = importlib.util.spec_from_file_location("isolated_auth_config", path)
        module = importlib.util.module_from_spec(spec)
        cipher = DataCipher.from_key_file(key_path)
        with (
            patch.dict(os.environ, environment, clear=True),
            patch(
                "dotenv.load_dotenv", wraps=load_dotenv if file_contents is not None else None
            ) as loader,
            patch("services.data_encryption.DataCipher.from_key_file", return_value=cipher),
        ):
            spec.loader.exec_module(module)
        module.test_environment_loader = loader
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

    def test_production_requires_secure_cookies_and_exact_https_origins(self):
        for overrides in (
            {"AUTH_COOKIE_SECURE": "false"},
            {"AUTH_ALLOWED_ORIGINS": "http://finance.test.ts.net"},
            {"AUTH_ALLOWED_ORIGINS": ""},
            {"AUTH_ALLOWED_ORIGINS": "https://*.test.ts.net"},
            {"AUTH_ALLOWED_ORIGINS": "https://.test.ts.net"},
            {"AUTH_ALLOWED_ORIGINS": "https://finance.test.ts.net/path"},
            {"AUTH_ALLOWED_ORIGINS": "https://finance.test.ts.net?redirect=evil"},
            {"AUTH_ALLOWED_ORIGINS": "https://finance.test.ts.net#fragment"},
            {"AUTH_ALLOWED_ORIGINS": "https://user:password@finance.test.ts.net"},
        ):
            with self.subTest(overrides=overrides), self.assertRaises(RuntimeError):
                self.load_config({"APP_ENV": "production", **overrides})

    def test_production_accepts_explicit_https_host_and_blocks_untrusted_host(self):
        config = self.load_config({"APP_ENV": "production"})
        self.assertFalse(config.app.config["DEBUG"])
        self.assertTrue(config.app.config["JWT_COOKIE_SECURE"])
        self.assertEqual(config.app.config["TRUSTED_HOSTS"], ["finance.test.ts.net"])

        @config.app.route("/probe")
        def production_probe():
            return {}

        client = config.app.test_client()
        self.assertEqual(
            client.get("/probe", base_url="https://finance.test.ts.net").status_code, 200
        )
        self.assertEqual(
            client.get("/probe", base_url="https://untrusted.example").status_code, 400
        )

    def test_production_requires_existing_environment_file_and_explicit_key_path(self):
        for overrides in (
            {"FINANCEHUB_ENV_FILE": str(Path(__file__).parent / "missing-production.env")},
            {"DATA_ENCRYPTION_KEY_FILE": None},
        ):
            with self.subTest(overrides=overrides), self.assertRaises(RuntimeError):
                self.load_config({"APP_ENV": "production", **overrides})

    def test_production_requires_persistent_sqlite_and_absolute_state_paths(self):
        for overrides in (
            {"DATABASE_URI": "sqlite:///:memory:"},
            {"DATABASE_URI": "sqlite:///relative.db"},
            {"DATABASE_URI": "postgresql://localhost/financehub"},
            {"BACKUP_DIRECTORY": "relative-backups"},
        ):
            with (
                self.subTest(overrides=overrides),
                self.assertRaisesRegex(RuntimeError, "caminhos absolutos"),
            ):
                self.load_config({"APP_ENV": "production", **overrides})
        with self.assertRaisesRegex(RuntimeError, "caminhos absolutos"):
            self.load_config({"APP_ENV": "production"}, relative_key=True)

    def test_explicit_environment_file_overrides_stale_shell_variables(self):
        fresh_secret = "new-production-configuration-with-at-least-32-characters"
        config = self.load_config(
            {"JWT_SECRET_KEY": "stale-shell-configuration-with-at-least-32-characters"},
            file_contents=f"JWT_SECRET_KEY='{fresh_secret}'\n",
        )
        self.assertEqual(config.app.config["JWT_SECRET_KEY"], fresh_secret)
        config.test_environment_loader.assert_called_once_with(
            Path(config.app.config["PLUGGY_ENV_FILE"]), override=True
        )
        config = self.load_config({"FINANCEHUB_ENV_FILE": None})
        self.assertFalse(config.test_environment_loader.call_args.kwargs["override"])

    def test_invalid_environment_name_fails_closed(self):
        with self.assertRaises(RuntimeError):
            self.load_config({"APP_ENV": "produciton"})


if __name__ == "__main__":
    unittest.main()

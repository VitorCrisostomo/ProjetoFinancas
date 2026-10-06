"""Valida a entrada WSGI sem abrir portas nem carregar configuração privada."""

import importlib.util
import os
import sys
import unittest
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock, patch

import test_authentication as auth_fixture
from test_authentication import isolated_modules, test_app, test_db

from services.data_encryption import DataEncryptionError


class ProductionServerTests(unittest.TestCase):
    def setUp(self):
        auth_fixture.AuthenticationTests.setUp(self)
        self.configuration_patch = patch.dict(test_app.config, {"APP_ENV": "production"})
        self.configuration_patch.start()
        self.environment_patch = patch.dict(os.environ, {}, clear=True)
        self.environment_patch.start()
        waitress_stub = ModuleType("waitress")
        waitress_stub.serve = Mock()
        path = Path(__file__).resolve().parents[1] / "server.py"
        spec = importlib.util.spec_from_file_location("isolated_production_server", path)
        self.server = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {**isolated_modules, "waitress": waitress_stub}):
            spec.loader.exec_module(self.server)
        self.serve = waitress_stub.serve

    def tearDown(self):
        self.environment_patch.stop()
        self.configuration_patch.stop()
        auth_fixture.AuthenticationTests.tearDown(self)

    def test_server_checks_schema_and_encryption_before_starting_waitress(self):
        events = []
        with (
            patch.object(
                self.server,
                "verify_encrypted_database",
                side_effect=lambda: events.append("verify"),
            ),
            patch.object(
                self.server, "serve", side_effect=lambda *_args, **_kwargs: events.append("serve")
            ),
        ):
            self.server.run()
        self.assertEqual(events, ["verify", "serve"])

    def test_server_defaults_to_loopback_and_trusts_only_one_concrete_proxy(self):
        self.server.run()
        self.serve.assert_called_once_with(
            test_app,
            host="127.0.0.1",
            port=8000,
            threads=4,
            max_request_body_size=test_app.config["MAX_CONTENT_LENGTH"],
            trusted_proxy="127.0.0.1",
            trusted_proxy_count=1,
            trusted_proxy_headers={"x-forwarded-for", "x-forwarded-proto", "x-forwarded-host"},
            clear_untrusted_proxy_headers=True,
        )

    def test_explicit_ipv6_loopback_and_concrete_proxy_are_accepted(self):
        with patch.dict(
            os.environ, {"SERVER_HOST": "::1", "TRUSTED_PROXY": "::1", "SERVER_PORT": "8123"}
        ):
            self.server.run()
        arguments = self.serve.call_args.kwargs
        self.assertEqual(arguments["host"], "::1")
        self.assertEqual(arguments["trusted_proxy"], "::1")
        self.assertEqual(arguments["port"], 8123)

    def test_development_configuration_cannot_start_production_server(self):
        test_app.config["APP_ENV"] = "development"
        with self.assertRaisesRegex(RuntimeError, "APP_ENV=production"):
            self.server.run()
        self.serve.assert_not_called()

    def test_public_bind_or_invalid_address_is_rejected_before_serving(self):
        for host in ("0.0.0.0", "::", "192.168.1.2", "100.64.0.2", "localhost", "*"):
            with self.subTest(host=host), patch.dict(os.environ, {"SERVER_HOST": host}):
                with self.assertRaises((RuntimeError, ValueError)):
                    self.server.run()
        self.serve.assert_not_called()

    def test_wildcard_or_network_proxy_trust_is_rejected(self):
        for proxy in ("*", "127.0.0.1/8", "localhost", ""):
            with self.subTest(proxy=proxy), patch.dict(os.environ, {"TRUSTED_PROXY": proxy}):
                with self.assertRaises(ValueError):
                    self.server.run()
        self.serve.assert_not_called()

    def test_missing_initialization_stops_startup_without_creating_tables(self):
        inspector = SimpleNamespace(get_table_names=lambda: [])
        with (
            patch.object(self.server, "inspect", return_value=inspector),
            patch.object(self.server, "verify_encrypted_database") as verifier,
        ):
            with self.assertRaisesRegex(RuntimeError, "init-db"):
                self.server.run()
        verifier.assert_not_called()
        self.serve.assert_not_called()

    def test_unreadable_encrypted_record_prevents_startup(self):
        original = test_app.extensions["financial_data_cipher"]
        test_app.extensions["financial_data_cipher"] = None
        try:
            with self.assertRaises(DataEncryptionError):
                self.server.run()
        finally:
            test_app.extensions["financial_data_cipher"] = original
        self.serve.assert_not_called()

    def test_corrupted_financial_record_prevents_startup(self):
        with test_db.engine.begin() as connection:
            connection.exec_driver_sql(
                "UPDATE transactions SET encrypted_data='alterado' WHERE id=1"
            )
        with self.assertRaises(DataEncryptionError):
            self.server.run()
        self.serve.assert_not_called()


if __name__ == "__main__":
    unittest.main()

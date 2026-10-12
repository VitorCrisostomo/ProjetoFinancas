"""Protege a preparação e o servidor local contra troca de estado e exposição de arquivos."""

import importlib.util
import os
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import Mock, patch

from flask import Flask
from werkzeug.test import Client
from werkzeug.wrappers import Response

PROJECT = Path(__file__).resolve().parents[2]


def load_script(name):
    spec = importlib.util.spec_from_file_location(
        f"tested_{name}", PROJECT / "deploy" / f"{name}.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


setup = load_script("setup")
local = load_script("run_local")


class SetupCommandTests(unittest.TestCase):
    def test_explicit_configuration_wins_and_external_python_paths_are_removed(self):
        with patch.dict(
            os.environ,
            {"FINANCEHUB_ENV_FILE": "old.env", "PYTHONPATH": "other-app", "APP_ENV": "production"},
        ):
            environment = setup.app_environment(Path("selected.env"))
        self.assertEqual(environment["FINANCEHUB_ENV_FILE"], "selected.env")
        self.assertNotIn("PYTHONPATH", environment)
        self.assertNotIn("APP_ENV", environment)

    def test_make_can_select_configuration_after_the_command(self):
        args = setup.parser().parse_args(
            ["create-user", "--env-file", "selected.env", "--email", "fixture@example.test"]
        )
        self.assertEqual(args.env_file, "selected.env")
        self.assertEqual(args.email, "fixture@example.test")

    def test_local_install_refuses_an_external_state_before_installing_dependencies(self):
        with (
            patch.object(sys, "argv", ["setup.py", "--env-file", "outside-state.env", "install"]),
            patch.object(setup, "install_runtime") as install,
        ):
            with self.assertRaises(SystemExit):
                setup.main()
        install.assert_not_called()

    def test_relative_environment_is_resolved_before_changing_directory(self):
        with (
            TemporaryDirectory() as directory,
            patch.object(setup, "require_runtime"),
            patch.object(setup, "run") as command,
        ):
            previous = Path.cwd()
            try:
                os.chdir(directory)
                selected = setup.configure("relative.env")
            finally:
                os.chdir(previous)
            self.assertEqual(selected, Path(directory).resolve() / "relative.env")
            self.assertIn(selected, command.call_args.args[0])

    def test_wrong_key_failure_prevents_database_initialization(self):
        with patch.object(
            setup, "flask", side_effect=subprocess.CalledProcessError(1, "verify")
        ) as command:
            with self.assertRaises(subprocess.CalledProcessError):
                setup.initialize(Path("synthetic.env"))
        command.assert_called_once_with(["verify-encrypted-data"], Path("synthetic.env"))

    def test_admin_options_and_configuration_reach_the_existing_cli(self):
        with (
            patch.object(
                sys,
                "argv",
                [
                    "setup.py",
                    "--env-file",
                    "selected.env",
                    "create-user",
                    "--email",
                    "fixture@example.test",
                    "--name",
                    "Teste",
                ],
            ),
            patch.object(setup, "require_runtime"),
            patch.object(setup, "configure", return_value=Path("selected.env")) as configure,
            patch.object(setup, "flask") as command,
        ):
            setup.main()
        configure.assert_called_once_with("selected.env")
        command.assert_called_once_with(
            ["create-user", "--email", "fixture@example.test", "--name", "Teste"],
            Path("selected.env"),
        )

    @unittest.skipUnless(os.name == "nt", "Preparação nativa é destinada ao Windows.")
    def test_production_existing_state_fails_before_dependencies_or_build(self):
        with TemporaryDirectory() as directory:
            args = setup.parser().parse_args(
                [
                    "production",
                    "--state-dir",
                    directory,
                    "--origin",
                    "https://finance.fixture.ts.net",
                    "--fresh",
                ]
            )
            with (
                patch.object(setup, "install_runtime") as install,
                patch.object(setup, "build") as build,
            ):
                with self.assertRaisesRegex(ValueError, "Estado já existente"):
                    setup.production(args)
            install.assert_not_called()
            build.assert_not_called()

    def test_local_run_checks_configuration_before_touching_the_database(self):
        with (
            patch.object(sys, "argv", ["setup.py", "run"]),
            patch.object(setup, "require_runtime"),
            patch.object(setup, "configure", return_value=Path("synthetic.env")),
            patch.object(setup, "run", side_effect=subprocess.CalledProcessError(1, "check")),
            patch.object(setup, "initialize") as initialize,
        ):
            with self.assertRaises(SystemExit):
                setup.main()
        initialize.assert_not_called()


class LocalServerTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.dist = self.root / "dist"
        self.dist.mkdir()
        (self.dist / "index.html").write_text("interface fictícia", encoding="utf-8")
        (self.dist / "assets").mkdir()
        (self.dist / "assets/app.js").write_text("/* fixture */", encoding="utf-8")
        api = Flask("synthetic_api")
        api.add_url_rule("/healthz", endpoint="health", view_func=lambda: {"status": "ok"})
        api.add_url_rule(
            "/private",
            endpoint="private",
            view_func=lambda: ({"message": "Login obrigatório"}, 401),
        )
        self.client = Client(local.application(api, self.dist), Response)

    def test_spa_routes_and_api_keep_their_respective_contracts(self):
        with self.client.get("/transactions") as response:
            self.assertEqual(response.text, "interface fictícia")
        self.assertEqual(self.client.get("/api/healthz").json, {"status": "ok"})
        self.assertEqual(self.client.get("/api/private").status_code, 401)
        self.assertEqual(self.client.get("/api/missing").status_code, 404)
        self.assertEqual(self.client.get("/assets/missing.js").status_code, 404)
        with self.client.get("/assets/app.js") as response:
            self.assertIn("nosniff", response.headers["X-Content-Type-Options"])

    def test_untrusted_host_is_refused_on_frontend_and_api(self):
        for path in ("/", "/api/healthz"):
            with self.subTest(path=path):
                self.assertEqual(
                    self.client.get(path, headers={"Host": "evil.example"}).status_code, 421
                )

    def test_paths_cannot_expose_a_file_outside_dist(self):
        (self.root / "private.txt").write_text("segredo fictício", encoding="utf-8")
        response = self.client.get("/../private.txt")
        self.assertEqual(response.status_code, 404)
        self.assertNotIn("segredo fictício", response.text)

    def test_production_configuration_cannot_start_the_local_http_server(self):
        api = Flask("production_guard_fixture")
        api.config.update(APP_ENV="production", DEPLOYMENT_MODE="native")
        with (
            patch.dict(sys.modules, {"main": SimpleNamespace(app=api)}),
            patch.object(sys, "argv", ["run_local.py", "--check"]),
            patch.object(local, "serve", Mock()) as serve,
        ):
            with self.assertRaises(SystemExit):
                local.main()
        serve.assert_not_called()


if __name__ == "__main__":
    unittest.main()

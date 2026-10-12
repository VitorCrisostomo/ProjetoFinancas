"""Instalação local verifica apenas configurações, arquivos e chaves sintéticos."""

import base64
import importlib.util
import json
import os
import stat
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from dotenv import dotenv_values

path = Path(__file__).resolve().parents[2] / "deploy/configure_local.py"
spec = importlib.util.spec_from_file_location("configure_local", path)
local_setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(local_setup)


class LocalSetupTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.project = Path(temporary.name) / "project with spaces"
        self.backend = self.project / "backend"
        self.frontend = self.project / "frontend"
        self.backend.mkdir(parents=True)
        self.frontend.mkdir()
        self.example = (
            "# Template sintético\nJWT_SECRET_KEY=\nAPP_ENV=development\n"
            "AUTH_COOKIE_SECURE=false\nAUTH_ALLOWED_ORIGINS=http://localhost:5173\n"
            "DATABASE_URI=sqlite:///financehub.db\nDATA_ENCRYPTION_KEY_FILE=\n"
        )
        (self.backend / ".env.example").write_text(self.example, encoding="utf-8")
        (self.frontend / ".env.example").write_text("VITE_API_URL=/api\n", encoding="utf-8")
        self.environment = self.backend / ".env"
        self.key = self.backend / ".secrets/financial-data-keys.json"
        environment_patch = patch.dict(os.environ, {"FINANCEHUB_ENV_FILE": ""})
        environment_patch.start()
        self.addCleanup(environment_patch.stop)

    def valid_environment(self, extra=""):
        content = self.example.replace("JWT_SECRET_KEY=\n", f"JWT_SECRET_KEY={'fixture-' * 8}\n")
        self.environment.write_text(content + extra, encoding="utf-8")

    def test_interpolation_cannot_select_a_database_from_the_shell(self):
        self.valid_environment()
        content = self.environment.read_text(encoding="utf-8").replace(
            "DATABASE_URI=sqlite:///financehub.db", "DATABASE_URI=sqlite:///${OTHER_DATABASE}"
        )
        self.environment.write_text(content, encoding="utf-8")
        with patch.dict(os.environ, {"OTHER_DATABASE": "some-other-installation.db"}):
            with self.assertRaisesRegex(ValueError, "literais"):
                local_setup.configure(self.project)
        self.assertFalse(self.key.exists())
        self.assertFalse((self.frontend / ".env").exists())

    def test_new_installation_generates_distinct_secrets_and_valid_absolute_key_path(self):
        target = local_setup.configure(self.project, local=True)
        self.assertEqual(target, self.environment.resolve())
        values = dotenv_values(target)
        self.assertEqual(len(values["JWT_SECRET_KEY"]), 64)
        self.assertEqual(Path(values["DATA_ENCRYPTION_KEY_FILE"]), self.key.resolve())
        cipher = local_setup.DataCipher.from_key_file(self.key)
        self.assertTrue(cipher.active_key)
        key_contents = json.loads(self.key.read_text(encoding="utf-8"))
        aes_key = base64.b64decode(key_contents["keys"][key_contents["active_key"]])
        self.assertEqual(len(aes_key), 32)
        self.assertNotEqual(aes_key, bytes.fromhex(values["JWT_SECRET_KEY"]))
        self.assertEqual(
            (self.frontend / ".env").read_bytes(), (self.frontend / ".env.example").read_bytes()
        )
        self.assertFalse((self.backend / "instance/financehub.db").exists())

    def test_repeated_setup_preserves_all_existing_files_byte_for_byte(self):
        local_setup.configure(self.project)
        files = (self.environment, self.key, self.frontend / ".env")
        original = {file: file.read_bytes() for file in files}
        with patch.object(local_setup, "generate_key_file") as generate:
            local_setup.configure(self.project)
            generate.assert_not_called()
        self.assertEqual({file: file.read_bytes() for file in files}, original)

    def test_existing_valid_configuration_preserves_credentials_and_relative_key(self):
        self.valid_environment("PLUGGY_USER_FIXTURE_CLIENT_ID='fixture-id'\r\n")
        local_setup.generate_key_file(self.key)
        before = self.environment.read_bytes()
        local_setup.configure(self.project)
        self.assertEqual(self.environment.read_bytes(), before)
        values = dotenv_values(self.environment)
        database, key, _backups = local_setup._resolve_configuration(values, self.backend)
        self.assertEqual(database, self.backend / "instance/financehub.db")
        self.assertEqual(key, self.key)

    def test_missing_environment_and_existing_database_or_backup_refuse_all_new_files(self):
        candidates = (
            self.backend / "instance/old.db",
            self.backend / "instance/subfolder/old.sqlite3-wal",
            self.backend / "old.sqlite",
            self.backend / "backups/old.fhbackup",
            self.backend / "backups/old.backup",
            self.backend / "backups/old.db",
        )
        for existing in candidates:
            with self.subTest(path=existing.name):
                existing.parent.mkdir(parents=True, exist_ok=True)
                existing.write_bytes(b"synthetic sentinel")
                with self.assertRaisesRegex(ValueError, "Restaure o .env"):
                    local_setup.configure(self.project)
                self.assertFalse(self.environment.exists())
                self.assertFalse(self.key.exists())
                self.assertFalse((self.frontend / ".env").exists())
                self.assertEqual(existing.read_bytes(), b"synthetic sentinel")
                existing.unlink()

    def test_database_and_sidecars_prevent_generating_a_replacement_key(self):
        self.valid_environment()
        (self.backend / "instance").mkdir()
        before = self.environment.read_bytes()
        for suffix in ("", "-wal", "-shm", "-journal"):
            existing = self.backend / f"instance/financehub.db{suffix}"
            existing.write_bytes(b"synthetic sentinel")
            with (
                self.subTest(suffix=suffix),
                patch.object(local_setup, "generate_key_file") as generate,
            ):
                with self.assertRaisesRegex(ValueError, "chaves"):
                    local_setup.configure(self.project)
                generate.assert_not_called()
                self.assertEqual(self.environment.read_bytes(), before)
                self.assertFalse((self.frontend / ".env").exists())
            existing.unlink()

    def test_invalid_existing_key_never_changes_it_or_other_files(self):
        self.valid_environment()
        self.key.parent.mkdir()
        self.key.write_bytes(b"invalid synthetic key")
        with self.assertRaises(RuntimeError):
            local_setup.configure(self.project)
        self.assertEqual(self.key.read_bytes(), b"invalid synthetic key")
        self.assertFalse((self.frontend / ".env").exists())

    def test_invalid_or_duplicate_configurations_fail_before_secret_generation(self):
        for content in (
            self.example,
            self.example.replace("JWT_SECRET_KEY=\n", "JWT_SECRET_KEY=short\n"),
            "BROKEN='unclosed\n",
            self.example + "DATABASE_URI=sqlite:///another.db\n",
        ):
            with self.subTest(content_length=len(content)):
                self.environment.write_text(content, encoding="utf-8")
                with self.assertRaises(ValueError):
                    local_setup.configure(self.project)
                self.assertEqual(self.environment.read_text(encoding="utf-8"), content)
                self.assertFalse(self.key.exists())
                self.assertFalse((self.frontend / ".env").exists())

    def test_invalid_frontend_template_is_rejected_before_backend_mutations(self):
        (self.frontend / ".env.example").write_text("BROKEN='unclosed\n", encoding="utf-8")
        with self.assertRaises(ValueError):
            local_setup.configure(self.project)
        self.assertFalse(self.key.exists())
        self.assertFalse(self.environment.exists())

    def test_existing_key_is_reused_for_fresh_configuration(self):
        local_setup.generate_key_file(self.key)
        before = self.key.read_bytes()
        local_setup.configure(self.project)
        self.assertEqual(self.key.read_bytes(), before)

    def test_external_production_configuration_is_respected_without_local_fallback(self):
        self.valid_environment()
        local_setup.generate_key_file(self.key)
        external = self.project.parent / "external.env"
        content = (
            f"JWT_SECRET_KEY={'fixture-' * 8}\nAPP_ENV=production\nAUTH_COOKIE_SECURE=true\n"
            "AUTH_ALLOWED_ORIGINS=https://finance.fixture.ts.net\n"
            f"DATABASE_URI='sqlite:///{(self.project.parent / 'production.db').as_posix()}'\n"
            f"DATA_ENCRYPTION_KEY_FILE='{self.key.as_posix()}'\n"
            f"BACKUP_DIRECTORY='{(self.project.parent / 'backups').as_posix()}'\n"
        )
        external.write_text(content, encoding="utf-8")
        local_before = self.environment.read_bytes()
        with patch.dict(os.environ, {"FINANCEHUB_ENV_FILE": str(external)}):
            self.assertEqual(local_setup.configure(self.project), external.resolve())
        self.assertEqual(external.read_text(encoding="utf-8"), content)
        self.assertEqual(self.environment.read_bytes(), local_before)

    def test_missing_external_configuration_or_key_never_creates_local_fallback(self):
        external = self.project.parent / "missing.env"
        with self.assertRaises(ValueError):
            local_setup.configure(self.project, external)
        self.valid_environment()
        external.write_bytes(self.environment.read_bytes())
        self.environment.unlink()
        with self.assertRaisesRegex(ValueError, "chaves"):
            local_setup.configure(self.project, external)
        self.assertFalse(self.environment.exists())
        self.assertFalse(self.key.exists())
        self.assertFalse((self.frontend / ".env").exists())

    def test_new_secret_files_have_private_posix_permissions(self):
        if os.name == "nt":
            self.skipTest("As ACLs do Windows são aplicadas pelo helper de escrita privada.")
        local_setup.configure(self.project)
        for path in (self.environment, self.key):
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)


if __name__ == "__main__":
    unittest.main()

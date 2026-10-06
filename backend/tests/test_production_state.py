"""Preparação de produção usando somente arquivos financeiros sintéticos."""

import importlib.util
import sqlite3
import unittest
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory

from dotenv import dotenv_values

from services.data_encryption import DataCipher, generate_key_file

path = Path(__file__).resolve().parents[2] / "deploy/prepare_state.py"
spec = importlib.util.spec_from_file_location("production_prepare", path)
prepare_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prepare_module)


class ProductionStateTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.output = self.root / "state with spaces"
        self.env = self.root / "source.env"
        self.env.write_text(
            "# Preserve configuration\nPLUGGY_USER_TEST_CLIENT_ID='fixture-id'\n"
            "FINANCEHUB_FILE_ACCESS_SID='S-1-5-123'\n",
            encoding="utf-8",
        )
        self.key = self.root / "key.json"
        generate_key_file(self.key)
        self.database = self.root / "source.db"
        with closing(sqlite3.connect(self.database)) as connection:
            connection.execute("CREATE TABLE marker (value TEXT)")
            connection.execute("INSERT INTO marker VALUES ('synthetic')")
            connection.commit()

    def prepare_existing(self):
        prepare_module.prepare(
            self.output,
            "https://finance.fixture.ts.net",
            source_env=self.env,
            source_key=self.key,
            source_database=self.database,
        )

    def test_migration_preserves_existing_keys_data_and_individual_credentials(self):
        original_key = self.key.read_bytes()
        self.prepare_existing()
        self.assertEqual((self.output / "keys/financial-data-keys.json").read_bytes(), original_key)
        with closing(sqlite3.connect(self.output / "data/financehub.db")) as connection:
            self.assertEqual(
                connection.execute("SELECT value FROM marker").fetchone()[0], "synthetic"
            )
        values = dotenv_values(self.output / "config/app.env")
        self.assertEqual(values["PLUGGY_USER_TEST_CLIENT_ID"], "fixture-id")
        self.assertNotIn("FINANCEHUB_FILE_ACCESS_SID", values)
        self.assertEqual(values["APP_ENV"], "production")
        self.assertEqual(values["AUTH_COOKIE_SECURE"], "true")
        self.assertGreaterEqual(len(values["JWT_SECRET_KEY"]), 32)
        self.assertEqual(values["AUTH_ALLOWED_ORIGINS"], "https://finance.fixture.ts.net")
        self.assertEqual(
            values["DATABASE_URI"], "sqlite:///" + (self.output / "data/financehub.db").as_posix()
        )

    def test_preparation_never_overwrites_existing_state(self):
        self.output.mkdir()
        sentinel = self.output / "sentinel"
        sentinel.write_text("preserve", encoding="utf-8")
        with self.assertRaises(ValueError):
            self.prepare_existing()
        self.assertEqual(sentinel.read_text(encoding="utf-8"), "preserve")

    def test_state_inside_checkout_is_rejected_before_any_creation(self):
        with self.assertRaisesRegex(ValueError, "fora do checkout"):
            prepare_module.prepare(
                prepare_module.PROJECT / "synthetic-production-state",
                "https://finance.fixture.ts.net",
                fresh=True,
            )

    def test_invalid_environment_is_rejected_before_creating_output(self):
        self.env.write_text("BROKEN='unclosed\n", encoding="utf-8")
        with self.assertRaises(ValueError):
            self.prepare_existing()
        self.assertFalse(self.output.exists())

    def test_fresh_install_generates_keys_but_requires_explicit_database_initialization(self):
        prepare_module.prepare(self.output, "https://finance.fixture.ts.net", fresh=True)
        DataCipher.from_key_file(self.output / "keys/financial-data-keys.json")
        self.assertFalse((self.output / "data/financehub.db").exists())

    def test_unsafe_origins_and_mixed_sources_are_rejected(self):
        for origin in ("http://finance.local", "https://*.ts.net", "https://host/path"):
            with self.subTest(origin=origin), self.assertRaises(ValueError):
                prepare_module.prepare(self.output, origin, fresh=True)
        with self.assertRaises(ValueError):
            prepare_module.prepare(
                self.output, "https://finance.fixture.ts.net", fresh=True, source_env=self.env
            )
        self.assertFalse(self.output.exists())

    def test_wal_snapshot_is_independent_and_preserves_committed_changes(self):
        with closing(sqlite3.connect(self.database)) as source:
            source.execute("PRAGMA journal_mode=WAL")
            source.execute("UPDATE marker SET value='committed-wal'")
            source.commit()
            self.prepare_existing()
            with closing(sqlite3.connect(self.output / "data/financehub.db")) as restored:
                self.assertEqual(
                    restored.execute("SELECT value FROM marker").fetchone()[0], "committed-wal"
                )
            self.assertEqual(source.execute("PRAGMA journal_mode").fetchone()[0], "wal")


if __name__ == "__main__":
    unittest.main()

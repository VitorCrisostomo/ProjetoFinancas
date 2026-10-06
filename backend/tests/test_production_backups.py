"""Recuperação de backups de produção usando somente registros e credenciais fictícios."""

import base64
import importlib.util
import json
import os
import sqlite3
import sys
import unittest
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

import test_authentication as auth_fixture
from sqlalchemy import create_engine, select
from test_authentication import isolated_modules, test_app, test_db

from services.data_encryption import DataCipher, DataEncryptionError

backup_service = isolated_modules["services.backup_service"]
script_path = Path(__file__).resolve().parents[2] / "deploy/run_backup.py"
script_spec = importlib.util.spec_from_file_location("production_backup_runner", script_path)
backup_runner = importlib.util.module_from_spec(script_spec)
script_spec.loader.exec_module(backup_runner)


class ProductionBackupTests(unittest.TestCase):
    def setUp(self):
        auth_fixture.AuthenticationTests.setUp(self)
        auth_fixture.AuthenticationTests.login(self)
        self.temporary = TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.path = self.root / "source.db"
        self.backups = self.root / "backups"
        self.environment = "# Configuração de teste\nPLUGGY_CLIENT_SECRET='MARCADOR-FICTICIO'\n"
        Path(test_app.config["PLUGGY_ENV_FILE"]).write_bytes(self.environment.encode("utf-8"))
        self.engine = create_engine(f"sqlite:///{self.path.as_posix()}")
        test_db.metadata.create_all(self.engine)
        with test_db.engine.connect() as source, self.engine.begin() as destination:
            for table in test_db.metadata.sorted_tables:
                records = [dict(row) for row in source.execute(select(table)).mappings()]
                if records:
                    destination.execute(table.insert(), records)
        self.db_patch = patch.object(backup_service, "db", SimpleNamespace(engine=self.engine))
        self.db_patch.start()
        self.previous_directory = test_app.config.get("BACKUP_DIRECTORY")
        test_app.config["BACKUP_DIRECTORY"] = str(self.backups)
        self.original_cipher = test_app.extensions["financial_data_cipher"]

    def tearDown(self):
        test_app.extensions["financial_data_cipher"] = self.original_cipher
        if self.previous_directory is None:
            test_app.config.pop("BACKUP_DIRECTORY", None)
        else:
            test_app.config["BACKUP_DIRECTORY"] = self.previous_directory
        self.db_patch.stop()
        self.engine.dispose()
        self.temporary.cleanup()
        auth_fixture.AuthenticationTests.tearDown(self)

    @staticmethod
    def rows(snapshot):
        with closing(sqlite3.connect(":memory:")) as connection:
            connection.deserialize(snapshot)
            tables = [
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
                )
            ]
            return {
                table: connection.execute(f'SELECT * FROM "{table}" ORDER BY rowid').fetchall()
                for table in tables
            }

    def test_backup_encrypts_database_and_configuration_and_preserves_all_records(self):
        with closing(sqlite3.connect(self.path)) as connection:
            expected = self.rows(connection.serialize())
        path = backup_service.create_backup()
        stored = path.read_bytes()
        for marker in (b"SQLite format", b"MARCADOR-FICTICIO", b"user1@example.com"):
            self.assertNotIn(marker, stored)
        snapshot, environment = backup_service.read_backup(path)
        self.assertEqual(self.rows(snapshot), expected)
        self.assertEqual(environment, self.environment)
        self.assertEqual(backup_service.check_backup(), path)
        self.assertEqual(list(self.backups.glob("*.tmp")), [])

    def test_restore_preserves_financial_data_and_revokes_all_original_sessions(self):
        path = backup_service.create_backup()
        snapshot, _environment = backup_service.read_backup(path)
        expected = self.rows(snapshot)
        self.assertTrue(any(not row[-1] for row in expected["auth_sessions"]))
        destination = backup_service.restore_backup(path, self.root / "restored")
        with closing(sqlite3.connect(destination / "financehub.db")) as connection:
            self.assertEqual(connection.execute("PRAGMA integrity_check").fetchone()[0], "ok")
            self.assertEqual(connection.execute("PRAGMA foreign_key_check").fetchall(), [])
            restored = self.rows(connection.serialize())
        for table, records in expected.items():
            if table != "auth_sessions":
                self.assertEqual(restored[table], records, table)
        self.assertTrue(all(row[-1] for row in restored["auth_sessions"]))
        self.assertEqual((destination / "app.env").read_text(encoding="utf-8"), self.environment)
        self.assertEqual(backup_service.read_backup(path)[0], snapshot)
        with closing(sqlite3.connect(self.path)) as original:
            self.assertEqual(
                original.execute("SELECT revoked FROM auth_sessions").fetchall(), [(0,)]
            )

    def test_restore_refuses_existing_directory_without_modifying_it(self):
        path = backup_service.create_backup()
        destination = self.root / "existing"
        destination.mkdir()
        sentinel = destination / "financehub.db"
        sentinel.write_bytes(b"NAO-SOBRESCREVER")
        with self.assertRaisesRegex(RuntimeError, "ainda não exista"):
            backup_service.restore_backup(path, destination)
        self.assertEqual(sentinel.read_bytes(), b"NAO-SOBRESCREVER")

    def test_modified_backup_or_wrong_key_cannot_restore_any_files(self):
        path = backup_service.create_backup()
        original = path.read_text(encoding="ascii")
        index = len(original) - 20
        path.write_text(
            original[:index] + ("A" if original[index] != "A" else "B") + original[index + 1 :],
            encoding="ascii",
        )
        destination = self.root / "rejected"
        with self.assertRaises(DataEncryptionError):
            backup_service.restore_backup(path, destination)
        self.assertFalse(destination.exists())
        path.write_text(original, encoding="ascii")
        test_app.extensions["financial_data_cipher"] = DataCipher("test", {"test": b"q" * 32})
        with self.assertRaises(DataEncryptionError):
            backup_service.read_backup(path)

    def test_key_rotation_preserves_old_backup_readability(self):
        path = backup_service.create_backup()
        expected = backup_service.read_backup(path)
        test_app.extensions["financial_data_cipher"] = DataCipher(
            "rotated", {"test": b"z" * 32, "rotated": b"r" * 32}
        )
        self.assertEqual(backup_service.read_backup(path), expected)
        self.assertTrue(
            backup_service.create_backup().read_text(encoding="ascii").startswith("fh1:rotated:")
        )

    def test_wal_commits_are_included_without_checkpoints_or_changes_to_source(self):
        self.engine.dispose()
        with closing(sqlite3.connect(self.path)) as writer:
            self.assertEqual(writer.execute("PRAGMA journal_mode=WAL").fetchone()[0], "wal")
            writer.execute("PRAGMA wal_autocheckpoint=0")
            writer.execute("UPDATE users SET name='COMMIT-NO-WAL' WHERE id=1")
            writer.commit()
            self.assertTrue(Path(str(self.path) + "-wal").is_file())
            original_bytes = self.path.read_bytes()
            path = backup_service.create_backup()
            snapshot, _environment = backup_service.read_backup(path)
            self.assertEqual(self.rows(snapshot)["users"][0][1], "COMMIT-NO-WAL")
            self.assertEqual(snapshot[18:20], b"\x01\x01")
            self.assertEqual(writer.execute("PRAGMA journal_mode").fetchone()[0], "wal")
            self.assertEqual(self.path.read_bytes(), original_bytes)

    def test_uncommitted_wal_changes_are_excluded(self):
        self.engine.dispose()
        with closing(sqlite3.connect(self.path)) as writer:
            writer.execute("PRAGMA journal_mode=WAL")
            writer.execute("UPDATE users SET name='NAO-CONFIRMADO' WHERE id=1")
            path = backup_service.create_backup()
            snapshot, _environment = backup_service.read_backup(path)
            self.assertEqual(self.rows(snapshot)["users"][0][1], "Pessoa 1")
            writer.rollback()

    def test_retention_preserves_unrelated_and_migration_files(self):
        self.backups.mkdir()
        unrelated = self.backups / "migration.fhbackup"
        unrelated.write_bytes(b"ARQUIVO-EXTERNO")
        for day in range(1, 4):
            (
                self.backups / f"scheduled-2000010{day}T000000000000Z-{'a' * 32}.fhbackup"
            ).write_bytes(b"ANTIGO")
        newest = backup_service.create_backup(keep=2)
        owned = sorted(
            path
            for path in self.backups.iterdir()
            if backup_service.BACKUP_NAME.fullmatch(path.name)
        )
        self.assertEqual(len(owned), 2)
        self.assertEqual(owned[-1], newest)
        self.assertEqual(unrelated.read_bytes(), b"ARQUIVO-EXTERNO")

    def test_failed_verification_never_prunes_the_last_valid_backup(self):
        previous = backup_service.create_backup()
        previous_bytes = previous.read_bytes()
        with patch.object(backup_service, "read_backup", side_effect=RuntimeError("verificação")):
            with self.assertRaises(RuntimeError):
                backup_service.create_backup(keep=1)
        self.assertEqual(previous.read_bytes(), previous_bytes)
        self.assertEqual(list(self.backups.iterdir()), [previous])

    def test_corrupt_financial_payloads_and_foreign_keys_are_rejected(self):
        with closing(sqlite3.connect(self.path)) as connection:
            connection.execute("UPDATE transactions SET encrypted_data='alterado' WHERE id=1")
            connection.commit()
        with self.assertRaises(DataEncryptionError):
            backup_service.create_backup()
        self.assertEqual(list(self.backups.iterdir()), [])

    def test_inconsistent_foreign_keys_are_rejected_before_backup_publication(self):
        with closing(sqlite3.connect(self.path)) as connection:
            connection.execute("DELETE FROM users WHERE id=1")
            connection.commit()
        with self.assertRaisesRegex(RuntimeError, "vínculos inconsistentes"):
            backup_service.create_backup()
        self.assertEqual(list(self.backups.iterdir()), [])

    def test_stale_missing_or_tampered_latest_backup_is_reported(self):
        with self.assertRaisesRegex(RuntimeError, "Nenhum backup"):
            backup_service.check_backup()
        path = backup_service.create_backup()
        old = self.backups / f"scheduled-20000101T000000000000Z-{'a' * 32}.fhbackup"
        path.rename(old)
        with self.assertRaisesRegex(RuntimeError, "atrasado"):
            backup_service.check_backup()
        old.rename(path)
        path.write_text("cópia alterada", encoding="utf-8")
        with self.assertRaises((DataEncryptionError, UnicodeError)):
            backup_service.check_backup()

    def rewrite_backup_document(self, path, document):
        path.write_text(
            self.original_cipher.encrypt(
                json.dumps(document).encode(), backup_service.BACKUP_CONTEXT
            ),
            encoding="ascii",
        )

    def decrypted_document(self, path):
        return json.loads(
            self.original_cipher.decrypt(
                path.read_text(encoding="ascii"), backup_service.BACKUP_CONTEXT
            )
        )

    def test_renaming_old_authenticated_backup_cannot_fake_freshness(self):
        path = backup_service.create_backup()
        document = self.decrypted_document(path)
        document["created_at"] = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
        self.rewrite_backup_document(path, document)
        recent_timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        renamed = self.backups / f"scheduled-{recent_timestamp}-{'b' * 32}.fhbackup"
        path.rename(renamed)
        with self.assertRaisesRegex(RuntimeError, "atrasado"):
            backup_service.check_backup()
        # Um backup antigo íntegro continua recuperável, mesmo não sendo recente.
        backup_service.restore_backup(renamed, self.root / "old-restored")

    def test_missing_invalid_or_naive_authenticated_creation_dates_are_rejected(self):
        path = backup_service.create_backup()
        original = self.decrypted_document(path)
        for created_at in (
            None,
            "",
            "not-a-date",
            "2026-10-01T12:00:00",
            "0001-01-01T00:00:00+14:00",
            123,
        ):
            with self.subTest(created_at=created_at):
                document = {**original, "created_at": created_at}
                if created_at is None:
                    del document["created_at"]
                self.rewrite_backup_document(path, document)
                with self.assertRaises(RuntimeError):
                    backup_service.read_backup(path)

    def test_authenticated_creation_date_supports_timezone_and_rejects_future_freshness(self):
        path = backup_service.create_backup()
        document = self.decrypted_document(path)
        document["created_at"] = datetime.now(timezone(timedelta(hours=3))).isoformat()
        self.rewrite_backup_document(path, document)
        self.assertEqual(backup_service.check_backup(), path)
        self.assertEqual(len(backup_service.read_backup(path)), 2)
        document["created_at"] = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
        self.rewrite_backup_document(path, document)
        with self.assertRaisesRegex(RuntimeError, "atrasado"):
            backup_service.check_backup()

    def test_invalid_encrypted_document_or_database_format_is_rejected(self):
        self.backups.mkdir()
        path = self.backups / "invalid.fhbackup"
        for document in (
            [],
            {"format": 2},
            {"format": 1, "database": 123, "environment": ""},
            {"format": 1, "database": base64.b64encode(b"nao-sqlite").decode(), "environment": ""},
        ):
            path.write_text(
                self.original_cipher.encrypt(
                    json.dumps(document).encode(), backup_service.BACKUP_CONTEXT
                ),
                encoding="ascii",
            )
            with self.assertRaises(RuntimeError):
                backup_service.read_backup(path)

    def test_environment_failure_is_reported_by_cli_without_exposing_its_contents(self):
        Path(test_app.config["PLUGGY_ENV_FILE"]).write_text(
            "'MARCADOR-FICTICIO\n", encoding="utf-8"
        )
        result = test_app.test_cli_runner().invoke(args=["backup-data"])
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("Operação de backup falhou", result.output)
        self.assertNotIn("MARCADOR-FICTICIO", result.output)
        self.assertNotIn("Traceback", result.output)

    def test_external_copy_checks_hash_and_preserves_original_after_conflict(self):
        path = backup_service.create_backup()
        external = self.root / "external"
        external.mkdir()
        backup_runner.copy_external(path, external)
        destination = external / path.name
        self.assertEqual(destination.read_bytes(), path.read_bytes())
        backup_runner.copy_external(path, external)
        destination.write_bytes(b"CONFLITO")
        with self.assertRaises(RuntimeError):
            backup_runner.copy_external(path, external)
        self.assertEqual(destination.read_bytes(), b"CONFLITO")
        backup_service.read_backup(path)

    def test_external_copy_requires_available_directory_distinct_from_local_backups(self):
        path = backup_service.create_backup()
        for directory in (self.root / "missing", self.backups):
            with self.assertRaises((ValueError, FileNotFoundError)):
                backup_runner.copy_external(path, directory)

    def test_snapshot_and_restore_size_limits_reject_before_publishing(self):
        with patch.object(backup_service, "MAX_DATABASE_BYTES", 1):
            with self.assertRaises(RuntimeError):
                backup_service.create_backup()
        self.assertEqual(list(self.backups.iterdir()), [])
        path = backup_service.create_backup()
        with patch.object(backup_service, "MAX_DATABASE_BYTES", 1):
            with self.assertRaises(RuntimeError):
                backup_service.restore_backup(path, self.root / "too-large")
        self.assertFalse((self.root / "too-large").exists())

    def test_scheduled_runner_records_verified_success_without_sensitive_content(self):
        (self.root / "logs").mkdir()
        with (
            patch.object(sys, "argv", ["run_backup.py", "--state-dir", str(self.root)]),
            patch.dict(os.environ),
        ):
            self.assertEqual(backup_runner.main(), 0)
        status_text = (self.root / "logs/backup-status.json").read_text(encoding="utf-8")
        status = json.loads(status_text)
        self.assertTrue(status["success"])
        self.assertFalse(status["external_copy"])
        self.assertNotIn("MARCADOR-FICTICIO", status_text)
        backup_service.check_backup()

    def test_scheduled_runner_reports_external_failure_but_keeps_verified_local_backup(self):
        (self.root / "logs").mkdir()
        arguments = [
            "run_backup.py",
            "--state-dir",
            str(self.root),
            "--external-directory",
            str(self.root / "missing"),
        ]
        with patch.object(sys, "argv", arguments), patch.dict(os.environ), patch("sys.stderr"):
            self.assertEqual(backup_runner.main(), 1)
        status = json.loads((self.root / "logs/backup-status.json").read_text(encoding="utf-8"))
        self.assertFalse(status["success"])
        backup_service.check_backup()


if __name__ == "__main__":
    unittest.main()

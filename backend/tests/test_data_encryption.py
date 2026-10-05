"""Verifica conteúdo físico, autenticidade, migração, rollback e recuperação."""

import json
import sqlite3
import sys
import unittest
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

import test_authentication as auth_fixture
from sqlalchemy import create_engine, text
from sqlalchemy.orm import scoped_session, sessionmaker
from test_authentication import (
    Account,
    Transaction,
    isolated_modules,
    test_app,
    test_db,
)

from services.data_encryption import DataCipher, DataEncryptionError

database_service = isolated_modules["services.database_encryption_service"]


class DataEncryptionTests(unittest.TestCase):
    def setUp(self):
        auth_fixture.AuthenticationTests.setUp(self)

    def tearDown(self):
        auth_fixture.AuthenticationTests.tearDown(self)

    def test_database_columns_contain_no_transaction_or_bank_content(self):
        account = test_db.session.get(Account, "account-1")
        account.taxNumber = "CPF-MARCADOR-PRIVADO"
        account.bankData = {"accountNumber": "CONTA-MARCADOR-PRIVADO", "value": 1500.0}
        transaction = test_db.session.get(Transaction, 1)
        transaction.name = "NOME-MARCADOR-PRIVADO"
        transaction.description = "DESCRICAO-MARCADOR-PRIVADO"
        transaction.subcategory = "SUBCATEGORIA-MARCADOR-PRIVADO"
        test_db.session.commit()
        with test_db.engine.connect() as connection:
            columns = [
                row[1] for row in connection.execute(text("PRAGMA table_info(transactions)"))
            ]
            self.assertEqual(
                set(columns),
                {
                    "id",
                    "external_id",
                    "account_id",
                    "user_id",
                    "encrypted_data",
                    "encryption_context",
                },
            )
            raw = connection.execute(
                text("SELECT encrypted_data FROM transactions WHERE id=1")
            ).scalar()
            bank = connection.execute(
                text("SELECT encrypted_data FROM accounts WHERE id='account-1'")
            ).scalar()
            self.assertTrue(raw.startswith("fh1:"))
            self.assertTrue(bank.startswith("fh1:"))
            for marker in (
                "NOME-MARCADOR",
                "DESCRICAO-MARCADOR",
                "SUBCATEGORIA-MARCADOR",
                "CPF-MARCADOR",
                "CONTA-MARCADOR",
                "1500",
            ):
                self.assertNotIn(marker, raw + bank)
        test_db.session.expire_all()
        self.assertEqual(transaction.name, "NOME-MARCADOR-PRIVADO")
        self.assertEqual(account.taxNumber, "CPF-MARCADOR-PRIVADO")
        self.assertEqual(account.bankData["value"], 1500.0)

    def test_equal_values_have_different_ciphertexts_and_updates_get_new_nonces(self):
        first = test_db.session.get(Transaction, 1)
        second = test_db.session.get(Transaction, 2)
        self.assertEqual(first.value, second.value)
        self.assertNotEqual(first.encrypted_data, second.encrypted_data)
        previous = first.encrypted_data
        first.value = first.value
        test_db.session.commit()
        self.assertNotEqual(first.encrypted_data, previous)

    def test_wrong_key_and_missing_key_never_return_plaintext(self):
        original = test_app.extensions["financial_data_cipher"]
        for cipher in (None, DataCipher("test", {"test": b"q" * 32})):
            test_app.extensions["financial_data_cipher"] = cipher
            test_db.session.expire_all()
            with self.assertRaises(DataEncryptionError):
                test_db.session.get(Transaction, 1).to_json()
        test_app.extensions["financial_data_cipher"] = original

    def test_corruption_and_cross_user_ciphertext_swaps_are_rejected(self):
        first = test_db.session.get(Transaction, 1)
        original = first.encrypted_data
        with test_db.engine.begin() as connection:
            connection.execute(
                text("UPDATE transactions SET encrypted_data=:value WHERE id=1"),
                {"value": original[:-20] + "A" * 20},
            )
        test_db.session.expire_all()
        with self.assertRaises(DataEncryptionError):
            first.to_json()
        with test_db.engine.begin() as connection:
            connection.execute(
                text("UPDATE transactions SET encrypted_data=:value WHERE id=2"),
                {"value": original},
            )
        test_db.session.expire_all()
        with self.assertRaises(DataEncryptionError):
            test_db.session.get(Transaction, 2).to_json()

    def test_modified_metadata_and_unencrypted_payload_are_rejected(self):
        with test_db.engine.begin() as connection:
            connection.execute(text("UPDATE transactions SET external_id='changed' WHERE id=1"))
        test_db.session.expire_all()
        with self.assertRaises(DataEncryptionError):
            test_db.session.get(Transaction, 1).to_json()
        with test_db.engine.begin() as connection:
            connection.execute(
                text("UPDATE transactions SET encrypted_data=:value WHERE id=2"),
                {"value": json.dumps({"value": 100})},
            )
        test_db.session.expire_all()
        with self.assertRaises(DataEncryptionError):
            test_db.session.get(Transaction, 2).to_json()

    def test_modified_transaction_id_is_rejected(self):
        with test_db.engine.begin() as connection:
            connection.execute(text("UPDATE transactions SET id=1000 WHERE id=1"))
        test_db.session.expire_all()
        with self.assertRaises(DataEncryptionError):
            test_db.session.get(Transaction, 1000).to_json()
        with self.assertRaises(DataEncryptionError):
            database_service.verify_encrypted_database()

    def test_generated_id_is_bound_before_commit_and_manual_payload_swap_is_rejected(self):
        first = test_db.session.get(Transaction, 1)
        records = [
            Transaction(
                user_id=first.user_id,
                account_id=first.account_id,
                value=0,
                date=first.date,
                name="Manual",
                type="income",
            )
            for _ in range(2)
        ]
        test_db.session.add_all(records)
        test_db.session.commit()
        test_db.session.expire_all()
        self.assertTrue(all(record.id is not None and record.value == 0 for record in records))
        source, target = records
        source_payload, source_context = source.encrypted_data, source.encryption_context
        with test_db.engine.begin() as connection:
            connection.execute(
                text(
                    "UPDATE transactions SET encryption_context='removed-for-swap-test' WHERE id=:id"
                ),
                {"id": source.id},
            )
            connection.execute(
                text(
                    "UPDATE transactions SET encrypted_data=:payload, encryption_context=:context "
                    "WHERE id=:id"
                ),
                {"payload": source_payload, "context": source_context, "id": target.id},
            )
        test_db.session.expire_all()
        with self.assertRaises(DataEncryptionError):
            target.to_json()

    def test_legitimate_binding_change_reencrypts_fields(self):
        record = test_db.session.get(Transaction, 1)
        before = record.to_json()
        record.id = 1000
        test_db.session.commit()
        test_db.session.expire_all()
        after = test_db.session.get(Transaction, 1000).to_json()
        self.assertEqual(after, {**before, "id": 1000})

    def test_json_responses_preserve_public_contract_and_hide_encryption_state(self):
        transaction = test_db.session.get(Transaction, 1).to_json()
        account = test_db.session.get(Account, "account-1").to_json()
        for response in (transaction, account):
            self.assertNotIn("encrypted_data", response)
            self.assertNotIn("encryption_context", response)
        self.assertEqual(transaction["value"], 100)
        self.assertEqual(transaction["date"], "2026-10-01T00:00:00")
        self.assertEqual(account["balance"], 100)

    def test_keyring_reads_previous_key_and_writes_only_active_key(self):
        old = DataCipher("old", {"old": b"a" * 32})
        rotated = DataCipher("new", {"old": b"a" * 32, "new": b"b" * 32})
        context = {"table": "test", "user_id": 1}
        envelope = old.encrypt_fields({"value": 123.45}, context)
        self.assertEqual(rotated.decrypt_fields(envelope, context), {"value": 123.45})
        self.assertTrue(rotated.encrypt_fields({"value": 123.45}, context).startswith("fh1:new:"))
        with self.assertRaises(DataEncryptionError):
            old.decrypt_fields(envelope, {"table": "test", "user_id": 2})

    def test_encrypted_schema_is_required_before_initialization(self):
        with test_db.engine.begin() as connection:
            connection.execute(text("ALTER TABLE transactions ADD COLUMN value FLOAT"))
        with self.assertRaises(RuntimeError):
            database_service.ensure_encrypted_schema()

    def test_wsgi_requests_are_blocked_when_financial_schema_is_legacy(self):
        previous = test_app.config.pop("FINANCIAL_SCHEMA_READY", None)
        try:
            with test_db.engine.begin() as connection:
                connection.execute(text("ALTER TABLE transactions ADD COLUMN value FLOAT"))
            response = test_app.test_client().get("/transactions")
            self.assertEqual(response.status_code, 503)
            self.assertIn("manutenção", response.json["message"])
        finally:
            if previous is not None:
                test_app.config["FINANCIAL_SCHEMA_READY"] = previous
            else:
                test_app.config.pop("FINANCIAL_SCHEMA_READY", None)


class EncryptionMigrationTests(unittest.TestCase):
    def setUp(self):
        self.module_patch = patch.dict(sys.modules, isolated_modules)
        self.module_patch.start()
        self.context = test_app.app_context()
        self.context.push()
        self.temporary = TemporaryDirectory()
        self.directory = Path(self.temporary.name)
        self.path = self.directory / "original.db"
        self.engine = create_engine(f"sqlite:///{self.path.as_posix()}")
        self.sessions = scoped_session(sessionmaker(bind=self.engine))
        self.db_patch = patch.object(
            database_service, "db", SimpleNamespace(engine=self.engine, session=self.sessions)
        )
        self.db_patch.start()
        self.create_legacy_database()

    def tearDown(self):
        self.sessions.remove()
        self.engine.dispose()
        self.db_patch.stop()
        self.context.pop()
        self.module_patch.stop()
        self.temporary.cleanup()

    def create_legacy_database(self, subcategory=True):
        connection = sqlite3.connect(self.path)
        connection.executescript("""
            CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, email TEXT, password TEXT);
            INSERT INTO users VALUES (1, 'Pessoa', 'person@example.com', 'hash-preservado');
            CREATE TABLE accounts (
                id VARCHAR(36) PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id),
                type VARCHAR(50) NOT NULL, subtype VARCHAR(50) NOT NULL, itemId VARCHAR(36) NOT NULL,
                number VARCHAR(50) NOT NULL, name VARCHAR(100) NOT NULL,
                marketingName VARCHAR(100), owner VARCHAR(100), taxNumber VARCHAR(30),
                balance FLOAT NOT NULL, currencyCode VARCHAR(10) NOT NULL, bankData JSON, creditData JSON
            );
            CREATE TABLE transactions (
                id INTEGER PRIMARY KEY, external_id VARCHAR(100) UNIQUE,
                account_id INTEGER REFERENCES accounts(id), value FLOAT NOT NULL,
                date DATETIME NOT NULL, name VARCHAR(120) NOT NULL, category VARCHAR(50),
                subcategory VARCHAR(50), description VARCHAR(255), type VARCHAR(20) NOT NULL,
                user_id INTEGER NOT NULL REFERENCES users(id)
            );
            CREATE TABLE transaction_sync_protections (
                user_id INTEGER NOT NULL, external_id VARCHAR(100) NOT NULL,
                PRIMARY KEY (user_id, external_id)
            );
            INSERT INTO transaction_sync_protections VALUES (1, 'associada-excluida');
        """)
        connection.execute(
            "INSERT INTO accounts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "account",
                1,
                "BANK",
                "CHECKING_ACCOUNT",
                "item",
                "NUMERO-PRIVADO-UNICO",
                "CONTA-PRIVADA-UNICA",
                None,
                "TITULAR-PRIVADO-UNICO",
                "CPF-PRIVADO-UNICO",
                1500.0,
                "BRL",
                json.dumps({"accountNumber": "JSON-PRIVADO-UNICO"}),
                None,
            ),
        )
        for index, value in ((1, 100.1), (2, 0), (3, 1500.0)):
            connection.execute(
                "INSERT INTO transactions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    index,
                    f"tx-{index}" if index < 3 else "opening-balance:account",
                    "account",
                    value,
                    "2026-09-30 00:00:00.000000",
                    f"TRANSACAO-PRIVADA-UNICA-{index}",
                    "Extra" if index < 3 else "Saldo anterior",
                    None,
                    "DESCRICAO-PRIVADA-UNICA",
                    "income",
                    1,
                ),
            )
        if not subcategory:
            connection.execute("ALTER TABLE transactions DROP COLUMN subcategory")
        connection.commit()
        connection.close()

    def migrate(self):
        return database_service.encrypt_database(self.directory / "backups")

    def test_migration_preserves_all_records_and_encrypted_backup_is_restorable(self):
        before = self.path.read_bytes()
        result = self.migrate()
        self.assertTrue(result["changed"])
        self.assertEqual(result["counts"], {"accounts": 1, "transactions": 3})
        self.assertEqual(database_service.read_encrypted_backup(result["backup"]), before)
        self.assertNotIn(b"TRANSACAO-PRIVADA", result["backup"].read_bytes())
        self.assertNotIn(b"SQLite format", result["backup"].read_bytes())
        counts = database_service.verify_encrypted_database()
        self.assertEqual(counts, result["counts"])
        with closing(sqlite3.connect(self.path)) as connection:
            self.assertEqual(
                connection.execute("SELECT * FROM users").fetchone(),
                (1, "Pessoa", "person@example.com", "hash-preservado"),
            )
            self.assertEqual(
                connection.execute(
                    "SELECT external_id FROM transaction_sync_protections"
                ).fetchone()[0],
                "associada-excluida",
            )
            self.assertEqual(connection.execute("PRAGMA integrity_check").fetchone()[0], "ok")
            self.assertEqual(connection.execute("PRAGMA foreign_key_check").fetchall(), [])
        restored = self.directory / "restored.db"
        database_service.restore_encrypted_backup(result["backup"], restored)
        with closing(sqlite3.connect(restored)) as connection:
            self.assertEqual(
                connection.execute("SELECT count(*) FROM transactions").fetchone()[0], 3
            )
            self.assertIn(
                "encrypted_data",
                {row[1] for row in connection.execute("PRAGMA table_info(transactions)")},
            )
        self.assertNotIn(b"TRANSACAO-PRIVADA", restored.read_bytes())
        with self.assertRaises(FileExistsError):
            database_service.restore_encrypted_backup(result["backup"], restored)

    def test_old_plaintext_is_absent_from_database_file_after_vacuum(self):
        self.migrate()
        content = self.path.read_bytes()
        for marker in (
            b"TRANSACAO-PRIVADA",
            b"DESCRICAO-PRIVADA",
            b"TITULAR-PRIVADO",
            b"CPF-PRIVADO",
            b"JSON-PRIVADO",
            b"NUMERO-PRIVADO",
            b"CONTA-PRIVADA",
        ):
            self.assertNotIn(marker, content)
        self.assertFalse(Path(str(self.path) + "-wal").exists())
        self.assertFalse(Path(str(self.path) + "-journal").exists())

    def test_second_migration_verifies_without_reencrypting_or_creating_backup(self):
        first = self.migrate()
        with closing(sqlite3.connect(self.path)) as connection:
            before = connection.execute("SELECT encrypted_data FROM transactions").fetchall()
        second = self.migrate()
        with closing(sqlite3.connect(self.path)) as connection:
            after = connection.execute("SELECT encrypted_data FROM transactions").fetchall()
        self.assertFalse(second["changed"])
        self.assertIsNone(second["backup"])
        self.assertEqual(before, after)
        self.assertTrue(first["backup"].exists())

    def test_failure_rolls_back_every_table_without_changing_financial_content(self):
        original = database_service._encode_legacy_row

        def fail_transaction(model, raw):
            if model is Transaction:
                raise RuntimeError("Falha simulada")
            return original(model, raw)

        with patch.object(database_service, "_encode_legacy_row", side_effect=fail_transaction):
            with self.assertRaises(RuntimeError):
                self.migrate()
        with closing(sqlite3.connect(self.path)) as connection:
            self.assertEqual(
                connection.execute("SELECT balance FROM accounts").fetchone()[0], 1500.0
            )
            self.assertEqual(
                connection.execute("SELECT count(*) FROM transactions").fetchone()[0], 3
            )
            self.assertFalse(
                any(
                    "encrypted" in row[0]
                    for row in connection.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    )
                )
            )
        self.assertEqual(len(list((self.directory / "backups").glob("*.fhbackup"))), 1)

    def test_migration_accepts_legacy_database_without_subcategory_column(self):
        with closing(sqlite3.connect(self.path)) as connection:
            connection.execute("ALTER TABLE transactions DROP COLUMN subcategory")
        self.migrate()
        self.assertEqual(database_service.verify_encrypted_database()["transactions"], 3)

    def test_custom_financial_indexes_are_not_silently_removed(self):
        with closing(sqlite3.connect(self.path)) as connection:
            connection.execute("CREATE INDEX custom_date_index ON transactions(date)")
        with self.assertRaises(RuntimeError):
            self.migrate()
        with closing(sqlite3.connect(self.path)) as connection:
            self.assertEqual(
                connection.execute("SELECT count(*) FROM transactions").fetchone()[0], 3
            )
            self.assertEqual(
                connection.execute("SELECT balance FROM accounts").fetchone()[0], 1500.0
            )

    def test_locked_database_is_not_migrated(self):
        locked = sqlite3.connect(self.path, isolation_level=None)
        locked.execute("BEGIN EXCLUSIVE")
        try:
            with self.assertRaises(sqlite3.OperationalError):
                self.migrate()
        finally:
            locked.execute("ROLLBACK")
            locked.close()
        self.assertFalse((self.directory / "backups").exists())

    def test_wal_is_checkpointed_before_migration(self):
        with closing(sqlite3.connect(self.path)) as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("UPDATE transactions SET name='WAL-PRIVADO-UNICO' WHERE id=1")
            connection.commit()
        self.migrate()
        self.assertNotIn(b"WAL-PRIVADO-UNICO", self.path.read_bytes())
        self.assertFalse(Path(str(self.path) + "-wal").exists())

    def test_unknown_key_blocks_verification_and_repeat_migration(self):
        self.migrate()
        original = test_app.extensions["financial_data_cipher"]
        try:
            test_app.extensions["financial_data_cipher"] = DataCipher("other", {"other": b"q" * 32})
            with self.assertRaises(DataEncryptionError):
                database_service.verify_encrypted_database()
            with self.assertRaises(DataEncryptionError):
                self.migrate()
        finally:
            test_app.extensions["financial_data_cipher"] = original


if __name__ == "__main__":
    unittest.main()

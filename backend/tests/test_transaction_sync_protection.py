"""Testa edições, associações e sincronização em um banco SQLite isolado."""

import sys
import unittest
from datetime import datetime
from types import ModuleType
from unittest.mock import patch

from flask import Flask
from flask_sqlalchemy import SQLAlchemy

test_app = Flask(__name__)
test_app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
test_db = SQLAlchemy(test_app)
config_stub = ModuleType("config")
config_stub.db = test_db

with patch.dict(sys.modules, {"config": config_stub}):
    from exceptions.api_errors import ValidationError
    from models.account import Account
    from models.transaction import Transaction
    from models.transaction_sync_protection import TransactionSyncProtection
    from models.user import User
    from repositories.transaction_repository import TransactionRepository
    from services.transaction_service import TransactionService


class TransactionSyncProtectionTests(unittest.TestCase):
    def setUp(self):
        self.context = test_app.app_context()
        self.context.push()
        test_db.create_all()
        test_db.session.add(User(id=1, name="Teste", email="teste@example.com", password="test"))
        test_db.session.add(
            Account(
                id="account",
                user_id=1,
                type="BANK",
                subtype="CHECKING_ACCOUNT",
                itemId="item",
                number="123",
                name="Conta",
            )
        )
        test_db.session.commit()
        self.service = TransactionService()

    def tearDown(self):
        test_db.session.remove()
        test_db.drop_all()
        self.context.pop()

    def transaction(self, external_id=None, value=100):
        transaction = Transaction(
            external_id=external_id,
            account_id="account",
            user_id=1,
            date=datetime(2026, 10, 1),
            name="Original",
            value=value,
            category="Extra",
            description="",
            type="income",
        )
        test_db.session.add(transaction)
        test_db.session.commit()
        return transaction

    def sync(self, external_id, amount=200):
        return self.service.sync_transaction(
            {
                "id": external_id,
                "amount": amount,
                "date": "2026-10-02",
                "description": "Banco",
                "type": "CREDIT",
            },
            "account",
            1,
        )

    def test_edited_fields_are_preserved_across_repeated_sync(self):
        transaction = self.transaction("edited")
        self.service.update_transaction(
            transaction.id,
            {
                "name": "Editado",
                "value": 80,
                "category": "Moradia",
                "date": "2026-09-01",
                "type": "expense",
                "description": "Manual",
            },
        )
        before = transaction.to_json()
        for _ in range(2):
            self.assertIsNone(self.sync("edited"))
        test_db.session.expire_all()
        self.assertEqual(transaction.to_json(), before)
        self.assertEqual(Transaction.query.count(), 1)

    def test_category_only_edit_protects_the_entire_transaction(self):
        transaction = self.transaction("category")
        self.service.update_transaction(transaction.id, {"category": "Moradia"})
        self.assertIsNone(self.sync("category"))
        self.assertEqual(transaction.value, 100)
        self.assertEqual(transaction.category, "Moradia")

    def test_association_protects_both_ids_and_prevents_recreation(self):
        kept = self.transaction("first")
        removed = self.transaction("second", 50)
        removed_id = removed.id
        self.service.associate_transaction(
            1,
            kept.id,
            removed.id,
            {
                "name": "Associadas",
                "value": 150,
                "type": "income",
            },
        )
        for external_id in ("first", "second"):
            self.assertIsNone(self.sync(external_id))
        self.assertIsNone(test_db.session.get(Transaction, removed_id))
        self.assertEqual(kept.value, 150)
        self.assertEqual(Transaction.query.count(), 1)

    def test_chained_associations_with_manual_survivor_preserve_all_external_ids(self):
        manual = self.transaction()
        for external_id in ("first", "second"):
            other = self.transaction(external_id)
            self.service.associate_transaction(1, manual.id, other.id, {"value": 200})
        test_db.session.remove()
        for external_id in ("first", "second"):
            self.assertIsNone(self.sync(external_id))
        self.assertEqual(Transaction.query.count(), 1)

    def test_unedited_transactions_still_update_and_new_transactions_are_created(self):
        original = self.transaction("unedited")
        self.assertEqual(self.sync("unedited").id, original.id)
        self.assertEqual(original.value, 200)
        self.assertIsNotNone(self.sync("new"))
        self.assertEqual(Transaction.query.count(), 2)

    def test_failed_association_rolls_back_edits_deletion_and_protections(self):
        kept = self.transaction("first")
        removed = self.transaction("second")
        with patch.object(test_db.session, "commit", side_effect=RuntimeError("Falha simulada")):
            with self.assertRaises(RuntimeError):
                self.service.associate_transaction(1, kept.id, removed.id, {"value": 150})
        self.assertEqual(kept.value, 100)
        self.assertEqual(Transaction.query.count(), 2)
        self.assertEqual(TransactionSyncProtection.query.count(), 0)
        with self.assertRaises(ValidationError):
            self.service.associate_transaction(1, kept.id, kept.id, {"value": 150})

    def test_initialization_preserves_existing_external_transactions_only_once(self):
        self.transaction("legacy")
        self.transaction()
        TransactionSyncProtection.__table__.drop(test_db.engine)
        TransactionRepository.initialize_sync_protection()
        self.assertIsNone(self.sync("legacy"))
        self.assertEqual(TransactionSyncProtection.query.count(), 1)
        fresh = self.sync("fresh")
        TransactionRepository.initialize_sync_protection()
        self.assertEqual(self.sync("fresh", 300).id, fresh.id)
        self.assertEqual(fresh.value, 300)

    def test_protection_is_scoped_to_the_user(self):
        test_db.session.add(User(id=2, name="Outro", email="outro@example.com", password="test"))
        test_db.session.commit()
        test_db.session.add(TransactionSyncProtection(user_id=2, external_id="shared"))
        test_db.session.commit()
        self.assertIsNotNone(self.sync("shared"))

    def test_initialization_works_on_a_fresh_database(self):
        test_db.session.remove()
        test_db.drop_all()
        TransactionRepository.initialize_sync_protection()
        self.assertEqual(Transaction.query.count(), 0)
        self.assertEqual(TransactionSyncProtection.query.count(), 0)

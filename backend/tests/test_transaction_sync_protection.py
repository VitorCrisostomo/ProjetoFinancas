"""Testa edições, associações e sincronização em um banco SQLite isolado."""

import sys
import unittest
from datetime import date, datetime, timedelta
from types import ModuleType
from unittest.mock import Mock, patch

from flask import Flask
from flask_sqlalchemy import SQLAlchemy

test_app = Flask(__name__)
test_app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
test_db = SQLAlchemy(test_app)
config_stub = ModuleType("config")
config_stub.db = test_db
jwt_stub = ModuleType("flask_jwt_extended")
jwt_stub.jwt_required = lambda: lambda function: function
jwt_stub.get_jwt_identity = lambda: "1"
requests_stub = ModuleType("requests")
requests_stub.get = Mock()
requests_stub.post = Mock()
requests_stub.RequestException = RuntimeError

with patch.dict(
    sys.modules,
    {
        "config": config_stub,
        "flask_jwt_extended": jwt_stub,
        "requests": requests_stub,
    },
):
    from exceptions.api_errors import ValidationError
    from models.account import Account
    from models.transaction import Transaction
    from models.transaction_sync_protection import TransactionSyncProtection
    from models.user import User
    from repositories.transaction_repository import TransactionRepository
    from routes import pluggy_route
    from services.account_service import AccountService
    from services.transaction_service import TransactionService

test_app.register_blueprint(pluggy_route.pluggy_routes)


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

    def test_opening_balance_matches_account_total_and_is_not_duplicated(self):
        self.transaction("income", 300)
        expense = self.transaction("expense", 50)
        expense.type = "expense"
        expense.date = datetime(2026, 4, 15)
        account = test_db.session.get(Account, "account")
        account.balance = 1000
        opening = self.service.reconcile_opening_balance(account)
        self.assertEqual(opening.value, 750)
        self.assertEqual(opening.type, "income")
        self.assertEqual(opening.date, datetime(2026, 3, 31))
        self.assertTrue(opening.to_json()["is_opening_balance"])
        self.assertEqual(self.service.reconcile_opening_balance(account).id, opening.id)
        self.assertEqual(Transaction.query.count(), 3)
        total = sum(t.value if t.type == "income" else -t.value for t in Transaction.query.all())
        self.assertEqual(total, account.balance)

    def test_new_connection_creates_only_the_local_opening_adjustment(self):
        account = AccountService().sync_account(
            {
                "id": "new-account",
                "type": "BANK",
                "subtype": "CHECKING_ACCOUNT",
                "itemId": "item",
                "number": "123",
                "name": "Nova",
                "balance": 28771.90,
            },
            1,
        )
        transactions = Transaction.query.filter_by(account_id=account.id).all()
        self.assertEqual(len(transactions), 1)
        self.assertTrue(transactions[0].is_opening_balance)
        self.assertEqual(transactions[0].value, 28771.90)
        self.assertEqual(
            transactions[0].date,
            datetime.combine(date.today().replace(day=1), datetime.min.time()) - timedelta(days=1),
        )

    def test_reconnection_rebases_using_the_new_balance_without_changing_edited_transactions(self):
        transaction = self.transaction("edited", 100)
        self.service.update_transaction(transaction.id, {"name": "Preservada", "value": 80})
        account_service = AccountService()
        account_service.sync_account({"id": "account", "balance": 1000}, 1)
        opening = Transaction.query.filter_by(external_id="opening-balance:account").one()
        self.assertEqual(opening.value, 920)
        account_service.sync_account({"id": "account", "balance": 1200}, 1)
        self.assertEqual(opening.value, 1120)
        self.assertEqual(transaction.value, 80)
        self.assertEqual(transaction.name, "Preservada")
        self.assertIsNone(self.sync("edited"))
        self.assertEqual(Transaction.query.count(), 2)

    def test_older_import_moves_and_recalculates_the_same_adjustment(self):
        account = test_db.session.get(Account, "account")
        account.balance = 1000
        opening = self.service.reconcile_opening_balance(account, reference_date=date(2026, 10, 1))
        self.assertEqual(opening.date, datetime(2026, 9, 30))
        transaction = self.transaction("older", 200)
        transaction.date = datetime(2024, 3, 1)
        self.assertEqual(self.service.reconcile_opening_balance(account).id, opening.id)
        self.assertEqual(opening.date, datetime(2024, 2, 29))
        self.assertEqual(opening.value, 800)
        transaction.date = datetime(2024, 1, 1)
        self.service.reconcile_opening_balance(account)
        self.assertEqual(opening.date, datetime(2023, 12, 31))

    def test_negative_credit_balance_and_cent_precision(self):
        account = test_db.session.get(Account, "account")
        account.type = "CREDIT"
        account.balance = -748.60
        expense = self.transaction("expense", 48.60)
        expense.type = "expense"
        opening = self.service.reconcile_opening_balance(account)
        self.assertEqual(opening.type, "expense")
        self.assertEqual(opening.value, 700)
        account.balance = 0.30
        expense.value = 0.20
        expense.type = "income"
        self.service.reconcile_opening_balance(account)
        self.assertEqual(opening.value, 0.10)
        self.assertEqual(opening.type, "income")

    def test_reconciliation_is_scoped_to_the_account_and_preserves_manual_opening(self):
        manual = self.transaction(None, 100)
        manual.name = "Saldo anterior"
        manual.date = datetime(2026, 4, 14)
        test_db.session.add(User(id=2, name="Outro", email="outro@example.com", password="test"))
        test_db.session.commit()
        other_user = self.transaction("other", 999)
        other_user.user_id = 2
        unlinked = self.transaction(None, 500)
        unlinked.account_id = None
        account = test_db.session.get(Account, "account")
        account.balance = 1000
        opening = self.service.reconcile_opening_balance(account)
        self.assertEqual(opening.value, 900)
        self.assertEqual(opening.date, datetime(2026, 3, 31))
        self.assertEqual(manual.value, 100)
        self.assertEqual(other_user.value, 999)
        self.assertEqual(unlinked.value, 500)

    def test_automatic_adjustment_cannot_be_edited_deleted_or_associated(self):
        opening = self.service.reconcile_opening_balance(test_db.session.get(Account, "account"))
        transaction = self.transaction("normal")
        with self.assertRaises(ValidationError):
            self.service.update_transaction(opening.id, {"value": 200})
        with self.assertRaises(ValidationError):
            self.service.delete_transaction(opening.id)
        with self.assertRaises(ValidationError):
            self.service.associate_transaction(1, transaction.id, opening.id, {"value": 200})
        self.assertEqual(Transaction.query.count(), 2)

    def test_account_and_adjustment_roll_back_together_on_failure(self):
        with patch.object(test_db.session, "commit", side_effect=RuntimeError("Falha simulada")):
            with self.assertRaises(RuntimeError):
                AccountService().sync_account({"id": "account", "balance": 1000}, 1)
        self.assertEqual(test_db.session.get(Account, "account").balance, 0)
        self.assertEqual(Transaction.query.count(), 0)

    def test_monthly_sync_refreshes_balance_and_rebases_without_overwriting_edits(self):
        edited = self.transaction("edited", 100)
        self.service.update_transaction(edited.id, {"name": "Manual", "value": 80})
        self.service.reconcile_opening_balance(test_db.session.get(Account, "account"))
        with (
            patch.object(
                pluggy_route.pluggy_service,
                "get_accounts_from_item",
                return_value=[
                    {"id": "account", "balance": 1000},
                ],
            ) as fetch_accounts,
            patch.object(
                pluggy_route.pluggy_service,
                "get_transactions_for_account",
                return_value=[
                    {"id": "edited", "amount": 999, "description": "Banco"},
                    {"id": "new", "amount": 200, "description": "Banco", "date": "2026-04-15"},
                ],
            ) as fetch_transactions,
        ):
            result = test_app.test_client().post(
                "/pluggy/transactions/sync",
                json={
                    "mode": "month",
                    "month": 4,
                    "year": 2026,
                },
            )
        self.assertEqual(result.status_code, 200, result.get_json())
        fetch_accounts.assert_called_once_with("item")
        fetch_transactions.assert_called_once_with(
            "account",
            date_from="2026-04-01",
            date_to="2026-04-30",
        )
        self.assertEqual(len(result.get_json()["transactions"]), 1)
        self.assertEqual(edited.value, 80)
        self.assertEqual(edited.name, "Manual")
        opening = Transaction.query.filter_by(external_id="opening-balance:account").one()
        self.assertEqual(opening.value, 720)
        self.assertEqual(opening.date, datetime(2026, 3, 31))
        self.assertEqual(test_db.session.get(Account, "account").balance, 1000)

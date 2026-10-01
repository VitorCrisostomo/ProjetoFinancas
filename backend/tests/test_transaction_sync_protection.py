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
    from routes import pluggy_route, transaction_route
    from services.account_service import AccountService
    from services.transaction_service import TransactionService

test_app.register_blueprint(pluggy_route.pluggy_routes)
test_app.register_blueprint(transaction_route.transaction_routes)


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
                "category": "Moradia",
                "date": "2026-09-01",
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

    def test_equal_income_and_expense_can_be_associated_with_zero_balance(self):
        income = self.transaction("income", 100)
        expense = self.transaction("expense", 100)
        expense.type = "expense"
        test_db.session.commit()
        associated = self.service.associate_transaction(
            1,
            income.id,
            expense.id,
            {
                "name": "Receita / Despesa",
                "value": 0,
                "type": "income",
            },
        )
        self.assertEqual(associated.to_json()["value"], 0)
        self.assertEqual(Transaction.query.count(), 1)
        self.assertIsNone(self.sync("income"))
        self.assertIsNone(self.sync("expense"))
        self.service.update_transaction(associated.id, {"name": "Conferida"})
        self.assertEqual(associated.value, 0)

    def test_reassociated_zero_transactions_preserve_every_original_id_after_session_reload(self):
        first = self.transaction("first", 100)
        second = self.transaction("second", 100)
        second.type = "expense"
        test_db.session.commit()
        self.service.associate_transaction(1, first.id, second.id, {"value": 0, "type": "income"})
        third = self.transaction("third", 50)
        # Troca a transação mantida: o resultado anterior passa a ser o lançamento excluído.
        self.service.associate_transaction(1, third.id, first.id, {"value": 50, "type": "income"})
        fourth = self.transaction("fourth", 50)
        fourth.type = "expense"
        test_db.session.commit()
        result = self.service.associate_transaction(
            1,
            third.id,
            fourth.id,
            {
                "value": 0,
                "type": "income",
                "name": "Todas associadas",
            },
        )
        saved_id, saved_json = result.id, result.to_json()
        test_db.session.remove()
        for _ in range(2):
            for external_id in ("first", "second", "third", "fourth"):
                self.assertIsNone(self.sync(external_id))
        self.assertEqual(Transaction.query.count(), 1)
        self.assertEqual(TransactionSyncProtection.query.count(), 4)
        self.assertEqual(test_db.session.get(Transaction, saved_id).to_json(), saved_json)
        self.assertIsNotNone(self.sync("new"))

    def test_update_still_rejects_missing_or_boolean_values(self):
        transaction = self.transaction("original", 100)
        for value in (None, "", False, True):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                self.service.update_transaction(transaction.id, {"value": value})
        self.assertEqual(transaction.value, 100)

    def test_public_update_allows_only_metadata_and_preserves_financial_fields(self):
        transaction = self.transaction("original", 100)
        client = test_app.test_client()
        for data in (
            {"value": 0},
            {"value": 80},
            {"type": "expense"},
            {"description": "Manual"},
            {"name": "Inválida", "value": 99},
            {},
            [],
        ):
            with self.subTest(data=data):
                response = client.patch(f"/update_transactions/{transaction.id}", json=data)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(transaction.name, "Original")
                self.assertEqual(transaction.value, 100)
                self.assertEqual(transaction.type, "income")
        response = client.patch(
            f"/update_transactions/{transaction.id}",
            json={
                "name": "Conferida",
                "date": "2026-09-30",
                "category": "Moradia",
            },
        )
        self.assertEqual(response.status_code, 200, response.get_json())
        self.assertEqual(transaction.name, "Conferida")
        self.assertEqual(transaction.category, "Moradia")
        self.assertEqual(transaction.value, 100)
        self.assertEqual(transaction.type, "income")

    def test_public_update_cannot_edit_another_users_transaction(self):
        transaction = self.transaction("other")
        test_db.session.add(User(id=2, name="Outro", email="outro@example.com", password="test"))
        transaction.user_id = 2
        test_db.session.commit()
        response = test_app.test_client().patch(
            f"/update_transactions/{transaction.id}",
            json={
                "name": "Não permitido",
            },
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(transaction.name, "Original")

    def test_creation_import_and_deletion_endpoints_are_removed(self):
        transaction = self.transaction("existing")
        client = test_app.test_client()
        self.assertEqual(client.post("/create_transactions", json={"value": 100}).status_code, 404)
        self.assertEqual(client.post("/transactions/import").status_code, 404)
        self.assertEqual(client.delete(f"/transactions/{transaction.id}").status_code, 404)
        self.assertEqual(Transaction.query.count(), 1)

    def test_legacy_association_endpoint_cannot_override_the_calculated_balance(self):
        first = self.transaction("first", 100)
        second = self.transaction("second", 40)
        second.type = "expense"
        test_db.session.commit()
        response = test_app.test_client().post(
            "/transactions/associate",
            json={
                "keep_id": first.id,
                "remove_id": second.id,
                "updated_data": {"value": 9999, "type": "expense", "name": "Associadas"},
            },
        )
        self.assertEqual(response.status_code, 200, response.get_json())
        self.assertEqual(response.get_json()["value"], 60)
        self.assertEqual(response.get_json()["type"], "income")

    def test_batch_association_calculates_the_total_and_protects_every_identifier(self):
        first = self.transaction("first", 100)
        second = self.transaction("second", 40)
        second.type = "expense"
        third = self.transaction("third", 20)
        third.type = "expense"
        fourth = self.transaction("fourth", 10)
        test_db.session.commit()
        selected = [first.id, second.id, third.id, fourth.id]
        result = test_app.test_client().post(
            "/transactions/associate",
            json={
                "transaction_ids": selected,
                "updated_data": {"value": 999, "type": "expense"},
            },
        )
        self.assertEqual(result.status_code, 200, result.get_json())
        self.assertEqual(result.get_json()["id"], first.id)
        self.assertEqual(result.get_json()["value"], 50)
        self.assertEqual(result.get_json()["type"], "income")
        self.assertEqual(Transaction.query.count(), 1)
        self.assertEqual(TransactionSyncProtection.query.count(), 4)
        test_db.session.remove()
        for external_id in ("first", "second", "third", "fourth"):
            self.assertIsNone(self.sync(external_id))

    def test_batch_association_can_be_zero_or_negative_and_associated_again(self):
        first = self.transaction("first", 0.10)
        second = self.transaction("second", 0.20)
        third = self.transaction("third", 0.30)
        third.type = "expense"
        test_db.session.commit()
        merged = self.service.associate_transactions(1, [first.id, second.id, third.id], {})
        self.assertEqual(merged.value, 0)
        fourth = self.transaction("fourth", 5)
        fourth.type = "expense"
        fifth = self.transaction("fifth", 2)
        test_db.session.commit()
        merged = self.service.associate_transactions(1, [first.id, fourth.id, fifth.id], {})
        self.assertEqual(merged.value, 3)
        self.assertEqual(merged.type, "expense")
        self.assertEqual(TransactionSyncProtection.query.count(), 5)
        for external_id in ("first", "second", "third", "fourth", "fifth"):
            self.assertIsNone(self.sync(external_id))
        self.assertEqual(Transaction.query.count(), 1)

    def test_batch_association_rejects_invalid_selection_without_partial_changes(self):
        first = self.transaction("first")
        second = self.transaction("second")
        opening = self.service.reconcile_opening_balance(test_db.session.get(Account, "account"))
        for selected in (
            [],
            [first.id],
            [first.id, first.id],
            "invalid",
            [True, second.id],
            [first.id, opening.id],
            [first.id, second.id, 999],
        ):
            with self.subTest(selected=selected):
                response = test_app.test_client().post(
                    "/transactions/associate",
                    json={
                        "transaction_ids": selected,
                    },
                )
                self.assertIn(response.status_code, (400, 404))
                self.assertEqual(Transaction.query.count(), 3)
                self.assertEqual(TransactionSyncProtection.query.count(), 0)
                self.assertEqual(first.value, 100)

    def test_batch_association_rejects_another_users_transaction(self):
        first = self.transaction("first")
        second = self.transaction("second")
        other = self.transaction("other")
        test_db.session.add(User(id=2, name="Outro", email="outro@example.com", password="test"))
        other.user_id = 2
        test_db.session.commit()
        response = test_app.test_client().post(
            "/transactions/associate",
            json={
                "transaction_ids": [first.id, second.id, other.id],
            },
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(Transaction.query.count(), 3)
        self.assertEqual(TransactionSyncProtection.query.count(), 0)

    def test_batch_association_rolls_back_the_entire_selection_if_commit_fails(self):
        transactions = [self.transaction(f"transaction-{index}") for index in range(4)]
        with patch.object(test_db.session, "commit", side_effect=RuntimeError("Falha simulada")):
            with self.assertRaises(RuntimeError):
                self.service.associate_transactions(1, [t.id for t in transactions], {})
        self.assertEqual(Transaction.query.count(), 4)
        self.assertEqual(TransactionSyncProtection.query.count(), 0)
        self.assertTrue(all(t.value == 100 for t in transactions))

    def test_reserve_reference_is_categorized_as_investment_in_text_and_nested_fields(self):
        cases = [
            {"description": "Aplicação RF RESERVA COFR automática"},
            {"name": "rf reserva cofr", "description": None, "merchant": None},
            {"observation": "Resgate rf   reserva\tcofr"},
            {"descriptionRaw": "RF RESERVA COFR"},
            {"merchant": {"name": "RF RESERVA COFR"}},
            {"paymentData": {"receiver": {"name": "RF RESERVA COFR"}}},
            {"details": [{"description": "RF RESERVA COFR"}, None, 1]},
        ]
        for index, fields in enumerate(cases):
            with self.subTest(fields=fields):
                transaction = self.service.sync_transaction(
                    {
                        "id": f"reserve-{index}",
                        "amount": -100,
                        "type": "DEBIT",
                        "date": "2026-10-01",
                        "description": "Banco",
                        "category": "Transfers",
                        **fields,
                    },
                    "account",
                    1,
                )
                self.assertEqual(transaction.category, "Investimentos")
                self.assertEqual(transaction.type, "expense")
                self.assertEqual(transaction.value, 100)

    def test_reserve_rule_updates_unedited_transactions_but_preserves_edited_categories(self):
        transaction = self.transaction("reserve")
        data = {"id": "reserve", "amount": 100, "description": "Resgate RF RESERVA COFR"}
        self.assertEqual(
            self.service.sync_transaction(data, "account", 1).category, "Investimentos"
        )
        self.service.update_transaction(transaction.id, {"category": "Extra"})
        self.assertIsNone(self.service.sync_transaction(data, "account", 1))
        self.assertEqual(transaction.category, "Extra")
        self.assertEqual(Transaction.query.count(), 1)

    def test_other_bank_transactions_keep_the_existing_category_mapping(self):
        transaction = self.service.sync_transaction(
            {
                "id": "groceries",
                "amount": -100,
                "description": "Reserva diferente",
                "category": "Groceries",
                "merchant": None,
            },
            "account",
            1,
        )
        self.assertEqual(transaction.category, "Alimentação")

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
        transaction = self.transaction("edited", 80)
        self.service.update_transaction(transaction.id, {"name": "Preservada"})
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
        self.assertEqual(
            test_app.test_client().delete(f"/transactions/{opening.id}").status_code, 404
        )
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
        edited = self.transaction("edited", 80)
        self.service.update_transaction(edited.id, {"name": "Manual"})
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

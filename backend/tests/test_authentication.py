"""Exercita JWT, cookies, CSRF e isolamento real em SQLite em memória."""

import sys
import time
import unittest
from datetime import datetime, timedelta
from types import ModuleType
from unittest.mock import Mock, patch

from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token, decode_token
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

test_app = Flask(__name__)
test_app.config.update(
    TESTING=True,
    SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
    JWT_SECRET_KEY="test-only-secret-with-at-least-32-characters",
    JWT_TOKEN_LOCATION=["cookies"],
    JWT_COOKIE_SECURE=True,
    JWT_COOKIE_SAMESITE="Lax",
    JWT_COOKIE_CSRF_PROTECT=True,
    JWT_CSRF_IN_COOKIES=False,
    JWT_ACCESS_TOKEN_EXPIRES=timedelta(hours=8),
    AUTH_ALLOWED_ORIGINS=["http://localhost:5173"],
    AUTH_LOGIN_WINDOW_SECONDS=900,
    AUTH_LOGIN_EMAIL_LIMIT=5,
    AUTH_LOGIN_ADDRESS_LIMIT=20,
)
test_db = SQLAlchemy(test_app)
test_jwt = JWTManager(test_app)
config_stub = ModuleType("config")
config_stub.app, config_stub.db, config_stub.jwt = test_app, test_db, test_jwt

# Apenas a configuração é substituída. JWT, cookies e decoradores são reais.
with patch.dict(sys.modules, {"config": config_stub}):
    from exceptions.api_errors import APIError
    from main import initialize_database
    from models.account import Account
    from models.auth_session import AuthSession, LoginAttempt, UserSecurity
    from models.category import Category, Subcategory
    from models.transaction import Transaction
    from models.transaction_sync_protection import TransactionSyncProtection
    from models.user import User
    from routes.pluggy_route import pluggy_service
    from services.auth_service import AuthService
    from services.transaction_service import TransactionService
    from services.user_service import UserService

    isolated_modules = {
        name: module
        for name, module in sys.modules.items()
        if name == "config"
        or name == "main"
        or name.startswith(("models", "routes", "services", "repositories", "exceptions"))
    }


PASSWORD = "senha-de-teste-123"
PASSWORD_HASH = generate_password_hash(PASSWORD)


class AuthenticationTests(unittest.TestCase):
    def setUp(self):
        self.module_patch = patch.dict(sys.modules, isolated_modules)
        self.module_patch.start()
        self.context = test_app.app_context()
        self.context.push()
        # O SQLite real aplica suas chaves estrangeiras nestes testes.
        with test_db.engine.connect() as connection:
            connection.exec_driver_sql("PRAGMA foreign_keys=ON")
        test_db.create_all()
        for user_id in (1, 2):
            test_db.session.add(
                User(
                    id=user_id,
                    name=f"Pessoa {user_id}",
                    email=f"user{user_id}@example.com",
                    password=PASSWORD_HASH,
                    is_verified=True,
                )
            )
        test_db.session.commit()
        for user_id in (1, 2):
            test_db.session.add(
                Account(
                    id=f"account-{user_id}",
                    user_id=user_id,
                    type="BANK",
                    subtype="CHECKING_ACCOUNT",
                    itemId=f"item-{user_id}",
                    number="123",
                    name=f"Conta {user_id}",
                    balance=100,
                )
            )
        test_db.session.commit()
        for user_id in (1, 2):
            test_db.session.add(
                Transaction(
                    id=user_id,
                    external_id=f"external-{user_id}",
                    account_id=f"account-{user_id}",
                    user_id=user_id,
                    date=datetime(2026, 10, 1),
                    name=f"Lançamento {user_id}",
                    value=100,
                    type="income",
                    category="Extra",
                )
            )
            test_db.session.add(
                Category(
                    id=user_id,
                    user_id=user_id,
                    name=f"Privada {user_id}",
                    normalized_name=f"privada {user_id}",
                )
            )
        test_db.session.commit()
        for user_id in (1, 2):
            test_db.session.add(
                Subcategory(
                    category_id=user_id,
                    name="Subcategoria",
                    normalized_name="subcategoria",
                )
            )
            test_db.session.add(
                TransactionSyncProtection(
                    user_id=user_id,
                    external_id=f"protected-{user_id}",
                )
            )
        test_db.session.commit()
        self.client = test_app.test_client()

    def tearDown(self):
        test_db.session.remove()
        test_db.drop_all()
        self.context.pop()
        self.module_patch.stop()

    def login(self, user_id=1, client=None):
        client = client or self.client
        result = client.post(
            "/login",
            json={
                "email": f"user{user_id}@example.com",
                "password": PASSWORD,
            },
        )
        self.assertEqual(result.status_code, 200, result.get_json())
        return result.get_json()["csrf_token"]

    def test_anonymous_requests_cannot_read_or_modify_data(self):
        for method, path in (
            ("GET", "/users"),
            ("GET", "/auth/session"),
            ("GET", "/accounts"),
            ("GET", "/transactions"),
            ("GET", "/categories"),
            ("PATCH", "/update_users/1"),
            ("DELETE", "/delete_users/1"),
            ("DELETE", "/accounts/account-1"),
            ("PATCH", "/update_transactions/1"),
            ("POST", "/transactions/associate"),
            ("POST", "/categories"),
            ("POST", "/categories/1/subcategories"),
            ("POST", "/pluggy/connect_token"),
            ("POST", "/pluggy/accounts/sync"),
            ("POST", "/pluggy/transactions/sync"),
        ):
            with self.subTest(path=path, method=method):
                result = self.client.open(path, method=method, json={})
                self.assertEqual(result.status_code, 401, result.get_json())

    def test_public_registration_and_verification_are_closed(self):
        for path in ("/create_users", "/verify_email"):
            result = self.client.post(
                path,
                json={
                    "name": "Ataque",
                    "email": "user1@example.com",
                    "password": "changed",
                    "code": "123456",
                },
            )
            self.assertEqual(result.status_code, 403)
        self.assertEqual(User.query.count(), 2)
        self.assertTrue(check_password_hash(test_db.session.get(User, 1).password, PASSWORD))

    def test_login_sets_protected_cookie_without_exposing_token(self):
        self.login()
        cookie = self.client.get_cookie("access_token_cookie")
        self.assertTrue(cookie.http_only)
        self.assertTrue(cookie.secure)
        self.assertEqual(cookie.same_site, "Lax")
        claims = decode_token(cookie.value)
        self.assertEqual(claims["exp"] - claims["iat"], 8 * 3600)
        self.assertEqual(AuthSession.query.count(), 1)
        result = self.client.get("/auth/session")
        self.assertEqual(result.status_code, 200)
        self.assertNotIn("access_token", result.get_json())
        self.assertNotIn("password", result.get_json()["user"])
        self.assertEqual(result.headers["Cache-Control"], "no-store")

    def test_old_bearer_tokens_and_unregistered_cookies_are_rejected(self):
        token = create_access_token(identity="1")
        result = self.client.get("/accounts", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(result.status_code, 401)
        self.client.set_cookie("access_token_cookie", token)
        self.assertEqual(self.client.get("/accounts").status_code, 401)

    def test_expired_signed_jwt_is_rejected(self):
        token = create_access_token(identity="1", expires_delta=timedelta(seconds=-1))
        self.client.set_cookie("access_token_cookie", token)
        self.assertEqual(self.client.get("/accounts").status_code, 401)

    def test_valid_cookie_restores_session_in_another_client(self):
        self.login()
        other = test_app.test_client()
        other.set_cookie("access_token_cookie", self.client.get_cookie("access_token_cookie").value)
        self.assertEqual(other.get("/auth/session").get_json()["user"]["id"], 1)

    def test_lists_are_isolated_and_profile_list_contains_only_self(self):
        for user_id in (1, 2):
            self.login(user_id)
            self.assertEqual(
                [user["id"] for user in self.client.get("/users").get_json()["users"]], [user_id]
            )
            self.assertEqual(
                [a["user_id"] for a in self.client.get("/accounts").get_json()], [user_id]
            )
            self.assertEqual(
                [t["user_id"] for t in self.client.get("/transactions").get_json()], [user_id]
            )
            names = [c["name"] for c in self.client.get("/categories").get_json()]
            self.assertIn(f"Privada {user_id}", names)
            self.assertNotIn(f"Privada {3 - user_id}", names)

    def test_csrf_is_required_and_must_match_the_session(self):
        self.login()
        for headers in ({}, {"X-CSRF-TOKEN": "invalid"}):
            result = self.client.post("/categories", json={"name": "Nova"}, headers=headers)
            self.assertEqual(result.status_code, 401)
        self.assertIsNone(Category.query.filter_by(name="Nova").first())

    def test_disallowed_origin_cannot_login_or_write_even_with_csrf(self):
        csrf = self.login()
        headers = {"Origin": "https://untrusted.example", "X-CSRF-TOKEN": csrf}
        result = self.client.post("/categories", json={"name": "Indevida"}, headers=headers)
        self.assertEqual(result.status_code, 403)
        self.assertEqual(
            self.client.post(
                "/login",
                json={
                    "email": "user1@example.com",
                    "password": PASSWORD,
                },
                headers=headers,
            ).status_code,
            403,
        )
        result = self.client.post(
            "/categories",
            json={"name": "Permitida"},
            headers={
                "Origin": "http://localhost:5173",
                "X-CSRF-TOKEN": csrf,
            },
        )
        self.assertEqual(result.status_code, 201)

    def test_user_cannot_change_or_delete_another_profile(self):
        csrf = self.login()
        for method, path in (("PATCH", "/update_users/2"), ("DELETE", "/delete_users/2")):
            result = self.client.open(
                path,
                method=method,
                headers={"X-CSRF-TOKEN": csrf},
                json={"current_password": PASSWORD, "name": "Ataque", "password": PASSWORD},
            )
            self.assertEqual(result.status_code, 404)
        self.assertEqual(test_db.session.get(User, 2).name, "Pessoa 2")

    def test_profile_change_requires_current_password_and_uses_name(self):
        csrf = self.login()
        for current in (None, "wrong"):
            result = self.client.patch(
                "/update_users/1",
                json={
                    "firstName": "Novo nome",
                    "current_password": current,
                },
                headers={"X-CSRF-TOKEN": csrf},
            )
            self.assertEqual(result.status_code, 403)
        result = self.client.patch(
            "/update_users/1",
            json={
                "name": "Novo nome",
                "current_password": PASSWORD,
            },
            headers={"X-CSRF-TOKEN": csrf},
        )
        self.assertEqual(result.status_code, 200)
        self.assertEqual(test_db.session.get(User, 1).name, "Novo nome")
        self.assertEqual(self.client.get("/auth/session").status_code, 200)

    def test_invalid_profile_fields_do_not_change_password_or_owner(self):
        csrf = self.login()
        for data in (
            {"name": "Changed", "password": "short"},
            {"name": "Changed", "user_id": 2},
            {"is_verified": True},
            {"name": []},
        ):
            result = self.client.patch(
                "/update_users/1",
                json={
                    **data,
                    "current_password": PASSWORD,
                },
                headers={"X-CSRF-TOKEN": csrf},
            )
            self.assertEqual(result.status_code, 400)
        self.assertEqual(test_db.session.get(User, 1).name, "Pessoa 1")
        self.assertEqual(test_db.session.get(User, 1).password, PASSWORD_HASH)

    def test_password_change_hashes_input_and_revokes_all_own_sessions(self):
        csrf = self.login()
        second = test_app.test_client()
        self.login(client=second)
        unrelated = test_app.test_client()
        self.login(2, client=unrelated)
        old_cookie = self.client.get_cookie("access_token_cookie").value
        result = self.client.patch(
            "/update_users/1",
            json={
                "password": "outra-senha-segura-123",
                "current_password": PASSWORD,
            },
            headers={"X-CSRF-TOKEN": csrf},
        )
        self.assertEqual(result.status_code, 200)
        saved = test_db.session.get(User, 1).password
        self.assertNotEqual(saved, "outra-senha-segura-123")
        self.assertTrue(check_password_hash(saved, "outra-senha-segura-123"))
        self.assertEqual(second.get("/accounts").status_code, 401)
        self.client.set_cookie("access_token_cookie", old_cookie)
        self.assertEqual(self.client.get("/accounts").status_code, 401)
        self.assertEqual(unrelated.get("/accounts").status_code, 200)
        self.assertEqual(
            self.client.post(
                "/login",
                json={
                    "email": "user1@example.com",
                    "password": "outra-senha-segura-123",
                },
            ).status_code,
            200,
        )

    def test_logout_revokes_replayed_cookie_but_preserves_other_device_session(self):
        csrf = self.login()
        second = test_app.test_client()
        self.login(client=second)
        old_cookie = self.client.get_cookie("access_token_cookie").value
        self.assertEqual(
            self.client.post("/logout", headers={"X-CSRF-TOKEN": csrf}).status_code, 200
        )
        self.client.set_cookie("access_token_cookie", old_cookie)
        self.assertEqual(self.client.get("/accounts").status_code, 401)
        self.assertEqual(second.get("/accounts").status_code, 200)

    def test_expired_tampered_disabled_and_deleted_users_cannot_use_session(self):
        self.login()
        cookie = self.client.get_cookie("access_token_cookie").value
        AuthSession.query.first().expires_at = int(time.time()) - 1
        test_db.session.commit()
        self.assertEqual(self.client.get("/accounts").status_code, 401)
        self.login()
        user = test_db.session.get(User, 1)
        user.is_verified = False
        test_db.session.commit()
        self.assertEqual(self.client.get("/accounts").status_code, 401)
        self.client.set_cookie("access_token_cookie", cookie[:-10] + "tampered")
        self.assertEqual(self.client.get("/accounts").status_code, 401)
        token = create_access_token(identity="999")
        claims = decode_token(token)
        # Identidade inexistente nunca deve chegar às consultas financeiras.
        self.client.set_cookie("access_token_cookie", token)
        self.assertEqual(self.client.get("/accounts").status_code, 401)
        self.assertNotEqual(claims["sub"], "1")

    def test_failed_login_limit_is_persistent_and_email_is_normalized(self):
        for _ in range(5):
            result = self.client.post(
                "/login",
                json={
                    "email": " USER1@EXAMPLE.COM ",
                    "password": "wrong",
                },
            )
            self.assertEqual(result.status_code, 401)
        fresh_client = test_app.test_client()
        result = fresh_client.post(
            "/login",
            json={
                "email": "user1@example.com",
                "password": PASSWORD,
            },
        )
        self.assertEqual(result.status_code, 429)
        self.assertEqual(LoginAttempt.query.count(), 5)
        self.assertNotIn("user1", LoginAttempt.query.first().email_key)
        LoginAttempt.query.update({"occurred_at": int(time.time()) - 901})
        test_db.session.commit()
        self.login()

    def test_address_limit_cannot_be_bypassed_by_switching_email_addresses(self):
        for index in range(20):
            AuthService().record_login_failure(f"attempt-{index}@example.com", "127.0.0.1")
        result = self.client.post(
            "/login",
            json={
                "email": "user1@example.com",
                "password": PASSWORD,
            },
            headers={"X-Forwarded-For": "203.0.113.1"},
        )
        self.assertEqual(result.status_code, 429)

    def test_own_deletion_requires_password_and_preserves_other_users_dependents(self):
        csrf = self.login()
        cookie = self.client.get_cookie("access_token_cookie").value
        result = self.client.delete("/delete_users/1", json={}, headers={"X-CSRF-TOKEN": csrf})
        self.assertEqual(result.status_code, 403)
        result = self.client.delete(
            "/delete_users/1",
            json={
                "current_password": PASSWORD,
            },
            headers={"X-CSRF-TOKEN": csrf},
        )
        self.assertEqual(result.status_code, 200)
        self.assertIsNone(test_db.session.get(User, 1))
        self.assertEqual(Account.query.count(), 1)
        self.assertEqual(Transaction.query.count(), 1)
        self.assertEqual(Category.query.count(), 1)
        self.assertEqual(Subcategory.query.count(), 1)
        self.assertEqual(TransactionSyncProtection.query.count(), 1)
        self.client.set_cookie("access_token_cookie", cookie)
        self.assertEqual(self.client.get("/accounts").status_code, 401)

    def test_foreign_financial_resources_cannot_be_changed_or_associated(self):
        csrf = self.login()
        for method, path, data in (
            ("DELETE", "/accounts/account-2", {}),
            ("PATCH", "/update_transactions/2", {"name": "Indevida"}),
            ("POST", "/transactions/associate", {"transaction_ids": [1, 2]}),
            ("POST", "/categories/2/subcategories", {"name": "Indevida"}),
        ):
            result = self.client.open(
                path, method=method, json=data, headers={"X-CSRF-TOKEN": csrf}
            )
            self.assertIn(result.status_code, (400, 404), result.get_json())
        self.assertEqual(test_db.session.get(Transaction, 2).name, "Lançamento 2")
        self.assertEqual(Transaction.query.count(), 2)

    def test_untrusted_client_cannot_submit_bank_account_data(self):
        csrf = self.login()
        result = self.client.post(
            "/accounts/sync",
            json={
                "id": "account-2",
                "balance": 99999,
                "user_id": 1,
            },
            headers={"X-CSRF-TOKEN": csrf},
        )
        self.assertEqual(result.status_code, 405)
        self.assertEqual(test_db.session.get(Account, "account-2").balance, 100)

    def test_sync_service_rejects_foreign_accounts_and_account_id_mismatch(self):
        service = TransactionService()
        for account_id, data in (
            ("account-2", {"id": "untrusted", "amount": 10}),
            ("account-1", {"id": "untrusted", "accountId": "account-2", "amount": 10}),
        ):
            with self.assertRaises(APIError):
                service.sync_transaction(data, account_id, 1)
        self.assertEqual(Transaction.query.count(), 2)

    def test_connect_token_uses_persistent_opaque_user_reference(self):
        csrf = self.login()
        response = Mock(status_code=200, json=Mock(return_value={"accessToken": "connect"}))
        with (
            patch.object(pluggy_service, "_get_api_key", return_value="test-key"),
            patch.object(
                pluggy_service.get_connect_token.__globals__["requests"],
                "post",
                return_value=response,
            ) as post,
        ):
            for _ in range(2):
                result = self.client.post("/pluggy/connect_token", headers={"X-CSRF-TOKEN": csrf})
                self.assertEqual(result.status_code, 200)
            reference = post.call_args.kwargs["json"]["options"]["clientUserId"]
            self.assertEqual(reference, test_db.session.get(UserSecurity, 1).pluggy_reference)
            self.assertNotEqual(reference, "1")
            self.assertEqual(post.call_args.kwargs["timeout"], 30)
        self.assertEqual(UserSecurity.query.count(), 1)
        self.assertEqual(Transaction.query.count(), 2)

    def test_foreign_or_unbound_item_is_rejected_before_fetching_accounts(self):
        csrf = self.login()
        foreign_reference = AuthService.get_pluggy_reference(2)
        for item_id, item in (
            ("unknown", {"id": "unknown", "clientUserId": foreign_reference}),
            ("unknown", {"id": "unknown", "clientUserId": None}),
            ("item-2", {"id": "item-2", "clientUserId": None}),
        ):
            with (
                patch.object(pluggy_service, "get_item", return_value=item),
                patch.object(pluggy_service, "get_accounts_from_item") as fetch,
            ):
                result = self.client.post(
                    "/pluggy/accounts/sync",
                    json={"itemId": item_id},
                    headers={"X-CSRF-TOKEN": csrf},
                )
                self.assertEqual(result.status_code, 403, result.get_json())
                fetch.assert_not_called()
        self.assertEqual(Account.query.count(), 2)

    def test_owned_new_connection_saves_accounts_without_fetching_transactions(self):
        csrf = self.login()
        reference = AuthService.get_pluggy_reference(1)
        data = {
            "id": "new-account",
            "itemId": "new-item",
            "type": "BANK",
            "subtype": "CHECKING_ACCOUNT",
            "number": "123",
            "name": "Nova",
            "balance": 20,
        }
        with (
            patch.object(
                pluggy_service,
                "get_item",
                return_value={
                    "id": "new-item",
                    "clientUserId": reference,
                },
            ),
            patch.object(pluggy_service, "get_accounts_from_item", return_value=[data]),
            patch.object(pluggy_service, "get_transactions_for_account") as fetch,
        ):
            result = self.client.post(
                "/pluggy/accounts/sync",
                json={
                    "itemId": "new-item",
                    "user_id": 2,
                },
                headers={"X-CSRF-TOKEN": csrf},
            )
            self.assertEqual(result.status_code, 200, result.get_json())
            fetch.assert_not_called()
        self.assertEqual(test_db.session.get(Account, "new-account").user_id, 1)

    def test_legacy_connection_only_remains_available_to_existing_owner(self):
        with patch.object(
            pluggy_service,
            "get_item",
            return_value={
                "id": "item-1",
                "clientUserId": None,
            },
        ):
            pluggy_service.verify_item_owner("item-1", 1)
            with self.assertRaises(APIError):
                pluggy_service.verify_item_owner("item-1", 2)

    def test_reused_user_id_does_not_inherit_previous_bank_connections(self):
        previous_reference = AuthService.get_pluggy_reference(1)
        csrf = self.login()
        self.client.delete(
            "/delete_users/1",
            json={
                "current_password": PASSWORD,
            },
            headers={"X-CSRF-TOKEN": csrf},
        )
        test_db.session.add(
            User(
                id=1,
                name="Outro usuário",
                email="new@example.com",
                password=PASSWORD_HASH,
                is_verified=True,
            )
        )
        test_db.session.commit()
        self.assertNotEqual(AuthService.get_pluggy_reference(1), previous_reference)
        with (
            patch.object(
                pluggy_service,
                "get_item",
                return_value={
                    "id": "item-1",
                    "clientUserId": previous_reference,
                },
            ),
            self.assertRaises(APIError),
        ):
            pluggy_service.verify_item_owner("item-1", 1)

    def test_unexpected_account_response_is_rejected_before_partial_writes(self):
        csrf = self.login()
        reference = AuthService.get_pluggy_reference(1)
        for bad in (
            {"id": "bad", "itemId": "item-2"},
            {"id": "account-2", "itemId": "new-item"},
        ):
            with (
                patch.object(
                    pluggy_service,
                    "get_item",
                    return_value={
                        "id": "new-item",
                        "clientUserId": reference,
                    },
                ),
                patch.object(
                    pluggy_service,
                    "get_accounts_from_item",
                    return_value=[
                        {"id": "new", "itemId": "new-item"},
                        bad,
                    ],
                ),
            ):
                result = self.client.post(
                    "/pluggy/accounts/sync",
                    json={"itemId": "new-item"},
                    headers={"X-CSRF-TOKEN": csrf},
                )
                self.assertIn(result.status_code, (403, 502))
        self.assertIsNone(test_db.session.get(Account, "new"))

    def test_manual_sync_checks_item_owner_before_fetching_any_transactions(self):
        csrf = self.login()
        reference = AuthService.get_pluggy_reference(2)
        with (
            patch.object(
                pluggy_service,
                "get_item",
                return_value={
                    "id": "item-1",
                    "clientUserId": reference,
                },
            ),
            patch.object(pluggy_service, "get_transactions_for_account") as fetch,
        ):
            result = self.client.post(
                "/pluggy/transactions/sync",
                json={
                    "mode": "month",
                    "year": 2026,
                    "month": 10,
                },
                headers={"X-CSRF-TOKEN": csrf},
            )
            self.assertEqual(result.status_code, 403)
            fetch.assert_not_called()

    def test_admin_can_create_user_and_reset_password_with_revocation(self):
        csrf = self.login()
        self.assertTrue(csrf)
        result = test_app.test_cli_runner().invoke(
            args=[
                "create-user",
                "--name",
                "Família",
                "--email",
                "family@example.com",
            ],
            input="senha-da-familia-123\nsenha-da-familia-123\n",
        )
        self.assertEqual(result.exit_code, 0, result.output)
        user = User.query.filter_by(email="family@example.com").first()
        self.assertTrue(user.is_verified)
        self.assertTrue(check_password_hash(user.password, "senha-da-familia-123"))
        result = test_app.test_cli_runner().invoke(
            args=[
                "reset-password",
                "--email",
                "user1@example.com",
            ],
            input="nova-senha-admin-123\nnova-senha-admin-123\n",
        )
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertEqual(self.client.get("/accounts").status_code, 401)

    def test_administrative_creation_does_not_overwrite_existing_pending_user(self):
        user = test_db.session.get(User, 1)
        user.is_verified = False
        test_db.session.commit()
        with self.assertRaises(APIError):
            UserService().create_user(
                {
                    "name": "Overwrite",
                    "email": "USER1@example.com",
                    "password": PASSWORD,
                }
            )
        self.assertEqual(user.name, "Pessoa 1")
        self.assertEqual(user.password, PASSWORD_HASH)

    def test_initialization_is_idempotent_and_preserves_users_and_balances(self):
        for _ in range(2):
            initialize_database()
        self.assertEqual(User.query.count(), 2)
        self.assertEqual(test_db.session.get(Account, "account-1").balance, 100)
        self.assertEqual(Transaction.query.count(), 2)
        self.assertEqual(test_db.session.get(User, 1).password, PASSWORD_HASH)


if __name__ == "__main__":
    unittest.main()

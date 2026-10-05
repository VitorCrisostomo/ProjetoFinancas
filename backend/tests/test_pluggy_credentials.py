"""Valida credenciais isoladas, administração e alterações privadas em .env fictícios."""

import os
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch
from uuid import uuid4

import test_authentication as auth_fixture
from werkzeug.security import check_password_hash

Store = auth_fixture.isolated_modules["services.pluggy_credentials"].PluggyCredentialsStore
APIError = auth_fixture.APIError
PluggyService = auth_fixture.pluggy_service
AuthService = auth_fixture.AuthService
User = auth_fixture.User
UserSecurity = auth_fixture.UserSecurity
test_app = auth_fixture.test_app
test_db = auth_fixture.test_db


class CredentialFileTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.path = Path(temporary.name) / ".env"
        self.store = Store(self.path)
        self.reference = str(uuid4())

    def test_preserves_other_settings_and_replaces_duplicates_as_one_pair(self):
        names = Store.variable_names(self.reference)
        prefix = '# configuração\r\nJWT_SECRET_KEY="fictício"\r\nOTHER="duas\nlinhas"\r\n'
        self.path.write_bytes(
            (prefix + f"{names[0]}=old\n{names[0]}=duplicate\n{names[1]}=old\n").encode()
        )
        with self.store.change(self.reference, "new-id", "new-secret"):
            pass
        content = self.path.read_bytes().decode()
        self.assertTrue(content.startswith(prefix))
        self.assertEqual(content.count(names[0] + "="), 1)
        self.assertEqual(content.count(names[1] + "="), 1)
        self.assertEqual(self.store.get(self.reference), ("new-id", "new-secret"))
        self.assertEqual(list(self.path.parent.glob(".env.*.tmp")), [])

    def test_special_characters_are_literal_and_do_not_expand_variables(self):
        pair = ("id'\\\"#", "${PATH}'\\$#=;")
        with self.store.change(self.reference, *pair):
            pass
        self.assertEqual(self.store.get(self.reference), pair)

    def test_absent_user_credentials_never_fall_back_to_global_or_another_user(self):
        self.path.write_text(
            "PLUGGY_CLIENT_ID=global\nPLUGGY_CLIENT_SECRET=global\n", encoding="utf-8"
        )
        with self.store.change(str(uuid4()), "other", "other-secret"):
            pass
        with patch.dict(
            os.environ, {"PLUGGY_CLIENT_ID": "global", "PLUGGY_CLIENT_SECRET": "global"}
        ):
            with self.assertRaises(APIError) as failure:
                self.store.get(self.reference)
        self.assertEqual(failure.exception.status_code, 503)

    def test_rejects_partial_or_injected_credentials_before_changing_file(self):
        self.path.write_text("OTHER=preserved\n", encoding="utf-8")
        for pair in (
            ("", "secret"),
            ("id", None),
            ("id", "a\nJWT_SECRET_KEY=bad"),
            ("id", "spaces invalid"),
            (True, "secret"),
            ("id", "x" * 4097),
        ):
            with self.subTest(pair=pair), self.assertRaises(APIError):
                with self.store.change(self.reference, *pair):
                    self.fail("Credenciais inválidas aceitas")
        self.assertEqual(self.path.read_text(), "OTHER=preserved\n")

    def test_invalid_env_is_not_rewritten(self):
        self.path.write_text("BROKEN='unterminated\n", encoding="utf-8")
        before = self.path.read_bytes()
        with self.assertRaises(APIError):
            with self.store.change(self.reference, "id", "secret"):
                pass
        self.assertEqual(self.path.read_bytes(), before)

    def test_exception_restores_original_file_and_removes_new_file(self):
        for existing in (False, True):
            with self.subTest(existing=existing):
                if existing:
                    self.path.write_bytes(b"OTHER=preserved\r\n")
                with self.assertRaises(RuntimeError):
                    with self.store.change(self.reference, "id", "secret"):
                        raise RuntimeError("Falha simulada de confirmação")
                if existing:
                    self.assertEqual(self.path.read_bytes(), b"OTHER=preserved\r\n")
                else:
                    self.assertFalse(self.path.exists())

    def test_failed_atomic_replace_preserves_env_and_removes_temporary_secret_file(self):
        self.path.write_text("OTHER=preserved\n", encoding="utf-8")
        with patch.object(os, "replace", side_effect=OSError("Falha simulada")):
            with self.assertRaises(APIError):
                with self.store.change(self.reference, "id", "secret"):
                    pass
        self.assertEqual(self.path.read_text(), "OTHER=preserved\n")
        self.assertEqual(list(self.path.parent.glob(".env.*.tmp")), [])

    def test_concurrent_updates_keep_both_user_pairs(self):
        references = [str(uuid4()), str(uuid4())]

        def save(index):
            with Store(self.path).change(references[index], f"id-{index}", f"secret-{index}"):
                pass

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(save, index) for index in range(2)]
            for future in futures:
                future.result(timeout=15)
        for index in range(2):
            self.assertEqual(self.store.get(references[index]), (f"id-{index}", f"secret-{index}"))


class UserCredentialTests(unittest.TestCase):
    def setUp(self):
        auth_fixture.AuthenticationTests.setUp(self)
        self.store = Store()

    def tearDown(self):
        auth_fixture.AuthenticationTests.tearDown(self)

    def save(self, user_id, client_id, secret):
        reference = AuthService.get_pluggy_reference(user_id)
        with self.store.change(reference, client_id, secret):
            pass
        return reference

    def invoke(self, command, email, inputs):
        return test_app.test_cli_runner().invoke(args=[command, "--email", email], input=inputs)

    def test_admin_creation_saves_hidden_credentials_and_user_identity_together(self):
        result = test_app.test_cli_runner().invoke(
            args=["create-user", "--name", "Família", "--email", "new@example.com"],
            input="senha-nova-de-teste\nsenha-nova-de-teste\nfake-id\nfake-secret\nfake-secret\n",
        )
        self.assertEqual(result.exit_code, 0, result.output)
        user = User.query.filter_by(email="new@example.com").one()
        reference = test_db.session.get(UserSecurity, user.id).pluggy_reference
        self.assertEqual(self.store.get(reference), ("fake-id", "fake-secret"))
        self.assertTrue(check_password_hash(user.password, "senha-nova-de-teste"))
        for secret in ("fake-id", "fake-secret", "senha-nova-de-teste"):
            self.assertNotIn(secret, result.output)
            self.assertNotIn(secret, str(user.to_json()))

    def test_reset_password_can_keep_credentials_unchanged(self):
        reference = self.save(1, "keep-id", "keep-secret")
        before = self.store.path.read_bytes()
        result = self.invoke(
            "reset-password", "user1@example.com", "nova-senha-de-teste\nnova-senha-de-teste\nn\n"
        )
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertEqual(self.store.path.read_bytes(), before)
        self.assertEqual(self.store.get(reference), ("keep-id", "keep-secret"))

    def test_reset_password_changes_only_selected_users_credentials_and_revokes_sessions(self):
        csrf = auth_fixture.AuthenticationTests.login(self)
        self.assertTrue(csrf)
        first = self.save(1, "first-id", "first-secret")
        second = self.save(2, "second-id", "second-secret")
        result = self.invoke(
            "reset-password",
            "user1@example.com",
            "nova-senha-de-teste\nnova-senha-de-teste\ny\nnew-id\nnew-secret\nnew-secret\n",
        )
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertEqual(self.store.get(first), ("new-id", "new-secret"))
        self.assertEqual(self.store.get(second), ("second-id", "second-secret"))
        self.assertEqual(test_db.session.get(UserSecurity, 1).pluggy_reference, first)
        self.assertEqual(self.client.get("/accounts").status_code, 401)

    def test_configure_pluggy_can_change_existing_access_without_changing_password(self):
        previous = test_db.session.get(User, 1).password
        result = self.invoke("configure-pluggy", "USER1@example.com", "id\nsecret\nsecret\n")
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertEqual(test_db.session.get(User, 1).password, previous)
        self.assertEqual(self.store.get(AuthService.get_pluggy_reference(1)), ("id", "secret"))

    def test_failed_credential_save_rolls_back_new_user_and_security_identity(self):
        with patch.object(Store, "_write", side_effect=OSError("Falha simulada")):
            result = test_app.test_cli_runner().invoke(
                args=["create-user", "--name", "Família", "--email", "new@example.com"],
                input="senha-nova-de-teste\nsenha-nova-de-teste\nid\nsecret\nsecret\n",
            )
        self.assertNotEqual(result.exit_code, 0)
        self.assertEqual(User.query.count(), 2)
        self.assertEqual(UserSecurity.query.count(), 0)

    def test_failed_database_commit_restores_password_sessions_and_env(self):
        auth_fixture.AuthenticationTests.login(self)
        reference = self.save(1, "old-id", "old-secret")
        previous = test_db.session.get(User, 1).password
        before = self.store.path.read_bytes()
        with patch.object(test_db.session, "commit", side_effect=RuntimeError("Falha simulada")):
            result = self.invoke(
                "reset-password",
                "user1@example.com",
                "nova-senha-de-teste\nnova-senha-de-teste\ny\nnew-id\nnew-secret\nnew-secret\n",
            )
        self.assertNotEqual(result.exit_code, 0)
        self.assertEqual(test_db.session.get(User, 1).password, previous)
        self.assertEqual(self.store.path.read_bytes(), before)
        self.assertEqual(self.store.get(reference), ("old-id", "old-secret"))
        self.assertEqual(self.client.get("/accounts").status_code, 200)

    def test_reused_numeric_id_does_not_inherit_credentials_of_deleted_user(self):
        old = self.save(1, "old-id", "old-secret")
        test_db.session.delete(test_db.session.get(UserSecurity, 1))
        test_db.session.commit()
        new = AuthService.get_pluggy_reference(1)
        self.assertNotEqual(new, old)
        with self.assertRaises(APIError):
            self.store.get(new)

    def test_each_service_uses_own_pair_and_new_requests_read_rotated_values(self):
        self.save(1, "first-id", "first-secret")
        self.save(2, "second-id", "second-secret")
        first = PluggyService(1)
        second = PluggyService(2)
        http = PluggyService._get_api_key.__globals__["requests"]
        with patch.object(
            http,
            "post",
            return_value=Mock(status_code=200, json=Mock(return_value={"apiKey": "key"})),
        ) as post:
            first._get_api_key()
            second._get_api_key()
            self.assertEqual(
                post.call_args_list[0].kwargs["json"],
                {"clientId": "first-id", "clientSecret": "first-secret"},
            )
            self.assertEqual(
                post.call_args_list[1].kwargs["json"],
                {"clientId": "second-id", "clientSecret": "second-secret"},
            )
            self.save(1, "rotated-id", "rotated-secret")
            self.assertEqual(first._credentials(), ("first-id", "first-secret"))
            PluggyService(1)._get_api_key()
            self.assertEqual(
                post.call_args.kwargs["json"],
                {"clientId": "rotated-id", "clientSecret": "rotated-secret"},
            )

    def test_unconfigured_or_unscoped_users_do_not_contact_provider(self):
        self.save(2, "other-id", "other-secret")
        http = PluggyService._get_api_key.__globals__["requests"]
        with patch.object(http, "post") as post:
            for service in (PluggyService(), PluggyService(1)):
                with self.assertRaises(APIError):
                    service._get_api_key()
            with self.assertRaises(APIError):
                PluggyService(1).get_connect_token(2)
            post.assert_not_called()

    def test_api_keys_are_reused_only_inside_the_same_user_request(self):
        self.save(1, "first-id", "first-secret")
        self.save(2, "second-id", "second-secret")
        first, second = PluggyService(1), PluggyService(2)
        http = PluggyService._get_api_key.__globals__["requests"]
        with patch.object(
            http,
            "post",
            side_effect=[
                Mock(status_code=200, json=Mock(return_value={"apiKey": "first-key"})),
                Mock(status_code=200, json=Mock(return_value={"apiKey": "second-key"})),
            ],
        ) as post:
            self.assertEqual(first._get_api_key(), "first-key")
            self.assertEqual(second._get_api_key(), "second-key")
            self.assertEqual(first._get_api_key(), "first-key")
            self.assertEqual(post.call_count, 2)

    def test_authenticated_routes_ignore_user_id_from_request_and_do_not_return_secrets(self):
        self.save(1, "first-id", "first-secret")
        self.save(2, "second-id", "second-secret")
        csrf = auth_fixture.AuthenticationTests.login(self)
        http = PluggyService._get_api_key.__globals__["requests"]
        with patch.object(
            http,
            "post",
            side_effect=[
                Mock(status_code=200, json=Mock(return_value={"apiKey": "key-first"})),
                Mock(status_code=200, json=Mock(return_value={"accessToken": "connect-first"})),
            ],
        ) as post:
            response = self.client.post(
                "/pluggy/connect_token", json={"user_id": 2}, headers={"X-CSRF-TOKEN": csrf}
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {"connectToken": "connect-first"})
        self.assertEqual(
            post.call_args_list[0].kwargs["json"],
            {"clientId": "first-id", "clientSecret": "first-secret"},
        )
        self.assertNotIn("secret", response.get_data(as_text=True))

    def test_profile_update_cannot_edit_server_side_credentials(self):
        self.save(1, "first-id", "first-secret")
        before = self.store.path.read_bytes()
        csrf = auth_fixture.AuthenticationTests.login(self)
        response = self.client.patch(
            "/update_users/1",
            json={
                "current_password": auth_fixture.PASSWORD,
                "client_id": "injected-id",
                "client_secret": "injected-secret",
            },
            headers={"X-CSRF-TOKEN": csrf},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.store.path.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()

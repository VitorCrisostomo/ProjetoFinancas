"""Valida períodos e paginação com respostas simuladas, sem acesso à rede."""

import sys
import unittest
from types import ModuleType
from unittest.mock import Mock, patch

from exceptions.api_errors import APIError, ValidationError


class RequestFailure(Exception):
    """Falha simulada de conexão com o provedor."""


requests_stub = ModuleType("requests")
requests_stub.get = Mock()
requests_stub.post = Mock()
requests_stub.RequestException = RequestFailure

# Isola o cliente HTTP para executar os testes sem credenciais ou bibliotecas externas.
with patch.dict(sys.modules, {"requests": requests_stub}):
    from services.pluggy_service import PluggyService


def response(data, status=200):
    return Mock(status_code=status, json=Mock(return_value=data))


class PluggySyncTests(unittest.TestCase):
    def setUp(self):
        requests_stub.get.reset_mock(return_value=True, side_effect=True)
        requests_stub.post.reset_mock(return_value=True, side_effect=True)
        self.service = PluggyService()
        self.service._get_api_key = Mock(return_value="test-key")

    def test_month_boundaries(self):
        for year, month, last in ((2024, 2, 29), (2026, 2, 28), (2026, 12, 31)):
            self.assertEqual(
                self.service.get_sync_date_range({"mode": "month", "year": year, "month": month}),
                (f"{year}-{month:02}-01", f"{year}-{month:02}-{last}"),
            )

    def test_rejects_invalid_options(self):
        for options in (
            None,
            {},
            {"mode": "all"},
            [],
            {"mode": "other"},
            {"mode": "month"},
            {"mode": "month", "month": 13, "year": 2026},
            {"mode": "month", "month": True, "year": 2026},
            {"mode": "month", "month": 2, "year": "2026"},
            {"mode": "month", "month": 2, "year": 1899},
        ):
            with self.subTest(options=options), self.assertRaises(ValidationError):
                self.service.get_sync_date_range(options)

    def test_fetches_every_cursor_page(self):
        cursor = "?accountId=account&after=opaque%2Bcursor"
        requests_stub.get.side_effect = [
            response({"results": [{"id": "first"}], "next": cursor}),
            response({"results": [{"id": "second"}], "next": None}),
        ]
        result = self.service.get_transactions_for_account("account")
        self.assertEqual([transaction["id"] for transaction in result], ["first", "second"])
        first, second = requests_stub.get.call_args_list
        self.assertEqual(first.kwargs["params"], {"accountId": "account"})
        self.assertEqual(second.args[0], "https://api.pluggy.ai/v2/transactions" + cursor)
        self.assertIsNone(second.kwargs["params"])
        self.service._get_api_key.assert_called_once()

    def test_passes_month_limits_and_preserves_cursor(self):
        cursor = "?accountId=a&dateFrom=2024-02-01&dateTo=2024-02-29&after=next"
        requests_stub.get.side_effect = [
            response({"results": [], "next": cursor}),
            response({"results": [{"id": "last-day"}], "next": None}),
        ]
        self.service.get_transactions_for_account("a", "2024-02-01", "2024-02-29")
        calls = requests_stub.get.call_args_list
        self.assertEqual(
            calls[0].kwargs["params"],
            {"accountId": "a", "dateFrom": "2024-02-01", "dateTo": "2024-02-29"},
        )
        self.assertEqual(calls[1].args[0], "https://api.pluggy.ai/v2/transactions" + cursor)

    def test_empty_history(self):
        requests_stub.get.return_value = response({"results": [], "next": None})
        self.assertEqual(self.service.get_transactions_for_account("a"), [])

    def test_rejects_invalid_or_repeating_cursor(self):
        for cursor in ("https://other.example/path", "", 123):
            requests_stub.get.side_effect = None
            requests_stub.get.return_value = response({"results": [], "next": cursor})
            with self.subTest(cursor=cursor), self.assertRaises(APIError):
                self.service.get_transactions_for_account("a")
        requests_stub.get.side_effect = [
            response({"results": [], "next": "?after=same"}),
            response({"results": [], "next": "?after=same"}),
        ]
        with self.assertRaises(APIError):
            self.service.get_transactions_for_account("a")

    def test_provider_errors(self):
        for data, status in (({}, 500), ({"results": "invalid"}, 200), ([], 200)):
            requests_stub.get.return_value = response(data, status)
            with self.subTest(data=data, status=status), self.assertRaises(APIError):
                self.service.get_transactions_for_account("a")
        requests_stub.get.side_effect = RequestFailure("timeout")
        with self.assertRaises(APIError):
            self.service.get_transactions_for_account("a")

    def test_authentication_has_timeout(self):
        credentials = patch.object(
            self.service, "_credentials", return_value=("test-id", "test-secret")
        )
        credentials.start()
        self.addCleanup(credentials.stop)
        requests_stub.post.return_value = response({"apiKey": "key"})
        self.assertEqual(PluggyService._get_api_key(self.service), "key")
        self.assertEqual(requests_stub.post.call_args.kwargs["timeout"], 30)
        self.service._api_key = None
        requests_stub.post.side_effect = RequestFailure("timeout")
        with self.assertRaises(APIError):
            PluggyService._get_api_key(self.service)


if __name__ == "__main__":
    unittest.main()

"""Cenário Docker com dados fictícios; não acessa Pluggy nem configurações do host."""

import argparse
import http.client
import json
import sqlite3
import sys
from contextlib import closing
from datetime import datetime
from http.cookies import SimpleCookie
from pathlib import Path
from urllib.parse import urlsplit


def synthetic_password():
    return "-".join(("docker", "synthetic", "fixture", "2026"))


def seed(backend_directory):
    sys.path.insert(0, str(Path(backend_directory).resolve()))
    from werkzeug.security import generate_password_hash

    from config import db
    from main import app
    from models.account import Account
    from models.transaction import Transaction
    from models.user import User

    with app.app_context():
        if (
            app.config["AUTH_ALLOWED_ORIGINS"] != ["https://docker-smoke.fixture.ts.net"]
            or app.config.get("DEPLOYMENT_MODE") != "docker"
        ):
            raise RuntimeError("O cenário exige a configuração exclusiva do teste Docker.")
        if User.query.count() or Account.query.count() or Transaction.query.count():
            raise RuntimeError("O cenário exige um banco vazio criado exclusivamente para teste.")
        for user_id in (1, 2):
            db.session.add(
                User(
                    id=user_id,
                    name=f"Synthetic person {user_id}",
                    email=f"smoke-user{user_id}@example.invalid",
                    password=generate_password_hash(synthetic_password()),
                    is_verified=True,
                )
            )
        db.session.commit()
        for user_id in (1, 2):
            db.session.add(
                Account(
                    id=f"smoke-account-{user_id}",
                    user_id=user_id,
                    itemId=f"smoke-item-{user_id}",
                    type="BANK",
                    subtype="CHECKING_ACCOUNT",
                    number=f"SYNTHETIC-{user_id}",
                    name=f"Synthetic account {user_id}",
                    balance=17.5 + user_id,
                )
            )
        db.session.commit()
        for user_id in (1, 2):
            db.session.add(
                Transaction(
                    id=user_id,
                    user_id=user_id,
                    account_id=f"smoke-account-{user_id}",
                    external_id=f"smoke-transaction-{user_id}",
                    name=f"Synthetic transaction {user_id}",
                    date=datetime(2026, 10, 1),
                    value=17.5 + user_id,
                    type="income",
                    category="Extra",
                )
            )
        db.session.commit()
    print("Cenário fictício preparado: dois usuários com dados financeiros separados.")


class Client:
    def __init__(self, base_url, app_host):
        target = urlsplit(base_url)
        if target.scheme != "http" or not target.hostname or target.path:
            raise ValueError("Informe a URL HTTP interna do web, sem caminho.")
        self.target = target
        self.app_host = app_host
        self.cookie = None
        self.csrf = None

    def request(self, method, path, payload=None, csrf=False, host=None, origin=None):
        headers = {"Host": host or self.app_host}
        if self.cookie:
            # O tráfego do teste é HTTP interno. A URL pública é HTTPS: verifica
            # Secure, mas envia o cookie explicitamente para exercer o proxy real.
            headers["Cookie"] = self.cookie
        if method in {"POST", "PATCH", "PUT", "DELETE"}:
            headers["Origin"] = origin or f"https://{self.app_host}"
        if csrf:
            headers["X-CSRF-TOKEN"] = self.csrf
        body = None
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        connection = http.client.HTTPConnection(
            self.target.hostname, self.target.port or 80, timeout=10
        )
        try:
            connection.request(method, path, body=body, headers=headers)
            response = connection.getresponse()
            return response.status, response.headers, response.read()
        finally:
            connection.close()

    def json(self, method, path, expected=200, **kwargs):
        status, headers, body = self.request(method, path, **kwargs)
        if status != expected:
            raise AssertionError(f"{method} {path}: status {status}, esperado {expected}.")
        return json.loads(body), headers

    def login(self, user_id):
        document, headers = self.json(
            "POST",
            "/api/login",
            payload={
                "email": f"smoke-user{user_id}@example.invalid",
                "password": synthetic_password(),
            },
        )
        assert document["user"]["id"] == user_id
        self.csrf = document["csrf_token"]
        assert isinstance(self.csrf, str) and self.csrf
        cookies = SimpleCookie()
        for value in headers.get_all("Set-Cookie", []):
            cookies.load(value)
        token = cookies["access_token_cookie"]
        assert token["secure"] and token["httponly"]
        assert token["samesite"].lower() == "lax"
        self.cookie = token.OutputString(attrs=[])


def check_http(base_url, app_host):
    first, second = Client(base_url, app_host), Client(base_url, app_host)
    first.json("GET", "/api/accounts", expected=401)
    health, _headers = first.json("GET", "/api/healthz")
    assert health == {"status": "ok"}
    first.login(1)
    second.login(2)
    for client, user_id in ((first, 1), (second, 2)):
        session, _headers = client.json("GET", "/api/auth/session")
        assert session["user"]["id"] == user_id
        accounts, _headers = client.json("GET", "/api/accounts")
        assert len(accounts) == 1 and accounts[0]["id"] == f"smoke-account-{user_id}"
        transactions, _headers = client.json("GET", "/api/transactions")
        assert len(transactions) == 1 and transactions[0]["user_id"] == user_id
        assert transactions[0]["value"] == 17.5 + user_id
        users, _headers = client.json("GET", "/api/users")
        assert [user["id"] for user in users["users"]] == [user_id]
    first.json(
        "PATCH",
        "/api/update_transactions/1",
        expected=401,
        payload={"name": "Synthetic edited transaction"},
    )
    first.json(
        "PATCH",
        "/api/update_transactions/1",
        expected=403,
        payload={"name": "Synthetic edited transaction"},
        csrf=True,
        origin="https://unauthorized.invalid",
    )
    first.json(
        "PATCH",
        "/api/update_transactions/2",
        expected=404,
        payload={"name": "Synthetic edited transaction"},
        csrf=True,
    )
    updated, _headers = first.json(
        "PATCH",
        "/api/update_transactions/1",
        payload={"name": "Synthetic edited transaction"},
        csrf=True,
    )
    assert updated["name"] == "Synthetic edited transaction"
    status, _headers, _body = first.request("GET", "/api/healthz", host="wrong.invalid")
    assert status == 421
    status, headers, body = first.request("GET", "/transactions")
    assert status == 200 and "text/html" in headers["Content-Type"]
    assert b"<html" in body.lower()
    first.json("POST", "/api/logout", expected=401)
    first.json("POST", "/api/logout", csrf=True)
    first.json("GET", "/api/auth/session", expected=401)
    # A segunda sessão permanece ativa no snapshot: a recuperação deve revogá-la.
    second.json("GET", "/api/auth/session")
    print("HTTP verificado: login, cookies, CSRF, isolamento, edição, logout, host e SPA.")


def verify_recovery(directory):
    root = Path(directory).resolve()
    database = root / "financehub.db"
    with closing(sqlite3.connect(database.as_uri() + "?mode=ro", uri=True)) as connection:
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        for table in ("users", "accounts", "transactions"):
            assert connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0] == 2
        count, revoked = connection.execute(
            "SELECT COUNT(*), COALESCE(SUM(revoked), 0) FROM auth_sessions"
        ).fetchone()
        assert count >= 2 and revoked == count
        for table in ("accounts", "transactions"):
            for (envelope,) in connection.execute(f'SELECT encrypted_data FROM "{table}"'):
                assert envelope.startswith("fh1:") and "Synthetic" not in envelope
    assert (root / "app.env").is_file()
    print(
        "Recuperação verificada: dois usuários, conteúdo financeiro criptografado e sessões revogadas."
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--seed", action="store_true")
    modes.add_argument("--check", action="store_true")
    modes.add_argument("--verify-recovery", action="store_true")
    parser.add_argument("--backend-dir", default="/app/backend")
    parser.add_argument("--base-url", default="http://web:8080")
    parser.add_argument("--host", default="docker-smoke.fixture.ts.net")
    parser.add_argument("--directory")
    args = parser.parse_args()
    if args.seed:
        seed(args.backend_dir)
    elif args.check:
        check_http(args.base_url, args.host)
    else:
        if not args.directory:
            parser.error("--verify-recovery exige --directory.")
        verify_recovery(args.directory)


if __name__ == "__main__":
    main()

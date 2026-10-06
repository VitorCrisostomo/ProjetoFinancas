"""Prepara estado externo uma única vez; nunca substitui dados ou chaves existentes."""

import argparse
import secrets
import sqlite3
import sys
from contextlib import closing
from io import StringIO
from pathlib import Path
from urllib.parse import urlsplit

from dotenv.parser import parse_stream

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "backend"))

from services.data_encryption import generate_key_file, write_private_file  # noqa: E402


def prepare(root, origin, fresh=False, source_env=None, source_key=None, source_database=None):
    root = Path(root).resolve()
    if root == PROJECT or PROJECT in root.parents or root in PROJECT.parents:
        raise ValueError("Mantenha o estado persistente fora do checkout da aplicação.")
    parsed = urlsplit(origin)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.path
        or parsed.query
        or parsed.fragment
        or "*" in parsed.netloc
    ):
        raise ValueError("Informe uma origem HTTPS exata, sem caminho ou credenciais.")
    if root.exists():
        raise ValueError("O diretório de estado já existe; preparação não sobrescreve arquivos.")
    if fresh and any((source_env, source_key, source_database)):
        raise ValueError("Não misture instalação nova com fontes existentes.")
    if not fresh and not all((source_env, source_key, source_database)):
        raise ValueError("Para preservar dados, informe configuração, banco e chave existentes.")
    content, snapshot, key = "", None, None
    if not fresh:
        content = Path(source_env).read_text(encoding="utf-8")
        key = Path(source_key).read_bytes()
        from services.data_encryption import DataCipher

        DataCipher.from_key_file(source_key)
        database = Path(source_database).resolve()
        with closing(
            sqlite3.connect(database.as_uri() + "?mode=ro", uri=True, timeout=30)
        ) as source:
            with closing(sqlite3.connect(":memory:")) as destination:
                source.backup(destination)
                if destination.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                    raise ValueError("O banco de origem não passou na verificação de integridade.")
                for table in ("accounts", "transactions"):
                    columns = {
                        row[1] for row in destination.execute(f'PRAGMA table_info("{table}")')
                    }
                    if columns and "encrypted_data" not in columns:
                        raise ValueError(
                            "Migre a criptografia na origem antes de preparar produção."
                        )
                snapshot = destination.serialize()
                # O snapshot independente não precisa do diário WAL da origem.
                snapshot = snapshot[:18] + b"\x01\x01" + snapshot[20:]
    bindings = list(parse_stream(StringIO(content)))
    if any(binding.error for binding in bindings):
        raise ValueError("Sintaxe inválida na configuração de origem.")
    root.mkdir(parents=True, mode=0o700)
    for name in ("config", "keys", "data", "backups", "logs", "services", "www"):
        (root / name).mkdir(mode=0o700)
    key_path = root / "keys/financial-data-keys.json"
    if fresh:
        generate_key_file(key_path)
    else:
        write_private_file(key_path, key)
        write_private_file(root / "data/financehub.db", snapshot)
    settings = {
        "APP_ENV": "production",
        "JWT_SECRET_KEY": secrets.token_hex(32),
        "AUTH_COOKIE_SECURE": "true",
        "AUTH_ALLOWED_ORIGINS": origin,
        "DATABASE_URI": "sqlite:///" + (root / "data/financehub.db").as_posix(),
        "DATA_ENCRYPTION_KEY_FILE": key_path.as_posix(),
        "BACKUP_DIRECTORY": (root / "backups").as_posix(),
        "SERVER_HOST": "127.0.0.1",
        "SERVER_PORT": "8000",
        "TRUSTED_PROXY": "127.0.0.1",
    }
    preserved = "".join(
        binding.original.string
        for binding in bindings
        if binding.key not in settings and binding.key != "FINANCEHUB_FILE_ACCESS_SID"
    )
    if preserved and not preserved.endswith("\n"):
        preserved += "\n"
    for name, value in settings.items():
        quoted_value = value.replace("\\", "\\\\").replace("'", "\\'")
        preserved += f"{name}='{quoted_value}'\n"
    write_private_file(root / "config/app.env", preserved.encode("utf-8"))
    print(
        "Estado de produção preparado; dados/chaves existentes preservados e JWT de produção nova."
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-dir", required=True)
    parser.add_argument("--origin", required=True)
    parser.add_argument("--fresh", action="store_true")
    parser.add_argument("--source-env")
    parser.add_argument("--source-key")
    parser.add_argument("--source-database")
    args = parser.parse_args()
    try:
        prepare(
            args.state_dir,
            args.origin,
            args.fresh,
            args.source_env,
            args.source_key,
            args.source_database,
        )
    except (OSError, ValueError, RuntimeError, sqlite3.Error):
        parser.exit(
            1,
            "Preparação falhou. Confira origem, caminhos, chave e banco; nenhum arquivo existente é substituído.\n",
        )


if __name__ == "__main__":
    main()

"""Recupera um backup com a chave preservada, mesmo sem uma instalação existente."""

import argparse
import os
import secrets
import sys
from pathlib import Path
from tempfile import TemporaryDirectory


def restore(backup, key, output_directory):
    # Cria só uma configuração efêmera. Não importa configuração da origem,
    # não abre seu SQLite e não substitui chaves ou arquivos existentes.
    backend = Path(__file__).resolve().parents[2] / "backend"
    if "config" in sys.modules or "main" in sys.modules:
        raise RuntimeError("Execute a recuperação em um processo separado da aplicação.")
    sys.path.insert(0, str(backend))
    from services.data_encryption import DataCipher, write_private_file

    key = Path(key).resolve(strict=True)
    DataCipher.from_key_file(key)
    with TemporaryDirectory(prefix="financehub-recovery-") as temporary:
        root = Path(temporary)
        configuration = root / "app.env"
        values = {
            "APP_ENV": "production",
            "DEPLOYMENT_MODE": "native",
            "JWT_SECRET_KEY": secrets.token_hex(32),
            "AUTH_COOKIE_SECURE": "true",
            "AUTH_ALLOWED_ORIGINS": "https://recovery.invalid",
            "DATABASE_URI": "sqlite:///" + (root / "unused.db").as_posix(),
            "DATA_ENCRYPTION_KEY_FILE": key.as_posix(),
            "BACKUP_DIRECTORY": (root / "unused-backups").as_posix(),
        }
        content = ""
        for name, value in values.items():
            quoted = value.replace("\\", "\\\\").replace("'", "\\'")
            content += f"{name}='{quoted}'\n"
        write_private_file(configuration, content.encode("utf-8"))
        os.environ["FINANCEHUB_ENV_FILE"] = str(configuration)
        from main import app
        from services.backup_service import restore_backup

        with app.app_context():
            return restore_backup(backup, output_directory)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backup", required=True)
    parser.add_argument("--key", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    try:
        restore(args.backup, args.key, args.output_dir)
    except Exception:
        # As exceções dos leitores podem conter caminhos ou conteúdo confidencial.
        print(
            "Recuperação falhou; confira backup, chave original e pasta nova de saída.",
            file=sys.stderr,
        )
        return 1
    print("Banco e configuração recuperados; sessões antigas revogadas. Prepare o novo estado.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
